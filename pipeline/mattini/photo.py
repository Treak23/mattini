"""The photo: SWISSIMAGE 2023 tiles to a JPEG over the area (M3-04; SPEC §8 *The photo*).

The area's 0.1 m source pixels are counted from its north-west corner. Texel (r, c) of the
grid at `cell_m` (0.2, 0.5 or 1 m, so k = 2, 5 or 10) is the k × k block of source pixels
whose rows are r·k … r·k + k − 1 and whose columns are c·k … c·k + k − 1, counted from that
corner and not from a tile's: per channel its value is the exact integer sum of the block
divided by k², rounded half to even. All of it is integer arithmetic, so every machine
gets the same bytes (Hard Rule 5). Box arithmetic is in integer decimetres: an edge off
the 0.1 m grid by more than 1e-6 m is refused, and so is a side that is not a whole number
of cells. The raw grid (rows north to south, columns west to east, R, G, B interleaved,
uint8) hashes to `pixels_sha256`. The JPEG is Pillow's, baseline, 4:2:0, quality 92, no
EXIF or ICC; `photo/<area>.jpg.import` beside it holds Godot's "keep" remap, so Godot does
not import the file as a texture (brain.md H24).

The pixels and the JPEG must be design's: config/photo.json holds, per cell, the SHA-256
of the raw grid (`expected_pixels_sha256`) and of the JPEG (`expected_sha256`). The step
compares the pixels first, then the JPEG, before it writes anything (lesson 38); a
difference in the pixels says this machine or this code computes other pixels than design's,
a difference in the JPEG alone says this machine's JPEG encoder writes other bytes, naming
Pillow's and libjpeg-turbo's versions. The expected values hold only for the world config
and the lock's `swissimage` entry the area's `computed_for` records (brief M2-07): they are
compared first, the world, then the lock's fit to the datasets config and the area, then the
entry, and each difference names design's step, since no command of the owner's can make
the photo match values computed for another world or other inputs.

The inputs are the tiles `provenance.json` lists in `<raw>/swissimage/<edition>/`, never the
folder's listing, the tiles the area box meets (`download.area_tiles`). Each file's SHA-256
must equal its provenance entry and the lock's, and the tile is decoded from the very bytes
hashed; each must be EPSG:2056, 10'000 × 10'000 pixels, 3 uint8 bands, with the transform
exactly (0.1, 0, E0, 0, −0.1, N0 + 1000) for its id. Every refusal is a PhotoError naming
the tile or file and the command that fixes it (Hard Rule 2). `build_photo` works in strips
of whole texel rows of 100 m, each reading only its windows of the verified tiles: the bytes
are those of one mosaic of the whole area, which peaked at 10.5 GB where the strips need
about 1.2 GB (measured on the real area, brief M3-04). The photo is in LV95 only, so the
world config's axis mapping does not enter it; the game's reader refuses any but the owner's
axes (SPEC §8).

`photo_tiles` and `read_tiles` are the checked tile reader for the roofs step (brief M3-05):
the area's tiles, each checked as above, decoded one at a time as rasters.

The files, each written through a `.part` rename: `photo/<area>.jpg`, then
`photo/<area>.jpg.import`, then the description `photo/<area>.json`, which the manifest
copies verbatim and which does not list the `.import` file (it is Godot's, not data).
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import PIL
import PIL.features
import rasterio
from PIL import Image
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile
from rasterio.windows import Window

from mattini.download import PROVENANCE, area_tiles
from mattini.lock import LOCK_PATH, fit_problem, load_lock, shape_problem
from mattini.terrain import (
    AREA_NAME,
    check_computed_for,
    configured_area,
    inputs_refusal,
    world_refusal,
)
from mattini.world import REPO, World, parse_world, read_config_bytes

PHOTO_CONFIG_PATH = REPO / "config" / "photo.json"
PHOTO_CONFIG_NAME = "config/photo.json"  # the home of the expected values, for messages
SCHEMA = 1
DATASET = "swissimage"
CELLS = (0.2, 0.5, 1.0)
CELL_KEYS = ("0.2", "0.5", "1")  # CELLS as swisstopo writes a resolution: format(c, "g")
AREA_CONFIG_KEYS = {"cell_m", "computed_for", "expected_pixels_sha256", "expected_sha256"}
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
TILE_ID = re.compile(r"([0-9]+)-([0-9]+)")
SOURCE_M = 0.1  # SWISSIMAGE's published pixel size; every cell is a whole number of pixels
TILE_M = 1000
TILE_PIXELS = round(TILE_M / SOURCE_M)
TILE_BANDS = 3
TILE_EPSG = 2056
STRIP_M = 100  # height of a strip of texel rows, metres; the bytes do not depend on it
GDAL_CACHE_MB = 256  # caps GDAL's block cache (its default is a twentieth of the memory)
FORMAT = "jpeg"
JPEG_SETTINGS = {"quality": 92, "subsampling": "4:2:0"}  # the description's wording
JPEG_SUBSAMPLING = 2  # Pillow's code for 4:2:0
KEEP_IMPORT = b'[remap]\n\nimporter="keep"\n'  # Godot keeps the JPEG as it is (brain.md H24)
PHOTO_COMMAND = "python -m mattini photo"
DOWNLOAD_COMMAND = "python -m mattini download photo"
BLOCK_KEYS = {
    "area",
    "cell_m",
    "columns",
    "file",
    "format",
    "jpeg",
    "lv95_box",
    "pixels_sha256",
    "rows",
    "sha256",
    "source",
    "world_sha256",
}
SOURCE_KEYS = {"attribution", "collection", "dataset", "edition", "resolution_m", "tiles"}
SOURCE_TILE_KEYS = {"sha256", "tile"}

Box = tuple[float, float, float, float]  # e_min, e_max, n_min, n_max
Progress = Callable[[str], None]


class PhotoError(ValueError):
    """The photo cannot be built or no longer matches its inputs; the message says why."""


@dataclass(frozen=True)
class PhotoTile:
    """One downloaded tile as `photo_tiles` vouches for it: its id, its file and the SHA-256
    that provenance.json and the lock both give."""

    tile: str
    path: Path
    sha256: str


def load_photo_config(path: Path | str = PHOTO_CONFIG_PATH) -> dict:
    """config/photo.json, validated by `check_photo_config`; an error names the file."""
    path = Path(path)
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise PhotoError(f"{path}: cannot read the photo config: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise PhotoError(f"{path}: not valid JSON: {exc}") from exc
    check_photo_config(data, path)
    return data


def check_photo_config(data: object, where: Path | str = "the photo config") -> None:
    """Refuse a photo config that is not schema 1 with exactly one well-formed area.

    An area has exactly the keys `cell_m`, `computed_for`, `expected_pixels_sha256` and
    `expected_sha256`: an allowed cell; two objects from the cells as swisstopo writes a
    resolution ("0.2", "0.5", "1") to a SHA-256 in 64 lower-case hex digits, each holding a
    value for the configured cell; and what the values were computed for
    (`terrain.check_computed_for`). SPEC §8. The PhotoError names `where`.
    """

    def fail(message: str) -> PhotoError:
        return PhotoError(f"{where}: {message}")

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
        if not _is_cell(area["cell_m"]):
            raise fail(
                f"area {name!r}: cell_m must be one of {list(CELLS)}, found {area['cell_m']!r}"
            )
        for field in ("expected_pixels_sha256", "expected_sha256"):
            expected = area[field]
            if not isinstance(expected, dict):
                raise fail(f"area {name!r}: {field} must be an object, found {expected!r}")
            unknown = [key for key in expected if key not in CELL_KEYS]
            if unknown:
                raise fail(
                    f"area {name!r}: {field} holds only the cells {list(CELL_KEYS)} as swisstopo "
                    f"writes a resolution, found {unknown!r}"
                )
            for key, value in expected.items():
                if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):
                    raise fail(
                        f"area {name!r}: {field}[{key!r}] must be a SHA-256 in 64 lower-case "
                        f"hex characters, found {value!r}"
                    )
            if cell_key(area["cell_m"]) not in expected:
                raise fail(
                    f"area {name!r}: {field} holds no value for the configured cell "
                    f"{cell_key(area['cell_m'])!r}"
                )
        check_computed_for(area["computed_for"], name, fail)


def cell_key(cell_m: float) -> str:
    """A cell as swisstopo writes a resolution, the key of the expected values: 0.2 -> "0.2",
    1.0 -> "1"."""
    return format(cell_m, "g")


def photo_grid(mosaic: np.ndarray, box: Box, cell_m: float) -> np.ndarray:
    """The grid's pixels (rows × columns × 3, uint8) from a 0.1 m, north-up mosaic.

    `mosaic` covers `box` = (e_min, e_max, n_min, n_max) exactly: row 0 is the northern
    pixel row, column 0 the western pixel column, then R, G, B. Texel (r, c) is the k × k
    block of pixels counted from the north-west corner, round-half-to-even of the exact
    integer sum / k² per channel (module docstring).
    """
    k = _block_size(cell_m)
    width, height = _box_decimetres(box, cell_m)
    if not isinstance(mosaic, np.ndarray) or mosaic.ndim != 3 or mosaic.dtype != np.uint8:
        raise PhotoError("the mosaic must be a three-dimensional array of 8-bit pixels")
    if mosaic.shape != (height, width, TILE_BANDS):
        raise PhotoError(
            f"the mosaic is {mosaic.shape[1]} × {mosaic.shape[0]} pixels of {mosaic.shape[2]} "
            f"bands, the box needs {width} × {height} of {TILE_BANDS}"
        )
    return _block_means(mosaic, k)


def jpeg_encoder() -> str:
    """The encoder behind `encode_jpeg`, as the JPEG refusal names it."""
    return f"Pillow {PIL.__version__}, libjpeg-turbo {PIL.features.version('libjpeg_turbo')}"


def encode_jpeg(pixels: np.ndarray) -> bytes:
    """The JPEG of a grid: Pillow, quality 92, 4:2:0, baseline, no optimised tables."""
    if not isinstance(pixels, np.ndarray) or pixels.ndim != 3 or pixels.dtype != np.uint8:
        raise PhotoError("the pixels must be a three-dimensional array of 8-bit values")
    rows, columns, bands = pixels.shape
    if bands != TILE_BANDS or rows < 1 or columns < 1:
        raise PhotoError(f"the pixels are {columns} × {rows} of {bands} bands, not RGB")
    raw = np.ascontiguousarray(pixels).reshape(-1)
    image = Image.frombuffer("RGB", (columns, rows), raw, "raw", "RGB", 0, 1)
    out = io.BytesIO()
    image.save(
        out,
        "JPEG",
        quality=JPEG_SETTINGS["quality"],
        subsampling=JPEG_SUBSAMPLING,
        optimize=False,
        progressive=False,
    )
    return out.getvalue()


def write_photo(
    out_dir: Path | str,
    area: str,
    pixels: np.ndarray,
    box: Box,
    cell_m: float,
    world_sha256: str,
    source: dict,
) -> dict:
    """Write `photo/<area>.jpg`, `photo/<area>.jpg.import` and `photo/<area>.json`, each
    through a `.part` rename, in that order. Returns the description the `.json` holds."""
    data, block = _describe(area, pixels, box, cell_m, world_sha256, source)
    _write_files(out_dir, data, block)
    return block


def photo_lock_problem(lock: object, datasets: dict, world: World, area: str) -> str | None:
    """Why the lock's `swissimage` entry does not fit the datasets config and the area, or None.

    This is `lock.fit_problem` for SWISSIMAGE, the rule's one home (SPEC §8; brief M3-13),
    then `lock.shape_problem` for the lock's structure: the whole refusal text for a
    PhotoError, naming `python -m mattini lock photo`. The datasets config must hold a usable
    SWISSIMAGE entry first (`swissimage_dataset`).
    """
    return fit_problem(lock, datasets, world, area, DATASET) or shape_problem(lock)


def photo_tiles(
    raw_root: Path | str, swissimage: dict, lock: dict, tiles: list[str]
) -> list[PhotoTile]:
    """The area's tiles as downloaded, once vouched for: provenance.json lists exactly
    `tiles` for the config's edition and resolution, and the file name and SHA-256 it gives
    for each are the lock's (D9, D7). Nothing is read but provenance.json.

    The lock must already fit the datasets config and the area (`photo_lock_problem`): the
    callers, `build_photo` and the roofs step, ask it before they call this. A tile download
    that has not completed is a PhotoError naming `python -m mattini download photo`. The
    files themselves are read, and their bytes hashed, by `read_tiles` and `build_photo`.
    """
    locked = lock["datasets"][DATASET]["tiles"]
    raw_dir = Path(raw_root) / DATASET / swissimage["edition"]
    listed = _provenance_tiles(raw_dir / PROVENANCE, swissimage, tiles)
    result = []
    for tile in tiles:
        entry = listed[tile]
        if entry["file"] != locked[tile]["file"] or entry["sha256"] != locked[tile]["sha256"]:
            raise PhotoError(
                f"tile {tile}: provenance.json lists {entry['file']} with SHA-256 "
                f"{entry['sha256']}, the tile lock pins {locked[tile]['file']} with SHA-256 "
                f"{locked[tile]['sha256']}; `{DOWNLOAD_COMMAND}` fetches the locked tiles"
            )
        result.append(PhotoTile(tile, raw_dir / entry["file"], entry["sha256"]))
    return result


def read_tiles(
    tiles: list[PhotoTile], *, progress: Progress | None = None
) -> Iterator[tuple[int, int, np.ndarray]]:
    """The tiles as rasters `(west_dm, north_dm, pixels)`, one decoded at a time.

    `tiles` come from `photo_tiles`. The raster's west edge is E = west_dm / 10 m and its
    north edge N = north_dm / 10 m; `pixels` is a uint8 array of shape (10000, 10000, 3),
    rows north to south, columns west to east, then R, G, B. Each tile's file is read once,
    its SHA-256 compared with the one vouched for, and the tile checked (EPSG:2056, size,
    bands, transform) before it is decoded from those same bytes. The generator keeps
    nothing of a tile it has yielded: a caller that holds none, holds one tile at a time.
    """
    say = progress or (lambda message: None)
    for item in tiles:
        say(f"reading {item.path}")
        raw = _verified_bytes(item)
        try:
            with MemoryFile(raw) as memory, memory.open() as ds:
                west_dm, north_dm = _check_tile(ds, item)
                data = ds.read()
        except RasterioError as exc:
            raise _tile_error(item, f"cannot read it as a GeoTIFF: {exc}") from exc
        del raw
        yield west_dm, north_dm, np.ascontiguousarray(data.transpose(1, 2, 0))
        del data


def build_photo(
    world: World,
    datasets: dict,
    lock: dict,
    photo_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's photo from the downloaded, locked tiles; return its block.

    The checks come in this order, each before the next is made: the config, the area and
    its box on the grid; the area's `computed_for` against the world config; the lock's
    fit; `computed_for` against the lock's entry; the download (provenance.json, then each
    tile's SHA-256 and shape); then the pixels against `expected_pixels_sha256` and the
    JPEG against `expected_sha256`, each a PhotoError naming both values. Nothing is
    created under `out_dir` before all of them have passed.
    """
    say = progress or (lambda message: None)
    check_photo_config(photo_config)
    area = configured_area(photo_config)
    settings = photo_config["areas"][area]
    cell = float(settings["cell_m"])
    expected_pixels = settings["expected_pixels_sha256"][cell_key(cell)]
    expected_jpeg = settings["expected_sha256"][cell_key(cell)]
    if area not in world.areas:
        raise PhotoError(f"{world.path}: no area named {area!r} for the photo config's area")
    box = world.area(area)
    width, height = _box_decimetres(box, cell)  # refuses an area the cells do not tile
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise PhotoError(f"{world.path}: the world config changed while the photo was built")
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    computed_for = settings["computed_for"]
    problem = world_refusal(PHOTO_CONFIG_NAME, computed_for, world_sha256)
    if problem:
        raise PhotoError(f"area {area!r}: {problem}")

    swissimage = swissimage_dataset(datasets)
    tiles = area_tiles(world, area)
    problem = photo_lock_problem(lock, datasets, world, area)
    if problem:
        raise PhotoError(problem)
    problem = inputs_refusal(PHOTO_CONFIG_NAME, computed_for, DATASET, lock["datasets"][DATASET])
    if problem:
        raise PhotoError(f"area {area!r}: {problem}")
    listed = photo_tiles(raw_root, swissimage, lock, tiles)

    # every tile is read once, hashed, and checked before any strip is made
    verified = []
    for item in listed:
        say(f"reading {item.path}")
        raw = _verified_bytes(item)
        try:
            with MemoryFile(raw) as memory, memory.open() as ds:
                west_dm, north_dm = _check_tile(ds, item)
        except RasterioError as exc:
            raise _tile_error(item, f"cannot read it as a GeoTIFF: {exc}") from exc
        verified.append((item, raw, west_dm, north_dm))

    k = _block_size(cell)
    rows, columns = height // k, width // k
    say(f"averaging {width} × {height} pixels to a {cell:g} m grid of {columns} × {rows} texels")
    pixels = _grid_from_tiles(verified, box, cell)
    verified.clear()
    actual = hashlib.sha256(np.ascontiguousarray(pixels)).hexdigest()
    if actual != expected_pixels:
        raise PhotoError(
            f"area {area!r} at {cell_key(cell)} m: the pixels built here have SHA-256 "
            f"{actual}, {PHOTO_CONFIG_NAME} expects {expected_pixels}. Design computed the "
            f"expected value two independent ways, so this machine or this code computes "
            f"other pixels than design's; nothing was written"
        )
    say(f"the pixels have the SHA-256 {PHOTO_CONFIG_NAME} expects, {expected_pixels}")

    say("encoding the JPEG")
    source = {
        "attribution": swissimage["attribution"],
        "collection": swissimage["collection"],
        "dataset": DATASET,
        "edition": swissimage["edition"],
        "resolution_m": swissimage["resolution_m"],
        "tiles": [{"sha256": item.sha256, "tile": item.tile} for item in listed],
    }
    data, block = _describe(area, pixels, box, cell, world_sha256, source)
    del pixels
    if block["sha256"] != expected_jpeg:
        raise PhotoError(
            f"area {area!r} at {cell_key(cell)} m: the pixels are design's; this machine's JPEG "
            f"encoder writes other bytes: {jpeg_encoder()}. The JPEG built here has SHA-256 "
            f"{block['sha256']}, {PHOTO_CONFIG_NAME} expects {expected_jpeg}; nothing was written"
        )
    say(f"the JPEG has the SHA-256 {PHOTO_CONFIG_NAME} expects, {expected_jpeg}")
    _write_files(out_dir, data, block)
    say(f"wrote {Path(out_dir) / block['file']} ({block['columns']} × {block['rows']} texels)")
    return block


def built_photo_block(
    out_dir: Path | str,
    photo_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str = LOCK_PATH,
) -> dict | None:
    """The description of the photo built in `out_dir`, or None when none is built.

    A built photo that no longer matches is a PhotoError naming the command that rebuilds
    it: a description whose key set, area, file, format, JPEG settings, cell, world config,
    box, columns, rows or source differ from what the configs and the lock give, a JPEG
    whose SHA-256 is not the description's and design's, `pixels_sha256` that is not
    design's, and a `.import` file beside the JPEG that is missing or not Godot's "keep"
    (SPEC §8). `world` is the world config the manifest is written from, parsed from the
    bytes whose SHA-256 is `world_sha256`. `lock` is the lock or the path of the lock file,
    read only when a photo is built.

    Before the description is read, `computed_for` is compared with the world config, then
    the lock is checked to fit the datasets config and the area (naming
    `python -m mattini lock photo`), then `computed_for` is compared with its entry: a
    difference there names design's step, not the rebuild, which would be refused for the
    same reason.
    """
    check_photo_config(photo_config)
    area = configured_area(photo_config)
    settings = photo_config["areas"][area]
    path = Path(out_dir) / "photo" / f"{area}.json"
    if not path.exists():
        return None

    def fail(message: str) -> PhotoError:
        return PhotoError(f"{path}: {message}; `{PHOTO_COMMAND}` rebuilds the photo")

    problem = world_refusal(PHOTO_CONFIG_NAME, settings["computed_for"], world_sha256)
    if problem:
        raise PhotoError(f"area {area!r}: {problem}")
    if area not in world.areas:
        raise fail(f"the world config has no area {area!r}")
    swissimage = swissimage_dataset(datasets)
    if not isinstance(lock, dict):
        lock = load_lock(lock)
    tiles = area_tiles(world, area)
    problem = photo_lock_problem(lock, datasets, world, area)
    if problem:
        raise PhotoError(problem)
    entry = lock["datasets"][DATASET]
    problem = inputs_refusal(PHOTO_CONFIG_NAME, settings["computed_for"], DATASET, entry)
    if problem:
        raise PhotoError(f"area {area!r}: {problem}")

    try:
        block = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the photo description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    wanted = {"area": area, "file": f"photo/{area}.jpg", "format": FORMAT}
    for key, value in wanted.items():
        if block[key] != value:
            raise fail(f"{key} is {block[key]!r}, expected {value!r}")
    if block["world_sha256"] != world_sha256:
        raise fail(
            f"it was built for the world config with SHA-256 {block['world_sha256']}, "
            f"the world config now has {world_sha256}"
        )
    cell = float(settings["cell_m"])
    if type(block["cell_m"]) not in (int, float) or block["cell_m"] != cell:
        raise fail(f"it was built at {block['cell_m']!r} m, the photo config asks for {cell!r} m")
    if block["jpeg"] != JPEG_SETTINGS:
        raise fail(f"its jpeg settings are {block['jpeg']!r}, expected {JPEG_SETTINGS!r}")
    _check_shape(block, world, area, cell, fail)
    source = block["source"]
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise fail(f"its source must have exactly the keys {sorted(SOURCE_KEYS)}")
    if source["dataset"] != DATASET:
        raise fail(f"it was built from the dataset {source['dataset']!r}, not {DATASET!r}")
    for key in ("attribution", "collection", "edition", "resolution_m"):
        if source[key] != swissimage[key]:
            raise fail(
                f"it was built from SWISSIMAGE {key} {source[key]!r}, the datasets config "
                f"pins {swissimage[key]!r}"
            )
    built_tiles = source["tiles"]
    if not isinstance(built_tiles, list) or not all(
        isinstance(item, dict) and set(item) == SOURCE_TILE_KEYS for item in built_tiles
    ):
        raise fail(
            f"its source's tiles must be a list of entries with exactly the keys "
            f"{sorted(SOURCE_TILE_KEYS)}"
        )
    built = [item["tile"] for item in built_tiles]
    if built != tiles:
        raise fail(f"it was built from the tiles {built}, the area needs {tiles}")
    for item in built_tiles:
        pinned = entry["tiles"][item["tile"]]["sha256"]
        if item["sha256"] != pinned:
            raise fail(
                f"tile {item['tile']} was read with SHA-256 {item['sha256']}, the tile lock "
                f"now pins {pinned}"
            )

    expected_pixels = settings["expected_pixels_sha256"][cell_key(cell)]
    if block["pixels_sha256"] != expected_pixels:
        raise fail(
            f"its pixels have SHA-256 {block['pixels_sha256']}, the photo config expects "
            f"{expected_pixels} at {cell_key(cell)} m"
        )
    jpeg = Path(out_dir) / block["file"]
    try:
        actual = _sha256_of(jpeg)
    except OSError as exc:
        raise fail(f"its JPEG cannot be read: {exc}") from exc
    if actual != block["sha256"]:
        raise fail(f"{jpeg} has SHA-256 {actual}, the description pins {block['sha256']}")
    expected_jpeg = settings["expected_sha256"][cell_key(cell)]
    if actual != expected_jpeg:
        raise fail(
            f"{jpeg} has SHA-256 {actual}, the photo config expects {expected_jpeg} at "
            f"{cell_key(cell)} m"
        )
    keep = jpeg.with_name(jpeg.name + ".import")
    try:
        found = keep.read_bytes()
    except OSError as exc:
        raise fail(
            f"{keep} cannot be read ({exc}): without it Godot imports the JPEG as a texture "
            f"and an export ships that instead of the file"
        ) from exc
    if found != KEEP_IMPORT:
        raise fail(f"{keep} holds {found!r}, it must hold exactly {KEEP_IMPORT!r}")
    return block


def _check_shape(
    block: dict, world: World, area: str, cell_m: float, fail: Callable[[str], PhotoError]
) -> None:
    """Refuse a description whose box, columns or rows are not the area's at the cell.

    `lv95_box` must be the world config's box for the area: exactly the keys e_max, e_min,
    n_max and n_min, each a float equal to the world's. `columns` and `rows` must be whole
    numbers, the box's width and depth over the cell.
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
    try:
        width, height = _box_decimetres((e_min, e_max, n_min, n_max), cell_m)
    except PhotoError as exc:
        raise fail(f"the world config's area {area!r} does not fit the cell: {exc}") from exc
    k = _block_size(cell_m)
    for field, count in (("columns", width // k), ("rows", height // k)):
        if type(block[field]) is not int or block[field] != count:
            raise fail(
                f"{field} is {block[field]!r}, the world config's area {area!r} at "
                f"{cell_m:g} m needs {count}"
            )


def _is_cell(value: object) -> bool:
    return type(value) in (int, float) and value in CELLS


def _block_size(cell_m: float) -> int:
    """Source pixels per cell side: 2, 5 or 10."""
    if not _is_cell(cell_m):
        raise PhotoError(f"cell_m must be one of {list(CELLS)}, found {cell_m!r}")
    return round(cell_m / SOURCE_M)


def _box_decimetres(box: Box, cell_m: float) -> tuple[int, int]:
    """The box's width and depth in whole 0.1 m pixels, refusing an edge off the 0.1 m grid
    by more than 1e-6 m, an empty box, and a side that is not a whole number of cells."""
    k = _block_size(cell_m)
    edges = []
    for name, value in zip(("e_min", "e_max", "n_min", "n_max"), box, strict=True):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise PhotoError(f"the box's {name} {value!r} is not a finite number")
        decimetres = round(float(value) * 10)
        if abs(float(value) - decimetres / 10) > 1e-6:
            raise PhotoError(f"the box's {name} {value!r} is not on the 0.1 m source grid")
        edges.append(decimetres)
    e_min, e_max, n_min, n_max = edges
    width, height = e_max - e_min, n_max - n_min
    if width < 1 or height < 1:
        raise PhotoError(f"the box {box!r} is empty")
    if width % k or height % k:
        raise PhotoError(f"the box {box!r} is not a whole number of {cell_m:g} m cells")
    return width, height


def _block_means(pixels: np.ndarray, k: int) -> np.ndarray:
    """Per channel round-half-to-even of the exact sum of each k × k block / k²: `pixels` is
    rows × columns × 3 with both sides multiples of k."""
    rows, columns, bands = pixels.shape
    sums = pixels.reshape(rows // k, k, columns // k, k, bands).sum(axis=(1, 3), dtype=np.uint32)
    count = k * k
    whole, rest = np.divmod(sums, np.uint32(count))
    twice = rest * np.uint32(2)
    up = (twice > count) | ((twice == count) & ((whole & np.uint32(1)) == 1))
    return (whole + up).astype(np.uint8)


def _grid_from_tiles(verified: list, box: Box, cell_m: float) -> np.ndarray:
    """The whole grid, built in strips of whole texel rows from the verified tiles.

    `verified` holds, per tile, (PhotoTile, its bytes, west_dm, north_dm). A strip counts
    its source rows from the area's north-west corner plus a whole number of texels, so
    the bytes are those of one mosaic of the whole area.
    """
    k = _block_size(cell_m)
    width, height = _box_decimetres(box, cell_m)
    e_min_dm, n_max_dm = round(box[0] * 10), round(box[3] * 10)
    rows, columns = height // k, width // k
    strip_rows = max(1, round(STRIP_M / cell_m))
    grid = np.empty((rows, columns, TILE_BANDS), dtype=np.uint8)
    with ExitStack() as stack:
        stack.enter_context(rasterio.Env(GDAL_CACHEMAX=GDAL_CACHE_MB))
        opened = []
        for item, raw, west_dm, north_dm in verified:
            memory = stack.enter_context(MemoryFile(raw))
            try:
                opened.append((item, stack.enter_context(memory.open()), west_dm, north_dm))
            except RasterioError as exc:
                raise _tile_error(item, f"cannot read it as a GeoTIFF: {exc}") from exc
        for first in range(0, rows, strip_rows):
            last = min(rows, first + strip_rows)
            top, bottom = first * k, last * k  # global source rows of the strip
            mosaic = np.zeros((bottom - top, width, TILE_BANDS), dtype=np.uint8)
            covered = 0
            for item, ds, west_dm, north_dm in opened:
                row_shift, column_shift = n_max_dm - north_dm, west_dm - e_min_dm
                r0, r1 = max(top, row_shift), min(bottom, row_shift + TILE_PIXELS)
                c0, c1 = max(0, column_shift), min(width, column_shift + TILE_PIXELS)
                if r0 >= r1 or c0 >= c1:
                    continue
                window = Window(c0 - column_shift, r0 - row_shift, c1 - c0, r1 - r0)
                try:
                    part = ds.read(window=window)
                except RasterioError as exc:
                    raise _tile_error(item, f"cannot read it as a GeoTIFF: {exc}") from exc
                mosaic[r0 - top : r1 - top, c0:c1] = part.transpose(1, 2, 0)
                covered += (r1 - r0) * (c1 - c0)
            if covered != mosaic.shape[0] * width:  # the tiles cover the box: a bug if it fires
                raise PhotoError(
                    f"the tiles {[item.tile for item, *_ in verified]} leave part of the area "
                    f"uncovered or cover it twice"
                )
            grid[first:last] = _block_means(mosaic, k)
    return grid


def _describe(
    area: str, pixels: np.ndarray, box: Box, cell_m: float, world_sha256: str, source: dict
) -> tuple[bytes, dict]:
    """The JPEG's bytes and the description; nothing is written."""
    if not AREA_NAME.fullmatch(area):
        raise PhotoError(f"area name {area!r} must be lower-case letters, digits and '_'")
    k = _block_size(cell_m)
    width, height = _box_decimetres(box, cell_m)
    if not isinstance(pixels, np.ndarray) or pixels.shape != (height // k, width // k, 3):
        raise PhotoError(
            f"the pixels must be a {height // k} × {width // k} grid of RGB texels for the box "
            f"{box!r} at {cell_m:g} m"
        )
    pixels_sha256 = hashlib.sha256(np.ascontiguousarray(pixels)).hexdigest()
    data = encode_jpeg(pixels)
    e_min, e_max, n_min, n_max = (float(v) for v in box)
    block = {
        "area": area,
        "cell_m": float(cell_m),
        "columns": width // k,
        "file": f"photo/{area}.jpg",
        "format": FORMAT,
        "jpeg": dict(JPEG_SETTINGS),
        "lv95_box": {"e_max": e_max, "e_min": e_min, "n_max": n_max, "n_min": n_min},
        "pixels_sha256": pixels_sha256,
        "rows": height // k,
        "sha256": hashlib.sha256(data).hexdigest(),
        "source": source,
        "world_sha256": world_sha256,
    }
    return data, block


def _write_files(out_dir: Path | str, data: bytes, block: dict) -> None:
    """Write the JPEG, its `.import` and the description, each through a `.part` rename."""
    photo_dir = Path(out_dir) / "photo"
    photo_dir.mkdir(parents=True, exist_ok=True)
    jpeg = photo_dir / f"{block['area']}.jpg"
    _replace(jpeg, data)
    _replace(jpeg.with_name(jpeg.name + ".import"), KEEP_IMPORT)
    _replace(photo_dir / f"{block['area']}.json", _json_bytes(block))


def swissimage_dataset(datasets: dict) -> dict:
    """The datasets config's SWISSIMAGE entry, which must be the 0.1 m source: a config
    without it, or pinning another resolution, is a PhotoError naming the file."""
    if DATASET not in datasets:
        raise PhotoError(
            f"config/datasets.json has no {DATASET!r} dataset: its collection, edition and "
            f"attribution are read from there"
        )
    swissimage = datasets[DATASET]
    if swissimage.get("resolution_m") != SOURCE_M:
        raise PhotoError(
            f"the photo is built from {SOURCE_M} m SWISSIMAGE pixels, the datasets config "
            f"pins resolution_m {swissimage.get('resolution_m')!r}"
        )
    return swissimage


def _provenance_tiles(path: Path, swissimage: dict, tiles: list[str]) -> dict[str, dict]:
    """provenance.json's entries by tile, once it is shown to match the config (D9)."""

    def fail(message: str) -> PhotoError:
        return PhotoError(f"{path}: {message}; `{DOWNLOAD_COMMAND}` downloads what it asks for")

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
        wanted = DATASET if key == "dataset" else swissimage.get(key)
        if provenance.get(key) != wanted:
            raise fail(f"it lists {key} {provenance.get(key)!r}, the config asks for {wanted!r}")
    entries = provenance.get("tiles")
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
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


def _verified_bytes(item: PhotoTile) -> bytes:
    """The bytes of a tile's file, once their SHA-256 is the one vouched for."""
    try:
        data = item.path.read_bytes()
    except OSError as exc:
        raise PhotoError(
            f"tile {item.tile}: cannot read {item.path}: {exc}; `{DOWNLOAD_COMMAND}` fetches "
            f"it again"
        ) from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != item.sha256:
        raise PhotoError(
            f"tile {item.tile}: {item.path} has SHA-256 {actual}, provenance.json and the tile "
            f"lock pin {item.sha256}; `{DOWNLOAD_COMMAND}` fetches it again"
        )
    return data


def _check_tile(ds, item: PhotoTile) -> tuple[int, int]:
    """Refuse a tile that is not where its id says; its west and north edges in decimetres."""
    e_km, n_km = (int(v) for v in TILE_ID.fullmatch(item.tile).groups())
    west, north = e_km * TILE_M, (n_km + 1) * TILE_M
    epsg = ds.crs.to_epsg() if ds.crs is not None else None
    if epsg != TILE_EPSG:
        raise _tile_error(item, f"its CRS is {ds.crs}, expected EPSG:{TILE_EPSG}")
    if (ds.width, ds.height, ds.count) != (TILE_PIXELS, TILE_PIXELS, TILE_BANDS):
        raise _tile_error(
            item,
            f"it is {ds.width} × {ds.height} pixels in {ds.count} bands, expected "
            f"{TILE_PIXELS} × {TILE_PIXELS} in {TILE_BANDS}",
        )
    if any(dtype != "uint8" for dtype in ds.dtypes):
        raise _tile_error(item, f"its pixels are {list(ds.dtypes)}, expected uint8")
    t = ds.transform
    if (t.a, t.b, t.c, t.d, t.e, t.f) != (SOURCE_M, 0.0, west, 0.0, -SOURCE_M, north):
        raise _tile_error(
            item,
            f"its top-left corner is ({t.c}, {t.f}) with {t.a} × {-t.e} m pixels, its id "
            f"says ({west}, {north}) with {SOURCE_M} m pixels",
        )
    return west * 10, north * 10


def _tile_error(item: PhotoTile, message: str) -> PhotoError:
    return PhotoError(f"tile {item.tile}: {item.path}: {message}")


def _sha256_of(path: Path) -> str:
    with open(path, "rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _replace(path: Path, data: bytes) -> None:
    part = path.with_name(path.name + ".part")
    part.write_bytes(data)
    os.replace(part, path)
