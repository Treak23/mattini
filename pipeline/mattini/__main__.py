"""Command line: `python -m mattini <command>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mattini import download
from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.manifest import DEFAULT_OUT, write_manifest
from mattini.world import WorldConfigError, load_world


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mattini")
    commands = parser.add_subparsers(dest="command", required=True)
    manifest = commands.add_parser("manifest", help="write the generated manifest.json")
    manifest.add_argument(
        "--out", default=DEFAULT_OUT, help="output directory (default: game/assets/generated)"
    )
    fetch = commands.add_parser("download", help="fetch and verify pinned swisstopo inputs")
    fetch.add_argument("dataset", choices=["terrain"], help="terrain: swissALTI3D, village area")
    fetch.add_argument(
        "--out", default=download.DEFAULT_OUT, help="download root (default: data/raw)"
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "manifest":
            print(write_manifest(args.out))
        elif args.command == "download":
            return _download_terrain(Path(args.out))
    except (WorldConfigError, DatasetsConfigError, download.DownloadError) as exc:
        print(f"mattini: error: {exc}", file=sys.stderr)
        return 1
    return 0


def _download_terrain(out_root: Path) -> int:
    """Fetch the village tiles with urllib; progress on stderr, the provenance path on stdout."""
    fetched = []

    def fetch_file(url: str, dest: Path) -> None:
        print(f"fetching {url}", file=sys.stderr, flush=True)
        fetched.append(url)
        download.urllib_fetch_file(url, dest)

    datasets = load_datasets()
    entries = download.download_terrain(
        load_world(), datasets, out_root, download.urllib_fetch_json, fetch_file
    )
    out_dir = out_root / download.DATASET / datasets[download.DATASET]["edition"]
    print(f"{len(entries)} tiles verified, {len(fetched)} fetches", file=sys.stderr)
    print(out_dir / download.PROVENANCE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
