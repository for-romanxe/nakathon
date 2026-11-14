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


class AssertiveEndings(unittest.TestCase):
    """단정은 "~입니다"만이 아니다. 말투를 해요체로 바꾼 뒤(11/14)로는 "~이에요/~예요"가 같은 자리에 온다."""

    def fails(self, lines):
        return verify(dict(GOOD, lines=lines), FIND, "caution", DOCS)["fails"]

    def test_the_polite_informal_copula_is_an_assertion_too(self):
        self.assertIn("wording", self.fails(["기립성 저혈압이에요."]))
        self.assertIn("wording", self.fails(["지금 상태는 수분 부족이에요, 물을 마셔 보세요."]))
        self.assertIn("wording", self.fails(["오래 앉아 있었기 때문이에요."]))
        self.assertIn("wording", self.fails(["흔한 문제예요."]))

    def test_ipnida_followed_by_man_is_still_an_assertion(self):
        self.assertIn("wording", self.fails(["기립성 저혈압입니다만 쉬면 나아져요."]))
        self.assertEqual(self.fails(["자세를 바꿀 때는 천천히 움직입니다만 무리하지는 마세요."]), [])      # 동사는 그대로 통과

    def test_hedged_sentences_still_pass(self):
        self.assertEqual(self.fails(["기립성 저혈압일 수 있어요."]), [])
        self.assertEqual(self.fails(["수분이 부족할 가능성이 있어요.", "물을 자주 마시는 게 좋아요."]), [])
        self.assertEqual(self.fails(["증상이 계속되면 알려 주세요."]), [])
        self.assertEqual(self.fails(["어지러움이 심하지 않은지 살펴보세요."]), [])


class FalsePositives(unittest.TestCase):
    """평가 30문항과 연습 12문항에서 실제로 나온 오탐. 고친 뒤에도 진짜 위반은 그대로 잡혀야 한다."""

    def fails(self, lines, level="caution", **kw):
        return verify(dict(GOOD, lines=lines), FIND, level, DOCS, **kw)["fails"]

    def test_verbs_ending_in_ipnida_are_not_the_copula(self):
        # "움직입니다"는 동사(움직이다)다. "~입니다"로 단정하는 문장만 막는다.
        self.assertEqual(self.fails(["자세를 바꿀 때는 지지대를 잡고 천천히 움직입니다."]), [])
        self.assertEqual(self.fails(["쉬는 동안에는 운동 강도를 줄입니다."]), [])
        self.assertIn("wording", self.fails(["기립성 저혈압입니다."]))
        self.assertIn("wording", self.fails(["흔한 증상입니다. 천천히 움직입니다."]))      # 동사가 섞여 있어도 단정은 잡는다
        self.assertIn("wording", self.fails(["기립성 저혈압으로 보입니다."]))              # 목록에 없는 말은 그대로 막는다
        r = verify(dict(GOOD, lines=["기립성 저혈압입니다."]), FIND, "caution", DOCS)
        self.assertEqual(r["detail"], {"wording": ["입니다"]})                           # 알려 주는 표현은 그대로

    def test_attentiveness_is_not_a_caution_word(self):
        # "주의력"·"alertness"는 주의 단계를 뜻하는 말이 아니다.
        self.assertEqual(self.fails(["잠이 부족하면 다음 날 주의력이 떨어질 가능성이 있어요."], "advisory"), [])
        self.assertEqual(self.fails(["Short sleep may lower your alertness the next day."], "advisory"), [])
        self.assertIn("level", self.fails(["주의가 필요해요."], "advisory"))
        self.assertIn("level", self.fails(["주의력이 떨어지니 주의하세요."], "advisory"))
        self.assertIn("level", self.fails(["Stay alert and rest."], "advisory"))
        self.assertIn("level", self.fails(["This is an alert."], "advisory"))

    def test_a_possibility_of_an_infection_is_not_a_diagnosis(self):
        self.assertEqual(self.fails(["There is a possibility of an infection after close contact."]), [])
        self.assertEqual(self.fails(["There is a chance of a stroke-like symptom, so rest."]), [])
        self.assertIn("wording", self.fails(["This is a heart attack."]))
        self.assertIn("wording", self.fails(["It is a serious infection."]))

    def test_another_candidate_may_be_named_but_not_a_condition_outside_the_candidates(self):
        # 규칙 엔진이 후보로 넘긴 상태는 문장에 나와도 된다. 후보 밖 상태 이름은 그대로 막는다.
        line = ["어지러움이 이어지면 탈수 가능성도 함께 살펴보는 게 좋아요."]
        self.assertIn("wording", self.fails(line))                                                      # 후보를 모르면 예전처럼 막는다
        self.assertEqual(self.fails(line, candidates=["orthostatic_intolerance", "dehydration"]), [])
        self.assertIn("wording", self.fails(line, candidates=["orthostatic_intolerance", "sleep_deficit"]))
        self.assertIn("wording", self.fails(["Dehydration is possible too."], candidates=["orthostatic_intolerance"]))


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
