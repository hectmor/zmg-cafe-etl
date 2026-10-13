"""Integration tests for the café API against PostgreSQL/PostGIS.

Every test truncates the four project schemas first so the assertions stay
deterministic across repeated runs against the same development database.
"""

import os
from pathlib import Path

import psycopg
import pytest
from api.db import AnalyticsStore
from api.main import create_app, get_store
from fastapi.testclient import TestClient

from zmg_cafes_etl.config import load_source_config
from zmg_cafes_etl.extract import extract_offline
from zmg_cafes_etl.load import load_run
from zmg_cafes_etl.transform import transform_payload

ROOT = Path(__file__).parents[2]
FIXTURE_PATH = ROOT / "tests/fixtures/overpass_cafes_sample.json"
CONFIG_PATH = ROOT / "config/sources.yaml"

DATABASE_URL = os.environ.get("ZMG_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    DATABASE_URL is None,
    reason="Set ZMG_TEST_DATABASE_URL to run PostgreSQL/PostGIS integration tests",
)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE analytics.cafes, staging.cafe_records,"
                " raw.overpass_snapshots, meta.pipeline_runs"
            )


@pytest.fixture
def loaded_run(tmp_path: Path) -> tuple[str, int]:
    source_config = load_source_config(CONFIG_PATH, "openstreetmap")
    extraction = extract_offline(FIXTURE_PATH, source_config, tmp_path / "raw")
    transformation = transform_payload(
        extraction.payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )
    metrics = load_run(extraction, transformation, dsn=DATABASE_URL)
    return extraction.run_id, metrics.accepted


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    app.dependency_overrides[get_store] = lambda: AnalyticsStore(DATABASE_URL)
    return TestClient(app)


def test_health_reaches_the_analytics_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_list_cafes_returns_the_loaded_analytics_rows(
    client: TestClient, loaded_run: tuple[str, int]
) -> None:
    run_id, accepted = loaded_run

    response = client.get("/cafes", params={"limit": 100, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == accepted
    assert len(body["items"]) == accepted
    assert all(item["run_id"] == run_id for item in body["items"])


def test_list_cafes_paginates_without_losing_the_total(
    client: TestClient, loaded_run: tuple[str, int]
) -> None:
    _, accepted = loaded_run

    first = client.get("/cafes", params={"limit": 1, "offset": 0}).json()
    second = client.get("/cafes", params={"limit": 1, "offset": 1}).json()

    assert first["total"] == second["total"] == accepted
    assert len(first["items"]) == 1
    assert first["items"][0]["source_id"] != second["items"][0]["source_id"]


def test_get_cafe_serves_one_loaded_identity(
    client: TestClient, loaded_run: tuple[str, int]
) -> None:
    listing = client.get("/cafes", params={"limit": 1, "offset": 0}).json()
    source_id = listing["items"][0]["source_id"]

    response = client.get(f"/cafes/{source_id}")

    assert response.status_code == 200
    assert response.json()["source_id"] == source_id


def test_get_cafe_returns_404_for_an_unloaded_identity(client: TestClient) -> None:
    response = client.get("/cafes/openstreetmap:node:999999")

    assert response.status_code == 404


def test_geojson_matches_the_loaded_coordinates(
    client: TestClient, loaded_run: tuple[str, int]
) -> None:
    _, accepted = loaded_run

    response = client.get("/geojson/cafes", params={"limit": 1000, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == accepted
    feature = body["features"][0]
    longitude, latitude = feature["geometry"]["coordinates"]
    assert feature["geometry"]["type"] == "Point"
    assert -180 <= longitude <= 180
    assert -90 <= latitude <= 90


def test_stats_agree_with_the_loaded_run(client: TestClient, loaded_run: tuple[str, int]) -> None:
    _, accepted = loaded_run

    response = client.get("/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == accepted
    assert body["with_name"] + body["without_name"] == accepted
    assert sum(body["by_object_type"].values()) == accepted
    assert sum(body["by_geometry_method"].values()) == accepted


def test_runs_reports_the_loaded_execution_as_completed(
    client: TestClient, loaded_run: tuple[str, int]
) -> None:
    run_id, _ = loaded_run

    response = client.get("/runs")

    assert response.status_code == 200
    body = response.json()
    assert len(body["runs"]) == 1
    assert body["runs"][0]["run_id"] == run_id
    assert body["runs"][0]["status"] == "completed"
    assert body["runs"][0]["completed_at"] is not None
    assert body["last_completed_at"] is not None
    assert body["seconds_since_last_completed"] >= 0


def test_runs_reports_no_freshness_without_any_execution(client: TestClient) -> None:
    response = client.get("/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["runs"] == []
    assert body["last_completed_at"] is None
    assert body["seconds_since_last_completed"] is None
