"""The terrain grid: swissALTI3D tiles to a heights file for Terrain3D (M1-03, M2-01; SPEC §8).

A vertex every `spacing_m` from the area's north-west corner, its edges included: row r,
column c is LV95 (e_min + c·s, n_max − r·s). Its height is the area-weighted mean of the
0.5 m source pixels under the s × s square centred on it, clipped to the area, minus
`height_offset_m` (so local y). The square always covers whole or equally cut pixels, so
the mean is the plain mean of the 2 × 2 (0.5 and 1 m) or 4 × 4 (2 m) pixels around the
vertex, fewer at the area's edges; the counts are powers of two. The sums of up to 16
32-bit heights are exact in 64-bit, so the mean is exact. The height offset is subtracted
in 64-bit, which is exact for every offset in use (0, 1000 and -12.25 m), and the result
is rounded once to 32-bit: the same bits on every machine, whatever the summation order
(Hard Rule 5). An offset with many binary fraction digits would make the subtraction round
too, a second rounding of at most one 32-bit step (SPEC §8, M1 R1 T-08).

The heights must be the ones design computed: config/terrain.json holds, per spacing, the
SHA-256 of the heights file (`expected_sha256`), and the step compares its output with the
value for its spacing before it writes anything (lesson 38, M1 R1 T-01). The manifest
re-checks a built terrain against that value, the datasets config and the tile lock, and
its box, rows and columns against the world config's area at the spacing (M2-06).

The inputs are the tiles `provenance.json` lists (D9), never the folder's listing; every
file's SHA-256 must equal its provenance entry and the tile lock's (D7), and every tile
must be where its id says with no nodata and no non-finite height in the area. Each
refusal is a TerrainError naming the file or tile and the command that fixes it (Hard
Rule 2).

The file: little-endian float32, row-major, rows north to south (+z), columns west to
east (+x), no header, `terrain/<area>.f32`; its description `terrain/<area>.json`, which
the manifest copies verbatim. Only the owner's axes (x = +e, y = +h, z = −n) are
supported: another mapping would place these rows and columns wrongly (Hard Rule 4).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Callable
from pathlib import Path

import numpy as np
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile

from mattini.download import DATASET, PROVENANCE, area_tiles
from mattini.lock import LOCK_PATH, load_lock
from mattini.world import REPO, SOURCE_AXES, World, parse_world, read_config_bytes

TERRAIN_CONFIG_PATH = REPO / "config" / "terrain.json"
TERRAIN_CONFIG_NAME = "config/terrain.json"  # the home of the expected heights, for messages
SCHEMA = 1
SPACINGS = (0.5, 1.0, 2.0)
SPACING_KEYS = ("0.5", "1", "2")  # SPACINGS as swisstopo writes them: format(s, "g")
AREA_CONFIG_KEYS = {"expected_sha256", "spacing_m"}
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SOURCE_M = 0.5  # swissALTI3D pixel size; every spacing is a whole number of pixels
FORMAT = "float32-le"
TILE_M = 1000
TILE_PIXELS = round(TILE_M / SOURCE_M)
TILE_EPSG = 2056
TERRAIN_COMMAND = "python -m mattini terrain"
DOWNLOAD_COMMAND = "python -m mattini download terrain"
LOCK_COMMAND = "python -m mattini lock terrain"
# World.mapping of x = +e, y = +h, z = -n: (sign, source axis) per game axis
OWNER_AXES = tuple(
    (sign, SOURCE_AXES.index(axis)) for sign, axis in ((1.0, "e"), (1.0, "h"), (-1.0, "n"))
)
TILE_ID = re.compile(r"([0-9]+)-([0-9]+)")
AREA_NAME = re.compile(r"[a-z][a-z0-9_]*")  # it names the files terrain/<area>.f32 and .json
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
BLOCK_KEYS = {
    "area",
    "columns",
    "file",
    "format",
    "lv95_box",
    "rows",
    "sha256",
    "source",
    "spacing_m",
    "world_sha256",
}
SOURCE_KEYS = {"attribution", "collection", "dataset", "edition", "resolution_m", "tiles"}
SOURCE_TILE_KEYS = {"sha256", "tile"}

Box = tuple[float, float, float, float]  # e_min, e_max, n_min, n_max
Progress = Callable[[str], None]


class TerrainError(ValueError):
    """The terrain cannot be built or no longer matches its inputs; the message says why."""


def load_terrain_config(path: Path | str = TERRAIN_CONFIG_PATH) -> dict:
    """config/terrain.json, validated by `check_terrain_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise TerrainError(f"{path}: cannot read the terrain config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise TerrainError(f"{path}: not valid JSON: {exc}") from exc
    check_terrain_config(data, path)
    return data


def check_terrain_config(data: object, where: Path | str = "the terrain config") -> None:
    """Refuse a terrain config that is not schema 1 with exactly one well-formed area.

    An area has exactly the keys `expected_sha256` and `spacing_m`: an allowed spacing, and
    an object from spacings as swisstopo writes them ("0.5", "1", "2") to the SHA-256 of
    the heights file at that spacing, 64 lower-case hex digits, holding the configured
    spacing (SPEC §8). The TerrainError names `where`.
    """

    def fail(message: str) -> TerrainError:
        return TerrainError(f"{where}: {message}")

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
        if not _is_spacing(area["spacing_m"]):
            raise fail(
                f"area {name!r}: spacing_m must be one of {list(SPACINGS)}, "
                f"found {area['spacing_m']!r}"
            )
        expected = area["expected_sha256"]
        if not isinstance(expected, dict):
            raise fail(f"area {name!r}: expected_sha256 must be an object, found {expected!r}")
        unknown = [key for key in expected if key not in SPACING_KEYS]
        if unknown:
            raise fail(
                f"area {name!r}: expected_sha256 holds only the spacings {list(SPACING_KEYS)} "
                f"as swisstopo writes them, found {unknown!r}"
            )
        for key, value in expected.items():
            if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):
                raise fail(
                    f"area {name!r}: expected_sha256[{key!r}] must be a SHA-256 in 64 "
                    f"lower-case hex characters, found {value!r}"
                )
        if spacing_key(area["spacing_m"]) not in expected:
            raise fail(
                f"area {name!r}: expected_sha256 holds no value for the configured spacing "
                f"{spacing_key(area['spacing_m'])!r}"
            )


def configured_area(terrain_config: dict) -> str:
    """The one area a validated terrain config names: the area the pipeline serves (T-06)."""
    ((area, _),) = terrain_config["areas"].items()
    return area


def spacing_key(spacing_m: float) -> str:
    """A spacing as swisstopo writes it, the key of `expected_sha256`: 0.5 -> "0.5", 2.0 -> "2"."""
    return format(spacing_m, "g")


def resample(mosaic: np.ndarray, box: Box, spacing_m: float, height_offset_m: float) -> np.ndarray:
    """The grid's 32-bit heights (rows × columns) from a 0.5 m, north-up 32-bit mosaic.

    `mosaic` covers `box` = (e_min, e_max, n_min, n_max) exactly: row 0 is the northern
    pixel row, column 0 the western pixel column.
    """
    if not _is_spacing(spacing_m):
        raise TerrainError(f"spacing_m must be one of {list(SPACINGS)}, found {spacing_m!r}")
    if not (isinstance(height_offset_m, int | float) and math.isfinite(height_offset_m)):
        raise TerrainError(f"height_offset_m must be a finite number, found {height_offset_m!r}")
    if not isinstance(mosaic, np.ndarray) or mosaic.ndim != 2 or mosaic.dtype != np.float32:
        raise TerrainError("the mosaic must be a two-dimensional array of 32-bit floats")
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    for name, value in zip(("e_min", "e_max", "n_min", "n_max"), box, strict=True):
        if not _whole(float(value) / SOURCE_M):
            raise TerrainError(f"the box's {name} {value!r} is not on the 0.5 m source grid")
    height, width = _whole_count(n_max - n_min, SOURCE_M), _whole_count(e_max - e_min, SOURCE_M)
    if height < 1 or width < 1:
        raise TerrainError(f"the box {box!r} is empty")
    if mosaic.shape != (height, width):
        raise TerrainError(
            f"the mosaic is {mosaic.shape[0]} × {mosaic.shape[1]} pixels, the box needs "
            f"{height} × {width}"
        )
    step = round(spacing_m / SOURCE_M)  # pixels per spacing: 1, 2 or 4
    if height % step or width % step:
        raise TerrainError(f"the box {box!r} is not a whole number of {spacing_m} m cells")
    bad = np.argwhere(~np.isfinite(mosaic))
    if len(bad):
        row, column = (int(v) for v in bad[0])
        raise TerrainError(
            f"source pixel (row {row}, column {column}) is {mosaic[row, column]!r}, not a height"
        )

    rows, columns = height // step + 1, width // step + 1
    half = max(1, step // 2)  # the window around a vertex: 2 × 2 or 4 × 4 pixels
    padded = np.pad(mosaic, half)  # zeros outside the area add nothing to a sum
    total = np.zeros((rows, columns), dtype=np.float64)
    for di in range(2 * half):
        for dj in range(2 * half):
            # exact: each vertex's sum holds at most 16 32-bit heights
            total += padded[
                di : di + (rows - 1) * step + 1 : step, dj : dj + (columns - 1) * step + 1 : step
            ]
    count = np.outer(
        _window_counts(rows, step, half, height), _window_counts(columns, step, half, width)
    )
    return (total / count - float(height_offset_m)).astype(np.float32)


def write_terrain(
    out_dir: Path | str,
    area: str,
    heights: np.ndarray,
    box: Box,
    spacing_m: float,
    world_sha256: str,
    source: dict,
) -> dict:
    """Write `terrain/<area>.f32` (through a `.part` rename), then `terrain/<area>.json`.

    Returns the description, which is what the `.json` holds.
    """
    data, block = _describe(area, heights, box, spacing_m, world_sha256, source)
    _write_files(out_dir, data, block)
    return block


def _describe(
    area: str,
    heights: np.ndarray,
    box: Box,
    spacing_m: float,
    world_sha256: str,
    source: dict,
) -> tuple[bytes, dict]:
    """The heights file's bytes and its description; nothing is written."""
    if heights.ndim != 2 or heights.dtype != np.float32:
        raise TerrainError("heights must be a two-dimensional array of 32-bit floats")
    if not AREA_NAME.fullmatch(area):
        raise TerrainError(f"area name {area!r} must be lower-case letters, digits and '_'")
    data = np.ascontiguousarray(heights, dtype="<f4").tobytes()
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    block = {
        "area": area,
        "columns": int(heights.shape[1]),
        "file": f"terrain/{area}.f32",
        "format": FORMAT,
        "lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},
        "rows": int(heights.shape[0]),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source": source,
        "spacing_m": float(spacing_m),
        "world_sha256": world_sha256,
    }
    return data, block


def _write_files(out_dir: Path | str, data: bytes, block: dict) -> None:
    """Write `terrain/<area>.f32` (through a `.part` rename), then `terrain/<area>.json`."""
    terrain_dir = Path(out_dir) / "terrain"
    terrain_dir.mkdir(parents=True, exist_ok=True)
    _replace(terrain_dir / f"{block['area']}.f32", data)
    _replace(terrain_dir / f"{block['area']}.json", _json_bytes(block))


def build_terrain(
    world: World,
    datasets: dict,
    lock: dict,
    terrain_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's terrain from the downloaded, locked tiles; return its block.

    The heights' SHA-256 must equal the terrain config's `expected_sha256` for the spacing;
    it is compared before anything is written, and a difference is a TerrainError naming
    both values (SPEC §8, lesson 38).
    """
    say = progress or (lambda message: None)
    if world.mapping != OWNER_AXES:
        raise TerrainError(
            f"{world.path}: the terrain supports only the axes x = +e, y = +h, z = -n"
        )
    check_terrain_config(terrain_config)
    area = configured_area(terrain_config)
    spacing = terrain_config["areas"][area]["spacing_m"]
    expected = terrain_config["areas"][area]["expected_sha256"][spacing_key(spacing)]
    if area not in world.areas:
        raise TerrainError(f"{world.path}: no area named {area!r} for the terrain config's area")
    box = world.area(area)
    e_min, e_max, n_min, n_max = box
    if not (
        _whole((e_min - world.origin_e) / spacing) and _whole((n_max - world.origin_n) / spacing)
    ):
        raise TerrainError(
            f"{world.path}: area {area!r}: its north-west corner ({e_min}, {n_max}) is not on "
            f"the {spacing} m vertex lattice from the origin"
        )
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise TerrainError(f"{world.path}: the world config changed while the terrain was built")

    alti = datasets[DATASET]
    if alti["resolution_m"] != SOURCE_M:
        raise TerrainError(
            f"the terrain is built from {SOURCE_M} m swissALTI3D pixels, the datasets config "
            f"pins resolution_m {alti['resolution_m']!r}"
        )
    tiles = area_tiles(world, area)
    raw_dir = Path(raw_root) / DATASET / alti["edition"]
    listed = _provenance_tiles(raw_dir / PROVENANCE, alti, tiles)
    locked = _locked_tiles(lock, alti, tiles)

    height, width = _whole_count(n_max - n_min, SOURCE_M), _whole_count(e_max - e_min, SOURCE_M)
    mosaic = np.full((height, width), np.nan, dtype=np.float32)
    source_tiles = []
    for tile in tiles:
        entry = listed[tile]
        path = raw_dir / entry["file"]
        say(f"reading {path}")
        if entry["file"] != locked[tile]["file"] or entry["sha256"] != locked[tile]["sha256"]:
            raise TerrainError(
                f"tile {tile}: provenance.json lists {entry['file']} with SHA-256 "
                f"{entry['sha256']}, the tile lock pins {locked[tile]['file']} with SHA-256 "
                f"{locked[tile]['sha256']}; `{DOWNLOAD_COMMAND}` fetches the locked tiles"
            )
        data = _read_tile(path, tile)  # the bytes verified are the bytes read
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry["sha256"]:
            raise TerrainError(
                f"tile {tile}: {path} has SHA-256 {actual}, provenance.json and the tile lock "
                f"pin {entry['sha256']}; `{DOWNLOAD_COMMAND}` fetches it again"
            )
        _place_tile(mosaic, box, tile, path, data)
        del data
        source_tiles.append({"sha256": entry["sha256"], "tile": tile})
    if not np.isfinite(mosaic).all():  # the tiles cover the box, so this is a bug if it fires
        raise TerrainError(f"the tiles {tiles} leave part of area {area!r} uncovered")

    say(f"resampling {width} × {height} pixels to a {spacing} m grid")
    heights = resample(mosaic, box, spacing, world.height_offset)
    del mosaic
    source = {
        "attribution": alti["attribution"],
        "collection": alti["collection"],
        "dataset": DATASET,
        "edition": alti["edition"],
        "resolution_m": alti["resolution_m"],
        "tiles": source_tiles,
    }
    data, block = _describe(
        area, heights, box, spacing, hashlib.sha256(world_raw).hexdigest(), source
    )
    del heights
    if block["sha256"] != expected:
        raise TerrainError(
            f"area {area!r} at {spacing_key(spacing)} m: the heights built here have SHA-256 "
            f"{block['sha256']}, {TERRAIN_CONFIG_NAME} expects {expected}. Design computed "
            f"the expected value two independent ways, so this machine or this code produces "
            f"other heights than the design's; nothing was written"
        )
    say(f"the heights have the SHA-256 {TERRAIN_CONFIG_NAME} expects, {expected}")
    _write_files(out_dir, data, block)
    say(f"wrote {Path(out_dir) / block['file']} ({block['columns']} × {block['rows']} vertices)")
    return block


def built_terrain_block(
    out_dir: Path | str,
    terrain_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    *,
    lock_path: Path | str = LOCK_PATH,
) -> dict | None:
    """The description of the terrain built in `out_dir`, or None when none is built.

    A built terrain that no longer matches is a TerrainError naming the command: its world
    config, its spacing, a box, columns or rows that are not the world config's area at
    the spacing (`_check_shape`), a `source` that is not exactly the datasets config's
    attribution, collection, edition and resolution (exact key sets), its heights file, a
    heights file whose SHA-256 is not the terrain config's expected value for the spacing,
    or tiles that are not, in order, the area's tiles with the SHA-256s the tile lock pins
    (SPEC §8; M1 R1 T-01, T-03, T-04; M2-06). `world` is the world config the manifest is
    written from, parsed from the bytes whose SHA-256 is `world_sha256`. The lock is read
    only when a terrain is built.
    """
    check_terrain_config(terrain_config)
    area = configured_area(terrain_config)
    settings = terrain_config["areas"][area]
    path = Path(out_dir) / "terrain" / f"{area}.json"
    if not path.exists():
        return None

    def fail(message: str) -> TerrainError:
        return TerrainError(f"{path}: {message}; `{TERRAIN_COMMAND}` rebuilds the terrain")

    try:
        block = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the terrain description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    expected = {"area": area, "file": f"terrain/{area}.f32", "format": FORMAT}
    for key, value in expected.items():
        if block[key] != value:
            raise fail(f"{key} is {block[key]!r}, expected {value!r}")
    if block["world_sha256"] != world_sha256:
        raise fail(
            f"it was built for the world config with SHA-256 {block['world_sha256']}, "
            f"the world config now has {world_sha256}"
        )
    if block["spacing_m"] != settings["spacing_m"]:
        raise fail(
            f"it was built at {block['spacing_m']!r} m, the terrain config asks for "
            f"{settings['spacing_m']!r} m"
        )
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    _check_shape(block, world, area, settings["spacing_m"], fail)
    alti = datasets[DATASET]
    source = block["source"]
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise fail(f"its source must have exactly the keys {sorted(SOURCE_KEYS)}")
    built_tiles = source["tiles"]
    if not isinstance(built_tiles, list) or not all(
        isinstance(entry, dict) and set(entry) == SOURCE_TILE_KEYS for entry in built_tiles
    ):
        raise fail(
            f"its source's tiles must be a list of entries with exactly the keys "
            f"{sorted(SOURCE_TILE_KEYS)}"
        )
    if source["dataset"] != DATASET:
        raise fail(f"it was built from the dataset {source['dataset']!r}, not {DATASET!r}")
    for key in ("attribution", "collection", "edition", "resolution_m"):
        if source[key] != alti[key]:
            raise fail(
                f"it was built from swissALTI3D {key} {source[key]!r}, the datasets "
                f"config pins {alti[key]!r}"
            )
    rows, columns = block["rows"], block["columns"]
    heights = Path(out_dir) / block["file"]
    try:
        size = heights.stat().st_size
    except OSError as exc:
        raise fail(f"its heights file cannot be read: {exc}") from exc
    if size != rows * columns * 4:
        raise fail(
            f"{heights} holds {size} bytes, {rows} × {columns} heights need {rows * columns * 4}"
        )
    actual = _sha256_of(heights)
    if actual != block["sha256"]:
        raise fail(f"{heights} has SHA-256 {actual}, the description pins {block['sha256']}")
    expected = settings["expected_sha256"][spacing_key(settings["spacing_m"])]
    if actual != expected:
        raise fail(
            f"{heights} has SHA-256 {actual}, the terrain config expects {expected} at "
            f"{spacing_key(settings['spacing_m'])} m"
        )
    tiles = area_tiles(world, area)
    locked = _locked_tiles(load_lock(lock_path), alti, tiles)
    built = [entry["tile"] for entry in built_tiles]
    if built != tiles:
        raise fail(f"it was built from the tiles {built}, the area needs {tiles}")
    for entry in built_tiles:
        pinned = locked[entry["tile"]]["sha256"]
        if entry["sha256"] != pinned:
            raise fail(
                f"tile {entry['tile']} was read with SHA-256 {entry['sha256']}, the tile lock "
                f"{lock_path} now pins {pinned}"
            )
    return block


def _check_shape(
    block: dict, world: World, area: str, spacing_m: float, fail: Callable[[str], TerrainError]
) -> None:
    """Refuse a description whose box, columns or rows are not the area's at the spacing.

    `lv95_box` must be the world config's box for the area: exactly the keys e_max, e_min,
    n_max and n_min, each a float equal to the world's. `columns` must be
    (e_max − e_min) / s + 1 and `rows` (n_max − n_min) / s + 1, whole numbers (SPEC §8, the
    grid; brief M2-06). Each refusal names the field and both values; `fail` adds the file
    and the command. The size check that follows compares the heights file with these.
    """
    e_min, e_max, n_min, n_max = world.area(area)
    box = {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min}
    found = block["lv95_box"]
    if not (
        isinstance(found, dict)
        and set(found) == set(box)
        and all(type(found[key]) is float and found[key] == value for key, value in box.items())
    ):
        raise fail(f"lv95_box is {found!r}, the world config's area {area!r} is {box!r}")
    for field, length in (("columns", e_max - e_min), ("rows", n_max - n_min)):
        count, wanted = block[field], length / spacing_m + 1
        if type(count) is not int or count != wanted:
            if not wanted.is_integer():  # no grid fits: the area is not whole cells
                needs = f"{wanted!r}, and the area is not a whole number of {spacing_m:g} m cells"
            elif type(count) is not int:
                needs = f"{int(wanted)}, a whole number"
            else:
                needs = f"{int(wanted)}"
            raise fail(
                f"{field} is {count!r}, the world config's area {area!r} at {spacing_m:g} m "
                f"needs {needs}"
            )


def _is_spacing(value: object) -> bool:
    return type(value) in (int, float) and value in SPACINGS


def _whole(value: float) -> bool:
    return math.isfinite(value) and float(value).is_integer()


def _whole_count(length: float, unit: float) -> int:
    count = length / unit
    if not _whole(count):
        raise TerrainError(f"{length} m is not a whole number of {unit} m")
    return int(count)


def _window_counts(vertices: int, step: int, half: int, pixels: int) -> np.ndarray:
    """How many pixels of each vertex's window lie inside the area, along one axis."""
    centre = np.arange(vertices) * step
    return (np.minimum(centre + half, pixels) - np.maximum(centre - half, 0)).astype(np.float64)


def _provenance_tiles(path: Path, alti: dict, tiles: list[str]) -> dict[str, dict]:
    """provenance.json's entries by tile, once it is shown to match the config (D9)."""

    def fail(message: str) -> TerrainError:
        return TerrainError(f"{path}: {message}; `{DOWNLOAD_COMMAND}` downloads what it asks for")

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
        wanted = DATASET if key == "dataset" else alti[key]
        if provenance.get(key) != wanted:
            raise fail(f"it lists {key} {provenance.get(key)!r}, the config asks for {wanted!r}")
    entries = provenance.get("tiles")
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise fail("its tiles are not a list of objects")
    listed = [entry.get("tile") for entry in entries]
    if listed != tiles:
        raise fail(f"it lists the tiles {listed}, the area needs {tiles}")
    for entry in entries:
        name, sha256 = entry.get("file"), entry.get("sha256")
        if not (isinstance(name, str) and SAFE_NAME.fullmatch(name)):
            raise fail(f"tile {entry['tile']}: file {name!r} is not a plain file name")
        if not isinstance(sha256, str):
            raise fail(f"tile {entry['tile']}: no sha256")
    return {entry["tile"]: entry for entry in entries}


def _locked_tiles(lock: dict, alti: dict, tiles: list[str]) -> dict[str, dict]:
    """The lock's entries for the area's tiles, once it is shown to be for the config (D7)."""

    def fail(message: str) -> TerrainError:
        return TerrainError(f"the tile lock {message}; `{LOCK_COMMAND}` writes the lock")

    locked = lock.get("datasets", {}).get(DATASET) if isinstance(lock, dict) else None
    if not isinstance(locked, dict):
        raise fail(f"has no {DATASET!r} entry")
    for key in ("collection", "edition", "resolution_m"):
        if locked.get(key) != alti[key]:
            raise fail(f"is for {key} {locked.get(key)!r}, the config pins {alti[key]!r}")
    entries = locked.get("tiles")
    missing = [tile for tile in tiles if not isinstance(entries, dict) or tile not in entries]
    if missing:
        raise fail(f"pins no checksum for the tiles {missing}")
    return entries


def _place_tile(mosaic: np.ndarray, box: Box, tile: str, path: Path, raw: bytes) -> None:
    """Check the tile (`raw`, the bytes of `path`) is where its id says; copy in its part."""
    e_km, n_km = (int(v) for v in TILE_ID.fullmatch(tile).groups())
    west, north = e_km * TILE_M, (n_km + 1) * TILE_M

    def fail(message: str) -> TerrainError:
        return TerrainError(f"tile {tile}: {path}: {message}")

    try:
        with MemoryFile(raw) as memory, memory.open() as ds:
            epsg = ds.crs.to_epsg() if ds.crs is not None else None
            if epsg != TILE_EPSG:
                raise fail(f"its CRS is {ds.crs}, expected EPSG:{TILE_EPSG}")
            if (ds.width, ds.height, ds.count) != (TILE_PIXELS, TILE_PIXELS, 1):
                raise fail(
                    f"it is {ds.width} × {ds.height} pixels in {ds.count} bands, expected "
                    f"{TILE_PIXELS} × {TILE_PIXELS} in 1"
                )
            if ds.dtypes[0] != "float32":
                raise fail(f"its pixels are {ds.dtypes[0]}, expected float32")
            t = ds.transform
            if (t.a, t.b, t.c, t.d, t.e, t.f) != (SOURCE_M, 0.0, west, 0.0, -SOURCE_M, north):
                raise fail(
                    f"its top-left corner is ({t.c}, {t.f}) with {t.a} × {-t.e} m pixels, its id "
                    f"says ({west}, {north}) with {SOURCE_M} m pixels"
                )
            nodata = ds.nodata
            data = ds.read(1)
    except RasterioError as exc:
        raise fail(f"cannot read it as a GeoTIFF: {exc}") from exc

    e_min, e_max, n_min, n_max = box
    # the part of the tile inside the area, in tile pixels and in mosaic pixels
    i0 = round((north - min(n_max, north)) / SOURCE_M)
    i1 = round((north - max(n_min, north - TILE_M)) / SOURCE_M)
    j0 = round((max(e_min, west) - west) / SOURCE_M)
    j1 = round((min(e_max, west + TILE_M) - west) / SOURCE_M)
    part = data[i0:i1, j0:j1]
    bad = ~np.isfinite(part)
    if nodata is not None:
        bad |= part == np.float32(nodata)
    if bad.any():
        i, j = (int(v) for v in np.argwhere(bad)[0])
        raise fail(
            f"pixel (row {i0 + i}, column {j0 + j}) at LV95 ({west + (j0 + j) * SOURCE_M}, "
            f"{north - (i0 + i) * SOURCE_M}) is {part[i, j]!r}, not a height (nodata {nodata!r})"
        )
    r0 = round((n_max - (north - i0 * SOURCE_M)) / SOURCE_M)
    c0 = round((west + j0 * SOURCE_M - e_min) / SOURCE_M)
    mosaic[r0 : r0 + part.shape[0], c0 : c0 + part.shape[1]] = part


def _read_tile(path: Path, tile: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TerrainError(
            f"tile {tile}: cannot read {path}: {exc}; `{DOWNLOAD_COMMAND}` fetches it again"
        ) from exc


def _sha256_of(path: Path) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)
