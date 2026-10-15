# Brief: M3-01 — M2's residue, the pipeline
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane A of wave 1, first; M3-03 follows in this lane
(`docs/briefs/M3-plan.md`).

## Goal

The pipeline half of M2's residue (`docs/history/ARCS.md` §M2, "Carried into M3"): eight
V1 findings and three builders' follow-ups, each a P3. None changes an output byte. They
make refusals name the command that helps, prove two orders of checks, and close test gaps
that let a wrong implementation pass:

- `manifest` checks the lock's fit by the steps' own rule, right after the world (V1-P-01,
  V1-P-07);
- `download terrain` requires exactly the area's tiles (V1-P-02);
- the terrain step's world and inputs checks run before any tile is read, proven by
  recording the reads (V1-P-03);
- two docstrings name test files that exist (V1-P-04);
- `resolution_m` is required for `swissalti3d` (V1-P-05);
- no `*.part` is left in a step's output folder (V1-P-06, the pipeline half; the export
  half is M3-08's presets);
- the canonical lock form is proven against its twins (V1-P-08);
- the follow-ups: `manifest.py`'s docstring lists the terrain's shape checks (M2-06 F9);
  fiona is imported only where a FileGDB is read (M2-04's check); the reader tests compare
  triangles in order (M2-09 F8).

## Read first, in order

1. `CLAUDE.md`; `brain.md` H9, H17, H18.
2. `docs/history/ARCS.md` §M2 (D25 and the carried table); `docs/reviews/M2-V1.md`.
3. `docs/SPEC.md` §5 (the lock), §8 (the expected output, `computed_for`).
4. `pipeline/mattini/download.py`, `lock.py`, `terrain.py`, `buildings.py`, `manifest.py`,
   `datasets.py`, and their tests.
5. The pinned tests: `docs/briefs/pinning/M3-01/`.

## Decisions already made

1. **The lock's fit (V1-P-01, V1-P-07, V1-P-02).** The fit is the steps' rule, exact for
   both datasets: the entry's collection, edition and resolution are the datasets config's,
   and it pins exactly the area's tiles (terrain) or sheets (buildings), no more and no
   fewer. Its one home is a public function in `lock.py`, `fit_problem(lock, datasets, world,
   area, dataset) -> str | None`: the refusal text, naming `python -m mattini lock <x>`, or
   None when the entry fits. Download, the step and `manifest` call it (design's decision:
   M3-03 extends it to the three new datasets, M3-13's manifest calls it for the new
   blocks). Not pinned, but named exactly so: M3-03 and M3-13 call it by this name.
   - The terrain step's own fit becomes exact. Measured: today it accepts an extra tile and
     then says "design recomputes".
   - `built_terrain_block` and `built_buildings_block` check in the step's order: the world,
     then the lock's fit, then the inputs (`computed_for`), then the block. An unfitting
     lock is refused with the step's own message, naming `python -m mattini lock <x>` and
     no other command. Measured: today an extra or a missing sheet gets "design recomputes",
     and another edition or no entry reaches a key-set refusal of the block first.
   - The steps check the fit before reading provenance.json, too (design's decision), so a
     changed datasets config names `lock <x>` at the step as well as at `manifest`. This
     one is not pinned: write its test.
   - `download terrain` refuses a lock pinning tiles beyond the area's before any STAC read,
     naming `lock terrain`, as `download buildings` does.
2. **The checks before reading (V1-P-03).** The terrain step's order is right today; its
   test only checked that no output exists. The pinned test records every path opened and
   proves no tile or sheet is read before both checks pass. No code change.
3. **Docstrings (V1-P-04, M2-06 F9).**
   - `test_terrain_manifest.py` and `test_buildings_manifest.py` name
     `test_computed_for_terrain.py` and `test_computed_for_buildings.py`.
   - `manifest.py`'s docstring names the box, the columns and the rows among the terrain's
     refusals.
   - The pinned census reads the docstrings and comments of `pipeline/`, `game/scripts`,
     `game/tests` and `tools/*.sh` (never code or strings): every test file they name exists.
4. **`resolution_m` (V1-P-05).** `load_datasets` refuses a `swissalti3d` entry whose
   `resolution_m` is not a positive finite number (an int or a float, not a bool), a
   `DatasetsConfigError` naming the file and the dataset. The four commands then end with one
   `mattini: error:` line instead of a KeyError's traceback. M3-03 extends the rule to
   `swissimage` and `swisssurface3d` in the same loop, after its edition rule.
5. **No `*.part` after a step (V1-P-06).** After a build that succeeds, the terrain step
   removes every `*.part` in `<out>/terrain/`, and the buildings step every `*.part` in
   `<out>/buildings/`. Each step cleans its own folder only, never `data/raw/`, where
   `download tlm` keeps its part on purpose (M3-03). A refusal removes nothing. The M2-07
   builder's test that pinned a kept `.part` changes.
6. **The canonical lock form (V1-P-08).** `entry_sha256` and `write_lock` are proven on an
   entry with every object's keys in reverse order and a non-ASCII collection; its digest
   `2cc3bd25…3111` was computed two ways (hashlib on the literal, coreutils' sha256sum on its
   bytes). No code change.
7. **fiona (M2-04's check).** Imported only inside the function that reads a FileGDB
   (`buildings.read_sheet`). The pinned test imports every module of the package, so later
   modules count too: lane D's `surfaces.py` and `trees.py` follow the same rule. Then it
   runs `write_manifest` with no fiona module loaded.
8. **The reader tests in order (M2-09 F8).** The two reader test files are replaced: they
   write clockwise, non-overlapping triangles that start at different points and compare
   them in order. Measured with fiona 1.10.1: GDAL's writer stores every ring clockwise seen
   from above, keeping its first point.
9. **Kept for M3-03** (the next brief in this lane; its pinned tests patch or match these):
   `mattini.__main__.main`, the `lock <dataset>` and `download <dataset> --out` shapes,
   `download.STAC_ITEM`, `lock.LOCK_PATH`, `lock.load_lock`, `lock.entry_sha256`,
   `load_datasets(path)`, `DatasetsConfigError`, and the refusal forms
   `"tile <t> of area '<a>': "` and `"cannot read the STAC item"`. Do not rename them.
10. **Kept for lanes C and D** (M3-04 to M3-07 import these while this lane changes their
    modules in the same wave): their names and signatures stay as they are; their insides may
    change.
    - `terrain.py`: `world_refusal`, `inputs_refusal`, `check_computed_for`,
      `configured_area`, `check_terrain_config`, `load_terrain_config`, `resample`,
      `OWNER_AXES`, `AREA_NAME`;
    - `buildings.py`: `build_chunks`, `read_sheet`, `BuildingsError`, and the rule helpers
      `_snapped`, `_weld`, `_check_solid`, `_signed_volume` (roofs.py repeats the
      selection with them);
    - `download.py`: `area_tiles`, `area_sheets`, `dataset_of`, `PROVENANCE`;
    - `lock.py`: `load_lock`, `validate_lock`, `LOCK_PATH`, `entry_sha256`.

    Not kept: `_lock_problem`, `_locked_tiles`, `_locked_sheets` and the private provenance
    readers. Their rule moves to `lock.fit_problem`, and lanes C and D write their own checks
    until M3-13.

## Scope — files you may touch

- `pipeline/mattini/download.py`, `lock.py`, `terrain.py`, `buildings.py`, `manifest.py`,
  `datasets.py`.
- `pipeline/tests/`:
  - the pinned copies, new: `one_tile.py`, `test_lock_fit.py`,
    `test_checks_before_reading.py`, `test_docstring_claims.py`, `test_fiona_import.py`,
    `test_lock_canonical.py`, `test_part_leftovers.py`;
  - the pinned copies that replace files: `test_refusals_not_tracebacks.py` (M2-07's,
    whole, plus the new cases), `test_buildings_read.py` (M2-04's pinned file),
    `test_buildings_reader.py` (M2-04's builder's file);
  - the existing tests the new rules change. Measured with design's throwaway, and no
    others: `test_buildings_manifest.py`, `test_terrain_manifest.py`,
    `test_terrain_manifest_source.py`, `test_terrain_refusals.py`, `test_buildings_step.py`.
    Each then expects `lock <x>` or the removed `.part`;
  - your own new tests, named `test_m3_01_*.py` (no other lane uses the prefix).

Not `__main__.py` (the pinned driver patches its `load_datasets` and `write_manifest`
names), `sheets.py`, `world.py`, `config/`, `tests/shared/`, `game/`, `tools/`.

## Depends on

None. First in lane A; M3-03 follows and starts from this brief's landing.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-01/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Before the fix, the pinned files fail for their findings' reasons; record the count per
      file. Design measured on the unmodified code: `test_lock_fit.py` 12,
      `test_refusals_not_tracebacks.py` 9, `test_docstring_claims.py` 2,
      `test_part_leftovers.py` 2, `test_fiona_import.py` 1. The others pass today: they close
      test gaps.
      - does NOT prove: that the fixes are minimal.
- [ ] Mutations, each failing a named pinned test, recorded:
      - the fit checked after the block, or after the inputs;
      - the terrain step's fit not exact (an extra tile accepted);
      - the terrain inputs check moved after the tile loop;
      - `entry_sha256` without `sort_keys`, or with `ensure_ascii=True`;
      - `read_sheet`'s `ring[:3]` kept as the whole ring;
      - fiona imported at module level.
      - does NOT prove: a real republish (none exists).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Changing an output byte (the fixtures, design's expected values), the lock, a config or a
pinned file; the export presets (M3-08); `game/` and `tools/` (M3-02).

## Findings (executor writes)

1. **Pinned copies and the counts before the fix.** All ten files are in place and `cmp`
   identical to `docs/briefs/pinning/M3-01/` (checked before the gate). On the unmodified
   code they failed as design measured: `test_lock_fit.py` 12, `test_refusals_not_tracebacks.py`
   9, `test_docstring_claims.py` 2, `test_part_leftovers.py` 2, `test_fiona_import.py` 1;
   `test_checks_before_reading.py` (6), `test_lock_canonical.py` (3), `test_buildings_read.py`
   (4) and `test_buildings_reader.py` (7) pass on it, as the brief says.

2. **What changed, by decision.**
   - 1: `lock.fit_problem(lock, datasets, world, area, dataset)`, one table (`_FITS`, rows of
     `_Fit(keys, files, ids, command)`) for `swissalti3d` and `swissbuildings3d`; M3-03 adds
     rows. `download_terrain`, `download_buildings`, `build_terrain`, `build_buildings`,
     `built_terrain_block` and `built_buildings_block` call it; the fit is exact for both
     datasets. The order in all four step/manifest paths: world, fit, inputs, then the rest.
     `download.py` imports it inside the two download functions, because `lock.py` imports
     `download.py` at module level. `_lock_problem`, `_locked_tiles`, `_locked_sheets` and the
     now unused `terrain.LOCK_COMMAND` are gone (decision 10 does not keep them);
     `buildings._check_source` lost the lock-fit branches the fit made unreachable.
   - 2: no code change; the pinned test passes on the unmodified order, and the mutation below
     moves the inputs check and fails it.
   - 3: the two test docstrings now name `test_computed_for_terrain.py` and
     `test_computed_for_buildings`; `manifest.py`'s docstring names the box, columns and rows
     and the new order.
   - 4: `DatasetsConfigError` for a `swissalti3d` entry whose `resolution_m` is not a positive
     finite int or float (`RESOLUTION_DATASETS` in `datasets.py` is M3-03's extension point).
   - 5: `terrain._write_files` and `buildings.write_buildings` remove `*.part` in their own
     folder after writing (files only; a directory named `*.part` is left); a refusal removes
     nothing. Each step says how many it removed, only when it removed any.
   - 6, 7, 8: tests only, as pinned. 9: `read_sheet`'s fiona import moved inside the function.

3. **Two reversible choices inside the scope** (BUILD.md §The orchestrator 5; for the board's
   *Decisions for design to audit*):
   - *The steps check `computed_for.inputs_sha256` before reading provenance.json*, not after
     it as before (the brief fixes "the fit before provenance" and the order "world, fit,
     inputs, block"; where the inputs sit relative to provenance in the *step* it leaves open).
     Chosen because an adopted lock with a stale download is design's to recompute first, and
     "no download has completed here" cannot help until then. The alternative is to leave the
     inputs check after provenance; undoing it is moving one four-line block in each step
     (`test_m3_01_step_order.py` pins the chosen order, two cases).
   - *`fit_problem` returns the whole refusal* (it names the area and `lock <x>`); each caller
     raises it in its own error class without a prefix, so the step, `download` and `manifest`
     say the same words. The alternative is a short reason that each caller dresses.

4. **Existing tests changed**, the five files the brief names and no others, each to expect
   `lock <x>` or the removed `.part`:
   - `test_buildings_manifest.py`: a datasets config with another collection or edition, a lock
     with an extra or another sheet, another edition, or no buildings entry now name
     `lock buildings` (`_refused` takes the command); the source's attribution, collection,
     edition and sheet are edited in the block instead, so those branches keep their cases; the
     sheet-order test needs a lock pinning two sheets, which now fits only an area that needs
     two (the fixture's box widened west to E 2650500, the block's box and world hash edited to
     match).
   - `test_buildings_step.py`: the earlier build's `.part` is removed, with its message.
   - `test_terrain_manifest.py`, `test_terrain_refusals.py`: another edition or resolution in the
     datasets config names `lock terrain`; the block's own edition and resolution stay covered
     by `test_terrain_manifest_source.py`'s source edits.
   - `test_terrain_manifest_source.py`: another collection names `lock terrain`, another
     attribution still the rebuild (`_refused` takes the command).

5. **New tests** (`test_m3_01_*`): `fit_problem.py` (33: every branch, both datasets, one
   command per refusal, a lock that is no lock), `step_order.py` (7: both steps check the fit
   and the inputs before provenance.json, positive controls reach the download; `manifest` over
   built buildings without the dataset in the config names the rebuild, where evaluating the
   lock's entry first would have raised a KeyError: found while editing, not a shipped defect),
   `part_and_resolution.py` (22: a refusal keeps `.part`, the progress line, a directory named
   `.part`, `write_terrain`, the loader's edges: NaN, infinity, a boolean, a list, null).

6. **Mutations**, each applied alone, the named test failed, restored with `git apply -R` of
   its saved diff (the tree was clean after each). Harm in every row: a wrong lock answered by a
   command that cannot help, or a step that reads or builds before it has the right to.
   | mutation | failed |
   |---|---|
   | `built_terrain_block`: inputs before the fit | `test_lock_fit.py` 6 (terrain and manifest) |
   | `built_terrain_block`: fit after the block | `test_lock_fit.py` 6 |
   | `built_buildings_block`: inputs before the fit | `test_lock_fit.py` 5 |
   | `built_buildings_block`: fit after the block | `test_lock_fit.py` 5 |
   | `build_terrain`: fit after the inputs | `test_lock_fit.py` 6 |
   | fit not exact (extra tile or sheet accepted) | `test_lock_fit.py` 3, `test_download_before_fetching.py` 2, `test_m3_01_fit_problem.py` 2 |
   | `build_terrain`: inputs check after the tile loop | `test_checks_before_reading.py::test_republished_and_relocked_inputs_are_refused_before_any_tile_is_read` |
   | `build_buildings`: inputs check after the sheet loop | `test_checks_before_reading.py::test_republished_and_relocked_sheets_are_refused_before_any_sheet_is_read` |
   | steps read provenance.json before the fit | `test_m3_01_step_order.py` 2 per step |
   | `entry_sha256` without `sort_keys` / with `ensure_ascii=True` | `test_lock_canonical.py::test_an_entry_s_sha256_is_that_of_its_canonical_text_whatever_its_key_order` (both) |
   | `write_lock` without `sort_keys` / with `ensure_ascii=True` | `test_lock_canonical.py::test_the_lock_file_is_sorted_utf_8_with_two_space_indent_and_a_final_lf` (both) |
   | `read_sheet` keeps the ring's closing point (`ring[:3]` as `ring`), or drops the first point | `test_buildings_read.py::test_a_synthetic_sheet_reads_its_triangles` and `test_buildings_reader.py::test_features_come_in_reading_order_with_their_attributes` (both) |
   | fiona imported at module level | `test_fiona_import.py` |
   | terrain step leaves its `.part` files | `test_part_leftovers.py::test_the_terrain_step_removes_part_files_from_its_folder`, `test_m3_01_part_and_resolution.py` 1 |
   | buildings step leaves its `.part` files | `test_part_leftovers.py::test_the_buildings_step_removes_part_files_from_its_folder`, `test_buildings_step.py` 1 |
   | terrain step cleans the other step's folder | `test_part_leftovers.py::test_the_terrain_step_removes_part_files_from_its_folder` |
   | loader accepts a boolean | `test_refusals_not_tracebacks.py::test_the_datasets_loader_refuses_swissalti3d_without_a_resolution[a-boolean]`, `test_m3_01_part_and_resolution.py` 1 |
   | loader has no `resolution_m` rule | `test_refusals_not_tracebacks.py` 9 |

   does NOT prove: that the pinned tests are the only way to see these defects; mutation shows
   a gate is sensitive to its own subject (lesson 4).

7. **Gate.** `tools/gate.sh > gate.log && git commit`: exit 0 in 1 min 49 s on this tree;
   pytest 849 passed, 4 network tests deselected (787 before the three new files; 743 at the
   M2 close); GUT 23 scripts, 110 tests, 2800 asserts, `GUT version:  9.6.1`; ruff check and
   format, gdlint and gdformat clean. No output byte changed: `manifest`'s step is in the gate
   and the fixtures' expected values are untouched (`git diff` of `tests/shared/` and `config/`
   is empty).

8. **For M3-03 (the next brief in this lane).** `fit_problem`'s table fits `swissimage` with
   one row (keys collection, edition, resolution_m; files `tiles`; `download.area_tiles`
   under another lock command). `swisssurface3d` needs the per-tile `edition` checked against
   `editions` and `swisstlm3d` has no files object (its entry holds `file` and `sha256`), so
   `_Fit` gets two more fields or the function a branch for them; `fit_problem` reads
   `config[key]` for each key, so `editions` is a list compared whole. The loader's
   `RESOLUTION_DATASETS` takes `swissimage` and `swisssurface3d`, after M3-03's
   edition/editions rule, which `load_datasets` must run first.

9. **What is not proven.** That the committed lock is swisstopo's (the network tests); that
   `manifest` is right for a real run (`3ca0445c…` is wave 2's); anything about the
   export's `.part` filter (M3-08).
