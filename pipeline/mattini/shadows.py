"""The capture shadows step: where the photo lay in shadow when it was flown (v0.5.0-01; SPEC §13
rows 41 and 47).

From the swissSURFACE3D 0.5 m tiles that `download surface` fetches (for the trees) the step
computes where SWISSIMAGE 2023 lay in shadow at the flight's sun and writes a 0.5 m mask,
`shadows/<area>.png` (0 lit, 255 shadow), its `.png.import` and its description
`shadows/<area>.json`. The game lifts the photo inside the mask (a later batch), so that the
moving sun's shadows read and the photo's do not darken a second time.

The rule (the pinned tests write it out cell by cell):
1. The cells are 1 m, aligned to the area's north-west corner, rows north to south, columns west
   to east. A cell's height is the largest of its 2 x 2 pixels, in float64 (`cell_heights`).
2. Cast shadow (`cast_shadow`): with A the grid azimuth and e the elevation, for k = 1 ... K the
   offset towards the sun is dx = k sin A (east), dy = -(k cos A) (south) cells, computed once
   per k; the surface there is the bilinear value of the four cells around it, and the cell is
   in cast shadow if that is above (h + k tan e) + threshold for any k. A point whose needed
   cells are not all inside the grid casts nothing. K = ceil((max - min) / tan e).
3. Own shadow (`own_shadow`): the normal from central differences (one-sided on the edges)
   faces away from the sun.
4. The mask (`capture_mask`): each 1 m cell in cast or own shadow becomes its 2 x 2 cells of
   0.5 m; then the inset keeps a shadow cell only when its four neighbours inside the grid are
   in shadow too (half a metre off every edge).

The sun and the threshold are read from config/shadows.json (design's data), never held here.
The mask's SHA-256 and the PNG's are compared with the config's expected values before
anything is written (lesson 38); the checks of the inputs run in the order of `build_shadows`.
The tiles, their provenance and their checks are the trees step's (`trees._provenance`,
`trees._mosaic`), read-only.

Does NOT prove: that the mask lies on the photo's shadows (the surface model is from 2021/22,
the photo from 2023, and the flight spans 11.6 degrees of azimuth while the mask uses the
mean); that another zlib writes the same PNG bytes (the step refuses one that does not).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import zlib
from collections.abc import Callable
from pathlib import Path

import numpy as np

from mattini.download import area_tiles
from mattini.lock import entry_sha256, fit_problem, shape_problem
from mattini.surfaces import (
    MIB,
    PNG_SIGNATURE,
    SHA256_HEX,
    SurfacesError,
    _chunk,
    _Frame,
    read_png_l8,
)
from mattini.terrain import (
    AREA_NAME,
    OWNER_AXES,
    check_computed_for,
    configured_area,
    inputs_refusal,
    world_refusal,
)
from mattini.trees import SAFE_NAME, TreesError, _mosaic, _provenance, _raw_dir
from mattini.world import REPO, World, parse_world, read_config_bytes

SHADOWS_CONFIG_PATH = REPO / "config" / "shadows.json"
SHADOWS_CONFIG_NAME = "config/shadows.json"  # the home of the expected values, for messages
SCHEMA = 1
DATASET = "swisssurface3d"
CELL_M = 0.5  # the mask
MARCH_CELL_M = 1  # the march
SHADOWS_COMMAND = "python -m mattini shadows"
DOWNLOAD_COMMAND = "python -m mattini download surface"
FORMAT = "png-l8"
KEEP = b'[remap]\n\nimporter="keep"\n'  # shadows/<area>.png.import (brain.md H24)
CONFIG_KEYS = {"schema", "cell_m", "march_cell_m", "sun", "threshold_m", "areas"}
SUN_KEYS = {"azimuth_grid_deg", "elevation_deg", "note"}
AREA_CONFIG_KEYS = {"computed_for", "expected_pixels_sha256", "expected_png_sha256"}
BLOCK_KEYS = {
    "area",
    "cell_m",
    "columns",
    "file",
    "format",
    "lv95_box",
    "pixels_sha256",
    "rows",
    "sha256",
    "source",
    "sun",
    "world_sha256",
}
SOURCE_KEYS = {"attribution", "collection", "dataset", "editions", "entry_sha256"}
Box = tuple[float, float, float, float]  # e_min, e_max, n_min, n_max
Progress = Callable[[str], None]


class ShadowsError(ValueError):
    """The shadows cannot be read or built, or no longer match their inputs; says why."""


# --------------------------------------------------------------------------------- config


def load_shadows_config(path: Path | str = SHADOWS_CONFIG_PATH) -> dict:
    """config/shadows.json, validated by `check_shadows_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise ShadowsError(f"{path}: cannot read the shadows config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise ShadowsError(f"{path}: not valid JSON: {exc}") from exc
    check_shadows_config(data, path)
    return data


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def check_shadows_config(data: object, where: Path | str = "the shadows config") -> None:
    """Refuse a shadows config that is not exactly schema 1, the mask's cell (0.5 m), the
    march's cell (1 m), a sun {azimuth_grid_deg in [0, 360), elevation_deg in (0, 90), note},
    a threshold of 0 m or more and one well-formed area: `computed_for`
    (`terrain.check_computed_for`), `expected_pixels_sha256` and `expected_png_sha256`, each a
    SHA-256 in 64 lower-case hex digits. The ShadowsError names `where`."""

    def fail(message: str) -> ShadowsError:
        return ShadowsError(f"{where}: {message}")

    if not isinstance(data, dict) or set(data) != CONFIG_KEYS:
        raise fail(f"the top level must have exactly the keys {sorted(CONFIG_KEYS)}")
    if type(data["schema"]) is not int or data["schema"] != SCHEMA:
        raise fail(f"schema must be {SCHEMA}, found {data['schema']!r}")
    for key, wanted in (("cell_m", CELL_M), ("march_cell_m", MARCH_CELL_M)):
        if not (_number(data[key]) and data[key] == wanted):
            raise fail(f"{key} must be {wanted}, found {data[key]!r}")
    if not (_number(data["threshold_m"]) and data["threshold_m"] >= 0):
        raise fail(
            f"threshold_m must be a number of metres, 0 or more, found {data['threshold_m']!r}"
        )
    sun = data["sun"]
    if not isinstance(sun, dict) or set(sun) != SUN_KEYS:
        raise fail(f"sun must have exactly the keys {sorted(SUN_KEYS)}")
    azimuth, elevation = sun["azimuth_grid_deg"], sun["elevation_deg"]
    if not (_number(azimuth) and 0 <= azimuth < 360):
        raise fail(f"sun azimuth_grid_deg must be a number in [0, 360), found {azimuth!r}")
    if not (_number(elevation) and 0 < elevation < 90):
        raise fail(f"sun elevation_deg must be a number in (0, 90), found {elevation!r}")
    if not (isinstance(sun["note"], str) and sun["note"]):
        raise fail(f"sun note must be a non-empty string, found {sun['note']!r}")
    areas = data["areas"]
    if not isinstance(areas, dict) or len(areas) != 1:
        found = sorted(areas) if isinstance(areas, dict) else areas
        raise fail(f"areas must hold exactly one area, found {found!r}")
    for name, area in areas.items():
        if not AREA_NAME.fullmatch(name):
            raise fail(f"area name {name!r} must be lower-case letters, digits and '_'")
        if not isinstance(area, dict) or set(area) != AREA_CONFIG_KEYS:
            raise fail(f"area {name!r} must have exactly the keys {sorted(AREA_CONFIG_KEYS)}")
        for field in ("expected_pixels_sha256", "expected_png_sha256"):
            value = area[field]
            if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):
                raise fail(
                    f"area {name!r}: {field} must be a SHA-256 in 64 lower-case hex "
                    f"characters, found {value!r}"
                )
        check_computed_for(area["computed_for"], name, fail)


# ----------------------------------------------------------------------------- the rule


def cell_heights(surface: np.ndarray) -> np.ndarray:
    """The 1 m cells' heights (float64) from the 0.5 m surface: the largest of each 2 x 2."""
    surface = np.asarray(surface)
    if surface.ndim != 2 or surface.shape[0] % 2 or surface.shape[1] % 2 or surface.size == 0:
        raise ShadowsError(f"a surface of {surface.shape} pixels does not make 1 m cells")
    rows, columns = surface.shape[0] // 2, surface.shape[1] // 2
    cells = surface.reshape(rows, 2, columns, 2).max(axis=(1, 3))
    return cells.astype(np.float64)


def march_steps(heights: np.ndarray, elevation_deg: float) -> int:
    """K = ceil((max - min) / tan e) over the cells, in float64."""
    span = float(np.max(heights)) - float(np.min(heights))
    return math.ceil(span / math.tan(math.radians(elevation_deg)))


def cast_shadow(
    heights: np.ndarray, azimuth_grid_deg: float, elevation_deg: float, threshold_m: float
) -> np.ndarray:
    """Which cells (bool, the grid's shape) lie in cast shadow: the module docstring's march.

    The offsets are computed once per k, so a cell's value does not depend on the others.
    Cells whose sample point has a needed cell outside the grid cast nothing there.
    """
    h = np.asarray(heights, dtype=np.float64)
    if h.ndim != 2 or h.size == 0:
        raise ShadowsError("the heights must be a non-empty two-dimensional array")
    rows, columns = h.shape
    azimuth = math.radians(azimuth_grid_deg)
    sin_a, cos_a = math.sin(azimuth), math.cos(azimuth)
    tan_e = math.tan(math.radians(elevation_deg))
    shadow = np.zeros(h.shape, dtype=bool)
    for k in range(1, march_steps(h, elevation_deg) + 1):
        dx = k * sin_a
        dy = -(k * cos_a)
        i0, j0 = math.floor(dx), math.floor(dy)
        fx, fy = dx - i0, dy - j0
        wide, tall = fx > 0, fy > 0
        r_lo, r_hi = max(0, -j0), min(rows - 1, rows - 1 - j0 - tall)
        c_lo, c_hi = max(0, -i0), min(columns - 1, columns - 1 - i0 - wide)
        if r_lo > r_hi or c_lo > c_hi:
            continue

        rs, cs = r_lo + j0, c_lo + i0  # the first source cell of the window
        nr, nc = r_hi - r_lo + 1, c_hi - c_lo + 1

        def at(dj: int, di: int, h=h, rs=rs, cs=cs, nr=nr, nc=nc) -> np.ndarray:
            return h[rs + dj : rs + dj + nr, cs + di : cs + di + nc]

        north = at(0, 0) * (1.0 - fx) + at(0, 1) * fx if wide else at(0, 0)
        if tall:
            south = at(1, 0) * (1.0 - fx) + at(1, 1) * fx if wide else at(1, 0)
            sample = north * (1.0 - fy) + south * fy
        else:
            sample = north
        own = h[r_lo : r_hi + 1, c_lo : c_hi + 1]
        shadow[r_lo : r_hi + 1, c_lo : c_hi + 1] |= sample > (own + k * tan_e) + threshold_m
    return shadow


def own_shadow(heights: np.ndarray, azimuth_grid_deg: float, elevation_deg: float) -> np.ndarray:
    """Which cells (bool) face away from the sun: ((-gx) ux - gy uy) + uz <= 0.

    gx = dh/dE and gy = dh/dN by central differences over the two neighbours divided by 2,
    one-sided (not halved) on the grid's edges; (ux, uy, uz) the sun's unit vector.
    """
    h = np.asarray(heights, dtype=np.float64)
    if h.ndim != 2 or min(h.shape) < 2:
        raise ShadowsError(
            "the heights must be a two-dimensional array of two cells or more a side"
        )
    gx = np.empty_like(h)
    gx[:, 1:-1] = (h[:, 2:] - h[:, :-2]) / 2
    gx[:, 0] = h[:, 1] - h[:, 0]
    gx[:, -1] = h[:, -1] - h[:, -2]
    gy = np.empty_like(h)  # rows grow southwards: dh/dN is the row above minus the row below
    gy[1:-1] = (h[:-2] - h[2:]) / 2
    gy[0] = h[0] - h[1]
    gy[-1] = h[-2] - h[-1]
    a, e = math.radians(azimuth_grid_deg), math.radians(elevation_deg)
    ux, uy, uz = math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)
    return ((-gx) * ux - gy * uy) + uz <= 0


def inset(shadow: np.ndarray) -> np.ndarray:
    """0 / 255 (uint8, the same shape): 255 where a cell is in shadow and so are its four
    neighbours inside the grid (a neighbour outside the grid does not count)."""
    shadow = np.asarray(shadow, dtype=bool)
    padded = np.pad(shadow, 1, constant_values=True)
    kept = shadow & padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
    return np.where(kept, np.uint8(255), np.uint8(0))


def capture_mask(
    surface: np.ndarray, azimuth_grid_deg: float, elevation_deg: float, threshold_m: float
) -> np.ndarray:
    """The 0.5 m mask (uint8 0 / 255, the surface's own shape) of the 0.5 m `surface`."""
    heights = cell_heights(surface)
    shadow = cast_shadow(heights, azimuth_grid_deg, elevation_deg, threshold_m)
    shadow |= own_shadow(heights, azimuth_grid_deg, elevation_deg)
    del heights
    fine = np.repeat(np.repeat(shadow, 2, axis=0), 2, axis=1)
    return inset(fine)


# ----------------------------------------------------------------------------- the PNG


def png_mask(pixels: np.ndarray) -> bytes:
    """`pixels` (uint8, rows x columns, values 0 and 255 only) as the surfaces' 8-bit grey PNG:
    no interlace, filter 0 on every row, one zlib stream at level 9 in IDAT chunks of 1 MiB."""
    if not isinstance(pixels, np.ndarray) or pixels.dtype != np.uint8 or pixels.ndim != 2:
        raise ShadowsError("the mask must be a two-dimensional array of uint8")
    rows, columns = pixels.shape
    if not (0 < rows < MIB and 0 < columns < MIB and rows * (columns + 1) < 1 << 31):
        raise ShadowsError(f"a mask of {columns} x {rows} cells does not make a PNG")
    if not np.isin(pixels, (0, 255)).all():
        raise ShadowsError("the mask holds 0 and 255 only")
    scanlines = np.zeros((rows, columns + 1), dtype=np.uint8)  # filter byte 0 on every row
    scanlines[:, 1:] = pixels
    stream = zlib.compress(scanlines, 9)
    del scanlines
    header = struct.pack(">IIBBBBB", columns, rows, 8, 0, 0, 0, 0)
    chunks = [PNG_SIGNATURE, _chunk(b"IHDR", header)]
    chunks += [_chunk(b"IDAT", stream[at : at + MIB]) for at in range(0, len(stream), MIB)]
    chunks.append(_chunk(b"IEND", b""))
    return b"".join(chunks)


# ------------------------------------------------------------------------------ writing


def _frame(box: Box) -> _Frame:
    try:
        return _Frame(box, CELL_M)
    except SurfacesError as exc:
        raise ShadowsError(str(exc)) from exc


def write_shadows(
    out_dir: Path | str,
    area: str,
    mask: np.ndarray,
    box: Box,
    world_sha256: str,
    source: dict,
    sun: dict,
    *,
    png: bytes | None = None,
) -> dict:
    """Write `shadows/<area>.png.import`, `.png` and `.json` (each through a `.part` rename),
    in that order, and return the description, which is what the `.json` holds.

    A `*.part` an earlier run left in `shadows/` is removed once all three are written. `png`
    is `png_mask(mask)` when the caller has encoded it already (the step does, to compare its
    SHA-256 before anything is written): it is written as given, not checked against the mask.
    """
    if not AREA_NAME.fullmatch(area):
        raise ShadowsError(f"area name {area!r} must be lower-case letters, digits and '_'")
    frame = _frame(box)
    if mask.shape != (frame.rows, frame.columns):
        raise ShadowsError(
            f"the mask is {mask.shape[1]} x {mask.shape[0]}, the box at {CELL_M} m needs "
            f"{frame.columns} x {frame.rows}"
        )
    if png is None:
        png = png_mask(mask)
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    block = {
        "area": area,
        "cell_m": float(CELL_M),
        "columns": frame.columns,
        "file": f"shadows/{area}.png",
        "format": FORMAT,
        "lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},
        "pixels_sha256": hashlib.sha256(np.ascontiguousarray(mask)).hexdigest(),
        "rows": frame.rows,
        "sha256": hashlib.sha256(png).hexdigest(),
        "source": source,
        "sun": sun,
        "world_sha256": world_sha256,
    }
    folder = Path(out_dir) / "shadows"
    folder.mkdir(parents=True, exist_ok=True)
    _replace(folder / f"{area}.png.import", KEEP)
    _replace(folder / f"{area}.png", png)
    _replace(folder / f"{area}.json", _json_bytes(block))
    for leftover in folder.glob("*.part"):
        leftover.unlink()
    return block


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)


# ----------------------------------------------------------------------------- the step


def _surface_config(datasets: dict) -> dict:
    """The datasets config's swisssurface3d entry, once it has what the step needs."""
    config = datasets.get(DATASET) if isinstance(datasets, dict) else None
    if not isinstance(config, dict):
        raise ShadowsError(f"config/datasets.json has no {DATASET!r} dataset")
    for key in ("attribution", "collection"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ShadowsError(f"config/datasets.json: {DATASET} {key} must be a non-empty string")
    editions = config.get("editions")
    if not (
        isinstance(editions, list)
        and editions
        and all(isinstance(e, str) and SAFE_NAME.fullmatch(e) for e in editions)
    ):
        raise ShadowsError(f"config/datasets.json: {DATASET} editions {editions!r}")
    if config.get("resolution_m") != 0.5:
        raise ShadowsError(
            f"the shadows are built from 0.5 m models, config/datasets.json pins "
            f"{DATASET} resolution_m {config.get('resolution_m')!r}"
        )
    return config


def _locked_entry(lock: object, datasets: dict, world: World, area: str) -> dict:
    """The lock's swisssurface3d entry, once it fits the datasets config and the area and the
    lock is well-formed; a lock that does not is refused naming `lock surface`."""
    problem = fit_problem(lock, datasets, world, area, DATASET) or shape_problem(lock)
    if problem:
        raise ShadowsError(problem)
    return lock["datasets"][DATASET]


def _lock_dict(lock: dict | Path | str) -> dict:
    """The lock as given (a dict), or the JSON file at the path given; the fit follows."""
    if not isinstance(lock, str | os.PathLike):
        return lock
    try:
        return json.loads(Path(lock).read_bytes().decode("utf-8"))
    except OSError as exc:
        raise ShadowsError(f"{lock}: cannot read the lock: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise ShadowsError(f"{lock}: the lock is not valid JSON: {exc}") from exc


def _source(config: dict, entry: dict) -> dict:
    return {
        "attribution": config["attribution"],
        "collection": config["collection"],
        "dataset": DATASET,
        "editions": list(config["editions"]),
        "entry_sha256": entry_sha256(entry),
    }


def build_shadows(
    world: World,
    datasets: dict,
    lock: dict,
    shadows_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's capture shadows from the downloaded, locked tiles; return
    the description.

    The checks run in this order, each before the next reads anything: the config; the world
    (the owner's axes only, the area, `computed_for.world_sha256`); the lock's fit; the
    `computed_for.inputs_sha256` against the lock's entry; the provenance and the presence of
    every tile (a missing one is refused naming `python -m mattini download surface`, before
    anything is created under `out_dir` and before any `progress` call); each tile's SHA-256
    against the lock's before it is read, then the tile checks. The mask's SHA-256 must equal
    the config's `expected_pixels_sha256`, and the PNG's, encoded once, its
    `expected_png_sha256`: each is compared before anything is written, and a difference is a
    ShadowsError naming both values (lesson 38), the PNG's naming the machine's zlib.
    """
    say = progress or (lambda message: None)
    check_shadows_config(shadows_config)
    if world.mapping != OWNER_AXES:
        raise ShadowsError(
            f"{world.path}: the shadows support only the axes x = +e, y = +h, z = -n"
        )
    area = configured_area(shadows_config)
    settings = shadows_config["areas"][area]
    sun = shadows_config["sun"]
    if area not in world.areas:
        raise ShadowsError(f"{world.path}: no area named {area!r} for the shadows config's area")
    box = world.area(area)
    _frame(box)
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise ShadowsError(f"{world.path}: the world config changed while the shadows were built")
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    problem = world_refusal(SHADOWS_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise ShadowsError(f"area {area!r}: {problem}")

    config = _surface_config(datasets)
    entry = _locked_entry(lock, datasets, world, area)
    problem = inputs_refusal(SHADOWS_CONFIG_NAME, settings["computed_for"], DATASET, entry)
    if problem:
        raise ShadowsError(f"area {area!r}: {problem}")

    tiles = area_tiles(world, area)
    folder = _raw_dir(raw_root, DATASET, config)
    try:
        listed = {DATASET: _provenance(raw_root, DATASET, config, entry, world, area)}
    except TreesError as exc:
        raise ShadowsError(str(exc)) from exc
    for tile in tiles:
        path = folder / listed[DATASET][tile]["file"]
        if not path.is_file():
            raise ShadowsError(
                f"{DATASET} tile {tile}: {path} is missing; `{DOWNLOAD_COMMAND}` fetches it"
            )

    say(f"reading the {len(tiles)} surface tiles")
    try:
        surface = _mosaic(
            raw_root, DATASET, {DATASET: config}, {DATASET: entry}, listed, box, tiles
        )
    except TreesError as exc:
        raise ShadowsError(str(exc)) from exc
    say(f"marching a {surface.shape[1] // 2} x {surface.shape[0] // 2} grid of 1 m cells")
    mask = capture_mask(
        surface, sun["azimuth_grid_deg"], sun["elevation_deg"], shadows_config["threshold_m"]
    )
    del surface
    pixels_sha256 = hashlib.sha256(np.ascontiguousarray(mask)).hexdigest()
    expected = settings["expected_pixels_sha256"]
    if pixels_sha256 != expected:
        raise ShadowsError(
            f"area {area!r}: the mask built here has SHA-256 {pixels_sha256}, "
            f"{SHADOWS_CONFIG_NAME} expects {expected} (expected_pixels_sha256). Design computed "
            f"the expected value two independent ways, so this machine or this code produces "
            f"another mask than the design's; nothing was written"
        )
    say(f"the mask has the SHA-256 {SHADOWS_CONFIG_NAME} expects, {expected}")
    png = png_mask(mask)
    png_sha256 = hashlib.sha256(png).hexdigest()
    expected_png = settings["expected_png_sha256"]
    if png_sha256 != expected_png:
        raise ShadowsError(
            f"area {area!r}: the mask is design's, but the PNG built here has SHA-256 "
            f"{png_sha256} and {SHADOWS_CONFIG_NAME} expects {expected_png} "
            f"(expected_png_sha256). The PNG's bytes depend on the zlib build, so this "
            f"machine's (zlib {zlib.ZLIB_RUNTIME_VERSION}) or this code writes other bytes than "
            f"design's; that value pins the encoder, not the mask. A Python whose zlib writes "
            f"design's bytes (zlib 1.3.x was measured to) builds the same file, uv's managed "
            f"CPython for one: `uv python install 3.13 --managed-python`, then run with "
            f"UV_PYTHON_PREFERENCE=only-managed; nothing was written"
        )
    say(f"the PNG has the SHA-256 {SHADOWS_CONFIG_NAME} expects, {expected_png}")
    block = write_shadows(
        out_dir, area, mask, box, world_sha256, _source(config, entry), dict(sun), png=png
    )
    say(f"wrote {Path(out_dir) / block['file']} ({block['columns']} x {block['rows']} cells)")
    return block


def built_shadows_block(
    out_dir: Path | str,
    shadows_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str,
) -> dict | None:
    """The description of the shadows built in `out_dir`, or None when none are built.

    Built shadows that no longer match are a ShadowsError naming `python -m mattini shadows`:
    a world or a lock entry that is not the one the expected values were computed for (naming
    design's step, as the build does), a description whose keys, area, file, format, cell,
    box, columns, rows, source or sun are not what the configs and the lock give, a missing or
    wrong `.png.import`, a PNG whose SHA-256 is not the description's, one that is not the
    pinned format or whose pixels do not have the description's `pixels_sha256` and the
    config's expected value, and last a PNG whose bytes are not the config's
    `expected_png_sha256`. `lock` is the lock (a dict) or the path of the lock file; it is
    read only when shadows are built.
    """
    check_shadows_config(shadows_config)
    area = configured_area(shadows_config)
    settings = shadows_config["areas"][area]
    description = Path(out_dir) / "shadows" / f"{area}.json"
    if not description.exists():
        return None

    def fail(message: str) -> ShadowsError:
        return ShadowsError(f"{description}: {message}; `{SHADOWS_COMMAND}` rebuilds the shadows")

    problem = world_refusal(SHADOWS_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise ShadowsError(f"area {area!r}: {problem}")
    config = _surface_config(datasets)
    entry = _locked_entry(_lock_dict(lock), datasets, world, area)
    problem = inputs_refusal(SHADOWS_CONFIG_NAME, settings["computed_for"], DATASET, entry)
    if problem:
        raise ShadowsError(f"area {area!r}: {problem}")

    try:
        block = json.loads(description.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the shadows description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    e_min, e_max, n_min, n_max = world.area(area)
    frame = _frame((e_min, e_max, n_min, n_max))
    box = {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min}
    wanted = {
        "area": area,
        "cell_m": float(CELL_M),
        "columns": frame.columns,
        "file": f"shadows/{area}.png",
        "format": FORMAT,
        "rows": frame.rows,
        "source": _source(config, entry),
        "sun": shadows_config["sun"],
        "world_sha256": world_sha256,
    }
    for key, value in wanted.items():
        if block[key] != value or type(block[key]) is not type(value):
            raise fail(f"{key} is {block[key]!r}, expected {value!r}")
    found = block["lv95_box"]
    if not (
        isinstance(found, dict)
        and set(found) == set(box)
        and all(type(found[key]) is float and found[key] == value for key, value in box.items())
    ):
        raise fail(f"lv95_box is {found!r}, the world config's area {area!r} is {box!r}")

    png_path = Path(out_dir) / block["file"]
    keep_path = png_path.with_name(png_path.name + ".import")
    try:
        keep = keep_path.read_bytes()
        data = png_path.read_bytes()
    except OSError as exc:
        raise fail(f"cannot read its files: {exc}") from exc
    if keep != KEEP:
        raise fail(f"{keep_path} must hold exactly {KEEP!r} (brain.md H24), found {keep!r}")
    png_sha256 = hashlib.sha256(data).hexdigest()
    if png_sha256 != block["sha256"]:
        raise fail(f"{png_path} has SHA-256 {png_sha256}, the description pins {block['sha256']}")
    try:
        pixels = read_png_l8(data)
    except SurfacesError as exc:
        raise fail(f"{png_path}: {exc}") from exc
    if pixels.shape != (frame.rows, frame.columns):
        raise fail(f"{png_path} is {pixels.shape[1]} x {pixels.shape[0]} cells")
    if not np.isin(pixels, (0, 255)).all():
        raise fail(f"{png_path} holds values besides 0 and 255")
    actual = hashlib.sha256(pixels).hexdigest()
    expected = settings["expected_pixels_sha256"]
    if actual != block["pixels_sha256"]:
        raise fail(
            f"the mask in {png_path} has SHA-256 {actual}, the description's pixels_sha256 "
            f"is {block['pixels_sha256']}"
        )
    if actual != expected:
        raise fail(
            f"the mask in {png_path} has SHA-256 {actual}, {SHADOWS_CONFIG_NAME} expects "
            f"{expected} (expected_pixels_sha256)"
        )
    expected_png = settings["expected_png_sha256"]
    if png_sha256 != expected_png:
        raise fail(
            f"{png_path} has SHA-256 {png_sha256}, {SHADOWS_CONFIG_NAME} expects {expected_png} "
            f"(expected_png_sha256): its mask is design's, its bytes are not (they depend on the "
            f"zlib build of the machine that wrote it; this machine's is zlib "
            f"{zlib.ZLIB_RUNTIME_VERSION})"
        )
    return block
