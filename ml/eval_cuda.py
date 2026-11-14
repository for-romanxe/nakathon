"""valid.jsonl로 증상 JSON 추출 정확도 측정 (CUDA, transformers). eval_symptoms.py(MLX)와 같은 지표.

사용: python eval_cuda.py --model D:\\models\\X [--adapter D:\\adapters\\X-symptoms] [-n 240] [--no-think]
"""
import json, time, argparse, pathlib, re, statistics
import torch
from cuda_common import load_model

HERE = pathlib.Path(__file__).parent
SCHEMA = json.load(open(HERE / "data/symptoms/schema.json", encoding="utf-8"))
CODES = set(SCHEMA["codes"])

def parse(s):
    m = re.search(r"\{.*?\}", s, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def main(a):
    model, tok = load_model(a.model)
    if a.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, a.adapter)
    model.eval()
    rows = [json.loads(l) for l in open(HERE / "data/symptoms/valid.jsonl", encoding="utf-8")][: a.n]
    stats = dict(n=0, json_ok=0, codes_exact=0, jacc=0.0, onset=0, worse=0, sev=0, needq=0, out_of_list=0, lat=[])
    fails = []
    kw = {"enable_thinking": False} if a.no_think else {}
    for r in rows:
        msgs = r["messages"][:2]
        gold = json.loads(r["messages"][2]["content"])
        prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False, **kw)
        enc = tok(prompt, return_tensors="pt", add_special_tokens=False).to("cuda")
        t0 = time.time()
        with torch.no_grad():
            out_ids = model.generate(**enc, max_new_tokens=a.max_tokens, do_sample=False)
        out = tok.decode(out_ids[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
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
    rep["model"] = a.model; rep["adapter"] = a.adapter; rep["device"] = torch.cuda.get_device_name(0)
    print(json.dumps(rep, ensure_ascii=False), flush=True)
    for t, o in fails[: a.show]:
        print("  ✗", t, "=>", o.replace("\n", " "), flush=True)
    if a.out:
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rep, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("-n", type=int, default=240)
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--show", type=int, default=10)
    ap.add_argument("--out", default=str(HERE / "results_cuda.jsonl"))
    ap.add_argument("--no-think", action="store_true")
    main(ap.parse_args())
