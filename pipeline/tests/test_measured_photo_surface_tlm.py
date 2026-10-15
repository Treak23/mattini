"""Pinning tests for brief M3-03: the committed lock pins the village's measured inputs.

Pinned decisions (docs/SPEC.md §5; lesson 38): config/datasets.lock.json, written by
`python -m mattini lock photo`, `lock surface` and `lock tlm` against the live STAC API and
committed, holds exactly the entries design read on 2026-10-14, two ways that agree: the
STAC items (`file:checksum`, published in upper-case hex) and the SHA-256 of the files
themselves (equal to the file host's `x-amz-meta-sha256`). swissSURFACE3D publishes the
village's tile 2623-1095 in 2022 only and the five others in 2021 only. The canonical
SHA-256 of each entry (`lock.entry_sha256`, the form SPEC §8 fixes) is what the expected
values of the steps that read it record as `computed_for.inputs_sha256` (photo, surfaces)
or combine with other entries (roofs, trees).

Does NOT prove: that swisstopo still publishes these files (`pytest -m network` does).
"""

import hashlib
import json

from mattini.lock import entry_sha256, load_lock

PHOTO = {  # tile: SHA-256 of swissimage-dop10_2023_<tile>_0.1_2056.tif
    "2623-1095": "49397f69d28bbab566fd6618090a088d0661f64551aca8b7d98da55ca16bd47b",
    "2623-1096": "9fb6d0cfcbcb4119e602821ae1a88da9d027bf477a807784bd7068dc1877335a",
    "2623-1097": "e491d7198993a5f515b886f6f3234efeebdad958afffe6a7b8643e2189c594d0",
    "2624-1095": "0913fdfc65ea5a1468d6d7ee857ad800040afb3516754570aec270b3756bb285",
    "2624-1096": "adf3ef9d934c3947a1c12b5e45a4dc48b7b2655b6aa8ecb11785d6ec281c817d",
    "2624-1097": "b911565192a58e408e9dc9bdad33f93ba30ac8022294bc727eb0c8919bb41d5b",
}
SURFACE = {  # tile: (edition, SHA-256 of swisssurface3d-raster_<edition>_<tile>_0.5_2056_5728.tif)
    "2623-1095": ("2022", "5cb9ad15b887de6b15c3371119c276b00ae75053ad27a5ee2e9ae19d3276b3d0"),
    "2623-1096": ("2021", "34657277bb0380973aab9b6abedec3e9946228fbadebd7192a00cd910c3c8771"),
    "2623-1097": ("2021", "d20fc78b1fbf096da544c91a6536d74cf911ce793dfe1ca5c8cf1a016dce464f"),
    "2624-1095": ("2021", "575090d21fb3a1fd1676bd030d825610fcbee75bc129eec9afe5726e1ecab391"),
    "2624-1096": ("2021", "17d6ba7e75b972c2abcb014563760a435cc992f1e2a8c274936b0c291c67e582"),
    "2624-1097": ("2021", "62d4b06901dc900f00c31cc230cda614f78913aa1e84c19cfa2e5ac054497571"),
}
TLM = "185ffca883e7a2d6be4ea3d1f62ee4d1a09f07fe90e381738fdcb3a849df28da"  # 2'882'823'552 bytes
ENTRY_SHA256 = {
    "swissimage": "415ed9bcbee7b5d719f40f5b105204dc38ebc570cd2973ebc9de199d86f30fdd",
    "swisssurface3d": "f73033b19c5ff89a1cff469d2777e9a9b4f91226eada171669017bf7c030f748",
    "swisstlm3d": "aa909f98c8abc2653875cf6c8b4857a01f3d095dcaa3d3d5991ccb16b6594ba2",
}
EXPECTED = {
    "swissimage": {
        "collection": "ch.swisstopo.swissimage-dop10",
        "edition": "2023",
        "resolution_m": 0.1,
        "tiles": {
            tile: {"file": f"swissimage-dop10_2023_{tile}_0.1_2056.tif", "sha256": sha}
            for tile, sha in PHOTO.items()
        },
    },
    "swisssurface3d": {
        "collection": "ch.swisstopo.swisssurface3d-raster",
        "resolution_m": 0.5,
        "tiles": {
            tile: {
                "edition": year,
                "file": f"swisssurface3d-raster_{year}_{tile}_0.5_2056_5728.tif",
                "sha256": sha,
            }
            for tile, (year, sha) in SURFACE.items()
        },
    },
    "swisstlm3d": {
        "collection": "ch.swisstopo.swisstlm3d",
        "edition": "2026-02",
        "file": "swisstlm3d_2026-02_2056_5728.gdb.zip",
        "sha256": TLM,
    },
}


def test_the_committed_lock_pins_the_measured_entries():
    datasets = load_lock()["datasets"]
    assert set(datasets) == {
        "swissalti3d",
        "swissbuildings3d",
        "swissimage",
        "swisssurface3d",
        "swisstlm3d",
    }
    for name, entry in EXPECTED.items():
        assert datasets[name] == entry, name
        text = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == ENTRY_SHA256[name], name
        assert entry_sha256(datasets[name]) == ENTRY_SHA256[name], name
