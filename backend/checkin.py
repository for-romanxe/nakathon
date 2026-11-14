import json
import sqlite3
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.seed import CONTRACT


SCALES = ("sleep_quality", "mood", "fatigue", "stress")


class Checkin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    answers: dict[str, Any]
    free_text: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_checkin(self) -> "Checkin":
        if self.kind not in CONTRACT["checkin_kind"]:
            raise ValueError("Unknown check-in kind.")
        if self.kind == "morning" and not set(SCALES[:3]) <= self.answers.keys():
            raise ValueError("Morning check-in requires sleep_quality, mood, and fatigue.")
        for key in SCALES:
            if key in self.answers:
                score = self.answers[key]
                if type(score) is not int or not 1 <= score <= 5:
                    raise ValueError(f"{key} must be an integer from 1 to 5.")
        if "symptoms" in self.answers and self.answers["symptoms"] not in ("none", "yes"):
            raise ValueError("symptoms must be none or yes.")
        try:
            json.dumps(self.answers, allow_nan=False)
        except ValueError as error:
            raise ValueError("Answers must contain finite JSON values.") from error
        return self


def save_checkin(
    connection: sqlite3.Connection, crew_id: str, sol: int, checkin: Checkin, level: str,
    timestamp: datetime,
) -> None:
    connection.execute(
        """INSERT INTO checkin (crew_id, mission_day, kind, answers, free_text, at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (crew_id, mission_day, kind) DO UPDATE
           SET answers = excluded.answers, free_text = excluded.free_text,
               derived = CASE
                   WHEN checkin.answers = excluded.answers
                    AND checkin.free_text IS excluded.free_text THEN checkin.derived
                   ELSE NULL
               END, at = excluded.at""",
        (crew_id, sol, checkin.kind, json.dumps(checkin.answers, sort_keys=True),
         checkin.free_text, timestamp.isoformat()),
    )
    if checkin.kind != "morning":
        return

    adjustment = None
    reason = None
    if level in ("caution", "warning"):
        adjustment = "Review today's activity plan with the crew medical officer."
        reason = "The personal baseline rules flagged today's readings."
    elif level == "hold":
        adjustment = "Continue collecting measurements for the personal baseline."
        reason = "Comparable baseline data are incomplete."
    connection.executemany(
        """INSERT INTO guide_item
           (crew_id, mission_day, item_key, target, adjustment, why, progress, done)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (crew_id, mission_day, item_key) DO UPDATE
           SET adjustment = excluded.adjustment, why = excluded.why,
               progress = MAX(guide_item.progress, excluded.progress),
               done = MAX(guide_item.done, excluded.done)""",
        [
            (crew_id, sol, "sleep", "Review last night's sleep", None, None, 1, 1),
            (crew_id, sol, "mood", "Record mood and fatigue", None, None, 1, 1),
            (crew_id, sol, "exercise", "Review today's scheduled activity", adjustment, reason, 0, 0),
        ],
    )
