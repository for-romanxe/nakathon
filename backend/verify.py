"""설명(Explanation) 검증기 (CONTRACT §4, 명세 §12). 검사 5개, 이름 고정: numbers, cites, level, schema, wording.

verify(expl, findings, level, doc_ids, lang) -> {"ok": bool, "fails": [검사 이름...], "note": str}
파이프라인은 실패 시 최대 2회 재생성, 그래도 실패면 level=hold 로 '판단 보류'.
"""
import re
from . import contracts

# 문장 강도가 판정을 넘는지: 해당 level 미만에서 쓰면 안 되는 표현
LEVEL_RANK = {"normal": 0, "advisory": 1, "caution": 2, "warning": 3, "hold": 0}
STRONG = {
    "warning": [r"즉시", r"응급", r"긴급", r"지금 바로", r"emergenc", r"immediately", r"urgent", r"call .*cmo now"],
    "caution": [r"주의", r"경고", r"caution", r"warning", r"alert"],
}
# 단정·진단 표현 금지 (ko/en 두 벌). "가능성/possible" 류만 허용.
BANNED = [r"확실", r"틀림없", r"진단", r"분명히", r"입니다\b", r"\bcertain", r"definitely", r"diagnos", r"\bis a\b .*(infection|attack|stroke)"]
NUM = re.compile(r"(?<![a-zA-Z_:#\-])\d+(?:\.\d+)?")


def _numbers_ok(lines, findings):
    """문장 속 숫자는 findings 의 value/baseline/z (소수 1자리 반올림 포함) 중 하나여야 한다."""
    allowed = set()
    for f in findings or []:
        for k in ("value", "baseline", "z", "sd"):
            v = f.get(k)
            if isinstance(v, (int, float)):
                allowed |= {f"{v:g}", f"{round(v, 1):g}", f"{round(v):d}"}
    for ln in lines:
        for n in NUM.findall(ln):
            if n not in allowed and n not in {"1", "2", "3"}:  # 순서 번호 정도는 허용
                return False
    return True


def _cites_ok(cites, doc_ids):
    return bool(cites) and all(c in doc_ids for c in cites)


def _level_ok(lines, level):
    rank = LEVEL_RANK.get(level, 0)
    text = " ".join(lines).lower()
    for lv, pats in STRONG.items():
        if rank < LEVEL_RANK[lv] and any(re.search(p, text) for p in pats):
            return False
    return True


def _wording_ok(expl, lines):
    text = " ".join(lines).lower()
    if any(re.search(p, text) for p in BANNED):
        return False
    conds = {k: v for k, v in contracts.enums()["conditions"].items() if isinstance(v, dict)}
    if expl.get("condition_id") not in conds:
        return False
    # 목록 밖 상태 이름: 다른 condition 의 표시명이 문장에 나오면 안 됨
    for cid, c in conds.items():
        if cid in ("none", expl.get("condition_id")):
            continue
        for name in (c.get("ko"), c.get("en")):
            if name and name.lower() in text:
                return False
    return True


def verify(expl: dict, findings: list, level: str, doc_ids, lang: str = "ko") -> dict:
    doc_ids = set(doc_ids or [])
    fails = []
    schema_fails = contracts.check_schema(expl, contracts.schema("explanation"))
    if schema_fails:
        fails.append("schema")
    lines = [str(x) for x in (expl.get("lines") or [])]
    if not _numbers_ok(lines, findings):
        fails.append("numbers")
    if not _cites_ok(expl.get("cites") or [], doc_ids):
        fails.append("cites")
    if not _level_ok(lines, level):
        fails.append("level")
    if not _wording_ok(expl, lines):
        fails.append("wording")
    order = contracts.enums()["verify_check"]
    fails.sort(key=order.index)
    return {"ok": not fails, "fails": fails, "note": "; ".join(schema_fails)[:200]}
