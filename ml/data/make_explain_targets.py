"""설명 학습 문항의 '답'을 만든다: 지금 서비스하는 구성(모델 + 프롬프트)이 쓴 문장 중 검증기를 통과한 것만 남긴다.

사용: python3 ml/data/make_explain_targets.py     (모델 서버가 떠 있어야 한다. 입력: ml/data/v2/explain_inputs.jsonl)
- 사람이 쓴 정답이 아니다. 어댑터를 학습할 때 설명 능력이 지금보다 나빠지지 않게 붙잡아 두는 용도다.
- 남기는 조건: 판단 보류 아님 · 첫 번째 후보를 고름 · 한국어는 모든 문장이 '요'로 끝남 · 문단의 '피할 말'이 없음.
"""
import json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["MODEL"] = "live"
from backend.model import client, pipeline      # noqa: E402

V2 = ROOT / "ml" / "data" / "v2"
kb = {json.loads(l)["id"]: json.loads(l) for f in sorted((ROOT / "ml" / "knowledge").glob("kb_*.jsonl")) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()}
cases = [json.loads(l) for l in (V2 / "explain_inputs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def yo(lines):
    parts = [s for line in lines for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
    return bool(parts) and all(re.sub(r"[\s.!?…]+$", "", s).endswith("요") for s in parts)


kept, dropped = [], {}
for n, c in enumerate(cases, 1):
    paras = [{"id": p, "text": kb[p]["text_" + c["para_lang"]]} for p in c["paragraphs"]]
    try:
        res = pipeline.explain_verified(c["level"], c["findings"], c["candidates"], paras, c["lang"])
    except client.ModelOutputError as e:
        sys.exit(f"ERROR {e}. Fix: start the model server (backend/model/README.md).")
    if any(r["note"].startswith("model unavailable") for r in res["runs"]):
        sys.exit("ERROR model server unreachable. Fix: start the model server (backend/model/README.md).")
    e = res["explanation"]
    avoid = [w for p in c["paragraphs"] for k in kb[p].get("key_terms", []) for w in k.get("ko_avoid", []) if w]
    why = ("hold" if res["hold"] else "not the first candidate" if e["condition_id"] != c["candidates"][0]
           else "not haeyo-che" if c["lang"] == "ko" and not yo(e["lines"])
           else "avoid term" if c["lang"] == "ko" and any(w in " ".join(e["lines"]) for w in avoid) else None)
    if why:
        dropped[why] = dropped.get(why, 0) + 1
    else:
        answer = {"category": e["category"], "condition_id": e["condition_id"], "lines": e["lines"], "cites": [c["paragraphs"].index(i) + 1 for i in e["cites"]]}
        kept.append({**{k: c[k] for k in ("id", "lang", "para_lang", "level", "candidates", "paragraphs", "findings")}, "answer": answer, "runs": len(res["runs"])})
    if n % 25 == 0:
        print(f"{n}/{len(cases)} kept {len(kept)} dropped {dropped}", flush=True)
(V2 / "explain_targets.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
print(f"done: kept {len(kept)} of {len(cases)}; dropped {dropped}; needed a second run {sum(r['runs'] > 1 for r in kept)}")
