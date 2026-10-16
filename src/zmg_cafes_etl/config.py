"""Load and validate non-secret project configuration."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when the source configuration is incomplete or invalid."""


@dataclass(frozen=True, slots=True)
class BoundingBox:
    south: float
    west: float
    north: float
    east: float

    def as_format_values(self) -> dict[str, float]:
        return {
            "south": self.south,
            "west": self.west,
            "north": self.north,
            "east": self.east,
        }


@dataclass(frozen=True, slots=True)
class Municipality:
    """One ZMG municipality as addressed by the INEGI DENUE API."""

    name: str
    entidad: str
    municipio: str


@dataclass(frozen=True, slots=True)
class SourceConfig:
    name: str
    access_method: str
    endpoint: str
    timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float
    study_area: BoundingBox
    query_template: str | None = None
    scian_class: str | None = None
    page_size: int | None = None
    municipalities: tuple[Municipality, ...] = ()


def load_source_config(config_path: Path, source_name: str = "openstreetmap") -> SourceConfig:
    """Load one source definition from a YAML configuration file."""

    try:
        document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigurationError(f"Could not read configuration: {config_path}") from error

    if not isinstance(document, dict):
        raise ConfigurationError("Source configuration must be a mapping")

    try:
        area_data = document["study_area"]["bbox"]
        bbox = BoundingBox(
            south=float(area_data["south"]),
            west=float(area_data["west"]),
            north=float(area_data["north"]),
            east=float(area_data["east"]),
        )
        _validate_bbox(bbox)
        source_data = next(
            source for source in document["sources"] if source["name"] == source_name
        )
        timeout_seconds = float(source_data["timeout_seconds"])
        max_retries = int(source_data["max_retries"])
        retry_backoff_seconds = float(source_data["retry_backoff_seconds"])
        _validate_request_settings(timeout_seconds, max_retries, retry_backoff_seconds)
        access_method = str(source_data.get("access_method", "overpass_api"))

        if access_method == "inegi_denue_api":
            query_template = None
            scian_class, page_size, municipalities = _load_denue_settings(source_data)
        else:
            query_template = source_data["query_template"]
            scian_class, page_size, municipalities = None, None, ()

        return SourceConfig(
            name=source_data["name"],
            access_method=access_method,
            endpoint=source_data["endpoint"],
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
            study_area=bbox,
            query_template=query_template,
            scian_class=scian_class,
            page_size=page_size,
            municipalities=municipalities,
        )
    except ConfigurationError:
        raise
    except (KeyError, StopIteration, TypeError, ValueError) as error:
        raise ConfigurationError(
            f"Invalid or missing configuration for source: {source_name}"
        ) from error


def _load_denue_settings(
    source_data: dict[str, Any],
) -> tuple[str, int, tuple[Municipality, ...]]:
    scian_class = str(source_data["scian_class"])
    page_size = int(source_data["page_size"])
    if page_size <= 0:
        raise ConfigurationError("DENUE page size must be a positive integer")
    municipalities = tuple(
        Municipality(
            name=str(item["name"]),
            entidad=str(item["entidad"]),
            municipio=str(item["municipio"]),
        )
        for item in source_data["municipalities"]
    )
    if not municipalities:
        raise ConfigurationError("DENUE source requires at least one municipality")
    return scian_class, page_size, municipalities


def _validate_bbox(bbox: BoundingBox) -> None:
    if not (-90 <= bbox.south < bbox.north <= 90):
        raise ConfigurationError("Bounding box latitude values are invalid")
    if not (-180 <= bbox.west < bbox.east <= 180):
        raise ConfigurationError("Bounding box longitude values are invalid")


def _validate_request_settings(
    timeout_seconds: float, max_retries: int, retry_backoff_seconds: float
) -> None:
    if not isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ConfigurationError("Source timeout must be a positive finite number")
    if max_retries < 0:
        raise ConfigurationError("Source max retries cannot be negative")
    if not isfinite(retry_backoff_seconds) or retry_backoff_seconds < 0:
        raise ConfigurationError("Source retry backoff must be a non-negative finite number")


def render_query(source_config: SourceConfig) -> str:
    """Render the configured source query for the configured study area."""

    if source_config.query_template is None:
        raise ConfigurationError(f"Source '{source_config.name}' has no query template to render")
    values: dict[str, Any] = source_config.study_area.as_format_values()
    return source_config.query_template.format(**values)
