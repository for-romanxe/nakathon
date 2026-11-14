import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator, model_validator

from backend.mission import mission_sol


PRODUCT_ID = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
CatalogID = Annotated[str, Field(pattern=PRODUCT_ID, max_length=80)]
INTAKE_COLUMNS = "id, name, amount, ts, mission_day, product_id, unit_count"


class IntakeLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_interval_minutes: int = Field(strict=True, gt=0, le=525600)
    maximum_units_24h: int = Field(strict=True, gt=0)


class PairCaution(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product_id: CatalogID
    lookback_minutes: int = Field(strict=True, gt=0, le=525600)
    text: str = Field(min_length=1, max_length=1000)


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
    active_ingredients: set[CatalogID] | None = Field(default=None, min_length=1)
    pair_cautions: list[PairCaution] | None = None

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
    ids = {reference.id for reference in references}
    if len(ids) != len(references):
        raise ValueError("Duplicate medication reference ID.")
    for reference in references:
        targets = [caution.product_id for caution in reference.pair_cautions or []]
        if reference.id in targets or not set(targets) <= ids or len(set(targets)) != len(targets):
            raise ValueError(f"Invalid pair caution targets for {reference.id}.")
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
    references: list[MedicationReference],
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
    review = review_other_products(connection, crew_id, reference, now, review_minutes, references)
    if limits is None:
        comparison = {"status": "hold", "reason": "no_limits"}
    elif row["unmatched_entries"]:
        comparison = {"status": "hold", "reason": "unmatched_entries"}
    elif review["unknown_product_history"]:
        comparison = {"status": "hold", "reason": "unknown_products"}
    elif review["shared_ingredient_in_limit_window"] or review["cautions"]:
        comparison = {"status": "hold", "reason": "other_products"}
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
        "product_review": review,
    }


def review_other_products(
    connection: sqlite3.Connection, crew_id: str, reference: MedicationReference,
    now: datetime, review_minutes: int, references: list[MedicationReference],
) -> dict:
    catalog = {item.id: item for item in references}
    rules_by_product = {}
    for source in references:
        for rule in source.pair_cautions or []:
            if source.id == reference.id:
                other_id = rule.product_id
            elif rule.product_id == reference.id:
                other_id = source.id
            else:
                continue
            rules_by_product.setdefault(other_id, []).append((source, rule))
    longest = max([review_minutes] + [
        rule.lookback_minutes for rules in rules_by_product.values() for _, rule in rules
    ])
    rows = connection.execute(
        """SELECT product_id, MAX(ts) AS latest FROM medication_intake
           WHERE crew_id = ? AND ts > ? AND ts <= ? AND (product_id != ? OR product_id IS NULL)
           GROUP BY product_id ORDER BY product_id""",
        (crew_id, (now - timedelta(minutes=longest)).isoformat(), now.isoformat(), reference.id),
    )
    shared_ingredients = []
    cautions = []
    unknown_product_history = shared_in_limit_window = False
    for row in rows:
        product_id = row["product_id"]
        age = now - datetime.fromisoformat(row["latest"])
        other = catalog.get(product_id)
        if other is None or other.active_ingredients is None or reference.active_ingredients is None:
            unknown_product_history = True
        elif shared := sorted(other.active_ingredients & reference.active_ingredients):
            if age < timedelta(minutes=review_minutes):
                shared_in_limit_window = True
            if age < timedelta(hours=24):
                shared_ingredients.append({"product_id": other.id, "product": other.product, "ingredients": shared})
        for source, rule in rules_by_product.get(product_id, []):
            if age < timedelta(minutes=rule.lookback_minutes):
                cautions.append({
                    "product_id": other.id, "product": other.product, "text": rule.text,
                    "source_product_id": source.id, "label_url": str(source.label_url),
                    "label_revision": source.label_revision,
                })
    return {
        "shared_ingredients": shared_ingredients, "cautions": cautions,
        "unknown_product_history": unknown_product_history,
        "shared_ingredient_in_limit_window": shared_in_limit_window,
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
