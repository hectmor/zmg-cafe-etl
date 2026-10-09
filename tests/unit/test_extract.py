import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from zmg_cafes_etl.config import load_source_config, render_query
from zmg_cafes_etl.extract import ExtractionError, extract_offline

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

    assert result.object_count == 3
    assert result.raw_path == tmp_path / "openstreetmap/2026/02/03/run-001.json"
    assert json.loads(result.raw_path.read_text(encoding="utf-8")) == json.loads(
        FIXTURE_PATH.read_text(encoding="utf-8")
    )
    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run-001"
    assert metadata["request_mode"] == "offline"
    assert metadata["object_count"] == 3
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
