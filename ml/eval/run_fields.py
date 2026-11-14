"""학습에 쓰지 않은 문장(ml/data/v2/valid.jsonl)으로 필드별 일치를 잰다: 증상 5개 필드, 기분 3개 척도.

평가셋 v2(run_eval2.py)는 코드가 맞는지만 본다. 여기서는 onset·worse_when·severity·needs_question 과 기분 점수가
라벨 규칙(research_notes 의 ITEM_SPEC, ml/data/gen_symptoms.py)과 얼마나 맞는지 본다. 라벨은 규칙으로 붙인 것이지 사람의 정답이 아니다.

사용: MODEL=live python3 ml/eval/run_fields.py --label <구성 이름> [-n 문항 수]
서버(MODEL_URL, 기본 127.0.0.1:8080)가 떠 있어야 한다. 어댑터를 비교하려면 서버를 --adapter-path 로 다시 띄운다.
"""
import argparse, json, os, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MODEL", "live")
from backend.model import client      # noqa: E402

FIELDS = ("codes", "onset", "worse_when", "severity", "needs_question")
DIMS = ("mood", "fatigue", "stress")


def frac(n, d):
    return f"{n}/{d}" if d else "-"


def main(a):
    rows = [json.loads(l) for l in (ROOT / "ml" / "data" / "v2" / "valid.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for r in rows:
        kind = "symptom" if r["source"].startswith("symptom") else "mood" if r["source"] == "mood" else None
        if not kind or sum(o["source"] == r["source"] for o in out) >= a.n:
            continue
        text, gold = r["messages"][-2]["content"], json.loads(r["messages"][-1]["content"])
        try:
            got = client.extract_symptoms(text, "ko") if kind == "symptom" else client.score_mood(text, "ko")
        except client.ModelOutputError as e:
            got = None
            print(f"  rejected: {text[:60]} | {e}")
        if got and kind == "symptom":
            got["codes"] = sorted(got["codes"])
        out.append({"source": r["source"], "text": text, "gold": gold, "got": got})
    print(f"== fields · {a.label} · {len(out)} sentences not used in training")
    for source in sorted({o["source"] for o in out}):
        rs = [o for o in out if o["source"] == source]
        ok = [o for o in rs if o["got"]]
        if source == "mood":
            parts = [f"{d} exact {frac(sum(o['got'][d] == o['gold'][d] for o in ok), len(rs))} within one {frac(sum(abs(o['got'][d] - o['gold'][d]) <= 1 for o in ok), len(rs))}" for d in DIMS]
        else:
            parts = [f"{f} {frac(sum(o['got'][f] == o['gold'][f] for o in ok), len(rs))}" for f in FIELDS]
            parts.append(f"severity within one {frac(sum(abs(o['got']['severity'] - o['gold']['severity']) <= 1 for o in ok), len(rs))}")
            parts.append(f"all five {frac(sum(all(o['got'][f] == o['gold'][f] for f in FIELDS) for o in ok), len(rs))}")
        print(f"{source:17} rejected {len(rs) - len(ok)}  |  " + "  ".join(parts))
    path = ROOT / "ml" / "eval" / "results" / f"v2-fields-{a.label}.json"
    path.write_text(json.dumps({"label": a.label, "rows": out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("saved", path.relative_to(ROOT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("-n", type=int, default=60, help="종류(템플릿·손으로 쓴 문장·기분)마다 최대 문항 수")
    main(ap.parse_args())
