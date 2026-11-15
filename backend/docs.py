FIELDS = ("title", "org", "kind")
LANGS = ("ko", "en")      # optional row metadata; legacy or unsupported values are omitted, never inferred or rejected


def _out(doc: dict) -> dict:
    paragraphs = sorted(doc["paragraphs"], key=lambda p: p["n"])
    out = {"id": doc["id"], "title": doc.get("title", doc["id"]), "org": doc.get("org", ""),
           "kind": doc.get("kind", ""), "paragraphs": paragraphs}
    langs = {p.get("lang") for p in paragraphs}
    if len(langs) == 1 and None not in langs:
        out["lang"] = langs.pop()
    return out


def build_docs(evidence: list[dict]) -> list[dict]:
    """Group validated evidence paragraphs into documents exposing UI fields only."""
    docs = {}
    for row in evidence:
        doc_id, para = row["id"].split("#p")
        doc = docs.setdefault(doc_id, {"id": doc_id, "paragraphs": []})
        for field in FIELDS:
            value = row.get(field)
            if value is None or value == "":
                continue
            if not isinstance(value, str):
                raise ValueError(f"Invalid {field} for {doc_id}.")
            if doc.setdefault(field, value) != value:
                raise ValueError(f"Conflicting {field} for {doc_id}.")
        paragraph = {"n": int(para), "text": row["text"]}
        if row.get("lang") in LANGS:
            paragraph["lang"] = row["lang"]
        doc["paragraphs"].append(paragraph)
    return [_out(doc) for doc in docs.values()]
