"""The roofs fixture's buildings with a noise photo, laid out as the downloads leave it (M3-05).

The roofs step reads a zipped FileGDB per map sheet and a GeoTIFF per 1 km tile. A FileGDB
that fiona writes does not give back the triangles it was given (brief M2-04's Findings), so
the sheet file here is the fixture's own `source.json`, as the fixture's lock pins it, and the
tests replace the step's `read_sheet` with `fake_read_sheet`, which reads that JSON; the
step's own reading of a FileGDB is the real run's. The photo is noise: random pixels over the
area grown by 60 m (so that the buildings that straddle the area's edge have pixels outside
it, as the real tiles have), written as four sparse 10000 × 10000 GeoTIFFs, read by the step
for real. Design's `.u8` windows are not used for the photo: a window's missing pixels are no
photo, while a tile's are zeros, so a roof that reaches outside the windows would count
differently.

What the step must produce is not copied from the step: the buildings' order, tiles and
counts are design's (`generated/roofs/fixture.json`), their roof colours and pixel counts are
those of `roofs_oracle.oracle` over the noise, and the description's bytes are assembled here
(`canonical`).
"""

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.windows import Window
from roofs_oracle import oracle
from synthetic_sheets import raw_folder

from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
FIXTURE = SHARED / "roofs_fixture"
GENERATED = FIXTURE / "generated"
WORLD_PATH = SHARED / "buildings_fixture" / "world.json"
TERRAIN_PATH = SHARED / "buildings_fixture" / "terrain.json"
AREA = "fixture"
SHEET = "1249-42"
TILES = ["2650-1149", "2650-1150", "2651-1149", "2651-1150"]
GROWN_DM = 600  # the noise reaches 60 m beyond the area on every side


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def features_of(data: bytes) -> list[dict]:
    """The features of the fixture's sheet file (`source.json`), as the reader hands them."""
    return [
        {
            "uuid": f["uuid"],
            "objektart": f["objektart"],
            "triangles": [tuple(tuple(p) for p in t) for t in f["triangles"]],
        }
        for f in json.loads(data.decode("utf-8"))["features"]
    ]


def fixture_features() -> list[dict]:
    return features_of((FIXTURE / "source.json").read_bytes())


def fake_read_sheet(data: bytes, sheet: str) -> list[dict]:
    """What the step's `read_sheet` gives for this fixture's sheet: its features, from the
    bytes the step hashed."""
    assert sheet == SHEET
    return features_of(data)


def design_chunks() -> list[dict]:
    return _json(GENERATED / "roofs" / "fixture.json")["chunks"]


def canonical(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def two_entries_sha256(lock: dict) -> str:
    """`computed_for.inputs_sha256` of the roofs step, computed here (lesson 34): the SHA-256
    of the canonical object of the two lock entries."""
    text = json.dumps(
        {name: lock["datasets"][name] for name in ("swissbuildings3d", "swissimage")},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def noise(world) -> tuple[int, int, np.ndarray]:
    """The photo: (west_dm, north_dm, pixels) of random pixels over the area grown by 60 m."""
    e_min, e_max, n_min, n_max = world.area(AREA)
    west_dm, north_dm = round(e_min * 10) - GROWN_DM, round(n_max * 10) + GROWN_DM
    columns = round((e_max - e_min) * 10) + 2 * GROWN_DM
    rows = round((n_max - n_min) * 10) + 2 * GROWN_DM
    pixels = np.random.RandomState(20261015).randint(0, 256, size=(rows, columns, 3))
    return west_dm, north_dm, pixels.astype(np.uint8)


def _write_tile(path: Path, tile: str, raster: tuple[int, int, np.ndarray]) -> None:
    """A sparse tile GeoTIFF holding the part of `raster` that lies in it."""
    e_km, n_km = (int(v) for v in tile.split("-"))
    west_dm, north_dm = e_km * 10000, (n_km + 1) * 10000
    r_west, r_north, pixels = raster
    left, right = max(west_dm, r_west), min(west_dm + 10000, r_west + pixels.shape[1])
    top, bottom = min(north_dm, r_north), max(north_dm - 10000, r_north - pixels.shape[0])
    assert left < right and bottom < top, f"the noise must reach the tile {tile}"
    profile = {
        "driver": "GTiff",
        "dtype": "uint8",
        "width": 10000,
        "height": 10000,
        "count": 3,
        "crs": "EPSG:2056",
        "transform": Affine(0.1, 0.0, e_km * 1000.0, 0.0, -0.1, (n_km + 1) * 1000.0),
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "compress": "deflate",
        "sparse_ok": True,
    }
    part = pixels[r_north - top : r_north - bottom, left - r_west : right - r_west]
    with rasterio.open(path, "w", **profile) as ds:
        ds.write(
            part.transpose(2, 0, 1),
            window=Window(left - west_dm, north_dm - top, right - left, top - bottom),
        )


def make_inputs(root: Path) -> dict:
    """Write the fixture's sheet and the noise tiles under `<root>/raw/` as the downloads leave
    them, and return what the step needs (world, datasets, terrain config, lock with both
    entries, config) and what it must produce (`block`, `data`, `expected_roofs`)."""
    datasets = _json(FIXTURE / "datasets.json")["datasets"]
    raw_root = root / "raw"
    lock = raw_folder(raw_root, datasets, {SHEET: (FIXTURE / "source.json").read_bytes()})
    world = load_world(WORLD_PATH)
    raster = noise(world)
    tiles_dir = raw_root / "swissimage" / "2023"
    tiles_dir.mkdir(parents=True)
    entries, locked = [], {}
    for tile in TILES:
        name = f"swissimage-dop10_2023_{tile}_0.1_2056.tif"
        path = tiles_dir / name
        _write_tile(path, tile, raster)
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append(
            {
                "file": name,
                "item": f"swissimage-dop10_2023_{tile}",
                "sha256": sha256,
                "size_bytes": path.stat().st_size,
                "tile": tile,
                "url": f"https://example.invalid/{name}",
            }
        )
        locked[tile] = {"file": name, "sha256": sha256}
    swissimage = datasets["swissimage"]
    (tiles_dir / "provenance.json").write_text(
        json.dumps(
            {
                "attribution": swissimage["attribution"],
                "collection": swissimage["collection"],
                "dataset": "swissimage",
                "edition": swissimage["edition"],
                "resolution_m": swissimage["resolution_m"],
                "schema": 1,
                "tiles": entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    lock["datasets"]["swissimage"] = {
        "collection": swissimage["collection"],
        "edition": swissimage["edition"],
        "resolution_m": swissimage["resolution_m"],
        "tiles": locked,
    }
    world_sha256 = hashlib.sha256(WORLD_PATH.read_bytes()).hexdigest()
    buildings = datasets["swissbuildings3d"]
    sheet = lock["datasets"]["swissbuildings3d"]["sheets"][SHEET]
    source = {
        "buildings": {
            "attribution": buildings["attribution"],
            "collection": buildings["collection"],
            "dataset": "swissbuildings3d",
            "edition": buildings["edition"],
            "sheets": [{"sha256": sheet["sha256"], "sheet": SHEET}],
        },
        "photo": {
            "attribution": swissimage["attribution"],
            "collection": swissimage["collection"],
            "dataset": "swissimage",
            "edition": swissimage["edition"],
            "resolution_m": swissimage["resolution_m"],
            "tiles": [{"sha256": locked[t]["sha256"], "tile": t} for t in TILES],
        },
    }
    expected = oracle(fixture_features(), [raster])
    chunks = copy.deepcopy(design_chunks())
    for chunk in chunks:
        for building in chunk["buildings"]:
            building["roof"], building["roof_pixels"] = expected[building["uuid"]]
    block = {
        "area": AREA,
        "chunks": chunks,
        "format": "roofs-v1",
        "lv95_box": dict(zip(("e_min", "e_max", "n_min", "n_max"), world.area(AREA), strict=True)),
        "source": source,
        "world_sha256": world_sha256,
    }
    data = canonical(block)
    config = {
        "schema": 1,
        "areas": {
            AREA: {
                "computed_for": {
                    "inputs_sha256": two_entries_sha256(lock),
                    "world_sha256": world_sha256,
                },
                "expected_sha256": hashlib.sha256(data).hexdigest(),
            }
        },
    }
    return {
        "world": world,
        "world_sha256": world_sha256,
        "datasets": datasets,
        "terrain": _json(TERRAIN_PATH),
        "lock": lock,
        "config": config,
        "raw_root": raw_root,
        "block": block,
        "data": data,
        "expected_roofs": expected,
    }
