# Brief: M2-07 — M2 R1's fixes, the pipeline half
Status: DONE (b3ec242)

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

The pipeline findings of review round M2 R1 (`docs/reviews/M2-R1-*.md`) are fixed.

- **Their inputs (P-02, I-01):** the expected values in `config/terrain.json` and
  `config/buildings.json` name the world config and the locked inputs they were computed
  for. A changed world or an adopted republished input then gets a refusal that says so
  and names design's step, where today it blames "this machine or this code" and points to
  a command that cannot succeed.
- **The buildings' box (P-03):** the manifest checks the buildings block's box against
  the world's area.
- **The download (I-02, I-03):** it is proven to refuse before fetching anything, and to
  remove `provenance.json` before a fetch.
- **The sheets (I-04):** the download and the buildings step agree on what a valid lock is.
- **Refusals, not tracebacks (I-05):** the two refusals that end in a traceback now reach
  the owner as `mattini: error:` lines.
- **The grid (I-06):** the sheet grid refuses the ids and boxes it cannot place.
- **Stale chunks (G-06, the pipeline half):** a buildings build removes the chunk files of
  an earlier build that its block no longer lists.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §5 (the lock), §8 (*The terrain grid*, its expected output; *The
   buildings*, its expected output).
3. `docs/reviews/M2-R1-placement.md` P-02, P-03; `docs/reviews/M2-R1-inputs.md` I-01 to
   I-06; `docs/reviews/M2-R1-game.md` G-06.
4. `pipeline/mattini/terrain.py`, `buildings.py`, `download.py`, `lock.py`, `sheets.py`,
   `manifest.py`, `__main__.py`.
5. The pinned files, `docs/briefs/pinning/M2-07/`.

## Decisions already made

- **What an expected value was computed for (P-02, I-01; SPEC §8).**
  - Each area of `config/terrain.json` and of `config/buildings.json` gains
    `computed_for`: exactly `{"inputs_sha256": <hex>, "world_sha256": <hex>}`, 64
    lower-case hex digits each. `world_sha256` is the SHA-256 of `config/world.json`'s
    bytes. `inputs_sha256` is the SHA-256 of the lock's entry for the dataset
    (`swissalti3d` or `swissbuildings3d`) rendered canonically:
    `json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`,
    UTF-8. The area's key sets become exactly
    `{"computed_for", "expected_sha256", "spacing_m"}` for the terrain and
    `{"computed_for", "expected_sha256"}` for the buildings.
  - `terrain`, `buildings`, and `manifest` for a block that is built, compare
    `computed_for` with the world config and the lock before they compare any output.
    Each difference is its own refusal, and none blames the machine or the code:
    - the world: "the expected values in config/<x>.json were computed for the world
      config with SHA-256 <recorded>; config/world.json now has <current>. A changed
      world is a design change: design recomputes the expected values (docs/SPEC.md §8)";
    - the inputs: "… were computed from the <dataset> lock entry with SHA-256
      <recorded>; config/datasets.lock.json's entry now has <current> (a new edition or
      an adopted republished file). Adopting new inputs is a design change: design
      recomputes the expected values (docs/SPEC.md §5, §8)".

    After both match, the existing output comparison and its message stay as they are.
  - The download's republish refusals (terrain and buildings) add: "then design
    recomputes the expected values in config/<x>.json (docs/SPEC.md §8)".
  - Design's values (pinned under `docs/briefs/pinning/M2-07/`: `config/terrain.json`,
    `config/buildings.json`, the three fixtures' configs):

    | Config | world_sha256 | inputs_sha256 |
    |---|---|---|
    | `config/terrain.json` | `d2607d13…299509b` | `025f9045…6f6424d` |
    | `config/buildings.json` | `d2607d13…299509b` | `4000a698…1f81605b` |
    | `tests/shared/terrain_fixture/terrain.json` | `3cab21e5…1e5e75` | `c241206d…f05b9ffa` |
    | `tests/shared/terrain_fixture_nw/terrain.json` | `f5bef481…adb2a40` | `25a8845a…45adc4a` |
    | `tests/shared/buildings_fixture/buildings.json` | `e7cd091d…d5254a` | `352a8f06…70da1e67` |

    The buildings fixture's `terrain.json` exists only to name its area. Its
    `expected_sha256` and `computed_for` are the first terrain fixture's: labelled
    placeholders, since no terrain is ever built in that fixture (P-06). Its vectors'
    `about` says so.
- **The buildings' box (P-03):** `built_buildings_block` compares `lv95_box` with the world
  config's box for the area, as floats, as `terrain._check_shape` does; the refusal names
  the field, both values and `python -m mattini buildings`.
- **The download (I-02, I-03, I-04):**
  - a test starts from an empty folder with a middle sheet republished, and asserts that
    nothing is fetched and `<out>/swissbuildings3d` does not exist;
  - a test completes a download, deletes one file, makes its re-fetch fail twice, and
    asserts `provenance.json` is gone;
  - `download buildings` requires the lock's buildings entry to pin exactly the area's
    sheets, as the step and the manifest do, naming `python -m mattini lock buildings`.
- **Refusals, not tracebacks (I-05):** `lock buildings` and `download buildings` check that
  `config/datasets.json` holds `swissbuildings3d` (a `DatasetsConfigError` or
  `DownloadError` naming the file). The sheet grid's `ValueError` reaches the owner as a
  `DownloadError` or `LockError` naming the area and `config/world.json`. A command-line
  test runs each and finds `mattini: error:` and no `Traceback`.
- **The grid (I-06):**
  - `sheet_box` refuses ids 2000 and above ("not an LK25 sheet mattini's grid places");
  - `sheets_near` refuses a box within the margin of the grid's east edge (E 2'830'000,
    "no sheets east of E 2'830'000 in mattini's grid: design extends it");
  - the docstrings and `test_sheets_grid.py`'s wording say what the grid covers.
- **Stale chunks (G-06):** after writing, `write_buildings` removes every `*.bin` in
  `buildings/` that the new block does not list (the description's own `.json` is kept),
  and says how many it removed on stderr.

## Scope: files you may touch

`pipeline/mattini/*.py` · `pipeline/tests/` · the pinned design data put in place by the
copy step (`config/terrain.json`, `config/buildings.json`,
`tests/shared/terrain_fixture/terrain.json`, `tests/shared/terrain_fixture_nw/terrain.json`,
`tests/shared/buildings_fixture/buildings.json`, `tests/shared/buildings_fixture/terrain.json`,
`tests/shared/buildings_vectors.json`), never edited.

## Depends on

None beyond what is merged. It shares no file with M2-08.

## Done when (gates)

- [x] The pinned copies are in place and byte-identical (`cmp`).
      (Findings 1: all eight, before each commit.)
      - does NOT prove: that the pinned tests are the right tests.
- [x] Mutations (Findings: both runs of each):
      - the world check removed: the shifted-origin test fails;
      - the inputs check removed: the republished-and-relocked test fails;
      - the buildings' box check removed: the shifted-box test fails;
      - the up-front comparison moved into the fetch loop: the empty-folder test fails.
      (Findings 5: runs M1 to M4, each through the full gate, exit 1 at pytest; unmutated
      738 passed.)
      - does NOT prove: anything about a real republish (none exists to try).
- [x] With the real inputs (scratch), `terrain` and `buildings` still write design's
      bytes, and `manifest` accepts them.
      (Findings 4: `b6334c1f…` and the six chunks of config/buildings.json, exit 0 each.)
      - does NOT prove: that it renders.
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      (Findings 2: `eb4247a` and `b3ec242`, each chained on exit 0.)
      - does NOT prove: that the game shows the buildings where the terrain is (M2-08).

## Forbidden

A change to any expected value, to the rules (SPEC §8) or to any fixture's generated bytes.

## Findings (executor writes)

Executor agent of the one M2 session, 2026-09-25, in its own worktree and branch (the
owner's run mode; nothing synced or pushed). The worktree started at `63816ac` (main);
`git merge --ff-only 2f7636a` fast-forwarded it to the brief's commit. Code commits
`eb4247a` (the fixes and their tests) and `b3ec242` (two tests item 6 found missing) on
top of `2f7636a`.

1. **Pinned copies:** `cp -r docs/briefs/pinning/M2-07/. .` put eight files in place:
   `config/terrain.json`, `config/buildings.json`, the three fixtures' configs,
   `tests/shared/buildings_fixture/terrain.json`, `tests/shared/buildings_vectors.json`
   and the new `pipeline/tests/test_expected_inputs.py`. `cmp` against the pinned copies:
   all eight identical, before the code commit and before this one. None was edited. With
   only the pinned files in place (the code unchanged) pytest gave 145 failed, 500 passed,
   26 errors: every config with `computed_for` was refused by the old key-set check.
2. **Standard gate** (`tools/gate.sh > gate-M2-07.log 2>&1 && git commit`), exit 0 for
   `eb4247a` and again for `b3ec242`: `uv lock --check`; pytest **738 passed**, then
   **740 passed**, 4 deselected (the network tests), 92 warnings (rasterio's
   `PendingDeprecationWarning`, from more synthetic GeoTIFFs); ruff check and format;
   `manifest`; Godot 4.6.3 import and parse check; GUT 20 scripts, 98 tests, 2692
   asserts, `---- All tests passed! ----`; gdlint; gdformat. The base `2f7636a` had 662
   pipeline tests (671 collected with the 9 pinned ones in place); 78 are new (9 pinned,
   69 the executor's). The first full gate run failed at `ruff format --check` (two test
   files); formatted, the next passed (88 s). After the mutation runs, three docstrings
   were reworded to say that the inputs check waits for a lock that fits (item 6), and the
   run `eb4247a` is chained on passed.
3. **What was built,** finding by finding:
   - *P-02, I-01:* `terrain.check_computed_for` (the key sets become exactly
     `{computed_for, expected_sha256, spacing_m}` and `{computed_for, expected_sha256}`),
     `lock.entry_sha256` (the canonical form of the brief), and `terrain.world_refusal` /
     `terrain.inputs_refusal`, shared by both steps and both manifest checks, with the
     brief's wording, prefixed `area '<area>': `. The download's two republish refusals
     end `…then commit the lock, then design recomputes the expected values in
     config/<x>.json (docs/SPEC.md §8)`. The output comparisons and their messages are
     unchanged.
   - *P-03:* `built_buildings_block` takes the parsed world (manifest.py passes it) and
     `_check_box` compares `lv95_box` as `_check_shape` does (floats, exact keys), naming
     the field, both boxes and the rebuild command. It replaces the old keys-and-finite
     check.
   - *I-02, I-03:* no code change was needed (the code already compared before fetching
     and unlinked before a fetch); the tests are new (`test_download_before_fetching.py`,
     with the terrain's twins).
   - *I-04:* `download._locked_sheets` refuses `pins the sheets [...], the area needs
     exactly [...]`, naming `python -m mattini lock buildings`, before any STAC read.
   - *I-05:* `download.dataset_of` (a DownloadError naming `config/datasets.json`), used
     by `lock.buildings_entry`, `published_sheets` and `download_buildings`;
     `download.area_sheets` turns the grid's ValueError into a DownloadError naming the
     area and the world config's path. `test_refusals_not_tracebacks.py` runs each
     command in a process of its own (`mattini: error:`, exit 1, no `Traceback`).
   - *I-06:* the grid places the sheets 1000 to 1999 (`_LAST`, 50 rows; N 702'000 to
     1'302'000); `sheet_box` refuses 2000 and above ("not an LK25 sheet mattini's grid
     places"); `sheets_near` refuses a box whose distance to E 2'830'000 is at most the
     margin ("no sheets east of E 2'830'000 in mattini's grid: design extends it").
     Docstrings and `test_sheets_grid.py` say what the grid covers (16'000 parts, not
     144'000).
   - *G-06:* after writing, `write_buildings` removes every other `*.bin` in `buildings/`
     and says `removed <n> chunk file(s) of an earlier build that <area>.json does not
     list from <dir>` through `progress` (stderr on the command line), 0 included.
4. **Real inputs** (the verified scratch download; outputs in
   `scratchpad/m207/generated`, nothing committed; `--frozen`):
   - `terrain`: exit 0; stderr `resampling 4000 × 6000 pixels to a 0.5 m grid`, `the
     heights have the SHA-256 config/terrain.json expects,
     b6334c1fdc992f0576bc59efd51484db2178cbe399ad46512a4bf510abb9411a`, `wrote
     …/terrain/village.f32 (4001 × 6001 vertices)`.
   - `buildings`: exit 0; `sheet 1348-11: 1359 features read, 1236 selected`, `sheet
     1348-12: 440 features read, 250 selected` (the other four: 0 selected), `1486
     buildings in 6 chunks: 92594 vertices, 178910 triangles, 3258048 bytes`, `the 6
     chunks have the SHA-256s config/buildings.json expects`, `removed 0 chunk files of an
     earlier build that village.json does not list from …/buildings`. `sha256sum` of the
     six chunks equals the six values of config/buildings.json.
   - `manifest --out …`: exit 0, manifest `b7c3cfd9…`. A 1 MiB `2622-1095.bin` then put
     beside the chunks (the review's G-06 proof) and `buildings` run again: exit 0,
     `removed 1 chunk file of an earlier build…`, the folder back to the six chunks and
     `village.json`, the manifest the same `b7c3cfd9…`.
   So the real world and lock match design's `computed_for` for both datasets, as the
   pinned test says of the committed files.
5. **Mutation proofs.** Each mutation is a saved diff (`scratchpad/m207/mut-<run>.diff`),
   made on the uncommitted work against a clean copy of the module, run, then undone with
   `git apply -R`; after each, `cmp` of the module against its clean copy and `git
   status` showed only the intended work. M1 to M4 (the brief's) each went through the
   full gate (`scratchpad/m207/gate-M<n>.log`, exit 1 at pytest); M5 to M16 (the
   executor's own) through the pipeline suite only (`pytest-M<n>.log`); M17 and M18,
   after `eb4247a`, through `test_refusals_not_tracebacks.py` only, as diffs against that
   commit. Unmutated: 738 passed (740 after `b3ec242`).

   | Run | Mutation | What failed | Owner-visible harm |
   |---|---|---|---|
   | M1 | the world check removed (`world_refusal` always None) | 10, among them the shifted-origin tests: `test_the_step_names_a_shifted_origin_as_design_s_step` (buildings: `the buildings built here give SHA-256 8f881a4e…, … so this machine or this code produces other buildings`), `test_the_step_names_a_changed_world_as_design_s_step[origin-moved-1-km]` (terrain: `DID NOT RAISE`), `[height-offset]` (`…this machine or this code produces other heights`), both manifest ones (`it was built for the world config…; python -m mattini terrain rebuilds`), and the two pinned world cases | P-02: a changed world.json blamed on the machine or the code, and `manifest` naming a rebuild that cannot succeed |
   | M2 | the inputs check removed (`inputs_refusal` always None) | 7: the republished-and-relocked tests (terrain and buildings step: `…this machine or this code produces other heights` / `…other buildings`; the terrain manifest: `tile 2623-1096 was read with SHA-256 …; python -m mattini terrain rebuilds`; the buildings manifest: `it was built from the sheets …; python -m mattini buildings rebuilds`), `test_a_tile_the_lock_now_pins_differently_is_refused`, the two pinned inputs cases | I-01: an adopted republish blamed on the owner's PC, a dead end |
   | M3 | the buildings' box check removed | 11: the four `test_a_box_shifted_by_a_kilometre_is_refused[east/west/north/south]`, the six `test_a_box_that_is_not_exactly_the_world_s_is_refused[…]`, `test_key_sets_that_are_not_exact_are_refused[box]`, all `DID NOT RAISE BuildingsError` | P-03: a block 1 km off its area in the manifest, which a later consumer would trust |
   | M4 | the up-front comparison moved into the fetch loop (the review's lazy diff, on this code) | `test_a_republished_middle_sheet_is_refused_from_an_empty_folder`: `assert fake.file_fetches == []`, 3 more items (1328-33, 1328-34, 1348-11) | I-02: about 9.5 MB fetched and a folder made before a refusal that says nothing was fetched |
   | M5 | the provenance unlink before fetching a missing file removed | both `test_a_missing_…_that_cannot_be_fetched_leaves_no_provenance` (sheet and tile): `assert not True` | I-03: provenance.json listing a file that is not on disk |
   | M6 | the download's exact-sheets check removed | both `test_a_lock_pinning_more_than_the_area_s_sheets_is_refused[…]`: `DID NOT RAISE` | I-04: a download reporting success, then a step refusing |
   | M7 | the stale chunks kept (`unlink` removed) | `test_a_build_removes_the_chunks_an_earlier_build_left` | G-06: an earlier build's chunks shipped in an export |
   | M8 | ids of 2000 and above placed | the five `test_ids_of_2000_and_above_are_refused_not_placed[…]`: `DID NOT RAISE` | I-06: 2240-11 placed 600 km from its data |
   | M9 | the east edge's margin not refused | 8: the five `test_a_box_within_the_margin_of_the_east_edge_is_refused[…]`; in `test_refusals_not_tracebacks.py`, `lock buildings` reached for the network (the test's guard raised, a traceback), `download buildings` refused for another reason (`the lock pins no checksum for the sheets ['1239-22'] …`) and `buildings` asked for a download (`…provenance.json: no download has completed here`) | I-06: an eastern area's buildings in sheets 2180/2240/2260 left out silently |
   | M10 | a missing dataset a KeyError again (`dataset_of`'s check removed) | the four `test_a_datasets_config_without_the_dataset_is_a_refusal[…]`: `KeyError: 'swissbuildings3d'` / `'swissalti3d'` tracebacks | I-05: a traceback instead of a refusal naming the file |
   | M11 | the grid's ValueError not wrapped | 5 in `test_refusals_not_tracebacks.py`: `ValueError: the box …` tracebacks | I-05, the same |
   | M12 | the terrain manifest's world check call removed (the step's kept) | 3: both `test_manifest_names_a_changed_world_as_design_s_step[…]` and the pinned world case | P-02 at `manifest` only |
   | M13 | the buildings manifest's inputs check call removed | 2: `test_manifest_names_a_relocked_input_as_design_s_step` and the pinned buildings inputs case | I-01 at `manifest` only |
   | M14 | the buildings step's world check call removed | 2: the step's shifted-origin test and `test_a_shifted_origin_is_named_before_changed_inputs` | P-02 at `buildings` only |
   | M15 | the terrain step's inputs check call removed | 1: the terrain step's republished-and-relocked test | I-01 at `terrain` only |
   | M16 | `entry_sha256` rendered like the lock file (`indent=2`) instead of canonically | 134 failed (in 17 files) and 27 errors: every build and manifest over a config whose `computed_for` is design's | every correct build refused as a design change |
   | M17 | `manifest`'s refusal of a built terrain without swissalti3d removed | `test_manifest_over_a_built_terrain_without_swissalti3d_is_a_refusal`: `KeyError: 'swissalti3d'` | a traceback instead of a refusal naming the dataset |
   | M18 | the terrain step reads `datasets["swissalti3d"]` directly | `test_the_terrain_step_without_swissalti3d_is_a_refusal`: the process ends in `KeyError: 'swissalti3d'` | the same, at `terrain` |
6. **Choices inside the brief's scope** (reversible; for design to audit):
   - *Where the checks sit.* The brief places them "before they compare any output". In
     the steps, the world check comes as soon as the world config's bytes are read (before
     the datasets config, provenance.json and the lock are looked at), and the inputs
     check once the lock is shown to fit the datasets config and the area (after
     `_provenance_*` and `_locked_*`, before any tile or sheet is read). In the manifest,
     both come right after the block is found, the inputs check only when the lock's entry
     fits the datasets config (and, for the terrain, pins the area's tiles). The
     alternative, the inputs check first everywhere, would answer a hand-broken lock
     (another edition, a tile key renamed) with "design recomputes" where `lock <x>` can
     restore it; the order chosen keeps every earlier refusal of a lock that does not fit
     the config as it was, and the existing tests of those refusals unchanged.
   - *The files named.* The messages name `config/world.json` and
     `config/datasets.lock.json` as the brief words them (the pinned test requires
     `config/world.json` with a fixture's world), like the existing
     `TERRAIN_CONFIG_NAME`; the grid's refusal names the world config's actual path.
   - *The terrain's twin of I-05.* `lock terrain`, `download terrain` and `terrain` read
     swissalti3d through `dataset_of` too, and `manifest` refuses a built terrain with no
     swissalti3d in the datasets config through `fail()`: the same class (lesson 9),
     inside Scope. `eb4247a` tested only `lock terrain` and `download terrain`; writing
     this item found the step and `manifest` untested, so `b3ec242` adds their tests
     (M17, M18).
   - *The tests that change an input to reach a later check* now record the change as
     design would (`pipeline/tests/computed_for.py`, computed without the pipeline's
     `entry_sha256`, lesson 34): `_relock` in test_terrain_build.py, `_adopt` in
     test_terrain_refusals.py, `_adopting` in test_buildings_step.py, `_adopted` in
     test_buildings_manifest.py, and the four-tile configs. Where such a test was the
     review's own proof (`test_a_tile_the_lock_now_pins_differently_is_refused`,
     `test_terrain_built_for_another_world_is_refused`,
     `test_buildings_built_for_another_world_are_refused`), it now asserts design's step
     first and the rebuild after design has recorded the change.
   - *Stale chunks:* only `*.bin` directly in `buildings/`, never a directory; the
     message comes on every build.
7. **Out-of-scope touches:** none. Code in `pipeline/mattini/` (`buildings.py`,
   `download.py`, `lock.py`, `manifest.py`, `sheets.py`, `terrain.py`), tests in
   `pipeline/tests/`, the pinned design data copied, this brief.
8. **Surprises.**
   - A world change that moves only the origin changes no terrain height, so without the
     world check `terrain` would build it (M1's `DID NOT RAISE`); with it, it is refused as
     a design change, as the brief decides. Likewise a republish that changes the file but
     not the geometry is refused by the inputs check although the output would match.
   - The step's own `.part` rename consumes a leftover `<tile>.bin.part` of a tile it
     writes, but one of a tile it does not write stays in `buildings/` (the brief removes
     `*.bin`); a test keeps one to pin that behaviour.
   - The first shape of the stale-chunk test planted `2650-1149.bin.part`, which the
     build itself overwrote and renamed: measured, then replaced by a tile the build does
     not write.
   - M9 showed the driver's network guard working: with the east-edge refusal removed,
     `lock buildings` asked for sheet 1239-22's item and the guard raised.
9. **Follow-up candidates** (not built; no design authority):
   - SPEC §5 and §8 do not describe `computed_for`, the design step after an adopted
     republish, the grid's extent (1000 to 1999, the east edge), the download's
     exact-sheets rule or the stale-chunk removal (SPEC is outside this Scope).
   - A datasets config whose swissalti3d has no `resolution_m` still ends `download
     terrain` in `KeyError: 'resolution_m'` (measured in scratch): the same class as
     I-05; `load_datasets` requires only collection, edition and attribution.
   - `*.bin.part` (and `terrain/*.part`) leftovers of an interrupted earlier run stay in
     `assets/generated/`; whether the export filter (M2-08) or the steps drop them is open.
   - In `manifest`, a lock that does not fit the datasets config is named only after the
     block's own checks (for example, a datasets config moved to another edition first
     meets "built from edition …; `terrain` rebuilds", and the step then asks for `lock
     terrain`): a longer path than checking the lock's fit first.
