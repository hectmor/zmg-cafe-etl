"""Persist extraction and transformation results into PostgreSQL/PostGIS."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .extract import ExtractionResult
from .models import NormalizedRecord, TransformationResult

logger = logging.getLogger(__name__)


class LoadError(RuntimeError):
    """Raised when a run cannot be persisted as one atomic unit."""


@dataclass(frozen=True, slots=True)
class LoadMetrics:
    accepted: int
    rejected: int
    inserted: int
    updated: int
    retired: int

    def as_dict(self) -> dict[str, int]:
        """Return the metrics as a JSON-serializable mapping."""

        return {
            "accepted": self.accepted,
            "rejected": self.rejected,
            "inserted": self.inserted,
            "updated": self.updated,
            "retired": self.retired,
        }


_LOCK_SOURCE = "SELECT pg_advisory_xact_lock(hashtext(%(lock_key)s))"

_INSERT_PIPELINE_RUN = """
INSERT INTO meta.pipeline_runs (run_id, source, retrieved_at, status)
VALUES (%(run_id)s, %(source)s, %(retrieved_at)s, 'started')
ON CONFLICT (run_id) DO UPDATE
SET source = EXCLUDED.source,
    retrieved_at = EXCLUDED.retrieved_at,
    status = 'started',
    started_at = CURRENT_TIMESTAMP,
    completed_at = NULL
"""


def _insert_snapshot_sql(table: str) -> str:
    """Build the snapshot upsert for a fixed, non-user-controlled table name."""

    return f"""
INSERT INTO {table} (run_id, query, query_hash, payload, snapshot_path)
VALUES (%(run_id)s, %(query)s, %(query_hash)s, %(payload)s, %(snapshot_path)s)
ON CONFLICT (run_id) DO UPDATE
SET query = EXCLUDED.query,
    query_hash = EXCLUDED.query_hash,
    payload = EXCLUDED.payload,
    snapshot_path = EXCLUDED.snapshot_path
"""


# Fixed, literal table identifiers per source (never built from request/user input).
_SNAPSHOT_TABLE_BY_SOURCE = {
    "openstreetmap": "raw.overpass_snapshots",
    "inegi_denue": "raw.denue_snapshots",
}

_INSERT_SNAPSHOT_BY_SOURCE = {
    source: _insert_snapshot_sql(table) for source, table in _SNAPSHOT_TABLE_BY_SOURCE.items()
}

_DELETE_STAGING_RUN = "DELETE FROM staging.cafe_records WHERE run_id = %(run_id)s"

_INSERT_STAGING = """
INSERT INTO staging.cafe_records (
    run_id, source, object_type, object_id, source_id, name, category,
    establishment_kind, municipio, ubicacion, areageo, clee, latitude, longitude, geometry,
    geometry_method, tags, source_updated_at, retrieved_at, validation_status, rejection_reason
)
VALUES (
    %(run_id)s, %(source)s, %(object_type)s, %(object_id)s, %(source_id)s, %(name)s,
    %(category)s, %(establishment_kind)s, %(municipio)s, %(ubicacion)s, %(areageo)s, %(clee)s,
    %(latitude)s, %(longitude)s,
    CASE
        WHEN %(validation_status)s = 'rejected' THEN NULL
        ELSE ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)
    END,
    %(geometry_method)s, %(tags)s, %(source_updated_at)s, %(retrieved_at)s,
    %(validation_status)s, %(rejection_reason)s
)
"""

_UPSERT_ANALYTICS = """
INSERT INTO analytics.establecimientos (
    source_id, source, object_type, object_id, name, category,
    establishment_kind, municipio, ubicacion, areageo, clee, latitude, longitude, geometry,
    geometry_method, tags, source_updated_at, retrieved_at, run_id
)
VALUES (
    %(source_id)s, %(source)s, %(object_type)s, %(object_id)s, %(name)s, %(category)s,
    %(establishment_kind)s, %(municipio)s, %(ubicacion)s, %(areageo)s, %(clee)s,
    %(latitude)s, %(longitude)s,
    ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326),
    %(geometry_method)s, %(tags)s, %(source_updated_at)s, %(retrieved_at)s, %(run_id)s
)
ON CONFLICT (source_id) DO UPDATE
SET source = EXCLUDED.source,
    object_type = EXCLUDED.object_type,
    object_id = EXCLUDED.object_id,
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    establishment_kind = EXCLUDED.establishment_kind,
    municipio = EXCLUDED.municipio,
    ubicacion = EXCLUDED.ubicacion,
    areageo = EXCLUDED.areageo,
    clee = EXCLUDED.clee,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    geometry = EXCLUDED.geometry,
    geometry_method = EXCLUDED.geometry_method,
    tags = EXCLUDED.tags,
    source_updated_at = EXCLUDED.source_updated_at,
    retrieved_at = EXCLUDED.retrieved_at,
    run_id = EXCLUDED.run_id
RETURNING (xmax = 0) AS inserted
"""

_RETIRE_ABSENT_ANALYTICS = """
DELETE FROM analytics.establecimientos
WHERE source = %(source)s
  AND NOT (source_id = ANY(%(current_source_ids)s::text[]))
"""

_COMPLETE_RUN = """
UPDATE meta.pipeline_runs
SET status = 'completed', completed_at = CURRENT_TIMESTAMP
WHERE run_id = %(run_id)s
"""


def normalize_dsn(dsn: str) -> str:
    """Return a DSN psycopg can open, dropping SQLAlchemy driver suffixes."""

    for prefix in ("postgresql+psycopg://", "postgres+psycopg://"):
        if dsn.startswith(prefix):
            return f"postgresql://{dsn[len(prefix) :]}"
    return dsn


def load_run(
    extraction: ExtractionResult,
    transformation: TransformationResult,
    *,
    dsn: str,
) -> LoadMetrics:
    """Persist one run in a single transaction and return its load metrics."""

    logger.info(
        "load_run started run_id=%s source=%s",
        extraction.run_id,
        extraction.source,
    )

    for record in transformation.records:
        if record.run_id != extraction.run_id:
            error = LoadError(
                f"Record run_id {record.run_id} does not match extraction run {extraction.run_id}"
            )
            logger.error(
                "load_run failed run_id=%s error_type=%s",
                extraction.run_id,
                type(error).__name__,
            )
            raise error

    accepted = transformation.accepted
    rejected = transformation.rejected
    inserted = 0
    updated = 0
    retired = 0
    try:
        insert_snapshot_sql = _INSERT_SNAPSHOT_BY_SOURCE[extraction.source]
    except KeyError as error:
        raise LoadError(
            f"Unknown source {extraction.source!r}; no raw snapshot table is configured for it"
        ) from error
    try:
        with psycopg.connect(normalize_dsn(dsn)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    _LOCK_SOURCE,
                    {"lock_key": f"zmg_cafes_etl.load_run:{extraction.source}"},
                )
                cursor.execute(
                    _INSERT_PIPELINE_RUN,
                    {
                        "run_id": extraction.run_id,
                        "source": extraction.source,
                        "retrieved_at": extraction.retrieved_at,
                    },
                )
                cursor.execute(
                    insert_snapshot_sql,
                    {
                        "run_id": extraction.run_id,
                        "query": extraction.query,
                        "query_hash": extraction.query_hash,
                        "payload": Jsonb(extraction.payload),
                        "snapshot_path": str(extraction.raw_path),
                    },
                )
                cursor.execute(_DELETE_STAGING_RUN, {"run_id": extraction.run_id})
                for record in transformation.records:
                    cursor.execute(_INSERT_STAGING, _record_parameters(record))
                for record in accepted:
                    cursor.execute(_UPSERT_ANALYTICS, _record_parameters(record))
                    row = cursor.fetchone()
                    if row is not None and row[0]:
                        inserted += 1
                    else:
                        updated += 1
                current_source_ids = [record.source_id for record in accepted]
                if current_source_ids:
                    cursor.execute(
                        _RETIRE_ABSENT_ANALYTICS,
                        {"source": extraction.source, "current_source_ids": current_source_ids},
                    )
                    retired = cursor.rowcount
                else:
                    retired = 0
                    logger.warning(
                        "load_run retirement skipped run_id=%s source=%s reason=no_accepted_records",
                        extraction.run_id,
                        extraction.source,
                    )
                cursor.execute(_COMPLETE_RUN, {"run_id": extraction.run_id})
    except psycopg.Error as error:
        logger.error(
            "load_run failed run_id=%s error_type=%s",
            extraction.run_id,
            type(error).__name__,
        )
        raise LoadError(f"Could not persist run {extraction.run_id}: {error}") from error

    metrics = LoadMetrics(
        accepted=len(accepted),
        rejected=len(rejected),
        inserted=inserted,
        updated=updated,
        retired=retired,
    )
    logger.info(
        "load_run completed run_id=%s accepted=%d rejected=%d inserted=%d updated=%d retired=%d",
        extraction.run_id,
        metrics.accepted,
        metrics.rejected,
        metrics.inserted,
        metrics.updated,
        metrics.retired,
    )
    return metrics


def _record_parameters(record: NormalizedRecord) -> dict[str, Any]:
    return {
        "run_id": record.run_id,
        "source": record.source,
        "object_type": record.object_type,
        "object_id": record.object_id,
        "source_id": record.source_id,
        "name": record.name,
        "category": record.category,
        "establishment_kind": record.establishment_kind,
        "municipio": record.municipio,
        "ubicacion": record.ubicacion,
        "areageo": record.areageo,
        "clee": record.clee,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "geometry_method": record.geometry_method.value if record.geometry_method else None,
        "tags": Jsonb(record.tags),
        "source_updated_at": record.source_updated_at,
        "retrieved_at": record.retrieved_at,
        "validation_status": record.validation_status.value,
        "rejection_reason": record.rejection_reason.value if record.rejection_reason else None,
    }
