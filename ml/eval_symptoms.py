"""valid.jsonl로 증상 JSON 추출 정확도 측정 (바닐라 vs 어댑터).

사용: python eval_symptoms.py --model ml/models/X [--adapter ml/adapters/X] [-n 100]
지표: JSON 파싱 성공률, codes 정확 일치, codes Jaccard, onset/worse/severity/needs_q 일치, 목록 밖 코드 수, 평균 지연.
"""
import json, time, argparse, pathlib, re, statistics
from mlx_lm import load, generate

HERE = pathlib.Path(__file__).parent
SCHEMA = json.load(open(HERE / "data/symptoms/schema.json"))
CODES = set(SCHEMA["codes"])

def parse(s):
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def main(a):
    model, tok = load(a.model, adapter_path=a.adapter)
    rows = [json.loads(l) for l in open(HERE / "data/symptoms/valid.jsonl")][: a.n]
    stats = dict(n=0, json_ok=0, codes_exact=0, jacc=0.0, onset=0, worse=0, sev=0, needq=0, out_of_list=0, lat=[])
    fails = []
    for r in rows:
        msgs = r["messages"][:2]
        gold = json.loads(r["messages"][2]["content"])
        prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, **a.template_kwargs)
        t0 = time.time()
        out = generate(model, tok, prompt=prompt, max_tokens=a.max_tokens, verbose=False)
        stats["lat"].append(time.time() - t0)
        stats["n"] += 1
        p = parse(out)
        if not p or "codes" not in p:
            fails.append((msgs[1]["content"], out[:120]))
            continue
        stats["json_ok"] += 1
        pc = set(p.get("codes") or [])
        gc = set(gold["codes"])
        stats["out_of_list"] += len(pc - CODES)
        stats["codes_exact"] += pc == gc
        stats["jacc"] += len(pc & gc) / max(1, len(pc | gc))
        stats["onset"] += p.get("onset") == gold["onset"]
        stats["worse"] += p.get("worse_when") == gold["worse_when"]
        stats["sev"] += p.get("severity") == gold["severity"]
        stats["needq"] += bool(p.get("needs_question")) == gold["needs_question"]
        if pc != gc and len(fails) < 40:
            fails.append((msgs[1]["content"], out[:120]))
    n = stats["n"]
    rep = {k: (round(v / n, 3) if isinstance(v, (int, float)) and k not in ("n", "out_of_list") else v) for k, v in stats.items() if k != "lat"}
    rep["lat_p50"] = round(statistics.median(stats["lat"]), 2)
    rep["lat_p95"] = round(sorted(stats["lat"])[int(0.95 * len(stats["lat"])) - 1], 2)
    rep["model"] = a.model; rep["adapter"] = a.adapter
    print(json.dumps(rep, ensure_ascii=False))
    if a.show:
        for t, o in fails[: a.show]:
            print("  ✗", t, "=>", o.replace("\n", " "))
    if a.out:
        with open(a.out, "a") as f:
            f.write(json.dumps(rep, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("-n", type=int, default=120)
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--show", type=int, default=8)
    ap.add_argument("--out", default=str(HERE / "results.jsonl"))
    ap.add_argument("--no-think", action="store_true", help="템플릿에 enable_thinking=False 전달")
    a = ap.parse_args()
    a.template_kwargs = {"enable_thinking": False} if a.no_think else {}
    main(a)
