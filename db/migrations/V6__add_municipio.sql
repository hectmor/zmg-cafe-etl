-- Additive migration (issue #58): adds municipio, the official ZMG
-- municipality for a record. Unlike establishment_kind (a heuristic keyword
-- classification of the commercial name, see V5), municipio is NOT guessed
-- from free text: INEGI DENUE is queried per municipality (entidad +
-- municipio in config/sources.yaml), so each DENUE record is tagged with
-- the exact municipality name of the query that returned it. OpenStreetMap/
-- Overpass does not provide this attribute at all, so it is always NULL for
-- openstreetmap records.

-- staging.cafe_records: nullable, no default. Existing rows (both
-- openstreetmap and inegi_denue, loaded before this migration/before the
-- ETL municipio labeling lands) are left NULL rather than backfilled,
-- since staging is a per-run audit log and municipio was never actually
-- recorded for them. A future reload with the updated ETL will populate it
-- for DENUE rows going forward.
ALTER TABLE staging.cafe_records
    ADD COLUMN municipio TEXT
        CHECK (
            municipio IS NULL OR municipio IN (
                'Guadalajara',
                'Zapopan',
                'Tlaquepaque',
                'Tonalá',
                'Tlajomulco de Zúñiga',
                'El Salto',
                'Juanacatlán',
                'Ixtlahuacán de los Membrillos',
                'Zapotlanejo'
            )
        );

COMMENT ON COLUMN staging.cafe_records.municipio IS
    'Official ZMG municipality from the INEGI DENUE query (entidad+municipio '
    'in config/sources.yaml) that returned the record. NOT inferred from '
    'free text. Always NULL for openstreetmap records (Overpass does not '
    'provide it) and NULL for rows loaded before this attribute existed.';

-- analytics.cafes: same column/constraint, also nullable with no default
-- and no backfill, for the same reason (OpenStreetMap rows never had this
-- data, and existing DENUE rows were loaded before the ETL tagged it).
ALTER TABLE analytics.cafes
    ADD COLUMN municipio TEXT
        CHECK (
            municipio IS NULL OR municipio IN (
                'Guadalajara',
                'Zapopan',
                'Tlaquepaque',
                'Tonalá',
                'Tlajomulco de Zúñiga',
                'El Salto',
                'Juanacatlán',
                'Ixtlahuacán de los Membrillos',
                'Zapotlanejo'
            )
        );

COMMENT ON COLUMN analytics.cafes.municipio IS
    'Official ZMG municipality from the INEGI DENUE query (entidad+municipio '
    'in config/sources.yaml) that returned the record. NOT inferred from '
    'free text. Always NULL for openstreetmap records (Overpass does not '
    'provide it) and NULL until a reload repopulates it for DENUE rows.';
