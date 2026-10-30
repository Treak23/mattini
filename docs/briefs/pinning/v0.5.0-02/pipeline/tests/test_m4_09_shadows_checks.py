"""Pinning tests for brief v0.5.0-02 (brief M4-09 cut to the shadows): `manifest` checks a built
`shadows` block's world, lock fit and inputs itself, then the block.

Pinned decisions (docs/SPEC.md §8, *The manifest*; brief M3-13's order; brief M4-09 decision 4,
the shadows only): for a built `shadows` block (`shadows/<area>.json`, the area
config/shadows.json names), `manifest` compares config/shadows.json's
`computed_for.world_sha256` with the world config first; then checks that the lock's
`swisssurface3d` entry fits the datasets config and the area through `lock.fit_problem` (the
area's tiles, each at an edition the config accepts); then compares
`computed_for.inputs_sha256` with that entry (`lock.entry_sha256`); and only then checks the
block itself (`shadows.built_shadows_block`). A lock that does not fit is a refusal naming
`python -m mattini lock surface` and no other command; a changed world, or a fitting lock with
other inputs, names design's step ("design recomputes") and config/shadows.json, and no command
(rebuilding cannot help). The manifest makes these three checks itself, in this order, whatever
the step's block function checks (M3-13's `_Step`, uniform): with `built_shadows_block` replaced
by a stand-in that refuses everything, naming `python -m mattini shadows`, each earlier refusal
is still the manifest's. Each refusal is a ShadowsError: one `mattini: error:` line, exit status
1, and no manifest; `build_manifest` itself raises the ShadowsError (not another step's error
class, which the command line would catch just the same). Every step config is loaded and checked even when its step has not run
(M4-09 decision 3): a shadows config the loader refuses is refused with nothing built.

The configs and the lock are the committed ones (the village), the built block a stand-in `{}`
that any check of a block refuses, so only a check made before the block's own can name anything
else. Harm prevented: the review's "refusals before the one that helps" (M2 V1-P-01) for the
shadows block; a lock without the `swisssurface3d` entry ending in a KeyError traceback; a mask
built from other tiles than design's reaching the game.

Does NOT prove: that the committed lock is swisstopo's (brief M2-03's and v0.5.0-01's tests);
anything about the files a fitting lock vouches for (the step's own checks, test_m4_03_step.py).
"""

import copy
import functools
import json
import re

import pytest

import mattini.__main__ as cli
from mattini import manifest as manifest_module
from mattini import shadows as shadows_module
from mattini.lock import write_lock
from mattini.manifest import build_manifest, write_manifest
from mattini.shadows import ShadowsError
from mattini.world import REPO

CONFIG = REPO / "config"
WORLD = CONFIG / "world.json"
LOCK = json.loads((CONFIG / "datasets.lock.json").read_text(encoding="utf-8"))
AREA = "village"  # the one area of config/terrain.json and config/shadows.json
DATASET = "swisssurface3d"
COMMAND = re.compile(
    r"python -m mattini (?:(?:lock|download) )?"
    r"(?:terrain|buildings|photo|surface|tlm|roofs|surfaces|trees|shadows|sky)\b"
    r"|python -m mattini manifest"
)
DESIGN = "design's step"  # what a refusal names when it says "design recomputes"
LOCK_SURFACE = "python -m mattini lock surface"
REBUILD = "python -m mattini shadows"


def _named(message: str) -> set[str]:
    named = set(COMMAND.findall(message))
    if "design recomputes" in message:
        named.add(DESIGN)
    return named


def _extra_tile(entry):
    """One tile beyond the last, 1 km east."""
    first, second = max(entry["tiles"]).split("-")
    entry["tiles"][f"{int(first) + 1:04d}-{second}"] = copy.deepcopy(
        entry["tiles"][max(entry["tiles"])]
    )


def _missing_tile(entry):
    del entry["tiles"][sorted(entry["tiles"])[len(entry["tiles"]) // 2]]


def _edition_not_accepted(entry):
    entry["tiles"][min(entry["tiles"])]["edition"] = "2019"  # a year the config does not accept


def _another_collection(entry):
    entry["collection"] = "ch.swisstopo.swisssurface3d-raster_x"


def _other_file(entry):
    """A fitting entry whose inputs changed: one file's SHA-256 (an adopted republish)."""
    entry["tiles"][min(entry["tiles"])]["sha256"] = "ab" * 32


DROP = "drop"  # the change that removes the entry

UNFITTING = [
    pytest.param(_extra_tile, id="extra-tile"),
    pytest.param(_missing_tile, id="missing-tile"),
    pytest.param(DROP, id="no-entry"),
    pytest.param(_edition_not_accepted, id="edition-not-accepted"),
    pytest.param(_another_collection, id="another-collection"),
]


def _stand_in(*args, **kwargs):
    raise ShadowsError(f"a stand-in block check refuses everything; `{REBUILD}` rebuilds")


@pytest.fixture(params=["the-step-s-block-check", "a-stand-in-block-check"])
def block_check(request, monkeypatch):
    """The step's own `built_shadows_block`, or a stand-in that refuses everything naming the
    step's command: the manifest's own checks must come first either way."""
    if request.param == "a-stand-in-block-check":
        monkeypatch.setattr(shadows_module, "built_shadows_block", _stand_in)
        monkeypatch.setattr(manifest_module, "built_shadows_block", _stand_in, raising=False)
    return request.param


def _moved_world(tmp_path):
    data = json.loads(WORLD.read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1.0
    path = tmp_path / "moved" / "world.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _manifest(tmp_path, monkeypatch, capsys, change=None, *, world=WORLD, built=True, **paths):
    """`python -m mattini manifest --out <tmp>` over a stand-in `shadows/village.json` (when
    `built`), the committed configs but those given, the world given and a lock whose
    `swisssurface3d` entry `change` alters: (exit status, the one stderr line)."""
    pinned = copy.deepcopy(LOCK)
    if change is DROP:
        del pinned["datasets"][DATASET]
    elif change is not None:
        change(pinned["datasets"][DATASET])
    lock_path = write_lock(pinned, tmp_path / "datasets.lock.json")  # a well-formed lock
    out = tmp_path / "generated"
    out.mkdir()
    if built:
        (out / "shadows").mkdir()
        (out / "shadows" / f"{AREA}.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "write_manifest",
        functools.partial(write_manifest, config_path=world, lock_path=lock_path, **paths),
    )
    status = cli.main(["manifest", "--out", str(out)])
    captured = capsys.readouterr()
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: error: "), captured.err
    assert "Traceback" not in captured.err
    return status, lines[0]


def test_a_changed_world_comes_first(tmp_path, monkeypatch, capsys, block_check):
    """Another world config (its origin moved) and a lock without the entry, which the fit
    would refuse next: design's step, naming config/world.json and config/shadows.json."""
    status, message = _manifest(tmp_path, monkeypatch, capsys, DROP, world=_moved_world(tmp_path))
    assert status == 1
    assert _named(message) == {DESIGN}, message
    assert "config/world.json" in message and "config/shadows.json" in message, message


@pytest.mark.parametrize("change", UNFITTING)
def test_a_lock_that_does_not_fit_is_named_before_the_inputs_and_the_block(
    tmp_path, monkeypatch, capsys, block_check, change
):
    status, message = _manifest(tmp_path, monkeypatch, capsys, change)
    assert status == 1
    assert _named(message) == {LOCK_SURFACE}, message


def test_a_fitting_lock_with_other_inputs_names_design_s_step(
    tmp_path, monkeypatch, capsys, block_check
):
    status, message = _manifest(tmp_path, monkeypatch, capsys, _other_file)
    assert status == 1
    assert _named(message) == {DESIGN} and "config/shadows.json" in message, message


def test_the_committed_lock_fits_and_the_block_is_checked(
    tmp_path, monkeypatch, capsys, block_check
):
    """Positive control: world, fit and inputs hold; the stand-in description is refused as a
    block (by the step's check, or by the stand-in), naming the step's command."""
    status, message = _manifest(tmp_path, monkeypatch, capsys)
    assert status == 1
    assert _named(message) == {REBUILD}, message


def test_a_shadows_config_the_loader_refuses_is_refused_with_nothing_built(
    tmp_path, monkeypatch, capsys
):
    """config/shadows.json with schema 2, no `shadows/` in the folder: the manifest still
    loads and checks the config, and refuses it (one line, exit 1, nothing written)."""
    data = json.loads((CONFIG / "shadows.json").read_text(encoding="utf-8"))
    data["schema"] = 2
    path = tmp_path / "config" / "shadows.json"
    path.parent.mkdir()
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    status, _ = _manifest(tmp_path, monkeypatch, capsys, built=False, shadows_config_path=path)
    assert status == 1


@pytest.mark.parametrize(
    "change, world",
    [
        pytest.param(_missing_tile, WORLD, id="unfitting-lock"),
        pytest.param(_other_file, WORLD, id="other-inputs"),
        pytest.param(None, "moved", id="changed-world"),
    ],
)
def test_build_manifest_raises_the_shadows_step_s_error_class(tmp_path, change, world):
    """`build_manifest` called directly (not through `cli.main`, whose `except` tuple holds every
    step's error class): the manifest's own refusals of a built shadows block are ShadowsErrors,
    not the trees' or any other step's."""
    pinned = copy.deepcopy(LOCK)
    if change is not None:
        change(pinned["datasets"][DATASET])
    lock_path = write_lock(pinned, tmp_path / "datasets.lock.json")
    out = tmp_path / "generated"
    (out / "shadows").mkdir(parents=True)
    (out / "shadows" / f"{AREA}.json").write_text("{}\n", encoding="utf-8")
    config_path = _moved_world(tmp_path) if world == "moved" else world
    with pytest.raises(ShadowsError):
        build_manifest(config_path, out, lock_path=lock_path)
