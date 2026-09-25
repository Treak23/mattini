"""`python -m mattini lock terrain` and `download terrain` end to end with urllib (M0-04, M1-01).

A local HTTP server stands in for swisstopo, so this runs without network: the command line
wires the standard-library fetchers, verifies every file, reports progress, fetches nothing
on a second run, and exits non-zero naming the tile and the URL when a file is missing or
cut short (Hard Rule 2). The tile lock lives in a temporary folder (`mattini.lock.LOCK_PATH`
patched), written from the local server's items: `lock terrain` fetches no file, and
`download terrain` refuses a missing or malformed lock, naming the file and the command,
and a republished tile, naming both checksums, before it fetches anything.
"""

import hashlib
import http.server
import json
import threading

import pytest

import mattini.__main__ as cli
from mattini import download, lock
from mattini.datasets import load_datasets
from mattini.world import REPO, load_world

TILES = ["2623-1095", "2623-1096", "2623-1097", "2624-1095", "2624-1096", "2624-1097"]


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.requests.append(self.path)
        route = self.server.routes.get(self.path)
        if route is None:
            self.send_error(404)
            return
        body, declared_length = route
        self.send_response(200)
        self.send_header("Content-Length", str(declared_length))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def swisstopo(monkeypatch, tmp_path):
    """A local stand-in serving the six STAC items and their 0.5 m files, and a lock for them."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    server.requests, server.routes, server.file_urls = [], {}, {}
    for tile in TILES:
        _publish(server, base, tile, f"GeoTIFF bytes of {tile}".encode() * 1000)
    monkeypatch.setattr(download, "STAC_ITEM", base + "/stac/{collection}/items/{item_id}")
    server.lock_path = tmp_path / "config" / "datasets.lock.json"
    server.lock_path.parent.mkdir()
    monkeypatch.setattr(lock, "LOCK_PATH", server.lock_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    pinned = lock.build_lock(
        load_world(), load_datasets(), download.urllib_fetch_json, area="village"
    )
    lock.write_lock(pinned, server.lock_path)
    server.requests.clear()
    yield server
    server.shutdown()
    server.server_close()


def _publish(server, base, tile, body):
    """Serve `body` as the tile's 0.5 m file, its STAC item publishing body's SHA-256."""
    item_id = f"swissalti3d_2024_{tile}"
    name = f"{item_id}_0.5_2056_5728.tif"
    item = {
        "id": item_id,
        "assets": {
            name: {
                "href": f"{base}/files/{name}",
                "file:checksum": "1220" + hashlib.sha256(body).hexdigest().upper(),
            }
        },
    }
    item_json = json.dumps(item).encode()
    server.routes[f"/stac/ch.swisstopo.swissalti3d/items/{item_id}"] = (item_json, len(item_json))
    server.routes[f"/files/{name}"] = (body, len(body))
    server.file_urls[tile] = (f"/files/{name}", f"{base}/files/{name}")


def _file_requests(server):
    return [path for path in server.requests if path.startswith("/files/")]


def test_default_download_root_is_data_raw():
    assert download.DEFAULT_OUT == REPO / "data" / "raw"


def test_download_then_rerun_fetches_nothing(swisstopo, tmp_path, capsys):
    provenance = tmp_path / "swissalti3d" / "2024" / "provenance.json"
    assert cli.main(["download", "terrain", "--out", str(tmp_path)]) == 0
    first = capsys.readouterr()
    assert first.out == f"{provenance}\n"
    assert first.err.count("fetching ") == 6
    assert "6 tiles verified, 6 fetches" in first.err
    assert len(_file_requests(swisstopo)) == 6
    for entry in json.loads(provenance.read_bytes())["tiles"]:
        data = (provenance.parent / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    before = provenance.read_bytes()

    assert cli.main(["download", "terrain", "--out", str(tmp_path)]) == 0
    second = capsys.readouterr()
    assert "fetching " not in second.err
    assert "6 tiles verified, 0 fetches" in second.err
    assert len(_file_requests(swisstopo)) == 6
    assert provenance.read_bytes() == before


def test_a_missing_file_fails_naming_tile_and_url(swisstopo, tmp_path, capsys):
    path, url = swisstopo.file_urls["2623-1097"]
    del swisstopo.routes[path]
    assert cli.main(["download", "terrain", "--out", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mattini: error: tile 2623-1097" in captured.err
    assert url in captured.err and "404" in captured.err
    assert _file_requests(swisstopo).count(path) == 2  # the one retry
    assert list(tmp_path.rglob("*.part")) == []
    assert not (tmp_path / "swissalti3d" / "2024" / "provenance.json").exists()


def test_a_file_cut_short_fails_naming_tile_and_url(swisstopo, tmp_path, capsys):
    path, url = swisstopo.file_urls["2624-1095"]
    body, length = swisstopo.routes[path]
    swisstopo.routes[path] = (body[: length // 2], length)
    assert cli.main(["download", "terrain", "--out", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "mattini: error: tile 2624-1095" in captured.err and url in captured.err
    out = tmp_path / "swissalti3d" / "2024"
    assert not (out / path.rsplit("/", 1)[1]).exists()
    assert list(tmp_path.rglob("*.part")) == []


def test_a_missing_stac_item_fails_naming_tile_and_url(swisstopo, tmp_path, capsys):
    item = "/stac/ch.swisstopo.swissalti3d/items/swissalti3d_2024_2624-1097"
    del swisstopo.routes[item]
    assert cli.main(["download", "terrain", "--out", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "mattini: error: tile 2624-1097" in captured.err
    assert item in captured.err and "cannot read the STAC item" in captured.err


def test_lock_terrain_writes_the_lock_from_the_stac_items_only(swisstopo, capsys):
    written = swisstopo.lock_path.read_bytes()
    swisstopo.lock_path.unlink()
    assert cli.main(["lock", "terrain"]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"{swisstopo.lock_path}\n"
    assert swisstopo.lock_path.read_bytes() == written
    tiles = lock.load_lock(swisstopo.lock_path)["datasets"]["swissalti3d"]["tiles"]
    for tile in TILES:
        body, _ = swisstopo.routes[swisstopo.file_urls[tile][0]]
        assert tiles[tile]["sha256"] == hashlib.sha256(body).hexdigest()
    assert len(swisstopo.requests) == 6
    assert _file_requests(swisstopo) == []


def test_lock_terrain_fails_naming_tile_and_url_and_writes_nothing(swisstopo, capsys):
    swisstopo.lock_path.unlink()
    del swisstopo.routes["/stac/ch.swisstopo.swissalti3d/items/swissalti3d_2024_2623-1096"]
    assert cli.main(["lock", "terrain"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mattini: error: tile 2623-1096" in captured.err
    assert "cannot read the STAC item" in captured.err
    assert list(swisstopo.lock_path.parent.iterdir()) == []


@pytest.mark.parametrize("text", [None, "", "{}", '{"schema": 1, "datasets": {}}'])
def test_download_without_a_valid_lock_names_the_file_and_the_command(
    swisstopo, tmp_path, capsys, text
):
    if text is None:
        swisstopo.lock_path.unlink()
    else:
        swisstopo.lock_path.write_text(text, encoding="utf-8")
    out = tmp_path / "raw"
    assert cli.main(["download", "terrain", "--out", str(out)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(f"mattini: error: {swisstopo.lock_path}: ")
    assert "`python -m mattini lock terrain`" in captured.err
    assert swisstopo.requests == []  # refused before anything is asked of swisstopo
    assert not out.exists()


def test_download_refuses_a_republished_tile_before_fetching(swisstopo, tmp_path, capsys):
    base = swisstopo.file_urls["2624-1096"][1].split("/files/")[0]
    old_body, _ = swisstopo.routes[swisstopo.file_urls["2624-1096"][0]]
    new_body = b"republished GeoTIFF bytes of 2624-1096" * 1000
    _publish(swisstopo, base, "2624-1096", new_body)
    assert cli.main(["download", "terrain", "--out", str(tmp_path / "raw")]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mattini: error: tile 2624-1096" in captured.err
    assert hashlib.sha256(old_body).hexdigest() in captured.err
    assert hashlib.sha256(new_body).hexdigest() in captured.err
    assert "`python -m mattini lock terrain`" in captured.err
    assert _file_requests(swisstopo) == []
    assert not (tmp_path / "raw" / "swissalti3d" / "2024" / "provenance.json").exists()
