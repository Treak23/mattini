"""Malformed world configs are refused with the file named (Hard Rules 2 and 4).

Complements the pinned refusals (brief M0-02) with the malformations a hand edit can
produce: unreadable file, broken JSON, duplicate keys, non-numbers, unknown or missing
keys, empty boxes, malformed axis specs.
"""

import json
import re
from pathlib import Path

import pytest

from mattini.world import WorldConfigError, load_world

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / "config" / "world.json"


def _write(tmp_path, text):
    path = tmp_path / "world.json"
    path.write_text(text, encoding="utf-8")
    return path


def _mutated(tmp_path, mutate):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    mutate(data)
    return _write(tmp_path, json.dumps(data))


def test_missing_file_is_refused_with_the_file_named(tmp_path):
    path = tmp_path / "absent.json"
    with pytest.raises(WorldConfigError, match=re.escape(str(path))):
        load_world(path)


@pytest.mark.parametrize(
    "text",
    [
        "{",
        "[]",
        CONFIG.read_text(encoding="utf-8").replace('"schema": 1,', '"schema": 1, "schema": 1,'),
        CONFIG.read_text(encoding="utf-8").replace(
            '"height_offset_m": 0.0', '"height_offset_m": NaN'
        ),
        CONFIG.read_text(encoding="utf-8").replace('"n_max": 1098000.0', '"n_max": Infinity'),
    ],
    ids=["broken-json", "not-an-object", "duplicate-key", "nan", "infinity"],
)
def test_malformed_json_is_refused_with_the_file_named(tmp_path, text):
    path = _write(tmp_path, text)
    with pytest.raises(WorldConfigError, match=re.escape(str(path))):
        load_world(path)


def _set(*keys, value):
    def mutate(d):
        for key in keys[:-1]:
            d = d[key]
        d[keys[-1]] = value

    return mutate


def _drop(*keys):
    def mutate(d):
        for key in keys[:-1]:
            d = d[key]
        del d[keys[-1]]

    return mutate


@pytest.mark.parametrize(
    "mutate",
    [
        _set("schema", value=True),
        _set("schema", value="1"),
        _set("crs", "vertical", value="EPSG:5773"),
        _set("crs", "extra", value="x"),
        _set("origin_lv95", "e", value="2600000"),
        _set("origin_lv95", "n", value=None),
        _set("origin_lv95", "n", value=10**400),
        _drop("origin_lv95", "e"),
        _set("height_offset_m", value=False),
        _drop("height_offset_m"),
        _set("origin", value={"e": 0.0, "n": 0.0}),
        _set("axes", "w", value="+e"),
        _set("axes", "x", value="e"),
        _set("axes", "x", value="+x"),
        _set("axes", "x", value="++e"),
        _set("axes", "x", value=1),
        _set("areas", value=[]),
        _set("areas", "village", "n_max", value=1095000.0),
        _drop("areas", "village", "n_min"),
        _set("areas", "village", "top", value=5.0),
        _set("areas", "village", value=None),
    ],
    ids=[
        "schema-bool",
        "schema-string",
        "vertical-crs",
        "crs-extra-key",
        "origin-string",
        "origin-null",
        "origin-overflow",
        "origin-missing",
        "height-offset-bool",
        "height-offset-missing",
        "unknown-top-level-key",
        "unknown-game-axis",
        "unsigned-axis",
        "unknown-source-axis",
        "double-sign",
        "axis-not-a-string",
        "areas-not-an-object",
        "empty-area-north-south",
        "area-key-missing",
        "area-key-unknown",
        "area-not-an-object",
    ],
)
def test_bad_values_are_refused_with_the_file_named(tmp_path, mutate):
    path = _mutated(tmp_path, mutate)
    with pytest.raises(WorldConfigError, match=re.escape(str(path))):
        load_world(path)


def test_unknown_area_is_an_error_naming_the_file():
    world = load_world()
    with pytest.raises(WorldConfigError, match=re.escape(str(CONFIG))):
        world.area("matterhorn")


def test_integer_numbers_are_accepted_as_floats(tmp_path):
    path = _mutated(tmp_path, _set("origin_lv95", value={"e": 2600000, "n": 1200000}))
    world = load_world(path)
    assert (world.origin_e, world.origin_n) == (2600000.0, 1200000.0)
    assert all(type(v) is float for v in world.to_local(2600000, 1200000, 0))
