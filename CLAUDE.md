# CLAUDE.md

mattini is a desktop game (Windows, Linux) set in Zermatt, built on swisstopo open
geodata, in a stylised diorama look. The first deliverable is a walkable / flyable sandbox
of the real terrain and village; game modes come later. It is the owner's learning
project, later shared with a few people; a commercial release is undecided, so everything
stays licence-clean. Full design in **docs/SPEC.md**: read it before any structural
change. Work in small increments per roadmap phase; do not build ahead of the current
phase.

## Build & Test

```bash
uv run --project pipeline pytest pipeline/tests        # pipeline unit tests
uv run --project pipeline ruff check pipeline          # pipeline lint
uv run --project pipeline python -m mattini manifest   # writes game/assets/generated/manifest.json
godot --headless --path game --import                  # asset import; exits 0 even on errors (brain.md §Hazards)
godot --headless --path game -s addons/gut/gut_cmdln.gd -gdir=res://tests -ginclude_subdirs -gexit -gconfig=   # game tests (GUT), no .gutconfig.json
uv run --project pipeline gdlint $(find game -path game/addons -prune -o -name '*.gd' -print)   # game lint, vendored addons excluded (the gate's list)
```

`godot` is the pinned Godot 4.6.3 binary; set `GODOT` to its path where it has another
name (e.g. on Windows). The Godot commands exist from brief M0-03 on.

**The standard gate** is `tools/gate.sh` (runs everything above, exits non-zero on any
failure), redirected to a log and chained to the commit by its own exit status
(`docs/roles/BUILD.md` rule 3c). Godot's own exit status is not enough, so the gate also
scans its output: error lines at the import and the parse check, an import left
`valid=false`, and in the GUT run any test script GUT skipped or could not load,
`SCRIPT ERROR`, GUT's own `[ERROR]`, and every engine `ERROR` line, inside a test or
outside one (brain.md §Hazards). The GUT run also fails unless GUT prints its run
summary and then `---- All tests passed! ----`: a run cut short, a pending test and a test
with no assert fail it. An error line known to be benign is excepted only in
`tools/gate_allowlist.txt`, globally or scoped to one test script, by a text specific
enough (12 characters at least, never a bare scan prefix such as `ERROR`). The gate also
refuses a `pipeline/uv.lock` out of step with `pyproject.toml`, any Godot but 4.6.3 and
any GUT but 9.6.1.
There is no never-happen rule (the owner chose none, 2026-09-24); the code that
guards Hard Rules 4 and 5 (`config/world.json`, the coordinate transforms on both sides,
the pipeline's determinism) MUST have tests, mutation-proved.

**What the gate cannot see:** containers have no GPU. Nothing here proves that anything
renders or looks right; the owner's PC is the visual test (brain.md §Hazards).

## Stack

- Godot 4.6.3-stable (standard build, not .NET), GDScript, terrain via the Terrain3D
  plugin 1.0.2 (vendored in `game/addons/terrain_3d/`). Game tests: GUT 9.6.1 (vendored in
  `game/addons/gut/`). GDScript lint: gdtoolkit 4.5.0. Versions and sources: SPEC §Stack.
- Python 3.13 via uv for `pipeline/`, lockfile `pipeline/uv.lock` committed; libraries
  (GDAL/rasterio, numpy, pyproj, shapely, trimesh, laspy) each confirmed by the design
  realm before it is added.
- **Forbidden:** Google Maps Platform content of any kind (its terms forbid storing,
  shipping or deriving assets from it); any geodata whose licence does not allow
  redistribution in a shipped game.

## Layout

```
config/world.json    local origin, bounding boxes, axis mapping (one home)
config/datasets.json swisstopo datasets: collection, pinned edition, attribution
config/datasets.lock.json  the pinned tile checksums, written by `mattini lock` (from M1-01)
config/terrain.json  the in-game terrain spacing per area, its expected heights (from M2-01)
config/buildings.json the expected building chunks per area (from M2-04)
pipeline/            Python data pipeline (offline, re-runnable); package `mattini`
data/                raw and intermediate downloads — git-ignored
game/                Godot project (project.godot)
game/addons/         vendored plugins (Terrain3D, GUT) — committed, SPEC §Storage
game/assets/generated/  pipeline output: terrain + manifest — git-ignored, regenerated
build/               exports made by tools/export.sh — git-ignored (from M1-06)
tests/shared/        fixtures read by both pipeline and game tests (the seam)
tools/gate.sh        the standard gate
docs/SPEC.md         design of record
docs/WORKFLOW.md     the process skeleton; docs/roles/ the role docs
docs/briefs/         briefs (the unit of work), BLOCKED.md, shots/ (software screenshots)
docs/feedback/       the inbox the clerk files into
docs/releases/       one record per shipped version
brain.md             compressed whole-project handoff
docs/LESSONS.md      numbered lessons, each tagged with the role it binds
docs/ROADMAP.md      the board — open items only
```

## Hard Rules

These bind the agents. The owner's explicit word overrides any of them except rule 1
(WORKFLOW §Rules about rules). There is no never-happen rule: the owner chose none on
2026-09-24.

1. **No secrets in the repo.** No API keys or tokens in code, config, tests or history.
   None are needed today (the swisstopo STAC API has no key); where one would live is
   decided when one is needed.
2. **Honest states.** No fabricated data: a placeholder mesh, texture or value is labelled
   as one in code and in the brief's Findings. Errors surface visibly (in the game and in
   pipeline output), never silently. A comment never claims what the code does not do,
   and no report claims a visual result that nobody rendered.
3. **Licence-clean data.** Only geodata whose terms allow redistribution enters the
   pipeline. Every shared build shows `© swisstopo` in its credits (plus any
   dataset-specific wording). Raw downloads stay in `data/` and never enter git history,
   but the one real sample the owner allowed (SPEC §13 row 24).
   Harm prevented: a game that cannot be shared or sold. A soft rule by the owner's choice
   (2026-09-24): enforced by a test and by `docs/RELEASE.md`, reviewed at Tier 2.
4. **One home for world coordinates.** The local origin and axis mapping exist only in
   `config/world.json`; pipeline and game both read it; no hard-coded offsets anywhere.
   Harm prevented: a world that is silently shifted or mirrored.
5. **The pipeline is re-runnable and deterministic.** Same inputs and config → same
   outputs; every step can run from scratch. Harm prevented: generated assets nobody can
   reproduce.

## Conventions

- Conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`); one roadmap item per
  commit series.
- Tests for every pipeline transform and every piece of game logic that can run headless.
- Metric units everywhere (metres, °C, km/h).
- **Close every shipped version with a report-back list:** one entry per item the owner
  reported (what they said, what was wrong, what changed, which version), kept separate
  from what the review found. Plain text.

## Process: three realms (`docs/WORKFLOW.md`)

Design sessions do everything before the build (`docs/roles/DESIGN.md`): the arc plan,
cut for speed into waves of briefs that can be built in parallel sessions, the briefs and
their pinning tests in `docs/briefs/`, and the review plan. Build sessions run it under
`docs/roles/BUILD.md`: one orchestrator spawns a builder session per lane, patches the
landings together, runs the reviews the design wrote, fixes, and ships the release — no
design authority, ambiguity goes to `docs/briefs/BLOCKED.md`, done = the brief's gates
green. The clerk files feedback under `docs/roles/FEEDBACK.md`.
If you have been pointed at a brief, you are an executor and BUILD.md binds you. A brief
marked `Builder: owner` on the board is the owner's to implement; no agent takes it (the
owner takes none today, 2026-09-24).

**Session roles (spawn words).** When the owner's first message is one of these words,
first run `git fetch --unshallow origin main || git fetch origin main`, then
`git checkout main && git pull --ff-only origin main` (brain.md H14), then read
the role doc and follow it: `design` → `docs/roles/DESIGN.md` · `ultracode build` →
`docs/roles/BUILD.md` · `feedback` → `docs/roles/FEEDBACK.md`. The model is the one the
owner picks when starting the chat; spawns name none and inherit it (WORKFLOW §Models).

**Rules about rules** (`docs/WORKFLOW.md`): rules bind the agents, never the owner; the
owner's explicit word overrides any process rule except no-secrets and no unrecoverable
loss of the owner's work (record the override in one line);
one home per rule — link, don't retell.
