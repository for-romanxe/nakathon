import argparse
import json
import os
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

# Issue 47 mission demo.
MISSION_DEMO_SCENES = (16, 17, 40, 46, 57)
BASELINE_WINDOW = 14
C1_SOL16_SLEEP = 5.1
# Opt-in demo only: widen C1 sleep history so Sol16 reads as z ~ -2.5 rather than -8.
# Existing rehearsal DBs are never rewritten; generate a fresh one with --mission-demo.
C1_DEMO_SLEEP_SD = 0.96
C1_SOL17_SLEEP = 7.2
C1_SOL17_HRV_Z = -0.6
C4_DEMO_SOL = 46
# Static scenario input for BE-04; intentionally not written as a guide_item row.
HYPOTHETICAL_EVA_ASSIGNMENT = {
    "crew_id": "c1",
    "mission_day": 16,
    "activity": "eva",
    "hypothetical": True,
}


def _profile(crew_id: str, metric: str) -> tuple[float, float, tuple, float, float]:
    crew_index = next(i for i, crew in enumerate(CREW) if crew[0] == crew_id)
    center, spread = METRIC_SEEDS[metric]
    offsets = HISTORICAL_OFFSETS[metric]
    # Normalize sols 2–15 to preserve the final-sol alert scenarios.
    return center + crew_index * spread, spread, offsets, mean(offsets[1:]), pstdev(offsets[1:])


def _insert_sample(connection: sqlite3.Connection, crew_id: str, metric: str, sol: int, value: float) -> None:
    ts = MISSION_START + timedelta(days=sol - 1, hours=6)
    connection.execute(
        """INSERT INTO sample
           (crew_id, metric, ts, mission_day, value, source, source_key)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (source, source_key) DO NOTHING""",
        (crew_id, metric, ts.isoformat(), sol, round(value, 4), SOURCE, f"{crew_id}:{metric}:{sol}"),
    )


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
                center, spread, offsets, baseline_mean, baseline_sd = _profile(crew_id, metric)
                connection.execute(
                    """INSERT INTO preflight_baseline (crew_id, metric, value, source)
                       VALUES (?, ?, ?, ?) ON CONFLICT (crew_id, metric) DO NOTHING""",
                    (crew_id, metric, center, SOURCE),
                )
                for sol in range(first_sol, DEMO_SOL + 1):
                    if sol == DEMO_SOL:
                        deviation = DEVIATIONS.get(crew_id, {}).get(metric, 0)
                    else:
                        deviation = (offsets[sol - 1] - baseline_mean) / baseline_sd
                    _insert_sample(connection, crew_id, metric, sol, center + spread * deviation)


def _default_value(crew_id: str, metric: str, sol: int, spread_override: float | None = None) -> float:
    center, spread, offsets, baseline_mean, baseline_sd = _profile(crew_id, metric)
    if spread_override is not None:
        spread = spread_override
    if sol == DEMO_SOL:
        deviation = DEVIATIONS.get(crew_id, {}).get(metric, 0)
    else:
        deviation = (offsets[sol - 1] - baseline_mean) / baseline_sd
    return center + spread * deviation


def seed_mission_demo(connection: sqlite3.Connection) -> None:
    """Insert demo overrides first; default seed and app startup then keep them via DO NOTHING."""
    with connection:
        connection.executemany(
            """INSERT INTO crew (id, name, role, cmo) VALUES (?, ?, ?, ?)
               ON CONFLICT (id) DO NOTHING""",
            CREW,
        )
        for sol in range(1, DEMO_SOL):
            _insert_sample(connection, "c1", "sleep", sol,
                           _default_value("c1", "sleep", sol, spread_override=C1_DEMO_SLEEP_SD))
        _insert_sample(connection, "c1", "sleep", DEMO_SOL, C1_SOL16_SLEEP)
        for metric in CONTRACT["metrics"]:
            center, spread, offsets, baseline_mean, baseline_sd = _profile("c1", metric)
            if metric == "sleep":
                value = C1_SOL17_SLEEP
            elif metric == "hrv":
                prior = [_default_value("c1", metric, sol) for sol in range(17 - BASELINE_WINDOW, 17)]
                value = mean(prior) + C1_SOL17_HRV_Z * pstdev(prior)
            else:
                value = center + spread * (offsets[0] - baseline_mean) / baseline_sd
            _insert_sample(connection, "c1", metric, 17, value)

            center, spread, offsets, baseline_mean, baseline_sd = _profile("c4", metric)
            first = C4_DEMO_SOL - BASELINE_WINDOW
            for sol in range(first, C4_DEMO_SOL + 1):
                index = 0 if sol == C4_DEMO_SOL else sol - first + 1
                _insert_sample(
                    connection, "c4", metric, sol,
                    center + spread * (offsets[index] - baseline_mean) / baseline_sd,
                )
    seed(connection)


def _create_mission_demo(db_path: Path) -> None:
    # Refuse an occupied target or SQLite sidecar before creating any parent
    # directory. lexists also catches directories and dangling symlinks.
    sidecars = (Path(f"{db_path}{suffix}") for suffix in ("-journal", "-wal", "-shm"))
    for path in (db_path, *sidecars):
        if os.path.lexists(path):
            raise FileExistsError(str(path))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # O_EXCL still rejects a path created after the check. It runs before the
    # try block, so a failed create never reaches the cleanup below. Cleanup
    # only removes the file this call created.
    fd = os.open(db_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    os.close(fd)
    try:
        initialize(db_path)
        with closing(connect(db_path)) as connection:
            seed_mission_demo(connection)
    except BaseException:
        try:
            db_path.unlink()
        except OSError:
            pass
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load the Crew Health synthetic scenario.")
    parser.add_argument("db_path", type=Path, nargs="?", default=None)
    parser.add_argument("--mission-demo", action="store_true",
                        help="Create a fresh DB (explicit path required) with the Issue 47 mission demo.")
    args = parser.parse_args()
    if args.mission_demo:
        if args.db_path is None:
            parser.error("--mission-demo requires an explicit fresh db_path")
        try:
            _create_mission_demo(args.db_path)
        except FileExistsError as exc:
            parser.error(f"refusing to overwrite existing path: {exc.filename or exc}")
        print(f"Crew Health mission demo loaded at {args.db_path}")
    else:
        db_path = args.db_path if args.db_path is not None else DEMO_DB
        initialize(db_path)
        with closing(connect(db_path)) as connection:
            seed(connection)
        print(f"Crew Health scenario loaded at {db_path}")
