"""Way 1 (plain Pillow, no mattini import): the fixture colour JPEG and the manifest block."""
import hashlib, io, json, sys
from pathlib import Path
from PIL import Image

repo = Path(sys.argv[1])
fx = repo / "tests/shared/surroundings_fixture"
COLS, ROWS = 15, 18
pix = bytearray()
for r in range(ROWS):
    for c in range(COLS):
        pix += bytes([60 + 9 * c + 2 * r, 90 + 5 * r, 150 - 4 * c + 3 * r])
img = Image.frombytes("RGB", (COLS, ROWS), bytes(pix))
out = io.BytesIO()
img.save(out, "JPEG", quality=92, subsampling=2, optimize=False, progressive=False)
jpeg = out.getvalue()
(fx / "generated/surroundings/fixture_colour.jpg").write_bytes(jpeg)
decoded = Image.open(io.BytesIO(jpeg)).convert("RGB").tobytes()
desc = json.loads((fx / "generated/surroundings/fixture.json").read_text("utf-8"))
block = dict(desc)
block.update({
    "colour_cell_m": 1000.0,
    "colour_columns": COLS,
    "colour_rows": ROWS,
    "colour_file": "surroundings/fixture_colour.jpg",
    "colour_format": "jpeg",
    "colour_pixels_sha256": hashlib.sha256(decoded).hexdigest(),
    "colour_sha256": hashlib.sha256(jpeg).hexdigest(),
    "colour_source": {
        "attribution": "© swisstopo (synthetic test colours, not SWISSIMAGE data)",
        "collection": "ch.swisstopo.swissimage-dop10",
        "dataset": "swissimage_far",
        "edition": "2023",
    },
    "filled_fraction": 0.2,
})
mpath = fx / "generated/manifest.json"
m = json.loads(mpath.read_text("utf-8"))
m["surroundings"] = block
mpath.write_text(json.dumps(m, indent=2, sort_keys=True, ensure_ascii=False) + "\n", "utf-8", newline="\n")
print(len(jpeg), block["colour_sha256"], block["colour_pixels_sha256"])
print(hashlib.sha256(mpath.read_bytes()).hexdigest(), len(mpath.read_bytes()))
