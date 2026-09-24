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

Executor session, 2026-09-24 (same session as M0-01 and M0-02). Godot 4.6.3 headless in a
cloud container; the gate takes about 11 s here.

1. **Pinned copy:** `cmp docs/briefs/pinning/M0-03/game/tests/test_world_config.gd
   game/tests/test_world_config.gd` exits 0. It passes gdlint and gdformat unchanged.
2. **Fresh clone:** exactly the committable files (`git ls-files -co --exclude-standard`)
   copied into a new repository with no `.godot/`, no `.venv/` and no generated manifest;
   `uv sync --project pipeline --frozen` exit 0; `tools/gate.sh` exit 0. GUT: 5 scripts,
   13 tests, 943 asserts, all passing. The pinned file: 4 tests, 57 asserts. Mine:
   `test_main_scene.gd` (instantiates `res://main.tscn`, runs two frames in the tree,
   frees it; asserts no engine error, no push_error, no orphans), `test_project_settings.gd`,
   `test_world_config_refusals.gd` (all 48 signed axis mappings: 24 rotations accepted and
   right-handed, 24 mirrors refused with the path in the error; 15 malformed manifests;
   a missing manifest; an infinite height offset) and `test_world_config_transforms.gd`
   (the origin and height offset come from the manifest given; 200 random round trips
   within 2 mm at up to 20 km). After the gate, `git status` in the clone is clean: every
   `.uid` file Godot 4.6 wants is committed.
3. **GUT vendored:** `git clone --depth 1 --branch v9.6.1 https://github.com/bitwes/Gut`,
   HEAD `c80954f47bed74a0a2c471d472c0389f98e0a8f6`; only `addons/gut/` copied (257 files,
   3.2 MB, MIT licence in `addons/gut/LICENSE.md`); `diff -r` against the tag's
   `addons/gut/` is empty, also after the imports.
4. **`main.tscn`** was written by Godot itself (`PackedScene.pack` + `ResourceSaver.save`
   in a scratch script), so its format is 4.6.3's own; 4.6 adds a `unique_id` attribute
   to the node line.
5. **Mutation proofs**, one per run through `tools/gate.sh` unless stated; scratch files
   deleted afterwards, edits undone with `git apply -R` of the saved diff; the restored
   run exits 0 (13 tests):

   | Run | Mutation | Exit, step | What failed | Owner-visible harm |
   |---|---|---|---|---|
   | a | `game/tests/test_scratch_parse.gd` uses an undeclared class | 1, `godot parse check` | `SCRIPT ERROR: Parse Error: Identifier "UndeclaredThing" not declared`. The GUT command alone: exit 0, `Ignoring script … does not extend GutTest`, `All tests passed!` (H3 reproduced) | a broken test silently skipped, its checks never run |
   | a2 | `game/tests/test_scratch_node.gd` parses but extends `Node` | 1, `gut` | the scan's `Ignoring script res://tests/test_scratch_node.gd` | the same, for a script only GUT can see |
   | b | `assert_eq(1, 2)` in a scratch test | 1, `gut` | `[Failed]: [1] expected to equal [2]`, GUT exit status 1 | a failing game test committed anyway |
   | c | 4 KB of random bytes as `game/corrupt_mutation.png` | 1, `godot import` | `ERROR: Error importing 'res://corrupt_mutation.png'.` and two more `ERROR` lines | a broken asset in the game (Godot's own exit status was 0) |
   | c2 | the same file left in place, second run | 1, `godot import` | Godot printed **no** error line this time; caught only by the `valid=false` check (item 6) | the same harm, on the run after the first failure |
   | d | `func badName()` in `game/scripts/scratch_lint.gd` | 1, `gdlint` | `Function name "badName" is not valid (function-name)` | lint drift in game code |
   | e | `to_local` subtracts the origin between two `Vector3`s (32-bit) | 1, `gut` | pinned `test_to_local_matches_shared_vectors`: the 32-bit trap vector's x = 825.25 (want 825.13) and z = −489.75 (want −489.77); mine: `test_round_trips_stay_within_a_millimetre` | everything placed up to 0.25 m off, jittering from point to point |
   | f | a newline appended to `config/world.json`, manifest not regenerated | the GUT command alone (CLAUDE.md): exit 1 | pinned `test_manifest_matches_config_world_json`: `manifest is current` | a game running on an origin the config no longer holds |
   | f′ | the same, through `tools/gate.sh` | 0 | nothing: the gate's `manifest` step regenerates the manifest before GUT runs, so a stale manifest cannot reach the gate's GUT step | — |
   | g | `game/tests/` moved out of the project | 1, `gut` | `[ERROR]: The path [res://tests] does not exist.`, `[ERROR]: Nothing was run.` (the GUT command alone exits 0) | a gate that passes because nothing was tested |
   | h | allowlist of blank and comment lines only, corrupt image present | 1, `godot import` | the import errors (an empty pattern would have allowed every line) | an allowlist that silently allows everything |
   | i | allowlist entry without ` # reason` | 1, `godot import` | `gate allowlist entry without a reason` | an unexplained exception |

   `config/world.json` is back to SHA-256 `d2607d13…509b` and the allowlist to 0 bytes.
6. **Gate checks added beyond the brief's list** (each measured here; the review may
   remove any of them):
   - **Import: any `.import` file with `valid=false` fails the step.** Measured on 4.6.3:
     Godot prints an import error only on the run that imports the file; the next
     `--import` prints nothing and exits 0 while the file is still broken, and the
     `.import` file keeps `valid=false` (run c2). Without this check the gate fails once
     and passes on a re-run. Candidate for brain.md §Hazards (H1's second half).
   - **GUT: `[ERROR]` in its output fails the step.** GUT 9.6.1 exits 0 when it runs
     nothing (run g); every `[ERROR]` it logs marks misuse or an aborted run, and a healthy
     run prints none.
   - **ANSI colour codes are stripped before scanning.** Godot colours its progress lines
     even when redirected; the `ERROR` lines were plain on 4.6.3, and stripping keeps a
     future colour prefix from blinding the `^ERROR` scan.
7. **The allowlist's format** (the brief fixes only "one line with its reason each"):
   `<text the error line contains> # <reason>`; blank lines and `#` lines are ignored and
   never reach `grep` (an empty pattern matches every line); an entry without a reason
   fails the gate. `tools/gate_allowlist.txt` is committed empty (0 bytes); the format is
   documented in the gate's header.
8. **Lint scope:** gdtoolkit 4.5.0 finds its config from the working directory upward and
   excludes folders by name, so the gate passes an explicit list: every `.gd` under
   `game/` except `game/addons/` (`find game -path game/addons -prune …`), the same list
   the parse check uses. **CLAUDE.md's command `uv run --project pipeline gdlint game` as
   written lints the vendored GUT: 645 problems; `gdformat --check game`: 85 files would
   be reformatted.** A root `gdlintrc` and `gdformatrc` with `excluded_directories: {.git,
   addons}`, or a changed CLAUDE.md line, would align them; both are outside this brief's
   Scope (design's call).
9. **Order matters for the parse check:** `--check-only` on a script that uses a new
   `class_name` fails with `Identifier not found: WorldConfig` until an import has
   refreshed the class cache (measured); the gate imports first.
10. **WorldConfig reads** the manifest's `schema` and the world block's `schema`, `crs`,
    `origin_lv95`, `height_offset_m` and `axes` (the areas are not read; nothing in the
    game needs them yet). Measured in Godot 4.6.3: `JSON` parses every number as a float
    (`1` → `1.0`, `1e400` → `inf`) and keeps the last of two duplicate keys, so the game
    side compares numbers numerically, refuses non-finite ones, and relies on the pipeline
    (brief M0-02) to refuse duplicate keys. It uses `JSON.new().parse()`, which reports
    through its return value, instead of `JSON.parse_string()`, which prints an engine
    `ERROR` line of its own. `height_offset_m` is read the way M0-02 reads it (y = H −
    height_offset_m), pinned on both sides by a test.
11. The refusal tests print `ERROR: WorldConfig: user://…` lines on purpose (push_error,
    consumed by `assert_push_error`); that is why the GUT step's scan does not include
    `^ERROR`, as the brief specifies.
12. No `.gitignore` change was needed: Godot 4.6.3's headless import writes only under
    `game/.godot/` (already ignored) and the `.uid` files, which are committed.
