-- Additive migration (issue #58): adds support for a second source,
-- INEGI DENUE, without touching Overpass/OpenStreetMap behavior or data.
-- DENUE records use a single object_type ('economic_unit', no OSM-style
-- subtypes) and a single geometry_method ('denue_coordinates', direct
-- lat/lon from the DENUE record).

-- raw.denue_snapshots mirrors raw.overpass_snapshots (same columns/types/
-- constraints), one snapshot row per pipeline run, for the DENUE source.
-- raw.overpass_snapshots itself is untouched.
CREATE TABLE raw.denue_snapshots (
    run_id UUID PRIMARY KEY REFERENCES meta.pipeline_runs (run_id),
    query TEXT NOT NULL,
    query_hash CHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    snapshot_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Postgres has no ALTER CHECK; widen existing checks via DROP + ADD,
-- keeping their original names since the logical rule (valid object_type /
-- geometry_method per source) is unchanged, only the allowed value set grows.

ALTER TABLE staging.cafe_records
    DROP CONSTRAINT staging_accepted_records_are_complete;

ALTER TABLE staging.cafe_records
    ADD CONSTRAINT staging_accepted_records_are_complete CHECK (
        (validation_status = 'rejected' AND rejection_reason IS NOT NULL AND geometry IS NULL)
        OR (
            validation_status IN ('accepted', 'accepted_with_warning')
            AND rejection_reason IS NULL
            AND object_type IN ('node', 'way', 'relation', 'economic_unit')
            AND object_id > 0
            AND source_id = source || ':' || object_type || ':' || object_id
            AND latitude IS NOT NULL
            AND longitude IS NOT NULL
            AND geometry IS NOT NULL
            AND geometry_method IN ('node_coordinates', 'overpass_center', 'denue_coordinates')
        )
    );

ALTER TABLE analytics.cafes
    DROP CONSTRAINT cafes_object_type_check;

ALTER TABLE analytics.cafes
    ADD CONSTRAINT cafes_object_type_check
        CHECK (object_type IN ('node', 'way', 'relation', 'economic_unit'));

ALTER TABLE analytics.cafes
    DROP CONSTRAINT cafes_geometry_method_check;

ALTER TABLE analytics.cafes
    ADD CONSTRAINT cafes_geometry_method_check
        CHECK (geometry_method IN ('node_coordinates', 'overpass_center', 'denue_coordinates'));
