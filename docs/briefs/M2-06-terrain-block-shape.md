# Brief: M2-06 — The terrain block's shape, and three test gaps (M2-01's check)
Status: DONE (cefa1ac)

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

`manifest` refuses a terrain description whose box, rows or columns are not the ones the
world config's area and the terrain config's spacing give. Three gaps that M2-01's
independent check found are closed with tests:
- the lock comparison beyond the first tile;
- the expected value chosen by the configured spacing;
- a refused build that leaves a good terrain on disk untouched.

Today a description with its box shifted 1 km, or with its rows and columns swapped, passes
every check (measured by M2-01's checker). The game would then place the village 1 km off,
or refuse it, and the manifest would never have said so.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §8, *The terrain grid*.
3. `docs/briefs/M2-01-terrain-residue-pipeline.md`, its Findings (item 9 in particular).
4. `pipeline/mattini/terrain.py` (`built_terrain_block`, `check_terrain_config`),
   `pipeline/mattini/manifest.py`, `pipeline/tests/test_terrain_manifest_source.py`,
   `pipeline/tests/test_terrain_build_tiles.py`.

## Decisions already made

- **The shape (the checker's P2):**
  - `built_terrain_block` requires `lv95_box` to equal the world config's box for the
    area, as floats;
  - it requires `columns` = (e_max − e_min) / s + 1 and `rows` = (n_max − n_min) / s + 1
    for the configured spacing s.

  Each refusal names the field, both values and `python -m mattini terrain`. The world
  config it compares with is the one the manifest is written from (the function takes
  the parsed world, or the manifest passes its box in: the builder's choice, recorded in
  Findings).
- **Test gaps (the checker's P3s):**
  - (a) A test whose area has at least two tiles changes the lock's SHA-256 of a tile other
    than the first, and `manifest` refuses (mutation: compare only the first tile, and see
    it fail).
  - (b) A config holding all three expected values, set to 2 m, builds and passes
    `manifest`; the same config with the 2 m value exchanged for the 0.5 m value is
    refused (mutation: take the first value, and see it fail).
  - (c) A good terrain in place, then a build refused by its expected value: the good
    files are byte for byte unchanged (mutation: write, then compare, then delete on a
    mismatch, and see it fail).
- **Wording:** `test_repo_tracked.py`'s does-NOT-prove line says what it means (M2-01's
  checker: "is missed" should read "is caught"), and its positive control asserts all four
  Terrain3D binaries.

## Scope: files you may touch

`pipeline/mattini/terrain.py` · `pipeline/mattini/manifest.py` (only to pass the world
config's box, if that is the choice) · `pipeline/tests/`.

## Depends on

M2-04 (it changes `manifest.py`; this brief comes after it, beside M2-05, with which it
shares no file).

## Done when (gates)

- [x] The shape check refuses a box shifted by 1 km and rows and columns swapped (tests on
      the first fixture), and the three mutations above each fail a named test (Findings:
      both runs of each).
      (Findings 3: before the fix the shifted box and the swap were accepted, `DID NOT
      RAISE`; Findings 5: runs A, B1, B2, C and C2, against 662 passed unmutated.)
      - does NOT prove: anything about the buildings' block (M2-04 has its own checks).
- [x] The real village at 0.5 m still builds and passes `manifest`, and its terrain block
      and `village.json` are byte for byte M1-03's (`ea6e6c90…`; Findings).
      (Findings 4: `village.f32` `b6334c1f…`, `village.json` `ea6e6c90…`, exit 0 twice.)
      - does NOT prove: that it renders.
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      (Findings 2: `cefa1ac`, chained on exit 0.)
      - does NOT prove: that the game places the terrain right (M2-02's two fixtures do).

## Forbidden

A change to the rule, to any fixture's bytes or to the expected values.

## Findings (executor writes)

Executor agent of the one M2 session, 2026-09-25, in its own worktree and branch (the
owner's run mode; nothing synced or pushed). The worktree started at `63816ac` (main);
`git merge --ff-only 18c369e` fast-forwarded it to the brief's commit. Code commit
`cefa1ac` on top of `18c369e`.

1. **Pinned copies:** none. `docs/briefs/pinning/` holds no `M2-06/` folder at `18c369e`,
   so the copy step had nothing to copy and there is no live copy to `cmp`. Every test
   below is the executor's own.
2. **Standard gate** (`tools/gate.sh > gate-M2-06.log 2>&1 && git commit`), exit 0 for
   `cefa1ac`: `uv lock --check`, pytest **662 passed**, 4 deselected (the network tests),
   79 warnings (rasterio's `PendingDeprecationWarning`, as before); ruff check and format;
   `manifest`; Godot 4.6.3 import and parse check; GUT 16 scripts, 76 tests, 1726 asserts,
   `---- All tests passed! ----`; gdlint; gdformat. The base `18c369e` measured 623 passed
   in this worktree before any change: 39 tests are new (27 + 6 + 5 + 1, item 6).
3. **The shape check** (`terrain._check_shape`, called by `built_terrain_block` right
   after the spacing check). Before the fix, on the base code, the new
   `test_terrain_block_shape.py` failed 18 of its tests: the checker's two cases were
   accepted, `Failed: DID NOT RAISE TerrainError` for the box shifted 1 km east, west,
   north and south (first fixture) and for rows and columns swapped (both fixtures); a
   count one off was refused only by the size check, which names no field. After it, all
   27 pass. The refusals, as the real village gives them (item 4):
   `lv95_box is {'e_max': 2626000.0, 'e_min': 2624000.0, 'n_max': 1098000.0, 'n_min':
   1095000.0}, the world config's area 'village' is {'e_max': 2625000.0, 'e_min':
   2623000.0, 'n_max': 1098000.0, 'n_min': 1095000.0}; `python -m mattini terrain`
   rebuilds the terrain` and `columns is 6001, the world config's area 'village' at 0.5 m
   needs 4001; …`. The builder's choice the brief left open: **the function takes the
   parsed world**, which it already did: `build_manifest` parses `world` from the very
   bytes whose SHA-256 it writes as `world_sha256` and passes both to
   `built_terrain_block`. So `manifest.py` is unchanged.
4. **Real run**, the six 2024 tiles in the scratch download, outputs in a scratch folder,
   nothing committed: `python -m mattini terrain --raw <scratch>/raw --out <scratch>/m206`
   exit 0 in 7.7 s, printing `the heights have the SHA-256 config/terrain.json expects,
   b6334c1f…`. `village.f32`
   `b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a`, 96'040'004 bytes,
   4001 × 6001; `village.json`
   `ea6e6c907e060f6813da1432bba490ef7719082643c025233967831e05f99c34`, M1-03's. The
   manifest `c7580568…` carries `village.json` as its `terrain` block (compared as parsed
   JSON: equal); without the line `  "buildings": null,` that M2-04 added, it hashes to
   `0e4572fb…`, M1-03's manifest. `python -m mattini manifest --out <scratch>/m206` run
   again: exit 0, the same bytes. With the real description edited in a scratch copy
   (heights file hard-linked), the box shifted 1 km east and rows and columns swapped are
   both refused (item 3's messages), and no `manifest.json` is written.
5. **Mutation proofs.** Each mutation is a saved diff (`m206-<run>.diff` in the scratch
   folder), applied to the worktree while the real code sat in the index, run through the
   full gate (`gate-M2-06-<run>.log`; each stopped at pytest, exit 1), then undone with
   `git apply -R`; `git diff` empty and `git status` showing only the staged work after
   each. Unmutated: 662 passed.

   | Run | Mutation | What failed | Owner-visible harm |
   |---|---|---|---|
   | A | (a) the lock comparison reaches the first tile only (`built_tiles[:1]`) | `test_every_tile_s_lock_sha256_is_compared[2623-1096]`, `[2624-1095]`, `[2624-1096]`: `DID NOT RAISE`; `[2623-1095]`, the first, passes; 659 passed | a republished tile other than the first adopted in the lock with the old terrain kept: two machines, one commit, two villages |
   | B1 | (b) `terrain` takes the first expected value | `test_a_config_holding_all_three_values_builds_and_passes_manifest[1.0]` and `[2.0]` (`the heights built here have SHA-256 04f17ba0…` / `42756c1c…`, `config/terrain.json expects c3bbb0f0…`, the 0.5 m value); `test_terrain_refuses_the_2_m_value_exchanged_for_the_0_5_m_value` (`DID NOT RAISE`) | the owner's switch to 1 or 2 m refused although the heights are design's; with the values misplaced, heights design never computed are written |
   | B2 | (b) `manifest` takes the first expected value | `…builds_and_passes_manifest[1.0]` and `[2.0]` (`village.f32 has SHA-256 04f17ba0…` / `42756c1c…`, refused); `test_manifest_refuses_the_2_m_value_exchanged_for_the_0_5_m_value` (`DID NOT RAISE`) | the same one step later: a correct terrain kept out of the game, or a wrong one shipped |
   | C | (c) write, then compare, then delete the two files on a mismatch | mine, `test_a_refused_build_leaves_the_good_terrain_byte_for_byte` (`assert {} == {'village.f32': …, 'village.json': …}`); also `test_heights_other_than_the_expected_ones_are_refused_before_anything_is_written` and `test_terrain_refuses_the_2_m_value_exchanged…` (`assert not out.exists()`: the folder the write made stays) | `terrain` refusing the owner's changed inputs deletes the working terrain; the game then has none |
   | C2 | C, and the folders the write made removed too, so nothing looks written | only `test_a_refused_build_leaves_the_good_terrain_byte_for_byte`; 661 passed | the same harm, invisible to every earlier test |
   | S1 | the box not compared | 12: the four `test_a_box_shifted_by_a_kilometre_is_refused[…]`, the seven `test_a_box_that_is_not_exactly_the_world_s_is_refused[…]`, `test_a_box_that_is_not_an_object_is_refused`, all `DID NOT RAISE` | the village placed 1 km off in the game, the manifest silent (the checker's P2) |
   | S2 | rows and columns not compared (the type check kept) | 7: `test_rows_and_columns_swapped_are_refused[fixture]`, `[fixture_nw]` and `test_an_area_that_is_not_whole_cells_is_named` (`DID NOT RAISE`); the four `test_each_count_is_checked_on_its_own[…]` (refused by the size check, which names no field) | a grid read with its axes swapped: the game refuses the village, or reads it transposed (the checker's P2) |
   | S3 | the counts at 0.5 m whatever the spacing | 33, among them `test_both_fixtures_have_the_shape_their_world_and_spacing_give[fixture_nw]` (`columns is 13, the world config's area 'fixture_nw' at 2 m needs 49`) and every 1 m and 2 m build that goes on to `manifest` | the owner's switch to 1 or 2 m refused by `manifest` |
   | T | the tracked-files scan misses one Terrain3D library (the Windows debug `.dll` excluded) | `test_the_scan_reaches_the_files_m1_s_list_missed`: `AssertionError: libterrain.windows.debug.x86_64.dll` | a Terrain3D library dropped from git passes the gate; the owner's clone has no terrain on that platform. The old `len(binaries) >= 2` passes with the three left (read from the code, not run) |

6. **Choices inside the brief's scope** (reversible):
   - *"As floats":* each of the box's values must be a Python `float` equal to the
     world's, and the key set exactly `e_max`, `e_min`, `n_max`, `n_min`, so a box written
     `2601015` (a whole number) is refused; the terrain step always writes floats. The
     alternative is to compare the values only, which accepts `2601015`.
   - *Order in `built_terrain_block`:* keys, area, file, format, world, spacing, then the
     area's presence in the world config (moved up from after the heights' SHA-256), the
     box, `columns`, `rows`, then the source and the rest as before. The old separate
     check "rows and columns must be positive whole numbers" is folded into the counts'
     (an `int` equal to the formula, which is at least 2 when whole, since the world config
     refuses an empty box). A count that cannot be whole, for a world whose area is not a
     whole number of cells, says so: `columns is 13, the world config's area 'fixture_nw'
     at 2 m needs 13.5, and the area is not a whole number of 2 m cells`
     (`test_an_area_that_is_not_whole_cells_is_named`: a world copy, with the block's box
     and `world_sha256` made to match it).
   - *(b)'s values:* the 0.5 m and 2 m values are design's (`c3bbb0f0…`, `42756c1c…`,
     `test_terrain_build_tiles.py`). Design computed no 1 m value for the four-tile world,
     so the test computes it with `window_mean.py` (the independent reference M2-01 uses):
     `04f17ba0c9e18cbfc381f025ef4f3b91afb17192c49ab094690334dc2ab1cdaf`, **not design
     data**. The same fixture checks that `window_mean.py` gives design's two values from
     the same mosaic, and the pipeline's own 1 m build gives `04f17ba0…` too (the passing
     `[1.0]` case). "Exchanged" is read as the two values swapped, all three present, in
     the order `"0.5"`, `"1"`, `"2"`, so at 2 m the first value is the 0.5 m one. The
     positive case runs at all three spacings, so a step taking the last value is caught
     at 0.5 m as well.
   - *(a):* all four tiles in turn, the first included; the terrain is built once per
     module and copied per test.
   - *(c):* the refused build's heights differ from the good ones (the tile rewritten
     0.25 m higher, provenance and lock made to vouch for it), so a step that left its new
     files would fail the test as well as one that deleted them (C, C2).
   - *test_repo_tracked.py:* "is missed" now reads "is caught"; the positive control names
     each of the four libraries (`TERRAIN3D_BINARIES`) and asserts each is scanned, so a
     fifth library added later does not fail it.
   - New files: `test_terrain_block_shape.py` (27 tests), `test_terrain_expected_spacing.py`
     (6). Added: 5 tests to `test_terrain_manifest_source.py` (the four tiles and their
     positive control), 1 to `test_terrain_build.py`.
7. **Out-of-scope touches:** none. The code change is in `pipeline/mattini/terrain.py`, the
   tests in `pipeline/tests/`; `manifest.py` untouched.
8. **Surprises.**
   - The checker's (c) said a write-then-delete step passed the tests. Measured: the
     pinned `test_a_wrong_expected_value_is_refused_before_anything_is_written` checks the
     two files only and passes under C; two other tests already failed under C, because
     they assert the output folder does not exist. A tidier mutation (C2) that removes the
     folders too passed every test until this brief's.
   - Under B1 the manifest's test passes and under B2 the terrain's does: each selection
     is guarded by its own test.
9. **Follow-up candidates** (not built; no design authority):
   - `manifest.py`'s module docstring lists the terrain refusals without the shape ("no
     longer matches the world config" covers it only loosely); the brief allowed
     `manifest.py` only to pass the box, so it is unchanged.
   - Whether the game's `TerrainGrid` refuses a shifted box or swapped counts in a
     manifest that did not come from `manifest` (a hand-edited one) is M2-02's side,
     unmeasured here.
