# Brief: M3-13 — The new steps on the command line and in the manifest
Status: DONE (3ccb38f)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane H of wave 2, after wave 1 has landed and been integrated
(`docs/briefs/M3-plan.md`).

## Goal

The four steps of wave 1 become commands, and their outputs reach the game through the
manifest.

- `python -m mattini photo`, `roofs`, `surfaces` and `trees` build their outputs, as
  `terrain` and `buildings` do.
- The manifest's top level becomes exactly {buildings, photo, roofs, schema, surfaces,
  terrain, trees, world, world_sha256}: each new block checked, null when its step has not
  run.
- The several-datasets rule for `computed_for` gets one home, `lock.entries_sha256`.

Measured with design's throwaway on the real village: every step from the command line
writes design's values, and the manifest is 324'359 bytes, SHA-256
`3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 4, 5); `brain.md` H9, H17, H18, H24.
2. `docs/SPEC.md` §5 (the lock), §8 (the manifest, the expected output and its check order,
   *The photo*, *Roof colours*, *The surfaces*, *The trees*).
3. `pipeline/mattini/__main__.py`, `manifest.py`, `lock.py`, and the wave-1 modules
   `photo.py`, `roofs.py`, `surfaces.py`, `trees.py` (their `build_*` and `built_*_block`
   functions); the briefs M3-01 and M3-03 to M3-07 and their Findings (a name M3-01 or M3-03
   chose differently is recorded there).
4. The pinned tests and fixture manifests: `docs/briefs/pinning/M3-13/`.

## Decisions already made

1. **The commands** `photo`, `roofs`, `surfaces`, `trees`.
   - Each loads `config/world.json`, `datasets.json`, `datasets.lock.json` and its step
     config, plus `config/terrain.json` for roofs and trees.
   - Each takes `--raw` and `--out`, as `terrain` and `buildings` do; calls
     `<module>.build_<step>(…, raw_root, out_dir, progress=…)` through the module attribute
     (the pinned Ctrl-C test patches it); then writes the manifest and prints its path.
   - A refusal is one `mattini: error: …` line and exit 1, no traceback. Ctrl-C is M3-03's
     one handler in `main()`: ``mattini: interrupted: `python -m mattini <command>` did not
     finish; run it again``, exit 130.
   - The help lists the commands in pipeline order: lock, download, terrain, buildings,
     photo, roofs, surfaces, trees, manifest.
2. **`write_manifest`.**
   - The top level is exactly {buildings, photo, roofs, schema, surfaces, terrain, trees,
     world, world_sha256}; schema stays 1; serialised as today
     (`json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`).
   - It is written through a `.part` rename (design's decision: at 324 KB, a cut write
     would leave a manifest the game refuses as JSON).
   - A new block is null when its step has not run (its description file is absent).
   - Every step config is loaded and checked even when its step has not run, as the
     terrain's and the buildings' are today.
   - Areas: photo and surfaces from their own config's one area; roofs and trees from the
     terrain config's.
3. **The check order for a built new block, in `manifest.py`** (uniform for the four, whatever
   wave 1's block functions check themselves):
   1. `computed_for.world_sha256`, with the terrain's world text (design's step,
      `config/world.json`);
   2. the lock's fit for every dataset the step reads, in sorted order, through
      `lock.fit_problem` (M3-01, extended by M3-03), naming `python -m mattini lock <x>`;
   3. `computed_for.inputs_sha256`: `lock.entry_sha256` for one dataset, `lock.entries_sha256`
      for several, with a "design recomputes" text naming the config;
   4. roofs only: refused when no buildings are built, naming `python -m mattini buildings`;
   5. the step's `built_<step>_block`.

   Refusals use the step's error class (PhotoError, RoofsError, SurfacesError, TreesError),
   which `__main__` catches.
4. **`lock.entries_sha256(lock, names) -> str`**: the SHA-256 of `json.dumps({name: entry
   for name in names}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` in
   UTF-8, the one home of the rule. roofs.py and trees.py call it instead of their own
   copies. A name the lock lacks is a LockError naming its lock command, not a KeyError.
5. **The M2 fixtures' manifests** (`tests/shared/terrain_fixture`, `terrain_fixture_nw`,
   `buildings_fixture`: `generated/manifest.json`) take the 9-key shape: design's pinned
   copies, each the M2 file plus four `"<block>": null` lines, made two ways.
6. **Known and accepted** (design's answers to the wiring agent's questions):
   - `roofs` run before `buildings` writes its file; `manifest` then refuses it, naming
     `buildings`.
   - `tests/shared/roofs_fixture/photo.json` describes the synthetic photo's windows, not a
     photo config; the pinned test says so.
   - The terrain file is 91.6 MiB, 8.4 MiB under GitHub's limit; M3-08's packs check it.

## Scope — files you may touch

- `pipeline/mattini/__main__.py`, `manifest.py`, `lock.py` (`entries_sha256`; the fit
  function's use).
- `pipeline/mattini/roofs.py` and `trees.py`: their `inputs_sha256` call
  `lock.entries_sha256`.
- `pipeline/mattini/photo.py`, `roofs.py`, `surfaces.py`, `trees.py`: their own wave-1 fit
  checks replaced by `lock.fit_problem` (the rule's one home, SPEC §8), the refusal texts
  then fit_problem's. No other change to the four steps.
- The pinned copies (`cp -r docs/briefs/pinning/M3-13/. .`): `pipeline/tests/`
  `test_manifest_m3.py`, `test_manifest_lock_fit_m3.py`, `test_lock_entries.py`,
  `test_refusals_m3.py`; the three M2 fixture manifests.
- The existing tests the 9-key manifest breaks (measured: 9 failures, no others):
  - `test_golden_outputs.py`: the key set; `MANIFEST_SHA256` ba8383ff… →
    `cf4b939c6e4a89bf202081c365f22b338180c7d7141d34189af69cf709e20081` (computed two ways)
    and its comment;
  - `test_terrain_manifest.py`: two key sets, `MANIFEST_WITHOUT_TERRAIN_SHA256` → cf4b939c…,
    and its docstring's top level;
  - `test_buildings_manifest.py`: two key sets and its docstring's top level;
  - `test_buildings_fixture.py`: the key set.
- Your own new tests.

Not `download.py`, `terrain.py`, `buildings.py`, the configs, the other fixtures, `game/`,
`tools/`; the four steps beyond the two changes above.

## Depends on

Wave 1 landed and integrated: M3-01 and M3-03 (`lock.fit_problem`, the Ctrl-C handler),
M3-04 to M3-07 (the four steps). Lane I (M3-14) runs at the same time and shares no file.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-13/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] The real village end to end in a scratch checkout, from the command line: `download`
      for every dataset (the TLM zip may be copied from a scratch root where it is verified,
      never fetched twice), then `terrain`, `buildings`, `photo`, `roofs`, `surfaces`,
      `trees`, `manifest`. Each writes design's values; the manifest is `3ca0445c…`
      (324'359 bytes) on two runs. Record each step's time and peak memory (design: photo
      1.6 GB in strips, trees 2.6 GB) and every generated file's size (each under 100 MiB).
      - does NOT prove: that the game reads it (M3-14 and the integration after wave 2).
- [ ] Mutations, each failing a named pinned test, recorded:
      - null blocks left out, or written as `{}`;
      - roofs not refused without buildings;
      - no fit check in `manifest`, or the fit after the inputs;
      - `entries_sha256` hashing the entries one by one;
      - a step keeping its own fit check beside `lock.fit_problem` (your test: each step's
        unfitting lock is refused with fit_problem's text);
      - Ctrl-C not caught.
      - does NOT prove: a real republish.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing a step's rule, design's values, a fixture other than the three M2 manifests, or a
pinned file; any game change.

## Findings (executor writes)

Built by one lane builder session, 2026-10-15, on `main` at `7f68ddb` (wave 1 integrated). Files
touched: `pipeline/mattini/__main__.py`, `manifest.py`, `lock.py`, `photo.py`, `roofs.py`,
`surfaces.py`, `trees.py`; the pinned copies; the four named M2 tests; the three M2 fixture
manifests; five new test files (`test_m3_13_*`); this brief. Nothing else.

1. **The pinned copies** (`cp -r docs/briefs/pinning/M3-13/. .`) are in place and byte-identical
   (`cmp` of all seven files, run after the last edit and before the gate). Before the code,
   in a clone of `7f68ddb` with them copied in, `test_lock_entries.py` could not be collected
   (`entries_sha256` did not exist) and the other three modules failed 40 tests; after it all 44 pass.
2. **A decision the Scope did not name: `lock.shape_problem`.** Thirteen existing wave-1 tests
   (`test_photo_refusals.py` 2, `test_surfaces_config.py` 6, `test_trees_checks.py` 5; all outside
   this brief's Scope, so unchangeable here) pin that a lock *entry* with another key set, a file
   name that is not plain or a checksum that is not 64 lower-case hex digits is refused by the step
   in its own error class, naming the lock command. `lock.fit_problem` does not look at those (it
   compares collection, edition, resolution and ids), so replacing the steps' own checks by it alone
   failed exactly those thirteen (measured). Two ways, both reversible:
   - taken: one new function in `lock.py`, `shape_problem(lock) -> str | None` (`validate_lock`'s
     refusal as the whole text, "the lock: …", all five lock commands), asked by the four steps
     right after `fit_problem` (photo `photo_lock_problem`, roofs `_require_fit`, surfaces
     `_locked_entry`, trees `_locked_entries`); the lock's structure has the one home it had,
     `validate_lock`, and no step keeps a shape rule of its own;
   - not taken: widening `fit_problem` to the entries' shape, which changes the terrain and the
     buildings steps and M3-01/M3-03's pins.
   To undo: delete `shape_problem` and its four calls, and the thirteen tests then fail again
   unless they are edited (design's call). For the board's *Decisions for design to audit*.
3. **What was removed from the steps** (each replaced by `fit_problem`, whose text is now the whole
   refusal): photo `LOCK_KEYS`, `LOCK_COMMAND` and the body of `photo_lock_problem`; roofs
   `_sheets_problem`, `LOCK_BUILDINGS_COMMAND` and the old `_require_fit`; surfaces `_lock_problem`;
   trees `LOCK_COMMANDS`, `_lock_problem`, `_file_problem`. Kept on purpose:
   - `photo.photo_lock_problem` (now `(lock, datasets, world, area)`, `fit_problem` then
     `shape_problem`), because `test_photo_refusals.py::test_the_names_the_step_exports_for_the_roofs_step_exist`
     (outside Scope) pins the name;
   - `photo_tiles(raw_root, swissimage, lock, tiles)` keeps its signature (`test_photo_strips.py`)
     and no longer checks the lock's fit itself: it cannot, it has no world or area, and its two
     callers, `build_photo` and `build_roofs`, ask first (its docstring says so);
   - `trees._inputs_sha256(entries)` keeps its signature (`test_trees_helpers.py`) and calls
     `entries_sha256({"datasets": entries}, DATASETS)`; `roofs.inputs_sha256(lock)` likewise.
   `_lock_dict` in surfaces.py and trees.py still read a lock given as a path as plain JSON (their
   tests pin "cannot read the lock" in the step's error class); M3-06's note that `load_lock` could
   replace them was not taken ("no other change to the four steps").
4. **`manifest.py` repeats the steps' block-level order on purpose** (decision 3 of the brief), so
   a step's block function is never what decides what the owner is told first. That made two of
   the brief's mutations invisible to the pinned tests, which run the real block functions:
   - *roofs not refused without buildings*: removing only the manifest's own refusal leaves
     `test_roof_colours_without_buildings_are_refused` green, because `built_roofs_block` refuses
     a missing buildings block first thing; removing it there too (the mutation B2 below) fails it.
     `test_m3_13_manifest_checks.py` stubs the four block functions to fail the test when reached,
     so the manifest's own checks are what is tested, and fails on B1;
   - *the fit after the inputs / no fit check in manifest*: the pinned tests catch both (the
     inputs check names design's step first for an entry whose bytes changed), and so do mine.
5. **Mutations** (each applied in a scratch clone, the named tests run, the file restored from the
   scratch commit; both runs recorded; every row's harm is the one the pinned test or mine names):
   | mutation | fails |
   |---|---|
   | A1 `"photo": photo` left out of the manifest | `test_manifest_m3::test_each_fixture_s_manifest_is_what_write_manifest_writes[buildings_fixture]` (all fixtures) |
   | A2 a null block written as `{}` | the same, and `test_with_nothing_built_every_block_is_null` |
   | B1 the manifest's own buildings refusal removed | `test_m3_13_manifest_checks::test_roofs_without_buildings_are_refused_before_the_roofs_own_check` (the pinned test stays green, see 4) |
   | B2 B1, and the block given `{}` for no buildings | `test_manifest_m3::test_roof_colours_without_buildings_are_refused` and the same |
   | C1 no fit check in `manifest` | `test_manifest_lock_fit_m3::test_a_lock_that_does_not_fit_is_named_before_the_inputs_and_the_block` (nine of its ten ids) |
   | C2 the fit after the inputs | the same test |
   | C3 the world check after the fit | `test_manifest_lock_fit_m3::test_a_changed_world_comes_before_the_lock` (4) and mine |
   | D entries_sha256 hashing the entries one by one | `test_lock_entries::test_entries_sha256_is_that_of_the_named_entries_canonical_text`, `…_recorded_roofs_and_trees_inputs` |
   | D2 over the whole lock | the same two |
   | D3 a spaced, ASCII-escaped copy in roofs.py | eight tests and four errors of `test_roofs_step` (the recorded inputs differ) |
   | D4 the rule's separators spelled out in trees.py | `test_lock_entries::test_the_canonical_form_is_written_in_lock_py_only` |
   | E1–E4 a step keeping its own fit check beside `fit_problem` (photo resolution, roofs edition, surfaces collection, trees collection) | `test_m3_13_step_fit::test_a_lock_that_does_not_fit_is_refused_with_fit_problem_s_text` (the matching ids, build and built-block) |
   | F Ctrl-C not caught | `test_refusals_m3::test_a_ctrl_c_in_a_step_names_the_command_to_run_again` (4) |
   | G the manifest written in place | `test_m3_13_commands::test_the_manifest_is_written_to_a_part_file_and_renamed`, `…_a_rename_that_fails_leaves_the_manifest_that_was_there` |
   | H1 roofs given its two configs swapped | `test_m3_13_commands::…[roofs]` |
   | H2 a step command that does not write the manifest | the same, four ids |
   | H3 roofs listed before photo in the help | `test_refusals_m3::test_the_help_lists_the_commands_in_pipeline_order` |
   | J1 a step config read but not checked when its step has not run | `test_m3_13_manifest_checks::test_every_step_config_is_checked_even_when_its_step_has_not_run[photo]` |
   | K the photo block's area taken from the terrain config | `test_manifest_m3::…[photo_fixture]` |
   | L1/L2 no shape check in photo / trees | `test_m3_13_step_fit::test_a_fitting_lock_that_is_not_well_formed…` and the wave-1 tests of item 2 |
   does NOT prove: that these are the only ways to break it (a first E4 drew no failure: no case
   changed a trees dataset's collection; the cases are now generated per dataset and per way).
6. **The real village, from the command line,** in a scratch `git clone` (H22) with the five
   downloads (3.2 GB in 2 min 37 s; `download photo` verified all six tiles on its first run, nine
   fetches for six tiles), my source copied over the clone's `pipeline/mattini`. Each step wrote design's values, compared with
   `config/*.json` before writing, wall time and peak resident memory of the process:
   | command | result | time | peak |
   |---|---|---|---|
   | terrain | `b6334c1f…`, 96'040'004 B | 9.6 s | 996 MB |
   | buildings | 1'486 in six chunks | 7.8 s | 346 MB |
   | photo | pixels `00533bc6…`, JPEG `cf83c705…`, 50'222'573 B | 76.5 s | 1'214 MB |
   | roofs | `8d9664b6…`, 1'486 of 1'486 coloured, 290'006 B | 34.7 s | 1'268 MB |
   | surfaces | `93d78ba6…`, PNG 1'148'917 B | 34.5 s | 441 MB |
   | trees | 34'412 in six chunks, 688'240 B | 41.5 s | 1'304 MB |
   | manifest | `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`, 324'359 B | 1.7 s | 350 MB |
   The manifest was deleted and written again: byte-identical (`cmp`), same hash. The largest file is
   the terrain's 96'040'004 B (91.6 MiB, 8.4 MiB under 100 MiB); every other is smaller (the photo
   48 MiB). Peak memory is under design's figures (photo 1.6 GB, trees 2.6 GB) and under M3-04's
   2 GB gate. Two refusals on the real data: `manifest` with the buildings description moved away
   ends `mattini: error: …/roofs/village.json: roof colours are built, but no buildings are: …;
   `python -m mattini buildings` builds the buildings first`, exit 1, no manifest; `roofs` and `trees`
   with `--raw /nonexistent` end in one line naming `python -m mattini download buildings` and
   `download terrain`, exit 1, nothing created under `--out`.
   does NOT prove: that the game reads it (M3-14 and the integration after wave 2), a real republish.
7. **The existing tests the nine-key manifest broke** are the four the brief names, edited as it
   says (key sets, `MANIFEST_SHA256` and `MANIFEST_WITHOUT_TERRAIN_SHA256` → `cf4b939c…`, comments,
   docstrings). Measured: with the three fixture manifests replaced and the old code, six tests
   failed (`test_buildings_fixture`, `test_buildings_manifest`, `test_buildings_step`,
   `test_terrain_fixture`, `test_terrain_fixture_nw`, and `test_repo_tracked` for the new files not
   yet staged); after the code and the four edits the full suite had one failure, `test_repo_tracked`,
   and none once the new files were staged. The brief's count of nine was not reproduced one for one
   (it probably counts asserts); nothing outside the named files needed a change.
8. **Residue, said out loud.**
   - A write cut between `manifest.json.part` and the rename leaves the `.part` in
     `game/assets/generated/` until the next `manifest` (which writes it again and renames it away).
     Nothing else removes it; whether `tools/export.sh` step 4c would stop on it was not checked.
   - `trees.py` still imports private helpers of `surfaces.py` (M3-07's finding); none was renamed.
   - `roofs.inputs_sha256`, `photo.photo_lock_problem` and `trees._inputs_sha256` are now thin
     calls onto `lock.py`; they stay because their names are pinned by tests outside this Scope.
9. **The standard gate,** both times chained to the commit or run alone after the rebase
   (`tools/gate.sh > gate.log`), exit 0, `== gate: all steps passed`:
   - on my own head (`8084c80`, base `7f68ddb`): pytest 2156 passed, 5 network tests deselected;
     GUT 41 scripts = 41 `test_*.gd` files, 224 tests, 8618 asserts, `GUT version:  9.6.1`;
   - after `git pull --rebase` brought in M3-14 (`4f7af57`, the lane that shares no file with
     this one), the pushed head `3ccb38f`: pytest 2169 passed, 5 deselected; GUT 44 scripts = 44
     files, 236 tests, 8745 asserts. This is plan item 3 of *After wave 2*: M3-13's three nine-key
     fixture manifests and M3-14's `complete_world.gd` leave every game test green on the combined
     head. The allowlist was not touched.
   does NOT prove: that it renders or looks right.
