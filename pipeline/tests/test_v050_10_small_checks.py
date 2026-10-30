"""Pinning tests for brief v0.5.0-10: four small pipeline checks (the M3 residue).

Pinned decisions (docs/briefs/v0.5.0-10-small-pipeline-checks.md):

- *A cut transfer is named (I-02).* `download.urllib_fetch_file` compares the bytes it wrote
  with the response's Content-Length and, when fewer arrived, raises one of
  `download.FETCH_ERRORS` (so the one retry still runs) whose text holds `cut at <bytes
  written> of <Content-Length> bytes`. When the last attempt's problem was such a cut, the
  refusal ends `(after 2 attempts); a dropped connection heals on a rerun: run the command
  again`; when it was anything else (a SHA-256 that differs, an HTTP error) it ends `(after 2
  attempts)` as before. Before this, a cut was told only by the SHA-256 (brain.md H9: Python's
  urllib ends a body cut short without an error). An answer without a Content-Length (a body
  ended by closing the connection, or chunked) or with one that is not digits is not checked:
  it loads as before, and the SHA-256 still tells it.
- *resolution_m for the three resolution datasets (I-04).* `load_datasets` refuses an entry of
  swissalti3d, swissimage or swisssurface3d whose `resolution_m` is missing, not a number, a
  boolean, zero, negative or not finite, naming the file, the dataset, `resolution_m` and the
  value found, and `python -m mattini lock|download photo|surface` print that refusal as one
  `mattini: error:` line, exit 1. Before this, only swissalti3d's was tested.
- *The roofs step's order (I-05).* `computed_for` is checked against the two lock entries
  before the downloads are: with no download at all (an empty raw folder), a lock whose
  inputs differ from `computed_for` is still design's step (config/roofs.json, design), never
  a download command, with no progress line and nothing under the output folder.
- *The surfaces config's SHA-256 keys (R2-S-01).* A value of `expected_pixels_sha256` or
  `expected_png_sha256` with 63, 65 or 40 lower-case hex digits is refused naming the key and the
  cell (`expected_png_sha256['0.2'] must be a SHA-256`).

Run through the real code: the downloads with the local HTTP stand-in (local_swisstopo.py,
real urllib, `python -m mattini download photo|surface`), the loaders and the roofs step as
the other tests call them.

Likeliest wrong twins, each caught here: no Content-Length check (the SHA-256 message comes
back); a missing or non-digit Content-Length taken for a cut (every chunked download refused
twice); the cut raised as an error the retry does not catch (one cut then fails the run); the
rerun hint on every refusal, or on none, or decided by the first attempt; the resolution rule
kept for swissalti3d alone; the inputs check moved after the provenance read; a SHA-256 test
by `match` or by a length range.

Does NOT prove: a real cut of a real swisstopo transfer (nobody can schedule one); a cut the
server sends with no Content-Length (close-delimited or chunked: the SHA-256 alone still tells
it; the pins prove only that such a body loads); the TLM
file's resumable transfer (brief M3-03's tests); that the rerun hint is the right advice for
every dropped connection.
"""

import copy
import json
import math
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from local_swisstopo import SURFACE_YEARS, LocalSwisstopo, photo_name, surface_name
from roofs_inputs import make_inputs

import mattini.__main__ as cli
from mattini import download, lock, roofs
from mattini.datasets import DatasetsConfigError, load_datasets
from mattini.roofs import RoofsError, build_roofs
from mattini.surfaces import SurfacesError, check_surfaces_config
from mattini.world import REPO

TILE = "2623-1096"
CUT = 100  # the bytes a cut transfer delivers
HINT = "; a dropped connection heals on a rerun: run the command again"
FOLDERS = {"photo": "swissimage/2023", "surface": "swisssurface3d/2021-2022"}


# --------------------------------------------------------------- I-02: a cut transfer


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


def _name(command):
    return photo_name(TILE) if command == "photo" else surface_name(TILE, SURFACE_YEARS[TILE])


def _download(site, capsys, command):
    code = cli.main(["download", command, "--out", str(site.out)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _error(err):
    """The refusal: stderr from its `mattini: error:` line on (progress lines come first)."""
    assert "mattini: error: " in err, err
    return err[err.index("mattini: error: ") :].rstrip("\n")


def _gets(site, path):
    return [r for r in site.file_requests() if r[0] == "GET" and r[1] == path]


def test_urllib_fetch_file_names_a_cut_as_a_fetch_error(swisstopo, tmp_path):
    """The body stops after 100 of its 1295 bytes and the connection closes: urllib returns
    the short body without an error, so the fetcher compares the bytes with Content-Length."""
    name = photo_name(TILE)
    path = swisstopo.file_path(name)
    size = len(swisstopo.bodies[name])
    assert size == 1295  # 35 characters, 37 times
    swisstopo.script[path] = [("cut", CUT)]
    part = tmp_path / "file.part"
    with pytest.raises(download.FETCH_ERRORS, match=rf"cut at {CUT} of {size} bytes"):
        download.urllib_fetch_file(swisstopo.base + path, part)
    download.urllib_fetch_file(swisstopo.base + path, part)  # served whole: no error
    assert part.read_bytes() == swisstopo.bodies[name]


@pytest.mark.parametrize("command", ["photo", "surface"])
def test_a_transfer_cut_twice_says_so_and_a_rerun_heals_it(swisstopo, capsys, command):
    name = _name(command)
    path = swisstopo.file_path(name)
    size = len(swisstopo.bodies[name])
    swisstopo.script[path] = [("cut", CUT), ("cut", CUT)]
    code, out, err = _download(swisstopo, capsys, command)
    assert (code, out) == (1, ""), err
    assert _error(err) == (
        f"mattini: error: tile {TILE} of area 'village': {swisstopo.base + path}: fetch failed: "
        f"cut at {CUT} of {size} bytes (after 2 attempts){HINT}"
    )
    assert len(_gets(swisstopo, path)) == 2  # the first fetch and the one retry
    folder = swisstopo.out / FOLDERS[command]
    assert not (folder / name).exists() and not (folder / "provenance.json").exists()
    assert list(swisstopo.out.rglob("*.part")) == []

    code, out, err = _download(swisstopo, capsys, command)  # the rerun the message asks for
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert (folder / name).read_bytes() == swisstopo.bodies[name]


def test_one_cut_is_healed_by_the_retry_within_the_run(swisstopo, capsys):
    name = photo_name(TILE)
    path = swisstopo.file_path(name)
    swisstopo.script[path] = [("cut", CUT)]
    code, out, err = _download(swisstopo, capsys, "photo")
    folder = swisstopo.out / FOLDERS["photo"]
    assert (code, out) == (0, f"{folder / 'provenance.json'}\n"), err
    assert len(_gets(swisstopo, path)) == 2
    assert (folder / name).read_bytes() == swisstopo.bodies[name]


class _Unannounced(BaseHTTPRequestHandler):
    """A body whose length the answer does not announce as digits: `close` ends it by closing
    the connection (HTTP/1.0), `chunked` sends it in chunks (HTTP/1.1), `not-digits` sends
    `Content-Length: abc` and closes (http.client then reads to the close)."""

    protocol_version = "HTTP/1.0"
    BODY = b"a body of no announced length\n" * 50

    def do_GET(self):
        how = self.path.strip("/")
        if how == "chunked":
            self.protocol_version = "HTTP/1.1"
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        if how == "chunked":
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Connection", "close")
        elif how == "not-digits":
            self.send_header("Content-Length", "abc")
        self.end_headers()
        if how == "chunked":
            for start in range(0, len(self.BODY), 500):
                chunk = self.BODY[start : start + 500]
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
            self.wfile.write(b"0\r\n\r\n")
        else:
            self.wfile.write(self.BODY)
        self.close_connection = True

    def log_message(self, *args):
        pass


@pytest.mark.parametrize("how", ["close", "chunked", "not-digits"])
def test_a_body_of_no_announced_length_loads_unchecked(monkeypatch, tmp_path, how):
    """Decision 1: only a Content-Length of digits is compared; any other answer loads whole,
    as before (its SHA-256 is still checked by the caller)."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Unannounced)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        part = tmp_path / "file.part"
        download.urllib_fetch_file(f"http://127.0.0.1:{server.server_port}/{how}", part)
        assert part.read_bytes() == _Unannounced.BODY
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _serve_other_bytes(site, name):
    """The host now serves other bytes of the same length than the STAC item's checksum."""
    path = site.file_path(name)
    body, content_type, host_sha256 = site.routes[path]
    site.routes[path] = (bytes(b ^ 0x20 for b in body), content_type, host_sha256)
    return path


def test_a_whole_file_with_another_sha256_has_no_rerun_hint(swisstopo, capsys):
    name = photo_name(TILE)
    path = _serve_other_bytes(swisstopo, name)
    code, _, err = _download(swisstopo, capsys, "photo")
    message = _error(err)
    assert code == 1
    assert len(_gets(swisstopo, path)) == 2
    assert "does not match the published" in message and "cut at" not in message
    assert message.endswith("(after 2 attempts)"), message
    assert "rerun" not in message


@pytest.mark.parametrize(
    ("script", "hinted"),
    [
        ([("status", 503), ("cut", CUT)], True),
        ([("cut", CUT), ("status", 503)], False),
    ],
    ids=["an-error-then-a-cut", "a-cut-then-an-error"],
)
def test_the_hint_follows_the_last_attempt(swisstopo, capsys, script, hinted):
    name = photo_name(TILE)
    path = swisstopo.file_path(name)
    swisstopo.script[path] = list(script)
    code, _, err = _download(swisstopo, capsys, "photo")
    message = _error(err)
    assert code == 1
    assert message.endswith("(after 2 attempts)" + (HINT if hinted else "")), message
    assert ("cut at" in message) == hinted
    # The status as download.py writes it ("HTTP Error 503: ..."), not a bare "503": a random
    # local port such as 45039 also holds those digits.
    assert ("HTTP Error 503" in message) == (not hinted)


def test_a_cut_then_another_sha256_has_no_rerun_hint(swisstopo, capsys):
    name = photo_name(TILE)
    path = _serve_other_bytes(swisstopo, name)
    swisstopo.script[path] = [("cut", CUT)]
    code, _, err = _download(swisstopo, capsys, "photo")
    message = _error(err)
    assert code == 1
    assert "does not match the published" in message and "rerun" not in message


# ------------------------------------------------- I-04: resolution_m of three datasets

DATASETS = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))
MISSING = object()


@pytest.mark.parametrize("dataset", ["swissalti3d", "swissimage", "swisssurface3d"])
@pytest.mark.parametrize(
    "value",
    [MISSING, None, "0.5", 0, 0.0, -0.1, True, False, [0.5], math.inf, math.nan],
    ids=[
        "missing",
        "null",
        "a-string",
        "zero",
        "zero-float",
        "negative",
        "true",
        "false",
        "a-list",
        "infinite",
        "nan",
    ],
)
def test_a_resolution_dataset_without_a_resolution_is_refused(tmp_path, dataset, value):
    data = copy.deepcopy(DATASETS)
    if value is MISSING:
        del data["datasets"][dataset]["resolution_m"]
        found = "None"
    else:
        data["datasets"][dataset]["resolution_m"] = value
        found = repr(value)
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")  # inf and nan as JSON allows
    with pytest.raises(DatasetsConfigError) as refused:
        load_datasets(path)
    assert str(refused.value) == (
        f"{path}: dataset {dataset!r}: resolution_m must be a positive number of metres, "
        f"found {found}"
    )


@pytest.mark.parametrize("dataset", ["swissalti3d", "swissimage", "swisssurface3d"])
def test_a_resolution_dataset_with_a_whole_number_of_metres_loads(tmp_path, dataset):
    data = copy.deepcopy(DATASETS)
    data["datasets"][dataset]["resolution_m"] = 2
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    assert load_datasets(path)[dataset]["resolution_m"] == 2


@pytest.mark.parametrize("dataset", ["photo", "surface"])
@pytest.mark.parametrize("command", ["lock", "download"])
def test_the_command_line_says_the_resolution_refusal(
    tmp_path, monkeypatch, capsys, command, dataset
):
    """M3-R1-I-04's harm was a KeyError traceback on `lock` and `download photo|surface`: the
    commands read the datasets file through the real loader and print its refusal."""
    name = {"photo": "swissimage", "surface": "swisssurface3d"}[dataset]
    data = copy.deepcopy(DATASETS)
    del data["datasets"][name]["resolution_m"]
    path = tmp_path / "datasets.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    monkeypatch.setattr(cli, "load_datasets", lambda: load_datasets(path))

    def no_network(*args, **kwargs):
        raise AssertionError("the test reached for the network")

    for fetcher in ("urllib_fetch_json", "urllib_fetch_file", "urllib_head"):
        monkeypatch.setattr(download, fetcher, no_network)
    lock_path = tmp_path / "datasets.lock.json"
    lock_path.write_bytes((REPO / "config" / "datasets.lock.json").read_bytes())
    monkeypatch.setattr(lock, "LOCK_PATH", lock_path)
    argv = [command, dataset] + (["--out", str(tmp_path / "raw")] if command == "download" else [])
    code = cli.main(argv)
    captured = capsys.readouterr()
    assert (code, captured.out) == (1, ""), captured.err
    assert captured.err == (
        f"mattini: error: {path}: dataset {name!r}: resolution_m must be a positive number of "
        "metres, found None\n"
    )
    assert lock_path.read_bytes() == (REPO / "config" / "datasets.lock.json").read_bytes()
    assert not (tmp_path / "raw").exists()


def test_the_other_datasets_need_no_resolution():
    datasets = load_datasets()
    assert sorted(name for name in datasets if "resolution_m" not in datasets[name]) == [
        "swissbuildings3d",
        "swisstlm3d",
    ]


# ------------------------------------------------ I-05: the roofs step's inputs first


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    return make_inputs(tmp_path_factory.mktemp("roofs_inputs"))


@pytest.mark.parametrize("entry", ["swissimage", "swissbuildings3d"])
def test_other_inputs_with_no_download_are_still_design_s_step(case, tmp_path, entry):
    """No download has run (an empty raw folder) and the lock's inputs are not the ones
    config/roofs.json was computed for: the refusal is design's, before any provenance."""
    lock_data = copy.deepcopy(case["lock"])
    if entry == "swissimage":
        lock_data["datasets"]["swissimage"]["tiles"]["2651-1150"]["sha256"] = "2" * 64
    else:
        lock_data["datasets"]["swissbuildings3d"]["sheets"]["1249-42"]["sha256"] = "3" * 64
    raw = tmp_path / "raw"
    raw.mkdir()
    out, said = tmp_path / "out", []
    with pytest.raises(RoofsError) as refused:
        build_roofs(
            case["world"],
            case["datasets"],
            lock_data,
            case["config"],
            case["terrain"],
            raw,
            out,
            progress=said.append,
        )
    message = str(refused.value)
    assert "config/roofs.json" in message and "design recomputes" in message, message
    assert "download" not in message and "provenance" not in message, message
    assert said == [] and not out.exists()


def test_the_inputs_refusal_reads_no_file_of_the_raw_folder(case, tmp_path, monkeypatch):
    """The same refusal with a raw folder that cannot be listed or read at all."""
    lock_data = copy.deepcopy(case["lock"])
    lock_data["datasets"]["swissimage"]["tiles"]["2651-1150"]["sha256"] = "2" * 64
    monkeypatch.setattr(roofs, "read_sheet", None)  # never reached
    with pytest.raises(RoofsError, match=r"design recomputes the expected value"):
        build_roofs(
            case["world"],
            case["datasets"],
            lock_data,
            case["config"],
            case["terrain"],
            tmp_path / "no such folder",
            tmp_path / "out",
        )
    assert not (tmp_path / "out").exists()


# ------------------------------------------- R2-S-01: the surfaces config's SHA-256 keys

SURFACES = json.loads((REPO / "config" / "surfaces.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("field", ["expected_pixels_sha256", "expected_png_sha256"])
@pytest.mark.parametrize("cell", ["0.2", "0.5", "1"])
@pytest.mark.parametrize("digits", [63, 65, 40])
def test_a_cell_s_sha256_of_another_length_is_refused_naming_the_key(field, cell, digits):
    config = copy.deepcopy(SURFACES)
    value = "0" * digits
    config["areas"]["village"][field][cell] = value
    with pytest.raises(SurfacesError) as refused:
        check_surfaces_config(config, "config/surfaces.json")
    assert str(refused.value) == (
        f"config/surfaces.json: area 'village': {field}[{cell!r}] must be a SHA-256 in 64 "
        f"lower-case hex characters, found {value!r}"
    )


def test_the_committed_surfaces_config_is_accepted():
    check_surfaces_config(copy.deepcopy(SURFACES), "config/surfaces.json")
