"""Pinning test for brief v0.6.0-06: the far colour's design data fits the committed lock, world
and datasets.

The seam between lanes A and B (lesson 3): the swissimage_far entry enters the committed lock in
brief v0.6.0-05 (`lock farphoto`), the swissaltiregio entry in v0.6.0-01; config/surroundings.json's
`colour` (design §5) records both, `computed_for.inputs_sha256` being the canonical SHA-256 over
{swissaltiregio, swissimage_far} (SPEC §8, `lock.entries_sha256`), computed here without the
pipeline's helper so a wrong canonical form would not agree with itself (lesson 34). The cell is
the swissALTIRegio sample spacing and five SWISSIMAGE 2 m pixels (design §2); the absent cells
are the filled ones.

Does NOT prove: that the expected pixels and JPEG are right (two ways at the pin author's real
run; the step's own comparison at the brief's real run and the release gate).
"""

import hashlib
import json

from mattini.world import REPO

LOCK = json.loads((REPO / "config" / "datasets.lock.json").read_text(encoding="utf-8"))
CONFIG = json.loads((REPO / "config" / "surroundings.json").read_text(encoding="utf-8"))
DATASETS = json.loads((REPO / "config" / "datasets.json").read_text(encoding="utf-8"))["datasets"]


def _colour():
    ((_, settings),) = CONFIG["areas"].items()
    return settings, settings["colour"]


def test_the_colour_was_computed_for_the_committed_entries_and_world():
    _, colour = _colour()
    both = {name: LOCK["datasets"][name] for name in ("swissaltiregio", "swissimage_far")}
    canonical = json.dumps(both, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    world = (REPO / "config" / "world.json").read_bytes()
    assert colour["computed_for"] == {
        "inputs_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "world_sha256": hashlib.sha256(world).hexdigest(),
    }


def test_the_cell_is_the_sample_spacing_and_five_source_pixels():
    _, colour = _colour()
    assert colour["cell_m"] == DATASETS["swissaltiregio"]["resolution_m"] == 10
    assert colour["cell_m"] == 5 * DATASETS["swissimage_far"]["resolution_m"]
    assert colour["band_m"] == 100


def test_the_filled_fraction_is_the_lock_s_absent_cells():
    settings, colour = _colour()
    far = LOCK["datasets"]["swissimage_far"]
    box = settings["expected_lv95_box"]
    cells = (box["e_max"] - box["e_min"]) / 1000 * (box["n_max"] - box["n_min"]) / 1000
    assert len(far["tiles"]) + len(far["absent"]) == cells == 1806
    assert colour["expected_filled_fraction"] == len(far["absent"]) / cells
    per_cell = (1000 // colour["cell_m"]) ** 2
    total = colour["expected_columns"] * colour["expected_rows"]
    assert colour["expected_filled_fraction"] == len(far["absent"]) * per_cell / total
