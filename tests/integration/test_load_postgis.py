"""Integration tests for the PostgreSQL/PostGIS loader.

Every test truncates the four project schemas first so the assertions stay
deterministic across repeated runs against the same database.
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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

# "Café Centro" in tests/fixtures/overpass_cafes_sample.json: a node, id 1001.
CAFE_CENTRO_OBJECT_ID = 1001
CAFE_CENTRO_SOURCE_ID = "openstreetmap:node:1001"

pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="Set ZMG_TEST_DATABASE_URL to run PostgreSQL/PostGIS integration tests",
)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE analytics.establecimientos, staging.cafe_records,"
                " raw.overpass_snapshots, raw.denue_snapshots, meta.pipeline_runs"
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


def _load_fixture_payload() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _without_cafe_centro(payload: dict[str, Any]) -> dict[str, Any]:
    payload["elements"] = [
        element for element in payload["elements"] if element.get("id") != CAFE_CENTRO_OBJECT_ID
    ]
    return payload


def _with_cafe_centro_missing_coordinates(payload: dict[str, Any]) -> dict[str, Any]:
    payload["elements"] = [
        {key: value for key, value in element.items() if key not in ("lat", "lon")}
        if element.get("id") == CAFE_CENTRO_OBJECT_ID
        else element
        for element in payload["elements"]
    ]
    return payload


def _extract_from_payload(
    payload: dict[str, Any], tmp_path: Path, source_config: SourceConfig, name: str
) -> ExtractionResult:
    snapshot_path = tmp_path / f"{name}.json"
    snapshot_path.write_text(json.dumps(payload), encoding="utf-8")
    return extract_offline(snapshot_path, source_config, tmp_path / "raw")


def _transform(extraction: ExtractionResult, source_config: SourceConfig) -> TransformationResult:
    return transform_payload(
        extraction.payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )


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
            "SELECT count(*) FROM analytics.establecimientos WHERE run_id = %(run_id)s",
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
            "SELECT count(*) FROM analytics.establecimientos",
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
            "SELECT count(*) FROM analytics.establecimientos WHERE source_id = 'openstreetmap:node:1'",
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
        establishment_kind="cafe",
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
        " FROM analytics.establecimientos WHERE source_id = %(source_id)s",
        {"source_id": record.source_id},
    )

    assert row is not None
    srid, x, y, geometry_method = row
    assert srid == 4326
    assert x == pytest.approx(record.longitude)
    assert y == pytest.approx(record.latitude)
    assert geometry_method == record.geometry_method.value


def test_load_run_logs_completion_metrics_without_the_raw_payload(
    extraction: ExtractionResult,
    source_config: SourceConfig,
    caplog: pytest.LogCaptureFixture,
) -> None:
    transformation = transform_payload(
        extraction.payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )

    with caplog.at_level(logging.INFO, logger="zmg_cafes_etl.load"):
        metrics = load_run(extraction, transformation, dsn=DATABASE_URL)

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "load_run started" in message and extraction.run_id in message for message in messages
    )
    completion_messages = [message for message in messages if "load_run completed" in message]
    assert completion_messages
    assert any(
        extraction.run_id in message
        and f"accepted={metrics.accepted}" in message
        and f"inserted={metrics.inserted}" in message
        for message in completion_messages
    )
    assert all(extraction.query not in message for message in messages)


def test_load_run_logs_failure_with_error_type_on_a_broken_record(
    extraction: ExtractionResult,
    caplog: pytest.LogCaptureFixture,
) -> None:
    broken = NormalizedRecord(
        source="openstreetmap",
        object_type="node",
        object_id=1,
        source_id="openstreetmap:node:999",
        name=None,
        category="cafe",
        establishment_kind="cafe",
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

    with caplog.at_level(logging.INFO, logger="zmg_cafes_etl.load"):
        with pytest.raises(LoadError):
            load_run(extraction, transformation, dsn=DATABASE_URL)

    messages = [record.getMessage() for record in caplog.records]
    assert any(
        "load_run failed" in message and extraction.run_id in message for message in messages
    )
    assert not any("load_run completed" in message for message in messages)


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


def test_second_run_retires_cafe_absent_from_current_run(
    extraction: ExtractionResult, source_config: SourceConfig, tmp_path: Path
) -> None:
    transformation_n = _transform(extraction, source_config)
    load_run(extraction, transformation_n, dsn=DATABASE_URL)
    count_before = _scalar("SELECT count(*) FROM analytics.establecimientos", {})

    extraction_n1 = _extract_from_payload(
        _without_cafe_centro(_load_fixture_payload()), tmp_path, source_config, "run_n1"
    )
    transformation_n1 = _transform(extraction_n1, source_config)

    metrics_n1 = load_run(extraction_n1, transformation_n1, dsn=DATABASE_URL)

    assert metrics_n1.retired == 1
    assert metrics_n1.inserted == 0
    assert _scalar("SELECT count(*) FROM analytics.establecimientos", {}) == count_before - 1
    assert (
        _scalar(
            "SELECT count(*) FROM analytics.establecimientos WHERE source_id = %(source_id)s",
            {"source_id": CAFE_CENTRO_SOURCE_ID},
        )
        == 0
    )
    assert str(
        _scalar(
            "SELECT DISTINCT run_id FROM analytics.establecimientos WHERE source = 'openstreetmap'",
            {},
        )
    ) == str(extraction_n1.run_id)


def test_retirement_keeps_previous_run_staging_intact(
    extraction: ExtractionResult, source_config: SourceConfig, tmp_path: Path
) -> None:
    transformation_n = _transform(extraction, source_config)
    load_run(extraction, transformation_n, dsn=DATABASE_URL)

    extraction_n1 = _extract_from_payload(
        _without_cafe_centro(_load_fixture_payload()), tmp_path, source_config, "run_n1"
    )
    transformation_n1 = _transform(extraction_n1, source_config)
    load_run(extraction_n1, transformation_n1, dsn=DATABASE_URL)

    row = _row(
        "SELECT name, ST_X(geometry), ST_Y(geometry)"
        " FROM staging.cafe_records WHERE run_id = %(run_id)s AND source_id = %(source_id)s",
        {"run_id": extraction.run_id, "source_id": CAFE_CENTRO_SOURCE_ID},
    )
    assert row is not None
    name, x, y = row
    assert name == "Café Centro"
    assert x == pytest.approx(-103.344)
    assert y == pytest.approx(20.6736)
    assert _scalar("SELECT count(*) FROM raw.overpass_snapshots", {}) == 2


def test_cafe_rejected_in_next_run_is_retired_and_auditable(
    extraction: ExtractionResult, source_config: SourceConfig, tmp_path: Path
) -> None:
    transformation_n = _transform(extraction, source_config)
    load_run(extraction, transformation_n, dsn=DATABASE_URL)

    extraction_n1 = _extract_from_payload(
        _with_cafe_centro_missing_coordinates(_load_fixture_payload()),
        tmp_path,
        source_config,
        "run_n1",
    )
    transformation_n1 = _transform(extraction_n1, source_config)
    rejected_cafe = next(
        record for record in transformation_n1.rejected if record.source_id == CAFE_CENTRO_SOURCE_ID
    )
    assert rejected_cafe.rejection_reason is RejectionReason.MISSING_COORDINATES

    metrics_n1 = load_run(extraction_n1, transformation_n1, dsn=DATABASE_URL)

    assert metrics_n1.retired == 1
    assert (
        _scalar(
            "SELECT count(*) FROM analytics.establecimientos WHERE source_id = %(source_id)s",
            {"source_id": CAFE_CENTRO_SOURCE_ID},
        )
        == 0
    )
    row = _row(
        "SELECT validation_status, rejection_reason FROM staging.cafe_records"
        " WHERE run_id = %(run_id)s AND source_id = %(source_id)s",
        {"run_id": extraction_n1.run_id, "source_id": CAFE_CENTRO_SOURCE_ID},
    )
    assert row == ("rejected", "missing_coordinates")


def test_retirement_only_affects_the_run_source(
    extraction: ExtractionResult, source_config: SourceConfig, tmp_path: Path
) -> None:
    transformation_n = _transform(extraction, source_config)
    load_run(extraction, transformation_n, dsn=DATABASE_URL)

    other_run_id = str(uuid4())
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO meta.pipeline_runs (run_id, source, retrieved_at, status)"
                " VALUES (%(run_id)s, 'other', CURRENT_TIMESTAMP, 'completed')",
                {"run_id": other_run_id},
            )
            cursor.execute(
                "INSERT INTO analytics.establecimientos ("
                " source_id, source, object_type, object_id, name, category,"
                " latitude, longitude, geometry, geometry_method, tags,"
                " retrieved_at, run_id"
                ") VALUES ("
                " 'other:node:1', 'other', 'node', 1, 'Otra fuente', 'cafe',"
                " 20.0, -103.0, ST_SetSRID(ST_MakePoint(-103.0, 20.0), 4326),"
                " 'node_coordinates', '{}'::jsonb, CURRENT_TIMESTAMP, %(run_id)s"
                ")",
                {"run_id": other_run_id},
            )

    extraction_n1 = _extract_from_payload(
        _without_cafe_centro(_load_fixture_payload()), tmp_path, source_config, "run_n1"
    )
    transformation_n1 = _transform(extraction_n1, source_config)
    load_run(extraction_n1, transformation_n1, dsn=DATABASE_URL)

    assert (
        _scalar(
            "SELECT count(*) FROM analytics.establecimientos WHERE source_id = 'other:node:1'",
            {},
        )
        == 1
    )


def test_run_without_accepted_records_does_not_retire(
    extraction: ExtractionResult,
    source_config: SourceConfig,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    transformation_n = _transform(extraction, source_config)
    load_run(extraction, transformation_n, dsn=DATABASE_URL)
    count_before = _scalar("SELECT count(*) FROM analytics.establecimientos", {})

    extraction_n1 = _extract_from_payload({"elements": []}, tmp_path, source_config, "run_n1")
    transformation_n1 = _transform(extraction_n1, source_config)

    with caplog.at_level(logging.WARNING, logger="zmg_cafes_etl.load"):
        metrics_n1 = load_run(extraction_n1, transformation_n1, dsn=DATABASE_URL)

    assert metrics_n1.retired == 0
    assert _scalar("SELECT count(*) FROM analytics.establecimientos", {}) == count_before
    messages = [record.getMessage() for record in caplog.records]
    assert any("retirement skipped" in message for message in messages)


def test_reappearing_cafe_is_reinserted(
    extraction: ExtractionResult, source_config: SourceConfig, tmp_path: Path
) -> None:
    transformation_n = _transform(extraction, source_config)
    load_run(extraction, transformation_n, dsn=DATABASE_URL)

    extraction_n1 = _extract_from_payload(
        _without_cafe_centro(_load_fixture_payload()), tmp_path, source_config, "run_n1"
    )
    transformation_n1 = _transform(extraction_n1, source_config)
    load_run(extraction_n1, transformation_n1, dsn=DATABASE_URL)

    extraction_n2 = _extract_from_payload(
        _load_fixture_payload(), tmp_path, source_config, "run_n2"
    )
    transformation_n2 = _transform(extraction_n2, source_config)
    metrics_n2 = load_run(extraction_n2, transformation_n2, dsn=DATABASE_URL)

    assert metrics_n2.inserted == 1
    assert metrics_n2.retired == 0
