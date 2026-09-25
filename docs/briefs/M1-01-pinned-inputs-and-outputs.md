# Brief: M1-01 — Pinned inputs, byte-pinned outputs (the M0 carry-over, pipeline half)
Status: OPEN

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

