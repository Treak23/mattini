"""The manifest's `buildings` block (brief M2-04; docs/SPEC.md §8).

Pinned decisions (brief M2-04, *The manifest*): the top level is exactly `buildings`,
`schema`, `terrain`, `world`, `world_sha256` (since M3-13 also `photo`, `roofs`, `surfaces`
and `trees`, since v0.4.0-07 also `sky`, null here: none is built); `buildings` is null when the folder holds no
`buildings/<area>.json` for the terrain config's area, whatever the buildings config says,
and otherwise that description copied verbatim. `manifest` refuses a built block, naming
`python -m mattini buildings`, and writes nothing, when its key sets are not exact, its
`world_sha256` is not the world config's, its `source` is not the datasets config's
attribution, collection and edition and, in order, the sheets the lock pins with their
SHA-256s, a chunk file's size or SHA-256 differs from its entry, or the chunks are not the
buildings config's. The shared buildings fixture's generated files stand in for a build.
Since M2-07 also when its `lv95_box` is not the world config's box for the area, as floats
with exact keys (M2 R1 P-03); and a test that changes the world or the lock to reach these
checks records the change in the buildings config (`_adopted`), since a config computed
for another world or lock entry is refused first, naming design's step.

Since M3-01 (M2 V1-P-01, V1-P-07) a lock that does not fit the datasets config and pin
exactly the area's sheets is refused before any check of the block, naming
`python -m mattini lock buildings` (test_lock_fit.py pins the order against the step's);
so the cases that reach the source's and the sheets' checks change the block, or the area.

Does NOT prove: that the game reads the block (M2-05); that the real village's block is
accepted (the real run writes the manifest after the step, Findings).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from computed_for import recorded

from mattini.buildings import BuildingsError
from mattini.lock import write_lock
from mattini.manifest import write_manifest

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "buildings_fixture"
GENERATED = FIXTURE / "generated"
BUILDINGS_COMMAND = "python -m mattini buildings"
LOCK_COMMAND = "python -m mattini lock buildings"
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


def _refused(out, command=BUILDINGS_COMMAND, **changes) -> str:
    with pytest.raises(BuildingsError, match=command) as refusal:
        _write(out, **changes)
    assert not (out / "manifest.json").exists(), "a refusal must write nothing"
    return str(refusal.value)


def test_a_built_block_is_copied_verbatim(tmp_path):
    path = _write(_out(tmp_path))
    assert path.read_bytes() == (GENERATED / "manifest.json").read_bytes()
    manifest = json.loads(path.read_bytes())
    assert set(manifest) == {
        "buildings",
        "photo",
        "roofs",
        "schema",
        "sky",
        "surfaces",
        "terrain",
        "trees",
        "world",
        "world_sha256",
    }
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
    assert set(manifest) == {
        "buildings",
        "photo",
        "roofs",
        "schema",
        "sky",
        "surfaces",
        "terrain",
        "trees",
        "world",
        "world_sha256",
    }
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
        lambda b: b["source"].update(attribution="© someone"),
        lambda b: b["source"].update(collection="ch.other"),
        lambda b: b["source"].update(edition="2019"),
        lambda b: b["source"]["sheets"][0].update(sheet="1249-41"),
    ],
    ids=[
        "area",
        "format",
        "world",
        "order",
        "file",
        "tile",
        "size",
        "sha256",
        "dataset",
        "source-attribution",
        "source-collection",
        "source-edition",
        "source-sheet",
    ],
)
def test_a_description_that_does_not_match_is_refused(tmp_path, change):
    out = _out(tmp_path)
    _edit_description(out, change)
    _refused(out)


WORLD_BOX = json.loads((FIXTURE / "world.json").read_bytes())["areas"]["fixture"]


@pytest.mark.parametrize(
    ("key", "shift"),
    [("e", 1000.0), ("e", -1000.0), ("n", 1000.0), ("n", -1000.0)],
    ids=["east", "west", "north", "south"],
)
def test_a_box_shifted_by_a_kilometre_is_refused(tmp_path, key, shift):
    """M2 R1 P-03's case: the box moved 1 km, the chunks, world, source and lock all fine.

    Harm: a later consumer (chunk loading by distance) trusting a box the manifest let
    through 1 km off the world's area. The refusal names the field and both boxes.
    """
    out = _out(tmp_path)

    def move(block):
        for edge in (f"{key}_min", f"{key}_max"):
            block["lv95_box"][edge] += shift

    _edit_description(out, move)
    found = json.loads((out / "buildings" / "fixture.json").read_bytes())["lv95_box"]
    assert found != WORLD_BOX
    message = _refused(out)
    for part in ("lv95_box", repr(found), repr(dict(sorted(WORLD_BOX.items())))):
        assert part in message, (part, message)


@pytest.mark.parametrize(
    "change",
    [
        lambda box: box.update(e_max=box["e_max"] + 0.5),
        lambda box: box.update(n_min=box["n_min"] - 0.001),
        lambda box: box.update(e_min=int(box["e_min"])),
        lambda box: box.update(n_max=str(box["n_max"])),
        lambda box: box.pop("n_min"),
        lambda box: box.update(e_min=box.pop("e_max"), e_max=box["e_min"]),
    ],
    ids=["an-edge-moved", "a-millimetre", "a-whole-number", "a-string", "a-key-missing", "swapped"],
)
def test_a_box_that_is_not_exactly_the_world_s_is_refused(tmp_path, change):
    """The box as floats with exactly the four keys, as the buildings step writes it."""
    out = _out(tmp_path)
    _edit_description(out, lambda b: change(b["lv95_box"]))
    found = json.loads((out / "buildings" / "fixture.json").read_bytes())["lv95_box"]
    message = _refused(out)
    assert "lv95_box" in message and repr(found) in message, message


def test_the_fixture_s_box_is_the_world_s():
    """Positive control for the two tests above: the built block's box passes as it is."""
    block = json.loads((GENERATED / "buildings" / "fixture.json").read_bytes())
    assert block["lv95_box"] == WORLD_BOX
    assert all(type(value) is float for value in block["lv95_box"].values())


def _adopted(tmp_path, world: Path = FIXTURE / "world.json", lock: Path | None = None) -> Path:
    """The fixture's buildings config recording `world` and `lock` (design has adopted them).

    Since M2-07 the config's `computed_for` is compared with the world and the lock first;
    a test of the checks of the built block that follow records the world or lock it
    changes, so it reaches them.
    """
    config = json.loads((FIXTURE / "buildings.json").read_text(encoding="utf-8"))
    lock_data = json.loads((lock or FIXTURE / "datasets.lock.json").read_bytes())
    path = tmp_path / "adopted-buildings.json"
    path.write_text(
        json.dumps(recorded(config, world, lock_data, "swissbuildings3d")), encoding="utf-8"
    )
    return path


def test_buildings_built_for_another_world_are_refused(tmp_path):
    """Design has recomputed for the changed world: the old block is refused, naming the
    rebuild. Without design's step the refusal names design's (test_computed_for_buildings)."""
    world = _copy_with(tmp_path, FIXTURE / "world.json", lambda d: d.update(height_offset_m=0.0))
    message = _refused(
        _out(tmp_path), config_path=world, buildings_config_path=_adopted(tmp_path, world)
    )
    assert "built for the world config" in message


@pytest.mark.parametrize(
    ("key", "command"),
    [("attribution", BUILDINGS_COMMAND), ("collection", LOCK_COMMAND), ("edition", LOCK_COMMAND)],
)
def test_a_datasets_config_that_is_not_the_source_s_is_refused(tmp_path, key, command):
    """The datasets config changed under a built block. The attribution is checked against
    the block's source; the collection and the edition are the lock's to match first (M3-01),
    so the refusal names `lock buildings`. The block's own source values are edited in
    test_a_description_that_does_not_match_is_refused."""
    value = {"attribution": "© someone", "collection": "ch.other", "edition": "2019"}[key]
    datasets = _copy_with(
        tmp_path,
        FIXTURE / "datasets.json",
        lambda d: d["datasets"]["swissbuildings3d"].update({key: value}),
    )
    message = _refused(_out(tmp_path), command, datasets_path=datasets)
    assert key in message


def _lock_with(tmp_path, change) -> Path:
    data = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    change(data["datasets"]["swissbuildings3d"])
    return write_lock(data, tmp_path / "datasets.lock.json")


def test_a_sheet_whose_sha256_is_not_the_lock_s_is_refused(tmp_path):
    """The lock re-pinned a sheet and adopted by design, the buildings not rebuilt since."""
    lock = _lock_with(tmp_path, lambda e: e["sheets"]["1249-42"].update(sha256="ab" * 32))
    message = _refused(
        _out(tmp_path), lock_path=lock, buildings_config_path=_adopted(tmp_path, lock=lock)
    )
    assert "ab" * 32 in message


@pytest.mark.parametrize(
    "change",
    [
        lambda e: e["sheets"].update({"1249-41": e["sheets"]["1249-42"]}),
        lambda e: e.update(sheets={"1249-41": e["sheets"]["1249-42"]}),
        lambda e: e.update(edition="2019"),
    ],
    ids=["another-sheet", "other-sheet", "edition"],
)
def test_a_lock_that_does_not_fit_the_area_is_refused_naming_lock_buildings(tmp_path, change):
    """An extra sheet, another sheet or another edition, even where design adopted the lock:
    the fit is checked before the block (M3-01)."""
    data = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    change(data["datasets"]["swissbuildings3d"])
    lock = tmp_path / "datasets.lock.json"
    lock.write_text(json.dumps(data, indent=2), encoding="utf-8")  # as a hand edit leaves it
    _refused(_out(tmp_path), LOCK_COMMAND, lock_path=lock, buildings_config_path=_adopted(tmp_path))


def test_the_sheets_must_come_in_the_lock_s_order(tmp_path):
    """An area whose box reaches 1249-41 as well as 1249-42, so that the lock pins both."""
    out = _out(tmp_path)
    world = _copy_with(
        tmp_path,
        FIXTURE / "world.json",
        lambda d: d["areas"]["fixture"].update(e_min=2650500.0),
    )
    lock = _lock_with(tmp_path, lambda e: e["sheets"].update({"1249-41": e["sheets"]["1249-42"]}))
    config = _adopted(tmp_path, world, lock)
    sheets = json.loads(lock.read_bytes())["datasets"]["swissbuildings3d"]["sheets"]
    in_order = [{"sha256": sheets[s]["sha256"], "sheet": s} for s in ("1249-41", "1249-42")]

    def built_for_it(block):
        block["source"].update(sheets=in_order)
        block["lv95_box"].update(e_min=2650500.0)
        block.update(world_sha256=hashlib.sha256(world.read_bytes()).hexdigest())

    _edit_description(out, built_for_it)
    paths = {"config_path": world, "lock_path": lock, "buildings_config_path": config}
    written = json.loads(_write(out, **paths).read_bytes())
    assert written["buildings"]["source"]["sheets"] == in_order
    (out / "manifest.json").unlink()
    _edit_description(out, lambda b: b["source"]["sheets"].reverse())
    _refused(out, **paths)


def test_a_lock_without_buildings_is_refused(tmp_path):
    message = _refused(_out(tmp_path), LOCK_COMMAND, lock_path=TERRAIN_FIXTURE_LOCK)
    assert "has no 'swissbuildings3d' entry" in message


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
