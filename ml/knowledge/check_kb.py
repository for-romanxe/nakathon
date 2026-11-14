"""지식 문단(ml/knowledge/*.jsonl) 점검. 사용: python3 ml/knowledge/check_kb.py [파일...]  (기본: ml/knowledge/kb_*.jsonl)
문단은 모델에게 근거로 주는 글이다. 규칙을 어기면 모델이 그대로 따라 써서 검증기에 걸리거나 틀린 말을 하게 된다."""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENUMS = json.loads((ROOT / "contracts" / "enums.json").read_text(encoding="utf-8"))
CONDS = {k: v for k, v in ENUMS["conditions"].items() if isinstance(v, dict) and k != "none"}
KINDS = {"why", "self_care", "watch", "escalate", "basics"}
CONTEXTS = {"in_flight", "surface_or_landing", "any"}
ID = re.compile(r"^[a-z]+:[a-z0-9-]+#p[0-9]+$")
STRONG = ["즉시", "응급", "긴급", "지금 바로", "주의", "경고", "emergenc", "immediately", "urgent", "caution", "warning", "alert"]
AGENCY = re.compile(r"NASA|\bCSA\b|\bCDC\b|\bNIH\b|\bWHO\b|(?i:according to)|에 따르면")      # 약어는 대문자만 본다 ("who" 는 보통 낱말)
BANNED_SOURCE = re.compile(r"medlineplus\.gov/ency", re.I)       # A.D.A.M. 백과: 복사·AI 사용 금지


def problems(path):
    out, seen = [], set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        where = f"{path.name}:{n}"
        try:
            p = json.loads(line)
        except ValueError as e:
            out.append(f"{where} not JSON: {e}")
            continue
        pid = p.get("id", "")
        where += f" {pid}"
        if not ID.match(pid):
            out.append(f"{where} id must look like org:slug#pN")
        if pid in seen:
            out.append(f"{where} id repeated")
        seen.add(pid)
        if p.get("condition") not in CONDS:
            out.append(f"{where} unknown condition {p.get('condition')!r}")
        if p.get("kind") not in KINDS or p.get("context") not in CONTEXTS:
            out.append(f"{where} kind/context not allowed: {p.get('kind')!r}, {p.get('context')!r}")
        en, ko = p.get("text_en", ""), p.get("text_ko", "")
        if not en or not ko:
            out.append(f"{where} needs both text_en and text_ko")
        for name, text in (("text_en", en), ("text_ko", ko)):
            if re.search(r"[0-9０-９]", text):
                out.append(f"{where} {name} has a digit (the model copies it and the numbers check rejects the sentence)")
            if AGENCY.search(text):
                out.append(f"{where} {name} names an agency (provenance belongs in sources)")
            if p.get("kind") != "escalate":
                hit = [w for w in STRONG if w in text.lower()]
                if hit:
                    out.append(f"{where} {name} has a strong word outside an escalate paragraph: {hit}")
            for cid, c in CONDS.items():        # 다른 상태의 표시명이 들어가면 모델이 따라 쓰고 검증기가 폐기한다
                if cid != p.get("condition"):
                    for label in (c.get("ko"), c.get("en")):
                        if label and label.lower() in text.lower():
                            out.append(f"{where} {name} names another condition: {label}")
        if len(en.split()) > 60:
            out.append(f"{where} text_en is {len(en.split())} words (max 60)")
        if ko and not all(s.strip().endswith("다") for s in re.split(r"[.!?]\s*", ko) if s.strip()):
            out.append(f"{where} text_ko has a sentence that does not end in -다")
        src = p.get("sources") or []
        if not src or not all(s.get("url", "").startswith("http") for s in src):
            out.append(f"{where} needs at least one source with a URL")
        if any(BANNED_SOURCE.search(s.get("url", "")) for s in src):
            out.append(f"{where} cites the MedlinePlus encyclopedia (not allowed)")
        if any(s.get("verified") not in ("FT", "AB") for s in src):
            out.append(f"{where} source verified must be FT or AB")
    return out


if __name__ == "__main__":
    files = [pathlib.Path(a) for a in sys.argv[1:]] or sorted((ROOT / "ml" / "knowledge").glob("kb_*.jsonl"))
    found = [x for f in files for x in problems(f)]
    rows = [json.loads(l) for f in files for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("\n".join(found[:60]))
    by = {}
    for r in rows:
        by.setdefault(r.get("condition"), []).append(r)
    for cond, rs in sorted(by.items()):
        kinds = {k: sum(r.get("kind") == k for r in rs) for k in sorted(KINDS)}
        official = sum(any(s.get("challenge") for s in r.get("sources", [])) for r in rs)
        print(f"{cond:<26} {len(rs):>3} paragraphs  {kinds}  cites an official challenge page: {official}")
    print(f"{len(rows)} paragraphs in {len(files)} file(s), {len(found)} problem(s)")
    sys.exit(1 if found else 0)
