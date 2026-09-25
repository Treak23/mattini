# Brief: M1-01 — Pinned inputs, byte-pinned outputs (the M0 carry-over, pipeline half)
Status: DONE (25972d4)

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

Every input the pipeline uses is pinned in the repository, and what it writes is pinned to
exact bytes, so two machines on two days provably build the same world:
`config/datasets.lock.json` pins the SHA-256 of the six village tiles and is written only by
a new `python -m mattini lock terrain`; `download terrain` refuses anything the lock does not
vouch for before it fetches or deletes a byte; `provenance.json` exists only after a run
that completed; the manifest and `provenance.json` are pinned to golden bytes and exact key
sets; the origin census reads every file git would commit; a Windows checkout gets the same
bytes as Linux; and the files the repository depends on are tracked, not merely not ignored.

## Read first, in order

1. `CLAUDE.md` — Hard Rules 2, 4 and 5.
2. `docs/history/ARCS.md` §M0: D5, D7, D9, D10 and the carry-over table rows C-01, C-02,
   C-04, G-06, G-08.
3. `docs/reviews/M0-R1-coordinates.md` (C-01, C-02, C-04) and `docs/reviews/M0-R1-gate.md`
   (G-06, G-08): each finding's proof and harm.
4. `docs/SPEC.md` §5 (the tile lock) and §9.
5. `pipeline/mattini/download.py` and its tests; brief M0-04 and its Findings.
6. The pinning tests, `docs/briefs/pinning/M1-01/pipeline/tests/`:
   `fake_swisstopo.py` (a shared fake, not a test), `test_tile_lock.py`,
   `test_provenance_lifecycle.py`, `test_golden_outputs.py`, `test_origin_census.py`,
   `test_line_endings.py`, `test_repo_tracked.py`.

## Decisions already made

- **The lock** (D7; form chosen at M1 planning, SPEC §5 and §13 row 20):
  `config/datasets.lock.json`, structure exactly as `test_build_lock_records_the_published_checksums`
  shows; written with sorted keys, 2-space indent, UTF-8, LF and a final newline. API:
  `mattini.lock.LOCK_PATH` (`config/datasets.lock.json`), `LockError` (a `ValueError` whose
  message names the file), `build_lock(world, datasets, fetch_json)` (reads the STAC items of
  the village tiles at the pinned edition and resolution, fetches no file),
  `write_lock(lock, path=LOCK_PATH)`, `load_lock(path=LOCK_PATH)` (validates: schema 1,
  `datasets`, each tile's `file` a plain name and `sha256` 64 lower-case hex digits).
- **`python -m mattini lock terrain`** writes the lock through urllib and prints its path,
  like `manifest`. You run it once, against the live STAC API, and commit the file: its
  values must equal the six pinned in `test_tile_lock.py` (M0-04 Findings 4, re-read by
  design on 2026-09-25). If swisstopo has republished a tile since, that is a BLOCKED
  question, not a new pin.
- **`download_terrain(world, datasets, out_root, fetch_json, fetch_file, *, lock)`**:
  1. the lock must be for the same collection, edition and resolution and list every tile
     of the area, else `DownloadError` naming the lock and `python -m mattini lock terrain`;
  2. it reads every STAC item and compares the published asset name and SHA-256 with the
     lock before any file is fetched or deleted. A difference is a `DownloadError` naming the
     tile, both SHA-256 values and `python -m mattini lock terrain`;
  3. then it verifies or fetches the files as M0-04 does.
  `download terrain` on the command line loads the committed lock; a missing or malformed
  lock is an error naming the file and the command.
- **`provenance.json`** is removed before the download's first change on disk (an unlink or
  a file fetch), so it exists only after a completed run; a run that fails before any
  change leaves the old one byte-identical (D9, G-06). Its format is unchanged (M0-04
  Findings 8, kept by D8).
- **Goldens** (C-01): the manifest for `tests/shared/terrain_fixture/world.json` and
  `provenance.json` for the fake server, pinned by SHA-256 and key sets in
  `test_golden_outputs.py`. M1-03 changes the manifest golden on purpose.
- **The census** (C-02): `test_origin_census.py` as pinned; the M0-02 census in the live
  `test_world.py` stays.
- **`.gitattributes`** (C-04, D5), exactly:

  ```
  # Line endings: LF in every checkout, whatever core.autocrlf says, so file bytes and
  # their SHA-256 are the same on every machine (docs/history/ARCS.md §M0, D5).
  * text=auto eol=lf

  # Binary formats, never converted even when their bytes look like text.
  *.f32 binary
  *.jpg binary
  *.png binary
  *.webp binary
  *.exr binary
  *.tif binary
  *.zip binary
  *.so binary
  *.dll binary
  *.res binary
  *.glb binary
  ```

  After adding it, `git add --renormalize .` must stage nothing else (measured at the M0
  close: the index holds no CRLF file).
- **Tracked files** (G-08): `test_repo_tracked.py` as pinned. It reads the index: stage new
  files before running the gate.
- Python standard library only; no new dependencies in this brief.

## Scope — files you may touch

`pipeline/mattini/lock.py` (new) · `pipeline/mattini/download.py` ·
`pipeline/mattini/__main__.py` (the `lock terrain` command; `download terrain` loads the
lock) · `pipeline/tests/` (the pinned copies, your own tests, and the live copies of the M0
download tests, which must pass a lock now) · `config/datasets.lock.json` (written by the
command, committed) · `.gitattributes` (new)

## Depends on

None. Shares no file with M1-02: the two may run at once.

## Done when (gates)

- [ ] The seven pinned files are in place and unchanged (`cmp` each against
      `docs/briefs/pinning/M1-01/pipeline/tests/`).
      - does NOT prove: that the pinned tests are right (design ran them against a scratch
        implementation, 2026-09-25: 60 passed).
- [ ] `uv run --project pipeline --frozen pytest pipeline/tests` passes without network.
      - does NOT prove: that the live STAC API behaves like the fake (next gate).
- [ ] One real run, recorded in Findings: `python -m mattini lock terrain` writes the lock
      (its `sha256sum`, and `git diff --stat` showing only that file); `download terrain`
      into a fresh `--out` fetches six files and verifies them against the lock; a second
      run fetches nothing and leaves `provenance.json` byte-identical.
      - does NOT prove: what happens when swisstopo republishes a tile (the fake shows it).
- [ ] After adding `.gitattributes`: `git add --renormalize .` then `git status --porcelain`
      lists only `.gitattributes` (record the output).
      - does NOT prove: the owner's Windows checkout (simulated with core.autocrlf=true on
        Linux).
- [ ] Mutation proofs, one per run of the pytest step, each undone with `git apply -R` of its
      saved diff (BUILD.md, Auto mode), each row naming the owner-visible harm:
      (a) skip the lock comparison → `test_a_republished_tile_is_refused_and_not_fetched`
      fails; (b) compare each tile with the lock just before fetching it, interleaved →
      `test_the_lock_is_checked_before_any_file_is_fetched` fails; (c) never remove
      `provenance.json` → `test_a_failed_rerun_after_a_damaged_file_leaves_no_provenance`
      fails; (d) remove it at the start of every run → the two keep-the-old-one tests fail;
      (e) `"generated_on": date.today().isoformat()` in the manifest → the manifest golden
      fails; (f) `ORIGIN_E = 2.623e6` in `pipeline/mattini/download.py` → the census fails;
      (g) delete `* text=auto eol=lf` → `test_a_crlf_configured_clone_gets_the_same_bytes`
      fails; (h) `git rm --cached tools/gate.sh` (restore with `git reset tools/gate.sh`) →
      `test_is_tracked[tools/gate.sh]` fails.
      - does NOT prove: that no other mutation survives; a census proves text only
        (lesson 5).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`; `git status` shows nothing
      under `data/`.
      - does NOT prove: that anything renders (nothing is drawn here).

## Forbidden

Committing anything from `data/`; new dependencies; asking the API for "the latest";
editing `config/world.json`, `config/datasets.json`, `config/terrain.json` or `tests/shared/`
(design data); writing `config/datasets.lock.json` by hand; changing a pinned copy.

## Findings (executor writes)

Executor session, 2026-09-25. Code commit `25972d4`.

1. **Pinned copies:** `cmp` of each of the seven files in
   `docs/briefs/pinning/M1-01/pipeline/tests/` against `pipeline/tests/` exits 0.
2. **pytest without network:** 275 passed, 3 deselected (the opt-in network tests), also
   with `HTTPS_PROXY`/`HTTP_PROXY` pointed at `127.0.0.1:9` and `UV_OFFLINE=1`. The pinned
   files give 59 tests (design's 60 includes `test_is_tracked[…terrain.gdextension]`,
   which appears once M1-04 vendors Terrain3D). Mine: 7 in `test_download_cli.py` (`lock
   terrain` writes the lock from the STAC items with no file request, and writes nothing
   when an item is missing; `download terrain` with a missing, empty, `{}` or tile-less lock
   exits 1 naming the file and the command before any request; a republished tile exits 1
   naming both SHA-256 values with no file request). Opt-in, `pytest -m network`: 3 passed
   in 10.5 s, including a new `test_the_committed_lock_is_what_swisstopo_publishes`.
3. **Real run, cloud container:**
   - `python -m mattini lock terrain`: exit 0 in 5.1 s, printed the lock's path.
     `sha256sum config/datasets.lock.json` =
     `c418a4136edb4a4d7d3078030b9865478b68679a2c3c7d1aecbb37e44982ef01`; `git diff --stat --
     config/` listed only `config/datasets.lock.json | 36 +++`. Its six SHA-256 equal the
     six pinned in `test_tile_lock.py`, so no tile was republished. Re-run on the committed
     tree: `git status --porcelain` empty (the same bytes).
   - `download terrain --out data/raw` (fresh, no `data/` before): exit 0, 5.1 s,
     `6 tiles verified, 6 fetches`; each file's `sha256sum` equals its lock entry;
     `provenance.json` = `28523b17e7cb733f9ea09387a6ce261f9692f279466d6d97ab19636d6c7a559f`,
     the same bytes as M0-04's run (M0-04 Findings 4).
   - Second run: exit 0, 2.2 s, `6 tiles verified, 0 fetches`; `sha256sum` of all seven
     files before and after identical (`cmp` of the two listings). `git status` shows
     nothing under `data/`.
4. **`.gitattributes` renormalize**, measured in a clean worktree of `1419199` (the working
   tree held this brief's code changes, which `--renormalize` would stage): with the file
   copied in, `git add --renormalize .` then `git status --porcelain` printed only
   `?? .gitattributes`. `git ls-files --eol`: 342 `i/lf`, 26 `i/-text`, 6 `i/none`, no
   `i/crlf`.
5. **Mutation proofs**, one per run of `uv run --project pipeline --frozen pytest
   pipeline/tests`, each applied from a saved diff and undone with `git apply -R` (then
   `cmp` against the saved original: identical); (h) undone with `git reset
   tools/gate.sh`. Unmutated: 275 passed.

   | Run | Mutation | Failing tests | Owner-visible harm |
   |---|---|---|---|
   | a | the lock comparison skipped (`if False:`) | 3: pinned `test_a_republished_tile_is_refused_and_not_fetched`, `test_the_lock_is_checked_before_any_file_is_fetched`; mine `test_download_refuses_a_republished_tile_before_fetching` | a tile swisstopo republished is adopted silently: two machines build different worlds from one config |
   | b | the comparison moved into the fetch loop, just before each tile | 3: the same three | five tiles fetched (and damaged files deleted) before the refusal: a half-changed download folder |
   | c | `provenance.json` never removed | 1: `test_a_failed_rerun_after_a_damaged_file_leaves_no_provenance` | a provenance listing six verified tiles while five are on disk; the terrain step would trust it |
   | d | `provenance.json` removed at the start of every run | 2: `test_a_run_that_fails_before_any_change_keeps_the_old_provenance`, `test_verified_tiles_are_no_change_on_disk` | an offline re-run throws away the record of a complete, valid download |
   | e | `"generated_on": date.today().isoformat()` in the manifest | 1: `test_manifest_bytes_for_a_fixed_world_config` (the live M0 manifest tests all passed: lesson 33) | a manifest that differs by day (Hard Rule 5) |
   | f | `ORIGIN_E = 2.623e6` in `download.py` | 1: `test_the_origin_lives_only_in_config` | a second origin outside `config/world.json` (Hard Rule 4) |
   | g | `* text=auto eol=lf` deleted | 2: `test_a_crlf_configured_clone_gets_the_same_bytes`, `test_gitattributes_forces_lf_and_marks_binaries` | on a CRLF-configured Windows clone the gate stops running and the manifest's bytes change |
   | h | `git rm --cached tools/gate.sh` | 1: `test_is_tracked[tools/gate.sh]` | the owner's next clone has no gate |

6. **Choices inside the brief's scope** (reversible):
   - The lock check runs in this order: the resolution is valid, then the lock is for the
     config's collection, edition and resolution and names every tile of the area (extra
     tiles are allowed, for later areas), then every STAC item is read, then every
     published file name and SHA-256 is compared with the lock, and only then is the folder
     created and anything fetched or deleted. Files are verified against the (equal)
     locked SHA-256.
   - `load_lock` also requires exact key sets at every level, tile ids `<digits>-<digits>`,
     a positive finite `resolution_m`, and non-empty `datasets` and `tiles`. `write_lock`
     validates before writing and writes through a `.part` rename. Every `LockError` names
     the file and `python -m mattini lock terrain`.
   - `download.published_assets()` reads the items for both `build_lock` and the download.
     `LOCK_COMMAND` lives in `download.py` (the lock module imports the download module,
     not the reverse).
   - The command line reads `mattini.lock.LOCK_PATH` when it runs, so the CLI tests point
     it at a temporary folder and never touch the committed lock.
   - The live copies of the M0 download tests now pass a lock built from their own fake
     server (in the refusal tests, from an untouched server at the pinned config); the live
     `test_download.py` differs from `docs/briefs/pinning/M0-04/` only by that argument, its
     import and a one-line comment.
