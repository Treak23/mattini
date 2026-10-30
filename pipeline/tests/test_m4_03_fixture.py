"""Pinning tests for brief v0.5.0-01: the pipeline reproduces the shared shadows fixture byte for byte.

Carried from brief M4-03's pin (docs/briefs/pinning/M4-03/) and re-pinned for release 0.5.0
(2026-10-29): only these docstrings changed, to name v0.5.0-01, v0.5.0-02 and the reader.

The fixture (tests/shared/shadows_fixture/, design data): a synthetic 0.5 m surface `dsm.f32`
(little-endian float32, 96 rows north to south x 64 columns west to east, covering the fixture
area's box exactly) in a world of its own (`world.json`: a non-zero `height_offset_m`, a box of
32 x 48 m crossing four 1 km tiles off its centre), the datasets config and a lock whose
`swisssurface3d` entry names `dsm.f32` for each tile, `shadows.json` (its expected values and
`computed_for`), and `generated/shadows/fixture.png` (64 x 96 cells of 0.5 m), `.png.import` and `.json` as the
step writes them. The game's reader (M4-06's, re-cut in 0.5.0) reads that generated folder. The surface holds a
10 m block casting north and leaning east, a 6 m wall one 0.5 m pixel thick, a ridge at the
east edge whose north face is steeper than the sun, and a slope at the south edge facing away
from the sun; tests/shared/shadows_vectors.json names cells and their values. Design computed
the mask two independent ways and cell by cell (identical), and wrote the files with its own
writer.

Pinned decisions (m4-design §3 as ruled on 2026-10-17, the brief): the march runs on 1 m cells,
the mask is written at 0.5 m (each 1 m cell's shadow on its 2 x 2 cells, then the inset at
0.5 m); the description is exactly {area, cell_m (0.5), columns,
file, format "png-l8", lv95_box, pixels_sha256, rows, sha256, source {attribution, collection,
dataset, editions, entry_sha256}, sun (the config's), world_sha256}, written with
`json.dumps(indent=2, sort_keys=True, ensure_ascii=False)` and a newline; the PNG is 8-bit grey,
values 0 and 255, rows north to south, filter 0 on every row, one zlib stream at level 9 in
IDAT chunks of at most 1 MiB (the surfaces' format, brief M3-06, read by `read_png_l8`).

Does NOT prove: the GeoTIFF tiles' reading (test_m4_03_step.py); the real village
(config/shadows.json and the brief's real run); the game's reading (M4-06's reader, re-cut in 0.5.0); the split of
a level-9 stream longer than 1 MiB into IDAT chunks on real data (the village's PNG is 854'622
bytes, one chunk; the split is shown here on a stored stream, level 0, which is fast); that the
sun's azimuth is right to a degree (this small fixture gives the same mask from 184.67 to
185.13 degrees: config/shadows.json's value is pinned in test_m4_03_village_config.py).
"""

import copy
import hashlib
import json
import struct
import zlib
from pathlib import Path

import numpy as np
import pytest

from mattini import shadows
from mattini.shadows import (
    ShadowsError,
    capture_mask,
    cast_shadow,
    cell_heights,
    check_shadows_config,
    inset,
    load_shadows_config,
    own_shadow,
    png_mask,
    write_shadows,
)
from mattini.surfaces import read_png_l8

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "shadows_fixture"
GENERATED = FIXTURE / "generated" / "shadows"
VECTORS = json.loads((REPO / "tests" / "shared" / "shadows_vectors.json").read_text("utf-8"))
BOX = (2650986.0, 2651018.0, 1149978.0, 1150026.0)
KEEP = b'[remap]\n\nimporter="keep"\n'


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _surface() -> np.ndarray:
    return np.fromfile(FIXTURE / "dsm.f32", dtype="<f4").reshape(96, 64)


def _config() -> dict:
    return load_shadows_config(FIXTURE / "shadows.json")


def _mask(**sun) -> np.ndarray:
    config = _config()
    az = sun.get("az", config["sun"]["azimuth_grid_deg"])
    el = sun.get("el", config["sun"]["elevation_deg"])
    return capture_mask(_surface(), az, el, config["threshold_m"])


def _block() -> dict:
    return json.loads((GENERATED / "fixture.json").read_text("utf-8"))


def _png_pixels() -> np.ndarray:
    return read_png_l8((GENERATED / "fixture.png").read_bytes())


def test_the_mask_is_the_generated_png():
    mask = _mask()
    assert mask.shape == (96, 64) and mask.dtype == np.uint8
    assert np.array_equal(mask, _png_pixels())
    assert _sha(mask.tobytes()) == _block()["pixels_sha256"]
    assert int((mask == 255).sum()) == VECTORS["shadow_cells"] == 489


@pytest.mark.parametrize("cell", VECTORS["cells"], ids=lambda c: c["name"])
def test_each_named_cell_has_its_value(cell):
    pixels = _png_pixels()
    r, c = cell["row"], cell["column"]
    assert int(pixels[r, c]) == cell["value"], cell["why"]
    # the 0.5 m cell's centre: a quarter metre in from the box's north-west corner
    assert cell["lv95"] == [BOX[0] + 0.25 + 0.5 * c, BOX[3] - 0.25 - 0.5 * r]
    world = json.loads((FIXTURE / "world.json").read_text("utf-8"))
    origin = world["origin_lv95"]
    assert cell["local_xz"] == [cell["lv95"][0] - origin["e"], -(cell["lv95"][1] - origin["n"])]
    config = _config()
    h = cell_heights(_surface())
    sun = config["sun"]
    cast = cast_shadow(h, sun["azimuth_grid_deg"], sun["elevation_deg"], config["threshold_m"])
    own = own_shadow(h, sun["azimuth_grid_deg"], sun["elevation_deg"])
    march = (r // 2, c // 2)  # the 1 m march cell holding it
    assert (bool(cast[march]), bool(own[march])) == (cell["cast"], cell["own"]), cell["why"]


def test_the_fixture_tells_the_likely_wrong_masks_apart():
    """Lesson 34: each likely mistake gives another mask on this fixture."""
    mask = _mask()
    config = _config()
    sun = config["sun"]
    az, el = sun["azimuth_grid_deg"], sun["elevation_deg"]
    h = cell_heights(_surface())
    raw = cast_shadow(h, az, el, config["threshold_m"]) | own_shadow(h, az, el)

    def fine(cells):
        return np.repeat(np.repeat(cells, 2, axis=0), 2, axis=1)

    wrong = {
        "rows flipped": mask[::-1],
        "columns flipped": mask[:, ::-1],
        "half a metre north": np.roll(mask, -1, axis=0),
        "half a metre south": np.roll(mask, 1, axis=0),
        "half a metre east": np.roll(mask, 1, axis=1),
        "half a metre west": np.roll(mask, -1, axis=1),
        "the sun mirrored east-west": _mask(az=360.0 - az),
        "the sun 180 degrees off": _mask(az=az - 180.0),
        "no inset": np.where(fine(raw), 255, 0).astype(np.uint8),
        "the inset at 1 m": fine(inset(raw)),
        "the mask at 1 m": inset(raw),
        "the mean of the four pixels": capture_mask(
            np.repeat(
                np.repeat(_surface().reshape(48, 2, 32, 2).mean(axis=(1, 3)), 2, axis=0), 2, axis=1
            ).astype(np.float32),
            az,
            el,
            config["threshold_m"],
        ),
    }
    for name, other in wrong.items():
        assert other.shape != mask.shape or not np.array_equal(other, mask), name


def test_write_shadows_writes_the_generated_files(tmp_path):
    block = _block()
    config = _config()
    world_sha256 = _sha((FIXTURE / "world.json").read_bytes())
    assert block["world_sha256"] == world_sha256
    written = write_shadows(
        tmp_path, "fixture", _mask(), BOX, world_sha256, block["source"], config["sun"]
    )
    assert written == block
    folder = tmp_path / "shadows"
    assert sorted(p.name for p in folder.iterdir()) == [
        "fixture.json",
        "fixture.png",
        "fixture.png.import",
    ]
    for name in ("fixture.json", "fixture.png", "fixture.png.import"):
        assert (folder / name).read_bytes() == (GENERATED / name).read_bytes(), name
    assert (folder / "fixture.png.import").read_bytes() == KEEP


def test_the_description_is_exactly_its_keys():
    block = _block()
    assert set(block) == {
        "area",
        "cell_m",
        "columns",
        "file",
        "format",
        "lv95_box",
        "pixels_sha256",
        "rows",
        "sha256",
        "source",
        "sun",
        "world_sha256",
    }
    assert (block["area"], block["cell_m"], block["columns"], block["rows"]) == (
        "fixture",
        0.5,
        64,
        96,
    )
    assert (block["file"], block["format"]) == ("shadows/fixture.png", "png-l8")
    assert block["lv95_box"] == dict(zip(("e_min", "e_max", "n_min", "n_max"), BOX, strict=True))
    assert set(block["source"]) == {
        "attribution",
        "collection",
        "dataset",
        "editions",
        "entry_sha256",
    }
    assert block["source"]["dataset"] == "swisssurface3d"
    assert block["sun"] == _config()["sun"]
    assert block["sha256"] == _sha((GENERATED / "fixture.png").read_bytes())
    text = json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert (GENERATED / "fixture.json").read_bytes() == text.encode("utf-8")


def test_the_fixture_config_records_its_inputs_and_its_files():
    config = _config()
    assert list(config["areas"]) == ["fixture"]
    area = config["areas"]["fixture"]
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text("utf-8"))
    entry = lock["datasets"]["swisssurface3d"]
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert area["computed_for"] == {
        "inputs_sha256": _sha(canonical.encode("utf-8")),
        "world_sha256": _sha((FIXTURE / "world.json").read_bytes()),
    }
    assert {t["file"] for t in entry["tiles"].values()} == {"dsm.f32"}
    assert {t["sha256"] for t in entry["tiles"].values()} == {
        _sha((FIXTURE / "dsm.f32").read_bytes())
    }
    assert area["expected_pixels_sha256"] == _block()["pixels_sha256"]
    assert area["expected_png_sha256"] == _sha((GENERATED / "fixture.png").read_bytes())
    assert _block()["source"]["entry_sha256"] == _sha(canonical.encode("utf-8"))
    world = json.loads((FIXTURE / "world.json").read_text("utf-8"))
    assert world["height_offset_m"] != 0
    assert world["areas"]["fixture"] == dict(
        zip(("e_min", "e_max", "n_min", "n_max"), BOX, strict=True)
    )


def _chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    at, found = 8, []
    while at < len(data):
        (length,) = struct.unpack(">I", data[at : at + 4])
        found.append((data[at + 4 : at + 8], data[at + 8 : at + 8 + length]))
        at += 12 + length
    return found


def test_the_png_is_the_surfaces_format_and_zlib_rule():
    rng = np.random.default_rng(3)
    for mask in (_mask(), np.where(rng.random((300, 700)) < 0.3, 255, 0).astype(np.uint8)):
        data = png_mask(mask)
        chunks = _chunks(data)
        kinds = [kind for kind, _ in chunks]
        assert kinds[0] == b"IHDR" and kinds[-1] == b"IEND" and set(kinds[1:-1]) == {b"IDAT"}
        rows, columns = mask.shape
        assert chunks[0][1] == struct.pack(">IIBBBBB", columns, rows, 8, 0, 0, 0, 0)
        idat = [body for kind, body in chunks if kind == b"IDAT"]
        assert all(len(body) <= 1 << 20 for body in idat)
        assert all(len(body) == 1 << 20 for body in idat[:-1])
        scanlines = np.zeros((rows, columns + 1), dtype=np.uint8)
        scanlines[:, 1:] = mask
        assert b"".join(idat) == zlib.compress(scanlines.tobytes(), 9)
        assert np.array_equal(read_png_l8(data), mask)


def test_a_stream_longer_than_1_mib_is_split_into_idat_chunks_of_1_mib(monkeypatch):
    """With level 0 (stored, so fast) a 4000 x 3000 mask's stream is about 12 MB: twelve full
    chunks of 1 MiB and a last shorter one, read back whole."""
    original = zlib.compress  # shadows.zlib is this module: patch with a closure over it
    monkeypatch.setattr(shadows.zlib, "compress", lambda data, level=-1: original(data, 0))
    mask = np.zeros((3000, 4000), dtype=np.uint8)
    mask[1000:2000, 1500:2500] = 255
    data = png_mask(mask)
    idat = [body for kind, body in _chunks(data) if kind == b"IDAT"]
    assert len(idat) == 12 and all(len(body) == 1 << 20 for body in idat[:-1])
    assert 0 < len(idat[-1]) < 1 << 20
    assert np.array_equal(read_png_l8(data), mask)


def test_this_machine_writes_the_designed_png_bytes():
    png = (GENERATED / "fixture.png").read_bytes()
    assert png_mask(read_png_l8(png)) == png, (
        f"this machine's zlib {zlib.ZLIB_RUNTIME_VERSION} writes other PNG bytes than design's"
    )


@pytest.mark.parametrize(
    "pixels",
    [
        np.ones((3, 3), dtype=np.uint8),
        np.full((3, 3), 255, dtype=np.int32),
        np.zeros(9, dtype=np.uint8),
    ],
)
def test_png_mask_refuses_anything_but_a_grid_of_0_and_255(pixels):
    with pytest.raises(ShadowsError):
        png_mask(pixels)


def _broken_configs() -> list:
    good = _config()
    cases = []
    for path, value in [
        (("schema",), 2),
        (("cell_m",), 1),
        (("march_cell_m",), 0.5),
        (("march_cell_m",), None),
        (("threshold_m",), -0.05),
        (("sun", "elevation_deg"), 0.0),
        (("sun", "azimuth_grid_deg"), "184.67"),
        (("areas", "fixture", "expected_pixels_sha256"), "0" * 63),
        (("areas", "fixture", "expected_png_sha256"), None),
        (("areas", "fixture", "computed_for"), {"world_sha256": "0" * 64}),
    ]:
        data = copy.deepcopy(good)
        target = data
        for key in path[:-1]:
            target = target[key]
        if value is None:
            del target[path[-1]]
        else:
            target[path[-1]] = value
        cases.append(data)
    extra = copy.deepcopy(good)
    extra["areas"]["other"] = copy.deepcopy(good["areas"]["fixture"])
    cases.append(extra)
    extra = copy.deepcopy(good)
    extra["sun"]["time"] = "11:40"
    cases.append(extra)
    return cases


@pytest.mark.parametrize("broken", _broken_configs())
def test_a_config_that_is_not_exactly_its_shape_is_refused(broken):
    check_shadows_config(_config())
    with pytest.raises(ShadowsError):
        check_shadows_config(broken)
