import pytest

from zmg_cafes_etl.__main__ import _resolve_denue_token
from zmg_cafes_etl.extract import ExtractionError


def test_resolve_denue_token_returns_the_configured_value(monkeypatch) -> None:
    monkeypatch.setenv("INEGI_DENUE_TOKEN", "a-real-token")

    assert _resolve_denue_token() == "a-real-token"


def test_resolve_denue_token_fails_explicitly_when_missing(monkeypatch) -> None:
    monkeypatch.delenv("INEGI_DENUE_TOKEN", raising=False)

    with pytest.raises(ExtractionError, match="INEGI_DENUE_TOKEN"):
        _resolve_denue_token()
