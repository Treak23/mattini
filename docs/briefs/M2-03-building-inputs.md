# Brief: M2-03 — The building inputs: sheets, lock and download
Status: OPEN

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
- [ ] `python -m mattini lock buildings` against the live STAC writes the six sheets with
      design's SHA-256s, and `git diff config/datasets.lock.json` shows only the new entry;
      then `download buildings --out <scratch>` fetches six files, and a second run
      fetches none (Findings: both runs' output).
      - does NOT prove: that the files hold what M2-04 expects (it reads them).
- [ ] Mutation: the lock's SHA-256 of one sheet changed by one digit, and `download
      buildings` refuses before fetching or deleting anything (the fake server's test).
      - does NOT prove: anything about a real republished sheet (none exists to try).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the buildings are placed right (M2-04, M2-05).

## Forbidden

Reading or unpacking the sheets (M2-04); a new dependency; hard-coding a sheet list; any
change to the terrain's download behaviour beyond sharing code.

## Findings (executor writes)
