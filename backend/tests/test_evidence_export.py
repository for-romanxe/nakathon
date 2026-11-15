"""지식 문단을 백엔드 근거 파일로 바꾼 결과(ml/knowledge/export_evidence.py)가 백엔드에서 그대로 읽히는지 본다."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

from backend import contracts, docs, event_flow

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "knowledge"))
import export_evidence      # noqa: E402


def loaded(lang):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "evidence.json"
        path.write_text(json.dumps(export_evidence.export(lang), ensure_ascii=False), encoding="utf-8")
        with mock.patch.dict(os.environ, {"CREW_HEALTH_EVIDENCE": str(path)}):
            return event_flow.load_evidence()


class EvidenceExport(unittest.TestCase):
    def test_both_languages_load_and_group_into_documents(self):
        for lang in ("ko", "en"):
            with self.subTest(lang=lang):
                rows = loaded(lang)
                self.assertEqual(len(rows), 146)
                self.assertEqual(len(docs.build_docs(rows)), 81)      # 문서 안에서 제목·기관이 하나로 맞아야 묶인다

    def test_every_symptom_code_gets_a_reason_and_an_action_first(self):
        rows = loaded("ko")
        kinds = {p["id"]: p["kind"] for f in sorted((ROOT / "ml" / "knowledge").glob("kb_*.jsonl"))
                 for p in map(json.loads, f.read_text(encoding="utf-8").splitlines())}
        standing = {"question_key": "worse_standing", "answer": "yes"}
        for code in contracts.enums()["symptom_codes"]:
            if code == "none":
                continue
            with self.subTest(code=code):
                got = event_flow.relevant_evidence(rows, [code], standing)
                first = [kinds[row["id"]] for row in got[:2]]
                self.assertIn(first[0], export_evidence.WHY)      # 모델이 학습·평가 때 받은 모양: 이유 하나 + 할 일 하나
                self.assertIn(first[1], export_evidence.DO)
                self.assertEqual(got[0]["condition_id"], got[1]["condition_id"])
                self.assertNotIn("escalate", [kinds[row["id"]] for row in got])      # "즉시" 같은 말이 든 문단은 모델에 주지 않는다

    def test_standing_dizziness_paragraphs_wait_for_the_answer(self):
        rows = loaded("ko")
        asked = [row["condition_id"] for row in event_flow.relevant_evidence(rows, ["dizziness"], {})]
        self.assertTrue(asked)
        self.assertNotIn("orthostatic_intolerance", asked)


if __name__ == "__main__":
    unittest.main()
