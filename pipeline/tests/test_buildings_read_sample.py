"""Pinning tests for brief M2-09: `read_sheet` reads swisstopo's own file, a real sample.

Pinned decisions (docs/SPEC.md §8, the buildings, *Reading*): as test_buildings_read.py,
on a real sheet. The sample is swissBUILDINGS3D 3.0, edition 2020, sheet 1328-33 (three
buildings, 45'668 bytes, © swisstopo), committed as a test fixture by the owner's word of
2026-09-25 (SPEC §13 row 24): only a real file holds an Esri MultiPatch.

Does NOT prove: that another edition or a larger sheet reads the same way (the real run
over the village's six sheets, checked against design's chunk hashes, does).
"""

import hashlib
from pathlib import Path

from mattini.buildings import read_sheet

REPO = Path(__file__).resolve().parents[2]
SAMPLE = (
    REPO
    / "tests"
    / "shared"
    / "buildings_sample"
    / "swissbuildings3d_3_0_2020_1328-33_2056_5728.gdb.zip"
)
SAMPLE_SHA256 = "72b2502856d315b9f265f8279a9491cfa3f45065a42cc492824fd9731d7c4292"
EXPECTED = [  # uuid, triangles, the first triangle's first point on the storage grid
    ("{B1DC7692-3FBD-4ADF-AEB5-1319B8B50BD2}", 112, (2622709.731, 1098156.074, 2828.6409)),
    ("{5DBC090C-8375-428D-AA75-3EB575FE5F00}", 128, (2620023.258, 1099703.89, 3204.5369)),
    ("{EEC39B2D-5F82-4738-8D83-6301D695D3F6}", 84, (2622659.455, 1100386.429, 3163.127)),
]


def _snap(point):
    e, n, h = point
    return (round(e * 1000) / 1000, round(n * 1000) / 1000, round(h * 10000) / 10000)


def test_the_sample_is_the_published_file():
    data = SAMPLE.read_bytes()
    assert len(data) == 45668
    assert hashlib.sha256(data).hexdigest() == SAMPLE_SHA256


def test_the_real_sheet_reads_in_order_as_triangles():
    features = read_sheet(SAMPLE.read_bytes(), "1328-33")
    assert [(f["uuid"], len(f["triangles"])) for f in features] == [
        (uuid, count) for uuid, count, _ in EXPECTED
    ]
    for feature, (_, _, first) in zip(features, EXPECTED, strict=True):
        assert feature["objektart"] == "Gebaeude Einzelhaus"
        for triangle in feature["triangles"]:
            assert len(triangle) == 3
            for point in triangle:
                assert len(point) == 3 and all(isinstance(v, float) for v in point)
                snapped = _snap(point)
                assert max(abs(a - b) for a, b in zip(point, snapped, strict=True)) < 1e-6
        assert _snap(feature["triangles"][0][0]) == first
