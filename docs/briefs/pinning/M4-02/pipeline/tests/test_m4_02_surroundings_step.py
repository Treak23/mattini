"""Pinning tests for brief M4-02: the surroundings step, its checks in order, and its block.

Pinned decisions (m4-design §2; SPEC §8's order of checks, as the terrain and the surfaces):

`build_surroundings(world, datasets, lock, surroundings_config, raw_root, out_dir, *,
progress=None)` serves the one area of the surroundings config and reads `download regio`'s
layout (brief M4-01): <raw_root>/swissaltiregio/<edition>/provenance.json and the zips it
lists. Before it reads anything there: the area's corners and `margin_m` on the
`spacing_m` lattice (else refused naming the world config and the spacing), the area's
`computed_for` against the world config (a design change, lesson 41), the surroundings box,
columns and rows against design's `expected_lv95_box`, `expected_columns` and
`expected_rows`, then the lock's fit (its `swissaltiregio` entry: the datasets config's
collection, edition and resolution, exactly the tiles the surroundings need; refused naming
`python -m mattini lock regio` and no other command), then `computed_for` against the lock's
entry (lesson 41). A missing download is refused naming `python -m mattini download regio`
before anything is created under `out_dir` and before any `progress` call; so are a
provenance.json that is not the locked download and a file whose SHA-256 is not the lock's.
Each tile is read from the very bytes whose SHA-256 was checked: a zip of one member
`<E km>_<N km>.xyz`, the header `x y z`, every point a whole-metre position on the tile's
cell-centre lattice inside its square, at most once, with a finite height; anything else is
refused naming the tile and `download regio`. A vertex that keeps a height and has no sample
in its square is refused naming its row, column and position and `download regio`; one
strictly inside the area is NaN whatever its square holds. The heights' SHA-256 is compared
with `expected_sha256` before anything is written (lesson 38). The files,
`surroundings/<area>.f32` then `surroundings/<area>.json`, are each written through a `.part`
rename; a `*.part` left in `surroundings/` is removed after a success. The description is
exactly {area, columns, cut_box, file, format "f32-le", lv95_box, rows, sha256, source
{attribution, collection, dataset, edition, entry_sha256}, spacing_m, world_sha256}.

`built_surroundings_block(out_dir, surroundings_config, world, world_sha256, datasets, lock)`
(the manifest's check, wired by brief M4-09) gives None when nothing is built, else the block
once it is shown to hold, refusing anything else naming `python -m mattini surroundings`
(design's step for a changed world or entry); `lock` is a dict or the lock file's path.

The step checks the lock's fit in its own module: `lock.fit_problem` learns swissALTIRegio
in brief M4-01, in the same wave, and M4-09 moves the step onto it.

Does NOT prove: that the real village gives design's heights (the step's own comparison with
config/surroundings.json does, at the orchestrator's integration run); the CLI and the
manifest (brief M4-09); the game's reading (brief M4-07).
"""

import copy
import hashlib
import json
import os
import random
import shutil
import zipfile

import pytest
from computed_for import recorded
from synthetic_regio import (
    FIXTURE,
    fixture_datasets,
    fixture_source,
    points_of,
    raw_regio,
    with_lines,
    xyz_zip,
    zip_name,
)

from mattini.surroundings import (
    SurroundingsError,
    build_surroundings,
    built_surroundings_block,
    load_surroundings_config,
)
from mattini.world import load_world

GENERATED = FIXTURE / "generated" / "surroundings"
LOCK_COMMAND = "python -m mattini lock regio"
DOWNLOAD_COMMAND = "python -m mattini download regio"
STEP_COMMAND = "python -m mattini surroundings"
FOLDER = ("swissaltiregio", "2026-06")
BLOCK_KEYS = {
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


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _world():
    return load_world(FIXTURE / "world.json")


def _config():
    return load_surroundings_config(FIXTURE / "surroundings.json")


def _committed_lock():
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))


def _source_with(tile, transform):
    """The fixture's source with `tile`'s point lines replaced by transform(lines)."""
    source = fixture_source()
    text = source["tiles"][tile]["text"]
    lines = text.split("\r\n")[1:-1]
    source["tiles"][tile]["text"] = with_lines(text, transform(lines))
    return source


def _build(tmp_path, source=None, *, lock=None, config=None, progress=None, **raw):
    """Build from `source` laid out by `download regio`; the config recorded for its lock."""
    root, made = raw_regio(tmp_path / "raw", source, **raw)
    lock = made if lock is None else lock
    if config is None:
        config = recorded(_config(), _world(), made, "swissaltiregio")
    out = tmp_path / "out"
    block = build_surroundings(
        _world(), fixture_datasets(), lock, config, root, out, progress=progress
    )
    return block, out


def _refusal(tmp_path, source=None, **kwargs):
    with pytest.raises(SurroundingsError) as refusal:
        _build(tmp_path, source, **kwargs)
    assert not (tmp_path / "out").exists()
    return str(refusal.value)


# ------------------------------------------------------------------- what it writes


def test_the_step_writes_the_designed_files_exactly(tmp_path):
    block, out = _build(tmp_path)
    assert set(block) == BLOCK_KEYS
    folder = out / "surroundings"
    assert sorted(p.name for p in folder.iterdir()) == ["fixture.f32", "fixture.json"]
    for name in ("fixture.f32", "fixture.json"):
        assert (folder / name).read_bytes() == (GENERATED / name).read_bytes(), name
    assert json.loads((folder / "fixture.json").read_text(encoding="utf-8")) == block
    assert block["format"] == "f32-le" and block["file"] == "surroundings/fixture.f32"
    assert type(block["columns"]) is int and type(block["rows"]) is int
    assert type(block["spacing_m"]) is float


def test_a_second_build_writes_the_same_bytes(tmp_path):
    _, out = _build(tmp_path)
    first = {p.name: p.read_bytes() for p in (out / "surroundings").iterdir()}
    shutil.rmtree(tmp_path / "raw")
    _, out = _build(tmp_path)
    assert {p.name: p.read_bytes() for p in (out / "surroundings").iterdir()} == first


def test_the_live_deflated_zips_give_the_same_heights(tmp_path):
    block, out = _build(tmp_path, deflated=True)
    data = (out / "surroundings" / "fixture.f32").read_bytes()
    assert data == (GENERATED / "fixture.f32").read_bytes()
    assert (
        block["source"]["entry_sha256"]
        != json.loads((GENERATED / "fixture.json").read_text(encoding="utf-8"))["source"][
            "entry_sha256"
        ]
    )


def test_the_order_of_a_tile_s_lines_does_not_matter(tmp_path):
    source = _source_with("2615-1094", lambda lines: random.Random(7).sample(lines, len(lines)))
    _, out = _build(tmp_path, source)
    data = (out / "surroundings" / "fixture.f32").read_bytes()
    assert data == (GENERATED / "fixture.f32").read_bytes()


def test_each_file_goes_through_a_part_rename_and_old_parts_go(tmp_path, monkeypatch):
    stale = tmp_path / "out" / "surroundings" / "older.f32.part"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"a run cut short")
    renames = []
    real = os.replace

    def replace(src, dst):
        renames.append((os.fspath(src), os.fspath(dst)))
        real(src, dst)

    monkeypatch.setattr(os, "replace", replace)
    root, lock = raw_regio(tmp_path / "raw")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    folder = tmp_path / "out" / "surroundings"
    assert renames == [
        (str(folder / "fixture.f32.part"), str(folder / "fixture.f32")),
        (str(folder / "fixture.json.part"), str(folder / "fixture.json")),
    ]
    assert sorted(p.name for p in folder.iterdir()) == ["fixture.f32", "fixture.json"]


# ------------------------------------------------------------------- the checks, in order


def test_another_world_is_refused_before_anything_else(tmp_path):
    config = recorded(_config(), b'{"another": "world"}\n', _committed_lock(), "swissaltiregio")
    lock = {"schema": 1, "datasets": {}}  # it would be refused next: the world comes first
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "config/world.json" in text, text
    assert "design" in text and DOWNLOAD_COMMAND not in text and LOCK_COMMAND not in text
    assert not (tmp_path / "out").exists()


def test_an_area_off_the_spacing_lattice_is_refused_naming_the_world(tmp_path):
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["areas"]["fixture"]["e_min"] = 2_616_500.0
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    world = load_world(path)
    config = recorded(_config(), world, _committed_lock(), "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            world, fixture_datasets(), _committed_lock(), config, tmp_path, tmp_path / "out"
        )
    text = str(refusal.value)
    assert str(path) in text and "fixture" in text and "3000" in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("expected_columns", 7),
        ("expected_rows", 6),
        (
            "expected_lv95_box",
            {"e_max": 2628000.0, "e_min": 2613000.0, "n_max": 1110000.0, "n_min": 1089000.0},
        ),
    ],
)
def test_a_box_that_is_not_design_s_is_refused_before_the_lock(tmp_path, key, value):
    config = _config()
    config["areas"]["fixture"][key] = value
    lock = {"schema": 1, "datasets": {}}
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert key in text and "config/surroundings.json" in text and LOCK_COMMAND not in text, text


@pytest.mark.parametrize(
    "case", ["no-entry", "a-tile-missing", "a-tile-too-many", "edition", "resolution", "collection"]
)
def test_a_lock_that_does_not_fit_is_refused_naming_lock_regio(tmp_path, case):
    lock = _committed_lock()
    entry = lock["datasets"]["swissaltiregio"]
    if case == "no-entry":
        lock["datasets"] = {"swisstlm3d": {"anything": "else"}}
    elif case == "a-tile-missing":
        del entry["tiles"]["2625-1104"]
    elif case == "a-tile-too-many":
        entry["tiles"]["2635-1104"] = {"file": zip_name("2635-1104"), "sha256": "0" * 64}
    elif case == "edition":
        entry["edition"] = "2025-06"
    elif case == "resolution":
        entry["resolution_m"] = 10
    else:
        entry["collection"] = "ch.swisstopo.swissalti3d"
    config = recorded(_config(), _world(), _committed_lock(), "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert f"`{LOCK_COMMAND}`" in text, text
    assert "download" not in text and "design recomputes" not in text, text
    assert not (tmp_path / "out").exists()


def test_a_box_edge_on_a_tile_edge_needs_the_tile_beyond_it(tmp_path):
    """The area's east edge moved to E 2'622'000: the box ends at 2'625'000, a tile edge.

    The vertices there take samples up to E 2'626'500 (half a spacing east), so the tiles
    of column 2625 are still needed: the fixture's lock, which pins them, fits, and the step
    goes on to the heights (refused there, as the config keeps the fixture's value).
    """
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["areas"]["fixture"]["e_max"] = 2_622_000.0
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    world = load_world(path)
    root, lock = raw_regio(tmp_path / "raw")
    config = recorded(_config(), world, lock, "swissaltiregio")
    settings = config["areas"]["fixture"]
    settings["expected_columns"] = 5
    settings["expected_lv95_box"] = {**settings["expected_lv95_box"], "e_max": 2625000.0}
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(world, fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert "nothing was written" in text and LOCK_COMMAND not in text, text
    assert not (tmp_path / "out").exists()


def test_other_inputs_are_refused_before_the_download_is_read(tmp_path):
    lock = _committed_lock()
    other = copy.deepcopy(lock)
    other["datasets"]["swissaltiregio"]["tiles"]["2615-1094"]["sha256"] = "1" * 64
    config = recorded(_config(), _world(), other, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "lock" in text and "design" in text, text
    assert DOWNLOAD_COMMAND not in text
    assert not (tmp_path / "out").exists()


def test_a_missing_download_is_refused_before_any_progress_or_folder(tmp_path):
    lines = []
    config = recorded(_config(), _world(), _committed_lock(), "swissaltiregio")
    with pytest.raises(SurroundingsError, match=DOWNLOAD_COMMAND):
        build_surroundings(
            _world(),
            fixture_datasets(),
            _committed_lock(),
            config,
            tmp_path / "raw",
            tmp_path / "out",
            progress=lines.append,
        )
    assert lines == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "case",
    [
        "provenance-of-other-bytes",
        "a-file-of-other-bytes",
        "a-file-missing",
        "provenance-tiles-differ",
        "provenance-edition",
    ],
)
def test_a_download_that_is_not_the_locked_one_is_refused(tmp_path, case):
    root, lock = raw_regio(tmp_path / "raw")
    folder = root.joinpath(*FOLDER)
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    name = zip_name("2615-1094")
    if case == "provenance-of-other-bytes":
        provenance["tiles"][4]["sha256"] = "e" * 64
    elif case == "a-file-of-other-bytes":
        (folder / name).write_bytes(xyz_zip("2615_1094.xyz", "x y z\r\n"))
    elif case == "a-file-missing":
        (folder / name).unlink()
    elif case == "provenance-tiles-differ":
        provenance["tiles"] = provenance["tiles"][:-1]
    else:
        provenance["edition"] = "2025-06"
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    assert DOWNLOAD_COMMAND in str(refusal.value), str(refusal.value)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "case",
    [
        "off-the-lattice",
        "outside-the-tile",
        "twice",
        "not-whole-metres",
        "nan",
        "inf",
        "not-a-number",
        "header",
        "member-name",
        "two-members",
    ],
)
def test_a_tile_that_is_not_what_its_id_says_is_refused_naming_it(tmp_path, case):
    tile = "2615-1094"
    source = fixture_source()
    text = source["tiles"][tile]["text"]
    lines = text.split("\r\n")[1:-1]
    first = lines[0].split(" ")
    if case == "off-the-lattice":
        lines[0] = f"{int(first[0]) + 100} {first[1]} {first[2]}"
    elif case == "outside-the-tile":
        lines[0] = f"{int(first[0]) - 1000} {first[1]} {first[2]}"
    elif case == "twice":
        lines.append(lines[0])
    elif case == "not-whole-metres":
        lines[0] = f"{first[0]}.0 {first[1]} {first[2]}"
    elif case in ("nan", "inf"):
        lines[0] = f"{first[0]} {first[1]} {case}"
    elif case == "not-a-number":
        lines[0] = f"{first[0]} {first[1]} 12.3.4"
    if case == "header":
        source["tiles"][tile]["text"] = "X Y Z" + text[len("x y z") :]
    elif case == "member-name":
        source["tiles"][tile]["member"] = "2615_1094.txt"
    else:
        source["tiles"][tile]["text"] = with_lines(text, lines)
    if case == "two-members":
        root, lock = raw_regio(tmp_path / "raw", source)
        folder = root.joinpath(*FOLDER)
        with zipfile.ZipFile(folder / zip_name(tile), "a") as archive:
            archive.writestr("readme.txt", "another member")
        data = (folder / zip_name(tile)).read_bytes()
        lock["datasets"]["swissaltiregio"]["tiles"][tile]["sha256"] = _sha(data)
        provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
        for entry in provenance["tiles"]:
            if entry["tile"] == tile:
                entry["sha256"], entry["size_bytes"] = _sha(data), len(data)
        (folder / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
        config = recorded(_config(), _world(), lock, "swissaltiregio")
        with pytest.raises(SurroundingsError) as refusal:
            build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
        text = str(refusal.value)
    else:
        text = _refusal(tmp_path, source)
    assert tile in text and DOWNLOAD_COMMAND in text, text
    assert not (tmp_path / "out").exists()


def test_a_vertex_that_keeps_a_height_without_a_sample_is_refused_naming_it(tmp_path):
    """Vertex (row 0, column 0) at (2613000, 1110000): its nine samples are all in 2605-1104."""
    square = {(x, y) for x in (2611500, 2612500, 2613500) for y in (1108500, 1109500, 1110500)}
    source = _source_with(
        "2605-1104",
        lambda lines: [ln for ln in lines if tuple(map(int, ln.split(" ")[:2])) not in square],
    )
    text = _refusal(tmp_path, source)
    for part in ("row 0", "column 0", "2613000", "1110000", DOWNLOAD_COMMAND):
        assert part in text, text


def test_a_hole_under_a_cut_vertex_changes_nothing(tmp_path):
    """Vertex (row 2, column 2) at (2619000, 1104000) lies strictly inside the area: NaN."""
    xs, ys = (2617500, 2618500, 2619500), (1102500, 1103500, 1104500)
    source = fixture_source()
    for tile in ("2615-1094", "2615-1104"):
        text = source["tiles"][tile]["text"]
        kept = [f"{x} {y} {z}" for x, y, z in points_of(text) if not (x in xs and y in ys)]
        source["tiles"][tile]["text"] = with_lines(text, kept)
    _, out = _build(tmp_path, source)
    data = (out / "surroundings" / "fixture.f32").read_bytes()
    assert data == (GENERATED / "fixture.f32").read_bytes()


def test_other_heights_are_refused_before_anything_is_written(tmp_path):
    config = _config()
    other = "ab" * 32
    config["areas"]["fixture"]["expected_sha256"] = other
    _, lock = raw_regio(tmp_path / "make")
    config = recorded(config, _world(), lock, "swissaltiregio")
    text = _refusal(tmp_path, config=config)
    expected = json.loads((GENERATED / "fixture.json").read_text(encoding="utf-8"))["sha256"]
    assert other in text and expected in text and "nothing was written" in text, text


def test_a_refused_build_leaves_the_old_files_as_they_were(tmp_path):
    _, out = _build(tmp_path)
    folder = out / "surroundings"
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    config = _config()
    config["areas"]["fixture"]["expected_sha256"] = "cd" * 32
    lock = _committed_lock()
    with pytest.raises(SurroundingsError):
        build_surroundings(
            _world(),
            fixture_datasets(),
            lock,
            recorded(config, _world(), lock, "swissaltiregio"),
            tmp_path / "raw",
            out,
        )
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


# ------------------------------------------------------------------- the built block


def _built(tmp_path):
    _, out = _build(tmp_path)
    world = _world()
    world_sha256 = _sha((FIXTURE / "world.json").read_bytes())
    lock = _committed_lock()
    return out, world, world_sha256, lock


def test_nothing_built_is_none(tmp_path):
    world_sha256 = _sha((FIXTURE / "world.json").read_bytes())
    assert (
        built_surroundings_block(
            tmp_path, _config(), _world(), world_sha256, fixture_datasets(), _committed_lock()
        )
        is None
    )


def test_the_built_block_is_the_description(tmp_path):
    out, world, world_sha256, lock = _built(tmp_path)
    description = json.loads((out / "surroundings" / "fixture.json").read_text(encoding="utf-8"))
    for given in (lock, FIXTURE / "datasets.lock.json", str(FIXTURE / "datasets.lock.json")):
        block = built_surroundings_block(
            out, _config(), world, world_sha256, fixture_datasets(), given
        )
        assert block == description


@pytest.mark.parametrize(
    "case", ["heights", "size", "sha256", "cut_box", "spacing", "source", "world", "keys"]
)
def test_a_built_block_that_no_longer_holds_is_refused_naming_the_step(tmp_path, case):
    out, world, world_sha256, lock = _built(tmp_path)
    folder = out / "surroundings"
    heights = folder / "fixture.f32"
    path = folder / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    if case == "heights":
        data = bytearray(heights.read_bytes())
        data[0] ^= 1
        heights.write_bytes(bytes(data))
    elif case == "size":
        heights.write_bytes(heights.read_bytes() + b"\0\0\0\0")
    elif case == "sha256":
        block["sha256"] = "0" * 64
    elif case == "cut_box":
        block["cut_box"]["e_min"] = 2613000.0
    elif case == "spacing":
        block["spacing_m"] = 1000.0
    elif case == "source":
        block["source"]["entry_sha256"] = "0" * 64
    elif case == "world":
        block["world_sha256"] = "0" * 64
    else:
        block["extra"] = 1
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), world, world_sha256, fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value), str(refusal.value)


def test_a_built_block_for_another_world_or_entry_names_design(tmp_path):
    out, world, world_sha256, lock = _built(tmp_path)
    config = recorded(_config(), b'{"another": "world"}\n', lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, config, world, world_sha256, fixture_datasets(), lock)
    assert "design" in str(refusal.value) and STEP_COMMAND not in str(refusal.value)
    other = copy.deepcopy(lock)
    other["datasets"]["swissaltiregio"]["tiles"]["2615-1094"]["sha256"] = "1" * 64
    config = recorded(_config(), world, other, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, config, world, world_sha256, fixture_datasets(), lock)
    assert "design" in str(refusal.value) and STEP_COMMAND not in str(refusal.value)
