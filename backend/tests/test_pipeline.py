"""설명 생성 → 검증 → 재생성 루프(명세 §11·§12). 모델 호출은 가짜로 바꿔 루프만 본다."""
import unittest
from unittest import mock

from backend.model import client, pipeline

FINDINGS = [{"metric": "hr", "value": 82, "baseline": 68, "sd": 5.6, "z": 2.5}]
PARAS = [{"id": "eval:fluids#p1", "text": "Drink fluids."}]
GOOD = {"category": "nutrition", "condition_id": "dehydration", "lines": ["수분 부족 가능성이 있어요."], "cites": ["eval:fluids#p1"]}
ASSERTIVE = {**GOOD, "lines": ["탈수입니다."]}                   # wording 실패
WITH_TIME = {**GOOD, "lines": ["12시 전에 물을 마시는 게 좋아요."]}   # numbers 실패


def run(*replies):
    """client.explain 이 차례로 replies 를 돌려주거나(예외면 던지고) 하게 한 뒤 파이프라인을 돈다."""
    with mock.patch.object(client, "explain", side_effect=list(replies)) as explain:
        result = pipeline.explain_verified("caution", FINDINGS, ["dehydration"], PARAS, "ko")
    return result, [call.kwargs.get("rejected") for call in explain.call_args_list]


class RetryLoop(unittest.TestCase):
    def test_first_run_passes(self):
        result, rejected = run(GOOD)
        self.assertEqual(result, {"explanation": GOOD, "hold": False, "verified": 5,
                                  "runs": [{"n": 1, "ok": True, "fails": [], "note": ""}]})
        self.assertEqual(rejected, [{}])

    def test_second_run_is_told_what_failed(self):
        result, rejected = run(ASSERTIVE, GOOD)
        self.assertEqual(result["explanation"], GOOD)
        self.assertFalse(result["hold"])
        self.assertEqual([(r["n"], r["ok"], r["fails"]) for r in result["runs"]], [(1, False, ["wording"]), (2, True, [])])
        self.assertEqual(rejected, [{}, {"wording": ["입니다"]}])      # 걸린 표현까지 넘긴다

    def test_two_failures_end_in_hold_without_an_explanation(self):
        result, rejected = run(ASSERTIVE, WITH_TIME)
        self.assertIsNone(result["explanation"])
        self.assertTrue(result["hold"])
        self.assertEqual([r["fails"] for r in result["runs"]], [["wording"], ["numbers"]])
        self.assertEqual(result["verified"], 4)          # 마지막 실행에서 5검사 중 4개 통과
        self.assertEqual(len(rejected), 2)               # 상한 2회 (명세 §12)

    def test_unusable_output_counts_as_a_schema_failure(self):
        result, rejected = run(client.ModelOutputError("explanation: lines: not an array"), GOOD)
        self.assertEqual(result["runs"][0], {"n": 1, "ok": False, "fails": ["schema"], "note": "explanation: lines: not an array"})
        self.assertEqual(rejected, [{}, {"schema": ["explanation: lines: not an array"]}])
        self.assertEqual(result["explanation"], GOOD)
        result, _ = run(client.ModelOutputError("bad"), client.ModelOutputError("bad again"))
        self.assertEqual((result["hold"], result["verified"]), (True, 0))    # 검사를 돌리지 못했으니 통과 0

    def test_unreachable_model_holds_at_once(self):
        result, rejected = run(client.ModelUnavailableError("model server http://127.0.0.1:8080: timed out"), GOOD)
        self.assertEqual(len(rejected), 1)               # 서버가 없는데 다시 부르지 않는다
        self.assertEqual((result["explanation"], result["hold"], result["verified"]), (None, True, 0))
        self.assertEqual(result["runs"][0]["fails"], [])
        self.assertIn("model unavailable", result["runs"][0]["note"])

    def test_unknown_candidate_holds_instead_of_raising(self):
        # 목록 밖 상태 후보는 호출 쪽 실수지만, 이벤트 처리 전체가 죽지 않게 이유를 적고 보류로 끝낸다.
        with mock.patch.object(client, "_chat") as chat:
            result = pipeline.explain_verified("caution", FINDINGS, ["made_up"], PARAS, "ko")
        chat.assert_not_called()
        self.assertEqual((result["explanation"], result["hold"], result["verified"]), (None, True, 0))
        self.assertEqual(len(result["runs"]), 1)         # 다시 불러도 같으니 한 번만
        self.assertEqual(result["runs"][0]["fails"], [])
        self.assertIn("unknown condition candidates ['made_up']", result["runs"][0]["note"])

    def test_the_other_candidate_may_be_named(self):
        # 후보가 둘일 때 고르지 않은 쪽 이름("수면 부족")을 썼다고 폐기하지 않는다. 후보 밖 이름은 폐기한다.
        named = {"category": "behavioral", "condition_id": "mood_low", "cites": ["eval:fluids#p1"],
                 "lines": ["수면 부족과 함께 기분이 가라앉을 가능성이 있어요."]}
        with mock.patch.object(client, "explain", side_effect=[named]):
            result = pipeline.explain_verified("caution", FINDINGS, ["mood_low", "sleep_deficit"], PARAS, "ko")
        self.assertEqual((result["hold"], result["runs"][0]["fails"]), (False, []))
        with mock.patch.object(client, "explain", side_effect=[named, named]):
            result = pipeline.explain_verified("caution", FINDINGS, ["mood_low", "dehydration"], PARAS, "ko")
        self.assertEqual((result["hold"], result["runs"][0]["fails"]), (True, ["wording"]))

    def test_malformed_input_holds_instead_of_raising(self):
        # 호출 쪽이 문단·후보·findings 를 잘못 넘겨도 이벤트 처리가 죽지 않는다. 이유는 runs[0].note 에 남는다.
        cases = {
            "paragraph without id": dict(paragraphs=[{"text": "no id"}]),
            "paragraph without text": dict(paragraphs=[{"id": "eval:a#p1"}]),
            "unhashable candidate": dict(candidates=[["x"]]),
            "findings not serialisable": dict(findings=[{"metric": "hr", "value": {1, 2}}]),
            "paragraphs is None": dict(paragraphs=None),
        }
        for name, change in cases.items():
            args = {"findings": FINDINGS, "candidates": ["dehydration"], "paragraphs": PARAS, **change}
            with self.subTest(name), mock.patch.dict("os.environ", {"MODEL": "live"}), \
                    mock.patch.object(client, "_chat", return_value=dict(GOOD, cites=[1])):
                result = pipeline.explain_verified("caution", args["findings"], args["candidates"], args["paragraphs"], "ko")
                self.assertEqual((result["explanation"], result["hold"], result["verified"]), (None, True, 0))
                self.assertEqual(len(result["runs"]), 1)
                self.assertRegex(result["runs"][0]["note"], r"^(KeyError|TypeError|ValueError)")


if __name__ == "__main__":
    unittest.main()
