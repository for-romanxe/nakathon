import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator, model_validator

from backend.mission import mission_sol


PRODUCT_ID = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
INTAKE_COLUMNS = "id, name, amount, ts, mission_day, product_id, unit_count"


class IntakeLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_interval_minutes: int = Field(strict=True, gt=0, le=525600)
    maximum_units_24h: int = Field(strict=True, gt=0)


class MedicationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(pattern=PRODUCT_ID, max_length=80)
    product: str = Field(min_length=1, max_length=160)
    strength: str = Field(min_length=1, max_length=80)
    directions: str = Field(min_length=1, max_length=4000)
    warnings: str = Field(min_length=1, max_length=4000)
    label_revision: str = Field(min_length=1, max_length=100)
    label_url: HttpUrl
    count_unit: str | None = Field(default=None, min_length=1, max_length=30)
    intake_limits: IntakeLimits | None = None

    @model_validator(mode="after")
    def require_count_unit_for_limits(self) -> "MedicationReference":
        if self.intake_limits is not None and self.count_unit is None:
            raise ValueError("Intake limits require a configured count unit.")
        return self

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


class ProductIntake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    product_id: str = Field(pattern=PRODUCT_ID, max_length=80)
    unit_count: int = Field(strict=True, gt=0, le=1_000_000)


def read_intakes(connection: sqlite3.Connection, crew_id: str) -> list[dict]:
    # The append-only SQLite primary key preserves creation order within a mission timestamp.
    rows = connection.execute(
        f"""SELECT {INTAKE_COLUMNS} FROM medication_intake
           WHERE crew_id = ? ORDER BY ts DESC, id DESC LIMIT 50""",
        (crew_id,),
    )
    return [dict(row) for row in rows]


def intake_summary(
    connection: sqlite3.Connection, crew_id: str, reference: MedicationReference, now: datetime,
) -> dict:
    limits = reference.intake_limits
    cutoff = (now - timedelta(hours=24)).isoformat()
    review_minutes = max(1440, limits.minimum_interval_minutes) if limits else 1440
    review_cutoff = (now - timedelta(minutes=review_minutes)).isoformat()
    row = connection.execute(
        """SELECT MAX(CASE WHEN product_id = :product THEN ts END) AS last_intake_at,
                  COALESCE(SUM(CASE WHEN product_id = :product AND ts > :cutoff THEN unit_count END), 0)
                      AS recorded_units_24h,
                  COUNT(CASE WHEN product_id IS NULL AND ts > :cutoff THEN 1 END) AS text_entries_24h,
                  COUNT(CASE WHEN product_id IS NULL AND ts > :review_cutoff THEN 1 END) AS unmatched_entries
           FROM medication_intake
           WHERE crew_id = :crew AND ts <= :now AND (product_id = :product OR product_id IS NULL)""",
        {"crew": crew_id, "product": reference.id, "cutoff": cutoff, "review_cutoff": review_cutoff,
         "now": now.isoformat()},
    ).fetchone()
    last = row["last_intake_at"]
    elapsed = None if last is None else int((now - datetime.fromisoformat(last)).total_seconds() // 60)
    if limits is None:
        comparison = {"status": "hold", "reason": "no_limits"}
    elif row["unmatched_entries"]:
        comparison = {"status": "hold", "reason": "unmatched_entries"}
    else:
        comparison = {
            "status": "compared",
            "minutes_below_minimum_interval": None if elapsed is None else max(0, limits.minimum_interval_minutes - elapsed),
            "units_below_24h_limit": max(0, limits.maximum_units_24h - row["recorded_units_24h"]),
            "exceeds_24h_limit": row["recorded_units_24h"] > limits.maximum_units_24h,
        }
    return {
        "product_id": reference.id, "last_intake_at": last, "minutes_since_last": elapsed,
        "recorded_units_24h": row["recorded_units_24h"], "text_entries_24h": row["text_entries_24h"],
        "limit_comparison": comparison,
    }


def save_intake(
    connection: sqlite3.Connection, crew_id: str, entry: MedicationIntake | ProductIntake,
    timestamp: datetime, references: list[MedicationReference],
) -> dict | None:
    key = (crew_id, str(entry.request_id))
    row = connection.execute(
        f"""SELECT {INTAKE_COLUMNS} FROM medication_intake
           WHERE crew_id = ? AND request_id = ?""",
        key,
    ).fetchone()
    if row is not None:
        if isinstance(entry, ProductIntake):
            matches = (row["product_id"], row["unit_count"]) == (entry.product_id, entry.unit_count)
        else:
            matches = row["product_id"] is None and (row["name"], row["amount"]) == (entry.name, entry.amount)
        return dict(row) if matches else None

    if isinstance(entry, ProductIntake):
        reference = next((row for row in references if row.id == entry.product_id), None)
        if reference is None or reference.count_unit is None:
            raise ValueError("This product has no configured count unit.")
        product_id, unit_count = entry.product_id, entry.unit_count
        name = f"{reference.product} · {reference.strength}"
        amount = f"{unit_count} × {reference.count_unit}"
    else:
        product_id, unit_count = None, None
        name, amount = entry.name, entry.amount

    row = connection.execute(
        f"""INSERT INTO medication_intake (crew_id, request_id, name, amount, ts, mission_day, product_id, unit_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING {INTAKE_COLUMNS}""",
        (*key, name, amount, timestamp.isoformat(), mission_sol(timestamp), product_id, unit_count),
    ).fetchone()
    return dict(row)
