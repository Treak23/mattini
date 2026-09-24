"""Pinning tests for brief M0-04: swissALTI3D download for the village area.

Pinned decisions (SPEC §5, §7 and §9): the six village tiles; the edition and resolution
come from config/datasets.json, never "the latest"; STAC items are addressed by id; every
file is checked against swisstopo's published SHA-256 (multihash `1220…`); a verified
file is not fetched again; provenance is deterministic; a bad checksum is a visible error
that leaves no file looking valid. No network: the STAC API and the file host are faked.
"""

import hashlib
from pathlib import Path

import pytest

from mattini.datasets import load_datasets
from mattini.download import DownloadError, download_terrain, parse_multihash_sha256, village_tiles
from mattini.world import load_world

VILLAGE_TILES = ["2623-1095", "2623-1096", "2623-1097", "2624-1095", "2624-1096", "2624-1097"]
STAC_ITEMS = "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissalti3d/items/"


class FakeSwisstopo:
    """Serves STAC items and file bytes from memory and counts file fetches."""

    def __init__(self, edition, tiles, corrupt=()):
        self.items, self.files, self.file_fetches = {}, {}, []
        for tile in tiles:
            item_id = f"swissalti3d_{edition}_{tile}"
            fine = f"{item_id}_0.5_2056_5728.tif"
            coarse = f"{item_id}_2_2056_5728.tif"
            body = f"synthetic terrain bytes for {tile}".encode()
            self.files[f"https://files.example/{fine}"] = b"corrupted" if tile in corrupt else body
            self.files[f"https://files.example/{coarse}"] = b"the 2 m file must not be fetched"
            self.items[STAC_ITEMS + item_id] = {
                "id": item_id,
                "assets": {
                    fine: {
                        "href": f"https://files.example/{fine}",
                        "file:checksum": "1220" + hashlib.sha256(body).hexdigest().upper(),
                        "gsd": 0.5,
                    },
                    coarse: {
                        "href": f"https://files.example/{coarse}",
                        "file:checksum": "1220" + "00" * 32,
                        "gsd": 2.0,
                    },
                },
            }

    def fetch_json(self, url):
        return self.items[url]

    def fetch_file(self, url, dest):
        self.file_fetches.append(url)
        Path(dest).write_bytes(self.files[url])


def _download(fake, out_root):
    return download_terrain(
        load_world(),
        load_datasets(),
        out_root,
        fetch_json=fake.fetch_json,
        fetch_file=fake.fetch_file,
    )


def test_village_tiles_are_the_six_measured_tiles():
    assert village_tiles(load_world()) == VILLAGE_TILES


def test_edition_resolution_and_attribution_are_pinned_in_config():
    alti = load_datasets()["swissalti3d"]
    assert alti["collection"] == "ch.swisstopo.swissalti3d"
    assert alti["edition"] == "2024"
    assert alti["resolution_m"] == 0.5
    assert alti["attribution"] == "© swisstopo"


def test_multihash_sha256_is_parsed_and_other_codes_refused():
    digest = "ab" * 32
    assert parse_multihash_sha256("1220" + digest.upper()) == digest
    with pytest.raises(ValueError):
        parse_multihash_sha256("1340" + "ab" * 64)  # a SHA-512 multihash is not accepted
    with pytest.raises(ValueError):
        parse_multihash_sha256("1220" + "ab" * 31)  # too short


def test_download_verifies_files_and_writes_deterministic_provenance(tmp_path):
    fake = FakeSwisstopo("2024", VILLAGE_TILES)
    first = _download(fake, tmp_path)
    out_dir = tmp_path / "swissalti3d" / "2024"
    assert [entry["tile"] for entry in first] == VILLAGE_TILES
    for entry in first:
        path = out_dir / entry["file"]
        assert entry["file"].endswith("_0.5_2056_5728.tif")
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(fake.file_fetches) == 6
    provenance = (out_dir / "provenance.json").read_bytes()
    assert str(tmp_path).encode() not in provenance  # no absolute paths

    second = _download(fake, tmp_path)
    assert len(fake.file_fetches) == 6  # verified files are not fetched again
    assert second == first
    assert (out_dir / "provenance.json").read_bytes() == provenance


def test_bad_checksum_is_a_visible_error(tmp_path):
    fake = FakeSwisstopo("2024", VILLAGE_TILES, corrupt={"2624-1096"})
    with pytest.raises(DownloadError, match="2624-1096"):
        _download(fake, tmp_path)
    bad = tmp_path / "swissalti3d" / "2024" / "swissalti3d_2024_2624-1096_0.5_2056_5728.tif"
    assert not bad.exists()
