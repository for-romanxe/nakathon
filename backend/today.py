import json
import sqlite3
from statistics import mean, pstdev

from backend.seed import CONTRACT


BASELINE_DAYS = 14
STATUS_TEXT = {
    "normal": "Today's readings are within your baseline.",
    "advisory": "One reading is outside your baseline.",
    "caution": "Some readings are outside your baseline.",
    "warning": "A reading crossed the demo warning threshold.",
    "hold": "There are not enough comparable readings to assess today's status.",
}


def metric_at(days: dict[int, float], sol: int) -> dict:
    history = [days[day] for day in range(sol - BASELINE_DAYS, sol) if day in days]
    value = days.get(sol)
    baseline = mean(history) if len(history) == BASELINE_DAYS else None
    sd = pstdev(history) if baseline is not None else None
    z = (value - baseline) / sd if value is not None and sd else None
    return {"value": value, "baseline": baseline, "sd": sd, "z": z}


def today(connection: sqlite3.Connection, crew_id: str, sol: int) -> dict:
    rows = connection.execute(
        """SELECT metric, mission_day, AVG(value) AS value
           FROM sample WHERE crew_id = ? AND mission_day BETWEEN ? AND ?
             AND value IS NOT NULL
           GROUP BY metric, mission_day""",
        (crew_id, sol - BASELINE_DAYS - 1, sol),
    )
    readings = {metric: {} for metric in CONTRACT["metrics"]}
    for row in rows:
        if row["metric"] in readings:
            readings[row["metric"]][row["mission_day"]] = row["value"]
    metrics = [{"metric": metric, **metric_at(days, sol)} for metric, days in readings.items()]
    advisory_limit, warning_limit = CONTRACT["sensitivity"]["standard"]
    outliers = [metric for metric in metrics if metric["z"] is not None
                and abs(metric["z"]) >= advisory_limit]
    repeated = any(
        abs(metric_at(readings[metric["metric"]], sol - 1)["z"] or 0) >= advisory_limit
        for metric in outliers
    )
    if any(abs(metric["z"]) >= warning_limit for metric in outliers):
        level = "warning"
    elif len(outliers) >= 2 or repeated:
        level = "caution"
    elif outliers:
        level = "advisory"
    elif any(metric["z"] is None for metric in metrics):
        level = "hold"
    else:
        level = "normal"

    checkins = connection.execute(
        "SELECT mission_day, kind FROM checkin WHERE crew_id = ? AND mission_day <= ?",
        (crew_id, sol),
    ).fetchall()
    kinds = {row["kind"] for row in checkins if row["mission_day"] == sol}
    morning_days = {row["mission_day"] for row in checkins if row["kind"] == "morning"}
    streak_day = sol if sol in morning_days else sol - 1
    streak = 0
    while streak_day in morning_days:
        streak += 1
        streak_day -= 1
    guide_rows = connection.execute(
        """SELECT item_key, target, adjustment, why, cites, progress, done FROM guide_item
           WHERE crew_id = ? AND mission_day = ? ORDER BY id""",
        (crew_id, sol),
    )
    guide = []
    for row in guide_rows:
        item = dict(row)
        item["key"] = item.pop("item_key")
        item["cites"] = json.loads(item["cites"])
        item["done"] = bool(item["done"])
        guide.append(item)
    return {
        "status": {"level": level, "text": STATUS_TEXT[level]},
        "guide": guide,
        "metrics": metrics,
        "events": [],
        "checkin": {"morning_done": "morning" in kinds, "evening_done": "evening" in kinds},
        "streak": streak,
    }
