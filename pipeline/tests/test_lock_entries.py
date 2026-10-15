"""Pinning tests for brief M3-13: `lock.entries_sha256`, the several-datasets rule's one home.

Pinned decisions (docs/SPEC.md §8, *Roof colours*, the inputs of a step with several
datasets; brief M3-13): `lock.entries_sha256(lock, names)` is the SHA-256 of
`json.dumps({name: lock["datasets"][name] for name in names}, sort_keys=True,
separators=(",", ":"), ensure_ascii=False)` in UTF-8, over exactly the named datasets, in
no order of their own: what `computed_for.inputs_sha256` records for the roofs (swissbuildings3d,
swissimage) and the trees (swissalti3d, swissbuildings3d, swisssurface3d, swisstlm3d). A
step with one dataset keeps `lock.entry_sha256`. The canonical text is written out here by
hand for a lock whose every object has its keys in reverse order, whose names come
reversed, that holds a third entry not named, and whose collection holds a non-ASCII letter
(U+00FC, two bytes in UTF-8); its digest was computed two ways (Python's hashlib on this
literal, coreutils' sha256sum on its bytes): 6deda5af…34b5. The committed lock gives the
values config/roofs.json and config/trees.json record (measured by design's inputs agent,
e66bee6e… and 1eb7b79e…). And the canonical form is written in one module only, lock.py:
roofs.py and trees.py call `entries_sha256`, so a second copy of the rule cannot drift.

Harm prevented: a roofs or trees step whose own copy of the rule (unsorted, ASCII-escaped,
spaced, hashed entry by entry, or over the whole lock) records or compares another value,
so the design-change refusal fires for nothing, or not at all.

Does NOT prove: that design's recorded values are the right inputs (test_expected_inputs_m3.py
ties them to the committed lock).
"""

import hashlib
import json
from pathlib import Path

from mattini.lock import entries_sha256, entry_sha256, load_lock

REPO = Path(__file__).resolve().parents[2]
A = "49397f69d28bbab566fd6618090a088d0661f64551aca8b7d98da55ca16bd47b"
B = "0913fdfc65ea5a1468d6d7ee857ad800040afb3516754570aec270b3756bb285"
C = "bd8f1a0b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6e7"
FA = "swissimage-dop10_2023_2623-1095_0.1_2056.tif"
FB = "swissimage-dop10_2023_2624-1095_0.1_2056.tif"
FC = "swissbuildings3d_3_0_2020_1348-11_2056_5728.gdb.zip"


def _reversed_lock() -> dict:
    """Every object's keys inserted in reverse sorted order; a third entry not named."""
    return {
        "schema": 1,
        "datasets": {
            "swisstlm3d": {
                "sha256": "cd" * 32,
                "file": "swisstlm3d_2026-02_2056_5728.gdb.zip",
                "edition": "2026-02",
                "collection": "ch.swisstopo.swisstlm3d",
            },
            "swissimage": {
                "tiles": {
                    "2624-1095": {"sha256": B, "file": FB},
                    "2623-1095": {"sha256": A, "file": FA},
                },
                "resolution_m": 0.1,
                "edition": "2023",
                "collection": "ch.swisstopo.swissimage-dop10",
            },
            "swissbuildings3d": {
                "sheets": {"1348-11": {"sha256": C, "file": FC}},
                "edition": "2020",
                "collection": "ch.swisstopo.swissbüildings3d_3_0",
            },
        },
    }


CANONICAL = (
    '{"swissbuildings3d":{"collection":"ch.swisstopo.swissbüildings3d_3_0","edition":"2020",'
    f'"sheets":{{"1348-11":{{"file":"{FC}","sha256":"{C}"}}}}}},'
    '"swissimage":{"collection":"ch.swisstopo.swissimage-dop10","edition":"2023",'
    f'"resolution_m":0.1,"tiles":{{"2623-1095":{{"file":"{FA}","sha256":"{A}"}},'
    f'"2624-1095":{{"file":"{FB}","sha256":"{B}"}}}}}}}}'
)
CANONICAL_SHA256 = "6deda5af97c0327548612250481d8305bbfb2f04176e0c0c04d870927a1234b5"
ROOFS = ("swissbuildings3d", "swissimage")
TREES = ("swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d")


def test_the_canonical_text_is_the_one_written_out_here():
    data = CANONICAL.encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == CANONICAL_SHA256
    assert b"\xc3\xbc" in data and b"\\u00fc" not in data


def test_entries_sha256_is_that_of_the_named_entries_canonical_text():
    lock = _reversed_lock()
    assert list(lock["datasets"]) != sorted(lock["datasets"])
    assert entries_sha256(lock, ["swissimage", "swissbuildings3d"]) == CANONICAL_SHA256
    assert entries_sha256(lock, ROOFS) == CANONICAL_SHA256
    one_by_one = hashlib.sha256(
        "".join(entry_sha256(lock["datasets"][name]) for name in ROOFS).encode()
    ).hexdigest()
    assert CANONICAL_SHA256 != one_by_one  # the twin hashing entry by entry


def test_the_committed_lock_gives_the_recorded_roofs_and_trees_inputs():
    lock = load_lock(REPO / "config" / "datasets.lock.json")
    roofs = "e66bee6eefdf491cbcf1dcca8ca87632d0779802f777b1caedc4a09009ca9a48"
    trees = "1eb7b79e450774e7aec8f15ebed4b8600c864de1f61d2813c49e967ad079164a"
    assert entries_sha256(lock, ROOFS) == roofs
    assert entries_sha256(lock, TREES) == trees
    for config, value in (("roofs.json", roofs), ("trees.json", trees)):
        recorded = json.loads((REPO / "config" / config).read_text(encoding="utf-8"))
        assert recorded["areas"]["village"]["computed_for"]["inputs_sha256"] == value, config


def test_the_canonical_form_is_written_in_lock_py_only():
    """A census of the package: the rule's separators appear in lock.py and nowhere else."""
    canonical = 'separators=(",", ":")'
    found = sorted(
        path.name
        for path in (REPO / "pipeline" / "mattini").glob("*.py")
        if canonical in path.read_text(encoding="utf-8")
    )
    assert found == ["lock.py"], found
