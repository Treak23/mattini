"""Command line: `python -m mattini <command>`.

`lock` and `download` take terrain, buildings, photo, surface or tlm; they, `terrain` and
`buildings` all serve the one area config/terrain.json names (briefs M2-01, M2-03, M2-04,
M3-03; M1 R1 T-06): the area has one home. swissTLM3D (`tlm`) is national and has none.
`lock <dataset>` writes that dataset's entry of config/datasets.lock.json and keeps every
other entry (brief M2-03).

`photo`, `roofs`, `surfaces` and `trees` build the M3 steps' outputs as `terrain` and
`buildings` build theirs (brief M3-13); each then writes the manifest. They read the
datasets that `download` fetched, and a step without its download ends in one
`mattini: error:` line naming the `download` command.

A Ctrl-C ends any command with one line, `mattini: interrupted: ...` naming the command to
run again, and exit status 130, never a traceback (brief M3-03). `download tlm` keeps the
part of its file, and the next run resumes it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mattini import buildings, download, lock, photo, roofs, surfaces, terrain, trees
from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.manifest import DEFAULT_OUT, write_manifest
from mattini.world import WorldConfigError, load_world

# the datasets `lock` and `download` serve: (their name in the configs and the lock, what
# they are made of)
DATASETS = {
    "buildings": (download.BUILDINGS, "sheets"),
    "photo": (download.PHOTO, "tiles"),
    "surface": (download.SURFACE, "tiles"),
    "terrain": (download.DATASET, "tiles"),
    "tlm": (download.TLM, "file"),
}
# the M3 steps, in pipeline order: what each builds from the downloads
STEPS = {
    "photo": "build the aerial photo of the area from the downloaded tiles",
    "roofs": "measure each building's roof colour from the photo",
    "surfaces": "classify roads, paths, water and rock from swissTLM3D",
    "trees": "find the trees in the surface model",
}
DATASETS_HELP = (
    "terrain: swissALTI3D; buildings: swissBUILDINGS3D 3.0, its map sheets; photo: "
    "SWISSIMAGE 10 cm; surface: the swissSURFACE3D raster; all for the area "
    "config/terrain.json names; tlm: swissTLM3D, national (2.9 GB)"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mattini")
    commands = parser.add_subparsers(dest="command", required=True)
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
    for name, summary in STEPS.items():
        step = commands.add_parser(name, help=f"{summary}, then the manifest")
        step.add_argument(
            "--raw", default=download.DEFAULT_OUT, help="download root (default: data/raw)"
        )
        step.add_argument(
            "--out", default=DEFAULT_OUT, help="output directory (default: game/assets/generated)"
        )
    manifest = commands.add_parser("manifest", help="write the generated manifest.json")
    manifest.add_argument(
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
        elif args.command in STEPS:
            print(_build_step(args.command, Path(args.raw), Path(args.out)))
    except KeyboardInterrupt:
        command = f"python -m mattini {args.command}"
        if args.command in ("lock", "download"):
            command += f" {args.dataset}"
        kept = (
            "; any part of the file is kept and the next run resumes it"
            if (args.command, getattr(args, "dataset", None)) == ("download", "tlm")
            else ""
        )
        print(
            f"mattini: interrupted: `{command}` did not finish; run it again{kept}",
            file=sys.stderr,
        )
        return 130
    except (
        WorldConfigError,
        DatasetsConfigError,
        lock.LockError,
        download.DownloadError,
        terrain.TerrainError,
        buildings.BuildingsError,
        photo.PhotoError,
        roofs.RoofsError,
        surfaces.SurfacesError,
        trees.TreesError,
    ) as exc:
        print(f"mattini: error: {exc}", file=sys.stderr)
        return 1
    return 0


def _lock(dataset: str) -> Path:
    """Write the dataset's entry of the lock, from STAC only.

    The tile and sheet datasets read the terrain config's area; swissTLM3D is national. Every
    other dataset's entry of the committed lock is kept; with no lock yet, the new one holds
    this entry alone. A lock that exists but cannot be read is refused before swisstopo is
    asked anything.
    """
    if dataset == "tlm":
        datasets = load_datasets()
        current = lock.load_lock_or_none(lock.LOCK_PATH)
        entry = lock.tlm_entry(datasets, download.urllib_fetch_json)
    else:
        area = terrain.configured_area(terrain.load_terrain_config())
        world, datasets = load_world(), load_datasets()
        current = lock.load_lock_or_none(lock.LOCK_PATH)
        entry_of = {
            "terrain": lock.terrain_entry,
            "buildings": lock.buildings_entry,
            "photo": lock.photo_entry,
            "surface": lock.surface_entry,
        }[dataset]
        entry = entry_of(world, datasets, download.urllib_fetch_json, area=area)
    return lock.write_lock(lock.with_entry(current, DATASETS[dataset][0], entry), lock.LOCK_PATH)


def _download(dataset: str, out_root: Path) -> int:
    """Fetch the files of the terrain config's area that the committed lock vouches for.

    With urllib; progress on stderr, the provenance path on stdout. swissTLM3D is one national
    file, resumed when a transfer is cut (`download.download_tlm`).
    """
    name, unit = DATASETS[dataset]
    fetched = []

    def say(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    def fetch_file(url: str, dest: Path) -> None:
        say(f"fetching {url}")
        fetched.append(url)
        download.urllib_fetch_file(url, dest)

    def fetch_range(url: str, part: Path, start: int) -> None:
        fetched.append(url)
        download.urllib_fetch_range(url, part, start, progress=say)

    if dataset == "tlm":
        datasets = load_datasets()
        pinned = lock.load_lock(lock.LOCK_PATH)
        download.download_tlm(
            datasets,
            out_root,
            download.urllib_fetch_json,
            download.urllib_head,
            fetch_range,
            lock=pinned,
            progress=say,
        )
        count = 1
    else:
        area = terrain.configured_area(terrain.load_terrain_config())
        world, datasets = load_world(), load_datasets()
        pinned = lock.load_lock(lock.LOCK_PATH)
        run = {
            "terrain": download.download_terrain,
            "buildings": download.download_buildings,
            "photo": download.download_photo,
            "surface": download.download_surface,
        }[dataset]
        count = len(
            run(
                world,
                datasets,
                out_root,
                download.urllib_fetch_json,
                fetch_file,
                lock=pinned,
                area=area,
            )
        )
    out_dir = out_root / name / download.raw_folder(datasets, name)
    print(f"{count} {unit} verified, {len(fetched)} fetches", file=sys.stderr)
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


def _build_step(step: str, raw_root: Path, out_dir: Path) -> Path:
    """Build one of the M3 steps (`STEPS`) for the configured area, then the manifest.

    Each loads config/world.json, datasets.json, datasets.lock.json and its own config, the
    roofs and the trees config/terrain.json too, and calls its module's `build_<step>`
    through the module, so a step is replaced in one place only. Progress on stderr.
    """

    def progress(message: str) -> None:
        print(message, file=sys.stderr, flush=True)

    world, datasets, pinned = load_world(), load_datasets(), lock.load_lock(lock.LOCK_PATH)
    if step == "photo":
        photo.build_photo(
            world, datasets, pinned, photo.load_photo_config(), raw_root, out_dir, progress=progress
        )
    elif step == "roofs":
        roofs.build_roofs(
            world,
            datasets,
            pinned,
            roofs.load_roofs_config(),
            terrain.load_terrain_config(),
            raw_root,
            out_dir,
            progress=progress,
        )
    elif step == "surfaces":
        surfaces.build_surfaces(
            world,
            datasets,
            pinned,
            surfaces.load_surfaces_config(),
            raw_root,
            out_dir,
            progress=progress,
        )
    else:
        trees.build_trees(
            world,
            datasets,
            pinned,
            trees.load_trees_config(),
            terrain.load_terrain_config(),
            raw_root,
            out_dir,
            progress=progress,
        )
    return write_manifest(out_dir)


if __name__ == "__main__":
    sys.exit(main())
