import argparse
import sqlite3
from contextlib import closing
from pathlib import Path


INITIAL_SCHEMA = Path(__file__).with_name("migrations") / "001_initial.sql"
EVENT_SCHEMA = INITIAL_SCHEMA.with_name("002_events.sql")
TRANSMISSION_SCHEMA = INITIAL_SCHEMA.with_name("003_transmission.sql")
PIPELINE_SCHEMA = INITIAL_SCHEMA.with_name("004_event_pipeline.sql")
RESPONSE_SCHEMA = INITIAL_SCHEMA.with_name("005_event_response.sql")
VISIBILITY_SCHEMA = INITIAL_SCHEMA.with_name("006_crew_visibility.sql")
MEDICATION_SCHEMA = INITIAL_SCHEMA.with_name("007_medication_intake.sql")
CREW_HEALTH_APPLICATION_ID = 1129465160


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(db_path: str | Path) -> None:
    with closing(connect(db_path)) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        if application_id == 0 and version == 0:
            populated = connection.execute(
                "SELECT 1 FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
            ).fetchone()
            if populated:
                raise ValueError("Choose a new database or an initialized Crew Health database.")
            connection.executescript(INITIAL_SCHEMA.read_text(encoding="utf-8"))
            version = 1
        elif application_id != CREW_HEALTH_APPLICATION_ID or not 1 <= version <= 7:
            raise ValueError("Choose a new database or an initialized Crew Health database.")
        if version == 1:
            connection.executescript(EVENT_SCHEMA.read_text(encoding="utf-8"))
        if version < 3:
            connection.executescript(TRANSMISSION_SCHEMA.read_text(encoding="utf-8"))
        if version < 4:
            connection.executescript(PIPELINE_SCHEMA.read_text(encoding="utf-8"))
        if version < 5:
            connection.executescript(RESPONSE_SCHEMA.read_text(encoding="utf-8"))
        if version < 6:
            connection.executescript(VISIBILITY_SCHEMA.read_text(encoding="utf-8"))
        if version < 7:
            connection.executescript(MEDICATION_SCHEMA.read_text(encoding="utf-8"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the Crew Health SQLite database.")
    parser.add_argument("db_path", type=Path)
    args = parser.parse_args()
    try:
        initialize(args.db_path)
    except (ValueError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")
    print(f"Crew Health database ready at {args.db_path}")
