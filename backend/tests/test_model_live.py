"""MODEL=live 경로를 가짜 OpenAI 호환 서버(127.0.0.1, 임시 포트)로 끝까지 돌린다. 실제 모델은 쓰지 않는다."""
import http.server, json, os, socket, threading, time, unittest
from unittest import mock

from backend.model import client

SYMPTOM = {"codes": ["dizziness"], "onset": "today", "worse_when": "standing", "severity": 2, "needs_question": True}


def completion(content):
    return 200, json.dumps({"choices": [{"message": {"role": "assistant", "content": content}}]}).encode()


class Stub(http.server.BaseHTTPRequestHandler):
    reply = completion("{}")     # (status, body) 테스트마다 바꾼다
    delay = 0.0
    seen = []

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        type(self).seen.append((self.path, json.loads(body)))
        time.sleep(type(self).delay)
        status, payload = type(self).reply
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class LiveModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Stub.seen, Stub.delay = [], 0.0
        self.use(MODEL="live", MODEL_URL=self.url, MODEL_NAME="stub-model", MODEL_TIMEOUT="5")

    def use(self, **env):
        patch = mock.patch.dict(os.environ, env)
        patch.start()
        self.addCleanup(patch.stop)

    def test_request_shape_and_reply(self):
        Stub.reply = completion(json.dumps(SYMPTOM))
        self.assertEqual(client.extract_symptoms("I feel dizzy when I stand up", "en"), SYMPTOM)
        path, body = Stub.seen[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(body["model"], "stub-model")
        self.assertEqual(body["temperature"], 0)
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertIn("I feel dizzy when I stand up", body["messages"][1]["content"])

    def test_first_json_object_is_used_when_the_model_says_more(self):
        one = json.dumps(SYMPTOM, ensure_ascii=False)
        for content in (
            one + '\n\n{"note": "second object"}',                       # 객체 두 개
            "Sure, here it is:\n```json\n" + one + "\n```\nLet me know {if} that helps.",   # 코드 펜스 + 뒤따르는 중괄호
            "Reading the report {carefully}... " + one,                  # 앞에 JSON 아닌 중괄호
        ):
            with self.subTest(content=content[:40]):
                Stub.reply = completion(content)
                self.assertEqual(client.extract_symptoms("어지러워요", "ko"), SYMPTOM)

    def test_reply_without_json_is_an_output_error(self):
        Stub.reply = completion("I cannot help with that.")
        with self.assertRaises(client.ModelOutputError) as caught:
            client.extract_symptoms("어지러워요", "ko")
        self.assertNotIsInstance(caught.exception, client.ModelUnavailableError)

    def test_transport_and_envelope_failures_are_model_unavailable(self):
        replies = {
            "http 500": (500, b'{"error": "boom"}'),
            "body is not json": (200, b"<html>bad gateway</html>"),
            "no choices": (200, b'{"choices": []}'),
            "no message": (200, b'{"choices": [{}]}'),
            "content is null": (200, b'{"choices": [{"message": {"content": null}}]}'),
            "envelope is a list": (200, b"[1, 2]"),
        }
        for name, reply in replies.items():
            with self.subTest(name=name):
                Stub.reply = reply
                with self.assertRaises(client.ModelUnavailableError):
                    client.score_mood("오늘 꿀꿀해", "ko")

    def test_connection_refused_is_model_unavailable(self):
        with socket.socket() as probe:                 # 아무도 듣지 않는 포트를 하나 얻는다
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.use(MODEL_URL=f"http://127.0.0.1:{port}")
        with self.assertRaises(client.ModelUnavailableError):
            client.extract_symptoms("어지러워요", "ko")

    def test_timeout_is_model_unavailable(self):
        Stub.reply, Stub.delay = completion(json.dumps(SYMPTOM)), 1.0
        self.use(MODEL_TIMEOUT="0.2")
        with self.assertRaises(client.ModelUnavailableError):
            client.extract_symptoms("어지러워요", "ko")

    def test_unavailable_can_be_handled_as_an_output_error(self):
        self.assertTrue(issubclass(client.ModelUnavailableError, client.ModelOutputError))
