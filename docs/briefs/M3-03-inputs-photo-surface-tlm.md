# Brief: M3-03 — The inputs of the photo, the surface model and swissTLM3D
Status: DONE (b6aee70)

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

1. **Pinned copies and the counts before the fix.** All eight files are in place and `cmp`
   identical to `docs/briefs/pinning/M3-03/`. On the code as M3-01 left it they failed:
   `test_datasets_editions.py` 25, `test_lock_photo_surface_tlm.py` 4,
   `test_download_photo_surface_tlm.py` 10, `test_measured_photo_surface_tlm.py` 1,
   `test_expected_inputs_m3.py` 5, `test_buildings_download.py` 11 (1 passes). Copying
   `config/datasets.json` alone made the whole suite fail to collect, as the brief warned; it
   landed with `datasets.py` in one commit.

2. **The live gates**, each against the real services from this container on 2026-10-15:
   - `lock photo`, `lock surface`, `lock tlm` (3.5 s, 6.3 s, 0.8 s): `config/datasets.lock.json`
     is 5'617 bytes, SHA-256 `c071385c…8cd0`, `git diff --numstat` 73 added and 0 removed: the
     brief's values exactly. A second run changes nothing.
     `test_measured_photo_surface_tlm.py` and `test_expected_inputs_m3.py` pass on it.
   - `download photo` and `download surface` into a scratch root: six files each (43 MB and
     16 MB each; 10 s and 11 s), provenance `f28eed29…` and `088f8bd2…` exactly; a second run of
     each: `6 tiles verified, 0 fetches`, provenance unchanged.
   - `download tlm` (a script outside the repository, `python -I`, real processes and a real
     SIGINT): killed at 1'005'584'384 bytes after 34.6 s: exit 130, one line
     `mattini: interrupted: `python -m mattini download tlm` did not finish; run it again;
     any part of the file is kept and the next run resumes it`, no traceback, the part kept
     at that size, no file, no provenance.json. The second run (48.9 s): one request, from byte
     1'005'584'384; the file `185ffca8…` (2'882'823'552 bytes), provenance `7034bea8…`
     exactly. A third run (9.6 s, the hashing): `1 file verified, 0 fetches`, provenance
     unchanged. The lock's TLM sha256 changed by one digit (a copy of the lock, file-host calls
     recorded): refused in 0.4 s with `swisstlm3d 2026-02: …nothing was fetched… lock tlm…
     config/surfaces.json and config/trees.json`, no call to the file host, nothing written.
   - `pytest -m network` (opt-in): the committed lock equals all five published entries, and the
     file host's HEAD for the TLM gives a size over 2 GB and the lock's checksum.
   - does NOT prove: a cut made by the network itself (the stand-in and the signal do), a
     republish after today, or that the steps read these files right (M3-04 to M3-07).

3. **What changed.**
   - `datasets.py`: exactly one of `edition` (`YYYY` or `YYYY-MM`, month 01 to 12) and
     `editions` (non-empty, distinct, ascending years); `resolution_m` required for
     `swissalti3d`, `swissimage` and `swisssurface3d`, after the edition rule.
   - `lock.py`: `photo_entry`, `surface_entry`, `tlm_entry`; `validate_lock` and the exact key
     sets for the three entries; five lock commands named in every malformed-lock error;
     `fit_problem` rows for the three (the surface: every tile's edition one of `editions`;
     the TLM: no area, `world` and `area` may be None); a config with the wrong kind of
     edition is a DownloadError naming `config/datasets.json` there too.
   - `download.py`: the terrain's tile download generalised (`_download_tiles`, the terrain
     and the photo share it), `download_photo`, `download_surface` (reads only the items the
     lock pins), `published_surface` (every year of `editions`; 404 is absent, anything else
     is "cannot read the STAC item"), `published_tlm`, `download_tlm` with `urllib_head` and
     `urllib_fetch_range`, `edition_of`, `editions_of`, `raw_folder`, `LOCK_COMMAND_OF`.
     The republish refusals of all five datasets name their dependants (the terrain's and the
     buildings' now name `config/trees.json` too).
   - `__main__.py`: `lock` and `download` take `photo`, `surface`, `tlm`; one handler in
     `main()` turns a Ctrl-C of any command into the one `interrupted` line and exit 130.
   - Names kept for lanes C and D: every name in M3-01's decision 10 is still there with its
     signature (`_resolution_tag` gained an optional second argument).

4. **Choices inside the scope, for the board's *Decisions for design to audit*.**
   - *The TLM's five GETs are per round.* A complete part with a wrong SHA-256 is deleted and
     fetched once more, and that second round has five GETs of its own, where the SPEC says
     "up to five GETs per run". At most ten in the worst case; the alternative is one counter
     for the run (one line in `_fetch_resumable`).
   - *`fit_problem(lock, datasets, None, None, "swisstlm3d")`* rather than a second function
     for the national file; the refusal for the TLM starts `swisstlm3d <edition>: ` (the
     download adds it) and names no area.
   - *The Ctrl-C line for `download tlm`* says `any part of the file is kept`, since a Ctrl-C
     before the first byte leaves no part.
   - *`urllib_fetch_range` prints a progress line every 256 MiB* to stderr (the CLI passes
     the printer); the brief asks for none.

5. **Existing tests changed** (the brief's list, and nothing else): `test_download_before_fetching.py`
   (the republish wording names the new dependants), `test_download_datasets_config.py` (the
   neither-nor case: dropping `edition` now reads "exactly one of edition and editions", and a
   `editions` list beside it is refused), `test_download_network.py` (five entries; the TLM's
   HEAD), `test_buildings_download.py` (design's update, pinned). Also my own
   `test_m3_01_fit_problem.py`: `swissimage` is no longer a dataset without a fit rule.

6. **New tests** (`test_m3_03_*`, 91): `fit_and_lock_shapes.py` (47: the three rows, every
   branch; the lock's exact shapes and the five commands in the error; the wrong kind of
   edition), `tlm_transfer.py` (21: the transfer with a scripted file host: a cut, a drop, a
   host that ignores the Range, a 206 from another byte, five cuts then a resumed run, a wrong
   body once and twice, a part too long, a complete part, a damaged file, the checksum header
   in upper case or absent, no Content-Length, a Ctrl-C), `commands.py` (23: the Ctrl-C line
   for seven commands, the wrong kind of edition before any request, which STAC items each
   command reads, a lock that does not fit before any request).

7. **Mutations**, each alone, restored with `git apply -R` (the tree clean after each):
   | mutation | failed |
   |---|---|
   | `lock <x>` writes its own entry alone | `test_each_command_writes_its_exact_entry_and_keeps_every_other` |
   | the first asset taken for the TLM | `test_lock_photo_surface_tlm.py`, `test_download_photo_surface_tlm.py` 6 |
   | `lock surface` takes the first edition that answers | `…_refuses_a_tile_in_no_edition_or_in_two[two]` |
   | a server error read as an absent item | `test_a_server_error_is_not_an_absent_edition` |
   | the checksum stored as published (upper case) | 11 |
   | the lock compared lazily before each fetch | `test_a_republished_file_is_refused_before_anything_is_fetched[photo]` |
   | `download surface` chooses the edition again | `test_download_surface_takes_the_edition_the_lock_pins`, `test_download_surface_reads_only_the_items_the_lock_pins` |
   | the host checksum compared case-sensitively | `test_the_file_host_s_checksum_in_upper_case_is_the_lock_s` |
   | a cut transfer fetched again from the start / from a wrong offset | 16 / 8 |
   | the part deleted at the end of a failed run | `test_a_run_that_fails_keeps_its_part_for_the_next_run`, `test_five_cuts_in_a_row_…` |
   | the file named before its checksum is checked | `test_a_complete_part_never_has_the_file_s_name_before_it_is_verified` (found equivalent to the real code on every outcome until a Ctrl-C during the hashing was added to the test) |
   | provenance.json not removed before the first change | `test_a_damaged_file_is_replaced_and_provenance_goes_before_the_first_change` |
   | a HEAD sent although the file is verified | `test_download_fetches_verifies_and_records[tlm]` |
   | a 206 from another byte appended; the five GETs not enforced | `test_a_206_from_another_byte_deletes_the_part_and_starts_again`; `test_five_cuts_in_a_row_…` |
   | the fit ignores the surface editions; names an area for the TLM | `test_a_surface_tile_in_an_edition_the_config_does_not_list_is_refused`; `test_the_tlm_needs_neither_a_world_nor_an_area` |
   | the Ctrl-C handler removed / exit status 1 | `test_a_ctrl_c_ends_one_line_with_status_130` 8 (the first form aborted pytest itself until the helper turned an escaped Ctrl-C into a failure) |
   | editions may repeat / descend; month 13 accepted; both keys accepted | `test_datasets_editions.py` 2 / 1 / 2 / 2 |
   | the validator accepts a surface tile without an edition | 10 |
   | `lock tlm` asks the file host (a HEAD) | `test_each_command_writes_its_exact_entry_and_keeps_every_other` |

   does NOT prove: that these are the only ways to see the defects (lesson 4).

8. **For M3-13** (the manifest and the command line): `fit_problem` already knows the three
   datasets, so its manifest blocks call it as they call it for the terrain; the Ctrl-C
   handler is in `main()` for every command, with the label `python -m mattini <command>` and
   the dataset for `lock` and `download`; `download.LOCK_COMMAND_OF` is the one table of lock
   commands.

9. **The landing.** The push needed no second rebase. The rebase before it brought in M3-08,
   M3-06, M3-10 and their DONE lines, so the gate ran again on the tree that landed, `b6aee70`:
   exit 0, pytest 1560 passed and 5 deselected, GUT 41 scripts, 224 tests, 8618 asserts. The
   DONE line is a docs-only commit: no test or tool reads `docs/briefs/` (grepped at M3-01,
   lesson 18). The scratch downloads (3 GB) were removed after the runs; nothing under `data/`
   was written.
