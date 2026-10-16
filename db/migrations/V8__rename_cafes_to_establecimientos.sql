-- Issue #62: analytics.cafes is a misleading name now that inegi_denue
-- (SCIAN 722515) covers cafeterías, neverías, refresquerías and similares,
-- not just cafés. Rename only the table; existing constraint/index names
-- that embed "cafes" are left as-is (no functional coupling to the table
-- name, same precedent as V4's comment on keeping constraint names stable
-- across schema changes).
ALTER TABLE analytics.cafes RENAME TO establecimientos;
