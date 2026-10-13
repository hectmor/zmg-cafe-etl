"""Integration tests for the Compose-served stack (API + frontend).

They expect a stack started with docker compose (see the README flow):

    POSTGRES_PORT=0 docker compose up -d db api frontend
    POSTGRES_PORT=0 docker compose --profile migrate run --rm flyway

and the following environment variables pointing at it:

- ZMG_STACK_API_URL, for example http://localhost:8000
- ZMG_STACK_FRONTEND_URL, for example http://localhost:8080
- ZMG_TEST_DATABASE_URL targeting the stack database, used to seed data
  through the real pipeline (extract -> transform -> load_run).
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from zmg_cafes_etl.config import SourceConfig, load_source_config
from zmg_cafes_etl.extract import ExtractionResult, extract_offline
from zmg_cafes_etl.load import load_run
from zmg_cafes_etl.transform import transform_payload

ROOT = Path(__file__).parents[2]
FIXTURE_PATH = ROOT / "tests/fixtures/overpass_cafes_sample.json"
CONFIG_PATH = ROOT / "config/sources.yaml"
FRONTEND_ORIGIN = "http://localhost:8080"

API_URL = os.environ.get("ZMG_STACK_API_URL")
FRONTEND_URL = os.environ.get("ZMG_STACK_FRONTEND_URL")
DATABASE_URL = os.environ.get("ZMG_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not (API_URL and FRONTEND_URL and DATABASE_URL),
    reason=(
        "Set ZMG_STACK_API_URL, ZMG_STACK_FRONTEND_URL and ZMG_TEST_DATABASE_URL "
        "against a running compose stack"
    ),
)


def _get(url: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read().decode("utf-8")


@pytest.fixture(scope="module")
def seeded_metrics(tmp_path_factory):
    source_config: SourceConfig = load_source_config(CONFIG_PATH, "openstreetmap")
    extraction: ExtractionResult = extract_offline(
        FIXTURE_PATH, source_config, tmp_path_factory.mktemp("raw")
    )
    transformation = transform_payload(
        extraction.payload,
        source=extraction.source,
        retrieved_at=extraction.retrieved_at,
        run_id=extraction.run_id,
        study_area=source_config.study_area,
    )
    return load_run(extraction, transformation, dsn=DATABASE_URL)


def test_health_reports_connected_database() -> None:
    status, _, body = _get(f"{API_URL}/health")

    assert status == 200
    assert json.loads(body) == {"status": "ok", "database": "connected"}


def test_pipeline_data_is_visible_in_the_api(seeded_metrics) -> None:
    status, _, body = _get(f"{API_URL}/cafes?limit=1000")

    assert status == 200
    payload = json.loads(body)
    assert payload["total"] >= seeded_metrics.accepted
    source_ids = {item["source_id"] for item in payload["items"]}
    assert {
        "openstreetmap:node:1001",
        "openstreetmap:way:2002",
        "openstreetmap:node:1003",
        "openstreetmap:relation:3003",
    } <= source_ids


def test_geojson_uses_longitude_latitude_order() -> None:
    status, _, body = _get(f"{API_URL}/geojson/cafes")

    assert status == 200
    collection = json.loads(body)
    assert collection["type"] == "FeatureCollection"
    for feature in collection["features"]:
        longitude, latitude = feature["geometry"]["coordinates"]
        assert -104 < longitude < -102
        assert 20 < latitude < 21

    by_id = {feature["properties"]["source_id"]: feature for feature in collection["features"]}
    assert by_id["openstreetmap:node:1001"]["geometry"]["coordinates"] == [-103.344, 20.6736]


def test_frontend_serves_the_map_client() -> None:
    status, _, body = _get(FRONTEND_URL)

    assert status == 200
    assert 'lang="es"' in body
    assert "app.js" in body


def test_api_allows_the_documented_frontend_origin() -> None:
    status, headers, _ = _get(f"{API_URL}/geojson/cafes", headers={"Origin": FRONTEND_ORIGIN})

    assert status == 200
    assert headers.get("access-control-allow-origin") == FRONTEND_ORIGIN
