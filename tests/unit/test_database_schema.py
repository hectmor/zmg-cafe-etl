from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]
MIGRATION_PATH = ROOT / "db/migrations/V1__initial_geospatial_schema.sql"


def test_compose_defines_postgis_and_flyway_migration_service() -> None:
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))

    assert compose["services"]["db"]["image"] == "postgis/postgis:17-3.5"
    assert compose["services"]["flyway"]["image"] == "redgate/flyway:13.6.0"
    assert compose["services"]["flyway"]["profiles"] == ["migrate"]
    assert compose["services"]["flyway"]["environment"]["FLYWAY_SCHEMAS"] == "meta"
    assert compose["services"]["flyway"]["environment"]["FLYWAY_LOCATIONS"] == (
        "filesystem:/flyway/migrations"
    )


def test_initial_migration_defines_geospatial_contract() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    for schema in ("meta", "raw", "staging", "analytics"):
        assert f"CREATE SCHEMA IF NOT EXISTS {schema}" in migration
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in migration
    assert "CREATE TABLE meta.pipeline_runs" in migration
    assert "CREATE TABLE raw.overpass_snapshots" in migration
    assert "CREATE TABLE staging.cafe_records" in migration
    assert "CREATE TABLE analytics.cafes" in migration
    assert migration.count("GEOMETRY(Point, 4326)") == 2
    assert "staging_run_source_identity UNIQUE (run_id, source_id)" in migration
    assert "USING GIST (geometry)" in migration


def test_second_migration_keeps_accepted_identity_unique_per_run() -> None:
    migration = (ROOT / "db/migrations/V2__partial_unique_accepted_identity.sql").read_text(
        encoding="utf-8"
    )

    assert (
        "ALTER TABLE staging.cafe_records DROP CONSTRAINT staging_run_source_identity" in migration
    )
    assert "CREATE UNIQUE INDEX staging_run_accepted_identity" in migration
    assert "ON staging.cafe_records (run_id, source_id)" in migration
    assert "WHERE validation_status IN ('accepted', 'accepted_with_warning')" in migration
