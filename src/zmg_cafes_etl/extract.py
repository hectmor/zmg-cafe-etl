"""Extract Overpass responses and preserve immutable raw snapshots."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import SourceConfig, render_query


class ExtractionError(RuntimeError):
    """Raised when extraction cannot produce a valid source response."""


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    run_id: str
    source: str
    retrieved_at: datetime
    query: str
    query_hash: str
    payload: dict[str, Any]
    raw_path: Path
    metadata_path: Path

    @property
    def object_count(self) -> int:
        """Return the number of source objects in the response."""

        return len(self.payload["elements"])


def extract_offline(
    snapshot_path: Path,
    source_config: SourceConfig,
    raw_root: Path,
    *,
    run_id: str | None = None,
    retrieved_at: datetime | None = None,
) -> ExtractionResult:
    """Read a deterministic JSON snapshot and preserve it as a new raw run."""

    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ExtractionError(f"Could not read offline snapshot: {snapshot_path}") from error

    return _build_result(
        payload=payload,
        source_config=source_config,
        raw_root=raw_root,
        run_id=run_id,
        retrieved_at=retrieved_at,
        request_mode="offline",
    )


def extract_live(
    source_config: SourceConfig,
    raw_root: Path,
    *,
    run_id: str | None = None,
    retrieved_at: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> ExtractionResult:
    """Request Overpass data with bounded retries and preserve the response."""

    query = render_query(source_config)
    body = query.encode("utf-8")
    attempts = source_config.max_retries + 1
    last_error: Exception | None = None

    for attempt in range(attempts):
        request = urllib.request.Request(
            source_config.endpoint,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=source_config.timeout_seconds) as response:
                raw_response = response.read()
            payload = json.loads(raw_response.decode("utf-8"))
            return _build_result(
                payload=payload,
                source_config=source_config,
                raw_root=raw_root,
                run_id=run_id,
                retrieved_at=retrieved_at,
                request_mode="live",
                query=query,
            )
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as error:
            last_error = error
            if attempt < attempts - 1:
                sleep(source_config.retry_backoff_seconds * (2**attempt))

    raise ExtractionError(
        f"Overpass extraction failed after {attempts} attempt(s): {last_error}"
    ) from last_error


def _build_result(
    *,
    payload: Any,
    source_config: SourceConfig,
    raw_root: Path,
    run_id: str | None,
    retrieved_at: datetime | None,
    request_mode: str,
    query: str | None = None,
) -> ExtractionResult:
    _validate_payload(payload)
    resolved_run_id = run_id or str(uuid4())
    resolved_retrieved_at = retrieved_at or datetime.now(UTC)
    resolved_query = query or render_query(source_config)
    query_hash = hashlib.sha256(resolved_query.encode("utf-8")).hexdigest()
    raw_path, metadata_path = _snapshot_paths(
        raw_root=raw_root,
        source=source_config.name,
        run_id=resolved_run_id,
        retrieved_at=resolved_retrieved_at,
    )

    if raw_path.exists() or metadata_path.exists():
        raise ExtractionError(f"Refusing to overwrite existing raw run: {resolved_run_id}")

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata = {
        "run_id": resolved_run_id,
        "source": source_config.name,
        "retrieved_at": resolved_retrieved_at.isoformat(),
        "query": resolved_query,
        "query_hash": query_hash,
        "request_mode": request_mode,
        "object_count": len(payload["elements"]),
        "snapshot_path": str(raw_path),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return ExtractionResult(
        run_id=resolved_run_id,
        source=source_config.name,
        retrieved_at=resolved_retrieved_at,
        query=resolved_query,
        query_hash=query_hash,
        payload=payload,
        raw_path=raw_path,
        metadata_path=metadata_path,
    )


def _snapshot_paths(
    *, raw_root: Path, source: str, run_id: str, retrieved_at: datetime
) -> tuple[Path, Path]:
    partition = raw_root / source / retrieved_at.strftime("%Y/%m/%d")
    return partition / f"{run_id}.json", partition / f"{run_id}.metadata.json"


def _validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ExtractionError("Overpass response must be a JSON object")
    if not isinstance(payload.get("elements"), list):
        raise ExtractionError("Overpass response must contain an 'elements' list")
