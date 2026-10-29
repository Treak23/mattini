"""The generated manifest: the game's only source of generated data (docs/SPEC.md §8).

Its top level is exactly `buildings`, `photo`, `roofs`, `schema`, `sky`, `surfaces`,
`terrain`, `trees`, `world` and `world_sha256`. Its `world` block is config/world.json verbatim, with
the SHA-256 of the file's bytes, so the game learns the origin and axes only from here (Hard
Rule 4). Every other block is the description its step wrote next to its files, copied
verbatim, or null when that step has not been run in this folder (brief M3-13): a block is
never left out and never an empty object. The file is written through a `.part` rename, so a
cut write never leaves the game a manifest it refuses as JSON.

Its `terrain` block is the description the terrain step wrote next to the heights file. A
built terrain is refused, naming `python -m mattini terrain`, and nothing is written, when
it no longer matches the world config, the spacing, a box, columns or rows that are not the
world config's area at the spacing, its heights file, the heights design expects for the
spacing (config/terrain.json), the datasets config's attribution, collection, edition and
resolution, or the tiles the lock pins (briefs M1-03, M2-01, M2-06). Its `buildings` block
is, likewise, the description the buildings step wrote next to the chunk files, or null when
none is built in this folder for the terrain config's area; built buildings that no longer
match the world config (its box too, M2-07), the datasets config, the sheets the lock pins,
their chunk files or the chunks design expects (config/buildings.json) are refused, naming
`python -m mattini buildings`, and nothing is written (brief M2-04). The `photo` and
`surfaces` blocks are those steps' descriptions for the area their own config names
(config/photo.json, config/surfaces.json), the `roofs` and `trees` blocks for the terrain
config's area (briefs M3-04 to M3-07, M3-13). The `sky` block (brief v0.4.0-07) has no lock: it is
checked world, then area, then block, by `sky.built_sky_block`. Every step config is loaded and checked even
when its step has not run.

For a block that is built, the checks come in the steps' own order (briefs M3-01, M3-13).
For the terrain and the buildings it is the steps': the expected values' `computed_for` is
compared with the world config first; then the lock must fit the datasets config and the
area exactly (`lock.fit_problem`), or the manifest is refused naming `python -m mattini
lock <x>` and no other command; then `computed_for` is compared with the lock's entry, and
a difference names design's step instead, since a rebuild would be refused too (brief
M2-07); only then is the block itself checked. For the four new blocks this module makes
those checks itself, in the same order whatever the steps' block functions check, the
refusal in the step's error class:

1. `computed_for.world_sha256` against config/world.json (design's step);
2. the lock's fit for every dataset the step reads, in sorted order, through
   `lock.fit_problem` (a refusal naming that dataset's lock command and no other);
3. `computed_for.inputs_sha256` against the lock's entries (`lock.entry_sha256` for one
   dataset, `lock.entries_sha256` for several; design's step);
4. roofs only: built roofs without built buildings are refused, naming
   `python -m mattini buildings`;
5. the step's own check of the block.

Written deterministically: sorted keys, fixed formatting, LF line endings, no times, no
absolute paths (Hard Rule 5).
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

from mattini.buildings import (
    BUILDINGS_CONFIG_PATH,
    built_buildings_block,
    load_buildings_config,
)
from mattini.datasets import DEFAULT_PATH as DATASETS_PATH
from mattini.datasets import load_datasets
from mattini.download import BUILDINGS, DATASET, PHOTO, SURFACE, TLM, DownloadError
from mattini.lock import LOCK_PATH, entries_sha256, fit_problem, load_lock
from mattini.photo import (
    PHOTO_CONFIG_NAME,
    PHOTO_CONFIG_PATH,
    PhotoError,
    built_photo_block,
    load_photo_config,
)
from mattini.roofs import (
    BUILDINGS_COMMAND,
    ROOFS_CONFIG_NAME,
    ROOFS_CONFIG_PATH,
    RoofsError,
    built_roofs_block,
    load_roofs_config,
)
from mattini.sky import SKY_CONFIG_PATH, built_sky_block, load_sky_config
from mattini.surfaces import (
    SURFACES_CONFIG_NAME,
    SURFACES_CONFIG_PATH,
    SurfacesError,
    built_surfaces_block,
    load_surfaces_config,
)
from mattini.terrain import (
    TERRAIN_CONFIG_PATH,
    built_terrain_block,
    configured_area,
    inputs_refusal,
    load_terrain_config,
    world_refusal,
)
from mattini.trees import (
    TREES_CONFIG_NAME,
    TREES_CONFIG_PATH,
    TreesError,
    built_trees_block,
    load_trees_config,
)
from mattini.world import DEFAULT_PATH, REPO, World, parse_world, read_config_bytes

SCHEMA = 1
DEFAULT_OUT = REPO / "game" / "assets" / "generated"
FILENAME = "manifest.json"


@dataclass(frozen=True)
class _Step:
    """What the manifest asks of a built block before the step's own check of it."""

    key: str  # the manifest's block, the step's folder under the output and its command
    config_name: str  # the home of the expected values, for messages
    names: tuple[str, ...]  # the lock's datasets the step reads, in sorted order
    error: type[ValueError]  # the step's error class, which the command line catches


_PHOTO = _Step("photo", PHOTO_CONFIG_NAME, (PHOTO,), PhotoError)
_ROOFS = _Step("roofs", ROOFS_CONFIG_NAME, tuple(sorted((BUILDINGS, PHOTO))), RoofsError)
_SURFACES = _Step("surfaces", SURFACES_CONFIG_NAME, (TLM,), SurfacesError)
_TREES = _Step(
    "trees", TREES_CONFIG_NAME, tuple(sorted((DATASET, BUILDINGS, SURFACE, TLM))), TreesError
)


def build_manifest(
    config_path: Path = DEFAULT_PATH,
    out_dir: Path | str = DEFAULT_OUT,
    *,
    terrain_config_path: Path | str = TERRAIN_CONFIG_PATH,
    datasets_path: Path | str = DATASETS_PATH,
    lock_path: Path | str = LOCK_PATH,
    buildings_config_path: Path | str = BUILDINGS_CONFIG_PATH,
    photo_config_path: Path | str = PHOTO_CONFIG_PATH,
    roofs_config_path: Path | str = ROOFS_CONFIG_PATH,
    surfaces_config_path: Path | str = SURFACES_CONFIG_PATH,
    trees_config_path: Path | str = TREES_CONFIG_PATH,
    sky_config_path: Path | str = SKY_CONFIG_PATH,
) -> dict:
    """The manifest's contents; refuses a world config the loader refuses and any built block
    that no longer matches. The lock is read only when a block is built."""
    config_path = Path(config_path)
    raw = read_config_bytes(config_path)
    world = parse_world(raw, config_path)
    world_sha256 = hashlib.sha256(raw).hexdigest()
    terrain_config = load_terrain_config(terrain_config_path)
    datasets = load_datasets(datasets_path)
    buildings_config = load_buildings_config(buildings_config_path)
    photo_config = load_photo_config(photo_config_path)
    roofs_config = load_roofs_config(roofs_config_path)
    surfaces_config = load_surfaces_config(surfaces_config_path)
    trees_config = load_trees_config(trees_config_path)
    sky_config = load_sky_config(sky_config_path)

    @functools.cache
    def lock() -> dict:
        return load_lock(lock_path)

    def checked(step: _Step, area: str, config: dict) -> bool:
        """True when the step's description is built in `out_dir` and passed steps 1 to 3."""
        if not (Path(out_dir) / step.key / f"{area}.json").exists():
            return False
        settings = config["areas"].get(area)
        if settings is not None:  # a config for another area is refused by the step's own check
            _inputs_check(step, area, settings["computed_for"], world, world_sha256, datasets, lock)
        return True

    terrain = built_terrain_block(
        out_dir, terrain_config, world, world_sha256, datasets, lock_path=lock_path
    )
    buildings = built_buildings_block(
        out_dir, buildings_config, terrain_config, world, world_sha256, datasets, lock_path
    )
    area = configured_area(photo_config)
    photo = (
        built_photo_block(out_dir, photo_config, world, world_sha256, datasets, lock())
        if checked(_PHOTO, area, photo_config)
        else None
    )
    area = configured_area(terrain_config)
    roofs = None
    if checked(_ROOFS, area, roofs_config):
        if buildings is None:
            raise RoofsError(
                f"{Path(out_dir) / 'roofs' / f'{area}.json'}: roof colours are built, but no "
                f"buildings are: they are colours of buildings' roofs; `{BUILDINGS_COMMAND}` "
                f"builds the buildings first"
            )
        roofs = built_roofs_block(
            out_dir,
            roofs_config,
            terrain_config,
            world,
            world_sha256,
            datasets,
            lock(),
            buildings,
        )
    area = configured_area(surfaces_config)
    surfaces = (
        built_surfaces_block(out_dir, surfaces_config, world, world_sha256, datasets, lock())
        if checked(_SURFACES, area, surfaces_config)
        else None
    )
    area = configured_area(terrain_config)
    trees = (
        built_trees_block(
            out_dir, trees_config, terrain_config, world, world_sha256, datasets, lock()
        )
        if checked(_TREES, area, trees_config)
        else None
    )
    return {
        "buildings": buildings,
        "photo": photo,
        "roofs": roofs,
        "schema": SCHEMA,
        "sky": built_sky_block(out_dir, sky_config, world, world_sha256),
        "surfaces": surfaces,
        "terrain": terrain,
        "trees": trees,
        "world": json.loads(raw.decode("utf-8")),
        "world_sha256": world_sha256,
    }


def write_manifest(
    out_dir: Path | str = DEFAULT_OUT,
    config_path: Path = DEFAULT_PATH,
    *,
    terrain_config_path: Path | str = TERRAIN_CONFIG_PATH,
    datasets_path: Path | str = DATASETS_PATH,
    lock_path: Path | str = LOCK_PATH,
    buildings_config_path: Path | str = BUILDINGS_CONFIG_PATH,
    photo_config_path: Path | str = PHOTO_CONFIG_PATH,
    roofs_config_path: Path | str = ROOFS_CONFIG_PATH,
    surfaces_config_path: Path | str = SURFACES_CONFIG_PATH,
    trees_config_path: Path | str = TREES_CONFIG_PATH,
    sky_config_path: Path | str = SKY_CONFIG_PATH,
) -> Path:
    """Write `<out_dir>/manifest.json` and return its path; a refusal writes nothing.

    The file is written to `manifest.json.part` and renamed, so a write cut short leaves
    the previous manifest, or none, never half of one.
    """
    out_dir = Path(out_dir)
    manifest = build_manifest(
        config_path,
        out_dir,
        terrain_config_path=terrain_config_path,
        datasets_path=datasets_path,
        lock_path=lock_path,
        buildings_config_path=buildings_config_path,
        photo_config_path=photo_config_path,
        roofs_config_path=roofs_config_path,
        surfaces_config_path=surfaces_config_path,
        trees_config_path=trees_config_path,
        sky_config_path=sky_config_path,
    )
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / FILENAME
    part = path.with_name(path.name + ".part")
    part.write_bytes((text + "\n").encode("utf-8"))
    os.replace(part, path)
    return path


def _inputs_check(
    step: _Step,
    area: str,
    computed_for: dict,
    world: World,
    world_sha256: str,
    datasets: dict,
    lock,
) -> None:
    """Steps 1 to 3 of a built new block, in the module docstring's order; raises `step.error`.

    `lock` is the function that reads the lock, so that no lock is read when the world is
    already refused. A world config without the area has no lock to fit: the step's own check
    of the block refuses it.
    """
    problem = world_refusal(step.config_name, computed_for, world_sha256)
    if problem:
        raise step.error(f"area {area!r}: {problem}")
    if area not in world.areas:
        return
    for name in step.names:
        try:
            problem = fit_problem(lock(), datasets, world, area, name)
        except DownloadError as exc:  # a datasets config without the dataset
            raise step.error(str(exc)) from exc
        if problem:
            raise step.error(problem)
    problem = _inputs_refusal(step, computed_for, lock())
    if problem:
        raise step.error(f"area {area!r}: {problem}")


def _inputs_refusal(step: _Step, computed_for: dict, lock: dict) -> str | None:
    """Why the expected values do not hold for the lock's entries of the step's datasets, or
    None: `lock.entry_sha256` for one dataset (`terrain.inputs_refusal`), `lock.entries_sha256`
    for several. Both name design's step, never a command."""
    if len(step.names) == 1:
        (name,) = step.names
        return inputs_refusal(step.config_name, computed_for, name, lock["datasets"][name])
    recorded, current = computed_for["inputs_sha256"], entries_sha256(lock, step.names)
    if recorded == current:
        return None
    return (
        f"the expected values in {step.config_name} were computed from the lock entries of "
        f"{', '.join(step.names)} with SHA-256 {recorded}; config/datasets.lock.json's entries "
        f"now have {current} (a new edition or an adopted republished file). Adopting new "
        f"inputs is a design change: design recomputes the expected values (docs/SPEC.md §5, §8)"
    )
