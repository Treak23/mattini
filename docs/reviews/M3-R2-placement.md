# Review M3 R2 — lens `placement`, placement (Tier 1: config/world.json and the coordinate transforms, pipeline and game)

**ROUND CLEAN: no P2 or above.** Four P3 (M3-R2-P-01 to P-04); P-01 is the nearest to a P2 and is graded P3 for the reason it gives.

- **Range:** `git diff 410dbba..a6779f3 -- . ':!game/addons' ':!pipeline/uv.lock'`; head reviewed `a6779f3` (69 files, +5'417 −156; 41 files, +2'378 −118 outside `docs/`). The fixes: M3-R1-fix-1 (`0385a7f`), fix-4 (`77e8508`), fix-5 (`2c70fd7`, `8cbb5c1`), fix-2 (`43aeb86`), fix-3 (`f928ccd`). Fix-6 (`da8914f`) is the surfaces lens's and was not reviewed here.
- **Date:** 2026-10-16.
- **How:** one review session, five fresh `git clone`s under its scratchpad, each with its own `XDG_DATA_HOME` and its own `uv sync` (no checkout copied, brain.md H22; only the generated village data was copied from `clean` into `fix2`): `clean` (the real village built from the pinned inputs, the standard gate, the probes), `mut` (the render-step mutations), `fix2` (fix-2's mutations and the 1 m and 2 m command runs), `gatem` (whole-gate mutation runs) and `scratchw` (the real village in a world with another origin, a height offset and the grid north-west of its origin). Every mutation is an exact string edit applied by a driver (`mutrun.py`, Appendix A) that saves `git diff`, runs, undoes with `git apply -R` of the saved diff and asserts `git status --porcelain` is empty: 229 runs, listed in Appendix F and summarised under "Mutations". The render mutations ran the gate's own `render_step` alone (a copy of `tools/gate.sh` with every other step deleted, so fix-1's text pins are not in the way); the whole `tools/gate.sh` ran with the pins removed for three of them, with the pins in place for one, and once over a change that removes every tree (P-01). Nothing set `MATTINI_SKIP_RENDER`. The clones and their data are removed; the scripts are in the Appendix.
- **Standard gate at the head (mine, not the orchestrator's):** exit 0 in 249 s from `tools/gate.sh > log` in `clean`: `uv lock --check`, pytest `2228 passed, 5 deselected` in 154.62 s, ruff check and format, `manifest`, Godot 4.6.3 import and parse, GUT `Scripts 47 / Tests 261 / Passing Tests 261 / Asserts 9760`, `GUT version:  9.6.1`, `---- All tests passed! ----` (371 `ERROR` lines in the GUT step, every one excepted), gdlint, gdformat, then the render step, run and not skipped: `RENDER photo: PASS correlation 0.9761 …`, `RENDER classes: PASS agreement 83092 of 83427 …`, `RENDER trees: PASS correlation 0.9380 over 20 trees …`; last line `== gate: all steps passed`.
- **The real village:** `download terrain|buildings|photo|surface|tlm` all exit 0 with every tile, sheet and file verified against the lock (15, 4, 16, 9 and 115 s; the photo took 7 fetches for its 6 tiles, tile 2623-1097 fetched twice, the command's own retry; the TLM file is 2'882'823'552 bytes), then `terrain` 7 s, `buildings` 6 s, `photo` 68 s, `roofs` 30 s, `surfaces` 29 s, `trees` 36 s, `manifest` 3 s, each exit 0: the manifest is `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`, 324'359 bytes, design's.
- **Result:** the three things the round was asked to prove hold, each by mutation. (1) The trees step and the manifest's trees block refuse every terrain spacing but 0.5: 17 mutations of the refusals and their order, 16 fail a named case, the one survivor is a position the pinned decision allows; the command runs at 1 m and 2 m; the village's trees stand on Terrain3D's ground (34'412 of them, 0 more than 5 cm off, worst 0.244 mm). (2) The gate's render step alone fails every named misplacement of the photo, the classes and the crowns' colour — a flip, a half texel, 0.1 m, swapped axes, a second assignment to `puv`, `xz`, `origin` or `uv` — and passes ten clean runs with the same numbers; the whole `tools/gate.sh` now exits 1 at its render step on three mutations that passed GUT in R1 and V1 (two of them left the whole gate at exit 0). (3) V1-1 is closed by the render step; V1-2 and V1-3 stay open, none is a P2. What the round adds are the limits of that step, found with more than 200 mutation runs of my own: it does not see an empty forest (P-01), its world has only positive coordinates and is 16 m wide (P-02), it reads one class of four (P-03) and its decision at 0.1 m rests on three samples in one direction (P-04).

## Findings

### M3-R2-P-01 · P3 · The tree check passes with no tree drawn: four edits that remove every tree leave the whole gate green, and the PASS line still says "over 20 trees"

- **Where:** game/tests/render/render_trees.gd (`_compare` and `_crown_lum`: the disc about each crown's axis is read whether or not a crown is there, and no clause compares it with the bare ground), tools/gate.sh `render_script` (a PASS line is all it asks), game/scripts/trees/tree_loader.gd:28 (`VISIBILITY_END_M := 3000.0`, a constant no test names: `grep -rn VISIBILITY_END_M game` finds it and its one use).
- **Claim:** under a missing tree the ground is the photo, so the luminance at the crown's axis correlates with the photo at the tree's position at least as well as under a drawn crown. The shipped check scores 0.9380 with its 20 trees drawn and 0.9759 with none, and passes both. The step proves where a crown's colour is read *when a crown is drawn*, as its header says; nothing in it, in GUT or in the gate sees that the crowns are not drawn.
- **Proof:**
  - Render step alone (`mutrun.py` with `specs5.py`, Appendix A and F): `T1` (`VISIBILITY_END_M := 0.5`), `T1b` (`15.0`), `T2` (`discard;` first in `fragment()` of tree_conifer.gdshader), `T3` (`multimesh.visible_instance_count = 0`) and, from the first battery, `E03` (R1's P-02: the Trees node 1 km east): each `exit=0` and `RENDER trees: PASS correlation 0.9759 over 20 trees; with the photo read x and z exchanged -0.1397, mirrored north-south 0.2113, mirrored east-west -0.0767`, the same numbers every time (the same bare picture). `E12` (R1's `GM-tree-buffer-z`) gives the same line.
  - GUT on the six tree scripts (`test_tree_loader`, `test_tree_loader_photo`, `test_m3_11_tree_conifer`, `test_scene_placement`, `test_main_scene_data`, `test_tree_chunks`; `gutmut.py`, `specs6.py`): control `Scripts 6 / Tests 33 / Passing Tests 33 / Asserts 3518`; `G1` (= T1), `G2` (= T2), `G3` (= T3) each `Tests 33 / Passing Tests 33`, `---- All tests passed! ----`. (E03 and E12 are caught by fix-1's scene tests and `test_tree_loader`, as R1 and V1 showed; the four above are not.)
  - The whole `tools/gate.sh` with `VISIBILITY_END_M := 0.5` (clone `gatem`, run `g5`): `== gate: all steps passed`, exit 0 after 253 s, and its render step printed `RENDER trees: PASS correlation 0.9759 over 20 trees`.
  - Other photos (`margin_trees.gd`, Appendix C: 21 renders over 5 random block-colour photos, three layouts and four crown radii): the same view with the `Trees` node hidden scores 0.9658 to 0.9881 in the shipped layout (a tree at the centre of every second block) against 0.8915 to 0.9360 with the trees drawn; the empty picture scores above the drawn one in 20 of the 21 renders. A presence clause would see every tree: |disc luminance with the trees − without| has a minimum of 30.2 to 41.5 and a median of 61 to 66 per photo in the shipped layout, and is 0 for T1 to T3.
- **Harm:** all 34'412 trees absent on the owner's PC — a cull distance, a `discard`, a draw count — with the standard gate green and its render check saying PASS; the owner sees it at the first start. P3 and not P2 because BUILD.md rule 2b and CLAUDE.md keep "that anything renders" as the owner's check, the step's header limits it to where the crowns' colour is read, and no gate saw the trees' visibility before the step either. It is the nearest this round comes to a P2: the step's PASS line reads as if 20 trees were drawn.
- **Fix:** in render_trees.gd take the same view with `Trees` hidden and add a clause: every crown disc differs from the bare ground by at least 15 luminance units (the measured minimum is 30), and print the drawn count in the PASS line; mutation-prove with T1 to T3. A GUT test that `VISIBILITY_END_M` is at least the village's diagonal is the cheap twin.

### M3-R2-P-02 · P3 · The render world is 16 m wide, flat and east and south of its origin: a sign error that shows only at negative coordinates passes, and so do drift with distance and a horizontal shift of the terrain's own vertices

- **Where:** game/tests/render/render_photo.gd (`CAMERA_AT`, `AREA_X`, `AREA_Z`), render_trees.gd (`PHOTO_X0`, `PHOTO_Z0`, `CAMERA_AT`), and the complete world's world block (origin E 2'600'000 / N 1'200'000: its terrain at local x 1015 to 1035, z 10.5 to 22; tests/shared/terrain_fixture/generated/manifest.json). The village lies at x 0 to 2000, z −2000 to 1000.
- **Claim:** R1's note — "a fixture world with the area north-west of its origin … is the cheap gate" — was taken up neither by fix-1's scene tests (V1-3) nor by the render step. The step proves where the photo, the classes and the crowns land at x ≈ 1025, z ≈ 16, in a photo 16 m wide, over a plane.
- **Proof (render step alone, `specs2.py`):**
  - Sign: `S-abs-xz` (`xz = abs(xz);` after its declaration), `S-abs-puv` (`abs(v_vertex.xz)` in the `puv` line), `S-abs-origin` (`origin = abs(origin);`), `S-abs-origin-x`: all four `exit=0`, every check PASS. The same four in a world north-west of its origin — the nine edits of `NW-00-clean` (Appendix D): the fixture's world block moved to origin E 2'601'100 / N 1'199'900 and height offset 1234.5, so the grid lies at x −85 to −65, z −89.5 to −78, and the three scripts' constants moved by −1100 m and −100 m: `NW-00-clean` PASS (photo 0.9761, classes 83096 of 83427, trees 0.9177); `NW-abs-xz` FAILS classes (agreement 74747 of 83427, best fit ±0.30 m); `NW-abs-puv` FAILS photo (correlation −0.0100); `NW-abs-origin` FAILS trees (−0.0283); `NW-abs-origin-x` FAILS trees (−0.1128); the controls `NW-xz-x+0.1` and `NW-tree-uv-zx` FAIL as in the shipped world.
  - Distance: `puv *= 1.0005` and `puv *= 1.002` pass, `1.005` FAILS photo. At the village's 2 km a scale error of 1.002 is a drift of 4 m at the far edge, and 16 m × 0.002 is 3 cm in the render.
  - The terrain's own vertices: `V01` (`v_vertex.x += 0.1;` at the top of `vertex()`), `V02` (the geomorph line removed), `V03` (doubled): PASS. On a flat terrain a horizontal shift of the mesh and of its height lookups cannot be seen.
  - The loaders: `S-loader-abs-x`, `S-loader-abs-z`, `S-loader-int-cell-x` (V1-3's) pass in both worlds, because the trees fall out of the picture (P-01).
- **Harm:** an `abs()`, a truncating cast or a scale that a negative-coordinate or large world shows, with the whole gate green. No realistic edit of these shaders is shown to make one (they compute positions relative to the rectangle), and fix-1's text pins still name the lines, which is why this is P3.
- **Fix:** run the two scripts in the north-west world as well (nine edits, constants and one fixture's world block; every value holds), or move the render world there for good; say in the "does NOT prove" lines of CLAUDE.md and SPEC §12 that the step proves nothing about distance or the terrain's mesh.

### M3-R2-P-03 · P3 · The classes check reads the water class only: the placement of rock, road and path, and the class codes, pass

- **Where:** game/tests/render/render_photo.gd `_check_classes` (the render's mask is a ratio below `WATER_RATIO`, compared with `class_at(...) == 2`), CLAUDE.md "What the gate cannot see", docs/SPEC.md §12 and the gate.sh header, which say "the surface classes".
- **Claim:** only water darkens the photo by a uniform factor; road and path add detail textures of mean 1, rock only on slopes, which the flat world lacks. Classes 1, 3 and 4 are never compared with anything.
- **Proof (render step alone, `specs.py`):** `C27` (the rock class read 0.5 m off: `classes.x = class_weights(xz + vec2(0.5, 0.0)).x;` after the `classes` line), `C28` (road 0.5 m off), `C29` (path mirrored about z = 0), `C24` (the road and path codes exchanged in `class_weights`): each `exit=0`, `RENDER classes: PASS agreement 83091 of 83427` or 83090. The controls: `C26` (the water class alone 0.1 m off) FAILS classes, `C25` (rock and water codes exchanged) FAILS classes.
- **Harm:** a change that moves or mislabels only roads, paths or rock is seen by fix-1's text pins (`test_m3_09_photo_shader.gd`: C24 and C27 to C29 each leave `Tests 5 / Passing Tests 4 / Failing Tests 1`, the pinned-lines test) and by nothing else; the render adds nothing for them while the docs say it covers "the surface classes". The owner would see misplaced roads at the first start.
- **Fix:** say "the water class" in the three places now; to see the others, the check already replaces `surfaces` and could replace `road_albedo` and `path_albedo` with flat images of unlike luminance, giving each class its own ratio (not tried here).

### M3-R2-P-04 · P3 · The classes check's rule for 0.1 m rests on a difference of three samples in one direction: `class_at` reading half a texel east passes, the same shift in the shader fails

- **Where:** game/tests/render/render_photo.gd `_best_class_shift` (the best fit must lie inside a window of ±0.05 m, inclusive, of a scan in 0.05 m steps) and `_check_classes`.
- **Claim:** fix-3's Findings 6 says the classes' resolution is 0.1 m. That holds for the shader side: 18 of 18 runs (a half texel in x, in z and in both, each of both signs, each three times: `H11` to `H16`, `H21` to `H26`, `H31` to `H36`) FAIL. It does not hold for the reader `class_at`: the argmax of a scan whose clean plateau sits near −0.025 m puts a half-texel error of one sign at +0.075 m, between the inside and the outside of the window.
- **Proof:** `H17`, `H27`, `H37` (`var column := roundi((x - x0) / cell_m)` in `SurfaceGrid.class_at`, R1's `GM-surf-class-at-round` for x): PASS three times, `agreement 82892 of 83427 … data_only 302` (clean: `data_only 2`); the scan by x shift of the data, −0.30 to +0.30 m, is `[…, 82891 (0), 83093 (+0.05), 83091 (+0.10), 82891 (+0.15), …]`: the best inside the window (83093) beats the best outside it (83091) by 2. The same 0.1 m in the shader (`C31`, the surfaces rectangle +0.1 m): `[…, 82890, 83088, 83091, 82892, …]` FAILS (the outside beats the inside by 3). `H18` (the same in z) and `H19` (`- 0.5` in x, the other sign) FAIL. The counts move by 1 to 2 samples between clean runs (83090 to 83092: the water's normal maps drift with `TIME`).
- **Harm:** none today: `test_surface_grid.gd` fails on this mutation (`gutmut.py`, `specs8.py`: `Tests 16 / Passing Tests 13 / Failing Tests 3`, among them `every texel's byte is class_at's class at its centre`, fix-1's row test). It is the step's resolution at the sign where it is thinnest, and a margin of two or three samples is below the noise between runs.
- **Fix:** decide by the agreement at no shift, not by the argmax: fail when it is more than about 100 samples below the best of the scan (clean: 0 to 2 below; a half texel: 201 to 411 below in `A3`, `C12`, `C30`, `C31`, `H12`).

## Checked and clean

Everything below was probed on the real village or the fixtures at `a6779f3`; "scratch world" is the world of `scratchw` (origin E 2'625'000 / N 1'095'000, height offset 1000 m: the whole grid at x < 0 and z < 0), "NW world" the fixture world of P-02 (origin E 2'601'100 / N 1'199'900, offset 1234.5).

### The trees refuse every terrain spacing but 0.5 (fix-2)

- **The code.** `_spacing_refusal(area, terrain_config)` is called by `build_trees` straight after `_area` (before the world check, the lock, any provenance or input, any file under `out_dir` and any progress line) and by `built_trees_block` after its "no description, return None" line. Seventeen mutations of the refusals, their messages and their order (`specs_fix2.py`, Table 9): sixteen fail named cases of the pinned file's seven, with the harm each reproduces (trees written, or a manifest accepted, on a 1 m or 2 m terrain with exit 0, floating or sunk). The one survivor, `F2-05` (the call moved after the world check, before the lock), is a position the pinned decision allows ("before it reads the lock, provenance or any input": the world check reads only `config/world.json` and the configs). A first run of `F2-06` passed: a stale `.pyc` (an edit of the same size within the same second); every F2 run was repeated with `PYTHONDONTWRITEBYTECODE=1` and the cache removed, `F2-06` fails, and the first results were discarded (Notes).
- **The commands** (clone `fix2`, the real village built, `config/terrain.json`'s `spacing_m` edited and put back with `git apply -R`):
  - `1.0` and `2.0`, `python -m mattini trees --raw <raw>`: `mattini: error: config/terrain.json: area 'village' has spacing_m 1, but the trees take their base heights from the 0.5 m terrain grid (docs/SPEC.md §8, trees, item 7) and stand off the ground at any other spacing; set spacing_m to 0.5 (…)` (and `… spacing_m 2 …`), exit 1, no traceback, the six chunk files byte-identical before and after.
  - `manifest` with terrain and trees built at 0.5 and the config at 1.0: exit 1, naming the terrain first (`…/terrain/village.json: it was built at 0.5 m, the terrain config asks for 1.0 m; python -m mattini terrain rebuilds the terrain`).
  - The route SPEC §7 describes, config 1.0 then `terrain --raw`: the heights are written (2001 × 3001 vertices, SHA-256 `71bd4f17…`, design's), then the manifest step refuses with the trees message, exit 1. The manifest on disk stays the previous one (`3ca0445c…`), and the game refuses it loudly: `ERROR: TerrainGrid: res://assets/generated/manifest.json: the heights file … holds 24020004 bytes, not 96040004 (4001 × 6001 float32)`. With 0.5 again and `terrain --raw`: exit 0, the manifest `3ca0445c…` again.
  - The trees directory taken away, config 1.0: `manifest` exit 0, `trees: null`; the game logs `ERROR: TreeChunks: … no trees have been built: run python -m mattini trees` and builds no Trees node; with the directory back, the refusal above.
  - Spacings the terrain config does not allow (0.25, 0, 0.5000000000000001, 0.500000000001, `true`, `"0.5"`, nan, null, `[0.5]`): `TerrainError … spacing_m must be one of [0.5, 1.0, 2.0]` from `_area`, before the trees refusal; `1` (an integer) is read as 1.0 and refused by the trees.
- **Does anything else let a tree's base height come from a grid that is not Terrain3D's?** In the pipeline: one source, `resample(dtm, box, SOURCE_M, height_offset)` at `SOURCE_M` 0.5, each tree at a pixel centre, y the mean of the four vertices, which is Terrain3D's bilinear height there; the refusal in both functions; the terrain block's own check of the built spacing against the config. In the game: `TreeChunks` and `TreeLoader` read y as written, `TerrainLoader` takes `vertex_spacing` from the manifest's terrain block, and no reader compares that spacing with the trees' 0.5 m (fix-2's brief says "no game change"). A hand-assembled manifest (the village's, with its terrain block replaced by the 1 m description) is accepted: `probe_trees.gd` prints `trees total=34412 nan_ground=0 off>1cm=23083 off>5cm=3542 worst=1.052246 … buckets 1338 / 9991 / 19541 / 3368 / 173 / 1` and no ERROR line, R1's numbers to the digit. No command writes such a manifest (the manifest step is its only writer and refuses it), so it is a note and not a finding.
- **The village's trees on the ground** (R1's Appendix A, unchanged): `trees total=34412 nan_ground=0 off>1cm=0 off>5cm=0 worst=0.000244 … mean_abs=0.000035`, buckets `[34412, 0, 0, 0, 0, 0]`, x 0.750 to 1999.250, z −1999.250 to 999.250, `Trees global_transform == IDENTITY: true`. In the scratch world: `worst=0.000122 … mean_abs=0.000016`, x −1999.250 to −0.750, z −2999.250 to −0.750.

### The render step (fix-3)

- **The named misplacements, alone.** The nine mutations of Table 1 (fix-3's eight and its own ninth) each fail the step with the check's own line, in the render step run on its own (`mutrun.py`, the gate's `render_step` in a copy of `gate.sh` with every other step deleted). The whole `tools/gate.sh`, run as the owner runs it, with fix-1's and fix-4's text pins replaced by `assert_true(true)` (`gatemut.py --no-pins`, formatted with gdformat so that the gate reaches its last step): `SH-photo-uv-flip` exits 1 after 257 s at step `render` (`RENDER photo: FAIL correlation 0.0554 …`; R1 measured exit 0 for it at `410dbba`); V1-1's `xz.x += 0.1` exits 1 after 254 s (`RENDER classes: FAIL best fit at an x shift of the data of -0.10 m`; V1 measured exit 0 at `bed42ec`); V1-1's `origin.x += 1.0` exits 1 after 256 s (`RENDER trees: FAIL correlation -0.2177 below 0.60`). With the pins in place, `SH-photo-uv-flip` exits 1 after 239 s at step `gut` (the pins act first; the render is not reached).
- **The smallest shift each check catches, and what it cannot see** (all from Tables 2 to 5, render step alone):

  | check | catches | does not catch |
  |---|---|---|
  | photo (`puv`) | every flip, axis swap and half texel (`B01` to `B07`, seven of seven); a shift of 0.025 m west or north (`B12`, `B13`), 0.04 m east or south (`B10`, `B11`: 0.025 passes); a scale of 1.005 | 0.01 m; 0.025 m east or south; a scale of 1.002 (4 m at the village's 2 km) |
  | classes (`xz`, the water class) | 0.1 m in every direction tried (`C10` to `C13`, four of four), 0.075 m east (`C10`), the surfaces rectangle +0.1 m (`C31`), every half texel in the shader (18 of 18) | 0.05 m in any direction; 0.075 m south (`C11`); the rectangle +0.05 m (`C32`); `class_at` half a texel east (P-04); the other three classes (P-03) |
  | trees (`origin`, the crown's colour) | 0.75 m east (`D10`), 1.0 m south (`D11`), the photo rectangle given to the trees +1.0 m (`E02`), every flip, swap and the model-space uv (`D20` to `D23`) | 0.5 m east, 0.75 m south, +0.5 m in the rectangle; every tree absent (P-01); the trees' own positions in the loader (`E10`: +0.1 to +1.0 m east, `E11`: +0.5 m up, `E12`: z mirrored: all PASS because the trees fall out of the picture) |
  | all | | negative coordinates, distance, the terrain's vertices and its LOD morph (P-02); rock (never drawn on a flat plane: `C43`); the photo's grey outside its rectangle (`C42`); lighting (`D30`, `D31`, `C44`) |

- **Ten clean runs** (`tenruns.sh`, the step alone, a quiet machine, each exit 0): photo `correlation 0.9761 north-south-mirrored 0.0547 east-west-mirrored -0.2240 over 34772 pixels` in all ten; trees `correlation 0.9380 over 20 trees; … x and z exchanged -0.2014, mirrored north-south 0.2324, mirrored east-west -0.0031` in all ten; classes agreement 83090 (four runs), 83091 (five) and 83092 (one) of 83'427, mirrored 70473 to 70475, water `both 8679, render_only 333 to 335, data_only 2, neither 74411 to 74413`. Two clean runs more in the gate (`83092`) and in the NW world (`83096`). A run of the step takes 12 to 15 s (31 s the first time, with the shaders compiled), the whole gate 249 s. Nothing flaky, nothing loosened; these are the builder's numbers (his mirrored count reads 70'471 to 70'473, mine 70'473 to 70'475).
- **The refusal and the skip** (the gate's own `render_step`, `skiptests.sh`; a `PATH` of symlinks to every executable but `xvfb-run`): hidden and the variable unset: exit 1, `== gate: xvfb-run is missing, so the render step cannot run: install it (the xvfb package), or on a machine that cannot render set MATTINI_SKIP_RENDER=1, which skips the step and says so in this log`, then `== gate: FAILED at step: render`. Hidden and `=1`: exit 0, `== render: SKIPPED (MATTINI_SKIP_RENDER=1): where the photo, the classes and the crowns' colour land is not checked` once on stdout (the log) and once on stderr (the terminal), no Godot started. Hidden and `""`, `0`, `true`, `yes`, `2`, ` 1` or `1 `: exit 1 with the refusal. `xvfb-run` found and `=1`: the step runs, says `== render: MATTINI_SKIP_RENDER=1 is set but xvfb-run is here, so the step runs: the variable excuses only a machine without xvfb-run`, three PASS lines. **Nothing sets the variable:** `git grep MATTINI_SKIP_RENDER` outside `docs/` finds only `tools/gate.sh` (the header comment, the skip line's text, the read at `render_step`, the refusal's text, the "is set but" text), `CLAUDE.md`, and `pipeline/tests/` (`fake_tools.py` `env.pop`s it; `test_gate_render.py` gives it to a subprocess); there is no `export` or assignment in `tools/`; `.claude/` (`settings.json`, `hooks/`) and `.github/workflows/janitor.yml` hold no `env` and no mention; the shell of this session had none (`env | grep SKIP` empty).
- **The step's own failure modes** (render step alone, `specs5.py`; `RENDER_TIMEOUT` is 180 s): `R1` (`render_photo.gd` does not parse): `SCRIPT ERROR: Parse Error: Expected closing ")" …`, `ERROR: Failed to load script`, exit 1 after 0.7 s. `R2` (it quits with 0 before any check): `did not print a 'RENDER photo: PASS' line` and the same for classes, exit 1. `R3` (`render_trees.gd` never ends): killed by `timeout` after 189 s, `== gate: exit status 124`, exit 1. `R4` (it prints a FAIL line and exits 0): refused. `R5` (a runtime error after the checks print: Godot stays running): `SCRIPT ERROR: Cannot call method 'queue_free' on a null value.`, killed at 180 s, exit 1. A stand-in `xvfb-run` that cannot start Xvfb (exit 3): `== gate: exit status 3`; one that exits 0 without running its command: both PASS lines missing; Mesa absent (`LIBGL_DRIVERS_PATH=/nonexistent`): six `ERROR:` lines (`Can't load EGL dynamic library` … `Unable to create DisplayServer`), listed and refused, as the builder reported. Eleven mutations of the step's code in `gate.sh` (`specs_gate.py`, Table 8: the timeout disabled, the SKIPPED line printed once, the PASS regex unanchored, the audio driver removed, the variable's note removed, the step moved, the trees script not run, the FAIL scan removed, the engine scan off, any value skipping, the variable skipping where `xvfb-run` is found) each fail one to ten of `test_gate_render.py`'s 25 cases (8 s).
- **The two choices the builder made (Findings 3 and 5).**
  - *The disc estimator, the threshold 0.6 unchanged: right.* The review's 5 × 5 apex estimator reads below 0.6 in 7 of the 21 clean renders of `margin_trees.gd` (other photos and layouts: down to 0.0968), so keeping it would have meant loosening or flaking; the 0.4 m disc reads 0.8915 to 0.9360 on five other photos in the shipped layout against worst wrong places of 0.1876 to 0.3432 (the shipped photo: 0.9380 against 0.2324): a margin of at least 0.54 to the wrong places and 0.29 to the threshold, on every photo tried. A misplacement it misses that matters: none the data could resolve (the smallest shift caught is 0.75 m east and 1.0 m south, a crown has a radius of 0.7 m, and the buildings and the photo agree to "about a metre", R1) — and the absence of crowns, which is P-01. The margin is a property of the layout and not of the estimator: with trees at random positions, off the block centres, the same disc reads 0.51 to 0.91 clean (0.5114 once, below the threshold), so the constants hold for the shipped layout and photo fixture, and whoever changes either re-measures. The pass band against look values is narrower than against placement: `crown_boost` 3.0 (from 1.25) reads 0.6498, a mip bias of +3 levels fails at 0.0299 with a message that names a correlation, not a look.
  - *The variable excuses only a machine without `xvfb-run`: right.* The owner's Windows has none and skips; a container always has it and cannot. Verified above. One remark for Notes: after a skip the gate still ends `== gate: all steps passed`, the SKIPPED line standing above it on both streams.
- **Look edits that do not trip it** (render step alone, `specs4.py`): `tonemap_exposure` 0.30, 0.40, 0.70 and 1.00 (shipped 0.54) pass, 1.50 and 2.50 fail photo and classes (the picture is white); the linear and ACES tonemappers pass; `crown_boost` 0.4, `rim_shade` 0.2 and the terrain's flat normal built the other way round (`C44`) pass.

### The census gaps V1-1 to V1-3

- **V1-1** (`xz` and `origin` unnamed by the census): closed in behaviour. `A7` and `A8` fail the step alone and the whole gate (above); the census itself is unchanged and still names neither word. The step resolves 0.075 to 0.1 m for `xz` and 0.75 to 1.0 m for `origin`; below that nothing sees it.
- **V1-2** (the normal's census counts lines that begin with `NORMAL`): open, P3 as V1 graded it. `G4` (the arguments back) fails the pinned-line test; `G5` (`if (true) { NORMAL = -NORMAL; }` after the pinned line) and `G6` (`{ NORMAL = vec3(0.0, 1.0, 0.0); }` before it and `{ NORMAL = -NORMAL; }` after) leave the six tree scripts at `Tests 33 / Passing Tests 33`. The render step passes them too (`D30`, `D31`: trees 0.8978 against 0.9380): lighting is outside it by design. The realistic regression, the order back, is caught by the pinned line.
- **V1-3** (the scene-level tree tests see one cell south-east of the origin): open, P3. `G7` (`buffer.append(absf(at.x))`), `G8` (the cells west of `4_*` shifted 1 km) and `G9` (`int()` for x in the cell key) leave the six scripts at 33 of 33; the render step adds nothing (`S-loader-*`: its world is positive too, and in the NW world the trees leave the picture, P-01, P-02). Not a P2: the village's trees lie at x 0.75 to 1999.25 (the probe above), so the three change nothing in the shipped world, and in the scratch world (every tree at x < 0) the `int()` key would only regroup the cells (reasoned, not run there); no change realistic for this arc is shown to give a wrong picture with the gate green.

### The photo's rectangle, the real village and the asymmetric worlds

- **The photo on the village** (`probe_photo.gd`, `photo_expect.py`, Appendix B): `PhotoGrid` on the real manifest: `rect (0.0, -2000.0, 2000.0, 3000.0)`, equal to `to_local` of the box's north-west and south-east corners (`(0, 0, -2000)` and `(2000, 0, 1000)`), decoded image 10'000 × 15'000, RGB8, with mipmaps. The four corner texels read from the swissimage tiles by rasterio (no code of `mattini`: each texel the round-half-even mean of its four 0.1 m pixels) are `(144, 141, 119)`, `(78, 94, 64)`, `(97, 116, 91)`, `(25, 33, 34)` for (0, 0), (9999, 0), (0, 14999), (9999, 14999): the four corner squares of the box, R1's colours; the game's decoded pixels there are `(144, 139, 119)`, `(76, 89, 69)`, `(101, 114, 96)`, `(31, 32, 37)` (JPEG quality 92, 4:2:0). Over 76 texels (the four corners, 60 random, 12 along the edges) the shader's own rule from the texel centre, `floor(u·columns)`, `floor(v·rows)`, lands on the texel itself 76 times in 76, and the decoded pixel differs from the independent texel by a mean `|ΔR|+|ΔG|+|ΔB|` of 8.32 against 19.97 one texel east, 20.13 south, 17.29 west, 18.88 north. In the scratch world the same 76 of 76, `rect (-2000.0, -3000.0, 2000.0, 3000.0)`, the same 8.32.
- **The scratch world end to end** (`scratchw`, `recompute_expected.py` of R1's Appendix E, 468 s): every step refused naming design's step until its `computed_for.world_sha256` and expected values were recomputed as design would (terrain 1, buildings 6, roofs 1, trees 6; the photo's and the surfaces' pixel hashes are world-independent and held); the buildings' six chunk hashes (`8542678c…`, `171518e4…`, `4d3bca7e…`, `83551c84…`, `d20dbcda…`, `a5191d46…`) and the roofs' (`b60fa6a9…`) are R1's to the digit, the trees' six are `b6ca77ed…`, `56ac732e…`, `3349d8a9…`, `1860a4b0…`, `5435de38…`, `e671f7d7…`. In that world the trees stand on Terrain3D's ground to 0.122 mm and the photo's rectangle is at the corners. Hard Rule 4 holds for the new code: only `config/world.json` moved. The render step passes in the NW world (`NW-00-clean`: the nine edits of Appendix D, nothing else).
- **Determinism:** the manifest `3ca0445c…` is the third lens's build of it, byte for byte.

### Pairs (lesson 8)

- *fix-4 under fix-3:* fix-4 gave the crowns' facets their normals and moved the review's tree estimator from 0.7513 to 0.5824; fix-3 saw it, changed the estimator and not the threshold, and said so (Findings 3). I reproduced the other direction on other photos (above).
- *fix-1's pins beside fix-3's render:* the two nets cover different gaps and the gate runs GUT first. The pins see the class-specific edits the render cannot (`C24`, `C27` to `C29`, P-03) and the render sees the `xz` and `origin` edits the pins cannot (V1-1); a whole gate over a named mutation fails at `gut` with the pins and at `render` without them (g4, g1).
- *fix-5 under fix-3:* the render scripts write a complete world and read it through all six readers with fix-5's type-safe guards; the three PASS lines are the proof that none refuses it.
- *fix-2 beside fix-1:* fix-1's scene test stands the fixture's trees on a 0.5 m terrain and fix-2 refuses every other spacing, so the pair holds for the same reason; neither tests the game on a 1 m terrain (the note above).

## Mutations

Each mutation is one exact edit (Appendix F), applied in a throwaway clone from a saved diff, run, undone with `git apply -R` of that diff, `git status` clean after each (the driver asserts it). "Render step alone" is the gate's own `render_step` in a copy of `tools/gate.sh` with every other step deleted; a result "FAILS photo" means `RENDER photo: FAIL …` and exit 1, "passes" means three PASS lines and exit 0 (when the photo script fails the trees script is not run). The harm is what the owner or the build would see if the change were real (lesson 4). Where a result carries a number it is the check's own.

### Table 1 — fix-3's eight mutations and its own ninth, render step alone

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `A1-SH-photo-uv-flip` | photo drawn upside down | FAILS photo: `correlation 0.0554 below 0.95; the photo reads better mirrored north-south (0.9749)` |
| `A2-SH-photo-uv-shift` | photo 0.1 m east of where it belongs | FAILS photo: `correlation 0.9352 below 0.95; the photo reads as well or better +0.10 m east` |
| `A3-SH-class-half-texel` | roads, paths, water and rock half a texel (0.1 m) off the photo | FAILS classes: `best fit at an x shift of the data of -0.15 m; … z shift … -0.10 m; agreement 82610 of 83427` |
| `A4-SH-class-ns-flip` | roads, paths, water and rock drawn north-south mirrored | FAILS photo (`correlation 0.8980`) and classes: `agreement 69895 of 83427, below 0.98; the data mirrored north-south agrees better (82742)` |
| `A5-GM-surf-texture-flip` | the texture the shader reads differs from `class_at`: the water is drawn mirrored | FAILS photo (`0.8979`) and classes: `agreement 69874 of 83427 … mirrored (82727)` |
| `A6-SH-tree-uv-zx` | crowns tinted from another place | FAILS trees: `correlation 0.0187 below 0.60; … mirrored east-west (0.2150)` |
| `A7-V11-xz-x+0.1` (V1-1) | classes 0.1 m off by an edit of `xz` after its declaration | FAILS classes: `best fit at an x shift of the data of -0.10 m; agreement 82708` |
| `A8-V11-origin-x+1.0` (V1-1) | crowns read 1 m east of the tree by an edit of `origin` after its declaration | FAILS trees: `correlation -0.2177 below 0.60` |
| `A9-xz.y-negated` (fix-3's own) | the water drawn nowhere near where the data has it | FAILS classes: `agreement 74746 of 83427, below 0.98` (`both 0, data_only 8681`) |

### Table 2 — the photo's placement, render step alone

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `B01-puv-swap-yx` | photo with its axes exchanged | FAILS photo |
| `B02-puv-ew-flip` | photo mirrored east-west | FAILS photo |
| `B03` to `B07` (`puv += or -= vec2(0.5, 0) / textureSize`, the same in z, and both) | a texel-centre error: the photo half a texel (0.1 m) off to the west, east, north, south, north-west | FAILS photo, five of five |
| `B10-puv-x-<d>`, d = 0.01, 0.025, 0.04, 0.05, 0.075, 0.1, 0.2 | photo d m east of where it belongs | passes, passes, FAILS, FAILS, FAILS, FAILS, FAILS |
| `B11-puv-z-<d>`, the same d | photo d m south | passes, passes, FAILS ×5 |
| `B12-puv-x+<d>`, d = 0.025, 0.05, 0.1 | photo d m west | FAILS ×3 |
| `B13-puv-z+<d>`, d = 0.025, 0.05, 0.1 | photo d m north | FAILS ×3 |
| `B20-puv-scale-<s>`, s = 1.0005, 1.002, 1.005, 1.02 | photo scaled about its north-west corner (at 2 km, s − 1 times 2000 m at the far edge) | passes, passes, FAILS photo, FAILS photo |
| `B21-puv-width-minus-0.2m` | rectangle one texel narrower in the shader (a fencepost) | FAILS photo |
| `C33-photo-rect-shift-0.1` | the photo rectangle given to the terrain shader 0.1 m east | FAILS photo |
| `C34-photo-rect-from-surfaces` | terrain given the surfaces' rectangle as its photo rectangle (R1's `GM-main-terrain-photo-rect`) | FAILS photo |
| `C41-photo-uses-surfaces-rect` | photo placed with the surfaces' rectangle in the shader | FAILS photo |
| `C35-photo-texture-flip-in-reader` | the photo decoded upside down in `PhotoGrid` (shader and expectation both read the flipped texture) | **passes**: both sides read the reader; `test_photo_grid.gd` is the net (R1) |
| `C36-photo-x0-half-texel` | `PhotoGrid`'s `x0` half a texel east (shader and expectation both read it) | **passes**: the same; `test_photo_grid.gd` is the net (R1) |
| `C42-outside-rect-fallback` | the grey outside the photo's rectangle removed | **passes**: nothing samples outside the rectangle |

### Table 3 — the classes' placement, render step alone

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `C10-xz-x+<d>`, d = 0.025, 0.05, 0.075, 0.1, 0.15, 0.2 | classes d m off in x | passes, passes, FAILS, FAILS, FAILS, FAILS |
| `C11-xz-z+<d>`, the same d | classes d m off in z | passes, passes, passes, FAILS, FAILS, FAILS |
| `C12-xz-x-<d>`, d = 0.05, 0.1 | the other way in x | passes, FAILS |
| `C13-xz-z-<d>`, d = 0.05, 0.1 | the other way in z | passes, FAILS |
| `C20-classes-xz-swap` | classes read with the axes exchanged | FAILS classes |
| `C21-fetch-transpose`, `C22-fetch-ew-flip` | texel index transposed; classes mirrored east-west | FAILS photo and classes, both |
| `C23-t-plus-half` | classes a whole texel off (`+ 0.5` for `- 0.5`) | FAILS classes |
| `C25-codes-rock-water-swapped` | rock and water exchanged in `class_weights` | FAILS classes |
| `C26-water-only-shift-0.1` | only the water class 0.1 m off | FAILS classes |
| `C24-codes-road-path-swapped`, `C27-rock-only-shift-0.5`, `C28-road-only-shift-0.5`, `C29-path-only-mirror` | road and path codes exchanged; rock, road, path alone 0.5 m off or mirrored | **pass** (P-03); each fails fix-1's pinned-lines test (Table 6) |
| `C31-surfaces-rect-shift-0.1`, `C32-…-0.05` | the surfaces rectangle given to the shader 0.1 m, 0.05 m east | FAILS classes (outside beats inside by 3 samples); passes |
| `C40-class-uses-photo-rect` | classes placed with the photo's rectangle | FAILS photo and classes |
| `H11` to `H16` (`- vec2(0, 0.5)`, `(1, 0.5)`, `(0.5, 0)`, `(0.5, 1)`, `(0, 0)`, `1.0` for `- 0.5`), each three times (`H21` to `H26`, `H31` to `H36`) | classes half a texel off in x, z or both, both signs | FAILS classes, 18 of 18 (best fits ±0.10 to ±0.15 m) |
| `H17`, `H27`, `H37` (= `C30`): `roundi` for `floori` in `class_at`'s column | `class_at` reads half a texel east: the data side is off, the picture is right | **passes** ×3 (P-04); `test_surface_grid.gd` fails 3 (Table 6) |
| `H18`, `H19`: `roundi` in the row; `- 0.5` in the column | the same, in z; the other sign in x | FAILS classes (+0.15 m z; −0.15 m x) |

### Table 4 — the crowns' colour, the trees' rectangle and the loaders, render step alone

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `D10-origin-x+<d>`, d = 0.1, 0.25, 0.5, 0.75, 1.0, 1.6, 3.2 | crowns read d m east of the tree | passes ×3, FAILS trees ×4 |
| `D11-origin-z+<d>`, the same d | crowns read d m south | passes ×4, FAILS trees ×3 (from 1.0) |
| `D20-uv-ns-flip`, `D21-uv-ew-flip`, `D22-uv-swap`, `D23-uv-from-model-vertex` | crowns read with the photo mirrored, with the axes exchanged, or at the model-space position | FAILS trees, four of four |
| `D24-uv-per-vertex-world` | each crown vertex reads at its own world position, not the tree's origin | **passes** (a spread inside the crown: not a misplacement) |
| `D25-uv-rect-shift-x+0.5` | the tree shader's rectangle 0.5 m east | **passes** (0.8000) |
| `E01-main-trees-rect-xz-exchanged` | R1's `GM-main-trees-rect` | FAILS trees |
| `E02-main-trees-rect-x+<d>`, d = 0.5, 1.0, 2.0 | the trees' photo rectangle d m east | passes, FAILS trees, FAILS trees |
| `E03-main-trees-node-1km-east` | R1's P-02: every tree 1 km east of the terrain | **passes**: `correlation 0.9759` (P-01); fix-1's scene tests fail it |
| `E10-tree-buffer-x+<d>`, d = 0.1, 0.25, 0.5, 1.0 | every tree d m east of where its chunk puts it | **passes** ×4; `test_tree_loader` is the net |
| `E11-tree-buffer-y+0.5`, `E12-tree-buffer-z-mirror` | every tree 0.5 m above the ground; z mirrored (R1's `GM-tree-buffer-z`) | **pass**; the scene and loader tests are the net |
| `T1-visibility-end-0.5m`, `T1b-…-15m`, `T2-tree-fragment-discard`, `T3-tree-instance-count-zero` | every tree culled beyond 0.5 m or 15 m; every crown discarded; no instance drawn | **pass**, `RENDER trees: PASS correlation 0.9759 over 20 trees` each (P-01) |

### Table 5 — other paths through the shaders, look values, the north-west world

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `S-abs-xz`, `S-abs-puv`, `S-abs-origin`, `S-abs-origin-x` | `abs()` in the classes' position, the photo's uv, the crowns' origin (a sign error that only a negative coordinate shows) | **pass**, shipped render world (P-02) |
| `NW-00-clean` | the NW world, no mutation | passes: 0.9761, 83096 of 83427, 0.9177 |
| `NW-abs-xz`, `NW-abs-puv`, `NW-abs-origin`, `NW-abs-origin-x` | the same four in the NW world | FAILS classes (`agreement 74747`), photo (`-0.0100`), trees (`-0.0283`), trees (`-0.1128`) |
| `NW-xz-x+0.1`, `NW-tree-uv-zx` (controls) | as in the shipped world | FAIL classes (−0.10 m), FAIL trees |
| `S-loader-abs-x`, `-abs-z`, `-int-cell-x` and `NW-…` | V1-3's: trees at \|x\|, \|z\|, cell keys truncated for x | **pass**, both worlds (the trees leave the picture) |
| `V01-vertex-shift-x+0.1` | the terrain's vertices and height lookups 0.1 m east | **passes**: a flat plane translated is the same plane |
| `V02-vertex-morph-removed`, `V03-vertex-morph-doubled` | the far-LOD geomorph of the sampling position removed or doubled | **pass** (the morph acts far from the camera, which is 9 m above the plane) |
| `C43-rock-triplanar-world-xz` | rock detail never drawn (weight forced to 0) | **passes**: flat plane, no slope |
| `C44-flat-normal-flipped` | the terrain's flat normal built the other way round | **passes**: lighting is outside the step |
| `D30-normal-reverted`, `D31-normal-braced-second` | G-01 back: crowns lit from inside | **pass**, trees `0.8978` against `0.9380` |
| `D40-crown-boost-0.4`, `D41-crown-boost-3.0`, `D42-rim-shade-0.2` | look values only | pass (D41: `0.6498`) |
| `D43-lod-plus-3` | a crown colour taken 3 mip levels coarser | FAILS trees `0.0299` (a look edit named as a correlation) |
| `L1-exposure-<v>`, v = 0.30, 0.40, 0.70, 1.00, 1.50, 2.50 (shipped 0.54) | `tonemap_exposure` | passes ×4, FAILS photo and classes ×2 |
| `L2-tonemap-linear`, `L3-tonemap-aces` | the tonemapper | pass |

### Table 6 — GUT (the named scripts, headless)

| Mutation | Scripts run | Result |
|---|---|---|
| none (control) | `test_tree_loader`, `test_tree_loader_photo`, `test_m3_11_tree_conifer`, `test_scene_placement`, `test_main_scene_data`, `test_tree_chunks` | `Scripts 6 / Tests 33 / Passing Tests 33 / Asserts 3518` |
| `G1-visibility-end-0.5m`, `G2-tree-fragment-discard`, `G3-visible-instance-count-0` | the six | 33 of 33, `---- All tests passed! ----` (P-01) |
| `G4-normal-reverted` | the six | 1 failing: `["NORMAL = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));"] != ["NORMAL = normalize(cross(dFdy(VERTEX), dFdx(VERTEX)));"]` |
| `G5-normal-braced-second`, `G6-normal-negated-in-braces-before` | the six | 33 of 33 (V1-2) |
| `G7-loader-abs-x`, `G8-loader-cells-west-of-4-moved`, `G9-loader-int-cell-x` | the six | 33 of 33 (V1-3) |
| `C24`, `C27`, `C28`, `C29` | `test_m3_09_photo_shader` | 1 of 5 failing each: the pinned-lines test |
| `C30` (= `H17`) | `test_surface_grid` | `Tests 16 / Passing Tests 13 / Failing Tests 3`, among them `every texel's byte is class_at's class at its centre (first wrong row)` |

### Table 7 — the whole `tools/gate.sh` over a mutation (clone `gatem`)

| Run | Mutation | Result |
|---|---|---|
| `g1` | `A1-SH-photo-uv-flip`, fix-1's and fix-4's pin tests replaced by `assert_true(true)` | exit 1 after 257 s, `== gate: FAILED at step: render`; `RENDER photo: FAIL correlation 0.0554 …`, classes PASS (R1: exit 0 for it at `410dbba`) |
| `g2` | `A7-V11-xz-x+0.1`, pins removed | exit 1 after 254 s at `render`; `RENDER classes: FAIL best fit at an x shift of the data of -0.10 m`, photo PASS (V1: exit 0 at `bed42ec`, with the pins in) |
| `g3` | `A8-V11-origin-x+1.0`, pins removed | exit 1 after 256 s at `render`; `RENDER trees: FAIL correlation -0.2177 below 0.60` |
| `g4` | `A1-SH-photo-uv-flip`, pins in place | exit 1 after 239 s at `gut` (the pins act first) |
| `g5` | `T1-visibility-end-0.5m` | **exit 0** after 253 s, `== gate: all steps passed`, `RENDER trees: PASS correlation 0.9759 over 20 trees` (P-01) |

### Table 8 — the step's own code and failure modes

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `GS1-timeout-disabled` (`RENDER_TIMEOUT=0`) | a hung render script is never killed | `test_gate_render.py`: 1 failed, 24 passed (`test_two_passing_scripts_pass_and_each_runs_under_xvfb_run`) |
| `GS2-skip-line-once` | the SKIPPED line only in the log | 1 failed (`test_with_the_variable_set_to_1_and_no_xvfb_run_the_step_is_skipped_and_says_so`) |
| `GS3-pass-regex-unanchored` | a line that merely contains a PASS text passes | 2 failed (`…a-near-miss-word`, `…indented-line`) |
| `GS4-audio-driver-removed` | Godot probes ALSA under Xvfb and prints an ERROR | 1 failed (the positive control) |
| `GS5-variable-silent-when-xvfb-present` | the variable set where `xvfb-run` is found says nothing | 1 failed |
| `GS6-render-before-gdformat` | the step moved | 1 failed (`test_the_render_step_comes_after_gdformat_and_last`) |
| `GS7-trees-script-not-run` | the trees check never runs | 10 failed |
| `GS8-fail-grep-removed` | a FAIL line with exit 0 is not refused | 1 failed |
| `GS9-engine-scan-off` | an ERROR line in the render run is not refused | 3 failed |
| `GS10-skip-any-nonempty` | any non-empty value skips | 5 failed |
| `GS11-skip-where-xvfb-present` | the variable skips even where `xvfb-run` is found | 1 failed |
| `R1` to `R5` (`specs5.py`) | a render script that does not parse, quits silently, never ends, prints FAIL with exit 0, or errors after its checks | FAIL at `render` in each (the lines are quoted above) |

### Table 9 — fix-2's refusals and their order (`specs_fix2.py`, `test_m3_r1_fix2_trees_spacing.py`, 7 cases)

| Mutation | Harm it reproduces | Result |
|---|---|---|
| `F2-01-build-call-removed` | trees built on a 1 m or 2 m terrain, exit 0 | FAILS 2 (`test_the_trees_step_refuses_a_terrain_that_is_not_half_a_metre[1.0]`, `[2.0]`) |
| `F2-02-block-call-removed` | the manifest accepts built trees on a 1 m or 2 m terrain | FAILS 2 (`test_the_manifest_refuses_built_trees_on_a_terrain_that_is_not_half_a_metre[1.0]`, `[2.0]`) |
| `F2-03-cmp-gt-1.0` | 1 m let through | FAILS 2 (`[1.0]` of both) |
| `F2-04-build-after-lock` | the lock's refusal arrives first | FAILS 2 |
| `F2-05-build-after-world-check` | the call between the world check and the lock | **passes** 7 (allowed by decision 2) |
| `F2-06-build-after-inputs-refusal`, `F2-07-build-after-provenance`, `F2-08-build-after-first-progress-line`, `F2-09-build-before-write` | the refusal after the lock's fit, the provenance, a progress line, the chunks built | FAILS 2 each |
| `F2-10-cmp-lt` | nothing refused | FAILS 4 |
| `F2-11-cmp-eq-2` | only 2 m refused | FAILS 2 (`[1.0]` of both) |
| `F2-12-msg-no-config-name`, `F2-13-msg-no-spacing` | the message names neither `config/terrain.json` nor the spacing found | FAILS 4 each |
| `F2-14-block-before-exists` | a terrain-only manifest at 1 m refused too | FAILS 2 (`test_no_trees_built_is_no_refusal_at_any_spacing[1.0]`, `[2.0]`) |
| `F2-15-block-after-world-and-lock`, `F2-16-block-after-description-read` | the manifest's refusal after other checks | FAILS 2 each |
| `F2-17-spacing-key-wrong-area` | the refusal reads a hard-coded 0.5 | FAILS 4 |

## Notes

- **What this lens does not prove.** That anything renders or looks right on the owner's Forward+ and GPU (every render here, the gate's and mine, is the Compatibility renderer on Mesa 25.2.8's llvmpipe under Xvfb 21.1.12, a flat synthetic world); the colour encoding (brain.md H21); the real village through the render step (its checks run on a 16 m photo and 20 synthetic trees, as the brief says); the exported build and the Windows build, and the skip on a real Windows machine (simulated here by hiding `xvfb-run` on Linux); another Mesa or Godot build; that Terrain3D's drawn mesh agrees with its `get_height` on relief (P-02); any mutation outside Tables 1 to 9; fix-6, which is the surfaces lens's.
- **The tree check's margins on other photos** (`margin_trees.gd`, Appendix C: a random block-colour photo of 80 × 40 texels, JPEG quality 0.92 written by Godot, labelled test data, with the gate's own world and camera; "centres" is the shipped layout, a tree at the centre of every second block; "all" a tree in every block of rows 1 to 4; "random" 20 positions at least 1.8 m apart; the worst wrong place is the largest of the three alternatives the gate tests; "right" is what the gate calls `correlation`):

| photo seed | layout | crown radius (m) | trees | disc 0.4 m: right | worst wrong place | apex 5 × 5: right | same view, Trees hidden (disc 0.4 m) |
|---|---|---|---|---|---|---|---|
| 1 | all | 0.7 | 40 | 0.9293 | 0.3068 | 0.7088 | 0.9789 |
| 1 | centres | 0.5 | 20 | 0.9342 | 0.2557 | 0.7016 | 0.9770 |
| 1 | centres | 0.7 | 20 | 0.9326 | 0.2528 | 0.7133 | 0.9770 |
| 1 | centres | 1.0 | 20 | 0.8476 | 0.2516 | 0.6633 | 0.9770 |
| 1 | centres | 1.5 | 20 | 0.5481 | 0.1738 | 0.5029 | 0.9770 |
| 1 | random | 0.7 | 20 | 0.7183 | 0.3923 | 0.5147 | 0.8238 |
| 2 | all | 0.7 | 40 | 0.9311 | 0.3743 | 0.6337 | 0.9709 |
| 2 | centres | 0.7 | 20 | 0.9275 | 0.1876 | 0.6967 | 0.9658 |
| 2 | random | 0.5 | 20 | 0.9084 | 0.3540 | 0.7262 | 0.8854 |
| 2 | random | 0.7 | 20 | 0.8795 | 0.2952 | 0.7404 | 0.8854 |
| 2 | random | 1.0 | 20 | 0.8115 | 0.2955 | 0.7551 | 0.8854 |
| 2 | random | 1.5 | 20 | 0.7208 | 0.3164 | 0.7447 | 0.8854 |
| 3 | all | 0.7 | 40 | 0.9037 | 0.0970 | 0.5638 | 0.9779 |
| 3 | centres | 0.7 | 20 | 0.8915 | 0.3432 | 0.4143 | 0.9743 |
| 3 | random | 0.7 | 20 | 0.8209 | 0.3216 | 0.6076 | 0.8469 |
| 4 | all | 0.7 | 40 | 0.9156 | 0.2640 | 0.7089 | 0.9717 |
| 4 | centres | 0.7 | 20 | 0.9360 | 0.2480 | 0.7683 | 0.9694 |
| 4 | random | 0.7 | 20 | 0.8887 | 0.4990 | 0.6967 | 0.9341 |
| 5 | all | 0.7 | 40 | 0.8940 | 0.2445 | 0.4727 | 0.9799 |
| 5 | centres | 0.7 | 20 | 0.9029 | 0.2079 | 0.5143 | 0.9881 |
| 5 | random | 0.7 | 20 | 0.5114 | 0.1091 | 0.0968 | 0.7914 |

  Read: the disc estimator holds the clean value near 0.9 where the trees stand at block centres, and falls where a tree stands near a block edge or the crown is wider than the disc; the apex estimator of R1 falls below the gate's 0.6 in 7 of 21 clean renders; and the last column is above the "right" column in 20 of 21 rows (P-01).
- **For design (not findings).**
  1. P-01's presence clause is the one change I would make before the release walk: it is a few lines in `render_trees.gd`, mutation-provable with T1 to T3 (Table 4), and it turns a PASS that can mean "no forest" into one that cannot.
  2. P-02's north-west world is nine edits (Appendix D) and every value holds in it; running both worlds costs about 15 s of the gate's 250 s.
  3. SPEC §7 says 1 m or 2 m is "a config change and a pipeline re-run, no code change". Row 37's refusal makes the re-run end in an error after the `terrain` step has already overwritten the 0.5 m heights file (the brief forbade touching that step), leaving the previous manifest on disk; the game refuses that pair loudly and the message says to set 0.5 again, so nothing is silent. An early refusal in the `terrain` step when trees are built would avoid the half state; it is design's call.
  4. After a skip, `tools/gate.sh` still ends `== gate: all steps passed`; the SKIPPED line stands above it on both streams. A script that reads only the last line, or an exit status (BUILD.md rule 3c), cannot tell a skipped gate from a full one. Nothing in a container can skip (it has `xvfb-run`), so this concerns the owner's machine only.
  5. V1-2's fix (count assignments to `NORMAL` anywhere in the code lines) is still unbuilt; the render cannot carry it (trees 0.8978 against a threshold of 0.6).
- **Process, said openly.** (1) The first run of fix-2's mutations passed `F2-06`: an edit of the same size as the previous one within the same second reused a stale `.pyc`; the driver now sets `PYTHONDONTWRITEBYTECODE=1` and removes the caches before each run, all seventeen runs were repeated, and the first results are not used. (2) The first whole-gate run over `SH-photo-uv-flip` with the pins removed failed at `gdformat --check`, before the render step: my stub functions were not formatted; the clone was restored with `git apply -R`, the driver now runs gdformat on the stubs, and the run was repeated (`g1`). (3) I stopped my own chain of whole-gate runs with a `pkill -f` whose pattern also matched my shell, which killed that shell as well; the orphaned gate in `gatem` was stopped by its process ids, the clone restored from the saved diff and checked clean, and `g2` to `g4` were run afresh. No result of the interrupted run is used. (4) The fix-2 command runs, one Godot import and one probe ran while the first render battery was running, so "never two heavy builds at once" was not kept for those minutes; the battery's clean values are identical in all twelve clean runs, ten of them alone, and no result moved. (5) My GUT driver's first control (an edit that replaces a text by itself) made an empty diff that `git apply -R` refused; nothing had changed, and the control was run by hand. (6) `probe_photo.gd` has a dead loop (`for key in [...]: pass`) left from a first draft; it is shown as run.
- **Placement verdict.** No P0, no P1, no P2. The fixes of the range hold under mutation: the trees refuse every spacing but 0.5 from the step and from the manifest; the render step fails every named misplacement on its own, with the numbers the builder reported, and a whole gate now fails where R1 and V1 passed two (and GUT a third); the real village's trees stand on Terrain3D's ground, its photo rectangle sits at the box's corners, and in a world with another origin, an offset and the grid north-west of its origin all of it holds again. The four P3 are limits of the new step, none of them a regression: it cannot tell a forest from none (P-01), it looks from one corner of a small positive world (P-02), at one class of four (P-03), with a 0.1 m decision that rests on three samples in one direction (P-04).

## Appendix: the scratch scripts that reproduce the findings

Everything below ran from the session's scratchpad, never from the repository, and is not committed. `\n` and `\t` in Appendix F are a line feed and a tab; "PUV", "XZ" and the other capitals are defined at the head of Appendix F. R1's Appendix A (`probe_trees.gd`) and Appendix E (`recompute_expected.py`) were run unchanged.

### A. The drivers

`mkharness.sh <clone> <out>` writes the render-step-only copy of the gate (every `step` line but `render` deleted and the `cd` pointed at the clone, so `render_step` and `render_script` are the gate's own text); `mutrun.py` applies each edit of a spec file, saves the diff, runs the harness, undoes with `git apply -R` and asserts a clean tree. `pymut.py` (pytest: `PYTHONDONTWRITEBYTECODE=1`, caches removed before each run), `gutmut.py` (GUT on named scripts: `godot --headless --path game -s addons/gut/gut_cmdln.gd -gtest=<scripts> -gexit -gconfig=`) and `gatemut.py` (the whole `tools/gate.sh`) are the same loop with another command.

```bash
#!/bin/bash
# mkharness.sh <clone> : writes $SP/h/render_only_<name>.sh, a copy of the clone's tools/gate.sh with every step but
# "render" removed and the cd pointed at the clone. The render_step/render_script functions are the gate's own.
clone="$1"; out="$2"
sed -e '/^step "/{/^step "render"/!d}' \
    -e 's|^cd "\$(dirname "\${BASH_SOURCE\[0\]}")/\.\."|cd "'"$clone"'"|' \
    "$clone/tools/gate.sh" > "$out"
chmod +x "$out"
grep -n '^step \|^cd ' "$out"
```

```python
#!/usr/bin/env python3
"""mutrun.py <clone> <harness> <specs.py> <jsonl-out> [id ...]
For each mutation id: apply its edits to the clone (each old string must occur exactly `count` times), save `git diff`
to muts/<id>.diff, run the harness (the gate's own render_step, alone), parse the RENDER lines, undo with `git apply -R`
of the saved diff, and assert `git status --porcelain` is empty."""
import importlib.util, json, os, re, subprocess, sys, time
from pathlib import Path
clone, harness, specs_path, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
want = sys.argv[5:]
SP = Path(open(os.path.join(os.path.dirname(__file__), "..", "sp.txt")).read().strip())
spec = importlib.util.spec_from_file_location("specs", specs_path); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
SPECS = mod.SPECS            # dict id -> dict(edits=[(file, old, new[, count])], harm=str)
env = dict(os.environ, XDG_DATA_HOME=str(SP / "xdg-mut"))
env.pop("MATTINI_SKIP_RENDER", None)
def git(*a, **k): return subprocess.run(["git", *a], cwd=clone, capture_output=True, text=True, **k)
def clean(): return git("status", "--porcelain").stdout.strip() == ""
(SP / "muts").mkdir(exist_ok=True); (SP / "runs").mkdir(exist_ok=True)
assert clean(), "clone is not clean at start: " + git("status", "--porcelain").stdout
for mid in (want or list(SPECS)):
    s = SPECS[mid]
    for e in s["edits"]:
        f, old, new = e[0], e[1], e[2]; cnt = e[3] if len(e) > 3 else 1
        p = clone / f; t = p.read_text()
        assert t.count(old) == cnt, (mid, f, old, t.count(old))
        p.write_text(t.replace(old, new))
    diff = git("diff").stdout
    dpath = SP / "muts" / f"{mid}.diff"; dpath.write_text(diff)
    t0 = time.time()
    try:
        r = subprocess.run([harness], cwd=clone, env=env, capture_output=True, text=True, timeout=420)
        code, txt = r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired as ex:
        code, txt = 124, "TIMEOUT " + str(ex)
    dt = time.time() - t0
    (SP / "runs" / f"{mid}.log").write_text(txt)
    u = subprocess.run(["git", "apply", "-R", str(dpath)], cwd=clone, capture_output=True, text=True)
    assert u.returncode == 0, u.stderr
    ok_clean = clean()
    lines = [l for l in txt.splitlines() if re.match(r"^RENDER [^:]+: (PASS|FAIL)", l)]
    failed_step = [l for l in txt.splitlines() if l.startswith("== gate: FAILED at step")]
    errs = [l for l in txt.splitlines() if re.match(r"^(ERROR|SCRIPT ERROR)", l)][:3]
    rec = dict(id=mid, exit=code, secs=round(dt, 1), render=lines, failed=failed_step, errors=errs, clean_after=ok_clean, harm=s.get("harm", ""))
    with out.open("a") as fh: fh.write(json.dumps(rec) + "\n")
    verdict = "FAILS " + ",".join(re.findall(r"RENDER (\w+): FAIL", txt)) if "FAIL" in txt and code != 0 else ("passes" if code == 0 else f"exit {code}")
    print(f"{mid:34s} exit={code} {dt:5.1f}s clean={ok_clean} {verdict}", flush=True)
    assert ok_clean, "tree not clean after undo: " + git("status", "--porcelain").stdout
```

`gatemut.py`'s removal of the pin tests (the part that differs; each stub is then formatted with `gdformat`):

```python
PINS = {"game/tests/test_m3_09_photo_shader.gd": ["test_the_photo_and_the_classes_are_placed_by_the_pinned_expressions", "test_exactly_one_statement_assigns_the_photo_uv"],
        "game/tests/test_m3_11_tree_conifer.gd": ["test_the_flat_normal_is_built_as_cross_dfdy_dfdx", "test_the_crown_colour_is_read_from_the_photo_at_the_origin_by_the_pinned_lines"],
        "game/tests/test_surface_grid.gd": ["test_the_texture_holds_the_class_bytes_row_by_row"]}
if nopins:
    for f, names in PINS.items():
        p = clone / f; t = p.read_text()
        for n in names:
            m = re.search(r"^func %s\(\) -> void:\n(?:(?:\t.*|)\n)*?(?=^func |^\Z|\Z)" % re.escape(n), t, re.M)
            assert m, (f, n)
            t = t[:m.start()] + f"func {n}() -> void:\n\tassert_true(true, \"pin removed for this run (reviewer)\")\n\n\n" + t[m.end():]
        p.write_text(t)
    subprocess.run(["uv", "run", "--project", "pipeline", "--frozen", "gdformat", *PINS], cwd=clone, capture_output=True, text=True)
```

`tenruns.sh` (the ten clean runs):

```bash
#!/bin/bash
SP=$(cat "$(dirname "$0")/../sp.txt"); cd $SP/mut; export XDG_DATA_HOME=$SP/xdg-mut
for i in 1 2 3 4 5 6 7 8 9 10; do
  env -u MATTINI_SKIP_RENDER bash $SP/h/render_only_mut.sh > $SP/runs/clean-$i.log 2>&1; rc=$?
  echo "run $i exit $rc"; grep -a '^RENDER \(photo\|classes\|trees\): PASS' $SP/runs/clean-$i.log | cut -c1-250
done
```

`skiptests.sh` (the refusal and the skip; `render_only_mut.sh` is the harness):

```bash
#!/bin/bash
# skiptests.sh : the render step's refusal and skip, with the gate's own render_step (render-only copy of gate.sh), xvfb-run hidden or not.
SP=$(cat "$(dirname "$0")/../sp.txt"); H=$SP/h/render_only_mut.sh; cd $SP/mut
export XDG_DATA_HOME=$SP/xdg-mut
# a PATH without xvfb-run: symlink farm of every other executable on PATH
FARM=$SP/farm; rm -rf $FARM; mkdir -p $FARM
IFS=: read -ra dirs <<< "$PATH"
for d in "${dirs[@]}"; do for f in "$d"/*; do b=$(basename "$f"); [ "$b" = xvfb-run ] && continue; [ -x "$f" ] && [ ! -e "$FARM/$b" ] && ln -s "$f" "$FARM/$b"; done; done 2>/dev/null
echo "farm has xvfb-run: $([ -e $FARM/xvfb-run ] && echo yes || echo no); command -v with farm PATH: $(PATH=$FARM command -v xvfb-run || echo none)"
run() { # label, PATH, env-assignment...
  local label="$1" p="$2"; shift 2
  env -u MATTINI_SKIP_RENDER PATH="$p" "$@" bash $H > $SP/runs/skip-$label.out 2> $SP/runs/skip-$label.err; local rc=$?
  echo "--- $label: exit $rc | stdout lines with SKIPPED/render/xvfb: $(grep -c -a 'SKIPPED' $SP/runs/skip-$label.out) SKIPPED in stdout (log), $(grep -c -a 'SKIPPED' $SP/runs/skip-$label.err) in stderr (terminal)"
  grep -a -h '^== render\|^== gate: xvfb\|^== gate: FAILED\|^== gate: all steps\|RENDER ' $SP/runs/skip-$label.out | cut -c1-260
  echo "    [stderr]"; grep -a -h . $SP/runs/skip-$label.err | cut -c1-200 | head -5
}
run hidden-novar     "$FARM"
run hidden-var1      "$FARM" MATTINI_SKIP_RENDER=1
for v in "" 0 true yes " 1" "1 " 2; do run "hidden-var[$v]" "$FARM" "MATTINI_SKIP_RENDER=$v"; done
run visible-var1     "$PATH" MATTINI_SKIP_RENDER=1
```

### B. The photo's corners (Hard Rule 4, the real village)

`uv run --project pipeline python -I photo_expect.py <clone>/data/raw samples.json`, then `godot --headless --path game -s probe_photo.gd -- samples.json out.json` in the clone with the village built; the two JSON files are compared per texel.

```python
"""Independent expectation of photo texels: each (col,row) of the 0.2 m grid over E 2623000..2625000 / N 1095000..1098000 is the
mean (round half to even) of its four 0.1 m source pixels, read from the swissimage tiles with rasterio, no code of mattini."""
import json, random, sys
import numpy as np, rasterio
raw = sys.argv[1]; out = sys.argv[2]
E0, N1 = 2623000, 1098000           # box north-west corner, metres
tiles = {}
def tile(ek, nk):
    k = (ek, nk)
    if k not in tiles:
        ds = rasterio.open(f"{raw}/swissimage/2023/swissimage-dop10_2023_{ek}-{nk}_0.1_2056.tif")
        tiles[k] = (ds, ds.read([1, 2, 3]))
    return tiles[k]
def source_pixel(dm_e, dm_n_top):
    """pixel whose north-west corner is at E = dm_e/10 m, N = dm_n_top/10 m (decimetres)"""
    ek, nk = dm_e // 10000, (dm_n_top - 1) // 10000
    ds, data = tile(ek, nk)
    t = ds.transform
    assert abs(t.a - 0.1) < 1e-9 and abs(t.e + 0.1) < 1e-9
    col = round((dm_e / 10 - t.c) / 0.1); row = round((t.f - dm_n_top / 10) / 0.1)
    return data[:, row, col].astype(np.int64)
def texel(c, r):
    e = E0 * 10 + 2 * c; n = N1 * 10 - 2 * r          # decimetres of the texel's north-west corner
    px = [source_pixel(e + dx, n - dy) for dy in (0, 1) for dx in (0, 1)]
    s = sum(px)                                        # mean of 4, round half to even
    return [int(np.round(v / 4.0)) for v in s]
random.seed(7)
pts = [(0, 0), (9999, 0), (0, 14999), (9999, 14999)]
pts += [(random.randrange(10000), random.randrange(15000)) for _ in range(60)]
pts += [(c, 0) for c in (1, 5000, 9998)] + [(c, 14999) for c in (1, 5000, 9998)] + [(0, r) for r in (1, 7500, 14998)] + [(9999, r) for r in (1, 7500, 14998)]
res = []
for c, r in pts:
    res.append({"c": c, "r": r, "rgb": texel(c, r),
                "east": texel(min(c + 1, 9999), r), "south": texel(c, min(r + 1, 14999)), "west": texel(max(c - 1, 0), r), "north": texel(c, max(r - 1, 0))})
json.dump(res, open(out, "w"))
print(len(res), "samples", res[:4])
```

```gdscript
extends SceneTree
## prints the photo rect against to_local of the box corners, and the decoded pixels at the texels of the JSON given after --
func _initialize() -> void:
	await process_frame
	var args := OS.get_cmdline_user_args()
	var manifest := "res://assets/generated/manifest.json"
	var world := WorldConfig.from_manifest(manifest)
	var photo := PhotoGrid.from_manifest(manifest, world)
	var nw := world.to_local(2623000.0, 1098000.0, world.height_offset)
	var se := world.to_local(2625000.0, 1095000.0, world.height_offset)
	print("PHOTORECT rect=%s nw=%s se=%s columns=%d rows=%d cell=%s" % [photo.rect(), nw, se, photo.columns, photo.rows, photo.cell_m])
	var img := photo.texture.get_image()
	print("PHOTORECT image %dx%d format=%d mipmaps=%s" % [img.get_width(), img.get_height(), img.get_format(), img.has_mipmaps()])
	var samples: Array = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var out := []
	for s in samples:
		var c := int(s["c"]); var r := int(s["r"])
		var d := {}
		for key in ["rgb", "east", "south", "west", "north"]:
			pass
		var px := img.get_pixel(c, r)
		var pe := img.get_pixel(mini(c + 1, 9999), r)
		var ps := img.get_pixel(c, mini(r + 1, 14999))
		var pw := img.get_pixel(maxi(c - 1, 0), r)
		var pn := img.get_pixel(c, maxi(r - 1, 0))
		# the texel the shader's own rule picks for the texel centre's world position
		var centre_x := photo.x0 + (c + 0.5) * photo.cell_m
		var centre_z := photo.z0 + (r + 0.5) * photo.cell_m
		var u := (centre_x - photo.x0) / photo.width_m
		var v := (centre_z - photo.z0) / photo.depth_m
		var cc := floori(u * photo.columns)
		var rr := floori(v * photo.rows)
		out.append({"c": c, "r": r, "game": [px.r8, px.g8, px.b8], "game_east": [pe.r8, pe.g8, pe.b8], "game_south": [ps.r8, ps.g8, ps.b8], "game_west": [pw.r8, pw.g8, pw.b8], "game_north": [pn.r8, pn.g8, pn.b8], "shader_texel": [cc, rr]})
	var f := FileAccess.open(args[1], FileAccess.WRITE)
	f.store_string(JSON.stringify(out))
	f.close()
	quit(0)
```

### C. margin_trees.gd (P-01 and the tree check's margins)

`xvfb-run -a godot --path game --audio-driver Dummy --rendering-method gl_compatibility --resolution 1280x720 -s margin_trees.gd -- <seed> <centres|random|all> <crown radius> <out.json> [<out.png>]`; the world, the camera and the estimators are the gate's, copied from `render_trees.gd`, with the photo replaced by a seeded random one and a second capture with the `Trees` node hidden.

```gdscript
extends SceneTree
## Reviewer's scratch: the gate's tree check on other photos and other tree layouts (the estimator's margins).
## godot --path game --rendering-method gl_compatibility --resolution 1280x720 -s margin_trees.gd -- <seed> <layout> <crown_radius> <out.json>
## layouts: centres (the gate's), random, all (a tree in every block but the first row). The photo is 80 x 40 texels of 8 x 8
## blocks with random colours (seeded), JPEG q92 like the fixture; labelled test data.
const CompleteWorld := preload("res://tests/complete_world.gd")
const Common := preload("res://tests/render/render_common.gd")
const LEVEL := 605.0
const PHOTO_X0 := 1017.0
const PHOTO_Z0 := 11.5
const BLOCK_M := 1.6
const CAMERA_AT := Vector3(1025.0, LEVEL + 22.0, 15.5)
const WORLD_DIR := "user://margin_trees"
const DISCS := [0.2, 0.3, 0.4, 0.6]
const SHIFTS := [[0.25, 0.0], [-0.25, 0.0], [0.5, 0.0], [-0.5, 0.0], [1.0, 0.0], [-1.0, 0.0], [0.0, 0.5], [0.0, -0.5], [0.0, 1.0], [0.0, -1.0], [1.6, 0.0], [0.0, 1.6]]


func _initialize() -> void:
	await process_frame
	var args := OS.get_cmdline_user_args()
	var seed_value := int(args[0])
	var layout: String = args[1]
	var crown_radius := float(args[2])
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var heights := PackedFloat32Array()
	heights.resize(41 * 24)
	heights.fill(LEVEL)
	var bytes := heights.to_byte_array()
	var trees := PackedFloat32Array()
	var count := 0
	if layout == "random":
		var placed := []
		while placed.size() < 20:
			var x := PHOTO_X0 + rng.randf_range(1.0, 15.0)
			var z := PHOTO_Z0 + rng.randf_range(1.0, 7.0)
			var ok := true
			for p: Vector2 in placed:
				if p.distance_to(Vector2(x, z)) < 1.8:
					ok = false
			if ok:
				placed.append(Vector2(x, z))
		for p: Vector2 in placed:
			trees.append_array(PackedFloat32Array([p.x, LEVEL, p.y, 4.0, crown_radius]))
	else:
		for bz in range(1, 5):
			for bx in range(0, 10, 2 if layout == "centres" else 1):
				trees.append_array(PackedFloat32Array([PHOTO_X0 + BLOCK_M * (bx + 0.5), LEVEL, PHOTO_Z0 + BLOCK_M * (bz + 0.5), 4.0, crown_radius]))
	count = trees.size() / 5
	var chunk := trees.to_byte_array()
	# the photo: random block colours
	var img := Image.create(80, 40, false, Image.FORMAT_RGB8)
	for by in 5:
		for bx in 10:
			var c := Color8(rng.randi_range(20, 235), rng.randi_range(20, 235), rng.randi_range(20, 235))
			for y in 8:
				for x in 8:
					img.set_pixel(bx * 8 + x, by * 8 + y, c)
	var jpg := img.save_jpg_to_buffer(0.92)
	var dec := Image.new()
	dec.load_jpg_from_buffer(jpg)
	var path := CompleteWorld.write(
		WORLD_DIR,
		func(m: Dictionary) -> void:
			m["terrain"]["sha256"] = CompleteWorld.sha256(bytes)
			Common.bury_buildings(WORLD_DIR, m)
			var f := FileAccess.open(WORLD_DIR.path_join(CompleteWorld.TREES_FILE), FileAccess.WRITE)
			f.store_buffer(chunk)
			f.close()
			m["trees"]["chunks"] = [{"file": CompleteWorld.TREES_FILE, "sha256": CompleteWorld.sha256(chunk), "tile": CompleteWorld.TILE, "trees": count}]
			var pf := FileAccess.open(WORLD_DIR.path_join(m["photo"]["file"]), FileAccess.WRITE)
			pf.store_buffer(jpg)
			pf.close()
			m["photo"]["sha256"] = CompleteWorld.sha256(jpg)
			m["photo"]["pixels_sha256"] = CompleteWorld.sha256(dec.get_data()),
		bytes
	)
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = path
	root.add_child(main)
	for i in 4:
		await process_frame
	var world := WorldConfig.from_manifest(path)
	var photo := PhotoGrid.from_manifest(path, world)
	if photo == null:
		print("MARGIN photo refused")
		quit(2)
		return
	main.get_node("UI/ErrorPanel").hide()
	var terrain: Terrain3D = main.get_node("Terrain")
	terrain.material.set_shader_param("surfaces", ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_L8)))
	var camera: FreeFlyCamera = main.get_node("Camera")
	camera.set_view(CAMERA_AT, 0.0, -deg_to_rad(89.0))
	var image := await Common.capture(self)
	if args.size() > 4:
		image.save_png(args[4])
	# the same view with the Trees node hidden: the bare ground (what a render with no tree drawn shows)
	main.get_node("Trees").hide()
	var bare := await Common.capture(self)
	main.get_node("Trees").show()
	var source := photo.texture.get_image()
	var result := {"seed": seed_value, "layout": layout, "crown_radius": crown_radius, "trees": count}
	# expected luminances
	var exp_right := PackedFloat64Array()
	var exp_swap := PackedFloat64Array()
	var exp_ns := PackedFloat64Array()
	var exp_ew := PackedFloat64Array()
	var exp_shift := []
	for s in SHIFTS:
		exp_shift.append(PackedFloat64Array())
	for k in count:
		var x := trees[5 * k]
		var z := trees[5 * k + 2]
		exp_right.append(_photo_lum(source, photo, x, z))
		exp_swap.append(_photo_lum(source, photo, photo.x0 + (z - photo.z0) * photo.width_m / photo.depth_m, photo.z0 + (x - photo.x0) * photo.depth_m / photo.width_m))
		exp_ns.append(_photo_lum(source, photo, x, 2.0 * photo.z0 + photo.depth_m - z))
		exp_ew.append(_photo_lum(source, photo, 2.0 * photo.x0 + photo.width_m - x, z))
		for i in SHIFTS.size():
			exp_shift[i].append(_photo_lum(source, photo, x + SHIFTS[i][0], z + SHIFTS[i][1]))
	var estimators := {}
	for disc: float in DISCS:
		var rendered := PackedFloat64Array()
		for k in count:
			rendered.append(_crown_lum(image, camera, Vector3(trees[5 * k], LEVEL + 2.0, trees[5 * k + 2]), disc))
		var row := {"right": Common.corr(rendered, exp_right), "swap": Common.corr(rendered, exp_swap), "ns": Common.corr(rendered, exp_ns), "ew": Common.corr(rendered, exp_ew)}
		var sh := []
		for i in SHIFTS.size():
			sh.append(Common.corr(rendered, exp_shift[i]))
		row["shifts"] = sh
		estimators["disc_%.1f" % disc] = row
	var rendered_apex := PackedFloat64Array()
	for k in count:
		var s := 0.0
		var n := 0
		for height in [1.6, 2.0, 2.4]:
			var at := camera.unproject_position(Vector3(trees[5 * k], LEVEL + height, trees[5 * k + 2]))
			for dy in range(-2, 3):
				for dx in range(-2, 3):
					s += Common.lum(image.get_pixel(int(at.x) + dx, int(at.y) + dy))
					n += 1
		rendered_apex.append(s / n)
	estimators["apex5x5"] = {"right": Common.corr(rendered_apex, exp_right), "swap": Common.corr(rendered_apex, exp_swap), "ns": Common.corr(rendered_apex, exp_ns), "ew": Common.corr(rendered_apex, exp_ew)}
	var rend_bare := PackedFloat64Array()
	var rend_trees := PackedFloat64Array()
	var diffs := []
	for k in count:
		var axis := Vector3(trees[5 * k], LEVEL + 2.0, trees[5 * k + 2])
		var a := _crown_lum(image, camera, axis, 0.4)
		var b := _crown_lum(bare, camera, axis, 0.4)
		rend_trees.append(a)
		rend_bare.append(b)
		diffs.append(absf(a - b))
	diffs.sort()
	estimators["bare_ground_disc_0.4"] = {"right": Common.corr(rend_bare, exp_right), "swap": Common.corr(rend_bare, exp_swap), "ns": Common.corr(rend_bare, exp_ns), "ew": Common.corr(rend_bare, exp_ew)}
	result["presence_abs_luminance_diff_min_median_max"] = [diffs[0], diffs[diffs.size() / 2], diffs[diffs.size() - 1]]
	result["estimators"] = estimators
	var out := FileAccess.open(args[3], FileAccess.WRITE)
	out.store_string(JSON.stringify(result))
	out.close()
	CompleteWorld.remove_tree(WORLD_DIR)
	quit(0)


func _crown_lum(image: Image, camera: Camera3D, axis: Vector3, read_m: float) -> float:
	var centre := camera.unproject_position(axis)
	var radius := centre.distance_to(camera.unproject_position(axis + Vector3(read_m, 0, 0)))
	var total := 0.0
	var n := 0
	var reach := ceili(radius)
	for dy in range(-reach, reach + 1):
		for dx in range(-reach, reach + 1):
			if dx * dx + dy * dy <= radius * radius:
				total += Common.lum(image.get_pixel(int(centre.x) + dx, int(centre.y) + dy))
				n += 1
	return total / maxi(n, 1)


func _photo_lum(source: Image, photo: PhotoGrid, x: float, z: float) -> float:
	var col := floori((x - photo.x0) / photo.cell_m)
	var row := floori((z - photo.z0) / photo.cell_m)
	var total := 0.0
	var n := 0
	for dr in range(-3, 4):
		for dc in range(-3, 4):
			total += Common.lum(source.get_pixel(clampi(col + dc, 0, photo.columns - 1), clampi(row + dr, 0, photo.rows - 1)))
			n += 1
	return total / n
```

### D. The north-west world (`NW-00-clean`, P-02)

The nine edits as a diff against `a6779f3`; applied with `git apply`, undone with `git apply -R`; the render step then passes (photo 0.9761, classes 83096 of 83427, trees 0.9177). The `NW-…` mutations are this diff plus one edit each.

```diff
diff --git a/game/tests/render/render_photo.gd b/game/tests/render/render_photo.gd
index 4fbfd64..d23ff57 100644
--- a/game/tests/render/render_photo.gd
+++ b/game/tests/render/render_photo.gd
@@ -35,10 +35,10 @@ const LEVEL := 605.0
 ## One pixel in STEP in each direction is sampled.
 const STEP := 3
 ## The camera's local position: over the photo's middle, 9 m above the ground.
-const CAMERA_AT := Vector3(1025.0, LEVEL + 9.0, 16.25)
+const CAMERA_AT := Vector3(-75.0, LEVEL + 9.0, -83.75)
 ## The samples' area, local x and z: inside the terrain, where the camera sees ground.
-const AREA_X := Vector2(1015.0, 1035.0)
-const AREA_Z := Vector2(10.5, 22.0)
+const AREA_X := Vector2(-85.0, -65.0)
+const AREA_Z := Vector2(-89.5, -78.0)
 ## The photo samples stay this far inside the photo's rectangle, as a fraction of it.
 const PHOTO_MARGIN := 0.03
 ## The photo shifts scanned, in 0.05 m steps, each way.
diff --git a/game/tests/render/render_trees.gd b/game/tests/render/render_trees.gd
index 4300a65..a3ec2ca 100644
--- a/game/tests/render/render_trees.gd
+++ b/game/tests/render/render_trees.gd
@@ -35,8 +35,8 @@ const BLOCK_M := 1.6
 const BLOCKS_ACROSS := 10
 const BLOCKS_DOWN := 5
 ## The photo fixture's rectangle in this world, local x0 and z0 (the complete world's PHOTO_BOX).
-const PHOTO_X0 := 1017.0
-const PHOTO_Z0 := 11.5
+const PHOTO_X0 := -83.0
+const PHOTO_Z0 := -88.5
 ## A tree's height and crown radius, metres: the records' last two floats.
 const TREE_HEIGHT_M := 4.0
 const TREE_CROWN_M := 0.7
@@ -46,7 +46,7 @@ const CROWN_READ_M := 0.4
 const CROWN_AXIS_M := 2.0
 ## The photo under a tree is averaged over this many texels each way from its centre.
 const PHOTO_TEXELS := 3
-const CAMERA_AT := Vector3(1025.0, LEVEL + 22.0, 15.5)
+const CAMERA_AT := Vector3(-75.0, LEVEL + 22.0, -84.5)
 const TREES_MIN_CORR := 0.6
 const WORLD_DIR := "user://render_trees"
 
diff --git a/tests/shared/terrain_fixture/generated/manifest.json b/tests/shared/terrain_fixture/generated/manifest.json
index ee11e1d..702e14f 100644
--- a/tests/shared/terrain_fixture/generated/manifest.json
+++ b/tests/shared/terrain_fixture/generated/manifest.json
@@ -52,10 +52,10 @@
       "horizontal": "EPSG:2056",
       "vertical": "EPSG:5728"
     },
-    "height_offset_m": 1000.0,
+    "height_offset_m": 1234.5,
     "origin_lv95": {
-      "e": 2600000.0,
-      "n": 1200000.0
+      "e": 2601100.0,
+      "n": 1199900.0
     },
     "schema": 1
   },
```

### E. The scratch world

As R1's Appendix E: `config/world.json` with origin E 2625000.0 / N 1095000.0 and `height_offset_m` 1000.0, then `recompute_expected.py <clone> <raw>` (unchanged; 468 s here), the Godot import, `probe_trees.gd` and `probe_photo.gd`.

### F. The mutations' edits

One line per edit: `TP` = `game/shaders/terrain_photo.gdshader`, `TC` = `game/shaders/tree_conifer.gdshader`, `SG` = `game/scripts/terrain/surface_grid.gd`, `TL` = `game/scripts/terrain/terrain_loader.gd`, `PG` = `game/scripts/terrain/photo_grid.gd`, `TRL` = `game/scripts/trees/tree_loader.gd`, `MAIN` = `game/scripts/main.gd`, `MT` = `game/main.tscn`, `TREES` = `pipeline/mattini/trees.py`, `GATE` = `tools/gate.sh`, `RP` = `game/tests/render/render_photo.gd`, `RT` = `game/tests/render/render_trees.gd`, `FIX` = `tests/shared/terrain_fixture/generated/manifest.json`; `PUV` = `vec2 puv = (v_vertex.xz - photo_rect.xy) / photo_rect.zw;`, `XZ` = `vec2 xz = v_vertex.xz;`, `CLS` = `vec4 classes = class_weights(xz); // rock, water, path, road`, `ORG` = `vec3 origin = MODEL_MATRIX[3].xyz;`, `UV` = `vec2 uv = (origin.xz - photo_rect.xy) / photo_rect.zw;`, `TLINE` = `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 0.5;`, `FETCH` = `texelFetch(surfaces, p, 0)`, `WGT` = `w += b * vec4(float(c == 1), float(c == 2), float(c == 3), float(c == 4));`, `NRM` = `NORMAL = normalize(cross(dFdy(VERTEX), dFdx(VERTEX)));`. Families are written once with `<d>` and their values; `H21` to `H36` repeat `H11` to `H19`. Files are `specs.py` (A to E), `specs2.py` (S, NW, V, C40 to C44), `specs3.py` (H), `specs4.py` (L), `specs5.py` (R, T), `specs6.py` (G), `specs_fix2.py` (F2), `specs_gate.py` (GS).

**specs.py**

- `A1-SH-photo-uv-flip`: TP: after PUV add `puv.y = 1.0 - puv.y;`
- `A2-SH-photo-uv-shift`: TP: after PUV add `puv.x -= 0.1 / photo_rect.z;`
- `A3-SH-class-half-texel`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size);`
- `A4-SH-class-ns-flip`: TP: FETCH → `texelFetch(surfaces, ivec2(p.x, size.y - 1 - p.y), 0)`
- `A5-GM-surf-texture-flip`: SG: `texture = ImageTexture.create_from_image(image)` → `image.flip_y()\n texture = ImageTexture.create_from_image(image)`
- `A6-SH-tree-uv-zx`: TC: UV → `vec2 uv = (origin.zx - photo_rect.xy) / photo_rect.zw;`
- `A7-V11-xz-x+0.1`: TP: after XZ add `xz.x += 0.1;`
- `A8-V11-origin-x+1.0`: TC: after ORG add `origin.x += 1.0;`
- `A9-xz.y-negated`: TP: after XZ add `xz.y = -xz.y;`
- `B01-puv-swap-yx`: TP: after PUV add `puv = puv.yx;`
- `B02-puv-ew-flip`: TP: after PUV add `puv.x = 1.0 - puv.x;`
- `B03-puv-centre-e+half`: TP: after PUV add `puv += vec2(0.5, 0.0) / vec2(textureSize(photo, 0));`
- `B04-puv-centre-e-half`: TP: after PUV add `puv -= vec2(0.5, 0.0) / vec2(textureSize(photo, 0));`
- `B05-puv-centre-n+half`: TP: after PUV add `puv += vec2(0.0, 0.5) / vec2(textureSize(photo, 0));`
- `B06-puv-centre-n-half`: TP: after PUV add `puv -= vec2(0.0, 0.5) / vec2(textureSize(photo, 0));`
- `B07-puv-centre-both`: TP: after PUV add `puv += vec2(0.5) / vec2(textureSize(photo, 0));`
- `B21-puv-width-minus-0.2m`: TP: PUV → `vec2 puv = (v_vertex.xz - photo_rect.xy) / (photo_rect.zw - vec2(0.2));`
- `C20-classes-xz-swap`: TP: CLS → `vec4 classes = class_weights(xz.yx); // rock, water, path, road`
- `C21-fetch-transpose`: TP: FETCH → `texelFetch(surfaces, p.yx, 0)`
- `C22-fetch-ew-flip`: TP: FETCH → `texelFetch(surfaces, ivec2(size.x - 1 - p.x, p.y), 0)`
- `C23-t-plus-half`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) + 0.5;`
- `C24-codes-road-path-swapped`: TP: WGT → `w += b * vec4(float(c == 1), float(c == 2), float(c == 4), float(c == 3));`
- `C25-codes-rock-water-swapped`: TP: WGT → `w += b * vec4(float(c == 2), float(c == 1), float(c == 3), float(c == 4));`
- `C26-water-only-shift-0.1`: TP: after CLS add `classes.y = class_weights(xz + vec2(0.1, 0.0)).y;`
- `C27-rock-only-shift-0.5`: TP: after CLS add `classes.x = class_weights(xz + vec2(0.5, 0.0)).x;`
- `C28-road-only-shift-0.5`: TP: after CLS add `classes.w = class_weights(xz + vec2(0.5, 0.0)).w;`
- `C29-path-only-mirror`: TP: after CLS add `classes.z = class_weights(vec2(xz.x, -xz.y)).z;`
- `C30-classat-round`: SG: `var column := floori((x - x0) / cell_m)` → `var column := roundi((x - x0) / cell_m)`
- `C31-surfaces-rect-shift-0.1`: TL: `material.set_shader_param("surfaces_rect", surfaces.rect())` → `material.set_shader_param("surfaces_rect", surfaces.rect() + Vector4(0.1, 0.0, 0.0, 0.0))`
- `C32-surfaces-rect-shift-0.05`: TL: `material.set_shader_param("surfaces_rect", surfaces.rect())` → `material.set_shader_param("surfaces_rect", surfaces.rect() + Vector4(0.05, 0.0, 0.0, 0.0))`
- `C33-photo-rect-shift-0.1`: TL: `material.set_shader_param("photo_rect", photo.rect())` → `material.set_shader_param("photo_rect", photo.rect() + Vector4(0.1, 0.0, 0.0, 0.0))`
- `C34-photo-rect-from-surfaces`: TL: `material.set_shader_param("photo_rect", photo.rect())` → `material.set_shader_param("photo_rect", photo.rect() if surfaces == null else surfaces.rect())`
- `C35-photo-texture-flip-in-reader`: PG: `image.generate_mipmaps()` → `image.flip_y()\n image.generate_mipmaps()`
- `C36-photo-x0-half-texel`: PG: `x0 = north_west.x` → `x0 = north_west.x + 0.1`
- `D20-uv-ns-flip`: TC: after UV add `uv.y = 1.0 - uv.y;`
- `D21-uv-ew-flip`: TC: after UV add `uv.x = 1.0 - uv.x;`
- `D22-uv-swap`: TC: after UV add `uv = uv.yx;`
- `D23-uv-from-model-vertex`: TC: UV → `vec2 uv = (VERTEX.xz - photo_rect.xy) / photo_rect.zw;`
- `D24-uv-per-vertex-world`: TC: UV → `vec2 uv = ((MODEL_MATRIX * vec4(VERTEX, 1.0)).xz - photo_rect.xy) / photo_rect.zw;`
- `D25-uv-rect-shift-x+0.5`: TC: UV → `vec2 uv = (origin.xz - (photo_rect.xy + vec2(0.5, 0.0))) / photo_rect.zw;`
- `D30-normal-reverted`: TC: NRM → `NORMAL = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));`
- `D31-normal-braced-second`: TC: after NRM add `if (true) { NORMAL = -NORMAL; }`
- `D40-crown-boost-0.4`: TC: `uniform float crown_boost = 1.25;` → `uniform float crown_boost = 0.4;`
- `D41-crown-boost-3.0`: TC: `uniform float crown_boost = 1.25;` → `uniform float crown_boost = 3.0;`
- `D42-rim-shade-0.2`: TC: `uniform float rim_shade = 0.75;` → `uniform float rim_shade = 0.2;`
- `D43-lod-plus-3`: TC: `float lod = log2(max(crown_width / texel, 1.0));` → `float lod = log2(max(crown_width / texel, 1.0)) + 3.0;`
- `E01-main-trees-rect-xz-exchanged`: MAIN: `var rect := photo.rect() if photo != null else Vector4.ZERO` → `var rect := Vector4(photo.rect().y, photo.rect().x, photo.rect().z, photo.rect().w) if photo != null else Vector4.ZERO`
- `E03-main-trees-node-1km-east`: MAIN: `move_child(TreeLoader.create(chunks, self, texture, rect), _ui.get_index())` → `var trees_node := TreeLoader.create(chunks, self, texture, rect)\n trees_node.position = Vector3(1000.0, 0.0, 0.0)\n move_child(trees_node, _ui.get_index())`
- `E11-tree-buffer-y+0.5`: TRL: `buffer.append(at.y)` → `buffer.append(at.y + 0.5)`
- `E12-tree-buffer-z-mirror`: TRL: `buffer.append(at.z)` → `buffer.append(-at.z)`
- `B10-puv-x<d>`, d = -0.01, -0.025, -0.04, -0.05, -0.075, -0.1, -0.2: TP: after PUV add `puv.x -= <d> / photo_rect.z;`
- `B11-puv-z<d>`, d = -0.01, -0.025, -0.04, -0.05, -0.075, -0.1, -0.2: TP: after PUV add `puv.y -= <d> / photo_rect.w;`
- `B12-puv-x<d>`, d = +0.025, +0.05, +0.1: TP: after PUV add `puv.x += <d> / photo_rect.z;`
- `B13-puv-z<d>`, d = +0.025, +0.05, +0.1: TP: after PUV add `puv.y += <d> / photo_rect.w;`
- `B20-puv-scale<d>`, d = -1.0005, -1.002, -1.005, -1.02: TP: after PUV add `puv *= <d>;`
- `C10-xz-x<d>`, d = +0.025, +0.05, +0.075, +0.1, +0.15, +0.2: TP: after XZ add `xz.x += <d>;`
- `C11-xz-z<d>`, d = +0.025, +0.05, +0.075, +0.1, +0.15, +0.2: TP: after XZ add `xz.y += <d>;`
- `C12-xz-x<d>`, d = -0.05, -0.1: TP: after XZ add `xz.x -= <d>;`
- `C13-xz-z<d>`, d = -0.05, -0.1: TP: after XZ add `xz.y -= <d>;`
- `D10-origin-x<d>`, d = +0.1, +0.25, +0.5, +0.75, +1.0, +1.6, +3.2: TC: after ORG add `origin.x += <d>;`
- `D11-origin-z<d>`, d = +0.1, +0.25, +0.5, +0.75, +1.0, +1.6, +3.2: TC: after ORG add `origin.z += <d>;`
- `E02-main-trees-rect-x<d>`, d = +0.5, +1.0, +2.0: MAIN: `var rect := photo.rect() if photo != null else Vector4.ZERO` → `var rect := (photo.rect() + Vector4(<d>, 0.0, 0.0, 0.0)) if photo != null else Vector4.ZERO`
- `E10-tree-buffer-x<d>`, d = +0.1, +0.25, +0.5, +1.0: TRL: `buffer.append(at.x)` → `buffer.append(at.x + <d>)`

**specs2.py**

- `S-abs-xz`: TP: after XZ add `xz = abs(xz);`
- `NW-abs-xz`: the `NW-00-clean` edits plus TP: after XZ add `xz = abs(xz);`
- `S-abs-puv`: TP: PUV → `vec2 puv = (abs(v_vertex.xz) - photo_rect.xy) / photo_rect.zw;`
- `NW-abs-puv`: the `NW-00-clean` edits plus TP: PUV → `vec2 puv = (abs(v_vertex.xz) - photo_rect.xy) / photo_rect.zw;`
- `S-abs-origin`: TC: after ORG add `origin = abs(origin);`
- `NW-abs-origin`: the `NW-00-clean` edits plus TC: after ORG add `origin = abs(origin);`
- `S-abs-origin-x`: TC: after ORG add `origin.x = abs(origin.x);`
- `NW-abs-origin-x`: the `NW-00-clean` edits plus TC: after ORG add `origin.x = abs(origin.x);`
- `S-loader-abs-x`: TRL: `buffer.append(at.x)` → `buffer.append(absf(at.x))`
- `NW-loader-abs-x`: the `NW-00-clean` edits plus TRL: `buffer.append(at.x)` → `buffer.append(absf(at.x))`
- `S-loader-abs-z`: TRL: `buffer.append(at.z)` → `buffer.append(absf(at.z))`
- `NW-loader-abs-z`: the `NW-00-clean` edits plus TRL: `buffer.append(at.z)` → `buffer.append(absf(at.z))`
- `S-loader-int-cell-x`: TRL: `var key := Vector2i(floori(at.x / CELL_M), floori(at.z / CELL_M))` → `var key := Vector2i(int(at.x / CELL_M), floori(at.z / CELL_M))`
- `NW-loader-int-cell-x`: the `NW-00-clean` edits plus TRL: `var key := Vector2i(floori(at.x / CELL_M), floori(at.z / CELL_M))` → `var key := Vector2i(int(at.x / CELL_M), floori(at.z / CELL_M))`
- `S-xz-x+0.1`: TP: after XZ add `xz.x += 0.1;`
- `NW-xz-x+0.1`: the `NW-00-clean` edits plus TP: after XZ add `xz.x += 0.1;`
- `S-tree-uv-zx`: TC: UV → `vec2 uv = (origin.zx - photo_rect.xy) / photo_rect.zw;`
- `NW-tree-uv-zx`: the `NW-00-clean` edits plus TC: UV → `vec2 uv = (origin.zx - photo_rect.xy) / photo_rect.zw;`
- `NW-00-clean`: FIX: `"e": 2600000.0` → `"e": 2601100.0`; FIX: `"n": 1200000.0` → `"n": 1199900.0`; FIX: `"height_offset_m": 1000.0` → `"height_offset_m": 1234.5`; RP: `const CAMERA_AT := Vector3(1025.0, LEVEL + 9.0, 16.25)` → `const CAMERA_AT := Vector3(-75.0, LEVEL + 9.0, -83.75)`; RP: `const AREA_X := Vector2(1015.0, 1035.0)` → `const AREA_X := Vector2(-85.0, -65.0)`; RP: `const AREA_Z := Vector2(10.5, 22.0)` → `const AREA_Z := Vector2(-89.5, -78.0)`; RT: `const PHOTO_X0 := 1017.0` → `const PHOTO_X0 := -83.0`; RT: `const PHOTO_Z0 := 11.5` → `const PHOTO_Z0 := -88.5`; RT: `const CAMERA_AT := Vector3(1025.0, LEVEL + 22.0, 15.5)` → `const CAMERA_AT := Vector3(-75.0, LEVEL + 22.0, -84.5)`
- `V01-vertex-shift-x+0.1`: TP: after `v_vertex = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;` add `v_vertex.x += 0.1;`
- `V02-vertex-morph-removed`: TP: delete `v_vertex.xz -= shift * scale * vertex_lerp;`
- `V03-vertex-morph-doubled`: TP: `v_vertex.xz -= shift * scale * vertex_lerp;` → `v_vertex.xz -= 2.0 * shift * scale * vertex_lerp;`
- `C40-class-uses-photo-rect`: TP: TLINE → `vec2 t = (xz - photo_rect.xy) / photo_rect.zw * vec2(size) - 0.5;`
- `C41-photo-uses-surfaces-rect`: TP: PUV → `vec2 puv = (v_vertex.xz - surfaces_rect.xy) / surfaces_rect.zw;`
- `C42-outside-rect-fallback`: TP: delete `if (any(lessThan(puv, vec2(0.0))) || any(greaterThan(puv, vec2(1.0)))) {\n  albedo = outside_albedo;\n }`
- `C43-rock-triplanar-world-xz`: TP: `float w_rock = classes.x * smoothstep(radians(35.0), radians(55.0), slope);` → `float w_rock = 0.0;`
- `C44-flat-normal-flipped`: TP: `NORMAL = normalize(cross(dFdyCoarse(VERTEX),dFdxCoarse(VERTEX)));` → `NORMAL = normalize(cross(dFdxCoarse(VERTEX),dFdyCoarse(VERTEX)));`

**specs3.py**

- `H11-classes-x-plus-half-texel`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - vec2(0.0, 0.5);`
- `H12-classes-x-minus-half-texel`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - vec2(1.0, 0.5);`
- `H13-classes-z-plus-half-texel`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - vec2(0.5, 0.0);`
- `H14-classes-z-minus-half-texel`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - vec2(0.5, 1.0);`
- `H15-classes-both-plus-half-texel`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - vec2(0.0, 0.0);`
- `H16-classes-both-minus-half-texel`: TP: TLINE → `vec2 t = (xz - surfaces_rect.xy) / surfaces_rect.zw * vec2(size) - 1.0;`
- `H17-classat-round-x`: SG: `var column := floori((x - x0) / cell_m)` → `var column := roundi((x - x0) / cell_m)`
- `H18-classat-round-z`: SG: `var row := floori((z - z0) / cell_m)` → `var row := roundi((z - z0) / cell_m)`
- `H19-classat-minus-half-x`: SG: `var column := floori((x - x0) / cell_m)` → `var column := floori((x - x0) / cell_m - 0.5)`

**specs4.py**

- `L2-tonemap-linear`: MT: `tonemap_mode = 2` → `tonemap_mode = 0`
- `L3-tonemap-aces`: MT: `tonemap_mode = 2` → `tonemap_mode = 3`
- `L1-exposure<d>`, d = -0.30, -0.40, -0.70, -1.00, -1.50, -2.50: MT: `tonemap_exposure = 0.54` → `tonemap_exposure = <d>`

**specs5.py**

- `R1-photo-script-parse-error`: RP: after `func _initialize() -> void:` add `var broken := (`
- `R2-photo-script-quits-silently`: RP: after `func _initialize() -> void:` add `quit(0)\n return`
- `R3-trees-script-hangs`: RT: after `func _initialize() -> void:` add `while true:\n  await process_frame`
- `R4-trees-script-prints-pass-and-fails-exit`: RT: after `var ok := await _check()` add `print("RENDER trees: FAIL forced by the reviewer")\n ok = true`
- `R5-photo-script-runtime-error`: RP: after `var ok := await _check()` add `var nothing: Node = null\n nothing.queue_free()`
- `T1-visibility-end-0.5m`: TRL: `const VISIBILITY_END_M := 3000.0` → `const VISIBILITY_END_M := 0.5`
- `T1b-visibility-end-15m`: TRL: `const VISIBILITY_END_M := 3000.0` → `const VISIBILITY_END_M := 15.0`
- `T2-tree-fragment-discard`: TC: after `void fragment() {` add `discard;`
- `T3-tree-instance-count-zero`: TRL: after `multimesh.buffer = buffer` add `multimesh.visible_instance_count = 0`

**specs6.py**

- `G1-visibility-end-0.5m`: TRL: `const VISIBILITY_END_M := 3000.0` → `const VISIBILITY_END_M := 0.5`
- `G2-tree-fragment-discard`: TC: after `void fragment() {` add `discard;`
- `G3-visible-instance-count-0`: TRL: after `multimesh.buffer = buffer` add `multimesh.visible_instance_count = 0`
- `G4-normal-reverted`: TC: NRM → `NORMAL = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));`
- `G5-normal-braced-second`: TC: after NRM add `if (true) { NORMAL = -NORMAL; }`
- `G6-normal-negated-in-braces-before`: TC: NRM → `{ NORMAL = vec3(0.0, 1.0, 0.0); }\n NORMAL = normalize(cross(dFdy(VERTEX), dFdx(VERTEX)));\n { NORMAL = -NORMAL; }`
- `G7-loader-abs-x`: TRL: `buffer.append(at.x)` → `buffer.append(absf(at.x))`
- `G8-loader-cells-west-of-4-moved`: TRL: after `instance.visibility_range_end = VISIBILITY_END_M` add `if key.x < 4:\n   instance.position = Vector3(1000.0, 0.0, 0.0)`
- `G9-loader-int-cell-x`: TRL: `var key := Vector2i(floori(at.x / CELL_M), floori(at.z / CELL_M))` → `var key := Vector2i(int(at.x / CELL_M), floori(at.z / CELL_M))`

**specs_fix2.py**

- `F2-01-build-call-removed`: TREES: `area = _area(trees_config, terrain_config)\n    _spacing_refusal(area, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping` → `area = _area(trees_config, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping`
- `F2-02-block-call-removed`: TREES: `_spacing_refusal(area, terrain_config)\n\n    def fail(message: str) -> TreesError:` → `def fail(message: str) -> TreesError:`
- `F2-03-cmp-gt-1.0`: TREES: `if spacing != SOURCE_M:` → `if spacing > 1.0:`
- `F2-04-build-after-lock`: TREES: `area = _area(trees_config, terrain_config)\n    _spacing_refusal(area, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping` → `area = _area(trees_config, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping`; TREES: `entries = _locked_entries(lock, datasets, world, area)\n    problem = _inputs_refusal(settings["computed_for"], entries)\n    if problem:\n        raise TreesError(f"area {area!r}: {problem}")\n    listed = {` → `entries = _locked_entries(lock, datasets, world, area)\n    _spacing_refusal(area, terrain_config)\n    problem = _inputs_refusal(settings["computed_for"], entries)\n    if problem:\n        raise TreesError(f"area {area!r}: {problem}")\n    listed = {`
- `F2-05-build-after-world-check`: TREES: `area = _area(trees_config, terrain_config)\n    _spacing_refusal(area, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping` → `area = _area(trees_config, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping`; TREES: `configs = _configs(datasets)\n    entries = _locked_entries(lock, datasets, world, area)\n    problem = _inputs_refusal` → `configs = _configs(datasets)\n    _spacing_refusal(area, terrain_config)\n    entries = _locked_entries(lock, datasets, world, area)\n    problem = _inputs_refusal`
- `F2-06-build-after-inputs-refusal`: TREES: `area = _area(trees_config, terrain_config)\n    _spacing_refusal(area, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping` → `area = _area(trees_config, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping`; TREES: `listed = {\n        name: _provenance` → `_spacing_refusal(area, terrain_config)\n    listed = {\n        name: _provenance`
- `F2-07-build-after-provenance`: TREES: `area = _area(trees_config, terrain_config)\n    _spacing_refusal(area, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping` → `area = _area(trees_config, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping`; TREES: `tiles = area_tiles(world, area)\n    say(f"reading the {len(tiles)} terrain and surface tiles")` → `_spacing_refusal(area, terrain_config)\n    tiles = area_tiles(world, area)\n    say(f"reading the {len(tiles)} terrain and surface tiles")`
- `F2-08-build-after-first-progress-line`: TREES: `area = _area(trees_config, terrain_config)\n    _spacing_refusal(area, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping` → `area = _area(trees_config, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping`; TREES: `terrain = _mosaic(raw_root, "swissalti3d", configs, entries, listed, box, tiles)` → `_spacing_refusal(area, terrain_config)\n    terrain = _mosaic(raw_root, "swissalti3d", configs, entries, listed, box, tiles)`
- `F2-09-build-before-write`: TREES: `area = _area(trees_config, terrain_config)\n    _spacing_refusal(area, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping` → `area = _area(trees_config, terrain_config)\n    settings = trees_config["areas"][area]\n    if world.mapping`; TREES: `block = write_trees(` → `_spacing_refusal(area, terrain_config)\n    block = write_trees(`
- `F2-10-cmp-lt`: TREES: `if spacing != SOURCE_M:` → `if spacing < SOURCE_M:`
- `F2-11-cmp-eq-2`: TREES: `if spacing != SOURCE_M:` → `if spacing == 2.0:`
- `F2-12-msg-no-config-name`: TREES: `f"{TERRAIN_CONFIG_NAME}: area {area!r} has spacing_m` → `f"area {area!r} has spacing_m`
- `F2-13-msg-no-spacing`: TREES: `has spacing_m {spacing_key(spacing)}, but "` → `has spacing_m ?, but "`
- `F2-14-block-before-exists`: TREES: `description = Path(out_dir) / "trees" / f"{area}.json"\n    if not description.exists():\n        return None\n    _spacing_refusal(area, terrain_config)` → `description = Path(out_dir) / "trees" / f"{area}.json"\n    _spacing_refusal(area, terrain_config)\n    if not description.exists():\n        return None`
- `F2-15-block-after-world-and-lock`: TREES: `_spacing_refusal(area, terrain_config)\n\n    def fail` → `def fail`; TREES: `problem = _inputs_refusal(settings["computed_for"], entries)\n    if problem:\n        raise TreesError(f"area {area!r}: {problem}")\n\n    try:\n        block = json.loads(description` → `problem = _inputs_refusal(settings["computed_for"], entries)\n    if problem:\n        raise TreesError(f"area {area!r}: {problem}")\n    _spacing_refusal(area, terrain_config)\n\n    try:\n        block = json.loads(description`
- `F2-16-block-after-description-read`: TREES: `_spacing_refusal(area, terrain_config)\n\n    def fail` → `def fail`; TREES: `return block\n\n\n# ------------------------------------------------------------- the lock and the downloads` → `_spacing_refusal(area, terrain_config)\n    return block\n\n\n# ------------------------------------------------------------- the lock and the downloads`
- `F2-17-spacing-key-wrong-area`: TREES: `spacing = terrain_config["areas"][area]["spacing_m"]` → `spacing = 0.5`

**specs_gate.py**

- `GS1-timeout-disabled`: GATE: `RENDER_TIMEOUT=180` → `RENDER_TIMEOUT=0`
- `GS2-skip-line-once`: GATE: delete `echo "$RENDER_SKIP_LINE" >&2`
- `GS3-pass-regex-unanchored`: GATE: `grep -a -q -E "^RENDER $check: PASS( |\$)"` → `grep -a -q -E "RENDER $check: PASS"`
- `GS4-audio-driver-removed`: GATE: delete `--audio-driver Dummy`
- `GS5-variable-silent-when-xvfb-present`: GATE: `echo "== render: MATTINI_SKIP_RENDER=$MATTINI_SKIP_RENDER is set but xvfb-run is here, so the step runs: the variable excuses only a machine without xvfb-run"` → `true`
- `GS6-render-before-gdformat`: GATE: `step "gdformat --check" "${UV_RUN[@]}" gdformat --check "${GD_FILES[@]}"\nstep "render" render_step` → `step "render" render_step\nstep "gdformat --check" "${UV_RUN[@]}" gdformat --check "${GD_FILES[@]}"`
- `GS7-trees-script-not-run`: GATE: `render_script res://tests/render/render_trees.gd trees` → `true`
- `GS8-fail-grep-removed`: GATE: `if grep -a -E '^RENDER [^:]+: FAIL' "$SCRATCH/out.log"; then` → `if false; then`
- `GS9-engine-scan-off`: GATE: `run_scanned '^(ERROR|SCRIPT ERROR)' "" \\n  env XDG_DATA_HOME` → `run_scanned '^$NEVER_MATCHES$' "" \\n  env XDG_DATA_HOME`
- `GS10-skip-any-nonempty`: GATE: `if [ "${MATTINI_SKIP_RENDER:-}" = "1" ]; then` → `if [ -n "${MATTINI_SKIP_RENDER:-}" ]; then`
- `GS11-skip-where-xvfb-present`: GATE: `if ! command -v xvfb-run > /dev/null; then\n  if [ "${MATTINI_SKIP_RENDER:-}" = "1" ]; then` → `if [ "${MATTINI_SKIP_RENDER:-}" = "1" ] || ! command -v xvfb-run > /dev/null; then\n  if [ "${MATTINI_SKIP_RENDER:-}" = "1" ]; then`
