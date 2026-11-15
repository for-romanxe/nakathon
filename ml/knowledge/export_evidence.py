"""지식 문단(kb_*.jsonl)을 백엔드가 읽는 근거 파일(CREW_HEALTH_EVIDENCE)로 바꾼다.

사용 (저장소 루트에서): python3 ml/knowledge/export_evidence.py ko > data/evidence-ko.json
                       CREW_HEALTH_EVIDENCE=data/evidence-ko.json MODEL=live python3 -m uvicorn backend.main:app --port 8000

백엔드는 증상 코드가 겹치는 문단을 파일 순서대로 앞에서 5개 고른다(backend/event_flow.py 의 relevant_evidence).
그래서 상태마다 이유 1개 + 할 일 1개를 맨 앞에 둔다(학습·평가 때 모델이 받은 모양). 나머지는 그 뒤에,
"즉시" 같은 말이 든 escalate 문단은 맨 끝에 둔다.

CODES(상태 → 증상 코드)는 AI 가 붙인 초안이고 사람이 검토하지 않았다. 코퍼스 담당이 확정한다.
한 실행에는 한 언어의 문단만 들어간다(백엔드 형식에 text 가 하나다).
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
CODES = {      # 상태 → 이 상태의 문단을 꺼낼 증상 코드. 순서가 곧 후보 순서다
    "orthostatic_intolerance": ["dizziness"],      # 백엔드가 "일어설 때 더 어지럽다"에 예라고 답한 때만 쓴다
    "space_motion_sickness": ["nausea", "dizziness"],
    "dehydration": ["dizziness", "nausea"],
    "co2_headache": ["headache"],
    "sleep_deficit": ["sleep_issue", "fatigue", "headache", "low_mood"],
    "mood_low": ["low_mood"],
    "musculoskeletal_strain": ["musculoskeletal_pain"],
    "upper_respiratory": ["congestion"],
    "skin_irritation": ["skin_rash"],
    "sans_suspect": ["vision_change"],
    "cardiac_emergency": ["chest_pain", "shortness_of_breath"],      # 경보 코드: 모델을 건너뛰므로 문서 화면에만 쓰인다
    "behavioral_crisis": ["crisis"],
}
WHY, DO = ("why", "basics"), ("self_care", "watch")


def export(lang):
    kb = [json.loads(l) for f in sorted(HERE.glob("kb_*.jsonl")) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    first = {}      # 문서(id 의 #p 앞)마다 제목·기관은 하나여야 한다: 번호가 가장 작은 문단의 것을 쓴다
    for p in sorted(kb, key=lambda p: int(p["id"].split("#p")[1])):
        first.setdefault(p["id"].split("#p")[0], p)
    lead = []
    for cond in CODES:
        ps = [p for p in kb if p["condition"] == cond]
        lead += [next(p for p in ps if p["kind"] in kinds) for kinds in (WHY, DO)]
    rest = [p for p in kb if p not in lead]
    ordered = lead + [p for p in rest if p["kind"] != "escalate"] + [p for p in rest if p["kind"] == "escalate"]
    return [{"id": p["id"], "text": p[f"text_{lang}"], "codes": CODES[p["condition"]], "condition_id": p["condition"],
             "title": first[p["id"].split("#p")[0]][f"title_{lang}"], "org": first[p["id"].split("#p")[0]]["sources"][0]["publisher"], "lang": lang}
            for p in ordered]


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("ko", "en"):
        sys.exit("usage: python3 ml/knowledge/export_evidence.py ko|en > data/evidence-ko.json")
    print(json.dumps(export(sys.argv[1]), ensure_ascii=False, indent=1))
