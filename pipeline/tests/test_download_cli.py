"""`python -m mattini download terrain` end to end with the real urllib fetchers (M0-04).

A local HTTP server stands in for swisstopo, so this runs without network: the command line
wires the standard-library fetchers, verifies every file, reports progress, fetches nothing
on a second run, and exits non-zero naming the tile and the URL when a file is missing or
cut short (Hard Rule 2).
"""

import hashlib
import http.server
import json
import threading

import pytest

import mattini.__main__ as cli
from mattini import download
from mattini.world import REPO

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
def swisstopo(monkeypatch):
    """A local stand-in serving the six STAC items and their 0.5 m files."""
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    server.requests, server.routes, server.file_urls = [], {}, {}
    for tile in TILES:
        item_id = f"swissalti3d_2024_{tile}"
        name = f"{item_id}_0.5_2056_5728.tif"
        body = f"GeoTIFF bytes of {tile}".encode() * 1000
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
        server.routes[f"/stac/ch.swisstopo.swissalti3d/items/{item_id}"] = (
            item_json,
            len(item_json),
        )
        server.routes[f"/files/{name}"] = (body, len(body))
        server.file_urls[tile] = (f"/files/{name}", f"{base}/files/{name}")
    monkeypatch.setattr(download, "STAC_ITEM", base + "/stac/{collection}/items/{item_id}")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


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
