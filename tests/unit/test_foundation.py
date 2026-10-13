import json
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]


def test_source_configuration_defines_provisional_area_and_overpass_contract() -> None:
    config = yaml.safe_load((ROOT / "config/sources.yaml").read_text(encoding="utf-8"))

    assert config["study_area"]["coordinate_reference_system"] == "EPSG:4326"
    assert set(config["study_area"]["bbox"]) == {"south", "west", "north", "east"}
    source = config["sources"][0]
    assert source["name"] == "openstreetmap"
    assert "nwr[amenity=cafe]" in source["query_template"]
    assert source["object_identity"] == "source + object_type + object_id"


def test_fixture_is_valid_overpass_shape_and_contains_multiple_object_types() -> None:
    payload = json.loads(
        (ROOT / "tests/fixtures/overpass_cafes_sample.json").read_text(encoding="utf-8")
    )

    assert isinstance(payload["elements"], list)
    assert {element["type"] for element in payload["elements"]} == {"node", "way", "relation"}
    assert all("id" in element and "tags" in element for element in payload["elements"])
