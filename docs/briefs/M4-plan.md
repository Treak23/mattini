# M4 — The sun cycle: the arc plan

Status: READY — waiting for the owner's GO. The two answers are in (2026-10-24, SPEC §13 rows 47, 48): the softened shadows kept (G = 3); the stars built, section S of M4-05 included (catalogue (a)). The owner will start the build in a new session after workflow changes.

> **Process note, 2026-10-24.** This plan was written under the three-realm process (ten
> arc-sized briefs in two waves for an `ultracode build` orchestrator), retired that day
> (SPEC §13 row 49). Its decisions, data, briefs and pinned tests stand. The first
> `ultracode design` session triages it: the owner's reported items (FB-003 to FB-007:
> M4-06's water, M4-08) first, into releases of two days each, the briefs re-cut to batch size
> where a brief is larger, each with a `Lane:` line; the owner names which of the rest comes
> in. Where this plan says orchestrator, read the release session; where it says builder
> session, read builder agent (`docs/roles/BUILD.md`).

**Base:** the commit that sets this status line to GO (its message starts `docs: M4 GO`;
`git log --grep '^docs: M4 GO' -1`). It is the base of the integration notes and of the
review's diff range.

Written by the design realm (`docs/roles/DESIGN.md` §The arc plan); run by one `ultracode
build` orchestrator (`docs/roles/BUILD.md` §The orchestrator). The owner's answers of
2026-10-17 are SPEC §13 rows 41–46 and `docs/history/RULINGS.md`. Design's working notes, which
the briefs cite as "m4-design §N", are `docs/briefs/sketches/m4-design.md` (SPEC and the briefs
outrank them); the measurements are in its §0 and in `docs/briefs/sketches/M4-deshadow/` and
`M4-soften/`. No model is named (WORKFLOW §Models): every spawn inherits.

## What M4 delivers

Version **0.4.0**: the real sun over Zermatt.
- The sun and the moon stand where they stand at the game's date and time, computed for the
  village. The game starts at the photo's moment (6 September 2023, 13:40 CEST); keys move the
  time and the date, change its speed, or set the computer's clock.
- The sun leaves the village behind the real mountains: swissALTIRegio's heights for 20 km
  around cast shadows (a shadows-only mesh; drawn in M5).
- A physical sky that follows the sun, a twilight, a faint night glow, the sun's disk; at night
  the moon lights the scene by its phase, and (with the owner's catalogue answer) the stars turn
  with the sky. Exposure follows the sun's height (0.70 by day, measured; 4.0 at night).
- The photo's baked shadows are softened (lifted 3× inside a capture-time mask from the surface
  model), so the moving sun's shadows read and the photo's do not darken twice.
- The river: the photo's own colour, less mirror, turbulent ripples, a soft bank.
- The 0.3.0 test's fixes: a frame cap (60; 15 while paused), the log flushed line by line, a
  missing data pack named, anti-aliasing (MSAA 4×).

## Briefs, lanes and waves

A lane is one builder session; its briefs run in order on shared files. The lanes of a wave run
at once and share no file in their Scopes (checked from each brief's Scope and Depends on lines).
Design data (`config/surroundings.json`, `config/shadows.json`, `config/sky.json`, the fixtures
and vectors under `tests/shared/`) is committed with this plan; no lane writes it.

**Wave 1: seven sessions at once.**

| Lane | Briefs, in order | Files (summary; each brief's Scope is the rule) |
|---|---|---|
| A · the input | M4-01 swissALTIRegio | `datasets.py`, `lock.py`, `download.py`, `__main__.py`, `config/datasets.json` (design's pinned copy), `config/datasets.lock.json` (written by `lock regio`), their tests |
| B · the surroundings step | M4-02 | `pipeline/mattini/surroundings.py`, its tests |
| C · the capture shadows step | M4-03 | `pipeline/mattini/shadows.py`, its tests |
| D · the sky clock | M4-04 | `game/scripts/sky/sky_clock.gd`, its tests |
| E · the sky rig | M4-05 | `game/scripts/sky/sky_rig.gd`, `game/shaders/sky_physical.gdshader`, section S (`game/sky/`, `tools/stars_table.py`) only with the owner's catalogue answer, its tests |
| F · the terrain's look, then the small fixes | M4-06 → M4-08 | M4-06: `shadow_grid.gd`, `terrain_loader.gd`, `terrain_photo.gdshader`, `game/tests/render/`, `complete_world.gd`, `tools/gate.sh` (one render line), named tests; M4-08: `game/project.godot`, `release_build.gd`, `data_packs.gd`, five readers' hint lines, `tools/export.sh`, named tests. Both: `pipeline/tests/fake_tools.py` (M4-08's pinned copy keeps M4-06's lines) |
| G · the far mountains in the game | M4-07 | `surroundings_grid.gd`, `surroundings_loader.gd`, named tests |

The one shared file of wave 1 is `tools/gate_allowlist.txt`, append-only: M4-06 and M4-07 each
append their pinned line. A builder whose rebase brings another lane's line keeps every line,
re-runs the gate and says so in Findings.

**Wave 2: two sessions at once, after wave 1 has landed and been integrated.**

| Lane | Briefs | Files |
|---|---|---|
| H · the pipeline wired | M4-09 the new steps wired | `__main__.py`, `manifest.py`, `lock.py`, the steps' fit checks onto `lock.fit_problem`, the fixture manifests the brief names, `docs/RELEASE.md` §C's manifest line, their tests |
| I · the main scene | M4-10 the main scene: the clock, the sky, the keys | `main.gd`, `main.tscn`, `project.godot` (the six time actions), `sky_site.gd` (new), the hint lines of `surroundings_grid.gd` and `shadow_grid.gd`, `tools/export.sh`, `tools/gate_allowlist.txt` (three lines), the main-scene tests and the replacements M4-10 names (`complete_world.gd`, `render_photo.gd`, `fake_tools.py`, `test_export_startup_lines.py`, `test_m4_08_release_hints.gd`, …) |

Lanes H and I share no file (checked from both Scopes). Design's integration rehearsal ran all ten
briefs' pins on throwaway implementations in one tree, in this plan's order: the gate green after
wave 1 (pytest 2502, GUT 58 scripts, 358 tests, four RENDER checks) and after wave 2 (pytest 2608, GUT
61 scripts, 393 tests, 16'571 asserts); the real village from the command line gave the manifest
`a0e2ec92…` (327'265 bytes), `tools/export.sh` exit 0, and the exported Linux build printed its two
pack lines and eight startup lines with no ERROR line. Its two seams are fixed in the pins (M4-08's
census, two exceptions; M4-10's `render_photo.gd` sets `shadow_lift` 1).

**Section S (the stars)** of M4-05, and the catalogue's credit line in M4-10, are built only if
the owner chose (a) at the GO (m4-design §10); the plan's status line says which. Without it every
pin still passes (measured: M4-10's stars switch is the file `res://sky/stars.csv`).

**Hints for every lane** (from design's rehearsals of every brief, 2026-10-17):

- The area's name never appears in `pipeline/mattini/` (M2-01's census): write "the area".
- The gate runs `ruff format --check` and `gdformat --check`: format before committing.
- A docstring or comment that no longer says what the code does is a Hard Rule 2 breach no
  census sees: re-read the ones your change touches.
- `max_fps=60` (M4-08) applies to headless runs too; a test that waits frames waits real time.
- Godot imports a `.csv` as translations unless its `.import` says `importer="keep"` (M4-05).
- Name your own new test files `test_m4_<nn>_*`, so no two lanes add the same file.
- Every brief's Scope also covers its own brief file (Status, Findings) and its screenshots,
  `docs/briefs/shots/<brief id>-*.jpg`.
- `--check-only` (the gate's parse step) does not know autoloads: `main.gd` reaches DataPacks by
  `preload("res://scripts/data_packs.gd")`, never by its autoload name (M4-10's rehearsal: GUT
  alone passed).
- MSAA 4× (M4-08) crashed software Forward+ (lavapipe, signal 11) at the first frame of the real
  village; the small test world renders with it. Software Forward+ probes of the real village set
  the root viewport's `msaa_3d` to 0 and say so. Whether it is lavapipe's alone is the owner's PC's
  to show (the release record says so).
- Uniform defaults of a shader cannot be read headless (null for every one, H25): the pins
  read the declarations' text; their "does NOT prove" says so.

## Integration notes (the seams the orchestrator checks; lesson 8)

Design rehearsed every brief on throwaway implementations before the GO (the reports are
summarised in each brief's Decisions; numbers in m4-design §0).

**After wave 1** (every lane landed; pull `main`; the full gate on the combined head, to a log,
the render step run):

1. **Design's data is untouched.** `git diff <base>..HEAD -- tests/shared/ config/surroundings.json
   config/shadows.json config/sky.json` is empty.
2. **Each pipeline step meets its game reader at its fixture:** the surroundings step (B) and
   SurroundingsGrid/SurroundingsLoader (G) at `tests/shared/surroundings_fixture/`; the capture
   shadows step (C) and CaptureShadowGrid with the terrain shader (F) at
   `tests/shared/shadows_fixture/`. Each pair's pinned tests pass on the combined head.
3. **The input meets the step** (A with B): in a scratch `git clone` (H22), `lock regio` writes
   design's entry (`9afdf81d…`, 30 tiles), `download regio` fetches and verifies 179'684'396 bytes,
   then `build_surroundings` from a Python one-liner writes `d317a358…` (design's rehearsal: 37 s,
   63 s, 504 MiB). And C on the M3 surface download: `build_shadows` writes pixels `203cae73…`,
   PNG `918dfdf6…` (165 s, 542 MB).
4. **Lane F's order:** M4-08's `fake_tools.py` holds M4-06's `render_lift` lines; the gate's render
   step names `render_lift` and passes (`RENDER lift`, `RENDER classes`, `RENDER photo`,
   `RENDER trees`).
5. **The allowlist** holds M4-06's and M4-07's lines once each, and no `Ignoring script` or
   `Failed to load script` entry (M3-02).
6. **The readers' hints:** M4-08's census names `surroundings_grid.gd` and `shadow_grid.gd` as
   its two exceptions (M4-07's and M4-06's readers, moved onto `ReleaseBuild.file_hint` by M4-10;
   found by design's integration rehearsal: without the second the wave-1 gate fails).
7. **What wave 2 relies on:** `SkyClock` and `SkyRig` exist with their pinned APIs;
   `TerrainLoader.create` takes the mask; `SurroundingsLoader.create`; `ReleaseBuild`;
   `DataPacks.EXPECTED_PACKS`; each new reader refuses with one `push_error("<Reader>: <path>:
   <problem>")`.

**After wave 2:**

1. **The real village end to end** (M4-09's gate, in a scratch clone): every step from the
   command line, then `manifest`; its SHA-256 and size recorded in M4-09's Findings and in
   RELEASE.md §C; then `tools/export.sh` with the packs; the exported Linux build starts headless
   with its packs and prints every startup line in order, with no ERROR line; every file under
   100 MiB.
2. **Software screenshots** (`tools/shot.sh`, and software Forward+ on lavapipe for the light,
   H12) of the start view, the same at 08:00, 18:00 and 22:00, the river at 30 m, and a softened
   shadow at 60 m, into `docs/briefs/shots/M4-*`. Evidence, not a gate.
3. **The shadow of the far mountains** in the real village (software Forward+): at 2023-09-06
   17:45 CEST the village centre is in shadow, at 17:30 it is lit (design's horizon: 17:41).
   Record the view and the numbers. And the observation of M4-05's rehearsal (no shadow in a
   narrow straight-down view from 300 m or more with the caster off screen): check the start view
   and a view from 300 m looking down; record.

## The review plan (WORKFLOW §Review policy)

Run by the orchestrator once every brief is DONE and integrated (BUILD.md §The orchestrator 6).
Diff range: from the base to the integrated head. Each lens is its own session or isolated agent,
in its own worktree with fresh caches; it builds the real village from the pinned inputs, works
by *prove it or downgrade it*, and commits one report, `docs/reviews/M4-R1-<lens>.md`. Grades: P0
crash or wrong world, P1 a wrong result the owner would see or a Hard Rule broken, P2 a weakness a
realistic change trips, P3 the rest.

**Round R1: three lenses.**

1. **placement (Tier 1).** *Prompt:* "Prove or break that the sun, the moon, the stars, the far
   mountains and the capture mask land where config/world.json, config/sky.json and the data say.
   Follow the sun from SkyClock's true azimuth through true_to_grid_deg and WorldConfig's axes to
   the light's direction and the sky shader's sun_direction; the moon the same way; the stars'
   celestial basis (the pole's place); the surroundings grid from the pipeline's vertices to the
   mesh's positions (the cut, the 64-bit subtraction, the winding); the capture mask from the 1 m
   march to the 0.5 m PNG to the shader's rect. Use asymmetric worlds (another origin, a height
   offset, a world far from the origin), mutate every transform (the convergence's sign, a swapped
   or mirrored axis, half a cell, a flipped row order) and show each named harm reproduced and
   caught." *Must prove:* for each seam, a mutation fails a named test or render check; at the start
   moment the light's grid azimuth is 184.66° ± 0.05° and elevation 50.33° ± 0.05° (SkyClock at the
   manifest's site); the real village's far-mountain shadow matches a CPU horizon check at three
   sun positions. *Does NOT prove:* the look, the owner's GPU.
2. **inputs and determinism (Tier 2, with Hard Rule 5's full discipline).** *Prompt:* "Prove or
   break the swissALTIRegio input (lock regio, download regio, every refusal before fetching), the
   surroundings and the capture shadows steps (every refusal, computed_for, expected values before
   writing, exact bytes across two fresh clones and machines' zlib), the manifest's three new blocks
   and the wiring." *Must prove:* each refusal reached by a test and by a command (`mattini:
   error:`, no traceback); two fresh builds identical; a time or host name added to an output fails
   the gate (lesson 33). *Does NOT prove:* a real republish.
3. **game and tools (Tier 2).** *Prompt:* "Prove or break the clock's keys and texts, the rig's
   curves, the sky shader's changes, the frame cap (60, 15 paused), the flushed log, the missing-pack
   messages in an export, MSAA, the credits (swissALTIRegio's source text whole, the catalogue's
   citation if stars), the startup lines, and the export with and without its packs." *Must
   prove:* each by a test or a run of the exported build. *Does NOT prove:* that it renders or looks
   right; the Windows build.

**Adjudication:** `docs/reviews/M4-round1.md`. P0, P1 and every placement (Tier 1) P2 get fix
briefs; the other P2s and the P3s go to the board's residue list. **Verification pass V1** over the
fixes (Tier 2). **Tier 1 rounds until clean:** a placement round is clean when it reports no P2 or
above. A truncated round leaves the arc open.

## The release

**0.4.0**, shipped through `docs/RELEASE.md` with the data packs. The record's "please look at
these" list must name, for the owner's PC:

- the day: dawn, noon, dusk and night (the keys), the sky's colours, the twilight, the exposure;
- the sun leaving the village behind the mountains, which are not drawn yet (M5);
- the softened photo shadows (`shadow_lift` 3) and the remaining glows where the 2021/22 surface
  model and the 2023 photo differ;
- the river: colour, ripples, the bank;
- the moon by its phase, and the stars (if the owner chose the catalogue);
- the GPU now capped (60 fps, 15 paused): heat and fan against 0.3.0's 94 %;
- the log appearing while the game runs; the anti-aliased edges, and whether the game starts at
  all with MSAA 4× (it crashed software Forward+ on the real village; 0.3.0 on `dist` is the rollback);
- what it does NOT prove: that it renders or looks right; Compatibility draws no far-mountain shadow.

FB-003, FB-005, FB-006 and FB-007 are the feedback it closes, or closes in part: its record says
which, from the owner's next look.

## DEFERRED, said out loud

| Item | Reason | Cost to the owner |
|---|---|---|
| The Windows build's first start | the owner: "not a priority" until sharing | it may not start on Windows |
| The far mountains drawn | M5 (backdrop extents, SPEC §14) | the sun sets behind mountains you cannot see |
| Snow, clouds, weather, seasons' look | M6 | any date looks like September |
| The photo stretched on steep river walls | needs a projection for steep faces; a look arc later | steep faces stay smeared |
| Bridges | need their own geometry from swissTLM3D | a bridge reads as a hump of terrain |
| Detail below about 30 m | the photo's 0.2 m is the data | close ground stays soft |
| Lit windows | no data says which windows are lit (SPEC §13 row 44) | the village is dark at night |
| Lifted shadows' colour | a blue gain would be invented; the prototype's measured blue share stays | lifted shadows read blue-grey |
| Far-mountain shadows under Compatibility | needs a 25 km pancake that costs self-shadow detail | none for the owner (Forward+) |
