"""Consumer-facing response models for the café API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Cafe(BaseModel):
    source_id: str
    source: str
    object_type: str
    object_id: int
    name: str | None
    category: str
    establishment_kind: str
    municipio: str | None
    ubicacion: str | None
    areageo: str | None
    clee: str | None
    latitude: float
    longitude: float
    geometry_method: str
    tags: dict[str, Any]
    source_updated_at: datetime | None
    retrieved_at: datetime
    run_id: str


class CafeList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Cafe]


class Stats(BaseModel):
    total: int
    with_name: int
    without_name: int
    by_object_type: dict[str, int]
    by_geometry_method: dict[str, int]
    by_source: dict[str, int]


class Health(BaseModel):
    status: str
    database: str


class PipelineRun(BaseModel):
    run_id: str
    source: str
    status: str
    started_at: datetime
    completed_at: datetime | None


class Freshness(BaseModel):
    runs: list[PipelineRun]
    last_completed_at: datetime | None
    seconds_since_last_completed: float | None


def cafe_from_row(row: dict[str, Any]) -> Cafe:
    """Build a Cafe response model from one analytics row."""

    cafe = dict(row)
    cafe["run_id"] = str(cafe["run_id"])
    cafe["object_id"] = int(cafe["object_id"])
    cafe["latitude"] = float(cafe["latitude"])
    cafe["longitude"] = float(cafe["longitude"])
    return Cafe(**cafe)


def cafe_feature(row: dict[str, Any]) -> dict[str, Any]:
    """Build one GeoJSON Feature with coordinates ordered [longitude, latitude]."""

    cafe = cafe_from_row(row)
    properties = cafe.model_dump()
    properties.pop("latitude")
    properties.pop("longitude")
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [cafe.longitude, cafe.latitude],
        },
        "properties": properties,
    }


def feature_collection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a GeoJSON FeatureCollection from analytics rows."""

    return {
        "type": "FeatureCollection",
        "features": [cafe_feature(row) for row in rows],
    }


def pipeline_run_from_row(row: dict[str, Any]) -> PipelineRun:
    """Build a PipelineRun response model from one `meta.pipeline_runs` row."""

    run = dict(row)
    run["run_id"] = str(run["run_id"])
    return PipelineRun(**run)


def freshness_from_rows(rows: list[dict[str, Any]], *, now: datetime) -> Freshness:
    """Summarize recent pipeline runs and the freshness of the last completed one.

    Freshness is derived only from rows actually returned by the database;
    it stays `None` when no run has completed, rather than fabricating a value.
    """

    runs = [pipeline_run_from_row(row) for row in rows]
    completed_at_values = [
        run.completed_at
        for run in runs
        if run.status == "completed" and run.completed_at is not None
    ]
    last_completed_at = max(completed_at_values) if completed_at_values else None
    seconds_since_last_completed = (
        (now - last_completed_at).total_seconds() if last_completed_at is not None else None
    )
    return Freshness(
        runs=runs,
        last_completed_at=last_completed_at,
        seconds_since_last_completed=seconds_since_last_completed,
    )
