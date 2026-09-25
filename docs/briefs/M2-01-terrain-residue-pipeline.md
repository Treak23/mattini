# Brief: M2-01 — M1's residue, the pipeline half
Status: DONE (b5a45e5)

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

The pipeline half of M1's review residue is closed (`docs/history/ARCS.md` §M1, the
carry-over table; the full findings in `docs/reviews/M1-R1-terrain.md`). Five changes:

- `terrain` knows the heights it must produce. The expected SHA-256 of each built terrain
  (the village at 0.5 m, 1 m and 2 m) is design data in `config/terrain.json`. `terrain`
  compares its output with it before writing anything, and `manifest` refuses any other
  file (T-01 b).
- A gate test builds a terrain from 2 × 2 synthetic tiles cut by the area, pinned to exact
  bytes (T-01 a). It also pins `build_terrain`'s own description bytes (T-03).
- `manifest` checks the terrain block's `source` against the lock and the datasets config
  (T-04), with exact key sets (T-03).
- The download and the lock serve the area named by `config/terrain.json` (T-06).
- The origin census, the tracked-files test and a docstring are tightened (T-05, T-07,
  T-08).

The pipeline also reproduces the second shared terrain fixture (`tests/shared/
terrain_fixture_nw/`) that M2-02's game tests load: the seam, as for the first fixture.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §5 (the lock) and §8 (*The terrain grid*, including the expected
   SHA-256 paragraph added at M2 planning).
3. `docs/history/ARCS.md` §M1: D19 and the carry-over table rows T-01, T-03 to T-08.
4. `docs/reviews/M1-R1-terrain.md`: T-01, T-03 to T-08 (the harm, the proof, the fix).
5. `config/terrain.json` (its new shape), `config/world.json`, `config/datasets.json`,
   `config/datasets.lock.json`.
6. `tests/shared/terrain_fixture/` and `tests/shared/terrain_fixture_nw/` with
   `tests/shared/terrain_vectors.json` and `tests/shared/terrain_vectors_nw.json`.
7. The pinning tests, `docs/briefs/pinning/M2-01/pipeline/tests/`.

## Decisions already made

- **The expected SHA-256 (T-01 b; SPEC §8).** Each area in `config/terrain.json` carries
  `expected_sha256`, an object from a spacing, as swisstopo writes it (`format(s, "g")`:
  `"0.5"`, `"1"`, `"2"`), to the SHA-256 of the heights file at that spacing: 64
  lower-case hex digits. It must hold the configured spacing, and holds no key but these
  three. The key set of an area is exactly `{"expected_sha256", "spacing_m"}`. The
  village's three values were computed by design two independent ways at M2 planning (the
  pipeline's own code and an exact area-overlap implementation, identical bits):
  - 0.5 m: `b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a` (96'040'004 bytes),
  - 1 m: `71bd4f174dfc3d07a3becace073c62bdf6b5cc010072a5e483a484210e8bc333` (24'020'004 bytes),
  - 2 m: `d6c1d558fee28c91472f2fea9c5db06d9b74480dd22f77554bf7037beec794ce` (6'010'004 bytes).

  `build_terrain` computes the heights, then compares their SHA-256 with the expected
  value *before* writing anything. A difference is a `TerrainError` naming the area, the
  spacing, both values and `config/terrain.json`, and says that design computed the
  expected value two independent ways, so this machine or this code produces other
  heights. Nothing is written then. `built_terrain_block` (so `manifest`) refuses a built
  block whose `sha256` is not the expected value for its spacing, naming
  `python -m mattini terrain`. The two shared fixtures' `terrain.json` carry their own
  value (0.5 m `fd02c744…` and 2 m `31096e50…`).
- **The 2 × 2 build test (T-01 a, T-03)** is pinned in `test_terrain_build_tiles.py`: four
  synthetic 0.5 m GeoTIFF tiles (2623-1095, 2624-1095, 2623-1096, 2624-1096) written by the
  test from a formula, and an area E 2'623'250–2'624'750 / N 1'095'500–1'096'500 that cuts
  all four. Built at 2 m and at 0.5 m, the heights file has design's exact SHA-256. The
  description `terrain/village.json` has exactly the bytes the test renders from the
  inputs (T-03: no date, host or path can enter it).
- **The manifest checks the source (T-04, T-03).** `built_terrain_block` also requires the
  following, else it refuses naming `python -m mattini terrain`:
  - `source` has exactly the keys `attribution`, `collection`, `dataset`, `edition`,
    `resolution_m`, `tiles`, and each entry of `tiles` exactly `sha256`, `tile`;
  - `source.dataset` is `swissalti3d`;
  - `attribution`, `collection`, `edition` and `resolution_m` equal `config/datasets.json`'s;
  - `tiles` equals, in order, the tiles covering the area, each with the SHA-256 the lock
    pins for it (`config/datasets.lock.json`).

  `build_manifest` and `write_manifest` take a `lock_path` keyword (default the committed
  lock). Consequence for the fixtures: their `source.tiles` name the real tile ids their
  boxes lie in (`2601-1199` for the first fixture, `2698-1101` for the second), not
  `synthetic`, and each fixture folder holds a `datasets.lock.json` pinning that tile's
  SHA-256 (the SHA-256 of its `source.f32`) with the file name `source.f32`. Design
  prepared both fixtures accordingly; their heights files are unchanged. The first
  fixture's changed files (`terrain.json`, `datasets.lock.json`,
  `generated/terrain/fixture.json`, `generated/manifest.json`) and the new
  `config/terrain.json` travel with the pinning tests
  (`docs/briefs/pinning/M2-01/config/`, `…/tests/shared/terrain_fixture/`), because the
  code M1 left refuses them; the pinned copy step puts them in place.
- **The area served (T-06).** `download terrain` and `lock terrain` take the area from
  `config/terrain.json` (its one area). The API: `village_tiles(world)` becomes
  `download.area_tiles(world, area)`; `published_assets`, `download_terrain` and
  `lock.build_lock` take a keyword-only `area`. The command line reads the area from the
  terrain config and passes it on. Nothing in `pipeline/mattini/` names `"village"` any
  more; the download's refusals name the area.
- **T-05, T-07, T-08:** as in the carry-over table.
  - T-05: the census also catches the kilometre pair reversed (`1096 … 2623`), the pair on
    lines up to three apart in either order, and a mantissa with trailing zeros
    (`2.6230e6`, `2.62300E+06`). It proves text only, and its docstring says so.
  - T-07: `test_repo_tracked.py` scoped by exclusion. Every file the gate or the game
    depends on under `config/`, `tests/shared/`, `tools/`, `game/` (vendored Terrain3D
    binaries included) and `pipeline/` must be tracked, minus named exclusions
    (`game/.godot/`, `game/assets/generated/`, caches).
  - T-08: `test_terrain_rules.py`'s docstring states SPEC §8's condition: one rounding
    while the height offset subtracts exactly.
- **The second fixture's pipeline half:** `test_terrain_fixture_nw.py` (pinned) reproduces
  `tests/shared/terrain_fixture_nw/generated/` byte for byte, as `test_terrain_fixture.py`
  does for the first.

## Scope: files you may touch

`pipeline/mattini/terrain.py` · `pipeline/mattini/manifest.py` ·
`pipeline/mattini/download.py` · `pipeline/mattini/lock.py` · `pipeline/mattini/__main__.py`
· `pipeline/tests/` (the pinned copies, your own tests, and the live copies of earlier
tests the changes touch) · the pinned design data put in place by the copy step
(`config/terrain.json`, `tests/shared/terrain_fixture/`), never edited: a pinned test that
proves one wrong is a BLOCKED question.

## Depends on

None. It shares no file with M2-02, so the two can run at once.

## Done when (gates)

- [x] The pinned copies are in place and byte-identical:
      `cmp` each file under `docs/briefs/pinning/M2-01/` with its live copy.
      (Findings 1: all 9 files, before each commit.)
      - does NOT prove: that the pinned tests are the right tests (design's job).
- [x] `terrain` refuses a mismatching output before writing anything. Mutation: change one
      height rule (e.g. the window) and watch `test_terrain_build_tiles.py` and the
      expected-SHA test fail; record both runs in Findings.
      (Findings 4, runs W, E, E2, M.)
      - does NOT prove: that the owner's Windows PC computes the same bytes (only its first
        run shows it, and now `terrain` says so itself).
- [x] With the real tiles (downloaded to a scratch folder, never committed),
      `python -m mattini terrain --raw <scratch>` writes `village.f32` `b6334c1f…` and
      exits 0. A copy of `config/terrain.json` set to 1 m or 2 m reproduces design's value
      (Findings: the three runs).
      (Findings 3: 0.5 m `b6334c1f…`, 1 m `71bd4f17…`, 2 m `d6c1d558…`, each exit 0.)
      - does NOT prove: that it renders or looks right.
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      (Findings 2: `b5a45e5`, chained on exit 0.)
      - does NOT prove: that the game places the terrain right (M2-02's second fixture).

## Forbidden

A new dependency; a change to the rule (SPEC §8) or to any fixture's expected bytes; a
version bump.

## Findings (executor writes)

Executor agent of the one M2 session, 2026-09-25, in its own worktree and branch (the
owner's run mode; nothing synced or pushed). Code commit `b5a45e5` on top of `8a713b5`.

1. **Pinned copies:** `cp -r docs/briefs/pinning/M2-01/. .` put 9 files in place (the four
   tests, `config/terrain.json`, and the first fixture's `terrain.json`,
   `datasets.lock.json`, `generated/manifest.json`, `generated/terrain/fixture.json`); `cmp`
   of each against its pinned copy exits 0 before the code commit and before this one.
   With M1's code they gave 38 failures (350 passed); now all 25 pinned tests pass.
2. **Standard gate** (`tools/gate.sh > gate-M2-01.log 2>&1 && git commit`), exit 0 for
   `b5a45e5`: `uv lock --check`, pytest **423 passed**, 3 deselected (the network tests;
   the M1 close had 367), ruff check and format, `manifest`, Godot 4.6.3 import and parse
   check, GUT 15 scripts, 69 tests, 1641 asserts, `---- All tests passed! ----`, gdlint,
   gdformat. The 73 pytest warnings are rasterio's `PendingDeprecationWarning` from
   `from_origin`, as in M1.
3. **Real runs**, the six 2024 tiles in the scratch download (its `provenance.json` and
   every tile's SHA-256 equal the lock), outputs in a scratch folder, nothing committed:

   | Spacing | How | Exit | `village.f32` SHA-256 | Bytes | Grid | Time |
   |---|---|---|---|---|---|---|
   | 0.5 m | `python -m mattini terrain --raw <scratch> --out <scratch>` (committed config) | 0 | `b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a` | 96'040'004 | 4001 × 6001 | 6 s |
   | 1 m | `build_terrain` with a config copy | 0 | `71bd4f174dfc3d07a3becace073c62bdf6b5cc010072a5e483a484210e8bc333` | 24'020'004 | 2001 × 3001 | 3.3 s |
   | 2 m | `build_terrain` with a config copy | 0 | `d6c1d558fee28c91472f2fea9c5db06d9b74480dd22f77554bf7037beec794ce` | 6'010'004 | 1001 × 1501 | 2.3 s |

   Each equals design's value, and each run printed `the heights have the SHA-256
   config/terrain.json expects, <value>` before writing. At 0.5 m the manifest is
   `0e4572fb…` and `village.json` `ea6e6c90…`, byte for byte M1-03's: the new checks add no
   field. How the 1 m and 2 m runs were made (a scratch script, not committed): read
   `config/terrain.json`, set `areas.village.spacing_m` to 1.0 or 2.0 (nothing else), write
   the copy to the scratch folder, load it with `load_terrain_config(copy)` (so it is
   validated), call `build_terrain(load_world(), load_datasets(), load_lock(), config, raw,
   out)` with the committed world config, datasets config and lock, then
   `write_manifest(out, terrain_config_path=copy)`; manifests `c9fe580d…` (1 m) and
   `a047b721…` (2 m).
4. **Mutation proofs.** Each from a saved patch, `git apply`, the run, `git apply -R`, then
   `cmp` against a saved original (T: `git ls-files -s` before and after identical); run on
   the code of `b5a45e5` (only a test comment changed after them). Unmutated: 423 passed.

   | Run | Mutation | What failed | Owner-visible harm |
   |---|---|---|---|
   | W | the window at 2 m is 2 × 2 pixels (`half = max(1, step // 4)`), the brief's height-rule change | `test_terrain_build_tiles.py`: 3 failed, 1 passed (0.5 m, which W does not change); the builds fail with the expected-SHA refusal itself: `TerrainError: area 'village' at 2 m: the heights built here have SHA-256 cf7bd4a3…, config/terrain.json expects 42756c1c…`. Full suite: 17 failed and 18 errors (the fixture of `test_terrain_manifest_source.py`, whose build is refused), among them every successful 2 m build in `test_terrain_build.py`, whose expected value comes from the independent reference (5). The real village at 2 m under W: refused, `3f915db8…` built, `d6c1d558…` expected, nothing written. | a changed rule, or a machine that computes other heights, writes another village without a word, and `manifest`, the game and an export accept it (M1 R1 T-01) |
   | E | `build_terrain`'s comparison removed (`if False`) | the expected-SHA tests: `test_a_wrong_expected_value_is_refused_before_anything_is_written` (pinned) and mine `test_heights_other_than_the_expected_ones_are_refused_before_anything_is_written`; 421 passed | the check exists on paper only |
   | E2 | the files written before the comparison | the same two: `assert not True` (the files exist) | a refused build still overwrites the good terrain on disk |
   | M | `manifest`'s comparison with the expected value removed | `test_manifest_refuses_a_terrain_that_is_not_the_expected_one` (pinned): `DID NOT RAISE` | a heights file other code or another machine built is accepted into the manifest and shipped |
   | S | `source` may carry extra keys (a subset check) | `[a-date]`, `[a-host]` of `test_a_source_that_is_not_exactly_the_inputs_is_refused` | a date or host name in the manifest: other bytes tomorrow or on the owner's PC (T-03, Hard Rule 5) |
   | A | attribution and collection not compared | `test_a_changed_datasets_config_is_refused[attribution]`, `[collection]` | the credits keep the old wording after `config/datasets.json` changes (T-04, Hard Rule 3) |
   | L | the tiles' SHA-256s not compared with the lock | `test_a_tile_the_lock_now_pins_differently_is_refused` (the review's T-04 scenario: tile rewritten 0.25 m higher, lock re-pinned, no `terrain`), `[another-tile-sha256]` | a republished tile adopted in the lock, the old terrain kept: two machines, one commit, two villages |
   | O | tiles compared without their order | `test_the_tiles_must_come_in_the_area_s_order` (four tiles, built for real) | a description not in the build's order accepted as if the pipeline had written it |
   | D | the command line's download serves the world's first area, not the terrain config's | 4 in `test_download_area.py` | T-06's loop: `terrain` names `download terrain`, which fetches another area again |
   | C | the census without the reversed and multi-line pair | 4 spellings of `test_every_spelling_the_review_found_is_caught` | a second origin as two constants drifts from `config/world.json` unnoticed (Hard Rule 4) |
   | C2 | the mantissa rule without trailing zeros | `[ORIGIN_E = 2.6230e6]`, `[E = 2.62300E+06]` | the same |
   | R | the review's own mutation C: the three spellings written into `terrain_loader.gd` and `terrain.py` | `test_the_origin_lives_only_in_config`, offenders `terrain_loader.gd: '2623\nconst ORIGIN_TILE_N_KM := 1096'`, `terrain.py: '1096, 2623'`, `'2.6230e6'`, `'1.0960e6'` (the review measured the M1 gate green with them) | the same |
   | T | the review's T-07 mutation: `git rm --cached -r tests/shared/terrain_fixture game/addons/terrain_3d/bin` (12 files, still on disk); undone with `git add` of the same paths | `test_every_file_the_gate_or_the_game_depends_on_is_tracked`, naming all 12 | a commit dropping the fixture or Terrain3D passes the gate; the owner's next clone lacks them |

   How I read the brief's gate line: `test_terrain_expected.py` builds nothing, so no height
   rule can fail it. Under W, every building test fails with the expected-SHA refusal (the
   gate's subject), and E, E2 and M fail the expected-SHA tests themselves; all four are
   recorded.
5. **Expected values for the earlier tests' synthetic builds.** `test_terrain_build.py`,
   `test_terrain_refusals.py` (so `test_terrain_cli.py` and `test_terrain_manifest_source.py`,
   which use its world) and `test_download_area.py` build one synthetic tile at 2 m. Their
   configs expect a SHA-256 computed from each test's own source by
   `pipeline/tests/window_mean.py`: SPEC §8's window rule written another way (the window
   around each vertex over a NaN-padded source, averaged by `np.nanmean`, cast once to
   32-bit), sharing no code with `resample`. Cross-check: it reproduces design's two 2 × 2
   values (`42756c1c…` at 2 m, `c3bbb0f0…` at 0.5 m) bit for bit, a third implementation
   agreeing. The fixture tests use the fixtures' own `terrain.json` (design's values). Two
   refusal tests carry `"0" * 64` as the expected value of a config that must be refused
   before any comparison (at the spacing, `test_terrain_manifest.py`; at the area name,
   `test_terrain_refusals.py`): deliberately invalid inputs, never compared.
6. **Choices inside the brief's scope** (reversible):
   - One validator, `check_terrain_config`, for `load_terrain_config`, `build_terrain` and
     `built_terrain_block`, so a config dict handed over directly is checked too. Its
     order: top-level keys, schema, one area, the name, the area's exact key set, the
     spacing, `expected_sha256` an object, no key but `"0.5"`, `"1"`, `"2"`, every value 64
     lower-case hex digits, the configured spacing present. Helpers `configured_area` and
     `spacing_key` (`format(s, "g")`).
   - `write_terrain` is split into `_describe` (the bytes and the description, nothing
     written) and `_write_files`; `build_terrain` hashes once, compares, then writes those
     bytes. `write_terrain` keeps its signature and output (the fixture tests call it).
   - The manifest's order: keys, area, file, format, world, spacing, then the source (exact
     keys; `tiles` a list of entries with exactly `sha256` and `tile`; `dataset`; the four
     values against the datasets config), rows and columns, size, the file against the
     description, the file against the expected value, then the lock, the tile list in
     order and each tile's SHA-256. The lock is read only when a description exists, so a
     manifest with `terrain` null depends on no lock (tested). **For design to rule:** a
     lock that does not fit the datasets config, or pins no SHA-256 for one of the area's
     tiles, is refused through the terrain step's own `_locked_tiles`, naming `python -m
     mattini lock terrain` (the command that helps, the T-06 lesson), not `terrain` as the
     brief's list says. The alternative is one line: name `terrain` there too.
   - `terrain`'s `_tiles_covering(box)` is gone: `download.area_tiles(world, area)` is the
     one implementation for the download, the lock, the terrain step and the manifest.
   - The download's refusals name the area: the lock refusals end `(area 'village')`, the
     per-tile ones start `tile <id> of area 'village': ` (keeping the `tile <id>` prefix the
     CLI tests match).
   - `terrain` prints `the heights have the SHA-256 config/terrain.json expects, <value>` on
     stderr before writing, so the owner's first run on Windows says itself that it
     matches (lesson 38).
   - T-05: besides the listed spellings, the e3 forms with a decimal mantissa (`2623.0e3`,
     `1096.0e3`) and `_` between trailing zeros (lesson 9). The pair on lines 1 to 3 apart
     is matched line by line (`2623[^\n]*\n(?:[^\n]*\n){0,2}[^\n]*1096`, and reversed); a
     pair four lines apart is not counted, and a test says so. Measured before writing it:
     0 hits in the 36 scanned files; the multi-line pair meets 55 places in the excluded
     homes (docs, config, tests), which is why the exclusions matter.
   - T-07: the roots `config/`, `tests/shared/`, `tools/`, `game/`, `pipeline/` plus
     `.gitattributes` and `.gitignore`; excluded `game/.godot/`, `game/assets/generated/`,
     `pipeline/.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.pyc`/`.pyo`/
     `.pyd`. Measured after a Godot import and a full gate: nothing else appears untracked.
     Positive controls: the scan reaches both fixtures' sources and the 4 Terrain3D
     binaries. The required-files list now also holds `terrain_vectors_nw.json` and requires
     `terrain.gdextension`. It reads the index, so new files are staged before the gate, as
     before.
   - T-08: the module docstring and `_reference`'s state the condition; no test change.
     `terrain.py`'s own docstring said "subtracted with one 64-bit rounding and ... rounded
     once", the same over-claim; it now states the condition too.
   - New test files: `test_terrain_manifest_source.py` (T-03, T-04: 20 tests, each refusal
     checked for its own reason), `test_download_area.py` (T-06: `lock`, `download` and
     `terrain` on the command line for a second area, `valley`, one tile east, served by a
     fake swisstopo with a real GeoTIFF; the refusals naming the area; a text census that
     no area name is written in `pipeline/mattini/`, text only).
7. **Out-of-scope touches:** none. Every change is in `pipeline/mattini/`,
   `pipeline/tests/` and the pinned design data. Mutation R touched
   `game/scripts/terrain/terrain_loader.gd` for one run and was undone (`cmp` equal).
8. **Surprises.**
   - The worktree was created at `63816ac`, while the brief lived in `8a713b5` on the
     design branch. My own `git merge --ff-only 8a713b5` was refused by the auto-mode
     classifier; the branch was fast-forwarded to `8a713b5` at 18:34:26Z by someone else
     (reflog: `merge 8a713b5: Fast-forward`), and I worked normally from there. The
     worktree for M2-02 (`…-2`) was created at `63816ac` too.
   - The pinned `test_a_wrong_expected_value_is_refused_before_anything_is_written`
     asserts design's value in the message, so it also fails under any height-rule change
     (W): it pins the bytes as well as the refusal.
9. **Follow-up candidates** (not built; no design authority):
   - **The manifest does not derive `rows`, `columns` or `lv95_box` from the world's area
     and the spacing.** Measured on the first fixture with a scratch script: a description
     with rows and columns swapped (41 × 24 instead of 24 × 41, the same product, so the
     size check passes) and one with its box shifted 1 km east are both ACCEPTED, with the
     world, spacing, source, lock and heights all matching. The pipeline's own build writes
     them right, so only a hand-edited or foreign description gets there; M0 C-01's class
     one field further (a field copied verbatim, not re-derived). Whether the game's
     `TerrainGrid` catches it is M2-02's side, unmeasured here.
   - Worktrees for the executors should start from the design branch's head, not
     `origin/main`.
