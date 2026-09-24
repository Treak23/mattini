"""Pinning tests for brief M0-02: config/world.json and the LV95 <-> Godot transforms.

Pinned decisions (SPEC §6 and §7; CLAUDE.md Hard Rule 4): origin E 2'623'000 /
N 1'096'000, heights unchanged (LN02 metres), x = +E, y = +H, z = -N, 1 unit = 1 m; the
village area box; conversions match the shared vectors the game's tests also use; a
mapping that mirrors or scrambles the world is refused with the file named; the origin
exists in no code file.
"""

import json
import re
from pathlib import Path

import pytest

from mattini.world import WorldConfigError, load_world

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "world.json"
VECTORS = json.loads((REPO / "tests" / "shared" / "world_vectors.json").read_text("utf-8"))
TOL = VECTORS["tolerance_m"]
CODE_SUFFIXES = {".py", ".gd", ".tscn", ".tres", ".cfg", ".json", ".sh"}


def test_config_holds_the_owners_decisions():
    world = load_world()
    assert (world.origin_e, world.origin_n) == (2623000.0, 1096000.0)
    assert world.height_offset == 0.0
    assert world.area("village") == (2623000.0, 2625000.0, 1095000.0, 1098000.0)
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert raw["crs"] == {"horizontal": "EPSG:2056", "vertical": "EPSG:5728"}
    assert raw["axes"] == {"x": "+e", "y": "+h", "z": "-n"}


def test_load_world_reads_the_given_file(tmp_path):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data["origin_lv95"] = {"e": 2600000.0, "n": 1200000.0}
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_world(path).to_local(2600001.0, 1200001.0, 5.0) == pytest.approx((1, 5, -1))


@pytest.mark.parametrize("vec", VECTORS["vectors"], ids=lambda v: v["name"])
def test_to_local_matches_shared_vectors(vec):
    assert load_world().to_local(*vec["lv95"]) == pytest.approx(tuple(vec["local"]), abs=TOL)


@pytest.mark.parametrize("vec", VECTORS["vectors"], ids=lambda v: v["name"])
def test_to_lv95_matches_shared_vectors(vec):
    assert load_world().to_lv95(*vec["local"]) == pytest.approx(tuple(vec["lv95"]), abs=TOL)


def test_mapping_is_a_rotation_not_a_mirror():
    world = load_world()
    base = world.to_local(world.origin_e, world.origin_n, 0.0)

    def step(de, dn, dh):
        moved = world.to_local(world.origin_e + de, world.origin_n + dn, dh)
        return tuple(m - b for b, m in zip(base, moved))

    east, north, up = step(1.0, 0.0, 0.0), step(0.0, 1.0, 0.0), step(0.0, 0.0, 1.0)
    assert east == (1.0, 0.0, 0.0)
    assert up == (0.0, 1.0, 0.0)
    assert north == (0.0, 0.0, -1.0)
    east_x_north = (
        east[1] * north[2] - east[2] * north[1],
        east[2] * north[0] - east[0] * north[2],
        east[0] * north[1] - east[1] * north[0],
    )
    assert east_x_north == up  # right-handed before and after the mapping


def _broken_copy(tmp_path, mutate):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    mutate(data)
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["axes"].update(z="+n"),
        lambda d: d["axes"].update(y="+e"),
        lambda d: d["axes"].pop("y"),
        lambda d: d["crs"].update(horizontal="EPSG:21781"),
        lambda d: d.update(schema=2),
        lambda d: d["areas"]["village"].update(e_min=2626000.0),
    ],
    ids=["mirror", "axis-used-twice", "axis-missing", "lv03-crs", "unknown-schema", "empty-area"],
)
def test_bad_config_is_refused_with_the_file_named(tmp_path, mutate):
    path = _broken_copy(tmp_path, mutate)
    with pytest.raises(WorldConfigError, match=re.escape(str(path))):
        load_world(path)


def test_origin_numbers_live_only_in_config():
    """Census for Hard Rule 4. Proves text only: no code file spells the origin."""
    pattern = re.compile(r"2[' _]?623[' _]?000|1[' _]?096[' _]?000")
    skip = {"addons", "tests", "generated", ".godot"}
    offenders = []
    for root in (REPO / "pipeline" / "mattini", REPO / "game", REPO / "tools"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or skip.intersection(path.relative_to(REPO).parts):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if path.suffix in CODE_SUFFIXES and pattern.search(text):
                offenders.append(str(path.relative_to(REPO)))
    assert offenders == [], offenders
