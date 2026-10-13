"""Transform raw Overpass payloads into normalized café records."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .config import BoundingBox
from .models import (
    GeometryMethod,
    NormalizedRecord,
    RejectionReason,
    TransformationResult,
    ValidationStatus,
)
from .validate import is_within_study_area, read_geometry, read_identity


def transform_payload(
    payload: Mapping[str, Any],
    *,
    source: str,
    retrieved_at: datetime,
    run_id: str,
    study_area: BoundingBox,
) -> TransformationResult:
    """Normalize Overpass elements and retain every rejected source record."""

    elements = payload.get("elements")
    if not isinstance(elements, list):
        record = _rejected_record(
            source=source,
            retrieved_at=retrieved_at,
            run_id=run_id,
            reason=RejectionReason.MALFORMED_RESPONSE,
        )
        return TransformationResult(records=(record,))

    records: list[NormalizedRecord] = []
    seen_source_ids: set[str] = set()
    for element in elements:
        record = _transform_element(
            element,
            source=source,
            retrieved_at=retrieved_at,
            run_id=run_id,
            study_area=study_area,
        )
        if record.source_id is not None:
            if record.source_id in seen_source_ids:
                record = _rejected_record(
                    source=source,
                    retrieved_at=retrieved_at,
                    run_id=run_id,
                    reason=RejectionReason.DUPLICATE_SOURCE_IDENTITY,
                    object_type=record.object_type,
                    object_id=record.object_id,
                    source_id=record.source_id,
                    name=record.name,
                    tags=record.tags,
                )
            else:
                seen_source_ids.add(record.source_id)
        records.append(record)
    return TransformationResult(records=tuple(records))


def _transform_element(
    element: Any,
    *,
    source: str,
    retrieved_at: datetime,
    run_id: str,
    study_area: BoundingBox,
) -> NormalizedRecord:
    if not isinstance(element, Mapping):
        return _rejected_record(
            source=source,
            retrieved_at=retrieved_at,
            run_id=run_id,
            reason=RejectionReason.MALFORMED_RESPONSE,
        )
    object_type, object_id, identity_error = read_identity(element)
    tags, tags_error = _read_tags(element)
    name = _normalize_name(tags.get("name"))
    source_id = _source_id(source, object_type, object_id)
    if identity_error is not None:
        return _rejected_record(
            source=source,
            retrieved_at=retrieved_at,
            run_id=run_id,
            reason=identity_error,
            object_type=object_type,
            object_id=object_id,
            source_id=source_id,
            name=name,
            tags=tags,
        )
    if tags_error is not None:
        return _rejected_record(
            source=source,
            retrieved_at=retrieved_at,
            run_id=run_id,
            reason=tags_error,
            object_type=object_type,
            object_id=object_id,
            source_id=source_id,
            name=name,
            tags=tags,
        )

    latitude, longitude, geometry_method, geometry_error = read_geometry(element, object_type)
    if geometry_error is not None:
        return _rejected_record(
            source=source,
            retrieved_at=retrieved_at,
            run_id=run_id,
            reason=geometry_error,
            object_type=object_type,
            object_id=object_id,
            source_id=source_id,
            name=name,
            tags=tags,
        )
    if not is_within_study_area(latitude, longitude, study_area):
        return _rejected_record(
            source=source,
            retrieved_at=retrieved_at,
            run_id=run_id,
            reason=RejectionReason.OUTSIDE_STUDY_AREA,
            object_type=object_type,
            object_id=object_id,
            source_id=source_id,
            name=name,
            tags=tags,
        )

    status = ValidationStatus.ACCEPTED
    if name is None or geometry_method is GeometryMethod.OVERPASS_CENTER:
        status = ValidationStatus.ACCEPTED_WITH_WARNING
    return NormalizedRecord(
        source=source,
        object_type=object_type,
        object_id=object_id,
        source_id=source_id,
        name=name,
        category="cafe",
        latitude=latitude,
        longitude=longitude,
        geometry={"type": "Point", "coordinates": [longitude, latitude]},
        geometry_method=geometry_method,
        tags=tags,
        source_updated_at=None,
        retrieved_at=retrieved_at,
        run_id=run_id,
        validation_status=status,
        rejection_reason=None,
    )


def _read_tags(element: Mapping[str, Any]) -> tuple[dict[str, Any], RejectionReason | None]:
    tags = element.get("tags", {})
    if not isinstance(tags, Mapping):
        return {}, RejectionReason.MALFORMED_RESPONSE
    return dict(tags), None


def _normalize_name(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _source_id(source: str, object_type: str | None, object_id: int | None) -> str | None:
    if object_type is None or object_id is None:
        return None
    return f"{source}:{object_type}:{object_id}"


def _rejected_record(
    *,
    source: str,
    retrieved_at: datetime,
    run_id: str,
    reason: RejectionReason,
    object_type: str | None = None,
    object_id: int | None = None,
    source_id: str | None = None,
    name: str | None = None,
    tags: dict[str, Any] | None = None,
) -> NormalizedRecord:
    return NormalizedRecord(
        source=source,
        object_type=object_type,
        object_id=object_id,
        source_id=source_id,
        name=name,
        category="cafe",
        latitude=None,
        longitude=None,
        geometry=None,
        geometry_method=None,
        tags=tags or {},
        source_updated_at=None,
        retrieved_at=retrieved_at,
        run_id=run_id,
        validation_status=ValidationStatus.REJECTED,
        rejection_reason=reason,
    )
