BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS crew (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    cmo INTEGER NOT NULL DEFAULT 0 CHECK (cmo IN (0, 1)),
    cmo_view_enabled INTEGER NOT NULL DEFAULT 1 CHECK (cmo_view_enabled IN (0, 1))
) STRICT;

CREATE TABLE IF NOT EXISTS sample (
    id INTEGER PRIMARY KEY,
    crew_id TEXT NOT NULL REFERENCES crew(id),
    metric TEXT NOT NULL,
    ts TEXT NOT NULL,
    mission_day INTEGER NOT NULL CHECK (mission_day >= 0),
    value REAL,
    source TEXT NOT NULL,
    source_key TEXT,
    UNIQUE (source, source_key)
) STRICT;

CREATE INDEX IF NOT EXISTS sample_crew_metric_ts ON sample (crew_id, metric, ts);

CREATE TABLE IF NOT EXISTS preflight_baseline (
    crew_id TEXT NOT NULL REFERENCES crew(id),
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    source TEXT NOT NULL,
    PRIMARY KEY (crew_id, metric)
) STRICT;

CREATE TABLE IF NOT EXISTS checkin (
    id INTEGER PRIMARY KEY,
    crew_id TEXT NOT NULL REFERENCES crew(id),
    mission_day INTEGER NOT NULL CHECK (mission_day >= 0),
    kind TEXT NOT NULL CHECK (kind IN ('morning', 'evening', 'weekly', 'monthly', 'quarterly')),
    answers TEXT NOT NULL CHECK (json_valid(answers) AND json_type(answers) = 'object'),
    free_text TEXT,
    derived TEXT CHECK (derived IS NULL OR (json_valid(derived) AND json_type(derived) = 'object')),
    at TEXT NOT NULL,
    UNIQUE (crew_id, mission_day, kind)
) STRICT;

CREATE TABLE IF NOT EXISTS guide_item (
    id INTEGER PRIMARY KEY,
    crew_id TEXT NOT NULL REFERENCES crew(id),
    mission_day INTEGER NOT NULL CHECK (mission_day >= 0),
    item_key TEXT NOT NULL,
    target TEXT,
    adjustment TEXT,
    why TEXT,
    cites TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(cites) AND json_type(cites) = 'array'),
    progress REAL NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 1),
    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
    UNIQUE (crew_id, mission_day, item_key)
) STRICT;

PRAGMA application_id = 1129465160;
PRAGMA user_version = 1;
COMMIT;
