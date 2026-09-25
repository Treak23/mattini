"""Pinning tests for brief M2-04: the buildings rule, case by case (docs/SPEC.md §8).

Pinned decisions (SPEC §8, the buildings): coordinates snapped to the source's storage
grid (E, N to 1 mm, H to 0.1 mm), a coordinate farther than 1 micrometre from it refused;
a building belongs to the area when its bounding-box centre lies in the box, west and south
edges included; its vertices welded by exact equality in first-appearance order; it must
be a closed, consistently oriented triangle mesh with a non-zero signed volume; a negative
volume reverses every triangle (a, b, c) -> (a, c, b), so the output is counter-clockwise
seen from outside; each vertex placed by the world config's to_local in 64-bit and rounded
once to 32-bit (any rotation the world config allows); chunks per 1 km tile of the centre,
buildings ordered by UUID; the file is the vertices (3 x float32 LE each), then the
triangles (3 x uint32 LE each, offset by the building's first vertex in the chunk).

The reference values here are computed by hand from the rule, independently of the code.
Does NOT prove: that the reader hands over what swisstopo's files hold (test_buildings_read.py
and the real run); that the game draws the buildings where the terrain is (M2-05).
"""

import json
import struct
from pathlib import Path

import numpy as np
import pytest
from mattini.buildings import BuildingsError, build_chunks, write_buildings

from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE_WORLD = REPO / "tests" / "shared" / "buildings_fixture" / "world.json"
E0, N0, H0 = 2650950.474, 1149980.125, 1520.1234  # a tetrahedron's corner, on the grids


def _tetra(uuid="{A}", e=E0, n=N0, h=H0, size=3.0, negative=True, objektart="Gebaeude"):
    """A tetrahedron O, X, Y, Z (right angle at O); swisstopo's winding when negative."""
    o, x, y, z = (e, n, h), (e + size, n, h), (e, n + size, h), (e, n, h + size)
    outward = [(o, y, x), (o, x, z), (o, z, y), (x, y, z)]  # counter-clockwise from outside
    triangles = [(a, c, b) for a, b, c in outward] if negative else outward
    return {"uuid": uuid, "objektart": objektart, "triangles": triangles}


def _world(tmp_path=None, axes=None):
    if axes is None:
        return load_world(FIXTURE_WORLD)
    data = json.loads(FIXTURE_WORLD.read_text(encoding="utf-8"))
    data["axes"] = axes
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_world(path)


def _f32(value: float) -> float:
    return float(np.float32(value))


def _local(e: float, n: float, h: float) -> tuple[float, float, float]:
    """The rule by hand for the fixture world (owner's axes): snap, subtract, round once."""
    e, n, h = round(e * 1000) / 1000, round(n * 1000) / 1000, round(h * 10000) / 10000
    return (_f32(e - 2650000.0), _f32(h - 500.0), _f32(-(n - 1150000.0)))


def _vertices(data: bytes, count: int) -> list[tuple[float, float, float]]:
    return [struct.unpack_from("<3f", data, 12 * i) for i in range(count)]


def _triangles(data: bytes, vertices: int, count: int) -> list[tuple[int, int, int]]:
    return [struct.unpack_from("<3I", data, 12 * vertices + 12 * i) for i in range(count)]


def test_a_negative_solid_is_reversed_and_placed():
    (chunk,) = build_chunks([_tetra()], _world(), "fixture")
    assert (chunk["tile"], chunk["buildings"], chunk["vertices"], chunk["triangles"]) == (
        "2650-1149",
        1,
        4,
        4,
    )
    data = chunk["data"]
    assert len(data) == 12 * 4 + 12 * 4
    # first appearance in the input (O, X, Y), (O, Z, X), ...: O 0, X 1, Y 2, Z 3
    assert _vertices(data, 4) == [
        _local(E0, N0, H0),
        _local(E0 + 3.0, N0, H0),
        _local(E0, N0 + 3.0, H0),
        _local(E0, N0, H0 + 3.0),
    ]
    # reversed back to counter-clockwise from outside: (O, Y, X), (O, X, Z), (O, Z, Y), (X, Y, Z)
    assert _triangles(data, 4, 4) == [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


def test_a_positive_solid_is_kept_as_it_is():
    (chunk,) = build_chunks([_tetra(negative=False)], _world(), "fixture")
    # first appearance (O, Y, X), (O, X, Z), ...: O 0, Y 1, X 2, Z 3
    assert _triangles(chunk["data"], 4, 4) == [(0, 1, 2), (0, 2, 3), (0, 3, 1), (2, 1, 3)]


def test_reader_noise_is_snapped_to_the_storage_grid():
    noisy_e = float(np.nextafter(E0, 0.0))  # one 64-bit step below 2650950.474
    noisy_h = float(np.nextafter(H0, 2000.0))
    assert noisy_e != E0 and noisy_h != H0
    clean = build_chunks([_tetra()], _world(), "fixture")
    noisy = build_chunks([_tetra(e=noisy_e, h=noisy_h)], _world(), "fixture")
    assert noisy == clean


@pytest.mark.parametrize(
    "shift", [{"e": E0 + 0.0005}, {"n": N0 - 0.0004}, {"h": H0 + 0.00005}], ids=["e", "n", "h"]
)
def test_a_coordinate_off_the_storage_grid_is_refused(shift):
    with pytest.raises(BuildingsError, match=r"\{A\}"):
        build_chunks([_tetra(**shift)], _world(), "fixture")


def test_placement_follows_any_rotation_of_the_world(tmp_path):
    world = _world(tmp_path, {"x": "+n", "y": "+h", "z": "+e"})
    (chunk,) = build_chunks([_tetra()], world, "fixture")
    # x = +n, y = +h, z = +e: every value on the grids already, so no snapping moves it
    x0, y0, z0 = N0 - 1150000.0, H0 - 500.0, E0 - 2650000.0
    assert _vertices(chunk["data"], 1) == [(_f32(x0), _f32(y0), _f32(z0))]
    # a rotation keeps the orientation: the same triangles as with the owner's axes
    assert _triangles(chunk["data"], 4, 4) == [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


def test_chunks_follow_the_bounding_box_centre_and_uuid_order():
    buildings = [
        _tetra("{C}", e=2650990.0, n=1150010.0),  # centre (2650991.5, 1150011.5): 2650-1150
        _tetra("{B}", e=2650996.0, n=1149980.0),  # centre (2650997.5, ...): 2650-1149
        _tetra("{A}", e=2650998.0, n=1149980.0),  # centre (2650999.5, ...): 2650-1149
        _tetra("{D}", e=2650999.0, n=1149980.0),  # centre (2651000.5, ...): 2651-1149
    ]
    chunks = build_chunks(buildings, _world(), "fixture")
    assert [(c["tile"], c["buildings"]) for c in chunks] == [
        ("2650-1149", 2),
        ("2650-1150", 1),
        ("2651-1149", 1),
    ]
    first = chunks[0]
    # {A} before {B}: A's four vertices first, then B's; B's indices offset by 4
    assert _vertices(first["data"], 8)[0][0] == _f32(2650998.0 - 2650000.0)
    assert _vertices(first["data"], 8)[4][0] == _f32(2650996.0 - 2650000.0)
    assert _triangles(first["data"], 8, 8)[4] == (4, 6, 5)


@pytest.mark.parametrize(
    ("e", "n", "kept"),
    [
        (2650898.5, 1149990.0, True),  # centre E 2650900.0: the west edge, included
        (2651098.5, 1149990.0, False),  # centre E 2651100.0: the east edge, excluded
        (2650950.0, 1149948.5, True),  # centre N 1149950.0: the south edge, included
        (2650950.0, 1150048.5, False),  # centre N 1150050.0: the north edge, excluded
    ],
    ids=["west", "east", "south", "north"],
)
def test_the_area_s_edges(e, n, kept):
    chunks = build_chunks([_tetra(e=e, n=n)], _world(), "fixture")
    assert (sum(c["buildings"] for c in chunks) == 1) is kept


def test_a_uuid_selected_twice_is_refused():
    with pytest.raises(BuildingsError, match=r"\{A\}"):
        build_chunks([_tetra("{A}"), _tetra("{A}", e=2651000.0)], _world(), "fixture")


def test_a_uuid_twice_outside_the_area_does_not_matter():
    outside = _tetra("{A}", e=2652000.0)
    chunks = build_chunks([_tetra("{A}"), outside], _world(), "fixture")
    assert sum(c["buildings"] for c in chunks) == 1


def _broken(change):
    building = _tetra("{BAD}")
    change(building["triangles"])
    return building


@pytest.mark.parametrize(
    "change",
    [
        lambda t: t.pop(),  # open: a face missing
        lambda t: t.__setitem__(0, (t[0][0], t[0][2], t[0][1])),  # one face flipped
        lambda t: t.__setitem__(0, (t[0][0], t[0][0], t[0][1])),  # a repeated vertex
        lambda t: t.append(t[0]),  # a face twice
    ],
    ids=["open", "inconsistent", "degenerate", "duplicated-face"],
)
def test_a_building_that_is_not_a_closed_oriented_solid_is_refused(change):
    with pytest.raises(BuildingsError, match=r"\{BAD\}"):
        build_chunks([_broken(change)], _world(), "fixture")


def test_a_solid_without_volume_is_refused():
    o, x, y = (E0, N0, H0), (E0 + 3.0, N0, H0), (E0, N0 + 3.0, H0)
    flat = {"uuid": "{FLAT}", "objektart": "x", "triangles": [(o, x, y), (o, y, x)]}
    with pytest.raises(BuildingsError, match=r"\{FLAT\}"):
        build_chunks([flat], _world(), "fixture")


def test_write_buildings_writes_the_files_and_the_description(tmp_path):
    chunks = build_chunks(
        [_tetra("{A}"), _tetra("{C}", e=2650990.0, n=1150010.0)], _world(), "fixture"
    )
    box = (2650900.0, 2651100.0, 1149950.0, 1150050.0)
    source = {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swissbuildings3d_3_0",
        "dataset": "swissbuildings3d",
        "edition": "2020",
        "sheets": [{"sha256": "ab" * 32, "sheet": "1249-42"}],
    }
    block = write_buildings(tmp_path, "fixture", chunks, box, "cd" * 32, source)
    assert set(block) == {"area", "chunks", "format", "lv95_box", "source", "world_sha256"}
    assert block["format"] == "mesh-f32-u32-le"
    assert block["lv95_box"] == {
        "e_max": 2651100.0,
        "e_min": 2650900.0,
        "n_max": 1150050.0,
        "n_min": 1149950.0,
    }
    assert [c["tile"] for c in block["chunks"]] == ["2650-1149", "2650-1150"]
    for entry, chunk in zip(block["chunks"], chunks, strict=True):
        assert set(entry) == {"buildings", "file", "sha256", "tile", "triangles", "vertices"}
        assert entry["file"] == f"buildings/{chunk['tile']}.bin"
        assert (tmp_path / entry["file"]).read_bytes() == chunk["data"]
    text = json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert (tmp_path / "buildings" / "fixture.json").read_bytes() == text.encode("utf-8")
    assert not list((tmp_path / "buildings").glob("*.part"))
