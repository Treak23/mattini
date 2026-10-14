"""Pinning tests for brief M3-01 (M2 V1-P-08): the lock's two forms, told from their twins.

Pinned decisions (docs/SPEC.md §5, the lock; §8, computed_for): a lock entry's SHA-256
(`lock.entry_sha256`, which `computed_for.inputs_sha256` records) is that of
`json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` in UTF-8,
and the lock file `write_lock` writes is `json.dumps(lock, indent=2, sort_keys=True,
ensure_ascii=False)` and a final LF, in UTF-8. Both are pinned here as exact bytes, written
out by hand, for an entry whose keys come in reverse order and whose collection holds a
non-ASCII letter (U+00E4, two bytes in UTF-8). Every lock the tests wrote before had its
keys sorted already and only ASCII, so a form without sort_keys, an ASCII-escaped one
(`\\u00e4`) or one with other separators gave the same bytes there (lesson 34). The
digest of the canonical text was computed two ways (Python's hashlib on this literal, and
coreutils' sha256sum on its bytes): 2cc3bd25…3111.

Does NOT prove: that design's recorded values in config/terrain.json and
config/buildings.json are right (test_expected_inputs.py ties them to the lock).
"""

import hashlib
import json

from mattini.lock import entry_sha256, validate_lock, write_lock

A = "a6ea488ecbb54b97100f22d867c38b8cd1efc37b68d61f175c98e53fb2c810ca"
B = "57f12bcf71d823f32a3186667f8d7dbbfac80e2335454fd4d505dd17ce6e08aa"
FILE_A = "swissalti3d_2024_2623-1095_0.5_2056_5728.tif"
FILE_B = "swissalti3d_2024_2624-1095_0.5_2056_5728.tif"
COLLECTION = "ch.swisstopo.swissälti3d"  # a non-ASCII letter where the lock allows one


def _reversed_entry() -> dict:
    """The entry with every object's keys inserted in reverse sorted order."""
    return {
        "tiles": {
            "2624-1095": {"sha256": B, "file": FILE_B},
            "2623-1095": {"sha256": A, "file": FILE_A},
        },
        "resolution_m": 0.5,
        "edition": "2024",
        "collection": COLLECTION,
    }


CANONICAL = (
    '{"collection":"ch.swisstopo.swissälti3d","edition":"2024","resolution_m":0.5,'
    f'"tiles":{{"2623-1095":{{"file":"{FILE_A}","sha256":"{A}"}},'
    f'"2624-1095":{{"file":"{FILE_B}","sha256":"{B}"}}}}}}'
)
CANONICAL_SHA256 = "2cc3bd2576f1805844e4b1f2bbf819150fe477a13f9e5cd1517c87639e053111"

LOCK_FILE = f"""{{
  "datasets": {{
    "swissalti3d": {{
      "collection": "ch.swisstopo.swissälti3d",
      "edition": "2024",
      "resolution_m": 0.5,
      "tiles": {{
        "2623-1095": {{
          "file": "{FILE_A}",
          "sha256": "{A}"
        }},
        "2624-1095": {{
          "file": "{FILE_B}",
          "sha256": "{B}"
        }}
      }}
    }}
  }},
  "schema": 1
}}
"""


def test_the_canonical_text_is_the_one_written_out_here():
    """The literal itself: its digest, and its non-ASCII letter as two UTF-8 bytes."""
    data = CANONICAL.encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == CANONICAL_SHA256
    assert b"\xc3\xa4" in data and b"\\u00e4" not in data


def test_an_entry_s_sha256_is_that_of_its_canonical_text_whatever_its_key_order():
    entry = _reversed_entry()
    assert list(entry) != sorted(entry)  # the twin without sort_keys would see this order
    assert entry_sha256(entry) == CANONICAL_SHA256
    assert entry_sha256(json.loads(CANONICAL)) == CANONICAL_SHA256


def test_the_lock_file_is_sorted_utf_8_with_two_space_indent_and_a_final_lf(tmp_path):
    lock = {"schema": 1, "datasets": {"swissalti3d": _reversed_entry()}}
    validate_lock(lock, "test")  # a lock the pipeline accepts
    path = write_lock(lock, tmp_path / "datasets.lock.json")
    assert path.read_bytes() == LOCK_FILE.encode("utf-8")
    assert json.loads(path.read_bytes())["datasets"]["swissalti3d"] == json.loads(CANONICAL)
