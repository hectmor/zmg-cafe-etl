"""Transform raw Overpass payloads into normalized café records."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .classify import classify_establishment_kind
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
            establishment_kind=_establishment_kind(source, None, None),
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
                    establishment_kind=record.establishment_kind,
                    municipio=record.municipio,
                    ubicacion=record.ubicacion,
                    areageo=record.areageo,
                    clee=record.clee,
                    source_updated_at=record.source_updated_at,
                    denue_fields={column: getattr(record, column) for column in _DENUE_TEXT_FIELDS},
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
            establishment_kind=_establishment_kind(source, None, None),
        )
    object_type, object_id, identity_error = read_identity(element)
    tags, tags_error = _read_tags(element)
    name = _normalize_name(tags.get("name"))
    source_id = _source_id(source, object_type, object_id)
    establishment_kind = _establishment_kind(source, name, tags.get("razon_social"))
    municipio = _municipio(source, tags)
    ubicacion, areageo, clee = _denue_raw_identifiers(source, element)
    denue_fields = _denue_contact_and_address(source, element)
    source_updated_at = _source_updated_at(source, element)
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
            establishment_kind=establishment_kind,
            municipio=municipio,
            ubicacion=ubicacion,
            areageo=areageo,
            clee=clee,
            source_updated_at=source_updated_at,
            denue_fields=denue_fields,
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
            establishment_kind=establishment_kind,
            municipio=municipio,
            ubicacion=ubicacion,
            areageo=areageo,
            clee=clee,
            source_updated_at=source_updated_at,
            denue_fields=denue_fields,
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
            establishment_kind=establishment_kind,
            municipio=municipio,
            ubicacion=ubicacion,
            areageo=areageo,
            clee=clee,
            source_updated_at=source_updated_at,
            denue_fields=denue_fields,
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
            establishment_kind=establishment_kind,
            municipio=municipio,
            ubicacion=ubicacion,
            areageo=areageo,
            clee=clee,
            source_updated_at=source_updated_at,
            denue_fields=denue_fields,
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
        establishment_kind=establishment_kind,
        latitude=latitude,
        longitude=longitude,
        geometry={"type": "Point", "coordinates": [longitude, latitude]},
        geometry_method=geometry_method,
        tags=tags,
        source_updated_at=source_updated_at,
        retrieved_at=retrieved_at,
        run_id=run_id,
        validation_status=status,
        rejection_reason=None,
        municipio=municipio,
        ubicacion=ubicacion,
        areageo=areageo,
        clee=clee,
        **denue_fields,
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


def _establishment_kind(source: str, name: str | None, razon_social: Any) -> str:
    if source == "openstreetmap":
        # The query already filters amenity=cafe: a source fact, not a guess.
        return "cafe"
    if source == "inegi_denue":
        return classify_establishment_kind(
            name, razon_social if isinstance(razon_social, str) else None
        )
    return "otro"


def _municipio(source: str, tags: Mapping[str, Any]) -> str | None:
    """Return the official municipio already stamped on the element's tags.

    Only `inegi_denue` carries this (set per query batch in
    `extract_denue.py`, never inferred); OpenStreetMap never has it.
    """

    if source != "inegi_denue":
        return None
    value = tags.get("municipio")
    return value if isinstance(value, str) and value else None


def _denue_raw_identifiers(
    source: str, element: Mapping[str, Any]
) -> tuple[str | None, str | None, str | None]:
    """Return the verbatim INEGI DENUE `Ubicacion`/`AreaGeo`/`CLEE` fields.

    These are official raw fields already complete on the DENUE record
    copied into the element (`extract_denue._to_element`); never
    parsed/derived. Always `None` for any other source, including
    OpenStreetMap, which does not provide them.
    """

    if source != "inegi_denue":
        return None, None, None
    return (
        _clean_denue_field(element.get("Ubicacion")),
        _clean_denue_field(element.get("AreaGeo")),
        _clean_denue_field(element.get("CLEE")),
    )


def _clean_denue_field(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


# Maps our column name to INEGI's raw field name (issue #66). Verbatim,
# same precedent as _denue_raw_identifiers: never parsed/derived.
_DENUE_TEXT_FIELDS = {
    "estrato": "Estrato",
    "tipo": "Tipo",
    "tipo_vialidad": "Tipo_vialidad",
    "calle": "Calle",
    "num_exterior": "Num_Exterior",
    "colonia": "Colonia",
    "cp": "CP",
    "telefono": "Telefono",
    "sitio_internet": "Sitio_internet",
    "correo_e": "Correo_e",
}


def _denue_contact_and_address(source: str, element: Mapping[str, Any]) -> dict[str, str | None]:
    """Return the verbatim INEGI DENUE address/contact fields (issue #66).

    Always `None` for any other source, including OpenStreetMap.
    """

    if source != "inegi_denue":
        return dict.fromkeys(_DENUE_TEXT_FIELDS, None)
    return {
        column: _clean_denue_field(element.get(raw_key))
        for column, raw_key in _DENUE_TEXT_FIELDS.items()
    }


def _source_updated_at(source: str, element: Mapping[str, Any]) -> datetime | None:
    """Parse INEGI DENUE's `Fecha_Alta` ("YYYY-MM") into a UTC timestamp.

    Returns `None` when the field is missing, malformed, or the source is
    not `inegi_denue` (OpenStreetMap has no registration date field) —
    never fabricated.
    """

    if source != "inegi_denue":
        return None
    value = element.get("Fecha_Alta")
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        year_text, month_text = value.strip().split("-")
        return datetime(int(year_text), int(month_text), 1, tzinfo=UTC)
    except ValueError:
        return None


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
    establishment_kind: str = "otro",
    municipio: str | None = None,
    ubicacion: str | None = None,
    areageo: str | None = None,
    clee: str | None = None,
    source_updated_at: datetime | None = None,
    denue_fields: dict[str, str | None] | None = None,
) -> NormalizedRecord:
    return NormalizedRecord(
        source=source,
        object_type=object_type,
        object_id=object_id,
        source_id=source_id,
        name=name,
        category="cafe",
        establishment_kind=establishment_kind,
        latitude=None,
        longitude=None,
        geometry=None,
        geometry_method=None,
        tags=tags or {},
        source_updated_at=source_updated_at,
        retrieved_at=retrieved_at,
        run_id=run_id,
        validation_status=ValidationStatus.REJECTED,
        rejection_reason=reason,
        municipio=municipio,
        ubicacion=ubicacion,
        areageo=areageo,
        clee=clee,
        **(denue_fields or {}),
    )
