"""Pinning tests for brief M4-09: `manifest` checks each new block's world, lock fit and
inputs first, then the block.

Pinned decisions (docs/SPEC.md §8, *The manifest*; brief M3-13's order, M4-09): for a built
`surroundings` or `shadows` block, `manifest` compares the step config's `computed_for` with
the world config first (config/surroundings.json, config/shadows.json), then checks that the
lock's entry of the dataset the step reads fits the datasets config and the area through
`lock.fit_problem` (swissaltiregio: the tiles of the area's surroundings at the surroundings
config's `margin_m` and `spacing_m`; swisssurface3d: the area's tiles, each at an edition the
config accepts), then compares `computed_for.inputs_sha256` with that entry
(`lock.entry_sha256`), and only then checks the block itself. A lock that does not fit is a
refusal naming `python -m mattini lock regio` or `python -m mattini lock surface` and no
other command; a changed world, or a fitting lock with other inputs, names design's step and
the step's config. For a built `sky` block (`sky/<area>.json`), a world config that is not the
one config/sky.json was computed for names design's step and config/sky.json, before the
block; a block that is not config/sky.json's values for this world names
`python -m mattini sky`. Each refusal is one `mattini: error:` line, exit status 1, and no
manifest.

The configs and the lock are the committed ones (the village; the lock with brief M4-01's
`swissaltiregio` entry), the built block a stand-in `{}` that any check of a block refuses, so
only a check made before the block's own can name anything else. Harm prevented: the review's
"refusals before the one that helps" (M2 V1-P-01) for the three new blocks, and a lock
without the new dataset's entry ending in a KeyError traceback.

Does NOT prove: that the committed lock is swisstopo's (brief M4-01's tests); anything about
the files a fitting lock vouches for.
"""

import copy
import functools
import hashlib
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
AREA = "village"  # the one area of config/terrain.json, surroundings.json, shadows.json, sky.json
COMMAND = re.compile(
    r"python -m mattini (?:(?:lock|download) )?"
    r"(?:terrain|buildings|photo|surface|tlm|regio|roofs|surfaces|trees|surroundings|shadows|sky)\b"
    r"|python -m mattini manifest"
)
DESIGN = "design's step"  # what a refusal names when it says "design recomputes"
LOCK_OF = {
    "swissaltiregio": "python -m mattini lock regio",
    "swisssurface3d": "python -m mattini lock surface",
}
DATASET_OF = {"surroundings": "swissaltiregio", "shadows": "swisssurface3d"}


def _named(message: str) -> set[str]:
    named = set(COMMAND.findall(message))
    if "design recomputes" in message:
        named.add(DESIGN)
    return named


def _extra_tile(entry):
    """One tile beyond the last (10 km east for swissALTIRegio, 1 km for swissSURFACE3D)."""
    first, second = max(entry["tiles"]).split("-")
    step = 10 if entry["collection"] == "ch.swisstopo.swissaltiregio" else 1
    entry["tiles"][f"{int(first) + step:04d}-{second}"] = copy.deepcopy(
        entry["tiles"][max(entry["tiles"])]
    )


def _missing_tile(entry):
    del entry["tiles"][sorted(entry["tiles"])[len(entry["tiles"]) // 2]]


def _surface_edition(entry):
    entry["tiles"][min(entry["tiles"])]["edition"] = "2019"  # a year the config does not accept


def _other_file(entry):
    """A fitting entry whose inputs changed: one file's SHA-256 (an adopted republish)."""
    entry["tiles"][min(entry["tiles"])]["sha256"] = "ab" * 32


DROP = "drop"  # the change that removes the dataset's entry

UNFITTING = [
    pytest.param("surroundings", _extra_tile, id="surroundings-extra-tile"),
    pytest.param("surroundings", _missing_tile, id="surroundings-missing-tile"),
    pytest.param("surroundings", DROP, id="surroundings-no-entry"),
    pytest.param(
        "surroundings", lambda e: e.update(resolution_m=2), id="surroundings-another-resolution"
    ),
    pytest.param(
        "surroundings", lambda e: e.update(edition="2025-06"), id="surroundings-another-edition"
    ),
    pytest.param("shadows", _extra_tile, id="shadows-extra-tile"),
    pytest.param("shadows", DROP, id="shadows-no-entry"),
    pytest.param("shadows", _surface_edition, id="shadows-edition-not-accepted"),
    pytest.param(
        "shadows",
        lambda e: e.update(collection="ch.swisstopo.swisssurface3d-raster_x"),
        id="shadows-another-collection",
    ),
]


def _moved_world(tmp_path):
    data = json.loads(WORLD.read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1.0
    path = tmp_path / "moved" / "world.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _manifest(tmp_path, monkeypatch, capsys, block, change=None, world=WORLD, text="{}\n"):
    """`python -m mattini manifest --out <tmp>` over a stand-in `<block>/village.json`, the
    committed configs, the world given and a lock whose entry for the block's dataset `change`
    alters: (exit status, the one stderr line)."""
    pinned = copy.deepcopy(LOCK)
    dataset = DATASET_OF.get(block)
    if change is DROP:
        del pinned["datasets"][dataset]
    elif change is not None:
        change(pinned["datasets"][dataset])
    lock_path = write_lock(pinned, tmp_path / "datasets.lock.json")  # a well-formed lock
    out = tmp_path / "generated"
    (out / block).mkdir(parents=True)
    (out / block / f"{AREA}.json").write_text(text, encoding="utf-8")
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


@pytest.mark.parametrize(("block", "change"), UNFITTING)
def test_a_lock_that_does_not_fit_is_named_before_the_inputs_and_the_block(
    tmp_path, monkeypatch, capsys, block, change
):
    status, message = _manifest(tmp_path, monkeypatch, capsys, block, change)
    assert status == 1
    assert _named(message) == {LOCK_OF[DATASET_OF[block]]}, message


@pytest.mark.parametrize("block", ["shadows", "sky", "surroundings"])
def test_a_changed_world_comes_first(tmp_path, monkeypatch, capsys, block):
    change = DROP if block in DATASET_OF else None  # the lock would be refused next
    status, message = _manifest(
        tmp_path, monkeypatch, capsys, block, change, world=_moved_world(tmp_path)
    )
    assert status == 1
    assert _named(message) == {DESIGN}, message
    assert "config/world.json" in message and f"config/{block}.json" in message, message


@pytest.mark.parametrize("block", sorted(DATASET_OF))
def test_a_fitting_lock_with_other_inputs_names_design_s_step(tmp_path, monkeypatch, capsys, block):
    status, message = _manifest(tmp_path, monkeypatch, capsys, block, _other_file)
    assert status == 1
    assert _named(message) == {DESIGN} and f"config/{block}.json" in message, message


@pytest.mark.parametrize("block", ["shadows", "sky", "surroundings"])
def test_the_committed_lock_fits_and_the_block_is_checked(tmp_path, monkeypatch, capsys, block):
    """Positive control: world, fit and inputs hold; the stand-in is refused as a block,
    naming the step's command."""
    status, message = _manifest(tmp_path, monkeypatch, capsys, block)
    assert status == 1
    assert _named(message) == {f"python -m mattini {block}"}, message


def _sky_values() -> dict:
    sky = json.loads((CONFIG / "sky.json").read_text(encoding="utf-8"))
    (values,) = sky["areas"].values()
    world_sha256 = hashlib.sha256(WORLD.read_bytes()).hexdigest()
    block = {key: values[key] for key in ("latitude_deg", "longitude_deg", "true_to_grid_deg")}
    return {"area": AREA, **block, "world_sha256": world_sha256}


def _sky_text(block: dict) -> str:
    return json.dumps(block, indent=2, sort_keys=True) + "\n"


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda b: b.update(latitude_deg=b["latitude_deg"] + 0.01), id="latitude"),
        pytest.param(lambda b: b.update(longitude_deg=b["longitude_deg"] - 0.01), id="longitude"),
        pytest.param(lambda b: b.update(true_to_grid_deg=0.2258), id="sign-of-true-to-grid"),
        pytest.param(lambda b: b.update(world_sha256="ab" * 32), id="world"),
        pytest.param(lambda b: b.update(area="fixture"), id="area"),
        pytest.param(lambda b: b.update(latitude_deg=str(b["latitude_deg"])), id="a-string"),
        pytest.param(lambda b: b.pop("true_to_grid_deg"), id="a-key-missing"),
        pytest.param(lambda b: b.update(note="x"), id="a-key-added"),
    ],
)
def test_a_sky_block_that_is_not_the_config_s_values_names_the_sky_step(
    tmp_path, monkeypatch, capsys, change
):
    block = _sky_values()
    change(block)
    status, message = _manifest(tmp_path, monkeypatch, capsys, "sky", text=_sky_text(block))
    assert status == 1
    assert _named(message) == {"python -m mattini sky"}, message


def test_the_sky_block_is_the_config_s_values_for_this_world(tmp_path):
    """Positive control: config/sky.json's values, the area and the world's SHA-256 pass and
    are copied verbatim."""
    out = tmp_path / "generated"
    (out / "sky").mkdir(parents=True)
    (out / "sky" / f"{AREA}.json").write_text(_sky_text(_sky_values()), encoding="utf-8")
    manifest = json.loads(write_manifest(out).read_bytes())
    assert manifest["sky"] == _sky_values()
