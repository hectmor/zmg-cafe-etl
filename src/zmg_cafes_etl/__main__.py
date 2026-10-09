"""Command-line entry point for the extraction milestone."""

import argparse
import json
from pathlib import Path

from .config import ConfigurationError, load_source_config
from .extract import ExtractionError, extract_live, extract_offline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract and preserve café source data")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--offline", type=Path, help="Read an existing Overpass JSON snapshot")
    mode.add_argument(
        "--live", action="store_true", help="Request the configured Overpass endpoint"
    )
    parser.add_argument("--config", type=Path, default=Path("config/sources.yaml"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--source", default="openstreetmap")
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

    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "source": result.source,
                "object_count": result.object_count,
                "raw_path": str(result.raw_path),
                "metadata_path": str(result.metadata_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
