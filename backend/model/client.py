"""모델 호출 단일 진입점 (CONTRACT §4). 함수 3개만 외부에 노출한다.

MODEL=mock (기본)  : backend/mock/*.json 시나리오를 MOCK_DELAY초 지연으로 돌려준다.
MODEL=live         : MODEL_URL 의 OpenAI 호환 /v1/chat/completions 를 호출한다 (mlx_lm.server 등).
어느 모드든 출력은 contracts 스키마 검사를 통과해야 하고, 실패하면 ModelOutputError.
모델 서버에 닿지 못한 경우는 그 하위 클래스 ModelUnavailableError. 호출 측은 ModelOutputError 하나만 잡아도 된다.
판정·경보는 여기서 하지 않는다. 규칙 엔진이 한다.
"""
import http.client, json, os, re, time, urllib.request, pathlib
from .. import contracts

MOCK_DIR = pathlib.Path(__file__).resolve().parent.parent / "mock"


class ModelOutputError(Exception):
    """모델 출력을 쓸 수 없다: JSON 없음, 스키마 위반, 후보 밖 상태. 파이프라인은 재생성하거나 '판단 보류'로 간다."""


class ModelUnavailableError(ModelOutputError):
    """모델 서버에 닿지 못했거나 응답 봉투가 깨졌다. 재생성해도 소용없는 실패를 구분하고 싶을 때 잡는다."""


def _mode():
    return os.environ.get("MODEL", "mock")


def _delay():
    time.sleep(float(os.environ.get("MOCK_DELAY", "1")))


def _clean_keys(pairs: list) -> dict:
    """키 이름 안의 공백을 지운다("worse_ when" → "worse_when"). 그 결과 같은 키가 둘이 되면
    ("codes" 와 "co des") 어느 값이 맞는지 알 수 없으니 덮어쓰지 않고 거부한다."""
    out = {}
    for key, value in pairs:
        key = "".join(key.split())
        if key in out:
            raise ModelOutputError(f"model output has the same key twice: {key!r}")
        out[key] = value
    return out


def _first_json_object(text: str) -> dict:
    """모델 답에서 첫 번째 온전한 JSON 객체를 꺼낸다. 앞뒤 설명, 코드 펜스, 뒤따르는 두 번째 객체는 무시한다."""
    decoder = json.JSONDecoder(object_pairs_hook=_clean_keys)
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            return obj
        start = text.find("{", start + 1)
    raise ModelOutputError("no JSON object in model output")


def _chat(system: str, user: str, max_tokens=160) -> dict:
    """live 모드: OpenAI 호환 서버를 호출하고 답의 첫 JSON 객체를 돌려준다."""
    root = os.environ.get("MODEL_URL", "http://127.0.0.1:8080").rstrip("/").removesuffix("/v1")
    url = root + "/v1/chat/completions"
    # "default_model" 은 mlx_lm.server 가 '서버를 띄울 때 준 모델(+어댑터)'로 읽는 이름이다.
    body = {"model": os.environ.get("MODEL_NAME", "default_model"), "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("MODEL_TIMEOUT", "60"))) as r:
            text = json.load(r)["choices"][0]["message"]["content"]
    except (OSError, http.client.HTTPException, ValueError, LookupError, TypeError) as e:
        # 연결 거부·시간 초과·HTTP 오류(OSError), 본문이 JSON 이 아님(ValueError), choices/message 없음(LookupError, TypeError)
        raise ModelUnavailableError(f"model server {url}: {type(e).__name__}: {e}") from e
    if not isinstance(text, str):
        raise ModelUnavailableError(f"model server {url}: reply has no text content")
    return _first_json_object(text)


def _validated(obj, kind):
    fails = contracts.check_schema(obj, contracts.schema(kind))
    if fails:
        raise ModelOutputError(f"{kind}: " + "; ".join(fails))
    return obj


def _mock_rows(kind: str) -> list:
    return json.loads((MOCK_DIR / f"{kind}.json").read_text(encoding="utf-8"))


def _keyword_hit(keyword: str, low: str) -> bool:
    """영문 키워드는 단어의 시작에서만 맞춘다: 'sleep'은 'asleep'에 걸리지 않고 'nause'는 'nauseous'에 걸린다.
    한글은 띄어쓰기로 단어가 갈리지 않으므로 부분 문자열로 찾되, 키워드 자체를 구체적으로 적는다."""
    k = keyword.lower()
    if k.isascii():
        return re.search(r"(?<![a-z])" + re.escape(k), low) is not None
    return k in low


def _mock_pick(kind: str, text: str) -> dict:
    """mock/<kind>.json: [{match:[키워드...], out:{...}}, ...]. 행 순서가 우선순위(급한 코드가 위), 없으면 마지막(default)."""
    rows = _mock_rows(kind)
    low = text.lower()
    for row in rows:
        if any(_keyword_hit(k, low) for k in row.get("match", [])):
            return row["out"]
    return rows[-1]["out"]


def _mock_explanation(candidates: list, paragraphs: list, lang: str) -> dict:
    """후보 순서대로 시나리오를 찾는다. 시나리오가 없는 후보는 그 후보에 맞는 일반 문장을 만든다. 후보가 없으면 none."""
    by_condition = {row["out"]["condition_id"]: row["out"] for row in _mock_rows("explanation")}
    if not candidates:
        return by_condition["none"]
    for condition_id in candidates:
        if condition_id in by_condition:
            return by_condition[condition_id]
    condition_id = candidates[0]
    condition = _conditions()[condition_id]
    line = (f"{condition['ko']} 가능성을 지켜볼 필요가 있어요." if lang == "ko"
            else f"{condition['en']} is a possibility; keep watching it.")
    cites = [p["id"] for p in paragraphs[:1]] or by_condition["none"]["cites"]
    return {"category": condition["hrp"], "condition_id": condition_id, "lines": [line], "cites": cites}


def _conditions() -> dict:
    return {k: v for k, v in contracts.enums()["conditions"].items() if isinstance(v, dict)}


def _among_candidates(out: dict, candidates: list) -> dict:
    """상태 이름은 규칙 엔진이 준 후보 안에서만 고를 수 있다. 후보가 없으면 none만."""
    allowed = candidates or ["none"]
    if out["condition_id"] not in allowed:
        raise ModelOutputError(f"explanation: condition_id {out['condition_id']!r} is not among the candidates {allowed}")
    out["category"] = _conditions()[out["condition_id"]]["hrp"]     # 범주는 상태 목록이 정한다. 모델이 쓴 값은 쓰지 않는다.
    return out


# ---- 공개 함수 3개 -------------------------------------------------------

def _cite_id(cite, paragraphs: list):
    """문단 번호(1부터, 정수나 숫자 문자열) → 문단 id. 범위 밖이거나 다른 값이면 그대로 두어 스키마 검사에서 걸리게 한다."""
    number = cite
    if isinstance(cite, str) and cite.isdigit():
        try:
            number = int(cite)
        except ValueError:      # "²", "①" 처럼 isdigit() 은 참이지만 정수로 못 바꾸는 글자
            return cite
    if isinstance(number, int) and not isinstance(number, bool) and 1 <= number <= len(paragraphs):
        return paragraphs[number - 1]["id"]
    return cite


def extract_symptoms(text: str, lang: str, recent_summary: str = "") -> dict:
    """① 증상 문장 → SymptomReport (codes[], onset, worse_when, severity, needs_question)."""
    if _mode() == "mock":
        _delay()
        return _validated(_mock_pick("symptom", text), "symptom")
    e = contracts.enums()
    system = ("You extract symptom codes from a crew member's free-text report. Answer with JSON only. "
              f"codes: array from {json.dumps(e['symptom_codes'])}. onset: one of {json.dumps(e['onset'])}. "
              f"worse_when: one of {json.dumps(e['worse_when'])}. severity: integer 1-5. "
              "needs_question: true when a single follow-up question would change the codes. Never invent codes outside the list.")
    user = text if not recent_summary else f"{text}\n\n[recent metrics] {recent_summary}"
    out = _chat(system, user)
    for key in ("onset", "worse_when"):      # 보조 필드를 지어내면 unknown 으로 둔다. codes 는 건드리지 않는다(목록 밖이면 거부).
        if key in out and out[key] not in e[key]:
            out[key] = "unknown"
    return _validated(out, "symptom")


def score_mood(text: str, lang: str) -> dict:
    """② 기분 문장 → MoodScore (mood, fatigue, stress 1-5, confidence 0-1)."""
    if _mode() == "mock":
        _delay()
        return _validated(_mock_pick("mood", text), "mood")
    system = ("Convert the crew member's free-text mood report into scales. Answer with JSON only: "
              "{\"mood\": 1-5 (5=best), \"fatigue\": 1-5 (5=most tired), \"stress\": 1-5 (5=most stressed), \"confidence\": 0-1}.")
    return _validated(_chat(system, text, 60), "mood")


# 재생성 때 모델에게 알려 주는 말: 검증기 검사 이름 → 고칠 점. 걸린 표현(verify 의 detail)이 있으면 뒤에 붙인다.
RETRY_HINTS = {
    "numbers": "the sentences contained a number, a clock time or a duration; write no digits at all",
    "cites": "cites must be numbers of the given paragraphs",
    "level": "the wording was stronger than the level allows; use calmer wording and avoid these words",
    "schema": "the JSON did not have the required shape; return exactly the keys shown above",
    "wording": "the sentences sounded certain or named another condition; say it is possible "
               "(Korean: end with '~일 수 있어요' or '가능성이 있어요', never '입니다'), never write 'certain', "
               "'definitely' or 'diagnosis', and do not name any condition that is not among the candidates",
}
ECHO = ("numbers", "level", "wording")     # 이 검사들은 걸린 표현을 그대로 알려 준다 (숫자, 금지어, 상태 이름)


def _retry_note(rejected: dict) -> str:
    parts = []
    for check, found in rejected.items():
        part = RETRY_HINTS[check]
        if check in ECHO and found:
            part += f" (you wrote: {', '.join(str(x) for x in found[:5])})"
        parts.append(part)
    return "\nYour previous answer was rejected by the checker. Fix this in the new answer: " + "; ".join(parts) + "."


def explain(level: str, findings: list, condition_candidates: list, paragraphs: list, lang: str, rejected=None) -> dict:
    """③ 규칙 판정 + findings + 검색 문단 → Explanation (category, condition_id, lines[≤3], cites[]).
    숫자 문장은 템플릿이 쓴다. 모델은 '왜·무엇을 조심' 1~2문장만. 반드시 verify.verify() 를 거친다.
    condition_id 는 condition_candidates 중 하나여야 한다(순서가 우선순위). 목록 밖 후보를 넘기면 ValueError.
    rejected 는 직전 실행의 verify()["detail"] (검사 이름 → 걸린 표현). 주면 프롬프트에 고칠 점을 덧붙인다(재생성, pipeline.py)."""
    conds = _conditions()
    unknown = [c for c in condition_candidates if c not in conds]
    if unknown:
        raise ValueError(f"unknown condition candidates {unknown}; see contracts/enums.json conditions")
    if _mode() == "mock":
        _delay()
        out = _mock_explanation(list(condition_candidates), paragraphs, lang)
        return _among_candidates(_validated(out, "explanation"), condition_candidates)
    cand = {c: conds[c] for c in condition_candidates}
    paras = "\n".join(f"[{n}] {p['text']}" for n, p in enumerate(paragraphs, 1))
    system = ("You write a short risk note for an astronaut. The rule engine already decided the level; never raise or lower it. "
              "Answer with JSON only: {\"category\": \"...\", \"condition_id\": \"one of the candidate keys\", "
              "\"lines\": [\"sentence\", \"sentence\"], \"cites\": [numbers of the paragraphs you used]}. "
              "lines is an array of 1-2 short sentences (why this matters, what to watch). "
              "Use only candidate conditions and only the given paragraphs. Do not state numbers. "
              "Say 'possible' / '가능성', never 'certain' or 'diagnosis'. "
              f"Write in {'Korean' if lang == 'ko' else 'English'}.")
    user = f"level: {level}\nfindings: {json.dumps(findings, ensure_ascii=False)}\ncandidates: {json.dumps(cand, ensure_ascii=False)}\nparagraphs:\n{paras}"
    if rejected:
        user += _retry_note(rejected)
    out = _chat(system, user, 220)
    if isinstance(out.get("cites"), list):   # 모델은 문단 번호만 쓴다. id 는 코드가 붙인다(잘못된 id 를 쓸 수 없게).
        out["cites"] = [_cite_id(c, paragraphs) for c in out["cites"]]
    return _among_candidates(_validated(out, "explanation"), condition_candidates)
