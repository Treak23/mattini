# brain.md — mattini, the whole picture in one file

Orientation for any session. Current as of **2026-09-25 — version 0.1.0 shipped at the
close of arc M1 (Terrain): the village terrain at 0.5 m in Terrain3D, a free-fly camera, a
pause screen with the credits; builds on the `dist` branch. Arc M2 (Buildings) is running,
planned, built and closed in one session by the owner's word (RULINGS 2026-09-25)**
(update this header when a phase closes). `CLAUDE.md` (rules) and
`docs/SPEC.md` (design) outrank this file.

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
4.5.0; Python 3.13 via uv with a committed lockfile; pytest and ruff; rasterio and numpy
from M1-03. Why each: SPEC §4 and §13. Test counts at the last gate (the M1 close,
2026-09-25): pytest 367 passed, 3 network tests deselected; GUT 15 scripts, 69 tests,
1641 asserts.

## 5. HISTORY
Per-arc record: `docs/history/ARCS.md`. Releases: `docs/releases/` (0.1.0, 2026-09-25).
Lessons: `docs/LESSONS.md`. Ledger: `docs/history/LEDGER.md`.

## 6. NEXT
M2 Buildings is running (the board). M2-01 and M2-02 carry M1's review residue; M2-03 to
M2-05 bring swissBUILDINGS3D's buildings into the pipeline and the game, once the owner
has chosen the access route. The owner's first look at 0.1.0 comes back through
`feedback`. The board is the live version.

## 7. HAZARDS
All measured in a cloud container on 2026-09-24 (Godot 4.6.3): on day one, by M0's
builders, and by its review (M0 R1, `docs/reviews/`).

- Containers have no GPU: nothing verifies rendering; the owner's PC does (start.md 1A).
- **H1 — Godot's import exits 0 on errors.** `godot --headless --path game --import`
  returns 0 while printing `ERROR: Error importing 'res://…'`. The gate scans the output.
  Godot prints that error only on the run that imports the file; later imports print
  nothing and exit 0 while its `.import` file keeps `valid=false`, which the gate also
  checks. In a fresh cloud container that first run is the session-start hook's warm-up,
  whose output is discarded, so there `valid=false` is the only detector (R1 G-05). To see
  Godot's reason, delete the `.import` file and import again.
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
  instance_reset_physics_interpolation() is deprecated.` It prints once per process, for
  the first Terrain3D only (measured 2026-09-25), so which test sees it depends on the run
  order. Handle it explicitly in every test that adds Terrain3D to the tree: mark a
  matching entry of `get_errors()` handled if one is there (the helper in
  `docs/briefs/pinning/M1-05/game/tests/test_main_scene_terrain.gd`). Note that
  `assert_engine_error_count(0)` also counts handled errors. Never switch GUT's error
  tracking off globally.
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
- **H8 — GUT 9.6.1's other blind spots.** It exits 0 when it runs nothing, printing
  `[ERROR]: Nothing was run.` (the gate scans `[ERROR]`). A test that calls
  `get_tree().quit()` ends the run with exit 0 and no summary line (R1 G-02); an engine
  error in `before_all` fails no test (G-03; `after_all` by the same code path, not run);
  it loads `res://.gutconfig.json` by default, and a committed one with
  `"failure_error_types": []` switches its error tracking off (G-04). The gate closes all
  three since M1-02: the summary line, the `ERROR` scan, `-gconfig=` (its runs b, c, d).
- **H9 — Small traps, each measured.** GNU grep treats output holding a NUL byte as binary
  and prints `binary file matches` instead of the lines, exit 0, so a scan without `-a` goes
  blind (G-07; Godot's `print` replaces NUL, native GDExtension output may not). Godot's
  `JSON` reads every number as a float and keeps the last of two duplicate keys, and
  `JSON.parse_string()` prints an `ERROR` line of its own where `JSON.new().parse()` does
  not (M0-03 Findings 10). `--check-only` on a script using a new `class_name` fails until
  an import has refreshed the class cache (Findings 9). gdtoolkit reads its config from the
  working directory upward, so `gdlint game` lints the vendored GUT; pass the file list
  (Findings 8). Python 3.13's urllib ends a body cut short before its `Content-Length`
  without an error; only the checksum catches it (M0-04 Findings 6). A worktree does not
  isolate Godot's `user://` (`~/.local/share/godot/app_userdata/mattini` for every
  checkout): two gates at once in one container collide unless `XDG_DATA_HOME` differs
  (G-10).
- **H10 — Line endings on Windows.** Without a `.gitattributes`, a checkout with
  `core.autocrlf=true` (Git for Windows' default install choice) gets CRLF: `tools/gate.sh`
  then fails in bash (`set: pipefail: invalid option name`) and `config/world.json`'s
  SHA-256, so the manifest, changes (R1 C-04, simulated on Linux). Fixed by M1-01's
  `.gitattributes` (`* text=auto eol=lf`, binaries such as `.f32` marked): such a clone
  gets the same bytes (its test; the M1 R1 game lens, all 484 files). `dist` carries its
  own (`* binary`).
- **H11 — Terrain3D 1.0.2 in Godot 4.6.3, measured at M1 planning (2026-09-25).** Each
  line below was measured in a cloud container; the M1-04 loader is built around them.
  - Measured once, at M1 planning: a fresh checkout's first headless Godot run that
    discovers the GDExtension aborted at exit (`Aborted`, exit 134) after importing. Not
    reproduced in any fresh-checkout run since (the M1-04 builder's eleven, the R1 game
    lens's two, the M1 close's export). The gate and the hook still write
    `game/.godot/extension_list.cfg` (one `res://…/terrain.gdextension` per line) before
    the first run; it costs nothing.
  - `import_images()` puts the image's first pixel at the corner of the region that holds
    the position given, not at the position (a heightmap placed at z = −2000 at region size
    1024 landed at z = −2048, 48 m north). Pass region-aligned images.
  - It turns every height that is not a normal float (0.0, NaN, ±inf) into the `offset`
    argument: NaN is not a hole, it is 0 m.
  - `get_height()` is NaN outside the regions and on holes, 0.0 on region parts no image
    filled, and bilinear between vertices.
  - Properties set before the node enters the tree: `region_size` and `collision_mode` are
    silently ignored (stay 256 and 1); `free_editor_textures` and `vertex_spacing` work.
    `region_size` set before entering, together with `set_camera()`, crashed Godot once
    (signal 11). Use `change_region_size()` after entering the tree.
  - `material` is null until the node enters the tree. Its `show_checkered` debug view is
    on by default and paints a checkerboard over any shader, an override included; with
    it off and no textures the default shader is black. Its `world_background` defaults to
    a flat plane at 0 m.
  - A Terrain3D made in code prints `ERROR: Resource file not found: res://` and `ERROR:
    Error loading resource: ''` on entering the tree unless `free_editor_textures` is set
    false first (terrain_3d.cpp:853–857). With no camera in the viewport it prints
    `ERROR: … Cannot find the active camera` and stops its `_physics_process`; it looks at
    its first physics frame, not on entering the tree, so a camera made current in the
    same frame is found (M1-05 Findings 1).
  - Collision (on by default) over areas that are all holes makes Godot print `ERROR:
    Condition "min_height > max_height" is true.`, 13 times for the fixture. M1 turns
    collision off; walking (M6) needs an answer.
  - The editor plugin enabled makes every headless import print two leak ERROR lines at
    exit: it is not vendored.
  - Loading 4001 × 6001 heights (the village at 0.5 m) takes 2.9 s and about 540 MB
    headless; 2001 × 3001, 0.3 s.
- **H12 — Software rendering in containers (measured 2026-09-25).** Xvfb and Mesa's
  llvmpipe are preinstalled: `xvfb-run -a godot --path game --rendering-method
  gl_compatibility …` renders Terrain3D and saves screenshots. Forward+ on Mesa's lavapipe
  (Vulkan, installable with apt) crashes as soon as Terrain3D draws. A Compatibility image
  is not the Forward+ look.
- **H13 — Firing a Routine with `text` starts a new session (measured 2026-09-25).** On the
  waker's Routine (it targets the waker's own session), `fire_trigger` without `text` wakes
  the waker (04:05 and 04:08, each turn visible in `get_session`), and so does a one-shot
  `create_trigger` with `persistent_session_id` and `run_once_at`. With `text`, it starts a
  fresh session instead ("⚡ <routine name>", origin `force_run_trigger`): no repository,
  Sonnet, tagged `routine_notify_push`, and absent from `list_sessions`' default listing,
  so the close's tag sweep misses it. Never pass `text` when firing the waker.
- **H14 — A session's checkout is shallow, and its local `main` can be an old ref
  (measured twice, 2026-09-25).** Sessions clone with depth 50. When the local `main` is
  older than the boundary, `git fetch origin main` reports a "forced update" and `git pull
  origin main` "diverged" with no merge base, although the old ref is an ancestor of
  `origin/main`: `git fetch --unshallow origin main` shows it, then `git pull --ff-only
  origin main` fast-forwards (M1-05 Findings 8; the M1 close, where the old ref was the
  repository's first commit). `git checkout -B main origin/main` was refused by the
  auto-mode classifier once and accepted once. Fetch `origin main` by name: a plain fetch
  of every branch also pulls `dist`'s builds. Since M2 planning every spawn prompt and
  CLAUDE.md's spawn-word line read `git fetch --unshallow origin main || git fetch origin
  main`, then `git checkout main && git pull --ff-only origin main` (D21).
- **H15 — Exports (measured at the M1 close, 2026-09-25).** The executables are Godot's
  release templates unchanged: the Windows one is 104'659'456 bytes, 198 KB under GitHub's
  100 MiB file limit, so a later Godot's template may cross it alone. The release template
  ignores `--script`, so a probe cannot run inside an export (the R1 game lens). Exports are
  not byte-reproducible: the `.pck` differs between exports at the same size. The first
  import of a fresh checkout may print `WARNING: Canceling suspended execution of
  "_enter_tree" due to a script reload.`, a warning line. The started build logs to
  `user://logs/godot.log` (Linux `~/.local/share/godot/app_userdata/mattini/logs/`).
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
11. `docs/releases/` — one record per version; the builds are on the `dist` branch
    (`README.md` there says how to start and roll back).
