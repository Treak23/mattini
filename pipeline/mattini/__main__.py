"""Command line: `python -m mattini <command>`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mattini import download, lock, terrain
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
    pin = commands.add_parser(
        "lock", help="pin the published SHA-256 of the inputs in config/datasets.lock.json"
    )
    pin.add_argument("dataset", choices=["terrain"], help="terrain: swissALTI3D, village area")
    fetch = commands.add_parser("download", help="fetch and verify pinned swisstopo inputs")
    fetch.add_argument("dataset", choices=["terrain"], help="terrain: swissALTI3D, village area")
    fetch.add_argument(
        "--out", default=download.DEFAULT_OUT, help="download root (default: data/raw)"
    )
    build = commands.add_parser(
        "terrain", help="build the terrain heights from the downloaded tiles, then the manifest"
    )
    build.add_argument(
        "--raw", default=download.DEFAULT_OUT, help="download root (default: data/raw)"
    )
    build.add_argument(
        "--out", default=DEFAULT_OUT, help="output directory (default: game/assets/generated)"
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "manifest":
            print(write_manifest(args.out))
        elif args.command == "lock":
            pinned = lock.build_lock(load_world(), load_datasets(), download.urllib_fetch_json)
            print(lock.write_lock(pinned, lock.LOCK_PATH))
        elif args.command == "download":
            return _download_terrain(Path(args.out))
        elif args.command == "terrain":
            print(_build_terrain(Path(args.raw), Path(args.out)))
    except (
        WorldConfigError,
        DatasetsConfigError,
        lock.LockError,
        download.DownloadError,
        terrain.TerrainError,
    ) as exc:
        print(f"mattini: error: {exc}", file=sys.stderr)
        return 1
    return 0


def _download_terrain(out_root: Path) -> int:
    """Fetch the village tiles the committed lock vouches for, with urllib.

    Progress on stderr, the provenance path on stdout.
    """
    fetched = []

    def fetch_file(url: str, dest: Path) -> None:
        print(f"fetching {url}", file=sys.stderr, flush=True)
        fetched.append(url)
        download.urllib_fetch_file(url, dest)

    world, datasets = load_world(), load_datasets()
    pinned = lock.load_lock(lock.LOCK_PATH)
    entries = download.download_terrain(
        world, datasets, out_root, download.urllib_fetch_json, fetch_file, lock=pinned
    )
    out_dir = out_root / download.DATASET / datasets[download.DATASET]["edition"]
    print(f"{len(entries)} tiles verified, {len(fetched)} fetches", file=sys.stderr)
    print(out_dir / download.PROVENANCE)
    return 0


def _build_terrain(raw_root: Path, out_dir: Path) -> Path:
    """Build the configured area's terrain, then the manifest; progress on stderr."""

    def progress(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    terrain.build_terrain(
        load_world(),
        load_datasets(),
        lock.load_lock(lock.LOCK_PATH),
        terrain.load_terrain_config(),
        raw_root,
        out_dir,
        progress=progress,
    )
    return write_manifest(out_dir)


if __name__ == "__main__":
    sys.exit(main())
