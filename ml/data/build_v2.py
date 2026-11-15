"""학습셋 v2 조립: 증상(템플릿 + 손으로 쓴 문장) · 기분 · 설명을 mlx-lm chat 형식 한 벌로 만든다.

사용: python3 ml/data/build_v2.py     → ml/data/v2/train.jsonl, valid.jsonl, summary.json
- 지시문은 서비스 코드(backend/model/client.py)의 것을 그대로 가져온다. 학습과 서비스의 프롬프트가 어긋날 수 없다.
- 라벨은 계약 스키마로, 설명 답은 검증기로 다시 확인한다. 하나라도 걸리면 멈춘다.
- 평가셋 v2(ml/eval/v2)와 같은 문장은 넣지 않는다.
"""
import importlib.util, json, pathlib, random, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend import contracts, verify            # noqa: E402
from backend.model import client                 # noqa: E402

HERE, V2, EVAL = pathlib.Path(__file__).resolve().parent, ROOT / "ml" / "data" / "v2", ROOT / "ml" / "eval" / "v2"
TEMPLATE_N, VALID_SHARE, SEED = 600, 0.1, 20261114


def rows(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def norm(text):
    return re.sub(r"[\W_]+", "", text).lower()


def chat(system, user, answer, shots=()):
    turns = [m for q, a in shots for m in ({"role": "user", "content": q}, {"role": "assistant", "content": a})]
    return {"messages": [{"role": "system", "content": system}, *turns, {"role": "user", "content": user},
                         {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)}]}


def must(ok, what):
    if not ok:
        sys.exit(f"ERROR {what}")


def build():
    rng = random.Random(SEED)
    held_out_text = {norm(r["text"]) for name in ("symptom.jsonl", "mood.jsonl") for r in rows(EVAL / name)}
    old = json.loads((ROOT / "ml" / "eval" / "questions.json").read_text(encoding="utf-8"))
    held_out_text |= {norm(r["text"]) for name in ("symptom", "mood") for r in old[name]}
    parts, skipped = {}, {}

    # 1) 증상 — 템플릿
    spec = importlib.util.spec_from_file_location("gen_symptoms", HERE / "gen_symptoms.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    gen.random.seed(SEED)
    seen, out = set(), []
    while len(out) < TEMPLATE_N:
        text, label = gen.make("ko" if gen.random.random() < 0.6 else "en")
        if text in seen or norm(text) in held_out_text:
            continue
        seen.add(text)
        out.append(chat(client._symptom_system(), text, label))
    parts["symptom_template"] = out

    # 2) 증상 — 손으로 쓴 문장
    out = []
    for r in rows(V2 / "symptom_natural.jsonl"):
        label = dict(r["label"], codes=sorted(r["label"]["codes"]))      # needs_question 은 작성자가 '모호하다'고 본 문장만 true
        if norm(r["text"]) in held_out_text:
            skipped["symptom_natural: same sentence as an evaluation item"] = skipped.get("symptom_natural: same sentence as an evaluation item", 0) + 1
            continue
        must(not contracts.check_schema(label, contracts.schema("symptom")), f"symptom label {r['id']} breaks the schema: {label}")
        out.append(chat(client._symptom_system(), r["text"], label))
    parts["symptom_natural"] = out

    # 3) 기분
    out = []
    for r in rows(V2 / "mood.jsonl"):
        if norm(r["text"]) in held_out_text:
            skipped["mood: same sentence as an evaluation item"] = skipped.get("mood: same sentence as an evaluation item", 0) + 1
            continue
        must(not contracts.check_schema(r["label"], contracts.schema("mood")), f"mood label {r['id']} breaks the schema: {r['label']}")
        out.append(chat(client.MOOD_SYSTEM, r["text"], r["label"]))
    parts["mood"] = out

    # 4) 설명 — 서비스와 같은 지시문·예시·요청 모양
    kb = {p["id"]: p for f in sorted((ROOT / "ml" / "knowledge").glob("kb_*.jsonl")) for p in rows(f)}
    held = json.loads((EVAL / "heldout_paragraphs.json").read_text(encoding="utf-8")) if (EVAL / "heldout_paragraphs.json").exists() else {}
    held_ids = {p for ids in held.values() for p in ids}
    prompts, out = client._explain_prompt(), []
    for r in rows(V2 / "explain_targets.jsonl"):
        must(not set(r["paragraphs"]) & held_ids, f"explanation {r['id']} uses a held-out paragraph")
        prompt = prompts["ko" if r["lang"] == "ko" else "en"]
        shots = [(client._explain_request(s["level"], s["findings"], s["candidates"], s["paragraphs"]), json.dumps(s["answer"], ensure_ascii=False)) for s in prompt["shots"]]
        texts = [kb[p]["text_" + r["para_lang"]] for p in r["paragraphs"]]
        shown = dict(r["answer"], cites=[r["paragraphs"][n - 1] for n in r["answer"]["cites"]])
        result = verify.verify(shown, r["findings"], r["level"], r["paragraphs"], r["lang"], candidates=r["candidates"])
        must(result["ok"], f"explanation {r['id']} does not pass the verifier: {result['note']}")
        out.append(chat(prompt["system"], client._explain_request(r["level"], r["findings"], r["candidates"], texts), r["answer"], shots))
    parts["explain"] = out

    train, valid = [], []
    for name, items in parts.items():
        for item in items:
            item["source"] = name               # 어디서 온 문항인지 (mlx-lm 은 messages 만 읽는다)
        rng.shuffle(items)
        cut = int(len(items) * VALID_SHARE)
        valid += items[:cut]
        train += items[cut:]
    rng.shuffle(train)
    rng.shuffle(valid)
    return train, valid, {"parts": {k: len(v) for k, v in parts.items()}, "train": len(train), "valid": len(valid), "skipped": skipped,
                          "template_n": TEMPLATE_N, "seed": SEED}


if __name__ == "__main__":
    train, valid, info = build()
    V2.mkdir(parents=True, exist_ok=True)
    for name, items in (("train.jsonl", train), ("valid.jsonl", valid)):
        (V2 / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items), encoding="utf-8")
    (V2 / "summary.json").write_text(json.dumps(info, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(info, ensure_ascii=False))
