-- Additive migration (issue #58): adds ubicacion, areageo and clee, three
-- OFFICIAL raw fields copied verbatim from each INEGI DENUE record (source
-- fields `Ubicacion`, `AreaGeo`, `CLEE`). Unlike establishment_kind (a
-- heuristic classification of the commercial name, see V5), these are NOT
-- derived/guessed/parsed by the ETL: they are stored exactly as INEGI
-- returns them, free text/codes with no fixed category set, so (unlike
-- municipio in V6) no CHECK ... IN (...) enum applies here.
--
-- OpenStreetMap/Overpass provides none of the three, so they are always
-- NULL for openstreetmap records, same as municipio.
--
-- No length/format CHECK on clee: a single confirmed real sample
-- ("14039722219022291020003311S4") is 28 characters, but that is not
-- enough to be sure of INEGI's exact fixed format (publicly documented CLEE
-- lengths for DENUE vary across sources/versions). Inventing a strict rule
-- from one example risks rejecting valid future records, so the constraint
-- is intentionally omitted; revisit if an authoritative INEGI spec for CLEE
-- is confirmed.

-- staging.cafe_records: nullable, no default, no backfill — same reasoning
-- as municipio (V6): staging is a per-run audit log, and rows loaded before
-- this migration/before the ETL change never actually had these values
-- recorded for them.
ALTER TABLE staging.cafe_records
    ADD COLUMN ubicacion TEXT,
    ADD COLUMN areageo TEXT,
    ADD COLUMN clee TEXT;

COMMENT ON COLUMN staging.cafe_records.ubicacion IS
    'Official raw INEGI DENUE field `Ubicacion` (locality, municipality, '
    'state as free text), copied verbatim, not parsed or inferred. Always '
    'NULL for openstreetmap records (Overpass does not provide it) and '
    'NULL for rows loaded before this attribute existed.';

COMMENT ON COLUMN staging.cafe_records.areageo IS
    'Official raw INEGI DENUE field `AreaGeo` (INEGI geostatistical area '
    'code), copied verbatim. Always NULL for openstreetmap records and '
    'NULL for rows loaded before this attribute existed.';

COMMENT ON COLUMN staging.cafe_records.clee IS
    'Official raw INEGI DENUE field `CLEE` (unique establishment '
    'geo-code), copied verbatim. No length/format CHECK: INEGI''s exact '
    'fixed format is not confirmed with certainty from a single sample '
    '(see migration header). Always NULL for openstreetmap records and '
    'NULL for rows loaded before this attribute existed.';

-- analytics.cafes: same columns, same nullable/no-default/no-backfill
-- reasoning as municipio in V6.
ALTER TABLE analytics.cafes
    ADD COLUMN ubicacion TEXT,
    ADD COLUMN areageo TEXT,
    ADD COLUMN clee TEXT;

COMMENT ON COLUMN analytics.cafes.ubicacion IS
    'Official raw INEGI DENUE field `Ubicacion` (locality, municipality, '
    'state as free text), copied verbatim, not parsed or inferred. Always '
    'NULL for openstreetmap records and NULL until a reload repopulates it '
    'for DENUE rows.';

COMMENT ON COLUMN analytics.cafes.areageo IS
    'Official raw INEGI DENUE field `AreaGeo` (INEGI geostatistical area '
    'code), copied verbatim. Always NULL for openstreetmap records and '
    'NULL until a reload repopulates it for DENUE rows.';

COMMENT ON COLUMN analytics.cafes.clee IS
    'Official raw INEGI DENUE field `CLEE` (unique establishment '
    'geo-code), copied verbatim. No length/format CHECK: INEGI''s exact '
    'fixed format is not confirmed with certainty from a single sample '
    '(see migration header). Always NULL for openstreetmap records and '
    'NULL until a reload repopulates it for DENUE rows.';
