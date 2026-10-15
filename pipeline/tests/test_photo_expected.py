"""Pinning tests for brief M3-04: the photo's expected values (config/photo.json).

Pinned decisions (m3-design §2, the expected values; lessons 38 and 41):
config/photo.json is exactly {"schema": 1, "areas": {<area>: {"cell_m",
"computed_for", "expected_pixels_sha256", "expected_sha256"}}}: one area; cell_m one of
0.2, 0.5 and 1; both expected objects keyed by the cell as swisstopo writes a resolution
("0.2", "0.5", "1"), each holding the configured cell, every value 64 lower-case hex
digits; `computed_for` exactly {inputs_sha256, world_sha256}: the SHA-256 of
config/world.json's bytes and `lock.entry_sha256` of the lock's `swissimage` entry. The
village's values were computed by design two independent ways at M3 planning
(2026-10-14): rasterio (GDAL 3.12.4, its libjpeg-turbo 3.1.4) with numpy block sums and
integer rounding, and a TIFF reader of design's own with Pillow's decoder (libjpeg-turbo
3.1.4.1), np.add.reduceat and float64 rint; identical bytes at every cell, and identical
decoded tiles with libjpeg-turbo's SIMD off, SSE2 only and AVX2. The JPEGs: Pillow 12.3.0
(libjpeg-turbo 3.1.4.1); the 0.2 m one byte-identical with Pillow 11.0.0, 10.4.0 and with
SIMD off. A malformed config is a PhotoError naming the file.

Does NOT prove: that the owner's machine computes these bytes (the step compares them).
"""

import json
from pathlib import Path

import pytest

from mattini.photo import PhotoError, load_photo_config

VILLAGE = {
    "cell_m": 0.2,
    "computed_for": {
        "inputs_sha256": "415ed9bcbee7b5d719f40f5b105204dc38ebc570cd2973ebc9de199d86f30fdd",
        "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
    },
    "expected_pixels_sha256": {
        "0.2": "00533bc6d6c2326c7625e09cadd35707f50573b95d33c2072d0aaf80053d35c0",
        "0.5": "1e105d47a15f9c1e43fe211b6d4c717b0f96a190c2e3fc918ce2fc34645fae92",
        "1": "b99f0710ecef8db6af582ea54ad1224fcdd07a9068da6ff8874ddf92ac2d55a5",
    },
    "expected_sha256": {
        "0.2": "cf83c705756c4560ee581de4911242eebca153729dc8ff5540991f9a6ba8ef5b",
        "0.5": "5035fe526a240b225a0d5dcea1a45f7a94a3974e936a3deb8164a07fc3bbf42a",
        "1": "db1d1b786c948aa768d3843fb685ab7daf42bc4401ad43f771320662da22e6a2",
    },
}


def test_the_committed_config_expects_design_s_village():
    assert load_photo_config() == {"schema": 1, "areas": {"village": VILLAGE}}


def _write(tmp_path, area: dict) -> Path:
    path = tmp_path / "photo.json"
    path.write_text(json.dumps({"schema": 1, "areas": {"village": area}}), encoding="utf-8")
    return path


def _with(**change) -> dict:
    area = json.loads(json.dumps(VILLAGE))
    for key, value in change.items():
        if value is None:
            del area[key]
        else:
            area[key] = value
    return area


SHA = VILLAGE["expected_sha256"]["0.2"]


@pytest.mark.parametrize(
    "area",
    [
        _with(cell_m=0.25),
        _with(cell_m=0.1),
        _with(expected_sha256={"0.5": SHA}),
        _with(expected_pixels_sha256={"0.2": SHA, "0.20": SHA}),
        _with(expected_sha256={"0.2": SHA.upper()}),
        _with(computed_for=None),
        _with(note="x"),
    ],
    ids=[
        "cell-0.25",
        "cell-0.1",
        "no-value-for-the-cell",
        "cell-key-written-0.20",
        "upper-case",
        "no-computed-for",
        "extra-key",
    ],
)
def test_a_malformed_config_is_refused_naming_the_file(tmp_path, area):
    path = _write(tmp_path, area)
    with pytest.raises(PhotoError, match=str(path)):
        load_photo_config(path)


def test_another_cell_is_a_config_change(tmp_path):
    path = _write(tmp_path, _with(cell_m=1.0))
    assert load_photo_config(path)["areas"]["village"]["cell_m"] == 1.0
