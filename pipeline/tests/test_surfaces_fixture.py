"""Pinning tests for brief M3-06: the surfaces rule reproduces the shared surfaces fixture.

Pinned decisions (m3-design §4, as refined by design on 2026-10-14):
- `class_grid(features, box, cell_m)` gives the area's classes as a uint8 array, rows north
  to south, columns west to east: texel (r, c) is the point E = e_min + cell/2 + c * cell,
  N = n_max - cell/2 - r * cell, in whole millimetres. Highest wins: 4 road > 3 path >
  2 water > 1 rock > 0 none. Road and path: TLM_STRASSE with BELAGSART 100 (Hart) or 200
  (Natur), OBJEKTART with a width (8: 10 m, 9: 6 m, 10: 4 m, 11: 3 m, 15: 2 m, 16: 1 m,
  17: 1 m, 18: 2 m, 20: 8 m: codes and names read from the FileGDB's subtypes), KUNSTBAUTE
  not 700, 1000, 1100, 1200 or 1400; a centre is on a line when its distance to a segment
  is at most half the width (exactly, ties included). Water: TLM_BODENBEDECKUNG 5 or 10
  (centre inside), TLM_FLIESSGEWAESSER 4 with VERLAUF 100 or 500 (an ASSUMED width of 2 m,
  a labelled placeholder). Rock: TLM_BODENBEDECKUNG 1-4 (centre inside). Inside: even-odd
  over all rings of one feature, an edge counting when (y1 > yc) != (y2 > yc) and
  xc < its crossing; features of one class are OR-ed, never XOR-ed.
- `png_l8(pixels)` writes the PNG without Pillow: the signature, IHDR (8-bit greyscale,
  colour type 0, no interlace), each scanline prefixed by filter byte 0, ONE zlib stream
  (zlib.compress, level 9) split into IDAT chunks of at most 1 MiB, IEND, CRC32 from
  zlib.crc32. Determinism is pinned on the pixels (`pixels_sha256`); the PNG's bytes
  depend on the zlib build and are design's too (`expected_png_sha256`, brief
  M3-R1-fix-6: the committed fixture PNG is written again byte for byte).
- `write_surfaces` writes surfaces/<area>.png.import (`importer="keep"`, so that Godot
  ships the PNG as it is: an imported PNG is not in an export, measured), the PNG and
  surfaces/<area>.json, each through a `.part` rename; the description has exactly its
  keys, sorted, 2-space indent, UTF-8, LF and a final newline.

The fixture (tests/shared/surfaces_fixture/, its outcomes and cases in
tests/shared/surfaces_vectors.json) was computed by design two independent ways (a
vectorised numpy rule and a pure-Python row scanline over Fractions; identical bytes at
0.2, 0.5 and 1 m). Its points tell apart the likeliest wrong twins (listed there).

Does NOT prove: that the reader hands these features over (test_surfaces_read.py); that
the real village's classes are design's (the step compares them with
config/surfaces.json, test_surfaces_step.py proves the comparison).
"""

import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np
import pytest

from mattini import surfaces
from mattini.surfaces import class_grid, load_surfaces_config, png_l8, write_surfaces

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surfaces_fixture"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "surfaces_vectors.json").read_text("utf-8"))
BOX = (2700012.0, 2700052.0, 1199971.0, 1200001.0)
KEEP = b'[remap]\n\nimporter="keep"\n'
MIB = 1 << 20
VILLAGE = {
    "0.2": "93d78ba6d89eea27d0ec897d9f5fca244633336ff29378cd2b2fc9def77e5093",
    "0.5": "adda417b52b9ebff5a4f8f9d6d9d985da65134c0e4eda1938db07b5f35b01d9e",
    "1": "4ea3d1e660fed1d46b4a7152e7378924c6597d1611faace59686d945e15db408",
}
VILLAGE_PNG = {  # the PNG's bytes, zlib 1.3 (brief M3-R1-fix-6); they pin the encoder, not the classes
    "0.2": "8922edf904e3e4e1de40c65daf1af1aae3474d71481d628a548152ce5b843e12",
    "0.5": "6773cfc4b553cd3fa7e6c19fda08a66a8db711f8fd9ff0a498852d5dac17b071",
    "1": "e68a251cef28046b921999e2792c1bab3497cc193ee42e6afd49dc9cc60d6344",
}
VILLAGE_TLM_ENTRY = {  # the lock entry design computed the village from (`lock tlm` writes it)
    "collection": "ch.swisstopo.swisstlm3d",
    "edition": "2026-02",
    "file": "swisstlm3d_2026-02_2056_5728.gdb.zip",
    "sha256": "185ffca883e7a2d6be4ea3d1f62ee4d1a09f07fe90e381738fdcb3a849df28da",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _features() -> dict:
    """The fixture's features as the reader hands them over: those its vectors list."""
    source = json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))
    by_uuid = {f["uuid"]: f for features in source.values() for f in features}
    return {layer: [by_uuid[u] for u in uuids] for layer, uuids in VECTORS["read"].items()}


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    """A PNG's chunks as (type, data), each CRC checked: a reader written here, not the step's."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    chunks, at = [], 8
    while at < len(data):
        (length,) = struct.unpack(">I", data[at : at + 4])
        kind, body = data[at + 4 : at + 8], data[at + 8 : at + 8 + length]
        (crc,) = struct.unpack(">I", data[at + 8 + length : at + 12 + length])
        assert crc == zlib.crc32(kind + body), kind
        chunks.append((kind, body))
        at += 12 + length
    return chunks


def _assert_designed_png(data: bytes, pixels: np.ndarray) -> None:
    """`data` is the PNG this machine's zlib gives for `pixels`, written as pinned above."""
    rows, columns = pixels.shape
    chunks = _chunks(data)
    kinds = [kind for kind, _ in chunks]
    idat = [body for kind, body in chunks if kind == b"IDAT"]
    assert kinds == [b"IHDR"] + [b"IDAT"] * len(idat) + [b"IEND"]
    assert chunks[0][1] == struct.pack(">IIBBBBB", columns, rows, 8, 0, 0, 0, 0)
    assert chunks[-1][1] == b""
    assert all(len(body) == MIB for body in idat[:-1]) and 0 < len(idat[-1]) <= MIB
    scanlines = np.zeros((rows, columns + 1), dtype=np.uint8)
    scanlines[:, 1:] = pixels
    assert b"".join(idat) == zlib.compress(scanlines.tobytes(), 9)


def test_the_class_grid_is_the_designed_one():
    grid = class_grid(_features(), BOX, 0.2)
    assert grid.dtype == np.uint8 and grid.shape == (150, 200)
    assert _sha(grid.tobytes()) == VECTORS["pixels_sha256"]["0.2"]
    counts = np.bincount(grid.ravel(), minlength=5).tolist()
    assert {str(k): counts[k] for k in range(5)} == VECTORS["counts"]
    for point in VECTORS["points"]:
        row, column = point["texel"]
        assert int(grid[row, column]) == point["class"], point["name"]


@pytest.mark.parametrize(("cell_m", "key", "shape"), [(0.5, "0.5", (60, 80)), (1.0, "1", (30, 40))])
def test_other_cells_give_the_designed_classes(cell_m, key, shape):
    grid = class_grid(_features(), BOX, cell_m)
    assert grid.shape == shape
    assert _sha(grid.tobytes()) == VECTORS["pixels_sha256"][key]


def test_the_fixture_s_files_hold_the_designed_classes():
    block = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    png = (GENERATED / "surfaces" / "fixture.png").read_bytes()
    assert block["sha256"] == _sha(png)
    rows, columns = block["rows"], block["columns"]
    raw = zlib.decompress(b"".join(body for kind, body in _chunks(png) if kind == b"IDAT"))
    lines = np.frombuffer(raw, dtype=np.uint8).reshape(rows, columns + 1)
    assert not lines[:, 0].any(), "filter 0 on every row"
    assert _sha(lines[:, 1:].tobytes()) == block["pixels_sha256"] == VECTORS["pixels_sha256"]["0.2"]
    config = load_surfaces_config(FIXTURE / "surfaces.json")
    assert config["areas"]["fixture"]["cell_m"] == 0.2
    assert config["areas"]["fixture"]["expected_pixels_sha256"] == VECTORS["pixels_sha256"]
    assert config["areas"]["fixture"]["expected_png_sha256"]["0.2"] == block["sha256"]
    manifest = json.loads((GENERATED / "manifest.json").read_text(encoding="utf-8"))
    world_raw = (FIXTURE / "world.json").read_bytes()
    assert manifest["surfaces"] == block and manifest["world"] == json.loads(world_raw)
    assert manifest["world_sha256"] == block["world_sha256"] == _sha(world_raw)


def test_write_surfaces_writes_the_designed_files(tmp_path):
    block = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    grid = class_grid(_features(), BOX, 0.2)
    written = write_surfaces(
        tmp_path, "fixture", grid, BOX, 0.2, block["world_sha256"], block["source"]
    )
    png = (tmp_path / "surfaces" / "fixture.png").read_bytes()
    assert written == block, "the whole description, the PNG's SHA-256 too, is design's"
    assert _sha(png) == block["sha256"], f"this machine's zlib {zlib.ZLIB_RUNTIME_VERSION}"
    text = json.dumps(written, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert (tmp_path / "surfaces" / "fixture.json").read_bytes() == text.encode("utf-8")
    assert (tmp_path / "surfaces" / "fixture.png.import").read_bytes() == KEEP
    _assert_designed_png(png, grid)
    assert sorted(p.name for p in (tmp_path / "surfaces").iterdir()) == [
        "fixture.json",
        "fixture.png",
        "fixture.png.import",
    ]


def test_write_surfaces_writes_the_png_it_is_given_and_encodes_nothing_again(tmp_path, monkeypatch):
    block = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    designed = (GENERATED / "surfaces" / "fixture.png").read_bytes()
    grid = class_grid(_features(), BOX, 0.2)

    def no_encoding(*args, **keywords):
        raise AssertionError("the PNG was compressed again")

    monkeypatch.setattr(surfaces.zlib, "compress", no_encoding)
    written = write_surfaces(
        tmp_path, "fixture", grid, BOX, 0.2, block["world_sha256"], block["source"], png=designed
    )
    assert written == block
    assert (tmp_path / "surfaces" / "fixture.png").read_bytes() == designed


def test_one_level_9_stream_is_split_into_idat_chunks_of_at_most_1_mib():
    # Random classes: their entropy alone is 1.04 MiB, so every zlib build needs two chunks.
    pixels = np.random.default_rng(6).integers(0, 5, size=(1300, 2900), dtype=np.uint8)
    png = png_l8(pixels)
    assert len([kind for kind, _ in _chunks(png) if kind == b"IDAT"]) >= 2
    _assert_designed_png(png, pixels)


def test_the_committed_config_expects_design_s_village():
    config = load_surfaces_config()
    world_sha256 = _sha((REPO / "config" / "world.json").read_bytes())
    entry = json.dumps(VILLAGE_TLM_ENTRY, sort_keys=True, separators=(",", ":"))
    assert config == {
        "schema": 1,
        "areas": {
            "village": {
                "cell_m": 0.2,
                "computed_for": {
                    "inputs_sha256": _sha(entry.encode("utf-8")),
                    "world_sha256": world_sha256,
                },
                "expected_pixels_sha256": VILLAGE,
                "expected_png_sha256": VILLAGE_PNG,
            }
        },
    }
