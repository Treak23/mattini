# M4 softened baked shadows and the river's water class (design measurement, 2026-10-17)

Evidence for SPEC §13 row 41 (soften, judged by the owner from these images) and FB-003.
Not production code. Crops of SWISSIMAGE 2023, © swisstopo.

Shadow mask: ray-cast on swissSURFACE3D 0.5 m for the flight's sun (az 184.9° true, 185.13° grid,
el 50.1°), eroded 0.5 m then Gaussian σ 0.5 m ("inset": the feather stays inside the shadow; a
centred feather lifts lit ground by 1.53× at G=3, a neon halo). Lift in linear light:
albedo × (1 + (G−1)·m), clipped.

- `A-village-compare.jpg`, `B-forest-edge-compare.jpg`: original | G=2 | G=3 | G=4 (2×2 grid).
  A: E 2624175–2624425, N 1096750–1097000. B: E 2623225–2623475, N 1096150–1096400.
- `*-zoom.jpg`: the same at 2×, 80 m × 80 m.
- `*-zoom-mask-variants.jpg`: G=3 with the mask at 0.5 m, at 1 m, with chroma denoise, centred feather.
- `water-overlay.jpg`: the water class (magenta) on a 500 m stretch of the Vispa against the channel in
  the photo (cyan, estimated) and the TLM line (yellow).

Measured (A / B): shadow/lit ground ratio 0.044 / 0.047 in the photo (about 23× darker), 0.128 / 0.141
at G=3 (about 7.5×); clipped inside the mask at G=3 2.03 % / 0.06 %; grain on former-shadow grass 8.7 /
6.5 sRGB levels at G=3 against 4.6 on lit grass; halo on lit ground next to the mask 1.12× at G=3. A 1 m
mask differs from 0.5 m by 0.65 levels on average (no visible difference); stored as 8-bit PNG for the
2 × 3 km box: 2.51 MB at 1 m, 6.82 MB at 0.5 m. Chroma denoise does not help at G ≤ 4. Design's choice
for the owner: G = 3, inset feather, 1 m mask; G a shader uniform. Remaining artefacts: yellow-green
glows where the 2021/22 surface model's crowns differ from the 2023 photo, lifted shadows stay
blue-grey, a dark pixel times three is still dark.

Water: the Vispa is a swissTLM3D area polygon and a line; 94 % of the channel seen in the photo carries
the water class in this stretch (classed widths 8–12 m, as the photo's 9–12 m). The "patch near the
camera" (FB-003) is therefore the shading, not the class: roughness 0.05 mirrors the sun near the
camera, elsewhere the water is the photo × 0.6; the ripples (4–6 m features) drift at about 0.25 m/s in a
fixed world direction across the channel.

`mask-capture.jpg` (brief M4-03's design rehearsal, 2026-10-17): the step's mask (cast and own
shadow marched on 1 m cells, written at 0.5 m with the inset at 0.5 m; sun 184.67° grid, 50.1°)
over the photo, E 2624000–2624500, N 1096500–1097000, at 0.5 m: photo | mask in blue. 20.4 % of
the crop is in the mask.
