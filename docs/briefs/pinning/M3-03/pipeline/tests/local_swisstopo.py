"""A local stand-in for swisstopo, over real HTTP, for the pinning tests of brief M3-03.

`LocalSwisstopo()` serves on 127.0.0.1 what the live STAC API and file host served for
the village on 2026-10-14 (design measured it), with synthetic file bodies:

- SWISSIMAGE 10 cm, edition 2023: item `swissimage-dop10_2023_<tile>` per village tile, its
  0.1 m GeoTIFF and the 2 m one as a decoy;
- swissSURFACE3D raster: item `swisssurface3d-raster_<year>_<tile>` in 2022 for 2623-1095
  and in 2021 for the five others (`SURFACE_YEARS`), each with its `.xyz.zip` as a decoy;
- swissTLM3D 2026-02: item `swisstlm3d_2026-02` with the FileGDB zip among the GeoPackage,
  Shapefile and INTERLIS zips. Live, the FileGDB zip comes first; here the GeoPackage does,
  on purpose, so that code taking the first asset fails.

As live: an item that is not published answers HTTP 404; `file:checksum` is `1220` and the
SHA-256 in upper-case hex; a file answers HEAD with its Content-Length and
`x-amz-meta-sha256` in lower-case hex, and GET with `Range: bytes=<first>-` with 206 and a
Content-Range. `script[path]` lists what the next GETs of that path get, one entry each:
`("cut", n)` serves the answer but stops after n bytes of its body, the Content-Length
unmet and the connection closed, which is how a cut transfer reaches Python's urllib (no
error, a short body; brain.md H9); `("status", code)` answers that HTTP status instead
(a server error is not an absent item). An empty script serves normally.
`requests` logs every request as (method, path, Range header); `sent[path]` counts the body
bytes sent. Nothing reaches the network.
"""

import hashlib
import http.server
import json
import re
import threading

VILLAGE_TILES = ["2623-1095", "2623-1096", "2623-1097", "2624-1095", "2624-1096", "2624-1097"]
SURFACE_YEARS = {tile: "2021" for tile in VILLAGE_TILES} | {"2623-1095": "2022"}
STAC = "/api/stac/v1/collections/{collection}/items/{item_id}"
PHOTO = "ch.swisstopo.swissimage-dop10"
SURFACE = "ch.swisstopo.swisssurface3d-raster"
TLM = "ch.swisstopo.swisstlm3d"
TLM_ITEM = "swisstlm3d_2026-02"
TLM_FILE = "swisstlm3d_2026-02_2056_5728.gdb.zip"
DECOY = b"a decoy asset: never fetched"


def photo_name(tile):
    return f"swissimage-dop10_2023_{tile}_0.1_2056.tif"


def surface_name(tile, year):
    return f"swisssurface3d-raster_{year}_{tile}_0.5_2056_5728.tif"


def tlm_body(size=200_003):
    """Bytes that differ everywhere, so a resume from a wrong offset cannot verify."""
    blocks = (
        hashlib.sha256(f"swissTLM3D block {i}".encode()).digest() for i in range(size // 32 + 1)
    )
    return b"".join(blocks)[:size]


def sha256(body):
    return hashlib.sha256(body).hexdigest()


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self._answer(head=True)

    def do_GET(self):
        self._answer(head=False)

    def _answer(self, *, head):
        site = self.server.site
        rng = self.headers.get("Range")
        with site.lock:
            site.requests.append((self.command, self.path, rng))
            route = site.routes.get(self.path)
            step = (
                site.script[self.path].pop(0) if not head and site.script.get(self.path) else None
            )
        cut = step[1] if step is not None and step[0] == "cut" else None
        if step is not None and step[0] == "status":
            self.send_error(step[1])
            return
        if route is None:
            self.send_error(404)
            return
        body, content_type, host_sha256 = route
        first, code, extra = 0, 200, {}
        if rng is not None and not head:
            match = re.fullmatch(r"bytes=([0-9]+)-([0-9]*)", rng)
            if match is None:
                self.send_error(400)
                return
            first = int(match.group(1))
            last = int(match.group(2)) if match.group(2) else len(body) - 1
            if first >= len(body):
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{len(body)}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            body = body[first : min(last, len(body) - 1) + 1]
            code = 206
            extra["Content-Range"] = f"bytes {first}-{first + len(body) - 1}/{len(route[0])}"
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if host_sha256 is not None:
            self.send_header("x-amz-meta-sha256", host_sha256)
        for key, value in extra.items():
            self.send_header(key, value)
        self.end_headers()
        if head:
            return
        payload = body if cut is None else body[:cut]
        with site.lock:  # counted first: the client may finish before this thread goes on
            site.sent[self.path] = site.sent.get(self.path, 0) + len(payload)
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class LocalSwisstopo:
    """The village's three new datasets as swisstopo serves them; see the module docstring."""

    def __init__(self):
        self.lock = threading.Lock()
        self.routes, self.script, self.sent, self.requests = {}, {}, {}, []
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.daemon_threads = True
        self.server.site = self
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.stac_item = self.base + STAC  # what `download.STAC_ITEM` becomes
        self.bodies = {}
        for tile in VILLAGE_TILES:
            self.publish_photo(tile, f"SWISSIMAGE 2023 bytes of {tile}\n".encode() * 37)
            year = SURFACE_YEARS[tile]
            self.publish_surface(
                tile, year, f"swissSURFACE3D {year} bytes of {tile}\n".encode() * 41
            )
        self.publish_tlm(tlm_body())
        self._thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
        )
        self._thread.start()

    # --- publishing, as swisstopo does it -------------------------------------------------

    def _item(self, collection, item_id, assets):
        """Publish a STAC item; `assets` maps an asset name to its body (or None: a decoy)."""
        item = {"id": item_id, "collection": collection, "assets": {}}
        for name, body in assets.items():
            path = f"/{collection}/{item_id}/{name}"
            served = DECOY if body is None else body
            self.routes[path] = (served, "application/octet-stream", sha256(served))
            checksum = "1220" + ("AB" * 32 if body is None else sha256(body).upper())
            item["assets"][name] = {"href": self.base + path, "file:checksum": checksum}
            if body is not None:
                self.bodies[name] = body
        text = json.dumps(item).encode()
        self.routes[STAC.format(collection=collection, item_id=item_id)] = (
            text,
            "application/geo+json",
            None,
        )

    def publish_photo(self, tile, body):
        item_id = f"swissimage-dop10_2023_{tile}"
        self._item(PHOTO, item_id, {photo_name(tile): body, f"{item_id}_2_2056.tif": None})

    def publish_surface(self, tile, year, body):
        item_id = f"swisssurface3d-raster_{year}_{tile}"
        self._item(
            SURFACE,
            item_id,
            {surface_name(tile, year): body, f"{item_id}_0.5_2056_5728.xyz.zip": None},
        )

    def withdraw_surface(self, tile, year):
        """The item is no longer published: its URL answers 404."""
        item_id = f"swisssurface3d-raster_{year}_{tile}"
        del self.routes[STAC.format(collection=SURFACE, item_id=item_id)]

    def publish_tlm(self, body):
        self._item(
            TLM,
            TLM_ITEM,
            {
                "swisstlm3d_2026-02_2056_5728.gpkg.zip": None,
                "swisstlm3d_2026-02_2056_5728.shp.zip": None,
                TLM_FILE: body,
                "swisstlm3d_2026-02_2056_5728.xtf.zip": None,
            },
        )

    # --- what the tests look at ------------------------------------------------------------

    def expected_entries(self):
        """The lock entries design expects from the items as published now: exact key sets,
        lower-case hex. Taken before a republish, it is what the lock pins."""
        return {
            "swissimage": {
                "collection": PHOTO,
                "edition": "2023",
                "resolution_m": 0.1,
                "tiles": {
                    tile: {
                        "file": photo_name(tile),
                        "sha256": sha256(self.bodies[photo_name(tile)]),
                    }
                    for tile in VILLAGE_TILES
                },
            },
            "swisssurface3d": {
                "collection": SURFACE,
                "resolution_m": 0.5,
                "tiles": {
                    tile: {
                        "edition": SURFACE_YEARS[tile],
                        "file": surface_name(tile, SURFACE_YEARS[tile]),
                        "sha256": sha256(self.bodies[surface_name(tile, SURFACE_YEARS[tile])]),
                    }
                    for tile in VILLAGE_TILES
                },
            },
            "swisstlm3d": {
                "collection": TLM,
                "edition": "2026-02",
                "file": TLM_FILE,
                "sha256": sha256(self.bodies[TLM_FILE]),
            },
        }

    def item_path(self, collection, item_id):
        return STAC.format(collection=collection, item_id=item_id)

    def file_path(self, name):
        """The path of a published file (not of a decoy), from its STAC item's href."""
        (path,) = [p for p, route in self.routes.items() if p.endswith("/" + name)]
        return path

    def file_requests(self):
        """Every request (HEAD or GET) for a file rather than a STAC item."""
        return [r for r in self.requests if not r[1].startswith("/api/stac/")]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
