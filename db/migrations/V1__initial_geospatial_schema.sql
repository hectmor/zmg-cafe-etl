CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE meta.pipeline_runs (
    run_id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE TABLE raw.overpass_snapshots (
    run_id UUID PRIMARY KEY REFERENCES meta.pipeline_runs (run_id),
    query TEXT NOT NULL,
    query_hash CHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    snapshot_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE staging.cafe_records (
    record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES meta.pipeline_runs (run_id),
    source TEXT NOT NULL,
    object_type TEXT,
    object_id BIGINT,
    source_id TEXT,
    name TEXT,
    category TEXT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geometry GEOMETRY(Point, 4326),
    geometry_method TEXT,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_updated_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    validation_status TEXT NOT NULL
        CHECK (validation_status IN ('accepted', 'accepted_with_warning', 'rejected')),
    rejection_reason TEXT,
    CONSTRAINT staging_coordinates_are_wgs84 CHECK (
        latitude IS NULL OR (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
    ),
    CONSTRAINT staging_accepted_records_are_complete CHECK (
        (validation_status = 'rejected' AND rejection_reason IS NOT NULL AND geometry IS NULL)
        OR (
            validation_status IN ('accepted', 'accepted_with_warning')
            AND rejection_reason IS NULL
            AND object_type IN ('node', 'way', 'relation')
            AND object_id > 0
            AND source_id = source || ':' || object_type || ':' || object_id
            AND latitude IS NOT NULL
            AND longitude IS NOT NULL
            AND geometry IS NOT NULL
            AND geometry_method IN ('node_coordinates', 'overpass_center')
        )
    ),
    CONSTRAINT staging_run_source_identity UNIQUE (run_id, source_id)
);

CREATE INDEX staging_cafe_records_geometry_idx
    ON staging.cafe_records USING GIST (geometry);

CREATE TABLE analytics.cafes (
    source_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    object_type TEXT NOT NULL CHECK (object_type IN ('node', 'way', 'relation')),
    object_id BIGINT NOT NULL CHECK (object_id > 0),
    name TEXT,
    category TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    geometry GEOMETRY(Point, 4326) NOT NULL,
    geometry_method TEXT NOT NULL CHECK (geometry_method IN ('node_coordinates', 'overpass_center')),
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_updated_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL,
    run_id UUID NOT NULL REFERENCES meta.pipeline_runs (run_id),
    CONSTRAINT analytics_source_identity CHECK (
        source_id = source || ':' || object_type || ':' || object_id
    )
);

CREATE INDEX analytics_cafes_geometry_idx ON analytics.cafes USING GIST (geometry);
