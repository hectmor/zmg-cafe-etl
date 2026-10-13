"""Command-line entry point for the extraction, transformation and load pipeline."""

import argparse
import json
import os
from pathlib import Path

from .config import ConfigurationError, load_source_config
from .extract import ExtractionError, extract_live, extract_offline
from .load import LoadError, load_run
from .transform import transform_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract, transform and load café source data")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline", type=Path, help="Read an existing Overpass JSON snapshot")
    mode.add_argument(
        "--live", action="store_true", help="Request the configured Overpass endpoint"
    )
    parser.add_argument("--config", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--source", default="openstreetmap")
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL DSN used to persist the run; defaults to the DATABASE_URL variable",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        source_config = load_source_config(args.config, args.source)
        if args.offline:
            result = extract_offline(args.offline, source_config, args.raw_root)
        else:
            result = extract_live(source_config, args.raw_root)
    except (ConfigurationError, ExtractionError) as error:
        print(f"Extraction failed: {error}")
        return 1

    transformation = transform_payload(
        result.payload,
        source=result.source,
        retrieved_at=result.retrieved_at,
        run_id=result.run_id,
        study_area=source_config.study_area,
    )

    summary = {
        "run_id": result.run_id,
        "source": result.source,
        "object_count": result.object_count,
        "raw_path": str(result.raw_path),
        "metadata_path": str(result.metadata_path),
        "accepted": len(transformation.accepted),
        "rejected": len(transformation.rejected),
    }

    dsn = args.database_url or os.environ.get("DATABASE_URL")
    if dsn:
        try:
            metrics = load_run(result, transformation, dsn=dsn)
        except LoadError as error:
            print(f"Load failed: {error}")
            return 1
        summary.update({"inserted": metrics.inserted, "updated": metrics.updated})

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
