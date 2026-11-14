BEGIN IMMEDIATE;
ALTER TABLE medication_intake ADD COLUMN product_id TEXT;
ALTER TABLE medication_intake ADD COLUMN unit_count INTEGER
    CHECK ((product_id IS NULL AND unit_count IS NULL)
        OR (product_id IS NOT NULL AND typeof(unit_count) = 'integer' AND unit_count BETWEEN 1 AND 1000000));
PRAGMA user_version = 8;
COMMIT;
