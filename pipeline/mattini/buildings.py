"""The buildings: swissBUILDINGS3D map sheets to mesh chunks (M2-04; SPEC §8 *The buildings*).

The inputs are the zipped FileGDBs of the map sheets `provenance.json` lists (never the
folder's listing), which must be the sheets within 100 m of the area's box
(`download.area_sheets`), each zip's SHA-256 equal to its provenance entry and the lock's.
Each zip is read from the very bytes that were hashed: its one `.gdb` folder, layer
`Building_solid`, one closed triangle solid per building (fiona reads swisstopo's
MultiPatch as a MultiPolygon Z whose every polygon is one triangle). fiona is imported
inside `read_sheet` only, never when this module is: a fiona that cannot load stops the
buildings and nothing else (brief M3-01, M2-04's check).

The rule, in order (`build_chunks`):
- *Snapping:* every coordinate goes to the file's storage grid in 64-bit, E and N to 1 mm,
  H to 0.1 mm (round half to even, then a correctly rounded division); a coordinate more
  than 1e-6 m off that grid is refused. What fiona hands over carries reader noise in the
  last bits (2622709.7309999987 for 2622709.731, measured), and the owner's Windows PC
  runs another GDAL build than a container: snapping is meant to make both read the same
  numbers, and the comparison with config/buildings.json says so when they do not.
- *Which buildings:* those whose bounding-box centre over their snapped vertices lies in
  the area box, the west and south edges included, the east and north edges excluded. A
  UUID selected twice is refused.
- *Each building:* its vertices welded by exact equality in first-appearance order; it
  must be a closed, consistently oriented triangle mesh (every directed edge once, and its
  reverse once, no triangle repeating a vertex); its signed volume, in 64-bit on the
  vertices minus vertex 0, must not be 0, and a negative one reverses every triangle
  (a, b, c) -> (a, c, b), so the output is counter-clockwise seen from outside.
- *Placement:* each vertex through the world config's `to_local` in 64-bit, then each
  component rounded once to 32-bit. The origin and axes come only from config/world.json
  (Hard Rule 4); any rotation it allows is followed.
- *Chunks:* a building belongs to the 1 km tile of its bounding-box centre; within a chunk,
  buildings are ordered by UUID as text.

The file `buildings/<tile>.bin`: the chunk's vertices (x, y, z little-endian float32 each),
then its triangles (three little-endian uint32 indices into the chunk's vertices each), no
header. Its description `buildings/<area>.json` lists the chunks; the manifest copies it
verbatim into its `buildings` block. After writing, the step removes every other `*.bin`
in `buildings/`, the chunks of an earlier build that this one does not list, and every
`*.part` there, a write cut short (briefs M2-07, M3-01; M2 R1 G-06, M2 V1-P-06), and says
how many: an export would otherwise ship them.

The chunks must be the ones design computed: config/buildings.json holds the SHA-256 of
every chunk, and the step compares the set of tiles and every chunk with it before it
writes anything (lesson 38). Those values hold only for the world config and the lock
entry the area's `computed_for` records (brief M2-07, M2 R1 P-02, I-01). The step and the
manifest check in one order (brief M3-01): the world first, then the lock's fit
(`lock.fit_problem`: the datasets config's collection and edition and exactly the area's
sheets; a lock that does not fit is refused naming `lock buildings`), then the lock's
entry, and only then the inputs and the block itself; a difference in the world or the
entry names design's step, never this machine or this code. Every refusal is a
BuildingsError naming the sheet and UUID, the file, or the command that fixes it (Hard
Rule 2). Same inputs, same bytes: no times, no absolute paths, a fixed order everywhere
(Hard Rule 5).
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import zipfile
from collections.abc import Callable
from pathlib import Path

import numpy as np

from mattini.download import BUILDINGS, BUILDINGS_LOCK_COMMAND, PROVENANCE, area_sheets
from mattini.lock import fit_problem, load_lock
from mattini.terrain import (
    AREA_NAME,
    check_computed_for,
    check_terrain_config,
    configured_area,
    inputs_refusal,
    world_refusal,
)
from mattini.world import REPO, World, parse_world, read_config_bytes

BUILDINGS_CONFIG_PATH = REPO / "config" / "buildings.json"
BUILDINGS_CONFIG_NAME = "config/buildings.json"  # the home of the expected chunks, for messages
SCHEMA = 1
FORMAT = "mesh-f32-u32-le"
LAYER = "Building_solid"
BUILDINGS_COMMAND = "python -m mattini buildings"
DOWNLOAD_COMMAND = "python -m mattini download buildings"
LOCK_COMMAND = BUILDINGS_LOCK_COMMAND
TILE_M = 1000  # a chunk is the 1 km tile `<floor(E / 1000)>-<floor(N / 1000)>`
EN_STEPS_PER_M = 1000  # the storage grid: E and N in whole millimetres
H_STEPS_PER_M = 10000  # H in tenths of a millimetre
SNAP_TOLERANCE_M = 1e-6  # farther from the grid than this is refused (a finer grid is design)
VERTEX_BYTES = 12  # x, y, z as float32
TRIANGLE_BYTES = 12  # three uint32 indices
MAX_INDEX = 2**32 - 1
AREA_CONFIG_KEYS = {"computed_for", "expected_sha256"}
TILE_ID = re.compile(r"[0-9]+-[0-9]+")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
BLOCK_KEYS = {"area", "chunks", "format", "lv95_box", "source", "world_sha256"}
CHUNK_KEYS = {"buildings", "file", "sha256", "tile", "triangles", "vertices"}
BOX_KEYS = {"e_max", "e_min", "n_max", "n_min"}
SOURCE_KEYS = {"attribution", "collection", "dataset", "edition", "sheets"}
SOURCE_SHEET_KEYS = {"sha256", "sheet"}

Box = tuple[float, float, float, float]  # e_min, e_max, n_min, n_max
Point = tuple[float, float, float]  # E, N, H
Progress = Callable[[str], None]


class BuildingsError(ValueError):
    """The buildings cannot be built or no longer match their inputs; the message says why."""


# --------------------------------------------------------------------------- the config


def load_buildings_config(path: Path | str = BUILDINGS_CONFIG_PATH) -> dict:
    """config/buildings.json, validated by `check_buildings_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise BuildingsError(f"{path}: cannot read the buildings config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise BuildingsError(f"{path}: not valid JSON: {exc}") from exc
    check_buildings_config(data, path)
    return data


def check_buildings_config(data: object, where: Path | str = "the buildings config") -> None:
    """Refuse a buildings config that is not schema 1 with exactly one well-formed area.

    The area has exactly the keys `computed_for` and `expected_sha256`: what the values
    were computed for (`terrain.check_computed_for`), and an object from tile ids
    `<e km>-<n km>` to the SHA-256 of that tile's chunk file, 64 lower-case hex digits
    (SPEC §8). The BuildingsError names `where`.
    """

    def fail(message: str) -> BuildingsError:
        return BuildingsError(f"{where}: {message}")

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
        if not isinstance(expected, dict):
            raise fail(f"area {name!r}: expected_sha256 must be an object, found {expected!r}")
        for tile, value in expected.items():
            if not TILE_ID.fullmatch(tile):
                raise fail(f"area {name!r}: {tile!r} is not a tile id '<e km>-<n km>'")
            if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):
                raise fail(
                    f"area {name!r}: expected_sha256[{tile!r}] must be a SHA-256 in 64 "
                    f"lower-case hex characters, found {value!r}"
                )
        check_computed_for(area["computed_for"], name, fail)


def _area_settings(buildings_config: dict, area: str, name: str) -> dict:
    """The buildings config's area (`computed_for`, `expected_sha256`), once it is `area`.

    `name` names the buildings config in the refusal.
    """
    check_buildings_config(buildings_config, name)
    ((configured, settings),) = buildings_config["areas"].items()
    if configured != area:
        raise BuildingsError(
            f"{name} expects the chunks of area {configured!r}, the terrain config names the "
            f"area {area!r}; the pipeline serves one area, the terrain config's"
        )
    return settings


# --------------------------------------------------------------------------- reading


def read_sheet(data: bytes, sheet: str) -> list[dict]:
    """The features of a zipped FileGDB, in reading order: {"uuid", "objektart", "triangles"}.

    `data` is the zip's bytes (the very bytes whose SHA-256 was checked); it must hold one
    `.gdb` folder, whose layer `Building_solid` is read with fiona. Each triangle is its
    three (E, N, H) points in ring order, the ring's closing point dropped, as read (not
    snapped). A feature without a non-empty text UUID, or whose geometry is not a
    MultiPolygon Z of triangles (every polygon one ring of four points, the first equal to
    the last), is refused naming the sheet and the UUID.

    fiona is imported here and nowhere else (brief M3-01): its wheel bundles its own GDAL,
    which is loaded only when a sheet is read.
    """
    import fiona.io
    from fiona.errors import FionaError

    def fail(message: str) -> BuildingsError:
        return BuildingsError(f"sheet {sheet}: {message}")

    try:
        names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        raise fail(f"not a zip archive: {exc}") from exc
    folders = sorted({name.split("/")[0] for name in names if "/" in name})
    gdbs = [folder for folder in folders if folder.endswith(".gdb")]
    if len(gdbs) != 1:
        raise fail(f"the zip must hold exactly one .gdb folder, found {gdbs}")
    features = []
    try:
        with fiona.io.ZipMemoryFile(data) as memory:
            layers = memory.listlayers(gdbs[0])
            if LAYER not in layers:
                raise fail(f"{gdbs[0]} has no layer {LAYER!r}, only {layers}")
            with memory.open(gdbs[0], layer=LAYER) as layer:
                for feature in layer:
                    features.append(_feature(feature, sheet))
    except BuildingsError:
        raise
    except (FionaError, OSError, ValueError) as exc:
        raise fail(f"cannot read {gdbs[0]} as a FileGDB layer {LAYER!r}: {exc}") from exc
    return features


def _feature(feature, sheet: str) -> dict:
    """One feature as the rule reads it, or a BuildingsError naming the sheet and the UUID."""
    properties = feature.properties
    uuid = properties.get("UUID")
    if not (isinstance(uuid, str) and uuid):
        raise BuildingsError(
            f"sheet {sheet}: feature {feature.id} has no UUID (found {uuid!r}); every "
            f"building needs one"
        )

    def fail(message: str) -> BuildingsError:
        return BuildingsError(f"sheet {sheet}, UUID {uuid}: {message}")

    geometry = feature.geometry
    if geometry is None:
        raise fail("it has no geometry")
    if geometry.type != "MultiPolygon":
        raise fail(f"its geometry is a {geometry.type}, not a MultiPolygon Z of triangles")
    triangles = []
    for number, polygon in enumerate(geometry.coordinates):
        if len(polygon) != 1:
            raise fail(f"polygon {number} has {len(polygon)} rings, a triangle has one")
        ring = polygon[0]
        if len(ring) != 4:
            raise fail(
                f"polygon {number} has {len(ring)} points, a triangle has four (the first "
                f"repeated as the last)"
            )
        if any(len(point) != 3 for point in ring):
            raise fail(f"polygon {number} has a point without a height: {ring!r}")
        if tuple(ring[0]) != tuple(ring[3]):
            raise fail(f"polygon {number} is not closed: {ring[0]!r} and {ring[3]!r}")
        triangles.append(tuple(tuple(float(value) for value in point) for point in ring[:3]))
    if not triangles:
        raise fail("its geometry holds no triangle")
    return {"uuid": uuid, "objektart": properties.get("OBJEKTART"), "triangles": triangles}


# --------------------------------------------------------------------------- the rule


def build_chunks(features: list[dict], world: World, area: str) -> list[dict]:
    """The area's chunks from the features in reading order, sorted by tile (SPEC §8).

    Each chunk is {"tile", "buildings", "vertices", "triangles", "data"}, `data` being the
    bytes of `buildings/<tile>.bin`. A feature may also carry "sheet", the sheet it was read
    from, which refusals then name beside its UUID.
    """
    chunks, _ = _build(features, world, area)
    return chunks


def _build(features: list[dict], world: World, area: str) -> tuple[list[dict], list[bool]]:
    """The chunks, and for each feature whether it was selected."""
    e_min, e_max, n_min, n_max = world.area(area)
    candidates = []  # (feature, snapped triangles, tile)
    selected = []
    for feature in features:
        snapped = _snapped(feature)
        es = [point[0] for triangle in snapped for point in triangle]
        ns = [point[1] for triangle in snapped for point in triangle]
        centre_e = (min(es) + max(es)) / 2
        centre_n = (min(ns) + max(ns)) / 2
        inside = e_min <= centre_e < e_max and n_min <= centre_n < n_max
        selected.append(inside)
        if inside:
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

    by_tile: dict[str, list[tuple[str, np.ndarray, list[tuple[int, int, int]]]]] = {}
    for feature, snapped, tile in candidates:
        vertices, triangles = _weld(snapped)
        _check_solid(feature, triangles)
        if _signed_volume(feature, vertices, triangles) < 0:
            triangles = [(a, c, b) for a, b, c in triangles]
        local = np.array([world.to_local(*vertex) for vertex in vertices], dtype=np.float64)
        by_tile.setdefault(tile, []).append((feature["uuid"], local, triangles))
    return [_chunk(tile, by_tile[tile]) for tile in sorted(by_tile)], selected


def _where(feature: dict) -> str:
    sheet = feature.get("sheet")
    return f"sheet {sheet}, UUID {feature['uuid']}" if sheet else f"UUID {feature['uuid']}"


def _snapped(feature: dict) -> list[tuple[Point, Point, Point]]:
    """The feature's triangles with every coordinate on the storage grid, in 64-bit."""
    triangles = feature["triangles"]
    if not triangles:
        raise BuildingsError(f"{_where(feature)}: it holds no triangle")
    snapped = []
    for triangle in triangles:
        if len(triangle) != 3 or any(len(point) != 3 for point in triangle):
            raise BuildingsError(f"{_where(feature)}: {triangle!r} is not three (E, N, H) points")
        snapped.append(
            tuple(
                (
                    _snap(feature, e, EN_STEPS_PER_M),
                    _snap(feature, n, EN_STEPS_PER_M),
                    _snap(feature, h, H_STEPS_PER_M),
                )
                for e, n, h in triangle
            )
        )
    return snapped


def _snap(feature: dict, value: float, steps_per_m: int) -> float:
    """round(value × steps) / steps: half to even, then a correctly rounded division."""
    value = float(value)
    if not math.isfinite(value):
        raise BuildingsError(f"{_where(feature)}: a coordinate is {value!r}, not a number")
    snapped = round(value * steps_per_m) / steps_per_m  # int / int: correctly rounded
    if abs(value - snapped) > SNAP_TOLERANCE_M:
        raise BuildingsError(
            f"{_where(feature)}: the coordinate {value!r} is {abs(value - snapped):.3g} m from "
            f"the storage grid ({1 / steps_per_m:g} m); a finer grid is a design change"
        )
    return snapped


def _weld(snapped: list[tuple[Point, Point, Point]]) -> tuple[list[Point], list[tuple[int, ...]]]:
    """Vertices by exact equality, numbered in order of first appearance; the triangles."""
    number: dict[Point, int] = {}
    vertices: list[Point] = []
    triangles = []
    for triangle in snapped:
        face = []
        for point in triangle:
            if point not in number:
                number[point] = len(vertices)
                vertices.append(point)
            face.append(number[point])
        triangles.append(tuple(face))
    return vertices, triangles


def _check_solid(feature: dict, triangles: list[tuple[int, ...]]) -> None:
    """Refuse a mesh that is not closed and consistently oriented (SPEC §8, *Each building*)."""

    def fail(message: str) -> BuildingsError:
        return BuildingsError(
            f"{_where(feature)}: not a closed, consistently oriented triangle mesh: {message}"
        )

    edges: dict[tuple[int, int], int] = {}
    for a, b, c in triangles:
        if a == b or b == c or a == c:
            raise fail(f"the triangle {(a, b, c)} repeats a vertex")
        for edge in ((a, b), (b, c), (c, a)):
            edges[edge] = edges.get(edge, 0) + 1
    for (a, b), count in edges.items():
        if count != 1:
            raise fail(f"the directed edge {(a, b)} occurs {count} times")
        if edges.get((b, a), 0) != 1:
            raise fail(f"the directed edge {(a, b)} has its reverse {edges.get((b, a), 0)} times")


def _signed_volume(feature: dict, vertices: list[Point], triangles: list[tuple[int, ...]]) -> float:
    """Σ a · (b × c) / 6 in triangle order, on the vertices minus vertex 0; 0 is refused."""
    e0, n0, h0 = vertices[0]
    relative = [(e - e0, n - n0, h - h0) for e, n, h in vertices]
    volume = 0.0
    for a, b, c in triangles:
        ax, ay, az = relative[a]
        bx, by, bz = relative[b]
        cx, cy, cz = relative[c]
        volume += (
            ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx)
        ) / 6
    if volume == 0:
        raise BuildingsError(f"{_where(feature)}: its signed volume is 0, it has no inside")
    return volume


def _chunk(tile: str, buildings: list[tuple[str, np.ndarray, list[tuple[int, ...]]]]) -> dict:
    """One chunk: its buildings by UUID as text, vertices then triangles, little-endian."""
    buildings = sorted(buildings, key=lambda building: building[0])
    vertices, triangles, offset = [], [], 0
    for _, local, faces in buildings:
        vertices.append(local)
        triangles.extend((a + offset, b + offset, c + offset) for a, b, c in faces)
        offset += len(local)
    if offset - 1 > MAX_INDEX:
        raise BuildingsError(f"chunk {tile}: {offset} vertices do not fit 32-bit indices")
    positions = np.concatenate(vertices).astype("<f4")  # each component rounded once
    indices = np.array(triangles, dtype="<u4")
    return {
        "tile": tile,
        "buildings": len(buildings),
        "vertices": int(positions.shape[0]),
        "triangles": int(indices.shape[0]),
        "data": positions.tobytes() + indices.tobytes(),
    }


# --------------------------------------------------------------------------- the files


def write_buildings(
    out_dir: Path | str,
    area: str,
    chunks: list[dict],
    box: Box,
    world_sha256: str,
    source: dict,
    *,
    progress: Progress | None = None,
) -> dict:
    """Write every `buildings/<tile>.bin` (through a `.part` rename), then `buildings/<area>.json`.

    Then remove every other `*.bin` in `buildings/`: the chunks of an earlier build that
    the new description does not list, which the game never reads and an export would ship
    (brief M2-07, M2 R1 G-06); and every `*.part` there, the files of a run cut short
    between a write and its rename (brief M3-01, M2 V1-P-06). Other files, the description
    among them, are kept; only this folder is cleaned. How many were removed goes to
    `progress` (stderr on the command line). Returns the description, which is what the
    `.json` holds.
    """
    say = progress or (lambda message: None)
    block = _describe(area, chunks, box, world_sha256, source)
    _write_files(out_dir, chunks, block)
    buildings_dir = Path(out_dir) / "buildings"
    listed = {Path(entry["file"]).name for entry in block["chunks"]}
    stale = [
        path
        for path in sorted(buildings_dir.glob("*.bin"))
        if path.name not in listed and not path.is_dir()
    ]
    for path in stale:
        path.unlink()
    say(
        f"removed {len(stale)} chunk file{'' if len(stale) == 1 else 's'} of an earlier build "
        f"that {area}.json does not list from {buildings_dir}"
    )
    leftovers = [path for path in sorted(buildings_dir.glob("*.part")) if path.is_file()]
    for path in leftovers:
        path.unlink()
    if leftovers:
        say(
            f"removed {len(leftovers)} .part file{'' if len(leftovers) == 1 else 's'} left "
            f"in {buildings_dir}"
        )
    return block


def _describe(area: str, chunks: list[dict], box: Box, world_sha256: str, source: dict) -> dict:
    """The description of `chunks`; nothing is written."""
    if not AREA_NAME.fullmatch(area):
        raise BuildingsError(f"area name {area!r} must be lower-case letters, digits and '_'")
    tiles = [chunk["tile"] for chunk in chunks]
    if tiles != sorted(set(tiles)) or not all(TILE_ID.fullmatch(tile) for tile in tiles):
        raise BuildingsError(f"the chunks' tiles {tiles} are not distinct tile ids in order")
    entries = []
    for chunk in chunks:
        if (
            len(chunk["data"])
            != VERTEX_BYTES * chunk["vertices"] + TRIANGLE_BYTES * chunk["triangles"]
        ):
            raise BuildingsError(f"chunk {chunk['tile']}: its bytes do not match its counts")
        entries.append(
            {
                "buildings": chunk["buildings"],
                "file": f"buildings/{chunk['tile']}.bin",
                "sha256": hashlib.sha256(chunk["data"]).hexdigest(),
                "tile": chunk["tile"],
                "triangles": chunk["triangles"],
                "vertices": chunk["vertices"],
            }
        )
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    return {
        "area": area,
        "chunks": entries,
        "format": FORMAT,
        "lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},
        "source": source,
        "world_sha256": world_sha256,
    }


def _write_files(out_dir: Path | str, chunks: list[dict], block: dict) -> None:
    buildings_dir = Path(out_dir) / "buildings"
    buildings_dir.mkdir(parents=True, exist_ok=True)
    for chunk in chunks:
        _replace(buildings_dir / f"{chunk['tile']}.bin", chunk["data"])
    _replace(buildings_dir / f"{block['area']}.json", _json_bytes(block))


# --------------------------------------------------------------------------- the step


def build_buildings(
    world: World,
    datasets: dict,
    lock: dict,
    buildings_config: dict,
    terrain_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's chunks from the downloaded, locked sheets; return the block.

    The area is the terrain config's one area (T-06). Every chunk's SHA-256, and the set of
    tiles, must equal the buildings config's `expected_sha256`; they are compared before
    anything is written, and a difference is a BuildingsError naming the tile and both
    values (SPEC §8, lesson 38). Before any sheet is read, and before provenance.json is,
    the checks come in this order: the area's `computed_for` must name this world config
    (as soon as it is read), the lock must fit the datasets config and the area
    (`lock.fit_problem`, a refusal naming `lock buildings`), and `computed_for` must name
    the lock's entry; each difference is its own BuildingsError (briefs M2-07, M3-01).
    """
    say = progress or (lambda message: None)
    check_terrain_config(terrain_config)
    area = configured_area(terrain_config)
    settings = _area_settings(buildings_config, area, BUILDINGS_CONFIG_NAME)
    expected, computed_for = settings["expected_sha256"], settings["computed_for"]
    if area not in world.areas:
        raise BuildingsError(f"{world.path}: no area named {area!r} for the terrain config's area")
    box = world.area(area)
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise BuildingsError(
            f"{world.path}: the world config changed while the buildings were built"
        )
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    problem = world_refusal(BUILDINGS_CONFIG_NAME, computed_for, world_sha256)
    if problem:
        raise BuildingsError(f"area {area!r}: {problem}")
    if BUILDINGS not in datasets:
        raise BuildingsError(f"the datasets config has no {BUILDINGS!r} dataset")
    dataset = datasets[BUILDINGS]
    problem = fit_problem(lock, datasets, world, area, BUILDINGS)
    if problem:
        raise BuildingsError(problem)
    locked = lock["datasets"][BUILDINGS]["sheets"]
    problem = inputs_refusal(
        BUILDINGS_CONFIG_NAME, computed_for, BUILDINGS, lock["datasets"][BUILDINGS]
    )
    if problem:
        raise BuildingsError(f"area {area!r}: {problem}")
    sheets = area_sheets(world, area)
    raw_dir = Path(raw_root) / BUILDINGS / dataset["edition"]
    listed = _provenance_sheets(raw_dir / PROVENANCE, dataset, sheets)

    features, ranges, source_sheets = [], [], []
    for sheet in sheets:
        entry = listed[sheet]
        path = raw_dir / entry["file"]
        if entry["file"] != locked[sheet]["file"] or entry["sha256"] != locked[sheet]["sha256"]:
            raise BuildingsError(
                f"sheet {sheet}: provenance.json lists {entry['file']} with SHA-256 "
                f"{entry['sha256']}, the lock pins {locked[sheet]['file']} with SHA-256 "
                f"{locked[sheet]['sha256']}; `{DOWNLOAD_COMMAND}` fetches the locked sheets"
            )
        say(f"reading {path}")
        data = _read_sheet_file(path, sheet)  # the bytes verified are the bytes read
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry["sha256"]:
            raise BuildingsError(
                f"sheet {sheet}: {path} has SHA-256 {actual}, provenance.json and the lock pin "
                f"{entry['sha256']}; `{DOWNLOAD_COMMAND}` fetches it again"
            )
        read = read_sheet(data, sheet)
        del data
        ranges.append((sheet, len(features), len(features) + len(read)))
        features.extend(dict(feature, sheet=sheet) for feature in read)
        source_sheets.append({"sha256": entry["sha256"], "sheet": sheet})

    chunks, selected = _build(features, world, area)
    del features
    for sheet, start, stop in ranges:
        say(f"sheet {sheet}: {stop - start} features read, {sum(selected[start:stop])} selected")
    buildings = sum(chunk["buildings"] for chunk in chunks)
    vertices = sum(chunk["vertices"] for chunk in chunks)
    triangles = sum(chunk["triangles"] for chunk in chunks)
    size = sum(len(chunk["data"]) for chunk in chunks)
    say(
        f"{buildings} buildings in {len(chunks)} chunks: {vertices} vertices, {triangles} "
        f"triangles, {size} bytes"
    )
    _compare_with_expected(area, chunks, expected)
    say(f"the {len(chunks)} chunks have the SHA-256s {BUILDINGS_CONFIG_NAME} expects")

    source = {
        "attribution": dataset["attribution"],
        "collection": dataset["collection"],
        "dataset": BUILDINGS,
        "edition": dataset["edition"],
        "sheets": source_sheets,
    }
    block = write_buildings(out_dir, area, chunks, box, world_sha256, source, progress=say)
    say(f"wrote {Path(out_dir) / 'buildings'} ({len(chunks)} chunks and {area}.json)")
    return block


def _compare_with_expected(area: str, chunks: list[dict], expected: dict[str, str]) -> None:
    """Refuse chunks whose tiles or SHA-256s are not the buildings config's (lesson 38)."""
    built = {chunk["tile"]: hashlib.sha256(chunk["data"]).hexdigest() for chunk in chunks}
    for tile in sorted(set(built) | set(expected)):
        if built.get(tile) == expected.get(tile):
            continue
        found = f"SHA-256 {built[tile]}" if tile in built else "no chunk"
        wanted = f"expects {expected[tile]}" if tile in expected else "expects no chunk"
        raise BuildingsError(
            f"area {area!r}, chunk {tile}: the buildings built here give {found}, "
            f"{BUILDINGS_CONFIG_NAME} {wanted}. Design computed the expected chunks two "
            f"independent ways, so this machine or this code produces other buildings than "
            f"the design's; nothing was written"
        )


def _provenance_sheets(path: Path, dataset: dict, sheets: list[str]) -> dict[str, dict]:
    """provenance.json's entries by sheet, once it is shown to match the config (D9)."""

    def fail(message: str) -> BuildingsError:
        return BuildingsError(f"{path}: {message}; `{DOWNLOAD_COMMAND}` downloads what it asks for")

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
        wanted = BUILDINGS if key == "dataset" else dataset[key]
        if provenance.get(key) != wanted:
            raise fail(f"it lists {key} {provenance.get(key)!r}, the config asks for {wanted!r}")
    entries = provenance.get("sheets")
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
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


def _read_sheet_file(path: Path, sheet: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise BuildingsError(
            f"sheet {sheet}: cannot read {path}: {exc}; `{DOWNLOAD_COMMAND}` fetches it again"
        ) from exc


# --------------------------------------------------------------------------- the manifest


def built_buildings_block(
    out_dir: Path | str,
    buildings_config: dict,
    terrain_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str,
) -> dict | None:
    """The description of the buildings built in `out_dir`, or None when none are built.

    The area is the terrain config's; with no `buildings/<area>.json` the result is None
    whatever the buildings config says, and nothing else is read. `lock` is the lock or its
    path; a path is read only when buildings are built. `world` is the world config the
    manifest is written from, parsed from the bytes whose SHA-256 is `world_sha256`.

    First, in the step's order (brief M3-01): the buildings config's `computed_for` is
    compared with the world config; then the lock must fit the datasets config and the
    area (`lock.fit_problem`), or it is refused naming `python -m mattini lock buildings`
    and no other command; then `computed_for` is compared with the lock's entry (brief
    M2-07). A difference in the world or the entry is a BuildingsError naming design's
    step, not the rebuild, which would be refused for the same reason. Then a built
    description that no longer matches is a BuildingsError naming `python -m mattini
    buildings` (SPEC §8): key sets that are not exact, another world config, an `lv95_box`
    that is not the world config's box for the area (as floats, like the terrain's; M2 R1
    P-03), a `source` that is not the datasets config's attribution, collection and edition
    and, in order, the sheets the lock pins with their SHA-256s, a chunk file whose size or
    SHA-256 differs from its entry, or chunks that are not the buildings config's. A world
    config without the area, or a datasets config without swissBUILDINGS3D, has no lock to
    fit: the block's own checks refuse it, naming the rebuild.
    """
    check_terrain_config(terrain_config)
    area = configured_area(terrain_config)
    path = Path(out_dir) / "buildings" / f"{area}.json"
    if not path.exists():
        return None

    def fail(message: str) -> BuildingsError:
        return BuildingsError(f"{path}: {message}; `{BUILDINGS_COMMAND}` rebuilds the buildings")

    try:
        settings = _area_settings(buildings_config, area, "the buildings config")
    except BuildingsError as exc:
        raise fail(str(exc)) from exc
    problem = world_refusal(BUILDINGS_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise BuildingsError(f"area {area!r}: {problem}")
    if not isinstance(lock, dict):
        lock = load_lock(lock)
    if area in world.areas and BUILDINGS in datasets:
        problem = fit_problem(lock, datasets, world, area, BUILDINGS)
        if problem:
            raise BuildingsError(problem)
        entry = lock["datasets"][BUILDINGS]
        problem = inputs_refusal(BUILDINGS_CONFIG_NAME, settings["computed_for"], BUILDINGS, entry)
        if problem:
            raise BuildingsError(f"area {area!r}: {problem}")

    try:
        block = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the buildings description: {exc}") from exc
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
    _check_source(block["source"], datasets, lock, fail)
    entries = _check_chunk_entries(block["chunks"], fail)
    for entry in entries:
        file = Path(out_dir) / entry["file"]
        try:
            size = file.stat().st_size
        except OSError as exc:
            raise fail(f"its chunk file {file} cannot be read: {exc}") from exc
        wanted = VERTEX_BYTES * entry["vertices"] + TRIANGLE_BYTES * entry["triangles"]
        if size != wanted:
            raise fail(
                f"{file} holds {size} bytes, {entry['vertices']} vertices and "
                f"{entry['triangles']} triangles need {wanted}"
            )
        actual = _sha256_of(file)
        if actual != entry["sha256"]:
            raise fail(f"{file} has SHA-256 {actual}, the description pins {entry['sha256']}")
    expected = settings["expected_sha256"]
    built = {entry["tile"]: entry["sha256"] for entry in entries}
    for tile in sorted(set(built) | set(expected)):
        if built.get(tile) != expected.get(tile):
            raise fail(
                f"chunk {tile} is {built.get(tile) or 'not built'}, the buildings config "
                f"expects {expected.get(tile) or 'no chunk'}"
            )
    return block


def _check_box(found: object, world: World, area: str, fail) -> None:
    """Refuse an `lv95_box` that is not the world config's box for the area (M2 R1 P-03).

    Exactly the keys e_max, e_min, n_max and n_min, each a float equal to the world's, as
    `terrain._check_shape` compares the terrain's; the refusal names the field and both
    values, and `fail` adds the file and the command.
    """
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    e_min, e_max, n_min, n_max = world.area(area)
    box = {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min}
    if not (
        isinstance(found, dict)
        and set(found) == BOX_KEYS
        and all(type(found[key]) is float and found[key] == value for key, value in box.items())
    ):
        raise fail(f"lv95_box is {found!r}, the world config's area {area!r} is {box!r}")


def _check_source(source: object, datasets: dict, lock: dict, fail) -> None:
    """Refuse a `source` that is not the datasets config's and, in order, the lock's sheets.

    `lock` is the parsed lock; once the datasets config has the dataset, its entry has been
    shown to fit the config and the area (`lock.fit_problem`, in `built_buildings_block`).
    """
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise fail(f"its source must have exactly the keys {sorted(SOURCE_KEYS)}")
    sheets = source["sheets"]
    if not isinstance(sheets, list) or not all(
        isinstance(entry, dict) and set(entry) == SOURCE_SHEET_KEYS for entry in sheets
    ):
        raise fail(
            f"its source's sheets must be a list of entries with exactly the keys "
            f"{sorted(SOURCE_SHEET_KEYS)}"
        )
    if source["dataset"] != BUILDINGS:
        raise fail(f"it was built from the dataset {source['dataset']!r}, not {BUILDINGS!r}")
    if BUILDINGS not in datasets:
        raise fail(f"the datasets config has no {BUILDINGS!r} dataset")
    dataset = datasets[BUILDINGS]
    for key in ("attribution", "collection", "edition"):
        if source[key] != dataset[key]:
            raise fail(
                f"it was built from swissBUILDINGS3D {key} {source[key]!r}, the datasets "
                f"config pins {dataset[key]!r}"
            )
    locked = lock["datasets"][BUILDINGS]["sheets"]
    pinned = [{"sha256": locked[sheet]["sha256"], "sheet": sheet} for sheet in sorted(locked)]
    if sheets != pinned:
        raise fail(f"it was built from the sheets {sheets}, the lock pins {pinned}")


def _check_chunk_entries(entries: object, fail) -> list[dict]:
    """The chunk entries, once each has exactly its keys and they are sorted by tile."""
    if not isinstance(entries, list):
        raise fail("its chunks must be a list")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != CHUNK_KEYS:
            raise fail(f"every chunk entry must have exactly the keys {sorted(CHUNK_KEYS)}")
        tile = entry["tile"]
        if not (isinstance(tile, str) and TILE_ID.fullmatch(tile)):
            raise fail(f"{tile!r} is not a tile id '<e km>-<n km>'")
        if entry["file"] != f"buildings/{tile}.bin":
            raise fail(f"chunk {tile}: file is {entry['file']!r}, expected 'buildings/{tile}.bin'")
        for key in ("buildings", "triangles", "vertices"):
            if type(entry[key]) is not int or entry[key] < 1:
                raise fail(f"chunk {tile}: {key} must be a positive whole number")
        if not (isinstance(entry["sha256"], str) and SHA256_HEX.fullmatch(entry["sha256"])):
            raise fail(f"chunk {tile}: sha256 must be 64 lower-case hex digits")
    tiles = [entry["tile"] for entry in entries]
    if tiles != sorted(set(tiles)):
        raise fail(f"its chunks {tiles} must be distinct and sorted by tile")
    return entries


def _sha256_of(path: Path) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)
