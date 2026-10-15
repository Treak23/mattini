"""The photo step's refusals, in their order, and what a refusal leaves behind (brief M3-04).

Beyond the pinned tests: `build_photo` checks the world config first, then the lock's fit,
then the lock's entry, then the download, then each tile's bytes and shape, and only then
computes and compares the pixels. A refusal leaves nothing under the output folder (not
even the folder) and makes no progress call before the download is vouched for. A world or
inputs check that fails reads no tile (every file the step opens is recorded). Each
refusal names the command that fixes it: design's step for a changed world or other
inputs, `python -m mattini lock photo` for a lock that does not fit, `python -m mattini
download photo` for a download that is missing, listed otherwise or not the locked bytes.
Same inputs, same bytes: two builds write identical files (Hard Rule 5).

Does NOT prove: that the pinned expected values are the right ones (the real run is
compared with config/photo.json); that a Windows machine decodes swisstopo's tiles to the
same pixels.
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
from computed_for import computed_for
from test_photo_build_tiles import DATASETS, EXPECTED, TILES, _build, _config, _inputs

from mattini import photo
from mattini.photo import PhotoError, build_photo

DOWNLOAD = "python -m mattini download photo"
LOCK = "python -m mattini lock photo"


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    return _inputs(tmp_path_factory.mktemp("refusal_tiles"))


def _good_config(case: dict) -> dict:
    pixels, jpeg, _, _ = EXPECTED[0.2]
    return _config(0.2, pixels, jpeg, copy.deepcopy(case["computed_for"]))


def _refusal(case, config, out, *, lock=None, raw_root=None, progress=None) -> str:
    with pytest.raises(PhotoError) as refusal:
        build_photo(
            case["world"],
            DATASETS,
            case["lock"] if lock is None else lock,
            config,
            case["raw_root"] if raw_root is None else raw_root,
            out,
            progress=progress,
        )
    assert not out.exists(), "a refusal creates nothing under the output folder"
    return str(refusal.value)


def test_a_good_build_makes_every_file_and_progress_calls(case, tmp_path):
    said = []
    out = tmp_path / "generated"
    build_photo(
        case["world"],
        DATASETS,
        case["lock"],
        _good_config(case),
        case["raw_root"],
        out,
        progress=said.append,
    )
    assert sorted(p.name for p in (out / "photo").iterdir()) == [
        "village.jpg",
        "village.jpg.import",
        "village.json",
    ]
    assert any(EXPECTED[0.2][0] in line for line in said), said
    assert any(EXPECTED[0.2][1] in line for line in said), said


def test_two_builds_write_the_same_bytes(case, tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    for out in (first, second):
        build_photo(
            case["world"], DATASETS, case["lock"], _good_config(case), case["raw_root"], out
        )
    for name in ("village.jpg", "village.jpg.import", "village.json"):
        assert (first / "photo" / name).read_bytes() == (second / "photo" / name).read_bytes()


def test_a_changed_world_is_design_s_step_and_comes_first(case, tmp_path):
    config = _good_config(case)
    config["areas"]["village"]["computed_for"]["world_sha256"] = "0" * 64
    broken_lock = copy.deepcopy(case["lock"])
    del broken_lock["datasets"]["swissimage"]  # also wrong, and later in the order
    said = []
    message = _refusal(case, config, tmp_path / "out", lock=broken_lock, progress=said.append)
    assert "config/world.json" in message and "design" in message
    assert LOCK not in message and DOWNLOAD not in message
    assert said == []


def _drop_entry(lock):
    del lock["datasets"]["swissimage"]


def _other_edition(lock):
    lock["datasets"]["swissimage"]["edition"] = "2020"


def _other_collection(lock):
    lock["datasets"]["swissimage"]["collection"] = "ch.swisstopo.swissimage-dop10-x"


def _other_resolution(lock):
    lock["datasets"]["swissimage"]["resolution_m"] = 0.25


def _missing_tile(lock):
    del lock["datasets"]["swissimage"]["tiles"]["2624-1096"]


def _extra_tile(lock):
    lock["datasets"]["swissimage"]["tiles"]["2625-1095"] = {
        "file": "swissimage-dop10_2023_2625-1095_0.1_2056.tif",
        "sha256": "1" * 64,
    }


def _tile_without_a_checksum(lock):
    del lock["datasets"]["swissimage"]["tiles"]["2623-1095"]["sha256"]


def _extra_key(lock):
    lock["datasets"]["swissimage"]["note"] = "x"


@pytest.mark.parametrize(
    "change",
    [
        _drop_entry,
        _other_edition,
        _other_collection,
        _other_resolution,
        _missing_tile,
        _extra_tile,
        _tile_without_a_checksum,
        _extra_key,
    ],
    ids=lambda f: f.__name__.strip("_"),
)
def test_a_lock_that_does_not_fit_is_named_before_the_inputs(case, tmp_path, change):
    lock = copy.deepcopy(case["lock"])
    change(lock)
    said = []
    message = _refusal(case, _good_config(case), tmp_path / "out", lock=lock, progress=said.append)
    assert LOCK in message and "design" not in message and DOWNLOAD not in message
    assert said == []


def test_other_inputs_are_design_s_step_not_a_command(case, tmp_path):
    lock = copy.deepcopy(case["lock"])
    lock["datasets"]["swissimage"]["tiles"]["2624-1096"]["sha256"] = "2" * 64
    message = _refusal(case, _good_config(case), tmp_path / "out", lock=lock)
    assert "config/photo.json" in message and "design" in message
    assert LOCK not in message and DOWNLOAD not in message


def test_a_download_that_never_ran_names_the_download_and_makes_no_progress_call(case, tmp_path):
    empty = tmp_path / "raw"
    empty.mkdir()
    said = []
    message = _refusal(
        case, _good_config(case), tmp_path / "out", raw_root=empty, progress=said.append
    )
    assert DOWNLOAD in message and "provenance.json" in message
    assert said == []


def _copied_download(case, tmp_path) -> Path:
    raw = tmp_path / "raw"
    shutil.copytree(case["raw_root"], raw)
    return raw


def _provenance(raw: Path) -> Path:
    return raw / "swissimage" / "2023" / "provenance.json"


def _rewrite(path: Path, change) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _drop_a_tile(data):
    del data["tiles"][-1]


def _other_file(data):
    data["tiles"][0]["file"] = "another-name.tif"


def _other_sha(data):
    data["tiles"][1]["sha256"] = "3" * 64


def _other_edition_listed(data):
    data["edition"] = "2020"


def _unsafe_name(data):
    data["tiles"][0]["file"] = "../escape.tif"


def _swapped_tiles(data):
    data["tiles"][0], data["tiles"][1] = data["tiles"][1], data["tiles"][0]


@pytest.mark.parametrize(
    "change",
    [_drop_a_tile, _other_file, _other_sha, _other_edition_listed, _unsafe_name, _swapped_tiles],
    ids=lambda f: f.__name__.strip("_"),
)
def test_a_provenance_that_is_not_the_locked_download_names_the_download(case, tmp_path, change):
    raw = _copied_download(case, tmp_path)
    _rewrite(_provenance(raw), change)
    message = _refusal(case, _good_config(case), tmp_path / "out", raw_root=raw)
    assert DOWNLOAD in message


def test_a_provenance_that_is_not_json_names_the_download(case, tmp_path):
    raw = _copied_download(case, tmp_path)
    _provenance(raw).write_text("{", encoding="utf-8")
    assert DOWNLOAD in _refusal(case, _good_config(case), tmp_path / "out", raw_root=raw)


def test_a_listed_tile_that_is_absent_names_it_and_the_download(case, tmp_path):
    raw = _copied_download(case, tmp_path)
    (raw / "swissimage" / "2023" / "swissimage-dop10_2023_2624-1096_0.1_2056.tif").unlink()
    message = _refusal(case, _good_config(case), tmp_path / "out", raw_root=raw)
    assert "2624-1096" in message and DOWNLOAD in message
    assert "2623-1095" not in message


def test_a_tile_that_changed_after_it_was_downloaded_is_refused_naming_it(case, tmp_path):
    raw = _copied_download(case, tmp_path)
    path = raw / "swissimage" / "2023" / "swissimage-dop10_2023_2623-1096_0.1_2056.tif"
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 1
    path.write_bytes(bytes(data))
    message = _refusal(case, _good_config(case), tmp_path / "out", raw_root=raw)
    assert "2623-1096" in message and DOWNLOAD in message
    assert case["tile_sha256"]["2623-1096"] in message


def test_a_tile_that_is_not_a_tiff_is_refused_naming_it(tmp_path):
    case = _inputs(tmp_path)
    path = tmp_path / "raw" / "swissimage" / "2023" / "swissimage-dop10_2023_2624-1095_0.1_2056.tif"
    path.write_bytes(b"not a tiff at all")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()  # provenance and lock vouch for it
    case["lock"]["datasets"]["swissimage"]["tiles"]["2624-1095"]["sha256"] = sha
    _rewrite(_provenance(tmp_path / "raw"), lambda d: d["tiles"][2].update(sha256=sha))
    case["computed_for"] = computed_for(case["world"].path, case["lock"], "swissimage")
    message = _refusal(case, _good_config(case), tmp_path / "out")
    assert "2624-1095" in message and "GeoTIFF" in message


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


def _tiles_read(paths, raw_root) -> list[str]:
    root = Path(raw_root).resolve()
    return [p.name for p in paths if p.is_relative_to(root) and p.suffix == ".tif"]


def test_no_tile_is_read_before_the_world_and_inputs_checks_pass(case, tmp_path, opened):
    config = _good_config(case)
    config["areas"]["village"]["computed_for"]["world_sha256"] = "0" * 64
    _refusal(case, config, tmp_path / "world")
    other = copy.deepcopy(case["lock"])
    other["datasets"]["swissimage"]["tiles"]["2624-1096"]["sha256"] = "2" * 64
    _refusal(case, _good_config(case), tmp_path / "inputs", lock=other)
    assert _tiles_read(opened, case["raw_root"]) == []
    # positive control: the recorder sees the tiles read once the checks pass
    _build(case, _good_config(case), tmp_path / "good")
    assert len(_tiles_read(opened, case["raw_root"])) >= len(TILES)


def test_a_world_config_changed_after_it_was_parsed_is_refused(tmp_path):
    case = _inputs(tmp_path)
    path = case["world"].path
    data = json.loads(path.read_text(encoding="utf-8"))
    data["origin_lv95"]["e"] += 1.0
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    message = _refusal(case, _good_config(case), tmp_path / "out")
    assert str(path) in message and "changed while the photo was built" in message


def test_an_area_the_world_does_not_have_is_refused(case, tmp_path):
    config = _good_config(case)
    config["areas"] = {"other": config["areas"].pop("village")}
    message = _refusal(case, config, tmp_path / "out")
    assert "other" in message and str(case["world"].path) in message


@pytest.mark.parametrize("resolution", [0.2, None])
def test_swissimage_must_be_the_0_1_m_source(case, tmp_path, resolution):
    datasets = {"swissimage": {**DATASETS["swissimage"], "resolution_m": resolution}}
    with pytest.raises(PhotoError, match="0.1 m SWISSIMAGE"):
        build_photo(
            case["world"],
            datasets,
            case["lock"],
            _good_config(case),
            case["raw_root"],
            tmp_path / "out",
        )
    assert not (tmp_path / "out").exists()


def test_a_datasets_config_without_swissimage_names_the_file(case, tmp_path):
    with pytest.raises(PhotoError, match="config/datasets.json"):
        build_photo(
            case["world"], {}, case["lock"], _good_config(case), case["raw_root"], tmp_path / "o"
        )


def test_the_names_the_step_exports_for_the_roofs_step_exist():
    for name in ("PhotoTile", "photo_tiles", "read_tiles", "photo_lock_problem", "PhotoError"):
        assert hasattr(photo, name), name
