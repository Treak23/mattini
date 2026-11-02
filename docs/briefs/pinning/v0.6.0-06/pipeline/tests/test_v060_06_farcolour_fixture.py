"""Pinning tests for brief v0.6.0-06: the far colour fixture is design's rule written out.

The fixture (tests/shared/farcolour_fixture/, design data of this brief; synthetic, no swisstopo
data) is a scaled-down village: an area of 1 km grown by a 1000 m margin to a 3 km box; colour
pixels of 100 m (30 × 30) over 1 km SWISSIMAGE cells of 20 m source pixels (5 × 5 to a pixel, as
the village's 2 m to 10 m), swissALTIRegio samples at 100 m on the pixel centres, 100 m bands. Of
its nine cells three have no item (a stepped south-east, as Italy's), so 300 of 900 pixels are
filled. It decides design §2's rule:

- covered pixels lie in exactly two bands, 21 (2100–2199 m) and 23; filled pixels lie in bands
  19 (none below with cover: the nearest above, 21), 21 and 23 (their own), 22 (empty, equally
  near 21 and 23: below first, 21), 24 and 25 (empty, above every covered band: the nearest below,
  23, skipping 24);
- samples on band edges: 2200.00 m (band 22), 2299.99 m (band 22), 2400.00 m (band 24);
- band 21's red sum over its 300 covered pixels is 16950, an exact half (56.5): the half-up
  integer mean 57 (the session's reading of design's "integer mean", the same rounding as
  (sum + 12) // 25) differs from floor and from half-to-even (56);
- the world's height offset is 1250.25 m: a band taken from the height minus the offset is
  another band;
- the area's own box is a covered cell: not cut (design §2).

Its expected values (`surroundings.json`'s `colour`) were computed by the pin author two ways that
share no code: the throwaway step, and plain Python (no numpy, no mattini) from source.json and
photo.u8; the vectors (tests/shared/farcolour_vectors.json) come from the second. This file
computes the pixels a third way (numpy, here) and shows that the likeliest wrong twins each change
them. The fixture files' SHA-256s are pinned, so a fixture rewritten by the code under test fails
(lesson 33).

Does NOT prove: that the step computes them (test_v060_06_farcolour_step.py); the village's
values (the step's own comparison at the brief's real run and the release gate).
"""

import hashlib
import json
from decimal import Decimal

import numpy as np
import pytest
from synthetic_farphoto import FIXTURE, fixture_photo, fixture_source, raw_inputs

from mattini.photo import encode_jpeg
from mattini.surroundings import build_surroundings, load_surroundings_config
from mattini.world import REPO, load_world

VECTORS = REPO / "tests" / "shared" / "farcolour_vectors.json"
FILES = {
    "datasets.json": "6219969d1e5c454a67ec407eac7b06d7283b411cf67ee166873186c485a09b89",
    "datasets.lock.json": "166382bd53b51fba13b31619df2aa11579c206c70f0e3d4a32f535674eb23514",
    "photo.u8": "d9ee40cdfcfa550ad4c73f278b0414d4ed8513c8a888fa179dac95ad25420ee4",
    "source.json": "4973fc5ddfc3869d5df1557cfd687437f6f6d93289dca791f7d70db9909c31e2",
    "surroundings.json": "efcf350979d33fb9e4d097d75f67be90cff3f3ad6fc530587949205a6cfc5a85",
    "world.json": "16a33fa5549cb04214a08d37bc53ea743d608962678d00bc4820ce3438424a21",
}
VECTORS_SHA256 = "7845e750878f33534e56d86d6c553a962f9d99c8b0f386eb82a0be86a3662393"
CELL, BLOCK, ROWS, COLUMNS = 100, 5, 30, 30
E_MIN, N_MAX = 2_615_000, 1_097_000


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _config() -> dict:
    return load_surroundings_config(FIXTURE / "surroundings.json")


def _colour() -> dict:
    return _config()["areas"]["fixture"]["colour"]


def _samples() -> np.ndarray:
    """The sample at every pixel centre, in whole centimetres (Decimal, not float)."""
    found = {}
    for tile in fixture_source()["regio"]["tiles"].values():
        for line in tile["text"].split("\r\n")[1:-1]:
            x, y, z = line.split(" ")
            found[int(x), int(y)] = int(Decimal(z) * 100)
    cents = np.zeros((ROWS, COLUMNS), np.int64)
    for r in range(ROWS):
        for c in range(COLUMNS):
            cents[r, c] = found[E_MIN + CELL // 2 + CELL * c, N_MAX - CELL // 2 - CELL * r]
    return cents


def _covered() -> np.ndarray:
    absent = set(fixture_source()["absent"])
    covered = np.zeros((ROWS, COLUMNS), bool)
    for r in range(ROWS):
        for c in range(COLUMNS):
            covered[r, c] = f"{2615 + c // 10}-{1096 - r // 10}" not in absent
    return covered


def _pixels(variant: str = "design") -> np.ndarray:
    """design §2's colour of the fixture, or one wrong twin of it."""
    photo = fixture_photo().astype(np.int64)
    if variant == "block-shifted":
        photo = np.roll(photo, 1, axis=1)
    sums = photo.reshape(ROWS, BLOCK, COLUMNS, BLOCK, 3).sum(axis=(1, 3))
    means = sums // 25 if variant == "block-floor" else (sums + 12) // 25
    covered, cents = _covered(), _samples()
    if variant == "band-from-offset-height":
        cents = cents - 125_025
    band = (np.rint(cents / 10_000) if variant == "band-rounded" else cents // 10_000).astype(int)
    bands = sorted(set(band[covered].tolist()))
    mean = {}
    for b in bands:
        if variant == "band-mean-of-source-pixels":
            mask = np.repeat(np.repeat(covered & (band == b), BLOCK, 0), BLOCK, 1)
            n, total = int(mask.sum()), photo[mask].sum(axis=0)
        else:
            mask = covered & (band == b)
            n, total = int(mask.sum()), means[mask].sum(axis=0)
        if variant == "band-mean-floor":
            mean[b] = total // n
        elif variant == "band-mean-half-even":
            mean[b] = np.array([round(v / n) for v in total.tolist()])  # Python rounds to even
        else:
            mean[b] = (total + n // 2) // n
    if variant == "one-mean-for-all":
        n = int(covered.sum())
        mean = {b: (means[covered].sum(axis=0) + n // 2) // n for b in bands}

    def taken(b: int) -> int:
        if b in mean:
            return b
        below, above = [x for x in bands if x < b], [x for x in bands if x > b]
        if variant == "above-first":
            return min(above) if above else max(below)
        if variant == "nearest-ties-above":
            return min(bands, key=lambda x: (abs(x - b), -x))
        return max(below) if below else min(above)

    out = np.zeros((ROWS, COLUMNS, 3), np.int64)
    for r in range(ROWS):
        for c in range(COLUMNS):
            out[r, c] = means[r, c] if covered[r, c] else mean[taken(int(band[r, c]))]
    if variant == "area-cut":
        out[10:20, 10:20] = 0
    if variant == "flip-north-south":
        out = out[::-1]
    if variant == "flip-east-west":
        out = out[:, ::-1]
    return out.astype(np.uint8)


def test_the_fixture_files_are_design_s_bytes():
    for name, sha256 in FILES.items():
        assert _sha((FIXTURE / name).read_bytes()) == sha256, name
    assert _sha(VECTORS.read_bytes()) == VECTORS_SHA256


def test_the_lock_pins_what_synthetic_farphoto_writes(tmp_path):
    _, lock = raw_inputs(tmp_path / "raw")
    committed = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    assert lock["datasets"] == committed["datasets"]
    far = committed["datasets"]["swissimage_far"]
    assert far["absent"] == ["2616-1094", "2617-1094", "2617-1095"]
    assert len(far["tiles"]) == 6 and far["resolution_m"] == 20


def test_computed_for_records_the_fixture_s_world_and_both_entries():
    """The canonical form computed here, not with `lock.entries_sha256` (lesson 34)."""
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    both = {name: lock["datasets"][name] for name in ("swissaltiregio", "swissimage_far")}
    text = json.dumps(both, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    world = _sha((FIXTURE / "world.json").read_bytes())
    assert _colour()["computed_for"] == {
        "inputs_sha256": _sha(text.encode("utf-8")),
        "world_sha256": world,
    }


def test_the_heights_part_is_the_surroundings_step_s(tmp_path):
    """The fixture's heights values hold (v0.6.0-04's step compares them before writing)."""
    root, lock = raw_inputs(tmp_path / "raw")
    world = load_world(FIXTURE / "world.json")
    datasets = json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]
    block = build_surroundings(world, datasets, lock, _config(), root, tmp_path / "out")
    assert (block["columns"], block["rows"]) == (7, 7)
    assert block["sha256"] == _config()["areas"]["fixture"]["expected_sha256"]


def test_the_expected_colour_is_the_rule_written_out():
    colour = _colour()
    pixels = _pixels()
    assert (colour["expected_columns"], colour["expected_rows"]) == (COLUMNS, ROWS)
    assert (colour["cell_m"], colour["band_m"]) == (100, 100)
    assert _sha(pixels.tobytes()) == colour["expected_pixels_sha256"]
    assert _sha(encode_jpeg(pixels)) == colour["expected_sha256"]
    assert colour["expected_filled_fraction"] == 300 / 900
    assert type(colour["expected_filled_fraction"]) is float


def test_the_named_pixels_are_the_vectors():
    vectors = json.loads(VECTORS.read_text(encoding="utf-8"))
    pixels, cents, covered = _pixels(), _samples(), _covered()
    assert len(vectors["pixels"]) == 13
    for v in vectors["pixels"]:
        r, c = v["row"], v["column"]
        assert v["lv95"] == [E_MIN + 50 + 100 * c, N_MAX - 50 - 100 * r], v["name"]
        assert v["covered"] == bool(covered[r, c]), v["name"]
        assert v["sample_cm"] == int(cents[r, c]) and v["band"] == int(cents[r, c]) // 10_000
        assert v["rgb"] == pixels[r, c].tolist(), v["name"]


def test_the_fixture_decides_the_band_rule():
    covered, cents = _covered(), _samples()
    band = cents // 10_000
    assert covered.sum() == 600 and sorted(set(band[covered].tolist())) == [21, 23]
    assert sorted(set(band[~covered].tolist())) == [19, 21, 22, 23, 24, 25]
    for r, c, cm in ((15, 20, 220_000), (19, 29, 229_999), (25, 20, 240_000)):
        assert cents[r, c] == cm and not covered[r, c]
    means = (
        fixture_photo().astype(np.int64).reshape(ROWS, 5, COLUMNS, 5, 3).sum((1, 3)) + 12
    ) // 25
    red = int(means[covered & (band == 21)][:, 0].sum())
    assert red == 16950 and red % 300 == 150 and (red // 300) % 2 == 0
    assert covered[10:20, 10:20].all()  # the area's own box


@pytest.mark.parametrize(
    "variant",
    [
        "flip-north-south",
        "flip-east-west",
        "block-floor",
        "block-shifted",
        "band-rounded",
        "band-from-offset-height",
        "band-mean-floor",
        "band-mean-half-even",
        "band-mean-of-source-pixels",
        "one-mean-for-all",
        "above-first",
        "nearest-ties-above",
        "area-cut",
    ],
)
def test_the_likeliest_wrong_twins_change_the_pixels(variant):
    assert _sha(_pixels(variant).tobytes()) != _colour()["expected_pixels_sha256"], variant
