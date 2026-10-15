"""The surfaces step: roads, paths, water and rock from swissTLM3D as a class grid (M3-06).

A class for every cell of the area's grid (`cell_m` from config/surfaces.json: 0.2, 0.5 or
1 m), rows north to south, columns west to east: texel (r, c) is the point E = e_min +
cell/2 + c·cell, N = n_max − cell/2 − r·cell. The classes are 0 none, 1 rock, 2 water, 3
path and 4 road, the highest one wins, and the game draws them sharp on the ground.

The rule (SPEC §8 *The surfaces*), on exact integer arithmetic throughout so that every
machine gets the same classes (Hard Rule 5):
- road and path: TLM_STRASSE with BELAGSART 100 (Hart) → road, 200 (Natur) → path, whose
  OBJEKTART has a width, on a texel whose centre lies within half that width of a segment;
  not drawn where the line is roofed or below ground (KUNSTBAUTE `NOT_DRAWN`);
- water: TLM_BODENBEDECKUNG OBJEKTART 5 and 10 (centre inside) and TLM_FLIESSGEWAESSER
  OBJEKTART 4 with VERLAUF 100 or 500 within 1.0 m of the line: an ASSUMED stream width of
  2 m, TLM gives none, a placeholder (`STREAM_WIDTH_MM`);
- rock: TLM_BODENBEDECKUNG OBJEKTART 1 to 4, the centre inside.
Coordinates are whole millimetres, centres are whole millimetres, a distance test is an
integer comparison (a centre exactly half a width from a line is on it), and "inside" is
even-odd over the rings of one feature by the half-open crossing rule (an edge counts when
(y1 > yc) ≠ (y2 > yc) and xc lies left of its crossing), OR-ed across features. A line is
tested per segment: the segment's band, and a disc at each end, exactly.

`read_tlm` reads the features of the national swissTLM3D FileGDB from its zip, never
unzipped and never read into memory whole (it is 2.88 GB). It is public so that the trees
step (brief M3-07) can read the same file through it. fiona is imported inside it only, so
that importing this module, and any command that reads no FileGDB, does not load it.

The classes must be the ones design computed: config/surfaces.json holds, per cell size, the
SHA-256 of the class bytes (`expected_pixels_sha256`), and the step compares its classes
with the value for its cell before it writes anything (lesson 38). The expected values hold
only for the world config and the TLM file design computed them for, which the area
records as `computed_for` (the SHA-256 of config/world.json's bytes and of the lock's
`swisstlm3d` entry, `lock.entry_sha256`); each difference is refused naming design's step,
since no command of the owner's can make the classes match (brief M2-07, lesson 41).

The checks run in this order, each before the next reads anything: the world, the lock's
fit to the datasets config, the lock's entry against `computed_for`, provenance.json (the
file, collection and edition, the lock's SHA-256), the file's size against provenance.json,
its SHA-256 against the lock's, then the read, after which the file's (size, mtime_ns,
inode) must be what they were. A missing download is refused before anything is created
under the output folder. Every refusal is a SurfacesError naming the file or the command
that fixes it (Hard Rule 2).

The PNG is written without Pillow, by the standard library: 8-bit grey, no interlace, filter
0 on every row, one zlib stream at level 9 in IDAT chunks of at most 1 MiB, values 0 to 4. Its
content is pinned (`pixels_sha256`); its bytes depend on the zlib build, so they are checked
for integrity only (`sha256`). `surfaces/<area>.png.import` says `importer="keep"` (brain.md
H24: Godot would import the PNG as a texture, and an export would ship the texture instead
of the PNG). The files are written in the order `.png.import`, `.png`, `.json`, each through
a `.part` rename. Only the owner's axes (x = +e, y = +h, z = −n) are supported: another
mapping would place the rows and columns wrongly (Hard Rule 4).

Does NOT prove: that the classes sit on the photo's roads (the grid is the TLM's, which
the photo does not have to agree with to a texel); the game's reading (brief M3-10).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import struct
import zipfile
import zlib
from collections.abc import Callable
from pathlib import Path

import numpy as np

from mattini.download import PROVENANCE
from mattini.lock import fit_problem, shape_problem
from mattini.terrain import (
    AREA_NAME,
    OWNER_AXES,
    check_computed_for,
    configured_area,
    inputs_refusal,
    world_refusal,
)
from mattini.world import REPO, World, parse_world, read_config_bytes

SURFACES_CONFIG_PATH = REPO / "config" / "surfaces.json"
SURFACES_CONFIG_NAME = "config/surfaces.json"  # the home of the expected classes, for messages
SCHEMA = 1
CELLS = (0.2, 0.5, 1.0)
CELL_KEYS = ("0.2", "0.5", "1")  # CELLS as the config writes them: format(c, "g")
AREA_CONFIG_KEYS = {"cell_m", "computed_for", "expected_pixels_sha256"}
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
DATASET = "swisstlm3d"
SURFACES_COMMAND = "python -m mattini surfaces"
DOWNLOAD_COMMAND = "python -m mattini download tlm"
LOCK_COMMAND = "python -m mattini lock tlm"
FORMAT = "png-l8"
KEEP = b'[remap]\n\nimporter="keep"\n'  # surfaces/<area>.png.import (brain.md H24)
CLASSES = {"0": "none", "1": "rock", "2": "water", "3": "path", "4": "road"}
NONE, ROCK, WATER, PATH, ROAD = 0, 1, 2, 3, 4
BLOCK_KEYS = {
    "area",
    "cell_m",
    "classes",
    "columns",
    "file",
    "format",
    "lv95_box",
    "pixels_sha256",
    "rows",
    "sha256",
    "source",
    "world_sha256",
}

# What the reader hands over per layer: the integer attributes besides the UUID.
STRASSE, BODENBEDECKUNG, FLIESSGEWAESSER = (
    "TLM_STRASSE",
    "TLM_BODENBEDECKUNG",
    "TLM_FLIESSGEWAESSER",
)
LAYERS = {
    BODENBEDECKUNG: ("OBJEKTART",),
    FLIESSGEWAESSER: ("OBJEKTART", "VERLAUF"),
    STRASSE: ("BELAGSART", "KUNSTBAUTE", "OBJEKTART"),
}
MARGIN_M = 10  # a feature is read when it meets the area grown by this much
PREFILTER_M = 1  # GDAL's rectangle filter gets the box grown by this much and only pre-filters

# TLM_STRASSE: BELAGSART gives the class, OBJEKTART the width (mm), KUNSTBAUTE what is not drawn.
BELAGSART_ROAD, BELAGSART_PATH = 100, 200  # Hart, Natur
WIDTH_MM = {
    8: 10000,
    9: 6000,
    10: 4000,
    11: 3000,
    15: 2000,
    16: 1000,
    17: 1000,
    18: 2000,
    20: 8000,
}
# Bruecke mit Galerie, Gedeckte Bruecke, Galerie, Tunnel, Unterfuehrung, Unterfuehrung mit
# Treppe, in/auf Gebaeude: roofed or below ground, so not on the ground the photo shows.
NOT_DRAWN = frozenset({300, 400, 700, 1000, 1100, 1200, 1400})
WATER_AREA = frozenset({5, 10})  # TLM_BODENBEDECKUNG: Fliessgewaesser, Stehende Gewaesser
ROCK_AREA = frozenset({1, 2, 3, 4})  # Fels, Fels locker, Felsbloecke, Felsbloecke locker
STREAM_OBJEKTART = 4
STREAM_VERLAUF = frozenset({100, 500})  # above ground, waterfall
STREAM_WIDTH_MM = 2000  # ASSUMED: TLM gives no width. A labelled placeholder, not data.

SNAP_TOLERANCE_M = 1e-6  # a coordinate this far or more off the 1 mm grid is refused
LIMIT_MM = 1 << 29  # relative to the box; keeps every product below in 64-bit (about 537 km)
PAIRS = 1 << 20  # (segment, row) pairs handled at once
BAND_CELLS = 1 << 22  # texels painted at once
MIB = 1 << 20
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
BIG = 1 << 60  # an interval end beyond every texel

Box = tuple[float, float, float, float]  # e_min, e_max, n_min, n_max
Progress = Callable[[str], None]


class SurfacesError(ValueError):
    """The surfaces cannot be read or built, or no longer match their inputs; says why."""


# --------------------------------------------------------------------------------- config


def load_surfaces_config(path: Path | str = SURFACES_CONFIG_PATH) -> dict:
    """config/surfaces.json, validated by `check_surfaces_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise SurfacesError(f"{path}: cannot read the surfaces config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise SurfacesError(f"{path}: not valid JSON: {exc}") from exc
    check_surfaces_config(data, path)
    return data


def check_surfaces_config(data: object, where: Path | str = "the surfaces config") -> None:
    """Refuse a surfaces config that is not schema 1 with exactly one well-formed area.

    An area has exactly the keys `cell_m` (0.2, 0.5 or 1), `computed_for` (what the values
    were computed for, `terrain.check_computed_for`) and `expected_pixels_sha256`: an object
    from cell sizes as the config writes them ("0.2", "0.5", "1") to the SHA-256 of the
    class bytes at that cell, 64 lower-case hex digits, holding the configured cell. The
    SurfacesError names `where`.
    """

    def fail(message: str) -> SurfacesError:
        return SurfacesError(f"{where}: {message}")

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
        if type(area["cell_m"]) not in (int, float) or area["cell_m"] not in CELLS:
            raise fail(
                f"area {name!r}: cell_m must be one of {list(CELLS)}, found {area['cell_m']!r}"
            )
        expected = area["expected_pixels_sha256"]
        if not isinstance(expected, dict):
            raise fail(
                f"area {name!r}: expected_pixels_sha256 must be an object, found {expected!r}"
            )
        unknown = [key for key in expected if key not in CELL_KEYS]
        if unknown:
            raise fail(
                f"area {name!r}: expected_pixels_sha256 holds only the cells {list(CELL_KEYS)}, "
                f"found {unknown!r}"
            )
        for key, value in expected.items():
            if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):
                raise fail(
                    f"area {name!r}: expected_pixels_sha256[{key!r}] must be a SHA-256 in 64 "
                    f"lower-case hex characters, found {value!r}"
                )
        if cell_key(area["cell_m"]) not in expected:
            raise fail(
                f"area {name!r}: expected_pixels_sha256 holds no value for the configured "
                f"cell {cell_key(area['cell_m'])!r}"
            )
        check_computed_for(area["computed_for"], name, fail)


def cell_key(cell_m: float) -> str:
    """A cell size as the config writes it, the key of `expected_pixels_sha256`."""
    return format(cell_m, "g")


# ---------------------------------------------------------------------------- the grid


class _Frame:
    """The grid's geometry in whole millimetres, relative to its north-west corner.

    A point (E, N) in mm becomes X = E − e0 and Y = N − n1 (negative to the south), so that
    texel (r, c) has its centre at X = half + c·cell and Y = −half − r·cell.
    """

    def __init__(self, box: Box, cell_m: float):
        e_min, e_max, n_min, n_max = (
            _mm(value, name)
            for value, name in zip(box, ("e_min", "e_max", "n_min", "n_max"), strict=True)
        )
        cell = _mm(cell_m, "the cell")
        if cell <= 0 or cell % 2:
            raise SurfacesError(f"the cell {cell_m!r} m must be an even number of millimetres")
        width, height = e_max - e_min, n_max - n_min
        if width <= 0 or height <= 0 or width % cell or height % cell:
            raise SurfacesError(f"the box {tuple(box)!r} is not a whole number of {cell_m} m cells")
        self.e0, self.n1, self.cell, self.half = e_min, n_max, cell, cell // 2
        self.columns, self.rows = width // cell, height // cell
        self.box_mm = (e_min, e_max, n_min, n_max)


def _mm(value: float, what: str) -> int:
    """`value` metres as whole millimetres (half to even); more than 1e-6 m off is refused."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise SurfacesError(f"{what} {value!r} is not a finite number of metres")
    mm = round(value * 1000)
    if abs(value - mm / 1000) > SNAP_TOLERANCE_M:
        raise SurfacesError(f"{what} {value!r} m is not on the 1 mm grid")
    return mm


def class_grid(features: dict, box: Box, cell_m: float) -> np.ndarray:
    """The classes (uint8, rows × columns) of the area `box` at `cell_m` from `features`.

    `features` is what `read_tlm` hands over, per layer of `LAYERS` (all three): plain dicts
    {"uuid", "attributes", "geometry": {"type", "coordinates"}} in whole millimetres. The
    rule is in the module's docstring. A feature of another shape is a SurfacesError naming
    the layer and the UUID.
    """
    frame = _Frame(box, cell_m)
    if not isinstance(features, dict) or set(features) != set(LAYERS):
        raise SurfacesError(f"the features must be a dict of exactly the layers {sorted(LAYERS)}")
    lines: dict[int, list] = {WATER: [], PATH: [], ROAD: []}
    spans: dict[int, list] = {ROCK: [], WATER: [], PATH: [], ROAD: []}
    for layer in sorted(LAYERS):
        for feature in features[layer]:
            uuid, attributes = _identity(feature, layer)
            if layer == STRASSE:
                code, radius = _street(attributes)
                if code is not None:
                    lines[code].append(_segments(frame, feature, layer, uuid, radius))
            elif layer == FLIESSGEWAESSER:
                if attributes["OBJEKTART"] == STREAM_OBJEKTART and (
                    attributes["VERLAUF"] in STREAM_VERLAUF
                ):
                    lines[WATER].append(
                        _segments(frame, feature, layer, uuid, STREAM_WIDTH_MM // 2)
                    )
            else:
                kind = attributes["OBJEKTART"]
                code = ROCK if kind in ROCK_AREA else WATER if kind in WATER_AREA else None
                if code is not None:
                    spans[code].append(_polygon_spans(frame, feature, layer, uuid))
    for code, parts in lines.items():
        if parts:
            segments = [np.concatenate([part[i] for part in parts]) for i in range(5)]
            spans[code].append(_stadium_spans(frame, *segments))
    grid = np.zeros((frame.rows, frame.columns), dtype=np.uint8)
    for code in (ROCK, WATER, PATH, ROAD):
        if spans[code]:
            _paint(grid, frame, code, *(np.concatenate(p) for p in zip(*spans[code], strict=True)))
    return grid


def _identity(feature: object, layer: str) -> tuple[str, dict]:
    """The UUID and the integer attributes of a feature of `layer`, or a SurfacesError."""
    if not isinstance(feature, dict) or not isinstance(feature.get("uuid"), str):
        raise SurfacesError(f"{layer}: a feature has no UUID: {feature!r}"[:200])
    uuid, attributes = feature["uuid"], feature.get("attributes")
    if not isinstance(attributes, dict) or set(attributes) != set(LAYERS[layer]):
        raise SurfacesError(f"{layer} {uuid}: its attributes must be exactly {LAYERS[layer]}")
    for name, value in attributes.items():
        if type(value) is not int:
            raise SurfacesError(f"{layer} {uuid}: {name} {value!r} is not an integer")
    return uuid, attributes


def _street(attributes: dict) -> tuple[int | None, int]:
    """(class, radius in mm) of a TLM_STRASSE feature, or (None, 0) when it is not drawn."""
    belag, width = attributes["BELAGSART"], WIDTH_MM.get(attributes["OBJEKTART"])
    code = ROAD if belag == BELAGSART_ROAD else PATH if belag == BELAGSART_PATH else None
    if code is None or width is None or attributes["KUNSTBAUTE"] in NOT_DRAWN:
        return None, 0
    return code, width // 2


def _points(frame: _Frame, coordinates: object, layer: str, uuid: str) -> np.ndarray:
    """A list of (E, N) in whole mm as an (n, 2) int64 array relative to the box's corner."""
    try:
        array = np.asarray(coordinates)
    except (ValueError, TypeError, OverflowError) as exc:
        raise SurfacesError(f"{layer} {uuid}: its coordinates are not a list of points") from exc
    if array.ndim != 2 or array.shape[1] != 2 or array.dtype.kind not in "iu" or not array.size:
        raise SurfacesError(f"{layer} {uuid}: its coordinates must be whole-mm (E, N) points")
    array = array.astype(np.int64) - np.array([frame.e0, frame.n1], dtype=np.int64)
    if np.abs(array).max() > LIMIT_MM:
        raise SurfacesError(f"{layer} {uuid}: it reaches more than 537 km from the area")
    return array


def _geometry(feature: dict, layer: str, uuid: str, kind: str) -> list:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != kind:
        raise SurfacesError(f"{layer} {uuid}: its geometry must be a {kind}")
    if not isinstance(geometry.get("coordinates"), list):
        raise SurfacesError(f"{layer} {uuid}: its geometry has no coordinates")
    return geometry["coordinates"]


def _segments(frame: _Frame, feature: dict, layer: str, uuid: str, radius: int) -> list:
    """The segments of a MultiLineString as int64 arrays (ax, ay, bx, by) and radii (mm).

    The parts are kept apart (never joined), a repeated vertex is a segment of length 0.
    """
    ends: list[list[np.ndarray]] = [[], [], [], []]
    for part in _geometry(feature, layer, uuid, "MultiLineString"):
        points = _points(frame, part, layer, uuid)
        if len(points) < 2:
            raise SurfacesError(f"{layer} {uuid}: a line with fewer than two points")
        for index, values in enumerate(
            (points[:-1, 0], points[:-1, 1], points[1:, 0], points[1:, 1])
        ):
            ends[index].append(values)
    joined = [np.concatenate(values) for values in ends]
    return [*joined, np.full(len(joined[0]), radius, dtype=np.int64)]


def _polygon_spans(frame: _Frame, feature: dict, layer: str, uuid: str):
    """The inside texels of a MultiPolygon as (rows, first column, end column) spans.

    Even-odd over all the rings of the feature by the half-open crossing rule: an edge with
    its lower end (in N) at or below the centre's N and its upper end above it counts when
    the centre lies strictly left of the crossing; an edge whose crossing is left of the
    area covers no column, one right of it covers every column. The crossings of a row,
    sorted, pair up into the inside spans.
    """
    edges: list[tuple[np.ndarray, np.ndarray]] = []
    for polygon in _geometry(feature, layer, uuid, "MultiPolygon"):
        for ring in polygon:
            points = _points(frame, ring, layer, uuid)
            if len(points) < 4 or not (points[0] == points[-1]).all():
                raise SurfacesError(f"{layer} {uuid}: a ring that is not closed")
            edges.append((points[:-1], points[1:]))
    if not edges:
        raise SurfacesError(f"{layer} {uuid}: a polygon without rings")
    start = np.concatenate([a for a, _ in edges])
    end = np.concatenate([b for _, b in edges])
    swap = start[:, 1] > end[:, 1]
    low, high = np.where(swap[:, None], end, start), np.where(swap[:, None], start, end)
    keep = low[:, 1] < high[:, 1]
    x1, y1, x2, y2 = low[keep, 0], low[keep, 1], high[keep, 0], high[keep, 1]
    dx, dy = x2 - x1, y2 - y1
    half, cell, columns, rows = frame.half, frame.cell, frame.columns, frame.rows
    first = np.maximum(_floor_div(-half - y2, cell) + 1, 0)  # the rows with y1 <= yc < y2
    last = np.minimum(_floor_div(-half - y1, cell), rows - 1)
    row_parts, k_parts = [], []
    for edge, row in _row_pairs(first, last):
        yc = -half - row * cell
        crossing = x1[edge] * dy[edge] + (yc - y1[edge]) * dx[edge] - half * dy[edge]
        k = _ceil_div(crossing, cell * dy[edge])  # columns left of the crossing: 0..k-1
        row_parts.append(row)
        k_parts.append(np.clip(k, 0, columns))
    if not row_parts:
        return (np.empty(0, np.int32), np.empty(0, np.int32), np.empty(0, np.int32))
    row, k = np.concatenate(row_parts), np.concatenate(k_parts)
    order = np.lexsort((k, row))
    row, k = row[order], k[order]
    if len(row) % 2 or (row[0::2] != row[1::2]).any():
        raise SurfacesError(f"{layer} {uuid}: its rings cross a row an odd number of times")
    inside = k[0::2] < k[1::2]
    return (
        row[0::2][inside].astype(np.int32),
        k[0::2][inside].astype(np.int32),
        k[1::2][inside].astype(np.int32),
    )


def _stadium_spans(
    frame: _Frame, ax: np.ndarray, ay: np.ndarray, bx: np.ndarray, by: np.ndarray, rr: np.ndarray
):
    """The texels within `rr` mm of segments A–B (distance ≤ rr, ties included), as spans.

    The stadium is convex, so its cut by a texel row is one interval; the hull of the cuts of
    its three pieces, the band (the points whose foot on the line lies on the segment and
    whose distance to the line is at most rr) and the discs at A and B, is that interval.
    Each piece's cut is solved exactly: `|cross| <= isqrt(rr² · len²)` is the integer form
    of `cross² <= rr² · len²`, a disc's chord is `isqrt(rr² − dy²)` wide.
    """
    half, cell, columns = frame.half, frame.cell, frame.columns
    dx, dy = bx - ax, by - ay
    len2 = dx * dx + dy * dy
    limit = np.fromiter(
        (math.isqrt(r * r * n) for r, n in zip(rr.tolist(), len2.tolist(), strict=True)),
        dtype=np.int64,
        count=len(rr),
    )
    first = np.maximum(_ceil_div(-half - (np.maximum(ay, by) + rr), cell), 0)
    last = np.minimum(_floor_div(-half - (np.minimum(ay, by) - rr), cell), frame.rows - 1)
    row_parts, start_parts, end_parts = [], [], []
    for s, row in _row_pairs(first, last):
        yc = -half - row * cell
        pax, pay, pbx, pby, prr = ax[s], ay[s], bx[s], by[s], rr[s]
        pdx, pdy, plen2, plimit = dx[s], dy[s], len2[s], limit[s]
        low, high = [], []
        for cx, cy in ((pax, pay), (pbx, pby)):  # the discs at A and B
            h = prr * prr - (yc - cy) ** 2
            reach = _isqrt(np.where(h >= 0, h, 0))
            low.append(np.where(h >= 0, cx - reach, BIG))
            high.append(np.where(h >= 0, cx + reach, -BIG))
        uy = yc - pay  # the band: ux = x − ax within the cross-product and the foot's limits
        ok = plen2 > 0
        cross_low, cross_high = _solve(pdy, uy * pdx - plimit, uy * pdx + plimit)
        ok &= np.where(pdy != 0, True, np.abs(uy * pdx) <= plimit)
        foot_low, foot_high = _solve(pdx, -uy * pdy, plen2 - uy * pdy)
        ok &= np.where(pdx != 0, True, (uy * pdy >= 0) & (uy * pdy <= plen2))
        band_low = pax + np.maximum(
            np.where(pdy != 0, cross_low, -BIG), np.where(pdx != 0, foot_low, -BIG)
        )
        band_high = pax + np.minimum(
            np.where(pdy != 0, cross_high, BIG), np.where(pdx != 0, foot_high, BIG)
        )
        ok &= band_low <= band_high
        low.append(np.where(ok, band_low, BIG))
        high.append(np.where(ok, band_high, -BIG))
        x_low, x_high = np.minimum.reduce(low), np.maximum.reduce(high)
        reached = x_low <= x_high
        start = np.maximum(_ceil_div(x_low - half, cell), 0)  # texels with centre x in [lo, hi]
        end = np.minimum(_floor_div(x_high - half, cell) + 1, columns)
        reached &= start < end
        row_parts.append(row[reached].astype(np.int32))
        start_parts.append(start[reached].astype(np.int32))
        end_parts.append(end[reached].astype(np.int32))
    if not row_parts:
        return (np.empty(0, np.int32),) * 3
    return np.concatenate(row_parts), np.concatenate(start_parts), np.concatenate(end_parts)


def _row_pairs(first: np.ndarray, last: np.ndarray):
    """Yield (index, row) arrays covering every row first[i]..last[i] of every item i.

    Items are handled in windows of about `PAIRS` pairs, so that a long road or a big
    polygon does not need arrays of its whole length at once.
    """
    counts = np.maximum(last - first + 1, 0)
    total = np.cumsum(counts)
    i = 0
    while i < len(counts):
        base = total[i - 1] if i else 0
        j = max(int(np.searchsorted(total, base + PAIRS, side="right")), i + 1)
        window = counts[i:j]
        pairs = int(window.sum())
        if pairs:
            index = np.repeat(np.arange(i, j), window)
            offset = np.arange(pairs) - np.repeat(np.cumsum(window) - window, window)
            yield index, first[index] + offset
        i = j


def _paint(grid, frame, code, rows, starts, ends) -> None:
    """Set `code` where it is higher than the class there, on the spans [start, end) of rows."""
    if not len(rows):
        return
    order = np.argsort(rows, kind="stable")
    rows, starts, ends = rows[order], starts[order], ends[order]
    width = frame.columns + 1
    band = max(1, BAND_CELLS // width)
    for top in range(0, frame.rows, band):
        bottom = min(top + band, frame.rows)
        lo, hi = np.searchsorted(rows, [top, bottom])
        if lo == hi:
            continue
        base = (rows[lo:hi].astype(np.int64) - top) * width
        size = (bottom - top) * width
        change = np.bincount(base + starts[lo:hi], minlength=size)
        change -= np.bincount(base + ends[lo:hi], minlength=size)
        covered = np.cumsum(change.reshape(-1, width), axis=1)[:, : frame.columns] > 0
        block = grid[top:bottom]
        np.maximum(block, np.uint8(code), out=block, where=covered)


def _solve(p: np.ndarray, low: np.ndarray, high: np.ndarray):
    """The integers u with low <= u·p <= high, as (smallest, largest); garbage where p is 0."""
    positive = p > 0
    divisor = np.where(p == 0, 1, np.abs(p))
    return (
        _ceil_div(np.where(positive, low, -high), divisor),
        _floor_div(np.where(positive, high, -low), divisor),
    )


def _floor_div(a, b):
    return a // b


def _ceil_div(a, b):
    return -((-a) // b)


def _isqrt(h: np.ndarray) -> np.ndarray:
    """floor(sqrt(h)) for non-negative int64, exactly, from a table of squares (no floats)."""
    if not h.size:
        return h.copy()
    squares = np.arange(math.isqrt(int(h.max())) + 2, dtype=np.int64) ** 2
    return np.searchsorted(squares, h, side="right") - 1


# ------------------------------------------------------------------------------- the PNG


def png_l8(pixels: np.ndarray) -> bytes:
    """`pixels` (uint8, rows × columns, values 0 to 4) as the pinned 8-bit grey PNG."""
    if not isinstance(pixels, np.ndarray) or pixels.dtype != np.uint8 or pixels.ndim != 2:
        raise SurfacesError("the classes must be a two-dimensional array of uint8")
    rows, columns = pixels.shape
    if not (0 < rows < MIB and 0 < columns < MIB and rows * (columns + 1) < 1 << 31):
        raise SurfacesError(f"{columns} × {rows} classes do not make a PNG")
    if pixels.max() > ROAD:
        raise SurfacesError(f"the classes are 0 to {ROAD}, found {int(pixels.max())}")
    scanlines = np.zeros((rows, columns + 1), dtype=np.uint8)  # filter byte 0 on every row
    scanlines[:, 1:] = pixels
    stream = zlib.compress(scanlines, 9)
    del scanlines
    header = struct.pack(">IIBBBBB", columns, rows, 8, 0, 0, 0, 0)
    chunks = [PNG_SIGNATURE, _chunk(b"IHDR", header)]
    chunks += [_chunk(b"IDAT", stream[at : at + MIB]) for at in range(0, len(stream), MIB)]
    chunks.append(_chunk(b"IEND", b""))
    return b"".join(chunks)


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def read_png_l8(data: bytes) -> np.ndarray:
    """The classes of a PNG written as `png_l8` writes it; anything else is a SurfacesError.

    Only the standard library decodes it. A valid PNG of another shape (another bit depth,
    interlaced, a filter other than 0 on a row, a chunk besides IHDR, IDAT and IEND, a bad
    CRC, data after IEND) is refused: the pinned format is what the game reads.
    """

    def fail(message: str) -> SurfacesError:
        return SurfacesError(f"not the pinned 8-bit grey PNG: {message}")

    if data[:8] != PNG_SIGNATURE:
        raise fail("no PNG signature")
    at, chunks = 8, []
    while True:
        if at + 12 > len(data):
            raise fail("cut short before IEND")
        (length,) = struct.unpack(">I", data[at : at + 4])
        kind, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + length]
        if at + 12 + length > len(data):
            raise fail(f"a {kind.decode('ascii', 'replace')} chunk is cut short")
        (crc,) = struct.unpack(">I", data[at + 8 + length : at + 12 + length])
        if crc != zlib.crc32(kind + body):
            raise fail(f"a {kind.decode('ascii', 'replace')} chunk has a bad CRC")
        chunks.append((kind, body))
        at += 12 + length
        if kind == b"IEND":
            break
    if at != len(data):
        raise fail("data after IEND")
    kinds = [kind for kind, _ in chunks]
    if kinds[0] != b"IHDR" or kinds[-1] != b"IEND" or set(kinds[1:-1]) != {b"IDAT"}:
        raise fail(f"its chunks are {kinds}, expected IHDR, IDAT... and IEND")
    if len(chunks[0][1]) != 13 or chunks[-1][1]:
        raise fail("an IHDR that is not 13 bytes or an IEND with data")
    columns, rows, depth, colour, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1]
    )
    if (depth, colour, compression, filtering, interlace) != (8, 0, 0, 0, 0):
        raise fail("it must be 8-bit grey (colour type 0), not interlaced")
    if not (0 < rows < MIB and 0 < columns < MIB and rows * (columns + 1) < 1 << 31):
        raise fail(f"{columns} × {rows} pixels")
    wanted = rows * (columns + 1)
    inflater = zlib.decompressobj()
    try:
        raw = inflater.decompress(
            b"".join(body for kind, body in chunks if kind == b"IDAT"), wanted + 1
        )
    except zlib.error as exc:
        raise fail(f"its zlib stream is damaged: {exc}") from exc
    if len(raw) != wanted or not inflater.eof or inflater.unused_data:
        raise fail(f"its zlib stream holds {len(raw)} bytes, {rows} rows need {wanted}")
    lines = np.frombuffer(raw, dtype=np.uint8).reshape(rows, columns + 1)
    bad = np.flatnonzero(lines[:, 0])
    if len(bad):
        raise fail(
            f"row {int(bad[0])} is written with filter {int(lines[bad[0], 0])}; the format has "
            f"filter 0 on every row"
        )
    return lines[:, 1:].copy()


# ------------------------------------------------------------------------------ writing


def write_surfaces(
    out_dir: Path | str,
    area: str,
    grid: np.ndarray,
    box: Box,
    cell_m: float,
    world_sha256: str,
    source: dict,
) -> dict:
    """Write `surfaces/<area>.png.import`, `.png` and `.json` (each through a `.part` rename).

    Returns the description, which is what the `.json` holds. A `*.part` an earlier run left
    in `surfaces/` is removed once all three files are written.
    """
    if not AREA_NAME.fullmatch(area):
        raise SurfacesError(f"area name {area!r} must be lower-case letters, digits and '_'")
    frame = _Frame(box, cell_m)
    if grid.shape != (frame.rows, frame.columns):
        raise SurfacesError(
            f"the classes are {grid.shape[1]} × {grid.shape[0]}, the box at {cell_m} m needs "
            f"{frame.columns} × {frame.rows}"
        )
    png = png_l8(grid)
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    block = {
        "area": area,
        "cell_m": float(cell_m),
        "classes": dict(CLASSES),
        "columns": frame.columns,
        "file": f"surfaces/{area}.png",
        "format": FORMAT,
        "lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},
        "pixels_sha256": hashlib.sha256(np.ascontiguousarray(grid)).hexdigest(),
        "rows": frame.rows,
        "sha256": hashlib.sha256(png).hexdigest(),
        "source": source,
        "world_sha256": world_sha256,
    }
    folder = Path(out_dir) / "surfaces"
    folder.mkdir(parents=True, exist_ok=True)
    _replace(folder / f"{area}.png.import", KEEP)
    _replace(folder / f"{area}.png", png)
    _replace(folder / f"{area}.json", _json_bytes(block))
    for leftover in folder.glob("*.part"):
        leftover.unlink()
    return block


# ----------------------------------------------------------------------------- the step


def build_surfaces(
    world: World,
    datasets: dict,
    lock: dict,
    surfaces_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's surfaces from the downloaded, locked TLM; return the block.

    The checks run in the order of the module's docstring, each before the next reads
    anything. The classes' SHA-256 must equal the config's `expected_pixels_sha256` for the
    cell; it is compared before anything is written, and a difference is a SurfacesError
    naming both values (lesson 38). A missing download is refused before anything is created
    under `out_dir` and before any `progress` call.
    """
    say = progress or (lambda message: None)
    if world.mapping != OWNER_AXES:
        raise SurfacesError(
            f"{world.path}: the surfaces support only the axes x = +e, y = +h, z = -n"
        )
    check_surfaces_config(surfaces_config)
    area = configured_area(surfaces_config)
    settings = surfaces_config["areas"][area]
    cell_m = float(settings["cell_m"])
    expected = settings["expected_pixels_sha256"][cell_key(cell_m)]
    if area not in world.areas:
        raise SurfacesError(f"{world.path}: no area named {area!r} for the surfaces config's area")
    box = world.area(area)
    _Frame(box, cell_m)  # refuses a box that is not whole cells
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise SurfacesError(f"{world.path}: the world config changed while the surfaces were built")
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    problem = world_refusal(SURFACES_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise SurfacesError(f"area {area!r}: {problem}")

    tlm = _dataset(datasets)
    entry = _locked_entry(lock, datasets, world, area)
    problem = inputs_refusal(SURFACES_CONFIG_NAME, settings["computed_for"], DATASET, entry)
    if problem:
        raise SurfacesError(f"area {area!r}: {problem}")

    folder = Path(raw_root) / DATASET / tlm["edition"]
    size = _provenance_size(folder / PROVENANCE, tlm, entry)
    path = folder / entry["file"]
    seen = _signature(path)
    if seen[0] != size:
        raise SurfacesError(
            f"{path} is {seen[0]} bytes, {folder / PROVENANCE} lists {size}; "
            f"`{DOWNLOAD_COMMAND}` fetches it again"
        )
    say(f"checking the SHA-256 of {path}")
    actual = _sha256_of(path)
    if actual != entry["sha256"]:
        raise SurfacesError(
            f"{path} has SHA-256 {actual}, provenance.json and the lock pin {entry['sha256']}; "
            f"`{DOWNLOAD_COMMAND}` fetches it again"
        )
    say(f"reading {path}")
    e_min, e_max, n_min, n_max = box
    grown = (
        e_min - MARGIN_M,
        e_max + MARGIN_M,
        n_min - MARGIN_M,
        n_max + MARGIN_M,
    )
    features = read_tlm(path, LAYERS, grown)
    if _signature(path) != seen:
        raise SurfacesError(
            f"{path} changed while it was read (size, modification time or inode); "
            f"`{DOWNLOAD_COMMAND}` fetches it again"
        )
    say(
        "read "
        + ", ".join(f"{len(features[layer])} {layer}" for layer in sorted(features))
        + f"; classifying a {cell_m} m grid"
    )
    grid = class_grid(features, box, cell_m)
    del features
    pixels_sha256 = hashlib.sha256(grid).hexdigest()
    if pixels_sha256 != expected:
        raise SurfacesError(
            f"area {area!r} at {cell_key(cell_m)} m: the classes built here have SHA-256 "
            f"{pixels_sha256}, {SURFACES_CONFIG_NAME} expects {expected}. Design computed "
            f"the expected value two independent ways, so this machine or this code produces "
            f"other classes than the design's; nothing was written"
        )
    say(f"the classes have the SHA-256 {SURFACES_CONFIG_NAME} expects, {expected}")
    source = {
        "attribution": tlm["attribution"],
        "collection": tlm["collection"],
        "dataset": DATASET,
        "edition": tlm["edition"],
        "file": entry["file"],
        "sha256": entry["sha256"],
    }
    block = write_surfaces(out_dir, area, grid, box, cell_m, world_sha256, source)
    say(f"wrote {Path(out_dir) / block['file']} ({block['columns']} × {block['rows']} texels)")
    return block


def built_surfaces_block(
    out_dir: Path | str,
    surfaces_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str,
) -> dict | None:
    """The description of the surfaces built in `out_dir`, or None when none are built.

    Built surfaces that no longer match are a SurfacesError naming the command: a world or a
    lock entry that is not the one the expected values were computed for (naming design's
    step, as the build does), a description whose keys, area, file, format, cell, classes,
    box, columns, rows or source are not what the configs and the lock give, a missing or
    wrong `.png.import`, a PNG whose SHA-256 is not the description's, one that is not the
    pinned format (`read_png_l8`: a row with a filter other than 0, say) or whose pixels do
    not have the description's `pixels_sha256` and the config's expected value for the cell.
    `world` is the world config the manifest is written from, parsed from the bytes whose
    SHA-256 is `world_sha256`. `lock` is the lock (a dict) or the path of the lock file; it
    is read only when surfaces are built.
    """
    check_surfaces_config(surfaces_config)
    area = configured_area(surfaces_config)
    settings = surfaces_config["areas"][area]
    description = Path(out_dir) / "surfaces" / f"{area}.json"
    if not description.exists():
        return None

    def fail(message: str) -> SurfacesError:
        return SurfacesError(
            f"{description}: {message}; `{SURFACES_COMMAND}` rebuilds the surfaces"
        )

    problem = world_refusal(SURFACES_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise SurfacesError(f"area {area!r}: {problem}")
    tlm = _dataset(datasets)
    entry = _locked_entry(_lock_dict(lock), datasets, world, area)
    problem = inputs_refusal(SURFACES_CONFIG_NAME, settings["computed_for"], DATASET, entry)
    if problem:
        raise SurfacesError(f"area {area!r}: {problem}")

    try:
        block = json.loads(description.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the surfaces description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    e_min, e_max, n_min, n_max = world.area(area)
    cell_m = float(settings["cell_m"])
    frame = _Frame((e_min, e_max, n_min, n_max), cell_m)
    source = {
        "attribution": tlm["attribution"],
        "collection": tlm["collection"],
        "dataset": DATASET,
        "edition": tlm["edition"],
        "file": entry["file"],
        "sha256": entry["sha256"],
    }
    box = {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min}
    wanted = {
        "area": area,
        "cell_m": cell_m,
        "classes": CLASSES,
        "columns": frame.columns,
        "file": f"surfaces/{area}.png",
        "format": FORMAT,
        "rows": frame.rows,
        "source": source,
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
        raise fail(f"{png_path} is {pixels.shape[1]} × {pixels.shape[0]} pixels")
    if pixels.max() > ROAD:
        raise fail(f"{png_path} holds the class {int(pixels.max())}; the classes are 0 to {ROAD}")
    actual = hashlib.sha256(pixels).hexdigest()
    expected = settings["expected_pixels_sha256"][cell_key(cell_m)]
    if actual != block["pixels_sha256"]:
        raise fail(
            f"the classes in {png_path} have SHA-256 {actual}, the description's pixels_sha256 "
            f"is {block['pixels_sha256']}"
        )
    if actual != expected:
        raise fail(
            f"the classes in {png_path} have SHA-256 {actual}, {SURFACES_CONFIG_NAME} expects "
            f"{expected} at {cell_key(cell_m)} m (pixels_sha256)"
        )
    return block


def _dataset(datasets: dict) -> dict:
    """The datasets config's swisstlm3d entry, once it has what the step needs."""
    tlm = datasets.get(DATASET) if isinstance(datasets, dict) else None
    if not isinstance(tlm, dict):
        raise SurfacesError(f"config/datasets.json has no {DATASET!r} dataset")
    for key in ("attribution", "collection", "edition"):
        if not isinstance(tlm.get(key), str) or not tlm[key]:
            raise SurfacesError(f"config/datasets.json: {DATASET} {key} must be a non-empty string")
    if not SAFE_NAME.fullmatch(tlm["edition"]):
        raise SurfacesError(f"config/datasets.json: {DATASET} edition {tlm['edition']!r}")
    return tlm


def _locked_entry(lock: object, datasets: dict, world: World, area: str) -> dict:
    """The lock's swisstlm3d entry, once `lock.fit_problem` shows it fits the datasets config
    and `lock.shape_problem` that the lock is well-formed.

    The entry pins one national file (no tiles): for the config's collection and edition,
    so `world` and `area` are not read by the rule. A lock that does not fit is refused
    naming `lock tlm`.
    """
    problem = fit_problem(lock, datasets, world, area, DATASET) or shape_problem(lock)
    if problem:
        raise SurfacesError(problem)
    return lock["datasets"][DATASET]


def _lock_dict(lock: dict | Path | str) -> dict:
    """The lock as given (a dict), or the JSON file at the path given; the lock's fit follows."""
    if not isinstance(lock, str | os.PathLike):
        return lock
    try:
        return json.loads(Path(lock).read_bytes().decode("utf-8"))
    except OSError as exc:
        raise SurfacesError(f"{lock}: cannot read the lock: {exc}; `{LOCK_COMMAND}`") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise SurfacesError(f"{lock}: the lock is not valid JSON: {exc}; `{LOCK_COMMAND}`") from exc


def _provenance_size(path: Path, tlm: dict, entry: dict) -> int:
    """provenance.json's `size_bytes`, once it is shown to be the download of the locked file."""

    def fail(message: str) -> SurfacesError:
        return SurfacesError(f"{path}: {message}; `{DOWNLOAD_COMMAND}` downloads what it asks for")

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
    wanted = {
        "dataset": DATASET,
        "collection": tlm["collection"],
        "edition": tlm["edition"],
        "file": entry["file"],
        "sha256": entry["sha256"],
    }
    for key, value in wanted.items():
        found = provenance.get(key)
        if isinstance(found, str) and key == "sha256":
            found = found.lower()
        if found != value:
            raise fail(
                f"it lists {key} {provenance.get(key)!r}, the config and lock ask for {value!r}"
            )
    size = provenance.get("size_bytes")
    if type(size) is not int or size < 1:
        raise fail(f"its size_bytes {size!r} is not a positive whole number")
    return size


def _signature(path: Path) -> tuple[int, int, int]:
    """(size, mtime_ns, inode) of the TLM file; a missing one is refused naming the download."""
    try:
        status = path.stat()
    except OSError as exc:
        raise SurfacesError(
            f"cannot read {path}: {exc}; `{DOWNLOAD_COMMAND}` downloads it"
        ) from exc
    return status.st_size, status.st_mtime_ns, status.st_ino


def _sha256_of(path: Path) -> str:
    try:
        with open(path, "rb") as file:
            return hashlib.file_digest(file, "sha256").hexdigest()
    except OSError as exc:
        raise SurfacesError(
            f"cannot read {path}: {exc}; `{DOWNLOAD_COMMAND}` downloads it again"
        ) from exc


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)


# ----------------------------------------------------------------------------- the reader


def read_tlm(path: Path | str, layers: dict, box: Box) -> dict:
    """The features of `layers` of the zipped swissTLM3D FileGDB at `path` that meet `box`.

    `layers` maps a layer name to the integer attributes to hand over besides the UUID. The
    zip is read through GDAL's zip access, from its one `.gdb` folder (swisstopo's member
    names use backslashes), never unzipped to disk and never read into memory whole. Per
    layer, sorted by UUID, every feature whose 2-D geometry meets the closed `box` (e_min,
    e_max, n_min, n_max in metres): a segment of a line or of a ring touches or crosses it,
    or the box lies inside the polygon (even-odd over all its rings). GDAL's rectangle
    filter, on a box 1 m larger, is only a pre-filter; the decision is exact, in whole
    millimetres. A feature is a plain dict {"uuid", "attributes": {name: int}, "geometry":
    {"type": "MultiLineString" | "MultiPolygon", "coordinates": ...}}, every (E, N) as whole
    millimetres (heights dropped); a coordinate more than 1e-6 m off the 1 mm grid is
    refused, naming the layer and the UUID. A layer the file lacks, or a zip without exactly
    one `.gdb` folder, is a SurfacesError.
    """
    import fiona  # here only: the pipeline's other commands read no FileGDB (M3-01)

    path = Path(path)
    folder = _gdb_folder(path)
    uri = f"/vsizip/{path.resolve().as_posix()}/{folder}"
    wanted = tuple(
        _mm(v, name) for v, name in zip(box, ("e_min", "e_max", "n_min", "n_max"), strict=True)
    )
    prefilter = (
        box[0] - PREFILTER_M,
        box[2] - PREFILTER_M,
        box[1] + PREFILTER_M,
        box[3] + PREFILTER_M,
    )
    try:
        present = fiona.listlayers(uri)
    except Exception as exc:  # fiona raises DriverError, FionaValueError, ... for a bad file
        raise SurfacesError(f"{path}: cannot open the FileGDB {folder}: {exc}") from exc
    for layer in sorted(layers):
        if layer not in present:
            raise SurfacesError(
                f"{path}: the FileGDB {folder} has no layer {layer} (it has {present})"
            )
    result = {}
    for layer in sorted(layers):
        found = []
        with fiona.open(uri, layer=layer) as source:
            for feature in source.filter(bbox=prefilter):
                made = _feature(feature, layer, layers[layer], wanted)
                if made is not None:
                    found.append(made)
        found.sort(key=lambda f: f["uuid"])
        uuids = [f["uuid"] for f in found]
        if len(set(uuids)) != len(uuids):
            raise SurfacesError(f"{path}: {layer} holds a UUID twice")
        result[layer] = found
    return result


def _gdb_folder(path: Path) -> str:
    """The name of the one `.gdb` folder the zip at `path` holds."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
    except (OSError, zipfile.BadZipFile) as exc:
        raise SurfacesError(f"{path}: cannot read it as a zip: {exc}") from exc
    folders = set()
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if len(parts) > 1 and parts[0].lower().endswith(".gdb"):
            folders.add(parts[0])
    if len(folders) != 1:
        raise SurfacesError(
            f"{path}: expected exactly one .gdb folder in the zip, found {sorted(folders)}"
        )
    return folders.pop()


def _feature(feature, layer: str, names: tuple, box_mm: tuple) -> dict | None:
    """The reader's dict for a fiona feature, or None when it does not meet the box."""
    properties = feature.properties
    uuid = properties.get("UUID")
    if not isinstance(uuid, str) or not uuid:
        raise SurfacesError(f"{layer}: a feature without a UUID")
    attributes = {}
    for name in names:
        value = properties.get(name)
        if type(value) is not int:
            raise SurfacesError(f"{layer} {uuid}: {name} {value!r} is not an integer")
        attributes[name] = value
    geometry = feature.geometry
    if geometry is None:
        raise SurfacesError(f"{layer} {uuid}: it has no geometry")
    kind, coordinates = geometry.type, geometry.coordinates
    if kind == "LineString":
        kind, coordinates = "MultiLineString", [coordinates]
    elif kind == "Polygon":
        kind, coordinates = "MultiPolygon", [coordinates]
    if kind not in ("MultiLineString", "MultiPolygon"):
        raise SurfacesError(f"{layer} {uuid}: a {kind} is neither a line nor a polygon")
    if kind == "MultiLineString":
        snapped = [_snapped(part, layer, uuid) for part in coordinates]
        rings = snapped
    else:
        snapped = [[_snapped(ring, layer, uuid) for ring in polygon] for polygon in coordinates]
        rings = [ring for polygon in snapped for ring in polygon]
    if not rings or not all(len(part) for part in rings):
        raise SurfacesError(f"{layer} {uuid}: it has an empty part")
    if not _meets(rings, box_mm, kind == "MultiPolygon"):
        return None
    return {
        "uuid": uuid,
        "attributes": attributes,
        "geometry": {"type": kind, "coordinates": [_listed(part) for part in snapped]},
    }


def _snapped(points, layer: str, uuid: str) -> np.ndarray:
    """(E, N) of `points` in whole mm, as an (n, 2) int64 array; off the 1 mm grid is refused.

    A vertex that is not finite is off the grid; an empty or ragged part is refused.
    """
    try:
        metres = np.asarray(points, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise SurfacesError(f"{layer} {uuid}: its coordinates are not a list of points") from exc
    if metres.ndim != 2 or not len(metres) or metres.shape[1] < 2:
        raise SurfacesError(f"{layer} {uuid}: it has an empty part")
    metres = metres[:, :2]
    finite = np.isfinite(metres).all(axis=1)
    safe = np.where(finite[:, None], metres, 0.0)
    mm = np.rint(safe * 1000)
    off = (np.abs(safe - mm / 1000) > SNAP_TOLERANCE_M).any(axis=1) | ~finite
    if off.any():
        index = int(np.argmax(off))
        raise SurfacesError(
            f"{layer} {uuid}: the vertex {tuple(metres[index].tolist())} is more than "
            f"{SNAP_TOLERANCE_M:g} m off the 1 mm grid"
        )
    return mm.astype(np.int64)


def _listed(part):
    """A snapped part (an array, or lists of arrays) as nested lists of Python ints."""
    if isinstance(part, np.ndarray):
        return part.tolist()
    return [_listed(item) for item in part]


def _meets(parts: list[np.ndarray], box_mm: tuple, polygon: bool) -> bool:
    """Whether the lines or rings `parts` (arrays of whole-mm points) meet the closed box.

    A segment meets the rectangle unless the rectangle and the segment are strictly
    separated: by an axis (their bounding boxes are disjoint) or by the segment's line (the
    four corners strictly on one side), which are the separating axes of the two convex
    sets. All in 64-bit integers, relative to the box's corner. A polygon whose boundary
    keeps clear of the box meets it when the box lies inside it: its corner is inside
    (even-odd over all the rings, the half-open crossing rule).
    """
    e_min, e_max, n_min, n_max = box_mm
    west, east, south, north = 0, e_max - e_min, 0, n_max - n_min
    shifted = [part - np.array([e_min, n_min], dtype=np.int64) for part in parts]
    if max(int(np.abs(part).max()) for part in shifted) > LIMIT_MM:
        raise SurfacesError("a feature reaches more than 537 km from the box")
    corners = [(west, south), (east, south), (east, north), (west, north)]
    for part in shifted:
        if len(part) == 1:
            points = np.concatenate([part, part])
        else:
            points = part
        ax, ay, bx, by = points[:-1, 0], points[:-1, 1], points[1:, 0], points[1:, 1]
        apart = (
            (np.maximum(ax, bx) < west)
            | (np.minimum(ax, bx) > east)
            | (np.maximum(ay, by) < south)
            | (np.minimum(ay, by) > north)
        )
        sides = [np.sign((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) for cx, cy in corners]
        one_side = np.logical_and.reduce([s > 0 for s in sides]) | np.logical_and.reduce(
            [s < 0 for s in sides]
        )
        if (~(apart | one_side)).any():
            return True
    if not polygon:
        return False
    inside = False
    for part in shifted:
        x1, y1, x2, y2 = part[:-1, 0], part[:-1, 1], part[1:, 0], part[1:, 1]
        across = (y1 > south) != (y2 > south)
        dy = y2 - y1
        left = (west - x1) * dy < (south - y1) * (x2 - x1)
        left = np.where(dy > 0, left, ((west - x1) * dy > (south - y1) * (x2 - x1)))
        inside ^= bool((across & left).sum() % 2)
    return inside
