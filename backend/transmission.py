import hashlib
import json
import sqlite3
from typing import Literal

from pydantic import BaseModel, ConfigDict, PositiveInt, StrictBool, model_validator


class QueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: PositiveInt | None = None
    daily: StrictBool = False

    @model_validator(mode="after")
    def validate_selection(self) -> "QueueRequest":
        if (self.event_id is not None) == self.daily:
            raise ValueError("Provide either an event ID or daily=true.")
        return self


class DeliveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["acked", "missing"]
    attempt: PositiveInt


def packets(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """SELECT tx_packet.*, COALESCE(tx_packet.crew_id, event.crew_id) AS crew
           FROM tx_packet LEFT JOIN event ON event.id = tx_packet.event_id
           ORDER BY CASE priority WHEN 'warning' THEN 0 WHEN 'caution' THEN 1 ELSE 2 END, seq"""
    )
    return [
        {"seq": row["seq"], "crew": row["crew"], "event_id": row["event_id"],
         "kind": row["kind"], "priority": row["priority"], "hash": row["hash"],
         "status": row["status"], "attempts": row["attempts"], "window_id": row["window_id"],
         "payload": json.loads(row["payload"])}
        for row in rows
    ]


def enqueue_event(connection: sqlite3.Connection, event: sqlite3.Row) -> None:
    summary = {
        "event_id": event["id"], "crew": event["crew_id"], "ts": event["ts"],
        "level": event["level"], "codes": json.loads(event["codes"]),
        "readings": [
            {"metric": metric["metric"], "value": metric["value"]}
            for metric in json.loads(event["findings"])
            if metric.get("level") in ("advisory", "caution", "warning")
        ],
    }
    priority = event["level"] if event["level"] in ("warning", "caution") else "daily"
    _enqueue(connection, "event", event["mission_day"], priority, summary, event_id=event["id"])


def enqueue_daily(connection: sqlite3.Connection, crew_id: str, sol: int, today: dict) -> None:
    summary = {
        "crew": crew_id, "sol": sol, "level": today["status"]["level"],
        "readings": [{"metric": metric["metric"], "value": metric["value"]} for metric in today["metrics"]],
    }
    _enqueue(connection, "daily", sol, "daily", summary, crew_id=crew_id)


def _enqueue(connection, kind, sol, priority, summary, *, event_id=None, crew_id=None) -> None:
    payload = json.dumps(summary, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    connection.execute(
        """INSERT INTO tx_packet (event_id, crew_id, kind, mission_day, priority, payload, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING""",
        (event_id, crew_id, kind, sol, priority, payload, digest),
    )


def dispatch(connection: sqlite3.Connection, window_id: str) -> None:
    connection.execute(
        """UPDATE tx_packet SET status = 'sent', attempts = attempts + 1, window_id = ?
           WHERE status = 'queued' OR (status = 'missing' AND window_id < ?)""",
        (window_id, window_id),
    )


def record_delivery(connection: sqlite3.Connection, seq: int, result: DeliveryResult) -> bool:
    cursor = connection.execute(
        """UPDATE tx_packet SET status = ?
           WHERE seq = ? AND attempts = ?
             AND (status = 'sent' OR (status = 'missing' AND ? = 'acked') OR status = ?)""",
        (result.status, seq, result.attempt, result.status, result.status),
    )
    return cursor.rowcount == 1
