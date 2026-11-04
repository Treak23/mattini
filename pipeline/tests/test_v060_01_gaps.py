"""Guards of brief v0.6.0-01 the pinned tests leave open (decision 9; the batch gate's prover).

The pinned copies state what swissALTIRegio's lock must do for the village. They leave open
what the same code must do for any other area, any other config and any other dataset's
twin; this file closes those, by the class and not by the instance (lesson 9):

- the area is the one asked for, never the village: the config's lookup
  (`download.surroundings_margin_spacing`), `regio_tiles`, `published_regio`,
  `lock.regio_entry` and `lock regio` all follow `config/terrain.json`'s area, with a second
  area in the world, the surroundings config and the items;
- `margin_m` and `spacing_m` reach the tile rule, an odd spacing keeps its half metre, the
  lookup reads nothing but the area's two numbers, and the config's one reader
  (`surroundings.load_surroundings_config`) refuses a boolean for a whole number of metres
  and what is not UTF-8 JSON, whatever its top level, naming the file;
- every tile item is checked the way `_published_asset` checks it for the other datasets (the
  item's id, exactly one asset ending `_2056_5728.xyz.zip`, a plain name, an href, a SHA-256
  multihash), and its `properties.datetime` must be a text in the pinned edition: a missing
  or wrong-typed one is refused naming the tile, the edition and what was found, never
  locked and never a KeyError; the refusal names the area and the item's URL;
- `collection`, in the URLs asked and in the entry, is the datasets config's;
- a lock that cannot be read ends every `lock` command before swisstopo is asked anything
  (the order in `__main__._lock`), for each lock command, not only for the dataset whose
  command the pins run;
- `validate_lock`'s field checks (collection, edition, resolution, the parts' ids and their
  file names and checksums) hold for every dataset the lock knows, swissALTIRegio included;
- the parser offers `download` exactly the datasets `_download` serves and `lock` exactly
  the lock commands, and each help names every choice its command takes and no other (the
  literal "regio is not a `download` choice" is brief v0.6.0-02's to retire, so it is
  stated here as that rule); the docstrings that count the lock's commands count them
  right and name every choice;
- the Release notes' credit lines sit once each in the credits' code block, swissALTIRegio's
  directly after swissALTI3D's (decision 5).

Re-cut by brief v0.6.0-07 onto the config's one reader: brief v0.6.0-01's small reader in
download.py (`download.surroundings_settings`, `download.SURROUNDINGS_PATH`) is gone, the
callers are given the config (`surroundings=`), and the command line reads it through
`surroundings.load_surroundings_config`, which the tests replace on its module.

Does NOT prove: that the live STAC API serves these items (the network test), the download
(brief v0.6.0-02), the heights (brief v0.6.0-04); and the docstring and template checks
prove text, never what the code does (lesson 5): they are the Tier-1 reviewer's reading,
written down.
"""

import copy
import hashlib
import inspect
import json
import math
import re
import shutil
import urllib.error
from types import SimpleNamespace

import pytest
from test_release_notes import TEMPLATE, _dataset_lines

import mattini.__main__ as cli
from mattini import datasets as datasets_module
from mattini import download, lock, surroundings, terrain
from mattini.datasets import load_datasets
from mattini.surroundings import SurroundingsError
from mattini.world import REPO, load_world

REGIO = download.REGIO
COMMITTED_LOCK_PATH = REPO / "config" / "datasets.lock.json"
COMMITTED_LOCK = json.loads(COMMITTED_LOCK_PATH.read_text(encoding="utf-8"))
COMMITTED_SURROUNDINGS = REPO / "config" / "surroundings.json"
DATASETS = load_datasets()
COLLECTION = DATASETS[REGIO]["collection"]
EDITION = DATASETS[REGIO]["edition"]
DATETIME = "2026-06-01T00:00:00Z"
HERE = (2_606_000.0, 2_616_000.0, 1_095_000.0, 1_096_000.0)  # another area: two tiles
HERE_TILES = ["2605-1094", "2615-1094"]  # at margin 0 and spacing 100, east outer
HERE_SETTINGS = (0, 100)
VILLAGE_SETTINGS = (20000, 50)  # what the village's entry says: the world's other area


# ------------------------------------------------------------------------- the stand-ins


def _sha(tile):
    return hashlib.sha256(tile.encode()).hexdigest()


def regio_item(tile, *, datetime=DATETIME):
    """The STAC item of a tile as live serves it (one asset, a `1220` + upper-case checksum)."""
    item_id = f"swissaltiregio_{tile}"
    name = f"{item_id}_2056_5728.xyz.zip"
    return {
        "id": item_id,
        "collection": COLLECTION,
        "properties": {"datetime": datetime},
        "assets": {
            name: {
                "href": f"https://data.example/{name}",
                "file:checksum": "1220" + _sha(tile).upper(),
            }
        },
    }


class Stac:
    """A `fetch_json` serving the swissALTIRegio items of `tiles`; `asked` logs every URL."""

    def __init__(self, tiles):
        self.items = {f"swissaltiregio_{tile}": regio_item(tile) for tile in tiles}
        self.asked = []

    def __call__(self, url):
        self.asked.append(url)
        item_id = url.rsplit("/", 1)[1]
        if item_id not in self.items:
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)
        return copy.deepcopy(self.items[item_id])

    def asked_ids(self):
        return [url.rsplit("/", 1)[1] for url in self.asked]


def _world(tmp_path, box=HERE):
    """The committed world plus a second area, `here`: the village is never the only one."""
    data = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    data["areas"]["here"] = dict(zip(("e_min", "e_max", "n_min", "n_max"), box, strict=True))
    path = tmp_path / "world.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return load_world(path)


def _surroundings(here=HERE_SETTINGS, village=VILLAGE_SETTINGS):
    """A surroundings config (as the reader returns it, here without the step's other keys) with
    the village's settings and `here`'s, which differ."""
    areas = {
        "village": {"margin_m": village[0], "spacing_m": village[1]},
        "here": {"margin_m": here[0], "spacing_m": here[1]},
    }
    return {"schema": 2, "areas": areas}


def _given(area, margin_m, spacing_m):
    """The config of one area with the two numbers: what `published_regio` is given."""
    return {"areas": {area: {"margin_m": margin_m, "spacing_m": spacing_m}}}


def _config(tmp_path, change=None, *, raw=None):
    """A copy of the committed config/surroundings.json with the village's settings changed."""
    path = tmp_path / "surroundings.json"
    if raw is not None:
        path.write_bytes(raw)
        return path
    data = json.loads(COMMITTED_SURROUNDINGS.read_text(encoding="utf-8"))
    if change is not None:
        change(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _published(world, stac, *, datasets=DATASETS, margin_m=0, spacing_m=100):
    return download.published_regio(
        world, datasets, stac, area="here", surroundings=_given("here", margin_m, spacing_m)
    )


def _refusal(call):
    with pytest.raises(download.DownloadError) as refusal:
        call()
    return str(refusal.value)


def _reader_refusal(path):
    """What the config's one reader says about a file it refuses."""
    with pytest.raises(SurroundingsError) as refusal:
        surroundings.load_surroundings_config(path)
    return str(refusal.value)


# --------------------------------------------------------- the area is the one asked for


def test_the_lookup_gives_the_area_asked_for_and_never_falls_back_to_another():
    config = _surroundings()
    assert download.surroundings_margin_spacing(config, "here") == HERE_SETTINGS
    assert download.surroundings_margin_spacing(config, "village") == VILLAGE_SETTINGS
    text = _refusal(lambda: download.surroundings_margin_spacing(config, "elsewhere"))
    assert "config/surroundings.json" in text and "'elsewhere'" in text, text


def test_the_lookup_reads_nothing_else_of_the_config():
    config = {
        "schema": 99,
        "areas": {
            "village": {"margin_m": 7, "spacing_m": 3, "computed_for": 1, "colour": []},
            "other": "garbage",
        },
        "colour": 5,
        "anything": [1],
    }
    assert download.surroundings_margin_spacing(config, "village") == (7, 3)


def test_published_regio_follows_the_area_it_is_given(tmp_path):
    world = _world(tmp_path)
    stac = Stac(HERE_TILES)  # only these: another area's tiles would be a refused 404
    published = _published(world, stac)
    assert [asset.tile for asset in published] == HERE_TILES
    assert stac.asked_ids() == [f"swissaltiregio_{tile}" for tile in HERE_TILES]


def test_the_entry_follows_the_area_it_is_given(tmp_path):
    entry = lock.regio_entry(
        _world(tmp_path), DATASETS, Stac(HERE_TILES), area="here", surroundings=_surroundings()
    )
    assert list(entry["tiles"]) == HERE_TILES


@pytest.fixture
def env(monkeypatch, tmp_path):
    """`python -m mattini lock …` for the area `here`, the village beside it in every config."""
    world = _world(tmp_path)
    stac = Stac(HERE_TILES)
    lock_path = tmp_path / "datasets.lock.json"
    shutil.copyfile(COMMITTED_LOCK_PATH, lock_path)
    monkeypatch.setattr(lock, "LOCK_PATH", lock_path)
    config = _surroundings()
    monkeypatch.setattr(surroundings, "load_surroundings_config", lambda *a, **k: config)
    monkeypatch.setattr(download, "urllib_fetch_json", stac)
    monkeypatch.setattr(terrain, "load_terrain_config", lambda *a, **k: {"areas": {"here": {}}})
    monkeypatch.setattr(cli, "load_world", lambda *a, **k: world)
    return SimpleNamespace(world=world, stac=stac, lock_path=lock_path)


def _run(capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_lock_regio_locks_the_area_the_terrain_config_names(env, capsys):
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (0, f"{env.lock_path}\n"), err
    written = json.loads(env.lock_path.read_bytes())["datasets"]
    assert list(written[REGIO]["tiles"]) == HERE_TILES  # not the village's 30
    assert env.stac.asked_ids() == [f"swissaltiregio_{tile}" for tile in HERE_TILES]
    kept = {name: entry for name, entry in COMMITTED_LOCK["datasets"].items() if name != REGIO}
    assert {name: entry for name, entry in written.items() if name != REGIO} == kept


def test_lock_regio_refuses_a_tile_naming_the_area_the_terrain_config_names(env, capsys):
    del env.stac.items["swissaltiregio_2615-1094"]
    before = env.lock_path.read_bytes()
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (1, "")
    assert "tile 2615-1094 of area 'here'" in err and "cannot read the STAC item" in err, err
    assert env.lock_path.read_bytes() == before


def test_lock_regio_refuses_an_area_the_surroundings_config_lacks(env, capsys, monkeypatch):
    only_the_village = {"areas": {"village": {"margin_m": 20000, "spacing_m": 50}}}
    monkeypatch.setattr(surroundings, "load_surroundings_config", lambda *a, **k: only_the_village)
    before = env.lock_path.read_bytes()
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (1, "")
    assert "config/surroundings.json" in err and "'here'" in err, err
    assert env.stac.asked == [] and env.lock_path.read_bytes() == before


# --------------------------------------------------- margin_m, spacing_m and the tile rule

PAIRS = [(0, 100), (0, 30_000), (20_000, 50), (10_000, 20_000), (3_000, 100)]


def test_the_pairs_below_lock_different_tiles():
    world = load_world()
    tiles = [
        tuple(download.regio_tiles(world, "village", margin_m=m, spacing_m=s)) for m, s in PAIRS
    ]
    assert len(set(tiles)) == len(PAIRS), tiles  # so that a test of one pair cannot pass for all


@pytest.mark.parametrize(("margin_m", "spacing_m"), PAIRS)
def test_published_regio_asks_for_exactly_the_tiles_of_its_margin_and_spacing(margin_m, spacing_m):
    world = load_world()
    tiles = download.regio_tiles(world, "village", margin_m=margin_m, spacing_m=spacing_m)
    stac = Stac(tiles)
    published = download.published_regio(
        world, DATASETS, stac, area="village", surroundings=_given("village", margin_m, spacing_m)
    )
    assert [asset.tile for asset in published] == tiles
    assert stac.asked_ids() == [f"swissaltiregio_{tile}" for tile in tiles]


@pytest.mark.parametrize(("margin_m", "spacing_m"), PAIRS)
def test_the_entry_locks_exactly_the_tiles_of_its_margin_and_spacing(margin_m, spacing_m):
    world = load_world()
    tiles = download.regio_tiles(world, "village", margin_m=margin_m, spacing_m=spacing_m)
    entry = lock.regio_entry(
        world,
        DATASETS,
        Stac(tiles),
        area="village",
        surroundings=_given("village", margin_m, spacing_m),
    )
    assert list(entry["tiles"]) == tiles


@pytest.mark.parametrize("spacing_m", [51, 101, 1001])
def test_an_odd_spacing_keeps_its_half_metre(tmp_path, spacing_m):
    half = (spacing_m - 1) // 2  # the whole metres of the half spacing; a half metre is left
    # each edge lies half a metre short of reaching the next tile, unless the half metre counts
    box = (2_615_000.0 + half, 2_625_000.0 - half, 1_094_000.0 + half, 1_104_000.0 - half)
    world = _world(tmp_path, box)
    expected = [f"{e}-{n}" for e in (2605, 2615, 2625) for n in (1084, 1094, 1104)]
    assert download.regio_tiles(world, "here", margin_m=0, spacing_m=spacing_m) == expected


@pytest.mark.parametrize(
    ("key", "value"), [("margin_m", True), ("margin_m", False), ("spacing_m", True)]
)
def test_a_boolean_is_not_a_whole_number_of_metres(tmp_path, key, value):
    path = _config(tmp_path, lambda d: d["areas"]["village"].update({key: value}))
    text = _reader_refusal(path)
    assert str(path) in text and key in text, text


@pytest.mark.parametrize(
    "raw",
    [
        b"[]",
        b'[{"areas": {"village": {"margin_m": 20000, "spacing_m": 50}}}]',
        b'"text"',
        b"null",
        b"42",
        b'{"areas": []}',
        b'{"areas": null}',
        b'{"areas": {"village": null}}',
        json.dumps({"areas": {"village": {"margin_m": 20000, "spacing_m": 50}}}).encode("utf-16"),
        b"\x00\x00\x00",
    ],
)
def test_a_config_that_is_not_utf_8_json_with_the_area_is_refused_naming_the_file(tmp_path, raw):
    path = _config(tmp_path, raw=raw)
    text = _reader_refusal(path)
    assert str(path) in text, text


# --------------------------------------------------------------- the items, one by one


def _two_assets(item):
    (asset,) = item["assets"].values()
    item["assets"]["swissaltiregio_extra_2056_5728.xyz.zip"] = dict(asset)


def _rename_asset(new_suffix):
    def change(item):
        ((name, asset),) = item["assets"].items()
        item["assets"] = {name.replace("_2056_5728.xyz.zip", new_suffix): asset}

    return change


def _asset(item):
    return next(iter(item["assets"].values()))


DAMAGE = {
    "another id": (lambda i: i.update(id="swissaltiregio_2625-1104"), "expected the STAC item"),
    "no id": (lambda i: i.pop("id"), "expected the STAC item"),
    "no assets": (lambda i: i.pop("assets"), "has no assets"),
    "assets a list": (lambda i: i.update(assets=[]), "has no assets"),
    "two xyz zips": (_two_assets, "exactly one asset"),
    "no xyz zip": (_rename_asset(".tif"), "exactly one asset"),
    "a gdb zip": (_rename_asset("_2056_5728.gdb.zip"), "exactly one asset"),
    "an xyz zip of another projection": (_rename_asset("_2056.xyz.zip"), "exactly one asset"),
    "no plain name": (
        lambda i: i.update(assets={"../swissaltiregio_x_2056_5728.xyz.zip": _asset(i)}),
        "plain file name",
    ),
    "no href": (lambda i: _asset(i).pop("href"), "has no href"),
    "empty href": (lambda i: _asset(i).update(href=""), "has no href"),
    "no checksum": (lambda i: _asset(i).pop("file:checksum"), "multihash"),
    "a checksum of another hash": (
        lambda i: _asset(i).update({"file:checksum": "1114" + "AB" * 32}),
        "multihash",
    ),
    "a short checksum": (
        lambda i: _asset(i).update({"file:checksum": "1220" + "AB" * 31}),
        "multihash",
    ),
}


@pytest.mark.parametrize("damage", sorted(DAMAGE))
def test_a_damaged_item_is_refused_naming_the_tile_the_area_and_the_url(tmp_path, damage):
    change, complaint = DAMAGE[damage]
    stac = Stac(HERE_TILES)
    change(stac.items["swissaltiregio_2615-1094"])
    text = _refusal(lambda: _published(_world(tmp_path), stac))
    url = download.STAC_ITEM.format(collection=COLLECTION, item_id="swissaltiregio_2615-1094")
    assert "tile 2615-1094 of area 'here'" in text, text
    assert url in text and complaint in text, text


def test_an_asset_that_is_not_the_xyz_zip_beside_it_is_not_the_file(tmp_path):
    stac = Stac(HERE_TILES)
    item = stac.items["swissaltiregio_2615-1094"]
    item["assets"]["swissaltiregio_2615-1094.tif"] = {
        "href": "https://data.example/decoy.tif",
        "file:checksum": "1220" + "00" * 32,
    }
    published = _published(_world(tmp_path), stac)
    assert published[1].name == "swissaltiregio_2615-1094_2056_5728.xyz.zip"
    assert published[1].sha256 == _sha("2615-1094")


BAD_STAMPS = {
    "no properties": (lambda i: i.pop("properties"), None),
    "properties null": (lambda i: i.update(properties=None), None),
    "properties a list": (lambda i: i.update(properties=["2026-06-01T00:00:00Z"]), None),
    "no datetime": (lambda i: i["properties"].pop("datetime"), None),
    "datetime null": (lambda i: i["properties"].update(datetime=None), None),
    "datetime a number": (lambda i: i["properties"].update(datetime=20260601), 20260601),
    "datetime empty": (lambda i: i["properties"].update(datetime=""), ""),
    "a month without its day": (lambda i: i["properties"].update(datetime="2026-06"), "2026-06"),
    "a longer month": (lambda i: i["properties"].update(datetime="2026-061-01"), "2026-061-01"),
    "another month": (
        lambda i: i["properties"].update(datetime="2026-07-01T00:00:00Z"),
        "2026-07-01T00:00:00Z",
    ),
    "another year": (
        lambda i: i["properties"].update(datetime="2025-06-01T00:00:00Z"),
        "2025-06-01T00:00:00Z",
    ),
}


@pytest.mark.parametrize("damage", sorted(BAD_STAMPS))
def test_an_item_without_a_datetime_in_the_edition_is_refused_naming_what_was_found(
    tmp_path, damage
):
    change, found = BAD_STAMPS[damage]
    stac = Stac(HERE_TILES)
    change(stac.items["swissaltiregio_2615-1094"])
    text = _refusal(lambda: _published(_world(tmp_path), stac))
    assert "tile 2615-1094 of area 'here'" in text, text
    assert repr(found) in text and repr(EDITION) in text, text


@pytest.mark.parametrize("stamp", ["2026-06-01T00:00:00Z", "2026-06-30T23:59:59Z", "2026-06-15"])
def test_any_day_of_the_pinned_month_is_in_the_edition(tmp_path, stamp):
    stac = Stac(HERE_TILES)
    stac.items["swissaltiregio_2615-1094"]["properties"]["datetime"] = stamp
    assert [a.tile for a in _published(_world(tmp_path), stac)] == HERE_TILES


@pytest.mark.parametrize("damage", ["no properties", "datetime null", "a month without its day"])
def test_lock_regio_writes_nothing_for_an_item_without_an_edition(env, capsys, damage):
    BAD_STAMPS[damage][0](env.stac.items["swissaltiregio_2615-1094"])
    before = env.lock_path.read_bytes()
    code, out, err = _run(capsys, "lock", "regio")
    assert (code, out) == (1, "")
    assert err.startswith("mattini: error: tile 2615-1094 of area 'here'"), err
    assert "Traceback" not in err and repr(EDITION) in err, err
    assert env.lock_path.read_bytes() == before


def test_the_collection_is_the_datasets_config_s_in_the_urls_asked_and_in_the_entry(tmp_path):
    datasets = copy.deepcopy(DATASETS)
    datasets[REGIO]["collection"] = "ch.swisstopo.swissaltiregio-another"
    stac = Stac(HERE_TILES)
    entry = lock.regio_entry(
        _world(tmp_path), datasets, stac, area="here", surroundings=_surroundings()
    )
    assert entry["collection"] == "ch.swisstopo.swissaltiregio-another"
    assert stac.asked == [
        download.STAC_ITEM.format(
            collection="ch.swisstopo.swissaltiregio-another", item_id=f"swissaltiregio_{tile}"
        )
        for tile in HERE_TILES
    ]


# ------------------------------------------- a lock that cannot be read: before any request

BAD_LOCKS = {
    "not json": "{not json",
    "empty object": "{}",
    "empty text": "",
    "a regio entry without its resolution": None,  # the committed lock, one key short
}


@pytest.mark.parametrize("damage", sorted(BAD_LOCKS))
@pytest.mark.parametrize("choice", sorted(cli.LOCK_DATASETS))
def test_a_lock_that_cannot_be_read_ends_every_lock_command_before_swisstopo_is_asked(
    env, capsys, choice, damage
):
    text = BAD_LOCKS[damage]
    if text is None:
        data = copy.deepcopy(COMMITTED_LOCK)
        del data["datasets"][REGIO]["resolution_m"]
        text = json.dumps(data, indent=2, sort_keys=True)
    env.lock_path.write_text(text, encoding="utf-8")
    before = env.lock_path.read_bytes()
    code, out, err = _run(capsys, "lock", choice)
    assert (code, out) == (1, "")
    assert err.startswith(f"mattini: error: {env.lock_path}: "), err
    assert env.stac.asked == [] and env.lock_path.read_bytes() == before


# -------------------------------------------- the lock's field checks, for every dataset


def _kind(name):
    keys = lock.DATASET_KEYS[name]
    return "tiles" if "tiles" in keys else "sheets" if "sheets" in keys else None


def _on(name, change):
    """A change to the dataset's entry, applied to the lock's `datasets` object."""

    def apply(datasets):
        change(datasets[name], datasets)

    return apply


def _field_cases():
    for name in lock.DATASET_KEYS:
        if name not in COMMITTED_LOCK["datasets"]:
            continue
        keys = lock.DATASET_KEYS[name]
        for value in ("", 5, None):
            yield (
                name,
                f"collection {value!r}",
                _on(name, lambda e, d, v=value: e.update(collection=v)),
                "collection must be a non-empty string",
            )
        if "edition" in keys:
            for value in ("", 2024, None):
                yield (
                    name,
                    f"edition {value!r}",
                    _on(name, lambda e, d, v=value: e.update(edition=v)),
                    "edition must be a non-empty string",
                )
        if "resolution_m" in keys:
            for value in (0, -1, True, "10", None, math.nan, math.inf):
                yield (
                    name,
                    f"resolution_m {value!r}",
                    _on(name, lambda e, d, v=value: e.update(resolution_m=v)),
                    "resolution_m must be a positive number of metres",
                )
        kind = _kind(name)
        if kind is None:  # swissTLM3D: the one national file, on the entry itself
            yield from _file_cases(name, lambda e: e)
            continue
        singular = kind[:-1]
        for value in ({}, [], None):
            yield (
                name,
                f"{kind} {value!r}",
                _on(name, lambda e, d, v=value, k=kind: e.update({k: v})),
                f"{kind} must be a non-empty object",
            )
        for bad in ("x", "2625-", "-1094", "2625_1094", ""):
            yield (
                name,
                f"{singular} id {bad!r}",
                _on(
                    name, lambda e, d, b=bad, k=kind: e.update({k: {b: next(iter(e[k].values()))}})
                ),
                f"a {singular} id is",
            )
        for label, change in (
            ("an extra key", lambda p: p.update(extra=1)),
            ("no sha256", lambda p: p.pop("sha256")),
            ("no file", lambda p: p.pop("file")),
        ):
            yield (
                name,
                f"{singular} with {label}",
                _on(name, lambda e, d, c=change, k=kind: c(next(iter(e[k].values())))),
                "exactly the keys",
            )
        yield (
            name,
            f"{singular} entry a text",
            _on(name, lambda e, d, k=kind: e[k].update({next(iter(e[k])): "text"})),
            "exactly the keys",
        )
        yield from _file_cases(name, lambda e, k=kind: next(iter(e[k].values())))


def _file_cases(name, part_of):
    for value in ("../x.zip", "a/b.zip", "", None, 5):
        yield (
            name,
            f"file {value!r}",
            _on(name, lambda e, d, v=value: part_of(e).update(file=v)),
            "file must be a plain file name",
        )
    for value in ("AB" * 32, "a" * 63, "a" * 65, "g" * 64, None):
        yield (
            name,
            f"sha256 {value!r}",
            _on(name, lambda e, d, v=value: part_of(e).update(sha256=v)),
            "sha256 must be 64 lower-case hex digits",
        )


FIELD_CASES = list(_field_cases())


def test_the_field_cases_cover_swissaltiregio_and_every_other_dataset_of_the_lock():
    covered = {name for name, *_ in FIELD_CASES}
    assert covered == set(lock.DATASET_KEYS) and REGIO in covered


@pytest.mark.parametrize(
    ("name", "label", "change", "complaint"),
    FIELD_CASES,
    ids=[f"{name}-{label}" for name, label, _, _ in FIELD_CASES],
)
def test_a_malformed_field_is_refused_for_every_dataset_naming_all_the_lock_commands(
    name, label, change, complaint
):
    data = copy.deepcopy(COMMITTED_LOCK)
    change(data["datasets"])
    with pytest.raises(lock.LockError) as refused:
        lock.validate_lock(data, "lock.json")
    message = str(refused.value)
    assert message.startswith("lock.json: ") and complaint in message, message
    assert f"dataset {name!r}" in message, message
    for command in lock.LOCK_COMMANDS:
        assert f"`{command}`" in message, (command, message)


# ------------------------------------------------ what each command line offers and says


def _choices(capsys, command):
    with pytest.raises(SystemExit) as stopped:
        cli.main([command, "nonesuch"])
    assert stopped.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice: 'nonesuch'" in err, err
    listed = err.split("(choose from", 1)[1].split(")", 1)[0]
    return re.findall(r"[a-z]+", listed)


def _dataset_help(capsys, command):
    """The `dataset` argument's own help text: between the usage and the options."""
    with pytest.raises(SystemExit) as stopped:
        cli.main([command, "--help"])
    assert stopped.value.code == 0
    out = capsys.readouterr().out
    return " ".join(out.split("positional arguments:", 1)[1].split("options:", 1)[0].split())


def test_download_offers_what_it_serves_and_lock_offers_the_lock_commands(capsys):
    lock_choices, download_choices = _choices(capsys, "lock"), _choices(capsys, "download")
    assert sorted(download_choices) == sorted(cli.DATASETS), "a choice `_download` cannot serve"
    assert sorted(lock_choices) == sorted(c.rsplit(" ", 1)[1] for c in lock.LOCK_COMMANDS)
    assert set(download_choices) <= set(lock_choices)
    assert set(download.LOCK_COMMAND_OF) == set(lock.DATASET_KEYS)  # one command per entry
    assert "regio" in lock_choices
    if "regio" not in cli.DATASETS:  # brief v0.6.0-02 adds it there, and this ends with it
        assert "regio" not in download_choices


def test_each_help_names_every_choice_its_command_takes_and_no_other(capsys):
    lock_choices, download_choices = _choices(capsys, "lock"), _choices(capsys, "download")
    helped = {"lock": _dataset_help(capsys, "lock"), "download": _dataset_help(capsys, "download")}
    for choice in lock_choices:
        assert re.search(rf"\b{choice}\b", helped["lock"]), (choice, helped["lock"])
    for choice in download_choices:
        assert re.search(rf"\b{choice}\b", helped["download"]), (choice, helped["download"])
    for choice in set(lock_choices) - set(download_choices):
        assert not re.search(rf"\b{choice}\b", helped["download"]), (choice, helped["download"])
    assert "swissALTIRegio" in helped["lock"], helped["lock"]


# --------------------------------------------------- the docstrings that count and name

NUMBERS = {
    word: number
    for number, word in enumerate(
        ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"), start=1
    )
}
COUNTED = re.compile(
    r"\b(" + "|".join(NUMBERS) + r")\s+(?:`?lock`?\s+)?(?:commands|choices|entries)\b"
)


def test_what_the_code_counts_in_words_is_the_number_of_lock_commands():
    counted = []
    for module in (datasets_module, download, lock, cli):
        counted += [NUMBERS[word] for word in COUNTED.findall(inspect.getsource(module))]
    assert counted, "no docstring counts the lock commands: this scan is blind"
    assert set(counted) == {len(lock.LOCK_COMMANDS)}, counted
    assert len(lock.LOCK_COMMANDS) == len(lock.DATASET_KEYS)


def test_the_lock_docstring_names_every_lock_command_and_the_main_one_every_choice():
    for command in lock.LOCK_COMMANDS:
        assert command.split("mattini ", 1)[1] in lock.__doc__, (command, "lock.py")
        choice = command.rsplit(" ", 1)[1]
        assert re.search(rf"\b{choice}\b", cli.__doc__), (choice, "__main__.py")
    assert "swissALTIRegio" in download.__doc__ and "lock regio" in download.__doc__


def test_the_datasets_docstring_lists_every_dataset_read_at_a_resolution():
    listed = re.search(r"`RESOLUTION_DATASETS`: ([^)]*)\)", datasets_module.__doc__)
    assert listed, "the docstring no longer lists `RESOLUTION_DATASETS` in a parenthesis"
    for name in datasets_module.RESOLUTION_DATASETS:
        assert name.split("_")[0] in listed.group(1).lower(), (name, listed.group(1))


# ----------------------------------------------------- the credits in the Release notes


def _credits():
    lines = TEMPLATE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Geodata from the Swiss"))
    opening = next(i for i in range(start, len(lines)) if lines[i] == "```")
    closing = next(i for i in range(opening + 1, len(lines)) if lines[i] == "```")
    return lines, lines[opening + 1 : closing]


def test_each_dataset_line_is_in_the_credits_block_once_and_only_there():
    lines, block = _credits()
    wanted = _dataset_lines()
    # one line per distinct credit (collection, edition, attribution) among the lock's datasets:
    # the rule `_dataset_lines` applies, so a dataset that shares its product's credit (brief
    # v0.6.0-05: swissimage_far) needs no line, and a later one no edit here
    credited = {
        (entry["collection"], entry.get("edition"), entry["attribution"])
        for name, entry in DATASETS.items()
        if name in lock.DATASET_KEYS
    }
    assert len(wanted) == len(credited)
    for line in wanted:
        assert block.count(line) == 1, f"not once in the credits block: {line[:60]}"
        assert lines.count(line) == 1, f"more than once in the notes: {line[:60]}"
    assert sorted(block) == sorted(wanted), "a line in the block is no dataset's"


def test_swissaltiregio_s_credit_follows_swissalti3d_s_directly():
    _, block = _credits()
    (alti,) = [i for i, line in enumerate(block) if line.startswith("swissalti3d ")]
    assert block[alti + 1].startswith("swissaltiregio 2026-06, "), block[alti + 1][:60]
