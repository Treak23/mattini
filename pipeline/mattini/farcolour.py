"""The far colour: SWISSIMAGE's 2 m tiles to the colour of the far terrain (v0.6.0-06; design §2).

The grid is a pixel every `cell_m` (10 m) over the surroundings box, the area's box grown by
`margin_m` (the heights' own `expected_lv95_box`, brief v0.6.0-04): pixel (r, c) is centred at
(e_min + cell/2 + cell·c, n_max − cell/2 − cell·r), rows north to south, columns west to east,
4200 columns × 4300 rows at the committed config's numbers. The area's own box is not cut: the
near terrain covers it. `cell_m` is swissALTIRegio's `resolution_m` (its samples lie on the pixel
centres) and 5 times swissimage_far's (5 × 5 source pixels a pixel), and it divides the box's
corners and 1000.

A covered pixel, one of a 1 km cell the lock pins a SWISSIMAGE tile for, is per channel
`(sum + 12) // 25` of its 5 × 5 source pixels, counted from the cell's north-west corner (the
tiles' pixel edges lie on the km grid). A pixel of a cell with no SWISSIMAGE item (the lock's
`absent` cells: Italy) is **filled**, a labelled placeholder (Hard Rule 2): its band is
`floor(h / band_m)` for the swissALTIRegio sample h at the pixel's centre in whole centimetres
(the height as swisstopo gives it, not minus `height_offset_m`), and its colour is the half-up
integer mean `(total + n // 2) // n` per channel of every covered pixel of that band; a band with
no covered pixel takes the mean of the nearest band below that has one, and only if none below has
one, of the nearest above. All of it is integer arithmetic, the band totals in 64 bits (300 pixels
of 255 already overflow 16 bits), so every machine gets the same bytes (Hard Rule 5). A pixel
centre without a sample, covered or not, is refused naming the pixel; no covered pixel at all is
refused (there is no colour to fill with).

The pixels and the JPEG must be design's: config/surroundings.json holds, in the area's `colour`,
the SHA-256 of the raw grid (rows × columns × RGB, uint8: `expected_pixels_sha256`), the filled
fraction and the JPEG's SHA-256. The step compares them in that order before it writes anything
(lesson 38): a difference in the pixels names the decoder (rasterio's and GDAL's versions: the 2 m
tiles are JPEG inside the GeoTIFF), one in the JPEG alone names the encoder (`photo.jpeg_encoder`).
The JPEG is `photo.encode_jpeg`'s, the photo's exactly. The values hold only for the world config
and the lock's `swissaltiregio` and `swissimage_far` entries that `colour.computed_for` records
(`lock.entries_sha256` over both).

The checks come in this order, each before the next reads anything, and every refusal is a
FarColourError naming what is wrong and the command or the design step that fixes it: the config
and the area's `colour` (an area without one is refused naming config/surroundings.json), the
owner's axes, the area and the box on the spacing lattice, the cell, the world (a difference is a
design change), the box, columns and rows against design's, the lock's fit (`lock.fit_problem`
with the config the step was given: swissALTIRegio's tiles, the heights' own rule, naming `python
-m mattini lock regio`; then swissimage_far's tiles and absent cells, exactly the box's 1 km
cells, naming `python -m mattini lock farphoto`; then `lock.shape_problem` once, whose text for a
lock that is not well-formed names every lock command; this module holds no copy of either rule),
the inputs (a design change again), both downloads' provenance.json, then the files. A download
that has not completed, or is not the locked one by its provenance.json, is refused naming its
`download` command before any progress line. The files are then read, the far tiles first and
swissALTIRegio's after them: each far tile's bytes against the lock's SHA-256, decoded from the
very bytes hashed, EPSG:2056, 1000 / resolution pixels a side, three uint8 bands, the transform
its id gives; each swissALTIRegio tile through the heights step's parser. A file that differs is
refused naming the tile and its `download` command. Nothing is created under `out_dir` before
every check has passed.

The files: `surroundings/<area>_colour.jpg`, then `surroundings/<area>_colour.jpg.import` (Godot's
"keep" remap, brain.md H24), then the description `surroundings/<area>_colour.json`, each written
through a `.part` rename; after a success every `*.part` left in `surroundings/` is removed and
nothing else there is touched (the heights' files stay). The description holds exactly the nine
colour keys the game's reader takes (brief v0.6.0-08), beside the heights' description.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile

from mattini import surroundings
from mattini.download import FARPHOTO, PROVENANCE, DownloadError
from mattini.lock import LockError, entries_sha256, fit_problem, shape_problem
from mattini.photo import KEEP_IMPORT, encode_jpeg, jpeg_encoder
from mattini.surroundings import (
    DATASETS_CONFIG_NAME,
    SURROUNDINGS_CONFIG_NAME,
    Grid,
    SurroundingsError,
    check_surroundings_config,
    expected_problem,
    read_lock,
    regio_config,
    regio_provenance_tiles,
    regio_tile_bytes,
    regio_tile_samples,
    surroundings_grid,
)
from mattini.terrain import OWNER_AXES, configured_area, world_refusal
from mattini.world import World, parse_world, read_config_bytes

REGIO = surroundings.DATASET  # "swissaltiregio": the samples that give the filled pixels a band
REGIO_DOWNLOAD_COMMAND = surroundings.DOWNLOAD_COMMAND
DATASET = FARPHOTO  # "swissimage_far": SWISSIMAGE's 2 m asset over the surroundings
FORMAT = "jpeg"
TILE_M = 1000  # SWISSIMAGE's tiles are 1 km cells named by their south-west corner in km
TILE_EPSG = 2056
TILE_BANDS = 3
BLOCK = 5  # source pixels a colour pixel's side: the cell is 5 times the tile's resolution
DOWNLOAD_COMMAND = "python -m mattini download farphoto"
STEP_COMMAND = "python -m mattini farcolour"
TILE_ID = re.compile(r"([0-9]+)-([0-9]+)")
BLOCK_KEYS = {
    "colour_cell_m",
    "colour_columns",
    "colour_file",
    "colour_format",
    "colour_pixels_sha256",
    "colour_rows",
    "colour_sha256",
    "colour_source",
    "filled_fraction",
}
SOURCE_KEYS = {"attribution", "collection", "dataset", "edition"}

Progress = Callable[[str], None]


class FarColourError(ValueError):
    """The far colour cannot be built or no longer matches its inputs; the message says why."""


@dataclass(frozen=True)
class _Plan:
    """What the checks up to the inputs settle: the grid, the datasets and the tiles to read."""

    area: str
    colour: dict  # the config's colour block
    grid: Grid  # the heights' grid: the surroundings box and swissALTIRegio's tile rule
    cell: int
    columns: int
    rows: int
    regio: dict  # the datasets config's swissaltiregio
    far: dict  # the datasets config's swissimage_far
    regio_tiles: list[str]  # the lock's swissaltiregio tiles (the fit showed them the box's)
    far_tiles: list[str]  # the lock's swissimage_far tiles, in its order


def build_farcolour(
    world: World,
    datasets: dict,
    lock: dict,
    surroundings_config: dict,
    raw_root: Path | str,
    out_dir: Path | str,
    *,
    progress: Progress | None = None,
) -> dict:
    """Build the configured area's far colour from the downloaded, locked tiles; return its block.

    The checks come in the order the module's docstring gives, each before the next reads
    anything, every refusal a FarColourError naming what is wrong and the command or the design
    step that fixes it. The pixels, the filled fraction and the JPEG must equal design's values
    in config/surroundings.json; they are compared in that order before anything is written,
    and a difference names both values (lesson 38).
    """
    say = progress or (lambda message: None)
    world_raw = read_config_bytes(world.path)
    if parse_world(world_raw, world.path) != world:
        raise FarColourError(f"{world.path}: the world config changed while the colour was built")
    world_sha256 = hashlib.sha256(world_raw).hexdigest()
    plan = _checked(world, world_sha256, datasets, lock, surroundings_config, FarColourError)
    regio_entry, far_entry = lock["datasets"][REGIO], lock["datasets"][DATASET]
    regio_dir = Path(raw_root) / REGIO / plan.regio["edition"]
    far_dir = Path(raw_root) / DATASET / plan.far["edition"]
    try:
        regio_listed = regio_provenance_tiles(
            regio_dir / PROVENANCE, plan.regio, plan.regio_tiles, regio_entry["tiles"]
        )
    except SurroundingsError as exc:
        raise FarColourError(str(exc)) from exc
    _check_far_provenance(far_dir / PROVENANCE, plan, far_entry)

    pixels, covered = _covered_pixels(plan, far_entry, far_dir, say)
    cents = _samples(plan, regio_entry, regio_dir, regio_listed, say)
    say(f"filling the {int(np.count_nonzero(~covered))} pixels without a photo by their altitude")
    _fill(pixels, covered, cents, plan.colour["band_m"])
    total = plan.rows * plan.columns
    filled = total - int(np.count_nonzero(covered))

    settings = plan.colour
    actual = hashlib.sha256(np.ascontiguousarray(pixels)).hexdigest()
    if actual != settings["expected_pixels_sha256"]:
        raise FarColourError(
            f"area {plan.area!r}: the colour pixels built here have SHA-256 {actual}, "
            f"{SURROUNDINGS_CONFIG_NAME} expects {settings['expected_pixels_sha256']}. Design "
            f"computed the expected value two ways that share no code, so this machine or this "
            f"code computes other pixels than design's; the 2 m tiles are JPEG inside the "
            f"GeoTIFF, decoded here by {_decoder()}; nothing was written"
        )
    say(
        f"the pixels have the SHA-256 {SURROUNDINGS_CONFIG_NAME} expects, "
        f"{settings['expected_pixels_sha256']}"
    )
    fraction = filled / total
    if fraction != settings["expected_filled_fraction"]:
        raise FarColourError(
            f"area {plan.area!r}: the filled fraction built here is {fraction!r} ({filled} of "
            f"{total} pixels), {SURROUNDINGS_CONFIG_NAME} expects "
            f"{settings['expected_filled_fraction']!r}; nothing was written"
        )

    say("encoding the JPEG")
    data = encode_jpeg(pixels)
    jpeg_sha256 = hashlib.sha256(data).hexdigest()
    if jpeg_sha256 != settings["expected_sha256"]:
        raise FarColourError(
            f"area {plan.area!r}: the pixels are design's; this machine's JPEG encoder writes "
            f"other bytes: {jpeg_encoder()}. The JPEG built here has SHA-256 {jpeg_sha256}, "
            f"{SURROUNDINGS_CONFIG_NAME} expects {settings['expected_sha256']}; nothing was written"
        )
    say(f"the JPEG has the SHA-256 {SURROUNDINGS_CONFIG_NAME} expects, {jpeg_sha256}")
    block = {
        "colour_cell_m": float(plan.cell),
        "colour_columns": plan.columns,
        "colour_file": f"surroundings/{plan.area}_colour.jpg",
        "colour_format": FORMAT,
        "colour_pixels_sha256": actual,
        "colour_rows": plan.rows,
        "colour_sha256": jpeg_sha256,
        "colour_source": _source(plan.far),
        "filled_fraction": fraction,
    }
    removed = _write_files(out_dir, plan.area, data, block)
    say(f"wrote {Path(out_dir) / block['colour_file']} ({plan.columns} × {plan.rows} pixels)")
    if removed:
        say(f"removed {removed} .part file{'' if removed == 1 else 's'} left in surroundings/")
    return block


def built_farcolour_block(
    out_dir: Path | str,
    surroundings_config: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: dict | Path | str,
) -> dict | None:
    """The description of the far colour built in `out_dir`, or None when none is built.

    `lock` is the lock as a dict or the lock file's path; it is read only when something is
    built. `world` is the world config the manifest is written from, parsed from the bytes whose
    SHA-256 is `world_sha256`. In the step's order: the config's `colour.computed_for` against
    the world, the box, the lock's fit (swissALTIRegio's, naming `python -m mattini lock regio`,
    then swissimage_far's, naming `python -m mattini lock farphoto`), then `computed_for` against
    the lock's two entries. A difference in the world or the entries is a FarColourError naming
    design, not the rebuild, which would be refused for the same reason. Anything else that no
    longer holds is refused naming `python -m mattini farcolour`: a description that is not
    exactly the one the step writes for this world, cell, box, source and entries (its JPEG's
    SHA-256 the config's expected one), a JPEG of another SHA-256 than the description pins, or a
    `.import` that is not Godot's "keep" remap.
    """
    try:
        check_surroundings_config(surroundings_config, SURROUNDINGS_CONFIG_NAME)
    except SurroundingsError as exc:
        raise FarColourError(str(exc)) from exc
    area = configured_area(surroundings_config)
    path = Path(out_dir) / "surroundings" / f"{area}_colour.json"
    if not path.exists():
        return None

    def fail(message: str) -> FarColourError:
        return FarColourError(f"{path}: {message}; `{STEP_COMMAND}` rebuilds the far colour")

    try:
        tile_lock = read_lock(lock)
    except SurroundingsError as exc:
        raise FarColourError(str(exc)) from exc
    plan = _checked(world, world_sha256, datasets, tile_lock, surroundings_config, fail)
    colour = plan.colour
    try:
        block = json.loads(path.read_bytes().decode("utf-8"))
    except OSError as exc:
        raise fail(f"cannot read the far colour description: {exc}") from exc
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc
    if not isinstance(block, dict) or set(block) != BLOCK_KEYS:
        raise fail(f"the description must have exactly the keys {sorted(BLOCK_KEYS)}")
    wanted = {
        "colour_file": f"surroundings/{area}_colour.jpg",
        "colour_format": FORMAT,
        "colour_pixels_sha256": colour["expected_pixels_sha256"],
        "colour_sha256": colour["expected_sha256"],
    }
    for key, value in wanted.items():
        if block[key] != value:
            raise fail(f"{key} is {block[key]!r}, expected {value!r}")
    if type(block["colour_cell_m"]) is not float or block["colour_cell_m"] != plan.cell:
        raise fail(
            f"it was built at {block['colour_cell_m']!r} m, the config asks for {plan.cell} m"
        )
    for key, count in (("colour_columns", plan.columns), ("colour_rows", plan.rows)):
        if type(block[key]) is not int or block[key] != count:
            raise fail(f"{key} is {block[key]!r}, the world config's area {area!r} needs {count}")
    fraction = block["filled_fraction"]
    if type(fraction) is not float or fraction != colour["expected_filled_fraction"]:
        raise fail(
            f"filled_fraction is {fraction!r}, {SURROUNDINGS_CONFIG_NAME} expects "
            f"{colour['expected_filled_fraction']!r}"
        )
    source = block["colour_source"]
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise fail(f"its source must have exactly the keys {sorted(SOURCE_KEYS)}")
    for key, value in _source(plan.far).items():
        if source[key] != value:
            raise fail(f"its source's {key} is {source[key]!r}, expected {value!r}")
    jpeg = Path(out_dir) / block["colour_file"]
    try:
        actual = _sha256_of(jpeg)
        keep = jpeg.with_name(jpeg.name + ".import").read_bytes()
    except OSError as exc:
        raise fail(f"the JPEG or its .import cannot be read: {exc}") from exc
    # the description's colour_sha256 is the config's expected one (`wanted` above), so the JPEG
    # that has it is the config's too: a third comparison, against the config, could never fire
    if actual != block["colour_sha256"]:
        raise fail(f"{jpeg} has SHA-256 {actual}, the description pins {block['colour_sha256']}")
    if keep != KEEP_IMPORT:
        raise fail(f"{jpeg}.import is {keep!r}, Godot must keep the JPEG as it is: {KEEP_IMPORT!r}")
    return block


def _colour_of(config: dict, area: str) -> dict:
    """The area's `colour` block, or a refusal naming config/surroundings.json."""
    colour = config["areas"][area].get("colour")
    if colour is None:
        raise FarColourError(
            f"{SURROUNDINGS_CONFIG_NAME}: area {area!r} holds no colour block: the far colour's "
            f"cell, bands and expected values are design's data and the step has none to build to "
            f"(docs/SPEC.md §8)"
        )
    return colour


def _checked(
    world: World,
    world_sha256: str,
    datasets: dict,
    lock: object,
    config: dict,
    fail: Callable[[str], FarColourError],
) -> _Plan:
    """Every check up to the inputs, in the module docstring's order; the plan they leave.

    `fail` words the refusals about the world's shape (axes, area, lattice); the rest are the
    same for the step and for the built block's check: a config, a cell, a box, a lock or an
    input that is not design's is plain.
    """
    try:
        check_surroundings_config(config, SURROUNDINGS_CONFIG_NAME)
    except SurroundingsError as exc:
        raise FarColourError(str(exc)) from exc
    area = configured_area(config)
    settings = config["areas"][area]
    colour = _colour_of(config, area)
    if world.mapping != OWNER_AXES:
        raise fail(f"{world.path}: the far colour supports only the axes x = +e, y = +h, z = -n")
    if area not in world.areas:
        raise fail(f"{world.path}: no area named {area!r} for the surroundings config's area")
    grid = surroundings_grid(world, area, settings, fail)
    regio = regio_config(datasets, fail)
    far = _far_config(datasets, fail)

    cell, box = colour["cell_m"], grid.box
    if (
        cell != regio["resolution_m"]
        or cell != BLOCK * far["resolution_m"]
        or TILE_M % cell
        or any(corner % cell for corner in box)
    ):
        raise FarColourError(
            f"{SURROUNDINGS_CONFIG_NAME}: area {area!r}: colour cell_m {cell} must be "
            f"{REGIO}'s resolution_m ({regio['resolution_m']}) and {BLOCK} times {DATASET}'s "
            f"resolution_m ({far['resolution_m']}), and divide the box's corners {list(box)} and "
            f"{TILE_M}: the samples lie on the pixel centres and a pixel is {BLOCK} × {BLOCK} "
            f"source pixels"
        )
    problem = world_refusal(SURROUNDINGS_CONFIG_NAME, colour["computed_for"], world_sha256)
    if problem:
        raise FarColourError(f"area {area!r}: {problem}")
    problem = expected_problem(grid, settings)
    if problem:
        raise FarColourError(problem)
    columns, rows = (box[1] - box[0]) // cell, (box[3] - box[2]) // cell
    for key, name, built in (
        ("expected_columns", "columns", columns),
        ("expected_rows", "rows", rows),
    ):
        if colour[key] != built:
            raise FarColourError(
                f"area {area!r}: the world config's area grown by the margin gives {built} "
                f"{name} of the colour at {cell} m, {SURROUNDINGS_CONFIG_NAME}'s colour {key} is "
                f"{colour[key]!r}. A changed area, margin or cell is a design change: design "
                f"recomputes the expected values (docs/SPEC.md §8)"
            )

    entries = (REGIO, DATASET)
    try:
        for name in entries:
            problem = fit_problem(lock, datasets, world, area, name, surroundings=config)
            if problem:
                raise FarColourError(problem)
    except DownloadError as exc:  # a datasets config fit_problem cannot read
        raise FarColourError(str(exc)) from exc
    problem = shape_problem(lock)
    if problem:
        raise FarColourError(problem)
    try:
        current = entries_sha256(lock, entries)
    except LockError as exc:  # the fits found both entries: not reached
        raise FarColourError(str(exc)) from exc
    recorded = colour["computed_for"]["inputs_sha256"]
    if recorded != current:
        raise FarColourError(
            f"area {area!r}: the expected values in {SURROUNDINGS_CONFIG_NAME}'s colour were "
            f"computed from the {REGIO} and {DATASET} lock entries with SHA-256 {recorded}; "
            f"config/datasets.lock.json's entries now have {current} (a new edition or an adopted "
            f"republished file). Adopting new inputs is a design change: design recomputes the "
            f"expected values (docs/SPEC.md §5, §8)"
        )
    far_entry = lock["datasets"][DATASET]
    return _Plan(
        area=area,
        colour=colour,
        grid=grid,
        cell=cell,
        columns=columns,
        rows=rows,
        regio=regio,
        far=far,
        regio_tiles=sorted(lock["datasets"][REGIO]["tiles"]),
        far_tiles=list(far_entry["tiles"]),
    )


def _far_config(datasets: object, fail: Callable[[str], FarColourError]) -> dict:
    """The datasets config's swissimage_far entry, once its keys are shown usable."""
    config = datasets.get(DATASET) if isinstance(datasets, dict) else None
    if not isinstance(config, dict):
        raise fail(f"{DATASETS_CONFIG_NAME} has no {DATASET!r} dataset")
    for key in ("attribution", "collection", "edition"):
        if not (isinstance(config.get(key), str) and config[key]):
            raise fail(
                f"{DATASETS_CONFIG_NAME}: {DATASET} {key} must be a text, found {config.get(key)!r}"
            )
    resolution = config.get("resolution_m")
    if type(resolution) is not int or resolution < 1:
        raise fail(
            f"{DATASETS_CONFIG_NAME}: {DATASET} resolution_m must be a whole number of metres, "
            f"found {resolution!r}"
        )
    return config


def _some(parts: list[str], limit: int = 6) -> str:
    """`parts` as a list, or its first `limit` and how many more when it is long."""
    return str(parts) if len(parts) <= limit else f"{parts[:limit]} and {len(parts) - limit} more"


def _check_far_provenance(path: Path, plan: _Plan, entry: dict) -> None:
    """Refuse a provenance.json that is not the locked swissimage_far download's."""

    def fail(message: str) -> FarColourError:
        return FarColourError(f"{path}: {message}; `{DOWNLOAD_COMMAND}` downloads what it asks for")

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
        wanted = DATASET if key == "dataset" else plan.far[key]
        if provenance.get(key) != wanted:
            raise fail(f"it lists {key} {provenance.get(key)!r}, the config asks for {wanted!r}")
    if provenance.get("absent") != entry["absent"]:
        raise fail(
            f"it lists the absent cells {provenance.get('absent')!r}, the lock records "
            f"{entry['absent']!r}"
        )
    entries = provenance.get("tiles")
    if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
        raise fail("its tiles are not a list of objects")
    listed = [item.get("tile") for item in entries]
    if listed != plan.far_tiles:
        raise fail(f"it lists the tiles {_some(listed)}, the lock pins {_some(plan.far_tiles)}")
    for item in entries:
        tile, name, sha256 = item["tile"], item.get("file"), item.get("sha256")
        pinned = entry["tiles"][tile]
        if name != pinned["file"] or sha256 != pinned["sha256"]:
            raise fail(
                f"tile {tile}: it lists {name!r} with SHA-256 {sha256!r}, the lock pins "
                f"{pinned['file']!r} with SHA-256 {pinned['sha256']!r}"
            )


def _covered_pixels(
    plan: _Plan, entry: dict, folder: Path, say: Progress
) -> tuple[np.ndarray, np.ndarray]:
    """The grid's pixels (rows × columns × 3, uint8; the filled ones still zero) and the mask of
    the covered ones, from the locked tiles read one at a time and checked."""
    e_min, _, _, n_max = plan.grid.box
    resolution = plan.far["resolution_m"]
    per_cell = TILE_M // plan.cell  # colour pixels a cell's side
    pixels = np.zeros((plan.rows, plan.columns, TILE_BANDS), dtype=np.uint8)
    covered = np.zeros((plan.rows, plan.columns), dtype=bool)
    for tile in plan.far_tiles:
        path = folder / entry["tiles"][tile]["file"]
        say(f"reading {path}")
        raw = _far_bytes(path, tile)
        actual = hashlib.sha256(raw).hexdigest()
        if actual != entry["tiles"][tile]["sha256"]:
            raise _tile_error(
                tile,
                path,
                f"it has SHA-256 {actual}, provenance.json and the lock pin "
                f"{entry['tiles'][tile]['sha256']}",
            )
        try:
            with MemoryFile(raw) as memory, memory.open() as ds:  # the bytes hashed are decoded
                west, north = _check_tile(ds, tile, path, resolution)
                data = ds.read()
        except RasterioError as exc:
            raise _tile_error(tile, path, f"cannot read it as a GeoTIFF: {exc}") from exc
        del raw
        means = _block_means(np.ascontiguousarray(data.transpose(1, 2, 0)), per_cell)
        del data
        # the tile's north-west pixel in the grid; both offsets are whole cells (the cell divides
        # the km and the box's corners)
        _place(pixels, covered, means, (n_max - north) // plan.cell, (west - e_min) // plan.cell)
    return pixels, covered


def _place(
    pixels: np.ndarray, covered: np.ndarray, means: np.ndarray, row: int, column: int
) -> None:
    """Copy a tile's `means` into the grid with their north-west pixel at (row, column), and mark
    them covered; a tile the box only meets is cut at the box's edge."""
    height, width = means.shape[:2]
    top, bottom = max(row, 0), min(row + height, pixels.shape[0])
    left, right = max(column, 0), min(column + width, pixels.shape[1])
    if top < bottom and left < right:
        pixels[top:bottom, left:right] = means[
            top - row : bottom - row, left - column : right - column
        ]
        covered[top:bottom, left:right] = True


def _block_means(source: np.ndarray, per_cell: int) -> np.ndarray:
    """Per channel `(sum + 12) // 25` of each 5 × 5 block of a tile's pixels, exact integers.

    `source` is a tile's rows × columns × 3 uint8 pixels, both sides `BLOCK` times `per_cell`;
    the blocks are counted from the tile's north-west corner.
    """
    sums = source.reshape(per_cell, BLOCK, per_cell, BLOCK, TILE_BANDS).sum(
        axis=(1, 3), dtype=np.int64
    )
    count = BLOCK * BLOCK
    return ((sums + count // 2) // count).astype(np.uint8)


def _far_bytes(path: Path, tile: str) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise _tile_error(tile, path, f"cannot read it: {exc}") from exc


def _check_tile(ds, tile: str, path: Path, resolution: int) -> tuple[int, int]:
    """Refuse a tile that is not where its id says; its west and north edges in metres."""
    e_km, n_km = (int(v) for v in TILE_ID.fullmatch(tile).groups())
    west, north = e_km * TILE_M, (n_km + 1) * TILE_M
    epsg = ds.crs.to_epsg() if ds.crs is not None else None
    if epsg != TILE_EPSG:
        raise _tile_error(tile, path, f"its CRS is {ds.crs}, expected EPSG:{TILE_EPSG}")
    side = TILE_M // resolution
    if (ds.width, ds.height, ds.count) != (side, side, TILE_BANDS):
        raise _tile_error(
            tile,
            path,
            f"it is {ds.width} × {ds.height} pixels in {ds.count} bands, expected "
            f"{side} × {side} in {TILE_BANDS}",
        )
    if any(dtype != "uint8" for dtype in ds.dtypes):
        raise _tile_error(tile, path, f"its pixels are {list(ds.dtypes)}, expected uint8")
    t = ds.transform
    if (t.a, t.b, t.c, t.d, t.e, t.f) != (
        float(resolution),
        0.0,
        west,
        0.0,
        -float(resolution),
        north,
    ):
        raise _tile_error(
            tile,
            path,
            f"its top-left corner is ({t.c}, {t.f}) with {t.a} × {-t.e} m pixels, its id says "
            f"({west}, {north}) with {resolution} m pixels",
        )
    return west, north


def _tile_error(tile: str, path: Path, message: str) -> FarColourError:
    return FarColourError(f"tile {tile}: {path}: {message}; `{DOWNLOAD_COMMAND}` fetches it again")


def _samples(
    plan: _Plan, entry: dict, folder: Path, listed: dict[str, dict], say: Progress
) -> np.ndarray:
    """The swissALTIRegio sample at every pixel centre, in whole centimetres (rows × columns).

    Each tile's bytes are hashed against the lock's and parsed by the heights step's parser, the
    very bytes hashed; a pixel centre no tile holds a sample for is refused naming the pixel.
    """
    e_min, _, _, n_max = plan.grid.box
    cell = plan.cell
    cents = np.zeros((plan.rows, plan.columns), dtype=np.int64)
    found = np.zeros((plan.rows, plan.columns), dtype=bool)
    try:
        for tile in plan.regio_tiles:
            path = folder / listed[tile]["file"]
            say(f"reading {path}")
            data = regio_tile_bytes(path, tile)
            actual = hashlib.sha256(data).hexdigest()
            if actual != entry["tiles"][tile]["sha256"]:
                raise FarColourError(
                    f"tile {tile}: {path} has SHA-256 {actual}, provenance.json and the lock pin "
                    f"{entry['tiles'][tile]['sha256']}; `{REGIO_DOWNLOAD_COMMAND}` fetches it again"
                )
            x, y, centimetres = regio_tile_samples(data, tile, path, plan.regio["resolution_m"])
            del data
            # a sample at (x, y) is pixel centre (row, column) when 2 (x − e_min) − cell is
            # 2 · cell · column and 2 (n_max − y) − cell is 2 · cell · row, exactly
            column, off_x = np.divmod(2 * (x - e_min) - cell, 2 * cell)
            row, off_y = np.divmod(2 * (n_max - y) - cell, 2 * cell)
            on = (
                (off_x == 0)
                & (off_y == 0)
                & (column >= 0)
                & (column < plan.columns)
                & (row >= 0)
                & (row < plan.rows)
            )
            cents[row[on], column[on]] = centimetres[on]
            found[row[on], column[on]] = True
    except SurroundingsError as exc:
        raise FarColourError(str(exc)) from exc
    missing = np.argwhere(~found)
    if len(missing):
        row, column = (int(v) for v in missing[0])
        raise FarColourError(
            f"pixel (row {row}, column {column}) at LV95 ({e_min + cell // 2 + cell * column}, "
            f"{n_max - cell // 2 - cell * row}) has no swissALTIRegio sample ({len(missing)} such "
            f"pixels); `{REGIO_DOWNLOAD_COMMAND}` fetches the tiles again"
        )
    return cents


def _fill(pixels: np.ndarray, covered: np.ndarray, cents: np.ndarray, band_m: int) -> None:
    """Colour the pixels that are not covered, in place (module docstring).

    The band of a pixel is `floor(cents / (100 · band_m))`, floor also below 0 m.
    """
    bands = cents // (100 * band_m)
    covered_bands = bands[covered]
    if covered_bands.size == 0:
        raise FarColourError(
            "no pixel is covered by a SWISSIMAGE tile, so there is no colour to fill the others with"
        )
    means = _band_means(covered_bands, pixels[covered])
    filled = ~covered
    wanted, inverse = np.unique(bands[filled], return_inverse=True)
    palette = np.array(
        [means[_donor_band(int(band), sorted(means))] for band in wanted], dtype=np.uint8
    ).reshape(len(wanted), TILE_BANDS)
    pixels[filled] = palette[inverse]


def _band_means(bands: np.ndarray, rgb: np.ndarray) -> dict[int, np.ndarray]:
    """The half-up integer mean `(total + n // 2) // n` per channel of each band's pixels.

    `bands` holds the band of each covered pixel and `rgb` its colour (n × 3, uint8). The totals
    are 64-bit integers: a band of 255s over 300 pixels is already above what 16 bits hold.
    """
    means = {}
    for band in np.unique(bands).tolist():
        chosen = rgb[bands == band]
        count = len(chosen)
        total = chosen.sum(axis=0, dtype=np.int64)
        means[band] = ((total + count // 2) // count).astype(np.uint8)
    return means


def _donor_band(band: int, with_colour: list[int]) -> int:
    """The band whose mean colours a filled pixel of `band`: itself when it holds a covered pixel,
    else the nearest band below that does, and only if none below does, the nearest above.

    `with_colour` is the sorted, non-empty list of the bands that hold a covered pixel.
    """
    if band in with_colour:
        return band
    below = [other for other in with_colour if other < band]
    if below:
        return below[-1]
    return next(other for other in with_colour if other > band)


def _decoder() -> str:
    """The decoder behind the tiles' pixels, as the pixels' refusal names it."""
    return f"rasterio {rasterio.__version__}, GDAL {rasterio.__gdal_version__}"


def _source(far: dict) -> dict:
    """The description's `colour_source`: the datasets config's credit and pinned edition."""
    return {
        "attribution": far["attribution"],
        "collection": far["collection"],
        "dataset": DATASET,
        "edition": far["edition"],
    }


def _write_files(out_dir: Path | str, area: str, data: bytes, block: dict) -> int:
    """Write the JPEG, its `.import` and the description, each through a `.part` rename.

    Then remove every `*.part` in `surroundings/`, the files of a run cut short between a write
    and its rename, which an export would ship; only this folder is cleaned and nothing else in
    it is touched. Returns how many parts were removed.
    """
    folder = Path(out_dir) / "surroundings"
    folder.mkdir(parents=True, exist_ok=True)
    jpeg = folder / f"{area}_colour.jpg"
    _replace(jpeg, data)
    _replace(jpeg.with_name(jpeg.name + ".import"), KEEP_IMPORT)
    _replace(folder / f"{area}_colour.json", _json_bytes(block))
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
