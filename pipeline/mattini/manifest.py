"""The generated manifest: the game's only source of generated data (docs/SPEC.md §8).

Its top level is exactly `buildings`, `schema`, `terrain`, `world` and `world_sha256`. Its
`world` block is config/world.json verbatim, with the SHA-256 of the file's bytes, so
the game learns the origin and axes only from here (Hard Rule 4). Its `terrain` block is
the description the terrain step wrote next to the heights file, copied verbatim, or null
when no terrain is built. A built terrain is refused, naming `python -m mattini terrain`,
and nothing is written, when it no longer matches the world config, the spacing, its
heights file, the heights design expects for the spacing (config/terrain.json), the
datasets config's attribution, collection, edition and resolution, or the tiles the lock
pins (briefs M1-03, M2-01). Its `buildings` block is, likewise, the description the
buildings step wrote next to the chunk files, or null when none is built in this folder
for the terrain config's area; built buildings that no longer match the world config (its
box too, M2-07), the datasets config, the sheets the lock pins, their chunk files or the
chunks design expects (config/buildings.json) are refused, naming `python -m mattini
buildings`, and nothing is written (brief M2-04). For a block that is built, the expected
values' `computed_for` is compared first with the world config and, when the lock fits
the datasets config, with the lock's entry: a difference names design's step instead,
since a rebuild would be refused too (brief M2-07). Written deterministically: sorted
keys, fixed formatting, LF line endings, no times, no absolute paths (Hard Rule 5).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mattini.buildings import (
    BUILDINGS_CONFIG_PATH,
    built_buildings_block,
    load_buildings_config,
)
from mattini.datasets import DEFAULT_PATH as DATASETS_PATH
from mattini.datasets import load_datasets
from mattini.lock import LOCK_PATH
from mattini.terrain import TERRAIN_CONFIG_PATH, built_terrain_block, load_terrain_config
from mattini.world import DEFAULT_PATH, REPO, parse_world, read_config_bytes

SCHEMA = 1
DEFAULT_OUT = REPO / "game" / "assets" / "generated"
FILENAME = "manifest.json"


def build_manifest(
    config_path: Path = DEFAULT_PATH,
    out_dir: Path | str = DEFAULT_OUT,
    *,
    terrain_config_path: Path | str = TERRAIN_CONFIG_PATH,
    datasets_path: Path | str = DATASETS_PATH,
    lock_path: Path | str = LOCK_PATH,
    buildings_config_path: Path | str = BUILDINGS_CONFIG_PATH,
) -> dict:
    """The manifest's contents; refuses a world config the loader refuses, stale terrain or
    stale buildings. The lock is read only when a terrain or buildings are built."""
    config_path = Path(config_path)
    raw = read_config_bytes(config_path)
    world = parse_world(raw, config_path)
    world_sha256 = hashlib.sha256(raw).hexdigest()
    terrain_config = load_terrain_config(terrain_config_path)
    datasets = load_datasets(datasets_path)
    terrain = built_terrain_block(
        out_dir, terrain_config, world, world_sha256, datasets, lock_path=lock_path
    )
    buildings = built_buildings_block(
        out_dir,
        load_buildings_config(buildings_config_path),
        terrain_config,
        world,
        world_sha256,
        datasets,
        lock_path,
    )
    return {
        "buildings": buildings,
        "schema": SCHEMA,
        "terrain": terrain,
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
) -> Path:
    """Write `<out_dir>/manifest.json` and return its path; a refusal writes nothing."""
    out_dir = Path(out_dir)
    manifest = build_manifest(
        config_path,
        out_dir,
        terrain_config_path=terrain_config_path,
        datasets_path=datasets_path,
        lock_path=lock_path,
        buildings_config_path=buildings_config_path,
    )
    text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / FILENAME
    path.write_bytes((text + "\n").encode("utf-8"))
    return path
