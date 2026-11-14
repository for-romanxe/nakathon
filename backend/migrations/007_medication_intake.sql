BEGIN IMMEDIATE;
CREATE TABLE medication_intake (
    id INTEGER PRIMARY KEY,
    crew_id TEXT NOT NULL REFERENCES crew(id),
    request_id TEXT NOT NULL,
    name TEXT NOT NULL,
    amount TEXT NOT NULL,
    ts TEXT NOT NULL,
    mission_day INTEGER NOT NULL,
    UNIQUE (crew_id, request_id)
);
CREATE INDEX medication_intake_crew_history ON medication_intake (crew_id, ts DESC, id DESC);
PRAGMA user_version = 7;
COMMIT;
