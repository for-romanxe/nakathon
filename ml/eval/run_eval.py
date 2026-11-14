"""평가 질문셋 30문항 실행기 (명세 §19).

  python3 ml/eval/run_eval.py --label <모델 이름> [--repeat 3]     # 모델 서버(MODEL_URL, 기본 8080)가 떠 있어야 한다
  python3 ml/eval/run_eval.py --check                               # 질문셋 자체 점검 + 학습셋과 겹치는 문장 찾기 (모델 불필요)

증상은 키워드(mock)와 모델(live)을 같은 문장으로 비교한다. 기분·설명은 모델만 잰다.
설명은 백엔드가 쓰는 pipeline.explain_verified() 를 그대로 돈다: 생성 → 검증, 실패하면 이유를 알려 주고 한 번 더, 두 번 실패하면 판단 보류.
"""
import argparse, datetime, json, os, pathlib, re, statistics, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import contracts                    # noqa: E402
from backend.model import client, pipeline       # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def _unique_keys(pairs):
    """JSON 은 같은 키를 두 번 써도 조용히 뒤의 것만 남긴다. 문단 id 가 겹치면 여기서 멈춘다."""
    keys = [k for k, _ in pairs]
    repeated = sorted({k for k in keys if keys.count(k) > 1})
    if repeated:
        sys.exit(f"ERROR questions.json repeats the key(s) {repeated}. Fix: give each entry its own id.")
    return dict(pairs)


Q = json.loads((HERE / "questions.json").read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)


def check_set(overlap=True):
    """질문셋이 계약과 맞는지 본다. 문제를 한 줄씩 돌려준다."""
    e, bad = contracts.enums(), []
    if [len(Q[k]) for k in ("symptom", "mood", "explain")] != [12, 8, 10]:
        bad.append("counts must be symptom 12 / mood 8 / explain 10")
    for it in Q["symptom"]:
        for code in it["expect"] + it.get("allow", []) + it.get("forbid", []):
            if code not in e["symptom_codes"]:
                bad.append(f"{it['id']}: unknown symptom code {code}")
    cite = re.compile(contracts.schema("explanation")["properties"]["cites"]["items"]["pattern"])
    bad += [f"paragraph id {p} does not match the cite format {cite.pattern}" for p in Q["paragraphs"] if p != "_doc" and not cite.match(p)]
    for it in Q["explain"]:
        bad += [f"{it['id']}: unknown condition {c}" for c in it["candidates"] if c not in e["conditions"]]
        bad += [f"{it['id']}: unknown paragraph {p}" for p in it["paragraphs"] if p not in Q["paragraphs"]]
        if len(set(it["paragraphs"])) != len(it["paragraphs"]):
            bad.append(f"{it['id']}: the same paragraph is listed twice")
        for f in it["findings"]:
            if abs(round((f["value"] - f["baseline"]) / f["sd"], 1) - f["z"]) > 0.051:
                bad.append(f"{it['id']}: z of {f['metric']} does not match value/baseline/sd")
    if overlap:
        seen = set()
        for name in ("train.jsonl", "valid.jsonl"):
            path = ROOT / "ml" / "data" / "symptoms" / name
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    seen.update(m["content"].strip() for m in json.loads(line)["messages"] if m["role"] == "user")
        if not seen:
            bad.append("overlap not checked: ml/data/symptoms is missing on this machine")
        bad += [f"{it['id']}: sentence is in the training data" for it in Q["symptom"] + Q["mood"] if it["text"] in seen]
    return bad


def call(fn, *args, mode="live"):
    """(출력 또는 None, 오류 문자열 또는 None, 초). 서버에 닿지 못하면 바로 끝낸다."""
    old = {k: os.environ.get(k) for k in ("MODEL", "MOCK_DELAY")}
    os.environ.update(MODEL=mode, MOCK_DELAY="0")
    t = time.time()
    try:
        return fn(*args), None, time.time() - t
    except client.ModelUnavailableError as err:
        sys.exit(f"ERROR model server unreachable: {err}. Fix: start mlx_lm.server (backend/model/README.md) or set MODEL_URL.")
    except client.ModelOutputError as err:
        return None, str(err), time.time() - t
    finally:
        for k, v in old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


def score_symptom(it, out):
    if out is None:
        return {"hit": False, "exact": False}
    got, want = set(out["codes"]), set(it["expect"])
    hit = want <= got and not got & set(it.get("forbid", []))
    return {"hit": hit, "exact": hit and got <= want | set(it.get("allow", []))}


def run(repeat):
    rows = []
    for it in Q["symptom"]:
        out, err, _ = call(client.extract_symptoms, it["text"], it["lang"], mode="mock")
        rows.append({"section": "symptom", "id": it["id"], "kind": it["kind"], "by": "keyword", "run": 0,
                     "out": out, "error": err, **score_symptom(it, out)})
        for n in range(1, repeat + 1):
            out, err, sec = call(client.extract_symptoms, it["text"], it["lang"])
            rows.append({"section": "symptom", "id": it["id"], "kind": it["kind"], "by": "model", "run": n,
                         "out": out, "error": err, "sec": round(sec, 2), **score_symptom(it, out)})
    for it in Q["mood"]:
        for n in range(1, repeat + 1):
            out, err, sec = call(client.score_mood, it["text"], it["lang"])
            # out 은 score_mood 의 스키마 검사를 통과한 값이라 mood·fatigue·stress 가 모두 정수로 들어 있다. 아니면 None 이다.
            off = [k for k, (lo, hi) in it["range"].items() if out is None or not lo <= out[k] <= hi]
            rows.append({"section": "mood", "id": it["id"], "by": "model", "run": n, "out": out, "error": err,
                         "sec": round(sec, 2), "ok": not off, "out_of_range": off})
    for it in Q["explain"]:
        paras = [{"id": p, "text": Q["paragraphs"][p]} for p in it["paragraphs"]]
        for n in range(1, repeat + 1):
            outs, real = [], client.explain

            def spy(*args, **kwargs):                # 폐기된 문장도 결과 파일에 남긴다
                outs.append(None)                    # 자리를 먼저 만든다: 호출이 예외로 끝나도 runs 와 순서가 맞는다
                outs[-1] = real(*args, **kwargs)
                return outs[-1]

            client.explain = spy
            try:
                result, _, sec = call(pipeline.explain_verified, it["level"], it["findings"], it["candidates"], paras, it["lang"])
            finally:
                client.explain = real
            down = [r["note"] for r in result["runs"] if r["note"].startswith("model unavailable")]
            if down:                                 # 재생성 중에 서버가 죽어도 보류로 세지 않고 멈춘다. 일부만 잰 결과는 저장하지 않는다
                sys.exit(f"ERROR {down[0]}. Fix: start mlx_lm.server (backend/model/README.md) or set MODEL_URL.")
            attempts = [{"out": out, **{k: r[k] for k in ("ok", "fails", "note")}} for out, r in zip(outs, result["runs"])]
            rows.append({"section": "explain", "id": it["id"], "by": "model", "run": n, "attempts": attempts,
                         "sec": round(sec, 2), "ok": not result["hold"], "hold": result["hold"]})
    return rows


def rate(rows, key):
    return f"{sum(bool(r[key]) for r in rows)}/{len(rows)}"


def summary(rows):
    sym = [r for r in rows if r["section"] == "symptom"]
    lines = []
    for by in ("keyword", "model"):
        part = [r for r in sym if r["by"] == by]
        kinds = "  ".join(f"{k} {rate([r for r in part if r['kind'] == k], 'hit')}"
                          for k in ("plain", "paraphrase", "negation", "mixed", "none"))
        lines.append(f"symptom {by:7} hit {rate(part, 'hit')}  exact {rate(part, 'exact')}  | {kinds}")
    mood = [r for r in rows if r["section"] == "mood"]
    lines.append(f"mood    model   in range {rate(mood, 'ok')}  schema errors {sum(r['error'] is not None for r in mood)}")
    exp = [r for r in rows if r["section"] == "explain"]
    first = [r["attempts"][0] for r in exp]
    by_check = {c: sum(c in a["fails"] for a in first) for c in contracts.enums()["verify_check"]}
    retried = [r for r in exp if len(r["attempts"]) > 1]
    lines.append(f"explain model   first run rejected {sum(not a['ok'] for a in first)}/{len(first)} "
                 f"({', '.join(f'{c} {n}' for c, n in by_check.items() if n) or 'none'})  "
                 f"second run passed {rate(retried, 'ok') if retried else '0/0'}  hold {rate(exp, 'hold')}")
    for sec in ("symptom", "mood", "explain"):
        t = [r["sec"] for r in rows if r["section"] == sec and "sec" in r]
        lines.append(f"latency {sec:7} median {statistics.median(t):.1f}s  mean {statistics.mean(t):.1f}s  max {max(t):.1f}s  (n={len(t)})")
    same = {}
    for r in rows:
        if r["by"] == "model":
            same.setdefault((r["section"], r["id"]), set()).add(json.dumps(r.get("out", r.get("attempts")), sort_keys=True, ensure_ascii=False))
    lines.append(f"identical output across runs: {sum(len(v) == 1 for v in same.values())}/{len(same)} questions")
    return lines


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", help="모델·어댑터 이름. 결과 파일 이름에도 쓴다")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--check", action="store_true", help="질문셋 점검만 하고 끝낸다")
    a = ap.parse_args()
    if a.repeat < 1:
        ap.error("--repeat must be 1 or more")
    if a.label and not re.fullmatch(r"[A-Za-z0-9._+-]+", a.label):     # 결과 파일 이름이 된다. 경로 글자는 받지 않는다
        ap.error("--label may only contain letters, digits and . _ + -")
    found = check_set()
    skipped = [p for p in found if p.startswith("overlap not checked")]      # 학습 파일이 없는 기기: 실패가 아니라 알림
    problems = [p for p in found if p not in skipped]
    print("\n".join(problems) or "question set ok: 12 symptom / 8 mood / 10 explain, "
          + (skipped[0] if skipped else "no sentence found in the training data"))
    if a.check or problems:
        sys.exit(1 if problems else 0)
    if not a.label:
        ap.error("--label is required to run the evaluation")
    rows = run(a.repeat)
    head = {"label": a.label, "date": datetime.datetime.now().isoformat(timespec="minutes"), "repeat": a.repeat,
            "question_set_version": Q["version"], "model_url": os.environ.get("MODEL_URL", "http://127.0.0.1:8080"),
            "model_name": os.environ.get("MODEL_NAME", "default_model"), "summary": summary(rows)}
    out = HERE / "results" / f"{a.label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({**head, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"== {a.label} · {head['date']} · repeat {a.repeat}")
    print("\n".join(head["summary"]))
    print(f"saved {out.relative_to(ROOT)}")
