FIELDS = ("title", "org", "kind")


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
        doc["paragraphs"].append({"n": int(para), "text": row["text"]})
    return [
        {"id": doc["id"], "title": doc.get("title", doc["id"]), "org": doc.get("org", ""),
         "kind": doc.get("kind", ""), "paragraphs": sorted(doc["paragraphs"], key=lambda p: p["n"])}
        for doc in docs.values()
    ]
