# Brief: M2-03 — The building inputs: sheets, lock and download
Status: BLOCKED

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

`uv run --project pipeline python -m mattini download buildings` fetches the
swissBUILDINGS3D 3.0 map sheets that the village needs, at the pinned edition (2020), and
verifies each against the checksum the committed lock pins. They go into
`data/raw/swissbuildings3d/2020/` with a `provenance.json`, and the guarantees are the
terrain download's (SPEC §5): no "latest", a republished file refused, a file under its
final name only once verified. `python -m mattini lock buildings` writes the lock's
buildings entry from the STAC items and leaves the terrain entry alone, and `lock terrain`
leaves the buildings entry alone. Which sheets are needed follows from the area's box by the
LK25 sheet grid, not from a list anyone types.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 3 and 5.
2. `docs/SPEC.md` §5 (swissBUILDINGS3D, the lock) and §8 *The buildings*: its *Source* and
   *Sheets* paragraphs.
3. `pipeline/mattini/download.py`, `lock.py`, `datasets.py` and `__main__.py` as M2-01
   left them (the area helper of T-06).
4. `pipeline/tests/fake_swisstopo.py`: the fake STAC server the download tests use.
5. The pinning tests, `docs/briefs/pinning/M2-03/pipeline/tests/`.

## Decisions already made

- **Dataset config:** `config/datasets.json` gains `swissbuildings3d`:
  `{"collection": "ch.swisstopo.swissbuildings3d_3_0", "edition": "2020", "attribution":
  "© swisstopo"}`. Design's copy travels with the pinning tests
  (`docs/briefs/pinning/M2-03/config/datasets.json`); the copy step puts it in place.
- **The sheet grid** (SPEC §8 *Sheets*) lives in `pipeline/mattini/sheets.py`:
  - `SHEET_ID` is the pattern `[0-9]{4}-[1-4][1-4]`;
  - `sheet_box(sheet) -> (e_min, e_max, n_min, n_max)` in whole metres as floats;
  - `sheets_near(box, margin_m=100.0) -> list[str]`: every sheet whose box is within
    `margin_m` of `box` (distance ≤ margin, touching included), sorted as text;
  - a malformed id or a box outside the grid is a `ValueError` naming it.

  The village gives 1328-33, 1328-34, 1348-11, 1348-12, 1348-13, 1348-14. Design
  checked this grid against the STAC items' bounding boxes: all 34 sheets around Zermatt
  of the 2020 edition lie within 7 mm of the grid (the rounding of STAC's degrees).
  Buildings overhang their sheet by up to about 12 m, and three of 2'134 have their centre
  up to 3.6 m outside it, which is why the step reads every sheet within 100 m.
- **The lock** (`config/datasets.lock.json`, still schema 1) holds one entry per dataset.
  `swissalti3d` keeps exactly `collection`, `edition`, `resolution_m`, `tiles`.
  `swissbuildings3d` is exactly `{"collection", "edition", "sheets": {"<sheet>": {"file",
  "sha256"}}}`, with every sheet id matching `SHEET_ID`. `validate_lock` knows both
  shapes and refuses an unknown dataset. The API (the pinning tests use it):
  - `lock.terrain_entry(world, datasets, fetch_json, *, area)` and
    `lock.buildings_entry(world, datasets, fetch_json, *, area)` build one entry each,
    from STAC only;
  - `lock.with_entry(lock_or_none, dataset, entry)` returns a new lock with that entry
    set and every other entry kept;
  - `build_lock(world, datasets, fetch_json, *, area)` stays as M2-01 left it (a lock
    with the terrain entry only), for its tests.

  `python -m mattini lock terrain|buildings` writes `with_entry(the committed lock, or
  None when there is none, …)`: that dataset's entry only.
  The committed lock gains the six sheets, written by the command against the live STAC
  API, and the builder checks them against design's values:

  | Sheet | File | SHA-256 | Bytes |
  |---|---|---|---|
  | 1328-33 | `swissbuildings3d_3_0_2020_1328-33_2056_5728.gdb.zip` | `72b2502856d315b9f265f8279a9491cfa3f45065a42cc492824fd9731d7c4292` | 45'668 |
  | 1328-34 | `swissbuildings3d_3_0_2020_1328-34_2056_5728.gdb.zip` | `0af21388ab8e665665ed61218fce7d9a276d260319ab77661ab652d039f5d4a9` | 391'181 |
  | 1348-11 | `swissbuildings3d_3_0_2020_1348-11_2056_5728.gdb.zip` | `14d4aea6a24ab8ae5fd9f287f07ffbac93a28bcab342f06a3e1a841aa5233ab4` | 9'117'186 |
  | 1348-12 | `swissbuildings3d_3_0_2020_1348-12_2056_5728.gdb.zip` | `d7fd32c439a633bae9d87cd94c1b793cdd64152be529344c5220b49fd50250b0` | 2'893'650 |
  | 1348-13 | `swissbuildings3d_3_0_2020_1348-13_2056_5728.gdb.zip` | `d886a6baa4697631e49fd2281a3f011bbe034b01ea79708c9d46b9dca9730a16` | 1'437'969 |
  | 1348-14 | `swissbuildings3d_3_0_2020_1348-14_2056_5728.gdb.zip` | `32c47a7da978832ba56c3e2709d692bf96dc1e386016c80dfda09f9f093db1e2` | 324'725 |

  (Read from the live STAC items on 2026-09-25 and equal to the SHA-256 of the files
  design downloaded.)
- **The download** (`python -m mattini download buildings [--out data/raw]`;
  `download.download_buildings(world, datasets, out_root, fetch_json, fetch_file, *, lock,
  area)`, returning the provenance entries), following
  the terrain download's rules:
  - it reads all the STAC items and compares every asset's file name and SHA-256 with the
    lock before anything on disk changes;
  - a file downloads to `.part`, is verified, then takes its name; one retry;
  - an existing file that matches is not fetched again;
  - `provenance.json` is removed before the first change and written at the end, holding
    `{"attribution", "collection", "dataset": "swissbuildings3d", "edition", "schema": 1,
    "sheets": [{"file", "item", "sha256", "sheet", "size_bytes", "url"}]}` in sheet order,
    with sorted keys, LF and no times.

  The item id is `swissbuildings3d_3_0_<edition>_<sheet>`; the asset is the one whose key
  ends `_2056_5728.gdb.zip`. Errors are `DownloadError`s naming the sheet and URL. A
  missing item (a sheet with no data in that edition) is refused, naming the sheet and the
  item.
- **The area:** the one area of `config/terrain.json` (T-06's helper); the margin is 100 m
  (buildings overhang their sheet by up to about 12 m, measured at M2 planning).
- **No reading of the zips here:** M2-04 opens them.

## Scope: files you may touch

`pipeline/mattini/sheets.py` (new) · `pipeline/mattini/download.py` ·
`pipeline/mattini/lock.py` · `pipeline/mattini/datasets.py` (only if a pinned test needs
it) · `pipeline/mattini/__main__.py` · `pipeline/tests/` · `config/datasets.lock.json`
(written by the command only) · `config/datasets.json` (the pinned copy, never edited).

## Depends on

M2-01 (the area helper, the lock and download modules it changes).

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical (`cmp`).
      - does NOT prove: that the pinned tests are the right tests.
      - NOT MET, BLOCKED (`docs/briefs/BLOCKED.md`, Findings 2): `config/datasets.json` and
        `pipeline/tests/test_buildings_download.py` are in place, and `cmp` exits 0 for both
        before each commit. `pipeline/tests/test_sheets.py` is not in the tree: its
        byte-identical copy fails the gate's `ruff check` (I001).
- [x] `python -m mattini lock buildings` against the live STAC writes the six sheets with
      design's SHA-256s, and `git diff config/datasets.lock.json` shows only the new entry;
      then `download buildings --out <scratch>` fetches six files, and a second run
      fetches none (Findings: both runs' output).
      - does NOT prove: that the files hold what M2-04 expects (it reads them).
      - Evidence, Findings 3: the six sheets equal design's table (and the pinned test
        `test_the_committed_lock_pins_the_six_measured_sheets` checks them). The diff is
        30 added lines, all in the new entry. Run 1: `6 sheets verified, 6 fetches`,
        and the six SHA-256s and sizes equal the table. Run 2: `6 sheets verified,
        0 fetches`, `provenance.json` byte-identical (`8a3da3f2…`).
- [x] Mutation: the lock's SHA-256 of one sheet changed by one digit, and `download
      buildings` refuses before fetching or deleting anything (the fake server's test).
      - does NOT prove: anything about a real republished sheet (none exists to try).
      - Evidence, Findings 4, run M2. The committed lock's 1348-12 digest ended `…250b1`
        instead of `…250b0`. The real `download buildings` exited 1 naming the sheet,
        both digests and `python -m mattini lock buildings`. The scratch folder's listing
        (with mtimes) and every SHA-256 were identical before and after. The full gate
        failed at pytest in `test_the_committed_lock_pins_the_six_measured_sheets`. The
        fake-server tests are the pinned
        `test_a_republished_sheet_is_refused_before_anything_changes` and my
        `test_a_sheet_whose_lock_sha256_differs_by_one_digit_is_refused_before_anything`;
        both fail when the comparison is removed (run M1).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the buildings are placed right (M2-04, M2-05).
      - NOT MET for the brief's full tree (BLOCKED): with the pinned `test_sheets.py` in
        place, it fails at `ruff check`. Without that file, the gate is green, and it
        was chained to the commit of `4035f08` (Findings 1).

## Forbidden

Reading or unpacking the sheets (M2-04); a new dependency; hard-coding a sheet list; any
change to the terrain's download behaviour beyond sharing code.

## Findings (executor writes)

Executor agent of the one M2 session, 2026-09-25, in its own worktree and branch
(`worktree-wf_6d184921-dea-1`, the owner's run mode: nothing synced or pushed). Base
`ce23118`; code commit `4035f08`. **Status BLOCKED** on one question (2), the only gate
not met. Everything else is done and committed.

1. **Standard gate** (`tools/gate.sh > gate-M2-03.log 2>&1 && git commit`), exit 0 for
   `4035f08` on the tree without the live `test_sheets.py`: `uv lock --check`, pytest
   **485 passed**, 4 deselected (the network tests, one more than M2-01's three), ruff
   check and format, `manifest`, Godot 4.6.3 import and parse check, GUT 16 scripts,
   76 tests, 1726 asserts, `---- All tests passed! ----`, gdlint, gdformat,
   `== gate: all steps passed`. The 73 pytest warnings are rasterio's, as in M2-01.
2. **The blocker.** With all three pinned files in place (`cmp` equal), the gate ran
   pytest **507 passed** (485 + the pinned file's 22), then `== gate: FAILED at step: ruff
   check`: `I001 [*] Import block is un-sorted or un-formatted --> pipeline/tests/test_sheets.py:21:1`.
   ruff 0.16.8's default rules include import sorting. In `pipeline/tests/`, `mattini`
   counts as the project's own package, so it needs a blank line after `import pytest`.
   In its pinned place it counts as third-party, and the file passes there. Run from
   `docs/` with `--config pipeline/pyproject.toml`, ruff flags the other pinned file
   instead, so linting the pinned tree does not predict the live one either way. A
   scratch copy of the live layout (the pipeline's `pyproject.toml` and `mattini/`, every
   live test, M2-04's four pinned pipeline tests) gives exactly this one error: M2-04's
   are clean. The live copy is left out of `4035f08`, and its 22 tests pass run from the
   pinned folder (`pytest docs/briefs/pinning/M2-03/pipeline/tests/test_sheets.py`:
   22 passed). The question is in `docs/briefs/BLOCKED.md`.
3. **Real runs** against the live STAC API, raw files in the scratch root
   `…/scratchpad/raw` next to the terrain's tiles, nothing downloaded committed:
   - `python -m mattini lock buildings`: exit 0, stdout the lock path. `git diff
     config/datasets.lock.json`: 30 added lines, all inside the new `swissbuildings3d`
     entry, and the `swissalti3d` entry untouched. The six sheets, their file names and
     SHA-256s equal design's table.
   - `download buildings --out …/raw`, run 1: six `fetching https://data.geo.admin.ch/ch.swisstopo.swissbuildings3d_3_0/swissbuildings3d_3_0_2020_<sheet>/…gdb.zip`
     lines, `6 sheets verified, 6 fetches`, stdout `…/raw/swissbuildings3d/2020/provenance.json`.
     `sha256sum` of the six zips equals the table, and so do their sizes (45'668,
     391'181, 9'117'186, 2'893'650, 1'437'969, 324'725 bytes; 14'210'379 in all).
     `provenance.json` is `8a3da3f2…`, 2'770 bytes, the brief's keys in sheet order.
   - Run 2: `6 sheets verified, 0 fetches`, `provenance.json` still `8a3da3f2…`.
   - `python -m mattini lock terrain` afterwards: the lock stays byte-identical
     (`8984f784…` before and after), buildings entry included.
   - `pytest -m network` (4 tests, one of them new, one updated): 4 passed in 7.88 s.
     They check that the committed lock's two entries each equal what swisstopo
     publishes today, and that the six village items each hold one `.gdb.zip`.
   - The live items hold two assets each: `…_2056_5728.dwg.zip`
     (`application/x.dwg+zip`) and `…_2056_5728.gdb.zip` (`application/x.filegdb+zip`),
     as the fake models. Their `updated` time is 2025-01-28 (1348-11 at 02:49, 1328-33
     at 02:48), so they were republished inside the 2020 edition once already; the files
     still equal design's reading.
4. **Mutation proofs.** For each one I saved a patch, applied it, ran the full gate, undid
   it with `git apply -R`, and checked that `git diff` against the index was empty.
   Unmutated: 485 passed.

   | Run | Mutation | What failed | Owner-visible harm |
   |---|---|---|---|
   | M1 | `download_buildings`' comparison with the lock skipped (`if False and …`) | pytest, 2 failed: the pinned `test_a_republished_sheet_is_refused_before_anything_changes` (`DID NOT RAISE DownloadError`) and my `test_a_sheet_whose_lock_sha256_differs_by_one_digit_is_refused_before_anything` (`assert (0, '…provenance.json\n') == (1, '')`) | a sheet swisstopo republishes is fetched and adopted with no one deciding it: other buildings from the same commit (Hard Rule 5) |
   | M2 | the brief's: the committed lock's 1348-12 SHA-256 changed by one digit (`…250b0` to `…250b1`) | the real `download buildings` exited 1: `sheet 1348-12 of area 'village': swisstopo now publishes … with SHA-256 d7fd…250b0, the lock pins … with SHA-256 d7fd…250b1; nothing was fetched. … `python -m mattini lock buildings`, then commit the lock`. The folder's `ls -l --time-style=full-iso` and every `sha256sum` were identical before and after (`cmp`). The gate failed at pytest: `test_the_committed_lock_pins_the_six_measured_sheets` (pinned) | a lock that no longer pins what swisstopo serves would go unnoticed; here it stops the download before anything on disk changes |
   | M3 | `lock <dataset>` writes `with_entry(None, …)`, dropping the other entry | 2 of mine: `test_lock_buildings_adds_its_entry_and_keeps_the_terrain_s` (`KeyError: 'swissalti3d'`) and `test_a_lock_that_does_not_fit_the_config_is_refused_before_anything[no-entry]`. No pinned test caught it: they test `with_entry` itself, not the command | `lock buildings` silently unpins the terrain; the next `download terrain` refuses, or a later `lock terrain` pins whatever is published that day |
   | M4 | "touching included" broken: `hypot(…) < margin_m` | 3 of mine in `test_sheets_grid.py`; and the pinned file run from its folder: `test_without_a_margin_only_the_sheets_the_area_touches`, `test_the_margin_is_inclusive_to_the_metre` (2 failed, 20 passed) | a sheet exactly 100 m away (or touching, with no margin) left out: buildings overhanging from it missing |
   | M5 | the larger of the two gaps (Chebyshev) instead of the diagonal | mine only: `test_the_distance_across_a_corner_is_the_diagonal` (`'1328-34' not in [...]` failed). The pinned file passes, 22/22 | none today (the village's six sheets are the same either way): a sheet across a corner read or left out by a rule design did not choose (6, first point) |

5. **The brief's decisions as built.**
   - `sheets.py`: `SHEET_ID`, `sheet_box`, `sheets_near(box, margin_m=100.0)` (default
     `DEFAULT_MARGIN_M`). The boxes are computed in integers, then made floats.
     `sheets_near` walks the sixteenths in range, one more on each side, and tests each
     exactly. The village gives the brief's six sheets.
   - `download.area_sheets(world, area)` is `sheets_near(world.area(area))`: no sheet
     list anywhere. `published_sheets` returns `PublishedSheet`s.
     `download_buildings(world, datasets, out_root, fetch_json, fetch_file, *, lock,
     area)` checks the lock's entry (collection, edition, every sheet of the area), then
     compares every published name and SHA-256, and only then creates the folder.
   - Errors name the sheet and the URL (`sheet 1348-12 of area 'village': …`). A missing
     item is `sheet 1328-33 of area 'village': <item URL>: cannot read the STAC item:
     HTTP Error 404 …`, and the URL ends in the item id.
   - `lock.terrain_entry`, `lock.buildings_entry`, `lock.with_entry(lock_or_none,
     dataset, entry)` (deep copies; neither argument changes), `build_lock` = the terrain
     entry alone, as before. `validate_lock` checks each dataset's exact key set and
     refuses an unknown dataset. It accepts a lock with only the buildings entry (M2-04's
     `tests/shared/buildings_fixture/datasets.lock.json` loads).
   - Code shared with the terrain: `_fetch_into` (the keep, remove or fetch of one file),
     `_fetch_verified` and `_published_asset` (`kind="sheet"`), and `_write_provenance`
     (takes the dict). The terrain's provenance bytes and messages are unchanged: the
     golden, provenance and CLI tests pass untouched.
6. **Choices inside the scope, for design to confirm (reversible):**
   - **Distance is Euclidean** between the two boxes (0 when they touch or overlap), the
     usual meaning of "distance ≤ 100 m". The pinned tests do not decide it (M5), and
     `test_the_distance_across_a_corner_is_the_diagonal` pins my reading.
   - **The grid's extent** is what four-digit ids can name: columns 0–19, rows 0–449
     (E 2'480'000–2'830'000, N −4'098'000–1'302'000). A box not wholly inside it
     (partly outside included) is a ValueError naming the box and the extent, and so is
     a sheet number below 1000. A malformed box (not four finite numbers, or empty) and
     a margin that is not finite and ≥ 0 are ValueErrors naming them. Near the grid's
     edge the margin simply finds no sheet beyond it: none can be named there.
   - **A lock the command cannot read is refused, not replaced.** `lock terrain|buildings`
     reads the committed lock first (`load_lock_or_none`: None when absent). If the file
     exists but is malformed, it exits 1 before asking swisstopo anything, saying the
     command keeps the other entries, so it does not overwrite a lock it cannot read:
     "restore it from git, or delete it and lock every dataset again". Before M2-03,
     `lock terrain` overwrote any file.
   - **The lock's refusal wording names both commands**:
     ``(`python -m mattini lock terrain` and `python -m mattini lock buildings` write the lock)``,
     and "cannot read the lock" (was "writes the tile lock", "cannot read the tile
     lock"). This is the one change the terrain download's output sees, in its refusal
     of a missing or malformed lock. The substring the existing tests pin stays.
   - The item id pattern `swissbuildings3d_3_0_{edition}_{sheet}` is a constant, as the
     brief writes it, not derived from the collection name.
   - `with_entry` does not validate; `write_lock` validates before it writes, so a
     malformed result never reaches the disk.
7. **Tests added** (in scope, `pipeline/tests/`):
   - `test_sheets_grid.py` (31): every id of sheets 1000–1399 round-trips through its
     box; 1348-11's eight neighbours; the diagonal; the grid's corners, and all 144'000
     parts of the grid, each named once; refusals of boxes, margins and ids.
   - `test_buildings_inputs.py` (19): the commands on a fake STAC serving both
     collections. `lock buildings` keeps the terrain entry, `lock terrain` gives the file
     back byte for byte. A lock it cannot read is refused (6 cases). A missing sheet item
     is refused. Download and a rerun with no fetches. Four lock mismatches refused before
     any request. The one-digit change. A damaged file replaced, and a dropped fetch
     retried once. No lock: both commands named. An unknown dataset refused.
     `with_entry` purity.
   - `test_download_network.py`: its whole-lock comparison would fail with two entries.
     It now compares each entry, and a test checks the six sheets' items.
8. **Out-of-scope touches:** none. `docs/briefs/BLOCKED.md` and this brief carry the
   filing.
9. **Follow-up candidates:**
   - Design: add the blank line to the pinned `test_sheets.py`. For later pinning tests,
     lint them in a scratch copy of their live layout, not in place under `docs/`, where
     ruff classifies `mattini` differently.
   - SPEC §5 says the six sheets are "14.1 MB together": measured 14'210'379 bytes
     (14.2 MB, 13.55 MiB). Wording only.
   - The 404 of a missing item reads "cannot read the STAC item: HTTP Error 404: Not
     Found". A dedicated "edition 2020 has no item for this sheet" would need the shared
     helper to tell a 404 from a network error; I left the terrain's wording unchanged.
   - M3 was caught only by this brief's own CLI tests. A pinned test of "`lock
     <dataset>` keeps the other entry" at the command line would bind it for later
     briefs.
