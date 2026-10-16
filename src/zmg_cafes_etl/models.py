"""Normalized records produced from raw Overpass elements."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class GeometryMethod(StrEnum):
    NODE_COORDINATES = "node_coordinates"
    OVERPASS_CENTER = "overpass_center"
    DENUE_COORDINATES = "denue_coordinates"


class ValidationStatus(StrEnum):
    ACCEPTED = "accepted"
    ACCEPTED_WITH_WARNING = "accepted_with_warning"
    REJECTED = "rejected"


class RejectionReason(StrEnum):
    MALFORMED_RESPONSE = "malformed_response"
    MISSING_OBJECT_TYPE = "missing_object_type"
    MISSING_OBJECT_ID = "missing_object_id"
    INVALID_OBJECT_ID = "invalid_object_id"
    MISSING_COORDINATES = "missing_coordinates"
    INVALID_LATITUDE = "invalid_latitude"
    INVALID_LONGITUDE = "invalid_longitude"
    MISSING_WAY_OR_RELATION_CENTER = "missing_way_or_relation_center"
    UNSUPPORTED_GEOMETRY = "unsupported_geometry"
    OUTSIDE_STUDY_AREA = "outside_study_area"
    DUPLICATE_SOURCE_IDENTITY = "duplicate_source_identity"


@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    source: str
    object_type: str | None
    object_id: int | None
    source_id: str | None
    name: str | None
    category: str
    # Derived heuristic subtype ("cafe"/"neveria"/"refresqueria"/"otro"); not
    # an official INEGI/OSM attribute, see classify.py.
    establishment_kind: str
    latitude: float | None
    longitude: float | None
    geometry: dict[str, Any] | None
    geometry_method: GeometryMethod | None
    tags: dict[str, Any]
    source_updated_at: datetime | None
    retrieved_at: datetime
    run_id: str
    validation_status: ValidationStatus
    rejection_reason: RejectionReason | None
    # Official municipality for the matching INEGI DENUE query batch (never
    # inferred from free text like `Ubicacion`); always None for OpenStreetMap,
    # which does not provide municipio.
    municipio: str | None = None
    # Verbatim INEGI DENUE fields (`Ubicacion`, `AreaGeo`, `CLEE`), already
    # complete on the raw record; never derived/parsed. Always None for
    # OpenStreetMap, which does not provide them.
    ubicacion: str | None = None
    areageo: str | None = None
    clee: str | None = None
    # Verbatim INEGI DENUE fields, same precedent as ubicacion/areageo/clee:
    # already complete on the raw record, never derived/parsed, always None
    # for OpenStreetMap, which does not provide them.
    estrato: str | None = None
    tipo: str | None = None
    tipo_vialidad: str | None = None
    calle: str | None = None
    num_exterior: str | None = None
    colonia: str | None = None
    cp: str | None = None
    telefono: str | None = None
    sitio_internet: str | None = None
    correo_e: str | None = None


@dataclass(frozen=True, slots=True)
class TransformationResult:
    records: tuple[NormalizedRecord, ...]

    @property
    def accepted(self) -> tuple[NormalizedRecord, ...]:
        return tuple(record for record in self.records if record.rejection_reason is None)

    @property
    def rejected(self) -> tuple[NormalizedRecord, ...]:
        return tuple(record for record in self.records if record.rejection_reason is not None)
