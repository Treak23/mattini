# Brief: M0-03 — Godot project, GUT, GDScript lint, WorldConfig and a hardened gate
Status: OPEN

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`. Review tier: **Tier 1** for `WorldConfig` (the game side of the
coordinates), Tier 2 for the rest.

## Goal

`game/` is a Godot 4.6.3 project (Forward+) that imports clean headless, with GUT 9.6.1
vendored, GDScript lint wired, and a `WorldConfig` class that learns the origin and axes
only from the generated manifest and converts exactly as the shared vectors say. The
standard gate gains the Godot steps and is hardened so that a broken resource, a script
that does not parse, or a test script GUT silently skips fails it — the three hazards
measured on 2026-09-24 (brain.md H1–H3).

## Read first, in order

1. `CLAUDE.md` — Build & Test, Hard Rules 2 and 4.
2. `brain.md` §Hazards — H1, H2, H3 and H5 in particular.
3. `docs/SPEC.md` §4 Stack, §6 Coordinates, §8 (the manifest).
4. `docs/briefs/pinning/M0-03/game/tests/test_world_config.gd` — the pinning tests.
5. GUT 9.6.1's own documentation for its command line (inside `addons/gut/` once vendored).

## Decisions already made

- Godot 4.6.3-stable, standard build; Forward+; project name `mattini`;
  `application/config/version="0.0.0"` until the first release; main scene
  `res://main.tscn`, an empty `Node3D` root for now.
- GUT 9.6.1 is vendored from git tag `v9.6.1`
  (`git clone --depth 1 --branch v9.6.1 https://github.com/bitwes/Gut`, commit
  `c80954f47bed74a0a2c471d472c0389f98e0a8f6`): only its `addons/gut/` folder, into
  `game/addons/gut/`, with the tag and commit named in the commit message. The plugin is
  enabled in `project.godot`.
- Game tests live in `game/tests/` as `test_*.gd`; GUT runs as in CLAUDE.md §Build & Test.
- gdlint and gdformat (gdtoolkit 4.5.0, already a pipeline dev dependency) run over
  `game/` except `game/addons/`.
- `WorldConfig` lives in `game/scripts/world/world_config.gd` (`class_name WorldConfig`,
  `extends RefCounted`): `static func from_manifest(path: String) -> WorldConfig` (returns
  null and calls `push_error` naming the path when it cannot read a valid world block),
  `origin_e` and `origin_n` (64-bit `float`), `to_local(e: float, n: float, h: float) ->
  Vector3` and `to_lv95(p: Vector3) -> PackedFloat64Array` (`[e, n, h]`). It reads the axis
  mapping from the manifest's world block and refuses a non-rotation as the pipeline does.
  The origin is subtracted in 64-bit before any `Vector3` is built (SPEC §6, brain.md H5).
- The gate's new steps, in order: `python -m mattini manifest`; the headless import with
  its output scanned (a line starting `ERROR` or `SCRIPT ERROR` fails the gate); a parse
  check of every `.gd` under `game/` except `addons/` with
  `godot --headless --path game --check-only -s res://<file>` (exits 1 on a parse error,
  measured); the GUT run, failing on a non-zero exit and on any of `Ignoring script`,
  `SCRIPT ERROR`, `Parse Error` or `Failed to load script` in its output; `gdlint`; and
  `gdformat --check`. If a known-benign error line ever needs an exception, it goes in
  `tools/gate_allowlist.txt`, one line with its reason each; the file starts empty and
  every entry is a Findings item.
- The Godot binary is `${GODOT:-godot}`.

## Scope — files you may touch

`game/**` except `game/addons/terrain_3d/` (M1) and `game/assets/generated/` (pipeline
output) · `game/tests/test_world_config.gd` (the pinned copy, unchanged) · `tools/gate.sh`
· `tools/gate_allowlist.txt` · `.gitignore` (Godot additions only)

## Depends on

M0-01, M0-02.

## Done when (gates)

- [ ] The pinned copy is in place and unchanged (`cmp` against
      `docs/briefs/pinning/M0-03/game/tests/test_world_config.gd`).
      - does NOT prove: that the pinned tests are right (verified by the design realm
        against a scratch `WorldConfig`, 4 tests and 57 asserts, 2026-09-24).
- [ ] `tools/gate.sh` passes in a fresh clone after `uv sync` (the manifest step runs
      before the Godot steps). GUT reports the pinned file's 4 tests passing, plus a test
      of your own that instantiates `res://main.tscn` and frees it with no engine errors.
      - does NOT prove: that anything renders or looks right (no GPU, and the main scene
        is empty).
- [ ] Mutation proofs, each recorded in Findings with the exit code and the gate step that
      failed: (a) a test script with a parse error → the gate fails (GUT alone would pass,
      brain.md H3); (b) a failing assertion → fails; (c) a corrupt image under `game/` →
      fails at the import step; (d) a gdlint violation → fails; (e) `to_local` subtracting
      the origin in 32-bit → `test_world_config.gd` fails on the "32-bit trap" vector;
      (f) `config/world.json` touched without regenerating the manifest → the
      stale-manifest test fails.
      - does NOT prove: that every Godot error format is caught (the scan matches the line
        prefixes measured on 4.6.3).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

Vendoring Terrain3D (M1); C#; changing a pinned copy, `config/` or `tests/shared/`; any
change to pipeline code (a needed change is a Findings item or a BLOCKED question).

## Findings (executor writes)
