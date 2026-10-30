"""Pinning tests for brief M3-05: the roofs step's rule reproduces the shared roofs fixture.

Pinned decisions (m3-design.md §3, roof colours): the buildings are exactly the buildings
step's (selection, snapping, orientation, chunks, order). In integer units of 0.1 mm, a
triangle (a, b, c) is roof when n = (b - a) × (c - a) has n_H > 0 and 4·n_H² >= n_E² +
n_N² + n_H². A building's roof pixels are the 0.1 m source pixels whose centre lies in or
on the plan projection of one of its roof triangles, each counted once, from the photo's
pixels only. Its colour is, per channel, the lower median (sorted ascending, the element
at (n - 1) // 2) as "rrggbb" in lower case, or null with roof_pixels 0 when n = 0. The
file roofs/<area>.json is exactly {area, chunks: [{buildings: [{roof, roof_pixels,
triangles, uuid, vertices}] in chunk order, tile}] sorted by tile, format "roofs-v1",
lv95_box, source: {buildings, photo}, world_sha256}, sorted keys, 2-space indent, UTF-8,
LF, a final newline. Per chunk, the buildings' triangles and vertices add up to the chunk
file's.

The photo reaches the rule as rasters (west_dm, north_dm, pixels): the raster's west edge
is E = west_dm / 10 m, its north edge N = north_dm / 10 m, pixels a uint8 array of shape
(rows, columns, 3), rows north to south; pixel (j, i) has its centre at E = west_dm / 10 +
0.05 + 0.1·i, N = north_dm / 10 - 0.05 - 0.1·j. A swissimage tile 2623-1095 is the raster
(26230000, 10960000, its 10000 × 10000 pixels).

The fixture (tests/shared/roofs_fixture/, its cases and detectors in
tests/shared/roofs_vectors.json): the buildings fixture's world and eleven buildings, six
more in the tile that had none, and a synthetic photo in windows. Every likely wrong rule
named in the vectors' detectors (another slope limit, the unoriented triangles, a mirrored
or transposed photo, reading order, a pixel corner instead of its centre, a row or column
off by one, the boundary left out, an upper median or a mean, a pixel counted per
triangle, floating-point edge tests) was run against it by design and changes named
buildings. Design computed generated/ two independent ways (identical bytes).

Does NOT prove: that the step reads swisstopo's GeoTIFF tiles into these rasters or reads
the sheets (the real run does, against config/roofs.json); that the game colours the roofs
(brief M3-12).
"""

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from mattini.buildings import build_chunks
from mattini.roofs import build_roof_chunks, built_roofs_block, write_roofs
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
FIXTURE = SHARED / "roofs_fixture"
GENERATED = FIXTURE / "generated"
BUILDINGS_FIXTURE = SHARED / "buildings_fixture"
WORLD = BUILDINGS_FIXTURE / "world.json"
VECTORS = json.loads((SHARED / "roofs_vectors.json").read_text(encoding="utf-8"))
BOX = (2650900.0, 2651100.0, 1149950.0, 1150050.0)
BLOCK_KEYS = {"area", "chunks", "format", "lv95_box", "source", "world_sha256"}
BUILDING_KEYS = {"roof", "roof_pixels", "triangles", "uuid", "vertices"}
HEX = set("0123456789abcdef")


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _features() -> list[dict]:
    return [
        {
            "uuid": f["uuid"],
            "objektart": f["objektart"],
            "triangles": [tuple(tuple(p) for p in t) for t in f["triangles"]],
        }
        for f in _json(FIXTURE / "source.json")["features"]
    ]


def _rasters() -> list[tuple[int, int, np.ndarray]]:
    rasters = []
    for tile in _json(FIXTURE / "photo.json")["tiles"]:
        data = (FIXTURE / tile["file"]).read_bytes()
        for w in tile["windows"]:
            size = w["rows"] * w["columns"] * 3
            pixels = np.frombuffer(data, dtype=np.uint8, count=size, offset=w["offset"])
            rasters.append(
                (w["west_dm"], w["north_dm"], pixels.reshape(w["rows"], w["columns"], 3))
            )
    return rasters


def _expected() -> dict:
    return _json(GENERATED / "roofs" / "fixture.json")


def _chunks(rasters=None) -> list[dict]:
    photo = _rasters() if rasters is None else rasters
    return build_roof_chunks(_features(), load_world(WORLD), "fixture", iter(photo))


def test_the_rule_gives_the_fixture_s_roofs():
    chunks = _chunks()
    expected = _expected()["chunks"]
    assert [c["tile"] for c in chunks] == [c["tile"] for c in expected]
    for chunk, entry in zip(chunks, expected, strict=True):
        assert chunk == entry, chunk["tile"]
    named = {b["uuid"]: (b["roof"], b["roof_pixels"]) for b in VECTORS["buildings"]}
    got = {b["uuid"]: (b["roof"], b["roof_pixels"]) for c in chunks for b in c["buildings"]}
    assert got == named


def test_write_roofs_writes_the_fixture_s_bytes(tmp_path):
    expected = _expected()
    block = write_roofs(
        tmp_path, "fixture", _chunks(), BOX, expected["world_sha256"], expected["source"]
    )
    assert block == expected
    written = tmp_path / "roofs" / "fixture.json"
    assert written.read_bytes() == (GENERATED / "roofs" / "fixture.json").read_bytes()
    assert sorted(p.name for p in (tmp_path / "roofs").iterdir()) == ["fixture.json"]


def test_the_description_has_exactly_its_keys():
    block = _expected()
    assert set(block) == BLOCK_KEYS
    assert block["format"] == "roofs-v1"
    assert set(block["lv95_box"]) == {"e_max", "e_min", "n_max", "n_min"}
    assert all(type(v) is float for v in block["lv95_box"].values())
    assert set(block["source"]) == {"buildings", "photo"}
    assert set(block["source"]["buildings"]) == {
        "attribution",
        "collection",
        "dataset",
        "edition",
        "sheets",
    }
    assert set(block["source"]["photo"]) == {
        "attribution",
        "collection",
        "dataset",
        "edition",
        "resolution_m",
        "tiles",
    }
    assert block["source"]["photo"]["dataset"] == "swissimage"
    assert block["source"]["photo"]["resolution_m"] == 0.1
    tiles = [c["tile"] for c in block["chunks"]]
    assert tiles == sorted(set(tiles))
    for chunk in block["chunks"]:
        assert set(chunk) == {"buildings", "tile"}
        uuids = [b["uuid"] for b in chunk["buildings"]]
        assert uuids == sorted(set(uuids)), "chunk order: by UUID as text"
        for b in chunk["buildings"]:
            assert set(b) == BUILDING_KEYS
            assert all(type(b[k]) is int for k in ("roof_pixels", "triangles", "vertices"))
            if b["roof_pixels"] == 0:
                assert b["roof"] is None
            else:
                assert isinstance(b["roof"], str) and len(b["roof"]) == 6 and set(b["roof"]) <= HEX


def test_no_roof_pixel_means_no_colour():
    by_uuid = {b["uuid"]: b for c in _expected()["chunks"] for b in c["buildings"]}
    # the tower (no roof triangle) and the two strips (roof triangles, no pixel centre)
    for suffix in ("012}", "014}", "015}"):
        (uuid,) = [u for u in by_uuid if u.endswith(suffix)]
        assert (by_uuid[uuid]["roof"], by_uuid[uuid]["roof_pixels"]) == (None, 0), uuid
    # without the photo's pixels under building 02, its roof is null and nothing else moves
    flat = "{6D3A8F24-0000-4000-8000-000000000002}"
    source = _json(FIXTURE / "source.json")["features"]
    points = [p for f in source if f["uuid"] == flat for t in f["triangles"] for p in t]
    e0, e1 = min(p[0] for p in points) * 10, max(p[0] for p in points) * 10
    n0, n1 = min(p[1] for p in points) * 10, max(p[1] for p in points) * 10
    kept = [
        r
        for r in _rasters()
        if not (r[0] < e1 and e0 < r[0] + r[2].shape[1] and r[1] - r[2].shape[0] < n1 and n0 < r[1])
    ]
    assert len(kept) == len(_rasters()) - 1
    got = {b["uuid"]: (b["roof"], b["roof_pixels"]) for c in _chunks(kept) for b in c["buildings"]}
    want = {u: (b["roof"], b["roof_pixels"]) for u, b in by_uuid.items()}
    want[flat] = (None, 0)
    assert got == want


def test_each_chunk_adds_up_to_its_chunk_file():
    chunks = _chunks()
    built = build_chunks(_features(), load_world(WORLD), "fixture")
    listed = _json(GENERATED / "buildings" / "fixture.json")["chunks"]
    assert [c["tile"] for c in chunks] == [c["tile"] for c in built] == [c["tile"] for c in listed]
    for chunk, mesh, entry in zip(chunks, built, listed, strict=True):
        triangles = sum(b["triangles"] for b in chunk["buildings"])
        vertices = sum(b["vertices"] for b in chunk["buildings"])
        assert len(chunk["buildings"]) == mesh["buildings"] == entry["buildings"]
        assert (triangles, vertices) == (mesh["triangles"], mesh["vertices"]), chunk["tile"]
        assert (triangles, vertices) == (entry["triangles"], entry["vertices"]), chunk["tile"]
        assert mesh["data"] == (GENERATED / entry["file"]).read_bytes()


def test_the_fixture_is_what_its_files_say():
    """Lesson 42: the fixture's own claims, checked."""
    lock = _json(FIXTURE / "datasets.lock.json")["datasets"]
    sheet = lock["swissbuildings3d"]["sheets"]["1249-42"]
    assert _sha((FIXTURE / sheet["file"]).read_bytes()) == sheet["sha256"]
    photo = _json(FIXTURE / "photo.json")
    assert {t["tile"]: {"file": t["file"], "sha256": t["sha256"]} for t in photo["tiles"]} == lock[
        "swissimage"
    ]["tiles"]
    for t in photo["tiles"]:
        assert _sha((FIXTURE / t["file"]).read_bytes()) == t["sha256"], t["file"]
    # the buildings fixture's eleven buildings, unchanged, and its three chunk files
    old = _json(BUILDINGS_FIXTURE / "source.json")["features"]
    assert _json(FIXTURE / "source.json")["features"][: len(old)] == old
    for tile in ("2650-1149", "2650-1150", "2651-1150"):
        same = (BUILDINGS_FIXTURE / "generated" / "buildings" / f"{tile}.bin").read_bytes()
        assert (GENERATED / "buildings" / f"{tile}.bin").read_bytes() == same, tile
    # its buildings config expects its chunk files, computed for its lock entry and world
    entry = json.dumps(
        lock["swissbuildings3d"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    chunks = _json(GENERATED / "buildings" / "fixture.json")["chunks"]
    assert _json(FIXTURE / "buildings.json")["areas"]["fixture"] == {
        "computed_for": {
            "inputs_sha256": _sha(entry.encode("utf-8")),
            "world_sha256": _sha(WORLD.read_bytes()),
        },
        "expected_sha256": {c["tile"]: _sha((GENERATED / c["file"]).read_bytes()) for c in chunks},
    }
    # the roofs config: what it was computed for, and the file it expects
    config = _json(FIXTURE / "roofs.json")
    entries = {name: lock[name] for name in ("swissbuildings3d", "swissimage")}
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert config == {
        "schema": 1,
        "areas": {
            "fixture": {
                "computed_for": {
                    "inputs_sha256": _sha(canonical.encode("utf-8")),
                    "world_sha256": _sha(WORLD.read_bytes()),
                },
                "expected_sha256": _sha((GENERATED / "roofs" / "fixture.json").read_bytes()),
            }
        },
    }
    # the manifest the game reads: M3's shape, since v0.4.0-07 the sky block and since v0.5.0-02
    # the shadows block, both built blocks verbatim, the others null, in the text manifest.py writes (the wiring brief reproduces
    # it byte for byte)
    text = (GENERATED / "manifest.json").read_bytes()
    manifest = json.loads(text.decode("utf-8"))
    assert set(manifest) == {
        "buildings",
        "photo",
        "roofs",
        "schema",
        "shadows",
        "sky",
        "surfaces",
        "terrain",
        "trees",
        "world",
        "world_sha256",
    }
    assert [key for key in sorted(manifest) if manifest[key] is None] == [
        "photo",
        "shadows",
        "sky",
        "surfaces",
        "terrain",
        "trees",
    ]
    canonical_text = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert text == canonical_text.encode("utf-8")
    assert manifest["schema"] == 1
    assert manifest["roofs"] == _expected()
    assert manifest["buildings"] == _json(GENERATED / "buildings" / "fixture.json")
    assert manifest["world"] == _json(WORLD)
    assert manifest["world_sha256"] == _sha(WORLD.read_bytes()) == _expected()["world_sha256"]
    # the raw photo files are binary to git: a CRLF checkout must not touch them (brain.md H10)
    rules = [
        line.split()
        for line in (REPO / ".gitattributes").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert ["*.u8", "binary"] in rules


def test_built_roofs_block_reads_the_fixture(tmp_path):
    out = tmp_path / "generated"
    shutil.copytree(GENERATED / "buildings", out / "buildings")
    world = load_world(WORLD)
    args = {
        "roofs_config": _json(FIXTURE / "roofs.json"),
        "terrain_config": _json(BUILDINGS_FIXTURE / "terrain.json"),
        "world": world,
        "world_sha256": _sha(WORLD.read_bytes()),
        "datasets": _json(FIXTURE / "datasets.json")["datasets"],
        "lock": _json(FIXTURE / "datasets.lock.json"),
        "buildings_block": _json(GENERATED / "buildings" / "fixture.json"),
    }
    assert built_roofs_block(out, **args) is None, "no roofs/fixture.json: nothing built"
    shutil.copytree(GENERATED / "roofs", out / "roofs")
    assert built_roofs_block(out, **args) == _expected()
