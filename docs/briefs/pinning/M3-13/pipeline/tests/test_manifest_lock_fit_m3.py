"""Pinning tests for brief M3-13: `manifest` checks each new block's lock fit first.

Pinned decisions (docs/SPEC.md §8, *The manifest* and the expected outputs; brief M3-01's
rule for the lock's fit, M3-13): for a built photo, roofs, surfaces or trees block,
`manifest` compares the step config's `computed_for` with the world config first, then
checks that the lock's entry of every dataset the step reads fits the datasets config and
the area (collection, edition or editions and resolution; exactly the area's tiles or
sheets; each surface tile at an edition the config accepts), then compares
`computed_for` with those entries (one entry's `entry_sha256`, or `entries_sha256` over
several), and only then checks the block itself. A lock that does not fit is a refusal
naming `python -m mattini lock <x>` (x the dataset's command name: terrain, buildings,
photo, surface, tlm) and no other command; a changed world, or a fitting lock with other
inputs, names design's step; with the committed lock the stand-in block is refused as a
block, naming the step (roofs: naming `python -m mattini buildings`, since none are built).
Each refusal is one `mattini: error:` line, exit status 1, and no manifest.

The configs and the lock are the committed ones (the village; the lock with the entries
of brief M3-03), the built block a stand-in `{}` that any check of a block refuses, so
only a check made before the block's own can name anything else. Harm prevented: the
review's "refusals before the one that helps" (M2 V1-P-01) for the four new blocks, and a
lock without a new dataset's entry ending in a KeyError traceback.

Does NOT prove: that the committed lock is swisstopo's (brief M3-03's tests); anything
about the files a fitting lock vouches for.
"""

import copy
import functools
import json
import re

import pytest

import mattini.__main__ as cli
from mattini.lock import write_lock
from mattini.manifest import write_manifest
from mattini.world import REPO

CONFIG = REPO / "config"
WORLD = CONFIG / "world.json"
LOCK = json.loads((CONFIG / "datasets.lock.json").read_text(encoding="utf-8"))
AREA = "village"  # the one area of config/terrain.json, photo.json and surfaces.json
COMMAND = re.compile(
    r"python -m mattini (?:(?:lock|download) )?"
    r"(?:terrain|buildings|photo|surface|tlm|roofs|surfaces|trees)\b"
    r"|python -m mattini manifest"
)
DESIGN = "design's step"  # what a refusal names when it says "design recomputes"
LOCK_OF = {
    "swissalti3d": "python -m mattini lock terrain",
    "swissbuildings3d": "python -m mattini lock buildings",
    "swissimage": "python -m mattini lock photo",
    "swisssurface3d": "python -m mattini lock surface",
    "swisstlm3d": "python -m mattini lock tlm",
}


def _named(message: str) -> set[str]:
    named = set(COMMAND.findall(message))
    if "design recomputes" in message:
        named.add(DESIGN)
    return named


def _east_of_last(parts: dict) -> str:
    first, second = max(parts).split("-")
    return f"{int(first) + 1}-{second}"


def _extra_tile(entry):
    entry["tiles"][_east_of_last(entry["tiles"])] = copy.deepcopy(
        entry["tiles"][max(entry["tiles"])]
    )


def _missing_sheet(entry):
    del entry["sheets"][sorted(entry["sheets"])[len(entry["sheets"]) // 2]]


def _surface_edition(entry):
    entry["tiles"][min(entry["tiles"])]["edition"] = "2019"  # a year the config does not accept


def _other_file(entry):
    """A fitting entry whose inputs changed: one file's SHA-256 (an adopted republish)."""
    if "sha256" in entry:
        entry["sha256"] = "ab" * 32
        return
    parts = entry.get("tiles") or entry["sheets"]
    parts[min(parts)]["sha256"] = "ab" * 32


DROP = "drop"  # the change that removes the dataset's entry

# (block, dataset, change): every dataset each new step reads, each with a lock entry that
# does not fit in one of the ways the rule names.
UNFITTING = [
    pytest.param("photo", "swissimage", _extra_tile, id="photo-swissimage-extra-tile"),
    pytest.param("photo", "swissimage", DROP, id="photo-swissimage-no-entry"),
    pytest.param(
        "surfaces",
        "swisstlm3d",
        lambda e: e.update(edition="2025-03"),
        id="surfaces-swisstlm3d-another-edition",
    ),
    pytest.param("surfaces", "swisstlm3d", DROP, id="surfaces-swisstlm3d-no-entry"),
    pytest.param("roofs", "swissbuildings3d", _missing_sheet, id="roofs-swissbuildings3d-missing"),
    pytest.param(
        "roofs",
        "swissimage",
        lambda e: e.update(resolution_m=0.2),
        id="roofs-swissimage-another-resolution",
    ),
    pytest.param("trees", "swissalti3d", _extra_tile, id="trees-swissalti3d-extra-tile"),
    pytest.param("trees", "swissbuildings3d", DROP, id="trees-swissbuildings3d-no-entry"),
    pytest.param(
        "trees", "swisssurface3d", _surface_edition, id="trees-swisssurface3d-edition-not-accepted"
    ),
    pytest.param(
        "trees",
        "swisstlm3d",
        lambda e: e.update(collection="ch.swisstopo.swisstlm3d_x"),
        id="trees-swisstlm3d-another-collection",
    ),
]
# one dataset per block, for the cases below
FIRST = {
    "photo": "swissimage",
    "roofs": "swissimage",
    "surfaces": "swisstlm3d",
    "trees": "swissalti3d",
}


def _moved_world(tmp_path):
    data = json.loads(WORLD.read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1.0
    path = tmp_path / "moved" / "world.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _manifest(tmp_path, monkeypatch, capsys, block, dataset=None, change=None, world=WORLD):
    """`python -m mattini manifest --out <tmp>` over a stand-in `<block>/village.json`, the
    committed configs, the world given and a lock whose `dataset` entry `change` alters:
    (exit status, stderr)."""
    pinned = copy.deepcopy(LOCK)
    if change is DROP:
        del pinned["datasets"][dataset]
    elif change is not None:
        change(pinned["datasets"][dataset])
    lock_path = write_lock(pinned, tmp_path / "datasets.lock.json")  # a well-formed lock
    out = tmp_path / "generated"
    (out / block).mkdir(parents=True)
    (out / block / f"{AREA}.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "write_manifest",
        functools.partial(write_manifest, config_path=world, lock_path=lock_path),
    )
    status = cli.main(["manifest", "--out", str(out)])
    captured = capsys.readouterr()
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: error: "), captured.err
    assert "Traceback" not in captured.err
    return status, lines[0]


@pytest.mark.parametrize(("block", "dataset", "change"), UNFITTING)
def test_a_lock_that_does_not_fit_is_named_before_the_inputs_and_the_block(
    tmp_path, monkeypatch, capsys, block, dataset, change
):
    status, message = _manifest(tmp_path, monkeypatch, capsys, block, dataset, change)
    assert status == 1
    assert _named(message) == {LOCK_OF[dataset]}, message


@pytest.mark.parametrize("block", sorted(FIRST))
def test_a_changed_world_comes_before_the_lock(tmp_path, monkeypatch, capsys, block):
    status, message = _manifest(
        tmp_path, monkeypatch, capsys, block, FIRST[block], DROP, world=_moved_world(tmp_path)
    )
    assert status == 1
    assert _named(message) == {DESIGN} and "config/world.json" in message, message


@pytest.mark.parametrize("block", sorted(FIRST))
def test_a_fitting_lock_with_other_inputs_names_design_s_step(tmp_path, monkeypatch, capsys, block):
    status, message = _manifest(tmp_path, monkeypatch, capsys, block, FIRST[block], _other_file)
    assert status == 1
    assert _named(message) == {DESIGN} and f"config/{block}.json" in message, message


@pytest.mark.parametrize("block", sorted(FIRST))
def test_the_committed_lock_fits_and_the_block_is_checked(tmp_path, monkeypatch, capsys, block):
    """Positive control: world, fit and inputs hold; the stand-in is refused as a block
    (the roofs, which colour buildings, first for the buildings none has built)."""
    status, message = _manifest(tmp_path, monkeypatch, capsys, block)
    assert status == 1
    wanted = "python -m mattini buildings" if block == "roofs" else f"python -m mattini {block}"
    assert _named(message) == {wanted}, message
