"""Pinning tests for brief M3-01 (M2-09 Findings 8): `read_sheet` beyond M2-04's pinned tests.

Design's full replacement of the file brief M2-04's builder wrote (docs/SPEC.md §8
*Reading*); only the comparison of the triangles and the triangle written changed.

The pinned tests (test_buildings_read.py) read one synthetic building and refuse a quad, a
missing UUID and bytes that are not a zip. These add: the features come in reading order
with their UUID and OBJEKTART, and a zip that is not one FileGDB with a `Building_solid`
layer, or a feature with no geometry, is refused naming the sheet (and the UUID where
there is one). The files are FileGDBs that fiona writes (MultiPolygon Z, see
synthetic_sheets.py).

Pinned decision (brief M3-01): each triangle is compared in order, no longer as a set of
points (a reader keeping each ring's closing point, or dropping its first point, passed
the set). The triangle is written clockwise seen from above, which GDAL's writer keeps as
it is (it re-winds the others, keeping the first point; measured with fiona 1.10.1), so
it comes back exactly as written.

Does NOT prove: that swisstopo's own MultiPatch reads the same way (the real run, checked
against design's chunk hashes).
"""

import io
import zipfile

import fiona
import pytest
from fiona.crs import CRS
from synthetic_sheets import sheet_zip

from mattini.buildings import BuildingsError, read_sheet

SHEET = "9999-11"
A, B, C = (
    (2650000.0, 1150000.0, 1500.0),
    (2650010.0, 1150000.0, 1500.0),
    (2650000.0, 1150010.0, 1500.0),
)


def _building(uuid, objektart="Gebaeude Einzelhaus", h=0.0):
    """One triangle, (A, C, B): clockwise seen from above, as GDAL stores a ring."""
    triangle = tuple((e, n, z + h) for e, n, z in (A, C, B))
    return {"uuid": uuid, "objektart": objektart, "triangles": [triangle]}


def test_features_come_in_reading_order_with_their_attributes(tmp_path):
    written = [_building("{Z}", "Kapelle", 1.0), _building("{A}"), _building("{M}", "Im Bau", 2.0)]
    features = read_sheet(sheet_zip(tmp_path, written), SHEET)
    assert [(f["uuid"], f["objektart"]) for f in features] == [
        ("{Z}", "Kapelle"),
        ("{A}", "Gebaeude Einzelhaus"),
        ("{M}", "Im Bau"),
    ]
    # the triangles in order, each its points in ring order, as written (clockwise seen
    # from above, which GDAL's writer keeps; it re-winds the others, measured)
    assert [f["triangles"] for f in features] == [w["triangles"] for w in written]
    assert all(set(f) == {"uuid", "objektart", "triangles"} for f in features)


def _rezip(data: bytes, rename) -> bytes:
    """The zip `data` with every member's name passed through `rename` (None drops it)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as source, zipfile.ZipFile(buffer, "w") as out:
        for name in source.namelist():
            for new in rename(name):
                out.writestr(new, source.read(name))
    return buffer.getvalue()


@pytest.mark.parametrize(
    "rename",
    [
        lambda name: [name, name.replace("synthetic.gdb", "second.gdb")],
        lambda name: [name.replace("synthetic.gdb/", "")],
        lambda name: [name.replace("synthetic.gdb", "synthetic")],
        lambda name: [],
    ],
    ids=["two-gdb-folders", "files-at-the-top", "no-gdb-suffix", "empty"],
)
def test_a_zip_that_is_not_one_filegdb_folder_is_refused(tmp_path, rename):
    data = _rezip(sheet_zip(tmp_path, [_building("{A}")]), rename)
    with pytest.raises(BuildingsError, match=SHEET):
        read_sheet(data, SHEET)


def test_a_filegdb_without_the_building_layer_is_refused(tmp_path):
    data = sheet_zip(tmp_path, [_building("{A}")], layer="Roof_solid")
    with pytest.raises(BuildingsError, match=f"{SHEET}.*Building_solid"):
        read_sheet(data, SHEET)


def test_a_feature_without_geometry_is_refused_naming_its_uuid(tmp_path):
    path = tmp_path / "nothing.gdb"
    schema = {
        "geometry": "3D MultiPolygon",
        "properties": {"UUID": "str:50", "OBJEKTART": "str:25"},
    }
    with fiona.open(
        path,
        "w",
        driver="OpenFileGDB",
        schema=schema,
        crs=CRS.from_epsg(2056),
        layer="Building_solid",
    ) as dst:
        dst.write({"geometry": None, "properties": {"UUID": "{EMPTY}", "OBJEKTART": "x"}})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for file in sorted(path.iterdir()):
            archive.write(file, f"nothing.gdb/{file.name}")
    with pytest.raises(BuildingsError, match=rf"{SHEET}, UUID \{{EMPTY\}}"):
        read_sheet(buffer.getvalue(), SHEET)
