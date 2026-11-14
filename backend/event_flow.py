import json
import os
import re
from pathlib import Path

from backend import contracts
from backend.model import client, pipeline


def load_evidence() -> list[dict]:
    path = os.environ.get("CREW_HEALTH_EVIDENCE")
    if not path:
        return []
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Evidence must be a JSON array.")
    ids = set()
    conditions = {key for key, value in contracts.enums()["conditions"].items() if isinstance(value, dict)}
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or not re.fullmatch(r"[a-z]+:[a-z0-9-]+#p[1-9][0-9]*", row["id"]) or row["id"] in ids
                or not isinstance(row.get("text"), str) or not row["text"].strip()
                or not isinstance(row.get("codes"), list) or not row["codes"]
                or any(code not in contracts.enums()["symptom_codes"] or code == "none" for code in row["codes"])
                or not isinstance(row.get("condition_id"), str) or row["condition_id"] not in conditions):
            raise ValueError("Invalid or duplicate evidence paragraph.")
        ids.add(row["id"])
        action = row.get("action_text")
        if action is not None and (not isinstance(action, str) or not action.strip()):
            raise ValueError(f"Invalid action_text for {row['id']}.")
    return rows


def extract(event: dict, lang: str) -> tuple[list[str], dict]:
    state = {"stages": ["collect", "rules", "symptom"]}
    try:
        report = client.extract_symptoms(event["symptom_text"], lang, json.dumps(event["findings"]))
    except client.ModelOutputError:
        state["hold_reason"] = "symptom_extraction_failed"
        state["stages"].append("hold")
        return [], state
    codes = [code for code in report["codes"] if code != "none"] or ["none"]
    state["locations"] = report.get("locations", ["unknown"])
    if report["needs_question"]:
        if "dizziness" in codes:
            state["question_key"] = "worse_standing"
            state["question"] = ("일어설 때 더 어지럽나요?" if lang == "ko"
                                 else "Does the dizziness get worse when you stand up?")
        else:
            state["question_key"] = "still_present"
            state["question"] = "지금도 증상이 있나요?" if lang == "ko" else "Are you still experiencing the symptoms?"
        state["stages"].append("question")
    return codes, state


def relevant_evidence(evidence: list[dict], codes: list[str], state: dict) -> list[dict]:
    # A standing-related candidate requires an affirmative answer when asked.
    return [
        row for row in evidence if set(codes).intersection(row["codes"])
        and (row["condition_id"] != "orthostatic_intolerance"
             or (state.get("question_key") == "worse_standing" and state.get("answer") == "yes"))
    ][:5]


def explain(event: dict, state: dict, evidence: list[dict], lang: str) -> None:
    candidates = list(dict.fromkeys(row["condition_id"] for row in evidence))
    paragraphs = [{"id": row["id"], "text": row["text"]} for row in evidence]
    result = pipeline.explain_verified(event["level"], event["findings"], candidates, paragraphs, lang)
    state.update(explanation=result["explanation"], runs=result["runs"], verified=result["verified"])
    state["stages"].extend(["generate", "verify"])
    if result["hold"]:
        state["hold_reason"] = "explanation_not_verified"
    elif (explanation := result["explanation"]) is not None:
        cited = set(explanation["cites"])
        actions = [
            {"text": row["action_text"].strip(), "doc": row["id"], "done": False}
            for row in evidence
            if row["id"] in cited and row["condition_id"] == explanation["condition_id"] and row.get("action_text")
        ]
        if actions:
            state["risk"] = {"actions": actions}
    state["stages"].append("hold" if result["hold"] else "done")
