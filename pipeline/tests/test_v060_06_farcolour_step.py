"""Pinning tests for brief v0.6.0-06: the far colour step `farcolour` (design §2).

Pinned decisions (the brief's Decisions; design §2, §5):
- `mattini.farcolour`: `FarColourError(ValueError)`, every refusal one; `build_farcolour(world,
  datasets, lock, surroundings_config, raw_root, out_dir, *, progress=None) -> dict` and
  `built_farcolour_block(out_dir, surroundings_config, world, world_sha256, datasets, lock) ->
  dict | None` (`lock` a dict or the lock file's path).
- The colour: pixel (r, c) centred at (e_min + cell/2 + cell·c, n_max − cell/2 − cell·r) over the
  surroundings box; a covered cell's pixel is (sum + 12) // 25 of its 5 × 5 source pixels; a pixel
  of a cell the lock records as absent is filled with the half-up integer mean of every covered
  pixel of its band (floor(sample / band_m), the swissALTIRegio sample at the pixel centre), or
  of the nearest band below that has one, else the nearest above (the fixture's vectors).
- The checks, each before the next reads anything: the config holds a colour block; the
  owner's axes; the cell is swissALTIRegio's resolution and 5 × swissimage_far's; the world
  (`colour.computed_for.world_sha256`, naming design); the box and design's columns and rows; the
  lock's fit, swissaltiregio's as the heights' (naming `lock regio`) and swissimage_far's tiles
  and absent cells exactly the box's 1 km cells (naming `lock farphoto`); the inputs
  (`lock.entries_sha256` over both entries, naming design); both downloads' provenance.json;
  then every file's SHA-256 and every tile's form (EPSG:2056, 1000 / resolution pixels a side,
  three uint8 bands, the transform its id gives), each refusal naming the tile and its download
  command; every pixel centre has its sample (refused naming the pixel and `download regio`).
- Before anything is written: the pixels against `expected_pixels_sha256` (the refusal names
  rasterio's and GDAL's versions), then the filled fraction against `expected_filled_fraction`,
  then the JPEG (photo.py's `encode_jpeg`) against `expected_sha256` (the refusal says the pixels
  are design's and names `jpeg_encoder()`); "nothing was written".
- The files, each through a `.part` rename, in this order: `surroundings/<area>_colour.jpg`, its
  `.import` (photo.py's KEEP remap), `surroundings/<area>_colour.json`, the description of brief
  v0.6.0-08's nine colour keys (sorted, 2-space indent, UTF-8, LF); after a success every `*.part`
  left in `surroundings/` is removed and nothing else there is touched.

Does NOT prove: the village's values (the step's own comparison at the brief's real run and the
release gate); the command line and the manifest (brief v0.6.0-07); what the game draws.
"""

import copy
import hashlib
import json
import os
import random

import pytest
from synthetic_farphoto import (
    FIXTURE,
    far_name,
    fixture_datasets,
    fixture_photo,
    fixture_source,
    geotiff,
    raw_farphoto,
    raw_inputs,
    tile_pixels,
)
from synthetic_regio import raw_regio

from mattini.farcolour import FarColourError, build_farcolour, built_farcolour_block
from mattini.surroundings import load_surroundings_config
from mattini.world import load_world

LOCK_REGIO = "python -m mattini lock regio"
LOCK_FAR = "python -m mattini lock farphoto"
DOWNLOAD_REGIO = "python -m mattini download regio"
DOWNLOAD_FAR = "python -m mattini download farphoto"
STEP_COMMAND = "python -m mattini farcolour"
KEEP = b'[remap]\n\nimporter="keep"\n'
FILES = ["fixture_colour.jpg", "fixture_colour.jpg.import", "fixture_colour.json"]
DESCRIPTION_KEYS = {
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


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _world():
    return load_world(FIXTURE / "world.json")


def _config():
    return load_surroundings_config(FIXTURE / "surroundings.json")


def _colour(config):
    return config["areas"]["fixture"]["colour"]


def _lock():
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))


def _recorded(config, world, lock):
    """A copy of `config` whose colour records `world` and both lock entries (computed here)."""
    config = copy.deepcopy(config)
    both = {name: lock["datasets"][name] for name in ("swissaltiregio", "swissimage_far")}
    text = json.dumps(both, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    data = world if isinstance(world, bytes) else (FIXTURE / "world.json").read_bytes()
    _colour(config)["computed_for"] = {
        "inputs_sha256": _sha(text.encode("utf-8")),
        "world_sha256": _sha(data),
    }
    return config


def _build(tmp_path, *, lock=None, config=None, progress=None, datasets=None, **far):
    root, made = raw_inputs(tmp_path / "raw", **far)
    lock = made if lock is None else lock
    config = _recorded(_config(), _world(), made) if config is None else config
    out = tmp_path / "out"
    block = build_farcolour(
        _world(), datasets or fixture_datasets(), lock, config, root, out, progress=progress
    )
    return block, out


def _refusal(tmp_path, **kwargs):
    with pytest.raises(FarColourError) as refusal:
        _build(tmp_path, **kwargs)
    assert not (tmp_path / "out").exists()
    return str(refusal.value)


# ------------------------------------------------------------------- what it writes


def test_the_step_writes_the_designed_files_exactly(tmp_path):
    block, out = _build(tmp_path)
    colour = _colour(_config())
    folder = out / "surroundings"
    assert sorted(p.name for p in folder.iterdir()) == FILES
    jpeg = (folder / "fixture_colour.jpg").read_bytes()
    assert _sha(jpeg) == colour["expected_sha256"]
    assert (folder / "fixture_colour.jpg.import").read_bytes() == KEEP
    text = (folder / "fixture_colour.json").read_bytes()
    assert text == (json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    assert set(block) == DESCRIPTION_KEYS
    far = fixture_datasets()["swissimage_far"]
    assert block == {
        "colour_cell_m": 100.0,
        "colour_columns": 30,
        "colour_file": "surroundings/fixture_colour.jpg",
        "colour_format": "jpeg",
        "colour_pixels_sha256": colour["expected_pixels_sha256"],
        "colour_rows": 30,
        "colour_sha256": colour["expected_sha256"],
        "colour_source": {
            "attribution": far["attribution"],
            "collection": far["collection"],
            "dataset": "swissimage_far",
            "edition": far["edition"],
        },
        "filled_fraction": 300 / 900,
    }
    assert type(block["colour_cell_m"]) is float and type(block["filled_fraction"]) is float
    assert type(block["colour_columns"]) is int and type(block["colour_rows"]) is int


def test_a_second_build_writes_the_same_bytes(tmp_path):
    _, out = _build(tmp_path)
    first = {p.name: p.read_bytes() for p in (out / "surroundings").iterdir()}
    _, out = _build(tmp_path)
    assert {p.name: p.read_bytes() for p in (out / "surroundings").iterdir()} == first


def test_the_order_of_a_regio_tile_s_lines_does_not_matter(tmp_path):
    source = fixture_source()
    tile = source["regio"]["tiles"]["2615-1094"]
    lines = tile["text"].split("\r\n")[1:-1]
    lines = random.Random(6).sample(lines, len(lines))
    tile["text"] = "\r\n".join(["x y z", *lines]) + "\r\n"
    block, _ = _build(tmp_path, source=source)
    assert block["colour_pixels_sha256"] == _colour(_config())["expected_pixels_sha256"]


def test_each_file_goes_through_a_part_rename_and_old_parts_go(tmp_path, monkeypatch):
    folder = tmp_path / "out" / "surroundings"
    folder.mkdir(parents=True)
    (folder / "older.jpg.part").write_bytes(b"a run cut short")
    (folder / "fixture.f32").write_bytes(b"the heights step's file")
    renames = []
    real = os.replace

    def replace(src, dst):
        renames.append((os.fspath(src), os.fspath(dst)))
        real(src, dst)

    monkeypatch.setattr(os, "replace", replace)
    _build(tmp_path)
    assert renames == [
        (str(folder / f"{name}.part"), str(folder / name))
        for name in ("fixture_colour.jpg", "fixture_colour.jpg.import", "fixture_colour.json")
    ]
    assert sorted(p.name for p in folder.iterdir()) == ["fixture.f32", *FILES]
    assert (folder / "fixture.f32").read_bytes() == b"the heights step's file"


# ------------------------------------------------------------------- the checks, in order


def test_a_config_without_a_colour_block_is_refused_naming_it(tmp_path):
    config = _config()
    del config["areas"]["fixture"]["colour"]
    text = _refusal(tmp_path, config=config)
    assert "colour" in text and "config/surroundings.json" in text, text


def test_a_malformed_config_is_a_far_colour_refusal(tmp_path):
    config = _config()
    _colour(config)["band_m"] = 0
    text = _refusal(tmp_path, config=config)
    assert "band_m" in text, text


def test_another_world_is_refused_before_anything_else(tmp_path):
    config = _recorded(_config(), b'{"another": "world"}\n', _lock())
    lock = {"schema": 1, "datasets": {}}  # it would be refused next: the world comes first
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "config/world.json" in text, text
    assert "design" in text, text
    for command in (LOCK_REGIO, LOCK_FAR, DOWNLOAD_REGIO, DOWNLOAD_FAR):
        assert command not in text
    assert not (tmp_path / "out").exists()


def test_other_axes_are_refused_naming_the_world(tmp_path):
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["axes"] = {"x": "-e", "y": "+h", "z": "+n"}  # turned half round: a rotation
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            load_world(path), fixture_datasets(), _lock(), _config(), tmp_path, tmp_path / "out"
        )
    assert str(path) in str(refusal.value)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "where, key, value",
    [
        ("colour", "cell_m", 50),  # not the swissALTIRegio sample spacing
        ("swissimage_far", "resolution_m", 10),  # not 5 source pixels a side
        ("swissaltiregio", "resolution_m", 50),
    ],
)
def test_a_cell_that_is_not_the_sample_and_five_source_pixels_is_refused(
    tmp_path, where, key, value
):
    config, datasets = _config(), fixture_datasets()
    if where == "colour":
        _colour(config)[key] = value
    else:
        datasets[where][key] = value
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), datasets, _lock(), config, tmp_path / "raw", tmp_path / "out")
    assert "cell_m" in str(refusal.value), str(refusal.value)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda a: a["colour"].update(expected_columns=31),
        lambda a: a["colour"].update(expected_rows=29),
        lambda a: a["expected_lv95_box"].update(e_min=2614000.0),
    ],
)
def test_a_box_that_is_not_design_s_is_refused_before_the_lock(tmp_path, change):
    config = _config()
    change(config["areas"]["fixture"])
    lock = {"schema": 1, "datasets": {}}
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "design" in text, text
    assert LOCK_REGIO not in text and LOCK_FAR not in text


@pytest.mark.parametrize(
    "case", ["no-entry", "a-tile-missing", "another-edition", "another-resolution"]
)
def test_a_regio_lock_that_does_not_fit_is_refused_naming_lock_regio(tmp_path, case):
    lock = _lock()
    entry = lock["datasets"]["swissaltiregio"]
    if case == "no-entry":
        del lock["datasets"]["swissaltiregio"]
    elif case == "a-tile-missing":
        del entry["tiles"]["2605-1084"]  # the heights' half-spacing border still needs it
    elif case == "another-edition":
        entry["edition"] = "2025-06"
    else:
        entry["resolution_m"] = 10
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), lock, _config(), tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert LOCK_REGIO in text and LOCK_FAR not in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "case",
    [
        "no-entry",
        "another-edition",
        "another-resolution",
        "another-collection",
        "a-cell-in-neither",
        "a-cell-in-both",
        "a-cell-beyond-the-box",
        "no-absent-list",
    ],
)
def test_a_farphoto_lock_that_does_not_fit_is_refused_naming_lock_farphoto(tmp_path, case):
    lock = _lock()
    entry = lock["datasets"]["swissimage_far"]
    if case == "no-entry":
        del lock["datasets"]["swissimage_far"]
    elif case == "another-edition":
        entry["edition"] = "2020"
    elif case == "another-resolution":
        entry["resolution_m"] = 2
    elif case == "another-collection":
        entry["collection"] = "ch.swisstopo.swissimage-dop10-2"
    elif case == "a-cell-in-neither":
        entry["absent"].remove("2617-1094")
    elif case == "a-cell-in-both":
        entry["absent"].append("2615-1094")
        entry["absent"].sort()
    elif case == "a-cell-beyond-the-box":
        entry["absent"].append("2618-1094")
    else:
        del entry["absent"]
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), lock, _config(), tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert LOCK_FAR in text and LOCK_REGIO not in text, text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("dataset", ["swissaltiregio", "swissimage_far"])
def test_other_inputs_are_refused_before_the_download_is_read(tmp_path, dataset):
    lock = _lock()
    other = copy.deepcopy(lock)
    tiles = other["datasets"][dataset]["tiles"]
    tiles[min(tiles)]["sha256"] = "1" * 64
    config = _recorded(_config(), _world(), other)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(), fixture_datasets(), lock, config, tmp_path / "raw", tmp_path / "out"
        )
    text = str(refusal.value)
    assert "config/surroundings.json" in text and "lock" in text and "design" in text, text
    assert DOWNLOAD_REGIO not in text and DOWNLOAD_FAR not in text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("missing", ["both", "swissimage_far", "swissaltiregio"])
def test_a_missing_download_is_refused_before_any_progress_or_folder(tmp_path, missing):
    root = tmp_path / "raw"
    if missing == "swissimage_far":
        raw_regio(root, fixture_source()["regio"], datasets=fixture_datasets())
    elif missing == "swissaltiregio":
        raw_farphoto(root)
    lines = []
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(
            _world(),
            fixture_datasets(),
            _lock(),
            _config(),
            root,
            tmp_path / "out",
            progress=lines.append,
        )
    text = str(refusal.value)
    expected = DOWNLOAD_FAR if missing == "swissimage_far" else DOWNLOAD_REGIO
    if missing == "both":
        assert DOWNLOAD_REGIO in text or DOWNLOAD_FAR in text, text
    else:
        assert expected in text, text
    assert lines == []
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "case",
    [
        "provenance-absent-differs",
        "provenance-tiles-differ",
        "provenance-edition",
        "provenance-dataset",
        "a-file-of-other-bytes",
        "a-file-missing",
    ],
)
def test_a_far_download_that_is_not_the_locked_one_is_refused(tmp_path, case):
    root, lock = raw_inputs(tmp_path / "raw")
    folder = root / "swissimage_far" / "2023"
    path = folder / "provenance.json"
    provenance = json.loads(path.read_text(encoding="utf-8"))
    name = far_name("2615-1095", "2023", 20)
    if case == "provenance-absent-differs":
        provenance["absent"] = provenance["absent"][:-1]
    elif case == "provenance-tiles-differ":
        provenance["tiles"] = provenance["tiles"][1:]
    elif case == "provenance-edition":
        provenance["edition"] = "2020"
    elif case == "provenance-dataset":
        provenance["dataset"] = "swissimage"
    elif case == "a-file-of-other-bytes":
        data = bytearray((folder / name).read_bytes())
        data[-1] ^= 1
        (folder / name).write_bytes(bytes(data))
    else:
        (folder / name).unlink()
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    config = _recorded(_config(), _world(), lock)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert DOWNLOAD_FAR in text, text
    if case.startswith("a-file"):
        assert "2615-1095" in text, text
    assert not (tmp_path / "out").exists()


def _tile_case(case: str) -> bytes:
    source = fixture_source()
    pixels = tile_pixels(fixture_photo(source), source, "2615-1095")
    west, north = 2_615_000.0, 1_096_000.0
    if case == "another-crs":
        return geotiff(pixels, west, north, 20, epsg=21781)
    if case == "another-size":
        return geotiff(pixels[:, :49], west, north, 20)
    if case == "four-bands":
        return geotiff(pixels[..., [0, 1, 2, 2]], west, north, 20)
    if case == "16-bit":
        return geotiff(pixels, west, north, 20, dtype_bits=16)
    if case == "shifted-east":
        return geotiff(pixels, west + 20, north, 20)
    if case == "shifted-north":
        return geotiff(pixels, west, north + 20, 20)
    if case == "other-pixel-size":
        return geotiff(pixels.repeat(2, 0).repeat(2, 1), west, north, 10)
    return b"not a GeoTIFF"


@pytest.mark.parametrize(
    "case",
    [
        "another-crs",
        "another-size",
        "four-bands",
        "16-bit",
        "shifted-east",
        "shifted-north",
        "other-pixel-size",
        "not-a-tiff",
    ],
)
def test_a_tile_that_is_not_what_its_id_says_is_refused_naming_it(tmp_path, case):
    """The lock and provenance.json pin the odd bytes, as a lock of them would."""
    root, lock = raw_inputs(tmp_path / "raw", bodies={"2615-1095": _tile_case(case)})
    config = _recorded(_config(), _world(), lock)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert "2615-1095" in text and DOWNLOAD_FAR in text, text
    assert not (tmp_path / "out").exists()


def _source_with_line(transform):
    source = fixture_source()
    tile = source["regio"]["tiles"]["2615-1094"]
    lines = tile["text"].split("\r\n")[1:-1]
    tile["text"] = "\r\n".join(["x y z", *transform(lines)]) + "\r\n"
    return source


def test_a_height_text_that_is_not_whole_centimetres_is_refused_through_the_one_parser(
    tmp_path,
):
    """The regio samples are read by v0.6.0-04's parser: its refusal, word for word in kind."""

    def three_decimals(lines):
        x, y, _ = lines[4].split(" ")
        return [*lines[:4], f"{x} {y} 2430.123", *lines[5:]]

    source = _source_with_line(three_decimals)
    root, lock = raw_inputs(tmp_path / "raw", source=source)
    config = _recorded(_config(), _world(), lock)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert "2615-1094" in text and "line 6" in text and "2430.123" in text, text
    assert DOWNLOAD_REGIO in text
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "row, column",
    [(0, 0), (29, 29)],  # a covered pixel and a filled one: each needs its sample
)
def test_a_pixel_without_a_sample_is_refused_naming_it(tmp_path, row, column):
    x, y = 2_615_050 + 100 * column, 1_096_950 - 100 * row
    source = _source_with_line(
        lambda lines: [line for line in lines if not line.startswith(f"{x} {y} ")]
    )
    root, lock = raw_inputs(tmp_path / "raw", source=source)
    config = _recorded(_config(), _world(), lock)
    with pytest.raises(FarColourError) as refusal:
        build_farcolour(_world(), fixture_datasets(), lock, config, root, tmp_path / "out")
    text = str(refusal.value)
    assert f"row {row}, column {column}" in text and f"{x}, {y}" in text, text
    assert DOWNLOAD_REGIO in text
    assert not (tmp_path / "out").exists()


def test_other_pixels_are_refused_before_anything_is_written_naming_the_decoder(tmp_path):
    _, lock = raw_inputs(tmp_path / "make")
    config = _recorded(_config(), _world(), lock)
    expected = _colour(config)["expected_pixels_sha256"]
    _colour(config)["expected_pixels_sha256"] = "ab" * 32
    _colour(config)["expected_sha256"] = "cd" * 32  # the pixels are compared first
    text = _refusal(tmp_path, config=config)
    assert "ab" * 32 in text and expected in text and "nothing was written" in text, text
    assert "rasterio" in text and "GDAL" in text, text
    assert "cd" * 32 not in text


def test_another_filled_fraction_is_refused_before_anything_is_written(tmp_path):
    _, lock = raw_inputs(tmp_path / "make")
    config = _recorded(_config(), _world(), lock)
    _colour(config)["expected_filled_fraction"] = 0.25
    text = _refusal(tmp_path, config=config)
    assert "0.25" in text and repr(300 / 900) in text and "nothing was written" in text, text


def test_a_jpeg_difference_alone_names_the_encoder(tmp_path):
    _, lock = raw_inputs(tmp_path / "make")
    config = _recorded(_config(), _world(), lock)
    expected = _colour(config)["expected_sha256"]
    _colour(config)["expected_sha256"] = "ef" * 32
    text = _refusal(tmp_path, config=config)
    assert "ef" * 32 in text and expected in text and "nothing was written" in text, text
    assert "Pillow" in text and "libjpeg-turbo" in text and "pixels are design's" in text


def test_a_refused_build_leaves_the_old_files_as_they_were(tmp_path):
    _, out = _build(tmp_path)
    folder = out / "surroundings"
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    config = _recorded(_config(), _world(), _lock())
    _colour(config)["expected_pixels_sha256"] = "cd" * 32
    with pytest.raises(FarColourError):
        build_farcolour(_world(), fixture_datasets(), _lock(), config, tmp_path / "raw", out)
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


# ------------------------------------------------------------------- the built block


def _built(tmp_path):
    _, out = _build(tmp_path)
    return out, _world(), _sha((FIXTURE / "world.json").read_bytes()), _lock()


def test_nothing_built_is_none(tmp_path):
    world_sha256 = _sha((FIXTURE / "world.json").read_bytes())
    block = built_farcolour_block(
        tmp_path, _config(), _world(), world_sha256, fixture_datasets(), _lock()
    )
    assert block is None


def test_the_built_block_is_the_description(tmp_path):
    out, world, world_sha256, lock = _built(tmp_path)
    folder = out / "surroundings"
    description = json.loads((folder / "fixture_colour.json").read_text(encoding="utf-8"))
    for given in (lock, FIXTURE / "datasets.lock.json", str(FIXTURE / "datasets.lock.json")):
        block = built_farcolour_block(
            out, _config(), world, world_sha256, fixture_datasets(), given
        )
        assert block == description


@pytest.mark.parametrize(
    "case",
    [
        "jpeg",
        "import-missing",
        "import-other",
        "filled_fraction",
        "colour_columns",
        "colour_cell_m",
        "edition",
        "extra-key",
    ],
)
def test_a_built_block_that_no_longer_holds_is_refused_naming_the_step(tmp_path, case):
    out, world, world_sha256, lock = _built(tmp_path)
    folder = out / "surroundings"
    jpeg = folder / "fixture_colour.jpg"
    path = folder / "fixture_colour.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    if case == "jpeg":
        data = bytearray(jpeg.read_bytes())
        data[-3] ^= 1
        jpeg.write_bytes(bytes(data))
    elif case == "import-missing":
        (folder / "fixture_colour.jpg.import").unlink()
    elif case == "import-other":
        (folder / "fixture_colour.jpg.import").write_bytes(b'[remap]\n\nimporter="texture"\n')
    elif case == "filled_fraction":
        block["filled_fraction"] = 0.5
    elif case == "colour_columns":
        block["colour_columns"] = 31
    elif case == "colour_cell_m":
        block["colour_cell_m"] = 10.0
    elif case == "edition":
        block["colour_source"]["edition"] = "2020"
    else:
        block["extra"] = 1
    path.write_text(json.dumps(block, indent=2), encoding="utf-8")
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, _config(), world, world_sha256, fixture_datasets(), lock)
    assert STEP_COMMAND in str(refusal.value), str(refusal.value)


def test_a_built_block_for_another_world_or_entries_names_design(tmp_path):
    out, world, world_sha256, lock = _built(tmp_path)
    config = _recorded(_config(), b'{"another": "world"}\n', lock)
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, config, world, world_sha256, fixture_datasets(), lock)
    assert "design" in str(refusal.value) and STEP_COMMAND not in str(refusal.value)
    other = copy.deepcopy(lock)
    other["datasets"]["swissimage_far"]["tiles"]["2615-1095"]["sha256"] = "1" * 64
    config = _recorded(_config(), _world(), other)
    with pytest.raises(FarColourError) as refusal:
        built_farcolour_block(out, config, world, world_sha256, fixture_datasets(), lock)
    assert "design" in str(refusal.value) and STEP_COMMAND not in str(refusal.value)
