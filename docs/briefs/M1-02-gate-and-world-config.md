# Brief: M1-02 — The gate cannot be switched off; WorldConfig's corners are tested (the M0 carry-over, gate and game half)
Status: OPEN

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

