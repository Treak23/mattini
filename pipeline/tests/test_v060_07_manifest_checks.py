"""Pinning tests for brief v0.6.0-07: `manifest` checks each built half of the `surroundings`
block's world, lock fit and inputs itself, then the half's own block check.

Pinned decisions (docs/SPEC.md §8, *The manifest*; brief M3-13's order; brief M4-09 decision 4,
re-scoped; brief v0.5.0-02's wiring of the shadows, followed):

- The heights (`surroundings/<area>.json`, the area config/surroundings.json names): first
  `computed_for.world_sha256` against the world config (design's step, naming
  config/surroundings.json); then the lock's `swissaltiregio` entry through `lock.fit_problem(...,
  surroundings=<the surroundings config given>)`, a refusal naming `python -m mattini lock
  regio` and no other command; then `computed_for.inputs_sha256` against `lock.entry_sha256` of
  that entry (design's step); only then `surroundings.built_surroundings_block`. Each refusal
  is a SurroundingsError.
- The colour (`surroundings/<area>_colour.json`): first the colour block's
  `computed_for.world_sha256` (design's step); then the fit of `swissaltiregio` and of
  `swissimage_far`, in that (sorted) order, each naming its own lock command (`lock regio`,
  `lock farphoto`) and no other; then the colour's `computed_for.inputs_sha256` against
  `lock.entries_sha256` of both entries (design's step); only then
  `farcolour.built_farcolour_block`. Each refusal is a FarColourError.
- The heights' checks come before the colour's.
- The manifest makes these checks itself, whatever the block functions check (M3-13's `_Step`,
  uniform): with `built_surroundings_block` or `built_farcolour_block` replaced by a stand-in
  that refuses everything, naming its rebuild command, each earlier refusal is still the
  manifest's. On the command line each refusal is one `mattini: error:` line, exit status 1, and
  no manifest.

The configs and the lock are the committed ones (the village) or copies with one change (a lock
the loader refuses, such as a cell both pinned and absent, is `lock.validate_lock`'s, before any
of these checks: brief v0.6.0-05); the descriptions are stand-ins (`{}`) that any check of a block refuses, so only a check made before
the block's own can name anything else. Where a colour case needs the heights to pass, the
heights' block function is a stand-in that accepts (the heights' own checks still run).

Harm prevented: "refusals before the one that helps" (M2 V1-P-01) for the far terrain; a lock
without an entry ending in a KeyError traceback; a far terrain built from other tiles than
design's reaching the game; a colour checked against another dataset's lock entry.

Does NOT prove: that the committed lock is swisstopo's (briefs v0.6.0-01, -05); anything about
the files a fitting lock vouches for (the steps' own checks, briefs v0.6.0-04 and -06).
"""

import copy
import json
import re

import pytest

import mattini.__main__ as cli
from mattini import farcolour as farcolour_module
from mattini import manifest as manifest_module
from mattini import surroundings as surroundings_module
from mattini.farcolour import FarColourError
from mattini.lock import write_lock
from mattini.manifest import build_manifest
from mattini.surroundings import SurroundingsError
from mattini.world import REPO

CONFIG = REPO / "config"
WORLD = CONFIG / "world.json"
LOCK = json.loads((CONFIG / "datasets.lock.json").read_text(encoding="utf-8"))
SURROUNDINGS = json.loads((CONFIG / "surroundings.json").read_text(encoding="utf-8"))
AREA = "village"
REGIO = "swissaltiregio"
FAR = "swissimage_far"
COMMAND = re.compile(r"python -m mattini (?:(?:lock|download) )?[a-z]+")
DESIGN = "design's step"  # what a refusal names when it says "design recomputes"
LOCK_REGIO = "python -m mattini lock regio"
LOCK_FAR = "python -m mattini lock farphoto"
HEIGHTS_COMMAND = "python -m mattini surroundings"
COLOUR_COMMAND = "python -m mattini farcolour"


def _named(message: str) -> set[str]:
    named = set(COMMAND.findall(message))
    if "design recomputes" in message:
        named.add(DESIGN)
    return named


def _changed_lock(change) -> dict:
    data = copy.deepcopy(LOCK)
    change(data["datasets"])
    return data


def _extra_regio_tile(datasets):
    tiles = datasets[REGIO]["tiles"]
    first, second = max(tiles).split("-")
    tiles[f"{int(first) + 10:04d}-{second}"] = copy.deepcopy(tiles[max(tiles)])


def _missing_regio_tile(datasets):
    tiles = datasets[REGIO]["tiles"]
    del tiles[sorted(tiles)[len(tiles) // 2]]


def _other_regio_inputs(datasets):
    """The same tiles, one checksum changed: the entry fits, its SHA-256 differs."""
    tiles = datasets[REGIO]["tiles"]
    tiles[min(tiles)]["sha256"] = "ab" * 32


def _extra_far_cell(datasets):
    datasets[FAR]["absent"] = sorted(datasets[FAR]["absent"] + ["2700-1200"])


def _missing_far_cell(datasets):
    datasets[FAR]["absent"] = datasets[FAR]["absent"][1:]


def _other_far_inputs(datasets):
    tiles = datasets[FAR]["tiles"]
    tiles[min(tiles)]["sha256"] = "cd" * 32


REGIO_UNFITTING = {
    "an-extra-tile": _extra_regio_tile,
    "a-missing-tile": _missing_regio_tile,
    "no-entry": lambda d: d.pop(REGIO),
    "another-edition": lambda d: d[REGIO].update(edition="2019-01"),
    "another-collection": lambda d: d[REGIO].update(collection="ch.swisstopo.swissalti3d"),
}
FAR_UNFITTING = {
    "an-extra-cell": _extra_far_cell,
    "a-missing-cell": _missing_far_cell,
    "no-entry": lambda d: d.pop(FAR),
    "another-edition": lambda d: d[FAR].update(edition="2020"),
}


def _out(tmp_path, *names: str):
    out = tmp_path / "out"
    (out / "surroundings").mkdir(parents=True)
    for name in names:
        (out / "surroundings" / name).write_text("{}\n", encoding="utf-8")
    return out


def _files(tmp_path, *, lock=None, surroundings=None, world=None) -> dict:
    """Paths for `build_manifest`: the committed files, or copies with the given content."""
    paths = {"config_path": WORLD}
    if lock is not None:
        paths["lock_path"] = write_lock(lock, tmp_path / "lock.json")
    if surroundings is not None:
        path = tmp_path / "surroundings.json"
        path.write_text(json.dumps(surroundings, indent=2), encoding="utf-8")
        paths["surroundings_config_path"] = path
    if world is not None:
        paths["config_path"] = world
    return paths


def _moved_world(tmp_path):
    """The committed world with other bytes (the same values, indented by four)."""
    path = tmp_path / "world.json"
    path.write_text(json.dumps(json.loads(WORLD.read_bytes()), indent=4), encoding="utf-8")
    return path


def _refuses_everything(command):
    def block(*args, **kwargs):
        raise_as = FarColourError if command == COLOUR_COMMAND else SurroundingsError
        raise raise_as(f"the stand-in block check refuses everything; `{command}`")

    return block


def _accepts(*args, **kwargs):
    return {"area": AREA, "stand-in": True}


def _replace(monkeypatch, name, module, function):
    monkeypatch.setattr(module, name, function)
    monkeypatch.setattr(manifest_module, name, function, raising=False)


@pytest.fixture(params=["the-step-s-block-check", "a-stand-in-block-check"])
def block_check(request, monkeypatch):
    """Either the steps' own block functions, or stand-ins that refuse everything."""
    if request.param == "a-stand-in-block-check":
        _replace(
            monkeypatch,
            "built_surroundings_block",
            surroundings_module,
            _refuses_everything(HEIGHTS_COMMAND),
        )
        _replace(
            monkeypatch,
            "built_farcolour_block",
            farcolour_module,
            _refuses_everything(COLOUR_COMMAND),
        )
    return request.param


@pytest.fixture
def heights_accepted(monkeypatch):
    """The heights' block function replaced by one that accepts (its manifest checks run)."""
    _replace(monkeypatch, "built_surroundings_block", surroundings_module, _accepts)


def _refusal(error, out, **files):
    """`build_manifest` raises the half's own error class (not another step's, which the
    command line would catch just the same); its text."""
    config_path = files.pop("config_path")
    with pytest.raises(error) as refusal:
        build_manifest(config_path, out, **files)
    return str(refusal.value)


# ------------------------------------------------------------------------------- the heights


def test_a_changed_world_comes_first_for_the_heights(tmp_path, block_check):
    """The world moved and the regio entry dropped: a fit-first order would name `lock regio`."""
    out = _out(tmp_path, f"{AREA}.json")
    files = _files(
        tmp_path, lock=_changed_lock(lambda d: d.pop(REGIO)), world=_moved_world(tmp_path)
    )
    message = _refusal(SurroundingsError, out, **files)
    assert _named(message) == {DESIGN} and "config/surroundings.json" in message, message


@pytest.mark.parametrize("case", sorted(REGIO_UNFITTING))
def test_an_unfitting_regio_lock_is_refused_naming_lock_regio(tmp_path, case, block_check):
    out = _out(tmp_path, f"{AREA}.json")
    files = _files(tmp_path, lock=_changed_lock(REGIO_UNFITTING[case]))
    message = _refusal(SurroundingsError, out, **files)
    assert _named(message) == {LOCK_REGIO}, message


def test_the_fit_takes_the_margin_of_the_surroundings_config_given(tmp_path, block_check):
    """The committed lock fits the committed config; with a margin of 0 in the config given to
    `manifest` it pins tiles the area does not need: refused naming `lock regio`."""
    config = copy.deepcopy(SURROUNDINGS)
    config["areas"][AREA]["margin_m"] = 0
    out = _out(tmp_path, f"{AREA}.json")
    message = _refusal(SurroundingsError, out, **_files(tmp_path, surroundings=config))
    assert _named(message) == {LOCK_REGIO}, message


def test_a_fitting_regio_lock_with_other_inputs_names_design(tmp_path, block_check):
    out = _out(tmp_path, f"{AREA}.json")
    files = _files(tmp_path, lock=_changed_lock(_other_regio_inputs))
    message = _refusal(SurroundingsError, out, **files)
    assert _named(message) == {DESIGN} and "config/surroundings.json" in message, message


def test_the_heights_block_check_comes_last(tmp_path, block_check):
    """The positive control: every manifest check passes, the block check names the step."""
    out = _out(tmp_path, f"{AREA}.json")
    message = _refusal(SurroundingsError, out, **_files(tmp_path))
    assert _named(message) == {HEIGHTS_COMMAND}, message


def test_the_heights_come_before_the_colour(tmp_path, block_check):
    """Both stand-ins built, the far entry dropped: the heights' block check speaks first."""
    out = _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json")
    files = _files(tmp_path, lock=_changed_lock(lambda d: d.pop(FAR)))
    message = _refusal(SurroundingsError, out, **files)
    assert _named(message) == {HEIGHTS_COMMAND}, message


# -------------------------------------------------------------------------------- the colour


def _colour_config(change) -> dict:
    config = copy.deepcopy(SURROUNDINGS)
    change(config["areas"][AREA]["colour"]["computed_for"])
    return config


def test_a_changed_world_comes_first_for_the_colour(tmp_path, block_check, heights_accepted):
    """The colour's world differs and the far entry is dropped: a fit-first order would name
    `lock farphoto`."""
    out = _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json")
    files = _files(
        tmp_path,
        lock=_changed_lock(lambda d: d.pop(FAR)),
        surroundings=_colour_config(lambda c: c.update(world_sha256="ab" * 32)),
    )
    message = _refusal(FarColourError, out, **files)
    assert _named(message) == {DESIGN} and "config/surroundings.json" in message, message


@pytest.mark.parametrize("case", sorted(FAR_UNFITTING))
def test_an_unfitting_far_lock_is_refused_naming_lock_farphoto(
    tmp_path, case, block_check, heights_accepted
):
    out = _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json")
    files = _files(tmp_path, lock=_changed_lock(FAR_UNFITTING[case]))
    message = _refusal(FarColourError, out, **files)
    assert _named(message) == {LOCK_FAR}, message


def test_the_colour_s_fit_comes_before_its_inputs(tmp_path, block_check, heights_accepted):
    """An extra far cell and the colour's recorded inputs changed: the fit speaks first."""
    out = _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json")
    files = _files(
        tmp_path,
        lock=_changed_lock(_extra_far_cell),
        surroundings=_colour_config(lambda c: c.update(inputs_sha256="ab" * 32)),
    )
    message = _refusal(FarColourError, out, **files)
    assert _named(message) == {LOCK_FAR}, message


def test_a_fitting_far_lock_with_other_inputs_names_design(tmp_path, block_check, heights_accepted):
    """One far checksum changed: both entries fit, `lock.entries_sha256` of the two differs."""
    out = _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json")
    files = _files(tmp_path, lock=_changed_lock(_other_far_inputs))
    message = _refusal(FarColourError, out, **files)
    assert _named(message) == {DESIGN} and "config/surroundings.json" in message, message


def test_the_colour_s_inputs_are_both_entries(tmp_path, block_check, heights_accepted):
    """The colour's recorded inputs are the regio entry's alone (the heights' value): refused,
    since the colour's inputs are both entries together."""
    regio_only = SURROUNDINGS["areas"][AREA]["computed_for"]["inputs_sha256"]
    out = _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json")
    files = _files(
        tmp_path, surroundings=_colour_config(lambda c: c.update(inputs_sha256=regio_only))
    )
    message = _refusal(FarColourError, out, **files)
    assert _named(message) == {DESIGN}, message


def test_the_colour_s_block_check_comes_last(tmp_path, block_check, heights_accepted):
    out = _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json")
    message = _refusal(FarColourError, out, **_files(tmp_path))
    assert _named(message) == {COLOUR_COMMAND}, message


# ------------------------------------------------------------------------ the command line


def _one_line(capsys, out) -> str:
    status = cli.main(["manifest", "--out", str(out)])
    captured = capsys.readouterr()
    assert status == 1 and captured.out == "", captured
    lines = captured.err.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: error: "), captured.err
    assert "Traceback" not in captured.err
    assert not (out / "manifest.json").exists()
    return lines[0]


def test_on_the_command_line_the_heights_refusal_is_one_line_and_no_manifest(tmp_path, capsys):
    line = _one_line(capsys, _out(tmp_path, f"{AREA}.json"))
    assert _named(line) == {HEIGHTS_COMMAND}, line


def test_on_the_command_line_the_colour_refusal_is_one_line_and_no_manifest(
    tmp_path, capsys, heights_accepted
):
    line = _one_line(capsys, _out(tmp_path, f"{AREA}.json", f"{AREA}_colour.json"))
    assert _named(line) == {COLOUR_COMMAND}, line
