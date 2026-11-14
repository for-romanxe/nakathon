"""설명 생성 → 검증 → 재생성 루프 (명세 §11·§12). 백엔드는 설명이 필요할 때 이 함수 하나만 부른다."""
from backend import contracts, verify
from backend.model import client

MAX_RUNS = 2      # 명세 §12: 루프 상한 2회. 두 번 실패하면 판단 보류


def explain_verified(level: str, findings: list, condition_candidates: list, paragraphs: list, lang: str) -> dict:
    """검증을 통과한 설명만 돌려준다.

    반환: {"explanation": Explanation | None, "hold": bool, "verified": 0~5, "runs": [{"n", "ok", "fails", "note"}]}
    - explanation 이 None 이면 hold 가 True 다. 화면에는 수치와 절차서만 보여 준다.
    - runs 는 이벤트의 runs[] 에 그대로 넣는다. fails 는 검증기 검사 이름(numbers, cites, level, schema, wording).
    - verified 는 마지막 실행에서 통과한 검사 수. 모델 출력을 쓸 수 없어 검사를 못 돌렸으면 0.
    - 예외를 던지지 않는다. 모델 서버에 닿지 못하거나 입력이 잘못됐으면(목록 밖 상태 후보, id 없는 문단 등)
      검사 없이 끝난 실행의 note 에 이유를 적고 보류로 끝낸다.
    """
    checks = len(contracts.enums()["verify_check"])
    runs, rejected, passed = [], {}, 0
    for n in range(1, MAX_RUNS + 1):
        try:
            out = client.explain(level, findings, condition_candidates, paragraphs, lang, rejected=rejected)
            result = verify.verify(out, findings, level, [p["id"] for p in paragraphs], lang)
            passed = checks - len(result["fails"])
        except client.ModelUnavailableError as error:      # 서버에 닿지 못하면 다시 불러도 같다
            return _stopped(runs, n, f"model unavailable: {error}")
        except client.ModelOutputError as error:           # 스키마에 안 맞는 출력
            result = {"ok": False, "fails": ["schema"], "note": str(error)[:200], "detail": {"schema": [str(error)[:200]]}}
            out, passed = None, 0
        except Exception as error:                         # 호출 쪽이 잘못 넘긴 입력(목록 밖 후보, id 없는 문단 등). 다시 불러도 같다
            return _stopped(runs, n, f"{type(error).__name__}: {error}")
        runs.append({"n": n, "ok": result["ok"], "fails": result["fails"], "note": result["note"]})
        if result["ok"]:
            return {"explanation": out, "hold": False, "verified": passed, "runs": runs}
        rejected = result["detail"]      # 다음 실행에 무엇이 걸렸는지 알려 준다
    return {"explanation": None, "hold": True, "verified": passed, "runs": runs}


def _stopped(runs: list, n: int, note: str) -> dict:
    """검사를 돌리지 못하고 끝난 경우: 이유를 적고 보류."""
    runs.append({"n": n, "ok": False, "fails": [], "note": note[:200]})
    return {"explanation": None, "hold": True, "verified": 0, "runs": runs}
