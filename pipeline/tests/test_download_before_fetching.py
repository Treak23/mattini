"""The downloads' guarantees the M2 R1 review found untested (brief M2-07; I-02, I-03, I-04).

- *Refused before anything changes, from an empty folder (I-02).* The earlier tests of the
  republish refusal ran a complete download first, so a check made lazily, just before each
  fetch, passed them: the sheets before the republished one were already on disk and were
  not fetched again. Here the folder is empty and a middle sheet (or tile) is republished:
  nothing may be fetched and the dataset's folder must not exist. Harm: about 9.5 MB
  fetched and folders made before a refusal whose message says nothing was fetched.
- *provenance.json goes before a fetch (I-03).* A complete download, one file deleted,
  its re-fetch failing twice: provenance.json must be gone, since it would list a file
  that is not on disk. The damaged-file branch has its own test
  (test_provenance_lifecycle.py); this is the missing-file branch.
- *One rule for the lock's sheets (I-04).* `download buildings` refuses a lock whose
  buildings entry pins other sheets beside the area's, as the buildings step and the
  manifest do, naming `python -m mattini lock buildings`, before swisstopo is asked
  anything. Harm: a download that reports success, then a step that refuses.

Each republish refusal also names design's step (brief M2-07): the expected values in
config/terrain.json or config/buildings.json record the lock entry they were computed from.

Does NOT prove: anything about a real republish (none exists to try); the network.
"""

import pytest
from fake_swisstopo import FakeSwisstopo
from test_buildings_download import SHEETS, FakeBuildingsStac, _download, _lock

from mattini import lock
from mattini.datasets import load_datasets
from mattini.download import DownloadError, download_terrain
from mattini.world import load_world

MIDDLE_SHEET = "1348-12"  # the fourth of the six
MIDDLE_TILE = "2623-1097"  # the third of the six


def _download_terrain(fake, out_root, pinned):
    return download_terrain(
        load_world(),
        load_datasets(),
        out_root,
        fake.fetch_json,
        fake.fetch_file,
        lock=pinned,
        area="village",
    )


def test_a_republished_middle_sheet_is_refused_from_an_empty_folder(tmp_path):
    fake = FakeBuildingsStac()
    pinned = _lock(fake)
    assert SHEETS.index(MIDDLE_SHEET) == 3
    fake.publish(MIDDLE_SHEET, b"republished")
    with pytest.raises(DownloadError) as refused:
        _download(fake, tmp_path, pinned)
    message = str(refused.value)
    assert f"sheet {MIDDLE_SHEET} of area 'village'" in message and "nothing was fetched" in message
    assert "`python -m mattini lock buildings`, then commit the lock, then design recomputes" in (
        message
    )
    assert (
        "the expected values in config/buildings.json, config/roofs.json and "
        "config/trees.json (docs/SPEC.md §8)"
    ) in message
    assert fake.file_fetches == []
    assert not (tmp_path / "swissbuildings3d").exists()
    assert list(tmp_path.iterdir()) == []


def test_a_republished_middle_tile_is_refused_from_an_empty_folder(tmp_path):
    """The terrain's twin of the test above (the same code path, the same class of harm)."""
    fake = FakeSwisstopo()
    pinned = lock.build_lock(load_world(), load_datasets(), fake.fetch_json, area="village")
    fake.republish(MIDDLE_TILE)
    with pytest.raises(DownloadError) as refused:
        _download_terrain(fake, tmp_path, pinned)
    message = str(refused.value)
    assert f"tile {MIDDLE_TILE} of area 'village'" in message and "nothing was fetched" in message
    assert "`python -m mattini lock terrain`, then commit the lock, then design recomputes" in (
        message
    )
    assert (
        "the expected values in config/terrain.json and config/trees.json (docs/SPEC.md §8)"
    ) in message
    assert fake.file_fetches == []
    assert not (tmp_path / "swissalti3d").exists()
    assert list(tmp_path.iterdir()) == []


def test_a_missing_sheet_that_cannot_be_fetched_leaves_no_provenance(tmp_path):
    fake = FakeBuildingsStac()
    pinned = _lock(fake)
    _download(fake, tmp_path, pinned)
    folder = tmp_path / "swissbuildings3d" / "2020"
    assert (folder / "provenance.json").is_file()
    missing = folder / f"swissbuildings3d_3_0_2020_{MIDDLE_SHEET}_2056_5728.gdb.zip"
    missing.unlink()
    url = f"https://files.example/{missing.name}"
    fetch = fake.fetch_file

    def failing(file_url, dest):
        if file_url == url:
            fake.file_fetches.append(file_url)
            raise ConnectionResetError("the network dropped")
        fetch(file_url, dest)

    fake.fetch_file = failing
    fake.file_fetches.clear()
    with pytest.raises(DownloadError, match=MIDDLE_SHEET):
        _download(fake, tmp_path, pinned)
    assert fake.file_fetches == [url, url]  # the fetch and its one retry
    assert not (folder / "provenance.json").exists()
    assert not missing.exists() and not list(folder.glob("*.part"))


def test_a_missing_tile_that_cannot_be_fetched_leaves_no_provenance(tmp_path):
    fake = FakeSwisstopo()
    pinned = lock.build_lock(load_world(), load_datasets(), fake.fetch_json, area="village")
    _download_terrain(fake, tmp_path, pinned)
    folder = tmp_path / "swissalti3d" / "2024"
    assert (folder / "provenance.json").is_file()
    missing = folder / f"swissalti3d_2024_{MIDDLE_TILE}_0.5_2056_5728.tif"
    missing.unlink()
    fake.broken_files.add(f"https://files.example/{missing.name}")
    fake.file_fetches.clear()
    with pytest.raises(DownloadError, match=MIDDLE_TILE):
        _download_terrain(fake, tmp_path, pinned)
    assert len(fake.file_fetches) == 2
    assert not (folder / "provenance.json").exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda sheets: sheets.update({"1347-22": dict(sheets["1348-11"])}),
        lambda sheets: sheets.update({"1349-11": dict(sheets["1348-14"])}),
    ],
    ids=["a-western-neighbour", "a-sheet-far-east"],
)
def test_a_lock_pinning_more_than_the_area_s_sheets_is_refused(tmp_path, change):
    fake = FakeBuildingsStac()
    pinned = _lock(fake)
    change(pinned["datasets"]["swissbuildings3d"]["sheets"])
    lock.validate_lock(pinned, "test")  # a well-formed lock; only its sheets are wrong
    fake.json_fetches.clear()
    with pytest.raises(DownloadError) as refused:
        _download(fake, tmp_path, pinned)
    message = str(refused.value)
    extra = sorted(set(pinned["datasets"]["swissbuildings3d"]["sheets"]) - set(SHEETS))
    for part in (*extra, str(SHEETS), "'village'", "`python -m mattini lock buildings`"):
        assert part in message, (part, message)
    assert fake.json_fetches == [] and fake.file_fetches == []
    assert list(tmp_path.iterdir()) == []


def test_the_lock_s_own_sheets_download(tmp_path):
    """Positive control: exactly the area's sheets, in the lock `lock buildings` writes."""
    fake = FakeBuildingsStac()
    pinned = _lock(fake)
    assert sorted(pinned["datasets"]["swissbuildings3d"]["sheets"]) == SHEETS
    assert [entry["sheet"] for entry in _download(fake, tmp_path, pinned)] == SHEETS
