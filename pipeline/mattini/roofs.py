"""Roof colours: each building's roof as the 2023 photo shows it (M3-05; SPEC §8 *Roof colours*).

Each building the buildings step selects gets the per-channel lower median of the photo's
0.1 m pixels inside its roof triangles, as `rrggbb`, or null when no pixel lies in them.
The selection, snapping, welding, solid check, orientation and chunk order are the buildings
step's own (`buildings._snapped`, `_weld`, `_check_solid`, `_signed_volume`, repeated here
because the step's chunks hold float32 positions and the rule below is exact). All
arithmetic is in integer units of 0.1 mm (E, N and H on their storage grids, so
round(v · 10000) is exact), a 0.1 m pixel being 1000 units:

- a *roof triangle* (a, b, c in the oriented order, counter-clockwise seen from outside) has
  n = (b − a) × (c − a) with n_H > 0 and 4·n_H² ≥ n_E² + n_N² + n_H², the game's rule that
  the unit normal's up component is at least 0.5 (Python integers, which cannot overflow);
- its *roof pixels* are the photo's pixels whose centre (west edge + 0.05 m + 0.1 m · i east,
  north edge − 0.05 m − 0.1 m · j south) lies inside or on the boundary of the plan
  projection of at least one roof triangle, by exact integer orientation tests; a pixel is
  counted once for the building however many of its triangles hold it, and pixels outside
  the photo are not counted and not refused;
- its *colour* is, per channel, the element at index floor((n − 1) / 2) of the roof pixels'
  values sorted ascending (the lower median), taken from a 256-bin histogram so that no
  list of pixels is held.

The photo reaches the rule as rasters `(west_dm, north_dm, pixels)` consumed once, none
overlapping another (a pixel in two rasters would count twice: that is refused): the
raster's west edge is E = west_dm / 10 m, its north edge N = north_dm / 10 m, `pixels` a
uint8 array (rows, columns, 3), rows north to south. `build_roofs` gives it the area's
SWISSIMAGE tiles one at a time through `photo.read_tiles`.

The file `roofs/<area>.json` (sorted keys, 2-space indent, UTF-8, LF, final newline; through
a `.part` rename) is {area, chunks: [{buildings: [{roof, roof_pixels, triangles, uuid,
vertices}] in chunk order, tile}] by tile, format "roofs-v1", lv95_box, source: {buildings,
photo}, world_sha256}; `triangles` and `vertices` are the building's counts in its chunk
file, so each chunk's sums are the chunk's. The manifest carries it verbatim.

The bytes must be design's: config/roofs.json holds the SHA-256 of the file (`expected_sha256`),
compared before anything is written (lesson 38). The value holds only for the world config
and the two lock entries, swissbuildings3d and swissimage, that the area's `computed_for`
records (brief M2-07); the step and the manifest compare the world first, then the fit of
both lock entries to the datasets config and the area, then the entries, and each difference
names design's step or the lock command, never a command that could not help. A missing
download names `python -m mattini download buildings` or `download photo`, the first of them
missing in the order of the datasets' names, before anything is created under `out_dir`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import numpy as np

from mattini import photo as photo_step
from mattini.buildings import (
    BuildingsError,
    _check_solid,
    _signed_volume,
    _snapped,
    _weld,
    read_sheet,
)
from mattini.download import PROVENANCE, area_sheets, area_tiles
from mattini.lock import entries_sha256, fit_problem, load_lock, shape_problem
from mattini.terrain import (
    AREA_NAME,
    check_computed_for,
    check_terrain_config,
    configured_area,
    world_refusal,
)
from mattini.world import REPO, World, parse_world, read_config_bytes

ROOFS_CONFIG_PATH = REPO / "config" / "roofs.json"
ROOFS_CONFIG_NAME = "config/roofs.json"  # the home of the expected value, for messages
SCHEMA = 1
FORMAT = "roofs-v1"
BUILDINGS = "swissbuildings3d"
PHOTO = photo_step.DATASET
ROOFS_COMMAND = "python -m mattini roofs"
BUILDINGS_COMMAND = "python -m mattini buildings"
DOWNLOAD_BUILDINGS_COMMAND = "python -m mattini download buildings"
TILE_M = 1000  # a chunk is the 1 km tile `<floor(E / 1000)>-<floor(N / 1000)>`
UNITS_PER_M = 10000  # integer units of 0.1 mm
PIXEL_UNITS = 1000  # one 0.1 m pixel
HALF_PIXEL_UNITS = PIXEL_UNITS // 2
MIN_UP_SQUARED = 4  # 4·n_H² >= |n|²: the unit normal's up component is at least 1/2
AREA_CONFIG_KEYS = {"computed_for", "expected_sha256"}
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
TILE_ID = re.compile(r"[0-9]+-[0-9]+")
ROOF_HEX = re.compile(r"[0-9a-f]{6}")
BLOCK_KEYS = {"area", "chunks", "format", "lv95_box", "source", "world_sha256"}
BOX_KEYS = {"e_max", "e_min", "n_max", "n_min"}
CHUNK_KEYS = {"buildings", "tile"}
BUILDING_KEYS = {"roof", "roof_pixels", "triangles", "uuid", "vertices"}
SOURCE_KEYS = {"buildings", "photo"}
BUILDINGS_SOURCE_KEYS = {"attribution", "collection", "dataset", "edition", "sheets"}
PHOTO_SOURCE_KEYS = {"attribution", "collection", "dataset", "edition", "resolution_m", "tiles"}
SHEET_KEYS = {"sha256", "sheet"}
TILE_KEYS = {"sha256", "tile"}

Box = tuple[float, float, float, float]  # e_min, e_max, n_min, n_max
Raster = tuple[int, int, np.ndarray]  # west_dm, north_dm, rows × columns × 3 uint8
Progress = Callable[[str], None]


class RoofsError(ValueError):
    """The roof colours cannot be built or no longer match their inputs; the message says why."""


def load_roofs_config(path: Path | str = ROOFS_CONFIG_PATH) -> dict:
    """config/roofs.json, validated by `check_roofs_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise RoofsError(f"{path}: cannot read the roofs config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise RoofsError(f"{path}: not valid JSON: {exc}") from exc
    check_roofs_config(data, path)
    return data


def check_roofs_config(data: object, where: Path | str = "the roofs config") -> None:
    """Refuse a roofs config that is not schema 1 with exactly one well-formed area.

    The area has exactly the keys `computed_for` (`terrain.check_computed_for`: the world
    config's SHA-256 and the SHA-256 of the two lock entries, `inputs_sha256`) and
    `expected_sha256`, the SHA-256 of `roofs/<area>.json` in 64 lower-case hex digits
    (SPEC §8). The RoofsError names `where`.
    """

    def fail(message: str) -> RoofsError:
        return RoofsError(f"{where}: {message}")

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
        expected = area["expected_sha256"]
        if not (isinstance(expected, str) and SHA256_HEX.fullmatch(expected)):
            raise fail(
                f"area {name!r}: expected_sha256 must be a SHA-256 in 64 lower-case hex "
                f"characters, found {expected!r}"
            )
        check_computed_for(area["computed_for"], name, fail)


def inputs_sha256(lock: dict) -> str:
    """The SHA-256 `computed_for.inputs_sha256` records for the two lock entries, swissbuildings3d
    and swissimage: `lock.entries_sha256`, the one home of the several-datasets rule (SPEC §8;
    brief M3-13)."""
    return entries_sha256(lock, (BUILDINGS, PHOTO))


def build_roof_chunks(
    features: list[dict], world: World, area: str, photo: Iterable[Raster]
) -> list[dict]:
    """The area's roof colours, chunk by chunk, from the features in reading order and the
    photo's rasters (module docstring).

    The chunks are sorted by tile, their buildings by UUID as text, exactly as the buildings
    step's; each building is {"roof", "roof_pixels", "triangles", "uuid", "vertices"}. A
    feature may carry "sheet", which refusals name beside its UUID. The rasters are consumed
    once, one at a time.
    """
    buildings = _selected_buildings(features, world, area)
    counts = np.zeros((len(buildings), 3, 256), dtype=np.int64)
    pixels = np.zeros(len(buildings), dtype=np.int64)
    seen: list[tuple[int, int, int, int]] = []
    for raster in photo:
        west_dm, north_dm, image = _checked_raster(raster)
        extent = (west_dm, north_dm, image.shape[0], image.shape[1])
        for other in seen:
            if _overlap(extent, other):
                raise RoofsError(
                    f"the photo's rasters at (west {west_dm / 10} m, north {north_dm / 10} m) "
                    f"and (west {other[0] / 10} m, north {other[1] / 10} m) overlap: a pixel in "
                    f"two of them would count twice"
                )
        seen.append(extent)
        for number, building in enumerate(buildings):
            if building["roof_triangles"]:
                _count_pixels(building, west_dm, north_dm, image, counts[number], pixels, number)
    chunks: dict[str, list[dict]] = {}
    for number, building in enumerate(buildings):
        chunks.setdefault(building["tile"], []).append(
            {
                "roof": _lower_median(counts[number], int(pixels[number])),
                "roof_pixels": int(pixels[number]),
                "triangles": building["triangles"],
                "uuid": building["uuid"],
                "vertices": building["vertices"],
            }
        )
    return [{"buildings": chunks[tile], "tile": tile} for tile in sorted(chunks)]


def write_roofs(
    out_dir: Path | str,
    area: str,
    chunks: list[dict],
    box: Box,
    world_sha256: str,
    source: dict,
) -> dict:
    """Write `roofs/<area>.json` (through a `.part` rename); return the description it holds."""
    data, block = _describe(area, chunks, box, world_sha256, source)
    _write_file(out_dir, data, block)
    return block


def build_roofs(
    world: World,
    datasets: dict,
    lock: dict,
    roofs_config: dict,
    terrain_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's roof colours from the downloaded, locked sheets and tiles.

    The area is the terrain config's one area (as the buildings'). The checks come in this
    order, each before the next is made: the area's `computed_for` against the world config;
    the fit of the lock's swissbuildings3d and swissimage entries to the datasets config and
    the area; `computed_for` against the two entries; the downloads (each dataset's
    provenance.json, in the order of their names); each sheet's and tile's SHA-256; then the
    SHA-256 of the file about to be written against `expected_sha256`. Nothing is created
    under `out_dir` and no progress is reported before the downloads are vouched for.
    """
    say = progress or (lambda message: None)
    check_terrain_config(terrain_config)
    area = configured_area(terrain_config)
    settings = _area_settings(roofs_config, area, ROOFS_CONFIG_NAME)
    if area not in world.areas:
        raise RoofsError(f"{world.path}: no area named {area!r} for the terrain config's area")
    box = world.area(area)
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise RoofsError(f"{world.path}: the world config changed while the roofs were built")
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    computed_for = settings["computed_for"]
    problem = world_refusal(ROOFS_CONFIG_NAME, computed_for, world_sha256)
    if problem:
        raise RoofsError(f"area {area!r}: {problem}")

    buildings = _dataset(datasets, BUILDINGS)
    swissimage = _swissimage(datasets)
    sheets, tiles = area_sheets(world, area), area_tiles(world, area)
    _require_fit(lock, datasets, world, area)
    problem = _inputs_refusal(computed_for, lock)
    if problem:
        raise RoofsError(f"area {area!r}: {problem}")

    raw_dir = Path(raw_root) / BUILDINGS / buildings["edition"]
    listed = _provenance_sheets(raw_dir / PROVENANCE, buildings, sheets)
    locked = lock["datasets"][BUILDINGS]["sheets"]
    for sheet in sheets:
        entry = listed[sheet]
        if entry["file"] != locked[sheet]["file"] or entry["sha256"] != locked[sheet]["sha256"]:
            raise RoofsError(
                f"sheet {sheet}: provenance.json lists {entry['file']} with SHA-256 "
                f"{entry['sha256']}, the lock pins {locked[sheet]['file']} with SHA-256 "
                f"{locked[sheet]['sha256']}; `{DOWNLOAD_BUILDINGS_COMMAND}` fetches the locked "
                f"sheets"
            )
    try:
        listed_tiles = photo_step.photo_tiles(raw_root, swissimage, lock, tiles)
    except photo_step.PhotoError as exc:
        raise RoofsError(str(exc)) from exc

    features, source_sheets = [], []
    for sheet in sheets:
        entry = listed[sheet]
        path = raw_dir / entry["file"]
        say(f"reading {path}")
        try:
            data = path.read_bytes()  # the bytes verified are the bytes read
        except OSError as exc:
            raise RoofsError(
                f"sheet {sheet}: cannot read {path}: {exc}; `{DOWNLOAD_BUILDINGS_COMMAND}` "
                f"fetches it again"
            ) from exc
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry["sha256"]:
            raise RoofsError(
                f"sheet {sheet}: {path} has SHA-256 {actual}, provenance.json and the lock pin "
                f"{entry['sha256']}; `{DOWNLOAD_BUILDINGS_COMMAND}` fetches it again"
            )
        read = read_sheet(data, sheet)
        del data
        features.extend(dict(feature, sheet=sheet) for feature in read)
        source_sheets.append({"sha256": entry["sha256"], "sheet": sheet})

    chunks = build_roof_chunks(features, world, area, _rasters(listed_tiles, say))
    del features
    count = sum(len(chunk["buildings"]) for chunk in chunks)
    coloured = sum(1 for chunk in chunks for b in chunk["buildings"] if b["roof"] is not None)
    pixels = sum(b["roof_pixels"] for chunk in chunks for b in chunk["buildings"])
    say(
        f"{count} buildings in {len(chunks)} chunks, {coloured} with a roof colour, {pixels} roof pixels"
    )
    source = {
        "buildings": {
            "attribution": buildings["attribution"],
            "collection": buildings["collection"],
            "dataset": BUILDINGS,
            "edition": buildings["edition"],
            "sheets": source_sheets,
        },
        "photo": _photo_source(swissimage, listed_tiles),
    }
    data, block = _describe(area, chunks, box, world_sha256, source)
    expected = settings["expected_sha256"]
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise RoofsError(
            f"area {area!r}: the roof colours built here have SHA-256 {actual}, "
            f"{ROOFS_CONFIG_NAME} expects {expected}. Design computed the expected value two "
            f"independent ways, so this machine or this code computes other roof colours than "
            f"design's; nothing was written"
        )
    say(f"the roof colours have the SHA-256 {ROOFS_CONFIG_NAME} expects, {expected}")
    _write_file(out_dir, data, block)
    say(f"wrote {Path(out_dir) / _block_file(area)}")
    return block


def built_roofs_block(
    out_dir: Path | str,
    roofs_config: dict,
    terrain_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str,
    buildings_block: dict | None,
) -> dict | None:
    """The roofs built in `out_dir` (the manifest's `roofs` block), or None when none are built.

    The area is the terrain config's. With no `roofs/<area>.json` the result is None and
    nothing else is read. Roof colours without built buildings are refused naming
    `python -m mattini buildings`. `lock` is the lock or its path (read only when roofs are
    built); `buildings_block` is the buildings step's description.

    Then, in this order: `computed_for` against the world config (design's step); the fit of
    both lock entries to the datasets config and the area, a lock without one of them
    refused naming its lock command; `computed_for` against the two entries (design's
    step); the description's key sets, area, format, world config and `lv95_box`; its
    `source` against the datasets config and both lock entries; the shape of its chunks and
    their buildings (key sets, whole counts, `rrggbb` in lower case or null, no colour
    without a pixel, buildings sorted by UUID as text); the file's SHA-256 against
    `expected_sha256`; and its chunks against `buildings_block`: the same tiles in order and,
    per chunk, the building count and the sums of triangles and vertices. Every refusal of
    the description names `python -m mattini roofs`.
    """
    check_terrain_config(terrain_config)
    area = configured_area(terrain_config)
    path = Path(out_dir) / _block_file(area)
    if not path.exists():
        return None
    if buildings_block is None:
        raise RoofsError(
            f"{path}: roof colours are built, but no buildings are: they are colours of "
            f"buildings' roofs; `{BUILDINGS_COMMAND}` builds the buildings first"
        )

    def fail(message: str) -> RoofsError:
        return RoofsError(f"{path}: {message}; `{ROOFS_COMMAND}` rebuilds the roof colours")

    settings = _area_settings(roofs_config, area, ROOFS_CONFIG_NAME)
    problem = world_refusal(ROOFS_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise RoofsError(f"area {area!r}: {problem}")
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    if not isinstance(lock, dict):
        lock = load_lock(lock)
    buildings, swissimage = _dataset(datasets, BUILDINGS), _swissimage(datasets)
    sheets, tiles = area_sheets(world, area), area_tiles(world, area)
    _require_fit(lock, datasets, world, area)
    problem = _inputs_refusal(settings["computed_for"], lock)
    if problem:
        raise RoofsError(f"area {area!r}: {problem}")

    try:
        block = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the roofs description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    for key, value in {"area": area, "format": FORMAT}.items():
        if block[key] != value:
            raise fail(f"{key} is {block[key]!r}, expected {value!r}")
    if block["world_sha256"] != world_sha256:
        raise fail(
            f"it was built for the world config with SHA-256 {block['world_sha256']}, "
            f"the world config now has {world_sha256}"
        )
    _check_box(block["lv95_box"], world, area, fail)
    _check_source(block["source"], buildings, swissimage, lock, sheets, tiles, fail)
    entries = _check_chunks(block["chunks"], fail)
    actual = _sha256_of(path)
    if actual != settings["expected_sha256"]:
        raise fail(
            f"{path} has SHA-256 {actual}, the roofs config expects {settings['expected_sha256']}"
        )
    _check_against_buildings(entries, buildings_block, fail)
    return block


# --------------------------------------------------------------------------- the rule


def _selected_buildings(features: list[dict], world: World, area: str) -> list[dict]:
    """Each selected building in chunk order: its tile, UUID, counts and roof triangles.

    The buildings step's loop (`buildings._build`) up to the orientation: candidates by the
    bounding-box centre over the snapped vertices (west and south edges in, east and north
    edges out), a UUID selected twice refused, the vertices welded, the solid checked and its
    triangles reversed when the signed volume is negative. Per tile, by UUID as text.
    """
    e_min, e_max, n_min, n_max = world.area(area)
    candidates = []
    for feature in features:
        snapped = _snapped(feature)
        es = [point[0] for triangle in snapped for point in triangle]
        ns = [point[1] for triangle in snapped for point in triangle]
        centre_e = (min(es) + max(es)) / 2
        centre_n = (min(ns) + max(ns)) / 2
        if e_min <= centre_e < e_max and n_min <= centre_n < n_max:
            tile = f"{math.floor(centre_e / TILE_M)}-{math.floor(centre_n / TILE_M)}"
            candidates.append((feature, snapped, tile))
    seen: dict[str, int] = {}
    for feature, _, _ in candidates:
        seen[feature["uuid"]] = seen.get(feature["uuid"], 0) + 1
    for feature, _, _ in candidates:
        if seen[feature["uuid"]] > 1:
            raise BuildingsError(
                f"{_where(feature)}: the UUID is selected {seen[feature['uuid']]} times in "
                f"area {area!r}; a building is in one place"
            )
    buildings = []
    for feature, snapped, tile in candidates:
        vertices, triangles = _weld(snapped)
        _check_solid(feature, triangles)
        if _signed_volume(feature, vertices, triangles) < 0:
            triangles = [(a, c, b) for a, b, c in triangles]
        units = [tuple(round(value * UNITS_PER_M) for value in vertex) for vertex in vertices]
        roofs = [
            plan
            for a, b, c in triangles
            if (plan := _roof_triangle(units[a], units[b], units[c])) is not None
        ]
        buildings.append(
            {
                "tile": tile,
                "uuid": feature["uuid"],
                "vertices": len(vertices),
                "triangles": len(triangles),
                "roof_triangles": roofs,
            }
        )
    return sorted(buildings, key=lambda building: (building["tile"], building["uuid"]))


def _where(feature: dict) -> str:
    sheet = feature.get("sheet")
    return f"sheet {sheet}, UUID {feature['uuid']}" if sheet else f"UUID {feature['uuid']}"


def _roof_triangle(a: tuple, b: tuple, c: tuple) -> tuple | None:
    """The plan projection ((E, N) of a, b, c) of a roof triangle, or None for any other.

    n = (b − a) × (c − a) in (E, N, H); a roof has n_H > 0 and 4·n_H² ≥ |n|². Python
    integers: the squares of coordinates in 0.1 mm overflow 64 bits.
    """
    ux, uy, uz = (b[i] - a[i] for i in range(3))
    vx, vy, vz = (c[i] - a[i] for i in range(3))
    n_e, n_n, n_h = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    if n_h > 0 and MIN_UP_SQUARED * n_h * n_h >= n_e * n_e + n_n * n_n + n_h * n_h:
        return ((a[0], a[1]), (b[0], b[1]), (c[0], c[1]))
    return None


def _checked_raster(raster: Raster) -> Raster:
    try:
        west_dm, north_dm, image = raster
    except (TypeError, ValueError) as exc:
        raise RoofsError(
            f"a photo raster must be (west_dm, north_dm, pixels), found {raster!r}"
        ) from exc
    if type(west_dm) is not int or type(north_dm) is not int:
        raise RoofsError(
            f"a photo raster's edges must be whole decimetres, found {west_dm!r}, {north_dm!r}"
        )
    if (
        not isinstance(image, np.ndarray)
        or image.ndim != 3
        or image.shape[2] != 3
        or image.dtype != np.uint8
    ):
        raise RoofsError("a photo raster's pixels must be a rows × columns × 3 array of uint8")
    return west_dm, north_dm, image


def _overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    """Whether two rasters (west_dm, north_dm, rows, columns) share a pixel."""
    return a[0] < b[0] + b[3] and b[0] < a[0] + a[3] and a[1] - a[2] < b[1] and b[1] - b[2] < a[1]


def _count_pixels(
    building: dict,
    west_dm: int,
    north_dm: int,
    image: np.ndarray,
    counts: np.ndarray,
    pixels: np.ndarray,
    number: int,
) -> None:
    """Add the building's roof pixels that lie in this raster to its histograms.

    The pixels are the union over its roof triangles of those whose centre lies inside or
    on the boundary of the triangle's plan projection: three integer edge functions, all at
    least 0 (the triangle is counter-clockwise in plan, n_H being positive).
    """
    rows, columns = image.shape[0], image.shape[1]
    east0 = west_dm * PIXEL_UNITS + HALF_PIXEL_UNITS  # E of column 0's centre
    north0 = north_dm * PIXEL_UNITS - HALF_PIXEL_UNITS  # N of row 0's centre
    ranges = []
    for triangle in building["roof_triangles"]:
        es = [point[0] for point in triangle]
        ns = [point[1] for point in triangle]
        first_column = max(0, -((east0 - min(es)) // PIXEL_UNITS))  # ceil((min E − east0) / 1000)
        last_column = min(columns - 1, (max(es) - east0) // PIXEL_UNITS)
        first_row = max(0, -((max(ns) - north0) // PIXEL_UNITS))  # ceil((north0 − max N) / 1000)
        last_row = min(rows - 1, (north0 - min(ns)) // PIXEL_UNITS)
        if first_column <= last_column and first_row <= last_row:
            ranges.append((triangle, first_column, last_column, first_row, last_row))
    if not ranges:
        return
    column0 = min(r[1] for r in ranges)
    column1 = max(r[2] for r in ranges)
    row0 = min(r[3] for r in ranges)
    row1 = max(r[4] for r in ranges)
    mask = np.zeros((row1 - row0 + 1, column1 - column0 + 1), dtype=bool)
    for (a, b, c), first_column, last_column, first_row, last_row in ranges:
        east = east0 + PIXEL_UNITS * np.arange(first_column, last_column + 1, dtype=np.int64)
        north = north0 - PIXEL_UNITS * np.arange(first_row, last_row + 1, dtype=np.int64)
        inside = np.ones((len(north), len(east)), dtype=bool)
        for p, q in ((a, b), (b, c), (c, a)):
            # (q − p) × (centre − p) >= 0: the centre is on the inner side of, or on, the edge
            side = (q[0] - p[0]) * (north - p[1])[:, None] - (q[1] - p[1]) * (east - p[0])[None, :]
            inside &= side >= 0
        mask[
            first_row - row0 : last_row - row0 + 1,
            first_column - column0 : last_column - column0 + 1,
        ] |= inside
    chosen = image[row0 : row1 + 1, column0 : column1 + 1][mask]
    if len(chosen):
        for channel in range(3):
            counts[channel] += np.bincount(chosen[:, channel], minlength=256)
        pixels[number] += len(chosen)


def _lower_median(counts: np.ndarray, total: int) -> str | None:
    """`rrggbb` of the per-channel element at floor((total − 1) / 2) of the sorted values,
    from their 256-bin histograms; None for no pixel."""
    if total == 0:
        return None
    index = (total - 1) // 2
    values = [
        int(np.searchsorted(np.cumsum(counts[channel]), index, side="right"))
        for channel in range(3)
    ]
    return "".join(f"{value:02x}" for value in values)


# --------------------------------------------------------------------------- the description


def _block_file(area: str) -> str:
    """The description's path under the output folder."""
    return f"roofs/{area}.json"


def _describe(
    area: str, chunks: list[dict], box: Box, world_sha256: str, source: dict
) -> tuple[bytes, dict]:
    """The file's bytes and its description; nothing is written."""
    if not AREA_NAME.fullmatch(area):
        raise RoofsError(f"area name {area!r} must be lower-case letters, digits and '_'")
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    block = {
        "area": area,
        "chunks": chunks,
        "format": FORMAT,
        "lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},
        "source": source,
        "world_sha256": world_sha256,
    }
    return _json_bytes(block), block


def _write_file(out_dir: Path | str, data: bytes, block: dict) -> None:
    roofs_dir = Path(out_dir) / "roofs"
    roofs_dir.mkdir(parents=True, exist_ok=True)
    _replace(roofs_dir / f"{block['area']}.json", data)


def _photo_source(swissimage: dict, tiles: list) -> dict:
    return {
        "attribution": swissimage["attribution"],
        "collection": swissimage["collection"],
        "dataset": PHOTO,
        "edition": swissimage["edition"],
        "resolution_m": swissimage["resolution_m"],
        "tiles": [{"sha256": item.sha256, "tile": item.tile} for item in tiles],
    }


# --------------------------------------------------------------------------- the inputs


def _area_settings(roofs_config: dict, area: str, name: str) -> dict:
    """The roofs config's area (`computed_for`, `expected_sha256`), once it is `area`."""
    check_roofs_config(roofs_config, name)
    ((configured, settings),) = roofs_config["areas"].items()
    if configured != area:
        raise RoofsError(
            f"{name} expects the roof colours of area {configured!r}, the terrain config names "
            f"the area {area!r}; the pipeline serves one area, the terrain config's"
        )
    return settings


def _swissimage(datasets: dict) -> dict:
    """The datasets config's SWISSIMAGE entry (the photo step's check), as a RoofsError."""
    try:
        return photo_step.swissimage_dataset(datasets)
    except photo_step.PhotoError as exc:
        raise RoofsError(str(exc)) from exc


def _rasters(tiles: list, say: Progress) -> Iterator[Raster]:
    """The area's tiles as rasters, one at a time (`photo.read_tiles`), a tile that cannot be
    read or is not the locked bytes refused as a RoofsError."""
    try:
        yield from photo_step.read_tiles(tiles, progress=say)
    except photo_step.PhotoError as exc:
        raise RoofsError(str(exc)) from exc


def _dataset(datasets: dict, name: str) -> dict:
    if name not in datasets:
        raise RoofsError(
            f"config/datasets.json has no {name!r} dataset: its collection, edition and "
            f"attribution are read from there"
        )
    return datasets[name]


def _require_fit(lock: object, datasets: dict, world: World, area: str) -> None:
    """Refuse a lock whose swissbuildings3d or swissimage entry does not fit the datasets
    config and the area (`lock.fit_problem`, in sorted order of the names), a missing entry
    too, naming that entry's lock command; then a lock that is not well-formed
    (`lock.shape_problem`)."""
    for name in sorted((BUILDINGS, PHOTO)):
        problem = fit_problem(lock, datasets, world, area, name)
        if problem:
            raise RoofsError(problem)
    problem = shape_problem(lock)
    if problem:
        raise RoofsError(problem)


def _inputs_refusal(computed_for: dict, lock: dict) -> str | None:
    """Why the expected value does not hold for the two lock entries, or None."""
    recorded, current = computed_for["inputs_sha256"], inputs_sha256(lock)
    if recorded == current:
        return None
    return (
        f"the expected value in {ROOFS_CONFIG_NAME} was computed from the {BUILDINGS} and "
        f"{PHOTO} lock entries with SHA-256 {recorded}; config/datasets.lock.json's entries "
        f"now have {current} (a new edition or an adopted republished file). Adopting new "
        f"inputs is a design change: design recomputes the expected value (docs/SPEC.md §5, §8)"
    )


def _provenance_sheets(path: Path, buildings: dict, sheets: list[str]) -> dict[str, dict]:
    """provenance.json's entries by sheet, once it is shown to match the config (D9)."""

    def fail(message: str) -> RoofsError:
        return RoofsError(
            f"{path}: {message}; `{DOWNLOAD_BUILDINGS_COMMAND}` downloads what it asks for"
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
    for key in ("dataset", "collection", "edition"):
        wanted = BUILDINGS if key == "dataset" else buildings[key]
        if provenance.get(key) != wanted:
            raise fail(f"it lists {key} {provenance.get(key)!r}, the config asks for {wanted!r}")
    entries = provenance.get("sheets")
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise fail("its sheets are not a list of objects")
    listed = [entry.get("sheet") for entry in entries]
    if listed != sheets:
        raise fail(f"it lists the sheets {listed}, the area needs {sheets}")
    for entry in entries:
        name, sha256 = entry.get("file"), entry.get("sha256")
        if not (isinstance(name, str) and SAFE_NAME.fullmatch(name)):
            raise fail(f"sheet {entry['sheet']}: file {name!r} is not a plain file name")
        if not isinstance(sha256, str):
            raise fail(f"sheet {entry['sheet']}: no sha256")
    return {entry["sheet"]: entry for entry in entries}


# --------------------------------------------------------------------------- the block


def _check_box(found: object, world: World, area: str, fail: Callable[[str], RoofsError]) -> None:
    """Refuse an `lv95_box` that is not the world config's box for the area (floats)."""
    e_min, e_max, n_min, n_max = world.area(area)
    box = {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min}
    if not (
        isinstance(found, dict)
        and set(found) == BOX_KEYS
        and all(type(found[key]) is float and found[key] == value for key, value in box.items())
    ):
        raise fail(f"lv95_box is {found!r}, the world config's area {area!r} is {box!r}")


def _check_source(
    source: object,
    buildings: dict,
    swissimage: dict,
    lock: dict,
    sheets: list[str],
    tiles: list[str],
    fail: Callable[[str], RoofsError],
) -> None:
    """Refuse a `source` that is not the datasets config's and, in order, the lock's."""
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise fail(f"its source must have exactly the keys {sorted(SOURCE_KEYS)}")
    for part, config, keys, dataset, listing, pinned in (
        (
            "buildings",
            buildings,
            BUILDINGS_SOURCE_KEYS,
            BUILDINGS,
            "sheets",
            [
                {"sha256": lock["datasets"][BUILDINGS]["sheets"][sheet]["sha256"], "sheet": sheet}
                for sheet in sheets
            ],
        ),
        (
            "photo",
            swissimage,
            PHOTO_SOURCE_KEYS,
            PHOTO,
            "tiles",
            [
                {"sha256": lock["datasets"][PHOTO]["tiles"][tile]["sha256"], "tile": tile}
                for tile in tiles
            ],
        ),
    ):
        found = source[part]
        if not isinstance(found, dict) or set(found) != keys:
            raise fail(f"its {part} source must have exactly the keys {sorted(keys)}")
        if found["dataset"] != dataset:
            raise fail(f"its {part} source is the dataset {found['dataset']!r}, not {dataset!r}")
        for key in sorted(keys - {"dataset", listing}):
            if found[key] != config[key]:
                raise fail(
                    f"its {part} source has {key} {found[key]!r}, the datasets config pins "
                    f"{config[key]!r}"
                )
        if found[listing] != pinned:
            raise fail(
                f"its {part} source lists the {listing} {found[listing]}, the lock pins {pinned}"
            )


def _check_chunks(chunks: object, fail: Callable[[str], RoofsError]) -> list[dict]:
    """The chunk entries, once each has exactly its keys, its buildings theirs, and the tiles
    are distinct and sorted; returns them."""
    if not isinstance(chunks, list):
        raise fail("its chunks must be a list")
    for chunk in chunks:
        if not isinstance(chunk, dict) or set(chunk) != CHUNK_KEYS:
            raise fail(f"every chunk must have exactly the keys {sorted(CHUNK_KEYS)}")
        tile = chunk["tile"]
        if not (isinstance(tile, str) and TILE_ID.fullmatch(tile)):
            raise fail(f"{tile!r} is not a tile id '<e km>-<n km>'")
        if not isinstance(chunk["buildings"], list):
            raise fail(f"chunk {tile}: buildings must be a list")
        uuids = []
        for building in chunk["buildings"]:
            if not isinstance(building, dict) or set(building) != BUILDING_KEYS:
                raise fail(
                    f"chunk {tile}: every building must have exactly the keys {sorted(BUILDING_KEYS)}"
                )
            for key in ("roof_pixels", "triangles", "vertices"):
                if type(building[key]) is not int or building[key] < 0:
                    raise fail(f"chunk {tile}: {key} must be a whole number, not negative")
            if not (isinstance(building["uuid"], str) and building["uuid"]):
                raise fail(f"chunk {tile}: a building has no UUID")
            roof = building["roof"]
            if building["roof_pixels"] == 0:
                if roof is not None:
                    raise fail(f"chunk {tile}: {building['uuid']} has no roof pixel and a colour")
            elif not (isinstance(roof, str) and ROOF_HEX.fullmatch(roof)):
                raise fail(
                    f"chunk {tile}: {building['uuid']}: roof {roof!r} is not 'rrggbb' in lower case"
                )
            uuids.append(building["uuid"])
        if uuids != sorted(set(uuids)):
            raise fail(f"chunk {tile}: its buildings must be distinct and sorted by UUID as text")
    tiles = [chunk["tile"] for chunk in chunks]
    if tiles != sorted(set(tiles)):
        raise fail(f"its chunks {tiles} must be distinct and sorted by tile")
    return chunks


def _check_against_buildings(
    chunks: list[dict], buildings_block: dict, fail: Callable[[str], RoofsError]
) -> None:
    """Refuse chunks that are not the buildings' own: the same tiles in order and, per
    chunk, the same building count and the same sums of triangles and vertices."""
    theirs = buildings_block.get("chunks") if isinstance(buildings_block, dict) else None
    if not isinstance(theirs, list):
        raise fail("the buildings description has no chunks to compare with")
    ours, wanted = [chunk["tile"] for chunk in chunks], [chunk.get("tile") for chunk in theirs]
    if ours != wanted:
        raise fail(f"its chunks are the tiles {ours}, the buildings' are {wanted}")
    for chunk, entry in zip(chunks, theirs, strict=True):
        found = (
            len(chunk["buildings"]),
            sum(b["triangles"] for b in chunk["buildings"]),
            sum(b["vertices"] for b in chunk["buildings"]),
        )
        wanted_counts = (entry.get("buildings"), entry.get("triangles"), entry.get("vertices"))
        if found != wanted_counts:
            raise fail(
                f"chunk {chunk['tile']} has {found[0]} buildings, {found[1]} triangles and "
                f"{found[2]} vertices, the buildings' chunk has {wanted_counts[0]}, "
                f"{wanted_counts[1]} and {wanted_counts[2]}"
            )


def _sha256_of(path: Path) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)
