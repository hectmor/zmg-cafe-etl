"""Unit tests for the load contract that do not require a database."""

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from zmg_cafes_etl.extract import ExtractionResult
from zmg_cafes_etl.load import LoadError, LoadMetrics, load_run, normalize_dsn
from zmg_cafes_etl.models import (
    GeometryMethod,
    NormalizedRecord,
    RejectionReason,
    TransformationResult,
    ValidationStatus,
)


def _extraction(run_id: str) -> ExtractionResult:
    return ExtractionResult(
        run_id=run_id,
        source="openstreetmap",
        retrieved_at=datetime(2026, 10, 12, tzinfo=UTC),
        query="[out:json];node(1,2,3,4);out;",
        query_hash="a" * 64,
        payload={"elements": []},
        raw_path=Path(f"/tmp/raw/{run_id}.json"),
        metadata_path=Path(f"/tmp/raw/{run_id}.metadata.json"),
    )


def _accepted_record(run_id: str) -> NormalizedRecord:
    return NormalizedRecord(
        source="openstreetmap",
        object_type="node",
        object_id=1,
        source_id="openstreetmap:node:1",
        name="Cafe",
        category="cafe",
        establishment_kind="cafe",
        latitude=20.67,
        longitude=-103.35,
        geometry={"type": "Point", "coordinates": [-103.35, 20.67]},
        geometry_method=GeometryMethod.NODE_COORDINATES,
        tags={"name": "Cafe"},
        source_updated_at=None,
        retrieved_at=datetime(2026, 10, 12, tzinfo=UTC),
        run_id=run_id,
        validation_status=ValidationStatus.ACCEPTED,
        rejection_reason=None,
    )


def test_normalize_dsn_strips_sqlalchemy_psycopg_suffix() -> None:
    assert normalize_dsn("postgresql+psycopg://user:pass@localhost:5432/db") == (
        "postgresql://user:pass@localhost:5432/db"
    )
    assert normalize_dsn("postgres+psycopg://user:pass@localhost:5432/db") == (
        "postgresql://user:pass@localhost:5432/db"
    )


def test_normalize_dsn_keeps_plain_postgresql_dsn() -> None:
    dsn = "postgresql://user:pass@localhost:5432/db"
    assert normalize_dsn(dsn) == dsn


def test_load_metrics_are_json_serializable() -> None:
    metrics = LoadMetrics(accepted=2, rejected=1, inserted=2, updated=0, retired=0)
    assert metrics.as_dict() == {
        "accepted": 2,
        "rejected": 1,
        "inserted": 2,
        "updated": 0,
        "retired": 0,
    }


def test_load_run_rejects_records_from_another_run() -> None:
    run_id = str(uuid4())
    other_record = _accepted_record(str(uuid4()))
    transformation = TransformationResult(records=(other_record,))

    with pytest.raises(LoadError, match="does not match extraction run"):
        load_run(_extraction(run_id), transformation, dsn="postgresql://localhost:5432/db")


def test_load_run_logs_start_and_failure_without_leaking_the_dsn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    run_id = str(uuid4())
    other_record = _accepted_record(str(uuid4()))
    transformation = TransformationResult(records=(other_record,))
    secret_dsn = "postgresql://user:s3cr3t@localhost:5432/db"

    with caplog.at_level(logging.INFO, logger="zmg_cafes_etl.load"):
        with pytest.raises(LoadError, match="does not match extraction run"):
            load_run(_extraction(run_id), transformation, dsn=secret_dsn)

    messages = [record.getMessage() for record in caplog.records]
    assert any("load_run started" in message and run_id in message for message in messages)
    assert any("load_run failed" in message and "LoadError" in message for message in messages)
    assert all("s3cr3t" not in message for message in messages)


def test_load_run_can_see_rejected_duplicates_in_the_same_run() -> None:
    run_id = str(uuid4())
    accepted = _accepted_record(run_id)
    duplicate = NormalizedRecord(
        source=accepted.source,
        object_type=accepted.object_type,
        object_id=accepted.object_id,
        source_id=accepted.source_id,
        name=accepted.name,
        category=accepted.category,
        establishment_kind=accepted.establishment_kind,
        latitude=None,
        longitude=None,
        geometry=None,
        geometry_method=None,
        tags=accepted.tags,
        source_updated_at=None,
        retrieved_at=accepted.retrieved_at,
        run_id=run_id,
        validation_status=ValidationStatus.REJECTED,
        rejection_reason=RejectionReason.DUPLICATE_SOURCE_IDENTITY,
    )
    transformation = TransformationResult(records=(accepted, duplicate))
    assert len(transformation.accepted) == 1
    assert len(transformation.rejected) == 1
