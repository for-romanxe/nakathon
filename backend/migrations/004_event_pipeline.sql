BEGIN IMMEDIATE;

ALTER TABLE event ADD COLUMN urgent INTEGER CHECK (urgent IN (0, 1));
ALTER TABLE event ADD COLUMN pipeline TEXT CHECK (json_valid(pipeline) AND json_type(pipeline) = 'object');

PRAGMA user_version = 4;
COMMIT;
