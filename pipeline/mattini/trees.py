"""The trees step: where the LiDAR surface model shows a tree (M3-07; SPEC §8 *The trees*).

From the surface model (swissSURFACE3D), the terrain model (swissALTI3D), the buildings
(swissBUILDINGS3D and swissTLM3D's footprints) and the rock (swissTLM3D's land cover) the
step finds each tree's position, base height, height and crown radius, and writes them per
1 km tile, 20 bytes a tree. The game stands a procedural conifer at each (brief M3-11).

The rule works on the area's 0.5 m pixels, (i, j) from the north-west, centre E = e_min +
0.25 + 0.5 j, N = n_max − 0.25 − 0.5 i, in exact integer arithmetic so that every machine
finds the same trees (Hard Rule 5). `build_tree_chunks` is its entry; its steps, in order:
1. chm = DSM − DTM per pixel, in 64-bit (exact for float32 inputs).
2. Three masks by pixel centres, exact in whole millimetres. F, the footprints: inside or on
   the boundary of the plan projection of a non-degenerate triangle of any building whose
   bounding box meets the area (the buildings step's selection does not matter), or inside a
   TLM_GEBAEUDE_FOOTPRINT polygon of any OBJEKTART but 16 (underground: no roof above
   ground). B: within 2.0 m of a pixel of F, centre to centre (di² + dj² ≤ 16), over the
   area's pixels only. R, the rock: inside a TLM_BODENBEDECKUNG polygon of OBJEKTART 1 to 4.
   Inside is even-odd over the rings of one feature by the half-open crossing rule, OR-ed
   across features: the surfaces step's (brief M3-06).
3. v = chm where chm > 0 and the pixel is not in B, else 0. Each v must be a whole multiple
   of 2⁻¹³ m (true for float32 heights from 1024 to 4096 m), or the pixel's LV95 centre and
   both heights are refused; V = v · 2¹³.
4. S = K ⊛ V, K = outer([1, 4, 6, 4, 1], [1, 4, 6, 4, 1]) (the weights sum to 256), pixels
   outside the area counted 0: integers in units of 2⁻²¹ m.
5. A top: a pixel not on the area's outermost ring, not in B, not in R, with S ≥ 3 m, such that
   within the disc of radius 3 + floor(S / 10 m) pixels (di² + dj² ≤ ρ², inside the area)
   every other pixel has a smaller S, or an equal one and comes after it in raster order.
6. Dropped: a top whose chm is above 40 m (a cliff), below 3 m (a gap in a crown), or on a
   DTM slope of 60° or more (gx² + gy² ≥ 3 from the neighbours' differences).
7. A tree: x and z through the world config's `to_local` in 64-bit, then float32; y the mean
   of the four vertices of the 0.5 m terrain grid around the centre (`terrain.resample`, the
   heights minus `height_offset_m`), in 64-bit, rounded once to float32, whatever the
   terrain config's spacing; height the chm at the top; crown radius clamp(min(d / 2,
   height / 4), 1.0, 6.0) m, d the distance to the nearest other tree kept in the area
   (infinite when there is none), a correctly rounded square root, then float32.
8. Chunks: the 1 km tile of (E, N); within a chunk the tops' raster order; a tile without a
   tree has no chunk.

The files: `trees/<tile>.bin` (x, y, z, height, crown radius, little-endian float32 each),
then `trees/<area>.json`, each through a `.part` rename; after a write, every `*.bin` that
no chunk of this run names and every `*.part` in `trees/` is removed (an export would ship
them). The chunks must be the ones design computed: config/trees.json holds the SHA-256 of
every chunk, and the step compares the set of tiles and every chunk with it before it writes
anything (lesson 38). Those values hold only for the world config and the four lock entries
the area records as `computed_for` (brief M2-07, lesson 41).

The checks run in this order, each before the next reads anything: the area (the terrain
config's, which the trees config must name), the world (the owner's axes, `computed_for`), each
lock entry's fit to the datasets config and the area (a lock that does not fit is refused
naming its lock command), the four entries against `computed_for`, then every dataset's
provenance.json in sorted dataset order (a missing download is refused naming its download
command, before anything is created under the output folder and before any progress line),
then, file by file, the SHA-256 of the bytes that are then read (each tile also gets the
terrain's tile checks; the 2.88 GB TLM zip has its size compared with provenance.json before
it is hashed, is read through its path, and must be unchanged after the read). Every refusal is a
TreesError naming the file, the tile or sheet, or the command that fixes it (Hard Rule 2).

Does NOT prove: that the trees stand where the owner sees trees (the data has residue: a few
false trees on vehicles and train cars in the 2021 surface model, canopy newer than both
building datasets, and the margin stops at the area's edge); the game's reading (M3-11).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import struct
from collections.abc import Callable
from pathlib import Path

import numpy as np
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile

from mattini.buildings import read_sheet
from mattini.download import PROVENANCE, area_sheets, area_tiles
from mattini.lock import entries_sha256, fit_problem, shape_problem
from mattini.surfaces import (
    BIG,
    LIMIT_MM,
    SurfacesError,
    _ceil_div,
    _floor_div,
    _Frame,
    _paint,
    _polygon_spans,
    _row_pairs,
    read_tlm,
)
from mattini.surfaces import (
    _snapped as surfaces_snapped,
)
from mattini.terrain import (
    AREA_NAME,
    OWNER_AXES,
    check_computed_for,
    check_terrain_config,
    configured_area,
    resample,
    world_refusal,
)
from mattini.world import REPO, World, parse_world, read_config_bytes

TREES_CONFIG_PATH = REPO / "config" / "trees.json"
TREES_CONFIG_NAME = "config/trees.json"  # the home of the expected chunks, for messages
SCHEMA = 1
FORMAT = "trees-f32x5-le"
TREES_COMMAND = "python -m mattini trees"
DATASETS = ("swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d")  # sorted
DOWNLOAD_COMMANDS = {
    "swissalti3d": "python -m mattini download terrain",
    "swissbuildings3d": "python -m mattini download buildings",
    "swisssurface3d": "python -m mattini download surface",
    "swisstlm3d": "python -m mattini download tlm",
}
PARAMETERS = {
    "building_margin_m": 2.0,
    "crown_radius": (
        "min(d / 2, height / 4), clamped to 1.0-6.0 m; d to the nearest other tree, "
        "infinite when none"
    ),
    "max_height_m": 40.0,
    "max_slope_deg": 60.0,
    "min_height_m": 3.0,
    "smoothing": "binomial-5x5",
    "window": "3 + floor(h / 10 m) pixels",
}
CONFIG_AREA_KEYS = {"computed_for", "expected_sha256"}
BLOCK_KEYS = {"area", "chunks", "format", "lv95_box", "parameters", "source", "world_sha256"}
CHUNK_KEYS = {"file", "sha256", "tile", "trees"}
BOX_KEYS = {"e_max", "e_min", "n_max", "n_min"}
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
TILE_ID = re.compile(r"([0-9]+)-([0-9]+)")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

SOURCE_M = 0.5  # the surface and terrain models' pixel
TILE_M = 1000
TILE_PIXELS = round(TILE_M / SOURCE_M)
TILE_EPSG = 2056
RECORD = struct.Struct("<5f")  # x, y, z, height, crown radius
FOOTPRINT_LAYER, COVER_LAYER = "TLM_GEBAEUDE_FOOTPRINT", "TLM_BODENBEDECKUNG"
TLM_LAYERS = {FOOTPRINT_LAYER: ("OBJEKTART",), COVER_LAYER: ("OBJEKTART",)}
UNDERGROUND = 16  # TLM_GEBAEUDE_FOOTPRINT: Unterirdisches Gebaeude
ROCK = frozenset({1, 2, 3, 4})
MARGIN_PIXELS_SQUARED = 16  # B: within 2.0 m of F, centre to centre (di² + dj² <= 16)
STEPS_PER_M = 1 << 13  # a canopy height is a whole multiple of 2^-13 m
S_PER_M = 1 << 21  # S is in units of 2^-21 m
MIN_TOP = 3 * S_PER_M  # S >= 3 m
WINDOW_M = 10 * S_PER_M  # the window grows by one pixel per 10 m of S
MIN_HEIGHT_M, MAX_HEIGHT_M, STEEP_SQUARED = 3.0, 40.0, 3.0
KERNEL = ((1, 4), (2, 1))  # [1, 4, 6, 4, 1] as (shift, weight) beside the centre's 6
SNAP_TOLERANCE_M = 1e-6
BAND_ROWS = 256  # rows handled at once by the checks that would need a whole-array temporary
CHUNK_CANDIDATES = 1 << 20  # candidates handled at once by the window test
NEIGHBOUR_ROWS = 16  # first band of the nearest-tree search, in rows (it doubles)

Box = tuple[float, float, float, float]
Progress = Callable[[str], None]


class TreesError(ValueError):
    """The trees cannot be built or no longer match their inputs; the message says why."""


# --------------------------------------------------------------------------------- config


def load_trees_config(path: Path | str = TREES_CONFIG_PATH) -> dict:
    """config/trees.json, validated by `check_trees_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise TreesError(f"{path}: cannot read the trees config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise TreesError(f"{path}: not valid JSON: {exc}") from exc
    check_trees_config(data, path)
    return data


def check_trees_config(data: object, where: Path | str = "the trees config") -> None:
    """Refuse a trees config that is not schema 1 with exactly one well-formed area.

    An area has exactly the keys `computed_for` (what the chunks were computed for,
    `terrain.check_computed_for`) and `expected_sha256`: a non-empty object from tile ids
    (`<e km>-<n km>`) to the SHA-256 of that tile's chunk file, 64 lower-case hex digits,
    one entry per tile that has trees. The TreesError names `where`.
    """

    def fail(message: str) -> TreesError:
        return TreesError(f"{where}: {message}")

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
        if not isinstance(area, dict) or set(area) != CONFIG_AREA_KEYS:
            raise fail(f"area {name!r} must have exactly the keys {sorted(CONFIG_AREA_KEYS)}")
        expected = area["expected_sha256"]
        if not isinstance(expected, dict) or not expected:
            raise fail(f"area {name!r}: expected_sha256 must be a non-empty object")
        for tile, value in expected.items():
            if not (isinstance(tile, str) and TILE_ID.fullmatch(tile)):
                raise fail(f"area {name!r}: {tile!r} is not a tile id like '2623-1095'")
            if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):
                raise fail(
                    f"area {name!r}: expected_sha256[{tile!r}] must be a SHA-256 in 64 "
                    f"lower-case hex characters, found {value!r}"
                )
        check_computed_for(area["computed_for"], name, fail)


def _inputs_sha256(entries: dict) -> str:
    """The SHA-256 of the four lock entries rendered canonically: what `computed_for` records.

    `lock.entries_sha256` over swissalti3d, swissbuildings3d, swisssurface3d and swisstlm3d,
    the one home of the rule (brief M3-13); `entries` is the lock's `datasets` object.
    """
    return entries_sha256({"datasets": entries}, DATASETS)


def _inputs_refusal(computed_for: dict, entries: dict) -> str | None:
    """Why the expected chunks do not hold for the lock's four entries, or None."""
    recorded, current = computed_for["inputs_sha256"], _inputs_sha256(entries)
    if recorded == current:
        return None
    return (
        f"the expected chunks in {TREES_CONFIG_NAME} were computed from the lock entries of "
        f"{', '.join(DATASETS)} with SHA-256 {recorded}; config/datasets.lock.json's entries "
        f"now have {current} (a new edition or an adopted republished file). Adopting new "
        f"inputs is a design change: design recomputes the expected chunks "
        f"(docs/SPEC.md §5, §8)"
    )


# ------------------------------------------------------------------------------ the rule


def build_tree_chunks(
    dsm: np.ndarray,
    dtm: np.ndarray,
    buildings: list[dict],
    footprints: list[dict],
    land_cover: list[dict],
    world: World,
    area: str,
) -> list[dict]:
    """The area's chunks by the rule in the module's docstring, sorted by tile.

    `dsm` and `dtm` are the area's surface and terrain models, 32-bit floats at 0.5 m, rows
    north to south, columns west to east. `buildings` are the buildings step's features
    ({"uuid", "objektart", "triangles"}, each triangle three (E, N, H) points, as
    `buildings.read_sheet` hands them over), `footprints` and `land_cover` the TLM polygons as
    {"uuid", "objektart", "polygons"}: MultiPolygon coordinates, rings closed, points (E, N)
    or (E, N, H). Each chunk is {"tile", "trees", "data"}, `data` the bytes of
    `trees/<tile>.bin`.
    """
    chunks, _ = _rule(dsm, dtm, buildings, footprints, land_cover, world, area)
    return chunks


def _rule(
    dsm, dtm, buildings, footprints, land_cover, world, area, say: Progress | None = None
) -> tuple[list[dict], dict]:
    """The chunks, and the counts the step reports (what each mask and each drop removed)."""
    say = say or (lambda message: None)
    if world.mapping != OWNER_AXES:
        raise TreesError(
            f"{world.path}: the trees support only the axes x = +e, y = +h, z = -n: the base "
            f"height comes from the terrain grid, which has no other"
        )
    if area not in world.areas:
        raise TreesError(f"{world.path}: no area named {area!r}")
    box = world.area(area)
    try:
        frame = _Frame(box, SOURCE_M)
    except SurfacesError as exc:
        raise TreesError(f"area {area!r}: {exc}") from exc
    rows, columns = frame.rows, frame.columns
    for name, raster in (("surface", dsm), ("terrain", dtm)):
        if not isinstance(raster, np.ndarray) or raster.dtype != np.float32 or raster.ndim != 2:
            raise TreesError(f"the {name} model must be a two-dimensional array of 32-bit floats")
        if raster.shape != (rows, columns):
            raise TreesError(
                f"the {name} model is {raster.shape[1]} × {raster.shape[0]} pixels, area "
                f"{area!r} at {SOURCE_M} m needs {columns} × {rows}"
            )
        bad = np.argwhere(~np.isfinite(raster))
        if len(bad):
            i, j = (int(v) for v in bad[0])
            raise TreesError(
                f"the {name} model holds {float(raster[i, j])!r} at row {i}, column {j}, "
                f"not a height"
            )

    stats: dict[str, int] = {}
    say("masking the buildings, the footprints and the rock")
    footprint_spans = [_triangle_spans(frame, _triangles(frame, buildings))]
    for feature in footprints:
        if feature.get("objektart") != UNDERGROUND:
            footprint_spans.append(_polygon_feature_spans(frame, feature, FOOTPRINT_LAYER))
    covered = _mask(frame, footprint_spans)
    del footprint_spans
    margin = _grown(covered)
    rock_spans = [
        _polygon_feature_spans(frame, f, COVER_LAYER)
        for f in land_cover
        if f.get("objektart") in ROCK
    ]
    rock = _mask(frame, rock_spans)
    del rock_spans
    stats.update(footprint_pixels=int(covered.sum()), margin_pixels=int(margin.sum()))
    stats.update(rock_pixels=int(rock.sum()))
    del covered

    say("smoothing the canopy height")
    canopy = _canopy(frame, dsm, dtm, margin)
    reach = 3 + (256 * int(canopy.max())) // WINDOW_M  # the largest window any S can ask for
    padded = np.full((rows + 2 * reach, columns + 2 * reach), -1, dtype=np.int64)
    _smooth(canopy, padded[reach : reach + rows, reach : reach + columns])
    del canopy

    say("finding the tops")
    tops = _tops(padded, reach, rows, columns, margin | rock)
    del padded, margin, rock
    stats["tops"] = len(tops[0])
    kept, height = _kept(dsm, dtm, tops[0], tops[1], stats)
    ti, tj, height = tops[0][kept], tops[1][kept], height[kept]
    stats["trees"] = len(ti)
    say(
        f"{stats['tops']} tops, {stats['trees']} kept ({stats['too_high']} above "
        f"{MAX_HEIGHT_M:g} m, {stats['too_low']} below {MIN_HEIGHT_M:g} m, {stats['too_steep']} "
        f"on slopes of 60° or more; a top can fail more than one)"
    )
    return _chunks(world, box, dtm, ti, tj, height), stats


def _grown(mask: np.ndarray) -> np.ndarray:
    """`mask` grown by the margin: every pixel within di² + dj² <= 16 of a set pixel (over the
    area's pixels only), the pixels themselves included."""
    rows, columns = mask.shape
    grown = np.zeros_like(mask)
    reach = math.isqrt(MARGIN_PIXELS_SQUARED)
    for di in range(-reach, reach + 1):
        for dj in range(-reach, reach + 1):
            if di * di + dj * dj <= MARGIN_PIXELS_SQUARED:
                grown[max(di, 0) : rows + min(di, 0), max(dj, 0) : columns + min(dj, 0)] |= mask[
                    max(-di, 0) : rows + min(-di, 0), max(-dj, 0) : columns + min(-dj, 0)
                ]
    return grown


def _mask(frame: _Frame, spans: list[tuple]) -> np.ndarray:
    """The texels covered by `spans`, a list of (rows, first column, end column) arrays."""
    grid = np.zeros((frame.rows, frame.columns), dtype=np.uint8)
    if any(len(s[0]) for s in spans):
        _paint(grid, frame, 1, *(np.concatenate(part) for part in zip(*spans, strict=True)))
    return grid != 0


def _canopy(frame: _Frame, dsm, dtm, margin: np.ndarray) -> np.ndarray:
    """V = v · 2¹³ (int64): the canopy height where it is above 0 and outside B, else 0.

    chm = DSM − DTM in 64-bit, exact; each kept v must be a whole multiple of 2⁻¹³ m, or the
    pixel's LV95 centre and both heights are refused. Done in bands of rows.
    """
    out = np.zeros((frame.rows, frame.columns), dtype=np.int64)
    for top in range(0, frame.rows, BAND_ROWS):
        band = slice(top, min(top + BAND_ROWS, frame.rows))
        chm = np.subtract(dsm[band], dtm[band], dtype=np.float64)
        scaled = np.where((chm > 0) & ~margin[band], chm * STEPS_PER_M, 0.0)
        whole = scaled == np.floor(scaled)
        if not whole.all():
            i, j = (int(v) for v in np.argwhere(~whole)[0])
            i += top
            east = frame.e0 / 1000 + SOURCE_M / 2 + SOURCE_M * j
            north = frame.n1 / 1000 - SOURCE_M / 2 - SOURCE_M * i
            raise TreesError(
                f"the canopy height at the pixel with LV95 centre ({east!r}, {north!r}) is not "
                f"a whole multiple of 2^-13 m: the surface model gives {float(dsm[i, j])!r} m "
                f"and the terrain model {float(dtm[i, j])!r} m (the exact integer rule holds "
                f"for heights from 1024 to 4096 m)"
            )
        out[band] = scaled.astype(np.int64)
    return out


def _smooth(canopy: np.ndarray, out: np.ndarray) -> None:
    """S = K ⊛ V into `out` (a view of the padded array): the binomial 5 × 5, zeros outside."""
    vertical = np.multiply(canopy, 6)
    for shift, weight in KERNEL:
        vertical[shift:] += weight * canopy[:-shift]
        vertical[:-shift] += weight * canopy[shift:]
    np.multiply(vertical, 6, out=out)
    for shift, weight in KERNEL:
        out[:, shift:] += weight * vertical[:, :-shift]
        out[:, :-shift] += weight * vertical[:, shift:]


def _tops(padded: np.ndarray, reach: int, rows: int, columns: int, excluded: np.ndarray):
    """The tops: (rows, columns, S) of the pixels that are windows' maxima, in raster order.

    `padded` holds S inside a border of `reach` pixels of -1 (outside the area: it
    dominates nothing). Pixel p is dominated by q within its window when S(q) > S(p), or
    S(q) = S(p) and q comes first in raster order (rows from the north, then columns from the
    west). The disc of radius 3 is tested first, for every candidate, since every window
    holds it; the rest of a larger window only for what is left.
    """
    interior = padded[reach : reach + rows, reach : reach + columns]
    candidate = interior >= MIN_TOP
    candidate[0, :] = candidate[-1, :] = False
    candidate[:, 0] = candidate[:, -1] = False
    candidate &= ~excluded
    ci, cj = np.nonzero(candidate)
    del candidate
    width = columns + 2 * reach
    flat = padded.reshape(-1)
    linear = (ci + reach) * width + (cj + reach)
    value = flat[linear]
    alive = np.ones(len(ci), dtype=bool)
    for start in range(0, len(ci), CHUNK_CANDIDATES):
        part = slice(start, start + CHUNK_CANDIDATES)
        alive[part] = ~_dominated(flat, linear[part], value[part], width, _ring(0, 3))
    keep = np.flatnonzero(alive)
    ci, cj, linear, value = ci[keep], cj[keep], linear[keep], value[keep]
    radius = 3 + value // WINDOW_M
    alive = np.ones(len(ci), dtype=bool)
    for rho in np.unique(radius):
        if rho == 3:
            continue
        group = np.flatnonzero(radius == rho)
        alive[group] = ~_dominated(flat, linear[group], value[group], width, _ring(3, int(rho)))
    keep = np.flatnonzero(alive)
    return ci[keep], cj[keep], value[keep]


def _ring(inner: int, outer: int) -> list[tuple[int, int]]:
    """The offsets (di, dj) with inner² < di² + dj² <= outer²: the centre is never in one."""
    return [
        (di, dj)
        for di in range(-outer, outer + 1)
        for dj in range(-outer, outer + 1)
        if inner * inner < di * di + dj * dj <= outer * outer
    ]


def _dominated(flat, linear, value, width: int, offsets) -> np.ndarray:
    """Which of the pixels `linear` (indices into `flat`) some pixel at `offsets` dominates."""
    dominated = np.zeros(len(linear), dtype=bool)
    for di, dj in offsets:
        other = flat[linear + (di * width + dj)]
        first = di < 0 or (di == 0 and dj < 0)  # the other pixel comes first in raster order
        dominated |= (other >= value) if first else (other > value)
    return dominated


def _kept(dsm, dtm, ti, tj, stats: dict) -> tuple[np.ndarray, np.ndarray]:
    """Which tops stay (chm from 3 to 40 m, the DTM's slope below 60°), and every top's chm."""
    height = np.subtract(dsm[ti, tj], dtm[ti, tj], dtype=np.float64)
    gx = np.subtract(dtm[ti, tj + 1], dtm[ti, tj - 1], dtype=np.float64)
    gy = np.subtract(dtm[ti + 1, tj], dtm[ti - 1, tj], dtype=np.float64)
    too_high, too_low = height > MAX_HEIGHT_M, height < MIN_HEIGHT_M
    too_steep = gx * gx + gy * gy >= STEEP_SQUARED
    stats.update(
        too_high=int(too_high.sum()), too_low=int(too_low.sum()), too_steep=int(too_steep.sum())
    )
    return ~(too_high | too_low | too_steep), height


def _chunks(world: World, box: Box, dtm, ti, tj, height) -> list[dict]:
    """The kept trees as chunks (steps 7 and 8): x, y, z, height and crown radius, as bytes."""
    if not len(ti):
        return []
    e_min, _, _, n_max = box
    terrain = resample(dtm, box, SOURCE_M, world.height_offset)  # the 0.5 m terrain grid
    corners = (
        terrain[ti, tj].astype(np.float64)
        + terrain[ti, tj + 1]
        + terrain[ti + 1, tj]
        + terrain[ti + 1, tj + 1]
    )
    east = e_min + SOURCE_M / 2 + SOURCE_M * tj
    north = n_max - SOURCE_M / 2 - SOURCE_M * ti
    local = [world.to_local(e, n, 0.0) for e, n in zip(east.tolist(), north.tolist(), strict=True)]
    nearest = _nearest(ti, tj)
    # d in metres from the squared distance in pixels: sqrt(n / 4) = sqrt(n) / 2 exactly
    distance = np.where(
        nearest >= 0, SOURCE_M * np.sqrt(np.maximum(nearest, 0).astype(float)), np.inf
    )
    radius = np.clip(np.minimum(distance / 2, height / 4), 1.0, 6.0)
    records = np.empty(len(ti), dtype=[(name, "<f4") for name in "xyzhr"])
    records["x"] = [x for x, _, _ in local]
    records["y"] = corners / 4
    records["z"] = [z for _, _, z in local]
    records["h"] = height
    records["r"] = radius
    east_km = np.floor(east / TILE_M).astype(np.int64)
    north_km = np.floor(north / TILE_M).astype(np.int64)
    chunks = []
    for e_km, n_km in sorted({(int(e), int(n)) for e, n in zip(east_km, north_km, strict=True)}):
        which = (east_km == e_km) & (north_km == n_km)
        chosen = records[which]
        chunks.append({"tile": f"{e_km}-{n_km}", "trees": len(chosen), "data": chosen.tobytes()})
    return chunks


def _nearest(ti: np.ndarray, tj: np.ndarray) -> np.ndarray:
    """For each tree (rows ascending), the squared distance in pixels to the nearest other
    tree, or -1 when there is none. Exact: the search takes the trees within a band of rows
    around each tree, and a tree whose nearest is farther than the band is searched again
    with a band twice as wide, until the band covers every row."""
    count = len(ti)
    best = np.full(count, -1, dtype=np.int64)
    if count < 2:
        return best
    unset = np.iinfo(np.int64).max
    span = int(ti[-1] - ti[0])
    todo = np.arange(count)
    reach = NEIGHBOUR_ROWS
    while len(todo):
        low = np.searchsorted(ti, ti[todo] - reach, side="left")
        high = np.searchsorted(ti, ti[todo] + reach, side="right")
        found = np.full(len(todo), unset, dtype=np.int64)
        for index, other in _row_pairs(low, high - 1):
            tree = todo[index]
            squared = (ti[tree] - ti[other]) ** 2 + (tj[tree] - tj[other]) ** 2
            squared[tree == other] = unset
            starts = np.flatnonzero(np.r_[True, index[1:] != index[:-1]])
            items = index[starts]
            found[items] = np.minimum(found[items], np.minimum.reduceat(squared, starts))
        sure = (found <= reach * reach) | (reach >= span)
        best[todo[sure]] = np.where(found[sure] == unset, -1, found[sure])
        todo = todo[~sure]
        reach *= 2
    return best


# ----------------------------------------------------------------------- the masks' inputs


def _snapped(points, label: str, uuid: str) -> np.ndarray:
    """(E, N) of `points` in whole mm, relative-free: an (n, 2) int64 array; a coordinate more
    than 1e-6 m off the 1 mm grid is refused naming `label` and the UUID."""
    try:
        return surfaces_snapped(points, label, uuid)
    except SurfacesError as exc:
        raise TreesError(str(exc)) from exc


def _relative(frame: _Frame, mm: np.ndarray, label: str, uuid: str) -> np.ndarray:
    """Whole-mm points relative to the area's north-west corner; a point too far is refused."""
    relative = mm - np.array([frame.e0, frame.n1], dtype=np.int64)
    if np.abs(relative).max() > LIMIT_MM:
        raise TreesError(f"{label} {uuid}: it reaches more than 537 km from the area")
    return relative


def _triangles(frame: _Frame, buildings: list[dict]) -> np.ndarray:
    """The plan projections (n, 3, 2) of the non-degenerate triangles of every building whose
    bounding box meets the area, in whole mm relative to the area's corner (step 2)."""
    width, height = frame.columns * frame.cell, frame.rows * frame.cell
    kept = []
    for feature in buildings:
        uuid = feature.get("uuid")
        label = f"sheet {feature['sheet']}, building" if feature.get("sheet") else "building"
        triangles = feature.get("triangles")
        try:
            points = np.asarray(triangles, dtype=np.float64)
        except (ValueError, TypeError) as exc:
            raise TreesError(
                f"{label} {uuid}: its triangles are not three (E, N, H) points"
            ) from exc
        if points.ndim != 3 or points.shape[1:] != (3, 3) or not len(points):
            raise TreesError(f"{label} {uuid}: its triangles are not three (E, N, H) points each")
        plan = _relative(frame, _snapped(points.reshape(-1, 3), label, str(uuid)), label, str(uuid))
        plan = plan.reshape(-1, 3, 2)
        x, y = plan[:, :, 0], plan[:, :, 1]
        if x.max() < 0 or x.min() > width or y.max() < -height or y.min() > 0:
            continue  # its bounding box does not meet the area
        area2 = (x[:, 1] - x[:, 0]) * (y[:, 2] - y[:, 0]) - (y[:, 1] - y[:, 0]) * (
            x[:, 2] - x[:, 0]
        )
        kept.append(plan[area2 != 0])
    return np.concatenate(kept) if kept else np.zeros((0, 3, 2), dtype=np.int64)


def _triangle_spans(frame: _Frame, plan: np.ndarray) -> tuple:
    """The texels whose centre is inside or on the boundary of a triangle, as spans.

    For each row the triangle's cut is one interval (it is convex): the hull of the cuts of
    its three edges, each solved exactly in integers: `ceil` of the leftmost crossing and
    `floor` of the rightmost give the first and last centre.
    """
    half, cell, columns = frame.half, frame.cell, frame.columns
    y = plan[:, :, 1]
    first = np.maximum(_ceil_div(-half - y.max(axis=1), cell), 0)
    last = np.minimum(_floor_div(-half - y.min(axis=1), cell), frame.rows - 1)
    parts: list[tuple[np.ndarray, ...]] = []
    for index, row in _row_pairs(first, last):
        yc = -half - row * cell
        corners = plan[index]
        low = np.full(len(row), BIG, dtype=np.int64)
        high = np.full(len(row), -BIG, dtype=np.int64)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            xa, ya, xb, yb = corners[:, a, 0], corners[:, a, 1], corners[:, b, 0], corners[:, b, 1]
            swap = ya > yb
            xl, yl = np.where(swap, xb, xa), np.where(swap, yb, ya)
            xh, yh = np.where(swap, xa, xb), np.where(swap, ya, yb)
            rise = yh - yl
            flat = rise == 0
            safe = np.where(flat, 1, rise)
            numerator = xl * safe + (yc - yl) * (xh - xl) - half * safe
            lo = np.where(
                flat, _ceil_div(np.minimum(xa, xb) - half, cell), _ceil_div(numerator, cell * safe)
            )
            hi = np.where(
                flat,
                _floor_div(np.maximum(xa, xb) - half, cell),
                _floor_div(numerator, cell * safe),
            )
            crosses = (yl <= yc) & (yc <= yh)
            low = np.minimum(low, np.where(crosses, lo, BIG))
            high = np.maximum(high, np.where(crosses, hi, -BIG))
        start, end = np.maximum(low, 0), np.minimum(high + 1, columns)
        reached = start < end
        parts.append((row[reached], start[reached], end[reached]))
    if not parts:
        return (np.empty(0, np.int32),) * 3
    return tuple(np.concatenate(p).astype(np.int32) for p in zip(*parts, strict=True))


def _polygon_feature_spans(frame: _Frame, feature: dict, layer: str) -> tuple:
    """The inside texels of a TLM polygon feature {uuid, objektart, polygons} as spans.

    Coordinates are snapped to whole millimetres (more than 1e-6 m off the grid is refused),
    then handed to the surfaces step's even-odd rule (brief M3-06).
    """
    uuid = feature.get("uuid")
    polygons = feature.get("polygons")
    if not isinstance(uuid, str) or not isinstance(polygons, list):
        raise TreesError(f"{layer}: a feature needs a UUID and polygons: {str(feature)[:120]}")
    coordinates = [
        [_snapped(ring, layer, uuid).tolist() for ring in polygon] for polygon in polygons
    ]
    record = {
        "uuid": uuid,
        "attributes": {},
        "geometry": {"type": "MultiPolygon", "coordinates": coordinates},
    }
    try:
        return _polygon_spans(frame, record, layer, uuid)
    except SurfacesError as exc:
        raise TreesError(str(exc)) from exc


# ------------------------------------------------------------------------------ writing


def write_trees(
    out_dir: Path | str,
    area: str,
    chunks: list[dict],
    box: Box,
    world_sha256: str,
    source: dict,
    *,
    progress: Progress | None = None,
) -> dict:
    """Write `trees/<tile>.bin` for each chunk, then `trees/<area>.json`, each through a
    `.part` rename; return the description, which is what the `.json` holds.

    Afterwards every `*.bin` in `trees/` that no chunk of this run names, and every `*.part`
    there, is removed and counted (an export would ship them).
    """
    say = progress or (lambda message: None)
    if not AREA_NAME.fullmatch(area):
        raise TreesError(f"area name {area!r} must be lower-case letters, digits and '_'")
    entries = []
    for chunk in chunks:
        tile, data = chunk["tile"], chunk["data"]
        if not TILE_ID.fullmatch(tile) or len(data) != RECORD.size * chunk["trees"]:
            raise TreesError(f"chunk {tile!r}: {len(data)} bytes are not {chunk['trees']} trees")
        entries.append(
            {
                "file": f"trees/{tile}.bin",
                "sha256": hashlib.sha256(data).hexdigest(),
                "tile": tile,
                "trees": chunk["trees"],
            }
        )
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    block = {
        "area": area,
        "chunks": entries,
        "format": FORMAT,
        "lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},
        "parameters": dict(PARAMETERS),
        "source": source,
        "world_sha256": world_sha256,
    }
    folder = Path(out_dir) / "trees"
    folder.mkdir(parents=True, exist_ok=True)
    for chunk in chunks:
        _replace(folder / f"{chunk['tile']}.bin", chunk["data"])
    _replace(folder / f"{area}.json", _json_bytes(block))
    named = {Path(entry["file"]).name for entry in entries}
    stale = [p for p in folder.glob("*.bin") if p.name not in named]
    parts = list(folder.glob("*.part"))
    for leftover in [*stale, *parts]:
        leftover.unlink()
    if stale or parts:
        say(f"removed {len(stale)} stale chunk files and {len(parts)} .part files from {folder}")
    return block


# ----------------------------------------------------------------------------- the step


def build_trees(
    world: World,
    datasets: dict,
    lock: dict,
    trees_config: dict,
    terrain_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's trees from the downloaded, locked inputs; return the block.

    The area is the terrain config's one area, which the trees config must name. The checks
    run in the order of the module's docstring; every chunk's SHA-256, and the set of tiles,
    must equal the trees config's `expected_sha256`, compared before anything is written (a
    difference is a TreesError naming the tile and both values, lesson 38). A missing
    download is refused naming its command before anything is created under `out_dir` and
    before any `progress` call.
    """
    say = progress or (lambda message: None)
    area = _area(trees_config, terrain_config)
    settings = trees_config["areas"][area]
    if world.mapping != OWNER_AXES:
        raise TreesError(
            f"{world.path}: the trees support only the axes x = +e, y = +h, z = -n: the base "
            f"height comes from the terrain grid, which has no other"
        )
    if area not in world.areas:
        raise TreesError(f"{world.path}: no area named {area!r} for the terrain config's area")
    box = world.area(area)
    try:
        _Frame(box, SOURCE_M)
    except SurfacesError as exc:
        raise TreesError(f"area {area!r}: {exc}") from exc
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise TreesError(f"{world.path}: the world config changed while the trees were built")
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    problem = world_refusal(TREES_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise TreesError(f"area {area!r}: {problem}")

    configs = _configs(datasets)
    entries = _locked_entries(lock, datasets, world, area)
    problem = _inputs_refusal(settings["computed_for"], entries)
    if problem:
        raise TreesError(f"area {area!r}: {problem}")
    listed = {
        name: _provenance(raw_root, name, configs[name], entries[name], world, area)
        for name in DATASETS
    }

    tiles = area_tiles(world, area)
    say(f"reading the {len(tiles)} terrain and surface tiles")
    terrain = _mosaic(raw_root, "swissalti3d", configs, entries, listed, box, tiles)
    surface = _mosaic(raw_root, "swisssurface3d", configs, entries, listed, box, tiles)
    sheets = area_sheets(world, area)
    say(f"reading the {len(sheets)} building sheets")
    buildings = _buildings(raw_root, configs["swissbuildings3d"], entries, listed, box, sheets)
    say("reading the footprints and the land cover")
    footprints, land_cover = _tlm(
        raw_root, configs["swisstlm3d"], entries["swisstlm3d"], listed, box
    )
    say(
        f"{len(buildings)} buildings meet the area, {len(footprints)} footprints, "
        f"{len(land_cover)} land-cover polygons"
    )

    chunks, stats = _rule(surface, terrain, buildings, footprints, land_cover, world, area, say)
    del surface, terrain, buildings
    say(
        f"masks: {stats['footprint_pixels']} footprint pixels, {stats['margin_pixels']} with the "
        f"margin, {stats['rock_pixels']} rock pixels"
    )
    size = sum(len(chunk["data"]) for chunk in chunks)
    say(f"{stats['trees']} trees in {len(chunks)} chunks, {size} bytes")
    _compare_with_expected(area, chunks, settings["expected_sha256"])
    say(f"the {len(chunks)} chunks have the SHA-256s {TREES_CONFIG_NAME} expects")
    block = write_trees(
        out_dir,
        area,
        chunks,
        box,
        world_sha256,
        _source(configs, entries, world, area),
        progress=say,
    )
    say(f"wrote {Path(out_dir) / 'trees'} ({len(chunks)} chunks and {area}.json)")
    return block


def _area(trees_config: dict, terrain_config: dict) -> str:
    """The area both configs name: the terrain config's one area."""
    check_trees_config(trees_config)
    check_terrain_config(terrain_config)
    area = configured_area(terrain_config)
    if list(trees_config["areas"]) != [area]:
        raise TreesError(
            f"{TREES_CONFIG_NAME} is for the area {next(iter(trees_config['areas']))!r}, "
            f"config/terrain.json names {area!r}: the one area the pipeline serves"
        )
    return area


def _compare_with_expected(area: str, chunks: list[dict], expected: dict[str, str]) -> None:
    """Refuse chunks whose tiles or SHA-256s are not the trees config's (lesson 38)."""
    built = {chunk["tile"]: hashlib.sha256(chunk["data"]).hexdigest() for chunk in chunks}
    for tile in sorted(set(built) | set(expected)):
        if built.get(tile) == expected.get(tile):
            continue
        found = f"SHA-256 {built[tile]}" if tile in built else "no chunk"
        wanted = f"expects {expected[tile]}" if tile in expected else "expects no chunk"
        raise TreesError(
            f"area {area!r}, chunk {tile}: the trees built here give {found}, "
            f"{TREES_CONFIG_NAME} {wanted}. Design computed the expected chunks two "
            f"independent ways, so this machine or this code produces other trees than the "
            f"design's; nothing was written"
        )


def built_trees_block(
    out_dir: Path | str,
    trees_config: dict,
    terrain_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str,
) -> dict | None:
    """The description of the trees built in `out_dir`, or None when none are built.

    The area is the terrain config's. Before anything else the trees config's `computed_for`
    is compared with the world config and the lock's four entries (the lock's fit first,
    naming its lock command): a difference names design's step, since a rebuild would be
    refused for the same reason. Then a built block that no longer matches is a TreesError
    naming `python -m mattini trees`: exact key sets, the area, format, world, box,
    parameters, a source that is exactly what the configs and the lock give, and every chunk:
    its tile among the config's, its file's size (20 bytes a tree) and SHA-256, which must be
    the description's and the config's. `lock` is the lock (a dict) or the path of the lock
    file; it is read only when trees are built.
    """
    area = _area(trees_config, terrain_config)
    settings = trees_config["areas"][area]
    description = Path(out_dir) / "trees" / f"{area}.json"
    if not description.exists():
        return None

    def fail(message: str) -> TreesError:
        return TreesError(f"{description}: {message}; `{TREES_COMMAND}` rebuilds the trees")

    problem = world_refusal(TREES_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise TreesError(f"area {area!r}: {problem}")
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    configs = _configs(datasets)
    entries = _locked_entries(_lock_dict(lock), datasets, world, area)
    problem = _inputs_refusal(settings["computed_for"], entries)
    if problem:
        raise TreesError(f"area {area!r}: {problem}")

    try:
        block = json.loads(description.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the trees description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    e_min, e_max, n_min, n_max = world.area(area)
    box = {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min}
    wanted = {
        "area": area,
        "format": FORMAT,
        "parameters": PARAMETERS,
        "source": _source(configs, entries, world, area),
        "world_sha256": world_sha256,
    }
    for key, value in wanted.items():
        if block[key] != value:
            raise fail(f"{key} is {block[key]!r}, expected {value!r}")
    found = block["lv95_box"]
    if not (
        isinstance(found, dict)
        and set(found) == BOX_KEYS
        and all(type(found[key]) is float and found[key] == value for key, value in box.items())
    ):
        raise fail(f"lv95_box is {found!r}, the world config's area {area!r} is {box!r}")
    expected = settings["expected_sha256"]
    chunks = block["chunks"]
    if not isinstance(chunks, list) or not all(
        isinstance(c, dict) and set(c) == CHUNK_KEYS for c in chunks
    ):
        raise fail(
            f"its chunks must be a list of entries with exactly the keys {sorted(CHUNK_KEYS)}"
        )
    tiles = [c["tile"] for c in chunks]
    if tiles != sorted(expected):
        raise fail(f"it lists the chunks {tiles}, {TREES_CONFIG_NAME} expects {sorted(expected)}")
    for chunk in chunks:
        tile, path = chunk["tile"], Path(out_dir) / chunk["file"]
        if chunk["file"] != f"trees/{tile}.bin" or type(chunk["trees"]) is not int:
            raise fail(f"chunk {tile}: its file is {chunk['file']!r}, its count {chunk['trees']!r}")
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise fail(f"chunk {tile}: its file cannot be read: {exc}") from exc
        if len(data) != RECORD.size * chunk["trees"]:
            raise fail(
                f"chunk {tile}: {path} holds {len(data)} bytes, {chunk['trees']} trees need "
                f"{RECORD.size * chunk['trees']}"
            )
        actual = hashlib.sha256(data).hexdigest()
        if actual != chunk["sha256"]:
            raise fail(
                f"chunk {tile}: {path} has SHA-256 {actual}, the description pins {chunk['sha256']}"
            )
        if actual != expected[tile]:
            raise fail(
                f"chunk {tile}: {path} has SHA-256 {actual}, {TREES_CONFIG_NAME} expects {expected[tile]}"
            )
    return block


# ------------------------------------------------------------- the lock and the downloads


def _configs(datasets: dict) -> dict:
    """The datasets config's four entries, once each has what the step needs."""
    configs = {}
    for name in DATASETS:
        config = datasets.get(name) if isinstance(datasets, dict) else None
        if not isinstance(config, dict):
            raise TreesError(f"config/datasets.json has no {name!r} dataset")
        needed = [
            "attribution",
            "collection",
            "editions" if name == "swisssurface3d" else "edition",
        ]
        for key in needed:
            if not config.get(key):
                raise TreesError(
                    f"config/datasets.json: {name} {key} must be set, found {config.get(key)!r}"
                )
        if name == "swisssurface3d":
            if not (
                isinstance(config["editions"], list)
                and all(isinstance(e, str) and SAFE_NAME.fullmatch(e) for e in config["editions"])
            ):
                raise TreesError(
                    f"config/datasets.json: swisssurface3d editions {config['editions']!r}"
                )
        elif not (isinstance(config["edition"], str) and SAFE_NAME.fullmatch(config["edition"])):
            raise TreesError(f"config/datasets.json: {name} edition {config['edition']!r}")
        if name in ("swissalti3d", "swisssurface3d") and config.get("resolution_m") != SOURCE_M:
            raise TreesError(
                f"the trees are built from {SOURCE_M} m models, config/datasets.json pins "
                f"{name} resolution_m {config.get('resolution_m')!r}"
            )
        configs[name] = config
    return configs


def _locked_entries(lock: object, datasets: dict, world: World, area: str) -> dict:
    """The lock's four entries, each shown to fit the datasets config and the area.

    `lock.fit_problem` asks the question of each dataset in sorted order, and a lock that
    does not fit is refused naming the lock command of the first dataset it does not fit,
    never a KeyError (SPEC §8); then `lock.shape_problem` refuses a lock that is not
    well-formed.
    """
    for name in DATASETS:
        problem = fit_problem(lock, datasets, world, area, name)
        if problem:
            raise TreesError(problem)
    problem = shape_problem(lock)
    if problem:
        raise TreesError(problem)
    return {name: lock["datasets"][name] for name in DATASETS}


def _lock_dict(lock: dict | Path | str) -> dict:
    """The lock as given (a dict), or the JSON file at the path given; the fit follows."""
    if not isinstance(lock, str | os.PathLike):
        return lock
    try:
        return json.loads(Path(lock).read_bytes().decode("utf-8"))
    except OSError as exc:
        raise TreesError(f"{lock}: cannot read the lock: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise TreesError(f"{lock}: the lock is not valid JSON: {exc}") from exc


def _raw_dir(raw_root: Path | str, name: str, config: dict) -> Path:
    """Where `download` leaves a dataset: <raw>/<dataset>/<edition>, or the editions joined."""
    edition = "-".join(config["editions"]) if name == "swisssurface3d" else config["edition"]
    return Path(raw_root) / name / edition


def _source(configs: dict, entries: dict, world: World, area: str) -> dict:
    """The four datasets' blocks of the description, from the configs and the lock."""
    tiles, sheets = area_tiles(world, area), area_sheets(world, area)
    alti, buildings = configs["swissalti3d"], configs["swissbuildings3d"]
    surface, tlm = configs["swisssurface3d"], configs["swisstlm3d"]
    pinned = {name: entries[name] for name in DATASETS}
    return {
        "swissalti3d": {
            "attribution": alti["attribution"],
            "collection": alti["collection"],
            "dataset": "swissalti3d",
            "edition": alti["edition"],
            "resolution_m": alti["resolution_m"],
            "tiles": [
                {"sha256": pinned["swissalti3d"]["tiles"][t]["sha256"], "tile": t} for t in tiles
            ],
        },
        "swissbuildings3d": {
            "attribution": buildings["attribution"],
            "collection": buildings["collection"],
            "dataset": "swissbuildings3d",
            "edition": buildings["edition"],
            "sheets": [
                {"sha256": pinned["swissbuildings3d"]["sheets"][s]["sha256"], "sheet": s}
                for s in sheets
            ],
        },
        "swisssurface3d": {
            "attribution": surface["attribution"],
            "collection": surface["collection"],
            "dataset": "swisssurface3d",
            "editions": list(surface["editions"]),
            "resolution_m": surface["resolution_m"],
            "tiles": [
                {
                    "edition": pinned["swisssurface3d"]["tiles"][t]["edition"],
                    "sha256": pinned["swisssurface3d"]["tiles"][t]["sha256"],
                    "tile": t,
                }
                for t in tiles
            ],
        },
        "swisstlm3d": {
            "attribution": tlm["attribution"],
            "collection": tlm["collection"],
            "dataset": "swisstlm3d",
            "edition": tlm["edition"],
            "file": pinned["swisstlm3d"]["file"],
            "sha256": pinned["swisstlm3d"]["sha256"],
        },
    }


def _provenance(raw_root, name: str, config: dict, entry: dict, world: World, area: str) -> dict:
    """provenance.json of `name`, once it is shown to be the download of the locked files.

    Returns {part: provenance entry} by tile or sheet, or for the TLM its one flat record.
    Every difference from the config or the lock is refused naming the download command.
    """
    path = _raw_dir(raw_root, name, config) / PROVENANCE

    def fail(message: str) -> TreesError:
        return TreesError(
            f"{path}: {message}; `{DOWNLOAD_COMMANDS[name]}` downloads what it asks for"
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
    keys = ["dataset", "collection", "editions" if name == "swisssurface3d" else "edition"]
    if name in ("swissalti3d", "swisssurface3d"):
        keys.append("resolution_m")
    for key in keys:
        wanted = name if key == "dataset" else config[key]
        if provenance.get(key) != wanted:
            raise fail(f"it lists {key} {provenance.get(key)!r}, the config asks for {wanted!r}")
    if name == "swisstlm3d":
        for key in ("file", "sha256"):
            found = provenance.get(key)
            if isinstance(found, str) and key == "sha256":
                found = found.lower()
            if found != entry[key]:
                raise fail(f"it lists {key} {provenance.get(key)!r}, the lock pins {entry[key]!r}")
        size = provenance.get("size_bytes")
        if type(size) is not int or size < 1:
            raise fail(f"its size_bytes {size!r} is not a positive whole number")
        return provenance
    parts_key, id_key = ("sheets", "sheet") if name == "swissbuildings3d" else ("tiles", "tile")
    needed = area_sheets(world, area) if name == "swissbuildings3d" else area_tiles(world, area)
    items = provenance.get(parts_key)
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise fail(f"its {parts_key} are not a list of objects")
    listed = [item.get(id_key) for item in items]
    if listed != needed:
        raise fail(f"it lists the {parts_key} {listed}, the area needs {needed}")
    pinned = entry[parts_key]
    for item in items:
        part = item[id_key]
        file, sha256 = item.get("file"), item.get("sha256")
        if not (isinstance(file, str) and SAFE_NAME.fullmatch(file)):
            raise fail(f"{id_key} {part}: file {file!r} is not a plain file name")
        if not isinstance(sha256, str):
            raise fail(f"{id_key} {part}: no sha256")
        if file != pinned[part]["file"] or sha256.lower() != pinned[part]["sha256"]:
            raise fail(
                f"{id_key} {part}: it lists {file} with SHA-256 {sha256}, the lock pins "
                f"{pinned[part]['file']} with SHA-256 {pinned[part]['sha256']}"
            )
        if name == "swisssurface3d" and item.get("edition") != pinned[part]["edition"]:
            raise fail(
                f"tile {part}: it lists the edition {item.get('edition')!r}, the lock pins "
                f"{pinned[part]['edition']!r}"
            )
    return {item[id_key]: item for item in items}


def _verified_bytes(path: Path, what: str, sha256: str, name: str) -> bytes:
    """The bytes of `path`, whose SHA-256 must be `sha256`; the bytes hashed are the bytes read."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TreesError(
            f"{what}: cannot read {path}: {exc}; `{DOWNLOAD_COMMANDS[name]}` fetches it again"
        ) from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != sha256:
        raise TreesError(
            f"{what}: {path} has SHA-256 {actual}, provenance.json and the lock pin {sha256}; "
            f"`{DOWNLOAD_COMMANDS[name]}` fetches it again"
        )
    return data


def _mosaic(
    raw_root, name: str, configs, entries, listed, box: Box, tiles: list[str]
) -> np.ndarray:
    """The area's 0.5 m mosaic (float32) of the dataset's tiles, each tile checked."""
    folder = _raw_dir(raw_root, name, configs[name])
    e_min, e_max, n_min, n_max = box
    mosaic = np.full(
        (round((n_max - n_min) / SOURCE_M), round((e_max - e_min) / SOURCE_M)),
        np.nan,
        dtype=np.float32,
    )
    for tile in tiles:
        item = listed[name][tile]
        data = _verified_bytes(
            folder / item["file"], f"{name} tile {tile}", item["sha256"].lower(), name
        )
        _place_tile(mosaic, box, tile, folder / item["file"], data, name)
        del data
    if not np.isfinite(mosaic).all():  # the tiles cover the box, so this is a bug if it fires
        raise TreesError(f"the {name} tiles {tiles} leave part of the area uncovered")
    return mosaic


def _place_tile(mosaic: np.ndarray, box: Box, tile: str, path: Path, raw: bytes, name: str) -> None:
    """Check the tile is where its id says (the terrain's tile checks); copy in its part."""
    e_km, n_km = (int(v) for v in TILE_ID.fullmatch(tile).groups())
    west, north = e_km * TILE_M, (n_km + 1) * TILE_M

    def fail(message: str) -> TreesError:
        return TreesError(f"{name} tile {tile}: {path}: {message}")

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


def _buildings(raw_root, config: dict, entries, listed, box: Box, sheets: list[str]) -> list[dict]:
    """The buildings of the area's sheets whose bounding box may meet the area.

    Each sheet is read from the bytes hashed. A building whose bounding box (over its raw
    coordinates, a millimetre beyond) is wholly outside the area is dropped at once: it can
    mask no pixel, and the sheets hold thousands of triangles it would carry in memory. The
    rule's own selection (`_triangles`) is the exact one.
    """
    folder = _raw_dir(raw_root, "swissbuildings3d", config)
    e_min, e_max, n_min, n_max = box
    margin = 0.001
    kept = []
    for sheet in sheets:
        item = listed["swissbuildings3d"][sheet]
        data = _verified_bytes(
            folder / item["file"], f"sheet {sheet}", item["sha256"].lower(), "swissbuildings3d"
        )
        try:
            features = read_sheet(data, sheet)
        except ValueError as exc:  # BuildingsError
            raise TreesError(str(exc)) from exc
        del data
        for feature in features:
            points = np.asarray(feature["triangles"], dtype=np.float64).reshape(-1, 3)
            e, n = points[:, 0], points[:, 1]
            if e.max() < e_min - margin or e.min() > e_max + margin:
                continue
            if n.max() < n_min - margin or n.min() > n_max + margin:
                continue
            kept.append(dict(feature, sheet=sheet))
    return kept


def _tlm(raw_root, config: dict, entry: dict, listed, box: Box) -> tuple[list[dict], list[dict]]:
    """The TLM footprints and land cover that meet the area, as {uuid, objektart, polygons}.

    The zip is checked as the surfaces step checks it (its size against provenance.json
    before it is hashed, its SHA-256, and its (size, mtime_ns, inode) unchanged after the
    read) and read through `surfaces.read_tlm`; the reader's integer millimetres are divided
    by 1000, which the rule snaps back to the same millimetres.
    """
    path = _raw_dir(raw_root, "swisstlm3d", config) / entry["file"]
    command = DOWNLOAD_COMMANDS["swisstlm3d"]

    def signature() -> tuple[int, int, int]:
        try:
            status = path.stat()
        except OSError as exc:
            raise TreesError(f"cannot read {path}: {exc}; `{command}` downloads it") from exc
        return status.st_size, status.st_mtime_ns, status.st_ino

    seen = signature()
    size = listed["swisstlm3d"]["size_bytes"]
    if seen[0] != size:
        raise TreesError(
            f"{path} is {seen[0]} bytes, its provenance.json lists {size}; `{command}` fetches it again"
        )
    try:
        with open(path, "rb") as file:
            actual = hashlib.file_digest(file, "sha256").hexdigest()
    except OSError as exc:
        raise TreesError(f"cannot read {path}: {exc}; `{command}` downloads it again") from exc
    if actual != entry["sha256"]:
        raise TreesError(
            f"{path} has SHA-256 {actual}, provenance.json and the lock pin {entry['sha256']}; "
            f"`{command}` fetches it again"
        )
    try:
        read = read_tlm(path, TLM_LAYERS, box)
    except SurfacesError as exc:
        raise TreesError(str(exc)) from exc
    if signature() != seen:
        raise TreesError(
            f"{path} changed while it was read (size, modification time or inode); "
            f"`{command}` fetches it again"
        )

    def adapted(features: list[dict]) -> list[dict]:
        return [
            {
                "uuid": f["uuid"],
                "objektart": f["attributes"]["OBJEKTART"],
                "polygons": [
                    [[[e / 1000, n / 1000] for e, n in ring] for ring in polygon]
                    for polygon in f["geometry"]["coordinates"]
                ],
            }
            for f in features
        ]

    return adapted(read[FOOTPRINT_LAYER]), adapted(read[COVER_LAYER])


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)
