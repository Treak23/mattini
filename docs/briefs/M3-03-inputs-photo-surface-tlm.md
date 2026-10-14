# Brief: M3-03 — The inputs of the photo, the surface model and swissTLM3D
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane A of wave 1, after M3-01 (`docs/briefs/M3-plan.md`).

## Goal

Three new swisstopo datasets reach every machine pinned, checksummed and reproducible,
as the terrain and the buildings do (SPEC §5):
- **SWISSIMAGE 2023,** the aerial photo, 0.1 m;
- **swissSURFACE3D,** the LiDAR surface model, 0.5 m, one edition per tile;
- **swissTLM3D 2026-02,** the national topographic model, one 2.88 GB FileGDB.

`config/datasets.json` names them; `datasets.py` accepts their shapes. New commands:
- `python -m mattini lock photo`, `lock surface`, `lock tlm` pin every file's SHA-256;
- `download photo`, `download surface`, `download tlm` fetch and verify them.

The TLM download resumes a cut transfer. No step reads them yet: M3-04 to M3-07 do, built at
the same time against the layout this brief fixes.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 3, 5); `brain.md` H6, H7, H9, H14, H20.
2. `docs/SPEC.md` §5 (the lock, and the paragraph *The photo, the surface model and
   swissTLM3D*), §13 rows 30, 33.
3. `pipeline/mattini/datasets.py`, `lock.py`, `download.py`, `__main__.py`, as M3-01 left
   them (the same lane, just before this brief), and their tests: `test_tile_lock.py`,
   `test_download*.py`, `fake_swisstopo.py`, `test_buildings_download.py`.
4. The pinned files: `docs/briefs/pinning/M3-03/`.

## Decisions already made

The rules are SPEC §5's paragraph *The photo, the surface model and swissTLM3D*, measured
live by design's agent on 2026-10-14. In short:

1. **Datasets** (the pinned `config/datasets.json`).
   - `swissimage`: `ch.swisstopo.swissimage-dop10`, edition `2023`, `resolution_m` 0.1.
   - `swisssurface3d`: `ch.swisstopo.swisssurface3d-raster`, `editions` `["2021", "2022"]`,
     `resolution_m` 0.5.
   - `swisstlm3d`: `ch.swisstopo.swisstlm3d`, edition `2026-02`.
   - Each carries `© swisstopo`.
   - A dataset has exactly one of `edition` (`YYYY`, or `YYYY-MM` with the month 01 to 12) or
     `editions` (a non-empty list of distinct years in ascending order). Both or neither is
     refused: "exactly one of edition and editions".
   - `resolution_m` is required, a positive number, for `swissimage` and `swisssurface3d`,
     as M3-01 makes it for `swissalti3d`.
2. **STAC items.** Items are `swissimage-dop10_<edition>_<tile>`,
   `swisssurface3d-raster_<year>_<tile>` and `swisstlm3d_<edition>`. The asset is the one whose
   key ends `_<resolution>_2056.tif`, `_<resolution>_2056_5728.tif` or `_2056_5728.gdb.zip`.
   - A surface item answering HTTP 404 is absent. Any other failure is "cannot read the STAC
     item".
   - `file:checksum` comes in upper-case hex; the lock stores lower-case.
3. **Lock entries,** exact key sets:
   - `swissimage` {collection, edition, resolution_m, tiles: {<tile>: {file, sha256}}};
   - `swisssurface3d` {collection, resolution_m, tiles: {<tile>: {edition, file, sha256}}};
   - `swisstlm3d` {collection, edition, file, sha256}.

   `lock surface` reads, for every tile, the item of every year in `editions`. Exactly one
   must exist, else it refuses naming the tile and the years found, and writes nothing. The
   lock commands read STAC only.
4. **The raw layout,** which M3-04 to M3-07 read:
   - `data/raw/swissimage/2023/`;
   - `data/raw/swisssurface3d/2021-2022/` (the editions joined by `-`);
   - `data/raw/swisstlm3d/2026-02/`.

   Each holds the files under swisstopo's names and a `provenance.json`:
   - swissimage: exactly the terrain's keys;
   - swisssurface3d: `editions` in place of `edition`, and each tile's `edition` added;
   - swisstlm3d: flat, exactly {attribution, collection, dataset, edition, file, item, schema,
     sha256, size_bytes, url}.
5. **The downloads.** Each first checks that the lock's entry fits the config, through
   M3-01's `lock.fit_problem`, extended here to `swissimage`, `swisssurface3d` (every tile's
   edition one of `editions`) and `swisstlm3d` (M3-13's manifest calls it for the new
   blocks). It then compares every published name and SHA-256 with the lock **before any
   request for a file and before anything on disk changes**.
   - `download surface` reads only the edition the lock pins per tile; choosing an edition is
     the lock's job.
   - The republish refusal names the configs whose expected values depend on the entry:
     - photo: `config/photo.json`, `config/roofs.json`;
     - surface: `config/trees.json`;
     - tlm: `config/surfaces.json`, `config/trees.json`.

     The terrain's and buildings' existing refusals now name their new dependants too:
     - swissalti3d: `config/terrain.json`, `config/trees.json`;
     - swissbuildings3d: `config/buildings.json`, `config/roofs.json`, `config/trees.json`.

     Update their existing tests' expected text accordingly.
6. **The TLM file** (2'882'823'552 bytes).
   - A verified file already there is kept, with no request to the file host.
   - Otherwise a HEAD first. An `x-amz-meta-sha256` that is present and differs from the lock
     is refused before any GET.
   - The file downloads to `<file>.part` with `Range: bytes=<part size>-` once the part holds
     bytes. A 206 must start there, else the part is deleted; a 200 rewrites it.
   - urllib ends a cut body silently (H9), so the part's size shows the cut: up to five GETs
     per run.
   - Verified, the part takes the file's name. A wrong SHA-256 deletes it and fetches once
     more, then refuses.
   - A run that cannot finish keeps its part and names `python -m mattini download tlm`.
   - **Ctrl-C** is caught by one handler in `main()`, for every command (design's decision,
     M3-13 relies on it): one line ``mattini: interrupted: `python -m mattini <command>` did
     not finish; run it again``, exit 130, no traceback; for `download tlm` the line adds that
     the part is kept and the next run resumes it.
   - Every TLM refusal starts `swisstlm3d 2026-02: `.
7. **The measured values** (live, 2026-10-14):
   - `lock.entry_sha256`: swissimage `415ed9bcbee7b5d719f40f5b105204dc38ebc570cd2973ebc9de199d86f30fdd`,
     swisssurface3d `f73033b19c5ff89a1cff469d2777e9a9b4f91226eada171669017bf7c030f748`,
     swisstlm3d `aa909f98c8abc2653875cf6c8b4857a01f3d095dcaa3d3d5991ccb16b6594ba2`.
   - The lock after the three commands: 5'617 bytes, SHA-256
     `c071385c5ef3077241c90369e5f4bc232dc671e95a3b7e09393ba09e718f8cd0`; `git diff` shows 73
     added lines and none removed.
   - provenance.json after real downloads: swissimage `f28eed29431b23dd73279a8ac0cc64b772368d762ea2cce23930a80c78837ca4`,
     swisssurface3d `088f8bd2750994a3d29030e06140eb4ce7c895c5cf6ae448bd610676ca75ef91`,
     swisstlm3d `7034bea820642a42ce9fc558e62a2f2749b53d18459570f082eecd7c93ed52e9`.
   - Surface editions: 2623-1095 in 2022 only, the five other tiles in 2021 only.
8. **The new steps' expected values fit this lock.** The four step configs design committed
   with the plan (`config/photo.json`, `surfaces.json`, `roofs.json`, `trees.json`) record
   `computed_for` over these entries. The pinned `test_expected_inputs_m3.py` checks each one
   against the committed lock and world. The steps' own tests (lanes C and D) read no
   committed lock, because it gains these entries only here, in the same wave; this test is
   the seam.

## Scope — files you may touch

- `config/datasets.json`: design's pinned copy, put in place by the copy step, never edited.
  It lands in the same commit as the `datasets.py` change: copied alone it breaks 185 or
  more existing tests (measured).
- `config/datasets.lock.json`: written only by `lock photo`, `lock surface` and `lock tlm`
  against the live STAC.
- `pipeline/mattini/datasets.py`, `lock.py`, `download.py`, `__main__.py`.
- `pipeline/tests/`:
  - the pinned copies (`local_swisstopo.py`, `test_datasets_editions.py`,
    `test_lock_photo_surface_tlm.py`, `test_download_photo_surface_tlm.py`,
    `test_measured_photo_surface_tlm.py`, `test_expected_inputs_m3.py`, and
    `test_buildings_download.py`, design's update of M2-03's pinned file);
  - `test_download_datasets_config.py` (the neither-nor case);
  - `test_download_network.py` (five entries now; compare the three new ones with what
    swisstopo publishes, and the TLM's HEAD);
  - the tests of the republish wording;
  - your own new tests.

Not `manifest.py`, `terrain.py`, `buildings.py`, `sheets.py`, `world.py`, the other configs,
`tests/shared/`, `game/`, `tools/`.

## Depends on

M3-01 (the same lane; it edits `datasets.py` and `download.py` too). Start from its landing
(`git merge-base --is-ancestor <M3-01 sha> HEAD`) and keep its pinned tests green. In
`load_datasets`' loop, the edition/editions rule comes before M3-01's resolution check.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-03/. .`) and stay
      byte-identical (`cmp`, before every commit).
      - does NOT prove: that they are the right tests.
- [ ] `lock photo`, `lock surface`, `lock tlm` against the live API write the lock file
      `c071385c…` (73 added lines), unless swisstopo republished meanwhile. If it did, that is
      a BLOCKED question; design's expected values depend on these entries.
      `test_measured_photo_surface_tlm.py` and `test_expected_inputs_m3.py` pass.
      - does NOT prove: that swisstopo will not republish later (the download refuses that).
- [ ] `download photo` and `download surface` into a scratch root: six files each, provenance
      `f28eed29…` and `088f8bd2…`; a second run fetches nothing.
      - does NOT prove: that the steps read the files right (M3-04 to M3-07), or a republish
        after today.
- [ ] `download tlm`:
      - stopped by Ctrl-C after at least 1 GB, then run again: one GET with
        `Range: bytes=<n>-`, the file `185ffca8…`, provenance `7034bea8…`;
      - a third run makes no request to the file host;
      - the lock's TLM sha256 changed by one digit refuses before any request for the file.

      Needs 2.9 GB of scratch. Record the times.
      - does NOT prove: a cut by the network itself (proven against the stand-in only).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that any step reads these files right (M3-04 to M3-07).

## Forbidden

- Committing anything under `data/`, or downloading into the repository's `data/` for the
  gates (use a scratch root).
- Changing a pinned file or the measured values.
- Any manifest or game change.

## Findings (executor writes)
