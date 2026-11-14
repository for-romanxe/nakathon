BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS event (
    id INTEGER PRIMARY KEY,
    crew_id TEXT NOT NULL REFERENCES crew(id),
    mission_day INTEGER NOT NULL CHECK (mission_day >= 0),
    ts TEXT NOT NULL,
    lang TEXT NOT NULL,
    symptom_text TEXT NOT NULL,
    codes TEXT NOT NULL CHECK (json_valid(codes) AND json_type(codes) = 'array'),
    level TEXT NOT NULL,
    findings TEXT NOT NULL CHECK (json_valid(findings) AND json_type(findings) = 'array')
) STRICT;

CREATE INDEX IF NOT EXISTS event_crew_day ON event (crew_id, mission_day);
PRAGMA user_version = 2;
COMMIT;
