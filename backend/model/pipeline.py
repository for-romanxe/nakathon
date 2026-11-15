"""설명 생성 → 검증 → 재생성 루프 (명세 §11·§12). 백엔드는 설명이 필요할 때 이 함수 하나만 부른다."""
import json, pathlib

from backend import contracts, verify
from backend.model import client

MAX_RUNS = 2      # 명세 §12: 루프 상한 2회. 두 번 실패하면 판단 보류
ADJUSTMENTS = pathlib.Path(__file__).resolve().parent / "adjustment_evidence.json"
PROCEDURES = pathlib.Path(__file__).resolve().parent / "procedure_steps.json"


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
            result = verify.verify(out, findings, level, [p["id"] for p in paragraphs], lang, candidates=condition_candidates)
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


def adjustment_reason(target: str, level: str, findings: list, evidence: list, lang: str) -> dict:
    """우주선 조정(조명·일정) 한 건에 붙일 이유 (이슈 #47). 조정할지와 전후 값은 규칙이 정한다. 여기서는 이유 문장만 만든다.

    target 은 adjustment_evidence.json 의 키(lighting, schedule). evidence 는 event_flow.load_evidence() 가 읽은 근거 목록.
    반환: {"reason": str | None, "cite_ids": [문단 id], "hold": bool, "verified": 0~5, "runs": [...]}
    - cite_ids 는 표가 정한 문단 가운데 근거 파일에 있는 것이다. 모델이 정하지 않으므로 모델을 부르기 전에도, 실패한 뒤에도 같다.
    - reason 은 검증을 통과한 설명 문장(1~2개)을 이은 것. 통과하지 못했거나 모델을 못 불렀으면 None 이고 hold 가 True 다.
      그때 화면에는 규칙이 쓴 수치 문장과 cite_ids 만 보여 준다. 조정 자체는 이유가 없어도 적용된다.
    - 예외를 던지지 않는다. 모르는 target 이거나 근거 문단이 하나도 없으면 모델을 부르지 않고 보류로 끝낸다.
    """
    entry = json.loads(ADJUSTMENTS.read_text(encoding="utf-8")).get(target)
    rows = {row["id"]: row for row in evidence}
    paragraphs = [{"id": i, "text": rows[i]["text"]} for i in (entry["cite_ids"] if isinstance(entry, dict) else []) if i in rows]
    cite_ids = [p["id"] for p in paragraphs]
    if not paragraphs:
        note = f"unknown adjustment target: {target}" if not isinstance(entry, dict) else f"no evidence paragraph loaded for {target}"
        return {"reason": None, "cite_ids": [], "hold": True, "verified": 0, "runs": _stopped([], 1, note)["runs"]}
    result = explain_verified(level, findings, [entry["condition_id"]], paragraphs, lang)
    reason = " ".join(result["explanation"]["lines"]) if result["explanation"] else None
    return {"reason": reason, "cite_ids": cite_ids, "hold": result["hold"], "verified": result["verified"], "runs": result["runs"]}


def procedure_steps(condition_id: str, evidence: list, lang: str) -> dict:
    """경보 때 보여 줄 절차 단계 (이슈 #47). 모델을 부르지 않는다. 단계와 근거 문단은 procedure_steps.json 에 고정돼 있다.

    반환: {"available": bool, "steps": [{"step_id", "text", "cite_id", "kind"}]}  (kind 의 뜻은 procedure_steps.json 의 _doc)
    이 상태의 절차가 없거나 단계가 가리키는 문단이 근거 파일에 하나라도 없으면 available 은 False 이고 steps 는 비어 있다.
    출처를 열 수 없는 단계는 보여 주지 않는다. 그때 화면은 경보와 의무관 호출만 보여 준다.
    """
    entry = json.loads(PROCEDURES.read_text(encoding="utf-8")).get(condition_id)
    loaded = {row["id"] for row in evidence}
    if not isinstance(entry, dict) or not all(step["cite_id"] in loaded for step in entry["steps"]):
        return {"available": False, "steps": []}
    return {"available": True, "steps": [{"step_id": step["step_id"], "text": step["ko" if lang == "ko" else "en"],
                                          "cite_id": step["cite_id"], "kind": step["kind"]} for step in entry["steps"]]}
