"""Pinning tests for brief M3-06: `read_tlm` reads the zipped swissTLM3D FileGDB.

Pinned decisions (m3-design §4, as measured and refined by design on 2026-10-14):
`read_tlm(path, layers, box)` reads the zip at `path` through GDAL's zip access (never
unzipped to disk, never read into memory whole: the national file is 2.88 GB), from its
one `.gdb` folder (swisstopo's member names use backslashes), each layer of `layers`
(layer name -> the integer attributes to hand over, besides UUID). It hands over, per layer
and sorted by UUID, every feature whose 2-D geometry meets the closed `box` (e_min, e_max,
n_min, n_max in metres): a segment of a line or of a ring touches or crosses it, or the box
lies inside a polygon (even-odd over all its rings). Not "its bounding box meets the box":
GDAL's rectangle filter, measured, is a geometry test, so the reader uses it only as a
pre-filter on a box 1 m larger and decides itself, exactly, in whole millimetres. Each
feature is a plain dict {"uuid", "attributes": {name: int}, "geometry": {"type":
"MultiLineString" | "MultiPolygon", "coordinates": ...}}, every (E, N) as whole
millimetres (round(v * 1000), half to even; heights dropped); a coordinate more than
1e-6 m off the 1 mm grid is refused, naming the layer and the UUID.

The shared fixture's source.json is written into a FileGDB here and read back: the
reader must hand over exactly the features its vectors list ('read'), and not the
L-shaped stream whose bounding box meets the box, the road 30 m away or the rock annulus
whose hole holds the box.

Does NOT prove: that swisstopo's national file reads the same way (design read it with
the same rule, 2026-10-14: 843 roads, 230 land-cover polygons and 73 watercourses for
the village, equal to an independent conversion of GDAL's own read).
"""

import json
import zipfile
from pathlib import Path

import pytest
from synthetic_tlm import zipped_tlm

from mattini.surfaces import SurfacesError, read_tlm

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surfaces_fixture"
VECTORS = json.loads((REPO / "tests" / "shared" / "surfaces_vectors.json").read_text("utf-8"))
LAYERS = {
    "TLM_BODENBEDECKUNG": ("OBJEKTART",),
    "TLM_FLIESSGEWAESSER": ("OBJEKTART", "VERLAUF"),
    "TLM_STRASSE": ("BELAGSART", "KUNSTBAUTE", "OBJEKTART"),
}
GROWN = (2700002.0, 2700062.0, 1199961.0, 1200011.0)  # the fixture's area grown by 10 m


def _source() -> dict:
    return json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))


def _expected() -> dict:
    by_uuid = {f["uuid"]: f for features in _source().values() for f in features}
    return {layer: [by_uuid[u] for u in uuids] for layer, uuids in VECTORS["read"].items()}


def test_the_reader_hands_over_the_features_that_meet_the_box(tmp_path):
    path = zipped_tlm(tmp_path, _source())
    names = zipfile.ZipFile(path).namelist()
    assert names and all("\\" in name and "/" not in name for name in names)
    read = read_tlm(path, LAYERS, GROWN)
    assert read == _expected()
    assert sum(len(features) for features in read.values()) == 36
    for features in read.values():
        uuids = [f["uuid"] for f in features]
        assert uuids == sorted(uuids)


def test_a_coordinate_off_the_1_mm_grid_is_refused(tmp_path):
    uuid = VECTORS["read"]["TLM_STRASSE"][0]
    path = zipped_tlm(tmp_path, _source(), nudge=(uuid, 0.0005), xy_scale=10000)
    with pytest.raises(SurfacesError) as refusal:
        read_tlm(path, LAYERS, GROWN)
    assert "TLM_STRASSE" in str(refusal.value) and uuid in str(refusal.value)


def test_a_layer_the_file_lacks_is_refused(tmp_path):
    path = zipped_tlm(tmp_path, _source())
    with pytest.raises(SurfacesError, match="TLM_EISENBAHN"):
        read_tlm(path, {**LAYERS, "TLM_EISENBAHN": ("OBJEKTART",)}, GROWN)


@pytest.mark.parametrize(
    "members",
    [["a.gdb\\a00000001.gdbtable", "b.gdb\\a00000001.gdbtable"], ["readme.txt"]],
    ids=["two-gdb-folders", "no-gdb-folder"],
)
def test_a_zip_without_exactly_one_gdb_folder_is_refused(tmp_path, members):
    path = tmp_path / "odd.gdb.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for name in members:
            info = zipfile.ZipInfo("member")
            info.filename = name
            archive.writestr(info, b"x")
    with pytest.raises(SurfacesError, match="odd.gdb.zip"):
        read_tlm(path, LAYERS, GROWN)
