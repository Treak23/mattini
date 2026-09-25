# Brief: M1-02 — The gate cannot be switched off; WorldConfig's corners are tested (the M0 carry-over, gate and game half)
Status: DONE (c635411)

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

Before M1 adds Terrain3D, shaders and a main-scene script (D12), the gate closes every way
the M0 review found to switch it off or cut the test run short, and WorldConfig's untested
corners are tested: a malformed allowlist entry, a run that stops early, an engine error
outside a test, a committed GUT config, a NUL byte, another Godot version, two gates at once
and a stale lockfile can no longer pass; the game's inverse transform is checked for all 24
rotations with inputs wider than 32 bits; a WorldConfig that never read a manifest, and an
empty manifest, are visible errors. CLAUDE.md says what the gate now does.

## Read first, in order

1. `CLAUDE.md` §Build & Test and the gate paragraph.
2. `docs/history/ARCS.md` §M0: D3, D5, D10, D12 and the carry-over table rows G-01, G-02,
   G-03, G-04, G-07, G-09, G-10, lock, C-03, C-06, C-07, C-08.
3. `docs/reviews/M0-R1-gate.md` (G-01 … G-10) and `docs/reviews/M0-R1-coordinates.md`
   (C-03, C-06, C-07, C-08): each finding's proof and measured fix.
4. `brain.md` §Hazards H1–H9.
5. `tools/gate.sh`, `tools/gate_allowlist.txt`, `game/scripts/world/world_config.gd` and
   the game tests.
6. The pinning tests, `docs/briefs/pinning/M1-02/game/tests/`:
   `test_world_config_round_trips.gd`, `test_world_config_unbuilt.gd`.

## Decisions already made

- **G-01:** `allowed_texts` refuses an entry whose text (the part before ` # `) is empty or
  only whitespace, with a message in the style of the missing-reason case.
- **G-02:** the GUT step passes only when its ANSI-stripped output holds the line
  `---- All tests passed! ----`. A pending (skipped) or risky (no-assert) test then fails
  the gate; that is intended (D10).
- **G-03:** the GUT step also scans `^ERROR`. The allowlist holds exactly these two entries
  after this brief (M1-04 adds the third):

  ```
  WorldConfig: user://test_ # the refusal tests write broken manifests under user://test_* on purpose
  WorldConfig: not read from a manifest # test_world_config_unbuilt.gd provokes it on purpose
  ```

  Refusal tests write their broken files under `user://test_…`; the game never reads a path
  like that outside tests, so these entries hide no real refusal.
- **G-04:** `-gconfig=` on the gate's GUT command, so only the command line configures GUT.
- **G-07:** `grep -a` in every scan.
- **G-09:** a first Godot step: `$GODOT --version` must start with `4.6.3.stable`, else the
  gate fails naming the version it found.
- **G-10:** the gate exports `XDG_DATA_HOME` into its scratch folder for the Godot steps, so
  each run gets its own `user://` on Linux (no effect on Windows).
- **lock:** a gate step `uv lock --check --project pipeline` (offline, 12 ms at the M0
  close; `--frozen` alone does not see a lockfile out of step with `pyproject.toml`).
- **C-03, C-06:** the pinned `test_world_config_round_trips.gd`. The M0 test
  `test_round_trips_stay_within_a_millimetre` in `test_world_config_transforms.gd` draws
  32-bit offsets, so its comment claims a narrowing it never exercises (Hard Rule 2):
  delete that one test, superseded by the pinned `test_random_round_trips_with_64_bit_offsets`.
- **C-07:** a `WorldConfig` not built by `from_manifest` starts with NaN origin and offset;
  its `to_local` and `to_lv95` call `push_error("WorldConfig: not read from a manifest (use
  WorldConfig.from_manifest)")` and return NaN in every component.
- **C-08:** an empty manifest file is refused with
  `WorldConfig: <path>: the manifest is empty`; `cannot read the manifest (<reason>)` stays
  for a file that cannot be opened.
- **CLAUDE.md:** the GUT line in §Build & Test gains `-gconfig=`; the gate paragraph says
  that the GUT step also fails on `ERROR` lines and without `All tests passed!`, and drops
  the sentence that engine errors outside a test do not fail the gate.

## Scope — files you may touch

`tools/gate.sh` · `tools/gate_allowlist.txt` · `game/scripts/world/world_config.gd` ·
`game/tests/test_world_config_round_trips.gd` and `game/tests/test_world_config_unbuilt.gd`
(the pinned copies) · `game/tests/test_world_config_transforms.gd` (the one superseded test)
· your own tests in `game/tests/` · `CLAUDE.md` §Build & Test (the GUT command line and the
gate paragraph only)

## Depends on

None. Shares no file with M1-01: the two may run at once.

## Done when (gates)

- [ ] The two pinned files are in place and unchanged (`cmp`).
      - does NOT prove: that the pinned tests are right (design ran them against a scratch
        WorldConfig, 2026-09-25; each fails on M0's code or the review's H4 mutation).
- [ ] Mutation proofs, each a full `tools/gate.sh` run in a separate worktree or undone with
      `git apply -R` of its saved diff, each row naming the owner-visible harm:
      (a) an allowlist entry ` # reason` plus a test script that extends `Node` → fails
      naming the entry; (b) a test that calls `get_tree().quit()` → fails at `gut` (no
      `All tests passed!`); (c) an engine error in a `before_all` (load a missing
      resource) → fails at `gut` on the `ERROR` line; (d) `game/.gutconfig.json` with
      `{"failure_error_types": []}` plus a test with an unexpected engine error → fails;
      (e) a NUL byte: `run_scanned` over a command that prints a NUL and an `ERROR` line →
      still caught (a direct call of the function is enough; say so); (f) `GODOT` set to a
      wrapper printing `4.6.2.stable` → fails at the version step; (g) a dependency added to
      `pipeline/pyproject.toml` without `uv lock` → fails at the lock step; (h) two full
      gates at once in two worktrees → both exit 0 (G-10); (i) the review's H4 mutation of
      `to_lv95` → `test_every_rotation_round_trips` fails; (j) the C-07 guard removed → the
      pinned unbuilt tests fail.
      - does NOT prove: that other Godot error formats are caught (G-09 limits the gate to
        4.6.3); that no other way to switch the gate off exists.
- [ ] The gate still fails on every class M0-03 and the review listed (the M0-R1-gate table,
      m1–m9): re-run three of them (m4, m5, m7) and record the step and evidence.
      - does NOT prove: the classes not re-run (named in the review's does-NOT-prove).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`.
      - does NOT prove: that anything renders (nothing is drawn here).

## Forbidden

Switching GUT's error tracking off; an allowlist entry wider than the two above; changing
`config/` or `tests/shared/`; changing a pinned copy; touching `pipeline/` (M1-01's).

## Findings (executor writes)

Executor session, 2026-09-25. Code commit `c635411` (rebased twice onto M1-01's commits and
the board's; the gate re-run after each rebase: exit 0).

1. **Pinned copies:** `cmp` of `docs/briefs/pinning/M1-02/game/tests/test_world_config_round_trips.gd`
   and `…/test_world_config_unbuilt.gd` against `game/tests/`: both exit 0.
2. **The gate on the pushed head:** exit 0 in about 21 s. `uv lock --check` 66 ms offline
   (`Resolved 17 packages in 5ms`); pytest 275 passed, 3 deselected; GUT 8 scripts,
   18 tests, 1195 asserts, `---- All tests passed! ----`. The GUT run prints 44 `ERROR`
   lines, each excepted by one of the two allowlist entries: 42 contain
   `WorldConfig: user://test_` (41 refusals plus the empty manifest), 2 contain
   `WorldConfig: not read from a manifest`. No other `ERROR` line anywhere in the log.
3. **Mutation proofs.** Each row is one full `tools/gate.sh` run (stdout and stderr to one
   log) in its own fresh detached worktree of `3f3cde0` (this commit before the rebase; the
   rebase brought M1-01's pipeline, config and test files and docs, none of this brief's), made with `git worktree add`
   and removed after the run, so nothing was undone by hand. Control, the same way: exit 0,
   all steps passed. Two worktrees ran at a time (lesson 20), each gate with its own
   `user://` (G-10).

   | Run | Mutation | Exit, step | Evidence | Owner-visible harm it reproduces |
   |---|---|---|---|---|
   | a | allowlist entry ` # Terrain3D prints a benign line at import` + `game/tests/test_scratch_node.gd` extending `Node` | 1, `godot import` | `gate allowlist entry with an empty text:  # Terrain3D prints a benign line at import` | one typo in the allowlist switches off every scan, and a skipped test script ships green |
   | a3 | the same with `  # reason` (a text of two spaces) | 1, `godot import` | `gate allowlist entry with an empty text:   # reason` | the same, through a blank text |
   | b | `test_aaa_quit.gd` whose test calls `get_tree().quit()` | 1, `gut` | no `Tests` line; `ERROR: 3 resources still in use at exit` caught by the scan, and `GUT printed no line '---- All tests passed! ----'` | a run that stops after the first script: every later test (the coordinate tests) never runs |
   | b2 | a test calling `pending("not written yet")` | 1, `gut` | `---- 1 pending/risky tests. ----`, no `ERROR` line, `GUT printed no line …`: the summary check alone | a skipped test passes as green (D10) |
   | c | `before_all()` loads `res://assets/missing_heightmap.res`, plus one passing test | 1, `gut` | GUT: `Passing Tests 19`, `---- All tests passed! ----`; the gate: `error lines in the output: ERROR: Cannot open file 'res://assets/missing_heightmap.res'.` | a missing terrain resource loaded once for a whole script, green |
   | d | `game/.gutconfig.json` = `{"failure_error_types": []}` + a test loading a missing resource in its body | 1, `gut` | GUT ignored the file: `[Failed]: Unexpected Errors`, `---- 1 failing tests ----`; also the `ERROR` scan and the summary check | one committed file turns GUT's error tracking off for every test (H4's "quickest wrong fix") |
   | d2 | `game/.gutconfig.json` = `{"suffix": "_settings.gd"}` | 0 | `Scripts 8`, `Tests 18`: the file is ignored | — (isolates `-gconfig=`, see d2-control) |
   | d2-control | d2 with `-gconfig=` taken out of `tools/gate.sh` | 0, all steps passed | `Scripts 1`, `Tests 1` | the harm `-gconfig=` prevents: a committed config quietly runs 1 of 8 scripts, green |
   | e | a direct call of `run_scanned '^(ERROR\|SCRIPT ERROR)'` over a function printing `native output\0with a NUL` then `ERROR: boom from native code` (the gate's functions sourced, its steps cut; a direct call is enough for this row, per the brief) | 1 | `== gate: error lines in the output: ERROR: boom from native code` | — |
   | e-control | e with `grep -a -E "$pattern"` back to `grep -E` | 0 | `grep: …/out.log: binary file matches`, the ERROR line not reported | native output holding a NUL (Terrain3D, M1) blinds the scan |
   | f | `GODOT` = a wrapper printing `4.6.2.stable.official.deadbeef` for `--version` | 1, `godot version` | `== gate: Godot 4.6.3.stable required, …/fake-godot-462.sh is: 4.6.2.stable.official.deadbeef` | a PC with another Godot whose error lines the scans may not know |
   | g | `"requests>=2"` added to `dependencies` in `pipeline/pyproject.toml`, no `uv lock` | 1, `uv lock --check` | `The lockfile at uv.lock needs to be updated, but --locked was provided.` | the committed lockfile no longer describes the environment; another machine installs something else |
   | h | two control runs started together in two worktrees | 0 and 0, 21 s each | both `Scripts 8`, `Tests 18`, all steps passed | — (see 5) |
   | i | the review's H4: `source[axis] = _sign[_source_index[axis]] * p[_source_index[axis]]` in `to_lv95` | 1, `gut` | `test_every_rotation_round_trips` fails for exactly the 8 cyclic rotations (`[+n,+h,+e]`, `[+n,-h,-e]`, `[-n,+h,-e]`, `[-n,-h,+e]`, `[+h,+e,+n]`, `[+h,-e,-n]`, `[-h,+e,-n]`, `[-h,-e,+n]`); e.g. e 2624606.37 for 2623825.13 | a coordinate readout about 1 km off if design ever picks a cyclic mapping |
   | j | both `if not _built:` guards removed from `to_local` and `to_lv95` | 1, `gut` | `Failing Tests 2`: the two pinned `…_on_an_unbuilt_config_is_nan_and_an_error` (`Expected push_error error containing 'WorldConfig: not read from a manifest'`) | a hand-built WorldConfig gives wrong answers without a word |
   | j2 | the three NaN defaults back to `0.0`, guards kept | 1, `gut` | `test_an_unbuilt_config_has_a_nan_origin_and_offset`: `origin_e is NaN: 0.0` (and n, offset) | code reading an unbuilt config's origin gets 0 m, which looks like a real place |

   - does NOT prove: that other Godot error formats are caught (G-09 limits the gate to
     4.6.3); that no other way to switch the gate off exists; that the G-10 race happens
     without the fix (no concurrent run without it was made, see 5).
4. **The M0 classes still fail the gate** (the M0-R1-gate table), the same way:

   | Run | Mutation | Exit, step | Evidence |
   |---|---|---|---|
   | m4 | a GUT test `assert_eq(1, 2)` | 1, `gut` | `[Failed]: [1] expected to equal [2]`, `---- 1 failing tests ----`, and the summary check |
   | m5 | a GUT test script using an undeclared class | 1, `godot parse check` | `SCRIPT ERROR: Parse Error: Identifier "UndeclaredThing" not declared in the current scope.`, `ERROR: Failed to load script "res://tests/test_scratch_undeclared.gd" with error "Parse error".` |
   | m7 | 4 KB of random bytes as `game/corrupt_mutation.png` | 1, `godot import` | `ERROR: Condition "!success" is true. Returning: ERR_FILE_CORRUPT`, `ERROR: Error importing 'res://corrupt_mutation.png'.` (a fresh worktree: the gate's import was the first) |

   - does NOT prove: m1–m3, m6, m8, m9 (not re-run), and the classes the review's
     does-NOT-prove names.
5. **G-10, measured.** A probe script printing `OS.get_user_data_dir()`: without
   `XDG_DATA_HOME`, `/root/.local/share/godot/app_userdata/mattini`; with it,
   `$XDG_DATA_HOME/godot/app_userdata/mattini`. Run h shows two gates at once passing; it
   does not show that they collided before (the refusal tests take under a second, and no
   run without the fix was made).
6. **Choices inside the brief's scope** (reversible):
   - `XDG_DATA_HOME` is set on each Godot command through one wrapper, `run_godot`, which
     every Godot call in the gate goes through (version, import, parse check, GUT), not
     exported to the whole script: the brief asks for it "for the Godot steps", and the uv
     steps then run with the environment they had.
   - `uv lock --check` is the first step, before any `uv run --frozen`.
   - Both allowlist refusals (the new empty-text case and the old missing-reason case) now
     print on stdout as well as stderr. Before, `tools/gate.sh > gate.log` kept only
     `FAILED at step: godot import` and not the reason.
   - The allowlist is still read at every scanned step, so a bad entry fails at the first
     one, `godot import`, after the pipeline steps.
   - The GUT step runs both checks every time and prints each reason (run b shows both).
     It deletes the scan's `out.log` first, so a log left by the parse check can never
     satisfy the summary check. The summary line may carry trailing whitespace (a CR from a
     Windows console would otherwise fail every run there; not measured on Windows).
   - The version check reads the whole `--version` output, so anything printed before the
     version fails it.
   - My own test, `game/tests/test_world_config_unbuilt_origin.gd`: an unbuilt config's
     `origin_e`, `origin_n` and `height_offset` are NaN. The pinned tests reach only the
     conversions, which the guard answers first, so without it the NaN defaults the brief
     decides were untested (run j2).
   - WorldConfig knows it was built by a `_built` flag that only `from_manifest` sets,
     after the world block was accepted; a hand-set origin on a `new()` object is still
     refused by the conversions.
   - `test_world_config_transforms.gd`'s header no longer claims round trips; it names the
     file that holds them.
7. **For M1-04 (next):** the GUT step now fails on every engine `ERROR` line, so every
   Terrain3D `ERROR` in brain.md H11 (`Resource file not found: res://`, `Cannot find the
   active camera`, `min_height > max_height`) fails the gate unless the loader avoids it
   or M1-04's third allowlist entry names it. `WARNING` lines (H4's deprecation) are not
   scanned.
