# Brief: M4-03 — The capture shadows step: where the photo lay in shadow when it was flown
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane C of wave 1 (`docs/briefs/sketches/m4-design.md` §3).

## Goal

`pipeline/mattini/shadows.py` computes where the photo (SWISSIMAGE 2023) lay in shadow when it
was flown, from the swissSURFACE3D 0.5 m tiles that `download surface` already fetches, and
writes it as a 1 m mask: `shadows/<area>.png` (0 lit, 255 shadow), its `.png.import` and its
description `shadows/<area>.json`. The terrain shader (M4-06) lifts the photo inside the mask so
that the moving sun's shadows read and the photo's do not darken a second time (SPEC §13 row
41).

- **The rule:** cast shadow by a march towards the flight's sun on the 1 m cells, own shadow from
  the cells' normals, then an inset that keeps a shadow cell only inside the shadow.
- **The output** is compared with design's expected mask and PNG bytes before anything is
  written, as the surfaces step does (lesson 38, brain.md H27).
- The command line (`python -m mattini shadows`) and the manifest's `shadows` block come in wave
  2 (M4-09), which calls this brief's `build_shadows` and `built_shadows_block`.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H9, H18, H20, H22, H24, H27.
2. `docs/briefs/sketches/m4-design.md` §0 (the flight's sun) and §3 (the rule); SPEC §5 (the
   surface model), §8 *The surfaces* (the PNG format this step shares), §13 rows 39 and 41.
3. `pipeline/mattini/surfaces.py` (the PNG writer and reader, the `.import` file, the zlib
   refusal of brief M3-R1-fix-6, the order of the checks), `trees.py` (the swissSURFACE3D
   provenance, the tile checks and the mosaic), `lock.py` (`fit_problem`, `shape_problem`,
   `entry_sha256`), `terrain.py` (`world_refusal`, `check_computed_for`, `configured_area`).
4. `tests/shared/shadows_fixture/`, `tests/shared/shadows_vectors.json`, `config/shadows.json`,
   `config/sky.json` (design data, committed with the plan; never edited).
5. The pinned tests: `docs/briefs/pinning/M4-03/`.

## Decisions already made

1. **The rule** is m4-design §3, made exact here (the pinned `test_m4_03_rule.py` writes it out
   cell by cell; its docstring is the reference):
   - **The cells:** 1 m, aligned to the area's north-west corner, rows north to south, columns
     west to east; cell (r, c) has its centre at E = e_min + 0.5 + c, N = n_max − 0.5 − r. Its
     height h is the largest of its 2 × 2 swissSURFACE3D pixels, in float64. The heights are
     the tiles' LV95 heights (EPSG:5728); `height_offset_m` plays no part (only differences
     count).
   - **Cast shadow:** with A the grid azimuth and e the elevation, the offset towards the sun is
     computed once per k = 1 … K, in cells: dx = k·sin A (east), dy = −(k·cos A) (south);
     i0 = floor(dx), fx = dx − i0, j0 = floor(dy), fy = dy − j0. The surface there is bilinear
     in the four cells (r + j0 [+1], c + i0 [+1]), evaluated as north = h00·(1 − fx) + h01·fx,
     south = h10·(1 − fx) + h11·fx, s = north·(1 − fy) + south·fy. A column or row whose weight
     is 0 is not needed. **The grid is the cells' centres:** a point whose needed cells are not
     all inside it casts nothing (nothing is clamped or padded). The cell is in cast shadow if
     s > (h + k·tan e) + threshold_m for any k. Design's decision (m4-design left it open): the
     offsets per k, not per point, so that a vectorised shift and a per-cell loop give the same
     bits.
   - **K** = ceil((max − min) / tan e) over the area's cells, in float64. Measured: the last step
     can never cast (a hit needs k < (max − min − threshold) / tan e), so `range(1, K)` is an
     equivalent mutant; `march_steps` is pinned to the definition anyway.
   - **Own shadow:** gx = dh/dE and gy = dh/dN by central differences over the two neighbours
     divided by 2, one-sided and not halved on the grid's edges; with (ux, uy, uz) = (cos e·sin A,
     cos e·cos A, sin e), the cell is in its own shadow when ((−gx)·ux − gy·uy) + uz ≤ 0.
   - **Ties:** strict `>` for the cast, `≤ 0` for the normal, as m4-design §3 writes them.
   - **The inset:** a cell in cast or own shadow is 255 only when its four neighbours inside the
     grid are in shadow too (a neighbour outside the grid does not count); every other cell 0.
2. **The sun** (config/shadows.json, design data): grid azimuth **184.67°**, elevation 50.1°,
   threshold 0.05 m, cell 1 m. m4-design §3 wrote 185.13° (184.9 + 0.226); design's rehearsal
   found the sign of the grid convergence reversed: at the village LV95 grid north lies 0.226°
   east of true north, so an azimuth from true north turns into one from grid north by
   **subtracting** 0.226° (pyproj, a step along the true meridian projected to EPSG:2056:
   −0.2258°; swisstopo's approximate formulas: grid north at true azimuth +0.2261°; PROJ's
   `meridian_convergence` +0.2265° is the true azimuth of grid north). `config/sky.json` holds
   `true_to_grid_deg` −0.2258 by m4-design §4's definition (added to a true azimuth it gives the
   grid one). The pinned `test_m4_03_village_config.py` ties the two configs together.
3. **The API** (the signatures are the API):
   - `ShadowsError(ValueError)`, `SHADOWS_CONFIG_PATH`, `load_shadows_config(path)`,
     `check_shadows_config(data, where)`;
   - the rule: `cell_heights(surface)` (float32 0.5 m → float64 1 m), `march_steps(heights,
     elevation_deg)`, `cast_shadow(heights, azimuth_grid_deg, elevation_deg, threshold_m)`,
     `own_shadow(heights, azimuth_grid_deg, elevation_deg)` (bool grids), `inset(shadow)`
     (uint8 0/255), `capture_mask(surface, azimuth_grid_deg, elevation_deg, threshold_m)`;
   - `png_mask(pixels)`; `write_shadows(out_dir, area, mask, box, world_sha256, source, sun, *,
     png=None)`;
   - `build_shadows(world, datasets, lock, shadows_config, raw_root, out_dir, *, progress=None)`;
   - `built_shadows_block(out_dir, shadows_config, world, world_sha256, datasets, lock)`, the
     lock a dict or a path (as the surfaces'), None when nothing is built, refusals naming
     `python -m mattini shadows`.
4. **The inputs:** the `swisssurface3d` lock entry and `<raw>/swisssurface3d/2021-2022/` with
   its provenance.json, exactly what `lock surface` and `download surface` write (the tiles of
   `download.area_tiles`). The checks come in this order, each before the next reads anything:
   the config; the world (the owner's axes only, the area, `computed_for.world_sha256`); the
   lock's fit (`lock.fit_problem`, then `shape_problem`, naming `python -m mattini lock
   surface`); `computed_for.inputs_sha256` against `lock.entry_sha256` of the entry; the
   provenance (a missing one, or a missing tile, is refused naming `python -m mattini download
   surface`, before anything is created under `out_dir` and before any progress line); each
   tile's SHA-256 against the lock's before it is read, then the tile checks of `trees.py`
   (CRS, size, corner, nodata). A `computed_for` difference is a design change and says so,
   naming both SHA-256s (lesson 41).
5. **The PNG:** the surfaces' format: 8-bit grey, no interlace, filter 0 on every row, one zlib
   stream at level 9 in IDAT chunks of at most 1 MiB; values 0 and 255 only. `surfaces.png_l8`
   refuses values above 4, so this step has its own `png_mask`, built from the surfaces'
   `_chunk`, `PNG_SIGNATURE` and `MIB` (imported read-only, as `trees.py` imports surfaces'
   helpers); it is read back with `surfaces.read_png_l8`. The mask's SHA-256 is compared with
   `expected_pixels_sha256`, then the PNG, encoded once, with `expected_png_sha256`; each
   difference is refused before anything is written, the PNG's naming zlib and
   `zlib.ZLIB_RUNTIME_VERSION` and the remedy of brief M3-R1-fix-6.
6. **The files:** `shadows/<area>.png.import` holding exactly `[remap]\n\nimporter="keep"\n`
   (H24), then `shadows/<area>.png`, then `shadows/<area>.json`, each through a `.part`
   rename; after a write no `*.part` stays in `shadows/` (another folder's are not touched).
7. **The description** is exactly {area, cell_m (1.0), columns, file, format "png-l8",
   lv95_box, pixels_sha256, rows, sha256 (the PNG's), source, sun, world_sha256}, written as
   the surfaces' (`indent=2, sort_keys=True, ensure_ascii=False`, a newline). `source` is
   {attribution, collection, dataset "swisssurface3d", editions, entry_sha256} (m4-design §2's
   form, with `editions` since swissSURFACE3D has one edition per tile; design's decision);
   `sun` is the config's `sun` object as it stands.
8. **The config** is exactly {schema 1, cell_m 1, sun {azimuth_grid_deg, elevation_deg, note},
   threshold_m, areas: {<one area>: {computed_for {inputs_sha256, world_sha256},
   expected_pixels_sha256, expected_png_sha256}}}; the area names are the surfaces' rule. The
   step reads the sun and the threshold from it; the code holds neither.
9. **Design's values** (the village, computed two independent ways, a slice shift-march and a
   fancy-index gather with an active set, `np.gradient` and a padded inset; identical; and cell
   by cell in Python on 47'408 cells, no difference; 2026-10-17):
   - `expected_pixels_sha256` `6f958c41f34ebc58847baefe9a386e19c6b4edf3835327bb5c11eb69526b7aa6`;
   - `expected_png_sha256` `5fff6e5833156bcdfc1d45060aa83ee86e9a1cf336d861d57f9c773fc7fa4df3`
     (319'479 bytes, zlib 1.3, one IDAT chunk);
   - computed_for: inputs `f73033b1…` (the `swisssurface3d` lock entry), world `d2607d13…`.

   2000 × 3000 cells, heights 1566.05 to 2619.18 m, K = 881; 32.05 % of the cells in cast or
   own shadow (the 0.5 m measurement of m4-design §0: 32.3 %), 29.07 % cast, 2.98 % own only;
   20.45 % kept by the inset. Design's slice march took 145 s and 630 MB on the container;
   design's throwaway step end to end on the real tiles: 157.6 s, peak 533 MB resident,
   the step's own comparisons passing. zlib 1.3 (system 3.13.16, 3.12.3) and 1.3.2 (uv's
   managed 3.13.14) write the same PNG bytes. A faster march that gives the same bits is
   welcome (e.g. skipping cells whose ray is above the area's highest cell).
   The mask over the photo: `docs/briefs/sketches/M4-soften/mask-1m.jpg`.
11. **Design's rehearsal** (a throwaway `shadows.py` in a scratch clone, never committed): the
    four pinned files pass with it and fail without it (collection error); the full pytest,
    `ruff check` and `ruff format --check` green in the live layout. Each mutation of the gate
    list above failed a named pinned test, and so did "the tile's SHA-256 not checked", "no
    expected-pixels check" and "`computed_for`'s inputs not checked".
10. **The area's name** stays out of `pipeline/mattini/` (M2-01's census); the step takes it
    from the config.

## Scope — files you may touch

`pipeline/mattini/shadows.py` (new) · `pipeline/tests/`: the pinned copies
(`test_m4_03_rule.py`, `test_m4_03_fixture.py`, `test_m4_03_step.py`,
`test_m4_03_village_config.py`) and your own new `test_shadows_*.py`. Read-only: everything
else, `surfaces.py`, `trees.py`, `terrain.py`, `lock.py` and `download.py` included.

## Depends on

None at build time (the lock's `swisssurface3d` entry and `download surface` exist since M3).
M4-09 (wave 2) wires the command and the manifest; M4-06 (wave 1) reads the shared fixture's
generated folder.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M4-03/. .`) and stay
      byte-identical (`cmp`); they pass.
      - does NOT prove: that they are the right tests.
- [ ] With the real tiles (`python -m mattini download surface --out <scratch>`, 6 tiles, about
      96 MB), `build_shadows` with the committed configs writes design's `6f958c41…` and
      `5fff6e58…`, the step's own comparisons passing; record the time and the peak memory.
      - does NOT prove: that the mask lies on the photo's shadows (the surface model is from
        2021/22, the photo from 2023: crowns and new buildings differ; the owner's eyes).
- [ ] Mutations, each failing a named pinned test, recorded with the owner-visible harm: the
      sun mirrored east-west; the sun 180° off; the nearest sample for the bilinear one; the
      mean of the 2 × 2 pixels; no threshold; K without the division by tan e; a point outside
      the grid clamped to its edge; no own shadow; the edge normal halved; no inset; the inset
      counting outside cells as lit; zlib level 6; no `.png.import`; the expected-value check
      after the write; the output folder made before the download check; `computed_for`'s
      inputs checked after the provenance.
      - does NOT prove: the game's reading (M4-06), the manifest's (M4-09).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

- Changing the rule, the sun, the threshold, design's values, the fixture or a pinned file.
- Editing `surfaces.py`, `trees.py`, `terrain.py`, `lock.py`, `download.py` or any other module;
  command-line or manifest wiring (M4-09); anything under `game/` or `tools/`.
- A new dependency.

## Findings (executor writes)
