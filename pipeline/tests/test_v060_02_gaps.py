"""Guards of brief v0.6.0-02 the pinned tests leave open (decision 8; the batch gate's prover).

The pinned copies run `download regio` against the committed config/surroundings.json, whose
(20000, 50) any hard-coded copy reproduces, and every pinned test that varies the config is
refused by the lock's fit before the download reads anything of its own. This file closes
what they leave, by the class and not by the instance (lesson 9): a guard of the regio flow
that a second, independent read of the same thing could break unseen.

- *The download's own read of the config* (the prover's X4, finding R1). A run reads the
  surroundings config twice: the fit's (`lock._regio_ids`) and the download's, for the items it
  asks swisstopo about (`_download_tiles`). A lock that fits a changed config (a margin of 0,
  a spacing of 4000 m, a margin of 30000 m: 2, 36 and 56 tiles; the stand-in serves the 56) must
  be downloaded in full: exactly its tiles fetched, listed in provenance.json and counted, so
  neither number hard-coded, nor halved, nor swapped, nor the area taken as the village, can
  fetch only the committed config's 30 (a subset of the larger locks, which the lock comparison
  lets through) or fail with a KeyError. Brief v0.6.0-07 gives the tile rule one home; until
  then these tests are what holds the two reads together.
- *The republish comparison is the name and the SHA-256* (X3a): a tile published under another
  file name with the same bytes is refused as a republish, word for word.
- *Files go through a `.part`* (X37): every file is fetched into `<name>.part` beside its
  final name, which does not exist until the part is verified.
- *provenance.json goes before a change on disk* (X1b, and X1a with it): a missing tile
  and a damaged one that cannot be fetched again leave no provenance.json (it would list a file
  this run changed), a damaged file is not left under its name, and the rerun restores both.

Closed elsewhere (no test here): the datetime of an item checked to the month and not the year
(X23) is `test_m4_01_lock_regio.py` and `test_v060_01_gaps.py`, through the same
`_published_asset`; the others the prover named are equivalent mutants.

Run as the owner runs them, against the local stand-in (local_regio.py, real urllib) through
`python -m mattini download regio`, except the area test, which calls `download.download_regio`
with a world that has a second area.

Does NOT prove: that the files hold what the surroundings step reads (brief v0.6.0-04); that
the two reads cannot drift in a way these three configs and one second area do not show; a
real cut of a real swisstopo transfer.
"""

import json

import pytest
from local_regio import REGIO, RING_TILES, TILE_E, VILLAGE_TILES, LocalRegio, regio_name
from local_swisstopo import STAC, sha256

import mattini.__main__ as cli
from mattini import download, lock
from mattini.datasets import load_datasets
from mattini.world import REPO, load_world

FOLDER = "swissaltiregio/2026-06"
COMMITTED_CONFIG = REPO / "config" / "surroundings.json"
CUT = 100
HERE = (2_606_000.0, 2_616_000.0, 1_095_000.0, 1_096_000.0)  # a second area: two tiles
HERE_TILES = ["2605-1094", "2615-1094"]  # at margin 0 and spacing 100, east outer
# What each changed village config asks for (measured, the stand-in serves all of them):
CONFIGS = {
    "margin 0": ({"margin_m": 0}, ["2615-1094", "2625-1094"]),
    "spacing 4000": (
        {"spacing_m": 4000},
        sorted(VILLAGE_TILES + [f"{e}-1064" for e in TILE_E]),  # the row N 1064 added
    ),
    "margin 30000": ({"margin_m": 30000}, sorted(VILLAGE_TILES + RING_TILES)),
}


@pytest.fixture
def regio(monkeypatch, tmp_path):
    """The stand-in of test_v060_02_download_regio.py, with a lock pinning what it publishes."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalRegio()
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    site.lock_path = tmp_path / "config" / "datasets.lock.json"
    site.lock_path.parent.mkdir()
    site.pinned = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    site.pinned["datasets"]["swissaltiregio"] = site.regio_entry()
    site.lock_path.write_text(json.dumps(site.pinned, indent=2, sort_keys=True), "utf-8")
    monkeypatch.setattr(lock, "LOCK_PATH", site.lock_path)
    site.out = tmp_path / "raw"
    yield site
    site.close()


def _pin(site, tiles):
    """Rewrite the lock so its swissaltiregio entry pins exactly `tiles`, as published now."""
    entry = site.regio_entry()
    entry["tiles"] = {
        tile: {"file": regio_name(tile), "sha256": sha256(site.bodies[regio_name(tile)])}
        for tile in tiles
    }
    site.pinned["datasets"]["swissaltiregio"] = entry
    site.lock_path.write_text(json.dumps(site.pinned, indent=2, sort_keys=True), "utf-8")


def _config(tmp_path, change):
    """A copy of the committed config/surroundings.json with the village's settings changed."""
    data = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    data["areas"]["village"].update(change)
    path = tmp_path / "surroundings.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _download(site, capsys):
    code = cli.main(["download", "regio", "--out", str(site.out)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _error(err):
    """The refusal: stderr from its `mattini: error:` line on (progress lines come first)."""
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :].rstrip("\n")


def _names(folder):
    return sorted(p.name for p in folder.iterdir())


# ---------------------------------------------- the download's own read of the config (R1)


@pytest.mark.parametrize("case", CONFIGS)
def test_download_regio_fetches_exactly_the_tiles_a_changed_config_asks_for(
    regio, capsys, monkeypatch, tmp_path, case
):
    change, tiles = CONFIGS[case]
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", _config(tmp_path, change))
    _pin(regio, tiles)
    world, datasets = load_world(), load_datasets()
    fit = lock.fit_problem(regio.pinned, datasets, world, "village", "swissaltiregio")
    assert fit is None, fit  # the lock fits this config: the download is the only thing left

    code, out, err = _download(regio, capsys)
    folder = regio.out / FOLDER
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    urls = [regio.base + regio.file_path(regio_name(tile)) for tile in tiles]
    assert err.splitlines() == [f"fetching {url}" for url in urls] + [
        f"{len(tiles)} tiles verified, {len(tiles)} fetches"
    ]
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    assert [entry["tile"] for entry in provenance["tiles"]] == tiles
    assert _names(folder) == sorted([regio_name(tile) for tile in tiles] + ["provenance.json"])
    assert [r for r in regio.file_requests() if r[0] == "GET"] == [
        ("GET", regio.file_path(regio_name(tile)), None) for tile in tiles
    ]


def test_download_regio_follows_the_area_it_is_given(regio, monkeypatch, tmp_path):
    data = json.loads((REPO / "config" / "world.json").read_text(encoding="utf-8"))
    data["areas"]["here"] = dict(zip(("e_min", "e_max", "n_min", "n_max"), HERE, strict=True))
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    areas = {
        "village": {"margin_m": 20000, "spacing_m": 50},
        "here": {"margin_m": 0, "spacing_m": 100},  # not the village's
    }
    config = tmp_path / "surroundings_here.json"
    config.write_text(json.dumps({"schema": 2, "areas": areas}, indent=2), encoding="utf-8")
    monkeypatch.setattr(download, "SURROUNDINGS_PATH", config)
    _pin(regio, HERE_TILES)

    entries = download.download_regio(
        load_world(world_path),
        load_datasets(),
        regio.out,
        download.urllib_fetch_json,
        download.urllib_fetch_file,
        lock=regio.pinned,
        area="here",
    )
    assert [entry["tile"] for entry in entries] == HERE_TILES
    assert _names(regio.out / FOLDER) == sorted(
        [regio_name(tile) for tile in HERE_TILES] + ["provenance.json"]
    )


# ------------------------------------------------- the republish comparison is name and bytes


def test_a_tile_published_under_another_name_with_the_same_bytes_is_refused(regio, capsys):
    tile = VILLAGE_TILES[7]
    name = regio_name(tile)
    other = f"swissaltiregio_{tile}_v2_2056_5728.xyz.zip"
    digest = sha256(regio.bodies[name])
    key = STAC.format(collection=REGIO, item_id=f"swissaltiregio_{tile}")
    with regio.lock:
        body, content_type, host_sha256 = regio.routes[key]
        item = json.loads(body)
        item["assets"] = {other: item["assets"][name]}  # the same href, the same checksum
        regio.routes[key] = (json.dumps(item).encode(), content_type, host_sha256)

    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, "")
    assert _error(err) == (
        f"mattini: error: tile {tile} of area 'village': swisstopo now publishes {other} with "
        f"SHA-256 {digest}, the tile lock pins {name} with SHA-256 {digest}; nothing was "
        f"fetched. A republished tile is adopted only on purpose: `python -m mattini lock "
        f"regio`, then commit the lock, then design recomputes the expected values in "
        f"config/surroundings.json (docs/SPEC.md §8)"
    )
    assert regio.file_requests() == []
    assert not (regio.out / FOLDER).exists()


# ------------------------------------------------------------- every file goes through a part


def test_every_file_is_fetched_into_a_part_beside_its_name(regio, capsys, monkeypatch):
    folder = regio.out / FOLDER
    fetch = download.urllib_fetch_file
    seen = []

    def watch(url, dest):
        """What the fetcher is handed: the part, with the final name not there before or after."""
        final = dest.with_name(dest.name.removesuffix(".part"))
        before = (dest.exists(), final.exists())
        fetch(url, dest)
        seen.append((dest.parent, dest.name, before, (dest.is_file(), final.exists())))

    monkeypatch.setattr(download, "urllib_fetch_file", watch)
    code, _, err = _download(regio, capsys)
    assert code == 0, err
    assert seen == [
        (folder, regio_name(tile) + ".part", (False, False), (True, False))
        for tile in VILLAGE_TILES
    ]
    assert _names(folder) == sorted(
        [regio_name(tile) for tile in VILLAGE_TILES] + ["provenance.json"]
    )


# --------------------------------------------- provenance.json goes before a change on disk


def test_a_missing_tile_that_cannot_be_fetched_leaves_no_provenance_and_a_rerun_heals(
    regio, capsys
):
    assert _download(regio, capsys)[0] == 0
    folder = regio.out / FOLDER
    provenance = folder / "provenance.json"
    written = provenance.read_bytes()
    name = regio_name(VILLAGE_TILES[9])
    (folder / name).unlink()
    regio.script[regio.file_path(name)] = [("cut", CUT), ("cut", CUT)]

    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, ""), err
    assert "cut at" in _error(err), err
    assert not provenance.exists()  # it would list a file that is not there
    assert _names(folder) == sorted(
        regio_name(tile) for tile in VILLAGE_TILES if regio_name(tile) != name
    )

    code, out, err = _download(regio, capsys)  # the rerun the message asks for
    assert (code, out) == (0, f"{provenance}\n"), err
    assert (folder / name).read_bytes() == regio.bodies[name]
    assert provenance.read_bytes() == written


def test_a_damaged_tile_that_cannot_be_fetched_is_not_left_under_its_name(regio, capsys):
    assert _download(regio, capsys)[0] == 0
    folder = regio.out / FOLDER
    provenance = folder / "provenance.json"
    written = provenance.read_bytes()
    name = regio_name(VILLAGE_TILES[21])
    (folder / name).write_bytes(b"damaged")
    regio.script[regio.file_path(name)] = [("cut", CUT), ("cut", CUT)]

    code, out, err = _download(regio, capsys)
    assert (code, out) == (1, ""), err
    assert "cut at" in _error(err), err
    assert not provenance.exists()  # it would list a file this run removed
    assert not (folder / name).exists()  # stale or damaged: never left looking valid
    assert not list(folder.glob("*.part"))

    code, out, err = _download(regio, capsys)
    assert (code, out) == (0, f"{provenance}\n"), err
    assert (folder / name).read_bytes() == regio.bodies[name]
    assert provenance.read_bytes() == written
