"""Pinning tests for brief v0.6.0-05: the committed lock pins the village's measured far photo.

Pinned decisions (design §0 and §2; lesson 38): config/datasets.lock.json, written by
`python -m mattini lock farphoto` against the live STAC API (v1) on 2026-11-02 and committed,
holds exactly the `swissimage_far` entry read two ways that agree: the pin author's lock run
(the items' `file:checksum`) and, by hand, the session's STAC v0.9 listing of 2026-11-02
(`checksum:multihash`, `eo:gsd` 2.0); the 1220 files downloaded have exactly these SHA-256
(201'117'688 bytes). Of the 42 × 43 = 1806 cells of the surroundings box, 1220 have an item
of edition 2023 (every item's `properties.datetime` 2023-01-01T00:00:00Z): in every column
of 1 km from its southernmost covered cell (`SOUTH`) up to N 1117; the 586 others (Italy, the
stepped south) are `absent`. The entry's canonical SHA-256 (`lock.entry_sha256`, SPEC §8) is
what config/surroundings.json's `colour.computed_for` will combine with the swissALTIRegio
entry (`lock.entries_sha256`, design §5; brief v0.6.0-06).

Does NOT prove: that swisstopo still publishes these files (`pytest -m network` reads a sample).
"""

import hashlib
import json

from mattini.lock import entry_sha256, load_lock

ENTRY_SHA256 = "072d8cffff62b34099d53ed1e46e292defce4ea28f5a57274b2bc774422bdc2f"
SOUTH = {  # east km: the southernmost north km with an item; every cell north of it has one
    2603: 1088,
    2604: 1089,
    2605: 1089,
    2606: 1089,
    2607: 1089,
    2608: 1089,
    2609: 1092,
    2610: 1092,
    2611: 1090,
    2612: 1090,
    2613: 1090,
    2614: 1090,
    2615: 1090,
    2616: 1090,
    2617: 1090,
    2618: 1089,
    2619: 1089,
    2620: 1086,
    2621: 1085,
    2622: 1085,
    2623: 1085,
    2624: 1086,
    2625: 1086,
    2626: 1086,
    2627: 1085,
    2628: 1085,
    2629: 1085,
    2630: 1085,
    2631: 1085,
    2632: 1085,
    2633: 1085,
    2634: 1086,
    2635: 1091,
    2636: 1093,
    2637: 1093,
    2638: 1093,
    2639: 1093,
    2640: 1093,
    2641: 1093,
    2642: 1093,
    2643: 1094,
    2644: 1095,
}
FIRST = (
    "2603-1088",
    "826dc2299fe0957c70daf31f9612bdad76c2a0c308a49ff4766343493a371013",
)
MIDDLE = (
    "2623-1106",
    "aed2384cbf3c79e6f50578a3546bd6e15c969305c433b94a4e7fac8bec3736be",
)
LAST = ("2644-1117", "83bf846a784130d28cc6ff4f301894701564b8259e7ba4185d9e8317326283f8")


def test_the_committed_lock_pins_the_measured_entry():
    datasets = load_lock()["datasets"]
    assert set(datasets) == {
        "swissaltiregio",
        "swissalti3d",
        "swissbuildings3d",
        "swissimage",
        "swissimage_far",
        "swisssurface3d",
        "swisstlm3d",
    }
    entry = datasets["swissimage_far"]
    cells = [f"{e}-{n}" for e in range(2603, 2645) for n in range(1075, 1118)]
    present = [c for c in cells if int(c[5:]) >= SOUTH[int(c[:4])]]
    assert (len(present), len(cells) - len(present)) == (1220, 586)
    assert list(entry["tiles"]) == present
    assert entry["absent"] == [c for c in cells if c not in present]
    assert {k: v for k, v in entry.items() if k not in ("absent", "tiles")} == {
        "collection": "ch.swisstopo.swissimage-dop10",
        "edition": "2023",
        "resolution_m": 2,
    }
    for cell, pinned in entry["tiles"].items():
        assert pinned["file"] == f"swissimage-dop10_2023_{cell}_2_2056.tif", cell
    for cell, sha in (FIRST, MIDDLE, LAST):
        assert entry["tiles"][cell]["sha256"] == sha, cell
    text = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == ENTRY_SHA256
    assert entry_sha256(entry) == ENTRY_SHA256
