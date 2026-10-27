"""Pinning tests for brief M3-06: the surfaces step's checks, in order, and its built block.

Pinned decisions (m3-design §4 and its conventions, as refined by design on 2026-10-14;
the input layout is brief M3-03's): `build_surfaces(world, datasets, lock, surfaces_config,
raw_root, out_dir)` serves the one area of config/surfaces.json and reads
<raw_root>/swisstlm3d/<edition>/<the lock's file>, beside the download's flat
provenance.json. Before it reads anything there it compares the area's `computed_for` with
the world config (`world_sha256`) and with the lock's `swisstlm3d` entry (`inputs_sha256`
= lock.entry_sha256), refusing each difference as a design change (lesson 41). Then
provenance.json must list the datasets config's collection and edition and the lock's file
and SHA-256, and the file's SHA-256 must be the lock's; each difference is refused naming
`python -m mattini download tlm`. It compares the classes' `pixels_sha256` with the
config's `expected_pixels_sha256` for its cell before it writes anything, and refuses a
difference naming both values (lesson 38). The block it returns is what
surfaces/<area>.json holds, exactly its keys.
`built_surfaces_block(out_dir, surfaces_config, world, world_sha256, datasets, lock)` (the
manifest's check, wired by a later brief) gives None when no surfaces are built, else the
block once it is shown to hold: it decodes the PNG with the standard library and refuses
a row whose filter is not 0 (a valid PNG Godot would read, but not the pinned format) and
pixels other than `pixels_sha256`, naming `python -m mattini surfaces`. From brief v0.4.0-01
the block also holds `flow`, the flow grid's description (test_surfaces_flow.py).

Does NOT prove: the CLI (`python -m mattini surfaces`) and the manifest's wiring (later
briefs); that the real village gives design's classes (the step's own comparison with
config/surfaces.json does, on the owner's run).
"""

import hashlib
import json
import shutil
import struct
import zlib
from pathlib import Path

import numpy as np
import pytest
from computed_for import recorded
from synthetic_tlm import zipped_tlm

from mattini.surfaces import (
    SurfacesError,
    build_surfaces,
    built_surfaces_block,
    load_surfaces_config,
)
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surfaces_fixture"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "surfaces_vectors.json").read_text("utf-8"))
ZIP_NAME = "swisstlm3d_2026-02_2056_5728.gdb.zip"
SURFACES_COMMAND = "python -m mattini surfaces"
DOWNLOAD_COMMAND = "python -m mattini download tlm"
BLOCK_KEYS = {
    "area",
    "cell_m",
    "classes",
    "columns",
    "file",
    "flow",  # brief v0.4.0-01
    "format",
    "lv95_box",
    "pixels_sha256",
    "rows",
    "sha256",
    "source",
    "world_sha256",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source() -> dict:
    return json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))


def _datasets() -> dict:
    return json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]


def _lock(sha256: str) -> dict:
    entry = {
        "collection": "ch.swisstopo.swisstlm3d",
        "edition": "2026-02",
        "file": ZIP_NAME,
        "sha256": sha256,
    }
    return {"schema": 1, "datasets": {"swisstlm3d": entry}}


def _config(world, lock: dict) -> dict:
    """The fixture's config, recorded for `world` and `lock` as design records it."""
    return recorded(load_surfaces_config(FIXTURE / "surfaces.json"), world, lock, "swisstlm3d")


def _raw(tmp_path, *, sha256: str | None = None) -> tuple[Path, str]:
    """`download tlm`'s layout (brief M3-03) holding the fixture as a zipped FileGDB.

    Returns the raw root and the zip's SHA-256; `sha256` puts another one in
    provenance.json.
    """
    (tmp_path / "make").mkdir()
    data = zipped_tlm(tmp_path / "make", _source(), zip_name=ZIP_NAME).read_bytes()
    folder = tmp_path / "raw" / "swisstlm3d" / "2026-02"
    folder.mkdir(parents=True)
    (folder / ZIP_NAME).write_bytes(data)
    provenance = {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swisstlm3d",
        "dataset": "swisstlm3d",
        "edition": "2026-02",
        "file": ZIP_NAME,
        "item": "swisstlm3d_2026-02",
        "schema": 1,
        "sha256": sha256 or _sha(data),
        "size_bytes": len(data),
        "url": f"https://data.geo.admin.ch/ch.swisstopo.swisstlm3d/swisstlm3d_2026-02/{ZIP_NAME}",
    }
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return tmp_path / "raw", _sha(data)


def test_the_step_writes_the_designed_classes(tmp_path):
    world = load_world(FIXTURE / "world.json")
    raw, sha256 = _raw(tmp_path)
    lock = _lock(sha256)
    out = tmp_path / "out"
    block = build_surfaces(world, _datasets(), lock, _config(world, lock), raw, out)
    assert set(block) == BLOCK_KEYS
    assert block["pixels_sha256"] == VECTORS["pixels_sha256"]["0.2"]
    assert block["source"] == {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swisstlm3d",
        "dataset": "swisstlm3d",
        "edition": "2026-02",
        "file": ZIP_NAME,
        "sha256": sha256,
    }
    assert json.loads((out / "surfaces" / "fixture.json").read_text(encoding="utf-8")) == block
    assert block["sha256"] == _sha((out / "surfaces" / "fixture.png").read_bytes())


def test_another_world_is_refused_before_the_download_is_read(tmp_path):
    world = load_world(FIXTURE / "world.json")
    lock = _lock("0" * 64)
    config = _config(b'{"another": "world"}\n', lock)
    empty = tmp_path / "raw"  # no provenance.json, no file: reading first would fail otherwise
    with pytest.raises(SurfacesError) as refusal:
        build_surfaces(world, _datasets(), lock, config, empty, tmp_path / "out")
    assert "config/surfaces.json" in str(refusal.value)
    assert "config/world.json" in str(refusal.value)
    assert not (tmp_path / "out").exists()


def test_other_inputs_are_refused_before_the_download_is_read(tmp_path):
    world = load_world(FIXTURE / "world.json")
    config = _config(world, _lock("1" * 64))
    empty = tmp_path / "raw"
    with pytest.raises(SurfacesError) as refusal:
        build_surfaces(world, _datasets(), _lock("0" * 64), config, empty, tmp_path / "out")
    assert "config/surfaces.json" in str(refusal.value) and "lock" in str(refusal.value)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "case", ["no-provenance", "provenance-of-another-file", "a-file-of-other-bytes"]
)
def test_a_download_that_is_not_the_locked_file_is_refused(tmp_path, case):
    world = load_world(FIXTURE / "world.json")
    raw, sha256 = _raw(tmp_path, sha256="e" * 64 if case == "provenance-of-another-file" else None)
    if case == "no-provenance":
        (raw / "swisstlm3d" / "2026-02" / "provenance.json").unlink()
    if case == "a-file-of-other-bytes":
        sha256 = _sha(b"another file")  # the lock and provenance.json agree; the bytes do not
        path = raw / "swisstlm3d" / "2026-02" / "provenance.json"
        provenance = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps({**provenance, "sha256": sha256}), encoding="utf-8")
    lock = _lock(sha256)
    with pytest.raises(SurfacesError, match=DOWNLOAD_COMMAND):
        build_surfaces(world, _datasets(), lock, _config(world, lock), raw, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_other_classes_are_refused_before_anything_is_written(tmp_path):
    world = load_world(FIXTURE / "world.json")
    raw, sha256 = _raw(tmp_path)
    lock = _lock(sha256)
    config = _config(world, lock)
    other = VECTORS["pixels_sha256"]["0.5"]
    config["areas"]["fixture"]["expected_pixels_sha256"]["0.2"] = other
    with pytest.raises(SurfacesError) as refusal:
        build_surfaces(world, _datasets(), lock, config, raw, tmp_path / "out")
    assert VECTORS["pixels_sha256"]["0.2"] in str(refusal.value) and other in str(refusal.value)
    assert not (tmp_path / "out" / "surfaces").exists()


# ---------------------------------------------------------------- the built block


def _built(tmp_path, png: bytes | None = None) -> Path:
    """A copy of the fixture's generated surfaces, with `png` in place of its PNG."""
    shutil.copytree(GENERATED / "surfaces", tmp_path / "surfaces")
    if png is not None:
        (tmp_path / "surfaces" / "fixture.png").write_bytes(png)
        path = tmp_path / "surfaces" / "fixture.json"
        block = json.loads(path.read_text(encoding="utf-8"))
        block["sha256"] = _sha(png)  # the description matches its file: only decoding can tell
        path.write_text(json.dumps(block, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return tmp_path


def _check(out: Path):
    world_path = FIXTURE / "world.json"
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    return built_surfaces_block(
        out,
        load_surfaces_config(FIXTURE / "surfaces.json"),
        load_world(world_path),
        _sha(world_path.read_bytes()),
        _datasets(),
        lock,
    )


def _png(pixels: np.ndarray, sub_row: int | None = None) -> bytes:
    """A valid 8-bit greyscale PNG written here; `sub_row` uses filter 1 (Sub) on one row."""
    rows, columns = pixels.shape
    lines = []
    for r in range(rows):
        row = pixels[r].astype(np.int16)
        if r == sub_row:
            left = np.concatenate([[0], row[:-1]])
            lines.append(b"\x01" + ((row - left) % 256).astype(np.uint8).tobytes())
        else:
            lines.append(b"\x00" + pixels[r].tobytes())

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = struct.pack(">I", zlib.crc32(kind + body))
        return struct.pack(">I", len(body)) + kind + body + crc

    header = struct.pack(">IIBBBBB", columns, rows, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(lines), 9))
        + chunk(b"IEND", b"")
    )


def _fixture_pixels() -> np.ndarray:
    png = (GENERATED / "surfaces" / "fixture.png").read_bytes()
    idat, at = b"", 8
    while at < len(png):
        (length,) = struct.unpack(">I", png[at : at + 4])
        if png[at + 4 : at + 8] == b"IDAT":
            idat += png[at + 8 : at + 8 + length]
        at += 12 + length
    lines = np.frombuffer(zlib.decompress(idat), dtype=np.uint8).reshape(150, 201)
    return lines[:, 1:].copy()


def test_built_surfaces_give_their_block(tmp_path):
    block = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    assert _check(_built(tmp_path)) == block


def test_no_built_surfaces_give_none(tmp_path):
    assert _check(tmp_path) is None


def test_a_row_written_with_another_filter_is_refused(tmp_path):
    pixels = _fixture_pixels()
    out = _built(tmp_path, _png(pixels, sub_row=75))
    with pytest.raises(SurfacesError, match="filter") as refusal:
        _check(out)
    assert SURFACES_COMMAND in str(refusal.value)


def test_other_classes_in_the_png_are_refused(tmp_path):
    pixels = _fixture_pixels()
    pixels[75, 0] = (pixels[75, 0] + 1) % 5
    out = _built(tmp_path, _png(pixels))
    with pytest.raises(SurfacesError, match="pixels_sha256") as refusal:
        _check(out)
    assert SURFACES_COMMAND in str(refusal.value)
