"""Guards of brief v0.6.0-07 the pinned tests leave open (decision 12; the batch gate's prover).

The pinned copies state what the wiring must do; they leave open these things, which no pin tells
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

- *A datasets config without a dataset a built block reads* (the fixer round's X17): the
  manifest's `_inputs_check` turns `download.dataset_of`'s DownloadError (a RuntimeError, which no
  step's error class is) into the step's own refusal, naming config/datasets.json and the
  dataset, for every block the manifest checks and every dataset it reads, the surroundings'
  two halves included.
- *A built colour whose area holds no `colour` block* (the fixer round's X27): the colour is
  optional in config/surroundings.json, so `checked` cannot compare its `computed_for`; the
  description is still refused (naming config/surroundings.json when the heights are built,
  the missing heights when they are not), never dropped to a null block.
- *A DownloadError out of the lock's fit* (the second fixer round's E35 and E36): `surroundings`
  (the step and the built block, which share `_lock_problem`) and `farcolour` (likewise, through
  `_checked`, both fits) turn it into their own refusal with its text, decision 6. The steps'
  own readers of the datasets config refuse its faults first, so no datasets config reaches
  the conversion; the tests raise the DownloadError from inside the fit with a stand-in tile
  rule, as the pins replace the rules.
- *A built block for an area the world config lacks* (the second fixer round's E38): the
  manifest's `_inputs_check` makes no lock fit for it (the tile rules read the area's box and
  raise a WorldConfigError, no step's class), so the half's own check refuses it in its own
  class; asked of every step but shadows (whose block function, outside this brief, leaves the
  WorldConfigError), and of the surroundings' two halves by their own refusal's text.

The manifest's `.part` rename (the pin author's third probe) is held by the full suite:
test_m3_13_commands.py's two cases for `write_manifest`, which the new key does not touch.

Does NOT prove: that these are the only unpinned orders (the batch gate's prover looks for more).
"""

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest
import synthetic_farphoto
from computed_for import recorded
from synthetic_regio import FIXTURE, fixture_datasets, raw_regio

from mattini import download, lock
from mattini import manifest as manifest_module
from mattini.farcolour import FarColourError, build_farcolour, built_farcolour_block
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


# --------------------- the manifest: a datasets config without a dataset a built block reads

_STEPS = sorted(
    (value for value in vars(manifest_module).values() if isinstance(value, manifest_module._Step)),
    key=lambda step: (step.key, step.suffix),
)
_STEP_DATASETS = [
    pytest.param(step, dataset, id=f"{step.key}{step.suffix}-without-{dataset}")
    for step in _STEPS
    for dataset in step.names
]


def _datasets_without(tmp_path: Path, dataset: str) -> Path:
    data = json.loads((CONFIG / "datasets.json").read_text(encoding="utf-8"))
    del data["datasets"][dataset]
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def test_the_manifest_s_steps_are_all_asked_about_their_datasets():
    """The table above follows the manifest's own steps; it must not be empty or lose one."""
    keys = {(step.key, step.suffix) for step in _STEPS}
    assert keys >= {
        ("photo", ""),
        ("roofs", ""),
        ("surfaces", ""),
        ("trees", ""),
        ("shadows", ""),
        ("surroundings", ""),
        ("surroundings", "_colour"),
    }, keys
    assert {name for step in _STEPS for name in step.names} >= {REGIO, FAR}


@pytest.mark.parametrize(("step", "dataset"), _STEP_DATASETS)
def test_a_datasets_config_without_a_dataset_a_built_block_reads_is_the_step_s_refusal(
    tmp_path, step, dataset
):
    """The lock's fit raises a DownloadError for it (a RuntimeError, caught by no step's class):
    the manifest turns it into the step's own refusal with its text, never lets it through."""
    out = tmp_path / "out"
    (out / step.key).mkdir(parents=True)
    (out / step.key / f"{AREA}{step.suffix}.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(step.error) as refusal:
        build_manifest(
            CONFIG / "world.json", out, datasets_path=_datasets_without(tmp_path, dataset)
        )
    text = str(refusal.value)
    assert type(refusal.value) is step.error and not isinstance(refusal.value, RuntimeError)
    assert "config/datasets.json" in text and repr(dataset) in text, text
    assert not (out / "manifest.json").exists()


# ------------------------------- the manifest: a built colour, an area that holds no `colour`


def _surroundings_without_colour(tmp_path: Path) -> Path:
    config = json.loads((CONFIG / "surroundings.json").read_text(encoding="utf-8"))
    del config["areas"][AREA]["colour"]
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


@pytest.mark.parametrize("heights", ["built", "absent"])
def test_a_built_colour_whose_area_holds_no_colour_block_is_refused_not_dropped(
    tmp_path, monkeypatch, heights
):
    """`colour` is optional in config/surroundings.json, so the manifest cannot check the colour's
    `computed_for` without it; the description is refused all the same (the colour block function
    names the config when the heights are built, the manifest the missing heights when not), and
    never left out of the block as if no colour were built."""
    out = tmp_path / "out"
    (out / "surroundings").mkdir(parents=True)
    names = [f"{AREA}_colour.json", *([f"{AREA}.json"] if heights == "built" else [])]
    for name in names:
        (out / "surroundings" / name).write_text("{}\n", encoding="utf-8")
    # the heights' own block check is not what is asked: a stand-in that accepts (the manifest's
    # checks of the heights, against the committed config, still run)
    monkeypatch.setattr(manifest_module, "built_surroundings_block", lambda *a, **k: {"area": AREA})
    with pytest.raises(FarColourError) as refusal:
        build_manifest(
            CONFIG / "world.json",
            out,
            surroundings_config_path=_surroundings_without_colour(tmp_path),
        )
    text = str(refusal.value)
    if heights == "built":
        assert "config/surroundings.json" in text and "no colour block" in text, text
    else:
        assert set(COMMAND.findall(text)) == {"python -m mattini surroundings"}, text


# --------- the steps: a DownloadError out of the lock's fit is the step's own refusal (decision 6)
#
# A datasets config without the dataset, or with a malformed one, is refused by the steps' own
# reader of it (`_regio_config`, `regio_config`, `_far_config`) before any fit is asked, in the
# step's class: no config reaches the conversion. What does is a DownloadError raised from inside
# the fit, by a tile rule or by the area lookup; a stand-in rule, replaced on `download` where
# the fit looks it up, raises one.


def _a_rule_that_refuses(monkeypatch, rule: str) -> str:
    """Replace `download.<rule>` by one that raises a DownloadError; return its text."""
    text = f"config/surroundings.json: stand-in refusal of {rule}"

    def refuse(*args, **kwargs):
        raise download.DownloadError(text)

    monkeypatch.setattr(download, rule, refuse)
    return text


def _is_the_steps_refusal(refusal, error, text: str) -> None:
    """Exactly the step's class (not the DownloadError, a RuntimeError no step catches), whole text."""
    assert type(refusal.value) is error, repr(refusal.value)
    assert not isinstance(refusal.value, download.DownloadError)
    assert str(refusal.value) == text, str(refusal.value)


def test_surroundings_turns_a_download_error_of_the_fit_into_its_own_refusal(tmp_path, monkeypatch):
    root, made = raw_regio(tmp_path / "raw")
    config = recorded(
        load_surroundings_config(FIXTURE / "surroundings.json"), _fixture_world(), made, REGIO
    )
    text = _a_rule_that_refuses(monkeypatch, "regio_tiles")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _fixture_world(), fixture_datasets(), made, config, root, tmp_path / "out"
        )
    _is_the_steps_refusal(refusal, SurroundingsError, text)
    assert not (tmp_path / "out").exists()


def test_the_surroundings_built_block_turns_a_download_error_of_the_fit_into_its_own_refusal(
    monkeypatch,
):
    out = FIXTURE / "generated"
    config = load_surroundings_config(FIXTURE / "surroundings.json")
    world_sha256 = json.loads((out / "surroundings" / "fixture.json").read_bytes())["world_sha256"]
    made = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    text = _a_rule_that_refuses(monkeypatch, "regio_tiles")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(
            out, config, _fixture_world(), world_sha256, fixture_datasets(), made
        )
    _is_the_steps_refusal(refusal, SurroundingsError, text)


@pytest.mark.parametrize("rule", ["regio_tiles", "farphoto_cells"])
def test_farcolour_turns_a_download_error_of_either_fit_into_its_own_refusal(
    tmp_path, monkeypatch, rule
):
    root, made = synthetic_farphoto.raw_inputs(tmp_path / "raw")
    text = _a_rule_that_refuses(monkeypatch, rule)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            load_world(FAR_FIXTURE / "world.json"),
            synthetic_farphoto.fixture_datasets(),
            made,
            _far_config(made),
            root,
            tmp_path / "out",
        )
    _is_the_steps_refusal(refusal, FarColourError, text)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("rule", ["regio_tiles", "farphoto_cells"])
def test_the_far_colour_built_block_turns_a_download_error_of_either_fit_into_its_own_refusal(
    tmp_path, monkeypatch, rule
):
    _, made = synthetic_farphoto.raw_inputs(tmp_path / "raw")
    out = tmp_path / "out"
    (out / "surroundings").mkdir(parents=True)
    (out / "surroundings" / "fixture_colour.json").write_text("{}\n", encoding="utf-8")
    world_sha256 = hashlib.sha256((FAR_FIXTURE / "world.json").read_bytes()).hexdigest()
    text = _a_rule_that_refuses(monkeypatch, rule)
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(
            out,
            _far_config(made),
            load_world(FAR_FIXTURE / "world.json"),
            world_sha256,
            synthetic_farphoto.fixture_datasets(),
            made,
        )
    _is_the_steps_refusal(refusal, FarColourError, text)


# ------------------- the manifest: a built block, a world config that holds no such area


def _world_without_the_area(tmp_path: Path) -> Path:
    """The committed world config with its one area renamed: valid, and no `village` in it."""
    data = json.loads((CONFIG / "world.json").read_text(encoding="utf-8"))
    data["areas"] = {"elsewhere": data["areas"].pop(AREA)}
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _config_recording(tmp_path: Path, key: str, world: Path) -> Path:
    """config/<key>.json with the committed world's SHA-256 replaced by `world`'s everywhere, so
    that the manifest's world check (step 1) passes for that world."""
    committed = hashlib.sha256((CONFIG / "world.json").read_bytes()).hexdigest()
    text = (CONFIG / f"{key}.json").read_text(encoding="utf-8")
    assert committed in text, f"config/{key}.json does not record the committed world"
    path = tmp_path / f"{key}.json"
    path.write_text(
        text.replace(committed, hashlib.sha256(world.read_bytes()).hexdigest()), encoding="utf-8"
    )
    return path


# shadows.built_shadows_block (v0.5.0-02's, outside this brief) asks its own lock fit before it
# looks at the area, so a world config without the area leaves it as the WorldConfigError that
# fit raises, which the command line catches with one line naming the world config: the one
# step whose block is not refused in the step's own class, and so the one left out here.
_AREA_STEPS = [step for step in _STEPS if step.key != "shadows"]


@pytest.mark.parametrize(
    "step", _AREA_STEPS, ids=[f"{step.key}{step.suffix}" for step in _AREA_STEPS]
)
def test_a_built_block_for_an_area_the_world_config_lacks_is_the_step_s_refusal(tmp_path, step):
    """`_inputs_check` makes no lock fit for such an area (the tile rules read the area's box and
    raise a WorldConfigError, no step's class): the block is refused in the step's own class and
    nothing is written."""
    world = _world_without_the_area(tmp_path)
    out = tmp_path / "out"
    (out / step.key).mkdir(parents=True)
    (out / step.key / f"{AREA}{step.suffix}.json").write_text("{}\n", encoding="utf-8")
    config = _config_recording(tmp_path, step.key, world)
    with pytest.raises(step.error) as refusal:
        build_manifest(world, out, **{f"{step.key}_config_path": config})
    assert type(refusal.value) is step.error, repr(refusal.value)
    assert not (out / "manifest.json").exists()


@pytest.mark.parametrize("half", ["heights", "colour"])
def test_each_surroundings_half_refuses_an_area_the_world_config_lacks_by_its_own_check(
    tmp_path, monkeypatch, half
):
    """The half's own check, not a lock fit and not the other half's: the heights' check refuses
    for the heights; for the colour the heights' block is a stand-in that accepts, so that the
    colour's own check is the one reached."""
    world = _world_without_the_area(tmp_path)
    out = tmp_path / "out"
    (out / "surroundings").mkdir(parents=True)
    for name in [f"{AREA}.json", *([f"{AREA}_colour.json"] if half == "colour" else [])]:
        (out / "surroundings" / name).write_text("{}\n", encoding="utf-8")
    if half == "colour":
        monkeypatch.setattr(
            manifest_module, "built_surroundings_block", lambda *a, **k: {"area": AREA}
        )
    error, name, said, command = {
        "heights": (
            SurroundingsError,
            f"{AREA}.json",
            f"the world config has no area {AREA!r}",
            "surroundings",
        ),
        "colour": (
            FarColourError,
            f"{AREA}_colour.json",
            f"no area named {AREA!r}",
            "farcolour",
        ),
    }[half]
    with pytest.raises(error) as refusal:
        build_manifest(
            world,
            out,
            surroundings_config_path=_config_recording(tmp_path, "surroundings", world),
        )
    text = str(refusal.value)
    assert type(refusal.value) is error, repr(refusal.value)
    assert name in text and said in text, text
    assert f"`python -m mattini {command}` rebuilds" in text, text
    assert not (out / "manifest.json").exists()
