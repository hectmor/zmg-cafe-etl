"""Structural tests for the Leaflet frontend contract."""

from pathlib import Path

ROOT = Path(__file__).parents[2]
FRONTEND = ROOT / "frontend"
INDEX_HTML = (FRONTEND / "index.html").read_text(encoding="utf-8")
APP_JS = (FRONTEND / "app.js").read_text(encoding="utf-8")
STYLE_CSS = (FRONTEND / "style.css").read_text(encoding="utf-8")


def test_frontend_declares_map_search_filter_status_and_count() -> None:
    assert 'id="map"' in INDEX_HTML
    assert 'id="search"' in INDEX_HTML
    assert 'id="type-filter"' in INDEX_HTML
    assert 'id="status"' in INDEX_HTML
    assert 'id="count"' in INDEX_HTML


def test_frontend_credits_openstreetmap_overpass_and_leaflet() -> None:
    assert "OpenStreetMap" in INDEX_HTML
    assert "Overpass" in INDEX_HTML
    assert "leafletjs.com" in INDEX_HTML
    assert "ZMG Cafés ETL" in INDEX_HTML


def test_frontend_loads_leaflet_from_a_pinned_version() -> None:
    assert "leaflet@1.9.4/dist/leaflet.js" in INDEX_HTML
    assert "leaflet@1.9.4/dist/leaflet.css" in INDEX_HTML


def test_frontend_reads_only_the_public_api_endpoints() -> None:
    assert "/geojson/cafes" in APP_JS
    assert "postgres" not in APP_JS.lower()
    assert "staging." not in APP_JS
    assert "raw." not in APP_JS
    assert "fetch(" in APP_JS


def test_frontend_renders_loading_ready_and_error_states() -> None:
    for state in ('"loading"', '"ready"', '"error"'):
        assert state in APP_JS
    assert "data-state" in STYLE_CSS or "data-state" in APP_JS


def test_frontend_orders_geojson_coordinates_as_longitude_latitude() -> None:
    assert "MAP_CENTER = [20.6736, -103.344]" in APP_JS
    assert "L.geoJSON" in APP_JS
