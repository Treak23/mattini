"""Pinning tests for brief M1-01: provenance.json exists only after a completed run (G-06, D9).

Pinned decisions (docs/history/ARCS.md §M0, D9): the download removes provenance.json
before its first change on disk (an unlink or a file fetch), so it exists only after a
run that completed; a run that fails before changing anything (offline, for example)
leaves the previous one in place, byte for byte. Harm prevented: M1's terrain step reads
only provenance.json, and a stale one listing a file the run deleted would claim six
verified tiles while five are on disk (Hard Rule 2).
"""

import pytest
from fake_swisstopo import FakeSwisstopo

from mattini.datasets import load_datasets
from mattini.download import DownloadError, download_terrain
from mattini.lock import build_lock
from mattini.world import load_world


def _download(fake, out_root, lock):
    return download_terrain(
        load_world(),
        load_datasets(),
        out_root,
        fetch_json=fake.fetch_json,
        fetch_file=fake.fetch_file,
        lock=lock,
        area="village",
    )


def _setup(tmp_path):
    fake = FakeSwisstopo()
    lock = build_lock(load_world(), load_datasets(), fake.fetch_json, area="village")
    _download(fake, tmp_path, lock)
    out_dir = tmp_path / "swissalti3d" / "2024"
    assert (out_dir / "provenance.json").is_file()
    return fake, lock, out_dir


def test_a_failed_rerun_after_a_damaged_file_leaves_no_provenance(tmp_path):
    fake, lock, out_dir = _setup(tmp_path)
    damaged = out_dir / "swissalti3d_2024_2623-1096_0.5_2056_5728.tif"
    damaged.write_bytes(b"damaged")
    fake.broken_files.add("https://files.example/" + damaged.name)
    with pytest.raises(DownloadError, match="2623-1096"):
        _download(fake, tmp_path, lock)
    assert not damaged.exists()
    assert not (out_dir / "provenance.json").exists()


def test_a_run_that_fails_before_any_change_keeps_the_old_provenance(tmp_path):
    fake, lock, out_dir = _setup(tmp_path)
    before = (out_dir / "provenance.json").read_bytes()
    fake.json_fetches.clear()
    fake.offline_after = 0  # offline from the first STAC read
    with pytest.raises(DownloadError):
        _download(fake, tmp_path, lock)
    assert (out_dir / "provenance.json").read_bytes() == before


def test_verified_tiles_are_no_change_on_disk(tmp_path):
    # The first three tiles are verified and kept, then the network drops: nothing changed.
    fake, lock, out_dir = _setup(tmp_path)
    before = (out_dir / "provenance.json").read_bytes()
    fake.json_fetches.clear()
    fake.offline_after = 3
    with pytest.raises(DownloadError):
        _download(fake, tmp_path, lock)
    assert (out_dir / "provenance.json").read_bytes() == before


def test_a_repaired_run_writes_provenance_again(tmp_path):
    fake, lock, out_dir = _setup(tmp_path)
    before = (out_dir / "provenance.json").read_bytes()
    (out_dir / "swissalti3d_2024_2623-1096_0.5_2056_5728.tif").write_bytes(b"damaged")
    _download(fake, tmp_path, lock)
    assert (out_dir / "provenance.json").read_bytes() == before
