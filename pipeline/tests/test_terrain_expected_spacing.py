"""The expected SHA-256 is chosen by the configured spacing (brief M2-06; SPEC §8, lesson 38).

A terrain config holds, per spacing, the SHA-256 the heights file must have. Both
`terrain` (before writing) and `manifest` (after) must take the value for the configured
spacing. M2-01's checker found every test config holding a single value, so a step that
took the first value in the object passed the gate. Here the config holds all three,
in the order "0.5", "1", "2", so at 2 m the first value is the 0.5 m one: that twin is
visible (lesson 34). The 2 x 2 tile world of test_terrain_build_tiles.py is built for
real.

The values: 0.5 m and 2 m are design's (test_terrain_build_tiles.py); design computed no
1 m value for this world, so the 1 m value is computed here from the tiles' own heights by
window_mean.py, the independent reference M2-01 uses for synthetic builds, and a test
checks that it gives design's two values from the same source.

Harm prevented: the owner's switch to 2 m or 1 m (a config change, SPEC §7) checked
against another spacing's value: `terrain` refuses a correct build, or accepts heights
that are not design's, and `manifest` then ships them.

Does NOT prove: that the owner's machine computes these bytes (the real village's values
are checked on it by `terrain` itself); anything about the buildings' expected chunks.
"""

import json

import numpy as np
import pytest
from test_terrain_build_tiles import (
    BOX,
    EXPECTED,
    NORTH_KM,
    WEST_KM,
    four_tiles,  # noqa: F401 (a fixture)
    tile_heights,
)
from test_terrain_build_tiles import _config as one_value_config
from window_mean import expected_sha256

from mattini import lock
from mattini.datasets import load_datasets
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, build_terrain

TERRAIN_COMMAND = "python -m mattini terrain"
KEYS = {0.5: "0.5", 1.0: "1", 2.0: "2"}


def _mosaic() -> np.ndarray:
    """The source pixels under the area: the 2 x 2 km block cut by BOX, rows north to south."""
    north = np.concatenate([tile_heights(2623, 1096), tile_heights(2624, 1096)], axis=1)
    south = np.concatenate([tile_heights(2623, 1095), tile_heights(2624, 1095)], axis=1)
    r0, r1 = (round((NORTH_KM * 1000 - BOX[k]) / 0.5) for k in ("n_max", "n_min"))
    c0, c1 = (round((BOX[k] - WEST_KM * 1000) / 0.5) for k in ("e_min", "e_max"))
    return np.concatenate([north, south], axis=0)[r0:r1, c0:c1]


@pytest.fixture(scope="module")
def values():
    """All three expected values of the four-tile world, keyed as swisstopo writes spacings."""
    mosaic = _mosaic()
    # the reference agrees with design's two values, so its 1 m value is the rule's
    for spacing in (0.5, 2.0):
        assert expected_sha256(mosaic, spacing) == EXPECTED[spacing][0], spacing
    return {"0.5": EXPECTED[0.5][0], "1": expected_sha256(mosaic, 1.0), "2": EXPECTED[2.0][0]}


def _config(expected: dict, spacing: float, computed_for: dict) -> dict:
    ordered = {key: expected[key] for key in ("0.5", "1", "2")}  # the order is the point
    area = {"computed_for": computed_for, "expected_sha256": ordered, "spacing_m": spacing}
    return {"schema": 1, "areas": {"village": area}}


def _exchanged(values: dict) -> dict:
    """The 2 m value exchanged for the 0.5 m value: all three still there, two misplaced."""
    return dict(values, **{"0.5": values["2"], "2": values["0.5"]})


def _build(case, config, out):
    return build_terrain(
        case["world"], load_datasets(), case["lock"], config, case["raw_root"], out
    )


def _manifest(case, tmp_path, config, out):
    terrain_path = tmp_path / "terrain.json"
    terrain_path.write_text(json.dumps(config), encoding="utf-8")  # keeps the keys' order
    lock_path = tmp_path / "datasets.lock.json"
    lock.write_lock(case["lock"], lock_path)
    return write_manifest(
        out, case["world"].path, terrain_config_path=terrain_path, lock_path=lock_path
    )


def test_the_three_values_are_three_different_ones(values):
    assert len(set(values.values())) == 3


@pytest.mark.parametrize("spacing", sorted(KEYS))
def test_a_config_holding_all_three_values_builds_and_passes_manifest(
    four_tiles,  # noqa: F811
    values,
    tmp_path,
    spacing,
):
    out = tmp_path / "generated"
    config = _config(values, spacing, four_tiles["computed_for"])
    block = _build(four_tiles, config, out)
    assert block["sha256"] == values[KEYS[spacing]]
    manifest = json.loads(_manifest(four_tiles, tmp_path, config, out).read_bytes())
    assert manifest["terrain"] == block


def test_terrain_refuses_the_2_m_value_exchanged_for_the_0_5_m_value(
    four_tiles,  # noqa: F811
    values,
    tmp_path,
):
    out = tmp_path / "generated"
    with pytest.raises(TerrainError) as refused:
        _build(four_tiles, _config(_exchanged(values), 2.0, four_tiles["computed_for"]), out)
    message = str(refused.value)
    # the heights built are the 2 m ones; the value it compared with, the 0.5 m one
    assert f"SHA-256 {values['2']}" in message, message
    assert f"expects {values['0.5']}" in message, message
    assert not out.exists()  # nothing written


def test_manifest_refuses_the_2_m_value_exchanged_for_the_0_5_m_value(
    four_tiles,  # noqa: F811
    values,
    tmp_path,
):
    """A terrain built right at 2 m; then the config's two values exchanged, no `terrain` run."""
    out = tmp_path / "generated"
    computed_for = four_tiles["computed_for"]
    _build(four_tiles, one_value_config(2.0, values["2"], computed_for), out)
    with pytest.raises(TerrainError) as refused:
        _manifest(four_tiles, tmp_path, _config(_exchanged(values), 2.0, computed_for), out)
    message = str(refused.value)
    for part in (TERRAIN_COMMAND, f"SHA-256 {values['2']}", f"expects {values['0.5']} at 2 m"):
        assert part in message, (part, message)
    assert not (out / "manifest.json").exists()
