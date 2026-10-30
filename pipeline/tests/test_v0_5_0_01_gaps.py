"""Guards of brief v0.5.0-01 the pinned tests leave open (Decision 12): the threshold is the
config's, and `built_shadows_block` refuses a world or a lock entry that is not the one the
expected values were computed for, naming design's step.

Does NOT prove: the real village (the brief's real run); the game's reading.
"""

import copy
import json
import math

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from test_m4_03_step import Case, _canonical, _file, _sha, tiles  # noqa: F401  (tiles: fixture)

from mattini.shadows import ShadowsError, built_shadows_block, cast_shadow, own_shadow
from mattini.world import load_world


@pytest.fixture
def case(tmp_path, tiles) -> Case:  # noqa: F811
    return Case(tmp_path, tiles)


def test_the_threshold_is_the_configs_not_the_code_s(case):
    config = copy.deepcopy(case.config)
    config["threshold_m"] = 50.0  # nothing in the fixture casts 50 m above itself
    with pytest.raises(ShadowsError, match="expected_pixels_sha256"):
        case.build(config=config)
    assert not case.out.exists()


def test_the_built_block_refuses_another_world_as_a_design_change(case):
    case.build()
    recorded = case.config["areas"]["fixture"]["computed_for"]["world_sha256"]
    other = "2" * 64
    with pytest.raises(ShadowsError) as caught:
        built_shadows_block(
            case.out, case.config, load_world(case.world_path), other, case.datasets, case.lock
        )
    text = str(caught.value)
    assert recorded in text and other in text and "design" in text, text


def test_the_built_block_refuses_other_inputs_as_a_design_change(case):
    case.build()
    config = copy.deepcopy(case.config)
    config["areas"]["fixture"]["computed_for"]["inputs_sha256"] = "1" * 64
    with pytest.raises(ShadowsError) as caught:
        built_shadows_block(
            case.out,
            config,
            load_world(case.world_path),
            _sha(case.world_path.read_bytes()),
            case.datasets,
            case.lock,
        )
    text = str(caught.value)
    current = _canonical(case.lock["datasets"]["swisssurface3d"])
    assert "1" * 64 in text and current in text and "design" in text, text


def test_the_built_block_refuses_a_sun_that_is_not_the_configs(case):
    case.build()
    description = case.out / "shadows" / "fixture.json"
    block = json.loads(description.read_text("utf-8"))
    block["sun"]["elevation_deg"] = 45.0
    description.write_text(json.dumps(block), "utf-8")
    with pytest.raises(ShadowsError, match="python -m mattini shadows"):
        case.block()


# ------------------------------------------------ the tie rules and the level's float order
# (Decision 1 and Decision 12: the real run's SHA-256 cannot tell these apart on the real data)


def test_a_sample_exactly_at_the_level_casts_no_shadow():
    tan_e = math.tan(math.radians(30.0))
    heights = np.array([[tan_e], [0.0]])  # north of the cell, exactly one step's rise above it
    shadow = cast_shadow(heights, 0.0, 30.0, 0.0)
    assert shadow.tolist() == [[False], [False]]  # `>`, not `>=`
    higher = cast_shadow(np.array([[np.nextafter(tan_e, 1e9)], [0.0]]), 0.0, 30.0, 0.0)
    assert higher.tolist() == [[False], [True]]  # and one ulp above is shadow


def test_a_cell_facing_exactly_edge_on_is_in_own_shadow():
    flat = np.full((3, 3), 7.0)
    assert own_shadow(flat, 123.0, 0.0).all()  # the sun at the horizon: 0 <= 0, `<=` not `<`
    assert not own_shadow(flat, 123.0, 1e-9).any()


def test_the_level_is_the_own_height_plus_the_rise_then_the_threshold():
    own, threshold = 2954.779, 0.16
    tan_e = math.tan(math.radians(30.0))
    level = (own + tan_e) + threshold
    other_order = own + (tan_e + threshold)
    assert level != other_order  # the case is one where the float order shows
    heights = np.array([[other_order], [own]])
    assert cast_shadow(heights, 0.0, 30.0, threshold).tolist() == [[False], [True]]
    heights = np.array([[level], [own]])
    assert cast_shadow(heights, 0.0, 30.0, threshold).tolist() == [[False], [False]]


# ------------------------------------------------ the built block's other comparisons


def _block(case: Case, config=None, lock=None):
    return built_shadows_block(
        case.out,
        config or case.config,
        load_world(case.world_path),
        _sha(case.world_path.read_bytes()),
        case.datasets,
        case.lock if lock is None else lock,
    )


def test_the_built_block_refuses_another_box_in_the_description(case):
    case.build()
    description = case.out / "shadows" / "fixture.json"
    original = description.read_text("utf-8")
    for change in (
        lambda b: b["lv95_box"].update(e_min=b["lv95_box"]["e_min"] + 1.0),
        lambda b: b["lv95_box"].update(n_max=int(b["lv95_box"]["n_max"])),  # int, not float
        lambda b: b["lv95_box"].update(extra=1.0),
        lambda b: b.update(lv95_box=None),
    ):
        block = json.loads(original)
        change(block)
        description.write_text(json.dumps(block), "utf-8")
        with pytest.raises(ShadowsError, match="lv95_box"):
            case.block()


def test_the_built_block_refuses_a_png_that_is_not_the_configs_expected_bytes(case):
    case.build()
    config = copy.deepcopy(case.config)
    config["areas"]["fixture"]["expected_png_sha256"] = "3" * 64
    with pytest.raises(ShadowsError, match="expected_png_sha256"):
        _block(case, config)


def test_the_built_block_refuses_a_mask_that_is_not_the_configs_expected_pixels(case):
    case.build()
    config = copy.deepcopy(case.config)
    config["areas"]["fixture"]["expected_pixels_sha256"] = "4" * 64  # the PNG's value kept
    with pytest.raises(ShadowsError, match="expected_pixels_sha256"):
        _block(case, config)


def test_the_built_block_reads_a_lock_given_as_a_path(case, tmp_path):
    expected = case.build()
    lock_path = tmp_path / "datasets.lock.json"
    lock_path.write_text(json.dumps(case.lock), "utf-8")
    for given in (lock_path, str(lock_path)):
        assert _block(case, lock=given) == expected


@pytest.mark.parametrize("content", [None, b"\xff\xfe", b"{not json"])
def test_the_built_block_refuses_a_lock_path_it_cannot_read(case, tmp_path, content):
    case.build()
    lock_path = tmp_path / "datasets.lock.json"
    if content is not None:
        lock_path.write_bytes(content)
    with pytest.raises(ShadowsError, match="the lock"):
        _block(case, lock=lock_path)


def test_no_lock_is_read_when_nothing_is_built(case, tmp_path):
    assert _block(case, lock=tmp_path / "no-such-lock.json") is None


# ------------------------------------------------ the step's own checks of the tiles


def _rewrite(raw: bytes, *, crs=None, dtype=None, shift=0.0, width=None, pixel=None) -> bytes:
    """The fixture tile with one thing wrong with it."""
    with rasterio.MemoryFile(raw) as memory, memory.open() as ds:
        profile = ds.profile
        values = ds.read(1)
    if crs:
        profile["crs"] = crs
    if shift:
        t = profile["transform"]
        profile["transform"] = from_origin(t.c + shift, t.f, 0.5, 0.5)
    if width:
        values = values[:, :width]
        profile["width"] = width
    if pixel is not None:
        values = values.copy()
        values[20, 1980] = pixel  # inside the area, in the tile 2650-1149
    if dtype:
        values = values.astype(dtype)
        profile["dtype"] = dtype
    with rasterio.MemoryFile() as memory:
        with memory.open(**profile) as ds:
            ds.write(values, 1)
        return memory.read()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"crs": "EPSG:21781"}, "CRS"),
        ({"width": 1999}, "pixels in"),
        ({"dtype": "float64"}, "float32"),
        ({"shift": 0.5}, "top-left corner"),
        ({"pixel": -9999.0}, "not a height"),
        ({"pixel": float("nan")}, "not a height"),
    ],
    ids=["crs", "size", "dtype", "corner", "nodata", "nan"],
)
def test_a_tile_that_is_not_where_its_id_says_is_refused_by_the_step(
    tmp_path,
    tiles,  # noqa: F811
    change,
    message,
):
    bad = dict(tiles)
    bad["2650-1149"] = _rewrite(tiles["2650-1149"], **change)
    case = Case(tmp_path, bad)  # the lock and provenance describe the bad bytes
    with pytest.raises(ShadowsError, match=message):
        case.build()
    assert not case.out.exists()


# ------------------------------------------------ the provenance against the lock


def _edit_provenance(case: Case, change) -> None:
    path = case.folder / "provenance.json"
    provenance = json.loads(path.read_text("utf-8"))
    change(provenance)
    path.write_text(json.dumps(provenance), "utf-8")


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p["tiles"][0].update(sha256="5" * 64),
        lambda p: p["tiles"][0].update(file="swisssurface3d-raster_2020_2650-1149_0.5.tif"),
        lambda p: p["tiles"][0].update(edition="1999"),
        lambda p: p["tiles"].pop(),
        lambda p: p.update(resolution_m=2.0),
    ],
    ids=["sha256", "file", "edition", "tile-list", "resolution"],
)
def test_a_provenance_that_is_not_the_locked_download_is_refused(case, change):
    _edit_provenance(case, change)
    with pytest.raises(ShadowsError, match="python -m mattini download surface"):
        case.build()
    assert case.said == []
    assert not case.out.exists()


def test_a_tile_changed_since_it_was_locked_is_refused_before_it_is_read(case):
    tile = case.folder / _file("2650-1149")
    tile.write_bytes(tile.read_bytes() + b"x")
    with pytest.raises(ShadowsError, match="SHA-256"):
        case.build()
    assert not case.out.exists()


def test_one_missing_tile_is_refused_before_any_progress_line(case):
    (case.folder / _file("2651-1150")).unlink()
    with pytest.raises(ShadowsError, match="is missing") as caught:
        case.build()
    assert "python -m mattini download surface" in str(caught.value)
    assert case.said == []
    assert not case.out.exists()
