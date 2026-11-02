# 0.6.0 — the far mountains drawn: design's decisions

Written by the release session of 0.6.0 after the go of 2026-11-02 (`docs/history/blocked/2026-11-02-1.md`;
SPEC §13 rows 58, 59). Every 0.6.0 brief cites this file as "design §N"; the SPEC and the briefs outrank it.
Measured on 2026-11-02 with throwaway scripts in the session's scratchpad (never committed): the numbers below
marked "measured" are reproducible from the pinned inputs; the scripts' logic is restated in the decisions.

## 0. What was measured

- **swissALTIRegio** (STAC v0.9, `ch.swisstopo.swissaltiregio`): the 30 tiles M4-01 named (E 2595 … 2645, N 1074
  … 1114), edition `2026-06`, every checksum equal to M4-01's pinned ones; `lock.entry_sha256` of the entry
  `9afdf81d…caaf908` = `config/surroundings.json`'s `computed_for.inputs_sha256`: swisstopo has not republished.
  179'684'396 bytes; pixel centres at 5 m offsets; every height a whole number of centimetres; no nodata in the
  window (the Italian corners included). M4-02's rule (100 m, max) reproduced exactly: `d317a358…` (421 × 431).
- **The drawn grid candidates** (the half-open square of M4-02, the MEAN instead of the max, float32):
  - 50 m: 841 × 861, 2'896'404 bytes, SHA-256 `2430baea5a4081cfedeb936a5b1da4b3d7fed441c17002c3035f8661bb31e38b`
    (2301 NaN; heights 859.54 to 4610.58 m); five summation orders give the same float32 bytes.
  - 25 m: 1681 × 1721, 11.6 MB; its squares hold 2 or 3 samples per axis, alternating (an irregular footprint).
  - The 50 m mean sits 15 to 31 m below the 10 m summits (Dufourspitze 4610.6 against 4634.2, Matterhorn
    4454.1 against 4477.0); 25 m sits 2 to 12 m below.
- **SWISSIMAGE 2 m** (`ch.swisstopo.swissimage-dop10`, the `_2_2056.tif` asset of every item): over the window
  (42 × 43 = 1806 cells of 1 km) 1220 cells have an item of edition 2023 (each also has 2017 and 2020), 586 have
  none (Italy). 201'117'688 bytes; each file 500 × 500 px RGB, pixel edges on the km grid, no nodata, no black
  margins at the border. A 10 m mosaic (the integer mean of 5 × 5 source pixels) of 4200 × 4300: pixels
  `6313604f…`, JPEG (photo.py's settings) 5'611'994 bytes `8fad1da8…`; 25 s, 323 MB peak.
- **Godot 4.6.3** (headless and Compatibility under Xvfb): the 50 m mesh in 121 chunks of 80 × 80 squares, 1.44 M
  triangles, builds in 1.7 to 2.8 s of GDScript, about 25 MiB of buffers; 25 m takes 7 to 10 s and 4×. The
  camera's far 20000 m clips three corner chunks seen from the village (the corners are up to 31.8 km away);
  the depth precision near the camera is set by near = 0.1 and does not change with far (measured in
  Compatibility at far 20000, 40000, 100000).
- **A software Forward+ probe** (lavapipe; evidence, not the look): the Matterhorn drawn where the engine places
  its summit from the village and from Gornergrat; the top view north-up, unmirrored; no holes, cracks or chunk
  seams. Seen wrong: the photo's stepped edge at the Italian border against a grey-white height ramp; up close
  (standing on the far mesh, e.g. at Gornergrat, which lies outside today's area box) 10 m colour on 50 m facets
  is a smear.

## 1. The grid (amends M4-02's rule)

- **Spacing 50 m**, the box the area's box grown by `margin_m` 20'000 (unchanged): the village 841 columns × 861
  rows, E 2'603'000–2'645'000, N 1'075'000–1'118'000, row r column c at (e_min + 50c, n_max − 50r).
- **The height:** the MEAN of the samples whose position lies in the half-open square [E − 25, E + 25) ×
  [N − 25, N + 25) (5 × 5 = 25 samples at 10 m), minus `height_offset_m`. Computed exactly: every height text is
  parsed to whole centimetres (M4-01 decision 3: at most two decimals; a text with more is refused naming the
  tile and line), summed as integers, divided once in float64 (`sum_cm / (100 · n)`), rounded once to float32.
  The order of summation cannot change the result. Why the mean, not M4-02's max: a drawn surface built from
  maxima bulges up to 418 m above the ground (the Matterhorn's face); for the shadows the mean at 50 m loses 15
  to 31 m at the summits, seconds of sun.
- **The cut, NaN and a vertex with no sample:** as M4-02 decision 1 (strictly inside the area box NaN 0x7FC00000,
  the edge kept; a kept vertex without a sample refused). The samples needed are those of
  [e_min − 25, e_max + 25) × [n_min − 25, n_max + 25): still M4-01's 30 tiles.
- **Expected:** the step compares its bytes with design's SHA-256 before writing (as the terrain's). Measured with
  the exact-centimetre rule (2026-11-02, the session): `2430baea…`, the same bytes as the float64 orders; design
  commits it in `config/surroundings.json` (§5).

## 2. The colour

- **The input:** a seventh swisstopo input (swissALTIRegio is the sixth), the dataset `swissimage_far` in `config/datasets.json`: collection
  `ch.swisstopo.swissimage-dop10`, edition `2023`, `resolution_m` 2, attribution `© swisstopo`; its tiles are
  every 1 km cell of the surroundings box ([e_min, e_max) × [n_min, n_max), the box itself, no half-spacing
  border) that has an item of the edition; the cells without one are recorded in the lock as absent (so a new
  item appearing, or one vanishing, is a refused fit, not a silent change). Commands `python -m mattini lock
  farphoto` and `download farphoto`, following `lock regio` and `download regio` (M4-01 decisions 5 and 6): the
  lock from the STAC items alone, the edition checked, the republish refusal, `.part` and verify, a provenance
  file. The asset is the item's `..._2_2056.tif` (eo:gsd 2.0); the lock records its file name and SHA-256 from
  `checksum:multihash`.
- **The step `farcolour`:** a 10 m RGB grid over the surroundings box, 4200 × 4300 for the village, pixel
  (r, c) centred at (e_min + 5 + 10c, n_max − 5 − 10r): the integer mean `(sum + 12) // 25` of the 5 × 5 source
  pixels of a covered cell; the village's own box is not cut (the near terrain covers it). Pixels of a cell
  without an item are **filled**, a labelled placeholder (Hard Rule 2): the integer mean colour of every covered
  pixel in the same 100 m height band, the band of the pixel's own swissALTIRegio sample (whose positions are
  the pixel centres, the same 10 m lattice), `band = floor(h / 100)`; a band with no covered pixel takes the
  nearest band below that has one, else above. So the Italian side takes the photo's own tone by altitude
  instead of a grey ramp (the probe's stepped edge), and the game needs no coverage file and no shader branch.
- **Its outputs:** `surroundings/<area>_colour.jpg` (photo.py's JPEG: Pillow, baseline, 4:2:0, quality 92,
  the same save arguments; the KEEP import file as the photo's) with the expected values compared before
  writing, pixels first, then the JPEG bytes, a JPEG difference alone naming the encoder (photo.py's
  `jpeg_encoder`): `expected_pixels_sha256` and `expected_sha256` in `config/surroundings.json`. The block
  records the filled fraction (`filled_fraction`, the count of filled pixels over all, a float) so the credits
  and the record can say how much is placeholder. Measured unfilled: 0.6755 of the cells covered.
- **Credits:** SWISSIMAGE 10 cm, edition 2023, © swisstopo (the photo's line already names it; the far colour adds
  no new line unless the editions differ) and swissALTIRegio's whole source text (M4-10 decision 8).

## 3. The game

- **The reader** (`game/scripts/terrain/surroundings_grid.gd`, M4-07 re-scoped): the manifest's `surroundings`
  block, the f32 heights (size, NaN exactly in the cut, the box, the world guard as the other readers, with the
  0.5.0 batches' residue fixed for this reader: it names "the height offset differs" apart from "the origin
  differs") and the colour JPEG (dimensions = the block's), the hint lines through `ReleaseBuild.file_hint`
  (the live census allows only `release_build.gd` to spell "rebuilds it").
- **The loader** (`surroundings_loader.gd`): a DRAWN mesh, cast_shadow ON (the default), placed by the world
  transform (Hard Rule 4: x = E − origin_e, z = −(N − origin_n), y = h − height_offset_m, read from the manifest's
  world block, never hard-coded), the node unturned at the origin:
  - chunks of 80 × 80 squares (4 km; 121 for the village), one `MeshInstance3D` each, so the camera culls them;
    two triangles per square whose four corners are finite, none in the cut; front faces up;
  - per-vertex normals by central differences of the grid (one-sided at the box edge and next to NaN), UV =
    ((E − e_min) / (e_max − e_min), (n_max − N) / (n_max − n_min)) over the colour texture;
  - **a skirt** along the cut's edge: for every edge segment a vertical quad from the edge vertices down 100 m,
    facing out of the cut, its own `MeshInstance3D` with cast_shadow OFF (so it never throws a line into the
    village at a low sun); it hides the crack between the 50 m edge and the 0.5 m terrain;
  - one material: albedo the colour texture (source_color, mipmaps, anisotropic), roughness 1, no specular; the
    scene's fog applies (aerial perspective, design §0);
  - built at load on the main thread (1.7 to 2.8 s measured at 50 m; the record states the startup cost).
- **The main scene:** the camera's far 40'000 m (covers every corner of the window from anywhere in the area box;
  the fog hides 79 % at 30 km); the startup line `surroundings <area> loaded, <columns> x <rows> vertices at 50 m,
  colour <w> x <h> at 10 m` (after the shadows line); the error panel's entry `Surroundings` (a missing or
  refused block opens the panel, the rest of the world shown); the credits line with swissALTIRegio's text.
  Terrain3D draws nothing outside the area box (`world_background` NONE, holes), so the far mesh never overlaps
  the near terrain; z-fighting none.
- **Not decided here, kept:** `directional_shadow_max_distance` 3000 (far peaks shade the far valleys only by
  their slope's light beyond 3 km); MSAA 4×.

## 4. What it does NOT do (said in the record)

- The far terrain is 50 m with 10 m colour: up close (standing outside the area box, e.g. at Gornergrat) it is a
  smooth smear; M5's stage 2 replaces it inside the municipality.
- Italy and every cell without SWISSIMAGE is a filled placeholder colour by altitude.
- No far shadows under Compatibility; shadows of far peaks on far valleys beyond 3 km are not drawn.

## 5. Design data (committed by the session with the pins)

`config/surroundings.json` (schema 2): per area `margin_m` 20000, `spacing_m` 50, `computed_for` {inputs_sha256 of
the `swissaltiregio` entry, world_sha256}, `expected_columns`, `expected_rows`, `expected_lv95_box`,
`expected_sha256` (heights); and `colour`: {`cell_m` 10, `band_m` 100, `computed_for` {inputs_sha256 of both the
`swissaltiregio` and `swissimage_far` entries (`lock.entries_sha256`), world_sha256}, `expected_columns`,
`expected_rows`, `expected_pixels_sha256`, `expected_sha256`, `expected_filled_fraction`}. The fixtures under
`tests/shared/surroundings_fixture/` re-cut to the 50 m rule and given a colour input. The manifest pair of 0.6.0
measured at the integration rehearsal.

## 6. The batches

| Id | Batch | Lane | After | Tier |
|---|---|---|---|---|
| v0.6.0-01 | swissALTIRegio: the dataset and `lock regio` (M4-01 a) | A | — | 1 |
| v0.6.0-02 | `download regio` (M4-01 b) | A | 01 | 1 |
| v0.6.0-03 | Release reproducibility (the Python pin, the sha on `main`, check 5's words, §C's size line) | B | — | 1 |
| v0.6.0-04 | The surroundings step: the 50 m mean grid (M4-02 re-scoped) | B | — | 1 |
| v0.6.0-05 | SWISSIMAGE 2 m: the dataset, `lock farphoto`, `download farphoto` | A | 02 | 1 |
| v0.6.0-06 | The far colour step | B | 04, 05 | 1 |
| v0.6.0-07 | The wiring: the commands, the manifest's `surroundings` block, one home for the tile rule and readers | A | 02, 04, 05, 06 | 1 |
| v0.6.0-08 | The far terrain in the game: the reader and the drawn loader (M4-07 re-scoped) | B | 04 (its fixture) | 1 |
| v0.6.0-09 | The main scene: the far terrain loaded, the camera's far, the line, the panel, the credits | B | 07, 08 | 1 |
| v0.6.0-10 | The export and the release workflow: the new inputs and steps, the startup line, the manifest pair | A | 03, 07, 09 | 2 |
| v0.6.0-11 | The version 0.6.0 and the release notes' rollback line | A | all | 2 |

## 7. Amended at the pins' review (2026-11-02, the session; the checkers' findings)

- **The skirt is double-sided** (§3 amended): its own material (the same albedo, `CULL_DISABLED`), shadows off,
  100 m deep. Facing out of the cut with back-face culling it would never be seen from the village, where the crack
  is seen. The chunks share one material; the skirt has its own.
- **The reader checks the heights' NaN layout** (§3 kept): NaN exactly at the vertices strictly inside `cut_box`,
  finite elsewhere.
- **The fixtures** (§5 amended): `tests/shared/surroundings_fixture/`'s colour JPEG and manifest block are game-only
  design data, hand-made, labelled and pinned by SHA-256; the colour step proves itself on its own fixture,
  `tests/shared/farcolour_fixture/`. The render checks' test world (`complete_world.gd`) cuts its far-terrain hole
  by its own grid, not by its 20 m area box (labelled test data), so the far mesh never covers the tiny test
  terrain and the five RENDER numbers stay as they were.
- **The fill of the cells without a photo** (§2) departs from the owner's "plain shading" (SPEC §13 row 59): put to
  the owner with the plan; until answered, the pins keep §2's altitude-band fill.
