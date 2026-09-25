"""swissALTI3D download for the terrain's area (briefs M0-04, M2-01; docs/SPEC.md §5, §7, §9).

The 1 km tiles covering the area config/terrain.json names (its one area; the box is in
config/world.json) are fetched at the edition and resolution pinned in
config/datasets.json, never "the latest" (Hard Rule 5); the caller passes the area, so the
download, the lock and the terrain step serve one area (M1 R1 T-06). STAC items are
addressed by id. Every file is checked against swisstopo's published SHA-256 (`file:checksum`,
a `1220…` multihash): it downloads to `<name>.part`, is verified, and only then takes its
final name, so a file under its final name matched the published checksum when it was
written. A mismatch deletes the temporary file; after one retry it is a DownloadError naming
the tile and the URL (Hard Rule 2). A file already on disk that matches is not fetched again.

Every tile's published file name and SHA-256 must equal the tile lock's
(config/datasets.lock.json, brief M1-01): all the STAC items are read and compared with the
lock before any file is fetched or deleted, so a tile swisstopo republished inside the
edition is refused, never adopted silently (Hard Rule 5); `python -m mattini lock terrain`
adopts it deliberately.

`provenance.json` records what was fetched and its attribution: sorted keys, LF endings, no
times, no absolute paths, so two runs on the same inputs write identical bytes. It is
removed before the run's first change on disk (an unlink or a file fetch) and written at
its end, so it exists only after a run that completed; a run that fails before changing
anything leaves the previous one as it was.
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

from mattini.world import REPO, World

DATASET = "swissalti3d"
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

FetchJson = Callable[[str], object]
FetchFile = Callable[[str, Path], None]


class DownloadError(RuntimeError):
    """A download could not be completed or verified; the message names the tile and URL."""


def area_tiles(world: World, area: str) -> list[str]:
    """The ids (`<e km>-<n km>`) of the 1 km tiles the named area's box touches, sorted.

    East outer, north inner: the order of the download, provenance.json, the terrain step
    and the manifest's `source.tiles`.
    """
    e_min, e_max, n_min, n_max = world.area(area)
    east = range(math.floor(e_min / TILE_M), math.ceil(e_max / TILE_M))
    north = range(math.floor(n_min / TILE_M), math.ceil(n_max / TILE_M))
    return [f"{e}-{n}" for e in east for n in north]


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
    alti = datasets[DATASET]
    edition = alti["edition"]
    suffix = f"_{_resolution_tag(alti['resolution_m'])}_2056_5728.tif"
    assets = []
    for tile in area_tiles(world, area):
        item_id = f"{DATASET}_{edition}_{tile}"
        item_url = STAC_ITEM.format(collection=alti["collection"], item_id=item_id)
        name, href, sha256 = _published_asset(fetch_json, item_url, item_id, tile, area, suffix)
        assets.append(PublishedAsset(tile, item_id, name, href, sha256))
    return assets


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

    `lock` is the tile lock (`mattini.lock.load_lock()`): it must be for the config's
    collection, edition and resolution and list every tile of the area, and every published
    file name and SHA-256 must equal it, all checked before anything on disk changes.
    Returns the provenance entries, one per tile in tile order, and writes them with the
    dataset's edition and attribution to `provenance.json` in the same directory.
    """
    alti = datasets[DATASET]
    _resolution_tag(alti["resolution_m"])
    pinned = _locked_tiles(lock, alti, area_tiles(world, area), area)
    assets = published_assets(world, datasets, fetch_json, area=area)
    for asset in assets:
        locked = pinned[asset.tile]
        if (asset.name, asset.sha256) != (locked["file"], locked["sha256"]):
            raise DownloadError(
                f"tile {asset.tile} of area {area!r}: swisstopo now publishes {asset.name} with "
                f"SHA-256 {asset.sha256}, the tile lock pins {locked['file']} with SHA-256 "
                f"{locked['sha256']}; nothing was fetched. A republished tile is adopted "
                f"only on purpose: `{LOCK_COMMAND}`, then commit the lock"
            )

    out_dir = Path(out_root) / DATASET / alti["edition"]
    out_dir.mkdir(parents=True, exist_ok=True)
    provenance = out_dir / PROVENANCE
    entries = []
    for asset in assets:
        dest = out_dir / asset.name
        if dest.exists() and not (dest.is_file() and _sha256(dest) == asset.sha256):
            provenance.unlink(missing_ok=True)  # it would list a file this run removes
            dest.unlink()  # stale or damaged: never leave it looking valid
        if not dest.exists():
            provenance.unlink(missing_ok=True)
            _fetch_verified(fetch_file, asset.href, dest, asset.sha256, asset.tile, area)
        entries.append(
            {
                "file": asset.name,
                "item": asset.item_id,
                "sha256": asset.sha256,
                "size_bytes": dest.stat().st_size,
                "tile": asset.tile,
                "url": asset.href,
            }
        )

    _write_provenance(out_dir, alti, entries)
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


def _locked_tiles(lock: object, alti: dict, tiles: list[str], area: str) -> dict:
    """The lock's tile entries, once it is shown to be for this config's tiles."""

    def fail(message: str) -> DownloadError:
        return DownloadError(
            f"the tile lock {message} (area {area!r}); `{LOCK_COMMAND}` writes the lock for "
            f"the config"
        )

    datasets = lock.get("datasets") if isinstance(lock, dict) else None
    locked = datasets.get(DATASET) if isinstance(datasets, dict) else None
    if not isinstance(locked, dict):
        raise fail(f"has no {DATASET!r} entry")
    for key in ("collection", "edition", "resolution_m"):
        if locked.get(key) != alti[key]:
            raise fail(f"is for {key} {locked.get(key)!r}, the config pins {alti[key]!r}")
    entries = locked.get("tiles")
    if not isinstance(entries, dict):
        raise fail("has no tiles")
    missing = [tile for tile in tiles if tile not in entries]
    if missing:
        raise fail(f"pins no checksum for the tiles {missing} of the area")
    return entries


def _published_asset(
    fetch_json: FetchJson, item_url: str, item_id: str, tile: str, area: str, suffix: str
) -> tuple[str, str, str]:
    """The (file name, href, SHA-256) of the one asset of the item whose key ends `suffix`."""

    def fail(message: str) -> DownloadError:
        return DownloadError(f"tile {tile} of area {area!r}: {item_url}: {message}")

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


def _fetch_verified(
    fetch_file: FetchFile, url: str, dest: Path, sha256: str, tile: str, area: str
) -> None:
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
    raise DownloadError(
        f"tile {tile} of area {area!r}: {url}: {problem} (after {ATTEMPTS} attempts)"
    )


def _sha256(path: Path) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _write_provenance(out_dir: Path, dataset: dict, entries: list[dict]) -> Path:
    provenance = {
        "attribution": dataset["attribution"],
        "collection": dataset["collection"],
        "dataset": DATASET,
        "edition": dataset["edition"],
        "resolution_m": dataset["resolution_m"],
        "schema": PROVENANCE_SCHEMA,
        "tiles": entries,
    }
    text = json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path = out_dir / PROVENANCE
    part = path.with_name(path.name + ".part")
    part.write_bytes(text.encode("utf-8"))
    os.replace(part, path)
    return path
