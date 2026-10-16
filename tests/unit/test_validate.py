import pytest

from zmg_cafes_etl.models import GeometryMethod, RejectionReason
from zmg_cafes_etl.validate import read_geometry, read_identity


@pytest.mark.parametrize(
    ("element", "reason"),
    [
        ({}, RejectionReason.MISSING_OBJECT_TYPE),
        ({"type": "node"}, RejectionReason.MISSING_OBJECT_ID),
        ({"type": "node", "id": 0}, RejectionReason.INVALID_OBJECT_ID),
    ],
)
def test_read_identity_rejects_invalid_identity(element, reason) -> None:
    assert read_identity(element)[2] is reason


@pytest.mark.parametrize(
    ("element", "object_type", "reason"),
    [
        ({}, "node", RejectionReason.MISSING_COORDINATES),
        ({"lat": 91, "lon": 0}, "node", RejectionReason.INVALID_LATITUDE),
        ({"lat": 0, "lon": 181}, "node", RejectionReason.INVALID_LONGITUDE),
        ({}, "way", RejectionReason.MISSING_WAY_OR_RELATION_CENTER),
        ({"center": {"lat": 0}}, "relation", RejectionReason.MISSING_COORDINATES),
        ({"lat": 0, "lon": 0}, "area", RejectionReason.UNSUPPORTED_GEOMETRY),
    ],
)
def test_read_geometry_rejects_invalid_geometries(element, object_type, reason) -> None:
    assert read_geometry(element, object_type)[3] is reason


def test_read_geometry_uses_overpass_center_for_relations() -> None:
    latitude, longitude, method, reason = read_geometry(
        {"center": {"lat": 20.67, "lon": -103.34}}, "relation"
    )

    assert (latitude, longitude, method, reason) == (
        20.67,
        -103.34,
        GeometryMethod.OVERPASS_CENTER,
        None,
    )


def test_read_identity_accepts_economic_unit_like_a_node() -> None:
    assert read_identity({"type": "economic_unit", "id": 7026403001}) == (
        "economic_unit",
        7026403001,
        None,
    )


def test_read_geometry_reads_denue_latitud_longitud_fields() -> None:
    latitude, longitude, method, reason = read_geometry(
        {"Latitud": "20.676195", "Longitud": "-103.347190"}, "economic_unit"
    )

    assert (latitude, longitude, method, reason) == (
        20.676195,
        -103.34719,
        GeometryMethod.DENUE_COORDINATES,
        None,
    )


def test_read_geometry_rejects_economic_unit_without_coordinates() -> None:
    assert read_geometry({}, "economic_unit")[3] is RejectionReason.MISSING_COORDINATES
