"""Pinning tests for brief M4-03: config/shadows.json holds design's village and what it was computed for.

Pinned decisions (m4-design §3, the brief's Decisions; lessons 38 and 41): config/shadows.json is
exactly {"schema": 1, "cell_m": 1, "sun": {azimuth_grid_deg, elevation_deg, note}, "threshold_m":
0.05, "areas": {<area>: {"computed_for": {inputs_sha256, world_sha256}, "expected_pixels_sha256",
"expected_png_sha256"}}}, its one area the terrain config's. `inputs_sha256` is the SHA-256 of
the lock's `swisssurface3d` entry rendered canonically (json.dumps(entry, sort_keys=True,
separators=(",", ":"), ensure_ascii=False) in UTF-8, as `lock.entry_sha256`), `world_sha256` that
of config/world.json's bytes, both computed here without the pipeline's code. The sun's grid
azimuth is the flight's mean true azimuth, 184.9 degrees, plus config/sky.json's
`true_to_grid_deg` (-0.2258: grid north lies east of true north at the village), to 0.01
degree. Design computed the village's mask two independent ways and cell by cell on 43'200
cells (identical; 2026-10-17): 2000 x 3000 cells, 32.05 % in cast or own shadow, 20.45 % kept
by the inset; its PNG is 319'479 bytes with zlib 1.3.

Does NOT prove: that this machine computes that mask (the step's own comparison does, at the
brief's real run); that the mask lies on the photo's shadows (the owner's eyes).
"""

import hashlib
import json
from pathlib import Path

from mattini.shadows import load_shadows_config

REPO = Path(__file__).resolve().parents[2]
VILLAGE = {
    "computed_for": {
        "inputs_sha256": "f73033b19c5ff89a1cff469d2777e9a9b4f91226eada171669017bf7c030f748",
        "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
    },
    "expected_pixels_sha256": "6f958c41f34ebc58847baefe9a386e19c6b4edf3835327bb5c11eb69526b7aa6",
    "expected_png_sha256": "5fff6e5833156bcdfc1d45060aa83ee86e9a1cf336d861d57f9c773fc7fa4df3",
}
TRUE_AZIMUTH = 184.9  # m4-design §0: the flight's mean sun, true north


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_committed_config_expects_design_s_village():
    config = load_shadows_config(REPO / "config" / "shadows.json")
    assert set(config) == {"schema", "cell_m", "sun", "threshold_m", "areas"}
    assert (config["schema"], config["cell_m"], config["threshold_m"]) == (1, 1, 0.05)
    assert config["areas"] == {"village": VILLAGE}
    sun = config["sun"]
    assert set(sun) == {"azimuth_grid_deg", "elevation_deg", "note"}
    assert (sun["azimuth_grid_deg"], sun["elevation_deg"]) == (184.67, 50.1)
    terrain = json.loads((REPO / "config" / "terrain.json").read_text("utf-8"))
    assert list(config["areas"]) == list(terrain["areas"]), "the one area is the terrain's"


def test_computed_for_is_this_world_and_this_lock():
    assert VILLAGE["computed_for"]["world_sha256"] == _sha(
        (REPO / "config" / "world.json").read_bytes()
    )
    lock = json.loads((REPO / "config" / "datasets.lock.json").read_text("utf-8"))
    entry = lock["datasets"]["swisssurface3d"]
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert VILLAGE["computed_for"]["inputs_sha256"] == _sha(canonical.encode("utf-8"))


def test_the_sun_s_grid_azimuth_is_the_true_one_turned_by_the_sky_config():
    sky = json.loads((REPO / "config" / "sky.json").read_text("utf-8"))
    turn = sky["areas"]["village"]["true_to_grid_deg"]
    config = load_shadows_config(REPO / "config" / "shadows.json")
    assert round(TRUE_AZIMUTH + turn, 2) == config["sun"]["azimuth_grid_deg"]
    assert config["sun"]["azimuth_grid_deg"] < TRUE_AZIMUTH, "grid north lies east of true north"
