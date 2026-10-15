"""Extract INEGI DENUE responses and preserve immutable raw snapshots.

Reuses the Overpass extractor's snapshot machinery (`_build_result` in
`extract.py`): every DENUE record is mapped into the same generic
`{"type", "id", "tags", ...}` element shape Overpass already produces, with
every original DENUE field kept alongside it, so the existing
transform/validate pipeline and raw-snapshot writer work unchanged.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Municipality, SourceConfig
from .extract import ExtractionError, ExtractionResult, _build_result

_DEFAULT_PAGE_SIZE = 250


def extract_offline_denue(
    snapshot_path: Path,
    source_config: SourceConfig,
    raw_root: Path,
    *,
    run_id: str | None = None,
    retrieved_at: datetime | None = None,
) -> ExtractionResult:
    """Read a deterministic JSON array of DENUE records and preserve it as a run."""

    try:
        raw_records = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExtractionError(f"Could not read offline snapshot: {snapshot_path}") from error
    if not isinstance(raw_records, list):
        raise ExtractionError("DENUE offline snapshot must be a JSON array of records")

    return _build_result(
        payload={
            "elements": [
                _to_element(record, municipio=_clean_text(record.get("Municipio")))
                for record in raw_records
            ]
        },
        source_config=source_config,
        raw_root=raw_root,
        run_id=run_id,
        retrieved_at=retrieved_at,
        request_mode="offline",
        query=_describe_query(source_config),
    )


def extract_live_denue(
    source_config: SourceConfig,
    raw_root: Path,
    *,
    token: str,
    run_id: str | None = None,
    retrieved_at: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ExtractionResult:
    """Page through every configured ZMG municipality and preserve one combined run."""

    if not token:
        raise ExtractionError("INEGI DENUE token is required for live extraction")

    elements: list[dict[str, Any]] = []
    for municipality in source_config.municipalities:
        records = _fetch_municipality(source_config, municipality, token, sleep)
        elements.extend(_to_element(record, municipio=municipality.name) for record in records)

    return _build_result(
        payload={"elements": elements},
        source_config=source_config,
        raw_root=raw_root,
        run_id=run_id,
        retrieved_at=retrieved_at,
        request_mode="live",
        query=_describe_query(source_config),
    )


def _fetch_municipality(
    source_config: SourceConfig,
    municipality: Municipality,
    token: str,
    sleep: Callable[[float], None],
) -> list[dict[str, Any]]:
    page_size = source_config.page_size or _DEFAULT_PAGE_SIZE
    records: list[dict[str, Any]] = []
    start = 1
    while True:
        end = start + page_size - 1
        window = _fetch_window(source_config, municipality, start, end, token, sleep)
        records.extend(window)
        if len(window) < page_size:
            return records
        start = end + 1


def _fetch_window(
    source_config: SourceConfig,
    municipality: Municipality,
    registro_inicial: int,
    registro_final: int,
    token: str,
    sleep: Callable[[float], None],
) -> list[dict[str, Any]]:
    url = _build_url(source_config, municipality, registro_inicial, registro_final, token)
    attempts = source_config.max_retries + 1
    last_error: Exception | None = None

    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "zmg-cafes-etl/0.1 (+https://github.com/hectmor/zmg-cafe-etl)"},
        )
        try:
            with urllib.request.urlopen(request, timeout=source_config.timeout_seconds) as response:
                raw_response = response.read()
            payload = json.loads(raw_response.decode("utf-8"))
            if not isinstance(payload, list):
                raise ExtractionError("DENUE response must be a JSON array of records")
            return payload
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as error:
            last_error = error
            if attempt < attempts - 1:
                sleep(source_config.retry_backoff_seconds * (2**attempt))

    masked_url = url.replace(token, "***") if token else url
    raise ExtractionError(
        f"DENUE extraction failed after {attempts} attempt(s) for municipio="
        f"{municipality.entidad}:{municipality.municipio}: {last_error} (url={masked_url})"
    ) from last_error


def _build_url(
    source_config: SourceConfig,
    municipality: Municipality,
    registro_inicial: int,
    registro_final: int,
    token: str,
) -> str:
    # BuscarAreaAct/{entidad}/{municipio}/{localidad}/{ageb}/{manzana}/
    # {sector}/{subsector}/{rama}/{clase}/{nombre}/{registro_inicial}/
    # {registro_final}/{id}/{token} — wildcards are the literal "0".
    segments = [
        municipality.entidad,
        municipality.municipio,
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        str(source_config.scian_class),
        "0",
        str(registro_inicial),
        str(registro_final),
        "0",
        token,
    ]
    return f"{source_config.endpoint.rstrip('/')}/" + "/".join(segments)


def _describe_query(source_config: SourceConfig) -> str:
    """Describe the DENUE request without ever including the token."""

    municipios = ",".join(f"{m.entidad}:{m.municipio}" for m in source_config.municipalities)
    return (
        f"INEGI DENUE BuscarAreaAct scian_class={source_config.scian_class} "
        f"municipios=[{municipios}] page_size={source_config.page_size}"
    )


def _to_element(record: Mapping[str, Any], *, municipio: str | None = None) -> dict[str, Any]:
    """Map one verbatim DENUE record into the shared Overpass-like element shape.

    Every original DENUE field is kept; `type`/`id`/`tags` are added as
    derived routing keys (mirroring how Overpass elements natively carry
    them) so `validate.read_identity` and `transform_payload` work unchanged.

    `municipio` is the official municipality already known from the query
    that produced this record (the config municipality for live extraction);
    it is never parsed from DENUE's free-text `Ubicacion`/`AreaGeo` fields.
    """

    element = dict(record)
    element["type"] = "economic_unit"
    element["id"] = _coerce_object_id(record.get("Id"))
    element["tags"] = {
        "name": _clean_text(record.get("Nombre")),
        "razon_social": _clean_text(record.get("Razon_social")),
        "clase_actividad": _clean_text(record.get("Clase_actividad")),
        "municipio": municipio,
    }
    return element


def _coerce_object_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _clean_text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None
