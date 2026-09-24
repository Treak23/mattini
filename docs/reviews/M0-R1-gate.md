# Review M0 R1 — lens `gate` (Tier 2)

- **Lens:** `gate`. It covers `tools/gate.sh` and `tools/gate_allowlist.txt`,
  `.claude/hooks/session-start.sh`, `pipeline/pyproject.toml` and the pytest configuration,
  the repo-hygiene tests, the Godot project and GUT, the download's error paths, licence and
  attribution, and the seam between M0-01 and M0-03.
- **Range:** `git diff 366b0b5..a8cfa63 -- . ':!game/addons' ':!pipeline/uv.lock'`. The
  session-start hook predates the range (`b04347a`) and was reviewed as it runs today.
- **Head reviewed:** `a8cfa63`. `main` was at `d643870` when this was written. Every change
  since `a8cfa63` is under `docs/`.
- **Date:** 2026-09-24.
- **How:** every mutation and every Godot run happened in one detached worktree at `a8cfa63`
  in the session's scratch directory. One build ran at a time, each mutation in its own run.
  A scratch file was deleted after its run; an edit was saved as a diff and undone with
  `git apply -R`. `git status` in the worktree was clean after each run. The worktree has
  been removed, and the main checkout was never touched.
- **Baseline** in that fresh worktree: `tools/gate.sh` exit 0 in 16 s. 209 pytest passed
  and 2 network tests were deselected; 13 GUT tests passed with 943 asserts.

**Result:** no P0 and no P1. The gate fails as claimed on every class the round named:
a failing pytest, a failing GUT test, a GUT script that cannot load, a GDScript parse error,
a Godot error line at import, a lint error and a formatting error, in both languages
(table under "Checked and clean"). There are six P2s and four P3s. The P2s are ways to
turn a gate check off, or to end the GUT run early, that the proved mechanisms do not
cover, and one stale-provenance state:
- one malformed allowlist line switches off every scan;
- a test that quits the scene tree ends the GUT run green;
- engine errors in `before_all` / `after_all` pass;
- a `game/.gutconfig.json` can switch GUT's error tracking off;
- in cloud sessions, the import check rests entirely on `valid=false`;
- a failed re-run leaves a `provenance.json` that lists a file it deleted.

## Findings

### M0-R1-G-01 · P2 · An allowlist entry with an empty or blank text turns off every scan

- **Where:** `tools/gate.sh:46`. The line `*" # "?*) printf '%s\n' "${line%% # *}"` accepts
  any line that contains ` # ` followed by at least one character. Then `tools/gate.sh:66`
  runs `grep -v -F -f "$allowed"`.
- **Claim:** the entry ` # reason` (one leading space) yields the text `""`, and the entry
  `  # reason` yields `" "`. The empty pattern matches every line, and the space pattern
  matches every line with a space in it. So `grep -v` drops every scanned line, in the
  import, parse-check and GUT steps alike. The gate's header (`:11`) and M0-03 Findings 7
  say that blank lines "never reach grep (an empty pattern matches every line)". Run h
  proved that guard for blank lines only. This is the same harm through a second mechanism
  (lesson 10).
- **Proof** (full `tools/gate.sh`, one mutation per run):
  - `a2-control`: add `game/tests/test_scratch_node.gd` (`extends Node`) with the allowlist
    empty. Exit 1 at `gut`: `[WARNING]:  Ignoring script res://tests/test_scratch_node.gd
    because it does not extend GutTest`.
  - `a2`: the same, with the allowlist set to
    ` # Terrain3D prints a benign line at import`. Exit 0, `== gate: all steps passed`. The
    log still holds the `Ignoring script` line, followed by `---- All tests passed! ----`.
  - `a3`: the same, with the allowlist set to `  # reason`. Exit 0, all steps passed.
  - `a1`: a corrupt PNG, with the allowlist set to ` # …`. Exit 1, but only from the
    `valid=false` check (`imports marked valid=false`). The import scan printed no
    `error lines in the output`, so it had been switched off as well.
- **Harm:** one malformed allowlist line, a likely typo once M1 adds entries for
  Terrain3D, and a skipped test script or a GUT run that ran nothing ships green. The owner
  then gets game code whose tests never ran.
- **Fix:** in `allowed_texts`, refuse an entry whose text part is empty or all whitespace,
  with the same message style as the missing-reason case, and add a mutation row for it.
  Unambiguous, and inside the arc's scope (M0-03, `tools/gate.sh`). A non-empty entry that
  is too broad (for example `ERROR # …`) still allows everything it matches; that remains
  a review matter.

### M0-R1-G-02 · P2 · A test that quits the scene tree ends the GUT run early, and the gate passes (extends: "GUT fails on `[ERROR]`")

- **Where:** `tools/gate.sh:111-113`. The GUT step passes whenever Godot exits 0 and no
  scanned line appears. It does not require GUT's final summary line
  (`game/addons/gut/summary.gd:131-149`).
- **Claim:** if code under test calls `get_tree().quit()`, Godot exits 0 at the end of that
  frame. No later test script runs, and GUT prints no summary. The header (`:6-8`) and
  M0-03 run g cover a GUT run that "runs nothing at all" (`[ERROR]: Nothing was run.`).
  A run that stops partway is the same harm through a mechanism run g does not reach.
- **Proof:** `q1` added `game/tests/test_aaa_quit.gd`, which sorts first. Its one test
  calls `get_tree().quit()`, waits two frames, then asserts true. Result: exit 0,
  `== gate: all steps passed`. The GUT output ends after
  `* test_a_scene_that_quits_the_game`, followed by only `WARNING: ObjectDB instances
  leaked` and `ERROR: 3 resources still in use at exit`. There is no `Tests` line and no
  `All tests passed!`. None of the 13 real tests ran, including the pinned coordinate
  tests.
- **Harm:** `test_main_scene.gd` instantiates `res://main.tscn` and runs it for two frames.
  M1 gives the main scene its first script (terrain and the free-fly camera). Any quit that
  script reaches headless, for example "quit when something is missing", would silently
  skip every later test script, and the owner would get a green gate over untested
  coordinate code.
- **Fix:** have the GUT step require GUT's final `---- … ----` summary line (plus a
  `Tests` count above 0). The requirement itself is unambiguous and inside scope. Which
  summary counts as a pass is design's call: `All tests passed!` only, or also
  `N pending/risky tests.`. GUT exits 0 on pending and risky tests (tests with no asserts),
  so requiring `All tests passed!` would also make those fail the gate.

### M0-R1-G-03 · P2 · Engine errors outside a test body (`before_all`, `after_all`) pass the gate

- **Where:**
  - `tools/gate.sh:111`: the GUT step does not scan for `^ERROR`, on purpose (M0-03
    Findings 11).
  - `game/addons/gut/gut.gd:624`: GUT's error tracker fails only the test that was running
    (`should_test_fail_from_errors(test_id)`).
  - `CLAUDE.md:27-28` says "the gate also fails on error lines in Godot's output".
- **Claim:** an engine error raised in `before_all` (or, by the same code path,
  `after_all`, not run) belongs to no test. No test fails, and the GUT step's scan does not
  look for it. CLAUDE.md's sentence holds for the import and parse-check steps, but not for
  the GUT step.
- **Proof:** `h3` added a scratch test whose `before_all()` runs
  `load("res://assets/missing_heightmap.res")`, plus one unrelated passing test. The GUT
  step printed `ERROR: Cannot open file 'res://assets/missing_heightmap.res'.` and
  `ERROR: Failed loading resource: res://assets/missing_heightmap.res.`, then
  `Passing Tests 14` and `---- All tests passed! ----`. The gate exited 0.
- **Harm:** consumers exist today. `test_world_config_refusals.gd:23-30` and
  `test_world_config_transforms.gd:13-20` set up and tear down their scratch folders in
  these hooks. M1's terrain tests are the natural place to load a heightmap or a Terrain3D
  node once in `before_all`. A missing or broken resource would then print ERROR lines
  while the tests pass.
- **Fix:** not unambiguous; design's call. The options:
  - (a) scan `^ERROR` in the GUT step and except the refusal tests' deliberate
    `ERROR: WorldConfig: user://test_world_config_` lines. The allowlist is global, so
    that entry would also apply to the import and parse steps; harmless today.
  - (b) make every hook assert on what it did, which is weaker because it relies on
    discipline.
  - Either way, reword CLAUDE.md:27-28 to say what the GUT step catches.

### M0-R1-G-04 · P2 · A committed `game/.gutconfig.json` can switch GUT's error tracking off, and the gate lets it

- **Where:**
  - `tools/gate.sh:111-113` does not pass `-gconfig=`.
  - `game/addons/gut/gut_config.gd:20` and `cli/gut_cli.gd:119`: GUT loads
    `res://.gutconfig.json` by default.
  - `gut_config.gd:57` sets `failure_error_types = ["engine", "gut", "push_error"]`.
  - `brain.md:64` (H4): "never switch GUT's error tracking off globally".
- **Claim:** brain.md states the H4 rule, but nothing enforces it (lesson 2). A single
  committed JSON file switches error tracking off for every test.
- **Proof** (full gate):
  - `e1-control`: a scratch test loads a missing resource in its body and never checks the
    result. Exit 1 at `gut`: `[Failed]:  Unexpected Errors:`.
  - `e2`: the same, plus `game/.gutconfig.json` holding `{"failure_error_types": []}`.
    Exit 0: `Passing Tests 14`, `All tests passed!`.
  - The fix, measured: the same GUT command with `-gconfig=` appended.
    - `e3`: the `e2` tree. Exit 1 at `gut`, `Failing Tests 1`.
    - `e4`: the clean tree. Exit 0, 13 passing.
- **Harm:** in M1, Terrain3D's deprecation warning fails GUT (brain.md H4). The quickest
  wrong fix is exactly this file. Every engine error and `push_error` in the game's tests
  would then pass the gate.
- **Fix:** add `-gconfig=` to the gate's GUT command, so that only the command line
  configures GUT. One flag. Unambiguous, and inside the arc's scope (M0-03,
  `tools/gate.sh`). CLAUDE.md's Build & Test line could carry the same flag, which is
  design's call.

### M0-R1-G-05 · P2 · In every fresh cloud session, the import step catches a broken asset only through `valid=false` (extends: "import fails on any `valid=false` `.import` file")

- **Where:**
  - `.claude/hooks/session-start.sh:50`: the warm-up `--import`, with its output sent to
    `/dev/null`.
  - `tools/gate.sh:83-89`: the `valid=false` check.
- **Claim:** Godot prints an import error only on the run that imports the file (M0-03
  run c2). The hook's warm-up is that run in every new cloud container, and it discards
  the output. From then on the gate's import scan sees nothing, and `valid=false` is the
  only detector. The board treats the check as a re-run nicety ("ratify or remove"). In
  cloud sessions it is the whole import step.
- **Proof:**
  - `k1`: corrupt PNG added, `game/.godot` removed, then the hook's warm-up command run
    verbatim (exit 0). The gate then exited 1 at `godot import` with only
    `imports marked valid=false: game/corrupt_mutation.png.import`. The gate log holds 0
    `^ERROR` lines.
  - `k2`: the same, with the `valid=false` block removed from `tools/gate.sh` (saved diff).
    Exit 0, `== gate: all steps passed`.
- **Harm:** remove the check at the close and a broken asset passes every cloud builder's
  gate. One example is a texture the owner commits from their PC. Even with the check in
  place, the failure names the file but not Godot's reason, which went to `/dev/null`. The
  builder must delete the `.import` file and import again to see it.
- **Fix:** ratify the check; do not remove it. Record H1's second half in brain.md
  §Hazards, naming the hook's warm-up as a trigger. Optionally, send the warm-up's output
  to a log file instead of `/dev/null`. Ratifying is unambiguous. The hazards text and the
  hook are design's.

### M0-R1-G-06 · P2 · After a failed re-run, `provenance.json` still lists a file the run deleted

- **Where:** `pipeline/mattini/download.py:91-94`. A damaged or stale file is unlinked and
  then fetched again. `:106`: `provenance.json` is rewritten only after every tile
  succeeds, and a failure never removes the previous one.
- **Claim:** if the re-fetch fails, the run exits 1 and names the tile (good). But the
  previous `provenance.json` stays in place, and it claims a verified file that is no
  longer on disk. This is the reverse of the coordinates lens's M0-R1-C-05 (files on disk
  that provenance does not list).
- **Proof:** a scratch script ran the real `download_terrain` with fake fetchers:
  1. A clean six-tile run.
  2. The 2623-1096 file overwritten with `b"damaged"`.
  3. A second run whose `fetch_file` raises `ConnectionResetError`.

  Output: `DownloadError: tile 2623-1096: …: fetch failed: network dropped (after 2
  attempts)`. `provenance.json` still there and unchanged: 6 tiles listed, 5 files on disk.
  Listed but missing: `swissalti3d_2024_2623-1096_0.5_2056_5728.tif`. A tile swisstopo
  republishes, whose re-fetch then fails (M0-04 Findings 7), ends in the same state.
- **Harm:** M1's terrain step is the first consumer. If it trusts `provenance.json`, which
  is one of C-05's options, it meets a listed file that is missing. If it lists the folder
  instead, it builds a village with a missing tile, while provenance claims six verified
  files. Either way the on-disk state after the error is not honest (Hard Rule 2).
- **Fix:** delete `provenance.json` at the start of `download_terrain`, before the first
  unlink or fetch, so that only a completed run leaves one. Add a test that a failed
  re-run leaves no `provenance.json`. Unambiguous, and inside the arc's scope (M0-04:
  `download.py`, `test_download_*.py`).

### M0-R1-G-07 · P3 · A NUL byte in a step's output blinds its scan (the end-to-end run is unproved)

- **Where:** `tools/gate.sh:66`, `grep -E "$pattern" "$out"`, without `-a`.
- **Claim:** GNU grep 3.11 treats a file that contains a NUL byte as binary. It then prints
  `binary file matches` on stderr instead of the matching lines, and exits 0, so `found`
  is empty.
- **Proof:** measured on the container's grep, with a file holding an `Ignoring script`
  line and a NUL. Under POSIX, C.UTF-8 and en_US.UTF-8 alike: rc=0, stdout empty, stderr
  `grep: nul.txt: binary file matches`. Godot's own `print` replaces NUL with U+FFFD
  (`print("A" + String.chr(0) + "B")` came out as `A\357\277\275B`), so only raw native
  output can trigger this, for example a GDExtension such as Terrain3D (M1). No end-to-end
  gate run was made.
- **Harm:** unproved. Native output carrying a NUL would switch off that step's scan
  silently.
- **Fix:** `grep -a -E`. Unambiguous, and inside scope.

### M0-R1-G-08 · P3 · The pinned hygiene test called "stay tracked" checks only "not ignored"

- **Where:** `pipeline/tests/test_repo_hygiene.py:69-70`, a pinned copy (M0-01).
- **Proof:** `git rm --cached pipeline/uv.lock tools/gate.sh config/datasets.json` staged
  the three deletions. `pytest pipeline/tests/test_repo_hygiene.py` then gave 21 passed.
  Restored with `git reset`; the tree was clean afterwards.
- **Harm:** a commit that drops the lockfile, the gate or the datasets config from git
  passes the gate. The owner's next fresh clone lacks them. The gate on that clone would
  then fail, but only later, and far from the cause.
- **Fix:** for the listed paths that exist, also assert `git ls-files --error-unmatch`.
  `game/addons/terrain_3d/…` is not vendored yet and keeps the ignore check only. It is a
  pinned test, so the change is design's.

### M0-R1-G-09 · P3 · The gate never checks which Godot it runs (harm unproved)

- **Where:** `tools/gate.sh:18` (`GODOT="${GODOT:-godot}"`). `grep -n -i version
  tools/gate.sh` finds nothing, and no test reads `Engine.get_version_info()`.
- **Claim:** the Godot scans match line prefixes measured on 4.6.3; M0-03's own
  does-NOT-prove line says so. The hook pins 4.6.3 in containers. On the owner's PC the gate
  runs whatever `godot` or `$GODOT` is, and nothing says so.
- **Harm:** unproved. With another Godot on the owner's PC, errors might print in a format
  the gate does not scan for, and the gate would pass unchanged.
- **Fix:** a first Godot step that requires `$GODOT --version` to start with `4.6.3.stable`.
  Unambiguous, and inside scope.

### M0-R1-G-10 · P3 · A worktree does not isolate Godot's `user://` (the race is unproved)

- **Where:** the GUT output reads `[INFO]:  using [/root/.local/share/godot/app_userdata/
  mattini] for temporary output.` That is the same path in every checkout of the project
  (checked in two runs). The refusal and transform tests create and delete
  `user://test_world_config_*` in `before_all` and `after_all`.
- **Claim:** two gates running at once in one container, in two worktrees (lesson 20's
  isolation), share those folders. The coordinates lens worked around this with
  `XDG_DATA_HOME`. No concurrent run was made here.
- **Harm:** phantom GUT failures during concurrent reviews or builds (lesson 19).
- **Fix:** a per-run scratch folder name in those tests, or a line in lesson 20 or brain.md
  saying that a worktree does not isolate `user://`. Design's call.

## Checked and clean

- **Every class the round named fails the gate.** One mutation per run through
  `tools/gate.sh`, in the worktree; each undone, and the tree was clean after each.

  | Run | Mutation | Exit, step | Evidence |
  |---|---|---|---|
  | m1 | `pipeline/tests/test_scratch_mut.py`: `assert 1 == 2` | 1, `pytest` | `1 failed, 209 passed, 2 deselected` |
  | m2 | `pipeline/mattini/_scratch_mut.py`: `import os` | 1, `ruff check` | F401 |
  | m3 | the same file: `X = {  'a':1 }` | 1, `ruff format --check` | — |
  | m4 | GUT test `assert_eq(1, 2)` | 1, `gut` | `[Failed]: [1] expected to equal [2]`, `Failing Tests 1` |
  | m5 | a GUT test script that cannot load (undeclared class) | 1, `godot parse check` | `SCRIPT ERROR: Parse Error: Identifier "UndeclaredThing" not declared`, `Failed to load script` |
  | m6 | parse error in `game/scripts/scratch_parse.gd` | 1, `godot parse check` | `Expected expression for variable initial value` |
  | m7 | 4 KB of random bytes as `game/corrupt_mutation.png` | 1, `godot import` | three `ERROR:` lines; `.import` has `valid=false` |
  | m8 | `func badName()` | 1, `gdlint` | `(function-name)` |
  | m9 | `var x = [1,2,  3]` | 1, `gdformat --check` | `would reformat game/scripts/scratch_fmt.gd` |
  | a2-control | `test_scratch_node.gd` extends `Node` | 1, `gut` | `Ignoring script …` |
  | e1-control | an engine error inside a test body | 1, `gut` | `Unexpected Errors` |

- **set -e, pipefail and subshells.** Every function that `step` calls runs under `if !`,
  where `set -e` is off. I read each line of `allowed_texts`, `run_scanned`, `godot_import`
  and `parse_check`: every failure that matters has an explicit `|| return 1` or `status`.
  `|| true` appears only on greps whose exit status 1 means "no match". `gdlint` and
  `gdformat` with no file arguments exit 1 (measured), so an empty `GD_FILES` cannot pass
  the lint steps vacuously.
- **Working directory.** The full gate exited 0 run as `/abs/…/tools/gate.sh` from `/tmp`,
  and as `../../tools/gate.sh` from `game/tests`. Both passed all steps (209 pytest,
  13 GUT).
- **The M0-01 ↔ M0-03 seam.** The hardened gate still runs every step M0-01 and CLAUDE.md
  name: pytest, ruff check, ruff format, manifest, import, GUT, gdlint and gdformat. The
  parse check comes on top. Each step fails the gate on its own (the table above). The
  steps still stop at the first failure and name it. Tools still run through `uv run
  --project pipeline --frozen`. The known differences (`--frozen`, and CLAUDE.md's
  `gdlint game` linting the vendored GUT) are on the board.
- **Pinned copies.** `cmp` of all five files under `docs/briefs/pinning/` against the live
  copies: all identical (on `main` at review time).
- **Network exclusion.** With every proxy variable pointed at a dead port and `NO_PROXY`
  unset, the default run gave `209 passed, 2 deselected`. So no default test reaches the
  network. `pytest -m network` under the same settings: 2 failed, so the marked tests do
  reach it. `--strict-markers` is in `addopts` (`pyproject.toml:26`).
- **Download error paths.** `python -m mattini download terrain --out <scratch>` with the
  network cut: exit 1, and on stderr `mattini: error: tile 2623-1095: <item URL>: cannot
  read the STAC item: <urlopen error [Errno 111] Connection refused>`. Afterwards the folder
  held only the empty `swissalti3d/2024/`: no `.part`, no `.tif`, no `provenance.json`.
  Reading the code (`download.py:172-188`): `.part` is removed in a `finally`, which also
  runs on KeyboardInterrupt. `provenance.json` is written through `.part` and
  `os.replace`. Every exception outside `FETCH_ERRORS` propagates, giving a traceback and
  exit 1. No path exits 0 on a failure, and none leaves a final-named file that is not
  verified. The one stale state is G-06.
- **Licence and attribution (Hard Rule 3).**
  - `config/datasets.json:9` holds `"attribution": "© swisstopo"`.
  - What enforces it: the pinned `test_download.py:78` (config value) and
    `test_download_provenance.py:112-113` (the bytes of `provenance.json`).
  - `docs/RELEASE.md:17` carries the credits checkbox.
  - Raw data stays out of git: `.gitignore:2` (`/data/`). `test_repo_hygiene.py:89-105`
    refuses any committable `.tif`, `.las` and so on, or any file over 10 MB, even outside
    `data/` (for example a `download --out` pointed inside the repository), and even when
    force-added.
  - `load_datasets` accepts any non-empty attribution for future datasets
    (`datasets.py:53-56`); the pinned test covers only swissALTI3D's.
- **The session-start hook.**
  - It runs only when `CLAUDE_CODE_REMOTE=true`.
  - It verifies the Godot zip's SHA-256 before unpacking, and refuses with a message on a
    mismatch.
  - A failing `uv sync` or import is reported as "non-fatal", with a line.
  - Its warm-up import is G-05's mechanism.

## Does NOT prove

- **Rendering.** That anything renders or looks right: there is no GPU here.
- **Other machines.** That the gate behaves the same on the owner's Windows or Linux PC.
  Nothing was run outside this container, with its POSIX locale, GNU grep 3.11 and bash
  5.2.
- **Other Godot versions.** That Godot error formats other than 4.6.3's are caught (G-09).
- **Output order.** That no interleaving of Godot's stdout and stderr can split an `ERROR`
  line mid-line. The editor build is expected to flush stdout on each print; that was not
  measured.
- **Other failure classes** that were not tried:
  - a runtime error in a test script's class-level initialiser;
  - broken `.tscn` or `.tres` files that no test loads;
  - `.gdshader` syntax errors (the headless dummy renderer probably never compiles
    shaders);
  - a GUT test that hangs (the gate has no timeout);
  - a test file not named `test_*.gd`, which GUT skips silently by design;
  - a `.part` file left by a killed download inside a non-ignored `--out` folder
    (`.part` is not in `RAW_SUFFIXES`; under 10 MB it would be committable).
- **The `after_all` half of G-03.** It is inferred from the same code path (`gut.gd:624`),
  not run.
- **The G-10 race.** Not run.
- **The fixes.** Only G-04's fix was measured (`e3`, `e4`). Every other fix is
  unimplemented and unmeasured.
