# Review M3 R2 — lens `surfaces`, verification of M3-R1-fix-6 (Tier 2, Hard Rule 5's full discipline)

**fix-6 is VERIFIED: no P0, no P1, no P2; three P3.**

- **Range:** `git diff d8d2471..da8914f` (fix-6's code commit `da8914f`; status commit `2abb18d`): 8 files, 395 insertions, 47 deletions. Head reviewed `a6779f3` (`main`); nothing in `pipeline/mattini/surfaces.py`, `config/surfaces.json`, `tests/shared/` or `docs/RELEASE.md` changed between `da8914f` and `a6779f3` (`git diff da8914f..a6779f3 --stat -- <those paths>` is empty; the later commits are the gate's render step, `fake_tools.py` and docs).
- **Date:** 2026-10-16.
- **How:** one session (`session_01D4QkAjK7dhF4Vn6RScTuNj`), no sub-agents. Three `git clone`s of the repository at `a6779f3`, each with its own `uv sync` and a scratch `UV_CACHE_DIR`; never two heavy runs at once:
  - **A** the real village: the five `download` commands (3.2 GB, all verified), then `terrain`, `buildings`, `photo`, `roofs`, `surfaces`, `trees`, `manifest` from the command line (5, 5, 45, 27, 19, 25 and 1 s). All shim, order and lesson-41 probes ran from A with `--raw A/data/raw` and a scratch `--out`.
  - **M** the throwaway clone: 26 saved mutation diffs, each applied alone, tested, and undone with `git apply -R` (`git status --short` empty after every one); also the system-Python (zlib 1.3) half of the three-cell runs.
  - **V** the uv-managed half: `uv python install 3.13 --managed-python` into a scratch `UV_PYTHON_INSTALL_DIR` (CPython 3.13.14, `zlib.ZLIB_RUNTIME_VERSION` `1.3.2`), `UV_PYTHON_PREFERENCE=only-managed`; its config edited for the cell runs and restored with `git checkout`.
  - Control: `uv run --project pipeline --frozen pytest pipeline/tests` at the head, 2228 passed, 5 deselected (2 m 04 s); the same on the managed Python (V), 2228 passed.
  - All three clones, the zlib builds and the scratch folders were removed before this report. The repository's tracked files were not touched but this report.
  - The shim is the R1 lens's: a `sitecustomize.py` on `PYTHONPATH` that replaces `zlib.compress` and `zlib.compressobj` with the PyPI `zlib-ng` 1.0.0 package (zlib-ng 2.2.5); mattini untouched (Appendix A). Shim 2 also sets `zlib.ZLIB_RUNTIME_VERSION` to `1.3.1.zlib-ng`, a string of the form a zlib-ng compat build reports of itself (my assumption from zlib-ng's naming, not measured: this container has no zlib-ng-linked Python).
- **Result:** the surfaces step and the manifest both refuse a PNG another deflate writes; the gate fails on such a machine (9 named cases); the other steps never call a Python deflate and are byte-identical under the shim; the real village gives the manifest `3ca0445c…` (324'359 bytes) on a fresh clone, in either order of `surfaces` and `trees`; the village's three PNG values are the bytes that design's pixels produce on zlib 1.3, 1.3.2 and (new, not asked) vanilla 1.2.11, 1.2.13, 1.3.1 built from source. 23 of 26 mutations fail a named test; the three that pass the full pytest are one gap (P3, S-01) and one test weakening that cannot be seen on the same machine (caught under the shim by eight other cases). The three P3 are a loosened-hex-check gap, a release box that fails silently on a wrong size, and a stale line in SPEC §8.

## Findings

### M3-R2-S-01 · P3 · No test gives a short lower-case hex string to the SHA-256 check of `expected_png_sha256` (nor of `expected_pixels_sha256`), so the check can lose its length and the gate stays green

- **Where:** pipeline/mattini/surfaces.py:94 (`SHA256_HEX = re.compile(r"[0-9a-f]{64}")`) and :229 (the one check both fields share); pipeline/tests/test_surfaces_config.py (the new `expected_png_sha256['0.5'] must be a SHA-256` cases: `"xyz"`, `"A" * 64`, `5`) and the pinned test_m3_r1_fix6_png_bytes.py (`"ABC"`, `"x" * 64`); fix-6's Findings 4, row 11 ("an upper-case or short value that can never match").
- **Claim:** The tests' "short" value is `"xyz"`, which is also not hex, so it is refused by the character class and says nothing about the length. A value of 40 to 63 lower-case hex digits (a SHA-1, a hash cut by an editor) is refused by nothing but the `{64}`, and no test would notice its loss. Row 11 of the builder's table claims a short value is caught; only an upper-case one and a non-hex one are.
- **Proof:** (a) `X9`, the shared regex changed to `[0-9a-f]{40,64}`: fast subset (`-k "surfaces or png or manifest or fix6"`) 645 passed; full `pytest pipeline/tests` **2228 passed, 5 deselected**. (b) `S3c`, only the PNG field accepting 40 to 64 digits: fast subset 645 passed, full pytest 2228 passed. (c) The harm, with `S3c` applied and `expected_png_sha256["0.2"]` cut to its first 40 digits, `surfaces` on the real inputs: exit 1, `mattini: error: area 'village' at 0.2 m: the classes are design's, but the PNG built here has SHA-256 8922edf9…3e12 and config/surfaces.json expects 8922edf904e3e4e1de40c65daf1af1aae3474d71 (expected_png_sha256). The PNG's bytes depend on the zlib build, so this machine's (zlib 1.3) or this code writes other bytes…`: the zlib message for a stored value that can never match. On the shipped code the same edit ends `…expected_png_sha256['0.2'] must be a SHA-256 in 64 lower-case hex characters, found '8922edf904e3e4e1de40c65daf1af1aae3474d71'`.
- **Harm:** A later edit of the check (or of the config by hand) loses the refusal that names the key, and the owner is sent to chase a zlib build for a typo. Only the message is lost: the comparison still refuses, nothing wrong is written.
- **Fix:** Two parametrised cases (one per field) in test_surfaces_config.py with a 40-digit and a 63-digit lower-case string, expecting `must be a SHA-256 in 64 lower-case hex characters`.

### M3-R2-S-02 · P3 · RELEASE.md §C's new box fails silently on a wrong size, so "its output in the release record" records nothing

- **Where:** docs/RELEASE.md:46-50 (the box; the command on :49), the command `test "$(wc -c < game/assets/generated/manifest.json)" -eq 324359 && echo "3ca0445c…  game/assets/generated/manifest.json" | sha256sum -c -`.
- **Claim:** The command is correct for the two cases that matter (right file: `OK`, exit 0; right size and wrong hash: `FAILED`, exit 1), and it can be followed literally from the checkout's root. The `&&` makes the size test gate the hash line, so a manifest of another size prints nothing at all and exits 1; the box says the output goes in the release record, and a walker who copies the output records an empty line for the failure that is most likely (a manifest with one more block or one more byte is another size). A missing file prints two shell errors and exits 2. The box does not say "from the checkout's root" (the path is relative), and the size test adds nothing the hash does not already decide (no other file has both).
- **Proof:** the command text extracted from RELEASE.md by `grep`/`sed` equals the one run; five manifests under `bash -c` and `sh -c` (dash), each in a folder holding `game/assets/generated/manifest.json`:

  | manifest | output | exit |
  |---|---|---|
  | A's real one (324'359 B, `3ca0445c…`) | `game/assets/generated/manifest.json: OK` | 0 |
  | same size, last-but-one byte flipped | `…: FAILED` and `sha256sum: WARNING: 1 computed checksum did NOT match` | 1 |
  | 10 bytes shorter (324'350) | nothing | 1 |
  | 1 byte longer (324'360) | nothing | 1 |
  | no file | `No such file or directory`, `test: : integer expression expected` (bash) / `Illegal number:` (dash) | 2 |

- **Harm:** A release walk can tick the box over an empty record when the check failed (the exit status is the only signal and the box does not tell the walker to read it). Nothing in the build is wrong.
- **Fix:** Drop the size test and keep `sha256sum -c` (a wrong size cannot have the right hash), and print the size for the record: `(cd <checkout> && wc -c game/assets/generated/manifest.json && echo "3ca0445c…  game/assets/generated/manifest.json" | sha256sum -c -)`, with "from the checkout's root, exit status 0" in the box.

### M3-R2-S-03 · P3 · SPEC §8 still describes the surfaces config without `expected_png_sha256`

- **Where:** docs/SPEC.md:658-659 (*The expected output*, the `config/surfaces.json` line: `{"schema": 1, "areas": {<area>: {"cell_m", "computed_for", "expected_pixels_sha256": {"0.2", "0.5", "1"}}}}`); the PNG bullet above it (:651) and §13 row 39 (:1013) do name `expected_png_sha256`.
- **Claim:** The design of record lists the config's exact key set, and the check now requires one more key; the list is the one place a reader (or a design session recomputing the values after a new edition) learns that the key set is exact. fix-6's Scope did not include the SPEC, and the brief says "SPEC §8 already says so" (it says it for the PNG, not for the shape).
- **Proof:** `grep -n expected_png_sha256 docs/SPEC.md` hits :651 and :1013 only (the PNG bullet and row 39); `check_surfaces_config` requires `{"cell_m", "computed_for", "expected_pixels_sha256", "expected_png_sha256"}` (surfaces.py:93 `AREA_CONFIG_KEYS`).
- **Harm:** A design session that rebuilds the config from the SPEC's shape writes a config the check refuses (`must have exactly the keys […]`); a refusal, not a wrong world.
- **Fix:** Design adds `"expected_png_sha256": {"0.2", "0.5", "1"}` to that line. Same family, already on the board (docs/ROADMAP.md:82): `tests/shared/surfaces_vectors.json` "about" still says "its bytes depend on the zlib build, so only its pixels are pinned" (design's file, stale since fix-6).

## Checked and clean

### 1. A machine whose deflate writes other bytes (shim 1 and 2; mattini untouched)

- **(a) `surfaces` on the real inputs, fresh `--out`:** `PYTHONPATH=shim/site1 python -m mattini surfaces --raw A/data/raw --out O1`: exit 1, stdout empty, stderr: the four progress lines (SHA-256 check of the TLM file, reading it, `read 230 TLM_BODENBEDECKUNG, 73 TLM_FLIESSGEWAESSER, 843 TLM_STRASSE; classifying a 0.2 m grid`, `the classes have the SHA-256 config/surfaces.json expects, 93d78ba6…`) then
  `mattini: error: area 'village' at 0.2 m: the classes are design's, but the PNG built here has SHA-256 6c045a8316088c84e1d093598cb0c5fe98d67fc5c276b3bf755c7b8f0547a0ab and config/surfaces.json expects 8922edf904e3e4e1de40c65daf1af1aae3474d71481d628a548152ce5b843e12 (expected_png_sha256). The PNG's bytes depend on the zlib build, so this machine's (zlib 1.3) or this code writes other bytes than design's; that value pins the encoder, not the classes. A Python whose zlib writes design's bytes (zlib 1.3.x was measured to) builds the same file, uv's managed CPython for one: `uv python install 3.13 --managed-python`, then run with UV_PYTHON_PREFERENCE=only-managed; nothing was written`.
  No `Traceback` (counted 0), `O1` does not exist afterwards. `6c045a83…` is the PNG the R1 lens measured. With shim 2 the message says `zlib 1.3.1.zlib-ng` (it prints `zlib.ZLIB_RUNTIME_VERSION`; shim 1 leaves that string at the real `1.3`, so its message names the unshimmed value).
  Over a copy of the good outputs (24 files, shim 2): exit 1, the same message, no `Traceback`; `find | stat` (name, size, mtime) before and after identical, `sha256sum` of all 24 files equal to the baseline, no `*.part`. Nothing is created and nothing is damaged.
- **(b) `manifest` refuses a PNG another deflate wrote.** The realistic route: the pre-fix code (clone at `d8d2471`) under shim 1 writes `surfaces/village.png` (950'293 bytes, `6c045a83…`), exit 0, as in R1 I-01. Those three files in a copy of the baseline's other outputs, then at the head and without the shim `python -m mattini manifest --out <copy>`: exit 1, stdout empty,
  `mattini: error: <copy>/surfaces/village.json: <copy>/surfaces/village.png has SHA-256 6c045a83…, config/surfaces.json expects 8922edf9… at 0.2 m (expected_png_sha256): its classes are design's, its bytes are not (they depend on the zlib build of the machine that wrote it; this machine's is zlib 1.3); `python -m mattini surfaces` rebuilds the surfaces`.
  `manifest.json` in the copy was left as it was (`3ca0445c…`). With shim 2 on, the same line ends `this machine's is zlib 1.3.1.zlib-ng`. The description's own `sha256` agrees with that PNG (the old code wrote it), so the refusal is the new last check, reached after the description, the decoding and the pixels; its remedy names `python -m mattini surfaces`, which on a zlib-ng machine ends in the step's refusal above (two hops to the remedy, each message true).
- **(c) The full pytest and the gate on such a machine.** `PYTHONPATH=shim/site1 … pytest pipeline/tests`: **9 failed, 2219 passed, 5 deselected** (2 m 02 s). `PYTHONPATH=shim/site2 MATTINI_SKIP_RENDER=1 tools/gate.sh` in A: `== gate: step: uv lock --check`, `== gate: step: pytest`, the same nine, `== gate: FAILED at step: pytest`, exit 1, 1 m 59.8 s. The nine:
  - `test_m3_r1_fix6_png_bytes.py::test_this_machine_writes_the_designed_png_bytes` (`AssertionError: this machine's zlib 1.3.1.zlib-ng writes other PNG bytes than design's`);
  - `test_surfaces_fixture.py::test_write_surfaces_writes_the_designed_files`;
  - `test_surfaces_step.py::test_the_step_writes_the_designed_classes`;
  - six in `test_surfaces_checks.py`: `test_the_progress_lines_come_in_order_and_the_hash_comes_before_the_read`, `test_the_checksum_may_be_written_in_upper_case_in_provenance`, `test_the_files_are_written_in_order_each_through_a_part_rename`, `test_part_files_left_by_a_cut_run_are_removed_from_the_surfaces_folder_only`, `test_the_png_is_encoded_once_and_is_the_one_written`, `test_two_builds_give_the_same_files`.
  The same nine as fix-6's Findings (their count of passes is lower because fix-1 to fix-5 added tests). Control, same head, no shim: 2228 passed.
- **(d) The other steps are not affected.** `grep -rn -i "zlib\|gzip\|deflate\|zipfile\|lzma\|bz2\|compress" pipeline/mattini` outside surfaces.py finds only `buildings.py:63,208-209` (`zipfile.ZipFile(...).namelist()`, a read). The photo's JPEG is Pillow's libjpeg-turbo (`photo.py:245`), the terrain and buildings are `tobytes()` of arrays, the roofs and trees are JSON/`tobytes()`; GDAL and fiona only inflate. Proof by behaviour, two ways, `terrain`, `buildings`, `photo`, `roofs`, `trees`, `manifest` (surfaces taken from the baseline) from the command line:
  - under shim 1: all exit 0, **all 24 output files byte-identical** to the unshimmed build (`sha256sum` diff empty), `manifest.json` `3ca0445c…`, 324'359 bytes;
  - under shim 3 (`zlib.compress` and `zlib.compressobj` raise `DEFLATE WRITER CALLED`): the same six commands exit 0, 24 files identical; `surfaces` under shim 3 is the control and ends in that `RuntimeError`. So no step but `surfaces` writes a deflate stream through Python, and none other can differ by it.

### 2. Hard Rule 5: the stored values are what the pixels produce, on more than the builder's machine

- **The three village values, from the command line, `cell_m` edited in a scratch config (clones M and V, `git checkout config` after each); the step's own content check is the oracle (every run first printed `the classes have the SHA-256 config/surfaces.json expects`, then the PNG line, exit 0):**

  | cell | zlib 1.3 (system, M) | zlib 1.3.2 (uv managed, V) | PNG bytes | SHA-256 | = config |
  |---|---|---|---|---|---|
  | 0.2 | exit 0, 20 s | exit 0, 20 s | 1'148'917 | `8922edf904e3e4e1…` | yes |
  | 0.5 | exit 0, 12 s | exit 0, 12 s | 307'716 | `6773cfc4b553cd3f…` | yes |
  | 1 | exit 0, 11 s | exit 0, 11 s | 130'159 | `e68a251cef28046b…` | yes |

  fix-6's Findings 6 said the 1.3.2 run was only done at 0.2 m; it holds at all three.
- **A writer that imports nothing of mattini** (Appendix B: stdlib PNG decoder, then its own 8-bit grey / filter 0 / one level-9 stream / 1 MiB IDAT writer, written from SPEC §8): for each of the six PNGs, under both interpreters, the decoded pixels have design's `expected_pixels_sha256` (`93d78ba6…`, `adda417b…`, `4ea3d1e6…`) and the writer's PNG has the file's SHA-256 and the config's `expected_png_sha256`: 12 of 12 `==`. The stored values are not the step's output read back into the config: they are what design's pixels give through an independent encoder, on two zlib builds.
- **Further zlib versions, not asked (Appendix C):** libz built from the zlib.net sources (SHA-256 of the tarballs as downloaded: 1.3.1 `9a93b2b7…`, 1.3 `ff0ba4c2…`, 1.2.13 `b3a24de9…`, 1.2.11 `c3e5e9fd…`, 1.3.2 `bb329a0a…`), `compress2` at level 9 through `ctypes` (the same `deflateInit` defaults as CPython's `zlib.compress`) over the village's three scanline arrays: **zlib 1.2.11, 1.2.13, 1.3, 1.3.1 and 1.3.2 all give design's three SHA-256s.** The refusal's "zlib 1.3.x was measured to" now has 1.3.1 under it too.
- **The fixture's values** (`FIXTURE_PNG_SHA256`): `ef3828f9…` (955 B, the committed `fixture.png`), `e0106ac1…` (404 B), `49e7647f…` (232 B) are the fixture PNG at 0.2, 0.5 and 1 m on zlib 1.3 and on 1.3.2 (`fixture_cells.py` over the pinned test's own `_case`/`_build`): 6 of 6 equal. Full pytest on the managed Python (V): 2228 passed. Under shim 2 the fixture at 0.2 m is refused (`01e0fe9d…`, not `ef3828f9…`), as design measured; at 0.5 and 1 m a zlib-ng machine writes the fixture's bytes (design's note), so the fixture alone cannot show the refusal at those cells and the pinned test says so.
- **Right cell:** at cell 0.5 and at cell 1 with the 0.2 value (`8922edf9…`) written into `expected_png_sha256` of the configured cell: `surfaces` exits 1 (`the PNG built here has SHA-256 6773cfc4… [e68a251c… at 1 m] and config/surfaces.json expects 8922edf9…`), no output folder; `manifest` over the good cell-0.5 and cell-1 PNGs refuses, naming `…at 0.5 m (expected_png_sha256)` / `at 1 m`; with the 0.2 slot set to 64 zeros and the cell 0.5 (1) configured, `manifest` exits 0 (another cell's value is not read). Mutations `X3a`, `X3b` (the step and the manifest reading `"0.2"` whatever the cell) fail `test_the_png_is_compared_with_the_value_of_its_own_cell[0.5-0.5]` and `[1.0-1]`; `X1` (the pixels' value for the PNG) fails ten cases.
- **Lesson 41, by command** (clone V, each edit undone with `git checkout config`; the step reads the real inputs, the manifest runs over a copy of the good outputs):

  | what changed | step says | manifest says |
  |---|---|---|
  | world origin moved by 100 m | `the expected values in config/surfaces.json were computed for the world config with SHA-256 d2607d13…; config/world.json now has e6b9bd6d…. A changed world is a design change: design recomputes the expected values (docs/SPEC.md §8)` | the same words for `config/terrain.json` (the first config it checks) |
  | one digit of the TLM lock entry | `…computed from the swisstlm3d lock entry with SHA-256 aa909f98…; config/datasets.lock.json's entry now has c1b2fbf8… (a new edition or an adopted republished file). Adopting new inputs is a design change: design recomputes…` | the same |
  | `expected_pixels_sha256["0.2"]` wrong | `the classes built here have SHA-256 93d78ba6…, config/surfaces.json expects 03d78ba6…. Design computed the expected value two independent ways…; nothing was written` | `the classes in …/village.png have SHA-256 93d78ba6…, config/surfaces.json expects 03d78ba6… at 0.2 m (pixels_sha256); python -m mattini surfaces rebuilds the surfaces` |
  | `expected_png_sha256["0.2"]` wrong | `the classes are design's, but the PNG built here has SHA-256 8922edf9… and … expects 0922edf9… (expected_png_sha256). The PNG's bytes depend on the zlib build…` | `…village.png has SHA-256 8922edf9…, … expects 0922edf9… at 0.2 m (expected_png_sha256): its classes are design's, its bytes are not…` |
  | both wrong | the pixels' message (the PNG is not even encoded: `S5b`, `S5c` fail `test_the_classes_are_compared_before_the_png_is_encoded`) | the pixels' message |

  The order is world, then inputs, then provenance and the file's SHA-256, then the pixels, then the PNG, in the step and in the manifest; a changed world or a republished input is never reported as a zlib problem. `l41out` did not exist after the five refusals. One remark: a wrong *stored PNG value* on a machine that already has a zlib design measured (V: `zlib 1.3.2`) gets the message above with its zlib remedy ("A Python whose zlib writes design's bytes…"), which cannot succeed there; the message does say "or this code" and "that value pins the encoder, not the classes", so it is true, only its remedy is for the likelier cause. Not graded (design recomputes the values from the printed digest).
- **The remedy runs, with an existing venv.** In V (a `uv sync` on the system Python 3.13.16, `zlib 1.3`), `UV_PYTHON_INSTALL_DIR=<scratch> UV_PYTHON_PREFERENCE=only-managed uv run --project pipeline --frozen python -c …`: `Using CPython 3.13.14 / Removed virtual environment / Creating virtual environment`, then `3.13.14 1.3.2`; the next `uv run` without the variables keeps that venv (no flip-back). Side observation: `uv python install` also puts a `python3.13` link in `~/.local/bin`, and with it on `PATH` a plain `uv sync` picks the managed Python by itself (my first attempt at the experiment did, which is why I redid it); I removed that link from this container.

### 3. Mutations (Appendix D): 26 saved diffs, 23 fail a named test, 3 pass the full pytest

Each applied alone to M, `git diff` saved, tested with `pytest pipeline/tests -k "surfaces or png or manifest or fix6"` (645 passed unmutated, 26-31 s), and the full `pytest pipeline/tests` for each that passed it; undone with `git apply -R`, `git status --short` empty after each (all 26 lines of the log). The first failing tests (file names without `test_` omitted where long):

| id | mutation | fails (named) |
|---|---|---|
| S1 | the step's PNG comparison removed | `fix6::test_a_png_that_is_not_the_configs_is_refused_naming_zlib`, `checks::test_a_png_of_other_bytes_is_refused_after_the_classes_and_before_anything_is_written` |
| S2 | the manifest's removed | `checks::test_the_png_is_compared_with_the_value_of_its_own_cell[0.5-0.5]`, `[1.0-1]`, `…_of_the_designed_classes_and_other_bytes_is_refused_naming_the_rebuild`, `…_that_is_not_the_one_the_config_expects_is_refused_whatever_it_holds` |
| S3a | config check accepts a missing `expected_png_sha256` | `fix6::test_a_config_without_well_formed_png_values_is_refused[None]`, `config::…refused_naming_where[…expected_png_sha256]` |
| S3b | upper-case value accepted | `config::…naming_where[…expected_png_sha256\['0.5'\] must be a SHA-256_1]` |
| **S3c** | **a 40-64 digit value accepted** | **none: full pytest 2228 passed (S-01)** |
| S3d | an extra cell in the PNG object accepted | `config::…[expected_png_sha256 holds only]`, `[the two must hold the same cells]` ×2 |
| S3e | a PNG cell the pixels object lacks accepted | `config::…[the two must hold the same cells]` ×2 |
| S3f | PNG object without the configured cell accepted | `fix6::…[value1]`, `config::…[expected_png_sha256 holds no value for]`, `[the two must hold the same cells]` ×2 |
| S3g | a non-string PNG value accepted | `config::…[expected_png_sha256\['0.5'\] must be a SHA-256_0, _1, _2]` |
| S4a | the comparison moved after the write | `fix6::test_a_png_that_is_not_the_configs_is_refused_naming_zlib`, `checks::…before_anything_is_written` |
| S4b | the output folder created before the comparison | `checks::…before_anything_is_written` only (as fix-6 said) |
| S5a | the writer not given the PNG (encoded twice) | `checks::test_the_png_is_encoded_once_and_is_the_one_written` |
| S5b | the PNG encoded before the classes are compared | `checks::test_the_classes_are_compared_before_the_png_is_encoded` |
| S5c | the PNG compared before the classes | the same test |
| **S6** | **the allowance restored (`written == {**block, "sha256": _sha(png)}`)** | **none unshimmed (full pytest 2228 passed: on the same machine it cannot show). Under shim 2: 8 failed, the nine above less `test_write_surfaces_writes_the_designed_files`, so the gate still fails** |
| X1 | the step compares the pixels' value for the PNG | 10 cases (`checks`×9, `step::test_the_step_writes_the_designed_classes`) |
| X2 | the manifest compares with the description's own `sha256` | the four `S2` cases |
| X3a / X3b | the step / the manifest reads `"0.2"` whatever the cell | `checks::test_the_png_is_compared_with_the_value_of_its_own_cell[0.5-0.5]`, `[1.0-1]` each |
| X4 | the manifest's PNG check before the pixel checks | 4: `checks::test_a_png_of_another_size_or_with_a_class_beyond_road_is_refused`, `test_pixels_that_are_not_the_configs_expected_classes_are_refused`, `step::test_a_row_written_with_another_filter_is_refused`, `test_other_classes_in_the_png_are_refused` |
| X5a | the encoder at level 6 | 12 (`fix6::test_this_machine_writes_the_designed_png_bytes`, `fixture::test_write_surfaces_writes_the_designed_files`, `test_one_level_9_stream_is_split_into_idat_chunks_of_at_most_1_mib`, …) |
| X5b | the IDAT chunk at 512 KiB | `fixture::test_one_level_9_stream_is_split_into_idat_chunks_of_at_most_1_mib` |
| X6 | the writer ignores the PNG it is given | `checks::test_the_png_is_encoded_once_and_is_the_one_written`, `fixture::test_write_surfaces_writes_the_png_it_is_given_and_encodes_nothing_again` |
| X7 | the step's refusal does not name the machine's zlib | `checks::…before_anything_is_written` (the pinned `test_a_png_that_is_not_the_configs_is_refused_naming_zlib` stays green: its `zlib.ZLIB_RUNTIME_VERSION in text` holds on a `1.3` machine through "zlib 1.3.x", as fix-6 Findings 5 said) |
| **X9** | **the shared regex `{64}` → `{40,64}`** | **none: full pytest 2228 passed (S-01)** |
| X8 | the manifest's refusal does not name `python -m mattini surfaces` | 27 cases |

The harms are the owner's: S1/S2 a zlib-ng machine's PNG and manifest accepted (R1 I-01); S3 a config without the key silently drops the check; S4 a refused run leaves another deflate's files (S4a) or a `surfaces/` folder (S4b); S5 150 MB compressed twice or for refused classes; X1/X3 a village built at 0.5 m compared with the 0.2 m value.

### 4. RELEASE.md §C: see S-02. The box is in the list, the surfaces line now says pixels and PNG bytes; its command was run on five manifests (table in S-02); on the real manifest it prints `OK` and exits 0 in `bash` and in `sh`.

### 5. The seam with trees.py

- `git diff d8d2471..da8914f -- pipeline/mattini/surfaces.py`: hunks at lines 43-55 (module docstring), 90, 188-250, 672-700, 735-842 and 855-975. An AST comparison of every top-level `def`, `class` and assignment of the two commits: removed `[]`, added `[]`, changed `AREA_CONFIG_KEYS`, `build_surfaces`, `built_surfaces_block`, `cell_key`, `check_surfaces_config`, `write_surfaces`. trees.py imports `BIG`, `LIMIT_MM`, `SurfacesError`, `_ceil_div`, `_floor_div`, `_Frame`, `_paint`, `_polygon_spans`, `_row_pairs`, `read_tlm`, `_snapped` (trees.py:84-98): none of them is in the changed list. manifest.py imports `SURFACES_CONFIG_NAME`, `SURFACES_CONFIG_PATH`, `SurfacesError`, `built_surfaces_block`, `load_surfaces_config`; `__main__.py` calls `build_surfaces` with the unchanged signature.
- Both orders on the real village, outputs `terrain`, `buildings`, `photo`, `roofs` copied from the baseline: `surfaces` then `trees` then `manifest`; `trees` then `surfaces` then `manifest`: all exit 0, each folder's 24 files byte-identical to the baseline, `manifest.json` `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`, 324'359 bytes, in both.

### 6. The real village, fresh clone, pinned inputs, from the command line

`terrain` (5 s), `buildings` (5 s), `photo` (45 s), `roofs` (27 s), `surfaces` (19 s, `the PNG has the SHA-256 config/surfaces.json expects, 8922edf9…`), `trees` (25 s), `manifest` (1 s): each exit 0. `game/assets/generated/manifest.json` 324'359 bytes, SHA-256 `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`. The same 24 files came out of every later run that was supposed to equal them (shim 1, shim 3, both orders), and the three PNGs the three-cell runs wrote on two zlib builds are byte-identical to each other.

### 7. fix-6's own claims, re-measured

Its Findings 1 (values), 3 (manifest `3ca0445c…`), 4 rows 1-11 (all except the "short value" half of row 11: S-01) and 5 (shim 2 nine failures, same nine) hold. Findings 2 (the remedy was run) holds and was run here with an existing venv (section 2). Findings 6 ("zlib 1.3.2 only at 0.2 m") is superseded: all three cells.

## Notes

- **Not measured, and the lens does not prove:** Windows' zlib (no Windows machine). A web search in this review (not a measurement) found a CPython commit, gh-91349, replacing zlib with zlib-ng in the Windows builds of Python 3.14; the project pins `requires-python = ">=3.13,<3.14"`, so it only matters on the day that pin is raised, and the step then refuses with the machine's zlib named (a `ZLIBNG_VERSION` constant exists from 3.14, absent otherwise). Source: https://code.everydayimshuflin.com/greg/cpython/commit/63a638c43f821e9c8b3256e7122c06e539dc585d (a mirror of the CPython commit). A real zlib-ng-linked Python (Fedora and similar): the shim stands for it (PyPI `zlib-ng` 1.0.0 = zlib-ng 2.2.5), as in R1. Distributions' zlib forks with other match finders (Chromium, Intel, Cloudflare) and macOS' system zlib: not measured. Other CPUs: not varied (two CPython builds and five source-built zlibs gave one answer, on this CPU).
- **Residue to state (not fixed, as ordered):** `tests/shared/surfaces_vectors.json` "about" still says the PNG's bytes are not pinned (design's file, stale since fix-6; already docs/ROADMAP.md:82); SPEC §8's config shape (S-03); `docs/briefs/M3-plan.md:234` and `docs/briefs/M3-06-the-surfaces-step.md:95,235` still say "checked for integrity only" (history, superseded by fix-6).
- **Two hops on a zlib-ng machine:** `manifest` over a foreign PNG says "`python -m mattini surfaces` rebuilds the surfaces"; on that same machine `surfaces` ends in the step's refusal and its remedy. Each message is true; neither is wrong, so not graded.
- **Method note:** my first remedy experiment (section 2) ran with the managed Python already first on `PATH` (the link `uv python install` writes), so its "existing system venv" was not one; I removed the link, rebuilt the venv on the system Python and redid it. The first RELEASE-box script was refused by the sandbox's safety check for an `rm -rf` of a glob I did not need; it was rerun without the removal.
- **Gate before the commit:** this report is the only file added, and the commit is chained to `tools/gate.sh`'s exit status on the checkout that holds it (BUILD.md rule 3c; lesson 18: a docs-only commit is not exempt).

## Appendix — scratch scripts (scratchpad of this session; the clones are removed)

### A. The shims (`sitecustomize.py` on `PYTHONPATH`; `shim/zngsite` is `uv pip install --target … zlib-ng==1.0.0`)  — site1 (the R1 lens's)

```python
"""R2 lens shim 1 = the R1 lens's: zlib.compress / zlib.compressobj written by zlib-ng 2.2.5
(PyPI zlib-ng 1.0.0). mattini is untouched; ZLIB_RUNTIME_VERSION stays the real one."""
import sys
sys.path.insert(0, "<scratch>/shim/zngsite")
import zlib
import zlib_ng.zlib_ng as _ng

zlib.compress = _ng.compress
zlib.compressobj = _ng.compressobj
```

### A2. site2 (shim 1 plus the version string)

```python
"""R2 lens shim 2 = shim 1 plus the version string a zlib-ng compat build reports of itself
(zlib-ng's zlib.h compat header: ZLIB_VERSION "1.3.1.zlib-ng"; taken from its header, not measured)."""
import sys
sys.path.insert(0, "<scratch>/shim/zngsite")
import zlib
import zlib_ng.zlib_ng as _ng

zlib.compress = _ng.compress
zlib.compressobj = _ng.compressobj
zlib.ZLIB_RUNTIME_VERSION = "1.3.1.zlib-ng"
```

### A3. site3 (any Python deflate writer raises)

```python
"""R2 lens shim 3: any call of zlib.compress / zlib.compressobj / gzip / zipfile compression in
Python raises, so a step that runs under it never writes a deflate stream through Python."""
import zlib

def _no(*a, **k):
    raise RuntimeError("DEFLATE WRITER CALLED")

zlib.compress = _no
zlib.compressobj = _no
```

### A4. probe_shim.py (the shims write other bytes: 872743 bytes with zlib 1.3, 804948 with the shim, on a 12 MB test array)

```python
import zlib, hashlib, sys
import numpy as np
rng = np.random.default_rng(7)
a = (rng.integers(0, 5, size=(3000, 4000)) * (rng.random((3000, 4000)) < 0.05)).astype(np.uint8)
a[:, ::50] = 3
d = a.tobytes()
c = zlib.compress(d, 9)
print(zlib.ZLIB_RUNTIME_VERSION, zlib.compress.__module__, len(c), hashlib.sha256(c).hexdigest()[:16])
```

### B. indep_png.py — the independent PNG check (imports nothing of mattini)

```python
"""R2 lens: an independent check of one surfaces PNG (imports nothing of mattini).

usage: indep_png.py <png> <config/surfaces.json> <cell-key>
Decodes the PNG with the standard library, checks the pixels' SHA-256 against the config's
expected_pixels_sha256[cell], writes the pixels again with its own PNG writer (8-bit grey, filter 0,
one zlib level-9 stream, IDAT chunks of at most 1 MiB), and compares that PNG's SHA-256 with
expected_png_sha256[cell] and with the file's own.  Prints zlib's version of the interpreter."""
import hashlib, json, struct, sys, zlib
import numpy as np

png_path, config_path, cell = sys.argv[1:4]
cfg = json.load(open(config_path))
(area,) = cfg["areas"].values()
want_px, want_png = area["expected_pixels_sha256"][cell], area["expected_png_sha256"][cell]
data = open(png_path, "rb").read()
assert data[:8] == b"\x89PNG\r\n\x1a\n"
at, idat, hdr = 8, [], None
while at < len(data):
    n, kind = struct.unpack(">I4s", data[at:at + 8]); body = data[at + 8:at + 8 + n]
    assert zlib.crc32(kind + body) == struct.unpack(">I", data[at + 8 + n:at + 12 + n])[0]
    if kind == b"IHDR": hdr = struct.unpack(">IIBBBBB", body)
    if kind == b"IDAT": idat.append(body)
    at += 12 + n
cols, rows = hdr[0], hdr[1]
raw = np.frombuffer(zlib.decompress(b"".join(idat)), dtype=np.uint8).reshape(rows, cols + 1)
assert not raw[:, 0].any(), "filter byte not 0"
pixels = np.ascontiguousarray(raw[:, 1:])
px = hashlib.sha256(pixels).hexdigest()
lines = np.zeros((rows, cols + 1), np.uint8); lines[:, 1:] = pixels
stream = zlib.compress(lines, 9)
def chunk(k, b): return struct.pack(">I", len(b)) + k + b + struct.pack(">I", zlib.crc32(k + b))
mine = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", cols, rows, 8, 0, 0, 0, 0))
for i in range(0, len(stream), 1 << 20): mine += chunk(b"IDAT", stream[i:i + (1 << 20)])
mine += chunk(b"IEND", b"")
mine_sha, file_sha = hashlib.sha256(mine).hexdigest(), hashlib.sha256(data).hexdigest()
print(f"zlib {zlib.ZLIB_RUNTIME_VERSION} | cell {cell} | {cols}x{rows} | file {len(data)} B")
print(f"  pixels  {px[:12]}  config {want_px[:12]}  {'==' if px == want_px else '!= PIXELS DIFFER'}")
print(f"  own PNG {mine_sha[:12]}  config {want_png[:12]}  file {file_sha[:12]}  "
      f"{'==' if mine_sha == want_png == file_sha else '!= PNG DIFFERS'}")
sys.exit(0 if (px == want_px and mine_sha == want_png == file_sha) else 1)
```

### C. zlib_versions.py — the village's PNGs under zlib 1.2.11, 1.2.13, 1.3, 1.3.1, 1.3.2 built from zlib.net sources (`./configure && make`, run with `python3 -I`)

```python
"""R2 lens: the village's PNG under zlib versions built from zlib.net sources, through ctypes compress2 level 9
(the same deflateInit defaults CPython's zlib.compress uses: windowBits 15, memLevel 8, default strategy)."""
import ctypes, hashlib, json, struct, sys, zlib
import numpy as np
S = sys.argv[1]
cfg = json.load(open(f"{S}/M/config/surfaces.json"))["areas"]["village"]["expected_png_sha256"]
def classes(path):
    data = open(path, "rb").read(); at, idat = 8, []
    while at < len(data):
        n, kind = struct.unpack(">I4s", data[at:at+8])
        if kind == b"IHDR": cols, rows = struct.unpack(">II", data[at+8:at+16])
        if kind == b"IDAT": idat.append(data[at+8:at+8+n])
        at += 12 + n
    raw = np.frombuffer(zlib.decompress(b"".join(idat)), np.uint8).reshape(rows, cols + 1)
    return np.ascontiguousarray(raw)            # scanlines, filter byte included
def chunk(k, b): return struct.pack(">I", len(b)) + k + b + struct.pack(">I", zlib.crc32(k + b))
def png(rows, cols, stream):
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", cols, rows, 8, 0, 0, 0, 0))
    for i in range(0, len(stream), 1 << 20): out += chunk(b"IDAT", stream[i:i + (1 << 20)])
    return out + chunk(b"IEND", b"")
cells = {k: classes(f"{S}/cells/M-{k}/surfaces/village.png") for k in ("0.2", "0.5", "1")}
def via(lib):
    z = ctypes.CDLL(lib); z.zlibVersion.restype = ctypes.c_char_p
    z.compress2.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.c_char_p, ctypes.c_ulong, ctypes.c_int]
    z.compressBound.restype = ctypes.c_ulong; z.compressBound.argtypes = [ctypes.c_ulong]
    def compress(a):
        src = a.tobytes(); n = ctypes.c_ulong(z.compressBound(len(src))); buf = ctypes.create_string_buffer(n.value)
        assert z.compress2(buf, ctypes.byref(n), src, len(src), 9) == 0
        return buf.raw[:n.value]
    return z.zlibVersion().decode(), compress
for ver in ("1.2.11", "1.2.13", "1.3", "1.3.1", "1.3.2"):
    name, compress = via(f"{S}/zbuild-{ver}/libz.so.{ver}")
    row = []
    for key, lines in cells.items():
        sha = hashlib.sha256(png(lines.shape[0], lines.shape[1] - 1, compress(lines))).hexdigest()
        row.append(f"{key}: {sha[:10]} {'==' if sha == cfg[key] else '!='}")
    print(f"zlib {name:7s} (built from zlib.net source) | " + " | ".join(row))
print("python's own zlib", zlib.ZLIB_RUNTIME_VERSION, "| design:", {k: v[:10] for k, v in cfg.items()})
```

### D1. mutate.py — the 26 mutations as exact replacements

```python
"""R2 lens: apply one mutation (a list of exact old->new replacements, each must match exactly once)
to a file of the throwaway clone; the caller saves `git diff` as the mutation's diff.
usage: mutate.py <clone> <name>   (mutations are defined in MUTATIONS below)"""
import pathlib, sys

SUR = "pipeline/mattini/surfaces.py"
STEP_CMP = """    if png_sha256 != expected_png:
        raise SurfacesError("""
MAN_CMP = """    if png_sha256 != expected_png:
        raise fail("""

M = {}
M["S1-step-png-comparison-removed"] = [(SUR, STEP_CMP, STEP_CMP.replace("if png_sha256 != expected_png:", "if False:"))]
M["S2-manifest-png-comparison-removed"] = [(SUR, MAN_CMP, MAN_CMP.replace("if png_sha256 != expected_png:", "if False:"))]
# --- config check
M["S3a-config-accepts-missing-png-key"] = [
    (SUR, 'AREA_CONFIG_KEYS = {"cell_m", "computed_for", "expected_pixels_sha256", "expected_png_sha256"}',
          'AREA_CONFIG_KEYS = {"cell_m", "computed_for", "expected_pixels_sha256"}\nOPTIONAL_KEYS = {"expected_png_sha256"}'),
    (SUR, 'set(area) != AREA_CONFIG_KEYS:', 'not (AREA_CONFIG_KEYS <= set(area) <= AREA_CONFIG_KEYS | OPTIONAL_KEYS):'),
    (SUR, '        for field in ("expected_pixels_sha256", "expected_png_sha256"):\n            expected = area[field]',
          '        for field in ("expected_pixels_sha256", "expected_png_sha256"):\n            if field not in area:\n                continue\n            expected = area[field]'),
    (SUR, '        if set(area["expected_png_sha256"]) != set(area["expected_pixels_sha256"]):',
          '        if "expected_png_sha256" in area and set(area["expected_png_sha256"]) != set(area["expected_pixels_sha256"]):'),
]
M["S3b-config-accepts-upper-case-png-value"] = [
    (SUR, '                if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):',
          '                if not (isinstance(value, str) and (SHA256_HEX.fullmatch(value) or (field == "expected_png_sha256" and re.fullmatch(r"[0-9a-fA-F]{64}", value)))):'),
]
M["S3c-config-accepts-short-png-value"] = [
    (SUR, '                if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):',
          '                if not (isinstance(value, str) and (SHA256_HEX.fullmatch(value) or (field == "expected_png_sha256" and re.fullmatch(r"[0-9a-f]{40,64}", value)))):'),
]
M["S3d-config-accepts-extra-png-cell"] = [
    (SUR, '            unknown = [key for key in expected if key not in CELL_KEYS]',
          '            unknown = [key for key in expected if key not in CELL_KEYS and field != "expected_png_sha256"]'),
    (SUR, '        if set(area["expected_png_sha256"]) != set(area["expected_pixels_sha256"]):',
          '        if False:'),
]
M["S3e-config-png-cell-the-pixels-object-lacks"] = [
    (SUR, '        if set(area["expected_png_sha256"]) != set(area["expected_pixels_sha256"]):', '        if False:'),
]
M["S3f-config-png-lacks-the-configured-cell"] = [
    (SUR, '            if cell_key(area["cell_m"]) not in expected:',
          '            if cell_key(area["cell_m"]) not in expected and field != "expected_png_sha256":'),
    (SUR, '        if set(area["expected_png_sha256"]) != set(area["expected_pixels_sha256"]):', '        if False:'),
]
M["S3g-config-png-value-not-a-string-type-check"] = [
    (SUR, '                if not (isinstance(value, str) and SHA256_HEX.fullmatch(value)):',
          '                if not (field == "expected_png_sha256" or (isinstance(value, str) and SHA256_HEX.fullmatch(value))):'),
]
# --- order
WRITE_CALL = "    block = write_surfaces(out_dir, area, grid, box, cell_m, world_sha256, source, png=png)\n"
STEP_BLOCK_START = "    if png_sha256 != expected_png:\n        raise SurfacesError(\n"
M["S4a-step-comparison-after-the-write"] = "SPECIAL"
M["S4b-folder-created-before-the-comparison"] = [
    (SUR, "    png = png_l8(grid)\n    png_sha256 = hashlib.sha256(png).hexdigest()\n    if png_sha256 != expected_png:",
          "    (Path(out_dir) / 'surfaces').mkdir(parents=True, exist_ok=True)\n    png = png_l8(grid)\n    png_sha256 = hashlib.sha256(png).hexdigest()\n    if png_sha256 != expected_png:"),
]
M["S5a-png-encoded-twice-writer-not-given-png"] = [(SUR, "source, png=png)\n", "source)\n")]
M["S5b-png-encoded-before-the-classes-are-compared"] = [
    (SUR, "    pixels_sha256 = hashlib.sha256(grid).hexdigest()\n    if pixels_sha256 != expected:",
          "    png = png_l8(grid)\n    pixels_sha256 = hashlib.sha256(grid).hexdigest()\n    if pixels_sha256 != expected:"),
    (SUR, "    png = png_l8(grid)\n    png_sha256 = hashlib.sha256(png).hexdigest()\n    if png_sha256 != expected_png:",
          "    png_sha256 = hashlib.sha256(png).hexdigest()\n    if png_sha256 != expected_png:"),
]
M["S5c-png-compared-before-the-classes"] = "SPECIAL"
# --- the right cell / the right value
M["X1-step-compares-the-pixels-value-not-the-png-value"] = [
    (SUR, '    expected_png = settings["expected_png_sha256"][cell_key(cell_m)]\n    if area not in world.areas:',
          '    expected_png = settings["expected_pixels_sha256"][cell_key(cell_m)]\n    if area not in world.areas:'),
]
M["X2-manifest-compares-with-the-descriptions-own-sha256"] = [
    (SUR, '    expected_png = settings["expected_png_sha256"][cell_key(cell_m)]\n    if png_sha256 != expected_png:\n        raise fail(',
          '    expected_png = block["sha256"]\n    if png_sha256 != expected_png:\n        raise fail('),
]
M["X3a-step-reads-the-0.2-png-value-whatever-the-cell"] = [
    (SUR, '    expected_png = settings["expected_png_sha256"][cell_key(cell_m)]\n    if area not in world.areas:',
          '    expected_png = settings["expected_png_sha256"]["0.2"]\n    if area not in world.areas:'),
]
M["X3b-manifest-reads-the-0.2-png-value-whatever-the-cell"] = [
    (SUR, '    expected_png = settings["expected_png_sha256"][cell_key(cell_m)]\n    if png_sha256 != expected_png:\n        raise fail(',
          '    expected_png = settings["expected_png_sha256"]["0.2"]\n    if png_sha256 != expected_png:\n        raise fail('),
]
M["X4-manifest-png-check-before-the-pixel-checks"] = "SPECIAL"
M["X5a-encoder-level-9-to-6"] = [(SUR, "stream = zlib.compress(scanlines, 9)", "stream = zlib.compress(scanlines, 6)")]
M["X5b-idat-chunk-1-mib-to-512-kib"] = [(SUR, "_chunk(b\"IDAT\", stream[at : at + MIB]) for at in range(0, len(stream), MIB)", "_chunk(b\"IDAT\", stream[at : at + MIB // 2]) for at in range(0, len(stream), MIB // 2)")]
M["X6-writer-ignores-the-png-it-is-given"] = [(SUR, "    if png is None:\n        png = png_l8(grid)\n", "    png = png_l8(grid)\n")]
M["X7-step-refusal-does-not-name-the-machine-zlib"] = [(SUR, "so this machine's (zlib {zlib.ZLIB_RUNTIME_VERSION}) or this code writes other \"", "so this machine's or this code writes other \"")]
FIX = "pipeline/tests/test_surfaces_fixture.py"
M["S6-fixture-allowance-restored"] = [
    (FIX, '    assert written == block, "the whole description, the PNG\'s SHA-256 too, is design\'s"\n    assert _sha(png) == block["sha256"], f"this machine\'s zlib {zlib.ZLIB_RUNTIME_VERSION}"\n',
          '    assert written == {**block, "sha256": _sha(png)}, "only the PNG\'s own SHA-256 may differ"\n'),
]
M["X9-shared-sha256-regex-accepts-40-to-64-digits"] = [(SUR, 'SHA256_HEX = re.compile(r"[0-9a-f]{64}")', 'SHA256_HEX = re.compile(r"[0-9a-f]{40,64}")')]
M["X8-manifest-refusal-does-not-name-rebuild-command"] = [(SUR, "f\"{description}: {message}; `{SURFACES_COMMAND}` rebuilds the surfaces\"", "f\"{description}: {message}\"")]


def special(name: str, text: str) -> str:
    if name == "S4a-step-comparison-after-the-write":
        start = text.index("    png = png_l8(grid)\n    png_sha256 = hashlib.sha256(png).hexdigest()\n    if png_sha256 != expected_png:")
        end = text.index("    say(f\"the PNG has the SHA-256")
        compare = text[start:end]
        text = text[:start] + text[end:]
        head = "    png = png_l8(grid)\n    png_sha256 = hashlib.sha256(png).hexdigest()\n"
        wcall = "    block = write_surfaces(out_dir, area, grid, box, cell_m, world_sha256, source, png=png)\n"
        i = text.index(wcall)
        return text[:i] + head + text[i:wcall and i + len(wcall)] + compare.replace(head, "") + text[i + len(wcall):]
    if name == "S5c-png-compared-before-the-classes":
        pix = text.index("    pixels_sha256 = hashlib.sha256(grid).hexdigest()\n    if pixels_sha256 != expected:")
        pix_end = text.index("    say(f\"the classes have the SHA-256")
        pix_block = text[pix:pix_end]
        text = text[:pix] + text[pix_end:]
        start = text.index("    png = png_l8(grid)\n    png_sha256 = hashlib.sha256(png).hexdigest()\n    if png_sha256 != expected_png:")
        end = text.index("    say(f\"the PNG has the SHA-256")
        return text[:start] + text[start:end] + pix_block + text[end:]
    if name == "X4-manifest-png-check-before-the-pixel-checks":
        m_start = text.index("    expected_png = settings[\"expected_png_sha256\"][cell_key(cell_m)]\n    if png_sha256 != expected_png:\n        raise fail(")
        m_end = text.index("    return block\n", m_start)
        move = text[m_start:m_end]
        text = text[:m_start] + text[m_end:]
        anchor = "    try:\n        pixels = read_png_l8(data)\n"
        i = text.index(anchor)
        return text[:i] + move + text[i:]
    raise SystemExit("unknown special " + name)


if __name__ == "__main__":
    clone, name = pathlib.Path(sys.argv[1]), sys.argv[2]
    spec = M[name]
    if spec == "SPECIAL":
        p = clone / SUR
        p.write_text(special(name, p.read_text()))
    else:
        for rel, old, new in spec:
            p = clone / rel
            t = p.read_text()
            assert t.count(old) == 1, (name, rel, t.count(old), old[:70])
            p.write_text(t.replace(old, new))
    print("mutated:", name)
```

### D2. runmut.sh — apply, save the diff, run the fast subset (then the full pytest if nothing failed), undo with `git apply -R`

```bash
#!/bin/bash
# usage: runmut.sh <mutation-name> [shim-dir]   -- apply, save diff, run the fast subset (full pytest if no failure), undo with git apply -R
S=<scratch>
n=$1; site=$2
cd $S/M
[ -z "$(git status --short)" ] || { echo "CLONE NOT CLEAN"; git status --short; exit 9; }
python3 $S/scripts/mutate.py $S/M $n >/dev/null || exit 9
git diff > $S/mut/$n.diff
python3 -m py_compile pipeline/mattini/surfaces.py || { echo "SYNTAX ERROR in mutant"; git apply -R $S/mut/$n.diff; exit 9; }
export PYTHONPATH=${site:+$S/shim/$site}
fast=$($S/M/pipeline/.venv/bin/python -m pytest pipeline/tests -q -p no:cacheprovider --tb=no -rf -k "surfaces or png or manifest or fix6" 2>&1)
failed=$(echo "$fast" | grep -E "^FAILED" | sed 's/^FAILED pipeline\/tests\///; s/ - .*//')
summary=$(echo "$fast" | grep -E "passed|failed" | tail -1)
echo "### $n  [${site:-no shim}]"
echo "    fast subset: $summary"
if [ -n "$failed" ]; then echo "$failed" | head -12 | sed 's/^/      FAILS  /'; [ $(echo "$failed" | wc -l) -gt 12 ] && echo "      ... $(echo "$failed" | wc -l) failing in all"
else
  echo "    fast subset passed -> full pytest"
  full=$($S/M/pipeline/.venv/bin/python -m pytest pipeline/tests -q -p no:cacheprovider --tb=no -rf 2>&1)
  echo "    full: $(echo "$full" | grep -E "passed|failed" | tail -1)"
  echo "$full" | grep -E "^FAILED" | sed 's/^FAILED pipeline\/tests\///; s/ - .*//' | sed 's/^/      FULL-FAILS  /'
fi
git apply -R $S/mut/$n.diff
echo "    undone: git status --short -> [$(git status --short)]"
```

### E1. cells.sh — three cells × two zlib builds

```bash
#!/bin/bash
# for each clone (M = system zlib 1.3, V = uv managed zlib 1.3.2) and each cell: edit cell_m in the clone's
# config copy, run `surfaces` on the real inputs, then check the PNG with the independent script under both pythons.
S=<scratch>
for R in M V; do
  for cell in 0.2 0.5 1; do
    cd $S/$R
    sed -i "s/\"cell_m\": [0-9.]*,/\"cell_m\": $cell,/" config/surfaces.json
    grep -m1 '"cell_m"' config/surfaces.json
    out=$S/cells/$R-$cell; rm -rf $out
    s0=$(date +%s)
    $S/$R/pipeline/.venv/bin/python -m mattini surfaces --raw $S/A/data/raw --out $out > $S/cells/$R-$cell.log 2>&1; rc=$?
    echo "== clone $R ($($S/$R/pipeline/.venv/bin/python -c 'import zlib;print("zlib",zlib.ZLIB_RUNTIME_VERSION)')) cell $cell: rc=$rc $(( $(date +%s)-s0 )) s"
    grep -E "^the (classes|PNG) have|^mattini: error" $S/cells/$R-$cell.log | cut -c1-200
    ls -l $out/surfaces/village.png | awk '{print "   png bytes", $5}'; sha256sum $out/surfaces/village.png | cut -c1-64
    for P in M V; do $S/$P/pipeline/.venv/bin/python $S/scripts/indep_png.py $out/surfaces/village.png $S/$R/config/surfaces.json $cell | sed 's/^/   [indep under '$P'] /'; done
    git checkout -q config/surfaces.json; git status --short
  done
done
```

### E2. fixture_cells.py — the fixture PNG at 0.2, 0.5 and 1 m

```python
import hashlib, sys, tempfile, zlib
from pathlib import Path
REPO = Path(sys.argv[1]); sys.path.insert(0, str(REPO / "pipeline" / "tests"))
from test_surfaces_checks import _build, _case
from test_m3_r1_fix6_png_bytes import FIXTURE_PNG_SHA256
print("zlib", zlib.ZLIB_RUNTIME_VERSION)
for cell, key in ((0.2, "0.2"), (0.5, "0.5"), (1.0, "1")):
    with tempfile.TemporaryDirectory() as tmp:
        case = _case(Path(tmp)); case.config["areas"]["fixture"]["cell_m"] = cell
        block = _build(case)
        png = (case.out / "surfaces" / "fixture.png").read_bytes()
        sha = hashlib.sha256(png).hexdigest()
        print(f"  fixture cell {key:>3}: {len(png):5d} B  {sha[:16]}  design {FIXTURE_PNG_SHA256[key][:16]}  {'==' if sha == FIXTURE_PNG_SHA256[key] == block['sha256'] else '!= DIFFERS'}")
```

### E3. lesson41.sh — which message after a changed world, lock or stored value

```bash
#!/bin/bash
# lesson 41: which message does the owner get after a changed world / republished input / a wrong stored value?
S=<scratch>
cd $S/V; PY=$S/V/pipeline/.venv/bin/python
flip() { python3 - "$1" "$2" "$3" <<'PY'
import sys, re
path, anchor, mode = sys.argv[1:4]
t = open(path).read()
i = t.index(anchor)
if mode == "hex":                      # flip the first hex digit of the first 64-hex string after the anchor
    m = re.compile(r'"[0-9a-f]{64}"').search(t, i)
    s = m.start() + 1
    t = t[:s] + ("0" if t[s] != "0" else "1") + t[s + 1:]
elif mode == "origin":
    t = t.replace('"e": 2623000.0,\n    "n": 1096000.0', '"e": 2623100.0,\n    "n": 1096000.0', 1)
open(path, "w").write(t)
PY
}
show() { sed "s#$S#\$S#g" | cut -c1-420; }
case1() { echo "=== $1"; shift; "$@" 2>&1 | grep -E "^mattini: error|Traceback|wrote|^the (classes|PNG)" | show; echo "   rc=${PIPESTATUS[0]}"; git checkout -q config; git -C $S/V status --short; }
step() { $PY -m mattini surfaces --raw $S/A/data/raw --out $S/l41out; }
rm -rf $S/l41out
flip config/world.json x origin;                                    case1 "STEP: world origin changed (computed_for)" step
flip config/datasets.lock.json '"swisstlm3d"' hex;                  case1 "STEP: TLM lock digit flipped (republished input adopted)" step
flip config/surfaces.json '"expected_pixels_sha256"' hex;           case1 "STEP: expected_pixels_sha256[0.2] wrong" step
flip config/surfaces.json '"expected_png_sha256"' hex;              case1 "STEP: expected_png_sha256[0.2] wrong" step
flip config/surfaces.json '"expected_pixels_sha256"' hex; flip config/surfaces.json '"expected_png_sha256"' hex
                                                                    case1 "STEP: both wrong" step
echo "--- exists after refusals?"; ls $S/l41out 2>&1 | head -2
# manifest side, on a copy of the good outputs
man() { $PY -m mattini manifest --out $S/l41man; }
mkdir -p $S/l41man_src; [ -d $S/l41man_src/surfaces ] || cp -a $S/base-out/. $S/l41man_src/
fresh() { rm -rf $S/l41man; cp -a $S/l41man_src $S/l41man; }
fresh; flip config/world.json x origin;                             case1 "MANIFEST: world origin changed" man
fresh; flip config/datasets.lock.json '"swisstlm3d"' hex;           case1 "MANIFEST: TLM lock digit flipped" man
fresh; flip config/surfaces.json '"expected_pixels_sha256"' hex;    case1 "MANIFEST: expected_pixels_sha256[0.2] wrong" man
fresh; flip config/surfaces.json '"expected_png_sha256"' hex;       case1 "MANIFEST: expected_png_sha256[0.2] wrong" man
fresh; flip config/surfaces.json '"expected_pixels_sha256"' hex; flip config/surfaces.json '"expected_png_sha256"' hex
                                                                    case1 "MANIFEST: both wrong" man
```

### E4. owncell.sh — the 0.2 value in the configured cell's place

```bash
#!/bin/bash
S=<scratch>
cd $S/V; PY=$S/V/pipeline/.venv/bin/python
V02=8922edf904e3e4e1de40c65daf1af1aae3474d71481d628a548152ce5b843e12
for cell in 0.5 1; do
  sed -i "s/\"cell_m\": [0-9.]*,/\"cell_m\": $cell,/" config/surfaces.json
  # the 0.2 value in the configured cell's place
  python3 - $cell $V02 <<'PY'
import json, sys
cell, v = sys.argv[1], sys.argv[2]
p = "config/surfaces.json"; d = json.load(open(p)); a = d["areas"]["village"]
a["expected_png_sha256"][cell] = v
open(p, "w").write(json.dumps(d, indent=2) + "\n")
PY
  echo "=== STEP at cell $cell with the 0.2 value in expected_png_sha256[$cell]"
  $PY -m mattini surfaces --raw $S/A/data/raw --out $S/owncell-$cell 2>&1 | grep -E "^mattini: error|^the PNG|wrote" | sed "s#$S#\$S#g" | cut -c1-330; echo "   rc=${PIPESTATUS[0]}; out folder: $(ls $S/owncell-$cell 2>&1 | head -1)"
  echo "=== MANIFEST over the good cell-$cell PNG with the same wrong config"
  rm -rf $S/owncell-man-$cell; cp -a $S/cells/V-$cell $S/owncell-man-$cell
  $PY -m mattini manifest --out $S/owncell-man-$cell 2>&1 | sed "s#$S#\$S#g" | cut -c1-330; echo "   rc=${PIPESTATUS[0]}"
  git checkout -q config
  # the other cell's slot (0.2) corrupted: must make no difference at this cell
  sed -i "s/\"cell_m\": [0-9.]*,/\"cell_m\": $cell,/" config/surfaces.json
  python3 - $cell <<'PY'
import json, sys
cell = sys.argv[1]; p = "config/surfaces.json"; d = json.load(open(p)); a = d["areas"]["village"]
a["expected_png_sha256"]["0.2"] = "0" * 64
open(p, "w").write(json.dumps(d, indent=2) + "\n")
PY
  echo "=== MANIFEST at cell $cell with expected_png_sha256[0.2] = 000... (another cell's value): must still pass"
  rm -rf $S/owncell-man-$cell; cp -a $S/cells/V-$cell $S/owncell-man-$cell
  $PY -m mattini manifest --out $S/owncell-man-$cell 2>&1 | sed "s#$S#\$S#g" | cut -c1-200; echo "   rc=${PIPESTATUS[0]}"
  git checkout -q config; git status --short
done
```

