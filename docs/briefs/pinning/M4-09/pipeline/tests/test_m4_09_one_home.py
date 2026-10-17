"""Pinning tests for brief M4-09: the swissALTIRegio tile rule and the surroundings config
each have one home.

Pinned decisions (brief M4-01 decisions 4 and 6, M4-02 decision 5, M4-09):
- `lock.fit_problem(lock, datasets, world, area, "swissaltiregio", *, surroundings=<the
  surroundings config>)` is the one check of the lock's swissALTIRegio entry: collection,
  edition, resolution, and exactly the tiles `download.regio_tiles(world, area, margin_m=...,
  spacing_m=...)` gives for the area's `margin_m` and `spacing_m` in the surroundings config
  it is given (not the committed file: the manifest and the step pass their own). The text is
  the whole refusal and names `python -m mattini lock regio` and no other command.
- The surroundings step (`build_surroundings`, `built_surroundings_block`) asks it, through
  `download.regio_tiles` looked up at call time, and keeps no tile rule of its own: its
  refusal of a lock that does not fit is fit_problem's text, word for word.
- The surroundings config is read by `surroundings.load_surroundings_config` only; the
  command line calls it through the module for `lock regio`, `download regio` and
  `surroundings` (brief M4-01's small reader in download.py moves there).

Harm prevented: two copies of the tile rule that drift apart, so `download regio` fetches
tiles the step then refuses, or the step accepts a lock `download regio` refuses (M4-01's
decision on the rule's duplication); a margin the owner's config changes that only one side
reads.

Does NOT prove: that the rule itself is right (brief M4-01's test_m4_01_regio_tiles.py).
"""

import copy
import json
import re
import urllib.error

import pytest
from computed_for import recorded
from synthetic_regio import FIXTURE, fixture_datasets, raw_regio

import mattini.__main__ as cli
from mattini import download, lock, surroundings
from mattini.surroundings import (
    SurroundingsError,
    build_surroundings,
    built_surroundings_block,
    load_surroundings_config,
)
from mattini.world import REPO, load_world

LOCK_COMMAND = "python -m mattini lock regio"
COMMAND = re.compile(r"python -m mattini [a-z]+(?: [a-z]+)?")
DATASET = "swissaltiregio"


def _world():
    return load_world(FIXTURE / "world.json")


def _config():
    return load_surroundings_config(FIXTURE / "surroundings.json")


def _lock():
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))


def _fit(pinned, config=None):
    return lock.fit_problem(
        pinned, fixture_datasets(), _world(), "fixture", DATASET, surroundings=config or _config()
    )


def test_the_fixture_s_lock_fits_its_surroundings_config():
    settings = _config()["areas"]["fixture"]
    tiles = download.regio_tiles(
        _world(), "fixture", margin_m=settings["margin_m"], spacing_m=settings["spacing_m"]
    )
    assert sorted(_lock()["datasets"][DATASET]["tiles"]) == tiles
    assert _fit(_lock()) is None


def test_the_fit_takes_the_margin_and_spacing_from_the_config_it_is_given():
    """A margin of 30 km needs more tiles than the fixture's lock pins: refused, naming only
    the lock command."""
    config = copy.deepcopy(_config())
    config["areas"]["fixture"]["margin_m"] = 30000
    problem = _fit(_lock(), config)
    assert problem is not None
    assert set(COMMAND.findall(problem)) == {LOCK_COMMAND}, problem


def _one_tile_more(pinned):
    pinned = copy.deepcopy(pinned)
    tiles = pinned["datasets"][DATASET]["tiles"]
    first, second = max(tiles).split("-")
    tiles[f"{int(first) + 10:04d}-{second}"] = copy.deepcopy(tiles[max(tiles)])
    return pinned


def _build(tmp_path, pinned=None):
    root, made = raw_regio(tmp_path / "raw")
    config = recorded(_config(), _world(), made, DATASET)
    return build_surroundings(
        _world(),
        fixture_datasets(),
        made if pinned is None else pinned,
        config,
        root,
        tmp_path / "out",
    )


def test_the_step_refuses_a_lock_that_does_not_fit_with_fit_problem_s_text(tmp_path):
    root, made = raw_regio(tmp_path / "raw")
    pinned = _one_tile_more(made)
    config = recorded(_config(), _world(), made, DATASET)
    with pytest.raises(SurroundingsError) as refused:
        build_surroundings(_world(), fixture_datasets(), pinned, config, root, tmp_path / "out")
    assert str(refused.value) == _fit(pinned, config)
    assert not (tmp_path / "out").exists()


def test_the_step_asks_download_s_tile_rule_through_fit_problem(tmp_path, monkeypatch):
    """The rule replaced in download.py alone: the step follows it (one home)."""
    _build(tmp_path / "before")  # the fixture builds with the rule as it is
    real = download.regio_tiles

    def one_tile_fewer(*args, **kwargs):
        return real(*args, **kwargs)[:-1]

    monkeypatch.setattr(download, "regio_tiles", one_tile_fewer)
    root, made = raw_regio(tmp_path / "raw")
    config = recorded(_config(), _world(), made, DATASET)
    with pytest.raises(SurroundingsError) as refused:
        build_surroundings(_world(), fixture_datasets(), made, config, root, tmp_path / "out")
    assert str(refused.value) == _fit(made, config)
    assert set(COMMAND.findall(str(refused.value))) == {LOCK_COMMAND}


def test_the_built_block_asks_the_same_rule(tmp_path, monkeypatch):
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


def _margin_zero(monkeypatch):
    """The command line's surroundings config, read through the module, with margin 0."""
    committed = load_surroundings_config(REPO / "config" / "surroundings.json")
    changed = copy.deepcopy(committed)
    (area,) = changed["areas"].values()
    area["margin_m"] = 0
    monkeypatch.setattr(surroundings, "load_surroundings_config", lambda *a, **k: changed)
    return changed


def test_download_regio_reads_the_surroundings_config_through_its_module(
    monkeypatch, capsys, tmp_path
):
    """With margin 0 the committed lock's 30 tiles do not fit: refused before swisstopo is
    asked anything, naming the lock command."""
    _margin_zero(monkeypatch)

    def no_network(*args, **kwargs):
        raise AssertionError("the test reached for the network")

    monkeypatch.setattr(download, "urllib_fetch_json", no_network)
    monkeypatch.setattr(download, "urllib_fetch_file", no_network)
    status = cli.main(["download", "regio", "--out", str(tmp_path / "raw")])
    err = capsys.readouterr().err
    assert status == 1, err
    assert set(COMMAND.findall(err)) == {LOCK_COMMAND}, err
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
