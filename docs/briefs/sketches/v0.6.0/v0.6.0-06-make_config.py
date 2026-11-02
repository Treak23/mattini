"""Way 2: the fixture's surroundings.json values from the throwaway steps."""
import hashlib, json, re, sys, tempfile
from pathlib import Path
repo = Path(sys.argv[1])
sys.path.insert(0, str(repo / "pipeline/tests"))
from synthetic_farphoto import FIXTURE, raw_inputs, fixture_datasets
from mattini.world import load_world
from mattini.lock import entry_sha256, entries_sha256
from mattini.surroundings import build_surroundings, SurroundingsError
from mattini.farcolour import colour_pixels
from mattini.photo import encode_jpeg
world = load_world(FIXTURE / "world.json")
wsha = hashlib.sha256((FIXTURE / "world.json").read_bytes()).hexdigest()
lock = json.loads((FIXTURE / "datasets.lock.json").read_text())
ds = fixture_datasets()
Z = "0" * 64
area = {"computed_for": {"inputs_sha256": entry_sha256(lock["datasets"]["swissaltiregio"]), "world_sha256": wsha},
        "expected_columns": 7, "expected_rows": 7,
        "expected_lv95_box": {"e_max": 2618000.0, "e_min": 2615000.0, "n_max": 1097000.0, "n_min": 1094000.0},
        "expected_sha256": Z, "margin_m": 1000, "spacing_m": 500}
cfg = {"schema": 2, "areas": {"fixture": area}}
with tempfile.TemporaryDirectory() as d:
    raw, _ = raw_inputs(Path(d) / "raw")
    try:
        build_surroundings(world, ds, lock, cfg, raw, Path(d) / "out")
    except SurroundingsError as e:
        area["expected_sha256"] = re.search(r"have SHA-256 ([0-9a-f]{64})", str(e)).group(1)
    blk = build_surroundings(world, ds, lock, cfg, raw, Path(d) / "out")
    heights = (Path(d) / "out/surroundings/fixture.f32").read_bytes()
    area["colour"] = {"band_m": 100, "cell_m": 100,
        "computed_for": {"inputs_sha256": entries_sha256(lock, ("swissaltiregio", "swissimage_far")), "world_sha256": wsha},
        "expected_columns": 30, "expected_rows": 30, "expected_filled_fraction": 0.0,
        "expected_pixels_sha256": Z, "expected_sha256": Z}
    pixels, covered, _ = colour_pixels(world, ds, lock, cfg, raw)
    area["colour"]["expected_pixels_sha256"] = hashlib.sha256(pixels.tobytes()).hexdigest()
    area["colour"]["expected_sha256"] = hashlib.sha256(encode_jpeg(pixels)).hexdigest()
    area["colour"]["expected_filled_fraction"] = int((~covered).sum()) / covered.size
(FIXTURE / "surroundings.json").write_bytes((json.dumps(cfg, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())
import numpy as np
print(json.dumps(area, indent=1)); print("heights", hashlib.sha256(heights).hexdigest(), np.frombuffer(heights, "<f4").reshape(7, 7))
np.save(Path(sys.argv[2]) / "fixture_pixels.npy", pixels)
