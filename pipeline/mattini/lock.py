"""config/datasets.lock.json: the SHA-256 of every tile the pipeline uses (brief M1-01; SPEC §5).

swisstopo can republish a tile inside an edition (M0-04 Findings 7), so the edition alone
does not pin the inputs. The lock records, for the pinned edition and resolution, each
tile's published file name and SHA-256, read from the STAC items only (no file is
fetched). It is written only by `python -m mattini lock terrain` and committed, like
`uv.lock`; `download terrain` refuses a published checksum that differs from it (Hard
Rule 5). Written deterministically: sorted keys, 2-space indent, UTF-8, LF, a final
newline. A malformed lock is a LockError naming the file (Hard Rule 2).
"""

from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

from mattini import download
from mattini.world import REPO, World

LOCK_PATH = REPO / "config" / "datasets.lock.json"
LOCK_COMMAND = download.LOCK_COMMAND
SCHEMA = 1
TOP_LEVEL_KEYS = {"schema", "datasets"}
DATASET_KEYS = {"collection", "edition", "resolution_m", "tiles"}
TILE_ENTRY_KEYS = {"file", "sha256"}
TILE_ID = re.compile(r"[0-9]+-[0-9]+")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")


class LockError(ValueError):
    """The tile lock is missing or malformed; the message names the file and the command."""


def build_lock(world: World, datasets: dict, fetch_json: download.FetchJson) -> dict:
    """The lock for the village tiles at the pinned edition and resolution, from STAC only."""
    alti = datasets[download.DATASET]
    tiles = {
        asset.tile: {"file": asset.name, "sha256": asset.sha256}
        for asset in download.published_assets(world, datasets, fetch_json)
    }
    return {
        "schema": SCHEMA,
        "datasets": {
            download.DATASET: {
                "collection": alti["collection"],
                "edition": alti["edition"],
                "resolution_m": alti["resolution_m"],
                "tiles": tiles,
            }
        },
    }


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
        raise _error(path, f"cannot read the tile lock: {exc}") from exc
    try:
        lock = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise _error(path, f"not valid JSON: {exc}") from exc
    validate_lock(lock, path)
    return lock


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
        if not isinstance(dataset, dict) or set(dataset) != DATASET_KEYS:
            raise fail(f"dataset {name!r} must have exactly the keys {sorted(DATASET_KEYS)}")
        for key in ("collection", "edition"):
            if not isinstance(dataset[key], str) or not dataset[key]:
                raise fail(f"dataset {name!r}: {key} must be a non-empty string")
        resolution = dataset["resolution_m"]
        if type(resolution) not in (int, float) or not (
            math.isfinite(resolution) and resolution > 0
        ):
            raise fail(f"dataset {name!r}: resolution_m must be a positive number of metres")
        tiles = dataset["tiles"]
        if not isinstance(tiles, dict) or not tiles:
            raise fail(f"dataset {name!r}: tiles must be a non-empty object")
        for tile, entry in tiles.items():
            where = f"dataset {name!r}, tile {tile!r}"
            if not TILE_ID.fullmatch(tile):
                raise fail(f"{where}: a tile id is '<e km>-<n km>'")
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


def _error(path: Path | str, message: str) -> LockError:
    return LockError(f"{path}: {message} (`{LOCK_COMMAND}` writes the tile lock)")
