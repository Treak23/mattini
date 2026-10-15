"""config/datasets.lock.json: the SHA-256 of every file the pipeline uses (M1-01, M2-03; SPEC §5).

swisstopo can republish a tile inside an edition (M0-04 Findings 7), so the edition alone
does not pin the inputs. The lock holds one entry per dataset, each recording, for the
pinned edition, every file's published name and SHA-256, read from the STAC items only (no
file is fetched):

- `swissalti3d` and `swissimage`: exactly {collection, edition, resolution_m,
  tiles: {<tile>: {file, sha256}}};
- `swissbuildings3d`: exactly {collection, edition, sheets: {<sheet>: {file, sha256}}}, every
  sheet id an LK25 sixteenth (`sheets.SHEET_ID`);
- `swisssurface3d` (brief M3-03): exactly {collection, resolution_m,
  tiles: {<tile>: {edition, file, sha256}}}: each tile's edition is its own, one of the
  config's `editions`, since a tile is published in one of several;
- `swisstlm3d`: exactly {collection, edition, file, sha256}, the one national file.

Any other dataset is refused. The lock is written only by `python -m mattini lock terrain`,
`lock buildings`, `lock photo`, `lock surface` and `lock tlm`, each of which replaces its
own entry and keeps every other (`with_entry`), and committed, like `uv.lock`; the
`download` commands refuse a published checksum that differs from it (Hard Rule 5). Written
deterministically: sorted keys, 2-space indent, UTF-8, LF, a final newline. A malformed
lock is a LockError naming the file (Hard Rule 2). `file:checksum` is published in upper-case
hex and stored in lower case.

The expected values of the steps' configs (config/terrain.json, buildings.json, photo.json,
roofs.json, surfaces.json, trees.json) record the inputs they were computed from as
`entry_sha256` of the dataset's entry (briefs M2-07, M3-03, SPEC §8): the entry rendered
canonically, so the lock file's own formatting does not count.

Whether a lock *fits* the configs has one home, `fit_problem` (brief M3-01, M2 V1-P-01):
the entry is for the datasets config's collection, edition (swissSURFACE3D: every tile's
edition one of `editions`) and resolution and pins exactly the area's tiles or map sheets,
no more and no fewer (swissTLM3D is national: no area). `download`, the steps and
`manifest` all ask it, so each refuses a lock that does not fit with the same words, naming
`python -m mattini lock <dataset>` and no other command.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mattini import download
from mattini.sheets import SHEET_ID
from mattini.world import REPO, World

LOCK_PATH = REPO / "config" / "datasets.lock.json"
LOCK_COMMAND = download.LOCK_COMMAND
LOCK_COMMANDS = tuple(  # the five commands that write the lock, in the order the help lists them
    download.LOCK_COMMAND_OF[name]
    for name in (
        download.DATASET,
        download.BUILDINGS,
        download.PHOTO,
        download.SURFACE,
        download.TLM,
    )
)
SCHEMA = 1
TOP_LEVEL_KEYS = {"schema", "datasets"}
DATASET_KEYS = {  # every dataset the lock knows, with its entry's exact key set
    download.DATASET: {"collection", "edition", "resolution_m", "tiles"},
    download.BUILDINGS: {"collection", "edition", "sheets"},
    download.PHOTO: {"collection", "edition", "resolution_m", "tiles"},
    download.SURFACE: {"collection", "resolution_m", "tiles"},
    download.TLM: {"collection", "edition", "file", "sha256"},
}
TILE_ENTRY_KEYS = {"file", "sha256"}  # one file of a tile or a sheet
SURFACE_TILE_ENTRY_KEYS = {"edition", "file", "sha256"}  # a swissSURFACE3D tile: its edition too
YEAR = re.compile(r"[0-9]{4}")
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
        "edition": download.edition_of(datasets, download.DATASET),
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
        "edition": download.edition_of(datasets, download.BUILDINGS),
        "sheets": {
            sheet.sheet: {"file": sheet.name, "sha256": sheet.sha256}
            for sheet in download.published_sheets(world, datasets, fetch_json, area=area)
        },
    }


def photo_entry(world: World, datasets: dict, fetch_json: download.FetchJson, *, area: str) -> dict:
    """The lock's SWISSIMAGE entry: the tiles of `area` at the pinned edition and resolution.

    From the STAC items only (brief M3-03); the checksum is stored in lower case.
    """
    photo = download.dataset_of(datasets, download.PHOTO)
    return {
        "collection": photo["collection"],
        "edition": download.edition_of(datasets, download.PHOTO),
        "resolution_m": photo["resolution_m"],
        "tiles": {
            asset.tile: {"file": asset.name, "sha256": asset.sha256}
            for asset in download.published_photo(world, datasets, fetch_json, area=area)
        },
    }


def surface_entry(
    world: World, datasets: dict, fetch_json: download.FetchJson, *, area: str
) -> dict:
    """The lock's swissSURFACE3D entry: for every tile of `area`, the one edition it is in.

    From the STAC items only: every year in the config's `editions` is read per tile, and
    exactly one must exist (`download.published_surface`), else a DownloadError names the
    tile and the years found and nothing is written (brief M3-03).
    """
    surface = download.dataset_of(datasets, download.SURFACE)
    return {
        "collection": surface["collection"],
        "resolution_m": surface["resolution_m"],
        "tiles": {
            asset.tile: {"edition": asset.edition, "file": asset.name, "sha256": asset.sha256}
            for asset in download.published_surface(world, datasets, fetch_json, area=area)
        },
    }


def tlm_entry(datasets: dict, fetch_json: download.FetchJson) -> dict:
    """The lock's swissTLM3D entry: the one national file of the pinned edition.

    From the STAC item only: no request goes to the file host, not even a HEAD (brief M3-03).
    """
    tlm = download.dataset_of(datasets, download.TLM)
    published = download.published_tlm(datasets, fetch_json)
    return {
        "collection": tlm["collection"],
        "edition": download.edition_of(datasets, download.TLM),
        "file": published.name,
        "sha256": published.sha256,
    }


@dataclass(frozen=True)
class _Fit:
    """What `fit_problem` compares for one dataset."""

    keys: tuple[str, ...]  # the entry's keys that must equal the datasets config's
    files: str | None  # the entry's object of files, "tiles" or "sheets"; None: one national file
    ids: Callable | None = None  # (world, area) -> the ids the area needs, in the order listed
    editions: bool = False  # every file's `edition` must be one of the config's `editions`


_FITS = {
    download.DATASET: _Fit(("collection", "edition", "resolution_m"), "tiles", download.area_tiles),
    download.BUILDINGS: _Fit(("collection", "edition"), "sheets", download.area_sheets),
    download.PHOTO: _Fit(("collection", "edition", "resolution_m"), "tiles", download.area_tiles),
    download.SURFACE: _Fit(
        ("collection", "resolution_m"), "tiles", download.area_tiles, editions=True
    ),
    download.TLM: _Fit(("collection", "edition"), None),
}


def fit_problem(
    lock: object, datasets: dict, world: World | None, area: str | None, dataset: str
) -> str | None:
    """Why the lock's entry for `dataset` does not fit the configs and `area`, or None.

    It fits when it exists, is for the datasets config's collection, edition and (where it
    has one) resolution, and pins exactly the tiles or map sheets the area needs
    (`download.area_tiles`, `download.area_sheets`), none missing and none beside them: a
    lock that pins others too would download and then be refused by the step and by
    `manifest` (brief M3-01, M2 R1 I-04, M2 V1-P-01, V1-P-02, V1-P-07). swissSURFACE3D has
    no one edition: every tile's own must be one of the config's `editions`. swissTLM3D is
    one national file, so `world` and `area` are not read for it (None is fine). The text is
    the whole refusal for the caller to raise in its own error class; it names the area (not
    for the TLM) and the lock command that fixes it, `python -m mattini lock <x>`, and no
    other command. A datasets config without `dataset` is a DownloadError naming
    config/datasets.json (`download.dataset_of`), and so is one that lists `editions` where the
    dataset needs one `edition` or the other way round (`download.edition_of`); an area the
    sheet grid cannot place is one too.
    """
    if dataset not in _FITS:
        raise ValueError(f"no fit rule for dataset {dataset!r}: the lock knows {sorted(_FITS)}")
    fit = _FITS[dataset]
    config = download.dataset_of(datasets, dataset)
    if "edition" in fit.keys:
        download.edition_of(datasets, dataset)  # a config that lists editions is a refusal
    if fit.editions:
        download.editions_of(datasets, dataset)  # and so is one that pins a single edition
    where = f" (area {area!r})" if fit.files is not None else ""

    def problem(message: str) -> str:
        return (
            f"the lock {message}{where}; `{download.LOCK_COMMAND_OF[dataset]}` writes the "
            f"lock's {dataset} entry for the config"
        )

    locked = lock.get("datasets") if isinstance(lock, dict) else None
    entry = locked.get(dataset) if isinstance(locked, dict) else None
    if not isinstance(entry, dict):
        return problem(f"has no {dataset!r} entry")
    for key in fit.keys:
        if entry.get(key) != config[key]:
            return problem(
                f"is for {dataset} {key} {entry.get(key)!r}, the config pins {config[key]!r}"
            )
    if fit.files is None:
        return None
    pinned = entry.get(fit.files)
    if not isinstance(pinned, dict):
        return problem(f"has no {fit.files}")
    needed = fit.ids(world, area)
    missing = [part for part in needed if part not in pinned]
    if missing:
        return problem(f"pins no checksum for the {fit.files} {missing} of the area")
    if set(pinned) != set(needed):
        return problem(f"pins the {fit.files} {sorted(pinned)}, the area needs exactly {needed}")
    if fit.editions:
        for part in needed:
            edition = pinned[part].get("edition") if isinstance(pinned[part], dict) else None
            if edition not in config["editions"]:
                return problem(
                    f"pins {part} in edition {edition!r}, which is none of the config's "
                    f"editions {config['editions']}"
                )
    return None


def entry_sha256(entry: dict) -> str:
    """The SHA-256 of a dataset's lock entry rendered canonically (brief M2-07, SPEC §8).

    `json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` in
    UTF-8: what `computed_for.inputs_sha256` in the steps' configs records for the entry
    design computed the expected values from (a step with several datasets records the
    same form over {dataset: entry}).
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
            if key in keys and (not isinstance(dataset[key], str) or not dataset[key]):
                raise fail(f"dataset {name!r}: {key} must be a non-empty string")
        if "resolution_m" in keys:
            resolution = dataset["resolution_m"]
            if type(resolution) not in (int, float) or not (
                math.isfinite(resolution) and resolution > 0
            ):
                raise fail(f"dataset {name!r}: resolution_m must be a positive number of metres")
        if name == download.TLM:
            _check_file(f"dataset {name!r}", dataset, fail)
            continue
        if name == download.BUILDINGS:
            parts, kind, pattern, form = dataset["sheets"], "sheet", SHEET_ID, "like '1348-11'"
        else:
            parts, kind, pattern, form = dataset["tiles"], "tile", TILE_ID, "'<e km>-<n km>'"
        entry_keys = SURFACE_TILE_ENTRY_KEYS if name == download.SURFACE else TILE_ENTRY_KEYS
        if not isinstance(parts, dict) or not parts:
            raise fail(f"dataset {name!r}: {kind}s must be a non-empty object")
        for part, entry in parts.items():
            where = f"dataset {name!r}, {kind} {part!r}"
            if not isinstance(part, str) or not pattern.fullmatch(part):
                raise fail(f"{where}: a {kind} id is {form}")
            if not isinstance(entry, dict) or set(entry) != entry_keys:
                raise fail(f"{where}: must have exactly the keys {sorted(entry_keys)}")
            if name == download.SURFACE and not (
                isinstance(entry["edition"], str) and YEAR.fullmatch(entry["edition"])
            ):
                raise fail(
                    f"{where}: edition must be a year like '2021', found {entry['edition']!r}"
                )
            _check_file(where, entry, fail)


def _check_file(where: str, entry: dict, fail) -> None:
    """Refuse an entry whose `file` is not a plain file name or `sha256` not 64 lower-case hex."""
    if not isinstance(entry["file"], str) or not download.SAFE_NAME.fullmatch(entry["file"]):
        raise fail(f"{where}: file must be a plain file name, found {entry['file']!r}")
    if not isinstance(entry["sha256"], str) or not SHA256_HEX.fullmatch(entry["sha256"]):
        raise fail(f"{where}: sha256 must be 64 lower-case hex digits, found {entry['sha256']!r}")


def _parsed(raw: bytes, path: Path) -> dict:
    try:
        lock = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise _error(path, f"not valid JSON: {exc}") from exc
    validate_lock(lock, path)
    return lock


def _error(path: Path | str, message: str) -> LockError:
    quoted = [f"`{command}`" for command in LOCK_COMMANDS]
    commands = f"{', '.join(quoted[:-1])} and {quoted[-1]}"
    return LockError(f"{path}: {message} ({commands} write the lock)")
