"""A local stand-in for swisstopo's swissALTIRegio, over real HTTP, for brief M4-01's pins.

`LocalRegio()` is brief M3-03's `LocalSwisstopo` (local_swisstopo.py: the same handler,
the same `script`, `requests` and `sent`) that also serves what the live STAC API served for
swissALTIRegio on 2026-10-17 (design measured it), with synthetic file bodies:

- the item `swissaltiregio_<E km>-<N km>` of every 10 km tile in `VILLAGE_TILES` (the 30
  that meet the village's surroundings box) and of the ring of tiles around them
  (`RING_TILES`, which the village does not need: a tile rule that takes too many locks
  them and fails the exact entry), each with `properties.datetime` "2026-06-01T00:00:00Z"
  as live and one asset `swissaltiregio_<tile>_2056_5728.xyz.zip`;
- as live, the item ids carry no edition: the edition is only in `properties.datetime`;
- as live, `file:checksum` is `1220` and the SHA-256 in upper-case hex, and a file answers
  HEAD with its Content-Length and `x-amz-meta-sha256` in lower-case hex.

`publish_regio(tile, body, datetime=...)` republishes a tile (a new checksum, or a new
edition's datetime); `withdraw_regio(tile)` makes its item answer 404.
"""

import json

from local_swisstopo import STAC, LocalSwisstopo, sha256

REGIO = "ch.swisstopo.swissaltiregio"
DATETIME = "2026-06-01T00:00:00Z"
TILE_E = (2595, 2605, 2615, 2625, 2635, 2645)  # km, measured: corners at 5 km mod 10 east
TILE_N = (1074, 1084, 1094, 1104, 1114)  # and at 4 km mod 10 north
VILLAGE_TILES = [f"{e}-{n}" for e in TILE_E for n in TILE_N]  # east outer, north inner
RING_TILES = [
    f"{e}-{n}"
    for e in (2585, *TILE_E, 2655)
    for n in (1064, *TILE_N, 1124)
    if f"{e}-{n}" not in VILLAGE_TILES
]


def regio_name(tile):
    return f"swissaltiregio_{tile}_2056_5728.xyz.zip"


class LocalRegio(LocalSwisstopo):
    """LocalSwisstopo with the swissALTIRegio items of the village and the ring around it."""

    def __init__(self):
        super().__init__()
        self.datetimes = {}
        for tile in VILLAGE_TILES + RING_TILES:
            self.publish_regio(tile, f"swissALTIRegio bytes of {tile}\r\n".encode() * 53)

    def publish_regio(self, tile, body, datetime=DATETIME):
        item_id = f"swissaltiregio_{tile}"
        name = regio_name(tile)
        path = f"/{REGIO}/{item_id}/{name}"
        with self.lock:
            self.routes[path] = (body, "application/x.ascii-xyz+zip", sha256(body))
            self.bodies[name] = body
            self.datetimes[tile] = datetime
            item = {
                "id": item_id,
                "collection": REGIO,
                "properties": {
                    "datetime": datetime,
                    "created": "2024-03-13T10:55:07.236587Z",
                    "updated": "2026-06-22T05:30:03.284883Z",
                },
                "assets": {
                    name: {
                        "type": "application/x.ascii-xyz+zip",
                        "href": self.base + path,
                        "proj:epsg": 2056,
                        "geoadmin:variant": "tiled",
                        "file:checksum": "1220" + sha256(body).upper(),
                    }
                },
            }
            self.routes[STAC.format(collection=REGIO, item_id=item_id)] = (
                json.dumps(item).encode(),
                "application/geo+json",
                None,
            )

    def withdraw_regio(self, tile):
        with self.lock:
            del self.routes[STAC.format(collection=REGIO, item_id=f"swissaltiregio_{tile}")]

    def regio_entry(self):
        """The lock entry design expects for the village from the items as published now."""
        return {
            "collection": REGIO,
            "edition": "2026-06",
            "resolution_m": 10,
            "tiles": {
                tile: {"file": regio_name(tile), "sha256": sha256(self.bodies[regio_name(tile)])}
                for tile in VILLAGE_TILES
            },
        }
