"""Preflight baseline values entered manually by crew members.

Values are validated for shape only (known metric, finite, nonnegative number).
No medical thresholds are applied here. The caller manages the transaction.
"""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.seed import CONTRACT


class PreflightUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]]

    @field_validator("values")
    @classmethod
    def check_metrics(cls, values):
        if not values:
            raise ValueError("Provide at least one preflight value.")
        if values.keys() - CONTRACT["metrics"].keys():
            raise ValueError("Unknown preflight metric.")
        return values


def read_preflight(db, crew_id):
    rows = db.execute(
        "SELECT metric, value, source FROM preflight_baseline WHERE crew_id = ?",
        (crew_id,),
    ).fetchall()
    return {"values": {row[0]: {"value": row[1], "source": row[2]} for row in rows}}


def save_preflight(db, crew_id, update):
    for metric, value in update.values.items():
        db.execute(
            "INSERT INTO preflight_baseline (crew_id, metric, value, source) "
            "VALUES (?, ?, ?, 'manual') "
            "ON CONFLICT(crew_id, metric) DO UPDATE SET "
            "value = excluded.value, source = 'manual'",
            (crew_id, metric, value),
        )
    return read_preflight(db, crew_id)
