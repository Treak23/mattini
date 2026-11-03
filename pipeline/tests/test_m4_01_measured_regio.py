"""Pinning tests for brief M4-01: the committed lock pins the village's measured swissALTIRegio.

Pinned decisions (m4-design §1; lesson 38): config/datasets.lock.json, written by
`python -m mattini lock regio` against the live STAC API and committed, holds exactly the
entry design read on 2026-10-17 two ways that agree: the STAC items' `file:checksum`
(published in upper-case hex) and the SHA-256 of the 30 files themselves (equal to the file
host's `x-amz-meta-sha256`; 179'684'396 bytes together). Every item's
`properties.datetime` was 2026-06-01T00:00:00Z: the edition `2026-06`. The entry's canonical
SHA-256 (`lock.entry_sha256`, SPEC §8) is what config/surroundings.json records as
`computed_for.inputs_sha256` (test_m4_01_expected_inputs.py).

Does NOT prove: that swisstopo still publishes these files (`pytest -m network` does).
"""

import hashlib
import json

from mattini.lock import entry_sha256, load_lock

TILES = {  # tile: SHA-256 of swissaltiregio_<tile>_2056_5728.xyz.zip
    "2595-1074": "89c352910b39de6eb4aa61c4621830c6f753cb9b1ca83b66c2f55426e999c8f5",
    "2595-1084": "5fd345d0f5df194a6ccfc5948cfade8094a98b7a4b4c394bc376478db82083b3",
    "2595-1094": "4cac3fd9d495bb17450aecf346007031618c21908879a0fb3da7380277e428c6",
    "2595-1104": "be915cc13f4dbe474652d55d20bd795c57b9e46b6480c96794002a7739ab2539",
    "2595-1114": "e1a1498d8dc88b5d8ac2fcb7915f3b635ecf5914664074f4699fb87d6b1a131e",
    "2605-1074": "ab7cf255866da44cbd3abd3bff78fd924fb053bd5109f9409d08288c2f618fda",
    "2605-1084": "90110f953e5ecbf992393cc3199d55eff809ad083119a434640ef9ba057425c0",
    "2605-1094": "912bdb28b2c5ec9c758436b2aee68d45fd35c82b129d2bd2f330bf92c40e7a15",
    "2605-1104": "bbf39adeec9527200533492ade49526e1c33d363a414c7b7ad7d44fc1b96198a",
    "2605-1114": "14b8f9b5197e5ae560eae1871f14e22c5893bc5212ef3e9f6b0bc54de5fb553b",
    "2615-1074": "4b4d3161eb2d8a22f2ea343e7c7e05d462596604783cc89b4df2e0de9babc045",
    "2615-1084": "4fce08e5a4baedd26b48fc60be795be739b3a43a7127d507ac012a5fdb9070be",
    "2615-1094": "a896fb0283828180bf2b7aa1a38d80036f62675dcb4194cc6f977260ddc8773d",
    "2615-1104": "7095aa3f1847f6f771e33f71d768d7c85432aeaafa93ac2dfe54089371706255",
    "2615-1114": "3a90cb977a2075cd3b824b83c5590cfde574a30a2669e8ab20fc5e5af0123462",
    "2625-1074": "7d0d2362eb4a49c31f247c86b5fec7fd640d7ffe342e7e5fa10fc481095b6b0f",
    "2625-1084": "0d2df9f5bab25a684812a2eb3ef0e76cb3aa217740e4ffa338e34b8caf453912",
    "2625-1094": "f01770a3e8eff0c6e5ecbfab54136fb56a449770c9d8f4004cebe4cbaa84ea41",
    "2625-1104": "8b3f8dbde5eb7076782707ea3a976a649a41f398fbfa37c8767efa1030d8ad3c",
    "2625-1114": "dc8510ce0cabbae5df5544557964477da6c0178ad34bde020246b09146c1235c",
    "2635-1074": "405060a42ba8a91d4933dfcf283230abbfa980dbcd95dfaba33f5ed56da0b5b0",
    "2635-1084": "56e6730dd5b56b5e90a9ce858d3a65cbbcd59e0d896097c5452a86b0da446d29",
    "2635-1094": "4ea2317333f96f011821e970d3f44b7968da519fc11d968c9aa91e5d5d8b4487",
    "2635-1104": "504f406371f3d4a5d912d0f7acdd92396b7c491ea8f06456de99c265cf3c5fcd",
    "2635-1114": "2aeb555f7741bb2e32a4b3c3b63236c6911b92e4f9c64e9439235be83b5ecc9a",
    "2645-1074": "01fe2984579e028bd0a30452ffd9756ce885ab29a6bf9d5ad562a765a10063f6",
    "2645-1084": "88d248076158d867c725567132be24f8aec8b9d8b868e330d8860899d90306e8",
    "2645-1094": "ea898dc0245eebf59cb8b5728f055f79d4038b37fc031b86aa114b947648830c",
    "2645-1104": "8faffb1dcacbe4da7a9428d78a7245683a0327a3165e90e2a376f1853439409b",
    "2645-1114": "fe22c00a968d3960f9be1aede2c3bd4d175b76e5a18800319b53b485cfc11fc0",
}
ENTRY_SHA256 = "9afdf81d58968b902b85e46b1ef9134dd30040114a73ad16940051246caaf908"
EXPECTED = {
    "collection": "ch.swisstopo.swissaltiregio",
    "edition": "2026-06",
    "resolution_m": 10,
    "tiles": {
        tile: {"file": f"swissaltiregio_{tile}_2056_5728.xyz.zip", "sha256": sha}
        for tile, sha in TILES.items()
    },
}


def test_the_committed_lock_pins_the_measured_entry():
    datasets = load_lock()["datasets"]
    assert set(datasets) == {
        "swissaltiregio",
        "swissalti3d",
        "swissbuildings3d",
        "swissimage",
        "swisssurface3d",
        "swisstlm3d",
    }
    assert datasets["swissaltiregio"] == EXPECTED
    text = json.dumps(EXPECTED, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == ENTRY_SHA256
    assert entry_sha256(datasets["swissaltiregio"]) == ENTRY_SHA256
