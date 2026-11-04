"""Guards of brief v0.6.0-07 the pinned tests leave open (decision 12; the batch gate's prover).

The pinned copies state what the wiring must do; they leave open six things that no pin tells
from their absence (each probe changed the code and left the pins green):

- *A surroundings config without the area* is a DownloadError naming config/surroundings.json and
  the area (decision 2), at every caller that is given the config: the lock's fit for both far
  datasets, `lock.regio_entry` and `lock.farphoto_entry` (before the first request) and the two
  downloads; never a KeyError.
- *The manifest's colour fits swissaltiregio, then swissimage_far* (decision 5, "sorted"): the
  colour's description alone, with both entries unfitting, is refused naming `lock regio`.
- *`farcolour` asks the same two fits in that order* (decision 6) and `shape_problem` after
  them, once: a lock that fits neither and is malformed too is refused with the first fit's text;
  one that fits and is malformed is refused with the lock's shape text.
- *`surroundings` asks `fit_problem` before `shape_problem`* (decision 6), for the step and for the
  built block: a lock that does not fit and is malformed too is refused with fit_problem's text,
  which names `lock regio` alone.
- *The colour without the heights* is refused after the colour's own checks 1 to 3 (decision 4
  leaves its place to the builder): a lock that does not fit is refused with the fit's text, not
  with the missing heights.

The manifest's `.part` rename (the pin author's third probe) is held by the full suite:
test_m3_13_commands.py's two cases for `write_manifest`, which the new key does not touch.

Does NOT prove: that these are the only unpinned orders (the batch gate's prover looks for more).
"""

import copy
import json
import re

import pytest
import synthetic_farphoto
from computed_for import recorded
from synthetic_regio import FIXTURE, fixture_datasets, raw_regio

from mattini import download, lock
from mattini.farcolour import FarColourError, build_farcolour
from mattini.lock import shape_problem, write_lock
from mattini.manifest import build_manifest
from mattini.surroundings import (
    SurroundingsError,
    build_surroundings,
    built_surroundings_block,
    load_surroundings_config,
)
from mattini.world import REPO, load_world

REGIO = "swissaltiregio"
FAR = "swissimage_far"
LOCK_REGIO = "python -m mattini lock regio"
LOCK_FAR = "python -m mattini lock farphoto"
COMMAND = re.compile(r"python -m mattini (?:(?:lock|download) )?[a-z]+")
FAR_FIXTURE = synthetic_farphoto.FIXTURE
CONFIG = REPO / "config"
AREA = "village"


def _no_network(*args, **kwargs):
    raise AssertionError("the call reached for the network")


# ---------------------------------------------------------- a config without the area


def _config_without(area: str) -> dict:
    """A surroundings config (as the reader returns it) that has settings for another area."""
    return {"schema": 2, "areas": {"elsewhere": {"margin_m": 3000, "spacing_m": 50}}}


def _far_inputs():
    """The far colour fixture's world, datasets config and lock: it has both far datasets."""
    return (
        load_world(FAR_FIXTURE / "world.json"),
        synthetic_farphoto.fixture_datasets(),
        json.loads((FAR_FIXTURE / "datasets.lock.json").read_text(encoding="utf-8")),
    )


@pytest.mark.parametrize("dataset", [REGIO, FAR])
def test_the_fit_refuses_a_config_without_the_area_naming_the_file_and_the_area(dataset):
    world, datasets, pinned = _far_inputs()
    with pytest.raises(download.DownloadError) as refusal:
        lock.fit_problem(
            pinned,
            datasets,
            world,
            "fixture",
            dataset,
            surroundings=_config_without("fixture"),
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "'fixture'" in text, text


@pytest.mark.parametrize("entry", ["regio_entry", "farphoto_entry"])
def test_an_entry_refuses_a_config_without_the_area_before_the_first_request(entry):
    world, datasets, _ = _far_inputs()
    with pytest.raises(download.DownloadError) as refusal:
        getattr(lock, entry)(
            world,
            datasets,
            _no_network,
            area="fixture",
            surroundings=_config_without("fixture"),
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "'fixture'" in text, text


@pytest.mark.parametrize("run", ["download_regio", "download_farphoto"])
def test_a_download_refuses_a_config_without_the_area_before_anything_is_asked(tmp_path, run):
    world, datasets, pinned = _far_inputs()
    with pytest.raises(download.DownloadError) as refusal:
        getattr(download, run)(
            world,
            datasets,
            tmp_path / "raw",
            _no_network,
            _no_network,
            lock=pinned,
            area="fixture",
            surroundings=_config_without("fixture"),
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "'fixture'" in text, text
    assert not (tmp_path / "raw").exists()


# ------------------------------------------------------- the lock to break in two ways


def _one_regio_tile_more(pinned: dict) -> None:
    tiles = pinned["datasets"][REGIO]["tiles"]
    first, second = max(tiles).split("-")
    tiles[f"{int(first) + 10:04d}-{second}"] = copy.deepcopy(tiles[max(tiles)])


def _one_far_cell_more(pinned: dict) -> None:
    entry = pinned["datasets"][FAR]
    entry["absent"] = sorted([*entry["absent"], "2700-1200"])


def _a_pin_with_an_extra_key(pinned: dict, dataset: str = REGIO) -> None:
    tiles = pinned["datasets"][dataset]["tiles"]
    tiles[min(tiles)]["size_bytes"] = 1


# ------------------------------------------ the manifest's colour: regio's fit, then the far one


def test_the_manifest_s_colour_fits_swissaltiregio_before_swissimage_far(tmp_path):
    """Both entries do not fit and only the colour's description is built (the heights' checks do
    not run): the refusal is the first fit's, `lock regio`."""
    pinned = json.loads((CONFIG / "datasets.lock.json").read_text(encoding="utf-8"))
    _one_regio_tile_more(pinned)
    _one_far_cell_more(pinned)
    out = tmp_path / "out"
    (out / "surroundings").mkdir(parents=True)
    (out / "surroundings" / f"{AREA}_colour.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        build_manifest(
            CONFIG / "world.json", out, lock_path=write_lock(pinned, tmp_path / "lock.json")
        )
    assert set(COMMAND.findall(str(refusal.value))) == {LOCK_REGIO}, str(refusal.value)


def test_the_colour_without_the_heights_is_refused_after_its_own_checks_one_to_three(tmp_path):
    """A lock that does not fit: the fit's refusal comes before the missing heights'."""
    pinned = json.loads((CONFIG / "datasets.lock.json").read_text(encoding="utf-8"))
    _one_far_cell_more(pinned)
    out = tmp_path / "out"
    (out / "surroundings").mkdir(parents=True)
    (out / "surroundings" / f"{AREA}_colour.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        build_manifest(
            CONFIG / "world.json", out, lock_path=write_lock(pinned, tmp_path / "lock.json")
        )
    assert set(COMMAND.findall(str(refusal.value))) == {LOCK_FAR}, str(refusal.value)


# ----------------------------------------------- farcolour: both fits in order, then the shape


def _far_config(made: dict) -> dict:
    """The far colour fixture's config (its colour records the fixture's inputs)."""
    return load_surroundings_config(FAR_FIXTURE / "surroundings.json")


def _far_fit(pinned: dict, dataset: str) -> str | None:
    return lock.fit_problem(
        pinned,
        synthetic_farphoto.fixture_datasets(),
        load_world(FAR_FIXTURE / "world.json"),
        "fixture",
        dataset,
        surroundings=_far_config(pinned),
    )


def _build_far(tmp_path, pinned: dict, root) -> str:
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            load_world(FAR_FIXTURE / "world.json"),
            synthetic_farphoto.fixture_datasets(),
            pinned,
            _far_config(pinned),
            root,
            tmp_path / "out",
        )
    assert not (tmp_path / "out").exists()
    return str(refusal.value)


def test_the_far_colour_asks_the_regio_fit_before_the_far_one(tmp_path):
    root, made = synthetic_farphoto.raw_inputs(tmp_path / "raw")
    pinned = copy.deepcopy(made)
    _one_regio_tile_more(pinned)
    _one_far_cell_more(pinned)
    text = _build_far(tmp_path, pinned, root)
    assert text == _far_fit(pinned, REGIO), text
    assert _far_fit(pinned, FAR) not in (None, text)  # the far fit would have said another thing


def test_the_far_colour_asks_both_fits_before_the_lock_s_shape(tmp_path):
    """The far fit refuses and a pin of the regio entry is malformed too: the fit's text."""
    root, made = synthetic_farphoto.raw_inputs(tmp_path / "raw")
    pinned = copy.deepcopy(made)
    _one_far_cell_more(pinned)
    _a_pin_with_an_extra_key(pinned, REGIO)
    text = _build_far(tmp_path, pinned, root)
    assert text == _far_fit(pinned, FAR), text
    assert shape_problem(pinned) not in (None, text)
    assert set(COMMAND.findall(text)) == {LOCK_FAR}, text


def test_the_far_colour_refuses_a_malformed_lock_that_fits_with_the_lock_s_shape_text(tmp_path):
    root, made = synthetic_farphoto.raw_inputs(tmp_path / "raw")
    pinned = copy.deepcopy(made)
    _a_pin_with_an_extra_key(pinned, REGIO)
    assert _far_fit(pinned, REGIO) is None and _far_fit(pinned, FAR) is None
    text = _build_far(tmp_path, pinned, root)
    assert text == shape_problem(pinned) and "size_bytes" not in text, text
    assert "must have exactly the keys" in text, text


# --------------------------------------------- surroundings: the fit, then the lock's shape


def _unfit_and_malformed(made: dict) -> dict:
    pinned = copy.deepcopy(made)
    _one_regio_tile_more(pinned)
    _a_pin_with_an_extra_key(pinned, REGIO)
    return pinned


def _fixture_world():
    return load_world(FIXTURE / "world.json")


def _fit(pinned: dict, config: dict) -> str | None:
    return lock.fit_problem(
        pinned, fixture_datasets(), _fixture_world(), "fixture", REGIO, surroundings=config
    )


def test_the_step_asks_the_fit_before_the_lock_s_shape(tmp_path):
    root, made = raw_regio(tmp_path / "raw")
    pinned = _unfit_and_malformed(made)
    config = recorded(
        load_surroundings_config(FIXTURE / "surroundings.json"), _fixture_world(), made, REGIO
    )
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _fixture_world(), fixture_datasets(), pinned, config, root, tmp_path / "out"
        )
    text = str(refusal.value)
    assert text == _fit(pinned, config), text
    assert shape_problem(pinned) not in (None, text)
    assert set(COMMAND.findall(text)) == {LOCK_REGIO}, text
    assert not (tmp_path / "out").exists()


def test_the_built_block_asks_the_fit_before_the_lock_s_shape():
    out = FIXTURE / "generated"
    config = load_surroundings_config(FIXTURE / "surroundings.json")
    world_sha256 = json.loads((out / "surroundings" / "fixture.json").read_bytes())["world_sha256"]
    made = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    pinned = _unfit_and_malformed(made)
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(
            out, config, _fixture_world(), world_sha256, fixture_datasets(), pinned
        )
    text = str(refusal.value)
    assert text == _fit(pinned, config), text
    assert shape_problem(pinned) not in (None, text)
    assert set(COMMAND.findall(text)) == {LOCK_REGIO}, text


def test_the_step_refuses_a_malformed_lock_that_fits_with_the_lock_s_shape_text(tmp_path):
    root, made = raw_regio(tmp_path / "raw")
    pinned = copy.deepcopy(made)
    _a_pin_with_an_extra_key(pinned, REGIO)
    config = recorded(
        load_surroundings_config(FIXTURE / "surroundings.json"), _fixture_world(), made, REGIO
    )
    assert _fit(pinned, config) is None
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _fixture_world(), fixture_datasets(), pinned, config, root, tmp_path / "out"
        )
    assert str(refusal.value) == shape_problem(pinned)
    assert not (tmp_path / "out").exists()
