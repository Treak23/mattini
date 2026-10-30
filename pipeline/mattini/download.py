"""swisstopo downloads for the configured area (briefs M0-04, M2-01, M2-03, M3-03; SPEC §5, §7-§9).

swissALTI3D (`download terrain`): the 1 km tiles covering the area config/terrain.json names
(its one area; the box is in config/world.json) are fetched at the edition and resolution
pinned in config/datasets.json, never "the latest" (Hard Rule 5); the caller passes the
area, so the download, the lock and the terrain step serve one area (M1 R1 T-06). STAC items are
addressed by id. Every file is checked against swisstopo's published SHA-256 (`file:checksum`,
a `1220…` multihash): it downloads to `<name>.part`, is verified, and only then takes its
final name, so a file under its final name matched the published checksum when it was
written. A mismatch deletes the temporary file; after one retry it is a DownloadError naming
the tile and the URL (Hard Rule 2). A file already on disk that matches is not fetched again.

Every tile's published file name and SHA-256 must equal the tile lock's
(config/datasets.lock.json, brief M1-01): the lock must first fit the config and pin
exactly the area's tiles (`lock.fit_problem`, before swisstopo is asked anything, brief
M3-01), then all the STAC items are read and compared with the lock before any file is
fetched or deleted, so a tile swisstopo republished inside the edition is refused, never
adopted silently (Hard Rule 5); `python -m mattini lock terrain` adopts it deliberately, and
design then recomputes the expected values in config/terrain.json, which record the lock
entry they were computed from (brief M2-07).

`provenance.json` records what was fetched and its attribution: sorted keys, LF endings, no
times, no absolute paths, so two runs on the same inputs write identical bytes. It is
removed before the run's first change on disk (an unlink or a file fetch) and written at
its end, so it exists only after a run that completed; a run that fails before changing
anything leaves the previous one as it was.

swissBUILDINGS3D 3.0 (`download buildings`, brief M2-03) follows the same rules, for the
map sheets of the pinned edition that `sheets.sheets_near` gives for the area's box (every
sheet within 100 m, SPEC §8 *Sheets*): item `swissbuildings3d_3_0_<edition>_<sheet>`, the
one asset whose key ends `_2056_5728.gdb.zip`, compared with the lock's `swissbuildings3d`
entry before anything on disk changes, into `<out_root>/swissbuildings3d/<edition>/` with
its own provenance.json. The lock's entry must pin exactly the area's sheets, as the
buildings step and the manifest require (brief M2-07, M2 R1 I-04), by the same rule
(`lock.fit_problem`). A sheet swisstopo republished is adopted only by `python -m mattini
lock buildings`, and design then recomputes config/buildings.json. The zips are not opened
here (M2-04 reads them).

SWISSIMAGE 2023 (`download photo`, brief M3-03) is the terrain's flow for item
`swissimage-dop10_<edition>_<tile>` and the asset ending `_<resolution>_2056.tif`.
swissSURFACE3D (`download surface`) reads, per tile, only the item of the edition the lock
pins (`swisssurface3d-raster_<year>_<tile>`, the asset ending `_<resolution>_2056_5728.tif`);
choosing the edition is `lock surface`'s, which reads the item of every year in the config's
`editions` and needs exactly one to exist (HTTP 404 means absent, any other failure is
"cannot read the STAC item"). Their files go to `swissimage/<edition>/` and
`swisssurface3d/<editions joined by "-">/` under the root, each with its provenance.json.

swissTLM3D (`download tlm`) is one national file of 2.88 GB, `swisstlm3d_<edition>`'s asset
ending `_2056_5728.gdb.zip`: a verified file already on disk is kept with no request to the
file host; otherwise one HEAD (an `x-amz-meta-sha256` that is not the lock's is refused
before any GET), then GETs into `<file>.part` with `Range: bytes=<part size>-` once the part
holds bytes, at most five a round, since Python's urllib ends a body cut short without an
error (brain.md H9) and only the part's size shows the cut. The part is kept when a run
cannot finish (also on Ctrl-C), and the file takes its name only when its SHA-256 equals
the lock's. Every refusal of the TLM starts `swisstlm3d <edition>: `.

A datasets config without the dataset, and an area the sheet grid cannot place, are
DownloadErrors naming config/datasets.json or the world config and the area, never a
traceback (M2 R1 I-05); so is one that lists `editions` where the command needs one
`edition`, or the other way round (brief M3-03).
"""

from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mattini.sheets import sheets_near
from mattini.world import REPO, World

DATASET = "swissalti3d"
BUILDINGS = "swissbuildings3d"
PHOTO = "swissimage"
SURFACE = "swisssurface3d"
TLM = "swisstlm3d"
BUILDINGS_ITEM = "swissbuildings3d_3_0_{edition}_{sheet}"  # a STAC item of the collection
BUILDINGS_SUFFIX = "_2056_5728.gdb.zip"  # the zipped FileGDB; the item also holds a DWG
PHOTO_ITEM = "swissimage-dop10_{edition}_{tile}"
SURFACE_ITEM = "swisssurface3d-raster_{year}_{tile}"
TLM_ITEM = "swisstlm3d_{edition}"
TLM_SUFFIX = "_2056_5728.gdb.zip"  # the zipped FileGDB; the item also holds three other formats
STAC_ITEM = "https://data.geo.admin.ch/api/stac/v1/collections/{collection}/items/{item_id}"
DEFAULT_OUT = REPO / "data" / "raw"
PROVENANCE = "provenance.json"
PROVENANCE_SCHEMA = 1
TILE_M = 1000  # swissALTI3D tiles are 1 km squares named by their south-west corner in km
ATTEMPTS = 2  # the first fetch and the one retry
TLM_GETS = 5  # the GETs a round of the TLM file may make: a cut transfer is resumed
SHA256_MULTIHASH = re.compile(r"1220([0-9A-Fa-f]{64})")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
FETCH_ERRORS = (OSError, http.client.HTTPException)  # urllib's errors are OSErrors
TIMEOUT_S = 60
USER_AGENT = "mattini-pipeline"
LOCK_COMMAND = "python -m mattini lock terrain"
BUILDINGS_LOCK_COMMAND = "python -m mattini lock buildings"
PHOTO_LOCK_COMMAND = "python -m mattini lock photo"
SURFACE_LOCK_COMMAND = "python -m mattini lock surface"
TLM_LOCK_COMMAND = "python -m mattini lock tlm"
TLM_DOWNLOAD_COMMAND = "python -m mattini download tlm"
LOCK_COMMAND_OF = {  # dataset -> the command that writes its lock entry
    DATASET: LOCK_COMMAND,
    BUILDINGS: BUILDINGS_LOCK_COMMAND,
    PHOTO: PHOTO_LOCK_COMMAND,
    SURFACE: SURFACE_LOCK_COMMAND,
    TLM: TLM_LOCK_COMMAND,
}
DATASETS_CONFIG_NAME = "config/datasets.json"  # the home of the datasets, for messages
# the config whose expected values design recomputes when a dataset's inputs change, and
# the step the republish refusals name after the lock command (brief M2-07)
EXPECTED_CONFIG_NAMES = {
    DATASET: "config/terrain.json and config/trees.json",
    BUILDINGS: "config/buildings.json, config/roofs.json and config/trees.json",
    PHOTO: "config/photo.json and config/roofs.json",
    SURFACE: "config/trees.json",
    TLM: "config/surfaces.json and config/trees.json",
}
_RECOMPUTE = {
    name: f"then design recomputes the expected values in {config} (docs/SPEC.md §8)"
    for name, config in EXPECTED_CONFIG_NAMES.items()
}

FetchJson = Callable[[str], object]
FetchFile = Callable[[str, Path], None]
FetchHead = Callable[[str], tuple[int | None, str | None]]  # (Content-Length, x-amz-meta-sha256)
FetchRange = Callable[[str, Path, int], None]  # url, part file, first byte wanted
Progress = Callable[[str], None]


class DownloadError(RuntimeError):
    """A download could not be completed or verified; the message names the tile and URL."""


class CutTransfer(OSError):
    """A body that ended before the Content-Length the answer announced (a dropped connection)."""


class ResumeMismatch(OSError):
    """A 206 answer that does not start at the byte asked for: the part cannot be extended."""


def dataset_of(datasets: dict, name: str) -> dict:
    """The datasets config's entry for `name`; its absence is a DownloadError naming the file.

    `lock` and `download` read the collection and edition from it; without this check a
    datasets config lacking the dataset ended in a KeyError traceback (M2 R1 I-05).
    """
    if name not in datasets:
        raise DownloadError(
            f"{DATASETS_CONFIG_NAME} has no {name!r} dataset: its collection, edition and "
            f"attribution are read from there"
        )
    return datasets[name]


def edition_of(datasets: dict, name: str) -> str:
    """The one pinned `edition` of `name`; a dataset that lists `editions` is a DownloadError.

    The commands that read one edition (everything but swissSURFACE3D) refuse a config that
    lists several, naming config/datasets.json (brief M3-03, M2 R1 I-05).
    """
    config = dataset_of(datasets, name)
    if "edition" not in config:
        raise DownloadError(
            f"{DATASETS_CONFIG_NAME}: dataset {name!r} lists editions {config.get('editions')!r}; "
            f"this command reads one pinned edition"
        )
    return config["edition"]


def editions_of(datasets: dict, name: str) -> list[str]:
    """The `editions` of `name` (swissSURFACE3D); a dataset with one `edition` is refused."""
    config = dataset_of(datasets, name)
    if "editions" not in config:
        raise DownloadError(
            f"{DATASETS_CONFIG_NAME}: dataset {name!r} pins one edition "
            f"{config.get('edition')!r}; this command reads a list of editions"
        )
    return config["editions"]


def raw_folder(datasets: dict, name: str) -> str:
    """The folder under the download root for `name`: its edition, or its editions joined by `-`.

    `2024`, `2026-02` or `2021-2022` (brief M3-03): the layout the steps read.
    """
    config = dataset_of(datasets, name)
    return config["edition"] if "edition" in config else "-".join(editions_of(datasets, name))


def area_tiles(world: World, area: str) -> list[str]:
    """The ids (`<e km>-<n km>`) of the 1 km tiles the named area's box touches, sorted.

    East outer, north inner: the order of the download, provenance.json, the terrain step
    and the manifest's `source.tiles`.
    """
    e_min, e_max, n_min, n_max = world.area(area)
    east = range(math.floor(e_min / TILE_M), math.ceil(e_max / TILE_M))
    north = range(math.floor(n_min / TILE_M), math.ceil(n_max / TILE_M))
    return [f"{e}-{n}" for e in east for n in north]


def area_sheets(world: World, area: str) -> list[str]:
    """The map sheets the named area's buildings are read from, sorted as text.

    Every sheet within `sheets.DEFAULT_MARGIN_M` (100 m) of the area's box: a building can
    overhang its own sheet (SPEC §8 *Sheets*). The order of the download, the lock and
    provenance.json. A box the sheet grid cannot place (outside it, or within the margin
    of its east edge) is a DownloadError naming the area and the world config (M2 R1 I-05).
    """
    box = world.area(area)
    try:
        return sheets_near(box)
    except ValueError as exc:
        raise DownloadError(f"area {area!r} of {world.path}: {exc}") from exc


def parse_multihash_sha256(text: object) -> str:
    """The lower-case hex digest of a SHA-256 multihash (`1220` + 64 hex digits)."""
    match = SHA256_MULTIHASH.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise ValueError(f"not a SHA-256 multihash ('1220' + 64 hex digits): {text!r}")
    return match.group(1).lower()


@dataclass(frozen=True)
class PublishedAsset:
    """What a tile's STAC item publishes for the pinned edition and resolution.

    `edition` is the year of a swissSURFACE3D tile's item (a tile has one of several); None
    for the datasets that pin one edition.
    """

    tile: str
    item_id: str
    name: str
    href: str
    sha256: str
    edition: str | None = None


@dataclass(frozen=True)
class _TileSet:
    """What differs between the tile datasets that download alike (swissALTI3D, SWISSIMAGE)."""

    item: str  # the STAC item id: {edition} and {tile}
    suffix: str  # the asset key's ending: {tag} is the resolution as swisstopo writes it


_TILE_SETS = {
    DATASET: _TileSet(DATASET + "_{edition}_{tile}", "_{tag}_2056_5728.tif"),
    PHOTO: _TileSet(PHOTO_ITEM, "_{tag}_2056.tif"),
}


def published_assets(
    world: World, datasets: dict, fetch_json: FetchJson, *, area: str
) -> list[PublishedAsset]:
    """Read the STAC item of every swissALTI3D tile of `area`, in tile order; no file is fetched."""
    return _published_tiles(DATASET, world, datasets, fetch_json, area)


def published_photo(
    world: World, datasets: dict, fetch_json: FetchJson, *, area: str
) -> list[PublishedAsset]:
    """Read the STAC item of every SWISSIMAGE tile of `area`, in tile order; no file is fetched.

    Item `swissimage-dop10_<edition>_<tile>`, the asset ending `_<resolution>_2056.tif` (the
    item also holds the 2 m image, which is not it).
    """
    return _published_tiles(PHOTO, world, datasets, fetch_json, area)


def _published_tiles(
    dataset: str, world: World, datasets: dict, fetch_json: FetchJson, area: str
) -> list[PublishedAsset]:
    config = dataset_of(datasets, dataset)
    spec = _TILE_SETS[dataset]
    edition = edition_of(datasets, dataset)
    suffix = spec.suffix.format(tag=_resolution_tag(config["resolution_m"], dataset))
    assets = []
    for tile in area_tiles(world, area):
        item_id = spec.item.format(edition=edition, tile=tile)
        item_url = STAC_ITEM.format(collection=config["collection"], item_id=item_id)
        name, href, sha256 = _published_asset(fetch_json, item_url, item_id, tile, area, suffix)
        assets.append(PublishedAsset(tile, item_id, name, href, sha256))
    return assets


def published_surface(
    world: World, datasets: dict, fetch_json: FetchJson, *, area: str
) -> list[PublishedAsset]:
    """Read, for every tile of `area`, the item of every year in the `editions`; no file is fetched.

    Exactly one of a tile's items must exist (HTTP 404 means absent; any other failure to
    read one is "cannot read the STAC item"), else it is a DownloadError naming the tile and
    the years found (`found none`, `found ['2021', '2022']`). The result is in tile order,
    each with its edition. This is `lock surface`'s read.
    """
    config = dataset_of(datasets, SURFACE)
    editions = editions_of(datasets, SURFACE)
    suffix = f"_{_resolution_tag(config['resolution_m'], SURFACE)}_2056_5728.tif"
    assets = []
    for tile in area_tiles(world, area):
        found = []
        for year in editions:
            item_id = SURFACE_ITEM.format(year=year, tile=tile)
            item_url = STAC_ITEM.format(collection=config["collection"], item_id=item_id)
            read = _published_asset(
                fetch_json, item_url, item_id, tile, area, suffix, absent_ok=True
            )
            if read is not None:
                found.append(PublishedAsset(tile, item_id, *read, edition=year))
        if len(found) != 1:
            raise DownloadError(
                f"tile {tile} of area {area!r}: {SURFACE} is published in exactly one of the "
                f"editions {editions} per tile, found {[asset.edition for asset in found] or 'none'}"
            )
        assets.append(found[0])
    return assets


def _published_surface_pinned(
    world: World, datasets: dict, fetch_json: FetchJson, locked: dict, area: str
) -> list[PublishedAsset]:
    """Read, per tile of `area`, only the item of the edition the lock pins (`download surface`).

    Choosing the edition is the lock's: an edition swisstopo publishes later stops no download
    of the pinned files. `locked` is the lock's `tiles` object, already shown to fit.
    """
    config = dataset_of(datasets, SURFACE)
    suffix = f"_{_resolution_tag(config['resolution_m'], SURFACE)}_2056_5728.tif"
    assets = []
    for tile in area_tiles(world, area):
        year = locked[tile]["edition"]
        item_id = SURFACE_ITEM.format(year=year, tile=tile)
        item_url = STAC_ITEM.format(collection=config["collection"], item_id=item_id)
        name, href, sha256 = _published_asset(fetch_json, item_url, item_id, tile, area, suffix)
        assets.append(PublishedAsset(tile, item_id, name, href, sha256, edition=year))
    return assets


@dataclass(frozen=True)
class PublishedSheet:
    """What a map sheet's STAC item publishes for the pinned swissBUILDINGS3D edition."""

    sheet: str
    item_id: str
    name: str
    href: str
    sha256: str


def published_sheets(
    world: World, datasets: dict, fetch_json: FetchJson, *, area: str
) -> list[PublishedSheet]:
    """Read the STAC item of every sheet of `area`, in sheet order; no file is fetched.

    A sheet with no item in the pinned edition is a DownloadError naming the sheet and the
    item's URL.
    """
    buildings = dataset_of(datasets, BUILDINGS)
    sheets = []
    for sheet in area_sheets(world, area):
        item_id = BUILDINGS_ITEM.format(edition=buildings["edition"], sheet=sheet)
        item_url = STAC_ITEM.format(collection=buildings["collection"], item_id=item_id)
        name, href, sha256 = _published_asset(
            fetch_json, item_url, item_id, sheet, area, BUILDINGS_SUFFIX, kind="sheet"
        )
        sheets.append(PublishedSheet(sheet, item_id, name, href, sha256))
    return sheets


def download_terrain(
    world: World,
    datasets: dict,
    out_root: Path | str,
    fetch_json: FetchJson,
    fetch_file: FetchFile,
    *,
    lock: dict,
    area: str,
) -> list[dict]:
    """Fetch and verify the tiles of `area` into `<out_root>/swissalti3d/<edition>/`.

    `lock` is the tile lock (`mattini.lock.load_lock()`): it must fit the config and pin
    exactly the tiles of the area (`lock.fit_problem`, refused before swisstopo is asked
    anything, naming `lock terrain`), and every published file name and SHA-256 must equal
    it, all checked before anything on disk changes. Returns the provenance entries, one per
    tile in tile order, and writes them with the dataset's edition and attribution to
    `provenance.json` in the same directory.
    """
    return _download_tiles(DATASET, world, datasets, out_root, fetch_json, fetch_file, lock, area)


def download_photo(
    world: World,
    datasets: dict,
    out_root: Path | str,
    fetch_json: FetchJson,
    fetch_file: FetchFile,
    *,
    lock: dict,
    area: str,
) -> list[dict]:
    """Fetch and verify the SWISSIMAGE tiles of `area` into `<out_root>/swissimage/<edition>/`.

    As `download_terrain`, for the lock's `swissimage` entry (naming `lock photo`); the
    provenance.json has exactly the terrain's keys (brief M3-03).
    """
    return _download_tiles(PHOTO, world, datasets, out_root, fetch_json, fetch_file, lock, area)


def _download_tiles(
    dataset: str,
    world: World,
    datasets: dict,
    out_root: Path | str,
    fetch_json: FetchJson,
    fetch_file: FetchFile,
    lock: dict,
    area: str,
) -> list[dict]:
    from mattini.lock import fit_problem  # lock imports this module

    config = dataset_of(datasets, dataset)
    _resolution_tag(config["resolution_m"], dataset)
    problem = fit_problem(lock, datasets, world, area, dataset)
    if problem:
        raise DownloadError(problem)
    pinned = lock["datasets"][dataset]["tiles"]
    assets = _published_tiles(dataset, world, datasets, fetch_json, area)
    _compare_with_lock(assets, pinned, dataset, area)
    out_dir = Path(out_root) / dataset / edition_of(datasets, dataset)
    entries = _fetch_tiles(out_dir, assets, fetch_file, area)
    _write_provenance(
        out_dir,
        {
            "attribution": config["attribution"],
            "collection": config["collection"],
            "dataset": dataset,
            "edition": config["edition"],
            "resolution_m": config["resolution_m"],
            "schema": PROVENANCE_SCHEMA,
            "tiles": entries,
        },
    )
    return entries


def download_surface(
    world: World,
    datasets: dict,
    out_root: Path | str,
    fetch_json: FetchJson,
    fetch_file: FetchFile,
    *,
    lock: dict,
    area: str,
) -> list[dict]:
    """Fetch and verify the swissSURFACE3D tiles of `area` into `<out_root>/swisssurface3d/<editions>/`.

    The lock must fit (`lock.fit_problem`: every tile's edition one of the config's `editions`,
    exactly the area's tiles; naming `lock surface`); each tile's item is read for the
    edition the lock pins and nothing else, and its published file name and SHA-256 must
    equal the lock's before anything is fetched. provenance.json has `editions` (the
    config's list) for `edition` and each tile's `edition` added (brief M3-03).
    """
    from mattini.lock import fit_problem  # lock imports this module

    config = dataset_of(datasets, SURFACE)
    _resolution_tag(config["resolution_m"], SURFACE)
    problem = fit_problem(lock, datasets, world, area, SURFACE)
    if problem:
        raise DownloadError(problem)
    pinned = lock["datasets"][SURFACE]["tiles"]
    assets = _published_surface_pinned(world, datasets, fetch_json, pinned, area)
    _compare_with_lock(assets, pinned, SURFACE, area)
    out_dir = Path(out_root) / SURFACE / raw_folder(datasets, SURFACE)
    entries = _fetch_tiles(out_dir, assets, fetch_file, area)
    _write_provenance(
        out_dir,
        {
            "attribution": config["attribution"],
            "collection": config["collection"],
            "dataset": SURFACE,
            "editions": config["editions"],
            "resolution_m": config["resolution_m"],
            "schema": PROVENANCE_SCHEMA,
            "tiles": entries,
        },
    )
    return entries


def _compare_with_lock(assets: list[PublishedAsset], pinned: dict, dataset: str, area: str) -> None:
    """Refuse the first tile whose published name or SHA-256 is not the lock's; nothing fetched."""
    for asset in assets:
        locked = pinned[asset.tile]
        if (asset.name, asset.sha256) != (locked["file"], locked["sha256"]):
            raise DownloadError(
                f"tile {asset.tile} of area {area!r}: swisstopo now publishes {asset.name} with "
                f"SHA-256 {asset.sha256}, the tile lock pins {locked['file']} with SHA-256 "
                f"{locked['sha256']}; nothing was fetched. A republished tile is adopted "
                f"only on purpose: `{LOCK_COMMAND_OF[dataset]}`, then commit the lock, "
                f"{_RECOMPUTE[dataset]}"
            )


def _fetch_tiles(
    out_dir: Path, assets: list[PublishedAsset], fetch_file: FetchFile, area: str
) -> list[dict]:
    """Make every asset's file the verified file in `out_dir`; return the provenance entries."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for asset in assets:
        where = f"tile {asset.tile} of area {area!r}"
        size = _fetch_into(out_dir, asset.name, asset.href, asset.sha256, fetch_file, where)
        entry = {
            "file": asset.name,
            "item": asset.item_id,
            "sha256": asset.sha256,
            "size_bytes": size,
            "tile": asset.tile,
            "url": asset.href,
        }
        if asset.edition is not None:
            entry["edition"] = asset.edition
        entries.append(entry)
    return entries


@dataclass(frozen=True)
class PublishedFile:
    """What the STAC item of the national swissTLM3D publishes for the pinned edition."""

    item_id: str
    name: str
    href: str
    sha256: str


def published_tlm(datasets: dict, fetch_json: FetchJson) -> PublishedFile:
    """Read the STAC item `swisstlm3d_<edition>`; no file is fetched (and no HEAD is sent).

    The one asset ending `_2056_5728.gdb.zip`, not the GeoPackage, Shapefile or INTERLIS zip.
    Every refusal starts `swisstlm3d <edition>: `.
    """
    config = dataset_of(datasets, TLM)
    edition = edition_of(datasets, TLM)
    item_id = TLM_ITEM.format(edition=edition)
    item_url = STAC_ITEM.format(collection=config["collection"], item_id=item_id)
    name, href, sha256 = _published_asset(
        fetch_json, item_url, item_id, "", "", TLM_SUFFIX, where=f"{TLM} {edition}"
    )
    return PublishedFile(item_id, name, href, sha256)


def download_tlm(
    datasets: dict,
    out_root: Path | str,
    fetch_json: FetchJson,
    fetch_head: FetchHead,
    fetch_range: FetchRange,
    *,
    lock: dict,
    progress: Progress | None = None,
) -> dict:
    """Fetch and verify swissTLM3D into `<out_root>/swisstlm3d/<edition>/`; return the provenance.

    The lock's `swisstlm3d` entry must fit the config (`lock.fit_problem`, naming `lock
    tlm`), and the published file name and SHA-256 must equal it before any request for the
    file. A verified file already there is kept with no request to the file host. Otherwise
    one HEAD (`fetch_head`: Content-Length, `x-amz-meta-sha256`), whose checksum, when it is
    not the lock's, is refused before any GET and before anything on disk changes; then
    GETs (`fetch_range(url, part, first_byte)`) into `<file>.part` until the part has the
    size, each from the part's size, at most `TLM_GETS` a round: a body cut short ends
    without an error (brain.md H9), so only the size shows it. The part is verified and
    takes the file's name only if its SHA-256 equals the lock's; a wrong one is deleted and
    fetched once more, then refused. A round that cannot finish keeps its part and names
    `python -m mattini download tlm`, which resumes it; a Ctrl-C keeps it too. provenance.json
    is removed before the first change on disk and written at the end. Every refusal starts
    `swisstlm3d <edition>: `.
    """
    from mattini.lock import fit_problem  # lock imports this module

    say = progress or (lambda message: None)
    config = dataset_of(datasets, TLM)
    edition = edition_of(datasets, TLM)

    def fail(message: str) -> DownloadError:
        return DownloadError(f"{TLM} {edition}: {message}")

    problem = fit_problem(lock, datasets, None, None, TLM)
    if problem:
        raise fail(problem)
    entry = lock["datasets"][TLM]
    published = published_tlm(datasets, fetch_json)
    if (published.name, published.sha256) != (entry["file"], entry["sha256"]):
        raise fail(
            f"swisstopo now publishes {published.name} with SHA-256 {published.sha256}, the "
            f"lock pins {entry['file']} with SHA-256 {entry['sha256']}; nothing was fetched. "
            f"A republished file is adopted only on purpose: `{TLM_LOCK_COMMAND}`, then "
            f"commit the lock, {_RECOMPUTE[TLM]}"
        )

    out_dir = Path(out_root) / TLM / edition
    dest = out_dir / published.name
    part = dest.with_name(dest.name + ".part")
    provenance = out_dir / PROVENANCE
    if not (dest.is_file() and _sha256(dest) == published.sha256):
        try:
            size, host_sha256 = fetch_head(published.href)
        except FETCH_ERRORS as exc:
            raise fail(f"{published.href}: cannot ask the file host: {exc}") from exc
        if not isinstance(size, int) or size < 1:
            raise fail(
                f"{published.href}: the file host sends no Content-Length; nothing was fetched"
            )
        if host_sha256 is not None and host_sha256.lower() != published.sha256:
            raise fail(
                f"{published.href}: the file host says SHA-256 {host_sha256}, the lock pins "
                f"{published.sha256}; nothing was fetched (the file host and the STAC item "
                f"disagree: try again later)"
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        provenance.unlink(missing_ok=True)  # it would list a file this run changes
        if dest.exists():
            dest.unlink()  # stale or damaged: never leave it looking valid
        _fetch_resumable(published, part, dest, size, fetch_range, say, fail)
    result = {
        "attribution": config["attribution"],
        "collection": config["collection"],
        "dataset": TLM,
        "edition": edition,
        "file": published.name,
        "item": published.item_id,
        "schema": PROVENANCE_SCHEMA,
        "sha256": published.sha256,
        "size_bytes": dest.stat().st_size,
        "url": published.href,
    }
    _write_provenance(out_dir, result)
    return result


def _fetch_resumable(
    published: PublishedFile,
    part: Path,
    dest: Path,
    size: int,
    fetch_range: FetchRange,
    say: Progress,
    fail: Callable[[str], DownloadError],
) -> None:
    """Make `dest` the verified file: GET into `part` from its size until it has `size` bytes.

    Two rounds at most, of `TLM_GETS` GETs each: the second only after a complete part had
    the wrong SHA-256 (deleted first).
    """
    wrong = ""
    for _ in range(2):
        gets, problem = 0, "the transfers were cut short"
        while True:
            have = part.stat().st_size if part.exists() else 0
            if have > size:
                part.unlink()  # not a start of this file
                have = 0
            if have == size:
                break
            if gets == TLM_GETS:
                raise fail(
                    f"{published.href}: the file has {size} bytes, the part holds {have} "
                    f"after {gets} requests ({problem}); the part is kept, and "
                    f"`{TLM_DOWNLOAD_COMMAND}` resumes it"
                )
            gets += 1
            say(f"fetching {published.href}" + (f" from byte {have}" if have else ""))
            try:
                fetch_range(published.href, part, have)
            except ResumeMismatch as exc:
                part.unlink(missing_ok=True)
                problem = str(exc)
            except FETCH_ERRORS as exc:
                problem = f"fetch failed: {exc}"
        wrong = _sha256(part)
        if wrong == published.sha256:
            os.replace(part, dest)
            return
        part.unlink()
        say(f"{part.name} has SHA-256 {wrong}, not the lock's; fetching it again")
    raise fail(
        f"{published.href}: two complete fetches gave SHA-256 {wrong}, the lock pins "
        f"{published.sha256}; the part was deleted. `{TLM_DOWNLOAD_COMMAND}` tries again"
    )


def download_buildings(
    world: World,
    datasets: dict,
    out_root: Path | str,
    fetch_json: FetchJson,
    fetch_file: FetchFile,
    *,
    lock: dict,
    area: str,
) -> list[dict]:
    """Fetch and verify the map sheets of `area` into `<out_root>/swissbuildings3d/<edition>/`.

    `lock` is the lock (`mattini.lock.load_lock()`): its `swissbuildings3d` entry must fit
    the config and pin exactly the sheets of the area (`lock.fit_problem`, as the buildings
    step and the manifest require, naming `lock buildings`), and every published file name
    and SHA-256 must equal it, all checked before anything on disk changes (M2 R1 I-02,
    I-04). Returns the provenance entries, one per sheet in sheet order, and writes them
    with the dataset's edition and attribution to `provenance.json` in the same directory.
    """
    from mattini.lock import fit_problem  # lock imports this module

    buildings = dataset_of(datasets, BUILDINGS)
    problem = fit_problem(lock, datasets, world, area, BUILDINGS)
    if problem:
        raise DownloadError(problem)
    pinned = lock["datasets"][BUILDINGS]["sheets"]
    published = published_sheets(world, datasets, fetch_json, area=area)
    for sheet in published:
        locked = pinned[sheet.sheet]
        if (sheet.name, sheet.sha256) != (locked["file"], locked["sha256"]):
            raise DownloadError(
                f"sheet {sheet.sheet} of area {area!r}: swisstopo now publishes {sheet.name} "
                f"with SHA-256 {sheet.sha256}, the lock pins {locked['file']} with SHA-256 "
                f"{locked['sha256']}; nothing was fetched. A republished sheet is adopted "
                f"only on purpose: `{BUILDINGS_LOCK_COMMAND}`, then commit the lock, "
                f"{_RECOMPUTE[BUILDINGS]}"
            )

    out_dir = Path(out_root) / BUILDINGS / buildings["edition"]
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for sheet in published:
        where = f"sheet {sheet.sheet} of area {area!r}"
        size = _fetch_into(out_dir, sheet.name, sheet.href, sheet.sha256, fetch_file, where)
        entries.append(
            {
                "file": sheet.name,
                "item": sheet.item_id,
                "sha256": sheet.sha256,
                "sheet": sheet.sheet,
                "size_bytes": size,
                "url": sheet.href,
            }
        )

    _write_provenance(
        out_dir,
        {
            "attribution": buildings["attribution"],
            "collection": buildings["collection"],
            "dataset": BUILDINGS,
            "edition": buildings["edition"],
            "schema": PROVENANCE_SCHEMA,
            "sheets": entries,
        },
    )
    return entries


def urllib_fetch_json(url: str) -> object:
    """GET a JSON document with the standard library."""
    request = urllib.request.Request(
        url, headers={"Accept": "application/geo+json, application/json", "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        return json.load(response)


def urllib_fetch_file(url: str, dest: Path) -> None:
    """GET a file with the standard library, streaming it to `dest`.

    A body cut before its Content-Length ends without an error in urllib (brain.md H9), so the
    bytes written are compared with the announced length: fewer is a CutTransfer. An answer with
    no Content-Length, or one that is not digits, is not checked here (the SHA-256 still is).
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    written = 0
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response, open(dest, "wb") as out:
        length = response.headers.get("Content-Length")
        while chunk := response.read(1 << 20):
            out.write(chunk)
            written += len(chunk)
    if length is not None and length.isdigit() and written < int(length):
        raise CutTransfer(f"cut at {written} of {int(length)} bytes")


def urllib_head(url: str) -> tuple[int | None, str | None]:
    """HEAD `url` with the standard library: (Content-Length, x-amz-meta-sha256) or None each."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        length = response.headers.get("Content-Length")
        return (int(length) if length and length.isdigit() else None), response.headers.get(
            "x-amz-meta-sha256"
        )


def urllib_fetch_range(url: str, part: Path, start: int, progress: Progress | None = None) -> None:
    """GET `url` into `part` from byte `start`: `Range: bytes=<start>-` once there are bytes.

    A 206 appends to the part and must start at `start`, else it is a ResumeMismatch (the
    caller deletes the part); a 200 is the whole file and rewrites the part. A body cut short
    ends without an error (brain.md H9): the part's size is the caller's evidence.
    """
    headers = {"User-Agent": USER_AGENT}
    if start:
        headers["Range"] = f"bytes={start}-"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        resumed = response.status == 206
        if resumed:
            match = re.fullmatch(
                r"bytes ([0-9]+)-[0-9]+/[0-9]+", response.headers.get("Content-Range", "")
            )
            if match is None or int(match.group(1)) != start:
                raise ResumeMismatch(
                    f"asked for bytes from {start}, the answer is "
                    f"{response.headers.get('Content-Range')!r}"
                )
        received, reported = 0, 0
        with open(part, "ab" if resumed else "wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)
                received += len(chunk)
                if progress is not None and received - reported >= 256 << 20:
                    reported = received
                    progress(f"  {(start if resumed else 0) + received >> 20} MiB of the file")


def _resolution_tag(resolution_m: object, dataset: str = DATASET) -> str:
    """How swisstopo writes a resolution in asset names: 0.5 -> '0.5', 2.0 -> '2', 0.1 -> '0.1'."""
    if type(resolution_m) not in (int, float) or not (
        math.isfinite(resolution_m) and resolution_m > 0
    ):
        raise DownloadError(
            f"{dataset}: resolution_m must be a positive number of metres, found {resolution_m!r}"
        )
    return format(resolution_m, "g")


def _published_asset(
    fetch_json: FetchJson,
    item_url: str,
    item_id: str,
    tile: str,
    area: str,
    suffix: str,
    *,
    kind: str = "tile",
    where: str | None = None,
    absent_ok: bool = False,
) -> tuple[str, str, str] | None:
    """The (file name, href, SHA-256) of the one asset of the item whose key ends `suffix`.

    `tile` is the item's tile or, with `kind="sheet"`, its map sheet; errors name it, and
    the area, unless `where` replaces that (`swisstlm3d 2026-02`, the national file). With
    `absent_ok`, an item that answers HTTP 404 is None (swissSURFACE3D: a tile is in one
    edition of several); any other failure to read it is still a refusal.
    """
    prefix = where if where is not None else f"{kind} {tile} of area {area!r}"

    def fail(message: str) -> DownloadError:
        return DownloadError(f"{prefix}: {item_url}: {message}")

    try:
        item = fetch_json(item_url)
    except urllib.error.HTTPError as exc:
        if absent_ok and exc.code == 404:
            return None
        raise fail(f"cannot read the STAC item: {exc}") from exc
    except (*FETCH_ERRORS, ValueError) as exc:
        raise fail(f"cannot read the STAC item: {exc}") from exc
    if not isinstance(item, dict) or item.get("id") != item_id:
        found = item.get("id") if isinstance(item, dict) else item
        raise fail(f"expected the STAC item {item_id!r}, found {found!r}")
    assets = item.get("assets")
    if not isinstance(assets, dict):
        raise fail("the STAC item has no assets")
    keys = sorted(key for key in assets if key.endswith(suffix))
    if len(keys) != 1:
        raise fail(f"expected exactly one asset ending {suffix!r}, found {keys}")
    name = keys[0]
    asset = assets[name]
    if not SAFE_NAME.fullmatch(name):
        raise fail(f"refusing an asset name that is not a plain file name: {name!r}")
    href = asset.get("href") if isinstance(asset, dict) else None
    if not isinstance(href, str) or not href:
        raise fail(f"asset {name!r} has no href")
    try:
        sha256 = parse_multihash_sha256(asset.get("file:checksum"))
    except ValueError as exc:
        raise fail(f"asset {name!r}: {exc}") from exc
    return name, href, sha256


def _fetch_into(
    out_dir: Path, name: str, href: str, sha256: str, fetch_file: FetchFile, where: str
) -> int:
    """Make `<out_dir>/<name>` the verified file; return its size in bytes.

    A file already there that matches is kept; one that does not is removed first. Either
    change removes provenance.json before it happens, since that would list the file.
    `where` names the tile or sheet in errors.
    """
    provenance = out_dir / PROVENANCE
    dest = out_dir / name
    if dest.exists() and not (dest.is_file() and _sha256(dest) == sha256):
        provenance.unlink(missing_ok=True)  # it would list a file this run removes
        dest.unlink()  # stale or damaged: never leave it looking valid
    if not dest.exists():
        provenance.unlink(missing_ok=True)
        _fetch_verified(fetch_file, href, dest, sha256, where)
    return dest.stat().st_size


def _fetch_verified(fetch_file: FetchFile, url: str, dest: Path, sha256: str, where: str) -> None:
    """Fetch `url` to `dest` via `<dest>.part`, keeping it only if its SHA-256 matches."""
    part = dest.with_name(dest.name + ".part")
    problem = ""
    cut = False
    for _ in range(ATTEMPTS):
        cut = False
        try:
            fetch_file(url, part)
            actual = _sha256(part)
            if actual == sha256:
                os.replace(part, dest)
                return
            problem = f"SHA-256 {actual} does not match the published {sha256}"
        except FETCH_ERRORS as exc:
            problem = f"fetch failed: {exc}"
            cut = isinstance(exc, CutTransfer)
        finally:
            part.unlink(missing_ok=True)
    hint = "; a dropped connection heals on a rerun: run the command again" if cut else ""
    raise DownloadError(f"{where}: {url}: {problem} (after {ATTEMPTS} attempts){hint}")


def _sha256(path: Path) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _write_provenance(out_dir: Path, provenance: dict) -> Path:
    """Write `<out_dir>/provenance.json` through a `.part` rename: sorted keys, LF, no times."""
    text = json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path = out_dir / PROVENANCE
    part = path.with_name(path.name + ".part")
    part.write_bytes(text.encode("utf-8"))
    os.replace(part, path)
    return path
