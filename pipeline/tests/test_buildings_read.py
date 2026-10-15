"""Pinning tests for briefs M2-04 and M3-01: `read_sheet` reads a zipped FileGDB, refusing what the rule refuses.

Pinned decisions (docs/SPEC.md §8, the buildings, *Reading*): a sheet is read from the very
bytes whose SHA-256 was checked (fiona's ZipMemoryFile), its one `.gdb` folder, layer
`Building_solid`; every feature gives its UUID, its OBJEKTART and its triangles as three
(E, N, H) points each, in reading order, not snapped; a feature without a UUID, or with a
polygon that is not one closed four-point ring, is refused naming the sheet and the UUID.
The files here are synthetic FileGDBs that fiona writes: MultiPolygon Z, not the Esri
MultiPatch swisstopo's files hold, because GDAL cannot write a MultiPatch (measured).

Since brief M3-01 (M2-09 Findings 8; design's full replacement of M2-04's file) the
triangles are compared in order, each its three points in ring order, no longer as a set
of points: a reader that kept each ring's closing point, or dropped its first point
instead, passed the set. GDAL's writer stores a ring clockwise seen from above and keeps
its first point (measured with fiona 1.10.1: (A, B, C) comes back as (A, C, B)); the
triangles here are clockwise already and do not overlap seen from above, so they come
back exactly as written.

Does NOT prove: that swisstopo's own MultiPatch reads the same way (the real sample's test,
or the real run checked against design's chunk hashes).
"""

import io
import zipfile
from pathlib import Path

import fiona
import pytest
from fiona.crs import CRS

from mattini.buildings import BuildingsError, read_sheet

REPO = Path(__file__).resolve().parents[2]


def _synthetic_zip(tmp_path, features, name="probe.gdb") -> bytes:
    """A zipped FileGDB written by fiona: MultiPolygon Z, not a MultiPatch."""
    folder = tmp_path / name
    schema = {
        "geometry": "3D MultiPolygon",
        "properties": {"UUID": "str:50", "OBJEKTART": "str:25"},
    }
    with fiona.open(
        folder,
        "w",
        driver="OpenFileGDB",
        schema=schema,
        crs=CRS.from_epsg(2056),
        layer="Building_solid",
    ) as dst:
        for uuid, rings in features:
            dst.write(
                {
                    "geometry": {"type": "MultiPolygon", "coordinates": [[r] for r in rings]},
                    "properties": {"UUID": uuid, "OBJEKTART": "Gebaeude Einzelhaus"},
                }
            )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in sorted(folder.iterdir()):
            archive.write(path, f"{name}/{path.name}")
    return buffer.getvalue()


A, B, C, D = (
    (2650000.0, 1150000.0, 1500.0),
    (2650010.0, 1150000.0, 1500.0),
    (2650000.0, 1150010.0, 1500.0),
    (2650010.0, 1150010.0, 1504.0),
)
# Two triangles, clockwise seen from above, sharing the edge B-C, starting at different
# points: in order, a rotation, a reversal or a kept closing point each differ.
FIRST, SECOND = (A, C, B), (B, C, D)


def test_a_synthetic_sheet_reads_its_triangles(tmp_path):
    data = _synthetic_zip(tmp_path, [("{S}", [[*FIRST, FIRST[0]], [*SECOND, SECOND[0]]])])
    (feature,) = read_sheet(data, "9999-11")
    assert feature["uuid"] == "{S}"
    assert feature["triangles"] == [FIRST, SECOND]
    assert all(type(t) is tuple and len(t) == 3 for t in feature["triangles"])


@pytest.mark.parametrize(
    ("uuid", "rings", "needle"),
    [
        ("{QUAD}", [[A, B, D, C, A]], "{QUAD}"),
        ("", [[A, B, C, A]], "9999-11"),
    ],
    ids=["a-quad", "no-uuid"],
)
def test_what_is_not_a_triangle_or_has_no_uuid_is_refused(tmp_path, uuid, rings, needle):
    data = _synthetic_zip(tmp_path, [(uuid, rings)])
    with pytest.raises(BuildingsError) as refusal:
        read_sheet(data, "9999-11")
    assert needle in str(refusal.value) and "9999-11" in str(refusal.value)


def test_bytes_that_are_not_a_zipped_filegdb_are_refused():
    with pytest.raises(BuildingsError, match="9999-11"):
        read_sheet(b"not a zip", "9999-11")
