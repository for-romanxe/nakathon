BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS tx_packet (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER UNIQUE REFERENCES event(id),
    crew_id TEXT REFERENCES crew(id),
    kind TEXT NOT NULL CHECK (kind IN ('event', 'daily')),
    mission_day INTEGER NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('warning', 'caution', 'daily')),
    payload TEXT NOT NULL CHECK (json_valid(payload)),
    hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'acked', 'missing')),
    attempts INTEGER NOT NULL DEFAULT 0,
    window_id TEXT,
    UNIQUE (kind, mission_day, crew_id),
    CHECK ((kind = 'event' AND event_id IS NOT NULL AND crew_id IS NULL)
        OR (kind = 'daily' AND event_id IS NULL AND crew_id IS NOT NULL))
) STRICT;

PRAGMA user_version = 3;
COMMIT;
