"""The roofs step end to end, and its refusals in their order (brief M3-05).

`build_roofs` over the roofs fixture laid out as the downloads leave it (`roofs_inputs`: the
fixture's own sheet file read through a stand-in for `read_sheet`, the photo as four sparse
GeoTIFF tiles read for real): it gives design's roof colours for the fixture's buildings, and
writes the description whose bytes the test assembles itself, as its expected value. Twice,
the same bytes.

The checks come in this order and each refusal leaves nothing under the output folder and
makes no progress call before the downloads are vouched for: the world config
(design's step), the fit of the lock's swissbuildings3d entry and then its swissimage entry
(naming `python -m mattini lock buildings` or `lock photo`), `computed_for` against the two
entries (design's step), the downloads in the order of the datasets' names (`download
buildings`, then `download photo`), each file's SHA-256, and last the SHA-256 of the file
about to be written against `expected_sha256`. A lock without one of the two entries is
refused naming its lock command, never a KeyError.

Does NOT prove: that `read_sheet` reads swisstopo's MultiPatch sheets and the tile reader its
JPEG-compressed tiles (the real run does, against config/roofs.json); the memory of the real
run (brief M3-05's Findings).
"""

import builtins
import copy
import hashlib
import io
import json
import os
import shutil
from pathlib import Path

import pytest
from roofs_inputs import AREA, design_chunks, fake_read_sheet, make_inputs, two_entries_sha256

from mattini import roofs
from mattini.roofs import RoofsError, build_roofs

LOCK_BUILDINGS = "python -m mattini lock buildings"
LOCK_PHOTO = "python -m mattini lock photo"
DOWNLOAD_BUILDINGS = "python -m mattini download buildings"
DOWNLOAD_PHOTO = "python -m mattini download photo"
MACHINE = "this machine or this code computes other roof colours than design's"
SHEET_FILE = "swissbuildings3d_3_0_2020_1249-42_2056_5728.gdb.zip"


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    return make_inputs(tmp_path_factory.mktemp("roofs_inputs"))


@pytest.fixture(autouse=True)
def fixture_sheets(monkeypatch):
    monkeypatch.setattr(roofs, "read_sheet", fake_read_sheet)


@pytest.fixture(scope="module")
def built(case, tmp_path_factory):
    """One good build, shared by the tests that look at its result: (out folder, block, the
    progress lines). The sheet reader is the fixture's, as in every test of this module."""
    out, said = tmp_path_factory.mktemp("built") / "generated", []
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(roofs, "read_sheet", fake_read_sheet)
        block = _build(case, out, progress=said.append)
    return out, block, said


def _build(case, out, *, lock=None, config=None, raw_root=None, progress=None, world=None):
    return build_roofs(
        case["world"] if world is None else world,
        case["datasets"],
        case["lock"] if lock is None else lock,
        case["config"] if config is None else config,
        case["terrain"],
        case["raw_root"] if raw_root is None else raw_root,
        out,
        progress=progress,
    )


def _refused(case, out: Path, **kwargs) -> str:
    said = []
    with pytest.raises(RoofsError) as refusal:
        _build(case, out, progress=said.append, **kwargs)
    assert not out.exists(), "a refusal creates nothing under the output folder"
    return str(refusal.value), said


def test_the_roofs_are_the_oracle_s_and_the_file_is_the_expected_one(case, built):
    """The buildings' order, tiles and counts are design's; their colours and pixel counts
    are the scalar oracle's over the noise; the file is the bytes the test assembled."""
    out, block, said = built
    assert block == case["block"]
    assert (out / "roofs" / "fixture.json").read_bytes() == case["data"]
    assert [p.name for p in (out / "roofs").iterdir()] == ["fixture.json"]
    assert sorted(p.name for p in out.iterdir()) == ["roofs"]
    assert any(case["config"]["areas"][AREA]["expected_sha256"] in line for line in said), said
    design = design_chunks()
    assert [(c["tile"], [b["uuid"] for b in c["buildings"]]) for c in block["chunks"]] == [
        (c["tile"], [b["uuid"] for b in c["buildings"]]) for c in design
    ]
    for chunk, wanted in zip(block["chunks"], design, strict=True):
        for building, designed in zip(chunk["buildings"], wanted["buildings"], strict=True):
            assert (building["triangles"], building["vertices"]) == (
                designed["triangles"],
                designed["vertices"],
            )
    coloured = {b["uuid"] for c in block["chunks"] for b in c["buildings"] if b["roof"]}
    designed = {b["uuid"] for c in design for b in c["buildings"] if b["roof"]}
    assert coloured == designed and len(coloured) >= 10  # the tower and the strips have none


def test_a_roof_reaching_beyond_the_area_counts_the_pixels_there(built):
    """The building whose centre is on the area's south edge has half its roof outside the
    area; design's windows end at the area, the tile's pixels do not."""
    _, block, _ = built
    south = "{3F09D6A1-0000-4000-8000-000000000010}"
    pixels = {b["uuid"]: b["roof_pixels"] for c in block["chunks"] for b in c["buildings"]}
    designed = {b["uuid"]: b["roof_pixels"] for c in design_chunks() for b in c["buildings"]}
    assert pixels[south] == 2 * designed[south] or pixels[south] > designed[south]


def test_two_builds_write_the_same_bytes(case, built, tmp_path):
    _build(case, tmp_path / "second")
    assert (built[0] / "roofs" / "fixture.json").read_bytes() == (
        tmp_path / "second" / "roofs" / "fixture.json"
    ).read_bytes()


def test_the_steps_readers_say_what_they_read(built):
    text = "\n".join(built[2])
    assert SHEET_FILE in text and "swissimage-dop10_2023_2650-1149_0.1_2056.tif" in text
    assert "buildings in" in text and "roof pixels" in text


def test_a_changed_world_is_design_s_step_and_comes_first(case, tmp_path):
    config = copy.deepcopy(case["config"])
    config["areas"][AREA]["computed_for"]["world_sha256"] = "0" * 64
    lock = copy.deepcopy(case["lock"])
    del lock["datasets"]["swissimage"]  # also wrong, and later in the order
    message, said = _refused(case, tmp_path / "out", config=config, lock=lock)
    assert "config/world.json" in message and "design" in message
    assert LOCK_PHOTO not in message and DOWNLOAD_BUILDINGS not in message
    assert said == []


def _drop(name):
    def edit(lock):
        del lock["datasets"][name]

    return edit


def _buildings(**change):
    def edit(lock):
        lock["datasets"]["swissbuildings3d"].update(change)

    return edit


def _photo(**change):
    def edit(lock):
        lock["datasets"]["swissimage"].update(change)

    return edit


def _missing_sheet(lock):
    lock["datasets"]["swissbuildings3d"]["sheets"].clear()


def _extra_sheet(lock):
    lock["datasets"]["swissbuildings3d"]["sheets"]["1249-43"] = {
        "file": "x.zip",
        "sha256": "1" * 64,
    }


def _missing_tile(lock):
    del lock["datasets"]["swissimage"]["tiles"]["2651-1150"]


def _extra_tile(lock):
    lock["datasets"]["swissimage"]["tiles"]["2652-1149"] = {"file": "x.tif", "sha256": "1" * 64}


@pytest.mark.parametrize(
    ("edit", "command"),
    [
        (_drop("swissbuildings3d"), LOCK_BUILDINGS),
        (_buildings(edition="2015"), LOCK_BUILDINGS),
        (_buildings(collection="ch.swisstopo.other"), LOCK_BUILDINGS),
        (_missing_sheet, LOCK_BUILDINGS),
        (_extra_sheet, LOCK_BUILDINGS),
        (_drop("swissimage"), LOCK_PHOTO),
        (_photo(edition="2020"), LOCK_PHOTO),
        (_photo(resolution_m=0.25), LOCK_PHOTO),
        (_missing_tile, LOCK_PHOTO),
        (_extra_tile, LOCK_PHOTO),
    ],
    ids=[
        "no-buildings-entry",
        "buildings-edition",
        "buildings-collection",
        "no-sheets",
        "extra-sheet",
        "no-photo-entry",
        "photo-edition",
        "photo-resolution",
        "missing-tile",
        "extra-tile",
    ],
)
def test_a_lock_that_does_not_fit_names_its_lock_command_never_a_key_error(
    case, tmp_path, edit, command
):
    lock = copy.deepcopy(case["lock"])
    edit(lock)
    message, said = _refused(case, tmp_path / "out", lock=lock)
    assert command in message
    other = {LOCK_BUILDINGS, LOCK_PHOTO} - {command}
    assert not any(c in message for c in other) and "design" not in message
    assert said == []


def test_the_buildings_entry_is_checked_before_the_photo_s(case, tmp_path):
    lock = copy.deepcopy(case["lock"])
    del lock["datasets"]["swissbuildings3d"], lock["datasets"]["swissimage"]
    message, _ = _refused(case, tmp_path / "out", lock=lock)
    assert LOCK_BUILDINGS in message and LOCK_PHOTO not in message


def test_other_inputs_are_design_s_step_not_a_command(case, tmp_path):
    lock = copy.deepcopy(case["lock"])
    lock["datasets"]["swissimage"]["tiles"]["2651-1150"]["sha256"] = "2" * 64
    message, said = _refused(case, tmp_path / "out", lock=lock)
    assert "config/roofs.json" in message and "design" in message
    assert LOCK_PHOTO not in message and DOWNLOAD_PHOTO not in message
    assert said == []
    lock = copy.deepcopy(case["lock"])
    sheets = lock["datasets"]["swissbuildings3d"]["sheets"]
    sheets["1249-42"]["sha256"] = "3" * 64
    message, _ = _refused(case, tmp_path / "again", lock=lock)
    assert "config/roofs.json" in message and "design" in message


def _empty_raw(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    raw.mkdir()
    return raw


def test_a_download_that_never_ran_names_buildings_first(case, tmp_path):
    message, said = _refused(case, tmp_path / "out", raw_root=_empty_raw(tmp_path))
    assert DOWNLOAD_BUILDINGS in message and DOWNLOAD_PHOTO not in message
    assert said == []


def test_only_the_photo_missing_names_the_photo(case, tmp_path):
    raw = _empty_raw(tmp_path)
    shutil.copytree(case["raw_root"] / "swissbuildings3d", raw / "swissbuildings3d")
    message, said = _refused(case, tmp_path / "out", raw_root=raw)
    assert DOWNLOAD_PHOTO in message and DOWNLOAD_BUILDINGS not in message
    assert said == []


def _copied(case, tmp_path) -> Path:
    raw = tmp_path / "raw"
    shutil.copytree(case["raw_root"], raw)
    return raw


def test_a_sheet_that_is_not_the_locked_one_is_refused_naming_it(case, tmp_path):
    raw = _copied(case, tmp_path)
    path = raw / "swissbuildings3d" / "2020" / SHEET_FILE
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 1
    path.write_bytes(bytes(data))
    message, _ = _refused(case, tmp_path / "out", raw_root=raw)
    assert "1249-42" in message and DOWNLOAD_BUILDINGS in message


def test_a_listed_sheet_that_is_absent_is_refused_naming_it(case, tmp_path):
    raw = _copied(case, tmp_path)
    (raw / "swissbuildings3d" / "2020" / SHEET_FILE).unlink()
    message, _ = _refused(case, tmp_path / "out", raw_root=raw)
    assert "1249-42" in message and DOWNLOAD_BUILDINGS in message


def test_a_provenance_that_is_not_the_locked_one_names_its_download(case, tmp_path):
    raw = _copied(case, tmp_path)
    path = raw / "swissbuildings3d" / "2020" / "provenance.json"
    provenance = json.loads(path.read_text(encoding="utf-8"))
    provenance["sheets"][0]["sha256"] = "4" * 64
    path.write_text(json.dumps(provenance), encoding="utf-8")
    message, _ = _refused(case, tmp_path / "out", raw_root=raw)
    assert "1249-42" in message and DOWNLOAD_BUILDINGS in message
    raw = _copied(case, tmp_path / "second")
    path = raw / "swissimage" / "2023" / "provenance.json"
    provenance = json.loads(path.read_text(encoding="utf-8"))
    provenance["tiles"] = provenance["tiles"][:-1]
    path.write_text(json.dumps(provenance), encoding="utf-8")
    message, _ = _refused(case, tmp_path / "out2", raw_root=raw)
    assert DOWNLOAD_PHOTO in message


def test_a_tile_that_changed_after_it_was_downloaded_is_refused_naming_it(case, tmp_path):
    raw = _copied(case, tmp_path)
    name = "swissimage-dop10_2023_2650-1150_0.1_2056.tif"
    path = raw / "swissimage" / "2023" / name
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 1
    path.write_bytes(bytes(data))
    message, said = _refused(case, tmp_path / "out", raw_root=raw)
    assert "2650-1150" in message and DOWNLOAD_PHOTO in message
    assert "2650-1149" not in message
    assert any(SHEET_FILE in line for line in said), "the sheets were read first"


def test_roofs_other_than_design_s_are_refused_before_anything_is_written(case, tmp_path):
    config = copy.deepcopy(case["config"])
    config["areas"][AREA]["expected_sha256"] = "5" * 64
    message, said = _refused(case, tmp_path / "out", config=config)
    assert MACHINE in message
    assert case["config"]["areas"][AREA]["expected_sha256"] in message and "5" * 64 in message
    assert not any("wrote" in line for line in said)


def test_the_area_must_be_the_terrain_configs(case, tmp_path):
    config = {"schema": 1, "areas": {"other": case["config"]["areas"][AREA]}}
    message, _ = _refused(case, tmp_path / "out", config=config)
    assert "other" in message and AREA in message


def test_an_area_the_world_does_not_have_is_refused(case, tmp_path):
    terrain = copy.deepcopy(case["terrain"])
    terrain["areas"] = {"elsewhere": terrain["areas"][AREA]}
    config = {"schema": 1, "areas": {"elsewhere": case["config"]["areas"][AREA]}}
    with pytest.raises(RoofsError, match="elsewhere"):
        build_roofs(
            case["world"], case["datasets"], case["lock"], config, terrain, case["raw_root"],
            tmp_path / "out",
        )  # fmt: skip
    assert not (tmp_path / "out").exists()


@pytest.fixture
def opened(monkeypatch):
    """Every path opened through builtins.open or io.open while the test runs."""
    paths = []
    real_open = io.open

    def recording_open(file, *args, **kwargs):
        if isinstance(file, str | bytes | os.PathLike):
            paths.append(Path(os.fsdecode(file)).resolve())
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", recording_open)
    monkeypatch.setattr(io, "open", recording_open)
    return paths


def _inputs_read(paths, raw_root) -> list[str]:
    root = Path(raw_root).resolve()
    return [p.name for p in paths if p.is_relative_to(root) and p.name != "provenance.json"]


def test_no_sheet_or_tile_is_read_before_the_checks_pass(case, tmp_path, opened):
    config = copy.deepcopy(case["config"])
    config["areas"][AREA]["computed_for"]["world_sha256"] = "0" * 64
    _refused(case, tmp_path / "world", config=config)
    other = copy.deepcopy(case["lock"])
    other["datasets"]["swissimage"]["tiles"]["2651-1150"]["sha256"] = "2" * 64
    _refused(case, tmp_path / "inputs", lock=other)
    assert _inputs_read(opened, case["raw_root"]) == []
    _build(case, tmp_path / "good")  # positive control: the recorder sees the reads
    assert SHEET_FILE in _inputs_read(opened, case["raw_root"])


def test_the_helper_s_inputs_hash_is_the_canonical_object_of_the_two_entries(case):
    entries = {n: case["lock"]["datasets"][n] for n in ("swissbuildings3d", "swissimage")}
    text = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert two_entries_sha256(case["lock"]) == hashlib.sha256(text.encode()).hexdigest()
    assert case["config"]["areas"][AREA]["computed_for"]["inputs_sha256"] == (
        two_entries_sha256(case["lock"])
    )
