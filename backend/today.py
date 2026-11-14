import json
import sqlite3
from statistics import mean, pstdev

from backend.events import event_payload
from backend.seed import CONTRACT


BASELINE_DAYS = 14
STATUS_TEXT = {
    "normal": "Today's readings are within your baseline.",
    "advisory": "One reading is outside your baseline.",
    "caution": "Some readings are outside your baseline.",
    "warning": "The demo rules flagged a reading or reported symptom.",
    "hold": "There are not enough comparable readings to assess today's status.",
}
STATUS_TEXT_KO = {
    "normal": "오늘 측정값은 개인 기준 범위 안에 있어요.",
    "advisory": "한 지표가 개인 기준 범위를 벗어났어요.",
    "caution": "개인 기준 범위를 벗어난 지표를 확인해 주세요.",
    "warning": "시연 규칙이 측정값 또는 보고된 증상에 경보를 표시했어요.",
    "hold": "오늘 상태를 판단하기에 비교 가능한 기록이 부족해요.",
}
HOLD_TEXT = {
    "insufficient_baseline": ("The 14-day baseline is incomplete.", "14일 기준선 기록이 부족해요."),
    "zero_variance": ("The baseline readings did not vary.", "기준선 측정값에 변화가 없어요."),
    "missing_reading": ("Today's reading is missing.", "오늘 측정값이 없어요."),
}


def metric_at(days: dict[int, float], sol: int, excluded_days: frozenset[int] = frozenset()) -> dict:
    history = [
        days[day] for day in range(sol - BASELINE_DAYS, sol)
        if day in days and day not in excluded_days
    ]
    value = days.get(sol)
    baseline = mean(history) if len(history) == BASELINE_DAYS else None
    sd = pstdev(history) if baseline is not None else None
    z = (value - baseline) / sd if value is not None and sd else None
    hold_reason = None
    if baseline is None:
        hold_reason = "insufficient_baseline"
    elif value is None:
        hold_reason = "missing_reading"
    elif sd == 0:
        hold_reason = "zero_variance"
    return {"value": value, "baseline": baseline, "sd": sd, "z": z, "hold_reason": hold_reason}


def today(connection: sqlite3.Connection, crew_id: str, sol: int, lang: str = "en") -> dict:
    event_rows = connection.execute(
        """SELECT * FROM event WHERE crew_id = ? AND mission_day BETWEEN ? AND ?
           ORDER BY id DESC""",
        (crew_id, sol - BASELINE_DAYS - 1, sol),
    ).fetchall()
    excluded_days = frozenset(row["mission_day"] for row in event_rows)
    events = [event_payload(row) for row in event_rows if row["mission_day"] == sol]
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
    metrics = [
        {"metric": metric, **metric_at(days, sol, excluded_days)}
        for metric, days in readings.items()
    ]
    advisory_limit, warning_limit = CONTRACT["sensitivity"]["standard"]
    outliers = [metric for metric in metrics if metric["z"] is not None
                and abs(metric["z"]) >= advisory_limit]
    repeated = set()
    for metric in outliers:
        previous = metric_at(readings[metric["metric"]], sol - 1, excluded_days)["z"]
        if previous is not None and abs(previous) >= advisory_limit:
            repeated.add(metric["metric"])
    for metric in metrics:
        z = metric["z"]
        if z is None:
            metric["level"] = "hold"
        elif abs(z) >= warning_limit:
            metric["level"] = "warning"
        elif abs(z) < advisory_limit:
            metric["level"] = "normal"
        elif len(outliers) >= 2 or metric["metric"] in repeated:
            metric["level"] = "caution"
        else:
            metric["level"] = "advisory"
    event_levels = {event["level"] for event in events}
    if "warning" in event_levels or any(abs(metric["z"]) >= warning_limit for metric in outliers):
        level = "warning"
    elif "caution" in event_levels or len(outliers) >= 2 or repeated:
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
    status_text = (STATUS_TEXT_KO if lang == "ko" else STATUS_TEXT)[level]
    if level == "hold":
        reasons = {metric["hold_reason"] for metric in metrics}
        language = 1 if lang == "ko" else 0
        status_text = " ".join(messages[language] for reason, messages in HOLD_TEXT.items() if reason in reasons)
    return {
        "status": {"level": level, "text": status_text},
        "guide": guide,
        "metrics": metrics,
        "events": events,
        "checkin": {"morning_done": "morning" in kinds, "evening_done": "evening" in kinds},
        "streak": streak,
    }
