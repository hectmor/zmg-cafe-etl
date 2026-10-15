import json
import urllib.error
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

import zmg_cafes_etl.extract as extract_module
from zmg_cafes_etl.config import ConfigurationError, load_source_config, render_query
from zmg_cafes_etl.extract import ExtractionError, extract_live, extract_offline

ROOT = Path(__file__).parents[2]
CONFIG_PATH = ROOT / "config/sources.yaml"
FIXTURE_PATH = ROOT / "tests/fixtures/overpass_cafes_sample.json"


@pytest.fixture
def source_config():
    return load_source_config(CONFIG_PATH)


def test_render_query_uses_configured_study_area(source_config) -> None:
    query = render_query(source_config)

    assert "nwr[amenity=cafe](20.52,-103.55,20.82,-103.15);" in query


def test_extract_offline_preserves_payload_and_metadata(tmp_path, source_config) -> None:
    retrieved_at = datetime(2026, 2, 3, 10, 30, tzinfo=UTC)
    result = extract_offline(
        FIXTURE_PATH,
        source_config,
        tmp_path,
        run_id="run-001",
        retrieved_at=retrieved_at,
    )

    assert result.object_count == 4
    assert result.raw_path == tmp_path / "openstreetmap/2026/02/03/run-001.json"
    assert json.loads(result.raw_path.read_text(encoding="utf-8")) == json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run-001"
    assert metadata["request_mode"] == "offline"
    assert metadata["object_count"] == 4
    assert len(metadata["query_hash"]) == 64


def test_extract_offline_refuses_to_overwrite_run(tmp_path, source_config) -> None:
    kwargs = {
        "run_id": "run-001",
        "retrieved_at": datetime(2026, 2, 3, tzinfo=UTC),
    }
    extract_offline(FIXTURE_PATH, source_config, tmp_path, **kwargs)

    with pytest.raises(ExtractionError, match="Refusing to overwrite"):
        extract_offline(FIXTURE_PATH, source_config, tmp_path, **kwargs)


@pytest.mark.parametrize("payload", [{}, {"elements": "invalid"}, []])
def test_extract_offline_rejects_malformed_payload(tmp_path, source_config, payload) -> None:
    snapshot = tmp_path / "invalid.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ExtractionError, match="elements|JSON object"):
        extract_offline(snapshot, source_config, tmp_path / "raw")


def test_extract_offline_accepts_empty_result_set(tmp_path, source_config) -> None:
    snapshot = tmp_path / "empty.json"
    snapshot.write_text(json.dumps({"version": 0.6, "elements": []}), encoding="utf-8")

    result = extract_offline(snapshot, source_config, tmp_path / "raw", run_id="empty-run")

    assert result.object_count == 0


def test_extract_live_posts_the_query_as_form_data(tmp_path, source_config, monkeypatch) -> None:
    calls = []

    class Response:
        def read(self):
            return FIXTURE_PATH.read_bytes()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    monkeypatch.setattr(extract_module.urllib.request, "urlopen", urlopen)

    result = extract_live(source_config, tmp_path, run_id="live-run")

    assert result.object_count == 4
    assert calls[0][1] == source_config.timeout_seconds
    assert urllib.parse.parse_qs(calls[0][0].data.decode("utf-8")) == {
        "data": [render_query(source_config)]
    }
    assert calls[0][0].get_header("User-agent")


def test_extract_live_retries_transport_errors(tmp_path, source_config, monkeypatch) -> None:
    attempts = []
    sleeps = []

    class Response:
        def read(self):
            return FIXTURE_PATH.read_bytes()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    def urlopen(*_, **__):
        attempts.append(None)
        if len(attempts) == 1:
            raise urllib.error.URLError("temporary failure")
        return Response()

    monkeypatch.setattr(extract_module.urllib.request, "urlopen", urlopen)

    extract_live(source_config, tmp_path, run_id="retry-run", sleep=sleeps.append)

    assert len(attempts) == 2
    assert sleeps == [source_config.retry_backoff_seconds]


def test_extract_live_rejects_a_response_without_elements(
    tmp_path, source_config, monkeypatch
) -> None:
    class Response:
        def read(self):
            return b"{}"

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    monkeypatch.setattr(extract_module.urllib.request, "urlopen", lambda *_, **__: Response())

    with pytest.raises(ExtractionError, match="elements"):
        extract_live(source_config, tmp_path)


def test_snapshot_write_removes_raw_file_when_metadata_publish_fails(
    tmp_path, source_config, monkeypatch
) -> None:
    original_link = extract_module.os.link
    link_count = 0

    def link(source, destination):
        nonlocal link_count
        link_count += 1
        if link_count == 2:
            raise OSError("metadata publish failed")
        original_link(source, destination)

    monkeypatch.setattr(extract_module.os, "link", link)

    with pytest.raises(ExtractionError, match="Could not preserve"):
        extract_offline(
            FIXTURE_PATH,
            source_config,
            tmp_path,
            run_id="failed-run",
            retrieved_at=datetime(2026, 2, 3, tzinfo=UTC),
        )

    raw_path = tmp_path / "openstreetmap/2026/02/03/failed-run.json"
    metadata_path = tmp_path / "openstreetmap/2026/02/03/failed-run.metadata.json"
    assert not raw_path.exists()
    assert not metadata_path.exists()


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("timeout_seconds", 0),
        ("max_retries", -1),
        ("retry_backoff_seconds", -1),
    ],
)
def test_load_source_config_rejects_invalid_request_settings(tmp_path, setting, value) -> None:
    document = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    document["sources"][0][setting] = value
    config_path = tmp_path / "sources.yaml"
    config_path.write_text(yaml.safe_dump(document), encoding="utf-8")

    with pytest.raises(ConfigurationError, match="timeout|retries|backoff"):
        load_source_config(config_path)
