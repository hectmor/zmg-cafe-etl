"""Validation helpers for raw Overpass elements."""

from collections.abc import Mapping
from math import isfinite
from typing import Any

from .config import BoundingBox
from .models import GeometryMethod, RejectionReason


def read_identity(
    element: Mapping[str, Any],
) -> tuple[str | None, int | None, RejectionReason | None]:
    object_type = element.get("type")
    if not isinstance(object_type, str) or not object_type:
        return None, None, RejectionReason.MISSING_OBJECT_TYPE

    if "id" not in element:
        return object_type, None, RejectionReason.MISSING_OBJECT_ID
    object_id = element["id"]
    if isinstance(object_id, bool) or not isinstance(object_id, int) or object_id <= 0:
        return object_type, None, RejectionReason.INVALID_OBJECT_ID
    return object_type, object_id, None


def read_geometry(
    element: Mapping[str, Any], object_type: str
) -> tuple[float | None, float | None, GeometryMethod | None, RejectionReason | None]:
    if object_type == "node":
        coordinate_data: Mapping[str, Any] = element
        geometry_method = GeometryMethod.NODE_COORDINATES
    elif object_type in {"way", "relation"}:
        center = element.get("center")
        if not isinstance(center, Mapping):
            return None, None, None, RejectionReason.MISSING_WAY_OR_RELATION_CENTER
        coordinate_data = center
        geometry_method = GeometryMethod.OVERPASS_CENTER
    else:
        return None, None, None, RejectionReason.UNSUPPORTED_GEOMETRY

    if "lat" not in coordinate_data or "lon" not in coordinate_data:
        return None, None, None, RejectionReason.MISSING_COORDINATES
    latitude = _as_coordinate(coordinate_data["lat"])
    if latitude is None or not -90 <= latitude <= 90:
        return None, None, None, RejectionReason.INVALID_LATITUDE
    longitude = _as_coordinate(coordinate_data["lon"])
    if longitude is None or not -180 <= longitude <= 180:
        return None, None, None, RejectionReason.INVALID_LONGITUDE
    return latitude, longitude, geometry_method, None


def is_within_study_area(latitude: float, longitude: float, bbox: BoundingBox) -> bool:
    return bbox.south <= latitude <= bbox.north and bbox.west <= longitude <= bbox.east


def _as_coordinate(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    return coordinate if isfinite(coordinate) else None
