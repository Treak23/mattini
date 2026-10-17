# M4 de-shadowing prototype (design measurement, 2026-10-17)

Not production code, not a decision: evidence for the M4 recommendation on the photo's baked
shadows. A 250 m x 250 m crop of SWISSIMAGE 2023 (E 2624175-2624425, N 1096750-1097000,
tile 2624-1096, averaged to 0.2 m); © swisstopo.

- `1-photo.jpg` the photo as shipped.
- `2-shadow-mask-overlay.jpg` the shadow cast at capture (sun az 184.9°, el 50.1°, ray-cast on
  swissSURFACE3D 0.5 m) in blue; shadow-like pixels the mask does not explain in red.
- `3-deshadowed.jpg` photo-guided lift (mask grown 2 m limits where dark, blue pixels are brightened).
- `4-deshadowed-naive-mask-only.jpg` mask-only lift: halos, 24 % clipped.
- `5-zoom-before-after.jpg` 2x zoom, before and after.

Measured: shadows are ~20x darker than lit ground in red and green (linear); lifting them amplifies
JPEG 4:2:0 noise to magenta/green speckle (11.3 sRGB levels vs 4.0 on lit grass). Full removal is not
viable; a partial lift (3-4x) is the option put to the owner.
