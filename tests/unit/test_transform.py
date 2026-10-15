import json
from datetime import UTC, datetime
from pathlib import Path

from zmg_cafes_etl.config import BoundingBox
from zmg_cafes_etl.models import GeometryMethod, RejectionReason, ValidationStatus
from zmg_cafes_etl.transform import transform_payload

ROOT = Path(__file__).parents[2]
FIXTURE_PATH = ROOT / "tests/fixtures/overpass_cafes_sample.json"
STUDY_AREA = BoundingBox(south=20.52, west=-103.55, north=20.82, east=-103.15)
RETRIEVED_AT = datetime(2026, 2, 3, tzinfo=UTC)


def transform(payload):
    return transform_payload(
        payload,
        source="openstreetmap",
        retrieved_at=RETRIEVED_AT,
        run_id="run-001",
        study_area=STUDY_AREA,
    )


def test_transform_payload_normalizes_fixture_records() -> None:
    result = transform(json.loads(FIXTURE_PATH.read_text(encoding="utf-8")))

    assert len(result.accepted) == 4
    assert not result.rejected
    node, way, unnamed_node, relation = result.records
    assert node.source_id == "openstreetmap:node:1001"
    assert node.geometry == {"type": "Point", "coordinates": [-103.344, 20.6736]}
    assert node.validation_status is ValidationStatus.ACCEPTED
    assert way.geometry_method is GeometryMethod.OVERPASS_CENTER
    assert way.validation_status is ValidationStatus.ACCEPTED_WITH_WARNING
    assert unnamed_node.name is None
    assert unnamed_node.validation_status is ValidationStatus.ACCEPTED_WITH_WARNING
    assert relation.object_type == "relation"
    # openstreetmap is always "cafe": the Overpass query already filters
    # amenity=cafe, so it is a source fact rather than a name-based guess.
    assert {record.establishment_kind for record in result.accepted} == {"cafe"}


def test_transform_payload_rejects_outside_records_and_later_duplicates() -> None:
    result = transform(
        {
            "elements": [
                {"type": "node", "id": 1, "lat": 20.6, "lon": -103.4, "tags": {}},
                {"type": "node", "id": 1, "lat": 20.6, "lon": -103.4, "tags": {}},
                {"type": "node", "id": 2, "lat": 21, "lon": -103.4, "tags": {}},
            ]
        }
    )

    assert result.records[0].validation_status is ValidationStatus.ACCEPTED_WITH_WARNING
    assert result.records[1].rejection_reason is RejectionReason.DUPLICATE_SOURCE_IDENTITY
    assert result.records[2].rejection_reason is RejectionReason.OUTSIDE_STUDY_AREA
    assert len(result.rejected) == 2


def test_transform_payload_retains_reasons_for_malformed_elements() -> None:
    result = transform(
        {
            "elements": [
                "not an object",
                {"id": 1},
                {"type": "node", "id": "1"},
                {"type": "way", "id": 2},
            ]
        }
    )

    assert [record.rejection_reason for record in result.records] == [
        RejectionReason.MALFORMED_RESPONSE,
        RejectionReason.MISSING_OBJECT_TYPE,
        RejectionReason.INVALID_OBJECT_ID,
        RejectionReason.MISSING_WAY_OR_RELATION_CENTER,
    ]


def test_transform_payload_rejects_a_payload_without_elements() -> None:
    result = transform({})

    assert result.rejected[0].rejection_reason is RejectionReason.MALFORMED_RESPONSE


def test_transform_payload_normalizes_names_and_missing_tags() -> None:
    result = transform(
        {
            "elements": [
                {"type": "node", "id": 1, "lat": 20.6, "lon": -103.4},
                {
                    "type": "node",
                    "id": 2,
                    "lat": 20.6,
                    "lon": -103.4,
                    "tags": {"name": "  Café Uno  "},
                },
            ]
        }
    )

    unnamed, named = result.accepted
    assert unnamed.name is None
    assert unnamed.tags == {}
    assert unnamed.validation_status is ValidationStatus.ACCEPTED_WITH_WARNING
    assert named.name == "Café Uno"
    assert named.validation_status is ValidationStatus.ACCEPTED
