"""설명(Explanation) 검증기 (CONTRACT §4, 명세 §12). 검사 5개, 이름 고정: numbers, cites, level, schema, wording.

verify(expl, findings, level, doc_ids, lang) -> {"ok": bool, "fails": [검사 이름...], "note": str, "detail": {검사 이름: [걸린 표현...]}}
파이프라인은 실패 시 최대 2회 재생성, 그래도 실패면 level=hold 로 '판단 보류'.
"""
import math, re
from . import contracts

# 문장 강도가 판정을 넘는지: 해당 level 미만에서 쓰면 안 되는 표현
LEVEL_RANK = {"normal": 0, "advisory": 1, "caution": 2, "warning": 3, "hold": 0}
STRONG = {
    "warning": [r"즉시", r"응급", r"긴급", r"지금 바로", r"emergenc", r"immediately", r"urgent", r"call .*cmo now"],
    "caution": [r"주의", r"경고", r"caution", r"warning", r"alert"],
}
# 단정·진단 표현 금지 (ko/en 두 벌). "가능성/possible" 류만 허용.
BANNED = [r"확실", r"틀림없", r"진단", r"분명히", r"입니다\b", r"\bcertain", r"definitely", r"diagnos", r"\bis a\b .*(infection|attack|stroke)"]
# 숫자 토큰 = (부호, 숫자). CO2·SpO2 처럼 글자에 붙은 숫자는 수치가 아니다.
# 부호는 숫자 바로 앞에 있고 그 앞이 글자·숫자가 아닐 때만 부호다: "z=-2.5" 는 부호, "68-92" 는 범위.
NUM = re.compile(r"(?:(?<![\w.])([+\-\u2212]))?(?<![A-Za-z_.\d])(\d+(?:\.\d+)?)")
CITE = re.compile(r"[a-z]+:[a-z0-9-]+#p\d+")             # 출처 id 안의 숫자도 수치가 아니다
Z_DECIMALS = 1                                            # 화면이 z 를 소수 1자리로 보여준다


def _references(findings):
    """findings 의 value·baseline·z 에서 (부호 있는 값, 화면 표시 소수 자릿수) 를 모은다. 자릿수는 contracts/enums.json 의
    metrics[].decimals. sd 는 넣지 않는다: 2~3 같은 작은 값이라 넣으면 '3σ' 같은 틀린 문장이 우연히 통과한다."""
    metrics = contracts.enums()["metrics"]
    refs = []
    for f in findings or []:
        shown = metrics.get(f.get("metric"), {}).get("decimals", 0)
        for key, decimals in (("value", shown), ("baseline", shown), ("z", Z_DECIMALS)):
            v = f.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
                refs.append((v, decimals))
    return refs


def _bad_numbers(lines, findings):
    """문장 속 숫자는 findings 값을 '그 숫자가 적힌 자릿수'로 반올림한 것이어야 하고,
    그 지표의 화면 표시 자릿수보다 거칠게 적으면 안 된다 (z=2.7 을 3 으로 쓰면 실패).
    부호를 적었으면 부호도 맞아야 한다 (z=-2.5 를 +2.5 로 쓰면 실패). 부호 없이 적은 숫자는 크기만 본다:
    "기준보다 2.5σ 낮아요" 처럼 방향을 말로 쓰는 문장이 있기 때문이다. 걸린 숫자를 돌려준다."""
    refs = _references(findings)
    bad = []
    for line in lines:
        for sign, number in NUM.findall(CITE.sub(" ", line)):
            written = len(number.partition(".")[2])
            x = float(number)
            negative = None if not sign else sign != "+"
            if not any(written >= decimals and abs(x - abs(v)) <= 0.5 * 10 ** -written + 1e-9
                       and (negative is None or v == 0 or negative == (v < 0)) for v, decimals in refs):
                bad.append(sign + number)
    return bad


def _bad_cites(cites, doc_ids):
    return [str(c) for c in cites if c not in doc_ids] if cites else ["no cite"]


def _too_strong(lines, level):
    rank = LEVEL_RANK.get(level, 0)
    text = " ".join(lines).lower()
    return [m.group(0) for lv, pats in STRONG.items() if rank < LEVEL_RANK[lv] for p in pats if (m := re.search(p, text))]


def _bad_wording(expl, lines):
    text = " ".join(lines).lower()
    bad = [m.group(0) for p in BANNED if (m := re.search(p, text))]
    conds = {k: v for k, v in contracts.enums()["conditions"].items() if isinstance(v, dict)}
    if expl.get("condition_id") not in conds:
        return bad + [f"condition_id {expl.get('condition_id')!r}"]
    # 목록 밖 상태 이름: 다른 condition 의 표시명이 문장에 나오면 안 됨
    for cid, c in conds.items():
        if cid in ("none", expl.get("condition_id")):
            continue
        bad += [name for name in (c.get("ko"), c.get("en")) if name and name.lower() in text]
    return bad


def verify(expl: dict, findings: list, level: str, doc_ids, lang: str = "ko") -> dict:
    doc_ids = set(doc_ids or [])
    lines = [str(x) for x in (expl.get("lines") or [])]
    caught = {
        "schema": contracts.check_schema(expl, contracts.schema("explanation")),
        "numbers": _bad_numbers(lines, findings),
        "cites": _bad_cites(expl.get("cites") or [], doc_ids),
        "level": _too_strong(lines, level),
        "wording": _bad_wording(expl, lines),
    }
    fails = [check for check in contracts.enums()["verify_check"] if caught[check]]
    detail = {check: caught[check] for check in fails}      # 검사 이름 → 걸린 표현들
    note = "; ".join(f"{check}: {', '.join(found)}" for check, found in detail.items())[:200]
    return {"ok": not fails, "fails": fails, "note": note, "detail": detail}
