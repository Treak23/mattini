"""Way 1 of the fixture colour: plain Python from source.json and photo.u8 (no numpy, no mattini)."""
import hashlib, io, json, sys
from decimal import Decimal
from pathlib import Path
from PIL import Image
fx = Path(sys.argv[1]) / "tests/shared/farcolour_fixture"
src = json.loads((fx / "source.json").read_text())
cfg = json.loads((fx / "surroundings.json").read_text())["areas"]["fixture"]
photo = (fx / "photo.u8").read_bytes()
P = src["photo"]; W = P["columns"]
E0, N1 = 2615000, 1097000
cell, k = 100, 5
cols = rows = 30
H = {}
for t in src["regio"]["tiles"].values():
    for line in t["text"].split("\r\n")[1:-1]:
        x, y, z = line.split(" ")
        H[(int(x), int(y))] = int(Decimal(z) * 100)
absent = set(src["absent"])
pix, cov, cm = {}, {}, {}
for r in range(rows):
    for c in range(cols):
        cellid = f"{2615 + c // 10}-{1096 - r // 10}"
        cov[r, c] = cellid not in absent
        cm[r, c] = H[(E0 + 50 + 100 * c, N1 - 50 - 100 * r)]
        if cov[r, c]:
            px = []
            for ch in range(3):
                s = sum(photo[3 * ((k * r + i) * W + k * c + j) + ch] for i in range(k) for j in range(k))
                px.append((s + 12) // 25)
            pix[r, c] = tuple(px)
band = {p: cm[p] // 10000 for p in cm}
sums = {}
for p in cm:
    if cov[p]:
        b = band[p]; n, s = sums.get(b, (0, [0, 0, 0]))
        sums[b] = (n + 1, [s[i] + pix[p][i] for i in range(3)])
mean = {b: tuple((s[i] + n // 2) // n for i in range(3)) for b, (n, s) in sums.items()}
def source_band(b):
    below = [x for x in mean if x < b]
    if b in mean: return b
    if below: return max(below)
    return min(x for x in mean if x > b)
out = bytearray(); used = {}
for r in range(rows):
    for c in range(cols):
        if cov[r, c]:
            out += bytes(pix[r, c])
        else:
            sb = source_band(band[r, c]); used.setdefault(band[r, c], sb)
            out += bytes(mean[sb])
im = Image.frombytes("RGB", (cols, rows), bytes(out)); o = io.BytesIO()
im.save(o, "JPEG", quality=92, subsampling=2, optimize=False, progressive=False)
filled = sum(1 for p in cov if not cov[p])
print("pixels", hashlib.sha256(bytes(out)).hexdigest(), cfg["colour"]["expected_pixels_sha256"] == hashlib.sha256(bytes(out)).hexdigest())
print("jpeg", hashlib.sha256(o.getvalue()).hexdigest(), cfg["colour"]["expected_sha256"] == hashlib.sha256(o.getvalue()).hexdigest(), len(o.getvalue()))
print("filled", filled, filled / 900, filled / 900 == cfg["colour"]["expected_filled_fraction"])
print("covered bands and counts", {b: n for b, (n, s) in sorted(sums.items())}, "sums", {b: s for b, (n, s) in sorted(sums.items())}, "means", mean)
print("uncovered bands -> source", dict(sorted(used.items())))
NAMED = [("the north-west corner", 0, 0), ("the north-east corner", 0, 29), ("the south-west corner", 29, 0),
         ("inside the area's own box, not cut", 15, 15), ("band 21 covered, by the area", 12, 9),
         ("band 25, the nearest below with cover is 23", 10, 25), ("2200.00 m: band 22, empty, below first: 21", 15, 20),
         ("2299.99 m: band 22", 19, 29), ("band 19, none below: the nearest above, 21", 20, 10),
         ("band 21, its own band", 25, 15), ("band 23, its own band", 20, 20), ("2400.00 m: band 24, empty: 23", 25, 20),
         ("the south-east corner, band 24", 29, 29)]
vec = []
for name, r, c in NAMED:
    i = 3 * (r * cols + c)
    vec.append({"name": name, "row": r, "column": c, "lv95": [E0 + 50 + 100 * c, N1 - 50 - 100 * r],
                "covered": cov[r, c], "sample_cm": cm[r, c], "band": band[r, c],
                "band_taken": band[r, c] if cov[r, c] else source_band(band[r, c]), "rgb": list(out[i:i + 3])})
doc = {"about": ("brief v0.6.0-06: named pixels of the far colour fixture (tests/shared/farcolour_fixture/), computed "
                 "by the pin author in plain Python from source.json and photo.u8 (no numpy, no mattini): pixel (row, column) "
                 "centred at LV95 (e_min + 50 + 100 column, n_max - 50 - 100 row); band = floor(sample_cm / 10000); a covered "
                 "pixel is (sum + 12) // 25 of its 5 x 5 source pixels; a filled one the half-up integer mean of its band_taken's "
                 "covered pixels."),
       "band_means": {str(b): list(mean[b]) for b in sorted(mean)},
       "band_counts": {str(b): sums[b][0] for b in sorted(sums)},
       "band_sums": {str(b): sums[b][1] for b in sorted(sums)},
       "pixels": vec}
(Path(sys.argv[1]) / "tests/shared/farcolour_vectors.json").write_bytes((json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())
for v in vec: print(v["name"], v["covered"], v["sample_cm"], v["band"], v["band_taken"], v["rgb"])
