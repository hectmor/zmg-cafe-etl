import json
import urllib.error
from datetime import UTC, datetime
from pathlib import Path

import pytest

import zmg_cafes_etl.extract_denue as extract_denue_module
from zmg_cafes_etl.config import ConfigurationError, load_source_config
from zmg_cafes_etl.extract import ExtractionError
from zmg_cafes_etl.extract_denue import extract_live_denue, extract_offline_denue
from zmg_cafes_etl.transform import transform_payload

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config/sources.yaml"
FIXTURE_PATH = ROOT / "tests/fixtures/denue_cafes_sample.json"


@pytest.fixture
def source_config():
    return load_source_config(CONFIG_PATH, "inegi_denue")


def test_load_source_config_reads_denue_settings(source_config) -> None:
    assert source_config.access_method == "inegi_denue_api"
    assert source_config.scian_class == "722515"
    assert source_config.page_size == 250
    assert source_config.query_template is None
    names = {municipality.name for municipality in source_config.municipalities}
    assert "Guadalajara" in names
    assert len(source_config.municipalities) == 9


def test_load_source_config_still_loads_openstreetmap_unchanged() -> None:
    overpass_config = load_source_config(CONFIG_PATH)

    assert overpass_config.access_method == "overpass_api"
    assert overpass_config.query_template is not None
    assert overpass_config.scian_class is None
    assert overpass_config.municipalities == ()


def test_load_source_config_rejects_denue_source_without_municipalities(tmp_path) -> None:
    import yaml

    document = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    denue_source = next(s for s in document["sources"] if s["name"] == "inegi_denue")
    denue_source["municipalities"] = []
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="municipality"):
        load_source_config(config_path, "inegi_denue")


def test_extract_offline_denue_maps_records_into_generic_elements(tmp_path, source_config) -> None:
    retrieved_at = datetime(2026, 2, 3, 10, 30, tzinfo=UTC)
    result = extract_offline_denue(
        FIXTURE_PATH,
        source_config,
        tmp_path,
        run_id="run-001",
        retrieved_at=retrieved_at,
    )

    assert result.object_count == 7
    assert result.raw_path == tmp_path / "inegi_denue/2026/02/03/run-001.json"
    stored = json.loads(result.raw_path.read_text(encoding="utf-8"))
    first = stored["elements"][0]
    assert first["type"] == "economic_unit"
    assert first["id"] == 7026403001
    assert first["Latitud"] == "20.676195"
    assert first["tags"]["name"] == "Café Ejemplo Centro"
    assert first["tags"]["municipio"] == "Guadalajara"

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["request_mode"] == "offline"
    assert "INEGI_DENUE_TOKEN" not in metadata["query"]
    assert "token" not in metadata["query"].lower()


def test_offline_denue_fixture_transforms_into_expected_statuses(tmp_path, source_config) -> None:
    retrieved_at = datetime(2026, 2, 3, 10, 30, tzinfo=UTC)
    result = extract_offline_denue(
        FIXTURE_PATH, source_config, tmp_path, run_id="run-002", retrieved_at=retrieved_at
    )

    transformation = transform_payload(
        result.payload,
        source="inegi_denue",
        retrieved_at=retrieved_at,
        run_id="run-002",
        study_area=source_config.study_area,
    )

    by_id = {record.object_id: record for record in transformation.records}
    assert by_id[7026403001].validation_status.value == "accepted"
    assert by_id[7026403001].source_id == "inegi_denue:economic_unit:7026403001"
    assert by_id[7026403001].geometry_method.value == "denue_coordinates"
    assert by_id[7026403001].establishment_kind == "cafe"
    assert by_id[7026403001].municipio == "Guadalajara"
    # Verbatim raw INEGI fields already complete on the record; never parsed.
    assert by_id[7026403001].ubicacion == "CALLE JUAREZ 123, CENTRO, GUADALAJARA, JALISCO"
    assert by_id[7026403001].areageo == "140390001234056"
    assert by_id[7026403001].clee == "141390001A0101234567"
    assert by_id[7026403002].validation_status.value == "accepted_with_warning"
    assert by_id[7026403002].name is None
    # "Negocio Local Café Dos", classified via Razon_social since Nombre is blank.
    assert by_id[7026403002].establishment_kind == "cafe"
    # Rejected for being outside the study area, but the municipio known from
    # the query is still preserved for audit (it is not a coordinate-derived fact).
    assert by_id[7026403003].rejection_reason.value == "outside_study_area"
    assert by_id[7026403003].municipio == "Guadalajara"
    assert by_id[7026403004].validation_status.value == "accepted"
    assert by_id[7026403004].establishment_kind == "cafe"
    assert by_id[7026403004].municipio == "Zapopan"
    assert by_id[7026403005].establishment_kind == "neveria"
    assert by_id[7026403005].municipio == "Tlaquepaque"
    assert by_id[7026403006].establishment_kind == "refresqueria"
    assert by_id[7026403006].municipio == "Tonalá"
    assert by_id[7026403007].establishment_kind == "otro"
    assert by_id[7026403007].municipio == "Guadalajara"


def test_extract_offline_denue_rejects_non_list_snapshot(tmp_path, source_config) -> None:
    snapshot = tmp_path / "invalid.json"
    snapshot.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    with pytest.raises(ExtractionError, match="JSON array"):
        extract_offline_denue(snapshot, source_config, tmp_path / "raw")


def test_extract_live_denue_requests_every_municipality_and_stops_pagination(
    tmp_path, source_config, monkeypatch
) -> None:
    requested_urls: list[str] = []

    class Response:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def urlopen(request, timeout):
        requested_urls.append(request.full_url)
        # One record per municipality, below page_size, so pagination stops
        # after a single window per municipality.
        return Response(json.dumps([{"Id": "1", "Nombre": "Café"}]).encode("utf-8"))

    monkeypatch.setattr(extract_denue_module.urllib.request, "urlopen", urlopen)

    result = extract_live_denue(
        source_config, tmp_path, token="secret-token-123", run_id="live-denue-run"
    )

    assert len(requested_urls) == len(source_config.municipalities)
    assert result.object_count == len(source_config.municipalities)
    assert all("secret-token-123" in url for url in requested_urls)
    # Each fetched record is tagged with the exact municipio of the batch
    # that returned it (known from config, never inferred from the response).
    assert [element["tags"]["municipio"] for element in result.payload["elements"]] == [
        municipality.name for municipality in source_config.municipalities
    ]


def test_extract_live_denue_paginates_until_a_short_window(
    tmp_path, source_config, monkeypatch
) -> None:
    import zmg_cafes_etl.config as config_module

    small_page_config = config_module.SourceConfig(
        name=source_config.name,
        access_method=source_config.access_method,
        endpoint=source_config.endpoint,
        timeout_seconds=source_config.timeout_seconds,
        max_retries=source_config.max_retries,
        retry_backoff_seconds=source_config.retry_backoff_seconds,
        study_area=source_config.study_area,
        scian_class=source_config.scian_class,
        page_size=2,
        municipalities=(source_config.municipalities[0],),
    )

    windows = []

    class Response:
        def __init__(self, body: bytes) -> None:
            self._body = body

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def urlopen(request, timeout):
        # First window full (2 records), second window short (1 record): stop.
        if not windows:
            windows.append(1)
            records = [{"Id": "1"}, {"Id": "2"}]
        else:
            records = [{"Id": "3"}]
        return Response(json.dumps(records).encode("utf-8"))

    monkeypatch.setattr(extract_denue_module.urllib.request, "urlopen", urlopen)

    result = extract_live_denue(small_page_config, tmp_path, token="tok", run_id="pagination-run")

    assert result.object_count == 3


def test_extract_live_denue_retries_and_masks_token_on_failure(
    tmp_path, source_config, monkeypatch
) -> None:
    import zmg_cafes_etl.config as config_module

    one_municipality_config = config_module.SourceConfig(
        name=source_config.name,
        access_method=source_config.access_method,
        endpoint=source_config.endpoint,
        timeout_seconds=source_config.timeout_seconds,
        max_retries=0,
        retry_backoff_seconds=0,
        study_area=source_config.study_area,
        scian_class=source_config.scian_class,
        page_size=source_config.page_size,
        municipalities=(source_config.municipalities[0],),
    )

    def urlopen(request, timeout):
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(extract_denue_module.urllib.request, "urlopen", urlopen)

    with pytest.raises(ExtractionError) as excinfo:
        extract_live_denue(one_municipality_config, tmp_path, token="super-secret")

    assert "super-secret" not in str(excinfo.value)
    assert "***" in str(excinfo.value)
