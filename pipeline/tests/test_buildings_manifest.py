"""The manifest's `buildings` block (brief M2-04; docs/SPEC.md §8).

Pinned decisions (brief M2-04, *The manifest*): the top level is exactly `buildings`,
`schema`, `terrain`, `world`, `world_sha256`; `buildings` is null when the folder holds no
`buildings/<area>.json` for the terrain config's area, whatever the buildings config says,
and otherwise that description copied verbatim. `manifest` refuses a built block, naming
`python -m mattini buildings`, and writes nothing, when its key sets are not exact, its
`world_sha256` is not the world config's, its `source` is not the datasets config's
attribution, collection and edition and, in order, the sheets the lock pins with their
SHA-256s, a chunk file's size or SHA-256 differs from its entry, or the chunks are not the
buildings config's. The shared buildings fixture's generated files stand in for a build.

Does NOT prove: that the game reads the block (M2-05); that the real village's block is
accepted (the real run writes the manifest after the step, Findings).
"""

import json
import shutil
from pathlib import Path

import pytest

from mattini.buildings import BuildingsError
from mattini.lock import write_lock
from mattini.manifest import write_manifest

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"
GENERATED = FIXTURE / "generated"
BUILDINGS_COMMAND = "python -m mattini buildings"
TERRAIN_FIXTURE_LOCK = REPO / "tests" / "shared" / "terrain_fixture" / "datasets.lock.json"


def _out(tmp_path) -> Path:
    out = tmp_path / "generated"
    shutil.copytree(GENERATED / "buildings", out / "buildings")
    return out


def _paths(**changes) -> dict:
    paths = {
        "config_path": FIXTURE / "world.json",
        "terrain_config_path": FIXTURE / "terrain.json",
        "datasets_path": FIXTURE / "datasets.json",
        "lock_path": FIXTURE / "datasets.lock.json",
        "buildings_config_path": FIXTURE / "buildings.json",
    }
    paths.update(changes)
    return paths


def _write(out, **changes) -> Path:
    paths = _paths(**changes)
    config_path = paths.pop("config_path")
    return write_manifest(out, config_path, **paths)


def _copy_with(tmp_path, source: Path, change) -> Path:
    data = json.loads(source.read_text(encoding="utf-8"))
    change(data)
    path = tmp_path / source.name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _edit_description(out, change) -> None:
    path = out / "buildings" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    change(block)
    path.write_text(json.dumps(block, indent=2, ensure_ascii=False), encoding="utf-8")


def _refused(out, **changes) -> str:
    with pytest.raises(BuildingsError, match=BUILDINGS_COMMAND) as refusal:
        _write(out, **changes)
    assert not (out / "manifest.json").exists(), "a refusal must write nothing"
    return str(refusal.value)


def test_a_built_block_is_copied_verbatim(tmp_path):
    path = _write(_out(tmp_path))
    assert path.read_bytes() == (GENERATED / "manifest.json").read_bytes()
    manifest = json.loads(path.read_bytes())
    assert set(manifest) == {"buildings", "schema", "terrain", "world", "world_sha256"}
    block = json.loads((GENERATED / "buildings" / "fixture.json").read_bytes())
    assert manifest["buildings"] == block


def test_without_a_description_the_block_is_null_whatever_the_buildings_config_says(tmp_path):
    out = _out(tmp_path)
    (out / "buildings" / "fixture.json").unlink()  # the chunk files alone are not a build
    manifest = json.loads(
        _write(
            out,
            lock_path=tmp_path / "no-such-lock.json",  # and no lock is read
            buildings_config_path=REPO / "config" / "buildings.json",  # another area's
        ).read_bytes()
    )
    assert manifest["buildings"] is None


def test_the_real_config_without_buildings_gives_a_null_block(tmp_path):
    manifest = json.loads(write_manifest(tmp_path).read_bytes())
    assert set(manifest) == {"buildings", "schema", "terrain", "world", "world_sha256"}
    assert manifest["buildings"] is None


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(extra=1),
        lambda b: b.pop("lv95_box"),
        lambda b: b["chunks"][0].update(extra=1),
        lambda b: b["chunks"][0].pop("buildings"),
        lambda b: b["lv95_box"].update(h_min=0.0),
        lambda b: b["source"].update(tiles=[]),
        lambda b: b["source"]["sheets"][0].update(file="source.json"),
    ],
    ids=["top-extra", "top-missing", "chunk-extra", "chunk-missing", "box", "source", "sheet"],
)
def test_key_sets_that_are_not_exact_are_refused(tmp_path, change):
    out = _out(tmp_path)
    _edit_description(out, change)
    _refused(out)


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(area="village"),
        lambda b: b.update(format="glb"),
        lambda b: b.update(world_sha256="0" * 64),
        lambda b: b["chunks"].reverse(),
        lambda b: b["chunks"][0].update(file="buildings/../2650-1149.bin"),
        lambda b: b["chunks"][0].update(tile="2650-1148"),
        lambda b: b["chunks"][0].update(vertices=b["chunks"][0]["vertices"] + 1),
        lambda b: b["chunks"][0].update(sha256="0" * 64),
        lambda b: b["source"].update(dataset="swissalti3d"),
    ],
    ids=["area", "format", "world", "order", "file", "tile", "size", "sha256", "dataset"],
)
def test_a_description_that_does_not_match_is_refused(tmp_path, change):
    out = _out(tmp_path)
    _edit_description(out, change)
    _refused(out)


def test_buildings_built_for_another_world_are_refused(tmp_path):
    world = _copy_with(tmp_path, FIXTURE / "world.json", lambda d: d.update(height_offset_m=0.0))
    message = _refused(_out(tmp_path), config_path=world)
    assert "world config" in message


@pytest.mark.parametrize("key", ["attribution", "collection", "edition"])
def test_a_source_that_is_not_the_datasets_config_s_is_refused(tmp_path, key):
    value = {"attribution": "© someone", "collection": "ch.other", "edition": "2019"}[key]
    datasets = _copy_with(
        tmp_path,
        FIXTURE / "datasets.json",
        lambda d: d["datasets"]["swissbuildings3d"].update({key: value}),
    )
    message = _refused(_out(tmp_path), datasets_path=datasets)
    assert key in message


def _lock_with(tmp_path, change) -> Path:
    data = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    change(data["datasets"]["swissbuildings3d"])
    return write_lock(data, tmp_path / "datasets.lock.json")


@pytest.mark.parametrize(
    "change",
    [
        lambda e: e["sheets"]["1249-42"].update(sha256="ab" * 32),
        lambda e: e["sheets"].update({"1249-41": e["sheets"]["1249-42"]}),
        lambda e: e.update(sheets={"1249-41": e["sheets"]["1249-42"]}),
        lambda e: e.update(edition="2019"),
    ],
    ids=["sha256", "another-sheet", "other-sheet", "edition"],
)
def test_sheets_that_are_not_the_lock_s_are_refused(tmp_path, change):
    _refused(_out(tmp_path), lock_path=_lock_with(tmp_path, change))


def test_the_sheets_must_come_in_the_lock_s_order(tmp_path):
    out = _out(tmp_path)
    lock = _lock_with(tmp_path, lambda e: e["sheets"].update({"1249-41": e["sheets"]["1249-42"]}))
    sheets = json.loads(lock.read_bytes())["datasets"]["swissbuildings3d"]["sheets"]
    in_order = [{"sha256": sheets[s]["sha256"], "sheet": s} for s in ("1249-41", "1249-42")]
    _edit_description(out, lambda b: b["source"].update(sheets=in_order))
    written = json.loads(_write(out, lock_path=lock).read_bytes())
    assert written["buildings"]["source"]["sheets"] == in_order
    (out / "manifest.json").unlink()
    _edit_description(out, lambda b: b["source"]["sheets"].reverse())
    _refused(out, lock_path=lock)


def test_a_lock_without_buildings_is_refused(tmp_path):
    message = _refused(_out(tmp_path), lock_path=TERRAIN_FIXTURE_LOCK)
    assert "python -m mattini lock buildings" in message


@pytest.mark.parametrize("damage", ["changed", "missing", "short", "longer"])
def test_a_chunk_file_that_does_not_match_is_refused(tmp_path, damage):
    out = _out(tmp_path)
    chunk = out / "buildings" / "2650-1150.bin"
    data = chunk.read_bytes()
    if damage == "changed":
        chunk.write_bytes(data[:100] + bytes([data[100] ^ 1]) + data[101:])
    elif damage == "missing":
        chunk.unlink()
    elif damage == "short":
        chunk.write_bytes(data[:-12])
    else:
        chunk.write_bytes(data + bytes(12))
    message = _refused(out)
    assert "2650-1150.bin" in message


@pytest.mark.parametrize(
    "change",
    [
        lambda e: e.update({"2650-1150": "0" * 64}),
        lambda e: e.update({"2651-1149": "0" * 64}),
        lambda e: e.pop("2651-1150"),
    ],
    ids=["another-sha256", "a-tile-not-built", "a-tile-not-expected"],
)
def test_chunks_that_are_not_the_buildings_config_s_are_refused(tmp_path, change):
    config = _copy_with(
        tmp_path,
        FIXTURE / "buildings.json",
        lambda d: change(d["areas"]["fixture"]["expected_sha256"]),
    )
    _refused(_out(tmp_path), buildings_config_path=config)


def test_a_buildings_config_for_another_area_is_refused_once_built(tmp_path):
    message = _refused(_out(tmp_path), buildings_config_path=REPO / "config" / "buildings.json")
    assert "'village'" in message and "'fixture'" in message
