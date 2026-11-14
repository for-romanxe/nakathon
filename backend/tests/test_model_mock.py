import os, unittest
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
