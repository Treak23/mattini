"""Pinning tests for brief v0.4.0-07 (brief M4-09 cut to the sky): `manifest` checks a built
`sky` block's world, then its area, then the block.

Pinned decisions (docs/SPEC.md §8, *The manifest*; brief M4-09 decisions 2 and 4, the sky
only): the sky block has no lock. For a built `sky` block (`sky/<area>.json`, the area
config/sky.json names), `manifest` compares config/sky.json's `computed_for.world_sha256` with
the world config's bytes first: a world config that is not the one config/sky.json was computed
for names design's step ("design recomputes"), config/sky.json and config/world.json, and no
command. Then the area: a sky config whose area the world config does not have (its
`computed_for` this world's) names the area and config/sky.json, and no command (running a step
again cannot help). Only then the block: a description that is not config/sky.json's values for
this world (each value, the area, the world's SHA-256, a key missing or added, a value's JSON
type) names `python -m mattini sky`. Each refusal is one `mattini: error:` line, exit status 1,
and no manifest.

The configs are the committed ones (the village), the built block a stand-in `{}` that the
block's check refuses, so only a check made before the block's own can name anything else.
Harm prevented: the review's "refusals before the one that helps" (M2 V1-P-01) for the sky
block, and a stale `sky/<area>.json` (another world's place, a flipped convergence) reaching
the game.

Does NOT prove: that config/sky.json's values are the place's (test_m4_09_sky_config.py);
that the game reads the block (brief v0.4.0-08).
"""

import functools
import hashlib
import json
import re

import pytest

import mattini.__main__ as cli
from mattini.manifest import write_manifest
from mattini.world import REPO

CONFIG = REPO / "config"
WORLD = CONFIG / "world.json"
SKY = CONFIG / "sky.json"
AREA = "village"  # the one area of config/terrain.json and config/sky.json
COMMAND = re.compile(
    r"python -m mattini (?:(?:lock|download) )?"
    r"(?:terrain|buildings|photo|surface|tlm|roofs|surfaces|trees|sky)\b"
    r"|python -m mattini manifest"
)
DESIGN = "design's step"  # what a refusal names when it says "design recomputes"


def _named(message: str) -> set[str]:
    named = set(COMMAND.findall(message))
    if "design recomputes" in message:
        named.add(DESIGN)
    return named


def _world(tmp_path, change):
    data = json.loads(WORLD.read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / "world" / "world.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _moved(data):
    data["origin_lv95"]["e"] += 1.0


def _renamed(data):
    data["areas"] = {"elsewhere": data["areas"][AREA]}


def _sky_for_another_area(tmp_path):
    """config/sky.json, its one area renamed `elsewhere`, still computed for this world."""
    data = json.loads(SKY.read_text(encoding="utf-8"))
    data["areas"] = {"elsewhere": data["areas"][AREA]}
    path = tmp_path / "sky" / "sky.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _manifest(tmp_path, monkeypatch, capsys, *, world=WORLD, sky=SKY, area=AREA, text="{}\n"):
    """`python -m mattini manifest --out <tmp>` over a stand-in `sky/<area>.json`, the
    committed configs but the world and sky config given: (exit status, the one stderr line)."""
    out = tmp_path / "generated"
    (out / "sky").mkdir(parents=True)
    (out / "sky" / f"{area}.json").write_text(text, encoding="utf-8")
    monkeypatch.setattr(
        cli,
        "write_manifest",
        functools.partial(write_manifest, config_path=world, sky_config_path=sky),
    )
    status = cli.main(["manifest", "--out", str(out)])
    captured = capsys.readouterr()
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: error: "), captured.err
    assert "Traceback" not in captured.err
    return status, lines[0]


@pytest.mark.parametrize("change", [_moved, _renamed], ids=["origin-moved", "area-renamed"])
def test_a_changed_world_comes_first(tmp_path, monkeypatch, capsys, change):
    """Another world config (its origin moved; its area renamed, so the area check would
    refuse too): design's step, before the area and the block."""
    status, message = _manifest(tmp_path, monkeypatch, capsys, world=_world(tmp_path, change))
    assert status == 1
    assert _named(message) == {DESIGN}, message
    assert "config/world.json" in message and "config/sky.json" in message, message


def test_an_area_the_world_does_not_have_comes_before_the_block(tmp_path, monkeypatch, capsys):
    status, message = _manifest(
        tmp_path, monkeypatch, capsys, sky=_sky_for_another_area(tmp_path), area="elsewhere"
    )
    assert status == 1
    assert _named(message) == set(), message
    assert "'elsewhere'" in message and "config/sky.json" in message, message


def test_the_committed_configs_hold_and_the_block_is_checked(tmp_path, monkeypatch, capsys):
    """Positive control: world and area hold; the stand-in is refused as a block, naming the
    step's command."""
    status, message = _manifest(tmp_path, monkeypatch, capsys)
    assert status == 1
    assert _named(message) == {"python -m mattini sky"}, message


def _sky_values() -> dict:
    sky = json.loads(SKY.read_text(encoding="utf-8"))
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
    status, message = _manifest(tmp_path, monkeypatch, capsys, text=_sky_text(block))
    assert status == 1
    assert _named(message) == {"python -m mattini sky"}, message


def test_an_integer_where_the_config_writes_a_float_is_refused(tmp_path, monkeypatch, capsys):
    """A value equal as a number but of another JSON type (46 for 46.0): JSON's type is part
    of the description (Godot reads every number as a float, Python does not)."""
    block = _sky_values()
    sky = json.loads(SKY.read_text(encoding="utf-8"))
    sky["areas"][AREA]["true_to_grid_deg"] = -1.0
    path = tmp_path / "sky" / "sky.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(sky, indent=2) + "\n", encoding="utf-8")
    block["true_to_grid_deg"] = -1
    status, message = _manifest(tmp_path, monkeypatch, capsys, sky=path, text=_sky_text(block))
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
    assert type(manifest["sky"]["true_to_grid_deg"]) is float
