"""Pinning tests for brief M4-02: config/surroundings.json, design's data (m4-design §2).

Pinned decisions: `{"schema": 1, "areas": {<area>: {...}}}` with exactly one area, whose keys
are exactly `computed_for` ({inputs_sha256, world_sha256}, 64 lower-case hex each, as every
step config), `expected_columns` and `expected_rows` (positive whole numbers),
`expected_lv95_box` (exactly e_max, e_min, n_max, n_min, numbers), `expected_sha256` (the
heights file's SHA-256, 64 lower-case hex), `margin_m` (a whole number of metres, 0 or
more, a multiple of `spacing_m`) and `spacing_m` (a positive whole number of metres).
`load_surroundings_config(path)` and `check_surroundings_config(data, where)` refuse
anything else with a SurroundingsError naming the file (Hard Rule 2).

The committed village values (design, 2026-10-17): margin 20'000 m, spacing 100 m; the box
E 2'603'000–2'645'000, N 1'075'000–1'118'000; 421 columns × 431 rows; the heights
`d317a358…` (725'804 bytes; 551 NaN, the area's interior), computed two independent ways
from the 30 tiles M4-01 locks (numpy; plain Python in whole centimetres), identical bytes.

Does NOT prove: that the expected values hold for the committed lock (brief M4-01's
test_m4_01_expected_inputs.py, once the lock holds the entry) or for the real tiles (the
step's own comparison, at the orchestrator's integration run).
"""

import copy
import json

import pytest

from mattini.surroundings import (
    SurroundingsError,
    check_surroundings_config,
    load_surroundings_config,
)
from mattini.world import REPO

CONFIG = REPO / "config" / "surroundings.json"
VILLAGE = {
    "computed_for": {
        "inputs_sha256": "9afdf81d58968b902b85e46b1ef9134dd30040114a73ad16940051246caaf908",
        "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
    },
    "expected_columns": 421,
    "expected_lv95_box": {
        "e_max": 2645000.0,
        "e_min": 2603000.0,
        "n_max": 1118000.0,
        "n_min": 1075000.0,
    },
    "expected_rows": 431,
    "expected_sha256": "d317a3588f67dcad64350c4b1a471fce016128b17688d6c069fee6f18690f311",
    "margin_m": 20000,
    "spacing_m": 100,
}


def test_the_committed_config_holds_design_s_village_values():
    config = load_surroundings_config(CONFIG)
    assert config == {"schema": 1, "areas": {"village": VILLAGE}}


def _changed(change):
    data = {"schema": 1, "areas": {"village": copy.deepcopy(VILLAGE)}}
    change(data, data["areas"]["village"])
    return data


@pytest.mark.parametrize(
    "change",
    [
        lambda d, a: d.update(schema=2),
        lambda d, a: d["areas"].update(other=copy.deepcopy(a)),
        lambda d, a: d.update(areas={}),
        lambda d, a: a.update(extra=1),
        lambda d, a: a.pop("margin_m"),
        lambda d, a: a.update(margin_m=20050),  # not a multiple of the spacing
        lambda d, a: a.update(margin_m=-100),
        lambda d, a: a.update(margin_m=20000.0),
        lambda d, a: a.update(spacing_m=0),
        lambda d, a: a.update(spacing_m=100.5),
        lambda d, a: a.update(spacing_m=True),
        lambda d, a: a.update(expected_columns=0),
        lambda d, a: a.update(expected_rows="431"),
        lambda d, a: a["expected_lv95_box"].pop("n_min"),
        lambda d, a: a.update(expected_sha256="D317" + VILLAGE["expected_sha256"][4:]),
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
