import sqlite3
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.mission import mission_sol


class MedicationIntake(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: UUID
    name: str = Field(min_length=1, max_length=120)
    amount: str = Field(min_length=1, max_length=80)


def read_intakes(connection: sqlite3.Connection, crew_id: str) -> list[dict]:
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
