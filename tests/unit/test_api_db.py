"""Unit tests for the API's DSN handling, isolated from a real connection."""

from api.db import AnalyticsStore


def test_analytics_store_normalizes_sqlalchemy_style_dsn() -> None:
    store = AnalyticsStore("postgresql+psycopg://user:pass@localhost:5432/zmg_cafes")

    assert store._dsn == "postgresql://user:pass@localhost:5432/zmg_cafes"


def test_analytics_store_leaves_a_plain_dsn_untouched() -> None:
    store = AnalyticsStore("postgresql://user:pass@localhost:5432/zmg_cafes")

    assert store._dsn == "postgresql://user:pass@localhost:5432/zmg_cafes"
