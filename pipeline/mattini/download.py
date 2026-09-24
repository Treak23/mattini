"""swissALTI3D download for the village area (brief M0-04; docs/SPEC.md §5, §7 and §9).

The 1 km tiles covering `areas.village` in config/world.json are fetched at the edition and
resolution pinned in config/datasets.json, never "the latest" (Hard Rule 5). STAC items are
addressed by id. Every file is checked against swisstopo's published SHA-256 (`file:checksum`,
a `1220…` multihash): it downloads to `<name>.part`, is verified, and only then takes its
final name, so a file under its final name matched the published checksum when it was
written. A mismatch deletes the temporary file; after one retry it is a DownloadError naming
the tile and the URL (Hard Rule 2). A file already on disk that matches is not fetched again.

`provenance.json` records what was fetched and its attribution: sorted keys, LF endings, no
times, no absolute paths, so two runs on the same inputs write identical bytes.
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

FetchJson = Callable[[str], object]
FetchFile = Callable[[str, Path], None]


class DownloadError(RuntimeError):
    """A download could not be completed or verified; the message names the tile and URL."""


def village_tiles(world: World) -> list[str]:
    """The ids (`<e km>-<n km>`) of the 1 km tiles covering the village area, sorted."""
    e_min, e_max, n_min, n_max = world.area("village")
    east = range(math.floor(e_min / TILE_M), math.ceil(e_max / TILE_M))
    north = range(math.floor(n_min / TILE_M), math.ceil(n_max / TILE_M))
    return [f"{e}-{n}" for e in east for n in north]


def parse_multihash_sha256(text: object) -> str:
    """The lower-case hex digest of a SHA-256 multihash (`1220` + 64 hex digits)."""
    match = SHA256_MULTIHASH.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise ValueError(f"not a SHA-256 multihash ('1220' + 64 hex digits): {text!r}")
    return match.group(1).lower()


def download_terrain(
    world: World,
    datasets: dict,
    out_root: Path | str,
    fetch_json: FetchJson,
    fetch_file: FetchFile,
) -> list[dict]:
    """Fetch and verify the village tiles into `<out_root>/swissalti3d/<edition>/`.

    Returns the provenance entries, one per tile in tile order, and writes them with the
    dataset's edition and attribution to `provenance.json` in the same directory.
    """
    alti = datasets[DATASET]
    edition = alti["edition"]
    suffix = f"_{_resolution_tag(alti['resolution_m'])}_2056_5728.tif"
    out_dir = Path(out_root) / DATASET / edition
    out_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for tile in village_tiles(world):
        item_id = f"{DATASET}_{edition}_{tile}"
        item_url = STAC_ITEM.format(collection=alti["collection"], item_id=item_id)
        name, href, sha256 = _published_asset(fetch_json, item_url, item_id, tile, suffix)
        dest = out_dir / name
        if dest.exists() and not (dest.is_file() and _sha256(dest) == sha256):
            dest.unlink()  # stale or damaged: never leave it looking valid
        if not dest.exists():
            _fetch_verified(fetch_file, href, dest, sha256, tile)
        entries.append(
            {
                "file": name,
                "item": item_id,
                "sha256": sha256,
                "size_bytes": dest.stat().st_size,
                "tile": tile,
                "url": href,
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


def _published_asset(
    fetch_json: FetchJson, item_url: str, item_id: str, tile: str, suffix: str
) -> tuple[str, str, str]:
    """The (file name, href, SHA-256) of the one asset of the item whose key ends `suffix`."""

    def fail(message: str) -> DownloadError:
        return DownloadError(f"tile {tile}: {item_url}: {message}")

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


def _fetch_verified(fetch_file: FetchFile, url: str, dest: Path, sha256: str, tile: str) -> None:
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
    raise DownloadError(f"tile {tile}: {url}: {problem} (after {ATTEMPTS} attempts)")


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
