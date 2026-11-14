import json, unittest
from backend.model import client
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


class Numbers(unittest.TestCase):
    def fails(self, line, findings):
        return verify(dict(GOOD, lines=[line]), findings, "caution", DOCS)["fails"]

    def test_rounding_follows_the_display_precision_of_the_metric(self):
        hr = [{"metric": "hr", "value": 92.6, "baseline": 68, "z": 2.7}]            # hr: 소수 0자리로 표시
        self.assertNotIn("numbers", self.fails("심박이 93까지 올랐어요.", hr))
        self.assertIn("numbers", self.fails("심박이 92까지 올랐어요.", hr))           # 버림은 반올림이 아니다
        self.assertIn("numbers", self.fails("심박이 94까지 올랐어요.", hr))
        temp = [{"metric": "temp", "value": 33.94, "baseline": 33.6, "z": 1.1}]     # temp: 소수 1자리로 표시
        self.assertNotIn("numbers", self.fails("피부온이 33.9도예요.", temp))
        self.assertNotIn("numbers", self.fails("피부온이 33.94도예요.", temp))
        self.assertIn("numbers", self.fails("피부온이 34도예요.", temp))              # 표시 자릿수보다 거칠다
        self.assertIn("numbers", self.fails("피부온이 33.92도예요.", temp))

    def test_z_is_not_rounded_to_a_whole_sigma(self):
        hr = [{"metric": "hr", "value": 92, "baseline": 68, "sd": 3.1, "z": 2.7}]    # sd 가 3 근처여도 통과하면 안 된다
        self.assertIn("numbers", self.fails("기준에서 3σ 벗어났어요.", hr))
        self.assertNotIn("numbers", self.fails("기준에서 2.7σ 벗어났어요.", hr))

    def test_small_integers_are_not_free_passes(self):
        hr = [{"metric": "hr", "value": 92, "baseline": 68, "z": 2.1}]
        for line in ("기준에서 3 정도 벗어났어요.", "심박이 2 올랐어요.", "1시간 뒤 다시 재요."):
            with self.subTest(line=line):
                self.assertIn("numbers", self.fails(line, hr))

    def test_negative_value_may_be_written_with_or_without_sign(self):
        hrv = [{"metric": "hrv", "value": 31, "baseline": 52, "z": -2.5}]
        self.assertNotIn("numbers", self.fails("HRV가 -2.5σ예요.", hrv))
        self.assertNotIn("numbers", self.fails("HRV가 기준보다 2.5σ 낮아요.", hrv))

    def test_an_explicit_sign_must_match_the_finding(self):
        low = [{"metric": "hrv", "value": 31, "baseline": 52, "z": -2.5}]
        for line in ("HRV가 +2.5σ예요.", "z=+2.5 정도예요."):
            with self.subTest(line=line):
                self.assertIn("numbers", self.fails(line, low))
        for line in ("HRV가 -2.5σ예요.", "HRV가 \u22122.5σ예요.", "z=-2.5 정도예요.", "HRV가 기준보다 2.5σ 낮아요."):
            with self.subTest(line=line):
                self.assertNotIn("numbers", self.fails(line, low))
        high = [{"metric": "hr", "value": 92, "baseline": 68, "z": 2.7}]
        self.assertIn("numbers", self.fails("심박이 -2.7σ예요.", high))
        self.assertNotIn("numbers", self.fails("심박이 +2.7σ예요.", high))

    def test_a_hyphen_between_two_numbers_is_a_range_not_a_sign(self):
        hr = [{"metric": "hr", "value": 92, "baseline": 68, "z": 2.7}]
        self.assertNotIn("numbers", self.fails("심박이 68-92 사이였어요.", hr))

    def test_cite_ids_and_unit_names_are_not_numbers(self):
        self.assertNotIn("numbers", self.fails("CO2 영향 가능성이 있어요 (hrp:cv-01#p3).", FIND))

    def test_mock_explanations_pass_the_verifier(self):
        for row in json.loads((client.MOCK_DIR / "explanation.json").read_text(encoding="utf-8")):
            out = row["out"]
            with self.subTest(condition=out["condition_id"]):
                self.assertEqual(verify(out, [], "caution", set(out["cites"]))["fails"], [])

    def test_detail_says_what_each_check_caught(self):
        # 재생성 때 모델에게 '무엇이' 걸렸는지 알려 주고, 화면의 폐기 이유(runs[].note)에도 쓴다.
        self.assertEqual(verify(GOOD, FIND, "caution", DOCS)["detail"], {})
        self.assertEqual(verify(GOOD, FIND, "caution", DOCS)["note"], "")
        r = verify(dict(GOOD, lines=["12시 전에 물을 마시는 게 좋아요."]), FIND, "caution", DOCS)
        self.assertEqual((r["fails"], r["detail"]), (["numbers"], {"numbers": ["12"]}))
        self.assertEqual(r["note"], "numbers: 12")
        r = verify(dict(GOOD, lines=["주의가 필요한 작업은 미루는 게 좋아요."]), FIND, "advisory", DOCS)
        self.assertEqual(r["detail"], {"level": ["주의"]})
        r = verify(dict(GOOD, lines=["수면 부족은 흔한 현상입니다."]), FIND, "caution", DOCS)     # 단정 + 다른 상태 이름
        self.assertEqual(r["detail"], {"wording": ["입니다", "수면 부족"]})
        r = verify(dict(GOOD, cites=["hrp:nope#p1"]), FIND, "caution", DOCS)
        self.assertEqual(r["detail"], {"cites": ["hrp:nope#p1"]})
        r = verify(dict(GOOD, lines="not a list"), FIND, "caution", DOCS)
        self.assertIn("schema", r["detail"])
