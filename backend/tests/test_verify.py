import unittest
from backend.verify import verify

DOCS = {"hrp:cv-01#p3", "hrp:sm-03#p5"}
FIND = [{"metric": "hr", "value": 92, "baseline": 68, "z": 2.7}]
GOOD = {"category": "cardiovascular", "condition_id": "orthostatic_intolerance",
        "lines": ["어지러움과 심박 상승이 함께 보여 기립성 저혈압 가능성이 있어요."], "cites": ["hrp:cv-01#p3"]}


class Verify(unittest.TestCase):
    def test_good_passes(self):
        r = verify(GOOD, FIND, "caution", DOCS)
        self.assertTrue(r["ok"], r)

    def test_numbers_must_match_findings(self):
        bad = dict(GOOD, lines=["심박이 95까지 올랐어요."])
        self.assertIn("numbers", verify(bad, FIND, "caution", DOCS)["fails"])
        ok = dict(GOOD, lines=["심박 92, 기준 68이에요."])
        self.assertNotIn("numbers", verify(ok, FIND, "caution", DOCS)["fails"])

    def test_missing_or_unknown_cite(self):
        self.assertIn("cites", verify(dict(GOOD, cites=["hrp:nope#p1"]), FIND, "caution", DOCS)["fails"])
        self.assertIn("cites", verify(dict(GOOD, cites=[]), FIND, "caution", DOCS)["fails"])

    def test_level_cannot_exceed_rule(self):
        bad = dict(GOOD, lines=["즉시 응급 조치가 필요해요."])
        self.assertIn("level", verify(bad, FIND, "caution", DOCS)["fails"])
        self.assertNotIn("level", verify(bad, FIND, "warning", DOCS)["fails"])

    def test_wording_bans_certainty_and_foreign_condition(self):
        self.assertIn("wording", verify(dict(GOOD, lines=["기립성 저혈압입니다."]), FIND, "caution", DOCS)["fails"])
        self.assertIn("wording", verify(dict(GOOD, lines=["탈수 가능성이 있어요."]), FIND, "caution", DOCS)["fails"])
        self.assertIn("wording", verify(dict(GOOD, condition_id="made_up"), FIND, "caution", DOCS)["fails"])

    def test_schema(self):
        self.assertIn("schema", verify(dict(GOOD, lines=[]), FIND, "caution", DOCS)["fails"])
        self.assertIn("schema", verify(dict(GOOD, extra=1), FIND, "caution", DOCS)["fails"])
