-- Additive migration (issue #58): adds establishment_kind, a HEURISTIC
-- classification of the commercial name into one of 'cafe', 'neveria',
-- 'refresqueria', 'otro'. SCIAN 722515 (DENUE) and amenity=cafe (Overpass)
-- both group these subtypes under one class; establishment_kind is derived
-- by keyword matching on the commercial name in the ETL transform step.
-- It is NOT an official INEGI/OSM attribute and must never be presented as
-- source data (see docs/project-spec.md and issue #58 discussion).

-- staging.cafe_records: nullable, no default. Rejected records (geometry
-- IS NULL) are never classified. Accepted/accepted_with_warning rows get
-- their value from the ETL classifier on each run; rows already in staging
-- before this migration are left NULL rather than guessed, since staging is
-- a per-run audit log, not the served dataset.
ALTER TABLE staging.cafe_records
    ADD COLUMN establishment_kind TEXT
        CHECK (establishment_kind IN ('cafe', 'neveria', 'refresqueria', 'otro'));

COMMENT ON COLUMN staging.cafe_records.establishment_kind IS
    'Heuristic keyword classification of the commercial name (cafe/neveria/'
    'refresqueria/otro). Derived by the ETL, not an official INEGI/OSM field. '
    'NULL for rejected records or rows not yet re-classified.';

-- analytics.cafes: NOT NULL with DEFAULT 'cafe'. This backfills the rows
-- already loaded (4 Overpass records, which are all amenity=cafe by query
-- construction, so 'cafe' is correct, not guessed) without inventing data
-- for any DENUE row, since none is loaded in analytics.cafes yet as of this
-- migration (verified below). The default also acts as a safe fallback for
-- any future insert that omits the column; the ETL loader is expected to
-- always pass an explicit classifier result.
ALTER TABLE analytics.cafes
    ADD COLUMN establishment_kind TEXT NOT NULL DEFAULT 'cafe'
        CHECK (establishment_kind IN ('cafe', 'neveria', 'refresqueria', 'otro'));

COMMENT ON COLUMN analytics.cafes.establishment_kind IS
    'Heuristic keyword classification of the commercial name (cafe/neveria/'
    'refresqueria/otro). Derived by the ETL, not an official INEGI/OSM field. '
    'DEFAULT ''cafe'' backfills pre-migration rows (Overpass amenity=cafe only) '
    'and is a fallback for inserts that omit an explicit classifier result.';
