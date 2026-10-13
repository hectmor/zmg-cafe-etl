"""Integration tests for the PostgreSQL/PostGIS loader.

Every test truncates the four project schemas first so the assertions stay
deterministic across repeated runs against the same database.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from zmg_cafes_etl.config import SourceConfig, load_source_config
from zmg_cafes_etl.extract import ExtractionResult, extract_offline
from zmg_cafes_etl.load import LoadError, load_run
from zmg_cafes_etl.models import (
    GeometryMethod,
    NormalizedRecord,
    RejectionReason,
    TransformationResult,
    ValidationStatus,
)
from zmg_cafes_etl.transform import transform_payload

ROOT = Path(__file__).parents[2]
FIXTURE_PATH = ROOT / "tests/fixtures/overpass_cafes_sample.json"
CONFIG_PATH = ROOT / "config/sources.yaml"

DATABASE_URL = os.environ.get("ZMG_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="Set ZMG_TEST_DATABASE_URL to run PostgreSQL/PostGIS integration tests",
)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE analytics.cafes, staging.cafe_records,"
                " raw.overpass_snapshots, meta.pipeline_runs"
            )


@pytest.fixture
def source_config() -> SourceConfig:
    return load_source_config(CONFIG_PATH, "openstreetmap")


@pytest.fixture
def extraction(tmp_path: Path, source_config: SourceConfig) -> ExtractionResult:
    return extract_offline(FIXTURE_PATH, source_config, tmp_path / "raw")


def _scalar(statement: str, params: dict[str, object]) -> object:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            row = cursor.fetchone()
            return row[0] if row else None


def _row(statement: str, params: dict[str, object]) -> tuple[object, ...] | None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            return cursor.fetchone()


def test_first_load_persists_run_snapshot_staging_and_analytics(
    extraction: ExtractionResult, source_config: SourceConfig
) -> None:
    transformation = transform_payload(
        extraction.payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )

    metrics = load_run(extraction, transformation, dsn=DATABASE_URL)

    assert metrics.accepted == len(transformation.accepted)
    assert metrics.rejected == len(transformation.rejected)
    assert metrics.inserted == metrics.accepted
    assert metrics.updated == 0
    assert metrics.accepted > 0

    assert (
        _scalar(
            "SELECT status FROM meta.pipeline_runs WHERE run_id = %(run_id)s",
            {"run_id": extraction.run_id},
        )
        == "completed"
    )
    assert (
        _scalar(
            "SELECT count(*) FROM raw.overpass_snapshots WHERE run_id = %(run_id)s",
            {"run_id": extraction.run_id},
        )
        == 1
    )
    assert _scalar(
        "SELECT count(*) FROM staging.cafe_records WHERE run_id = %(run_id)s",
        {"run_id": extraction.run_id},
    ) == len(transformation.records)
    assert (
        _scalar(
            "SELECT count(*) FROM analytics.cafes WHERE run_id = %(run_id)s",
            {"run_id": extraction.run_id},
        )
        == metrics.accepted
    )


def test_reloading_the_same_run_updates_without_duplicates(
    extraction: ExtractionResult, source_config: SourceConfig
) -> None:
    transformation = transform_payload(
        extraction.payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )
    load_run(extraction, transformation, dsn=DATABASE_URL)

    metrics = load_run(extraction, transformation, dsn=DATABASE_URL)

    assert metrics.inserted == 0
    assert metrics.updated == metrics.accepted
    assert _scalar(
        "SELECT count(*) FROM staging.cafe_records WHERE run_id = %(run_id)s",
        {"run_id": extraction.run_id},
    ) == len(transformation.records)
    assert (
        _scalar(
            "SELECT count(*) FROM analytics.cafes",
            {},
        )
        >= metrics.accepted
    )


def test_rejected_duplicate_identity_is_stored_and_accepted_identity_is_unique(
    extraction: ExtractionResult, source_config: SourceConfig
) -> None:
    payload = {
        "elements": [
            {"type": "node", "id": 1, "lat": 20.67, "lon": -103.35, "tags": {"name": "Cafe"}},
            {"type": "node", "id": 1, "lat": 20.68, "lon": -103.36, "tags": {"name": "Otro"}},
        ]
    }
    transformation = transform_payload(
        payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )
    assert len(transformation.accepted) == 1
    assert transformation.rejected[0].rejection_reason is RejectionReason.DUPLICATE_SOURCE_IDENTITY

    metrics = load_run(extraction, transformation, dsn=DATABASE_URL)

    assert metrics.inserted == 1
    assert (
        _scalar(
            "SELECT count(*) FROM staging.cafe_records WHERE run_id = %(run_id)s",
            {"run_id": extraction.run_id},
        )
        == 2
    )
    assert (
        _scalar(
            "SELECT validation_status FROM staging.cafe_records"
            " WHERE run_id = %(run_id)s AND rejection_reason = 'duplicate_source_identity'",
            {"run_id": extraction.run_id},
        )
        == "rejected"
    )
    assert (
        _scalar(
            "SELECT count(*) FROM analytics.cafes WHERE source_id = 'openstreetmap:node:1'",
            {},
        )
        == 1
    )


def test_failed_load_leaves_no_completed_run_or_partial_results(
    extraction: ExtractionResult,
) -> None:
    broken = NormalizedRecord(
        source="openstreetmap",
        object_type="node",
        object_id=1,
        source_id="openstreetmap:node:999",
        name=None,
        category="cafe",
        latitude=20.67,
        longitude=-103.35,
        geometry={"type": "Point", "coordinates": [-103.35, 20.67]},
        geometry_method=GeometryMethod.NODE_COORDINATES,
        tags={},
        source_updated_at=None,
        retrieved_at=datetime(2026, 10, 12, tzinfo=UTC),
        run_id=extraction.run_id,
        validation_status=ValidationStatus.ACCEPTED,
        rejection_reason=None,
    )
    transformation = TransformationResult(records=(broken,))

    with pytest.raises(LoadError):
        load_run(extraction, transformation, dsn=DATABASE_URL)

    assert (
        _scalar(
            "SELECT count(*) FROM meta.pipeline_runs WHERE run_id = %(run_id)s",
            {"run_id": extraction.run_id},
        )
        == 0
    )
    assert (
        _scalar(
            "SELECT count(*) FROM staging.cafe_records WHERE run_id = %(run_id)s",
            {"run_id": extraction.run_id},
        )
        == 0
    )
    assert (
        _scalar(
            "SELECT count(*) FROM raw.overpass_snapshots WHERE run_id = %(run_id)s",
            {"run_id": extraction.run_id},
        )
        == 0
    )


def test_analytics_geometry_is_a_wgs84_point_matching_the_coordinates(
    extraction: ExtractionResult, source_config: SourceConfig
) -> None:
    transformation = transform_payload(
        extraction.payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )
    load_run(extraction, transformation, dsn=DATABASE_URL)
    record = transformation.accepted[0]

    row = _row(
        "SELECT ST_SRID(geometry), ST_X(geometry), ST_Y(geometry), geometry_method"
        " FROM analytics.cafes WHERE source_id = %(source_id)s",
        {"source_id": record.source_id},
    )

    assert row is not None
    srid, x, y, geometry_method = row
    assert srid == 4326
    assert x == pytest.approx(record.longitude)
    assert y == pytest.approx(record.latitude)
    assert geometry_method == record.geometry_method.value


def test_staging_geometry_is_null_for_rejected_rows(
    extraction: ExtractionResult, source_config: SourceConfig
) -> None:
    payload = {
        "elements": [
            {"type": "node", "id": 7, "tags": {"name": "Sin coordenadas"}},
        ]
    }
    transformation = transform_payload(
        payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )
    assert transformation.rejected[0].rejection_reason is RejectionReason.MISSING_COORDINATES

    load_run(extraction, transformation, dsn=DATABASE_URL)

    assert (
        _scalar(
            "SELECT count(*) FROM staging.cafe_records"
            " WHERE run_id = %(run_id)s AND geometry IS NULL AND rejection_reason = 'missing_coordinates'",
            {"run_id": extraction.run_id},
        )
        == 1
    )
