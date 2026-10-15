# Brief: M3-07 — The trees step: where the LiDAR shows a tree
Status: DONE (c6113a8)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane D of wave 1, after M3-06 (`docs/briefs/M3-plan.md`).

## Goal

`pipeline/mattini/trees.py` finds the village's trees in the LiDAR surface model
(swissSURFACE3D, flown in 2021 and 2022) and writes, per 1 km tile, each tree's position,
base height, height and crown radius. The game (M3-11) stands a procedural conifer at each.

- **The rule** works on the area's 0.5 m pixels in exact integer arithmetic, so every
  machine finds the same 34'412 trees:
  - canopy height = surface − terrain;
  - minus buildings (swissBUILDINGS3D and swissTLM3D footprints, with a 2 m margin) and
    rock;
  - smoothed, then the local maxima in a window that grows with the height;
  - cliffs, steep slopes and gaps dropped.
- **The output** is compared with design's expected values before anything is written.
- The command line and the manifest come in wave 2 (M3-13).

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H9, H17, H20.
2. `docs/SPEC.md` §5 (the surface model, swissTLM3D), §8 *The terrain grid* (the vertices
   the base height uses), *The buildings* (the sheets), *The surfaces* (the TLM reader),
   *The trees* (the rule), §13 row 29.
3. `pipeline/mattini/terrain.py` (the tile checks, `computed_for`, the resampling),
   `buildings.py` (`read_sheet`, the sheets), `surfaces.py` (M3-06, landed in this lane
   just before: `read_tlm`).
4. `tests/shared/trees_fixture/`, `tests/shared/trees_vectors.json`, `config/trees.json`
   (design data, committed with the plan; never edited).
5. The pinned tests: `docs/briefs/pinning/M3-07/`.

## Decisions already made

1. **The rule** is SPEC §8 *The trees*, steps 1 to 8. Its points most easily got wrong:
   - the masks use every building of the area's sheets whose bounding box meets the area,
     selected or not, and the TLM footprints of every OBJEKTART but 16 (underground);
   - the margin B counts the area's pixels only, and canopy in B counts 0;
   - ties go to the earlier pixel in raster order (rows from the north);
   - a dropped top is not a neighbour: d is taken over the kept trees;
   - the crown radius is clamp(min(d / 2, height / 4), 1.0, 6.0) m, d = +∞ when the tree
     has no other;
   - the 2⁻¹³ m refusal names the pixel's LV95 centre and both heights;
   - only the owner's axes; another mapping is refused.
2. **The API** (the signatures here are the API; SPEC §8 *The trees* holds the rule):
   - `TreesError(ValueError)`, `TREES_CONFIG_PATH`, `load_trees_config`,
     `check_trees_config`;
   - `build_tree_chunks(dsm, dtm, buildings, footprints, land_cover, world, area)`: the
     rule, pinned by the fixture;
   - `write_trees(out_dir, area, chunks, box, world_sha256, source, *, progress=None)`;
   - `build_trees(world, datasets, lock, trees_config, terrain_config, raw_root, out_dir, *,
     progress=None)`;
   - `built_trees_block(out_dir, trees_config, terrain_config, world, world_sha256,
     datasets, lock)`, where the lock is a dict or a path (M3-03's lock lands at the same
     time). A lock that lacks one of the four entries is refused naming its lock command,
     never a KeyError (measured in design's rehearsal: a traceback).
3. **The TLM features** reach `build_tree_chunks` as `{uuid, objektart, polygons}`
   (MultiPolygon coordinates as read, rings closed, points (E, N[, H])), so the rule does not
   depend on M3-06's record form. Read them with M3-06's `read_tlm`, whose records are
   {uuid, attributes: {OBJEKTART, …}, geometry: {type, coordinates}} in integer millimetres,
   and adapt them in `trees.py`: OBJEKTART, and the coordinates divided by 1000 (the rule
   snaps them back to the same millimetres; design's wave-1 rehearsal wrote the six chunks
   this way). fiona is imported inside the reading function, never at module level (M3-01's
   pinned `test_fiona_import.py` walks every module of the package).
4. **Inputs** in M3-03's layout:
   - `<raw_root>/swisssurface3d/2021-2022/` (the six tiles and a provenance with `editions`
     and each tile's `edition`);
   - `<raw_root>/swissalti3d/2024/`, `<raw_root>/swissbuildings3d/2020/`;
   - `<raw_root>/swisstlm3d/2026-02/swisstlm3d_2026-02_2056_5728.gdb.zip` and its flat
     provenance.

   The checks run in SPEC's order: the terrain config's area (the trees config's); the world
   (the owner's axes, `computed_for.world_sha256`); each lock entry's fit; the inputs
   `computed_for` over the four entries; the provenance; every file's SHA-256 against the
   lock, each read from the bytes hashed (the 2.88 GB zip through its path, unchanged after
   the read, as M3-06 does); the DSM and DTM tiles with the terrain's tile checks, written
   in `trees.py` after `terrain.py`'s (its tile helpers are private, and lane A changes that
   file in this wave). Only the names M3-01 keeps are imported from lane A's modules (its
   decision 10).
   - **The lock's fit, in wave 1:** the step checks its entries' fit itself, in its own
     module, by the fit rule (SPEC §8, as §5 applies it to the downloads):
     swissalti3d's and swisssurface3d's collection, edition (for the surface, `editions`, each
     tile's edition one of them) and `resolution_m` are the config's and they pin exactly
     the area's tiles; swissbuildings3d's pins exactly the area's sheets; swisstlm3d's one
     file, naming `python -m mattini lock terrain`, `lock buildings`, `lock surface` or `lock tlm`. It imports
     no fit or provenance helper of `terrain.py`, `buildings.py` or `download.py` (M3-01
     changes them in lane A): `lock.fit_problem` arrives in lane A in this wave, and M3-13
     moves the step onto it in wave 2.
   - **A missing download** is refused naming `python -m mattini download terrain`, `download buildings`, `download surface` or `download tlm`, the first missing in sorted dataset order, before anything is created under
     `out_dir`, not even a folder: no `provenance.json` before any `progress` call, as
     `terrain.py` does; a file it lists absent when it is read. M3-13's pinned CLI test runs the
     step on an empty raw folder. Not pinned in this lane: write its test.
5. **The base height** comes from the 0.5 m terrain grid (`terrain.py`'s resampling of the
   DTM), whatever the terrain config's spacing.
6. **The files:** `trees/<tile>.bin`, then `trees/<area>.json`, each through a `.part`
   rename. After a build that succeeds, stale `*.bin` and every `*.part` in `<out>/trees/`
   are removed (M3-01's rule for the terrain and the buildings). The source block:
   - swissalti3d as the terrain's, swissbuildings3d as the buildings', swisstlm3d as the
     surfaces' {attribution, collection, dataset, edition, file, sha256};
   - swisssurface3d {attribution, collection, dataset, editions, resolution_m 0.5, tiles:
     [{edition, sha256, tile}] by tile}.
7. **Memory.** Design's two implementations peaked at 2.6 GB and 1.7 GB. Free arrays as you go, or
   work in row bands; the halo is 2 rows for S and 12 for the tops' discs (S reaches 91.6 m
   over a cliff: ρ = 12).
8. **Design's values** (config/trees.json; the village computed two independent ways, numpy
   in int64 and exact fractions with scipy, identical bytes on all six chunks):

   | Tile | Trees | SHA-256 |
   |---|---|---|
   | 2623-1095 | 5'731 | `69fc652cd1cb957d0aa0583c370278ae572d56b93b792328e73339cc2eae24fa` |
   | 2623-1096 | 3'659 | `e4e0474920523973ffeb7b5805640df823ccd9a0f1dd4cc1d0c08951ee66846e` |
   | 2623-1097 | 1'278 | `2ebf5a8147d238b6cbac77bf23b2dce0b62bb9a2058cc1798610a66c7fe4e1f6` |
   | 2624-1095 | 10'031 | `89442014113296c26970640bc1ae09770a398c4b7e438fcd25e10c3ea7e2bc8e` |
   | 2624-1096 | 8'566 | `d42745218831146a076fc8e77067d897cf5e1fd83fade8b1f271c08f5d0d95b6` |
   | 2624-1097 | 5'147 | `765aac8e8f5b2bd365bc302f81510f9d483ec6af4ee16fafb171e761782a4271` |
   | all | 34'412 | 688'240 bytes |

   computed_for: inputs `1eb7b79e…` (the four lock entries), world `d2607d13…`. Design's
   runs took 33.5 s and 35.8 s.

## Scope — files you may touch

`pipeline/mattini/trees.py` (new) · `pipeline/tests/`: the pinned copies
(`test_trees_fixture.py`, `test_trees_rules.py`, `test_trees_expected.py`,
`test_trees_block.py`) and your own new `test_trees_*.py`. The pinned `config/trees.json`
copy is identical to the committed one. `pipeline/mattini/surfaces.py` only to expose a
reading helper, its behaviour and bytes unchanged. Read-only: everything else.

## Depends on

M3-06 (the same lane: `read_tlm`). Nothing in the other lanes: the tests use the fixture's
own lock; M3-03 (lane A) writes the lock's new entries, and its pinned
`test_expected_inputs_m3.py` checks `config/trees.json` against them at integration.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-07/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] With the real inputs in a scratch root in M3-03's layout (the six surface tiles, the
      terrain's six DTM tiles, the six building sheets, the TLM zip; provenance written by
      hand in M3-03's format until M3-03 lands), `build_trees` writes design's six chunks.
      Record the time and peak memory.
      - does NOT prove: that the trees stand where the owner sees trees (the owner's eyes;
        design's previews show a top on nearly every crown and a few false ones on vehicles).
- [ ] Mutations, each failing a named pinned test, recorded:
      - ties in column order;
      - a square margin;
      - dropped tops counted as neighbours;
      - no 2⁻¹³ m check;
      - the height / 4 cap left out;
      - OBJEKTART 16 masked.
      - does NOT prove: the game's reading (M3-11).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

- Changing the rule, design's values, the fixture or a pinned file.
- Pillow or any new dependency (lane C adds Pillow); unzipping the TLM file.
- Command-line or manifest wiring (M3-13).

## Findings (executor writes)

1. **The real village gives design's six chunks.** The inputs were fetched once into a
   scratch root in M3-03's layout: the six swissSURFACE3D tiles (SHA-256s equal to M3-03's
   pinned measurements) by curl, the six swissALTI3D tiles and the six building sheets by the
   existing `download terrain` and `download buildings`, the TLM zip of M3-06; the surface
   tiles' provenance.json by hand in M3-03's form (the terrain's keys, `editions` for
   `edition`, each tile's `edition`). The lock is the committed one's two entries plus
   M3-03's measured swisssurface3d and swisstlm3d entries, and the four together hash to
   `1eb7b79e450774e7aec8f15ebed4b8600c864de1f61d2813c49e967ad079164a`, config/trees.json's
   `inputs_sha256`. `build_trees` wrote all six chunks with design's SHA-256s (5'731, 3'659,
   1'278, 10'031, 8'566 and 5'147 trees: **34'412 trees, 688'240 bytes**), its own comparison
   with the config passing, then `built_trees_block` accepted them. **37.6 s end to end, peak
   1'291 MB resident** (design's two implementations: 2.6 GB and 1.7 GB; 33.5 s and 35.8 s);
   the 35'399 tops lose 27 above 40 m, 12 below 3 m and 952 on slopes of 60° or more, the
   numbers SPEC §8 gives, and 1'489 buildings, 2'625 TLM footprints and 224 land-cover
   polygons met the area. Where the time goes: the six tiles 3 s, the sheets 4 s, the TLM
   zip 17 s (9 s hashing, 8 s reading), the masks 2 s, the smoothing 5 s, the tops 2 s, the
   chunks 3 s. *does NOT prove:* that the trees stand where the owner sees trees (the owner's
   eyes), or a run on another machine.
2. **The six required mutations, each caught by a named pinned test** (applied to a copy of
   `trees.py`, run against the four pinned files; the module restored byte-identical):
   - ties in column order (`first = dj < 0 or (dj == 0 and di < 0)`):
     `test_trees_fixture.py::test_each_case_has_its_outcome[diagonal tie]` and `[diagonal tie, second]`,
     `test_the_chunks_are_the_fixture_s_bytes` (5 failures). Harm: of two equal crowns, or on a
     flat roof of canopy, the tree stands on the other pixel, up to a metre away;
   - a square margin (`if True` for the disc test): `test_each_case_has_its_outcome[beside the margin]`
     and the bytes (4 failures). Harm: trees near a wall's corner vanish that stand on the
     photo;
   - dropped tops counted as neighbours (d over all tops): `test_the_chunks_are_the_fixture_s_bytes`,
     `test_every_named_tree_is_in_its_chunk_at_its_index` (3 failures). Harm: crowns shrink
     beside a cliff top or a steep one that was dropped;
   - no 2⁻¹³ m check: `test_trees_rules.py::test_a_canopy_height_off_the_2_13_grid_is_refused`.
     Harm: a surface model with heights below 1024 m would give tops by an inexact rule with
     no error;
   - the height / 4 cap left out: `test_a_tree_alone_takes_a_quarter_of_its_height` and the
     bytes (4 failures). Harm: every short tree gets a crown up to 6 m wide;
   - OBJEKTART 16 masked: `test_each_case_has_its_outcome[over an underground building]`,
     `test_each_mask_input_decides_its_trees[underground building as a building]` (5
     failures). Harm: real trees above a cellar or a tunnel entrance are erased.
3. **Own mutations against my own tests** (17, the full `-k trees` run, first failure
   shown): the triangle's edge rows strict, its last column one short, degenerate triangles
   kept, the bounding-box test dropped, a kernel weight changed, the window not growing,
   the outer ring allowed, the slope limit 4, the radius clamp 7, the base height taken from
   the DTM pixel, the expected chunks not compared, the world checked after the lock, stale
   chunks kept, the tile by `round`, the tree its own nearest neighbour, nodata allowed:
   each a named test of `test_trees_fixture.py`, `test_trees_helpers.py` or
   `test_trees_checks.py`. One survived: the minimum smoothed height 2 m instead of 3 m
   (no fixture crown has S between 2 and 3 m); it is now killed by
   `test_a_single_pixel_needs_36_over_256_of_its_height_to_reach_3_m` (a one-pixel pole has S =
   36/256 of its height: 18 m and 21.25 m give no tree, 21.5 m and 40.0 m one, 40.125 m none).
   *does NOT prove:* the game's reading (M3-11).
4. **Decisions inside the brief's scope** (the first of each is the one taken):
   - `surfaces.py` is unchanged. `trees.py` imports `read_tlm` and, from the same lane's
     module, its private grid helpers (`_Frame`, `_polygon_spans`, `_paint`, `_row_pairs`,
     `_ceil_div`, `_floor_div`, `_snapped`): the TLM masks use the surfaces step's even-odd
     rule, not a copy of it. If M3-13 renames one, `trees.py` fails to import; the alternative
     (exposing public names in `surfaces.py`) would have touched a landed module.
   - The base height is the mean of the four float32 vertices `terrain.resample(dtm, box, 0.5,
     height_offset)` gives around the centre, in 64-bit, rounded once. The alternative (the
     mean of the exact DTM minus the offset, one rounding) is not what the real run needed:
     design's six hashes matched with this one.
   - The TLM is read with the area's box itself, not a grown one: only the pixels in the
     area are masked, and the margin B stops at the area's edge.
   - `build_tree_chunks` has exactly the pinned signature; the counts the step reports come
     from an internal `_rule` that returns them too.
   - All four provenance.json files are checked (in sorted dataset order) before any file is
     hashed or read; a lock that does not fit is refused naming the first dataset's lock
     command in sorted order; `check_trees_config` refuses an empty `expected_sha256`.
   - Building sheets are read one at a time, and a building whose raw bounding box is more
     than a millimetre outside the area is dropped at once (it can mask no pixel); the
     rule's own selection in `_triangles` is the exact one, on snapped coordinates.
   - The step's own lock-fit and provenance checks are in `trees.py`, as the brief says; none is
     imported from `terrain.py`, `buildings.py` or `download.py` (the names M3-01 keeps
     are: `area_tiles`, `area_sheets`, `PROVENANCE`, `terrain.resample`, `check_terrain_config`,
     `configured_area`, `world_refusal`, `check_computed_for`, `AREA_NAME`, `OWNER_AXES`,
     `buildings.read_sheet`).
5. **Seams for the orchestrator and wave 2.** `build_trees(world, datasets, lock,
   trees_config, terrain_config, raw_root, out_dir, *, progress=None)`: `datasets` must hold
   the four datasets (swisssurface3d with `editions`), which `load_datasets` refuses until M3-01
   and M3-03 have landed in full (my driver passed a dict). The tests of the step replace
   `mattini.trees.read_sheet` and `mattini.trees.read_tlm`: M3-13's CLI test can do the same.
   `built_trees_block` takes the lock as a dict or a path. A memory note: the 24 million
   pixels of the village are held as a 96 MB float32 model each for the surface and the
   terrain, one int64 canopy array and the padded S (195 MB each), and bands handle the
   per-pixel checks.
6. **Gates.** The pinned copies are byte-identical to `docs/briefs/pinning/M3-07/` (`cmp`);
   own tests: `test_trees_helpers.py` (71: the neighbours, triangles, margin, smoothing and tops
   against slow exact definitions, the one-pixel pole, the rule's refusals),
   `test_trees_checks.py` (105: the step on a synthetic world with real GeoTIFF tiles, the
   checks in order, a missing download per dataset, every lock and provenance refusal, the
   tile checks, the TLM zip's size, hash and stability, the comparison before writing, stale
   files, the built block); 237 trees tests with the pinned 66.
7. **The standard gate** (`tools/gate.sh > gate.log && git commit`, rule 3c) was green on the
   commit before the rebase (1665 pytest tests, GUT's 39 scripts) and again on the rebased head
   with lanes A (M3-03), B, C (M3-05), E, F and G landed: 1954 pytest tests, 41 GUT scripts.
   M3-03's changes to `download.py`, `lock.py` and `datasets.py` (rebased onto while this
   brief was in the gate) leave every name `trees.py` imports in place.
   *does NOT prove:* that it renders or looks right.
