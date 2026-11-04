"""Gap tests for brief v0.6.0-04: what the 103 pinned tests leave open (lesson 51).

The pin author's probes on the rehearsal's throwaway left the pins green with three removals: the
owner's-axes refusal, provenance.json's `dataset` key and the member's final CRLF. This file pins
those three, and the other places where the pinned tests check a refusal in part: the line a bad
sample is on, the keys of provenance.json and of the datasets config, a tile that is not a zip,
the built block's fields one by one, the lock's fit and the lock file in `built_surroundings_block`,
and the progress lines. The pinned files stay untouched; the words of a refusal are pinned only
where a reader needs them (the tile, the line, the command).

The second half of this file (from "the fixer's round") answers the prover's findings at the
batch gate. Each test there fails on a named change to the module (the brief's Findings table
lists the changes and the counts): the rule's arithmetic (one division, the offset in 64 bits),
the vertex-level sums and counts, the tile range on every side, the per-tile pins of the lock,
the shape of every config, the order of the bytes' check and the read, the way a zip can fail,
the words that name a missing vertex, the scope of the `.part` cleanup, the progress lines.

Does NOT prove: that the real tiles read as these synthetic ones do (the step's own comparison
with design's SHA-256 does, at v0.6.0-07's real run); the command line and the manifest (brief
v0.6.0-07); the game's reading (brief v0.6.0-08); that two divisions, or a float sum, differ
from the rule on any real data (they cannot: at nine or 25 samples a square and an offset
that is a whole number of centimetres the exact mean lies at least 5e-8 m from a float32
rounding midpoint; the vectors of `test_the_rule_is_one_division_...` are constructed
numbers, not data).
"""

import copy
import hashlib
import json
import shutil
import struct
import zipfile
from fractions import Fraction

import numpy as np
import pytest
from computed_for import recorded
from synthetic_regio import (
    FIXTURE,
    REPO,
    fixture_datasets,
    fixture_source,
    raw_regio,
    xyz_zip,
    zip_name,
)

from mattini import download, surroundings
from mattini.surroundings import (
    SurroundingsError,
    build_surroundings,
    built_surroundings_block,
    check_surroundings_config,
    load_surroundings_config,
)
from mattini.world import load_world

LOCK_COMMAND = "python -m mattini lock regio"
DOWNLOAD_COMMAND = "python -m mattini download regio"
STEP_COMMAND = "python -m mattini surroundings"
FOLDER = ("swissaltiregio", "2026-06")
TILE = "2615-1094"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _world(path=None):
    return load_world(path or FIXTURE / "world.json")


def _config():
    return load_surroundings_config(FIXTURE / "surroundings.json")


def _committed_lock():
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))


def _text_of(source, tile=TILE):
    return source["tiles"][tile]["text"]


def _lines_of(source, tile=TILE):
    return _text_of(source, tile).split("\r\n")[1:-1]


def _with_lines(source, lines, tile=TILE):
    source["tiles"][tile]["text"] = "\r\n".join(["x y z", *lines]) + "\r\n"
    return source


def _build(tmp_path, source=None, *, world=None, progress=None):
    """Build the fixture (or `source`) from `download regio`'s layout, recorded for its lock."""
    root, lock = raw_regio(tmp_path / "raw", source)
    world = world or _world()
    config = recorded(_config(), world, lock, "swissaltiregio")
    out = tmp_path / "out"
    block = build_surroundings(
        world, fixture_datasets(), lock, config, root, out, progress=progress
    )
    return block, out


def _refusal(tmp_path, source=None, **kwargs) -> str:
    with pytest.raises(SurroundingsError) as refusal:
        _build(tmp_path, source, **kwargs)
    assert not (tmp_path / "out").exists()
    return str(refusal.value)


def _rotated_world(tmp_path):
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["axes"] = {"x": "+n", "y": "+h", "z": "+e"}  # a proper rotation, not the owner's
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# ------------------------------------------------------------------- the config's values


@pytest.mark.parametrize(
    "change",
    [
        lambda d, a: a["expected_lv95_box"].update(e_max=float("nan")),
        lambda d, a: a["expected_lv95_box"].update(e_max=float("inf")),
        lambda d, a: a["expected_lv95_box"].update(n_min=-float("inf")),
        lambda d, a: a["expected_lv95_box"].update(e_max=10**400),  # no float holds it
        lambda d, a: a["expected_lv95_box"].update(e_min=True),
        lambda d, a: a["expected_lv95_box"].update(extra=2628000.0),
        lambda d, a: a.update(expected_columns=True),
        lambda d, a: a.update(expected_rows=True),
        lambda d, a: a.update(expected_rows=-7),
        lambda d, a: a.update(expected_sha256=None),
        lambda d, a: a.update(expected_sha256="ab" * 31),
        lambda d, a: a.update(computed_for=[]),
        lambda d, a: d.update(areas={"Not A Name": a}),
        lambda d, a: d.update(areas=[a]),
        lambda d, a: d.pop("schema"),
    ],
)
def test_a_config_value_that_is_not_design_s_kind_is_refused_naming_the_config(change):
    data = copy.deepcopy(_config())
    change(data, data["areas"]["fixture"])
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(data, "the config here")
    assert "the config here" in str(refusal.value), str(refusal.value)


# ------------------------------------------------------------------- the owner's axes


def test_other_axes_than_the_owner_s_are_refused_naming_the_world(tmp_path):
    path = _rotated_world(tmp_path)
    text = _refusal(tmp_path, world=_world(path))
    assert str(path) in text and "axes" in text, text


def test_a_built_block_for_other_axes_is_refused(tmp_path):
    _, out = _build(tmp_path)
    path = _rotated_world(tmp_path)
    lock = _committed_lock()
    config = recorded(_config(), path, lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(
            out, config, _world(path), _sha(path.read_bytes()), fixture_datasets(), lock
        )
    assert str(path) in str(refusal.value) and "axes" in str(refusal.value), str(refusal.value)


# ------------------------------------------------------------------- provenance.json


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("dataset", "swissalti3d"),
        ("collection", "ch.swisstopo.swissalti3d"),
        ("resolution_m", 10),
        ("tiles", "none"),
    ],
)
def test_a_provenance_of_another_dataset_collection_or_resolution_is_refused(tmp_path, key, value):
    root, lock = raw_regio(tmp_path / "raw")
    path = root.joinpath(*FOLDER, "provenance.json")
    provenance = json.loads(path.read_text(encoding="utf-8"))
    provenance[key] = value
    path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    assert DOWNLOAD_COMMAND in str(refusal.value), str(refusal.value)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("case", ["not-json", "not-an-object", "file-with-a-path"])
def test_a_provenance_that_cannot_be_read_is_refused(tmp_path, case):
    root, lock = raw_regio(tmp_path / "raw")
    path = root.joinpath(*FOLDER, "provenance.json")
    if case == "not-json":
        path.write_text("{", encoding="utf-8")
    elif case == "not-an-object":
        path.write_text("[]", encoding="utf-8")
    else:
        provenance = json.loads(path.read_text(encoding="utf-8"))
        provenance["tiles"][0]["file"] = "../" + provenance["tiles"][0]["file"]
        path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    assert DOWNLOAD_COMMAND in str(refusal.value), str(refusal.value)
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- the datasets config


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.clear(),
        lambda d: d["swissaltiregio"].update(resolution_m=3000),  # does not divide the 10 km tile
        lambda d: d["swissaltiregio"].update(resolution_m=1000.0),
        lambda d: d["swissaltiregio"].update(resolution_m=0),
        lambda d: d["swissaltiregio"].pop("attribution"),
        lambda d: d["swissaltiregio"].update(edition=["2026-06"]),
    ],
)
def test_a_datasets_config_the_step_cannot_use_is_refused_naming_it(tmp_path, change):
    datasets = fixture_datasets()
    change(datasets)
    lock = _committed_lock()
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), datasets, lock, config, tmp_path / "raw", tmp_path / "out")
    assert "config/datasets.json" in str(refusal.value), str(refusal.value)
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- a tile's bytes and lines


def _laid_out(tmp_path, source, zip_bytes):
    """`download regio`'s layout for `source`, with tile TILE's file replaced by `zip_bytes`."""
    root, lock = raw_regio(tmp_path / "raw", source)
    folder = root.joinpath(*FOLDER)
    (folder / zip_name(TILE)).write_bytes(zip_bytes)
    lock["datasets"]["swissaltiregio"]["tiles"][TILE]["sha256"] = _sha(zip_bytes)
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    for entry in provenance["tiles"]:
        if entry["tile"] == TILE:
            entry["sha256"], entry["size_bytes"] = _sha(zip_bytes), len(zip_bytes)
    (folder / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    return root, lock


def test_a_file_that_is_not_a_zip_is_refused_naming_the_tile(tmp_path):
    root, lock = _laid_out(tmp_path, fixture_source(), b"this is not a zip file")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert TILE in text and DOWNLOAD_COMMAND in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "case", ["no-final-line-end", "lf-line-ends", "an-empty-member", "no-header-line-end"]
)
def test_a_member_that_is_not_swisstopo_s_text_is_refused_naming_the_tile(tmp_path, case):
    source = fixture_source()
    text = _text_of(source)
    assert text.endswith("\r\n")
    source["tiles"][TILE]["text"] = {
        "no-final-line-end": text[:-2],  # the last line lacks its CR LF
        "lf-line-ends": text.replace("\r\n", "\n"),
        "an-empty-member": "",
        "no-header-line-end": text.replace("x y z\r\n", "x y z", 1),
    }[case]
    message = _refusal(tmp_path, source)
    assert TILE in message and DOWNLOAD_COMMAND in message, message


@pytest.mark.parametrize(
    ("dx", "dy"),
    [
        (100, 0),  # off the lattice to the east, still in its own cell
        (0, 100),  # off the lattice to the north, still in its own cell
        (10_000, 0),  # on the lattice, one cell beyond the tile's east edge
        (-1_000, 0),  # on the lattice, one cell beyond its west edge
        (0, 1_000),  # on the lattice, exactly one cell beyond its north edge
        (0, 10_000),  # beyond its north edge
        (0, -10_000),  # beyond its south edge
    ],
)
def test_a_point_off_the_cell_centres_is_refused_naming_its_line(tmp_path, dx, dy):
    """The first sample is the tile's north-west cell: the 100 samples are lines 2 to 101."""
    lines = _lines_of(fixture_source())
    x, y, z = lines[0].split(" ")
    source = _with_lines(fixture_source(), [f"{int(x) + dx} {int(y) + dy} {z}", *lines[1:]])
    message = _refusal(tmp_path, source)
    assert "line 2:" in message and TILE in message and DOWNLOAD_COMMAND in message, message


def test_a_point_given_twice_is_refused_naming_the_repeat(tmp_path):
    lines = _lines_of(fixture_source())
    source = _with_lines(fixture_source(), [*lines, lines[3]])
    message = _refusal(tmp_path, source)
    # the header is line 1, the 100 samples lines 2 to 101: the repeat is line 102
    assert "line 102:" in message and "more than once" in message, message


def test_a_world_config_changed_after_it_was_parsed_is_refused(tmp_path):
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    world = _world(path)
    data["origin_lv95"]["e"] += 1.0
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    root, lock = raw_regio(tmp_path / "raw")
    config = recorded(_config(), path, lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(world, fixture_datasets(), lock, config, root, tmp_path / "out")
    assert str(path) in str(refusal.value) and "changed while" in str(refusal.value)
    assert not (tmp_path / "out").exists()


def _world_without_the_area(tmp_path):
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["areas"] = {"another": data["areas"]["fixture"]}
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def test_an_area_the_world_does_not_have_is_refused_naming_both(tmp_path):
    path = _world_without_the_area(tmp_path)
    text = _refusal(tmp_path, world=_world(path))
    assert str(path) in text and "fixture" in text, text


def test_a_built_block_for_a_world_without_the_area_is_refused(tmp_path):
    _, out = _build(tmp_path)
    path = _world_without_the_area(tmp_path)
    lock = _committed_lock()
    config = recorded(_config(), path, lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(
            out, config, _world(path), _sha(path.read_bytes()), fixture_datasets(), lock
        )
    assert "fixture" in str(refusal.value) and STEP_COMMAND in str(refusal.value)


@pytest.mark.parametrize(
    "line",
    [
        "{x} {y}",  # two fields
        "{x} {y} {z} {z}",  # four fields
        "{x}  {y} {z}",  # two spaces
        "{x}\t{y} {z}",  # a tab
        "{x} {y} {z} ",  # a space at the end
        " {x} {y} {z}",  # a space at the start
        "{x} {y} 12345678901",  # a height of more digits than any height
        "12345678901234567890 {y} {z}",  # a position that would not fit 64 bits
        "{x} 12345678901234567890 {z}",
        "-{x} {y} {z}",  # a signed position
    ],
)
def test_a_line_that_is_not_three_fields_is_refused_naming_its_line(tmp_path, line):
    lines = _lines_of(fixture_source())
    x, y, z = lines[4].split(" ")
    lines[4] = line.format(x=x, y=y, z=z)
    message = _refusal(tmp_path, _with_lines(fixture_source(), lines))
    for part in (TILE, "line 6", DOWNLOAD_COMMAND):
        assert part in message, message


# ------------------------------------------------------------------- the built block's fields


def _built(tmp_path):
    _, out = _build(tmp_path)
    lock = _committed_lock()
    world_sha256 = _sha((FIXTURE / "world.json").read_bytes())
    return out, lock, world_sha256


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b.update(area="another"),
        lambda b: b.update(file="surroundings/another.f32"),
        lambda b: b.update(format="float32-le"),
        lambda b: b.update(columns=7),
        lambda b: b.update(columns=6.0),
        lambda b: b.update(rows=6),
        lambda b: b.update(rows=7.0),
        lambda b: b.update(spacing_m=3000),  # the step writes a float
        lambda b: b["lv95_box"].update(n_min=1089000.0),
        lambda b: b["lv95_box"].update(e_max=2628000),  # the step writes floats
        lambda b: b["cut_box"].pop("n_min"),
        lambda b: b["source"].update(attribution="© swisstopo"),
        lambda b: b["source"].update(collection="ch.swisstopo.swissalti3d"),
        lambda b: b["source"].update(edition="2025-06"),
        lambda b: b["source"].update(dataset="swissalti3d"),
        lambda b: b["source"].pop("edition"),
        lambda b: b.update(source="synthetic"),
    ],
)
def test_a_built_block_with_another_field_is_refused_naming_the_step(tmp_path, change):
    out, lock, world_sha256 = _built(tmp_path)
    path = out / "surroundings" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    change(block)
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value), str(refusal.value)


@pytest.mark.parametrize("case", ["not-json", "not-an-object", "gone"])
def test_a_built_description_that_cannot_be_read_is_refused_naming_the_step(tmp_path, case):
    out, lock, world_sha256 = _built(tmp_path)
    folder = out / "surroundings"
    if case == "not-json":
        (folder / "fixture.json").write_text("{", encoding="utf-8")
    elif case == "not-an-object":
        (folder / "fixture.json").write_text("[]", encoding="utf-8")
    else:
        (folder / "fixture.f32").unlink()
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value), str(refusal.value)


def test_a_built_heights_file_of_another_size_is_refused_naming_its_size(tmp_path):
    out, lock, world_sha256 = _built(tmp_path)
    heights = out / "surroundings" / "fixture.f32"
    heights.write_bytes(heights.read_bytes() + b"\0\0\0\0")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), lock)
    text = str(refusal.value)
    assert STEP_COMMAND in text and f"holds {6 * 7 * 4 + 4} bytes" in text, text


def test_a_built_heights_file_that_is_not_the_configs_expected_value_is_refused(tmp_path):
    out, lock, world_sha256 = _built(tmp_path)
    config = _config()
    config["areas"]["fixture"]["expected_sha256"] = "ab" * 32
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, config, _world(), world_sha256, fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value) and "ab" * 32 in str(refusal.value)


def test_a_built_block_with_a_lock_that_does_not_fit_names_lock_regio(tmp_path):
    out, lock, world_sha256 = _built(tmp_path)
    del lock["datasets"]["swissaltiregio"]["tiles"]["2625-1104"]
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), lock)
    text = str(refusal.value)
    assert f"`{LOCK_COMMAND}`" in text and STEP_COMMAND not in text, text


def test_a_built_block_with_a_box_that_is_not_designs_names_design(tmp_path):
    out, lock, world_sha256 = _built(tmp_path)
    config = _config()
    config["areas"]["fixture"]["expected_columns"] = 7
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, config, _world(), world_sha256, fixture_datasets(), lock)
    text = str(refusal.value)
    assert "expected_columns" in text and "design" in text and STEP_COMMAND not in text, text


def test_a_lock_file_that_cannot_be_read_is_refused_naming_it(tmp_path):
    out, _, world_sha256 = _built(tmp_path)
    for text in (None, "{"):
        path = tmp_path / "datasets.lock.json"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        with pytest.raises(SurroundingsError) as refusal:
            built_surroundings_block(
                out, _config(), _world(), world_sha256, fixture_datasets(), path
            )
        assert str(path) in str(refusal.value), str(refusal.value)


# ------------------------------------------------------------------- progress


def test_progress_names_every_tile_in_order_and_the_files_written(tmp_path):
    lines = []
    block, out = _build(tmp_path, progress=lines.append)
    reading = [line for line in lines if line.startswith("reading ")]
    tiles = sorted(fixture_source()["tiles"])
    assert [line.rsplit("/", 1)[-1] for line in reading] == [zip_name(tile) for tile in tiles]
    assert lines.index(reading[-1]) < len(lines) - 1
    assert str(out / block["file"]) in lines[-1] and lines[-1].startswith("wrote ")


# ===================================================================== the fixer's round
# What the prover found open after the tests above: one test per pattern, each over the whole
# class (every conjunct of a shape, every border of a range, every exception a zip can raise).

NAN = bytes.fromhex("0000c07f")  # the quiet NaN of the cut, little-endian
FIXTURE_SHA = _config()["areas"]["fixture"]["expected_sha256"]
VECTORS_FILE = REPO / "tests" / "shared" / "surroundings_vectors.json"


def _vectors() -> dict:
    return json.loads(VECTORS_FILE.read_text(encoding="utf-8"))


# ------------------------------------------------------------------- the shapes of the config


@pytest.mark.parametrize(
    "top",
    [None, [], ["areas", "schema"], "areas", 7],
    ids=["none", "empty-list", "list-of-the-keys", "text", "number"],
)
def test_a_top_level_that_is_not_an_object_is_refused_naming_the_config(top):
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(top, "the config here")
    assert "the config here" in str(refusal.value), str(refusal.value)


@pytest.mark.parametrize(
    "name",
    ["Fixture", "1fixture", "fixture-2", "fixture x", "fixture/x", "../fixture", "fixture\n", ""],
    ids=repr,
)
def test_an_area_name_must_match_whole_since_it_names_the_files(name):
    data = copy.deepcopy(_config())
    data["areas"] = {name: data["areas"]["fixture"]}
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(data, "the config here")
    assert "the config here" in str(refusal.value), str(refusal.value)


@pytest.mark.parametrize(
    "value",
    [
        FIXTURE_SHA + "0",
        "0" + FIXTURE_SHA,
        FIXTURE_SHA + "\n",
        FIXTURE_SHA.upper(),
        "g" * 64,
        FIXTURE_SHA[:31] + " " + FIXTURE_SHA[32:],
        7,
    ],
    ids=["65-digits", "leading-junk", "trailing-newline", "upper-case", "not-hex", "a-space", "7"],
)
def test_the_expected_sha256_must_be_exactly_64_lower_case_hex(value):
    data = copy.deepcopy(_config())
    data["areas"]["fixture"]["expected_sha256"] = value
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(data, "the config here")
    assert "the config here" in str(refusal.value) and "expected_sha256" in str(refusal.value)


@pytest.mark.parametrize(
    "change",
    [
        lambda d, a: d["areas"].update(fixture=sorted(a)),
        lambda d, a: a.update(expected_lv95_box=sorted(a["expected_lv95_box"])),
        lambda d, a: d.update(areas=[a, a]),
        lambda d, a: d.update(areas=7),
    ],
    ids=["the-area", "the-box", "areas-two-in-a-list", "areas-a-number"],
)
def test_an_object_of_the_wrong_type_is_refused_naming_the_config(change):
    """A list of the right keys has the right `set()`: only its type refuses it. And a refusal
    that names what it found must not fail while building its words."""
    data = copy.deepcopy(_config())
    change(data, data["areas"]["fixture"])
    with pytest.raises(SurroundingsError) as refusal:
        check_surroundings_config(data, "the config here")
    assert "the config here" in str(refusal.value), str(refusal.value)


def test_the_smallest_values_the_config_allows_are_accepted():
    """spacing 1 m, margin 0 m, one column and one row: the bounds are 'positive' and '0 or more'."""
    data = copy.deepcopy(_config())
    data["areas"]["fixture"].update(spacing_m=1, margin_m=0, expected_columns=1, expected_rows=1)
    check_surroundings_config(data, "the config here")


BROKEN_CONFIGS = [
    pytest.param(lambda d, a: d.update(schema=1), "schema", id="schema-1"),
    pytest.param(lambda d, a: a.update(spacing_m=3000.0), "spacing_m", id="spacing-a-float"),
    pytest.param(lambda d, a: a.update(expected_sha256="ab" * 31), "expected_sha256", id="short"),
    pytest.param(lambda d, a: a.update(colour=1), "exactly the keys", id="an-extra-key"),
]


@pytest.mark.parametrize(("change", "word"), BROKEN_CONFIGS)
def test_the_step_checks_its_config_before_it_reads_anything_else(tmp_path, change, word):
    lock = _committed_lock()
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    change(config, config["areas"]["fixture"])
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and word in text, text
    assert DOWNLOAD_COMMAND not in text and LOCK_COMMAND not in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(("change", "word"), BROKEN_CONFIGS)
@pytest.mark.parametrize("built", [False, True], ids=["nothing-built", "built"])
def test_the_built_block_check_checks_its_config_even_when_nothing_is_built(
    tmp_path, change, word, built
):
    """A broken config is a refusal, never the quiet `None` of 'nothing built'."""
    out, lock, world_sha256 = _built(tmp_path) if built else (tmp_path, _committed_lock(), None)
    world_sha256 = world_sha256 or _sha((FIXTURE / "world.json").read_bytes())
    config = _config()
    change(config, config["areas"]["fixture"])
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, config, _world(), world_sha256, fixture_datasets(), lock)
    text = str(refusal.value)
    assert "config/surroundings.json" in text and word in text, text


@pytest.mark.parametrize("corner", ["e_min", "e_max", "n_min", "n_max"])
@pytest.mark.parametrize("shift", [0.5, 1000.0], ids=["fractional", "off-the-lattice"])
def test_each_corner_of_the_area_must_lie_on_the_lattice_in_whole_metres(tmp_path, corner, shift):
    """A corner of 2616000.5 is not a multiple of 3000 m whatever `int()` makes of it."""
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["areas"]["fixture"][corner] += shift
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    world = _world(path)
    lock = _committed_lock()
    config = recorded(_config(), path, lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            world, fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    named = f"{corner} {data['areas']['fixture'][corner]!r} is not a multiple"
    assert str(path) in text and "fixture" in text and "3000" in text and named in text, text
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- the datasets config


@pytest.mark.parametrize("key", ["attribution", "collection", "edition"])
@pytest.mark.parametrize("bad", ["missing", "empty", "number", "list"])
def test_each_text_of_the_datasets_config_is_checked_naming_the_config(tmp_path, key, bad):
    datasets = fixture_datasets()
    if bad == "missing":
        del datasets["swissaltiregio"][key]
    else:
        datasets["swissaltiregio"][key] = {"empty": "", "number": 7, "list": ["x"]}[bad]
    lock = _committed_lock()
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), datasets, lock, config, tmp_path / "raw", tmp_path / "out")
    text = str(refusal.value)
    assert "config/datasets.json" in text and key in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("resolution", [True, "1000", -1000, None], ids=repr)
def test_a_resolution_that_is_not_a_positive_whole_number_is_refused_naming_the_config(
    tmp_path, resolution
):
    datasets = fixture_datasets()
    datasets["swissaltiregio"]["resolution_m"] = resolution
    lock = _committed_lock()
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), datasets, lock, config, tmp_path / "raw", tmp_path / "out")
    assert "config/datasets.json" in str(refusal.value), str(refusal.value)


@pytest.mark.parametrize("datasets", [[], None, "swissaltiregio", ["swissaltiregio"]], ids=repr)
def test_a_datasets_config_that_is_not_an_object_is_refused_naming_it(tmp_path, datasets):
    lock = _committed_lock()
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), datasets, lock, config, tmp_path / "raw", tmp_path / "out")
    assert "config/datasets.json" in str(refusal.value), str(refusal.value)


def test_a_resolution_of_one_metre_is_a_usable_resolution(tmp_path):
    """The bound is 'positive': 1 m passes the datasets config and the fit, and the step goes on
    to the download, which is not there."""
    datasets = fixture_datasets()
    datasets["swissaltiregio"]["resolution_m"] = 1
    lock = _committed_lock()
    _entry_of(lock)["resolution_m"] = 1
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), datasets, lock, config, tmp_path / "raw", tmp_path / "out")
    text = str(refusal.value)
    assert DOWNLOAD_COMMAND in text and "config/datasets.json" not in text, text


# ------------------------------------------------------------------- the lock's fit


def _entry_of(lock: dict) -> dict:
    return lock["datasets"]["swissaltiregio"]


def _entry_with(**changes):
    def make(lock):
        _entry_of(lock).update(changes)
        return lock

    return make


def _without_the_tiles(lock):
    del _entry_of(lock)["tiles"]
    return lock


LOCK_SHAPES = [
    pytest.param(lambda lock: [], id="the-lock-is-a-list"),
    pytest.param(lambda lock: {"schema": 1}, id="no-datasets"),
    pytest.param(lambda lock: {"schema": 1, "datasets": ["swissaltiregio"]}, id="datasets-a-list"),
    pytest.param(lambda lock: {"schema": 1, "datasets": {"swissaltiregio": []}}, id="entry-a-list"),
    pytest.param(lambda lock: {"schema": 1, "datasets": {"swissaltiregio": None}}, id="entry-none"),
    pytest.param(_without_the_tiles, id="no-tiles"),
    pytest.param(_entry_with(tiles=None), id="tiles-none"),
    pytest.param(_entry_with(tiles=["2615-1094"]), id="tiles-a-list"),
    pytest.param(_entry_with(tiles="2615-1094"), id="tiles-a-text"),
]


@pytest.mark.parametrize("make", LOCK_SHAPES)
def test_a_lock_of_another_shape_is_refused_naming_lock_regio_and_no_other_command(tmp_path, make):
    lock = make(_committed_lock())
    config = recorded(_config(), _world(), _committed_lock(), "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert f"`{LOCK_COMMAND}`" in text and DOWNLOAD_COMMAND not in text, text
    assert not (tmp_path / "out").exists()


def test_a_lock_that_pins_no_checksum_for_a_tile_names_the_tile(tmp_path):
    lock = _committed_lock()
    del _entry_of(lock)["tiles"]["2625-1104"]
    config = recorded(_config(), _world(), _committed_lock(), "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert "pins no checksum for the tiles ['2625-1104']" in text, text
    assert f"`{LOCK_COMMAND}`" in text, text


@pytest.mark.parametrize("make", LOCK_SHAPES[:1] + LOCK_SHAPES[5:6])
def test_a_built_block_with_a_lock_file_of_another_shape_names_lock_regio(tmp_path, make):
    """The lock file is read as it is: a JSON list, or an entry without tiles, is a lock that
    does not fit, not an AttributeError or a TypeError."""
    out, lock, world_sha256 = _built(tmp_path)
    path = tmp_path / "datasets.lock.json"
    path.write_text(json.dumps(make(lock)), encoding="utf-8")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), path)
    assert f"`{LOCK_COMMAND}`" in str(refusal.value), str(refusal.value)


def _pin(**changes):
    def make(pin):
        return {**pin, **changes}

    return make


PIN_SHAPES = [
    pytest.param(lambda pin: "swissaltiregio_2615-1094.zip", id="pin-a-text"),
    pytest.param(lambda pin: None, id="pin-none"),
    pytest.param(lambda pin: ["file", "sha256"], id="pin-a-list-of-the-keys"),
    pytest.param(lambda pin: {"file": pin["file"]}, id="no-sha256"),
    pytest.param(lambda pin: {"sha256": pin["sha256"]}, id="no-file"),
    pytest.param(_pin(size_bytes=1), id="an-extra-key"),
    pytest.param(_pin(file=5), id="file-a-number"),
    pytest.param(_pin(file=None), id="file-none"),
    pytest.param(_pin(file=""), id="file-empty"),
    pytest.param(_pin(file="../x.zip"), id="file-up-a-folder"),
    pytest.param(_pin(file="dir/x.zip"), id="file-in-a-folder"),
    pytest.param(_pin(file=".hidden.zip"), id="file-starts-with-a-dot"),
    pytest.param(_pin(file="-x.zip"), id="file-starts-with-a-dash"),
    pytest.param(_pin(file="a b.zip"), id="file-with-a-space"),
    pytest.param(_pin(file="x.zip\n"), id="file-with-a-newline"),
    pytest.param(_pin(sha256=5), id="sha256-a-number"),
    pytest.param(_pin(sha256=None), id="sha256-none"),
    pytest.param(_pin(sha256="ab" * 31), id="sha256-62-digits"),
    pytest.param(_pin(sha256="ab" * 32 + "0"), id="sha256-65-digits"),
    pytest.param(_pin(sha256="AB" * 32), id="sha256-upper-case"),
    pytest.param(_pin(sha256="g" * 64), id="sha256-not-hex"),
    pytest.param(_pin(sha256="ab" * 32 + "\n"), id="sha256-with-a-newline"),
    pytest.param(_pin(sha256=" " + "ab" * 32), id="sha256-with-a-space"),
]


@pytest.mark.parametrize("make", PIN_SHAPES)
def test_a_tile_pin_that_is_not_exactly_a_file_name_and_a_sha256_is_refused(tmp_path, make):
    """Each conjunct of the pin's shape, one change at a time, the tile set being right."""
    lock = _committed_lock()
    tiles = _entry_of(lock)["tiles"]
    tiles[TILE] = make(tiles[TILE])
    config = recorded(_config(), _world(), _committed_lock(), "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert f"`{LOCK_COMMAND}`" in text and TILE in text and DOWNLOAD_COMMAND not in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("make", PIN_SHAPES[3:6] + PIN_SHAPES[9:10] + PIN_SHAPES[19:20])
def test_a_built_block_with_a_malformed_tile_pin_names_lock_regio(tmp_path, make):
    out, lock, world_sha256 = _built(tmp_path)
    tiles = _entry_of(lock)["tiles"]
    tiles[TILE] = make(tiles[TILE])
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), lock)
    assert f"`{LOCK_COMMAND}`" in str(refusal.value), str(refusal.value)


# ------------------------------------------------------------------- the tiles a box needs


def _tile_ids(box, spacing) -> list[str]:
    """The oracle: the 10 km tiles meeting [e_min - s/2, e_max + s/2) x [n_min - s/2, n_max + s/2).

    Tile by tile in exact integers (every coordinate doubled), east outer and north inner, the
    corners at E = 5 km + 10 km i and N = 4 km + 10 km j: no range arithmetic shared with the step.
    """
    e_min, e_max, n_min, n_max = box
    ids = []
    for e0 in range(5_000 + 10_000 * (e_min // 10_000 - 2), e_max + 20_000, 10_000):
        for n0 in range(4_000 + 10_000 * (n_min // 10_000 - 2), n_max + 20_000, 10_000):
            meets_east = 2 * e0 < 2 * e_max + spacing and 2 * (e0 + 10_000) > 2 * e_min - spacing
            meets_north = 2 * n0 < 2 * n_max + spacing and 2 * (n0 + 10_000) > 2 * n_min - spacing
            if meets_east and meets_north:
                ids.append(f"{e0 // 1000:04d}-{n0 // 1000:04d}")
    return ids


def _fit_run(where, spacing, margin, area, tiles) -> str:
    """Run the step on a world with `area` and a lock pinning exactly `tiles`; the refusal's text.

    There is no download there, so a lock that fits is refused for the download (the fit passed)
    and one that does not is refused naming `lock regio`.
    """
    where.mkdir(parents=True)
    box = (area[0] - margin, area[1] + margin, area[2] - margin, area[3] + margin)
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["areas"] = {"fixture": dict(zip(("e_min", "e_max", "n_min", "n_max"), map(float, area)))}
    path = where / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lock = _committed_lock()
    _entry_of(lock)["tiles"] = {t: {"file": zip_name(t), "sha256": "0" * 64} for t in tiles}
    config = recorded(_config(), path, lock, "swissaltiregio")
    config["areas"]["fixture"].update(
        margin_m=margin,
        spacing_m=spacing,
        expected_columns=(box[1] - box[0]) // spacing + 1,
        expected_rows=(box[3] - box[2]) // spacing + 1,
        expected_lv95_box={
            "e_max": float(box[1]),
            "e_min": float(box[0]),
            "n_max": float(box[3]),
            "n_min": float(box[2]),
        },
    )
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(
            _world(path), fixture_datasets(), lock, config, where / "raw", where / "o"
        )
    assert not (where / "o").exists()
    return str(refusal.value)


# (id, spacing, margin, the area's (e_min, e_max, n_min, n_max), the tile that decides, needed?)
# A border: the box's edge is a tile edge, so the vertices there take samples from the tile
# beyond it (needed). A touch: the box's edge less (or plus) half a spacing is a tile edge, so
# the tile beyond holds no sample of the last square (not needed). The touches need a spacing of
# 16 m on the east-west axis and 32 m on the north-south one: a tile edge is half a spacing off
# a multiple of it nowhere else (tile edges 5 km + 10 km i, 4 km + 10 km j).
FIT_CASES = [
    ("east-border", 3000, 3000, (2616000, 2622000, 1095000, 1107000), "2625-1094", True),
    ("west-border", 3000, 3000, (2628000, 2634000, 1095000, 1107000), "2615-1094", True),
    ("north-border", 3000, 3000, (2616000, 2625000, 1095000, 1101000), "2615-1104", True),
    ("south-border", 3000, 3000, (2616000, 2625000, 1107000, 1113000), "2615-1094", True),
    ("east-touch", 16, 16, (2616000, 2624976, 1095008, 1107008), "2625-1094", False),
    ("west-touch", 16, 16, (2625024, 2631008, 1095008, 1107008), "2615-1094", False),
    ("north-touch", 32, 32, (2616000, 2624000, 1086016, 1093952), "2615-1094", False),
    ("south-touch", 32, 32, (2616000, 2624000, 1094048, 1106016), "2615-1084", False),
]


@pytest.mark.parametrize(
    ("spacing", "margin", "area", "tile", "needed"),
    [case[1:] for case in FIT_CASES],
    ids=[case[0] for case in FIT_CASES],
)
def test_the_tiles_a_box_needs_follow_half_a_spacing_on_every_side(
    tmp_path, spacing, margin, area, tile, needed
):
    box = (area[0] - margin, area[1] + margin, area[2] - margin, area[3] + margin)
    exact = _tile_ids(box, spacing)
    assert (tile in exact) is needed, (tile, exact)  # the case is what its comment says
    text = _fit_run(tmp_path / "exact", spacing, margin, area, exact)
    assert DOWNLOAD_COMMAND in text and LOCK_COMMAND not in text, text
    other = [t for t in exact if t != tile] if needed else sorted([*exact, tile])
    text = _fit_run(tmp_path / "other", spacing, margin, area, other)
    assert f"`{LOCK_COMMAND}`" in text, text


# ------------------------------------------------------------------- a vertex without a sample


def _without_square(source, e, n):
    """`source` without the nine samples of the square [e - 1500, e + 1500) x [n - 1500, n + 1500)."""
    for tile in source["tiles"]:
        kept = []
        for line in _lines_of(source, tile):
            x, y, _ = line.split(" ")
            if not (e - 1500 <= int(x) < e + 1500 and n - 1500 <= int(y) < n + 1500):
                kept.append(line)
        _with_lines(source, kept, tile)
    return source


def test_the_first_vertex_without_a_sample_is_named_by_row_column_and_position(tmp_path):
    """(row 5, column 1) and (row 6, column 4): row and column differ, east and north differ."""
    source = fixture_source()
    for e, n in ((2616000, 1095000), (2625000, 1092000)):
        _without_square(source, e, n)
    text = _refusal(tmp_path, source)
    assert "row 5, column 1" in text and "(2616000, 1095000)" in text, text
    assert "2 such vertices" in text and DOWNLOAD_COMMAND in text, text
    assert "row 6" not in text and "2625000" not in text, text


# ------------------------------------------------------------------- the files and the cleanup


def test_only_the_surroundings_folder_is_cleaned_of_parts(tmp_path):
    out = tmp_path / "out"
    folder = out / "surroundings"
    (out / "terrain").mkdir(parents=True)
    folder.mkdir()
    stale = [folder / "a.f32.part", folder / "b.json.part"]
    kept = [out / "top.part", out / "terrain" / "dem.f32.part"]
    for path in [*stale, *kept]:
        path.write_bytes(b"a run cut short")
    (folder / "dir.part").mkdir()  # a folder named like a part is no file of a run: left alone
    lines = []
    _build(tmp_path, progress=lines.append)
    assert not any(path.exists() for path in stale)
    assert all(path.read_bytes() == b"a run cut short" for path in kept)
    assert sorted(p.name for p in folder.iterdir()) == ["dir.part", "fixture.f32", "fixture.json"]
    assert lines[-1] == "removed 2 .part files left in surroundings/", lines


# ------------------------------------------------------------------- progress


def test_progress_tells_the_whole_run_in_order(tmp_path):
    lines = []
    _build(tmp_path, progress=lines.append)
    heads = [line.split(" ", 1)[0] for line in lines]
    assert heads == ["reading"] * 9 + ["computing", "the", "wrote"], lines
    assert lines[9] == "computing 6 × 7 vertices at 3000 m"
    assert lines[10] == (
        f"the heights have the SHA-256 config/surroundings.json expects, {FIXTURE_SHA}"
    )


def test_a_part_left_by_a_cut_run_is_told_once_in_the_singular(tmp_path):
    stale = tmp_path / "out" / "surroundings" / "older.f32.part"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"a run cut short")
    lines = []
    _build(tmp_path, progress=lines.append)
    assert lines[-1] == "removed 1 .part file left in surroundings/", lines
    assert [line for line in lines if line.startswith("removed")] == [lines[-1]]


def test_the_expected_value_is_not_reported_before_it_holds(tmp_path):
    """Hard Rule 2: no line says the heights match until they have been compared."""
    config = _config()
    config["areas"]["fixture"]["expected_sha256"] = "ab" * 32
    root, lock = raw_regio(tmp_path / "raw")
    lines = []
    with pytest.raises(SurroundingsError):
        build_surroundings(
            _world(),
            fixture_datasets(),
            lock,
            recorded(config, _world(), lock, "swissaltiregio"),
            root,
            tmp_path / "out",
            progress=lines.append,
        )
    assert [line.split(" ", 1)[0] for line in lines] == ["reading"] * 9 + ["computing"], lines
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- the built description's file


@pytest.mark.parametrize(
    "name",
    ["surroundings/copy.f32", "surroundings/../surroundings/fixture.f32"],
    ids=["a-copy-of-the-heights", "the-same-file-by-another-path"],
)
def test_a_built_description_that_points_at_another_file_is_refused_naming_the_step(tmp_path, name):
    """The path the heights are read from comes from the description: it must be the step's."""
    out, lock, world_sha256 = _built(tmp_path)
    folder = out / "surroundings"
    shutil.copy(folder / "fixture.f32", folder / "copy.f32")
    block = json.loads((folder / "fixture.json").read_text(encoding="utf-8"))
    block["file"] = name
    (folder / "fixture.json").write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), lock)
    text = str(refusal.value)
    assert STEP_COMMAND in text and "file is" in text, text


@pytest.mark.parametrize("where", ["description", "source", "lv95_box", "cut_box"])
def test_a_built_description_part_given_as_a_list_of_its_keys_is_refused_naming_the_step(
    tmp_path, where
):
    """A list of the right keys has the right `set()`: only its type refuses it."""
    out, lock, world_sha256 = _built(tmp_path)
    path = out / "surroundings" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    if where == "description":
        block = sorted(block)
    else:
        block[where] = sorted(block[where])
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(SurroundingsError) as refusal:
        built_surroundings_block(out, _config(), _world(), world_sha256, fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value), str(refusal.value)


# ------------------------------------------------------------------- provenance.json and the lock


def test_a_provenance_that_lists_another_file_name_than_the_lock_is_refused(tmp_path):
    """The same bytes under another name: the lock pins the name too, and the step reads it."""
    root, lock = raw_regio(tmp_path / "raw")
    folder = root.joinpath(*FOLDER)
    other = "swissaltiregio_copy.xyz.zip"
    (folder / other).write_bytes((folder / zip_name(TILE)).read_bytes())
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    for entry in provenance["tiles"]:
        if entry["tile"] == TILE:
            entry["file"] = other
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert DOWNLOAD_COMMAND in text and other in text and zip_name(TILE) in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(tiles=["not-an-object"] * 9),
        lambda p: p["tiles"][4].pop("file"),
        lambda p: p["tiles"][4].pop("sha256"),
        lambda p: p["tiles"].reverse(),
    ],
    ids=["tiles-not-objects", "entry-without-file", "entry-without-sha256", "tiles-out-of-order"],
)
def test_a_provenance_whose_tiles_are_not_the_locked_ones_in_order_is_refused(tmp_path, change):
    root, lock = raw_regio(tmp_path / "raw")
    path = root.joinpath(*FOLDER, "provenance.json")
    provenance = json.loads(path.read_text(encoding="utf-8"))
    change(provenance)
    path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    assert DOWNLOAD_COMMAND in str(refusal.value), str(refusal.value)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("tiles", [{}, "none", None, 5, [1], [None]], ids=repr)
def test_a_provenance_whose_tiles_are_not_a_list_of_objects_says_so(tmp_path, tiles):
    root, lock = raw_regio(tmp_path / "raw")
    path = root.joinpath(*FOLDER, "provenance.json")
    provenance = json.loads(path.read_text(encoding="utf-8"))
    provenance["tiles"] = tiles
    path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert DOWNLOAD_COMMAND in text and "not a list of objects" in text, text


# ------------------------------------------------------------------- a tile's bytes before its lines


@pytest.mark.parametrize("case", ["not-a-zip", "a-bad-height-text"])
def test_a_tile_of_other_bytes_is_refused_for_its_checksum_before_anything_is_read(tmp_path, case):
    """The bytes are checked against the lock first: a tile that is also unreadable says so second."""
    root, lock = raw_regio(tmp_path / "raw")  # the zips, provenance and lock agree
    path = root.joinpath(*FOLDER, zip_name(TILE))
    pinned = _entry_of(lock)["tiles"][TILE]["sha256"]
    if case == "not-a-zip":
        path.write_bytes(b"this is not a zip file")
    else:
        lines = _lines_of(fixture_source())
        x, y, _ = lines[0].split(" ")
        source = _with_lines(fixture_source(), [f"{x} {y} 1e3", *lines[1:]])
        path.write_bytes(xyz_zip(source["tiles"][TILE]["member"], _text_of(source)))
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert f"tile {TILE}" in text and f"has SHA-256 {_sha(path.read_bytes())}" in text, text
    assert pinned in text and DOWNLOAD_COMMAND in text, text
    assert "cannot read it as a zip" not in text and "height text" not in text, text
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- what is wrong with a line


@pytest.mark.parametrize(
    ("line", "words"),
    [
        ("{x} {y}", ["not three fields"]),
        ("{x}.0 {y} {z}", ["x '{x}.0'", "whole number of metres"]),
        ("{x} {y}.5 {z}", ["y '{y}.5'", "whole number of metres"]),
        ("{x} {y} 1e3", ["the height text '1e3'", "whole centimetres"]),
    ],
    ids=["two-fields", "a-bad-x", "a-bad-y", "a-bad-height"],
)
def test_a_refused_line_says_which_of_its_fields_is_wrong(tmp_path, line, words):
    """Hard Rule 2: a refusal that blames the height for a bad position sends the owner to the
    wrong column of a 25-million-line file."""
    lines = _lines_of(fixture_source())
    x, y, z = lines[4].split(" ")
    lines[4] = line.format(x=x, y=y, z=z)
    message = _refusal(tmp_path, _with_lines(fixture_source(), lines))
    assert "line 6:" in message, message
    for word in words:
        assert word.format(x=x, y=y) in message, message
    if "height text" not in " ".join(words):
        assert "height text" not in message, message


# ------------------------------------------------------------------- how a zip can fail


def _stored(tile=TILE) -> bytes:
    source = fixture_source()
    return xyz_zip(source["tiles"][tile]["member"], _text_of(source, tile))


def _headers(data: bytes) -> tuple[int, int]:
    """The offsets of the (one) member's local header and central directory entry."""
    return data.find(b"PK\x03\x04"), data.rfind(b"PK\x01\x02")


def _method(data: bytes, method: int) -> bytes:
    data = bytearray(data)
    local, central = _headers(data)
    struct.pack_into("<H", data, local + 8, method)
    struct.pack_into("<H", data, central + 10, method)
    return bytes(data)


def _flags(data: bytes, flags: int) -> bytes:
    data = bytearray(data)
    local, central = _headers(data)
    struct.pack_into("<H", data, local + 6, flags)
    struct.pack_into("<H", data, central + 8, flags)
    return bytes(data)


def _deflated_but_corrupt() -> bytes:
    """The live (deflated) form with its first block's header made the reserved type 3."""
    source = fixture_source()
    data = bytearray(xyz_zip(source["tiles"][TILE]["member"], _text_of(source), deflated=True))
    local, _ = _headers(data)
    name_length, extra_length = struct.unpack_from("<HH", data, local + 26)
    data[local + 30 + name_length + extra_length] = 0xFF  # BFINAL = 1, BTYPE = 11
    return bytes(data)


def _invalid_utf8_name() -> bytes:
    """A member whose name is flagged UTF-8 and is not: zipfile fails decoding it, not reading it."""
    data = bytearray(_flags(_stored(), 0x800))
    local, central = _headers(data)
    data[local + 30] = 0xFF
    data[central + 46] = 0xFF
    return bytes(data)


ZIP_FAILURES = [
    pytest.param(_deflated_but_corrupt, id="zlib-error-a-corrupt-deflate-block"),
    pytest.param(lambda: _method(_stored(), 99), id="not-implemented-an-unknown-method"),
    pytest.param(lambda: _method(_stored(), 9), id="not-implemented-deflate64"),
    pytest.param(lambda: _flags(_stored(), 0x1), id="runtime-error-an-encrypted-member"),
    pytest.param(_invalid_utf8_name, id="unicode-error-a-name-that-is-not-utf-8"),
]


@pytest.mark.parametrize("make", ZIP_FAILURES)
def test_a_zip_that_fails_to_read_is_refused_naming_the_tile_not_left_to_raise(tmp_path, make):
    """Every way the standard library's zip reader fails, each a refusal naming tile and command."""
    root, lock = _laid_out(tmp_path, fixture_source(), make())
    config = recorded(_config(), _world(), lock, "swissaltiregio")
    with pytest.raises(SurroundingsError) as refusal:
        build_surroundings(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert f"tile {TILE}" in text and DOWNLOAD_COMMAND in text, text
    assert "cannot read it as a zip" in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("error", [EOFError, OSError], ids=lambda e: e.__name__)
def test_a_zip_reader_that_ends_early_or_cannot_read_is_refused_naming_the_tile(
    tmp_path, monkeypatch, error
):
    """Simulated: none of the zips tried here (a stored member claiming more bytes than the archive
    holds is `BadZipFile`, "Overlapped entries") made zipfile raise these two from memory, so the
    reader is replaced by one that raises them, to show the step turns them into a refusal too."""

    def read(self, name, pwd=None):
        raise error("simulated by the test")

    monkeypatch.setattr(zipfile.ZipFile, "read", read)
    text = _refusal(tmp_path)
    assert "tile 2605-1084" in text, text  # the first tile of the fixture's nine
    assert "cannot read it as a zip" in text and "simulated by the test" in text, text
    assert DOWNLOAD_COMMAND in text, text


# ------------------------------------------------------------------- the rule's arithmetic


def _rule(total_cm: int, count: int, offset: float) -> np.float32:
    """The brief's rule in plain Python scalars: one exact int / int division (correctly rounded
    in 64 bits), the 64-bit offset subtracted, one rounding to 32 bits."""
    return np.float32(total_cm / (100 * count) - offset)


TWINS = {
    "the offset rounded to 32 bits first": lambda s, n, o: np.float32(
        s / (100 * n) - float(np.float32(o))
    ),
    "the mean rounded to 32 bits before the offset": lambda s, n, o: np.float32(
        np.float32(s / (100 * n)) - np.float32(o)
    ),
    "two divisions, by 100 and then by the count": lambda s, n, o: np.float32((s / 100) / n - o),
    "two divisions, by the count and then by 100": lambda s, n, o: np.float32((s / n) / 100 - o),
}
# (sum in cm, samples, offset, the float32 bits of the rule, the twins that give other bits).
# The first two are heights of a village's size with an offset float32 cannot hold. The others
# are constructed (a search over sums at 25 and nine samples; the offset chosen so that the
# exact difference is a float32 rounding tie, which one more 64-bit rounding in the division
# moves to the other side): no real offset is such a number, and none is needed: they pin the
# order of the operations the rule states, which the village's own offsets cannot tell.
RULE_VECTORS = [
    (4215748, 25, 1250.1, 1138366847, list(TWINS)[:2]),
    (6189299, 25, 1250.25, 1150889735, list(TWINS)[1:2]),
    (6250043, 25, 0.10008574218727517, 1159478956, list(TWINS)[2:]),
    (2250004, 9, 0.10002549913178882, 1159478904, list(TWINS)[2:3]),
    (2250070, 9, 0.10011664496505546, 1159479204, list(TWINS)[3:]),
    # a square at the data's edge holds fewer samples: the divisor is the count, even one
    (243100, 1, 0.0, 1159196672, []),
    (486225, 2, 1250.25, 1150524416, []),
]


@pytest.mark.parametrize(
    ("total", "count", "offset", "bits", "twins"),
    RULE_VECTORS,
    ids=[
        "32-bit-offset",
        "32-bit-mean",
        "two-divisions-25",
        "two-divisions-9-a",
        "two-divisions-9-b",
        "one-sample",
        "two-samples",
    ],
)
def test_the_rule_is_one_division_and_a_64_bit_offset_then_one_rounding(
    total, count, offset, bits, twins
):
    assert int(_rule(total, count, offset).view("<u4")) == bits  # the vector is the rule's
    for name in twins:  # and it tells each twin it is meant to tell from the rule
        assert int(TWINS[name](total, count, offset).view("<u4")) != bits, name
    heights = surroundings._heights(
        np.array([[total]], dtype=np.int64),
        np.array([[count]], dtype=np.int64),
        np.zeros((1, 1), dtype=bool),
        offset,
    )
    assert heights.dtype == np.dtype("<f4")
    assert int(heights.view("<u4")[0, 0]) == bits


def test_the_cut_is_the_quiet_nan_whatever_its_square_holds():
    sums = np.array([[4215748, 0]], dtype=np.int64)
    counts = np.array([[25, 0]], dtype=np.int64)
    heights = surroundings._heights(sums, counts, np.array([[True, True]]), 1250.1)
    assert heights.tobytes() == NAN * 2


def _oracle_grid(offset: float, *, offset_in_32_bits: bool = False) -> bytes:
    """The fixture's grid by the rule in plain Python: exact integer sums of whole centimetres,
    one division, the offset in 64 bits (or, for the twin, rounded to 32), one rounding."""
    vectors = _vectors()
    box, cut, s = vectors["lv95_box"], vectors["cut_box"], vectors["spacing_m"]
    samples = {}
    for tile in fixture_source()["tiles"].values():
        for line in tile["text"].split("\r\n")[1:-1]:
            x, y, z = line.split(" ")
            samples[(int(x), int(y))] = int(Fraction(z) * 100)
    taken = float(np.float32(offset)) if offset_in_32_bits else offset
    cells = []
    for row in range(vectors["rows"]):
        for column in range(vectors["columns"]):
            e, n = int(box["e_min"]) + column * s, int(box["n_max"]) - row * s
            if cut["e_min"] < e < cut["e_max"] and cut["n_min"] < n < cut["n_max"]:
                cells.append(NAN)
                continue
            mine = [
                z
                for (x, y), z in samples.items()
                if e - s // 2 <= x < e + s // 2 and n - s // 2 <= y < n + s // 2
            ]
            cells.append(np.float32(sum(mine) / (100 * len(mine)) - taken).astype("<f4").tobytes())
    return b"".join(cells)


def test_a_height_offset_float32_cannot_hold_is_subtracted_in_64_bits_end_to_end(tmp_path):
    """The brief's own admission: the pinned offsets (0.0, 1250.25) are exact in 32 bits. 1250.1
    is not (float32 holds 1250.0999755859375), and the grid it gives is not the 32-bit twin's."""
    offset = 1250.1
    expected = _oracle_grid(offset)
    assert _oracle_grid(offset, offset_in_32_bits=True) != expected  # the test has teeth
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["height_offset_m"] = offset
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    root, lock = raw_regio(tmp_path / "raw")
    config = recorded(_config(), path, lock, "swissaltiregio")
    config["areas"]["fixture"]["expected_sha256"] = _sha(expected)
    out = tmp_path / "out"
    build_surroundings(_world(path), fixture_datasets(), lock, config, root, out)
    assert (out / "surroundings" / "fixture.f32").read_bytes() == expected


# ------------------------------------------------------------------- the vertices, one by one


@pytest.mark.parametrize("spacing", [1, 2, 3, 4, 5, 7, 50])
def test_a_sample_goes_to_the_one_vertex_whose_half_open_square_holds_it(spacing):
    """[E - s/2, E + s/2) x [N - s/2, N + s/2) for even and odd spacings (the village's is even,
    but the config allows any whole number): every integer position in and around a small grid,
    against the square written out in exact fractions. The step's integer arithmetic has a
    different rounding for odd and even spacings (`+ s - 1` on the north-south axis)."""
    s = spacing
    box = (100, 100 + 3 * s, 200, 200 + 2 * s)  # 4 columns, 3 rows
    grid = surroundings._Grid(area="x", spacing=s, cut=box, box=box, columns=4, rows=3)
    points = [
        (px, py)
        for px in range(box[0] - s, box[1] + s + 1)
        for py in range(box[2] - s, box[3] + s + 1)
    ]

    def cents(px, py):
        return 1000 + 7 * px + 13 * py

    sums = np.zeros((3, 4), dtype=np.int64)
    counts = np.zeros_like(sums)
    surroundings._accumulate(
        grid,
        np.array([p[0] for p in points], dtype=np.int64),
        np.array([p[1] for p in points], dtype=np.int64),
        np.array([cents(*p) for p in points], dtype=np.int64),
        sums,
        counts,
    )
    half = Fraction(s, 2)
    for r in range(3):
        for c in range(4):
            e, n = box[0] + c * s, box[3] - r * s
            mine = [
                p for p in points if e - half <= p[0] < e + half and n - half <= p[1] < n + half
            ]
            assert len(mine) == s * s  # a half-open square of side s holds s positions an axis
            assert (int(counts[r, c]), int(sums[r, c])) == (len(mine), sum(cents(*p) for p in mine))
    assert int(counts.sum()) == 12 * s * s


def test_the_step_s_sums_counts_cut_and_heights_are_the_shared_vectors_vertex_by_vertex(tmp_path):
    """The rule's twins (a square closed on a side, rows flipped, a vertex at the square's centre,
    no cut, a cut that takes the edge, another NaN, no offset, the mean rounded down) change the
    step's comparison with the fixture's expected SHA-256 and so every test that builds. This one
    does not build: it asks the step's own reading, accumulation, cut and heights for the 14
    vertices the vectors name, and for the whole grid, so that each twin also fails here, naming
    the vertex."""
    vectors = _vectors()
    world, settings = _world(), _config()["areas"]["fixture"]
    grid = surroundings._grid_of(world, "fixture", settings, SurroundingsError)
    assert (grid.columns, grid.rows) == (vectors["columns"], vectors["rows"])
    root, _ = raw_regio(tmp_path / "raw")
    folder = root.joinpath(*FOLDER)
    resolution = fixture_datasets()["swissaltiregio"]["resolution_m"]
    sums = np.zeros((grid.rows, grid.columns), dtype=np.int64)
    counts = np.zeros_like(sums)
    for tile in download.regio_tiles(
        world, "fixture", margin_m=settings["margin_m"], spacing_m=settings["spacing_m"]
    ):  # the tile rule has one home (brief v0.6.0-07)
        path = folder / zip_name(tile)
        x, y, centimetres = surroundings._tile_samples(path.read_bytes(), tile, path, resolution)
        surroundings._accumulate(grid, x, y, centimetres, sums, counts)
    cut = surroundings._cut_mask(grid)
    heights = surroundings._heights(sums, counts, cut, world.height_offset)
    for vertex in vectors["vertices"]:
        r, c = vertex["row"], vertex["column"]
        assert (int(counts[r, c]), int(sums[r, c])) == (vertex["samples"], vertex["sum_cm"]), (r, c)
        assert bool(cut[r, c]) == (vertex["local_y"] is None), (r, c)
        if vertex["local_y"] is None:
            assert heights[r, c].tobytes() == NAN, (r, c)
        else:
            assert float(heights[r, c]) == vertex["local_y"], (r, c)
    assert int(cut.sum()) == vectors["nan_count"]
    data = heights.tobytes()
    assert _sha(data) == vectors["sha256"]
    assert data == (FIXTURE / "generated" / "surroundings" / "fixture.f32").read_bytes()
