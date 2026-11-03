"""The surroundings grid: swissALTIRegio tiles to the far terrain's heights (v0.6.0-04; SPEC §8).

A vertex every `spacing_m` over the area's box grown by `margin_m` on every side, its edges
included: row r, column c is LV95 (e_min + c·s, n_max − r·s) of that box, rows north to south,
columns west to east. A vertex's height is the MEAN of the samples whose position lies in the
half-open square [E − s/2, E + s/2) × [N − s/2, N + s/2), minus `height_offset_m` (so local y);
the samples on a square's west and south edges are its own, those on its east and north edges
are its neighbour's (design §1, `docs/briefs/sketches/v0.6.0/design.md`). A vertex strictly
inside the area's box is NaN, the quiet NaN 0x7FC00000: the real terrain is there. A vertex on
the area's edge keeps its height.

The mean is computed exactly. Every height text is parsed to whole centimetres (`-?[0-9]+` with
at most two decimals after a point; any other text is refused naming the tile and the line), the
samples of a square are summed as integers, the sum is divided once in 64-bit by 100 times their
count, the 64-bit `height_offset_m` is subtracted, and the result is rounded once to 32-bit. No
order of summation can change it (Hard Rule 5). A square that lacks some of its samples (a tile
at the data's edge) takes the mean of those it holds; a vertex that keeps a height and has no
sample at all is refused.

The heights must be the ones design computed: config/surroundings.json holds their SHA-256
(`expected_sha256`), and the step compares its output with it before it writes anything (lesson
38). The values hold only for the world config and the inputs design computed them for, which
the area records as `computed_for`; the step checks, in this order and each before the next
reads anything: the owner's axes, the area on the spacing lattice, the world (a difference is a
design change, naming design's step), the box, columns and rows against the expected ones, the
lock's fit (the datasets config's collection, edition and resolution and exactly the tiles the
surroundings need, refused naming `python -m mattini lock regio` and no other command), the
lock's entry (a design change again), provenance.json, then tile by tile the bytes' SHA-256
against the lock's, read from the very bytes parsed. A missing or different download is refused
naming `python -m mattini download regio`, before anything is created under `out_dir` and
before any progress line.

The lock's fit is written here, not read from `lock.py` or `download.py`: the tiles are the 10 km
squares (south-west corners at E = 5 km + 10 km·i, N = 4 km + 10 km·j) that meet the box grown by
half a spacing, [e_min − s/2, e_max + s/2) × [n_min − s/2, n_max + s/2), the samples a vertex
needs. A tile is one zip with one member `<E km>_<N km>.xyz`, ASCII with CRLF line ends, the
header `x y z`, then a line `x y z` per sample: whole-metre x and y on the tile's cell centres at
`resolution_m` (E0 + r/2 + r·i, N0 + r/2 + r·j) inside its square, each at most once, in any
order. Anything else is refused naming the tile.

The files: `surroundings/<area>.f32` (little-endian float32, row-major, no header), then
`surroundings/<area>.json`, each written through a `.part` rename; after a success every `*.part`
left in `surroundings/` is removed. Only the owner's axes (x = +e, y = +h, z = −n) are
supported: another mapping would place these rows and columns wrongly (Hard Rule 4).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import zipfile
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np

from mattini.download import PROVENANCE
from mattini.lock import entry_sha256
from mattini.terrain import (
    AREA_NAME,
    OWNER_AXES,
    check_computed_for,
    configured_area,
    inputs_refusal,
    world_refusal,
)
from mattini.world import REPO, World, parse_world, read_config_bytes

SURROUNDINGS_CONFIG_PATH = REPO / "config" / "surroundings.json"
SURROUNDINGS_CONFIG_NAME = "config/surroundings.json"  # the home of the expected heights
DATASETS_CONFIG_NAME = "config/datasets.json"
SCHEMA = 2
DATASET = "swissaltiregio"
FORMAT = "f32-le"
LOCK_COMMAND = "python -m mattini lock regio"
DOWNLOAD_COMMAND = "python -m mattini download regio"
STEP_COMMAND = "python -m mattini surroundings"
AREA_CONFIG_KEYS = {
    "computed_for",
    "expected_columns",
    "expected_lv95_box",
    "expected_rows",
    "expected_sha256",
    "margin_m",
    "spacing_m",
}
BOX_KEYS = {"e_max", "e_min", "n_max", "n_min"}
BLOCK_KEYS = {
    "area",
    "columns",
    "cut_box",
    "file",
    "format",
    "lv95_box",
    "rows",
    "sha256",
    "source",
    "spacing_m",
    "world_sha256",
}
SOURCE_KEYS = {"attribution", "collection", "dataset", "edition", "entry_sha256"}
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
TILE_ID = re.compile(r"([0-9]{4})-([0-9]{4})")
TILE_M = 10_000  # swissALTIRegio tiles are 10 km squares
TILE_ORIGIN_M = (
    5_000,
    4_000,
)  # their south-west corners lie at E = 5 km + 10 km·i, N = 4 km + 10 km·j
NAN_BITS = 0x7FC00000  # the quiet NaN written in the cut (bytes 00 00 c0 7f)
DIGITS = 9  # a position or a height of more digits is no sample of this data
# one sample: x, y, the height's sign, its whole metres, its hundredths (None, one or two digits)
SAMPLE = re.compile(rb"([0-9]{1,9}) ([0-9]{1,9}) (-?)([0-9]{1,9})(?:\.([0-9]{1,2}))?")
WHOLE_METRES = re.compile(rb"[0-9]{1,9}")
HUNDREDTHS = {None: 0}
HUNDREDTHS.update({b"%d" % i: i * 10 for i in range(10)})
HUNDREDTHS.update({b"%02d" % i: i for i in range(100)})

Box = tuple[int, int, int, int]  # e_min, e_max, n_min, n_max, whole metres
Progress = Callable[[str], None]


class SurroundingsError(ValueError):
    """The surroundings cannot be built or no longer match their inputs; the message says why."""


@dataclass(frozen=True)
class _Grid:
    """The area's surroundings grid: what the world config and the config's margin and spacing say."""

    area: str
    spacing: int
    cut: Box  # the area's box: its interior is NaN
    box: Box  # the area's box grown by the margin: the grid's extent
    columns: int
    rows: int


def load_surroundings_config(path: Path | str = SURROUNDINGS_CONFIG_PATH) -> dict:
    """config/surroundings.json, validated by `check_surroundings_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise SurroundingsError(f"{path}: cannot read the surroundings config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise SurroundingsError(f"{path}: not valid JSON: {exc}") from exc
    check_surroundings_config(data, path)
    return data


def check_surroundings_config(data: object, where: Path | str = "the surroundings config") -> None:
    """Refuse a surroundings config that is not schema 2 with exactly one well-formed area.

    An area has exactly the keys `computed_for` (`check_computed_for`), `expected_columns` and
    `expected_rows` (positive whole numbers), `expected_lv95_box` (exactly e_max, e_min, n_max and
    n_min, numbers), `expected_sha256` (the heights file's SHA-256, 64 lower-case hex digits),
    `margin_m` (a whole number of metres, 0 or more, a multiple of `spacing_m`) and `spacing_m` (a
    positive whole number of metres). Schema 1, the 100 m grid of maxima, is refused. The
    SurroundingsError names `where`.
    """

    def fail(message: str) -> SurroundingsError:
        return SurroundingsError(f"{where}: {message}")

    if not isinstance(data, dict) or set(data) != {"schema", "areas"}:
        raise fail("the top level must have exactly the keys ['areas', 'schema']")
    if type(data["schema"]) is not int or data["schema"] != SCHEMA:
        raise fail(f"schema must be {SCHEMA}, found {data['schema']!r}")
    areas = data["areas"]
    if not isinstance(areas, dict) or len(areas) != 1:
        found = sorted(areas) if isinstance(areas, dict) else areas
        raise fail(f"areas must hold exactly one area, found {found!r}")
    for name, area in areas.items():
        if not AREA_NAME.fullmatch(name):
            raise fail(f"area name {name!r} must be lower-case letters, digits and '_'")
        if not isinstance(area, dict) or set(area) != AREA_CONFIG_KEYS:
            raise fail(f"area {name!r} must have exactly the keys {sorted(AREA_CONFIG_KEYS)}")
        spacing, margin = area["spacing_m"], area["margin_m"]
        if type(spacing) is not int or spacing < 1:
            raise fail(
                f"area {name!r}: spacing_m must be a whole number of metres, 1 or more, "
                f"found {spacing!r}"
            )
        if type(margin) is not int or margin < 0 or margin % spacing:
            raise fail(
                f"area {name!r}: margin_m must be a whole number of metres, 0 or more and a "
                f"multiple of spacing_m {spacing}, found {margin!r}"
            )
        for key in ("expected_columns", "expected_rows"):
            if type(area[key]) is not int or area[key] < 1:
                raise fail(
                    f"area {name!r}: {key} must be a positive whole number, found {area[key]!r}"
                )
        box = area["expected_lv95_box"]
        if not isinstance(box, dict) or set(box) != BOX_KEYS:
            raise fail(
                f"area {name!r}: expected_lv95_box must have exactly the keys {sorted(BOX_KEYS)}"
            )
        for key in sorted(BOX_KEYS):
            if not _finite_number(box[key]):
                raise fail(
                    f"area {name!r}: expected_lv95_box[{key!r}] must be a finite number, "
                    f"found {box[key]!r}"
                )
        expected = area["expected_sha256"]
        if not (isinstance(expected, str) and SHA256_HEX.fullmatch(expected)):
            raise fail(
                f"area {name!r}: expected_sha256 must be a SHA-256 in 64 lower-case hex "
                f"characters, found {expected!r}"
            )
        check_computed_for(area["computed_for"], name, fail)


def build_surroundings(
    world: World,
    datasets: dict,
    lock: dict,
    surroundings_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's surroundings from the downloaded, locked tiles; return its block.

    The checks come in the order the module's docstring gives, each before the next reads
    anything, every refusal a SurroundingsError naming what is wrong and the command or the
    design step that fixes it. The heights' SHA-256 must equal `expected_sha256`; it is
    compared before anything is written, and a difference names both values (lesson 38).
    """
    say = progress or (lambda message: None)
    if world.mapping != OWNER_AXES:
        raise SurroundingsError(
            f"{world.path}: the surroundings support only the axes x = +e, y = +h, z = -n"
        )
    check_surroundings_config(surroundings_config, SURROUNDINGS_CONFIG_NAME)
    area = configured_area(surroundings_config)
    settings = surroundings_config["areas"][area]
    if area not in world.areas:
        raise SurroundingsError(
            f"{world.path}: no area named {area!r} for the surroundings config's area"
        )
    grid = _grid_of(world, area, settings, SurroundingsError)
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise SurroundingsError(
            f"{world.path}: the world config changed while the surroundings were built"
        )
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    problem = world_refusal(SURROUNDINGS_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise SurroundingsError(f"area {area!r}: {problem}")
    problem = _expected_problem(grid, settings)
    if problem:
        raise SurroundingsError(problem)

    regio = _regio_config(datasets, SurroundingsError)
    problem = _fit_problem(lock, regio, grid)
    if problem:
        raise SurroundingsError(problem)
    entry = lock["datasets"][DATASET]
    problem = inputs_refusal(SURROUNDINGS_CONFIG_NAME, settings["computed_for"], DATASET, entry)
    if problem:
        raise SurroundingsError(f"area {area!r}: {problem}")
    tiles = _tiles_needed(grid)
    locked = entry["tiles"]
    raw_dir = Path(raw_root) / DATASET / regio["edition"]
    listed = _provenance_tiles(raw_dir / PROVENANCE, regio, tiles, locked)

    sums = np.zeros((grid.rows, grid.columns), dtype=np.int64)  # whole centimetres, exact
    counts = np.zeros((grid.rows, grid.columns), dtype=np.int64)
    for tile in tiles:
        path = raw_dir / listed[tile]["file"]
        say(f"reading {path}")
        data = _read_bytes(path, tile)  # the bytes verified are the bytes parsed
        actual = hashlib.sha256(data).hexdigest()
        if actual != locked[tile]["sha256"]:
            raise SurroundingsError(
                f"tile {tile}: {path} has SHA-256 {actual}, provenance.json and the lock pin "
                f"{locked[tile]['sha256']}; `{DOWNLOAD_COMMAND}` fetches it again"
            )
        x, y, centimetres = _tile_samples(data, tile, path, regio["resolution_m"])
        del data
        _accumulate(grid, x, y, centimetres, sums, counts)

    say(f"computing {grid.columns} × {grid.rows} vertices at {grid.spacing} m")
    cut = _cut_mask(grid)
    missing = np.argwhere((counts == 0) & ~cut)
    if len(missing):
        row, column = (int(v) for v in missing[0])
        raise SurroundingsError(
            f"vertex (row {row}, column {column}) at LV95 ({_easting(grid, column)}, "
            f"{_northing(grid, row)}) keeps a height but its square holds no sample "
            f"({len(missing)} such vertices); `{DOWNLOAD_COMMAND}` fetches the tiles again"
        )
    heights = _heights(sums, counts, cut, world.height_offset)
    data = heights.tobytes()
    block = {
        "area": area,
        "columns": grid.columns,
        "cut_box": _box_block(grid.cut),
        "file": f"surroundings/{area}.f32",
        "format": FORMAT,
        "lv95_box": _box_block(grid.box),
        "rows": grid.rows,
        "sha256": hashlib.sha256(data).hexdigest(),
        "source": {
            "attribution": regio["attribution"],
            "collection": regio["collection"],
            "dataset": DATASET,
            "edition": regio["edition"],
            "entry_sha256": entry_sha256(entry),
        },
        "spacing_m": float(grid.spacing),
        "world_sha256": world_sha256,
    }
    expected = settings["expected_sha256"]
    if block["sha256"] != expected:
        raise SurroundingsError(
            f"area {area!r}: the heights built here have SHA-256 {block['sha256']}, "
            f"{SURROUNDINGS_CONFIG_NAME} expects {expected}. Design computed the expected value "
            f"two independent ways, so this machine or this code produces other heights than "
            f"the design's; nothing was written"
        )
    say(f"the heights have the SHA-256 {SURROUNDINGS_CONFIG_NAME} expects, {expected}")
    removed = _write_files(out_dir, data, block)
    say(f"wrote {Path(out_dir) / block['file']} ({grid.columns} × {grid.rows} vertices)")
    if removed:
        say(f"removed {removed} .part file{'' if removed == 1 else 's'} left in surroundings/")
    return block


def built_surroundings_block(
    out_dir: Path | str,
    surroundings_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str,
) -> dict | None:
    """The description of the surroundings built in `out_dir`, or None when none is built.

    `lock` is the lock as a dict or the lock file's path; it is read only when something is
    built. `world` is the world config the manifest is written from, parsed from the bytes whose
    SHA-256 is `world_sha256`. In the step's order: the config's `computed_for` against the
    world, then the config's expected box against the world's area, then the lock's fit (refused
    naming `python -m mattini lock regio` and no other command), then `computed_for` against the
    lock's entry. A difference in the world or the entry is a SurroundingsError naming design's
    step, not the rebuild, which would be refused for the same reason. Anything else that no
    longer holds is refused naming `python -m mattini surroundings`: a description that is not
    exactly the one the step writes for this world, spacing, box, source and entry, a heights
    file of another size or SHA-256 than the description pins, or one that is not the config's
    expected value.
    """
    check_surroundings_config(surroundings_config, SURROUNDINGS_CONFIG_NAME)
    area = configured_area(surroundings_config)
    settings = surroundings_config["areas"][area]
    path = Path(out_dir) / "surroundings" / f"{area}.json"
    if not path.exists():
        return None

    def fail(message: str) -> SurroundingsError:
        return SurroundingsError(f"{path}: {message}; `{STEP_COMMAND}` rebuilds the surroundings")

    problem = world_refusal(SURROUNDINGS_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise SurroundingsError(f"area {area!r}: {problem}")
    tile_lock = _lock_of(lock)
    if world.mapping != OWNER_AXES:
        raise fail(f"{world.path}: the surroundings support only the axes x = +e, y = +h, z = -n")
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    grid = _grid_of(world, area, settings, fail)
    problem = _expected_problem(grid, settings)
    if problem:
        raise SurroundingsError(problem)
    regio = _regio_config(datasets, fail)
    problem = _fit_problem(tile_lock, regio, grid)
    if problem:
        raise SurroundingsError(problem)
    entry = tile_lock["datasets"][DATASET]
    problem = inputs_refusal(SURROUNDINGS_CONFIG_NAME, settings["computed_for"], DATASET, entry)
    if problem:
        raise SurroundingsError(f"area {area!r}: {problem}")

    try:
        block = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the surroundings description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    wanted = {"area": area, "file": f"surroundings/{area}.f32", "format": FORMAT}
    for key, value in wanted.items():
        if block[key] != value:
            raise fail(f"{key} is {block[key]!r}, expected {value!r}")
    if block["world_sha256"] != world_sha256:
        raise fail(
            f"it was built for the world config with SHA-256 {block['world_sha256']}, "
            f"the world config now has {world_sha256}"
        )
    if type(block["spacing_m"]) is not float or block["spacing_m"] != grid.spacing:
        raise fail(
            f"it was built at {block['spacing_m']!r} m, the config asks for {grid.spacing} m"
        )
    for key, box in (("lv95_box", grid.box), ("cut_box", grid.cut)):
        if not _is_box_block(block[key], box):
            raise fail(
                f"{key} is {block[key]!r}, the world config's area {area!r} needs {_box_block(box)!r}"
            )
    for key, count in (("columns", grid.columns), ("rows", grid.rows)):
        if type(block[key]) is not int or block[key] != count:
            raise fail(f"{key} is {block[key]!r}, the world config's area {area!r} needs {count}")
    source = block["source"]
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise fail(f"its source must have exactly the keys {sorted(SOURCE_KEYS)}")
    sourced = {
        "attribution": regio["attribution"],
        "collection": regio["collection"],
        "dataset": DATASET,
        "edition": regio["edition"],
        "entry_sha256": entry_sha256(entry),
    }
    for key, value in sourced.items():
        if source[key] != value:
            raise fail(f"its source's {key} is {source[key]!r}, expected {value!r}")
    heights = Path(out_dir) / block["file"]
    try:
        size = heights.stat().st_size
        actual = _sha256_of(heights)
    except OSError as exc:
        raise fail(f"its heights file cannot be read: {exc}") from exc
    if size != grid.rows * grid.columns * 4:
        raise fail(
            f"{heights} holds {size} bytes, {grid.rows} × {grid.columns} heights need "
            f"{grid.rows * grid.columns * 4}"
        )
    if actual != block["sha256"]:
        raise fail(f"{heights} has SHA-256 {actual}, the description pins {block['sha256']}")
    if actual != settings["expected_sha256"]:
        raise fail(
            f"{heights} has SHA-256 {actual}, the surroundings config expects "
            f"{settings['expected_sha256']}"
        )
    return block


def _finite_number(value: object) -> bool:
    """Whether `value` is a JSON number (not a boolean) that is finite."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:  # an integer too large for a float
        return False


def _grid_of(
    world: World, area: str, settings: dict, fail: Callable[[str], SurroundingsError]
) -> _Grid:
    """The area's grid; the area's corners must lie on the spacing lattice (else `fail`)."""
    spacing, margin = settings["spacing_m"], settings["margin_m"]
    corners = []
    for name, value in zip(("e_min", "e_max", "n_min", "n_max"), world.area(area), strict=True):
        if not (float(value).is_integer() and int(value) % spacing == 0):
            raise fail(
                f"{world.path}: area {area!r}: {name} {value!r} is not a multiple of the "
                f"{spacing} m spacing, so its edge lies between two vertices of the surroundings"
            )
        corners.append(int(value))
    e_min, e_max, n_min, n_max = corners
    box = (e_min - margin, e_max + margin, n_min - margin, n_max + margin)
    return _Grid(
        area=area,
        spacing=spacing,
        cut=(e_min, e_max, n_min, n_max),
        box=box,
        columns=(box[1] - box[0]) // spacing + 1,
        rows=(box[3] - box[2]) // spacing + 1,
    )


def _expected_problem(grid: _Grid, settings: dict) -> str | None:
    """Why design's box, columns or rows are not the world config's area grown by the margin."""
    found = {
        "expected_lv95_box": (_box_block(grid.box), settings["expected_lv95_box"]),
        "expected_columns": (grid.columns, settings["expected_columns"]),
        "expected_rows": (grid.rows, settings["expected_rows"]),
    }
    for key, (built, expected) in found.items():
        if built != expected:
            return (
                f"area {grid.area!r}: the world config's area grown by the margin gives "
                f"{built!r}, {SURROUNDINGS_CONFIG_NAME}'s {key} is {expected!r}. A changed area "
                f"or margin is a design change: design recomputes the expected values "
                f"(docs/SPEC.md §8)"
            )
    return None


def _regio_config(datasets: object, fail: Callable[[str], SurroundingsError]) -> dict:
    """The datasets config's swissALTIRegio entry, once its keys are shown usable."""
    config = datasets.get(DATASET) if isinstance(datasets, dict) else None
    if not isinstance(config, dict):
        raise fail(f"{DATASETS_CONFIG_NAME} has no {DATASET!r} dataset")
    for key in ("attribution", "collection", "edition"):
        if not (isinstance(config.get(key), str) and config[key]):
            raise fail(
                f"{DATASETS_CONFIG_NAME}: {DATASET} {key} must be a text, found {config.get(key)!r}"
            )
    resolution = config.get("resolution_m")
    if type(resolution) is not int or resolution < 1 or TILE_M % resolution:
        raise fail(
            f"{DATASETS_CONFIG_NAME}: {DATASET} resolution_m must be a whole number of metres "
            f"that divides the {TILE_M} m tile, found {resolution!r}"
        )
    return config


def _tiles_needed(grid: _Grid) -> list[str]:
    """The ids (`<E km>-<N km>`) of the tiles that meet the box grown by half a spacing, sorted.

    A tile [E0, E0 + 10 km) × [N0, N0 + 10 km) is needed when it meets [e_min − s/2, e_max + s/2)
    × [n_min − s/2, n_max + s/2): the samples a vertex takes its height from. East outer, north
    inner: the order of the lock, provenance.json and the reading.
    """
    e_min, e_max, n_min, n_max = grid.box
    east = _corners_km(2 * e_min - grid.spacing, 2 * e_max + grid.spacing, TILE_ORIGIN_M[0])
    north = _corners_km(2 * n_min - grid.spacing, 2 * n_max + grid.spacing, TILE_ORIGIN_M[1])
    return [f"{e:04d}-{n:04d}" for e in east for n in north]


def _corners_km(low2: int, high2: int, origin_m: int) -> list[int]:
    """The corners, in whole km, of the tile squares meeting [low2/2, high2/2) on one axis."""
    step = 2 * TILE_M
    first = (low2 - 2 * origin_m) // step
    last = -((2 * origin_m - high2) // step)  # the ceiling
    return [(origin_m + i * TILE_M) // 1000 for i in range(first, last)]


def _fit_problem(lock: object, regio: dict, grid: _Grid) -> str | None:
    """Why the lock's entry does not fit the datasets config and the grid, or None.

    It fits when it exists, is for the datasets config's collection, edition and resolution, and
    pins exactly the tiles the surroundings need, none missing and none beside them, each as
    exactly a file name and a SHA-256. The text is the whole refusal: it names the area and
    `python -m mattini lock regio`, and no other command.
    """

    def problem(message: str) -> str:
        return (
            f"the lock {message} (area {grid.area!r}); `{LOCK_COMMAND}` writes the lock's "
            f"{DATASET} entry for the config"
        )

    datasets = lock.get("datasets") if isinstance(lock, dict) else None
    entry = datasets.get(DATASET) if isinstance(datasets, dict) else None
    if not isinstance(entry, dict):
        return problem(f"has no {DATASET!r} entry")
    for key in ("collection", "edition", "resolution_m"):
        if entry.get(key) != regio[key]:
            return problem(
                f"is for {DATASET} {key} {entry.get(key)!r}, the config pins {regio[key]!r}"
            )
    pinned = entry.get("tiles")
    if not isinstance(pinned, dict):
        return problem("has no tiles")
    needed = _tiles_needed(grid)
    missing = [tile for tile in needed if tile not in pinned]
    if missing:
        return problem(f"pins no checksum for the tiles {missing} the surroundings need")
    if set(pinned) != set(needed):
        return problem(f"pins the tiles {sorted(pinned)}, the surroundings need exactly {needed}")
    for tile in needed:
        pin = pinned[tile]
        if not (
            isinstance(pin, dict)
            and set(pin) == {"file", "sha256"}
            and isinstance(pin["file"], str)
            and SAFE_NAME.fullmatch(pin["file"])
            and isinstance(pin["sha256"], str)
            and SHA256_HEX.fullmatch(pin["sha256"])
        ):
            return problem(
                f"pins the tile {tile} as {pin!r}, not exactly a file name and a SHA-256"
            )
    return None


def _provenance_tiles(path: Path, regio: dict, tiles: list[str], locked: dict) -> dict[str, dict]:
    """provenance.json's entries by tile, once it is shown to be the locked download."""

    def fail(message: str) -> SurroundingsError:
        return SurroundingsError(
            f"{path}: {message}; `{DOWNLOAD_COMMAND}` downloads what it asks for"
        )

    try:
        provenance = json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError as exc:
        raise fail("no download has completed here") from exc
    except OSError as exc:
        raise fail(f"cannot read it: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(provenance, dict):
        raise fail("it is not a JSON object")
    for key in ("dataset", "collection", "edition", "resolution_m"):
        wanted = DATASET if key == "dataset" else regio[key]
        if provenance.get(key) != wanted:
            raise fail(f"it lists {key} {provenance.get(key)!r}, the config asks for {wanted!r}")
    entries = provenance.get("tiles")
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise fail("its tiles are not a list of objects")
    listed = [entry.get("tile") for entry in entries]
    if listed != tiles:
        raise fail(f"it lists the tiles {listed}, the surroundings need {tiles}")
    for entry in entries:
        # the lock's file names are plain (`_fit_problem`), so a name equal to the lock's is too
        tile, name, sha256 = entry["tile"], entry.get("file"), entry.get("sha256")
        if name != locked[tile]["file"] or sha256 != locked[tile]["sha256"]:
            raise fail(
                f"tile {tile}: it lists {name!r} with SHA-256 {sha256!r}, the lock pins "
                f"{locked[tile]['file']!r} with SHA-256 {locked[tile]['sha256']!r}"
            )
    return {entry["tile"]: entry for entry in entries}


def _read_bytes(path: Path, tile: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SurroundingsError(
            f"tile {tile}: cannot read {path}: {exc}; `{DOWNLOAD_COMMAND}` fetches it again"
        ) from exc


def _tile_samples(
    data: bytes, tile: str, path: Path, resolution: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The samples of a tile (the bytes of `path`): x, y in whole metres, heights in centimetres.

    The tile must be what its id says: one member `<E km>_<N km>.xyz`, the header `x y z`, every
    line three fields (x and y whole metres, the height whole centimetres), every point on the
    tile's cell centres inside its square, at most once. The lines may come in any order.
    """

    def fail(message: str) -> SurroundingsError:
        return SurroundingsError(
            f"tile {tile}: {path}: {message}; `{DOWNLOAD_COMMAND}` fetches it again"
        )

    e_km, n_km = (int(v) for v in TILE_ID.fullmatch(tile).groups())
    west, south = e_km * 1000, n_km * 1000
    member = tile.replace("-", "_") + ".xyz"
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            names = archive.namelist()
            if names != [member]:
                raise fail(f"it holds {names}, expected the one member {member!r}")
            raw = archive.read(member)
    except (
        zipfile.BadZipFile,
        zlib.error,
        EOFError,
        OSError,
        RuntimeError,  # an encrypted member, and (a subclass) a compression method not supported
        UnicodeDecodeError,  # a member name flagged UTF-8 that is not (zipfile decodes it)
    ) as exc:
        raise fail(f"cannot read it as a zip: {exc}") from exc

    lines = raw.split(b"\r\n")
    if lines[0] != b"x y z":
        raise fail(f"the header is {_text(lines[0])!r}, expected 'x y z'")
    if lines.pop() != b"":
        raise fail("its last line does not end with a line end (CR LF)")
    del lines[0]  # the header was line 1: the first sample is line 2
    xs, ys, cents = [], [], []
    for number, line in enumerate(lines, start=2):
        match = SAMPLE.fullmatch(line)
        if match is None:
            raise fail(f"line {number}: {_line_problem(line)}")
        x, y, sign, whole, hundredths = match.groups()
        value = int(whole) * 100 + HUNDREDTHS[hundredths]
        xs.append(int(x))
        ys.append(int(y))
        cents.append(-value if sign else value)
    x = np.array(xs, dtype=np.int64)
    y = np.array(ys, dtype=np.int64)
    del xs, ys

    # a cell centre is W + r/2 + r·i, so 2 (x − W) − r = 2 r i with 0 <= i < cells
    cells = TILE_M // resolution
    ix, rx = np.divmod(2 * (x - west) - resolution, 2 * resolution)
    iy, ry = np.divmod(2 * (y - south) - resolution, 2 * resolution)
    off = (rx != 0) | (ry != 0) | (ix < 0) | (ix >= cells) | (iy < 0) | (iy >= cells)
    if off.any():
        k = int(np.argmax(off))
        raise fail(
            f"line {k + 2}: the point ({x[k]}, {y[k]}) is not one of the tile's cell centres "
            f"at {resolution} m inside its square"
        )
    _, first = np.unique(ix * cells + iy, return_index=True)
    again = np.ones(len(x), dtype=bool)
    again[first] = False
    if again.any():
        k = int(np.argmax(again))
        raise fail(f"line {k + 2}: the point ({x[k]}, {y[k]}) is given more than once")
    return x, y, np.array(cents, dtype=np.int64)


def _line_problem(line: bytes) -> str:
    """Why a sample line is not `x y z` with whole-metre x and y and a whole-centimetre z."""
    parts = line.split(b" ")
    if len(parts) != 3:
        return f"{_text(line)!r} is not three fields `x y z` separated by single spaces"
    for name, text in (("x", parts[0]), ("y", parts[1])):
        if not WHOLE_METRES.fullmatch(text):
            return (
                f"{name} {_text(text)!r} is not a whole number of metres ({DIGITS} digits at most)"
            )
    return (
        f"the height text {_text(parts[2])!r} is not whole centimetres: `-?[0-9]+`, at most "
        f"{DIGITS} digits, with at most two decimals after a point"
    )


def _text(raw: bytes) -> str:
    return raw.decode("ascii", errors="replace")


def _accumulate(
    grid: _Grid,
    x: np.ndarray,
    y: np.ndarray,
    cents: np.ndarray,
    sums: np.ndarray,
    counts: np.ndarray,
) -> None:
    """Add each sample to the vertex whose half-open square holds it, in whole centimetres.

    Vertex column c holds E = e_min + c·s, so x lies in [E − s/2, E + s/2) when c is the floor of
    (2 (x − e_min) + s) / 2 s. Vertex row r holds N = n_max − r·s, and y lies in [N − s/2,
    N + s/2) when r·s − s/2 < n_max − y <= r·s + s/2, so r is the floor of
    (2 (n_max − y) + s − 1) / 2 s. A sample outside the grid's squares adds to nothing.
    """
    s = grid.spacing
    column = (2 * (x - grid.box[0]) + s) // (2 * s)
    row = (2 * (grid.box[3] - y) + s - 1) // (2 * s)
    inside = (column >= 0) & (column < grid.columns) & (row >= 0) & (row < grid.rows)
    np.add.at(sums, (row[inside], column[inside]), cents[inside])
    np.add.at(counts, (row[inside], column[inside]), 1)


def _easting(grid: _Grid, column: int) -> int:
    return grid.box[0] + column * grid.spacing


def _northing(grid: _Grid, row: int) -> int:
    return grid.box[3] - row * grid.spacing


def _cut_mask(grid: _Grid) -> np.ndarray:
    """The vertices strictly inside the area's box (rows × columns): NaN, the real terrain's."""
    eastings = grid.box[0] + grid.spacing * np.arange(grid.columns, dtype=np.int64)
    northings = grid.box[3] - grid.spacing * np.arange(grid.rows, dtype=np.int64)
    inside_e = (eastings > grid.cut[0]) & (eastings < grid.cut[1])
    inside_n = (northings > grid.cut[2]) & (northings < grid.cut[3])
    return np.outer(inside_n, inside_e)


def _heights(sums: np.ndarray, counts: np.ndarray, cut: np.ndarray, offset: float) -> np.ndarray:
    """The grid's little-endian float32 heights: the exact mean minus the offset, one rounding.

    `sums` are whole centimetres and `counts` the samples each square holds; the quotient
    `sum / (100 · count)` is one correctly rounded 64-bit division of two exact integers, the
    64-bit offset is subtracted, and the result is rounded once to 32-bit. The cut is NaN.
    """
    mean = sums / (100.0 * np.maximum(counts, 1))
    heights = (mean - float(offset)).astype("<f4")
    heights.view("<u4")[cut] = NAN_BITS
    return heights


def _box_block(box: Box) -> dict:
    e_min, e_max, n_min, n_max = box
    return {
        "e_max": float(e_max),
        "e_min": float(e_min),
        "n_max": float(n_max),
        "n_min": float(n_min),
    }


def _is_box_block(found: object, box: Box) -> bool:
    """Whether `found` is exactly `_box_block(box)`: the same keys, each a float and equal."""
    wanted = _box_block(box)
    return (
        isinstance(found, dict)
        and set(found) == set(wanted)
        and all(type(found[key]) is float and found[key] == value for key, value in wanted.items())
    )


def _lock_of(lock: dict | Path | str) -> dict:
    """The tile lock: the dict itself, or the JSON file at the path."""
    if isinstance(lock, dict):
        return lock
    path = Path(lock)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise SurroundingsError(f"{path}: cannot read the tile lock: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise SurroundingsError(f"{path}: the tile lock is not valid JSON: {exc}") from exc
    return data


def _write_files(out_dir: Path | str, data: bytes, block: dict) -> int:
    """Write `surroundings/<area>.f32` (through a `.part` rename), then `surroundings/<area>.json`.

    Then remove every `*.part` in `surroundings/`, the files of a run cut short between a write
    and its rename, which an export would ship; only this folder is cleaned. Returns how many
    were removed.
    """
    folder = Path(out_dir) / "surroundings"
    folder.mkdir(parents=True, exist_ok=True)
    _replace(folder / f"{block['area']}.f32", data)
    _replace(folder / f"{block['area']}.json", _json_bytes(block))
    leftovers = [path for path in sorted(folder.glob("*.part")) if path.is_file()]
    for path in leftovers:
        path.unlink()
    return len(leftovers)


def _sha256_of(path: Path) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)
