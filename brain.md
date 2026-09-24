# brain.md — mattini, the whole picture in one file

Orientation for any session. Current as of **2026-09-24 — no version yet — day one: the
process is scaffolded, SPEC v0 is written, arc M0 (setup and the first M1 step) is
briefed** (update this header when a phase closes). `CLAUDE.md` (rules) and `docs/SPEC.md`
(design) outrank this file.

## 1. WHAT
A desktop game (Windows, Linux) set in Zermatt on swisstopo open geodata; stylised diorama
look; real day/night and weather; sandbox first, game modes later. The owner's learning
project, shared later with a few people; commercial release undecided. v1 = the sandbox
with free-fly camera, walking, day/night cycle and weather (SPEC §2).

## 2. SHAPE
Python pipeline (swisstopo → chunks + manifest) → Godot game that reads only the generated
folder. `config/world.json` is the one home of the origin and axis mapping; the pipeline
copies it into the generated manifest, and the game learns the origin only from there
(SPEC §6).

## 3. PHILOSOPHY
- No never-happen rule (the owner chose none, 2026-09-24). The absolutes are no secrets in
  the repo and no unrecoverable loss of the owner's work; full discipline covers the
  coordinates and the pipeline's determinism (Hard Rules 4 and 5).
- Licence-clean data; attribution in every shared build (a soft rule by the owner's
  choice: a test and the release checklist enforce it).
- Evidence over assertion: measure before deciding; prove gates by mutation; docs state
  the limits of their own claims. Hunt the unimplemented premise and the gap between two
  tested halves (e.g. a pipeline output that is correct and a loader that is correct, with
  a mismatched axis between them).

## 4. STACK
Godot 4.6.3 (standard build, Forward+), GDScript, Terrain3D 1.0.2, GUT 9.6.1, gdtoolkit
4.5.0; Python 3.13 via uv with a committed lockfile; pytest and ruff. Why each: SPEC §4 and
§13. Test counts at the last gate: none yet (no gate has run on `main`).

## 5. HISTORY
Per-arc record: `docs/history/ARCS.md`. Lessons: `docs/LESSONS.md`. Ledger:
`docs/history/LEDGER.md`.

## 6. NEXT
Arc M0: M0-01 skeleton and gate → M0-02 world config and transforms → M0-03 Godot project
and hardened gate, and M0-04 terrain download (these two can run side by side). Then M1:
terrain in Godot with a free-fly camera. The board is the live version.

## 7. HAZARDS
All measured on Godot 4.6.3 in a cloud container on 2026-09-24.

- Containers have no GPU: nothing verifies rendering; the owner's PC does (start.md 1A).
- **H1 — Godot's import exits 0 on errors.** `godot --headless --path game --import`
  returns 0 while printing `ERROR: Error importing 'res://…'`. The gate scans the output.
- **H2 — A scene whose script does not parse still exits 0.** Running it prints
  `SCRIPT ERROR: Parse Error: …` and `ERROR: Failed to load script "res://…" with error
  "Parse error".` and returns 0. `godot --headless --path game --check-only -s res://<file>.gd`
  returns 1 on a parse error (including an undeclared class) and 0 on a valid script,
  whether it extends a Node or GutTest.
- **H3 — GUT 9.6.1 skips a test script that does not parse, and passes.** Output:
  `[WARNING]: Ignoring script res://tests/<file>.gd because it does not extend GutTest`,
  then `---- All tests passed! ----`, exit 0. A pinning test whose class is not written yet
  is exactly such a script.
- **H4 — Terrain3D 1.0.2 prints a deprecation warning GUT counts as a failure.** Adding a
  `Terrain3D` node to the tree prints `WARNING: instance_reset_physics_interpolation() is
  deprecated.`; GUT 9.6.1 then reports `[Failed]: Unexpected Errors: [1] <engine-1>
  instance_reset_physics_interpolation() is deprecated.` Handle it explicitly in the tests
  that add Terrain3D to the tree; never switch GUT's error tracking off globally.
- **H5 — 32-bit coordinates.** `Vector3` is 32-bit: an LV95 easting near 2.6 million keeps
  only 0.25 m. Subtract the origin in 64-bit `float` first (SPEC §6); the shared vectors
  hold a trap point that fails otherwise (measured: 825.25 instead of 825.13).
- **H6 — Downloads in cloud containers.** github.com release downloads and codeload return
  403; `git clone` of public repositories works. Godot comes from
  `downloads.godotengine.org`, Terrain3D from `store.godotengine.org`, Python packages from
  PyPI, Python itself through uv.
- **H7 — Size of swisstopo files.** The current swissBUILDINGS3D edition is one 14.1 GB
  national file; swissTLM3D is national only (2.9–4.8 GB); one LiDAR tile is 213 MB. Never
  download those in a cloud session without a brief that says how (SPEC §14).
- Benign: GUT runs end with `WARNING: ObjectDB instances leaked at exit`, a warning line,
  not an error.

## 8. PROCESS
Three realms and a supervisor (`docs/WORKFLOW.md`, `docs/roles/`). Spawn words `design`,
`ultracode build`, `supervise`, `feedback`. `main` is the only branch. State lives in the
repo, never in chat. Pinning tests travel with their brief under `docs/briefs/pinning/`
(WORKFLOW §Brief lifecycle).

## 9. KEY FILES
1. `CLAUDE.md` — rules, commands, spawn words.
2. `docs/SPEC.md` — design of record, including the decision record (§13).
3. `docs/ROADMAP.md` — the board, open items only.
4. `docs/WORKFLOW.md` and `docs/roles/` — the process, one doc per role.
5. `config/world.json` — origin, axis mapping, areas (the one home).
6. `config/datasets.json` — datasets, pinned editions, attribution.
7. `tests/shared/world_vectors.json` — the conversions both halves must agree on.
8. `docs/briefs/` — briefs, `BLOCKED.md`, `pinning/`.
9. `docs/LESSONS.md` — lessons by role tag.
10. `tools/gate.sh` — the standard gate (from M0-01 on).
