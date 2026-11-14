"""모델 호출 단일 진입점 (CONTRACT §4). 함수 3개만 외부에 노출한다.

MODEL=mock (기본)  : backend/mock/*.json 시나리오를 MOCK_DELAY초 지연으로 돌려준다.
MODEL=live         : MODEL_URL 의 OpenAI 호환 /v1/chat/completions 를 호출한다 (mlx_lm.server 등).
어느 모드든 출력은 contracts 스키마 검사를 통과해야 하고, 실패하면 ModelOutputError.
판정·경보는 여기서 하지 않는다. 규칙 엔진이 한다.
"""
import json, os, re, time, urllib.request, pathlib
from .. import contracts

MOCK_DIR = pathlib.Path(__file__).resolve().parent.parent / "mock"


class ModelOutputError(Exception):
    pass


def _mode():
    return os.environ.get("MODEL", "mock")


def _delay():
    time.sleep(float(os.environ.get("MOCK_DELAY", "1")))


def _chat(system: str, user: str, max_tokens=160) -> dict:
    """live 모드: OpenAI 호환 서버 호출 후 첫 JSON 객체를 파싱."""
    url = os.environ.get("MODEL_URL", "http://127.0.0.1:8080").rstrip("/") + "/v1/chat/completions"
    body = {"model": os.environ.get("MODEL_NAME", "default"), "temperature": 0, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=float(os.environ.get("MODEL_TIMEOUT", "60"))) as r:
        text = json.load(r)["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ModelOutputError("no JSON in model output")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ModelOutputError(f"bad JSON: {e}")


def _validated(obj, kind):
    fails = contracts.check_schema(obj, contracts.schema(kind))
    if fails:
        raise ModelOutputError(f"{kind}: " + "; ".join(fails))
    return obj


def _mock_pick(kind: str, text: str) -> dict:
    """mock/<kind>.json: [{match:[키워드...], out:{...}}, ...]. 첫 매치, 없으면 마지막(default)."""
    rows = json.loads((MOCK_DIR / f"{kind}.json").read_text(encoding="utf-8"))
    low = text.lower()
    for row in rows:
        if any(k.lower() in low for k in row.get("match", [])):
            return row["out"]
    return rows[-1]["out"]


# ---- 공개 함수 3개 -------------------------------------------------------

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
    return _validated(_chat(system, user), "symptom")


def score_mood(text: str, lang: str) -> dict:
    """② 기분 문장 → MoodScore (mood, fatigue, stress 1-5, confidence 0-1)."""
    if _mode() == "mock":
        _delay()
        return _validated(_mock_pick("mood", text), "mood")
    system = ("Convert the crew member's free-text mood report into scales. Answer with JSON only: "
              "{\"mood\": 1-5 (5=best), \"fatigue\": 1-5 (5=most tired), \"stress\": 1-5 (5=most stressed), \"confidence\": 0-1}.")
    return _validated(_chat(system, text, 60), "mood")


def explain(level: str, findings: list, condition_candidates: list, paragraphs: list, lang: str) -> dict:
    """③ 규칙 판정 + findings + 검색 문단 → Explanation (category, condition_id, lines[≤3], cites[]).
    숫자 문장은 템플릿이 쓴다. 모델은 '왜·무엇을 조심' 1~2문장만. 반드시 verify.verify() 를 거친다."""
    if _mode() == "mock":
        _delay()
        key = " ".join(condition_candidates) + " " + level
        return _validated(_mock_pick("explanation", key), "explanation")
    conds = contracts.enums()["conditions"]
    cand = {c: conds[c] for c in condition_candidates if c in conds}
    paras = "\n".join(f"[{p['id']}] {p['text']}" for p in paragraphs)
    system = ("You write a short risk note for an astronaut. The rule engine already decided the level; never raise or lower it. "
              "Answer with JSON only: {\"category\": str, \"condition_id\": one of the candidate keys, "
              "\"lines\": 1-2 sentences (why this matters, what to watch), \"cites\": paragraph ids you used}. "
              "Use only candidate conditions and only the given paragraphs. Do not state numbers. "
              "Say 'possible' / '가능성', never 'certain' or 'diagnosis'. "
              f"Write in {'Korean' if lang == 'ko' else 'English'}.")
    user = f"level: {level}\nfindings: {json.dumps(findings, ensure_ascii=False)}\ncandidates: {json.dumps(cand, ensure_ascii=False)}\nparagraphs:\n{paras}"
    return _validated(_chat(system, user, 220), "explanation")
