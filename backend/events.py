import json
import re
import sqlite3
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.seed import CONTRACT


# Demo keyword rules run before model inference.
WARNING_PHRASES = {
    "chest_pain": r"\bchest pain\b|흉통|가슴 통증|가슴이 아파",
    "shortness_of_breath": r"\bshortness of breath\b|\b(can't|cannot) breathe\b|호흡곤란|숨을 못 쉬",
    "crisis": r"\bkill myself\b|\bwant to die\b|죽고 싶",
}
CONSCIOUSNESS_CHANGE = r"\bloss of consciousness\b|\bunresponsive\b|의식 소실|의식이 없"


class SymptomInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=4000)
    lang: str

    @field_validator("lang")
    @classmethod
    def validate_language(cls, lang: str) -> str:
        if lang not in CONTRACT["lang"]:
            raise ValueError("Unsupported language.")
        return lang


class SymptomAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: Literal["yes", "no"]


class EventOverride(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str
    note: str | None = Field(default=None, max_length=4000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, reason: str) -> str:
        if reason not in CONTRACT["override_reason"]:
            raise ValueError("Unsupported override reason.")
        return reason


def urgent_symptoms(text: str) -> tuple[list[str], bool]:
    codes = [
        code for code in CONTRACT["immediate_warning_codes"]
        if code in WARNING_PHRASES and re.search(WARNING_PHRASES[code], text, re.IGNORECASE)
    ]
    return codes, bool(codes) or bool(re.search(CONSCIOUSNESS_CHANGE, text, re.IGNORECASE))


def readings_level(levels) -> str:
    return next((level for level in ("warning", "caution", "advisory", "hold") if level in levels), "normal")


def save_event(
    connection: sqlite3.Connection, crew_id: str, sol: int, report: SymptomInput, current: dict,
    timestamp: datetime,
) -> int:
    codes, urgent = urgent_symptoms(report.text)
    level = "warning" if urgent else readings_level({metric["level"] for metric in current["metrics"]})
    level = "caution" if level == "advisory" else level
    stages = ["collect", "rules"]
    if level == "warning":
        stages.append("done")
    cursor = connection.execute(
        """INSERT INTO event (crew_id, mission_day, ts, lang, symptom_text, codes, level, findings, urgent, pipeline)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (crew_id, sol, timestamp.isoformat(), report.lang, report.text, json.dumps(codes), level,
         json.dumps(current["metrics"], allow_nan=False), int(urgent), json.dumps({"stages": stages})),
    )
    return cursor.lastrowid


def event_payload(row: sqlite3.Row) -> dict:
    urgent = bool(row["urgent"]) if row["urgent"] is not None else urgent_symptoms(row["symptom_text"])[1]
    title = ("긴급 증상 보고" if urgent else "증상 보고") if row["lang"] == "ko" else (
        "Urgent symptom report" if urgent else "Symptom report"
    )
    state = json.loads(row["pipeline"]) if row["pipeline"] else {}
    stage = state["stages"][-1] if state else ("done" if row["level"] == "warning" else "hold")
    override = None
    if row["closed_reason"] in CONTRACT["override_reason"]:
        override = {"reason": row["closed_reason"], "note": row["override_note"], "ts": row["closed_at"]}
    return {
        "id": row["id"], "crew": row["crew_id"], "ts": row["ts"], "title": title,
        "symptom_text": row["symptom_text"], "codes": json.loads(row["codes"]),
        "urgent": urgent, "level": row["level"], "findings": json.loads(row["findings"]),
        "risk": state.get("risk"), "explanation": state.get("explanation"), "runs": state.get("runs", []),
        "verified": state.get("verified", 0), "stage": stage, "hold_reason": state.get("hold_reason"),
        "question": state.get("question"), "answer": state.get("answer"),
        "status": "closed" if row["closed_at"] else "open",
        "closed_reason": row["closed_reason"], "closed_at": row["closed_at"],
        "override": override, "shared": bool(row["shared"]), "tx_ref": None,
    }
