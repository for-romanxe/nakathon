import os
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator

from backend.mission import mission_sol


class MedicationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    product: str = Field(min_length=1, max_length=160)
    strength: str = Field(min_length=1, max_length=80)
    directions: str = Field(min_length=1, max_length=4000)
    warnings: str = Field(min_length=1, max_length=4000)
    label_revision: str = Field(min_length=1, max_length=100)
    label_url: HttpUrl

    @field_validator("label_url")
    @classmethod
    def require_https(cls, url: HttpUrl) -> HttpUrl:
        if url.scheme != "https" or url.username is not None or url.password is not None:
            raise ValueError("Use an HTTPS product label URL.")
        return url


def load_medication_references() -> list[MedicationReference]:
    path = os.environ.get("CREW_HEALTH_MEDICATION_REFERENCES")
    if not path:
        return []
    references = TypeAdapter(list[MedicationReference]).validate_json(Path(path).read_bytes())
    if len({reference.id for reference in references}) != len(references):
        raise ValueError("Duplicate medication reference ID.")
    return references


class MedicationIntake(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: UUID
    name: str = Field(min_length=1, max_length=120)
    amount: str = Field(min_length=1, max_length=80)


def read_intakes(connection: sqlite3.Connection, crew_id: str) -> list[dict]:
    # The append-only SQLite primary key preserves creation order within a mission timestamp.
    rows = connection.execute(
        """SELECT id, name, amount, ts, mission_day FROM medication_intake
           WHERE crew_id = ? ORDER BY ts DESC, id DESC LIMIT 50""",
        (crew_id,),
    )
    return [dict(row) for row in rows]


def save_intake(
    connection: sqlite3.Connection, crew_id: str, entry: MedicationIntake, timestamp: datetime,
) -> dict | None:
    key = (crew_id, str(entry.request_id))
    connection.execute(
        """INSERT INTO medication_intake (crew_id, request_id, name, amount, ts, mission_day)
           VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (crew_id, request_id) DO NOTHING""",
        (*key, entry.name, entry.amount, timestamp.isoformat(), mission_sol(timestamp)),
    )
    row = connection.execute(
        """SELECT id, name, amount, ts, mission_day FROM medication_intake
           WHERE crew_id = ? AND request_id = ?""",
        key,
    ).fetchone()
    if (row["name"], row["amount"]) != (entry.name, entry.amount):
        return None
    return dict(row)
