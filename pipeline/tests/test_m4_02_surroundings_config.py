"""Pinning tests for brief v0.6.0-04 (brief M4-02 re-scoped by design §1): config/surroundings.json,
design's data (design §1, §5; m4-design §2).

Re-cut from M4-02's pinned file of the same name for 0.6.0: the schema is 2 and the village's
spacing 50 m with the heights of the 50 m mean (design §1); the shape of the area and the
refusals are M4-02's.

Pinned decisions: `{"schema": 2, "areas": {<area>: {...}}}` with exactly one area, whose keys
are exactly `computed_for` ({inputs_sha256, world_sha256}, 64 lower-case hex each, as every
step config), `expected_columns` and `expected_rows` (positive whole numbers),
`expected_lv95_box` (exactly e_max, e_min, n_max, n_min, numbers), `expected_sha256` (the
heights file's SHA-256, 64 lower-case hex), `margin_m` (a whole number of metres, 0 or
more, a multiple of `spacing_m`) and `spacing_m` (a positive whole number of metres).
Schema 1 (M4-02's config, the max at 100 m) is refused, so a step built to M4-02's text cannot
read 0.6.0's config as its own. `load_surroundings_config(path)` and
`check_surroundings_config(data, where)` refuse anything else with a SurroundingsError naming
the file (Hard Rule 2). The colour's keys (design §5) are brief v0.6.0-06's, which re-pins this
file.

The committed village values (design, 2026-11-02, the session's staged design data, byte for
byte): margin 20'000 m, spacing 50 m; the box E 2'603'000–2'645'000, N 1'075'000–1'118'000;
841 columns × 861 rows; the heights `2430baea…` (2'896'404 bytes; 2301 NaN, the area's
interior), measured by design (five summation orders, identical float32 bytes) and by the pin
author (the throwaway step and a block sum of whole centimetres, identical bytes) from the 30
tiles M4-01 locks; `computed_for` the entry `9afdf81d…` and the world `d2607d13…`.

Does NOT prove: that the expected values hold for the committed lock (the lock gains the
`swissaltiregio` entry in brief v0.6.0-01) or for the real tiles (the step's own comparison,
at the brief's real run and the release gate).
"""

import copy
import hashlib
import json

import pytest

from mattini.surroundings import (
    SurroundingsError,
    check_surroundings_config,
    load_surroundings_config,
)
from mattini.world import REPO

CONFIG = REPO / "config" / "surroundings.json"
CONFIG_SHA256 = "85805490a22f454f152094e60ee184ff7370e08250b60629ed8f3ec4a5798d0c"  # the bytes
VILLAGE = {
    "computed_for": {
        "inputs_sha256": "9afdf81d58968b902b85e46b1ef9134dd30040114a73ad16940051246caaf908",
        "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
    },
    "expected_columns": 841,
    "expected_lv95_box": {
        "e_max": 2645000.0,
        "e_min": 2603000.0,
        "n_max": 1118000.0,
        "n_min": 1075000.0,
    },
    "expected_rows": 861,
    "expected_sha256": "2430baea5a4081cfedeb936a5b1da4b3d7fed441c17002c3035f8661bb31e38b",
    "margin_m": 20000,
    "spacing_m": 50,
}


def test_the_committed_config_holds_design_s_village_values():
    assert hashlib.sha256(CONFIG.read_bytes()).hexdigest() == CONFIG_SHA256
    config = load_surroundings_config(CONFIG)
    assert config == {"schema": 2, "areas": {"village": VILLAGE}}
    assert type(VILLAGE["spacing_m"]) is int and type(config["areas"]["village"]["margin_m"]) is int


def test_the_village_box_is_the_world_s_area_grown_by_the_margin_at_the_spacing():
    """Computed here from config/world.json, without the pipeline's code."""
    world = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    area, margin, s = world["areas"]["village"], VILLAGE["margin_m"], VILLAGE["spacing_m"]
    box = {
        "e_max": area["e_max"] + margin,
        "e_min": area["e_min"] - margin,
        "n_max": area["n_max"] + margin,
        "n_min": area["n_min"] - margin,
    }
    assert box == VILLAGE["expected_lv95_box"]
    assert (box["e_max"] - box["e_min"]) / s + 1 == VILLAGE["expected_columns"]
    assert (box["n_max"] - box["n_min"]) / s + 1 == VILLAGE["expected_rows"]


def _changed(change):
    data = {"schema": 2, "areas": {"village": copy.deepcopy(VILLAGE)}}
    change(data, data["areas"]["village"])
    return data


@pytest.mark.parametrize(
    "change",
    [
        lambda d, a: d.update(schema=1),  # M4-02's config
        lambda d, a: d.update(schema=3),
        lambda d, a: d.update(schema=2.0),
        lambda d, a: d["areas"].update(other=copy.deepcopy(a)),
        lambda d, a: d.update(areas={}),
        lambda d, a: d.update(extra=1),
        lambda d, a: a.update(extra=1),
        lambda d, a: a.pop("margin_m"),
        lambda d, a: a.update(margin_m=20025),  # not a multiple of the spacing
        lambda d, a: a.update(margin_m=-50),
        lambda d, a: a.update(margin_m=20000.0),
        lambda d, a: a.update(spacing_m=0),
        lambda d, a: a.update(spacing_m=-50),
        lambda d, a: a.update(spacing_m=50.5),
        lambda d, a: a.update(spacing_m=50.0),
        lambda d, a: a.update(spacing_m=True),
        lambda d, a: a.update(expected_columns=0),
        lambda d, a: a.update(expected_columns=841.0),
        lambda d, a: a.update(expected_rows="861"),
        lambda d, a: a["expected_lv95_box"].pop("n_min"),
        lambda d, a: a["expected_lv95_box"].update(n_min="1075000"),
        lambda d, a: a.update(expected_sha256="2430BAEA" + VILLAGE["expected_sha256"][8:]),
        lambda d, a: a["computed_for"].pop("world_sha256"),
        lambda d, a: a["computed_for"].update(inputs_sha256="0" * 63),
    ],
)
def test_a_malformed_config_is_refused_naming_it(tmp_path, change):
    data = _changed(change)
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SurroundingsError) as refusal:
        load_surroundings_config(path)
    assert str(path) in str(refusal.value)
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(data, "the config here")
    assert "the config here" in str(refusal.value)


def test_a_missing_or_broken_file_is_refused_naming_it(tmp_path):
    path = tmp_path / "surroundings.json"
    with pytest.raises(SurroundingsError, match="surroundings.json"):
        load_surroundings_config(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(SurroundingsError, match="surroundings.json"):
        load_surroundings_config(path)
