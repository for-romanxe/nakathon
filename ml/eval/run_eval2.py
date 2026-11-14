"""평가셋 v2 실행기 (지식 문단 기반: 증상 · 기분 · 설명). 30문항 실행기(run_eval.py)는 그대로 둔다.

  python3 ml/eval/run_eval2.py --check                          # 세트 점검 (모델 불필요)
  python3 ml/eval/run_eval2.py --split dev --label <이름>        # 모델 서버(MODEL_URL, 기본 8080)가 떠 있어야 한다
  python3 ml/eval/run_eval2.py --split test --label <이름> [--only symptom,mood,explain]

split: dev = 프롬프트·체크포인트를 고를 때 쓴다. test = 정한 뒤 한 번만 돌린다. cross = 한국어 답 + 영어 문단(비교용).
결과: ml/eval/results/v2-<split>-<label>.json 과 사람이 읽을 .md (설명 문장과 원문 문단을 나란히).
"""
import argparse, datetime, json, os, pathlib, re, statistics, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT), str(HERE)]
from backend import contracts                      # noqa: E402
from backend.model import client, pipeline         # noqa: E402
from run_eval import call, score_symptom           # noqa: E402  (호출·채점은 30문항 실행기와 같은 코드)

V2, KB_DIR, TRAIN = HERE / "v2", ROOT / "ml" / "knowledge", ROOT / "ml" / "data" / "v2"
ENUMS = contracts.enums()
URGENT = set(ENUMS["immediate_warning_codes"])


def rows_of(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def load():
    kb = {p["id"]: p for f in sorted(KB_DIR.glob("kb_*.jsonl")) for p in rows_of(f)}
    return {"symptom": rows_of(V2 / "symptom.jsonl"), "mood": rows_of(V2 / "mood.jsonl"), "explain": rows_of(V2 / "explain.jsonl"), "kb": kb}


def norm(text):
    return re.sub(r"[\W_]+", "", text).lower()


def check(S):
    bad, codes, conds = [], set(ENUMS["symptom_codes"]), set(ENUMS["conditions"])
    for name in ("symptom", "mood", "explain"):
        ids = [r.get("id") for r in S[name]]
        bad += [f"{name}: id {i} repeated" for i in {i for i in ids if ids.count(i) > 1}]
        if not S[name]:
            bad.append(f"{name}: no items (ml/eval/v2/{name}.jsonl)")
    for r in S["symptom"]:
        e, a, f = (set(r.get(k, [])) for k in ("expect", "allow", "forbid"))
        if not e or (e | a | f) - codes or e & f or r.get("split") not in ("test", "dev") or r.get("lang") not in ("ko", "en"):
            bad.append(f"symptom {r.get('id')}: expect/allow/forbid, split or lang not valid")
        named, may = set(r.get("locations", [])), set(r.get("locations_allow", []))
        if "locations" not in r or (named | may) - set(ENUMS["body_location"]) or named & may or (e == {"none"} and named | may):
            bad.append(f"symptom {r.get('id')}: locations/locations_allow not valid")
    for r in S["mood"]:
        rng = r.get("range") or {}
        if not rng or set(rng) - {"mood", "fatigue", "stress"} or any(not (len(v) == 2 and 1 <= v[0] <= v[1] <= 5) for v in rng.values()):
            bad.append(f"mood {r.get('id')}: range not valid")
    held = json.loads((V2 / "heldout_paragraphs.json").read_text(encoding="utf-8")) if (V2 / "heldout_paragraphs.json").exists() else {}
    for r in S["explain"]:
        if set(r["paragraphs"]) - set(S["kb"]) or set(r["candidates"]) - conds or r["level"] not in ("advisory", "caution"):
            bad.append(f"explain {r['id']}: paragraph, candidate or level not valid")
    # 학습 자료와 겹치면 안 된다: 시험 전용 문단이 학습 입력에 들어갔는지, 평가 문장이 학습 문장과 같은지
    train_inputs = rows_of(TRAIN / "explain_inputs.jsonl")
    leaked = {p for r in train_inputs for p in r["paragraphs"]} & {p for ids in held.values() for p in ids}
    bad += [f"explain: held-out paragraph {p} is used in the training inputs" for p in sorted(leaked)]
    train_text = {norm(r["text"]) for name in ("symptom_natural.jsonl", "mood.jsonl") for r in rows_of(TRAIN / name)}
    for f in ("train.jsonl", "valid.jsonl"):
        train_text |= {norm(m["content"]) for r in rows_of(TRAIN / f) for m in r["messages"] if m["role"] == "user"}
    for name in ("symptom", "mood"):
        seen = {}
        for r in S[name]:
            key = norm(r["text"])
            if key in train_text:
                bad.append(f"{name} {r['id']}: the same sentence is in the training data")
            if key in seen:
                bad.append(f"{name} {r['id']}: same sentence as {seen[key]}")
            seen[key] = r["id"]
    return bad, bool(train_text)


def ends_in_yo(lines):
    sentences = [s for line in lines for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
    return bool(sentences) and all(re.sub(r"[\s.!?…]+$", "", s).endswith("요") for s in sentences)


def grounding(lines, texts):
    """답의 글자 3개 묶음 가운데 문단에도 있는 비율. 뜻 검사가 아니라 '문단에 없는 말을 얼마나 썼나'의 거친 지표다."""
    grams = lambda s: {s[i:i + 3] for i in range(len(s) - 2)}
    out, src = grams(norm(" ".join(lines))), grams(norm(" ".join(texts)))
    return round(len(out & src) / len(out), 2) if out else None


def score_locations(it, out):
    """부위(몸 화면 표시용): 말한 부위를 모두 냈고, 허용한 부위 말고는 더 내지 않았으면 ok. 칸이 없거나 ["unknown"]이면 missing(프론트가 문장에서 찾는다)."""
    if out is None:
        return None
    if out.get("locations", ["unknown"]) == ["unknown"]:
        return "missing"
    got, named = set(out["locations"]), set(it["locations"])
    return "ok" if named <= got <= named | set(it.get("locations_allow", [])) else "wrong"


def run(S, split, only):
    rows = []
    for it in S["symptom"] if "symptom" in only else []:
        if it["split"] != split:
            continue
        base = {"section": "symptom", "id": it["id"], "lang": it["lang"], "kind": it["kind"], "urgent": bool(set(it["expect"]) & URGENT), "names_part": bool(it["locations"])}
        out, err, _ = call(client.extract_symptoms, it["text"], it["lang"], mode="mock")
        rows.append({**base, "by": "keyword", "out": out, "error": err, **score_symptom(it, out)})
        out, err, sec = call(client.extract_symptoms, it["text"], it["lang"])
        rows.append({**base, "by": "model", "out": out, "error": err, "sec": round(sec, 2), **score_symptom(it, out), "loc": score_locations(it, out)})
    for it in S["mood"] if "mood" in only else []:
        if it["split"] != split:
            continue
        out, err, sec = call(client.score_mood, it["text"], it["lang"])
        off = [k for k, (lo, hi) in it["range"].items() if out is None or not lo <= out[k] <= hi]
        rows.append({"section": "mood", "id": it["id"], "lang": it["lang"], "by": "model", "out": out, "error": err, "sec": round(sec, 2), "ok": not off, "out_of_range": off})
    for it in S["explain"] if "explain" in only else []:
        if it["split"] != split:
            continue
        paras = [{"id": p, "text": S["kb"][p]["text_" + it["para_lang"]]} for p in it["paragraphs"]]
        outs, real = [], client.explain

        def spy(*args, **kwargs):                 # 폐기된 문장도 남긴다. 자리를 먼저 만들어 runs 와 순서를 맞춘다
            outs.append(None)
            outs[-1] = real(*args, **kwargs)
            return outs[-1]

        client.explain = spy
        try:
            result, _, sec = call(pipeline.explain_verified, it["level"], it["findings"], it["candidates"], paras, it["lang"])
        finally:
            client.explain = real
        down = [r["note"] for r in result["runs"] if r["note"].startswith("model unavailable")]
        if down:
            sys.exit(f"ERROR {down[0]}. Fix: start mlx_lm.server (backend/model/README.md) or set MODEL_URL.")
        shown = result["explanation"]
        avoid = [w for p in it["paragraphs"] for k in S["kb"][p].get("key_terms", []) for w in k.get("ko_avoid", [])]
        text = " ".join(shown["lines"]) if shown else ""
        rows.append({"section": "explain", "id": it["id"], "lang": it["lang"], "para_lang": it["para_lang"], "heldout": it["heldout_paragraphs"], "by": "model",
                     "attempts": [{"out": o, **{k: r[k] for k in ("ok", "fails", "note")}} for o, r in zip(outs, result["runs"])],
                     "sec": round(sec, 2), "first_ok": result["runs"][0]["ok"], "hold": result["hold"],
                     "picked_first": bool(shown) and shown["condition_id"] == it["candidates"][0],
                     "yo": ends_in_yo(shown["lines"]) if shown and it["lang"] == "ko" else None,
                     "avoid_hits": sorted({w for w in avoid if w and w in text}) if it["lang"] == "ko" else [],
                     "grounding": grounding(shown["lines"], [p["text"] for p in paras]) if shown and it["lang"] == it["para_lang"] else None})
    return rows


def frac(rows, key="hit"):
    return f"{sum(bool(r[key]) for r in rows)}/{len(rows)}"


def summary(rows):
    out = []
    sym = [r for r in rows if r["section"] == "symptom"]
    if sym:
        model, kw = [r for r in sym if r["by"] == "model"], [r for r in sym if r["by"] == "keyword"]
        out.append(f"symptom  model {frac(model)} (exact {frac(model, 'exact')})  keyword {frac(kw)}  | ko {frac([r for r in model if r['lang'] == 'ko'])}  en {frac([r for r in model if r['lang'] == 'en'])}")
        out.append("  by kind: " + "  ".join(f"{k} {frac([r for r in model if r['kind'] == k])}" for k in sorted({r["kind"] for r in model})))
        out.append(f"  urgent codes (chest pain, breathlessness, crisis) caught: model {frac([r for r in model if r['urgent']])}  keyword {frac([r for r in kw if r['urgent']])}")
        out.append(f"  schema errors: {sum(r['out'] is None for r in model)}")
        loc = [r for r in model if r.get("loc")]
        ok = lambda rs: f"{sum(r['loc'] == 'ok' for r in rs)}/{len(rs)}"
        out.append(f"  body parts (display only): right {ok(loc)}  field absent {sum(r['loc'] == 'missing' for r in loc)}"
                   f"  | report names a part {ok([r for r in loc if r['names_part']])}  names none {ok([r for r in loc if not r['names_part']])}")
    mood = [r for r in rows if r["section"] == "mood"]
    if mood:
        out.append(f"mood     in range {frac(mood, 'ok')}  schema errors {sum(r['out'] is None for r in mood)}")
    ex = [r for r in rows if r["section"] == "explain"]
    for name, rs in (("all", ex), ("held-out paragraphs", [r for r in ex if r["heldout"]]), ("seen paragraphs", [r for r in ex if not r["heldout"]])):
        if not rs or (name != "all" and len(rs) == len(ex)):
            continue
        ko = [r for r in rs if r["lang"] == "ko" and not r["hold"]]
        g = [r["grounding"] for r in rs if r["grounding"] is not None]
        out.append(f"explain  {name}: first-run pass {frac(rs, 'first_ok')}  hold {frac(rs, 'hold')}  picked first candidate {frac([r for r in rs if not r['hold']], 'picked_first')}"
                   + (f"  해요체 {frac(ko, 'yo')}  avoid-term hits {sum(bool(r['avoid_hits']) for r in ko)}" if ko else "")
                   + (f"  grounding median {statistics.median(g):.2f} (min {min(g):.2f})" if g else ""))
    for name in ("symptom", "mood", "explain"):
        secs = [r["sec"] for r in rows if r["section"] == name and r["by"] == "model"]
        if secs:
            out.append(f"latency  {name} median {statistics.median(secs):.1f}s  max {max(secs):.1f}s  (n={len(secs)})")
    return out


def sheet(S, rows, head):
    """사람이 읽을 표: 틀린 증상·기분 문항과, 설명 문장을 원문 문단과 나란히."""
    by_id = {r["id"]: r for name in ("symptom", "mood", "explain") for r in S[name]}
    md = [f"# 평가셋 v2 — {head['split']} · {head['label']} · {head['date']}", "", "```", *head["summary"], "```", "", "## 증상: 틀린 문항", "",
          "| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r["section"] == "symptom" and r["by"] == "model" and not r["hit"]:
            it = by_id[r["id"]]
            md.append(f"| {r['id']} | {r['kind']} | {it['text']} | {', '.join(it['expect'])} | {', '.join(it.get('forbid', [])) or '-'} | {', '.join(r['out']['codes']) if r['out'] else '오류: ' + str(r['error'])[:60]} |")
    md += ["", "## 부위: 틀린 문항 (표시용, 증상 점수와 별개)", "", "| # | 문장 | 말한 부위 | 허용 | 모델이 낸 부위 |", "|---|---|---|---|---|"]
    for r in rows:
        if r["section"] == "symptom" and r["by"] == "model" and r.get("loc") == "wrong":
            it = by_id[r["id"]]
            md.append(f"| {r['id']} | {it['text']} | {', '.join(it['locations']) or '-'} | {', '.join(it.get('locations_allow', [])) or '-'} | {', '.join(r['out']['locations']) or '-'} |")
    md += ["", "## 기분: 범위 밖 문항", "", "| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |", "|---|---|---|---|"]
    for r in rows:
        if r["section"] == "mood" and not r["ok"]:
            it = by_id[r["id"]]
            got = f"{r['out']['mood']} / {r['out']['fatigue']} / {r['out']['stress']}" if r["out"] else "오류"
            md.append(f"| {r['id']} | {it['text']} | {', '.join(f'{k} {lo}~{hi}' for k, (lo, hi) in it['range'].items())} | {got} |")
    md += ["", "## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)", ""]
    for r in rows:
        if r["section"] != "explain":
            continue
        it = by_id[r["id"]]
        flags = [f for f, on in (("판단 보류", r["hold"]), ("1차 폐기", not r["first_ok"]), ("첫 후보 아님", not r["hold"] and not r["picked_first"]),
                                 ("해요체 아님", r["yo"] is False), ("피할 말: " + ", ".join(r["avoid_hits"]), bool(r["avoid_hits"]))) if on]
        md += [f"### {r['id']} · {it['lang']} · {it['level']} · 후보 {', '.join(it['candidates'])}" + (" · 시험 전용 문단" if it["heldout_paragraphs"] else "")
               + (f" · ⚠ {' / '.join(flags)}" if flags else ""), ""]
        md += [f"- 문단 `{p}`: {S['kb'][p]['text_' + it['para_lang']]}" for p in it["paragraphs"]]
        for n, a in enumerate(r["attempts"], 1):
            md.append(f"- **{n}차** " + ("통과" if a["ok"] else f"폐기({a['note']})") + (f" [{a['out']['condition_id']}]: " + " / ".join(a["out"]["lines"]) if a["out"] else ""))
        md.append("")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "cross"], default="dev")
    ap.add_argument("--label", help="모델·구성 이름. 결과 파일 이름에도 쓴다")
    ap.add_argument("--only", default="symptom,mood,explain")
    ap.add_argument("--check", action="store_true", help="세트 점검만 하고 끝낸다")
    a = ap.parse_args()
    if a.label and not re.fullmatch(r"[A-Za-z0-9._+-]+", a.label):
        ap.error("--label may only contain letters, digits and . _ + -")
    only = set(a.only.split(","))
    if only - {"symptom", "mood", "explain"}:
        ap.error("--only takes symptom, mood, explain")
    S = load()
    problems, compared = check(S)
    problems = [x for x in problems if x.split()[0].rstrip(":") in only]      # 돌리지 않는 묶음의 문제로 멈추지 않는다
    counts = "  ".join(f"{name} " + "/".join(f"{s} {sum(r['split'] == s for r in S[name])}" for s in ("test", "dev", "cross") if any(r["split"] == s for r in S[name])) for name in ("symptom", "mood", "explain"))
    print("\n".join(problems) or f"set ok: {counts}; {len(S['kb'])} paragraphs; " + ("no evaluation sentence found in the training data" if compared else "overlap with training data not checked (no training files here)"))
    if a.check or problems:
        sys.exit(1 if problems else 0)
    if not a.label:
        ap.error("--label is required to run the evaluation")
    rows = run(S, a.split, only)
    head = {"label": a.label, "split": a.split, "date": datetime.datetime.now().isoformat(timespec="minutes"),
            "model_url": os.environ.get("MODEL_URL", "http://127.0.0.1:8080"), "summary": summary(rows)}
    out = HERE / "results" / f"v2-{a.split}-{a.label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({**head, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    out.with_suffix(".md").write_text(sheet(S, rows, head), encoding="utf-8")
    print(f"== v2 {a.split} · {a.label} · {head['date']}")
    print("\n".join(head["summary"]))
    print(f"saved {out.relative_to(ROOT)} and {out.with_suffix('.md').name}")
