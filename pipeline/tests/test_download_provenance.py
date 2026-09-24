"""What is fetched follows the config, and provenance.json is deterministic (Hard Rule 5).

Beyond the pinned tests (brief M0-04): the exact STAC URLs, the edition and resolution
taken from the config rather than written into the code, the tiles following the village
box, and the provenance bytes: sorted, LF, UTF-8, the attribution, no times, the same
whichever directory they are written under.
"""

import hashlib
import json
import re

from mattini.datasets import load_datasets
from mattini.download import download_terrain, village_tiles
from mattini.world import REPO, load_world

TILES = ["2623-1095", "2623-1096", "2623-1097", "2624-1095", "2624-1096", "2624-1097"]
STAC_ITEMS = "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissalti3d/items/"


class Server:
    """Fake STAC API: every edition and tile, each with a 0.5 m and a 2 m GeoTIFF asset."""

    def __init__(self):
        self.item_requests, self.fetches = [], []

    @staticmethod
    def body(name):
        return f"bytes of {name}".encode()

    def fetch_json(self, url):
        self.item_requests.append(url)
        item_id = url.removeprefix(STAC_ITEMS)
        assets = {}
        for resolution in ("0.5", "2"):
            name = f"{item_id}_{resolution}_2056_5728.tif"
            assets[name] = {
                "href": f"https://files.example/{name}",
                "file:checksum": "1220" + hashlib.sha256(self.body(name)).hexdigest(),
            }
        return {"id": item_id, "assets": assets}

    def fetch_file(self, url, dest):
        self.fetches.append(url)
        dest.write_bytes(self.body(url.rsplit("/", 1)[1]))


def _run(out_root, datasets=None, world=None):
    server = Server()
    entries = download_terrain(
        world or load_world(),
        datasets or load_datasets(),
        out_root,
        fetch_json=server.fetch_json,
        fetch_file=server.fetch_file,
    )
    return server, entries


def _with(**changes):
    datasets = load_datasets()
    datasets["swissalti3d"] = dict(datasets["swissalti3d"], **changes)
    return datasets


def test_items_are_requested_by_id_at_the_pinned_edition(tmp_path):
    server, _ = _run(tmp_path)
    assert server.item_requests == [STAC_ITEMS + f"swissalti3d_2024_{tile}" for tile in TILES]
    assert server.fetches == [
        f"https://files.example/swissalti3d_2024_{tile}_0.5_2056_5728.tif" for tile in TILES
    ]


def test_edition_and_resolution_come_from_the_config(tmp_path):
    server, entries = _run(tmp_path, _with(edition="2019", resolution_m=2.0))
    assert server.item_requests == [STAC_ITEMS + f"swissalti3d_2019_{tile}" for tile in TILES]
    assert [e["file"] for e in entries] == [
        f"swissalti3d_2019_{tile}_2_2056_5728.tif" for tile in TILES
    ]
    out = tmp_path / "swissalti3d" / "2019"
    assert sorted(p.name for p in out.iterdir()) == sorted(
        [e["file"] for e in entries] + ["provenance.json"]
    )
    assert json.loads((out / "provenance.json").read_bytes())["edition"] == "2019"


def test_tiles_follow_the_village_box_in_the_world_config(tmp_path):
    data = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    data["areas"]["village"] = {
        "e_min": 2623500.0,
        "e_max": 2624000.5,
        "n_min": 1095999.0,
        "n_max": 1096000.0,
    }
    config = tmp_path / "world.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    world = load_world(config)
    expected = ["2623-1095", "2624-1095"]
    assert village_tiles(world) == expected  # every tile the box touches, none it does not
    _, entries = _run(tmp_path / "out", world=world)
    assert [e["tile"] for e in entries] == expected


def test_provenance_bytes_are_sorted_utf8_json_with_lf_and_no_times(tmp_path):
    _, entries = _run(tmp_path)
    raw = (tmp_path / "swissalti3d" / "2024" / "provenance.json").read_bytes()
    assert b"\r" not in raw and raw.endswith(b"}\n")
    provenance = json.loads(raw)
    assert raw == (
        json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    assert "© swisstopo".encode() in raw
    assert provenance["attribution"] == "© swisstopo"
    assert provenance["collection"] == "ch.swisstopo.swissalti3d"
    assert provenance["edition"] == "2024"
    assert provenance["resolution_m"] == 0.5
    assert provenance["tiles"] == entries
    assert not re.search(rb"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", raw)  # no timestamps
    for entry in entries:
        assert entry["size_bytes"] == len(Server.body(entry["file"]))
        assert entry["url"] == f"https://files.example/{entry['file']}"


def test_provenance_does_not_depend_on_where_it_is_written(tmp_path):
    _run(tmp_path / "one")
    _run(tmp_path / "deeper" / "two")
    one = (tmp_path / "one" / "swissalti3d" / "2024" / "provenance.json").read_bytes()
    two = (tmp_path / "deeper" / "two" / "swissalti3d" / "2024" / "provenance.json").read_bytes()
    assert one == two
    assert str(tmp_path).encode() not in one
    provenance = json.loads(one)
    names = [provenance[k] for k in ("attribution", "collection", "dataset", "edition")]
    names += [e[k] for e in provenance["tiles"] for k in ("file", "item", "sha256", "tile")]
    assert not [name for name in names if "/" in name or "\\" in name]  # no paths, only names


def test_a_second_run_fetches_nothing_and_rewrites_identical_bytes(tmp_path):
    _run(tmp_path)
    out = tmp_path / "swissalti3d" / "2024"
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    server, _ = _run(tmp_path)
    assert server.fetches == []
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before
