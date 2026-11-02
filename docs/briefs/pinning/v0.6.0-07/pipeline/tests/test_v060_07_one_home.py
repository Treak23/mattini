"""Pinning tests for brief v0.6.0-07: the tile rules and the surroundings config each have one
home (brief M4-09's one-home pin, re-cut onto 0.6.0's two far datasets).

Pinned decisions (brief M4-01 decisions 4 and 6, M4-02 decision 5, M4-09 decisions 5 and 6;
briefs v0.6.0-01, -04, -05, -06; brief v0.6.0-07 decisions 5 and 6):

- `lock.fit_problem(lock, datasets, world, area, dataset, *, surroundings=None)` is the one
  check of the lock's `swissaltiregio` and `swissimage_far` entries. Their ids are
  `download.regio_tiles(world, area, margin_m=..., spacing_m=...)` and
  `download.farphoto_cells(world, area, margin_m=...)`, looked up on `download` when the fit
  runs, with the area's `margin_m` and `spacing_m` in the surroundings config it is GIVEN (never
  the committed file read by the lock: the manifest and the steps pass their own). For those two
  datasets a call without `surroundings` is a TypeError (a caller's bug, not a refusal); every
  other dataset ignores the keyword. The text is the whole refusal and names that dataset's lock
  command and no other.
- The surroundings step (`build_surroundings`, `built_surroundings_block`) and the far colour
  step (`build_farcolour`) keep no tile rule of their own: each refuses a lock that does not fit
  with fit_problem's text, word for word, in its own error class, and follows the rule when
  `download`'s is replaced. The tile reader's own check that a tile is the 10 km square its id
  names stays in surroundings.py.
- config/surroundings.json is read by `surroundings.load_surroundings_config` alone; the command
  line calls it through the module for `lock regio`, `lock farphoto`, `download regio`,
  `download farphoto`, `surroundings` and `farcolour` (brief v0.6.0-01's small reader in
  download.py, `download.surroundings_settings` and `download.SURROUNDINGS_PATH`, and v0.6.0-02's
  and -05's `area_regio_tiles` and `area_farphoto_cells` are gone). No module of the pipeline but
  surroundings.py names the file's path.

Harm prevented: two copies of a tile rule that drift apart, so `download regio` or `download
farphoto` fetches tiles a step then refuses, or a step accepts a lock the download refuses
(M4-01's decision on the rule's duplication); a margin the owner's config changes that only one
side reads; the manifest checking the surroundings fixture's lock against the village's config.

Does NOT prove: that the rules themselves are right (test_m4_01_regio_tiles.py,
test_v060_05_farphoto_cells.py).
"""

import copy
import hashlib
import json
import re
import urllib.error

import pytest
import synthetic_farphoto
from computed_for import recorded
from synthetic_regio import FIXTURE, fixture_datasets, raw_regio

import mattini.__main__ as cli
from mattini import download, lock, surroundings
from mattini.farcolour import FarColourError, build_farcolour
from mattini.surroundings import (
    SurroundingsError,
    build_surroundings,
    built_surroundings_block,
    load_surroundings_config,
)
from mattini.world import REPO, load_world

LOCK_REGIO = "python -m mattini lock regio"
LOCK_FAR = "python -m mattini lock farphoto"
COMMAND = re.compile(r"python -m mattini [a-z]+(?: [a-z]+)?")
REGIO = "swissaltiregio"
FAR = "swissimage_far"
FAR_FIXTURE = synthetic_farphoto.FIXTURE


def _world():
    return load_world(FIXTURE / "world.json")


def _config():
    return load_surroundings_config(FIXTURE / "surroundings.json")


def _lock():
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))


def _fit(pinned, config=None):
    return lock.fit_problem(
        pinned, fixture_datasets(), _world(), "fixture", REGIO, surroundings=config or _config()
    )


def test_the_fixture_s_lock_fits_its_surroundings_config():
    settings = _config()["areas"]["fixture"]
    tiles = download.regio_tiles(
        _world(), "fixture", margin_m=settings["margin_m"], spacing_m=settings["spacing_m"]
    )
    assert sorted(_lock()["datasets"][REGIO]["tiles"]) == tiles
    assert _fit(_lock()) is None


def test_the_fit_takes_the_margin_and_spacing_from_the_config_it_is_given():
    """A margin of 30 km needs more tiles than the fixture's lock pins: refused, naming only
    the lock command. So does a spacing of 10 km with the margin unchanged (the session's
    ruling of 2026-11-02; measured: at the fixture's margin of 3 km every spacing from 1 to
    5000 m gives the same 9 tiles, 10000 m adds the row N 1114, `2605-1114` to `2625-1114`),
    so a fit that reads the margin and hard-codes or halves the spacing is refused here."""
    config = copy.deepcopy(_config())
    config["areas"]["fixture"]["margin_m"] = 30000
    problem = _fit(_lock(), config)
    assert problem is not None
    assert set(COMMAND.findall(problem)) == {LOCK_REGIO}, problem

    config = copy.deepcopy(_config())
    config["areas"]["fixture"]["spacing_m"] = 10000
    problem = _fit(_lock(), config)
    assert problem is not None and "2605-1114" in problem and "2625-1114" in problem, problem
    assert set(COMMAND.findall(problem)) == {LOCK_REGIO}, problem


@pytest.mark.parametrize("dataset", [REGIO, FAR])
def test_the_far_datasets_fit_needs_the_config(dataset):
    with pytest.raises(TypeError):
        lock.fit_problem(_lock(), fixture_datasets(), _world(), "fixture", dataset)


def test_every_other_dataset_ignores_the_keyword():
    committed = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    datasets = json.loads((REPO / "config" / "datasets.json").read_bytes())["datasets"]
    world = load_world()
    config = load_surroundings_config(REPO / "config" / "surroundings.json")
    for dataset in ("swissalti3d", "swissimage", "swisssurface3d", "swissbuildings3d"):
        plain = lock.fit_problem(committed, datasets, world, "village", dataset)
        assert plain is None, plain
        given = lock.fit_problem(
            committed, datasets, world, "village", dataset, surroundings=config
        )
        assert given is None, given


def _one_tile_more(pinned):
    pinned = copy.deepcopy(pinned)
    tiles = pinned["datasets"][REGIO]["tiles"]
    first, second = max(tiles).split("-")
    tiles[f"{int(first) + 10:04d}-{second}"] = copy.deepcopy(tiles[max(tiles)])
    return pinned


def test_the_step_refuses_a_lock_that_does_not_fit_with_fit_problem_s_text(tmp_path):
    root, made = raw_regio(tmp_path / "raw")
    pinned = _one_tile_more(made)
    config = recorded(_config(), _world(), made, REGIO)
    with pytest.raises(SurroundingsError) as refused:
        build_surroundings(_world(), fixture_datasets(), pinned, config, root, tmp_path / "out")
    assert str(refused.value) == _fit(pinned, config)
    assert not (tmp_path / "out").exists()


def test_the_step_asks_download_s_tile_rule_through_fit_problem(tmp_path, monkeypatch):
    """The rule replaced in download.py alone: the step follows it (one home)."""
    root, made = raw_regio(tmp_path / "raw")
    config = recorded(_config(), _world(), made, REGIO)
    build_surroundings(_world(), fixture_datasets(), made, config, root, tmp_path / "before")
    real = download.regio_tiles

    def one_tile_fewer(*args, **kwargs):
        return real(*args, **kwargs)[:-1]

    monkeypatch.setattr(download, "regio_tiles", one_tile_fewer)
    with pytest.raises(SurroundingsError) as refused:
        build_surroundings(_world(), fixture_datasets(), made, config, root, tmp_path / "out")
    assert str(refused.value) == _fit(made, config)
    assert set(COMMAND.findall(str(refused.value))) == {LOCK_REGIO}


def test_the_built_block_asks_the_same_rule(monkeypatch):
    out = FIXTURE / "generated"
    args = (_config(), _world())
    world_sha256 = json.loads((out / "surroundings" / "fixture.json").read_bytes())["world_sha256"]
    block = built_surroundings_block(out, *args, world_sha256, fixture_datasets(), _lock())
    assert block is not None
    real = download.regio_tiles
    monkeypatch.setattr(download, "regio_tiles", lambda *a, **k: real(*a, **k)[1:])
    with pytest.raises(SurroundingsError) as refused:
        built_surroundings_block(out, *args, world_sha256, fixture_datasets(), _lock())
    assert str(refused.value) == _fit(_lock())


# ---------------------------------------------------------------------- the far colour step


def _far_config(made: dict) -> dict:
    """The far colour fixture's config, its colour recording the fixture's world and both of
    `made`'s entries (as brief v0.6.0-06's own test does)."""
    config = copy.deepcopy(load_surroundings_config(FAR_FIXTURE / "surroundings.json"))
    both = {name: made["datasets"][name] for name in (REGIO, FAR)}
    text = json.dumps(both, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    config["areas"]["fixture"]["colour"]["computed_for"] = {
        "inputs_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "world_sha256": hashlib.sha256((FAR_FIXTURE / "world.json").read_bytes()).hexdigest(),
    }
    return config


def _far_fit(pinned, config, dataset):
    return lock.fit_problem(
        pinned,
        synthetic_farphoto.fixture_datasets(),
        load_world(FAR_FIXTURE / "world.json"),
        "fixture",
        dataset,
        surroundings=config,
    )


@pytest.mark.parametrize(
    ("rule", "dataset", "command"),
    [("farphoto_cells", FAR, LOCK_FAR), ("regio_tiles", REGIO, LOCK_REGIO)],
)
def test_the_far_colour_asks_download_s_rules_through_fit_problem(
    tmp_path, monkeypatch, rule, dataset, command
):
    """Each rule replaced in download.py alone: the far colour step follows it, refusing with
    fit_problem's text word for word, and builds with it as it is."""
    root, made = synthetic_farphoto.raw_inputs(tmp_path / "raw")
    config = _far_config(made)
    world = load_world(FAR_FIXTURE / "world.json")
    datasets = synthetic_farphoto.fixture_datasets()
    build_farcolour(world, datasets, made, config, root, tmp_path / "before")
    real = getattr(download, rule)

    def one_fewer(*args, **kwargs):
        return real(*args, **kwargs)[:-1]

    monkeypatch.setattr(download, rule, one_fewer)
    with pytest.raises(FarColourError) as refused:
        build_farcolour(world, datasets, made, config, root, tmp_path / "out")
    assert str(refused.value) == _far_fit(made, config, dataset)
    assert set(COMMAND.findall(str(refused.value))) == {command}
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------------- the one reader


def test_no_module_but_surroundings_py_names_the_config_s_path():
    """The file's path appears in the pipeline once, in its one reader's module."""
    sources = sorted((REPO / "pipeline" / "mattini").glob("*.py"))
    naming = [p.name for p in sources if '"surroundings.json"' in p.read_text(encoding="utf-8")]
    assert naming == ["surroundings.py"], naming
    assert not hasattr(download, "surroundings_settings")
    assert not hasattr(download, "SURROUNDINGS_PATH")
    assert not hasattr(download, "area_regio_tiles")
    assert not hasattr(download, "area_farphoto_cells")


def _margin_zero(monkeypatch):
    """The command line's surroundings config, read through the module, with margin 0."""
    committed = load_surroundings_config(REPO / "config" / "surroundings.json")
    changed = copy.deepcopy(committed)
    (area,) = changed["areas"].values()
    area["margin_m"] = 0
    monkeypatch.setattr(surroundings, "load_surroundings_config", lambda *a, **k: changed)
    return changed


def _no_network(*args, **kwargs):
    raise AssertionError("the test reached for the network")


@pytest.mark.parametrize(("dataset", "command"), [("regio", LOCK_REGIO), ("farphoto", LOCK_FAR)])
def test_download_reads_the_surroundings_config_through_its_module(
    monkeypatch, capsys, tmp_path, dataset, command
):
    """With margin 0 the committed lock's tiles do not fit: refused before swisstopo is asked
    anything, naming the lock command alone."""
    _margin_zero(monkeypatch)
    monkeypatch.setattr(download, "urllib_fetch_json", _no_network)
    monkeypatch.setattr(download, "urllib_fetch_file", _no_network)
    status = cli.main(["download", dataset, "--out", str(tmp_path / "raw")])
    err = capsys.readouterr().err
    assert status == 1, err
    assert set(COMMAND.findall(err)) == {command}, err
    assert not (tmp_path / "raw").exists() or not any((tmp_path / "raw").rglob("*"))


def test_lock_regio_reads_the_surroundings_config_through_its_module(monkeypatch, capsys):
    """With margin 0, `lock regio` asks STAC for the area's own tiles first."""
    changed = _margin_zero(monkeypatch)
    asked = []

    def stac(url, *args, **kwargs):
        asked.append(url)
        raise urllib.error.URLError("the test refuses the network")

    monkeypatch.setattr(download, "urllib_fetch_json", stac)
    monkeypatch.setattr(lock, "write_lock", lambda *a, **k: pytest.fail("nothing is written"))
    status = cli.main(["lock", "regio"])
    assert status == 1, capsys.readouterr().err
    world = load_world(REPO / "config" / "world.json")
    ((name, area),) = changed["areas"].items()
    first = download.regio_tiles(world, name, margin_m=0, spacing_m=area["spacing_m"])[0]
    assert asked and f"swissaltiregio_{first}" in asked[0], asked


def test_lock_farphoto_reads_the_surroundings_config_through_its_module(monkeypatch, capsys):
    """With margin 0, `lock farphoto` asks STAC for the area's own cells only (six)."""
    changed = _margin_zero(monkeypatch)
    asked = []

    def stac(url, *args, **kwargs):
        asked.append(url)
        raise urllib.error.URLError("the test refuses the network")

    monkeypatch.setattr(download, "urllib_fetch_json", stac)
    monkeypatch.setattr(lock, "write_lock", lambda *a, **k: pytest.fail("nothing is written"))
    status = cli.main(["lock", "farphoto"])
    assert status == 1, capsys.readouterr().err
    world = load_world(REPO / "config" / "world.json")
    (name,) = changed["areas"]
    cells = download.farphoto_cells(world, name, margin_m=0)
    assert asked and {u.split("_")[-1] for u in asked} <= set(cells), asked
