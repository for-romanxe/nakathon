import importlib.util, os, pathlib, unittest
from unittest import mock
os.environ["MODEL"] = "mock"; os.environ["MOCK_DELAY"] = "0"
from backend.model import client
from backend import contracts


class MockClient(unittest.TestCase):
    def test_symptom_matches_schema_and_enums(self):
        e = contracts.enums()
        for text in ["어지러워요", "my chest hurts", "오늘은 특별한 증상 없어요", "죽고 싶어요"]:
            out = client.extract_symptoms(text, "ko")
            self.assertEqual(contracts.check_schema(out, contracts.schema("symptom")), [])
            self.assertTrue(set(out["codes"]) <= set(e["symptom_codes"]))

    def test_crisis_and_chest_are_immediate_codes(self):
        e = contracts.enums()
        self.assertIn(client.extract_symptoms("가슴이 아파요", "ko")["codes"][0], e["immediate_warning_codes"])
        self.assertIn(client.extract_symptoms("I want to die", "en")["codes"][0], e["immediate_warning_codes"])

    def test_mood_and_explanation(self):
        self.assertEqual(contracts.check_schema(client.score_mood("오늘 꿀꿀해", "ko"), contracts.schema("mood")), [])
        out = client.explain("caution", [], ["orthostatic_intolerance"], [], "ko")
        self.assertEqual(out["condition_id"], "orthostatic_intolerance")

    def test_every_mock_row_passes_schema(self):
        import json
        for kind in ("symptom", "mood", "explanation"):
            for row in json.loads((client.MOCK_DIR / f"{kind}.json").read_text(encoding="utf-8")):
                self.assertEqual(contracts.check_schema(row["out"], contracts.schema(kind)), [], f"{kind}: {row}")


GENERATOR = pathlib.Path(__file__).resolve().parents[2] / "ml/data/gen_symptoms.py"


def code_of(text):
    return client.extract_symptoms(text, "ko")["codes"][0]


class MockKeywords(unittest.TestCase):
    def test_keywords_do_not_fire_inside_other_words(self):
        cases = {"I fell asleep right away": "none", "I had a crash course": "none", "the pain disappeared": "none",
                 "I'm back to normal": "none", "운동을 끝내고 왔어요": "none", "기운이 넘쳐요": "none",
                 "잠시 쉬면 괜찮아요": "none", "한숨도 못 잤어요": "sleep_issue"}
        for text, code in cases.items():
            with self.subTest(text=text):
                self.assertEqual(code_of(text), code)

    def test_specific_keyword_wins_over_general(self):
        cases = {"목이 따가워요": "congestion", "목이 칼칼하고 기침이 나요": "congestion", "목이 뻐근해요": "musculoskeletal_pain",
                 "머리가 빙글빙글 돌아요": "dizziness", "hives on my back": "skin_rash", "I can't fall asleep": "sleep_issue"}
        for text, code in cases.items():
            with self.subTest(text=text):
                self.assertEqual(code_of(text), code)

    @unittest.skipUnless(GENERATOR.exists(), "dataset generator not present")
    def test_generator_phrases_never_map_to_a_different_code(self):
        spec = importlib.util.spec_from_file_location("gen_symptoms", GENERATOR)
        gen = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen)
        for code, (ko, en) in gen.PH.items():
            for text in ko + en:
                with self.subTest(code=code, text=text):
                    self.assertIn(code_of(text), (code, "none"))      # 못 알아듣는 건 허용, 다른 코드로 가는 건 금지
        for text in gen.PH["crisis"][0] + gen.PH["crisis"][1]:
            with self.subTest(text=text):
                self.assertEqual(code_of(text), "crisis")              # 위기 표현은 빠뜨리지 않는다
        for text in gen.NONE_PH[0] + gen.NONE_PH[1]:
            with self.subTest(text=text):
                self.assertEqual(code_of(text), "none")

    def test_mood_negation_is_not_read_as_good(self):
        for text in ("기분이 안 좋아요", "not good today"):
            with self.subTest(text=text):
                self.assertLessEqual(client.score_mood(text, "ko")["mood"], 2)
        self.assertGreaterEqual(client.score_mood("기분 좋아요", "ko")["mood"], 4)


class ExplainCandidates(unittest.TestCase):
    def test_result_is_always_among_the_candidates(self):
        for candidates in (["space_motion_sickness"], ["upper_respiratory", "co2_headache"], ["dehydration", "orthostatic_intolerance"]):
            with self.subTest(candidates=candidates):
                out = client.explain("caution", [], candidates, [], "ko")
                self.assertIn(out["condition_id"], candidates)
                self.assertEqual(contracts.check_schema(out, contracts.schema("explanation")), [])

    def test_candidate_order_decides(self):
        self.assertEqual(client.explain("caution", [], ["dehydration", "orthostatic_intolerance"], [], "ko")["condition_id"], "dehydration")
        self.assertEqual(client.explain("caution", [], ["space_motion_sickness", "sleep_deficit"], [], "ko")["condition_id"], "sleep_deficit")

    def test_no_candidates_means_none(self):
        self.assertEqual(client.explain("advisory", [], [], [], "ko")["condition_id"], "none")

    def test_candidate_without_a_scenario_cites_the_given_paragraphs(self):
        out = client.explain("caution", [], ["space_motion_sickness"], [{"id": "hrp:sms-01#p2", "text": "..."}], "en")
        self.assertEqual(out["cites"], ["hrp:sms-01#p2"])
        self.assertEqual(out["category"], contracts.enums()["conditions"]["space_motion_sickness"]["hrp"])

    def test_unknown_candidate_is_a_caller_error(self):
        with self.assertRaises(ValueError):
            client.explain("caution", [], ["made_up"], [], "ko")


class LiveOutputGuards(unittest.TestCase):
    def live(self, reply):
        return mock.patch.dict(os.environ, {"MODEL": "live"}), mock.patch.object(client, "_chat", return_value=reply)

    def test_condition_outside_the_candidates_is_rejected(self):
        env, chat = self.live({"category": "nutrition", "condition_id": "dehydration", "lines": ["x"], "cites": ["hrp:nut-01#p2"]})
        with env, chat, self.assertRaises(client.ModelOutputError):
            client.explain("caution", [], ["sleep_deficit"], [], "ko")

    def test_out_of_range_mood_is_rejected(self):
        env, chat = self.live({"mood": 9, "fatigue": 3, "stress": 3, "confidence": 0.5})
        with env, chat, self.assertRaises(client.ModelOutputError):
            client.score_mood("오늘 꿀꿀해", "ko")
