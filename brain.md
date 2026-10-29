# brain.md — mattini, the whole picture in one file

Orientation for any session. Current as of **2026-10-29 — version 0.4.0 (the river flows downstream along
swissTLM3D's lines; the sun and the moon move at the game's time, a physical sky and stars on the Hipparcos Catalogue; built
from `main` `4bf2d83` by the first release session to run two lanes, recorded in `docs/releases/v0.4.0.md`; no P0 or P1 open) is
built and audited, its `dist` commit `e2633b6` waits for the owner's "push dist"** (local branch `dist-publish` of the release
session's container; until pushed, `dist` still holds 0.3.1, `5b51347`, built from `main` `cb5946e`; 0.3.1 stays as
`mattini-0.3.1/`, the rollback)
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
0.4.0 release gate, 2026-10-29): pytest 2407 passed, 5 network tests deselected; GUT 64 scripts, 395 tests, 18196 asserts; the
gate's render step passes (RENDER trees 0.8615, repeating exactly).

## 5. HISTORY
Per-arc record: `docs/history/ARCS.md`. Releases: `docs/releases/` (0.1.0, 2026-09-25;
0.2.0, 2026-09-26; 0.3.0, 2026-10-16, `dist` `5f08379`).
Lessons: `docs/LESSONS.md`. Ledger: `docs/history/LEDGER.md`.

## 6. NEXT
The owner's word "push dist" for 0.4.0 (`git push origin dist-publish:dist` from the release session's checkout, or rebuild: the
export is not byte-reproducible, H15). Then, from a fresh `ultracode design` session: the softened photo shadows (FB-004 item 3;
M4-03, M4-06, the shadows parts of M4-09 and M4-10, rebuilt on 0.4.0's files per `docs/briefs/v0.4.0-plan.md`'s process note) and
delivery through GitHub Releases (the owner's "Yes if it makes sense", 2026-10-29), then the far mountains' shadows (M4-01,
M4-02, M4-07 and their parts of M4-09 and M4-10), the trees' variant the owner picks from the record's table, a clamp or label
for the clock's range, the move to Godot 4.8 once it is out of beta, M5 scale-up, M6 weather and walking. The board is the live
version.

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
- **H12 — Software rendering in containers (measured 2026-09-25; corrected 2026-10-15).** Xvfb and
  Mesa's llvmpipe are preinstalled: `xvfb-run -a godot --path game --rendering-method
  gl_compatibility …` renders Terrain3D and saves screenshots. Forward+ on Mesa's lavapipe did
  crash as soon as Terrain3D drew (M1); measured again in M3's review round and its verification
  pass, it renders the whole village and the exported build: `apt-get update`, then `apt-get install
  mesa-vulkan-drivers`, then `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json xvfb-run -a godot
  --path game --rendering-driver vulkan --rendering-method forward_plus …` (the install fails
  without the `update` in a fresh container). A Forward+ software image shows what Forward+ does
  with normals, lighting and `source_color`, which a Compatibility image cannot; it is still not the
  owner's GPU or look. A Compatibility image is not the Forward+ look.
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
  not byte-reproducible: the `.pck` differs between exports at the same size. Measured at the 0.3.0
  release (2026-10-16): of `mattini.pck`'s 119 entries exactly one varies between fresh clones, the
  exported binary form of the main scene (`.godot/exported/…/export-…-main.scn`, same size, other
  bytes: three clones, three hashes); a re-export inside one clone reuses Godot's cache and gives the
  same file, so "two exports in a row" proves nothing (lesson 33). The data packs, the executables and
  the libraries were byte-identical in every build, and a record that lists a `.pck` hash lists the
  one that was pushed. The first
  import of a fresh checkout may print `WARNING: Canceling suspended execution of
  "_enter_tree" due to a script reload.`, a warning line. The started build logs to
  `user://logs/godot.log` (Linux `~/.local/share/godot/app_userdata/mattini/logs/`). Measured at the 0.3.1
  release gate (2026-10-26): an exported build reads an `override.cfg` beside its executable (a version
  override showed in every startup line), and `--print-fps` prints `Project FPS: 60` headless under the
  project's cap.
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
- **H26 — GDScript `!=` across types, and Godot's flat normal (measured in M3's review round,
  2026-10-15).** `!=` between a bool, a String, an Array or a Dictionary and a value of another type is
  a runtime error ("Invalid operands … in operator '!='"): the function stops, a guard that held it
  does not refuse and the reader returns its block (a numeric `world_sha256` passed all six readers,
  R1 G-03). null and an int against a float are not errors; two containers of one type compare
  without error whatever their elements hold. `ManifestValue.differs` (fix-5) is the guarded compare.
  Godot 4.6.3's face normal from screen derivatives is `cross(dFdy(VERTEX), dFdx(VERTEX))`; the other
  order points into the surface and lights every facet from inside, in both renderers (R1 G-01).
- **H27 — The surfaces PNG depends on the zlib build (measured in M3's review round, 2026-10-15).**
  `zlib.compress(…, 9)` writes 1'148'848 bytes with zlib 1.3 and 950'236 with zlib-ng 2.2.5 for the
  village's class grid; the PNG's SHA-256 is in its description and so in `manifest.json`: the
  expected manifest `3ca0445c…` holds only where zlib is 1.3 (R1 I-01, the board's design question).
  Every other step's output is byte-identical across machines in every run so far.
  Measured at the fix wave's planning (2026-10-15): zlib 1.3.2 (uv's managed CPython 3.13.14) writes
  zlib 1.3's bytes (the fixture at every cell, a 2500 × 4000 class-like grid); zlib-ng writes other bytes
  for the fixture at 0.2 m but the same at 0.5 and 1 m: a small grid can compress alike. Brief M3-R1-fix-6
  (`da8914f`, verified in round R2 on zlib 1.2.11 to 1.3.2 and against zlib-ng) made the PNG's bytes
  design's data: `config/surfaces.json` holds `expected_png_sha256` per cell, and the step refuses
  another deflate before writing, naming the machine's zlib. Python 3.14's Windows builds move to
  zlib-ng; the project's `requires-python` pin is below 3.14.
- **H28 — The gate's render step (measured at M3-R1-fix-3 and round R2, 2026-10-16).** `tools/gate.sh` ends
  with `render`: two SceneTree scripts in `game/tests/render/` (names without `test_`, so GUT does not count
  them) run under `xvfb-run -a` with Compatibility on Mesa llvmpipe, 12 to 19 s, and print one `RENDER <check>:
  PASS|FAIL …` line each (photo, classes, trees). Under Xvfb a Godot run needs `--audio-driver Dummy`, or ALSA's
  probe prints an `ERROR` line the gate's scan refuses. From 0.3.1 the classes check switches the light's highlight
  off and every number repeats exactly between runs (15 runs at v0.3.1-01's rehearsal): a count that moves is a
  defect to read, not drift. From v0.4.0-08 the main scene's clock runs, so the render scripts stop it
  (`main.set_process(false)` right after `add_child`, v0.4.0-11): without that RENDER trees moved in its fourth decimal;
  with it the number repeats exactly again (0.8615). The step cannot see the river's direction (it zeroes the ripples). Where `xvfb-run` is missing the step
  fails unless `MATTINI_SKIP_RENDER=1`, which skips and says so on both streams and excuses nothing where `xvfb-run`
  exists. It proves where the photo, the water class and the crowns' colour land on a flat 16 m test world with
  positive coordinates (a shift of 0.1 m, a flip, swapped axes); it does not see an empty forest, rock, road or path,
  distance, or the terrain's mesh (round R2 P-01 to P-04), and it is not the look.
- **H29 — The river's shader and the sky (measured in 0.4.0, 2026-10-27 to 29).** Shader `TIME` advances by
  `process_step * Engine.time_scale` per drawn frame (with `--fixed-fps 60` each step is exactly 1/60 s and two software renders
  are byte-identical), so a use of `Engine.time_scale` would speed the river: M4-10 forbids it for the game clock, which moves the
  sun and the moon only. A `sampler2D` uniform without `hint_default_black` reads **white** (1, 1, 1, 1) when unset under
  Compatibility (found by the release rehearsal's seam check 02 x 03: `water_flow` declares the hint so an unset flow means no
  drift). The sky's ground (`SkyRig.GROUND_COLOUR`, 2.6 x the physical K) is measured in software Forward+; Godot's default
  `ground_color` gives faces that look sideways about a third of 0.3.1's ambient light. Software Forward+ renders of the real
  village need MSAA 4x off (it crashed lavapipe) and `mesa-vulkan-drivers` (H12).
- **H30 — Network and publishing from a cloud container (measured 2026-10-29).** `cdsarc.cds.unistra.fr` (the Hipparcos Catalogue,
  CDS I/239) answered the pin authors on 2026-10-27 and reset every connection two days later ("Connection reset by peer",
  `ws_closed_mid_exchange` in the agent proxy's log): the star table's source is identified by its size and SHA-256
  (53'316'318 bytes, `58ceabb1…16e0`), so the session keeps a verified copy in its checkout's git-ignored `data/raw/hipparcos/`
  (docs/history/blocked/2026-10-29-1.md). The auto-mode classifier refused `git push origin dist-publish:dist` once, without a
  reason: a 21 MB binary into a public branch needs the owner's word, as at 0.3.0. GitHub refuses a file over 100 MiB on a push, public
  repository or not; 2 GB is the limit for Release assets and Git LFS.
- Benign: GUT runs end with `WARNING: ObjectDB instances leaked at exit`, a warning line,
  not an error.

## 8. PROCESS
One session per release (`docs/WORKFLOW.md`, `docs/roles/`; adopted on the owner's word
2026-10-24 from another of their projects, the handoff kept as `docs/history/WORKFLOW-SEED.md`).
Spawn words: `ultracode design` (a release start to finish: two-list triage, the go with the
helpers' model, the budget and the lane count, batch-sized briefs built one builder agent each
through `docs/briefs/RELEASE-WORKFLOW.js`, reviews by tier, the whole-range review, the release
gate, RELEASE.md, the record, the end), `design` (a conversation, builds nothing), `feedback`
(the clerk). A release is two days of build and about half a week's allowance, the owner's inbox
first, the list frozen at the go. Three gate levels: the standard gate per commit, the batch gate
before DONE, the release gate from a fresh clone. Lanes are separate sessions: one build-running
agent per container. Nothing pins a model; the batch script sets the one effort. `main` is the only source branch (`dist`
holds builds). State lives in the repo, never in chat. Pinning tests travel with their brief under
`docs/briefs/pinning/` (WORKFLOW §Brief lifecycle). Before 2026-10-24: three realms (design,
`ultracode build` orchestrator with builder sessions per wave, clerk), their record
`docs/history/ARCS.md`; M2 ran in one session with in-session agents by the owner's word.

## 9. KEY FILES
1. `CLAUDE.md` — rules, commands, spawn words.
2. `docs/SPEC.md` — design of record, including the decision record (§13).
3. `docs/ROADMAP.md` — the board, open items only.
4. `docs/WORKFLOW.md` and `docs/roles/` — the process, one doc per role.
5. `config/world.json` — origin, axis mapping, areas (the one home).
6. `config/datasets.json` — datasets, pinned editions, attribution.
7. `tests/shared/world_vectors.json` — the conversions both halves must agree on.
8. `docs/briefs/` — briefs, `<release>-plan.md`, `BLOCKED.md`, `pinning/`, `TEMPLATE.md`,
   `RELEASE-WORKFLOW.js` (the per-batch helper-agent script).
9. `docs/LESSONS.md` — lessons by role tag.
10. `tools/gate.sh` — the standard gate (from M0-01 on).
11. `docs/releases/` — one record per version; the builds are on the `dist` branch
    (`README.md` there says how to start and roll back).
