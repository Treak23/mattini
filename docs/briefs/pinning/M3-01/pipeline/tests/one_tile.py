"""A one-tile terrain world laid out as the owner's commands leave it (brief M3-01's pins).

The tile is 2601-1199 (E 2'601'000-2'602'000, N 1'199'000-1'200'000): a synthetic 0.5 m
GeoTIFF, every pixel 1600 m. The world's area `probe` is 4 m x 4 m inside it, at 2 m
spacing (3 x 3 vertices), with a height offset of 1000 m, so every vertex is 600 m: the
expected heights' SHA-256 is that of nine float32 600.0, computed here without any of the
pipeline's code. The lock, provenance.json and terrain config are laid out as `lock
terrain`, `download terrain` and design leave them, and the config records this world and
this lock as what its value was computed for (SPEC §8, computed_for). Small and quick: the
tile is deflated on disk, and the step resamples nine vertices.

Does NOT prove: anything about the heights' resampling (a flat tile hides it; the shared
fixtures and design's expected values pin that).
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

TILE = "2601-1199"
WEST, SOUTH = 2601000.0, 1199000.0
NAME = f"swissalti3d_2024_{TILE}_0.5_2056_5728.tif"
AREA = "probe"
BOX = {"e_min": 2601100.0, "e_max": 2601104.0, "n_min": 1199100.0, "n_max": 1199104.0}
HEIGHT_M = 1600.0
OFFSET_M = 1000.0
ALTI = {
    "collection": "ch.swisstopo.swissalti3d",
    "edition": "2024",
    "resolution_m": 0.5,
    "attribution": "© swisstopo",
}
HEIGHTS_SHA256 = hashlib.sha256(
    np.full((3, 3), HEIGHT_M - OFFSET_M, dtype="<f4").tobytes()
).hexdigest()


def canonical_sha256(entry: dict) -> str:
    """A lock entry's SHA-256 in the canonical form SPEC §8 names, computed here."""
    text = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_tile(path: Path, height_m: float = HEIGHT_M) -> str:
    """Write the tile, every pixel `height_m`, and return its SHA-256."""
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": 2000,
        "height": 2000,
        "count": 1,
        "crs": "EPSG:2056",
        "transform": from_origin(WEST, SOUTH + 1000.0, 0.5, 0.5),
        "nodata": -9999.0,
        "compress": "deflate",
    }
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(np.full((2000, 2000), height_m, dtype=np.float32), 1)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_world(folder: Path, change=lambda data: None) -> Path:
    """The one-tile world config, changed by `change`, as `<folder>/world.json`."""
    data = {
        "schema": 1,
        "crs": {"horizontal": "EPSG:2056", "vertical": "EPSG:5728"},
        "origin_lv95": {"e": WEST, "n": SOUTH},
        "height_offset_m": OFFSET_M,
        "axes": {"x": "+e", "y": "+h", "z": "-n"},
        "areas": {AREA: dict(BOX)},
    }
    change(data)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def relay(case: dict, sha256: str) -> None:
    """Pin the tile with `sha256` in the case's lock and provenance.json, as `lock terrain`
    and `download terrain` leave them after a republish; the terrain config is untouched."""
    case["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"] = sha256
    provenance = case["raw_dir"] / "provenance.json"
    data = json.loads(provenance.read_text(encoding="utf-8"))
    data["tiles"][0]["sha256"] = sha256
    provenance.write_text(json.dumps(data, indent=2), encoding="utf-8")


def one_tile_case(tmp_path: Path) -> dict:
    """The world, datasets, lock, terrain config and raw folder of the one-tile world."""
    raw_root = tmp_path / "raw"
    raw_dir = raw_root / "swissalti3d" / "2024"
    raw_dir.mkdir(parents=True)
    sha256 = write_tile(raw_dir / NAME)
    provenance = {
        "attribution": ALTI["attribution"],
        "collection": ALTI["collection"],
        "dataset": "swissalti3d",
        "edition": ALTI["edition"],
        "resolution_m": ALTI["resolution_m"],
        "schema": 1,
        "tiles": [{"file": NAME, "sha256": sha256, "tile": TILE}],
    }
    (raw_dir / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    entry = {
        "collection": ALTI["collection"],
        "edition": ALTI["edition"],
        "resolution_m": ALTI["resolution_m"],
        "tiles": {TILE: {"file": NAME, "sha256": sha256}},
    }
    world_path = write_world(tmp_path / "config")
    config = {
        "schema": 1,
        "areas": {
            AREA: {
                "computed_for": {
                    "inputs_sha256": canonical_sha256(entry),
                    "world_sha256": hashlib.sha256(world_path.read_bytes()).hexdigest(),
                },
                "expected_sha256": {"2": HEIGHTS_SHA256},
                "spacing_m": 2.0,
            }
        },
    }
    return {
        "tmp": tmp_path,
        "world_path": world_path,
        "datasets": {"swissalti3d": dict(ALTI)},
        "lock": {"schema": 1, "datasets": {"swissalti3d": entry}},
        "config": config,
        "raw_root": raw_root,
        "raw_dir": raw_dir,
        "tile_path": raw_dir / NAME,
        "out": tmp_path / "generated",
    }
