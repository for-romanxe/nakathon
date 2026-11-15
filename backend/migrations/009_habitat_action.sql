BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS habitat_action (
    id INTEGER PRIMARY KEY,
    crew_id TEXT NOT NULL REFERENCES crew(id),
    sol INTEGER NOT NULL,
    target TEXT NOT NULL,
    status TEXT NOT NULL,
    auto INTEGER NOT NULL CHECK (auto IN (0, 1)),
    approved_by TEXT,
    applied_at TEXT,
    undone_by TEXT,
    undone_at TEXT,
    undo_reason TEXT CHECK (undo_reason IS NULL OR length(undo_reason) <= 240),
    released_at TEXT,
    data TEXT NOT NULL CHECK (json_valid(data)),
    UNIQUE (crew_id, sol, target)
);
PRAGMA user_version = 9;
COMMIT;
