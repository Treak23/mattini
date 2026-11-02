"""Writes tests/shared/farcolour_fixture/{world.json, datasets.json, source.json, photo.u8}
(brief v0.6.0-06's design data; no mattini import). The lock and surroundings.json follow from
the files written here (make_lock.py, then the two ways)."""
import hashlib, json, sys
from pathlib import Path

repo = Path(sys.argv[1])
fx = repo / "tests/shared/farcolour_fixture"
fx.mkdir(parents=True, exist_ok=True)

def dump(path, data):
    path.write_bytes((json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())

AREA = {"e_min": 2616000.0, "e_max": 2617000.0, "n_min": 1095000.0, "n_max": 1096000.0}
dump(fx / "world.json", {
    "schema": 1,
    "crs": {"horizontal": "EPSG:2056", "vertical": "EPSG:5728"},
    "origin_lv95": {"e": 2616500.0, "n": 1095500.0},
    "height_offset_m": 1250.25,
    "axes": {"x": "+e", "y": "+h", "z": "-n"},
    "areas": {"fixture": AREA},
})
dump(fx / "datasets.json", {
    "schema": 1,
    "terms": "Terms of use for free geodata and geoservices (OGD) from swisstopo, version 1.3.2021",
    "datasets": {
        "swissaltiregio": {
            "collection": "ch.swisstopo.swissaltiregio", "edition": "2026-06", "resolution_m": 100,
            "attribution": "© swisstopo (synthetic test heights, not swissALTIRegio data)"},
        "swissimage_far": {
            "collection": "ch.swisstopo.swissimage-dop10", "edition": "2023", "resolution_m": 20,
            "attribution": "© swisstopo (synthetic test colours, not SWISSIMAGE data)"},
    },
})
# The surroundings box: the area grown by margin 1000 -> E 2615000-2618000, N 1094000-1097000.
E0, E1, N0, N1 = 2615000, 2618000, 1094000, 1097000
ABSENT = ["2616-1094", "2617-1094", "2617-1095"]  # a stepped south-east, as Italy's

def height_cm(x, y):
    """Invented heights in whole centimetres at a 100 m sample (x, y)."""
    if not (E0 < x < E1 and N0 < y < N1):
        return 215000 + (x - E0 + 7 * (y - N0)) % 4000  # the border the heights' squares need
    c, r = (x - E0 - 50) // 100, (N1 - 50 - y) // 100
    ce, rn = c // 10, r // 10
    cell = f"{2615 + ce}-{1096 - rn}"
    if cell not in ABSENT:  # covered: band 23 on the north km row, band 21 below it
        if rn == 0:
            return 230000 + ((7 * r + 3 * c) % 100) * 100 + (c % 3) * 25
        return 210000 + ((5 * r + 11 * c) % 100) * 100 + (r % 4) * 5
    if cell == "2617-1095":  # band 25 north half, band 22 south half (its edges 2200.00, 2299.99)
        if r < 15:
            return 250000 + ((r * 13 + c) % 100) * 100
        v = 220000 + ((r * 3 + c * 7) % 100) * 100 + 99 * (c % 2)
        return {(15, 20): 220000, (19, 29): 229999}.get((r, c), v)
    if cell == "2616-1094":  # band 19 north half, band 21 south half
        if r < 25:
            return 190000 + ((r + c) % 100) * 100 + 1
        return 210000 + ((r * 9 + c) % 100) * 100
    # 2617-1094: band 23 north half, band 24 south half (its edge 2400.00)
    if r < 25:
        return 230000 + ((r * 11 + c * 5) % 100) * 100 + 50
    return 240000 if (r, c) == (25, 20) else 240000 + ((r + 3 * c) % 100) * 100 + 7

def z_text(cents):
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return sign + f"{whole}.{frac:02d}".rstrip("0").rstrip(".")

# Samples over the heights' half-spacing border: [E0 - 250, E1 + 250) x [N0 - 250, N1 + 250).
tiles = {}
for y in range(N1 + 150, N0 - 251, -100):  # rows north to south: 1097150 ... 1093750
    for x in range(E0 - 250, E1 + 250, 100):  # 2614750 ... 2618150
        e0 = 5000 + ((x - 5000) // 10000) * 10000
        n0 = 4000 + ((y - 4000) // 10000) * 10000
        tiles.setdefault(f"{e0 // 1000:04d}-{n0 // 1000:04d}", []).append(f"{x} {y} {z_text(height_cm(x, y))}")
regio = {t: {"member": t.replace("-", "_") + ".xyz", "text": "\r\n".join(["x y z"] + lines) + "\r\n"}
         for t, lines in sorted(tiles.items())}
# The photo: 20 m source pixels over the box, 150 x 150, R G B row-major north to south.
RES = 20
cols, rows = (E1 - E0) // RES, (N1 - N0) // RES
px = {}
for Y in range(rows):
    for X in range(cols):
        cell = f"{2615 + X // 50}-{1096 - Y // 50}"
        if cell in ABSENT:
            px[Y, X] = [0, 0, 0]  # no item: never read (the tiles of these cells do not exist)
        elif Y < 50:  # the north km row (band 23): pale, snow and rock
            px[Y, X] = [130 + X // 2 + (X * Y) % 5, 150 + Y + (3 * X) % 7 + ((X % 5) * 5 + Y % 5 < 12), 170 + (X + Y) // 3]
        else:  # band 21: green
            px[Y, X] = [40 + X // 3 + (7 * Y) % 5, 10 + Y + X % 4, 30 + (X + 2 * Y) // 5 + (X * Y) % 3 + ((X % 5) * 5 + Y % 5 < 9)]
# Tune band 21's red sum to an exact half (remainder 150 of 300, the whole even), so half-up and
# half-to-even differ: +1 on all 25 source pixels of the first d of its output pixels, row-major.
def out_red(Y0, X0):
    return (sum(px[Y0 + i, X0 + j][0] for i in range(5) for j in range(5)) + 12) // 25
band21 = [(r, c) for r in range(10, 30) for c in range(30)
          if f"{2615 + c // 10}-{1096 - r // 10}" not in ABSENT]
assert len(band21) == 300
total = sum(out_red(5 * r, 5 * c) for r, c in band21)
d = (150 - total) % 600
for step in range(d):
    r, c = band21[step % 300]
    for i in range(5):
        for j in range(5):
            px[5 * r + i, 5 * c + j][0] += 1
total = sum(out_red(5 * r, 5 * c) for r, c in band21)
assert total % 600 == 150, total
pix = bytearray()
for Y in range(rows):
    for X in range(cols):
        pix += bytes(px[Y, X])
(fx / "photo.u8").write_bytes(bytes(pix))
dump(fx / "source.json", {
    "about": ("brief v0.6.0-06's far colour fixture (synthetic, no swisstopo data): regio holds four "
              "swissALTIRegio tiles' member text at a 100 m cell (only the points the fixture needs), "
              "invented heights; photo.u8 holds the 20 m source pixels over photo.lv95_box (uint8 R, G, B "
              "interleaved, row-major, rows north to south), zero in the absent cells; synthetic_farphoto.py "
              "cuts the 1 km tiles of the cells not in absent from it and writes them as GeoTIFFs."),
    "absent": ABSENT,
    "photo": {"columns": cols, "rows": rows, "resolution_m": RES,
              "lv95_box": {"e_min": float(E0), "e_max": float(E1), "n_min": float(N0), "n_max": float(N1)},
              "sha256": hashlib.sha256(bytes(pix)).hexdigest()},
    "regio": {"tiles": regio},
})
print(sorted(regio), {t: len(v["text"]) for t, v in regio.items()}, len(pix))
