"""Command line: `python -m mattini <command>`.

`lock terrain|buildings`, `download terrain|buildings`, `terrain` and `buildings` all serve
the one area config/terrain.json names (briefs M2-01, M2-03, M2-04; M1 R1 T-06): the area
has one home.
`lock <dataset>` writes that dataset's entry of config/datasets.lock.json and keeps every
other entry (brief M2-03).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mattini import buildings, download, lock, terrain
from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.manifest import DEFAULT_OUT, write_manifest
from mattini.world import WorldConfigError, load_world

# the datasets `lock` and `download` serve: (their name in the configs and the lock, what
# they are made of)
DATASETS = {"buildings": (download.BUILDINGS, "sheets"), "terrain": (download.DATASET, "tiles")}
DATASETS_HELP = (
    "terrain: swissALTI3D; buildings: swissBUILDINGS3D 3.0, its map sheets; both for the "
    "area config/terrain.json names"
)


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
    pin.add_argument("dataset", choices=sorted(DATASETS), help=DATASETS_HELP)
    fetch = commands.add_parser("download", help="fetch and verify pinned swisstopo inputs")
    fetch.add_argument("dataset", choices=sorted(DATASETS), help=DATASETS_HELP)
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
    solids = commands.add_parser(
        "buildings",
        help="build the building chunks from the downloaded map sheets, then the manifest",
    )
    solids.add_argument(
        "--raw", default=download.DEFAULT_OUT, help="download root (default: data/raw)"
    )
    solids.add_argument(
        "--out", default=DEFAULT_OUT, help="output directory (default: game/assets/generated)"
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "manifest":
            print(write_manifest(args.out))
        elif args.command == "lock":
            print(_lock(args.dataset))
        elif args.command == "download":
            return _download(args.dataset, Path(args.out))
        elif args.command == "terrain":
            print(_build_terrain(Path(args.raw), Path(args.out)))
        elif args.command == "buildings":
            print(_build_buildings(Path(args.raw), Path(args.out)))
    except (
        WorldConfigError,
        DatasetsConfigError,
        lock.LockError,
        download.DownloadError,
        terrain.TerrainError,
        buildings.BuildingsError,
    ) as exc:
        print(f"mattini: error: {exc}", file=sys.stderr)
        return 1
    return 0


def _lock(dataset: str) -> Path:
    """Write the dataset's entry of the lock for the terrain config's area, from STAC only.

    Every other dataset's entry of the committed lock is kept; with no lock yet, the new
    one holds this entry alone. A lock that exists but cannot be read is refused before
    swisstopo is asked anything.
    """
    area = terrain.configured_area(terrain.load_terrain_config())
    world, datasets = load_world(), load_datasets()
    current = lock.load_lock_or_none(lock.LOCK_PATH)
    entry_of = lock.terrain_entry if dataset == "terrain" else lock.buildings_entry
    entry = entry_of(world, datasets, download.urllib_fetch_json, area=area)
    return lock.write_lock(lock.with_entry(current, DATASETS[dataset][0], entry), lock.LOCK_PATH)


def _download(dataset: str, out_root: Path) -> int:
    """Fetch the files of the terrain config's area that the committed lock vouches for.

    With urllib; progress on stderr, the provenance path on stdout.
    """
    name, unit = DATASETS[dataset]
    fetched = []

    def fetch_file(url: str, dest: Path) -> None:
        print(f"fetching {url}", file=sys.stderr, flush=True)
        fetched.append(url)
        download.urllib_fetch_file(url, dest)

    area = terrain.configured_area(terrain.load_terrain_config())
    world, datasets = load_world(), load_datasets()
    pinned = lock.load_lock(lock.LOCK_PATH)
    run = download.download_terrain if dataset == "terrain" else download.download_buildings
    entries = run(
        world, datasets, out_root, download.urllib_fetch_json, fetch_file, lock=pinned, area=area
    )
    out_dir = out_root / name / datasets[name]["edition"]
    print(f"{len(entries)} {unit} verified, {len(fetched)} fetches", file=sys.stderr)
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


def _build_buildings(raw_root: Path, out_dir: Path) -> Path:
    """Build the configured area's building chunks, then the manifest; progress on stderr."""

    def progress(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    buildings.build_buildings(
        load_world(),
        load_datasets(),
        lock.load_lock(lock.LOCK_PATH),
        buildings.load_buildings_config(),
        terrain.load_terrain_config(),
        raw_root,
        out_dir,
        progress=progress,
    )
    return write_manifest(out_dir)


if __name__ == "__main__":
    sys.exit(main())
