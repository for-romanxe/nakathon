import json
import re
import sqlite3
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.seed import CONTRACT


# Demo keyword rules run before model inference. The AI integration will handle
# free-form reports and provide the validated explanation in a later step.
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


def save_event(
    connection: sqlite3.Connection, crew_id: str, sol: int, report: SymptomInput, current: dict,
    timestamp: datetime,
) -> int:
    codes = [
        code for code in CONTRACT["immediate_warning_codes"]
        if code in WARNING_PHRASES and re.search(WARNING_PHRASES[code], report.text, re.IGNORECASE)
    ]
    urgent = bool(codes) or bool(re.search(CONSCIOUSNESS_CHANGE, report.text, re.IGNORECASE))
    level = current["status"]["level"]
    if urgent:
        level = "warning"
    elif level == "advisory":
        level = "caution"
    cursor = connection.execute(
        """INSERT INTO event (crew_id, mission_day, ts, lang, symptom_text, codes, level, findings)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (crew_id, sol, timestamp.isoformat(), report.lang, report.text, json.dumps(codes), level,
         json.dumps(current["metrics"], allow_nan=False)),
    )
    return cursor.lastrowid


def event_payload(row: sqlite3.Row) -> dict:
    warning = row["level"] == "warning"
    title = ("긴급 증상 보고" if warning else "증상 보고") if row["lang"] == "ko" else (
        "Urgent symptom report" if warning else "Symptom report"
    )
    return {
        "id": row["id"], "crew": row["crew_id"], "ts": row["ts"], "title": title,
        "symptom_text": row["symptom_text"], "codes": json.loads(row["codes"]),
        "level": row["level"], "findings": json.loads(row["findings"]),
        "risk": None, "explanation": None, "runs": [], "verified": 0,
        "status": "open", "closed_reason": None, "shared": False, "tx_ref": None,
    }
