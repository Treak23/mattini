"""Pinning tests for brief M4-09: the sky step, `pipeline/mattini/sky.py`.

Pinned decisions (m4-design §4; brief M4-09):
- `SkyError(ValueError)`; `SKY_CONFIG_PATH` (config/sky.json); `load_sky_config(path)` and
  `check_sky_config(data, where)` refuse anything but {"schema": 1, "areas": {<one area>:
  {"computed_for": {"world_sha256": <64 lower-case hex>}, "latitude_deg", "longitude_deg",
  "true_to_grid_deg"}}}, the three values JSON numbers with a fraction (floats, as the
  committed file writes them), finite, |latitude| <= 90, |longitude| <= 180,
  |true_to_grid| <= 10, naming the file.
- `build_sky(world, sky_config, out_dir, *, progress=None) -> dict` checks, in order, the
  config, then `computed_for.world_sha256` against the world config's bytes (a difference is
  design's step: "design recomputes", naming config/sky.json and config/world.json), then the
  area in the world config; then writes `sky/<area>.json` through a `.part` rename: exactly
  {area, latitude_deg, longitude_deg, true_to_grid_deg, world_sha256}, the config's values
  verbatim, as `json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False)` and an LF.
  A refusal writes nothing.
- `built_sky_block(out_dir, sky_config, world, world_sha256) -> dict | None`: None when
  `sky/<area>.json` is absent; else the same checks, then the description must be exactly
  that block (key set, values and their JSON types), or it is refused naming
  `python -m mattini sky`.
- The fixtures that hold a sky config (tests/shared/surroundings_fixture/sky.json,
  shadows_fixture/sky.json; design data, computed with pyproj 3.8.0 / PROJ 9.8.1 as
  config/sky.json was, which the same script reproduced byte for byte) are their world's centre
  by swisstopo's approximate formulas within the tolerances of test_m4_09_sky_config.py, and
  their `generated/sky/fixture.json` is what `build_sky` writes.

Does NOT prove: that the game turns azimuths with these values (brief M4-10).
"""

import copy
import hashlib
import json
import math
import os
from pathlib import Path

import pytest
from test_m4_09_sky_config import WGS84_A, WGS84_E2, _formulas

from mattini.sky import (
    SKY_CONFIG_PATH,
    SkyError,
    build_sky,
    built_sky_block,
    check_sky_config,
    load_sky_config,
)
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
SKY_FIXTURES = ("shadows_fixture", "surroundings_fixture")
BLOCK_KEYS = {"area", "latitude_deg", "longitude_deg", "true_to_grid_deg", "world_sha256"}
SKY_COMMAND = "python -m mattini sky"
FIXTURE_SHA256 = {  # generated/sky/fixture.json, design's
    "shadows_fixture": "4d010fc9b36d78ca77d1b25f2d07f448883c4caaf95316dcd247c8a925afd0fb",
    "surroundings_fixture": "43ae572c6933e9ffdc2bfd92b498e0ef48ddb3a188d3c6dfa48d7ae4a0988bb9",
}


def _text(block: dict) -> bytes:
    return (json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _expected(fixture: Path) -> dict:
    ((area, values),) = json.loads((fixture / "sky.json").read_bytes())["areas"].items()
    return {
        "area": area,
        "latitude_deg": values["latitude_deg"],
        "longitude_deg": values["longitude_deg"],
        "true_to_grid_deg": values["true_to_grid_deg"],
        "world_sha256": hashlib.sha256((fixture / "world.json").read_bytes()).hexdigest(),
    }


@pytest.mark.parametrize("name", SKY_FIXTURES)
def test_build_sky_writes_the_fixture_s_description_exactly(tmp_path, name):
    fixture = SHARED / name
    committed = (fixture / "generated" / "sky" / "fixture.json").read_bytes()
    assert hashlib.sha256(committed).hexdigest() == FIXTURE_SHA256[name]
    block = build_sky(
        load_world(fixture / "world.json"), load_sky_config(fixture / "sky.json"), tmp_path
    )
    assert block == _expected(fixture) and set(block) == BLOCK_KEYS
    assert (tmp_path / "sky" / "fixture.json").read_bytes() == committed == _text(block)
    assert sorted(p.name for p in (tmp_path / "sky").iterdir()) == ["fixture.json"]
    assert type(block["latitude_deg"]) is float and type(block["true_to_grid_deg"]) is float


def test_the_description_goes_through_a_part_rename(tmp_path, monkeypatch):
    fixture = SHARED / "shadows_fixture"
    (tmp_path / "sky").mkdir()
    (tmp_path / "sky" / "fixture.json").write_text("old\n")
    renamed = []
    real = os.replace

    def replace(src, dst):
        renamed.append((Path(src).name, Path(dst).name))
        assert (tmp_path / "sky" / "fixture.json").read_text() == "old\n"
        return real(src, dst)

    monkeypatch.setattr("os.replace", replace)
    build_sky(load_world(fixture / "world.json"), load_sky_config(fixture / "sky.json"), tmp_path)
    assert renamed == [("fixture.json.part", "fixture.json")]


def test_a_sky_config_for_another_world_is_design_s_step_and_writes_nothing(tmp_path):
    """The committed config (the village's world) with a fixture's world."""
    world = load_world(SHARED / "shadows_fixture" / "world.json")
    with pytest.raises(SkyError) as refused:
        build_sky(world, load_sky_config(SKY_CONFIG_PATH), tmp_path / "out")
    message = str(refused.value)
    assert "design recomputes" in message, message
    assert "config/sky.json" in message and "config/world.json" in message, message
    assert SKY_COMMAND not in message
    assert not (tmp_path / "out").exists()


def test_an_area_the_world_does_not_have_is_refused(tmp_path):
    fixture = SHARED / "shadows_fixture"
    config = load_sky_config(fixture / "sky.json")
    config["areas"] = {"elsewhere": config["areas"]["fixture"]}
    with pytest.raises(SkyError, match="elsewhere"):
        build_sky(load_world(fixture / "world.json"), config, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def _committed() -> dict:
    return json.loads(SKY_CONFIG_PATH.read_text(encoding="utf-8"))


def _area(data):
    return next(iter(data["areas"].values()))


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda d: d.update(note="x"), id="top-extra"),
        pytest.param(lambda d: d.update(schema=2), id="schema"),
        pytest.param(lambda d: d["areas"].update(other=_area(d)), id="two-areas"),
        pytest.param(lambda d: d.update(areas={}), id="no-area"),
        pytest.param(lambda d: _area(d).pop("true_to_grid_deg"), id="key-missing"),
        pytest.param(lambda d: _area(d).update(elevation_m=1610.0), id="key-extra"),
        pytest.param(lambda d: _area(d).update(latitude_deg=46), id="an-integer"),
        pytest.param(lambda d: _area(d).update(longitude_deg="7.7"), id="a-string"),
        pytest.param(lambda d: _area(d).update(latitude_deg=91.0), id="latitude-range"),
        pytest.param(lambda d: _area(d).update(longitude_deg=-181.0), id="longitude-range"),
        pytest.param(lambda d: _area(d).update(true_to_grid_deg=12.0), id="convergence-range"),
        pytest.param(lambda d: _area(d)["computed_for"].update(inputs_sha256="a" * 64), id="cf"),
        pytest.param(
            lambda d: _area(d)["computed_for"].update(world_sha256="A" * 64), id="cf-upper"
        ),
    ],
)
def test_a_sky_config_that_is_not_exactly_its_shape_is_refused_naming_the_file(tmp_path, change):
    data = copy.deepcopy(_committed())
    change(data)
    with pytest.raises(SkyError, match="the sky file here"):
        check_sky_config(data, "the sky file here")
    path = tmp_path / "sky.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SkyError, match="sky.json"):
        load_sky_config(path)


def test_the_committed_config_passes():
    check_sky_config(_committed(), "config/sky.json")
    assert load_sky_config() == _committed()


@pytest.mark.parametrize("name", SKY_FIXTURES)
def test_built_sky_block_is_none_until_built_then_the_description(tmp_path, name):
    fixture = SHARED / name
    world, config = load_world(fixture / "world.json"), load_sky_config(fixture / "sky.json")
    sha = hashlib.sha256((fixture / "world.json").read_bytes()).hexdigest()
    assert built_sky_block(tmp_path, config, world, sha) is None
    assert built_sky_block(fixture / "generated", config, world, sha) == _expected(fixture)


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda b: b.update(latitude_deg=b["latitude_deg"] + 1e-7), id="latitude"),
        pytest.param(lambda b: b.update(true_to_grid_deg=-b["true_to_grid_deg"]), id="sign"),
        pytest.param(lambda b: b.update(longitude_deg=round(b["longitude_deg"], 3)), id="rounded"),
        pytest.param(lambda b: b.update(world_sha256="0" * 64), id="world"),
        pytest.param(lambda b: b.pop("area"), id="key-missing"),
        pytest.param(lambda b: b.update(source="pyproj"), id="key-extra"),
    ],
)
def test_a_description_that_is_not_the_config_s_values_names_the_sky_step(tmp_path, change):
    fixture = SHARED / "shadows_fixture"
    block = _expected(fixture)
    change(block)
    (tmp_path / "sky").mkdir()
    (tmp_path / "sky" / "fixture.json").write_bytes(_text(block))
    sha = hashlib.sha256((fixture / "world.json").read_bytes()).hexdigest()
    world, config = load_world(fixture / "world.json"), load_sky_config(fixture / "sky.json")
    with pytest.raises(SkyError) as refused:
        built_sky_block(tmp_path, config, world, sha)
    assert SKY_COMMAND in str(refused.value)


@pytest.mark.parametrize("name", SKY_FIXTURES)
def test_a_fixture_s_sky_is_its_world_s_centre(name):
    fixture = SHARED / name
    raw = (fixture / "world.json").read_bytes()
    world = json.loads(raw)
    data = json.loads((fixture / "sky.json").read_bytes())
    assert set(data) == {"schema", "areas"} and list(data["areas"]) == list(world["areas"])
    (area,) = world["areas"].values()
    (sky,) = data["areas"].values()
    assert sky["computed_for"] == {"world_sha256": hashlib.sha256(raw).hexdigest()}
    east, north = (area["e_min"] + area["e_max"]) / 2, (area["n_min"] + area["n_max"]) / 2
    lat, lon, dlat, dlon = _formulas(east, north)
    assert abs(sky["latitude_deg"] - lat) < 1e-4 and abs(sky["longitude_deg"] - lon) < 1e-4
    phi = math.radians(lat)
    w = math.sqrt(1 - WGS84_E2 * math.sin(phi) ** 2)
    grid_north = math.degrees(
        math.atan2(
            WGS84_A / w * math.cos(phi) * math.radians(dlon),
            WGS84_A * (1 - WGS84_E2) / w**3 * math.radians(dlat),
        )
    )
    assert abs(sky["true_to_grid_deg"] + grid_north) < 0.01, (sky, grid_north)
