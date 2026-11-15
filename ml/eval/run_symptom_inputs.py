"""증상 추출을 두 입력으로 잰다: 문장만(학습·평가 때 모양) / 문장 + 측정값 JSON(백엔드가 실제로 보내는 모양).

백엔드는 extract_symptoms(문장, 언어, 측정값 JSON) 으로 부른다(backend/event_flow.py). 평가셋 v2(run_eval2.py)는 문장만 넣는다.
두 입력에서 결과가 같은지 본다. 측정값은 데모 승무원 c1 의 것(ml/eval/v2/serving_findings.json, 백엔드 /events 응답에서 가져옴).

사용: MODEL=live python3 ml/eval/run_symptom_inputs.py dev|test   → ml/eval/results/v2-<split>-symptom-inputs.json
"""
import json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MODEL", "live")
from backend.model import client      # noqa: E402

split = sys.argv[1]
findings = (ROOT / "ml" / "eval" / "v2" / "serving_findings.json").read_text(encoding="utf-8").strip()
items = [json.loads(l) for l in (ROOT / "ml" / "eval" / "v2" / "symptom.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
items = [it for it in items if it["split"] == split]
rows = []
for name, summary in (("sentence only", ""), ("sentence + metrics", findings)):
    right = rejected = loc_right = 0
    for it in items:
        try:
            got = client.extract_symptoms(it["text"], it["lang"], summary)
        except client.ModelOutputError as e:
            rejected += 1
            rows.append({"cond": name, "id": it["id"], "text": it["text"], "error": str(e)[:160]})
            continue
        ok = all(c in got["codes"] for c in it["expect"]) and not any(c in got["codes"] for c in it["forbid"])
        need, allow = set(it.get("locations", [])), set(it.get("locations_allow", []))
        loc = set(got.get("locations", ["unknown"]))
        loc_ok = need <= loc <= need | allow
        right += ok; loc_right += loc_ok
        rows.append({"cond": name, "id": it["id"], "text": it["text"], "codes": got["codes"], "ok": ok, "locations": sorted(loc), "loc_ok": loc_ok})
    print(f"{split} · {name:20} codes right {right}/{len(items)}  rejected {rejected}  body parts right {loc_right}/{len(items)}", flush=True)
path = ROOT / "ml" / "eval" / "results" / f"v2-{split}-symptom-inputs.json"
path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("saved", path.relative_to(ROOT))
