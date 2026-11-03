"""Gap tests for brief v0.6.0-04: what the 103 pinned tests leave open (lesson 51).

The pin author's probes on the rehearsal's throwaway left the pins green with three removals: the
owner's-axes refusal, provenance.json's `dataset` key and the member's final CRLF. This file pins
those three, and the other places where the pinned tests check a refusal in part: the line a bad
sample is on, the keys of provenance.json and of the datasets config, a tile that is not a zip,
the built block's fields one by one, the lock's fit and the lock file in `built_surroundings_block`,
and the progress lines. The pinned files stay untouched; the words of a refusal are pinned only
where a reader needs them (the tile, the line, the command).

Does NOT prove: that the real tiles read as these synthetic ones do (the step's own comparison
with design's SHA-256 does, at v0.6.0-07's real run); the command line and the manifest (brief
v0.6.0-07); the game's reading (brief v0.6.0-08).
"""

import copy
import hashlib
import json

import pytest
from computed_for import recorded
from synthetic_regio import FIXTURE, fixture_datasets, fixture_source, raw_regio, zip_name

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
