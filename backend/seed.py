import argparse
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean, pstdev

from backend.db import connect, initialize


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "contracts/enums.json").read_text(encoding="utf-8"))
DEMO_DB = ROOT / "data/crew-health.sqlite3"
DEMO_SOL = 16
MISSION_START = datetime(2026, 10, 30, tzinfo=UTC)
SOURCE = "synthetic_scenario"
CREW = (
    ("c1", "C1", "Flight engineer", 0),
    ("c2", "C2", "Commander", 1),
    ("c3", "C3", "Scientist", 0),
    ("c4", "C4", "Pilot", 0),
)
METRIC_SEEDS = {
    "hr": (68, 2),
    "hrv": (52, 3),
    "eda": (2, 0.2),
    "temp": (33, 0.2),
    "sleep": (7.5, 0.3),
    "act": (150, 8),
}
HISTORICAL_OFFSETS = {
    "hr": (-2, -2, -1, 0, 1, 2, 2, 1, 0, -1, -2, -1, 0, 1, 1),
    "hrv": (0, 1, -2, -1, 1, 2, 1, 2, 0, -2, -1, -2, 0, 1, 2),
    "eda": (-1, -1, 0, 3, 0, -1, -1, 0, 2, 0, -1, 1, 3, 1, 0),
    "temp": (-2, -2, -1, -1, 0, 0, 1, 2, 1, 0, -1, 0, 1, 1, 2),
    "sleep": (2, 1, 0, -1, -2, 1, 2, 0, -2, -2, -1, 1, 2, 2, 0),
    "act": (0, 2, 1, 0, -2, -2, 0, 1, 2, 3, 0, -2, -1, 1, 3),
}
DEVIATIONS = {"c1": {"hr": 2.5, "hrv": -2.5}, "c4": {"hr": 2.5}}


def seed(connection: sqlite3.Connection) -> None:
    with connection:
        connection.executemany(
            """INSERT INTO crew (id, name, role, cmo) VALUES (?, ?, ?, ?)
               ON CONFLICT (id) DO NOTHING""",
            CREW,
        )
        for crew_index, (crew_id, name, _, _) in enumerate(CREW):
            connection.execute(
                "UPDATE crew SET name = ? WHERE id = ? AND name = ?",
                (name, crew_id, f"Crew {chr(ord('A') + crew_index)}"),
            )
            first_sol = DEMO_SOL - 9 if crew_id == "c3" else 1
            for metric in CONTRACT["metrics"]:
                center, spread = METRIC_SEEDS[metric]
                center += crew_index * spread
                offsets = HISTORICAL_OFFSETS[metric]
                # Normalize sols 2–15 to preserve the final-sol alert scenarios.
                baseline_mean = mean(offsets[1:])
                baseline_sd = pstdev(offsets[1:])
                connection.execute(
                    """INSERT INTO preflight_baseline (crew_id, metric, value, source)
                       VALUES (?, ?, ?, ?) ON CONFLICT (crew_id, metric) DO NOTHING""",
                    (crew_id, metric, center, SOURCE),
                )
                for sol in range(first_sol, DEMO_SOL + 1):
                    ts = MISSION_START + timedelta(days=sol - 1, hours=6)
                    if sol == DEMO_SOL:
                        deviation = DEVIATIONS.get(crew_id, {}).get(metric, 0)
                    else:
                        deviation = (offsets[sol - 1] - baseline_mean) / baseline_sd
                    connection.execute(
                        """INSERT INTO sample
                           (crew_id, metric, ts, mission_day, value, source, source_key)
                           VALUES (?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT (source, source_key) DO NOTHING""",
                        (crew_id, metric, ts.isoformat(), sol, round(center + spread * deviation, 4),
                         SOURCE, f"{crew_id}:{metric}:{sol}"),
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the Crew Health synthetic scenario.")
    parser.add_argument("db_path", type=Path, nargs="?", default=DEMO_DB)
    args = parser.parse_args()
    initialize(args.db_path)
    with closing(connect(args.db_path)) as connection:
        seed(connection)
    print(f"Crew Health scenario loaded at {args.db_path}")
