# brain.md — mattini, the whole picture in one file

Orientation for any session. Current as of **2026-10-14 — version 0.2.0 shipped (M2,
Buildings: the village terrain at 0.5 m in Terrain3D with its 1'486 buildings as a white
model, a free-fly camera, a pause screen with the credits; builds on the `dist` branch).
M3 (Surfaces and trees: the realistic look from data) is planned and has the owner's GO
(`docs/briefs/M3-plan.md`); its build runs in parallel sessions after design's last review**
(update this header when a phase closes). `CLAUDE.md` (rules) and
`docs/SPEC.md` (design) outrank this file.

## 1. WHAT
A desktop game (Windows, Linux) set in Zermatt on swisstopo open geodata; a realistic look
made from the data (from M3; M1–M2 a stylised model); real day/night and weather; sandbox first, game modes later. The owner's learning
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
from M1-03, fiona from M2-04. Why each: SPEC §4 and §13. Test counts at the last gate (the
M2 close, 2026-09-26): pytest 743 passed, 4 network tests deselected; GUT 23 scripts, 110
tests, 2800 asserts.

## 5. HISTORY
Per-arc record: `docs/history/ARCS.md`. Releases: `docs/releases/` (0.1.0, 2026-09-25;
0.2.0, 2026-09-26).
Lessons: `docs/LESSONS.md`. Ledger: `docs/history/LEDGER.md`.

## 6. NEXT
M3's build (`docs/briefs/M3-plan.md`, GO 2026-10-14): wave 1 seven lanes at once (M2's
residue, the inputs, the photo, roof colours, surfaces, trees, data packs and their game
readers), wave 2 two lanes (the command line and manifest, the main scene), then the
review round R1 and the release 0.3.0. The owner's first looks at 0.2.0 (Windows) and 0.3.0
come back through `feedback`. The board is the live version.

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
  Measured at M3 planning (2026-10-14): a test that prints `= Run Summary` and the pass
  line itself, then quits, passed the whole gate with no allowlist entry; an allowlist entry
  could except `Ignoring script`; GUT counts an inner test class as one more script; GUT
  prints its own version as `GUT version:  9.6.1` (two spaces). Brief M3-02's fixes: the
  script count must equal the `test_*.gd` files on disk, the not-run lines are never
  excepted, the version line is required.
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
- **H13 — Firing a Routine with `text` starts a new session (measured 2026-09-25).** On a
  Routine that targets an existing session (then the supervisor's waker), `fire_trigger` without `text` wakes
  the waker (04:05 and 04:08, each turn visible in `get_session`), and so does a one-shot
  `create_trigger` with `persistent_session_id` and `run_once_at`. With `text`, it starts a
  fresh session instead ("⚡ <routine name>", origin `force_run_trigger`): no repository,
  a default model, tagged `routine_notify_push`, and absent from `list_sessions`' default listing,
  so the close's tag sweep misses it. Never pass `text` when firing a Routine meant to wake
  an existing session.
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
  100 MiB file limit, so a later Godot's template may cross it alone. At 0.2.0 the `.pck`
  is 99'405'400 bytes, 5'452'200 under the limit (the terrain 96 MB, the buildings 3.1 MiB),
  and the started build peaks at 875 MiB resident, headless. The release template
  ignores `--script`, so a probe cannot run inside an export (the R1 game lens). Exports are
  not byte-reproducible: the `.pck` differs between exports at the same size. The first
  import of a fresh checkout may print `WARNING: Canceling suspended execution of
  "_enter_tree" due to a script reload.`, a warning line. The started build logs to
  `user://logs/godot.log` (Linux `~/.local/share/godot/app_userdata/mattini/logs/`).
- **H16 — Godot's meshes (measured at M2 planning and in M2-05, 2026-09-25).** Front
  faces are clockwise: `SurfaceTool.generate_normals` gives (0, 1, 0) for the triangle
  (0,0,0), (1,0,0), (0,0,1), whose right-hand normal is (0, −1, 0), so a counter-clockwise
  triangle goes in as (a, c, b) (SPEC §8). `generate_normals` smooths across shared
  vertices unless `set_smooth_group(-1)` is set first. An `ArrayMesh` stores normals as
  16-bit octahedral pairs: read back, they differ by up to about 1e-4. A `.glb` under
  `res://` is imported and an export ships the imported copy, not the file; a `.bin` or
  `.f32` ships as it is.
- **H17 — Reading swissBUILDINGS3D (measured at M2 planning, 2026-09-25).** The 2020
  per-sheet FileGDB's `Building_solid` layer is an Esri MultiPatch. fiona 1.10.1 (its
  wheel's GDAL 3.9.2) reads it as a MultiPolygon Z of triangles; pyogrio refuses the
  layer's TIN Z / MultiPatch type. GDAL cannot write a MultiPatch, and a FileGDB that fiona
  writes does not give back the triangles it was given (M2-04 Findings 8): the tests feed
  the step synthetic features, and only swisstopo's own file (the committed sample, the
  real run) exercises the reader. fiona's and rasterio's Windows wheels each bundle their
  own renamed GDAL DLLs, so they do not clash (the M2 review).
- **H18 — ruff's import order depends on the tree (measured in M2-03, 2026-09-25).** ruff
  classifies `mattini.x` as first-party only when it finds the module, so a pinned test
  that imports a module not written yet lints clean in `docs/briefs/pinning/` and fails
  `I001` once the module exists. Lint pinned tests in a layout that holds the modules
  (lesson 40).
- **H19 — Worktrees of in-session workflow agents start from the default branch
  (measured in M2, 2026-09-25).** An agent run with worktree isolation got a worktree of
  `main`, not of the session's branch: every M2 builder's first step was `git merge
  --ff-only <base>` and a check of the head.
- **H20 — swisstopo's new datasets (measured at M3 planning, 2026-10-14).** SWISSIMAGE
  2023 over Zermatt is 25 cm imagery published upsampled to 10 cm, flown 6–7 Sep 2023 at
  about 11:25–11:55 UTC (the image strips' ids, `ch.swisstopo.lubis-bildstreifen`); its
  tiles are JPEG-in-COG (quality 95, YCbCr 4:2:0), and three decoders (GDAL 3.12.4, 3.12.2,
  libjpeg-turbo 3.2) give identical pixels. swissSURFACE3D's raster has one edition per
  tile (2021 or 2022 here); the 2024 swissALTI3D comes from the same LiDAR (open ground
  agrees to 3 mm). swissTLM3D is national only: its GeoPackage zip is one deflated 10.8 GB
  member that GDAL cannot read in part (3.2 GB fetched in 300 s without listing the
  layers); its FileGDB zip (2.88 GB) has one deflated member per table, with backslashes in
  the member names, and is read straight from the zip in 24 s. data.geo.admin.ch answers
  Range requests (206) though HEAD sends no `Accept-Ranges`; HEAD carries
  `X-Amz-Meta-Sha256`, equal to STAC's checksum but in mixed case, and STAC writes some
  checksums in upper case: compare case-insensitively, store lower case. One 528 MB
  single-range transfer was cut off without an error: a big download resumes and checks its
  SHA-256. Older editions' files have been replaced after publication (Last-Modified later
  than the item, the STAC checksum updated): only the checksum notices.
- **H21 — Godot's images and packs (measured at M3 planning, 2026-10-14).** In an exported
  build `Image.compress()` returns ERR_UNAVAILABLE (4.6's compressors are editor-only); the
  DDS, KTX, JPEG, PNG and WebP loaders are there. Under the Compatibility renderer an
  ImageTexture wider or taller than 16384 px reads back all zeros with no ERROR line (16384
  works). Terrain3D's colour map is RGBA8 per vertex and its alpha a roughness modifier
  (0.5 neutral): an RGB image gets alpha 255, roughness +1; `get_color` returns the vertex
  below and left of the point, alpha 1.0. Colour under Compat (this container): no
  conversion shows on any path (a literal ALBEDO, uniforms with and without `source_color`, a
  `source_color` texel, INSTANCE_CUSTOM, instance COLOR, EMISSION: 0.5 or texel 128 all
  display as 128). An earlier reading of "custom data arrives converted to linear" was
  wrong. Forward+ linearises `source_color` samples and encodes its output, so a colour
  passed raw (instance data, vertex COLOR without `vertex_color_is_srgb`) looks right in a
  Compat shot and too light on the owner's PC. Colours enter only through `source_color`
  samplers or uniforms, or vertex colours with `vertex_color_is_srgb`; a Compat screenshot
  cannot check colour encoding. `PCKPacker` writes the same bytes for the same files in the
  same order (the order changes them); `ProjectSettings.load_resource_pack` takes a `.pck` or
  a `.zip` (a `.zip` renamed `.dat` returns false with no ERROR line), and loads in under
  1 ms; a 96 MB file is read from a `.pck` in about 55 ms.
- **H22 — A copied checkout writes into its original (measured 2026-10-14).** Copying the
  repository with `pipeline/.venv` copies a `.pth` that points at the original checkout:
  `python -m mattini` in the copy then writes into the original. Use `git clone` (the venv
  is git-ignored, so a clone makes its own with `uv sync`), or delete the copied venv.
- **H23 — Why 0.2.0 looked white (measured on a software render, 2026-10-14).** Besides
  white materials, 0.2.0's exposure (0.85, filmic) renders flat sunlit ground about 3.06×
  brighter than the photo, clipping everything above sRGB ~144 to white, and the procedural
  sky supplies 59 % of the light on flat ground with a blue cast. Exposure 0.40 renders the
  photo at its own brightness; with the sky's contribution at 0.25, exposure 0.54. Measured
  under Compatibility only; the owner's Forward+ is the check.
- **H24 — Godot imports a generated image (measured at M3 planning, 2026-10-14).** A `.jpg` or
  `.png` under `res://` is imported as a texture on the first import of every fresh checkout
  (the session-start warm-up, the gate's import step, the export's scan, the owner's editor):
  for the village's 0.2 m photo 43.6 s, 5.2 GiB peak and a 170 MB `.ctex`. An export then
  ships the imported texture and its `.import`, not the file, so a `FileAccess` read of the
  image in the build finds nothing. A `<file>.import` holding exactly
  `[remap]\n\nimporter="keep"\n` stops both: 5.8 s, the image left and shipped as it is. The
  steps that write images write it beside them (M3-04, M3-06); `tools/export.sh` step 4c
  checks that every generated file ships once, unchanged (M3-08).
- **H25 — Terrain3D's material and texture imports, headless (measured at M3 planning,
  2026-10-14).** `Terrain3DMaterial.get_shader_param()` returns null headless for every
  uniform; the readable store is the material's `_shader_parameters` Dictionary, which keeps
  only uniforms the active shader declares (a parameter set before `shader_override` is
  dropped) and does not check their types; a shader's declarations read through
  `Shader.get_shader_uniform_list()`. A texture imported without settings is lossless and has
  no mipmaps (`compress/mode=0`, `mipmaps/generate=false`; "detect 3D" reimports only in the
  editor): a committed texture that needs mipmaps carries its `.import` file. Headless, a
  MultiMesh drops `set_instance_transform` (`get_instance_transform` returns the identity)
  but keeps an assigned `buffer`: fill `buffer`. A SceneTree script that fails in
  `_initialize`, or names a class whose script fails to parse, can hang with no output and
  no exit: run `--check-only` first and wrap such runs in `timeout`.
- Benign: GUT runs end with `WARNING: ObjectDB instances leaked at exit`, a warning line,
  not an error.

## 8. PROCESS
Three realms (`docs/WORKFLOW.md`, `docs/roles/`). Spawn words `design`, `ultracode build`,
`feedback`. Design does everything before the build and plans each arc for parallel
building; one `ultracode build` orchestrator spawns builder sessions per wave, integrates,
runs the design's review plan and ships (owner, 2026-10-14). `main` is the only source branch (`dist` holds
builds). M2 ran instead in one session with in-session workflow agents, by the owner's
word for M2 (RULINGS 2026-09-25); the realms' sessions are the default again unless the
owner says otherwise. State lives in the repo, never in chat. Pinning tests travel with their brief under `docs/briefs/pinning/`
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
