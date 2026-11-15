"""우주선 조정 이유(pipeline.adjustment_reason, 이슈 #47): 근거 문단은 표가 정하고 모델은 이유 문장만 쓴다."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

from backend.model import client, pipeline

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml" / "knowledge"))
import export_evidence      # noqa: E402

TABLE = {k: v for k, v in json.loads(pipeline.ADJUSTMENTS.read_text(encoding="utf-8")).items() if k != "_doc"}
FINDINGS = [{"metric": "sleep", "value": 5.1, "baseline": 7.0, "sd": 0.7, "z": -2.7}]
KO = export_evidence.export("ko")
KINDS = {json.loads(line)["id"]: json.loads(line)["kind"]
         for f in sorted((ROOT / "ml" / "knowledge").glob("kb_*.jsonl")) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()}


class Table(unittest.TestCase):
    def test_every_target_cites_a_why_then_a_do_paragraph_of_its_condition_in_both_languages(self):
        self.assertEqual(set(TABLE), {"lighting", "schedule"})
        for lang in ("ko", "en"):
            rows = {row["id"]: row for row in export_evidence.export(lang)}
            for target, entry in TABLE.items():
                with self.subTest(lang=lang, target=target):
                    why, do = entry["cite_ids"]      # 설명 모델이 학습·평가 때 받은 모양: 이유 1개 + 살필 것 1개
                    self.assertIn(KINDS[why], export_evidence.WHY)
                    self.assertIn(KINDS[do], export_evidence.DO)
                    self.assertEqual({rows[i]["condition_id"] for i in entry["cite_ids"]}, {entry["condition_id"]})


class Reason(unittest.TestCase):
    def test_mock_mode_returns_a_reason_with_the_table_cites(self):
        with mock.patch.dict(os.environ, {"MODEL": "mock", "MOCK_DELAY": "0"}):
            for target, entry in TABLE.items():
                with self.subTest(target=target):
                    result = pipeline.adjustment_reason(target, "caution", FINDINGS, KO, "ko")
                    self.assertFalse(result["hold"], result["runs"])
                    self.assertTrue(result["reason"])
                    self.assertEqual(result["cite_ids"], entry["cite_ids"])
                    self.assertEqual(result["verified"], 5)

    def test_reason_joins_the_verified_lines_and_the_model_sees_only_the_table_paragraphs(self):
        answer = {"category": "sleep", "condition_id": "sleep_deficit", "cites": ["hrp:sleep-02#p1"],
                  "lines": ["빛을 받는 시간대가 어긋나면 잠들기 어려울 수 있어요.", "잠들기 전에는 어두운 조명이 도움이 될 수 있어요."]}
        with mock.patch.object(client, "explain", return_value=answer) as explain:
            result = pipeline.adjustment_reason("lighting", "caution", FINDINGS, KO, "ko")
        self.assertEqual(result["reason"], " ".join(answer["lines"]))
        self.assertEqual([p["id"] for p in explain.call_args.args[3]], TABLE["lighting"]["cite_ids"])
        self.assertEqual(explain.call_args.args[2], ["sleep_deficit"])

    def test_model_failure_keeps_the_cites_and_holds_the_reason(self):
        with mock.patch.object(client, "explain", side_effect=client.ModelUnavailableError("connection refused")):
            result = pipeline.adjustment_reason("schedule", "caution", FINDINGS, KO, "ko")
        self.assertEqual((result["reason"], result["hold"], result["verified"]), (None, True, 0))
        self.assertEqual(result["cite_ids"], TABLE["schedule"]["cite_ids"])
        self.assertIn("model unavailable", result["runs"][0]["note"])

    def test_no_evidence_or_unknown_target_holds_without_calling_the_model(self):
        with mock.patch.object(client, "explain") as explain:
            empty = pipeline.adjustment_reason("lighting", "caution", FINDINGS, [], "ko")
            unknown = pipeline.adjustment_reason("air", "caution", FINDINGS, KO, "ko")
        explain.assert_not_called()
        for result, note in ((empty, "no evidence paragraph loaded for lighting"), (unknown, "unknown adjustment target: air")):
            self.assertEqual((result["reason"], result["cite_ids"], result["hold"], result["verified"]), (None, [], True, 0))
            self.assertEqual(result["runs"], [{"n": 1, "ok": False, "fails": [], "note": note}])
            self.assertNotIn("explanation", result)

    def test_malformed_evidence_rows_are_skipped_and_a_non_list_holds_without_raising(self):
        junk = [{"text": "no id"}, {"id": "x:y#p1"}, "not a row", None, {"id": ["unhashable"], "text": "t"}]
        with mock.patch.dict(os.environ, {"MODEL": "mock", "MOCK_DELAY": "0"}):
            mixed = pipeline.adjustment_reason("lighting", "caution", FINDINGS, junk[:4] + KO, "ko")
            self.assertEqual((mixed["hold"], mixed["cite_ids"]), (False, TABLE["lighting"]["cite_ids"]))
            for evidence in (junk[:4], junk, None, 7):
                with self.subTest(evidence=str(evidence)[:40]):
                    result = pipeline.adjustment_reason("lighting", "caution", FINDINGS, evidence, "ko")
                    self.assertEqual((result["reason"], result["cite_ids"], result["hold"]), (None, [], True))
                    self.assertEqual(result["runs"][0]["note"], "no evidence paragraph loaded for lighting")

    def test_missing_or_broken_table_file_holds_without_raising_or_calling_the_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken, not_an_object = Path(tmp) / "broken.json", Path(tmp) / "list.json"
            broken.write_text("{not json", encoding="utf-8")
            not_an_object.write_text("[1, 2]", encoding="utf-8")
            for path, error in ((Path(tmp) / "missing.json", "FileNotFoundError"), (broken, "JSONDecodeError"), (not_an_object, "AttributeError")):
                with self.subTest(file=path.name), mock.patch.object(pipeline, "ADJUSTMENTS", path), mock.patch.object(client, "explain") as explain:
                    result = pipeline.adjustment_reason("lighting", "caution", FINDINGS, KO, "ko")
                    explain.assert_not_called()
                    self.assertEqual(result, {"reason": None, "cite_ids": [], "hold": True, "verified": 0, "runs": [
                        {"n": 1, "ok": False, "fails": [], "note": f"adjustment table unreadable: {error}"}]})


if __name__ == "__main__":
    unittest.main()
