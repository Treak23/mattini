"""SWISSIMAGE's 2 m tiles as swisstopo publishes them, scaled down, for the pins of brief v0.6.0-06.

The live form (design §0, measured on all 1220 village tiles, 2026-11-02): one GeoTIFF per 1 km
cell, `swissimage-dop10_2023_<E km>-<N km>_2_2056.tif`, 500 × 500 pixels of 2 m, three uint8
bands (R, G, B), EPSG:2056, the top-left corner on the km grid at (E km · 1000, (N km + 1) · 1000),
no nodata; inside, JPEG-in-COG. `download farphoto` (brief v0.6.0-05) puts them in
`<raw>/swissimage_far/<edition>/` beside a provenance.json {absent, attribution, collection,
dataset, edition, resolution_m, schema 1, tiles [{file, item, sha256, size_bytes, tile, url}]}.

The fixture (tests/shared/farcolour_fixture/) keeps its 20 m source pixels in `photo.u8`, since no
`.tif` may be committed (test_repo_hygiene.py), and its lock pins the GeoTIFFs this module writes
from them: a plain strip TIFF (uncompressed, one strip, little-endian) with the three GeoTIFF tags
(ModelPixelScale, ModelTiepoint, a GeoKeyDirectory naming EPSG:2056), written byte by byte here, so
the bytes, and with them the lock and `computed_for`, are the same on every machine (no GDAL or
zlib build enters them, brain.md H27). At the fixture's 20 m a tile is 50 × 50 pixels; the step
reads it as it reads the live 500 × 500.

`raw_farphoto(root)` writes `download farphoto`'s layout for the fixture's covered cells and
returns the lock entry; `raw_inputs(root)` writes both downloads (swissALTIRegio's through
synthetic_regio.raw_regio from the fixture's `regio` source) and returns (root, lock).
"""

import copy
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
from synthetic_regio import raw_regio

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "farcolour_fixture"
DATASET = "swissimage_far"
TILE_M = 1000
URL = "https://data.geo.admin.ch/ch.swisstopo.swissimage-dop10/{item}/{file}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(name: str) -> dict:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def fixture_source() -> dict:
    return load("source.json")


def fixture_datasets() -> dict:
    return load("datasets.json")["datasets"]


def fixture_photo(source: dict | None = None) -> np.ndarray:
    """photo.u8 as a (rows, columns, 3) uint8 array, rows north to south; its SHA-256 checked."""
    photo = (source or fixture_source())["photo"]
    data = (FIXTURE / "photo.u8").read_bytes()
    assert sha256(data) == photo["sha256"], "photo.u8 is not the fixture's"
    return np.frombuffer(data, dtype=np.uint8).reshape(photo["rows"], photo["columns"], 3)


def item_of(cell: str, edition: str) -> str:
    return f"swissimage-dop10_{edition}_{cell}"


def far_name(cell: str, edition: str, resolution_m: int) -> str:
    return f"{item_of(cell, edition)}_{resolution_m}_2056.tif"


def geotiff(
    pixels: np.ndarray,
    west: float,
    north: float,
    resolution_m: float,
    *,
    epsg: int = 2056,
    dtype_bits: int = 8,
) -> bytes:
    """A plain strip GeoTIFF of `pixels` (rows × columns × bands, uint8), top-left at (west, north).

    `epsg` and `dtype_bits` exist for the refusal cases (another CRS; 16-bit samples).
    """
    rows, columns, bands = pixels.shape
    if dtype_bits == 16:
        data = np.ascontiguousarray(pixels, dtype="<u2").tobytes()
    else:
        data = np.ascontiguousarray(pixels, dtype=np.uint8).tobytes()
    entries = []

    def add(tag: int, kind: int, fmt: str, values) -> None:
        entries.append((tag, kind, len(values), struct.pack(f"<{len(values)}{fmt}", *values)))

    add(256, 3, "H", [columns])  # ImageWidth
    add(257, 3, "H", [rows])  # ImageLength
    add(258, 3, "H", [dtype_bits] * bands)  # BitsPerSample
    add(259, 3, "H", [1])  # Compression: none
    add(262, 3, "H", [2 if bands == 3 else 1])  # Photometric: RGB
    add(273, 4, "I", [0])  # StripOffsets, patched below
    add(277, 3, "H", [bands])  # SamplesPerPixel
    add(278, 3, "H", [rows])  # RowsPerStrip
    add(279, 4, "I", [len(data)])  # StripByteCounts
    add(284, 3, "H", [1])  # PlanarConfiguration: chunky
    add(339, 3, "H", [1] * bands)  # SampleFormat: unsigned
    add(33550, 12, "d", [float(resolution_m), float(resolution_m), 0.0])  # ModelPixelScale
    add(33922, 12, "d", [0.0, 0.0, 0.0, float(west), float(north), 0.0])  # ModelTiepoint
    add(34735, 3, "H", [1, 1, 0, 3, 1024, 0, 1, 1, 1025, 0, 1, 1, 3072, 0, 1, epsg])
    entries.sort()
    extra_at = 8 + 2 + 12 * len(entries) + 4
    fields, extra, strip_field = b"", b"", None
    for tag, kind, count, payload in entries:
        if len(payload) <= 4:
            if tag == 273:
                strip_field = len(fields)
            fields += struct.pack("<HHI", tag, kind, count) + payload.ljust(4, b"\0")
        else:
            fields += struct.pack("<HHII", tag, kind, count, extra_at + len(extra))
            extra += payload
            extra += b"\0" * (len(extra) % 2)
    data_at = extra_at + len(extra)
    fields = fields[: strip_field + 8] + struct.pack("<I", data_at) + fields[strip_field + 12 :]
    head = b"II" + struct.pack("<HI", 42, 8)
    return head + struct.pack("<H", len(entries)) + fields + struct.pack("<I", 0) + extra + data


def tile_pixels(photo: np.ndarray, source: dict, cell: str) -> np.ndarray:
    """The cell's part of the fixture's source pixels."""
    info = source["photo"]
    res, box = info["resolution_m"], info["lv95_box"]
    e_km, n_km = (int(v) for v in cell.split("-"))
    side = TILE_M // res
    r0 = round((box["n_max"] - (n_km + 1) * TILE_M) / res)
    c0 = round((e_km * TILE_M - box["e_min"]) / res)
    return photo[r0 : r0 + side, c0 : c0 + side]


def fixture_cells(source: dict | None = None) -> list[str]:
    """Every 1 km cell of the fixture's box, sorted (east outer, north inner)."""
    box = (source or fixture_source())["photo"]["lv95_box"]
    east = range(int(box["e_min"]) // TILE_M, int(box["e_max"]) // TILE_M)
    north = range(int(box["n_min"]) // TILE_M, int(box["n_max"]) // TILE_M)
    return sorted(f"{e}-{n}" for e in east for n in north)


def tile_bytes(cell: str, *, source: dict | None = None, datasets: dict | None = None) -> bytes:
    source = source or fixture_source()
    config = (datasets or fixture_datasets())[DATASET]
    e_km, n_km = (int(v) for v in cell.split("-"))
    pixels = tile_pixels(fixture_photo(source), source, cell)
    return geotiff(pixels, e_km * TILE_M, (n_km + 1) * TILE_M, config["resolution_m"])


def raw_farphoto(
    root: Path,
    *,
    source: dict | None = None,
    datasets: dict | None = None,
    bodies: dict | None = None,
) -> tuple[Path, dict]:
    """Write `download farphoto`'s layout for the fixture under `root`; return (root, entry).

    `bodies` maps a cell to the bytes to write instead of its GeoTIFF (a refusal case); the
    lock entry and provenance.json then pin those bytes, as a lock of them would.
    """
    source = copy.deepcopy(source or fixture_source())
    config = (datasets or fixture_datasets())[DATASET]
    folder = Path(root) / DATASET / config["edition"]
    folder.mkdir(parents=True, exist_ok=True)
    absent = sorted(source["absent"])
    tiles, entries = {}, []
    for cell in fixture_cells(source):
        if cell in absent:
            continue
        data = (bodies or {}).get(cell) or tile_bytes(cell, source=source, datasets=datasets)
        name = far_name(cell, config["edition"], config["resolution_m"])
        (folder / name).write_bytes(data)
        tiles[cell] = {"file": name, "sha256": sha256(data)}
        item = item_of(cell, config["edition"])
        entries.append(
            {
                "file": name,
                "item": item,
                "sha256": sha256(data),
                "size_bytes": len(data),
                "tile": cell,
                "url": URL.format(item=item, file=name),
            }
        )
    provenance = {
        "absent": absent,
        "attribution": config["attribution"],
        "collection": config["collection"],
        "dataset": DATASET,
        "edition": config["edition"],
        "resolution_m": config["resolution_m"],
        "schema": 1,
        "tiles": entries,
    }
    text = json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (folder / "provenance.json").write_bytes(text.encode("utf-8"))
    entry = {
        "absent": absent,
        "collection": config["collection"],
        "edition": config["edition"],
        "resolution_m": config["resolution_m"],
        "tiles": tiles,
    }
    return Path(root), entry


def raw_inputs(root: Path, **far) -> tuple[Path, dict]:
    """Both downloads of the fixture under `root`; the lock holds both entries."""
    source = far.get("source") or fixture_source()
    datasets = far.get("datasets") or fixture_datasets()
    _, lock = raw_regio(root, source["regio"], datasets=datasets)
    _, entry = raw_farphoto(root, **far)
    lock["datasets"][DATASET] = entry
    return Path(root), lock
