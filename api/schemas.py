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


class Health(BaseModel):
    status: str
    database: str


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
