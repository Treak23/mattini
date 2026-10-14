# Brief: M3-07 — The trees step: where the LiDAR shows a tree
Status: OPEN

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
2. **The API** (signatures in SPEC §8 *The trees*):
   - `TreesError`, `TREES_CONFIG_PATH`, `load_trees_config`, `check_trees_config`;
   - `build_tree_chunks(dsm, dtm, buildings, footprints, land_cover, world, area)`: the
     rule, pinned by the fixture;
   - `write_trees(out_dir, area, chunks, box, world_sha256, source, *, progress=None)`;
   - `build_trees(world, datasets, lock, trees_config, terrain_config, raw_root, out_dir, *,
     progress=None)`;
   - `built_trees_block(out_dir, trees_config, terrain_config, world, world_sha256,
     datasets, lock)`, where the lock is a dict or a path (M3-03's lock lands at the same
     time).
3. **The TLM features** reach `build_tree_chunks` as `{uuid, objektart, polygons}`
   (MultiPolygon coordinates as read, rings closed, points (E, N[, H])), so the rule does not
   depend on M3-06's record form. Read them with M3-06's `read_tlm` and adapt its records in
   `trees.py`. fiona is imported inside the reading function, never at module level (M3-01's
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
   the read, as M3-06 does); the DSM and DTM tiles with the terrain's tile checks.
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
