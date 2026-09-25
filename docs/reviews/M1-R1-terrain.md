# Review M1 R1 — lens `terrain` (Tier 1)

- **Lens:** `terrain`: `config/world.json`, `config/terrain.json`, the shared terrain
  fixture and vectors, the pipeline's grid and resampling (`pipeline/mattini/terrain.py`),
  the tile lock, provenance and goldens (Hard Rule 5), the origin census (Hard Rule 4), the
  manifest's `terrain` block, `WorldConfig`, and `TerrainGrid`/`TerrainLoader` placement in
  the game. Seams: M1-01↔M1-03, M1-03↔M1-04, M1-02↔M1-04.
- **Range:** `git diff e83a36a..6fb378d -- . ':!game/addons' ':!pipeline/uv.lock'`, plus
  `config/world.json`, `config/terrain.json`, `tests/shared/terrain_fixture/`,
  `tests/shared/terrain_vectors.json` and `tests/shared/world_vectors.json` as they stand.
- **Head reviewed:** `6fb378d`. `main` was at `7869537` when this was written; the only
  change since `6fb378d` is `docs/ROADMAP.md`.
- **Date:** 2026-09-25.
- **How:** everything ran in a separate worktree at `6fb378d` in the session's scratch
  directory, with Godot's `user://` in a scratch folder (`XDG_DATA_HOME`). One build at a
  time. Each mutation was saved as a diff, run through the full `tools/gate.sh`, then undone
  with `git apply -R` (the untracking run with `git reset`); `git status` was empty after
  each. Where a finding needed the real village, the six real tiles were downloaded with
  `python -m mattini download terrain` into the scratch folder (never committed), and the
  terrain was built with `python -m mattini terrain --out <scratch>`, never into the
  worktree's `game/assets/generated/`. The game side was measured with a probe script (not
  committed) that loads a manifest through `WorldConfig`, `TerrainGrid` and
  `TerrainLoader` and reads heights back from Terrain3D. Scratch tests were written in the
  worktree, run, and deleted. No permission prompt came up.
- **Baseline** in that worktree: `tools/gate.sh` exit 0 in 48 s; pytest 367 passed,
  3 deselected; GUT 15 scripts, 69 tests, 1641 asserts, all passed; 65 `ERROR` lines, each
  excepted by the allowlist.

**Result:** no P0, no P1. Five P2s and five P3s (two of the P3s are the known items the
board asked me to grade).

What is right, measured: the real village comes out bit for bit as designed
(`b6334c1f…`), and the game puts every one of its heights on the right spot, at 0.5 m and
also at 1 m and 2 m.

What is weak is what the gate can see. Its test data is smaller and tidier than the
village:
- the pipeline's build tests use one whole tile;
- the game's tests use one tiny grid, at one spacing, in one row of Terrain3D regions, on
  the positive side of the origin;
- the one check made against the real village (its SHA-256) lives only in the SPEC and the
  briefs.

So a mistake that swaps the village's tiles, or moves it 2 km north in the game, passes the
whole gate. Besides that:
- `manifest` does not notice a terrain built from tiles the lock no longer pins;
- a date or host name can reach the manifest through the terrain block;
- the origin census misses three more spellings;
- the download serves the village by name while the terrain step builds whatever area its
  config names.

## Findings

### M1-R1-T-01 · P2 · No gate test builds the terrain from more than one tile, and nothing compares a finished village with its designed SHA-256

- **Where:** `pipeline/mattini/terrain.py:485-487` (`_place_tile` puts each tile's pixels
  into the mosaic). The build tests: `pipeline/tests/test_terrain_build.py:51-105` and
  `pipeline/tests/test_terrain_refusals.py:70-104` both build a world whose area is one
  whole tile. The fixture tests (`test_terrain_fixture.py`) feed `source.f32` straight into
  `resample`, so tile reading and mosaic assembly are not part of the fixture. The village's
  SHA-256 appears only in `docs/SPEC.md:203` and the briefs (`git grep b6334c1f`).
- **Claim:** where each tile lands in the mosaic is checked by no gate test. With one whole
  tile, every placement formula gives row 0, column 0, so a wrong formula looks right. After
  the fact, nothing compares a built `village.f32` with `b6334c1f…`: not `terrain`, not
  `manifest`, not the game, not `tools/export.sh`, not `docs/RELEASE.md`. M1-03's brief
  says "the owner's first run is the check: the SHA-256 in this brief"
  (`docs/briefs/M1-03-village-terrain.md:100`). Nothing carries that check out, and the
  owner is not expected to compare hashes by hand (lesson 2).
- **Proof:** mutation A: the tile rows are counted from the south instead of the north
  (`r0 = round((north - i1 * SOURCE_M - n_min) / SOURCE_M)`). `tools/gate.sh` exit 0
  (pytest 367 passed, GUT 69/69). With the real tiles, the mutated `terrain` exits 0 and
  writes `village.f32` `ba2140ea…` instead of `b6334c1f…`; `manifest` accepts it (exit 0).
  The seven check points of brief M1-03:

  | Point | Designed | Mutation A | Off by |
  |---|---|---|---|
  | Bahnhofplatz 1 (tile 2623-1096) | 1605.64 | 1605.64 | 0 |
  | tile 2623-1095, flat | 1625.82 | 2306.38 | +680.55 m |
  | tile 2623-1096, flat | 1632.94 | 1632.94 | 0 |
  | tile 2623-1097, slope | 2244.99 | 1645.60 | −599.38 m |
  | tile 2624-1095, slope | 2015.10 | 1584.23 | −430.87 m |
  | tile 2624-1096, flat | 1646.33 | 1646.33 | 0 |
  | tile 2624-1097, flat | 1593.66 | 1882.71 | +289.05 m |

- **Harm:** the village with its northern and southern kilometres swapped. It builds, the
  manifest accepts it, the game loads it and an export ships it, all without a word, while
  the gate is green. That is the harm of Hard Rules 4 and 5. Two more places are just as
  blind: the arithmetic that cuts a tile at the area's edge (the village's box follows tile
  edges, so it cuts none today), and the first run on the owner's Windows PC.
- **Fix:** design's call.
  - A build test from at least two tile rows and two tile columns, with an area that cuts
    the outer tiles, pinned to exact bytes.
  - On the real-data side, something that compares a finished `village.f32` with the
    SPEC's value and says so. For example, `terrain` could print whether it matches, or a
    release checklist line could ask for it.
- **Does NOT prove:** that the code is wrong today (it is right: the unmutated build gives
  `b6334c1f…`); that the owner's PC computes different bytes (not measured); that the
  cut-tile arithmetic is wrong (checked by reading only).

### M1-R1-T-02 · P2 · The game's terrain placement is tested only on a grid that sits where the village does not

- **Where:** `game/scripts/terrain/terrain_loader.gd:32-33` (region size), `:51-56` (first
  region, corner, offset) and `:69` (the import). Every game test that builds a terrain
  loads the fixture (`game/tests/test_terrain_loader.gd:34-41`,
  `test_main_scene*.gd`). The fixture's grid is described in
  `tests/shared/terrain_vectors.json`: 0.5 m, `x_min` 1015, `z_min` 10.5, regions (0,0) and
  (1,0).
- **Claim:** the fixture sits east and south of its origin, at 0.5 m, in one row of regions
  that starts at region (0,0). The village is different on every one of those points: it
  starts at z = −2000, spans three rows of regions from (0,−2) to (1,0), and the owner was
  told 1 m or 2 m is "a config change and a pipeline re-run, no code change" (SPEC §7).
  Any mistake that happens to vanish when the first region is (0,0) and the spacing is
  0.5 m passes the gate: confusing metres with vertices, rounding negative numbers towards
  zero, or a region size written for 0.5 m only. This is lesson 34: the test data cannot
  tell the right code from its likeliest wrong twins.
- **Proof:** three mutations, each through the full `tools/gate.sh`, then the real village
  loaded with the probe (8 points: Kirchplatz 1 and the seven check points; 2000 random
  vertices):

  | Run | Mutation | Gate | Real village in Terrain3D |
  |---|---|---|---|
  | L | the import position given in vertices (`corner / s`) | exit 0 | regions (0,−4)…(1,−2): the village 2048 m north. 6 of 8 points have no ground, the other two are wrong (1637.96 for 2244.99; 1915.45 for 1593.66); 1399 of 2000 vertices missing, worst error 876 m |
  | L2 | the first region rounded towards zero (`int` for `floori`) | exit 0 | regions (0,−1)…(1,0): the northern 976 m missing, no error printed; 2 of 8 points and 618 of 2000 vertices without ground |
  | L3 | the region size fixed at 2048 vertices | exit 0 | 0.5 m village exact; the village built at 2 m lands on regions (0,−1)…(1,1): Bahnhofplatz without ground, 1390 of 2000 vertices missing, worst error 867 m |

  Unmutated, the same probe finds the village exact at every spacing (see "Checked and
  clean" 3).
- **Harm:** a later change to the loader (M5 scales the area up) moves or cuts the village
  while the gate stays green, and so does the owner's switch to 1 m or 2 m, which the SPEC
  promises needs no code change. The owner sees a village 2 km off or missing a kilometre,
  with no error on screen.
- **Fix:** design's call. One option: a second shared fixture (or a variant of the first)
  placed north-west of its origin, crossing a row of regions, at 1 m or 2 m, with its
  expected heights computed by design, read back by the loader tests.
- **Does NOT prove:** that the loader is wrong today (it is right at 0.5, 1 and 2 m); that
  it renders or looks right (no GPU).

### M1-R1-T-03 · P2 · A day- or machine-dependent field can enter the manifest through the terrain block's `source` (M0 C-01's class, one layer out)

- **Where:** `pipeline/mattini/terrain.py:276-283` builds `source` inside `build_terrain`.
  The goldens: `pipeline/tests/test_golden_outputs.py:154-161` pins the manifest with
  `terrain` null. `test_terrain_fixture.py:58-71` pins `fixture.json`, but it hands
  design's own `source` to `write_terrain`, so `build_terrain`'s `source` never meets a
  golden. `test_terrain_build.py:141-147` checks only `attribution` and `tiles` inside
  `source`. `test_terrain_refusals.py:214-219` compares two builds made in the same second.
  `manifest` checks the block's top-level keys only (`terrain.py:313`).
- **Claim:** the goldens M1-01 added for M0 C-01 (lesson 33) cover the manifest without a
  terrain and `provenance.json`. They do not cover the terrain block as the real command
  writes it, so a field that changes by day or by machine can reach the manifest that way.
- **Proof:**
  - Mutation D2 added `"built_by": platform.node()` and
    `"built_on": datetime.now(tz=UTC).date().isoformat()` to `source`. `tools/gate.sh`
    exit 0 (pytest 367 passed, GUT 69/69).
  - The real `terrain` then wrote a manifest holding `"built_by": "vm"` and
    `"built_on": "2026-09-25"`. Its SHA-256 was `538dcf6a…` instead of `0e4572fb…`
    (M1-03's value, which the unmutated build reproduces), and the game loads it.
  - Mutation D (the same with `date.today()`): pytest also passed all 367, and the gate
    failed only at `ruff check`, on rule DTZ011. That rule asks for a time zone; it is not
    a determinism check, and the time-zone-aware spelling in D2 passes it.
- **Harm:** tomorrow's rebuild, or the owner's PC, writes different manifest bytes for the
  same inputs while the gate is green (Hard Rule 5). M2 adds more blocks to the manifest
  ("the datasets used … and the chunk lists", SPEC §8) and may follow this pattern.
- **Fix:** pin `build_terrain`'s own output for a fixed synthetic input to exact bytes (the
  same test T-01 asks for can do it), and have `manifest` require exact key sets for
  `source` and for each of its `tiles`. Unambiguous, but it touches pinned M1-03 files, so
  it is design's to place.
- **Does NOT prove:** that any such field exists today (none does).

### M1-R1-T-04 · P2 · `manifest` accepts a terrain whose tiles the lock no longer pins, and keeps its old attribution

- **Where:** `pipeline/mattini/manifest.py:41-46` and `pipeline/mattini/terrain.py:319-336`
  (`built_terrain_block` checks the world SHA-256, the spacing, the edition, the resolution
  and the heights file; it never reads the lock, and it compares neither the attribution
  nor the collection with `config/datasets.json`).
- **Claim:** SPEC §5 says a republished tile is "a deliberate change like a new edition".
  A new edition makes `manifest` refuse the old terrain, naming `terrain`. A new lock
  entry does not. The class is "inputs of a built terrain that `manifest` does not
  re-check", and it has four members:
  - the lock's tile checksums;
  - the datasets config's `attribution`;
  - its `collection`;
  - the pipeline's own code (nothing records which version of the resampling rule built
    the file).
- **Proof:** two scratch tests (one whole synthetic tile, the real `build_terrain` and
  `write_manifest`), both failing on `6fb378d`:
  - After a build, the tile is rewritten 0.25 m higher, and provenance and lock are pinned
    to it (what `lock terrain` then `download terrain` do), with no `terrain` run. Result:
    `Failed: DID NOT RAISE TerrainError`. `manifest` accepted a terrain built from tile
    `9432d9f9…` while the lock pins `cb07afcd…`.
  - After a build, `config/datasets.json`'s attribution is changed to new wording. The
    manifest still carries `'© swisstopo'`, which is what the game's credits show.
- **Harm:** swisstopo republishes a village tile; the owner adopts it on purpose and
  downloads it, but forgets `terrain`. Their game, `manifest`, the gate and an export all
  keep the old terrain without a word, while a fresh clone builds the new one: two
  machines, one commit, two villages (Hard Rule 5). A changed attribution wording reaches
  the credits only after a rebuild nobody is told to run (Hard Rule 3, a soft rule).
- **Fix:** design's call. `manifest` could compare the block's `source` with the lock and
  with `config/datasets.json`, naming `terrain`.
- **Does NOT prove:** a real republish (simulated with synthetic tiles); a changed
  collection or changed code (named only, not run).

### M1-R1-T-05 · P2 · The origin census still misses three spellings, including the likeliest one for a kilometre grid

- **Where:** `pipeline/tests/test_origin_census.py:23-31` (`SPELLINGS`; the kilometre pair
  is line 30, `2623.{0,12}1096`).
- **Claim:** the census now reads every committable file (M0 C-02 fixed). Three spellings
  still get through:
  - the two kilometre numbers on two lines;
  - the two kilometre numbers in north-then-east order;
  - e-notation with trailing zeros in the digits before the `e` (such as `2.6230e6`).
- **Proof:** mutation C added all three, then ran the full `tools/gate.sh`. It exited 0,
  with `test_origin_census.py` passing all 25 of its tests. The three additions:
  - `const ORIGIN_TILE_E_KM := 2623` and `const ORIGIN_TILE_N_KM := 1096` on two lines in
    `terrain_loader.gd`;
  - `ORIGIN_TILE_KM = (1096, 2623)` in `terrain.py`;
  - `ORIGIN_E = 2.6230e6` and `ORIGIN_N = 1.0960e6` in `terrain.py`.

  Control: `ORIGIN_E = 2.623e6` alone is still caught
  (`["pipeline/mattini/terrain.py: '2.623e6'"]`).
- **Harm:** a second origin, written as two constants in the chunk-grid code M2 or M5 is
  likely to add, drifts away from `config/world.json` unnoticed (Hard Rule 4).
- **Fix:** add the three spellings: the pair on nearby lines, the pair reversed, and a
  mantissa with trailing zeros. How far apart the pair may be before it stops counting is
  design's call, since a wide search gives false alarms. A census proves text only
  (lesson 5).
- **Does NOT prove:** that no other spelling gets through, or anything about an origin
  computed from other numbers.

### M1-R1-T-06 · P3 · The download and the lock serve the village by name; the terrain step builds the area its config names, and its refusal points at a command that cannot help

- **Where:** `pipeline/mattini/download.py:62-67` (`world.area("village")`) and
  `pipeline/mattini/lock.py:37-43`. `pipeline/mattini/terrain.py:219-222`, `:242-245` and
  `:409` (the area comes from `config/terrain.json`; a provenance for other tiles is refused,
  naming `download terrain`).
- **Claim:** which area the pipeline serves has two homes: code for the download and the
  lock, config for the terrain step. When they differ, `terrain` says "`python -m mattini
  download terrain` downloads what it asks for", but that command fetches the village
  again.
- **Proof:** scratch test with the fake swisstopo server:
  - a world with a second area, `valley`, one tile east of the village, and
    `config/terrain.json` naming `valley`;
  - run twice: `download terrain`, then `terrain`;
  - both refusals are identical:
    `it lists the tiles ['2623-1095', …, '2624-1097'], the area needs ['2625-1096']`;
  - the lock also holds only the six village tiles.
- **Harm:** none today, since there is one area. When M5 points the terrain at a larger area,
  the owner follows the message and loops.
- **Fix:** design's call. The download and lock could take the area from
  `config/terrain.json`, or the terrain step could refuse any area but the one the
  download serves, saying why.
- **Does NOT prove:** anything about M5's actual design.

### M1-R1-T-07 · P3 · The shared terrain fixture, and Terrain3D's binaries, can leave git with the gate green (lesson 37 again)

- **Where:** `pipeline/tests/test_repo_tracked.py:16-33`. `DEPENDED_ON` is a list of the
  files that must be tracked; it names none of the seven files under
  `tests/shared/terrain_fixture/`, and none of the four binaries under
  `game/addons/terrain_3d/bin/`.
- **Claim:** the "tracked files" test is scoped by an inclusion list, the pattern lesson 37
  warns about. M1 added files the repository depends on that the list does not name.
- **Proof:** `git rm --cached -r tests/shared/terrain_fixture game/addons/terrain_3d/bin`
  (11 files untracked, still on disk), then `tools/gate.sh`: exit 0, pytest 367 passed,
  GUT 69/69. Undone with `git reset`.
- **Harm:** a commit that drops them passes the gate. The owner's next clone has no
  fixture, so its gate fails with missing-file errors, and has no Terrain3D, so the game
  has no terrain. The failure is visible, but it lands on the owner, not on the commit
  that caused it.
- **Fix:** scope by exclusion (every file under `config/`, `tests/shared/`, `tools/`, the
  vendored addons…) or compare against the index. The binaries are the `game` lens's
  subject (vendoring); they are named here because they are the same class.
- **Does NOT prove:** that a fresh clone was made (the harm follows from what git stores).

### M1-R1-T-08 · P3 · "Rounded once" holds only while the height offset subtracts exactly; the rules test's "exact" reference rounds twice as well

- **Where:** `pipeline/mattini/terrain.py:162` subtracts the offset in 64-bit, then rounds
  to 32-bit. `pipeline/tests/test_terrain_rules.py:47` does `float(...)` then
  `np.float32(...)`, although its docstring (`:23`) says "one rounding at the end".
  `docs/SPEC.md:201` says "every correct implementation gives the same bits".
- **Claim:** with the offsets used today (0.0 in `config/world.json`, 1000.0 in the
  fixture, −12.25 in the tests) the subtraction is exact, so there is one rounding and the
  claim holds. With an offset that has many binary fraction digits there are two roundings,
  and a correct implementation that rounds once can differ by one 32-bit step.
- **Proof:** a mosaic of 1600.0 with offset 2⁻¹⁴ + 2⁻⁴⁵ (0.00006103515627842171 m).
  `resample` and the test's reference both give 1600.0; the value rounded once from the
  exact result is 1599.9998779296875.
- **Harm:** 0.12 mm, and only with an offset nobody would choose (a non-zero offset is a
  design change anyway, SPEC §6). The test's docstring claims a single rounding that its
  code does not do (Hard Rule 2, clarity only).
- **Fix:** reword, or compute the reference with a single rounding and add one such offset
  case. Design's call.
- **Does NOT prove:** any effect on the village (offset 0.0: exact).

### M1-R1-T-09 · P3 (known, graded) · M1-04 Findings 5 runs e and j: the pinned rotated-world test accepts any refusal

- **Where:** `game/tests/test_terrain_grid.gd:163-168` (pinned);
  `game/scripts/terrain/terrain_grid.gd:125` (the axes check).
- **Grade and why:** re-run at `6fb378d` with the axes check disabled: the gate exits 1,
  and the only failing test is the builder's own `test_a_rotated_world_is_refused_for_its_axes`
  (GUT 68 of 69 passed). The pinned test passes, as the Findings say. It is P3, not higher,
  for two reasons:
  - no rotated terrain can be drawn either way: the pipeline refuses a rotated world before
    it writes anything (`terrain.py:215-218`, tested with its message);
  - in the game, the columns-and-rows check refuses every rotation of a grid with at least
    2 × 2 vertices. For the four turns about the vertical axis, one of the two fitted
    counts comes out negative. For the rest, one axis maps to height, which gives a count
    of 1. This is reasoned from `terrain_grid.gd:177-186` and `world_config.gd`, not run.

  What remains is a pinned test whose name promises the axes check but proves any refusal.
  The builder's tests that do see it (runs e and j) are not pinned and may change with a
  later brief.
- **Does NOT prove:** the rotations other than the one the tests use, in the game (reasoned).

### M1-R1-T-10 · P3 (known, graded) · M1-03 Findings 7: the stray-tile test fails the folder-reading mutation only through the stray tile's unknown id

- **Where:** `pipeline/tests/test_terrain_build.py:157-163`.
- **Grade and why:** P3. The mutation the brief names (the tile list read from the folder)
  is caught twice: by this test's `KeyError`, and by the builder's missing-tile test. A
  folder reader that skipped unknown ids would pass this test, but every file it read is
  still hashed and compared with provenance and the lock (`terrain.py:254-266`). So its
  worst effect would be a refusal, not a wrong terrain. Reasoned from the code, not run.
- **Does NOT prove:** the behaviour of that variant (not built).

## Checked and clean

1. **The real village, reproduced here.**
   - `download terrain`: six tiles in 12.6 s. Its `provenance.json` is `28523b17…`, the
     same bytes as M1-01's run.
   - `terrain`: 6.2 s. `village.f32` is `b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a`,
     96'040'004 bytes, the SPEC's value. The manifest is `0e4572fb…`, M1-03's.
   - That makes three runs in three sessions giving the same bytes: design's, M1-03's
     builder's, and this one.
   - The seven check points equal design's values exactly.
2. **Rows, columns and orientation agree on both sides.**
   - The pipeline's row 0 is `n_max` and its column 0 is `e_min` (`terrain.py:3-4`,
     `resample`).
   - The game puts row 0 at `to_local(e_min, n_max)`, with rows running along +z
     (`terrain_grid.gd:177-197`).
   - The fixture can tell a flip or a transpose from the right answer (lesson 34): its
     gradients differ along rows and columns, the north-west corner is 600.0625 and the
     south-west one 595.25, and a transpose changes the shape (41 × 24 against 24 × 41).
3. **The real village sits right in Terrain3D at 0.5, 1 and 2 m.** The probe, run on the
   unmutated code:
   - at each spacing, six regions from (0,−2) to (1,0), and 2000 random vertices read back
     exactly (0 missing, worst difference 0.0 m);
   - check points that lie on a vertex equal the grid's height; the others lie between
     vertices and read Terrain3D's in-between value, as expected;
   - the 1 m and 2 m villages were built with `config/terrain.json` edited in the scratch
     worktree only (`71bd4f17…` and `d6c1d558…`), then restored.
4. **The resampling rule, read against SPEC §8.**
   - The window is 2 × 2 pixels at 0.5 m and 1 m, and 4 × 4 at 2 m; at the edges the
     counts clip correctly and the zero padding adds nothing.
   - The sums are exact in 64-bit for real heights, and the counts are powers of two.
   - The pinned rule test matches exact fractions at all three spacings × three offsets.
5. **Seam M1-01↔M1-03.**
   - The terrain step reads its tile list only from `provenance.json`, requires the same
     order as the download's (the same formula in `download.py:62-67` and
     `terrain.py:376-381`), and compares each entry with the lock.
   - It hashes the very bytes it then reads, and it refuses a world config that changed
     while it ran.
   - Provenance's format is pinned by M1-01's golden on the writer side and by
     hand-written provenance on the reader side.
6. **Seam M1-03↔M1-04.**
   - What the pipeline writes (the block's keys, relative `file`, `float32-le`, rows
     running north to south) is what `TerrainGrid` reads.
   - The fixture's `generated/` is reproduced byte for byte by the pipeline and loaded by
     the game: the same files on both sides.
   - `terrain.world_sha256` must equal the manifest's own, on both sides.
7. **Seam M1-02↔M1-04.**
   - `TerrainGrid` given an unbuilt `WorldConfig` refuses visibly ("not read from this
     manifest"). It prints no `not read from a manifest` line, so M1-02's allowlist entry
     hides nothing here.
   - No production path calls `to_local` on an unbuilt config: `main.gd` and `shot.gd`
     convert only after `from_manifest` returned one.
   - `TerrainGrid` never subtracts an origin; it places the grid through `to_local`.
8. **Hard Rule 4 in production code.**
   - `git grep` for the origin, the village box and tile ids finds none in code.
   - Directions come from `WorldConfig` in `main.gd:163-178` and `shot.gd:80-85`.
   - Two places state the owner's axes on purpose, and both refuse any other mapping:
     `OWNER_AXES` in the pipeline and the axes check in `TerrainGrid`.
   - The census's control spelling is still caught (T-05).
9. **Line endings.** The pinned CRLF clone test passed in the baseline, and `* text=auto
   eol=lf` covers the fixture's JSON; `*.f32` is binary.
10. **`WorldConfig` (M1-02):** the pinned round-trip test really draws offsets wider than
    32 bits (it asserts more than 150 of 200 are inexact) and covers all 24 rotations.

## Does NOT prove

Nothing here shows:

- **Rendering.** That anything renders or looks right: there is no GPU.
- **Windows.** That the owner's PC computes `b6334c1f…`, or that its GDAL decodes the tiles
  the same way (T-01 is exactly that gap).
- **Cut tiles.** The code that cuts a tile at the area's edge was checked by reading only;
  the village cuts none.
- **Scale.** M5-scale areas: Terrain3D's ±16 km region map, image size limits, memory (about
  1 GB at the village) were not measured.
- **Tiny offsets in the game.** `TerrainGrid`'s fit and lattice checks run on 32-bit
  values, so an offset below their precision (well under a millimetre at the village) would
  pass. The pipeline refuses such an offset in 64-bit first. Read, not run.
- **Every mutation.** The mutations are a sample.
- **Known items.** M1-04 Findings 5 runs e and j, and M1-03 Findings 7, were graded (T-09,
  T-10), not re-found.
