"""Pinning tests for brief M2-04: `read_sheet` reads a zipped FileGDB and refuses what the rule refuses.

Pinned decisions (docs/SPEC.md §8, the buildings, *Reading*): a sheet is read from the very
bytes whose SHA-256 was checked (fiona's ZipMemoryFile), its one `.gdb` folder, layer
`Building_solid`; every feature gives its UUID, its OBJEKTART and its triangles as three
(E, N, H) points each, in reading order, not snapped; a feature without a UUID, or with a
polygon that is not one closed four-point ring, is refused naming the sheet and the UUID.
The files here are synthetic FileGDBs that fiona writes: MultiPolygon Z, not the Esri
MultiPatch swisstopo's files hold, because GDAL cannot write a MultiPatch (measured).

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
    (2650000.0, 1150000.0, 1510.0),
)


def test_a_synthetic_sheet_reads_its_triangles(tmp_path):
    data = _synthetic_zip(tmp_path, [("{S}", [[A, B, C, A], [A, B, D, A]])])
    (feature,) = read_sheet(data, "9999-11")
    assert feature["uuid"] == "{S}"
    assert len(feature["triangles"]) == 2
    assert {tuple(p) for t in feature["triangles"] for p in t} == {A, B, C, D}


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
