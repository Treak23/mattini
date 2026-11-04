"""Pinning tests for brief v0.6.0-07: the manifest's `surroundings` block (design §3, §5).

Pinned decisions (brief v0.6.0-07 decisions 3 and 4; brief M4-09 decision 3, re-scoped; brief
v0.6.0-08 decision 1, the block's shape):

- The manifest's top level is exactly `buildings`, `photo`, `roofs`, `schema`, `shadows`, `sky`,
  `surfaces`, `surroundings`, `terrain`, `trees`, `world` and `world_sha256` (twelve keys);
  `schema` stays 1; the text is `json.dumps(manifest, indent=2, sort_keys=True,
  ensure_ascii=False)` and a final LF, in UTF-8.
- `write_manifest` and `build_manifest` take `surroundings_config_path` (default
  config/surroundings.json) beside the other configs; the surroundings config is loaded and
  checked even when neither step has run (a config the reader refuses is refused, nothing
  written). The block is for the one area that config names.
- The `surroundings` block is ONE flat object of exactly 20 keys: the heights' description
  `python -m mattini surroundings` wrote (`surroundings/<area>.json`, brief v0.6.0-04, 11 keys)
  and the colour's description `python -m mattini farcolour` wrote
  (`surroundings/<area>_colour.json`, brief v0.6.0-06, the nine `colour_` and `filled_fraction`
  keys), side by side, each verbatim, no key in both: brief v0.6.0-08's reader refuses any other
  key set.
- It is null while the heights' description is absent from the folder and while the colour's is
  (the heights alone are the state between the two commands in pipeline order: null, so the
  game says which commands build it); never an empty object, never computed by `manifest` from
  the config. The colour's description WITHOUT the heights' is refused, a FarColourError naming
  `python -m mattini surroundings` (the roofs' rule for a step that needs an earlier one), and
  nothing is written.
- Every earlier fixture's committed manifest (the seven M2/M3 fixtures and the shadows fixture)
  is its v0.5.0-02 text plus one line, `  "surroundings": null,`, right before the `terrain`
  line, nothing else: design's copies, made three ways (that text edit; the pin author's
  throwaway `write_manifest`, test_manifest_m3.py and test_m4_09_manifest.py; brief M4-09's
  pinned copies, identical for six fixtures and the shadows fixture). Both SHA-256s pinned
  (lesson 33).
- The far colour fixture (tests/shared/farcolour_fixture/, brief v0.6.0-06), built at test time
  by both steps from its synthetic inputs with its committed configs and lock, gives the
  manifest pinned here (SHA-256 and size; made two ways: the throwaway `write_manifest`, and the
  dict assembled by hand from the two descriptions and the world).
- The surroundings fixture's committed manifest (tests/shared/surroundings_fixture/, brief
  v0.6.0-08's design data for the game, `c75b7bd7…`) is NOT what `write_manifest` writes from its
  folder: that fixture has no colour description (its colour JPEG is v0.6.0-08's designed
  placeholder), so its folder gives a null block. Its file is not this brief's and stays as it is.

Does NOT prove: that the game reads the block (brief v0.6.0-08's reader, v0.6.0-09's scene);
that the real village's block is design's (the brief's real run, and the release gate).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from synthetic_farphoto import FIXTURE, fixture_datasets, raw_inputs

from mattini.farcolour import FarColourError, build_farcolour
from mattini.manifest import build_manifest, write_manifest
from mattini.surroundings import (
    SurroundingsError,
    build_surroundings,
    load_surroundings_config,
)
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
TOP_LEVEL = {
    "buildings",
    "photo",
    "roofs",
    "schema",
    "shadows",
    "sky",
    "surfaces",
    "surroundings",
    "terrain",
    "trees",
    "world",
    "world_sha256",
}
BLOCKS = sorted(TOP_LEVEL - {"schema", "world", "world_sha256"})
HEIGHTS_KEYS = {
    "area",
    "columns",
    "cut_box",
    "file",
    "format",
    "lv95_box",
    "rows",
    "sha256",
    "source",
    "spacing_m",
    "world_sha256",
}
COLOUR_KEYS = {
    "colour_cell_m",
    "colour_columns",
    "colour_file",
    "colour_format",
    "colour_pixels_sha256",
    "colour_rows",
    "colour_sha256",
    "colour_source",
    "filled_fraction",
}
LINE = '  "surroundings": null,'
# Each earlier fixture's committed manifest: v0.5.0-02's SHA-256 (before), this brief's (after).
FIXTURES = {
    "terrain_fixture": (
        "3d5d9e353dec37c32a0e0f3aaef90871e5eebcad6f4ee6ffcc03594e44e24fab",
        "7da6238dc7cad625ecab5039be762c7d9518b001f7c5ab5524597fca27f36cd1",
    ),
    "terrain_fixture_nw": (
        "fd2481dffa88ebbc7be198fabc8758a7d7fb6c6a1502fb88c7d6aae91597ca84",
        "d5b2566d7467cc9278bf6ab720869f288432e9947fea18ffbdd51b9a7a46ff97",
    ),
    "buildings_fixture": (
        "5814d95c2af053eb1955b2762599fbacbe9aabe61859c03e7ebcf925ed67770d",
        "e21c525b8d8c714fd92feec7e8945730a015e62879ded0f54ee697dccaa6e442",
    ),
    "photo_fixture": (
        "252c92a7bc858aa0169cb6eaccc199719f86a46b36c54f6dd4c04cda92ac611f",
        "72a550df79c733392eabbad4dfca3602b4d6e68fc3d73cb2bf78883f0414c1a7",
    ),
    "roofs_fixture": (
        "f65abc0b7fc685fa53005bd1e37cc92fb57d24e2ab30a04ba209a18bcb47bea7",
        "396e5b2b70165992d709762bfac7ae9412131df2de7aa14cf0e3a5f7550a3ee6",
    ),
    "surfaces_fixture": (
        "1df51af7602407115ddba5c990c6e02ca8aaabae902fe8f8de40fe12fb8843e5",
        "6e9300dfccee77d47b2af3a087b0fc0b2f1eed14c6d98337922720fb7adeb22a",
    ),
    "trees_fixture": (
        "c9066f6d68ce27cc71c5db1ccb649ea5fa829c1f6d7968fb6b1e75b4dc885645",
        "8bd7a99d986ab30aa98c2eaa8956108d7295ef6d2936ec682526f5ad99a8ff5b",
    ),
    "shadows_fixture": (
        "0ffcf8984de34e783aa301d270de6af004dfbb2d0ba74bfd493f6cc90c2b90ea",
        "d4bceb8f9c77daf4cd5efa2355b4b4d90df555c98bb04c476bfc854483108993",
    ),
}
# The far colour fixture built by both steps: the manifest's SHA-256 and size.
FARCOLOUR_MANIFEST = ("ae165f6142dfa85f0baa75bb4929cf34e0fd08162ac2225a8e5575fbfa81218a", 2219)
# brief v0.6.0-08's committed manifest of the surroundings fixture (the game's design data)
SURROUNDINGS_FIXTURE_MANIFEST = (
    "c75b7bd7ee0b98249b6cb1f8bdb2cf570da075ac1c48a291de3d71241b11f557",
    2206,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(manifest: dict) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _write(out: Path, **configs) -> Path:
    """`write_manifest` with the far colour fixture's world, datasets config, lock and
    surroundings config (every other config the committed one, for a step not run there)."""
    paths = {
        "datasets_path": FIXTURE / "datasets.json",
        "lock_path": FIXTURE / "datasets.lock.json",
        "surroundings_config_path": FIXTURE / "surroundings.json",
    }
    paths.update(configs)
    return write_manifest(out, FIXTURE / "world.json", **paths)


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    """Both steps run on the far colour fixture's synthetic inputs, its committed configs and
    lock: the folder `python -m mattini surroundings` and `farcolour` leave (no manifest)."""
    tmp = tmp_path_factory.mktemp("built")
    root, made = raw_inputs(tmp / "raw")
    lock = json.loads((FIXTURE / "datasets.lock.json").read_bytes())
    assert made == lock, "the fixture's lock pins the inputs its helpers write"
    world = load_world(FIXTURE / "world.json")
    config = load_surroundings_config(FIXTURE / "surroundings.json")
    out = tmp / "out"
    build_surroundings(world, fixture_datasets(), lock, config, root, out)
    build_farcolour(world, fixture_datasets(), lock, config, root, out)
    return out


def _copy(built: Path, tmp_path: Path, *, leave_out: tuple[str, ...] = ()) -> Path:
    out = tmp_path / "generated"
    shutil.copytree(built, out, ignore=shutil.ignore_patterns(*leave_out))
    return out


def _description(built: Path, name: str) -> dict:
    return json.loads((built / "surroundings" / name).read_bytes())


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_an_earlier_fixture_s_manifest_is_its_previous_text_with_one_null_line(name):
    raw = (SHARED / name / "generated" / "manifest.json").read_bytes()
    before, after = FIXTURES[name]
    assert _sha(raw) == after, name
    lines = raw.decode("utf-8").split("\n")
    assert lines.count(LINE) == 1, name
    at = lines.index(LINE)
    assert lines[at + 1].startswith('  "terrain": '), name
    assert lines[at - 1].startswith("  ") and lines[at - 1].endswith(","), name
    previous = "\n".join(lines[:at] + lines[at + 1 :]).encode("utf-8")
    assert _sha(previous) == before, name
    manifest = json.loads(raw)
    assert set(manifest) == TOP_LEVEL and manifest["surroundings"] is None
    assert raw == _canonical(manifest)


def test_with_nothing_built_the_surroundings_block_is_null(tmp_path):
    """The committed configs (config/surroundings.json holds the village's design data), an
    empty folder: null, the step's rule, not the config's."""
    raw = write_manifest(tmp_path / "empty").read_bytes()
    manifest = json.loads(raw)
    assert set(manifest) == TOP_LEVEL and manifest["schema"] == 1
    assert {key: manifest[key] for key in BLOCKS} == dict.fromkeys(BLOCKS)
    assert b'  "surroundings": null,\n' in raw


def test_both_steps_built_give_the_two_descriptions_side_by_side(built, tmp_path):
    out = _copy(built, tmp_path)
    raw = _write(out).read_bytes()
    assert (_sha(raw), len(raw)) == FARCOLOUR_MANIFEST
    manifest = json.loads(raw)
    assert set(manifest) == TOP_LEVEL and raw == _canonical(manifest)
    assert [key for key in BLOCKS if manifest[key] is not None] == ["surroundings"]
    heights = _description(built, "fixture.json")
    colour = _description(built, "fixture_colour.json")
    assert set(heights) == HEIGHTS_KEYS and set(colour) == COLOUR_KEYS
    block = manifest["surroundings"]
    assert set(block) == HEIGHTS_KEYS | COLOUR_KEYS and len(block) == 20
    assert block == {**heights, **colour}
    world = (FIXTURE / "world.json").read_bytes()
    by_hand = dict.fromkeys(BLOCKS)
    by_hand.update(
        schema=1,
        surroundings={**heights, **colour},
        world=json.loads(world),
        world_sha256=_sha(world),
    )
    assert raw == _canonical(by_hand)


def test_the_heights_alone_give_null_and_nothing_else_changes(built, tmp_path):
    out = _copy(built, tmp_path, leave_out=("fixture_colour.*",))
    assert (out / "surroundings" / "fixture.json").exists()
    manifest = json.loads(_write(out).read_bytes())
    both = json.loads(_write(_copy(built, tmp_path / "both")).read_bytes())
    assert manifest["surroundings"] is None and both["surroundings"] is not None
    both["surroundings"] = None
    assert manifest == both


def test_the_colour_without_the_heights_is_refused_naming_the_surroundings_command(built, tmp_path):
    out = _copy(built, tmp_path, leave_out=("fixture.json", "fixture.f32"))
    assert (out / "surroundings" / "fixture_colour.json").exists()
    with pytest.raises(FarColourError) as refusal:
        _write(out)
    assert "python -m mattini surroundings" in str(refusal.value), str(refusal.value)
    assert "python -m mattini farcolour" not in str(refusal.value), str(refusal.value)
    assert not (out / "manifest.json").exists()


def test_neither_description_gives_null_whatever_the_files_beside_them(built, tmp_path):
    """The heights' and colour's data files alone (no description) are not a build."""
    out = _copy(built, tmp_path, leave_out=("*.json",))
    assert (out / "surroundings" / "fixture.f32").exists()
    assert json.loads(_write(out).read_bytes())["surroundings"] is None


@pytest.mark.parametrize(
    ("damaged", "command"),
    [
        ("fixture.f32", "python -m mattini surroundings"),
        ("fixture_colour.jpg", "python -m mattini farcolour"),
    ],
)
def test_a_damaged_half_is_refused_naming_its_own_step(built, tmp_path, damaged, command):
    out = _copy(built, tmp_path)
    path = out / "surroundings" / damaged
    path.write_bytes(path.read_bytes()[:-1] + b"\x00")
    with pytest.raises((SurroundingsError, FarColourError)) as refusal:
        _write(out)
    assert command in str(refusal.value), str(refusal.value)
    assert not (out / "manifest.json").exists()


def test_a_surroundings_config_the_reader_refuses_is_refused_with_nothing_built(tmp_path):
    config = json.loads((REPO / "config" / "surroundings.json").read_bytes())
    config["schema"] = 1
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(SurroundingsError) as refusal:
        build_manifest(out_dir=tmp_path / "empty", surroundings_config_path=path)
    assert str(path) in str(refusal.value), str(refusal.value)
    with pytest.raises(SurroundingsError):
        write_manifest(tmp_path / "empty", surroundings_config_path=path)
    assert not (tmp_path / "empty" / "manifest.json").exists()


def test_the_surroundings_fixture_s_committed_manifest_is_the_game_s_design_data(tmp_path):
    """brief v0.6.0-08's file is kept byte for byte; its folder holds no colour description,
    so `write_manifest` gives null for it: the file is design data for the game's reader."""
    fixture = SHARED / "surroundings_fixture"
    committed = (fixture / "generated" / "manifest.json").read_bytes()
    assert (_sha(committed), len(committed)) == SURROUNDINGS_FIXTURE_MANIFEST
    assert set(json.loads(committed)) == TOP_LEVEL
    out = tmp_path / "generated"
    shutil.copytree(fixture / "generated" / "surroundings", out / "surroundings")
    assert not (out / "surroundings" / "fixture_colour.json").exists()
    manifest = json.loads(
        write_manifest(
            out,
            fixture / "world.json",
            datasets_path=fixture / "datasets.json",
            lock_path=fixture / "datasets.lock.json",
            surroundings_config_path=fixture / "surroundings.json",
        ).read_bytes()
    )
    assert manifest["surroundings"] is None
