"""지식 문단(ml/knowledge/kb_*.jsonl)으로 설명 문항의 '입력'을 만든다: test / cross / dev / train.
답 문장은 여기서 만들지 않는다(학습용 답은 따로 쓰고 검증기로 거른다).

사용: python3 ml/data/build_explain_cases.py   → ml/eval/v2/explain.jsonl (test·cross·dev), ml/data/v2/explain_inputs.jsonl (train)
- 경보(warning) 상태인 cardiac_emergency·behavioral_crisis 는 모델을 건너뛰므로 설명 문항에 넣지 않는다.
- escalate 문단은 "즉시" 같은 말이 들어 있어 참고·주의 단계 문항에 쓰지 않는다.
- 상태마다 문단 2개(이유 1 + 할 일 1)를 시험 전용으로 떼어 둔다. 학습 문항은 나머지 문단만 쓴다.
- 지표와 상태의 짝(SIGNALS)은 문항을 만들기 위한 가정이다. 손목 신호로 이 상태들을 판별할 수 있다는 근거는 없다.
"""
import argparse, json, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKIP = {"cardiac_emergency", "behavioral_crisis"}
# 지표: (기준, 표준편차, 소수 자릿수) — contracts/enums.json metrics 의 decimals 와 같다
BASE = {"hr": (68, 5.0, 0), "hrv": (54, 6.0, 0), "eda": (3.8, 1.0, 1), "temp": (34.2, 0.35, 1), "sleep": (7.0, 0.8, 1), "act": (60, 15.0, 0)}
SIGNALS = {      # 상태 → (지표, 방향) 후보. 문항용 가정.
    "orthostatic_intolerance": [("hr", 1), ("hrv", -1)], "dehydration": [("hr", 1), ("hrv", -1), ("temp", 1)],
    "sleep_deficit": [("sleep", -1), ("hrv", -1)], "mood_low": [("hrv", -1), ("sleep", -1), ("act", -1)],
    "space_motion_sickness": [("eda", 1), ("hr", 1)], "co2_headache": [("sleep", -1), ("hr", 1)],
    "musculoskeletal_strain": [("act", -1), ("sleep", -1)], "upper_respiratory": [("temp", 1), ("hr", 1)],
    "skin_irritation": [("temp", 1), ("eda", 1)], "sans_suspect": [("sleep", -1), ("hrv", -1)],
}
RELATED = {      # 두 번째 후보로 함께 올 만한 상태
    "orthostatic_intolerance": "dehydration", "dehydration": "orthostatic_intolerance", "sleep_deficit": "mood_low", "mood_low": "sleep_deficit",
    "space_motion_sickness": "dehydration", "co2_headache": "sleep_deficit", "musculoskeletal_strain": "sleep_deficit",
    "upper_respiratory": "dehydration", "skin_irritation": None, "sans_suspect": "co2_headache",
}
WHY, DO = ("why", "basics"), ("self_care", "watch")


def finding(rng, metric, direction):
    base, sd, dec = BASE[metric]
    base = round(base + rng.uniform(-0.6, 0.6) * sd, dec)
    while True:
        value = round(base + direction * rng.uniform(2.05, 2.95) * sd, dec)
        z = round((value - base) / sd, 1)
        if 2.0 <= abs(z) < 3.0:
            return {"metric": metric, "value": int(value) if dec == 0 else value, "baseline": int(base) if dec == 0 else base, "sd": sd, "z": z}


def case(rng, cond, why, do, level, lang, para_lang, two_candidates):
    metrics = rng.sample(SIGNALS[cond], 2 if level == "caution" else 1)
    other = RELATED[cond] if two_candidates else None
    return {"lang": lang, "para_lang": para_lang, "level": level, "candidates": [cond] + ([other] if other else []),
            "paragraphs": [why["id"], do["id"]], "findings": [finding(rng, m, d) for m, d in metrics]}


def build(kb, seed=20261114):
    rng = random.Random(seed)
    by = {}
    for p in kb:
        if p["condition"] not in SKIP and p["kind"] != "escalate":
            by.setdefault(p["condition"], []).append(p)
    heldout, rows = {}, []
    for cond in sorted(by):
        ps = sorted(by[cond], key=lambda p: p["id"])
        whys, dos = [p for p in ps if p["kind"] in WHY], [p for p in ps if p["kind"] in DO]
        hw, hd = rng.choice(whys), rng.choice(dos)                       # 시험 전용 문단 2개
        heldout[cond] = [hw["id"], hd["id"]]
        seen_w, seen_d = [p for p in whys if p is not hw], [p for p in dos if p is not hd]
        used = set()

        def fresh(level, lang, two):
            for _ in range(200):
                w, d = rng.choice(seen_w), rng.choice(seen_d)
                key = (w["id"], d["id"], level, lang, two)
                if key not in used:
                    used.add(key)
                    return case(rng, cond, w, d, level, lang, lang, two)
            return None

        for lang in ("ko", "en"):
            rows.append({"split": "test", "heldout_paragraphs": True, **case(rng, cond, hw, hd, "caution", lang, lang, True)})
            rows.append({"split": "test", "heldout_paragraphs": False, **fresh("advisory", lang, False)})
            rows.append({"split": "dev", "heldout_paragraphs": False, **fresh(rng.choice(["advisory", "caution"]), lang, rng.random() < 0.5)})
        # 한국어 답 + 영어 문단: 문단을 미리 한국어로 준 경우와 비교하기 위한 문항 (시험 전용 문단)
        rows.append({"split": "cross", "heldout_paragraphs": True, **case(rng, cond, hw, hd, "advisory", "ko", "en", False)})
        for lang in ("ko", "en"):
            for _ in range(15):
                c = fresh(rng.choice(["advisory", "caution"]), lang, rng.random() < 0.4)
                if c:
                    rows.append({"split": "train", "heldout_paragraphs": False, **c})
    prefix = {"test": "ET", "cross": "EX", "dev": "ED", "train": "EN"}
    count = {}
    for r in rows:
        count[r["split"]] = count.get(r["split"], 0) + 1
        r["id"] = f"{prefix[r['split']]}-{count[r['split']]:03d}"
    return rows, heldout


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=str(ROOT / "ml" / "knowledge"))
    ap.add_argument("--eval-out", default=str(ROOT / "ml" / "eval" / "v2"))
    ap.add_argument("--train-out", default=str(ROOT / "ml" / "data" / "v2"))
    a = ap.parse_args()
    kb = [json.loads(l) for f in sorted(pathlib.Path(a.kb).glob("kb_*.jsonl")) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows, heldout = build(kb)
    train_paras = {p for r in rows if r["split"] == "train" for p in r["paragraphs"]}
    leaked = sorted(train_paras & {p for ids in heldout.values() for p in ids})
    assert not leaked, f"held-out paragraphs used in training: {leaked}"
    dump = lambda rs: "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs)
    ev, tr = pathlib.Path(a.eval_out), pathlib.Path(a.train_out)
    ev.mkdir(parents=True, exist_ok=True)
    tr.mkdir(parents=True, exist_ok=True)
    (ev / "explain.jsonl").write_text(dump(r for r in rows if r["split"] != "train"), encoding="utf-8")
    (ev / "heldout_paragraphs.json").write_text(json.dumps(heldout, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (tr / "explain_inputs.jsonl").write_text(dump(r for r in rows if r["split"] == "train"), encoding="utf-8")
    print({s: sum(r["split"] == s for r in rows) for s in ("test", "cross", "dev", "train")}, "| held-out paragraphs:", sum(len(v) for v in heldout.values()))
