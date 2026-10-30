"""Guards of brief v0.5.0-01 the pinned tests leave open (Decision 12): the threshold is the
config's, and `built_shadows_block` refuses a world or a lock entry that is not the one the
expected values were computed for, naming design's step.

Does NOT prove: the real village (the brief's real run); the game's reading.
"""

import copy
import json

import pytest
from test_m4_03_step import Case, _canonical, _sha, tiles  # noqa: F401  (tiles is a fixture)

from mattini.shadows import ShadowsError, built_shadows_block
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
