"""A fake swisstopo STAC API and file host for the pinning tests of brief M1-01.

Serves one STAC item per village tile with a 0.5 m and a 2 m asset; the 0.5 m file is
`synthetic terrain bytes for <tile>` and its published checksum is that body's SHA-256.
`republish(tile)` changes a tile's body and checksum, as swisstopo can inside an edition
(M0-04 Findings 7). Nothing reaches the network.
"""

import hashlib
from pathlib import Path

STAC_ITEMS = "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissalti3d/items/"
VILLAGE_TILES = [
    "2623-1095",
    "2623-1096",
    "2623-1097",
    "2624-1095",
    "2624-1096",
    "2624-1097",
]


class FakeSwisstopo:
    def __init__(self, edition="2024", tiles=VILLAGE_TILES):
        self.edition = edition
        self.items, self.files = {}, {}
        self.file_fetches, self.json_fetches = [], []
        self.offline_after = None  # number of STAC reads that succeed before the network drops
        self.broken_files = set()  # file URLs whose fetch fails with ConnectionResetError
        for tile in tiles:
            self._publish(tile, f"synthetic terrain bytes for {tile}".encode())

    def _publish(self, tile, body):
        item_id = f"swissalti3d_{self.edition}_{tile}"
        fine = f"{item_id}_0.5_2056_5728.tif"
        coarse = f"{item_id}_2_2056_5728.tif"
        self.files[f"https://files.example/{fine}"] = body
        self.files[f"https://files.example/{coarse}"] = b"the 2 m file must not be fetched"
        self.items[STAC_ITEMS + item_id] = {
            "id": item_id,
            "assets": {
                fine: {
                    "href": f"https://files.example/{fine}",
                    "file:checksum": "1220" + hashlib.sha256(body).hexdigest().upper(),
                },
                coarse: {
                    "href": f"https://files.example/{coarse}",
                    "file:checksum": "1220" + "00" * 32,
                },
            },
        }

    def republish(self, tile):
        self._publish(tile, f"republished terrain bytes for {tile}".encode())

    def sha256(self, tile):
        return hashlib.sha256(f"synthetic terrain bytes for {tile}".encode()).hexdigest()

    def fetch_json(self, url):
        if self.offline_after is not None and len(self.json_fetches) >= self.offline_after:
            raise ConnectionResetError("the network dropped")
        self.json_fetches.append(url)
        return self.items[url]

    def fetch_file(self, url, dest):
        self.file_fetches.append(url)
        if url in self.broken_files:
            raise ConnectionResetError("the network dropped")
        Path(dest).write_bytes(self.files[url])
