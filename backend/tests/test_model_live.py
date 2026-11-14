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
                user = Stub.seen[0][1]["messages"][-1]["content"]
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
        first, retry = (seen[1]["messages"][-1]["content"] for seen in Stub.seen)
        self.assertNotIn("rejected", first)
        self.assertTrue(retry.startswith(first))
        self.assertIn("write no digits at all (you wrote: 12)", retry)
        self.assertIn("(you wrote: 입니다, 수면 부족)", retry)

    def test_explain_prompt_is_written_in_the_output_language_with_two_examples(self):
        # 연습 12문항에서 한국어 지시문 + 예시 2개가 첫 통과 7/7·해요체 7/7 로 가장 좋았다 (ml/eval/README.md).
        Stub.reply = completion(json.dumps({"category": "sleep", "condition_id": "sleep_deficit", "lines": ["잠이 부족할 수 있어요."], "cites": [1]}))
        paras = [{"id": "eval:sleep#p1", "text": "Sleep."}]
        for lang, in_system, in_example in (("ko", "한국어로 쓰세요", "좋아요"), ("en", "Write in English", "may")):
            with self.subTest(lang=lang):
                Stub.seen = []
                client.explain("advisory", [], ["sleep_deficit"], paras, lang, rejected={"numbers": ["12"]})
                messages = Stub.seen[0][1]["messages"]
                self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user", "assistant", "user"])
                self.assertIn(in_system, messages[0]["content"])
                self.assertIn('"lines": [', messages[0]["content"])
                for asked, answered in ((messages[1], messages[2]), (messages[3], messages[4])):
                    self.assertIn("paragraphs:\n[1] ", asked["content"])           # 예시 요청은 실제 요청과 같은 모양
                    self.assertNotIn("rejected", asked["content"])                  # 고칠 점은 실제 요청에만 붙는다
                    self.assertIn(in_example, " ".join(json.loads(answered["content"])["lines"]))
                self.assertIn("you wrote: 12", messages[5]["content"])

    def test_the_examples_shown_to_the_model_pass_the_verifier_themselves(self):
        # 예시가 검증기에 걸리는 문장이면 모델에게 걸리는 문장을 가르치는 셈이다.
        from backend import verify
        for lang, profile in client._explain_prompt().items():
            if lang.startswith("_"):
                continue
            for n, shot in enumerate(profile["shots"]):
                with self.subTest(lang=lang, shot=n):
                    ids = [f"eval:shot#p{i}" for i in range(1, len(shot["paragraphs"]) + 1)]
                    answer = dict(shot["answer"], cites=[ids[c - 1] for c in shot["answer"]["cites"]])
                    result = verify.verify(answer, shot["findings"], shot["level"], ids, lang, candidates=shot["candidates"])
                    self.assertEqual(result["fails"], [], result["note"])
                    if lang == "ko":
                        self.assertTrue(all(line.rstrip(".").endswith("요") for line in answer["lines"]), answer["lines"])

    def test_category_follows_the_condition_not_the_model(self):
        # 실제 모델이 category 에 "advisory"(판정 단계)나 상태 이름을 써 넣었다(10문항 중 4개). 범주는 상태 목록이 정한다.
        Stub.reply = completion(json.dumps({"category": "advisory", "condition_id": "sleep_deficit",
                                            "lines": ["Short sleep is possible."], "cites": [1]}))
        out = client.explain("advisory", [], ["sleep_deficit"], [{"id": "eval:sleep#p1", "text": "Sleep."}], "en")
        self.assertEqual(out["category"], "sleep")

    def test_a_space_inside_a_key_name_is_removed(self):
        # PC 에서 학습해 변환한 어댑터가 Mac 에서 "worse_ when" 이라고 써서, 코드가 맞은 답 3개가 스키마 오류로 버려졌다.
        Stub.reply = completion('{"codes": ["headache"], "onset": "today", "worse_ when": "unknown", "severity": 2, "needs_question": false}')
        out = client.extract_symptoms("오늘 headache가 좀 있어요", "ko")
        self.assertEqual((out["codes"], out["worse_when"]), (["headache"], "unknown"))
        self.assertNotIn("worse_ when", out)

    def test_keys_that_collide_after_removing_spaces_are_rejected(self):
        # "codes" 와 "co des" 가 같이 오면 공백을 지운 뒤 같은 키가 된다. 뒤의 값이 앞의 값을 덮어쓰면 안 된다.
        for reply in ('{"codes": ["headache"], "co des": ["congestion"], "onset": "today", "worse_when": "unknown", "severity": 2, "needs_question": false}',
                      '{"codes": ["headache"], "onset": "today", "worse_when": "standing", "worse_ when": "unknown", "severity": 2, "needs_question": false}'):
            with self.subTest(reply=reply[:40]):
                Stub.reply = completion(reply)
                with self.assertRaises(client.ModelOutputError) as caught:
                    client.extract_symptoms("머리가 아파요", "ko")
                self.assertNotIsInstance(caught.exception, client.ModelUnavailableError)
                self.assertIn("same key", str(caught.exception))

    def test_made_up_onset_or_worse_when_becomes_unknown(self):
        # 실제 모델이 "hurts when I bend it" 에 worse_when "bending" 을 지어내 맞는 코드까지 버려졌다.
        Stub.reply = completion(json.dumps({**SYMPTOM, "codes": ["musculoskeletal_pain"], "worse_when": "bending", "onset": "yesterday"}))
        out = client.extract_symptoms("My left knee hurts when I bend it", "en")
        self.assertEqual((out["codes"], out["worse_when"], out["onset"]), (["musculoskeletal_pain"], "unknown", "unknown"))
        Stub.reply = completion(json.dumps({**SYMPTOM, "codes": ["knee_pain"]}))      # 목록 밖 코드는 그대로 거부
        with self.assertRaises(client.ModelOutputError):
            client.extract_symptoms("My left knee hurts when I bend it", "en")

    def test_severity_outside_the_scale_is_clamped(self):
        # 실제 모델이 증상 없는 보고("no aches, appetite normal")에 severity 0 을 써서 none 보고가 통째로 버려졌다.
        Stub.reply = completion(json.dumps({**SYMPTOM, "codes": ["none"], "severity": 0}))
        self.assertEqual(client.extract_symptoms("No aches, appetite normal", "en")["severity"], 1)
        Stub.reply = completion(json.dumps({**SYMPTOM, "severity": 7}))
        self.assertEqual(client.extract_symptoms("My head is splitting", "en")["severity"], 5)
        Stub.reply = completion(json.dumps({**SYMPTOM, "severity": "high"}))             # 숫자가 아니면 그대로 거부
        with self.assertRaises(client.ModelOutputError):
            client.extract_symptoms("My head is splitting", "en")

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
