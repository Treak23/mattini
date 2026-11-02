"""Way 2 of the real far colour (no mattini import): float parse rounded to cm, numpy fill."""
import glob, hashlib, io, json, os, sys, time, zipfile, resource
import numpy as np, rasterio
from PIL import Image
RAW = sys.argv[1]
E0, E1, N0, N1 = 2603000, 2645000, 1075000, 1118000
W, H = (E1 - E0) // 10, (N1 - N0) // 10
t0 = time.time()
pix = np.zeros((H, W, 3), np.int64)
cov = np.zeros((H, W), bool)
prov = json.load(open(os.path.join(RAW, "swissimage_far/2023/provenance.json")))
for t in prov["tiles"]:
    e, n = map(int, t["tile"].split("-"))
    with rasterio.open(os.path.join(RAW, "swissimage_far/2023", t["file"])) as r:
        a = r.read().astype(np.int64)
    s = a.reshape(3, 100, 5, 100, 5).sum((2, 4))
    rr, cc = (N1 - (n + 1) * 1000) // 10, (e * 1000 - E0) // 10
    pix[rr:rr + 100, cc:cc + 100] = np.moveaxis((s + 12) // 25, 0, 2)
    cov[rr:rr + 100, cc:cc + 100] = True
t1 = time.time()
hcm = np.full((H, W), np.iinfo(np.int64).min, np.int64)
for z in sorted(glob.glob(os.path.join(RAW, "swissaltiregio/2026-06/*.zip"))):
    with zipfile.ZipFile(z) as zf:
        txt = zf.read(zf.namelist()[0])
    arr = np.loadtxt(io.BytesIO(txt), skiprows=1)
    x, y, h = arr[:, 0].astype(np.int64), arr[:, 1].astype(np.int64), np.rint(arr[:, 2] * 100).astype(np.int64)
    c, r = (x - E0 - 5) // 10, (N1 - 5 - y) // 10
    ok = (c >= 0) & (c < W) & (r >= 0) & (r < H)
    hcm[r[ok], c[ok]] = h[ok]
assert (hcm != np.iinfo(np.int64).min).all()
t2 = time.time()
band = hcm // 10000
bmin = band.min()
b = band - bmin
nb = b.max() + 1
cnt = np.bincount(b[cov], minlength=nb)
means = np.zeros((nb, 3), np.int64)
for ch in range(3):
    sm = np.bincount(b[cov], weights=None, minlength=nb) * 0
    sm = np.zeros(nb, np.int64)
    np.add.at(sm, b[cov], pix[..., ch][cov])
    means[cnt > 0, ch] = (sm[cnt > 0] + cnt[cnt > 0] // 2) // cnt[cnt > 0]
src = np.arange(nb)
have = cnt > 0
for k in range(nb):
    if have[k]:
        continue
    below = np.flatnonzero(have[:k])
    if below.size:
        src[k] = below[-1]
    else:
        src[k] = k + 1 + np.flatnonzero(have[k + 1:])[0]
fill = means[src[b]]
out = np.where(cov[..., None], pix, fill).astype(np.uint8)
filled = int((~cov).sum())
raw = out.tobytes()
im = Image.frombuffer("RGB", (W, H), raw, "raw", "RGB", 0, 1)
o = io.BytesIO(); im.save(o, "JPEG", quality=92, subsampling=2, optimize=False, progressive=False)
j = o.getvalue()
t3 = time.time()
print(json.dumps({
  "unfilled_pixels_sha256": hashlib.sha256(np.where(cov[..., None], pix, 0).astype(np.uint8).tobytes()).hexdigest(),
  "pixels_sha256": hashlib.sha256(raw).hexdigest(), "jpeg_sha256": hashlib.sha256(j).hexdigest(),
  "jpeg_bytes": len(j), "filled": filled, "total": W * H, "filled_fraction": filled / (W * H),
  "bands_min_max": [int(band.min()), int(band.max())],
  "bands_covered": [int(bmin + k) for k in np.flatnonzero(have)],
  "bands_filled_only": sorted(set(int(v) for v in np.unique(band[~cov])) - set(int(bmin + k) for k in np.flatnonzero(have))),
  "src_for_uncovered_bands": {int(bmin + k): int(bmin + src[k]) for k in range(nb) if not have[k] and (band[~cov] == bmin + k).any()},
  "h_range_m": [int(hcm.min()) / 100, int(hcm.max()) / 100],
  "t_photo": round(t1 - t0, 1), "t_regio": round(t2 - t1, 1), "t_fill_encode": round(t3 - t2, 1),
  "peak_MiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}, indent=1))
