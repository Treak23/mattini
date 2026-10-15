"""Pinning tests for brief M1-01: exact bytes and key sets of what the pipeline writes (C-01).

Pinned decisions (docs/history/ARCS.md §M0; lesson 33): two runs compared on one machine
cannot see a field that changes by day or by machine (a date, a host name, a version), so
the manifest and provenance.json are pinned to exact bytes for fixed inputs, and their
key sets are pinned exactly. A later field changes these goldens on purpose, in the brief
that adds it (M1-03 adds the manifest's terrain block, M2-04 its buildings block).
"""

import hashlib
import json
from pathlib import Path

from fake_swisstopo import VILLAGE_TILES, FakeSwisstopo

from mattini.datasets import load_datasets
from mattini.download import download_terrain
from mattini.lock import build_lock
from mattini.manifest import write_manifest
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE_WORLD = REPO / "tests" / "shared" / "terrain_fixture" / "world.json"
# M1-03 added the terrain block, M2-04 the buildings block, M3-13 the photo, roofs, surfaces
# and trees blocks (all null here: nothing is built): each a new key set and golden. M3-13's
# golden is M2-04's bytes (ba8383ff…) with the four lines `  "photo": null,`, `  "roofs":
# null,`, `  "surfaces": null,` and `  "trees": null,` added, computed two ways (design).
MANIFEST_SHA256 = "cf4b939c6e4a89bf202081c365f22b338180c7d7141d34189af69cf709e20081"
PROVENANCE_SHA256 = "2efd91929da1aa4aa7a987c39a1b66ad25af330ba51eabcde84da3809b77b73a"
PROVENANCE_KEYS = {
    "attribution",
    "collection",
    "dataset",
    "edition",
    "resolution_m",
    "schema",
    "tiles",
}
TILE_KEYS = {"file", "item", "sha256", "size_bytes", "tile", "url"}


def test_manifest_bytes_for_a_fixed_world_config(tmp_path):
    raw = write_manifest(tmp_path, FIXTURE_WORLD).read_bytes()
    manifest = json.loads(raw)
    assert set(manifest) == {
        "buildings",
        "photo",
        "roofs",
        "schema",
        "surfaces",
        "terrain",
        "trees",
        "world",
        "world_sha256",
    }
    assert manifest["terrain"] is None
    assert manifest["buildings"] is None
    assert manifest["world"] == json.loads(FIXTURE_WORLD.read_text(encoding="utf-8"))
    assert manifest["world_sha256"] == hashlib.sha256(FIXTURE_WORLD.read_bytes()).hexdigest()
    assert hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256


def test_provenance_bytes_for_a_fixed_fake_server(tmp_path):
    fake = FakeSwisstopo()
    lock = build_lock(load_world(), load_datasets(), fake.fetch_json, area="village")
    download_terrain(
        load_world(),
        load_datasets(),
        tmp_path,
        fetch_json=fake.fetch_json,
        fetch_file=fake.fetch_file,
        lock=lock,
        area="village",
    )
    raw = (tmp_path / "swissalti3d" / "2024" / "provenance.json").read_bytes()
    provenance = json.loads(raw)
    assert set(provenance) == PROVENANCE_KEYS
    assert [entry["tile"] for entry in provenance["tiles"]] == VILLAGE_TILES
    for entry in provenance["tiles"]:
        assert set(entry) == TILE_KEYS
    assert hashlib.sha256(raw).hexdigest() == PROVENANCE_SHA256
