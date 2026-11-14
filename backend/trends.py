import sqlite3

from backend.events import event_payload
from backend.today import BASELINE_DAYS, metric_at


def trends(connection: sqlite3.Connection, crew_id: str, metric: str, days: int, sol: int) -> dict:
    chart_start = max(0, sol - days + 1)
    history_start = min(chart_start, sol - BASELINE_DAYS)
    params = (crew_id, history_start, sol)
    readings = connection.execute(
        """SELECT mission_day, MIN(ts) AS ts, AVG(value) AS value
           FROM sample WHERE crew_id = ? AND mission_day BETWEEN ? AND ?
             AND metric = ? AND value IS NOT NULL
           GROUP BY mission_day ORDER BY mission_day""",
        (*params, metric),
    ).fetchall()
    events = connection.execute(
        """SELECT * FROM event WHERE crew_id = ? AND mission_day BETWEEN ? AND ?
           ORDER BY mission_day, id""",
        params,
    ).fetchall()
    current = metric_at(
        {row["mission_day"]: row["value"] for row in readings},
        sol,
        frozenset(row["mission_day"] for row in events),
    )
    preflight = connection.execute(
        "SELECT value, source FROM preflight_baseline WHERE crew_id = ? AND metric = ?",
        (crew_id, metric),
    ).fetchone()
    return {
        "points": [{"ts": row["ts"], "value": row["value"]}
                   for row in readings if row["mission_day"] >= chart_start],
        "baseline": {"mean": current["baseline"], "sd": current["sd"]},
        "preflight": dict(preflight) if preflight is not None else None,
        "events": [event_payload(row) for row in events if row["mission_day"] >= chart_start],
    }
