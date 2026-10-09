"""Load and validate non-secret project configuration."""

from dataclasses import dataclass
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
class SourceConfig:
    name: str
    endpoint: str
    query_template: str
    timeout_seconds: float
    max_retries: int
    retry_backoff_seconds: float
    study_area: BoundingBox


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
        return SourceConfig(
            name=source_data["name"],
            endpoint=source_data["endpoint"],
            query_template=source_data["query_template"],
            timeout_seconds=float(source_data["timeout_seconds"]),
            max_retries=int(source_data["max_retries"]),
            retry_backoff_seconds=float(source_data["retry_backoff_seconds"]),
            study_area=bbox,
        )
    except (KeyError, StopIteration, TypeError, ValueError) as error:
        raise ConfigurationError(
            f"Invalid or missing configuration for source: {source_name}"
        ) from error


def _validate_bbox(bbox: BoundingBox) -> None:
    if not (-90 <= bbox.south < bbox.north <= 90):
        raise ConfigurationError("Bounding box latitude values are invalid")
    if not (-180 <= bbox.west < bbox.east <= 180):
        raise ConfigurationError("Bounding box longitude values are invalid")


def render_query(source_config: SourceConfig) -> str:
    """Render the configured source query for the configured study area."""

    values: dict[str, Any] = source_config.study_area.as_format_values()
    return source_config.query_template.format(**values)
