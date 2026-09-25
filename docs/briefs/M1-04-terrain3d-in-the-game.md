# Brief: M1-04 — Terrain3D in the game: every height on its own vertex
Status: DONE (2160a3c)

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

Terrain3D 1.0.2 is vendored (its runtime part only) and the game turns a manifest's terrain
block into a Terrain3D terrain on which every height sits on the vertex the pipeline put it
on: `TerrainGrid` reads the block and the heights file and refuses anything wrong, visibly;
`TerrainLoader` builds the node with the settings, regions, holes and clay look the
measurements require. The gate passes on a fresh checkout that contains a GDExtension, and
a software screenshot tool exists for this and later visual briefs.

## Read first, in order

1. `CLAUDE.md`; `brain.md` §Hazards H1–H4, **H11** (every Terrain3D trap this brief is
   built around) and H12.
2. `docs/SPEC.md` §8 *The terrain grid* (*The game* and *Shared fixture*), §9 (vendoring),
   §10 (*M1's game*, the look), §12 (software screenshots).
3. `tests/shared/terrain_vectors.json` and `tests/shared/terrain_fixture/generated/`.
4. `game/scripts/world/world_config.gd` (after M1-02).
5. The pinning tests, `docs/briefs/pinning/M1-04/game/tests/`: `test_terrain_grid.gd`,
   `test_terrain_loader.gd`, `test_terrain3d_vendored.gd`.
6. Terrain3D 1.0.2's zip (below): its `extras/shaders/minimum.gdshader` is the base of the
   clay shader; its source is at `github.com/TokisanGames/Terrain3D`, tag `v1.0.2-stable`
   (`git clone` works in containers).
7. `docs/briefs/shots/M1-look-proposal-overview.jpg` and `…-start.jpg`: design's
   prototype of the look, software-rendered on the real village heights.

## Decisions already made

- **Vendoring** (SPEC §4, §9): from
  `https://store.godotengine.org/asset/tokisangames/terrain3d/download/1377/` (redirects to
  `Terrain3D_v1.0.2-stable-2.zip`, SHA-256
  `a071850250ec5e596aa54da61c01d75768774eb379ee997584d426a45f4884a2`; verify before
  unpacking), copy into `game/addons/terrain_3d/` exactly: `LICENSE.txt`, `README.md`,
  `terrain.gdextension`, `terrain.gdextension.uid`, `icons/` (40 files), and
  `bin/libterrain.{linux,windows}.{debug,release}.x86_64.{so,dll}`: about 15 MB. Nothing
  else: not the other platforms, not the editor plugin (`plugin.cfg`, `src/`, `menu/`,
  `tools/`, `utils/`, `brushes/`, `extras/`), not the demo. Bytes as in the zip, measured:

  ```
  4dbcfc70ae9005d11bd82e45cab93d8ed7e3dbb804f123e71c72abd3e95ae678  LICENSE.txt
  fed83e7f26ae341f4456a7c1be57c1d5827aa35ff2a44b68cc519d81f8a69774  README.md
  93d2f783ff7a62733ce6176746725a07750321b83bfb59feabf8f28ba76829db  terrain.gdextension
  1d0ea8752c673b1cc4212ce7eddea5b2c8f4f2c6fc80bbf523377485d6dd363a  terrain.gdextension.uid
  178ae39467bb0743c1bbdf854a00f8e7d258a3691bcc1b63d4493beb6bde865e  bin/libterrain.linux.debug.x86_64.so
  e79ebb2e48a63a5d6189a825f1d63ec847319dc8fa030936d95bf6fad8f294ef  bin/libterrain.linux.release.x86_64.so
  bf72686a7e1d8d8370ba9ba5eaa70c59375ee2cb5638d63b8942f1ad7d448cda  bin/libterrain.windows.debug.x86_64.dll
  40900e649c3c6c7619c383d28732c3e2e8dc87c2938de43b29122a668aedcf86  bin/libterrain.windows.release.x86_64.dll
  ```

  One exception, measured: Godot 4.6.3's first import rewrites the 20 `icons/*.svg.import`
  files (it adds four default keys); commit them as Godot writes them, so imports leave the
  tree clean. The commit message names the source URL and the zip's SHA-256. The editor
  plugin stays off (not in `editor_plugins/enabled`).
- **A fresh checkout** (H11): before the first Godot run, the gate writes
  `game/.godot/extension_list.cfg` listing every `res://addons/**/*.gdextension`, one per
  line, when that file is missing; the session-start hook does the same before its warm-up
  import. Measured: without it a fresh checkout's first headless run aborts at exit (exit
  134) and the gate fails; with it, exit 0.
- **`TerrainGrid`** (`game/scripts/terrain/terrain_grid.gd`, `class_name TerrainGrid`,
  `extends RefCounted`): `static func from_manifest(path: String, world: WorldConfig) ->
  TerrainGrid`, which returns null and calls `push_error("TerrainGrid: <path>: <problem>")`
  on every problem the pinned tests list; properties `area`, `spacing_m`, `columns`, `rows`,
  `x_min`, `z_min`, `height_offset_m`, `heights` (PackedFloat32Array, row-major, rows along
  +z) and `attribution`; `func height(column: int, row: int) -> float`. It places the grid
  through the WorldConfig it is given (`to_local` of the box's north-west corner, and the
  south-east corner to check `columns` and `rows`), never by subtracting an origin itself;
  it refuses a world whose axes are not x=+e, y=+h, z=−n; `file` must be a plain relative
  path inside the manifest's folder; it checks the file's size and SHA-256
  (`FileAccess.get_sha256`). Godot's JSON reads every number as a float: accept whole
  floats for `columns` and `rows`, refuse fractions. The two refusals the owner fixes by
  re-running the pipeline name `python -m mattini terrain` (and `download terrain` where no
  terrain was built).
- **`TerrainLoader`** (`game/scripts/terrain/terrain_loader.gd`, `class_name
  TerrainLoader`): `static func create(grid: TerrainGrid, parent: Node) -> Terrain3D`,
  which adds the node, named `Terrain`, to `parent` (the parent is in the tree, and a camera
  is already in its viewport) and returns it loaded. In this order, each step measured (H11):
  1. before entering the tree: `free_editor_textures = false`, `vertex_spacing =
     grid.spacing_m`;
  2. `parent.add_child(terrain)`;
  3. after entering: `collision_mode = 0` (no collision in M1: nothing walks, and collision
     over hole-only areas prints ERROR lines), `change_region_size(int(1024.0 /
     spacing_m))` (regions 1024 m wide), `material.world_background = 0` (none),
     `material.show_checkered = false`, the clay shader (below);
  4. one height image and one control image covering whole regions from the region corner
     at or north-west of the grid (`import_images` snaps to region corners), the grid
     blitted at its vertex offset, every other vertex a hole (`Terrain3DUtil.enc_hole`), then
     `data.import_images([height, control, null], <region corner>, 0.0, 1.0)`. Never import at
     a position that is not a region corner, and never import NaN.
- **The clay look** (the owner does not design; SPEC §10): `game/shaders/terrain_clay.gdshader`,
  a copy of the zip's `extras/shaders/minimum.gdshader` with its copyright line kept (MIT;
  the licence file is vendored), whose `ALBEDO`/`ROUGHNESS` lines become: a light warm-grey
  clay, roughness about 0.9, contour lines every 10 m of real height (H = local y +
  `height_offset_m`, a shader uniform the loader sets from the grid) and stronger ones every
  100 m, anti-aliased with `fwidth` and faded where they would alias. Design's prototype
  (the reference shots) used, at the end of `fragment()`:

  ```glsl
  float H = v_vertex.y + height_offset_m;
  vec3 clay = vec3(0.52, 0.50, 0.47);
  vec3 ink = vec3(0.22, 0.21, 0.20);
  float fw = max(fwidth(H), 1e-4);
  float d10 = abs(fract(H / 10.0 + 0.5) - 0.5) * 10.0;
  float d100 = abs(fract(H / 100.0 + 0.5) - 0.5) * 100.0;
  float minor = (1.0 - smoothstep(0.5 * fw, 1.5 * fw, d10)) * (1.0 - smoothstep(1.5, 3.5, fw));
  float major = 1.0 - smoothstep(1.0 * fw, 2.0 * fw, d100);
  ALBEDO = mix(clay, ink, max(minor * 0.55, major * 0.85));
  ROUGHNESS = 0.9;
  ```

  Tune it by screenshots; it must compile under Forward+ and Compatibility (the base shader
  handles both). Set `material.shader_override` then `shader_override_enabled = true`, after
  the node is in the tree.
- **The screenshot tool** (SPEC §12): `game/tools/shot.gd` (`extends SceneTree`) renders a
  manifest's terrain with the clay look, a fixed sun (elevation 35°, azimuth 150°, shadows)
  and a procedural sky with neutral ground colours, from views given as
  `name,E,N,metres_above_ground,bearing_deg,pitch_deg;…` (LV95, converted through
  WorldConfig), and saves `<out>/<name>.jpg` (1280 × 720, quality 0.85). `tools/shot.sh
  <manifest> <out_dir> <views>` runs it with `xvfb-run -a godot --path game
  --rendering-method gl_compatibility --resolution 1280x720`, and exits non-zero with a
  message when `xvfb-run` is missing. Not a gate step.
- **Allowlist:** one entry, `TerrainGrid: user://test_ # the terrain refusal tests write
  broken manifests under user://test_* on purpose`.
- **H4 in tests:** the pinned loader tests build the terrain in `before_all`; any test of
  yours that adds a Terrain3D in a test body marks the deprecation warning handled if it is
  there (the helper in M1-05's pinned `test_main_scene_terrain.gd`).

## Scope — files you may touch

`game/addons/terrain_3d/**` (vendored as above) · `game/scripts/terrain/terrain_grid.gd` ·
`game/scripts/terrain/terrain_loader.gd` · `game/shaders/terrain_clay.gdshader` ·
`game/tools/shot.gd` · `tools/shot.sh` · `tools/gate.sh` (the extension-list step only) ·
`tools/gate_allowlist.txt` (the one entry) · `.claude/hooks/session-start.sh` (the same
step before the warm-up) · `game/tests/` (the pinned copies and your own tests) ·
`docs/briefs/shots/M1-04-*.jpg`

## Depends on

M1-02 (the hardened gate before any Terrain3D test, D12). Shares no file with M1-03: the two
may run at once. The fixture is design's and read-only.

## Done when (gates)

- [ ] The three pinned files are in place and unchanged (`cmp`).
      - does NOT prove: that the pinned tests are right (design ran them against a scratch
        TerrainGrid and TerrainLoader, 2026-09-25: all passed, and every Terrain3D trap in
        H11 was hit on the way).
- [ ] The vendored files match the list above (`sha256sum`, recorded) and the icons'
      `.import` files are the only other changes; `git status` is clean after a second
      import.
      - does NOT prove: that the Windows binaries load (no Windows here).
- [ ] A fresh checkout passes: in a new worktree with no `game/.godot`, `tools/gate.sh`
      exits 0; with the extension-list step removed (saved diff), it fails at `godot import`
      (exit 134). Both runs recorded.
      - does NOT prove: the owner's first editor start on a fresh clone (not measured with a
        display).
- [ ] Mutation proofs, each undone with `git apply -R`, each row naming the owner-visible
      harm: (a) import at the grid's own position instead of the region corner →
      `test_heights_read_back_on_their_own_vertices` fails (the 48 m shift); (b) collision
      left on → the gate fails on the `min_height > max_height` ERROR lines; (c) world
      background left flat → `test_terrain3d_settings_follow_the_grid` fails; (d)
      TerrainGrid without its SHA-256 check → `test_heights_files_that_do_not_match_are_refused`
      fails; (e) TerrainGrid without its axes check → `test_a_rotated_world_is_refused` fails;
      (f) the allowlist entry removed → the gate fails on the refusal tests' ERROR lines.
      - does NOT prove: that the heights look right (next gate is evidence only).
- [ ] Software screenshots (evidence, not a gate): the fixture terrain from two views; and,
      if M1-03 is DONE when you reach this, the village from design's three views (start:
      `2624000,1096500,150,235,20`; overview: `2625000,1098000,700,215,30`; Kirchplatz:
      `2623825,1096490,60,200,35`, after `download terrain` and `terrain`). Committed as
      `docs/briefs/shots/M1-04-<view>.jpg` and named in Findings.
      - does NOT prove: that it renders or looks right in Forward+ on the owner's PC.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`.
      - does NOT prove: that it renders or looks right.

## Forbidden

Enabling or vendoring Terrain3D's editor plugin; switching GUT's error tracking off;
importing heights with NaN; a camera or main-scene change (M1-05's); changing `config/`,
`tests/shared/`, `pipeline/` or a pinned copy.

## Findings (executor writes)

Executor session, 2026-09-25. Code commit `2160a3c` (rebased onto M1-03's commits; the gate
re-run after the rebase: exit 0).

1. **For design first: H11's fresh-checkout abort did not reproduce here.** With the
   extension-list step removed (the one `step` line, saved diff), a fresh worktree's gate
   exits **0**, not 134: `godot import` printed no `Aborted` and its `.godot/` got an
   `extension_list.cfg` from Godot itself. Also tried, each in a fresh worktree of this
   commit with no `game/.godot`: a bare first `--import`, three times with and three
   times without `XDG_DATA_HOME` (all exit 0); a first GUT run and a first `--editor
   --quit` (exit 0; a first `--check-only` exits 1, H9's class cache, not an abort); the
   zip's original `icons/*.import` in place of Godot's rewrite (exit 0, then 0); the
   whole zip addon, editor plugin files included but not enabled (exit 0, then 0). So the
   gate row "fails at `godot import` (exit 134)" is not met: the step is built and kept
   as decided (it writes what Godot writes, `res://addons/terrain_3d/terrain.gdextension`),
   but nothing here shows that it is needed. What differed in design's measurement is not
   known; H11's first bullet wants a re-measure. The fresh-checkout run with the step:
   exit 0 in 30 s.
   - does NOT prove: the owner's first editor start on a fresh clone (not measured with a
     display).
2. **Pinned copies:** `cmp` of `test_terrain_grid.gd`, `test_terrain_loader.gd` and
   `test_terrain3d_vendored.gd` against `docs/briefs/pinning/M1-04/game/tests/`: all
   identical.
3. **Vendoring.** The zip from the store URL: SHA-256
   `a071850250ec5e596aa54da61c01d75768774eb379ee997584d426a45f4884a2`, as the brief says.
   `sha256sum` of the eight listed files in `game/addons/terrain_3d/`: all eight equal the
   brief's list. 48 files, 15 MB: the eight, `icons/` (20 `.svg`, byte-identical to the
   zip, and 20 `.svg.import`). No text file has a CR, so `.gitattributes`' `eol=lf` leaves
   every byte as in the zip. Godot 4.6.3's first import rewrote the 20 `.svg.import` files
   by adding **six** lines each (the brief says four keys): `compress/uastc_level=0`,
   `compress/rdo_quality_loss=0.0` and `process/channel_remap/red|green|blue|alpha`;
   committed as Godot wrote them. A second `--import`: exit 0, `git status` empty. The
   editor plugin is neither vendored nor in `editor_plugins/enabled` (pinned test).
   - does NOT prove: that the Windows binaries load (no Windows here).
4. **The gate on the pushed head:** exit 0. pytest 362 passed, 3 deselected; GUT 12
   scripts, 40 tests, 1367 asserts, all passed. 60 `ERROR` lines, each excepted: 16 are
   `TerrainGrid: user://test_…` (the pinned and my refusal tests), the rest M1-02's two
   WorldConfig entries. H4's deprecation warning prints once, in the loader tests'
   `before_all`, so no test is charged with it and the gate does not scan `WARNING` lines;
   no test of mine adds a Terrain3D in a test body.
5. **Mutation proofs.** Each a full `tools/gate.sh` in its own fresh worktree of this
   commit before the rebase (`c7c9ec2`, the same game code), made with `git worktree add`
   and removed after the run, two at a time. The unmutated run: exit 0.

   | Run | Mutation | Exit, step | Evidence | Owner-visible harm it reproduces |
   |---|---|---|---|---|
   | a | the grid image alone imported at the grid's own position (`Vector3(x_min, 0, z_min)`) | 1, `gut` | `test_heights_read_back_on_their_own_vertices`: `[0.0] expected to equal [600.0625]` (north-west corner); also `test_terrain3d_settings_follow_the_grid` (regions `[(0,0)]`) and the holes test | the village drawn 1 km off its coordinates (the fixture's shift; 48 m in design's village measurement) |
   | b | `collision_mode` line removed | 1, `gut` | 13 × `ERROR: Condition "min_height > max_height" is true.` in the gate's error lines; also `[1] expected to equal [0]: no collision in M1` | a console full of engine errors, and collision the camera does not need |
   | c | `world_background` line removed | 1, `gut` | `test_terrain3d_settings_follow_the_grid`: `[1] expected to equal [0]: world background none: no invented ground` | an invented flat ground plane at 0 m around the village (Hard Rule 2) |
   | d | the SHA-256 comparison disabled (`if false and …`) | 1, `gut` | `test_heights_files_that_do_not_match_are_refused`: `a file with one bit changed is refused` fails | a damaged or stale heights file drawn as if it were the pipeline's |
   | e | the axes comparison disabled | 1, `gut` | only my `test_a_rotated_world_is_refused_for_its_axes` fails. The pinned `test_a_rotated_world_is_refused` **passes**: the columns check refuses the rotated grid too (`do not fit lv95_box at 0.5 m (-22.0 × 41.0)`), and the pinned test accepts any refusal | a rotated world refused with the wrong reason; for every proper rotation but the owner's, the box no longer fits, so no rotated grid is drawn either way |
   | f | the `TerrainGrid: user://test_` allowlist entry removed | 1, `gut` | GUT: 40 passed, `All tests passed!`; the gate: `error lines in the output: ERROR: TerrainGrid: user://test_terrain_grid/…` | — (the entry is needed; without it the refusal tests' own lines fail the gate) |
   | g | `control.fill(hole)` removed | 1, `gut` | `test_vertices_of_the_regions_outside_the_grid_are_holes`: `one vertex west of the grid: a hole` | an invented flat ground at 0 m over the rest of each 1 km region |
   | h | the lattice check disabled | 1, `gut` | `test_a_grid_off_the_vertex_lattice_is_refused`: `a grid between the vertices is refused` | heights a quarter metre off their vertices |
   | i2 | the world-origin comparison removed | 1, `gut` | my `test_a_world_from_another_manifest_is_refused` fails (the grid is accepted) | a grid placed with another manifest's origin: 1 km off in the test |
   | j | the whole-number check removed | 1, `gut` | my `test_a_fractional_column_count_is_refused` fails; the grid is still refused, by the columns check (`(41 × 24) do not fit … (41.5 × 24.0)`) | a refusal with a less precise reason |

   - does NOT prove: that the heights look right (the next item is evidence only). Runs e
     and j: two of TerrainGrid's checks are backed by the columns check, so only my own
     tests with the refusal's reason see them go (lesson 10).
6. **Software screenshots** (evidence, not a gate; Compatibility on llvmpipe under Xvfb,
   `tools/shot.sh`, each run 7 s for the fixture and 22 s for the three village views):
   - `docs/briefs/shots/M1-04-fixture-overhead.jpg` (`2601025,1199983.75,14,0,89`) and
     `M1-04-fixture-oblique.jpg` (`2601016,1199979,8,45,30`): the 20 × 11.5 m fixture is
     the only thing drawn, with the 1600 m and 1610 m contours; everything around it is
     the sky's neutral ground, so the holes and "no world background" show.
   - After `download terrain` (6 tiles, 6 fetches) and `terrain` (`village.f32`
     `b6334c1f…411a`, SPEC §8's value): `M1-04-start.jpg`, `M1-04-overview.jpg` and
     `M1-04-kirchplatz.jpg`, design's three views. Start and overview match design's
     reference shots view for view: the valley, the contours every 10 m, the stronger
     100 m ones, the terrain's edge against the neutral ground. The clay constants are
     design's prototype, unchanged.
   - does NOT prove: that it renders or looks right in Forward+ on the owner's PC.
7. **The real village, headless** (a probe script, not committed): `TerrainGrid` read the
   4001 × 6001 grid in 975 ms (x_min 0.0, z_min −2000.0); `TerrainLoader.create` took
   5.5 s; six regions, (0,−2) to (1,0); Godot's static memory peak 831 MB; 7.0 s for the
   whole run. 2000 random vertices read back from Terrain3D equal the grid's heights
   exactly (worst difference 0.0 m). Kirchplatz 1 (E 2623825.25, N 1096489.75): H 1617.06 m.
   For M1-05: loading the village is a 5–6 s wait on start.
8. **Choices inside the brief's scope** (reversible):
   - TerrainGrid also refuses: a WorldConfig whose origin or height offset differs from
     the manifest's own world block (run i2); an empty `area`; an empty attribution; a
     `sha256` that is not 64 hex digits. The heights-file refusals (missing, wrong size,
     wrong SHA-256) also name `python -m mattini terrain`, following SPEC §10's "errors on
     screen" rule; "no terrain built" names `download terrain` then `terrain`, as the
     brief says. TerrainGrid does not scan the heights for NaN (24 million floats in
     GDScript would take seconds): the SHA-256 match ties the file to the pipeline, which
     refuses non-finite values.
   - The checks run in this order: world given, manifest readable, terrain built, built
     for this world, the world's origin and axes, the block's fields, the placement (fit,
     then lattice), the heights file (path, size, SHA-256).
   - TerrainLoader has no guard for a parent outside the tree: a test of such a guard
     would print an ERROR line the one-entry allowlist cannot except. Without the tree,
     `material` is null and the script stops with a `SCRIPT ERROR`: the first
     `shot.gd` run did exactly that from `_initialize` (the root enters the tree only after
     it returns), and Godot then kept running for 5 minutes until killed. Hence `shot.gd`
     waits one frame before it builds anything, and `shot.sh` runs Godot under `timeout`
     (`SHOT_TIMEOUT`, default 300 s) and fails unless every `<name>.jpg` was written
     (H2), after deleting stale ones first.
   - `shot.gd`: a view over no terrain (NaN height) ends the run naming the view, rather
     than inventing a ground height; the pitch is degrees below the horizon and the
     bearing is clockwise from north (design's view strings read that way); camera near
     0.5 m, far 20 km; shadows to 3000 m; filmic tone mapping; the sky's ground colours are
     greys 0.42 and 0.62; 10 frames before each capture. Every capture came out 1280 × 720
     (it is resized only if not).
   - The gate's `extension_list` and the hook's block write the list with `LC_ALL=C sort`;
     the hook's copy is soft-failing like its other steps and was not run in this session
     (the hook runs at container start).
   - My own tests: `game/tests/test_terrain_grid_placement.gd` (the fixture control, a
     world from another manifest, a fractional count, a rotated world refused for its
     axes).
   - Compile-forced files outside the Scope list, named in the commit: the `.uid` files
     Godot writes for `terrain_grid.gd`, `terrain_loader.gd`, `terrain_clay.gdshader` and
     `shot.gd`, so that imports leave the tree clean.
