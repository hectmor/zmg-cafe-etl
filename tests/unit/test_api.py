"""Route tests for the café API that do not require a database."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from api.main import create_app, get_store
from fastapi.testclient import TestClient

RETRIEVED_AT = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)
RUN_ID = uuid4()


def _row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source_id": "openstreetmap:node:1",
        "source": "openstreetmap",
        "object_type": "node",
        "object_id": 1,
        "name": "Cafe Central",
        "category": "cafe",
        "latitude": 20.67,
        "longitude": -103.35,
        "geometry_method": "node_coordinates",
        "tags": {"name": "Cafe Central"},
        "source_updated_at": None,
        "retrieved_at": RETRIEVED_AT,
        "run_id": RUN_ID,
    }
    row.update(overrides)
    return row


class FakeStore:
    def __init__(self, rows: list[dict[str, Any]], *, reachable: bool = True) -> None:
        self.rows = rows
        self.reachable = reachable

    def ping(self) -> bool:
        return self.reachable

    def count_cafes(self) -> int:
        return len(self.rows)

    def list_cafes(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        return self.rows[offset : offset + limit]

    def get_cafe(self, source_id: str) -> dict[str, Any] | None:
        return next((row for row in self.rows if row["source_id"] == source_id), None)

    def stats(self) -> dict[str, Any]:
        return {
            "total": len(self.rows),
            "with_name": sum(1 for row in self.rows if row["name"] is not None),
            "without_name": sum(1 for row in self.rows if row["name"] is None),
            "by_object_type": {"node": len(self.rows)},
            "by_geometry_method": {"node_coordinates": len(self.rows)},
        }


def _client(store: FakeStore) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app)


def test_health_reports_a_connected_database() -> None:
    response = _client(FakeStore([_row()])).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_reports_service_unavailable_when_the_database_is_down() -> None:
    response = _client(FakeStore([_row()], reachable=False)).get("/health")

    assert response.status_code == 503
    assert response.json()["detail"] == "database is unreachable"


def test_list_cafes_returns_total_limit_offset_and_items() -> None:
    rows = [_row(source_id=f"openstreetmap:node:{index}", object_id=index) for index in range(3)]
    response = _client(FakeStore(rows)).get("/cafes", params={"limit": 2, "offset": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [item["source_id"] for item in body["items"]] == [
        "openstreetmap:node:1",
        "openstreetmap:node:2",
    ]


def test_list_cafes_rejects_out_of_range_pagination() -> None:
    client = _client(FakeStore([_row()]))

    for params in ({"limit": 0}, {"limit": 1001}, {"offset": -1}):
        assert client.get("/cafes", params=params).status_code == 422


def test_get_cafe_returns_the_record_for_a_colon_identified_source() -> None:
    response = _client(FakeStore([_row()])).get("/cafes/openstreetmap:node:1")

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "openstreetmap:node:1"
    assert body["object_id"] == 1
    assert body["run_id"] == str(RUN_ID)


def test_get_cafe_returns_404_for_unknown_identity() -> None:
    response = _client(FakeStore([_row()])).get("/cafes/openstreetmap:node:999")

    assert response.status_code == 404
    assert response.json()["detail"] == "cafe not found"


def test_geojson_orders_coordinates_as_longitude_latitude() -> None:
    response = _client(FakeStore([_row()])).get("/geojson/cafes")

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    feature = body["features"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"] == {
        "type": "Point",
        "coordinates": [-103.35, 20.67],
    }
    assert "latitude" not in feature["properties"]
    assert "longitude" not in feature["properties"]
    assert feature["properties"]["source_id"] == "openstreetmap:node:1"


def test_stats_summarize_the_analytics_layer() -> None:
    response = _client(FakeStore([_row(), _row(source_id="openstreetmap:node:2", name=None)])).get(
        "/stats"
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "with_name": 1,
        "without_name": 1,
        "by_object_type": {"node": 2},
        "by_geometry_method": {"node_coordinates": 2},
    }
