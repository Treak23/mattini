"""The manifest re-checks a built terrain's source (brief M2-01; M1 R1 T-03, T-04; SPEC §8).

`manifest` refuses, naming `python -m mattini terrain` and writing nothing, a built terrain
whose `source` is not exactly the datasets config's attribution, collection, edition and
resolution with the exact key sets, or whose tiles are not, in order, the tiles covering
the area with the SHA-256s the tile lock pins. The class M1 R1 T-04 named: an input of a
built terrain that `manifest` did not re-check (the lock, the attribution, the
collection; the fourth member, the code, is the expected SHA-256 of
test_terrain_expected.py). The one-tile world of test_terrain_refusals.py is built for
real, then its inputs change the way the owner would change them, with no `terrain` run.

Does NOT prove: a real republish by swisstopo (simulated with a synthetic tile); that the
game shows the new attribution (the manifest is its only source, SPEC §8).
"""

import hashlib
import json

import numpy as np
import pytest
from test_terrain_build_tiles import EXPECTED, four_tiles  # noqa: F401 (a fixture)
from test_terrain_build_tiles import TILES as FOUR_TILES
from test_terrain_build_tiles import _config as four_tiles_config
from test_terrain_refusals import NAME, TILE, _heights, _write_tile, case  # noqa: F401

from mattini import lock
from mattini.datasets import load_datasets
from mattini.manifest import write_manifest
from mattini.terrain import TerrainError, build_terrain
from mattini.world import REPO

TERRAIN_COMMAND = "python -m mattini terrain"
LOCK_COMMAND = "python -m mattini lock terrain"
DATASETS = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))


@pytest.fixture
def built(case):  # noqa: F811
    """The one-tile terrain built for real, with its lock, terrain and datasets configs on disk."""
    build_terrain(
        case["world"],
        case["datasets"],
        case["lock"],
        case["config"],
        case["tmp"] / "raw",
        case["out"],
    )
    paths = {
        "world": case["world"].path,
        "terrain": case["tmp"] / "terrain.json",
        "datasets": case["tmp"] / "datasets.json",
        "lock": case["tmp"] / "datasets.lock.json",
    }
    paths["terrain"].write_text(json.dumps(case["config"]), encoding="utf-8")
    paths["datasets"].write_text(json.dumps(DATASETS), encoding="utf-8")
    lock.write_lock(case["lock"], paths["lock"])
    return dict(case, paths=paths)


def _manifest(built):
    return write_manifest(
        built["out"],
        built["paths"]["world"],
        terrain_config_path=built["paths"]["terrain"],
        datasets_path=built["paths"]["datasets"],
        lock_path=built["paths"]["lock"],
    )


def _refused(built, *patterns):
    with pytest.raises(TerrainError) as refused:
        _manifest(built)
    message = str(refused.value)
    for pattern in (TERRAIN_COMMAND, *patterns):
        assert pattern in message, (pattern, message)
    assert not (built["out"] / "manifest.json").exists()
    return message


def _edit_json(path, change):
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _edit_source(built, change):
    _edit_json(built["out"] / "terrain" / "village.json", lambda block: change(block["source"]))


def test_a_terrain_built_from_the_locked_tiles_is_accepted(built):
    manifest = json.loads(_manifest(built).read_bytes())
    block = json.loads((built["out"] / "terrain" / "village.json").read_bytes())
    assert manifest["terrain"] == block
    assert block["source"]["tiles"] == [
        {"sha256": built["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"], "tile": TILE}
    ]


def test_a_tile_the_lock_now_pins_differently_is_refused(built):
    """M1 R1 T-04's proof: the tile republished, then locked and downloaded, but no `terrain`."""
    path = built["raw_dir"] / NAME
    _write_tile(path, _heights() + np.float32(0.25))
    new = hashlib.sha256(path.read_bytes()).hexdigest()
    _edit_json(
        built["paths"]["lock"],
        lambda lk: lk["datasets"]["swissalti3d"]["tiles"][TILE].update(sha256=new),
    )
    old = built["lock"]["datasets"]["swissalti3d"]["tiles"][TILE]["sha256"]
    _refused(built, TILE, old, new)


@pytest.mark.parametrize("key", ["attribution", "collection"])
def test_a_changed_datasets_config_is_refused(built, key):
    """The credits come from the manifest: a new attribution needs a rebuild (T-04)."""
    changed = {"attribution": "© swisstopo, new wording", "collection": "ch.swisstopo.other"}
    _edit_json(
        built["paths"]["datasets"],
        lambda d: d["datasets"]["swissalti3d"].update({key: changed[key]}),
    )
    _refused(built, key, changed[key])


SOURCE_KEYS = "exactly the keys ['attribution', 'collection', 'dataset', 'edition', 'resolution_m'"
TILE_KEYS = "tiles must be a list of entries with exactly the keys ['sha256', 'tile']"


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda s: s.update(built_on="2026-09-25"), SOURCE_KEYS),
        (lambda s: s.update(built_by="vm"), SOURCE_KEYS),
        (lambda s: s.pop("attribution"), SOURCE_KEYS),
        (lambda s: s["tiles"][0].update(file=NAME), TILE_KEYS),
        (lambda s: s["tiles"][0].pop("sha256"), TILE_KEYS),
        (lambda s: s.update(tiles={TILE: s["tiles"][0]["sha256"]}), TILE_KEYS),
        (lambda s: s.update(dataset="swissalti3d_2m"), "the dataset 'swissalti3d_2m'"),
        (lambda s: s.update(edition="2019"), "edition '2019'"),
        (lambda s: s.update(resolution_m=2.0), "resolution_m 2.0"),
        (lambda s: s.update(tiles=[]), "built from the tiles []"),
        (lambda s: s.update(tiles=s["tiles"] * 2), f"tiles ['{TILE}', '{TILE}']"),
        (lambda s: s["tiles"][0].update(tile="2623-1095"), "built from the tiles ['2623-1095']"),
        (lambda s: s["tiles"][0].update(sha256="ab" * 32), "ab" * 32),
    ],
    ids=[
        "a-date",
        "a-host",
        "a-key-missing",
        "a-tile-key-added",
        "a-tile-key-missing",
        "tiles-not-a-list",
        "another-dataset",
        "another-edition",
        "another-resolution",
        "no-tiles",
        "a-tile-twice",
        "another-tile",
        "another-tile-sha256",
    ],
)
def test_a_source_that_is_not_exactly_the_inputs_is_refused(built, change, reason):
    """T-03: no field a day or a machine could change gets through; T-04: nor a stale input."""
    _edit_source(built, change)
    _refused(built, reason)


def test_a_lock_without_the_area_s_tile_names_the_lock_command(built):
    """The lock itself does not fit the area: `lock terrain` is the command that helps."""
    _edit_json(
        built["paths"]["lock"],
        lambda lk: lk["datasets"]["swissalti3d"]["tiles"].update(
            {"2623-1095": lk["datasets"]["swissalti3d"]["tiles"].pop(TILE)}
        ),
    )
    with pytest.raises(TerrainError, match=LOCK_COMMAND):
        _manifest(built)
    assert not (built["out"] / "manifest.json").exists()


def test_without_a_built_terrain_the_lock_is_not_read(tmp_path):
    """A manifest with `terrain` null depends on no lock (the gate's containers build none)."""
    manifest = write_manifest(tmp_path / "out", lock_path=tmp_path / "no-such-lock.json")
    assert json.loads(manifest.read_bytes())["terrain"] is None


def test_the_tiles_must_come_in_the_area_s_order(four_tiles, tmp_path):  # noqa: F811
    """Four tiles, built for real: the same tiles in another order are refused."""
    out = tmp_path / "generated"
    sha256 = EXPECTED[2.0][0]
    config = four_tiles_config(2.0, sha256)
    build_terrain(
        four_tiles["world"],
        load_datasets(),
        four_tiles["lock"],
        config,
        four_tiles["raw_root"],
        out,
    )
    terrain_path, lock_path = tmp_path / "terrain.json", tmp_path / "datasets.lock.json"
    terrain_path.write_text(json.dumps(config), encoding="utf-8")
    lock.write_lock(four_tiles["lock"], lock_path)

    def manifest():
        return write_manifest(
            out, four_tiles["world"].path, terrain_config_path=terrain_path, lock_path=lock_path
        )

    written = json.loads(manifest().read_bytes())["terrain"]
    assert [entry["tile"] for entry in written["source"]["tiles"]] == FOUR_TILES
    (out / "manifest.json").unlink()
    _edit_json(out / "terrain" / "village.json", lambda b: b["source"]["tiles"].reverse())
    with pytest.raises(TerrainError, match=TERRAIN_COMMAND) as refused:
        manifest()
    assert str(FOUR_TILES) in str(refused.value)
    assert not (out / "manifest.json").exists()
