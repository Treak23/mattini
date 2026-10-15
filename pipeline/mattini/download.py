"""swisstopo downloads for the configured area (briefs M0-04, M2-01, M2-03; SPEC §5, §7-§9).

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

A datasets config without the dataset, and an area the sheet grid cannot place, are
DownloadErrors naming config/datasets.json or the world config and the area, never a
traceback (M2 R1 I-05).
"""

from __future__ import annotations

import hashlib
import http.client
import json
import math
import os
import re
import shutil
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mattini.sheets import sheets_near
from mattini.world import REPO, World

DATASET = "swissalti3d"
BUILDINGS = "swissbuildings3d"
BUILDINGS_ITEM = "swissbuildings3d_3_0_{edition}_{sheet}"  # a STAC item of the collection
BUILDINGS_SUFFIX = "_2056_5728.gdb.zip"  # the zipped FileGDB; the item also holds a DWG
STAC_ITEM = "https://data.geo.admin.ch/api/stac/v1/collections/{collection}/items/{item_id}"
DEFAULT_OUT = REPO / "data" / "raw"
PROVENANCE = "provenance.json"
PROVENANCE_SCHEMA = 1
TILE_M = 1000  # swissALTI3D tiles are 1 km squares named by their south-west corner in km
ATTEMPTS = 2  # the first fetch and the one retry
SHA256_MULTIHASH = re.compile(r"1220([0-9A-Fa-f]{64})")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
FETCH_ERRORS = (OSError, http.client.HTTPException)  # urllib's errors are OSErrors
TIMEOUT_S = 60
USER_AGENT = "mattini-pipeline"
LOCK_COMMAND = "python -m mattini lock terrain"
BUILDINGS_LOCK_COMMAND = "python -m mattini lock buildings"
DATASETS_CONFIG_NAME = "config/datasets.json"  # the home of the datasets, for messages
# the config whose expected values design recomputes when a dataset's inputs change, and
# the step the republish refusals name after the lock command (brief M2-07)
EXPECTED_CONFIG_NAMES = {DATASET: "config/terrain.json", BUILDINGS: "config/buildings.json"}
_RECOMPUTE = {
    name: f"then design recomputes the expected values in {config} (docs/SPEC.md §8)"
    for name, config in EXPECTED_CONFIG_NAMES.items()
}

FetchJson = Callable[[str], object]
FetchFile = Callable[[str, Path], None]


class DownloadError(RuntimeError):
    """A download could not be completed or verified; the message names the tile and URL."""


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
    """What a tile's STAC item publishes for the pinned edition and resolution."""

    tile: str
    item_id: str
    name: str
    href: str
    sha256: str


def published_assets(
    world: World, datasets: dict, fetch_json: FetchJson, *, area: str
) -> list[PublishedAsset]:
    """Read the STAC item of every tile of `area`, in tile order; no file is fetched."""
    alti = dataset_of(datasets, DATASET)
    edition = alti["edition"]
    suffix = f"_{_resolution_tag(alti['resolution_m'])}_2056_5728.tif"
    assets = []
    for tile in area_tiles(world, area):
        item_id = f"{DATASET}_{edition}_{tile}"
        item_url = STAC_ITEM.format(collection=alti["collection"], item_id=item_id)
        name, href, sha256 = _published_asset(fetch_json, item_url, item_id, tile, area, suffix)
        assets.append(PublishedAsset(tile, item_id, name, href, sha256))
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
    from mattini.lock import fit_problem  # lock imports this module

    alti = dataset_of(datasets, DATASET)
    _resolution_tag(alti["resolution_m"])
    problem = fit_problem(lock, datasets, world, area, DATASET)
    if problem:
        raise DownloadError(problem)
    pinned = lock["datasets"][DATASET]["tiles"]
    assets = published_assets(world, datasets, fetch_json, area=area)
    for asset in assets:
        locked = pinned[asset.tile]
        if (asset.name, asset.sha256) != (locked["file"], locked["sha256"]):
            raise DownloadError(
                f"tile {asset.tile} of area {area!r}: swisstopo now publishes {asset.name} with "
                f"SHA-256 {asset.sha256}, the tile lock pins {locked['file']} with SHA-256 "
                f"{locked['sha256']}; nothing was fetched. A republished tile is adopted "
                f"only on purpose: `{LOCK_COMMAND}`, then commit the lock, {_RECOMPUTE[DATASET]}"
            )

    out_dir = Path(out_root) / DATASET / alti["edition"]
    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for asset in assets:
        where = f"tile {asset.tile} of area {area!r}"
        size = _fetch_into(out_dir, asset.name, asset.href, asset.sha256, fetch_file, where)
        entries.append(
            {
                "file": asset.name,
                "item": asset.item_id,
                "sha256": asset.sha256,
                "size_bytes": size,
                "tile": asset.tile,
                "url": asset.href,
            }
        )

    _write_provenance(
        out_dir,
        {
            "attribution": alti["attribution"],
            "collection": alti["collection"],
            "dataset": DATASET,
            "edition": alti["edition"],
            "resolution_m": alti["resolution_m"],
            "schema": PROVENANCE_SCHEMA,
            "tiles": entries,
        },
    )
    return entries


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
    """GET a file with the standard library, streaming it to `dest`."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out, 1 << 20)


def _resolution_tag(resolution_m: object) -> str:
    """How swisstopo writes a resolution in asset names: 0.5 → '0.5', 2.0 → '2'."""
    if type(resolution_m) not in (int, float) or not (
        math.isfinite(resolution_m) and resolution_m > 0
    ):
        raise DownloadError(
            f"{DATASET}: resolution_m must be a positive number of metres, found {resolution_m!r}"
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
) -> tuple[str, str, str]:
    """The (file name, href, SHA-256) of the one asset of the item whose key ends `suffix`.

    `tile` is the item's tile or, with `kind="sheet"`, its map sheet; errors name it.
    """

    def fail(message: str) -> DownloadError:
        return DownloadError(f"{kind} {tile} of area {area!r}: {item_url}: {message}")

    try:
        item = fetch_json(item_url)
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
    for _ in range(ATTEMPTS):
        try:
            fetch_file(url, part)
            actual = _sha256(part)
            if actual == sha256:
                os.replace(part, dest)
                return
            problem = f"SHA-256 {actual} does not match the published {sha256}"
        except FETCH_ERRORS as exc:
            problem = f"fetch failed: {exc}"
        finally:
            part.unlink(missing_ok=True)
    raise DownloadError(f"{where}: {url}: {problem} (after {ATTEMPTS} attempts)")


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
