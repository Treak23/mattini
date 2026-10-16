# Brief: M3-R1-fix-6 — The surfaces PNG's bytes are design's, so the manifest is the same everywhere
Status: DONE (da8914f)

Written in the design realm from review finding M3-R1-I-01 (P2, Tier 2 with Hard Rule 5's full
discipline; `docs/reviews/M3-R1-inputs.md`) and design's answer of 2026-10-15 (SPEC §13 row 39);
executed by one fresh builder session under `docs/roles/BUILD.md`. Lane F-C of the fix wave
(`docs/briefs/M3-plan.md` §Fix wave).

## Goal

On a machine whose deflate writes other bytes than design's, `python -m mattini surfaces` refuses
before writing anything and names the machine's zlib, instead of exiting 0 with a PNG and a
manifest that differ from design's `3ca0445c…`. The gate on such a machine fails too. Today the
PNG's SHA-256 goes into `surfaces/<area>.json` and from there into `manifest.json`, and only its
pixels are compared (`pipeline/mattini/surfaces.py:578`, `:690`, `:908`).

Measured by design (2026-10-15): zlib 1.3 (the container's system Python) and zlib 1.3.2 (uv's
managed CPython 3.13.14, what a machine without a system 3.13 gets) write the same bytes for the
fixture at every cell and for a 2500 × 4000 class-like grid; zlib-ng 2.2.5 writes other bytes for
the fixture at 0.2 m (960 bytes, not 955) and for the village (the lens: 950'236, not 1'148'848),
and the same bytes for the fixture at 0.5 and 1 m (small grids can compress alike). Windows was
not measured.

## Read first, in order

1. `docs/reviews/M3-R1-inputs.md` §M3-R1-I-01.
2. `docs/SPEC.md` §8, the surfaces, *The PNG* (amended 2026-10-15).
3. `pipeline/mattini/surfaces.py`: `check_surfaces_config`, `build_surfaces`, `write_surfaces`,
   `built_surfaces_block`, `png_l8`.
4. `pipeline/tests/test_surfaces_fixture.py` (line 150's allowance), `test_surfaces_config.py`,
   `test_surfaces_checks.py`.
5. The pinned test: `docs/briefs/pinning/M3-R1-fix-6/pipeline/tests/test_m3_r1_fix6_png_bytes.py`.

## Decisions already made

1. **The config** gains `expected_png_sha256` in each area, keyed by cell exactly as
   `expected_pixels_sha256` (same key set), 64 lower-case hex digits each;
   `check_surfaces_config` requires it (exact key sets stay exact). SPEC §8 already says so.
2. **The fixture's values** are design's and are in the pinned test (`FIXTURE_PNG_SHA256`); write
   them into `tests/shared/surfaces_fixture/surfaces.json`.
3. **The village's values**: the 0.2 value is the PNG of the classes design pinned
   (`expected_pixels_sha256["0.2"]`), which the R1 inputs lens built independently: 1'148'917
   bytes, SHA-256 starting `8922edf9`. You compute all three (0.2, 0.5, 1) from the real run, on
   the container's Python (record `zlib.ZLIB_RUNTIME_VERSION`), with the cell changed in a scratch
   copy of the config, each run's pixels first equal to design's `expected_pixels_sha256` for that
   cell (so the step's own content check is the oracle); the 0.2 value must match the lens's size
   and prefix, or the brief is BLOCKED. These values pin the encoder, not the classes (JSON holds
   no comment): Findings and the step's refusal say so.
4. **Where the step refuses:** after the classes match `expected_pixels_sha256` and before
   anything is written (no `.part`, no folder). The message is a `SurfacesError` naming
   `zlib.ZLIB_RUNTIME_VERSION`, both SHA-256s, the config, and the remedy: a Python whose zlib
   writes design's bytes (zlib 1.3.x was measured to; uv's managed CPython, e.g. `uv python
   install 3.13 --managed-python` with `UV_PYTHON_PREFERENCE=only-managed`). Encode the PNG once
   (it is about 150 MB of scanlines): pass it to the writer rather than compressing twice.
5. **The manifest side:** `built_surfaces_block` refuses a built PNG whose SHA-256 is not the
   config's for the block's cell, naming `python -m mattini surfaces` (a test of yours, with a
   mutation).
6. **The allowance goes:** `test_surfaces_fixture.py`'s "only the PNG's own SHA-256 may differ"
   becomes an exact comparison with the committed block, so the gate fails on a machine whose
   zlib writes other bytes (the pinned `test_this_machine_writes_the_designed_png_bytes` too).
7. **The release walk:** `docs/RELEASE.md` §C's list says the surfaces compare by pixels and PNG
   (`config/surfaces.json`) and gains one box: the fresh checkout's `manifest.json` has the
   SHA-256 the arc plan names (M3: `3ca0445c…`, 324'359 bytes), compared by a command, its
   output in the release record.

## Scope — files you may touch

- `pipeline/mattini/surfaces.py`.
- `config/surfaces.json` (the new key only), `tests/shared/surfaces_fixture/surfaces.json` (the
  new key only).
- `pipeline/tests/test_m3_r1_fix6_png_bytes.py` (the pinned copy, byte-identical),
  `pipeline/tests/test_surfaces_config.py`, `test_surfaces_fixture.py`,
  `test_surfaces_checks.py`, and any other test that pins the surfaces config's exact key set
  (design's throwaway run: four cases in the first two files).
- `docs/RELEASE.md` §C (decision 7 only).
- This brief file (Status and Findings).

## Depends on

None.

## Done when (gates)

- [ ] `cmp` of the pinned and live `test_m3_r1_fix6_png_bytes.py` exits 0 and its nine cases
      pass.
      - does NOT prove: that every other deflate is refused by the fixture alone (the real run's
        refusal covers the village).
- [ ] Mutation proof in a throwaway clone (saved diffs, `git apply -R`): (1) the step's PNG
      comparison removed; (2) the manifest's removed; (3) the config check accepting a missing
      key; (4) the step's comparison moved after the write (a `.part` left); (5) zlib-ng in place
      of zlib (`sitecustomize.py` on `PYTHONPATH`, as the lens did) with mattini untouched: the
      full pytest fails (name the case) and `surfaces` on the real inputs refuses naming
      zlib-ng's version. Each fails a named test; output and owner-visible harm in Findings.
      - does NOT prove: Windows' bundled zlib (not measured; the owner's run there is the
        check, and the refusal names it if it differs).
- [ ] The real village from the command line, fresh clone, pinned inputs: `surfaces` and
      `manifest` exit 0, `manifest.json` is 324'359 bytes with SHA-256 `3ca0445c9109eec4696d654d
      1c7536f50220f4db04503fab836412f5b0c01065` (the descriptions do not change).
      - does NOT prove: another machine's bytes.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`.
      - does NOT prove: that it renders or looks right.

## Forbidden

A deflate of mattini's own; renaming or changing the helpers `trees.py` imports from
`surfaces.py` (lane F-A builds beside you); dropping the PNG's SHA-256 from the description; any change to the
description's or the manifest's key sets, the PNG's format, the game, `tools/`; a version bump;
a new dependency; a model's name or id anywhere in the repository.

## Findings (executor writes)

0. **What changed, and the gates.** `pipeline/mattini/surfaces.py`; `config/surfaces.json` and
   the fixture's `surfaces.json` (`expected_png_sha256` only: design's fixture values from the
   pinned test, the village's from the real run, item 1); the three surfaces test files, with the
   pinned copy (`cmp` exit 0, its nine cases pass); `docs/RELEASE.md` §C (the surfaces compare by
   pixels and PNG, and the new box with its command). The standard gate, on the head after the
   rebase onto fix-2: exit 0, pytest 2203 passed (5 network tests deselected), GUT 47 scripts,
   261 tests, 9760 asserts. Before the rebase the same tree passed too (pytest 2196 passed,
   the same GUT counts). The gate's render step is fix-3's and had
   not landed. Gate does NOT prove: that it renders or looks right.
1. **The village's PNG values (decision 3).** Computed from the real run in a scratch `git clone`
   (data/ downloads in its own folder: terrain, buildings, photo, surface and tlm fetched and
   verified in 13 s, 10 s, 14 s, 12 s and 32 s), on the container's Python 3.13.16,
   `zlib.ZLIB_RUNTIME_VERSION` `1.3`. The step's own content check was the oracle: each run's
   classes first equalled design's `expected_pixels_sha256` for the cell (`93d78ba6…`,
   `adda417b…`, `4ea3d1e6…`), then the PNG was hashed:

   | cell | PNG bytes | SHA-256 | time, peak |
   |---|---|---|---|
   | 0.2 | 1'148'917 | `8922edf904e3e4e1de40c65daf1af1aae3474d71481d628a548152ce5b843e12` | 33.5 s, 395 MB |
   | 0.5 | 307'716 | `6773cfc4b553cd3fa7e6c19fda08a66a8db711f8fd9ff0a498852d5dac17b071` | 19.5 s, 205 MB |
   | 1 | 130'159 | `e68a251cef28046b921999e2792c1bab3497cc193ee42e6afd49dc9cc60d6344` | 17.8 s, 191 MB |

   The 0.2 value matches the R1 inputs lens's build: 1'148'917 bytes, prefix `8922edf9`. These
   values pin the encoder, not the classes (JSON holds no comment); the step's refusal says so.
2. **The remedy was run, not only written.** uv 0.11.32 installed its managed CPython 3.13.14
   (zlib `1.3.2`) with `uv python install 3.13 --managed-python` into a scratch folder
   (`UV_PYTHON_INSTALL_DIR`; the container's own uv Python folder was not touched);
   `UV_PYTHON_PREFERENCE=only-managed` made `uv run` pick it (so does `UV_MANAGED_PYTHON=1`; the
   system 3.13.16 is picked without them). `python -m mattini surfaces` under it, on the real
   inputs: exit 0, `village.png` 1'148'917 bytes, SHA-256 `8922edf9…`, the same as zlib 1.3's.
   That is the village's own confirmation of the fixture-level measurement design made.
3. **Real village from the command line, fresh clone of the commit** (before the rebase onto fix-2,
   `5962cae`; the downloads are the scratch clone's, passed with `--raw`, each step verifying
   its SHA-256 against the lock): `terrain` (7.3 s, 1'048 MB), `buildings` (7.2 s, 349 MB),
   `photo` (101.6 s, 1'216 MB), `roofs` (35.4 s, 1'271 MB), `surfaces` (32.1 s, 444 MB, printing
   "the PNG has the SHA-256 config/surfaces.json expects, 8922edf9…"), `trees` (40.6 s, 1'308 MB),
   `manifest` (1.7 s), each its own process, each exit 0 and each compared against its
   config before writing. `game/assets/generated/manifest.json`: 324'359 bytes, SHA-256
   `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`, the arc plan's.
   (Times with a second pytest running at the same time.)
4. **Mutations** (a throwaway `git clone` with the work as its baseline commit; each mutation a
   saved diff, undone with `git apply -R`, the tree clean after each; first, then the failing
   tests run: `pytest -k "surfaces or png or manifest"`, 643 passed unmutated). Owner-visible harm
   in the right column.

   | # | Mutation | Fails (named) | Harm it reproduces |
   |---|---|---|---|
   | 1 | the step's PNG comparison removed | `test_m3_r1_fix6_png_bytes.py::test_a_png_that_is_not_the_configs_is_refused_naming_zlib`, `test_surfaces_checks.py::test_a_png_of_other_bytes_is_refused_after_the_classes_and_before_anything_is_written` | `surfaces` exits 0 on a zlib-ng machine and writes another PNG and manifest (R1 I-01) |
   | 2 | the manifest's comparison removed | `test_surfaces_checks.py::test_a_png_of_the_designed_classes_and_other_bytes_is_refused_naming_the_rebuild`, `…::test_a_png_that_is_not_the_one_the_config_expects_is_refused_whatever_it_holds`, `…::test_the_png_is_compared_with_the_value_of_its_own_cell[0.5-0.5]`, `[1.0-1]` | `manifest` writes `manifest.json` from a PNG another deflate wrote, and the release check fails with no word of zlib |
   | 3 | the config check accepts a missing `expected_png_sha256` (and the step and the manifest then compare nothing) | the pinned `test_a_config_without_well_formed_png_values_is_refused[None]`, `test_surfaces_config.py::test_a_malformed_config_is_refused_naming_where[…expected_png_sha256]` | a config edited to lack the key silently drops the check |
   | 4a | the step's comparison moved after the write | the pinned `test_a_png_that_is_not_the_configs_is_refused_naming_zlib`, `test_a_png_of_other_bytes_is_refused_after_…_before_anything_is_written` | a refused run leaves the other deflate's PNG and description in `surfaces/` |
   | 4b | the output folder created before the comparison | `test_a_png_of_other_bytes_is_refused_after_…_before_anything_is_written` only (the pinned test globs `*.png` and does not see a folder) | a refused run leaves a `surfaces/` folder |
   | 5 | zlib-ng 2.2.5 in place of zlib (`sitecustomize.py` on `PYTHONPATH`, the PyPI `zlib-ng` 1.0.0 package, mattini untouched; the shim also sets `zlib.ZLIB_RUNTIME_VERSION` to `1.2.12 (zlib-ng 2.2.5)`, what such a build says of itself) | full `pytest pipeline/tests`: 9 failed, 2187 passed: the pinned `test_this_machine_writes_the_designed_png_bytes` (the fixture re-encoded: 960 bytes, not 955), `test_surfaces_fixture.py::test_write_surfaces_writes_the_designed_files` (the exact comparison of decision 6), `test_surfaces_step.py::test_the_step_writes_the_designed_classes` and six `test_surfaces_checks.py` builds that now meet the step's refusal. `surfaces` on the real inputs: exit 1, `mattini: error: area 'village' at 0.2 m: the classes are design's, but the PNG built here has SHA-256 6c045a83… and config/surfaces.json expects 8922edf9… (expected_png_sha256). … this machine's (zlib 1.2.12 (zlib-ng 2.2.5)) or this code writes other bytes than design's … nothing was written`; no output folder | the lens's own scenario; `6c045a83…` is the PNG the lens measured |
   | 6a, 6b | the step, the manifest reads the village's own cell (`"0.2"`) whatever the cell | `test_the_png_is_compared_with_the_value_of_its_own_cell[0.5-0.5]`, `[1.0-1]` | a village built at 0.5 m is compared with the 0.2 m PNG |
   | 7a | the step passes no `png` to the writer (compresses the 150 MB twice) | `test_the_png_is_encoded_once_and_is_the_one_written` | twice the encode time and memory |
   | 7b | the writer ignores the `png` it is given | `test_surfaces_fixture.py::test_write_surfaces_writes_the_png_it_is_given_and_encodes_nothing_again`, `test_the_png_is_encoded_once_and_is_the_one_written` | the same |
   | 8 | the step's refusal does not name the machine's zlib | `test_a_png_of_other_bytes_is_refused_after_…_before_anything_is_written` | the owner is not told whose zlib |
   | 9 | the PNG encoded before the classes are compared | `test_the_classes_are_compared_before_the_png_is_encoded`, `test_the_png_is_encoded_once_and_is_the_one_written` | 150 MB compressed for classes that are refused |
   | 10 | the config check no longer requires the two objects to hold the same cells | `test_surfaces_config.py::test_a_malformed_config_is_refused_naming_where[…the two must hold the same cells]` (two cases) | a cell with classes and no PNG value |
   | 11 | the config check does not test the PNG values' form | `test_surfaces_config.py::test_a_malformed_config_is_refused_naming_where[…expected_png_sha256['0.5'] must be a SHA-256]` (three cases) | an upper-case or short value that can never match |
5. **Decisions inside the brief, and what a reader should know.**
   - `write_surfaces` gained a keyword-only `png` (default `None`, the old behaviour), so the
     step encodes once and hands the bytes over; the existing positional calls and the helpers
     `trees.py` imports (`_Frame`, `_paint`, `_polygon_spans`, `_row_pairs`, `_ceil_div`,
     `_floor_div`, `BIG`, `LIMIT_MM`, `_snapped`, `read_tlm`, `SurfacesError`) are untouched.
   - `built_surfaces_block`'s comparison is the *last* check, after the description, decoding and
     the classes, so every existing refusal keeps its own, more specific message; only a PNG that
     passes all of those and has other bytes meets it.
   - The step says one more progress line ("the PNG has the SHA-256 … expects"), so
     `test_the_progress_lines_come_in_order_and_the_hash_comes_before_the_read` counts eight events
     where it counted seven (the one change to an existing test's expectation; its Scope is the
     brief's).
   - The pinned test asserts `zlib.ZLIB_RUNTIME_VERSION in text`; the refusal's remedy says "zlib
     1.3.x", so on this container (`1.3`) that assertion would pass even if the refusal did not
     name the machine's zlib. The builder's tests patch `ZLIB_RUNTIME_VERSION` to a version no other
     text holds (mutation 8 shows it) — the pinned file is byte-identical and was not touched.
   - `tests/shared/surfaces_vectors.json` ("about": "its bytes depend on the zlib build, so only
     its pixels are pinned") is design's file, outside this brief's Scope, and is now stale: for
     design to reword.
   - No `.part` and no folder is written by a refused run (mutation 4b is the proof for the folder).
6. **Not done / not measured.** Windows' bundled zlib was not measured: the refusal names it if it
   differs, and the owner's run there is the check. zlib 1.3.2 was shown to give the village's
   bytes at 0.2 m only (the 0.5 and 1 m values were built with zlib 1.3). Peak memory of the
   build function at 0.2 m, the same script before and after this change: 395 MB, then 399 MB
   (the encode is still once; the command line's 444 MB includes the manifest it writes after
   the step, which reads the PNG back).
