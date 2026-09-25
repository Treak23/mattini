"""config/datasets.lock.json: the SHA-256 of every file the pipeline uses (M1-01, M2-03; SPEC §5).

swisstopo can republish a tile inside an edition (M0-04 Findings 7), so the edition alone
does not pin the inputs. The lock holds one entry per dataset, each recording, for the
pinned edition, every file's published name and SHA-256, read from the STAC items only (no
file is fetched):

- `swissalti3d`: exactly {collection, edition, resolution_m, tiles: {<tile>: {file, sha256}}};
- `swissbuildings3d`: exactly {collection, edition, sheets: {<sheet>: {file, sha256}}}, every
  sheet id an LK25 sixteenth (`sheets.SHEET_ID`).

Any other dataset is refused. The lock is written only by `python -m mattini lock terrain`
and `python -m mattini lock buildings`, each of which replaces its own entry and keeps every
other (`with_entry`), and committed, like `uv.lock`; `download terrain` and `download
buildings` refuse a published checksum that differs from it (Hard Rule 5). Written
deterministically: sorted keys, 2-space indent, UTF-8, LF, a final newline. A malformed
lock is a LockError naming the file (Hard Rule 2).

The expected values in config/terrain.json and config/buildings.json record the inputs
they were computed from as `entry_sha256` of the dataset's entry (brief M2-07, SPEC §8):
the entry rendered canonically, so the lock file's own formatting does not count.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from pathlib import Path

from mattini import download
from mattini.sheets import SHEET_ID
from mattini.world import REPO, World

LOCK_PATH = REPO / "config" / "datasets.lock.json"
LOCK_COMMAND = download.LOCK_COMMAND
LOCK_COMMANDS = (download.LOCK_COMMAND, download.BUILDINGS_LOCK_COMMAND)
SCHEMA = 1
TOP_LEVEL_KEYS = {"schema", "datasets"}
DATASET_KEYS = {  # every dataset the lock knows, with its entry's exact key set
    download.DATASET: {"collection", "edition", "resolution_m", "tiles"},
    download.BUILDINGS: {"collection", "edition", "sheets"},
}
TILE_ENTRY_KEYS = {"file", "sha256"}  # one file of a tile or a sheet
TILE_ID = re.compile(r"[0-9]+-[0-9]+")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")


class LockError(ValueError):
    """The lock is missing or malformed; the message names the file and the commands."""


def terrain_entry(
    world: World, datasets: dict, fetch_json: download.FetchJson, *, area: str
) -> dict:
    """The lock's swissALTI3D entry: the tiles of `area` at the pinned edition and resolution.

    From the STAC items only. The command line passes the area config/terrain.json names
    (brief M2-01, M1 R1 T-06). A datasets config without `swissalti3d` is a DownloadError
    naming config/datasets.json.
    """
    alti = download.dataset_of(datasets, download.DATASET)
    return {
        "collection": alti["collection"],
        "edition": alti["edition"],
        "resolution_m": alti["resolution_m"],
        "tiles": {
            asset.tile: {"file": asset.name, "sha256": asset.sha256}
            for asset in download.published_assets(world, datasets, fetch_json, area=area)
        },
    }


def buildings_entry(
    world: World, datasets: dict, fetch_json: download.FetchJson, *, area: str
) -> dict:
    """The lock's swissBUILDINGS3D entry: the map sheets of `area` at the pinned edition.

    From the STAC items only; the sheets are `download.area_sheets(world, area)`. A datasets
    config without `swissbuildings3d` is a DownloadError naming config/datasets.json.
    """
    buildings = download.dataset_of(datasets, download.BUILDINGS)
    return {
        "collection": buildings["collection"],
        "edition": buildings["edition"],
        "sheets": {
            sheet.sheet: {"file": sheet.name, "sha256": sheet.sha256}
            for sheet in download.published_sheets(world, datasets, fetch_json, area=area)
        },
    }


def entry_sha256(entry: dict) -> str:
    """The SHA-256 of a dataset's lock entry rendered canonically (brief M2-07, SPEC §8).

    `json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` in
    UTF-8: what `computed_for.inputs_sha256` in config/terrain.json and
    config/buildings.json records for the entry design computed the expected values from.
    """
    text = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def with_entry(lock: dict | None, dataset: str, entry: dict) -> dict:
    """A new lock: `lock` (or an empty one for None) with `dataset`'s entry set to `entry`.

    Every other dataset's entry is kept as it was; neither argument is changed.
    `write_lock` validates the result before anything is written.
    """
    result = copy.deepcopy(lock) if lock is not None else {"schema": SCHEMA, "datasets": {}}
    result["datasets"][dataset] = copy.deepcopy(entry)
    return result


def build_lock(world: World, datasets: dict, fetch_json: download.FetchJson, *, area: str) -> dict:
    """A lock holding the swissALTI3D entry for `area` only (`terrain_entry`), from STAC only."""
    return with_entry(None, download.DATASET, terrain_entry(world, datasets, fetch_json, area=area))


def write_lock(lock: dict, path: Path | str = LOCK_PATH) -> Path:
    """Validate `lock` and write it to `path` through a `.part` rename; return the path."""
    path = Path(path)
    validate_lock(lock, path)
    text = json.dumps(lock, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    part = path.with_name(path.name + ".part")
    part.write_bytes(text.encode("utf-8"))
    os.replace(part, path)
    return path


def load_lock(path: Path | str = LOCK_PATH) -> dict:
    """The lock at `path`, validated; a missing or malformed one is a LockError naming it."""
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise _error(path, f"cannot read the lock: {exc}") from exc
    return _parsed(raw, path)


def load_lock_or_none(path: Path | str = LOCK_PATH) -> dict | None:
    """The lock at `path` for the lock command to add an entry to; None when there is none.

    A lock that exists but cannot be read or is malformed is a LockError: the command keeps
    every other dataset's entry, so it never replaces a lock it cannot read.
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        problem = _error(path, f"cannot read the lock: {exc}")
    else:
        try:
            return _parsed(raw, path)
        except LockError as exc:
            problem = exc
    raise LockError(
        f"{problem}. The lock command replaces one dataset's entry and keeps the others, so "
        f"it does not overwrite a lock it cannot read: restore {path} from git, or delete it "
        f"and lock every dataset again"
    ) from problem


def validate_lock(lock: object, path: Path | str) -> None:
    """Raise a LockError naming `path` unless `lock` has the lock's exact structure."""

    def fail(message: str) -> LockError:
        return _error(path, message)

    if not isinstance(lock, dict) or set(lock) != TOP_LEVEL_KEYS:
        raise fail(f"the top level must have exactly the keys {sorted(TOP_LEVEL_KEYS)}")
    if type(lock["schema"]) is not int or lock["schema"] != SCHEMA:
        raise fail(f"schema must be {SCHEMA}, found {lock['schema']!r}")
    datasets = lock["datasets"]
    if not isinstance(datasets, dict) or not datasets:
        raise fail("datasets must be a non-empty object")
    for name, dataset in datasets.items():
        if name not in DATASET_KEYS:
            raise fail(f"unknown dataset {name!r}: the lock knows {sorted(DATASET_KEYS)}")
        keys = DATASET_KEYS[name]
        if not isinstance(dataset, dict) or set(dataset) != keys:
            raise fail(f"dataset {name!r} must have exactly the keys {sorted(keys)}")
        for key in ("collection", "edition"):
            if not isinstance(dataset[key], str) or not dataset[key]:
                raise fail(f"dataset {name!r}: {key} must be a non-empty string")
        if name == download.DATASET:
            resolution = dataset["resolution_m"]
            if type(resolution) not in (int, float) or not (
                math.isfinite(resolution) and resolution > 0
            ):
                raise fail(f"dataset {name!r}: resolution_m must be a positive number of metres")
            parts, kind, pattern, form = dataset["tiles"], "tile", TILE_ID, "'<e km>-<n km>'"
        else:
            parts, kind, pattern, form = dataset["sheets"], "sheet", SHEET_ID, "like '1348-11'"
        if not isinstance(parts, dict) or not parts:
            raise fail(f"dataset {name!r}: {kind}s must be a non-empty object")
        for part, entry in parts.items():
            where = f"dataset {name!r}, {kind} {part!r}"
            if not isinstance(part, str) or not pattern.fullmatch(part):
                raise fail(f"{where}: a {kind} id is {form}")
            if not isinstance(entry, dict) or set(entry) != TILE_ENTRY_KEYS:
                raise fail(f"{where}: must have exactly the keys {sorted(TILE_ENTRY_KEYS)}")
            if not isinstance(entry["file"], str) or not download.SAFE_NAME.fullmatch(
                entry["file"]
            ):
                raise fail(f"{where}: file must be a plain file name, found {entry['file']!r}")
            if not isinstance(entry["sha256"], str) or not SHA256_HEX.fullmatch(entry["sha256"]):
                raise fail(
                    f"{where}: sha256 must be 64 lower-case hex digits, found {entry['sha256']!r}"
                )


def _parsed(raw: bytes, path: Path) -> dict:
    try:
        lock = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise _error(path, f"not valid JSON: {exc}") from exc
    validate_lock(lock, path)
    return lock


def _error(path: Path | str, message: str) -> LockError:
    commands = " and ".join(f"`{command}`" for command in LOCK_COMMANDS)
    return LockError(f"{path}: {message} ({commands} write the lock)")
