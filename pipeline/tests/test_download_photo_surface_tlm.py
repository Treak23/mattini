"""Pinning tests for brief M3-03: `download photo`, `download surface`, `download tlm`.

Pinned decisions (docs/SPEC.md §5, §9):

- *Layout.* Under the download root (`--out`, default data/raw): `swissimage/<edition>/`,
  `swisssurface3d/<editions joined by "-">/` (`2021-2022`), `swisstlm3d/<edition>/`, each
  with the files under swisstopo's names and a provenance.json (sorted keys, 2-space
  indent, UTF-8, LF, final newline, no times, no paths), exactly:
  swissimage {attribution, collection, dataset, edition, resolution_m, schema: 1,
  tiles: [{file, item, sha256, size_bytes, tile, url}] in tile order}, as the terrain's;
  swisssurface3d the same with `editions` (the config's list) for `edition` and each tile's
  `edition` added; swisstlm3d flat {attribution, collection, dataset, edition, file, item,
  schema: 1, sha256, size_bytes, url}. The command prints the provenance path on stdout.
- *Checked before anything is fetched.* Every published file name and SHA-256 is compared
  with the lock before any request for a file and before anything on disk changes; a
  difference is refused naming the tile (the TLM's refusals start `swisstlm3d <edition>:`),
  both checksums, "nothing was fetched", the dataset's lock command, "then commit the lock"
  and design's step, the configs whose expected values record the entry: photo →
  config/photo.json and config/roofs.json, surface → config/trees.json, tlm →
  config/surfaces.json and config/trees.json.
- *The surface's edition is the lock's.* `download surface` reads, per tile, the item of
  the edition the lock pins: choosing the edition is `lock surface`'s, so an edition
  swisstopo adds later does not stop a download of the pinned files.
- *The TLM file (2.88 GB).* A verified file already there is kept without any request for
  it. Otherwise one HEAD first: an `x-amz-meta-sha256` that is not the lock's is refused
  before any GET. The file downloads to a part file; a cut transfer is resumed with
  `Range: bytes=<bytes already received>-`, within the run and by the next run (the part
  of a run that fails is kept), and the file takes its name only once its SHA-256 equals
  the lock's.

Run as the owner runs them, `python -m mattini download <x>`, against the local HTTP
stand-in (local_swisstopo.py) through the real urllib code; the lock is written here from
design's expected entries, not by the lock commands.

Likeliest wrong twins, each caught here: a comparison made lazily before each fetch (the
last tile is the republished one); `download surface` choosing the edition again; a HEAD
checksum compared with the upper-case STAC text; a cut transfer fetched again from the
start, or resumed from a wrong offset (the TLM body differs everywhere); a part deleted at
the end of a failed run.

Does NOT prove: a real cut of the real 2.88 GB file (the builder's live run does), nor that
the files hold what M3-04, M3-06 and M3-07 expect (they read them).
"""

import json

import pytest
from local_swisstopo import (
    PHOTO,
    SURFACE,
    SURFACE_YEARS,
    TLM,
    TLM_FILE,
    TLM_ITEM,
    VILLAGE_TILES,
    LocalSwisstopo,
    photo_name,
    sha256,
    surface_name,
)

import mattini.__main__ as cli
from mattini import download, lock
from mattini.world import REPO

FOLDERS = {
    "photo": "swissimage/2023",
    "surface": "swisssurface3d/2021-2022",
    "tlm": "swisstlm3d/2026-02",
}
RECOMPUTE = {
    "photo": "config/photo.json and config/roofs.json",
    "surface": "config/trees.json",
    "tlm": "config/surfaces.json and config/trees.json",
}
CUT = 77_777  # the first transfer of the TLM file stops here (its body is 200'003 bytes)
TLM_WHERE = "mattini: error: swisstlm3d 2026-02: "  # how every TLM refusal starts


@pytest.fixture
def swisstopo(monkeypatch, tmp_path):
    """The stand-in wired into the command line, and a lock pinning what it publishes."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    site = LocalSwisstopo()
    monkeypatch.setattr(download, "STAC_ITEM", site.stac_item)
    site.lock_path = tmp_path / "config" / "datasets.lock.json"
    site.lock_path.parent.mkdir()
    pinned = json.loads((REPO / "config" / "datasets.lock.json").read_bytes())
    pinned["datasets"].update(site.expected_entries())
    site.lock_path.write_text(json.dumps(pinned, indent=2, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(lock, "LOCK_PATH", site.lock_path)
    site.out = tmp_path / "raw"
    yield site
    site.close()


def _run(capsys, *argv):
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _error(err):
    """The refusal: stderr from its `mattini: error:` line on (progress lines come first)."""
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :]


def _download(site, capsys, command):
    return _run(capsys, "download", command, "--out", str(site.out))


def _url(site, name):
    return site.base + site.file_path(name)


def _provenance(site, command):
    """What provenance.json must hold after the stand-in's files are fetched."""
    if command == "tlm":
        return {
            "attribution": "© swisstopo",
            "collection": TLM,
            "dataset": "swisstlm3d",
            "edition": "2026-02",
            "file": TLM_FILE,
            "item": TLM_ITEM,
            "schema": 1,
            "sha256": sha256(site.bodies[TLM_FILE]),
            "size_bytes": len(site.bodies[TLM_FILE]),
            "url": _url(site, TLM_FILE),
        }
    tiles = []
    for tile in VILLAGE_TILES:
        if command == "photo":
            name, item, extra = photo_name(tile), f"swissimage-dop10_2023_{tile}", {}
        else:
            year = SURFACE_YEARS[tile]
            name, item = surface_name(tile, year), f"swisssurface3d-raster_{year}_{tile}"
            extra = {"edition": year}
        body = site.bodies[name]
        tiles.append(
            {
                "file": name,
                "item": item,
                "sha256": sha256(body),
                "size_bytes": len(body),
                "tile": tile,
                "url": _url(site, name),
            }
            | extra
        )
    if command == "photo":
        head = {
            "collection": PHOTO,
            "dataset": "swissimage",
            "edition": "2023",
            "resolution_m": 0.1,
        }
    else:
        head = {"collection": SURFACE, "dataset": "swisssurface3d", "resolution_m": 0.5}
        head["editions"] = ["2021", "2022"]
    return {"attribution": "© swisstopo", **head, "schema": 1, "tiles": tiles}


def _files(provenance):
    if "tiles" in provenance:
        return [entry["file"] for entry in provenance["tiles"]]
    return [provenance["file"]]


@pytest.mark.parametrize("command", ["photo", "surface", "tlm"])
def test_download_fetches_verifies_and_records(swisstopo, capsys, command):
    folder = swisstopo.out / FOLDERS[command]
    code, out, err = _download(swisstopo, capsys, command)
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    raw = (folder / "provenance.json").read_bytes()
    expected = _provenance(swisstopo, command)
    assert json.loads(raw) == expected
    assert (
        raw == (json.dumps(expected, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    )
    files = _files(expected)
    assert sorted(p.name for p in folder.iterdir()) == sorted([*files, "provenance.json"])
    for name in files:
        assert (folder / name).read_bytes() == swisstopo.bodies[name]
    fetched = {path for method, path, _ in swisstopo.file_requests() if method == "GET"}
    assert fetched == {swisstopo.file_path(name) for name in files}  # no decoy

    swisstopo.requests.clear()
    code, out, err = _download(swisstopo, capsys, command)
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert swisstopo.file_requests() == []  # verified files: no GET, no HEAD
    assert (folder / "provenance.json").read_bytes() == raw


@pytest.mark.parametrize("command", ["photo", "surface", "tlm"])
def test_a_republished_file_is_refused_before_anything_is_fetched(swisstopo, capsys, command):
    pinned = swisstopo.expected_entries()  # what the lock pins
    where = "mattini: error: tile 2624-1097 of area 'village': "  # the last tile in order
    if command == "photo":
        name, old = photo_name("2624-1097"), pinned["swissimage"]["tiles"]["2624-1097"]["sha256"]
        swisstopo.publish_photo("2624-1097", b"republished SWISSIMAGE bytes")
    elif command == "surface":
        name = surface_name("2624-1097", "2021")
        old = pinned["swisssurface3d"]["tiles"]["2624-1097"]["sha256"]
        swisstopo.publish_surface("2624-1097", "2021", b"republished swissSURFACE3D bytes")
    else:
        name, old, where = TLM_FILE, pinned["swisstlm3d"]["sha256"], TLM_WHERE
        swisstopo.publish_tlm(b"republished swissTLM3D bytes")
    new = sha256(swisstopo.bodies[name])
    assert old != new
    code, out, err = _download(swisstopo, capsys, command)
    assert (code, out) == (1, "")
    error = _error(err)
    assert error.startswith(where), err
    for part in (
        old,
        new,
        "nothing was fetched",
        f"`python -m mattini lock {command}`, then commit the lock, then design recomputes",
        f"the expected values in {RECOMPUTE[command]} (docs/SPEC.md §8)",
    ):
        assert part in error, (part, err)
    assert swisstopo.file_requests() == []  # no GET and no HEAD
    assert not swisstopo.out.exists()


def test_download_surface_takes_the_edition_the_lock_pins(swisstopo, capsys):
    swisstopo.publish_surface("2624-1096", "2022", b"an edition published after the lock")
    folder = swisstopo.out / FOLDERS["surface"]
    code, out, err = _download(swisstopo, capsys, "surface")
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert json.loads((folder / "provenance.json").read_bytes()) == _provenance(
        swisstopo, "surface"
    )
    assert not (folder / surface_name("2624-1096", "2022")).exists()


def test_download_tlm_refuses_a_file_host_checksum_that_is_not_the_lock_s(swisstopo, capsys):
    path = swisstopo.file_path(TLM_FILE)
    body, content_type, _ = swisstopo.routes[path]
    other = sha256(b"what the file host would send")
    swisstopo.routes[path] = (body, content_type, other)
    code, out, err = _download(swisstopo, capsys, "tlm")
    assert (code, out) == (1, "")
    error = _error(err)
    assert error.startswith(TLM_WHERE), err
    for part in (other, sha256(body), _url(swisstopo, TLM_FILE), "nothing was fetched"):
        assert part in error, (part, err)
    assert [r[0] for r in swisstopo.file_requests()] == ["HEAD"]
    assert not (swisstopo.out / "swisstlm3d").exists()


def _gets(site):
    return [rng for method, path, rng in site.file_requests() if method == "GET"]


def test_download_tlm_resumes_a_cut_transfer(swisstopo, capsys):
    path = swisstopo.file_path(TLM_FILE)
    swisstopo.script[path] = [("cut", CUT)]
    folder = swisstopo.out / FOLDERS["tlm"]
    code, out, err = _download(swisstopo, capsys, "tlm")
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    ranges = _gets(swisstopo)
    assert len(ranges) == 2 and ranges[0] in (None, "bytes=0-"), ranges
    assert ranges[1] == f"bytes={CUT}-", ranges
    assert swisstopo.sent[path] == len(swisstopo.bodies[TLM_FILE])  # nothing sent twice
    assert (folder / TLM_FILE).read_bytes() == swisstopo.bodies[TLM_FILE]
    assert sorted(p.name for p in folder.iterdir()) == sorted([TLM_FILE, "provenance.json"])
    assert json.loads((folder / "provenance.json").read_bytes()) == _provenance(swisstopo, "tlm")


def test_a_run_that_fails_keeps_its_part_for_the_next_run(swisstopo, capsys):
    path = swisstopo.file_path(TLM_FILE)
    swisstopo.script[path] = [("cut", CUT)] + [("status", 503)] * 50
    code, out, err = _download(swisstopo, capsys, "tlm")
    assert (code, out) == (1, "")
    assert _error(err).startswith(TLM_WHERE), err
    assert "`python -m mattini download tlm`" in _error(err), err  # how to resume
    folder = swisstopo.out / FOLDERS["tlm"]
    assert not (folder / TLM_FILE).exists() and not (folder / "provenance.json").exists()

    swisstopo.script[path] = []
    swisstopo.requests.clear()
    code, out, err = _download(swisstopo, capsys, "tlm")
    assert code == 0, err
    assert _gets(swisstopo) == [f"bytes={CUT}-"]
    assert (folder / TLM_FILE).read_bytes() == swisstopo.bodies[TLM_FILE]
    assert sorted(p.name for p in folder.iterdir()) == sorted([TLM_FILE, "provenance.json"])
