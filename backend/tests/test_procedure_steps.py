"""경보 절차 단계(pipeline.procedure_steps, 이슈 #47): 단계마다 열 수 있는 근거 문단이 있고, 약 이름이 없다."""
import json, sys, unittest
from pathlib import Path

from backend.model import pipeline

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "knowledge"))
import export_evidence      # noqa: E402

MEDICINES = ("aspirin", "ascriptin", "nitroglycerin", "nitrate", "아스피린", "니트로")


class ProcedureSteps(unittest.TestCase):
    def test_chest_pain_steps_follow_the_paragraphs_in_order_in_both_languages(self):
        for lang in ("ko", "en"):
            evidence = export_evidence.export(lang)
            rows = {row["id"]: row for row in evidence}
            got = pipeline.procedure_steps("cardiac_emergency", evidence, lang)
            with self.subTest(lang=lang):
                self.assertTrue(got["available"])
                self.assertEqual([s["cite_id"] for s in got["steps"]], [f"nasa:card-10#p{n}" for n in range(1, 6)])
                self.assertEqual(len({s["step_id"] for s in got["steps"]}), 5)
                self.assertTrue(all(s["text"].strip() and s["kind"] in ("treatment", "record", "cmo", "contact") for s in got["steps"]))
                self.assertEqual({rows[s["cite_id"]]["condition_id"] for s in got["steps"]}, {"cardiac_emergency"})
                self.assertIn("chest_pain", rows["nasa:card-10#p1"]["codes"])

    def test_steps_are_withheld_when_a_cited_paragraph_is_not_loaded_or_the_condition_has_no_procedure(self):
        evidence = export_evidence.export("ko")
        without_one = [row for row in evidence if row["id"] != "nasa:card-10#p3"]
        for got in (pipeline.procedure_steps("cardiac_emergency", without_one, "ko"),
                    pipeline.procedure_steps("cardiac_emergency", [], "ko"),
                    pipeline.procedure_steps("sleep_deficit", evidence, "ko")):
            self.assertEqual(got, {"available": False, "steps": []})

    def test_no_step_and_no_procedure_paragraph_names_a_medicine(self):
        steps = json.loads(pipeline.PROCEDURES.read_text(encoding="utf-8"))["cardiac_emergency"]["steps"]
        texts = [s[lang] for s in steps for lang in ("ko", "en")]
        texts += [row["text"] for lang in ("ko", "en") for row in export_evidence.export(lang) if row["id"].startswith("nasa:card-10#")]
        self.assertEqual(len(texts), 20)
        for text in texts:
            self.assertFalse([m for m in MEDICINES if m in text.lower()], text)


if __name__ == "__main__":
    unittest.main()
