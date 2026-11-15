BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS procedure_approval (
    event_id INTEGER NOT NULL REFERENCES event(id),
    step_id TEXT NOT NULL,
    crew_id TEXT NOT NULL REFERENCES crew(id),
    at TEXT NOT NULL,
    PRIMARY KEY (event_id, step_id, crew_id)
);

CREATE TABLE IF NOT EXISTS earth_report (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL UNIQUE REFERENCES event(id),
    packet_seq INTEGER NOT NULL REFERENCES tx_packet(seq),
    created_at TEXT NOT NULL,
    snapshot TEXT NOT NULL CHECK (json_valid(snapshot))
);

PRAGMA user_version = 10;

COMMIT;
