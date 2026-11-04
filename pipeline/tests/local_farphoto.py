"""A local stand-in for SWISSIMAGE's 2 m asset over the surroundings, for brief v0.6.0-05's pins.

`LocalFarphoto(margin_m=1000)` is brief M3-03's `LocalSwisstopo` (local_swisstopo.py: the same
handler, `script`, `requests` and `sent`) that also serves what the live STAC API serves for
SWISSIMAGE 2023 over a box around the village (the pin author read it on 2026-11-02, v1 API),
with synthetic file bodies:

- an item `swissimage-dop10_2023_<E km>-<N km>` for every 1 km cell of the village's box grown
  by `margin_m` but the `ABSENT` ones (with the default 1000: 20 cells, 17 with an item, a
  stepped south-east edge as Italy's), each with `properties.datetime` "2023-01-01T00:00:00Z"
  as live and two assets, `..._0.1_2056.tif` and `..._2_2056.tif`; the 2 m one is the far
  photo's, the 10 cm one a decoy (for the village's own six cells it is the photo's real file,
  as M3-03's stand-in serves it);
- as live, a cell without an item answers HTTP 404, `file:checksum` is `1220` and the SHA-256
  in upper-case hex (`gsd` 2.0 beside it, as the v1 API writes it; the v0.9 API wrote
  `checksum:multihash` and `eo:gsd`), and a file answers HEAD with its Content-Length and
  `x-amz-meta-sha256`.

`publish_far(cell, body, datetime=...)` publishes or republishes a cell's item (a new checksum,
a new edition's datetime, or an item where there was none); `withdraw_far(cell)` makes its
item answer 404. `far_entry()` is the lock entry design expects from the items as published
now; `far_cells` every cell of the box, east outer, north inner.
"""

import json
import math

from local_swisstopo import PHOTO, STAC, LocalSwisstopo, photo_name, sha256

DATETIME = "2023-01-01T00:00:00Z"
VILLAGE = (
    2_623_000,
    2_625_000,
    1_095_000,
    1_098_000,
)  # config/world.json's village box
ABSENT = (
    "2624-1094",
    "2625-1094",
    "2625-1095",
)  # of the 1000 m box: the stepped south-east


def far_name(cell):
    return f"swissimage-dop10_2023_{cell}_2_2056.tif"


def cells_of(margin_m):
    """Every 1 km cell of the village's box grown by `margin_m`: east outer, north inner."""
    e_min, e_max, n_min, n_max = VILLAGE
    east = range(math.floor((e_min - margin_m) / 1000), math.ceil((e_max + margin_m) / 1000))
    north = range(math.floor((n_min - margin_m) / 1000), math.ceil((n_max + margin_m) / 1000))
    return [f"{e}-{n}" for e in east for n in north]


class LocalFarphoto(LocalSwisstopo):
    """LocalSwisstopo with the 2023 items of every cell of the box but `absent`."""

    def __init__(self, margin_m=1000, absent=ABSENT):
        self.datetimes = {}
        super().__init__()  # publishes the village's photo items through publish_photo below
        self.server.socket.listen(64)  # eight parallel clients: socketserver's backlog is 5
        self.far_cells = cells_of(margin_m)
        for cell in self.far_cells:
            if cell not in absent and far_name(cell) not in self.bodies:
                self.publish_far(cell, f"SWISSIMAGE 2 m bytes of {cell}\n".encode() * 29)

    def publish_photo(self, tile, body):
        """The village's photo item: its 10 cm file as M3-03's, and a real 2 m file too."""
        self.publish_far(tile, f"SWISSIMAGE 2 m bytes of {tile}\n".encode() * 29, photo=body)

    def publish_far(self, cell, body, datetime=DATETIME, photo=None):
        item_id = f"swissimage-dop10_2023_{cell}"
        assets = {}
        with self.lock:
            for name, served, gsd in (
                (photo_name(cell), photo, 0.1),
                (far_name(cell), body, 2.0),
            ):
                path = f"/{PHOTO}/{item_id}/{name}"
                data = served if served is not None else b"a decoy asset: never fetched"
                self.routes[path] = (
                    data,
                    "image/tiff; application=geotiff",
                    sha256(data),
                )
                if served is not None:
                    self.bodies[name] = served
                assets[name] = {
                    "type": "image/tiff; application=geotiff; profile=cloud-optimized",
                    "href": self.base + path,
                    "gsd": gsd,
                    "proj:epsg": 2056,
                    "file:checksum": "1220" + sha256(data).upper(),
                }
            self.datetimes[cell] = datetime
            item = {
                "id": item_id,
                "collection": PHOTO,
                "properties": {
                    "datetime": datetime,
                    "created": "2024-05-23T15:59:14.425569Z",
                    "updated": "2025-01-27T13:15:18.996250Z",
                },
                "assets": assets,
            }
            self.routes[STAC.format(collection=PHOTO, item_id=item_id)] = (
                json.dumps(item).encode(),
                "application/geo+json",
                None,
            )

    def withdraw_far(self, cell):
        with self.lock:
            del self.routes[STAC.format(collection=PHOTO, item_id=f"swissimage-dop10_2023_{cell}")]

    def has_item(self, cell):
        return STAC.format(collection=PHOTO, item_id=f"swissimage-dop10_2023_{cell}") in self.routes

    def far_entry(self):
        """The lock entry design expects for the box from the items as published now."""
        return {
            "absent": [cell for cell in self.far_cells if not self.has_item(cell)],
            "collection": PHOTO,
            "edition": "2023",
            "resolution_m": 2,
            "tiles": {
                cell: {
                    "file": far_name(cell),
                    "sha256": sha256(self.bodies[far_name(cell)]),
                }
                for cell in self.far_cells
                if self.has_item(cell)
            },
        }
