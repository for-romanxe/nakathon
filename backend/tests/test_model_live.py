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

    def test_model_url_may_end_with_v1(self):
        # OpenAI 클라이언트 관례대로 .../v1 까지 적어도 같은 경로로 간다.
        Stub.reply = completion(json.dumps(SYMPTOM))
        for suffix in ("/v1", "/v1/", "/"):
            with self.subTest(suffix=suffix):
                Stub.seen = []
                self.use(MODEL_URL=self.url + suffix)
                self.assertEqual(client.extract_symptoms("어지러워요", "ko"), SYMPTOM)
                self.assertEqual(Stub.seen[0][0], "/v1/chat/completions")

    def test_default_model_name_is_the_one_mlx_lm_server_accepts(self):
        # MODEL_NAME 을 안 주면 mlx_lm.server 가 '서버를 띄울 때 준 모델'로 읽는 이름을 보낸다.
        Stub.reply = completion(json.dumps(SYMPTOM))
        with mock.patch.dict(os.environ):
            del os.environ["MODEL_NAME"]
            client.extract_symptoms("어지러워요", "ko")
        self.assertEqual(Stub.seen[0][1]["model"], "default_model")

    def test_explain_prompt_shows_lines_as_an_array(self):
        # 실제 모델(Ministral 8B)이 "1-2 sentences" 라는 말만 보고 lines 를 문자열로 냈다.
        Stub.reply = completion(json.dumps({"category": "cardiovascular", "condition_id": "dehydration",
                                            "lines": ["Fluid loss is possible."], "cites": ["hrp:oi-01#p2"]}))
        client.explain("caution", [], ["dehydration"], [{"id": "hrp:oi-01#p2", "text": "Drink fluids."}], "en")
        self.assertIn('"lines": [', Stub.seen[0][1]["messages"][0]["content"])

    def test_explain_cites_come_back_as_paragraph_numbers(self):
        # 실제 모델이 'eval:fluids#p1' 을 'fluids#p1' 로 줄여 써서 10문항 중 8개가 폐기됐다. id 를 쓰게 하지 않고 번호로 받는다.
        paras = [{"id": "eval:orthostatic#p1", "text": "Stand up slowly."}, {"id": "eval:fluids#p1", "text": "Drink fluids."}]
        reply = {"category": "nutrition", "condition_id": "dehydration", "lines": ["Fluid loss is possible."]}
        for cites, want in (([2], ["eval:fluids#p1"]), (["1", 2], ["eval:orthostatic#p1", "eval:fluids#p1"]),
                            (["eval:fluids#p1"], ["eval:fluids#p1"])):
            with self.subTest(cites=cites):
                Stub.seen = []
                Stub.reply = completion(json.dumps({**reply, "cites": cites}))
                self.assertEqual(client.explain("caution", [], ["dehydration"], paras, "en")["cites"], want)
                user = Stub.seen[0][1]["messages"][1]["content"]
                self.assertIn("[1] Stand up slowly.", user)
                self.assertNotIn("eval:fluids#p1", user)
        # "²", "①" 은 isdigit() 은 참이지만 int() 로 못 바꾼다. 그때도 ValueError 가 아니라 ModelOutputError 여야 한다.
        for cites in ([3], [0], ["fluids#p1"], [True], ["²"], ["①"], ["1²"]):
            with self.subTest(cites=cites):
                Stub.reply = completion(json.dumps({**reply, "cites": cites}))
                with self.assertRaises(client.ModelOutputError):
                    client.explain("caution", [], ["dehydration"], paras, "en")

    def test_retry_prompt_names_what_the_checker_rejected(self):
        # temperature 0 이라 같은 프롬프트로는 같은 문장이 다시 나온다. 재생성 때는 실패한 검사를 알려 준다.
        Stub.reply = completion(json.dumps({"category": "sleep", "condition_id": "sleep_deficit",
                                            "lines": ["Short sleep is possible."], "cites": [1]}))
        paras = [{"id": "eval:sleep#p1", "text": "Sleep."}]
        client.explain("advisory", [], ["sleep_deficit"], paras, "en")
        client.explain("advisory", [], ["sleep_deficit"], paras, "en", rejected={"numbers": ["12"], "wording": ["입니다", "수면 부족"]})
        first, retry = (seen[1]["messages"][1]["content"] for seen in Stub.seen)
        self.assertNotIn("rejected", first)
        self.assertTrue(retry.startswith(first))
        self.assertIn("write no digits at all (you wrote: 12)", retry)
        self.assertIn("(you wrote: 입니다, 수면 부족)", retry)

    def test_category_follows_the_condition_not_the_model(self):
        # 실제 모델이 category 에 "advisory"(판정 단계)나 상태 이름을 써 넣었다(10문항 중 4개). 범주는 상태 목록이 정한다.
        Stub.reply = completion(json.dumps({"category": "advisory", "condition_id": "sleep_deficit",
                                            "lines": ["Short sleep is possible."], "cites": [1]}))
        out = client.explain("advisory", [], ["sleep_deficit"], [{"id": "eval:sleep#p1", "text": "Sleep."}], "en")
        self.assertEqual(out["category"], "sleep")

    def test_made_up_onset_or_worse_when_becomes_unknown(self):
        # 실제 모델이 "hurts when I bend it" 에 worse_when "bending" 을 지어내 맞는 코드까지 버려졌다.
        Stub.reply = completion(json.dumps({**SYMPTOM, "codes": ["musculoskeletal_pain"], "worse_when": "bending", "onset": "yesterday"}))
        out = client.extract_symptoms("My left knee hurts when I bend it", "en")
        self.assertEqual((out["codes"], out["worse_when"], out["onset"]), (["musculoskeletal_pain"], "unknown", "unknown"))
        Stub.reply = completion(json.dumps({**SYMPTOM, "codes": ["knee_pain"]}))      # 목록 밖 코드는 그대로 거부
        with self.assertRaises(client.ModelOutputError):
            client.extract_symptoms("My left knee hurts when I bend it", "en")

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
