# Brief: M1-05 — Free-fly over the village
Status: DONE (29e829f)

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

Starting the game shows the village terrain in the clay look under a fixed sun and a sky,
seen from 150 m above its centre towards the Matterhorn, and the owner can fly anywhere
over it like in the Godot editor's fly mode. Escape opens a pause screen with the version
(the only place it shows), the controls, the credits and Resume and Quit. When the
generated data is missing, refused or stale, the screen says so and names the command that
fixes it.

## Read first, in order

1. `CLAUDE.md`; `brain.md` §Hazards H4, H11, H12.
2. `docs/SPEC.md` §10 *M1's game* (look, camera, pause screen, errors), §11 (the version),
   §8 *The terrain grid*, §12 (software screenshots); `docs/RELEASE.md` §A (credits).
3. M1-04's `TerrainGrid`, `TerrainLoader`, `game/tools/shot.gd` and its Findings.
4. The pinning tests, `docs/briefs/pinning/M1-05/game/tests/`: `test_free_fly_camera.gd`,
   `test_main_scene_terrain.gd`.
5. The current `game/main.tscn` and `game/tests/test_main_scene.gd` (M0-03's).

## Decisions already made

- **Scene** (`game/main.tscn`, root `Main`, a `Node3D` with `game/scripts/main.gd`):
  `@export var manifest_path := "res://assets/generated/manifest.json"`; children `Camera`
  (FreeFlyCamera), `Sun` (DirectionalLight3D), `Environment` (WorldEnvironment), `Terrain`
  (made at runtime by TerrainLoader, after the camera is in the tree) and `UI` (CanvasLayer)
  with `ErrorPanel` (a Control holding the Label `Message`, hidden unless there is an error)
  and `PauseMenu` (a Control holding the Labels `Version`, `Controls`, `Credits` and the
  Resume and Quit buttons, hidden at start). `func toggle_pause()` opens and closes it.
- **Loading:** `WorldConfig.from_manifest`, then `TerrainGrid.from_manifest`, then
  `TerrainLoader.create`; stop at the first refusal (one push_error per problem) and show it
  in `ErrorPanel/Message` with the command that fixes it: a missing or refused manifest →
  `uv run --project pipeline python -m mattini manifest`; no terrain built, or a stale or
  damaged one → `uv run --project pipeline python -m mattini download terrain` and then
  `… python -m mattini terrain`. The camera flies either way.
- **FreeFlyCamera** (`game/scripts/camera/free_fly_camera.gd`, `class_name
  FreeFlyCamera`, `extends Camera3D`), the API the pinned tests use: exported `speed_mps`
  30, `fast_factor` 5, `min_speed_mps` 2, `max_speed_mps` 1000, `wheel_factor` 1.25,
  `mouse_sensitivity` (radians per pixel), `clearance_m` 1.5; `var height_at: Callable`
  ((x, z) → ground height or NaN; main wires it to the terrain's `get_height`);
  `var input_enabled := true`; `fly(delta, direction, fast)` (direction x = right, y = world
  up, z = back; along the view, pitch included; a diagonal is not faster);
  `look(relative: Vector2)` (yaw and pitch; pitch stops at ±89°); `change_speed(steps)`;
  `set_view(at, yaw, pitch)`. After every move the camera stays `clearance_m` above the
  ground where `height_at` gives a finite height. `_process` reads the actions;
  `_unhandled_input` captures the mouse while `fly_look` is held, turns on mouse motion,
  and changes speed on the wheel. Near 0.1 m, far 20 km, field of view 70°.
- **InputMap actions** in `game/project.godot`: `fly_forward` W, `fly_back` S, `fly_left` A,
  `fly_right` D, `fly_up` E, `fly_down` Q, `fly_fast` Shift, `fly_look` the right mouse
  button, `pause` Escape (physical keys).
- **Start view:** at the grid's centre (x_min + (columns − 1)·s/2, z_min + (rows −
  1)·s/2), 150 m above the ground there, facing bearing 235° (clockwise from LV95 north,
  towards the Matterhorn), 20° down. Compute the direction from LV95 north and east through
  `WorldConfig` (`to_local` of points 1 m apart), not from a hard-coded axis.
- **Sun and sky:** a DirectionalLight3D at elevation 35° from azimuth 150°, shadows on; a
  ProceduralSkyMaterial sky, with neutral grey-blue ground colours (below the horizon lies
  no data, not earth). Exposure so that the clay is light grey, not white (design's first
  prototype came out washed out).
- **Pause screen:** `Version` reads `mattini <application/config/version>`; nothing else
  shows the version, not the window title (owner, 2026-09-25). `Controls` lists every
  control with its key. `Credits`: for the terrain, `<dataset> <edition>, <attribution>`
  from the manifest's `terrain.source`; "Godot Engine" with `Engine.get_license_text()` and
  the components and licences of `Engine.get_copyright_info()` and
  `Engine.get_license_info()`; "Terrain3D 1.0.2" with the text of
  `res://addons/terrain_3d/LICENSE.txt`. Scrollable. While open, the camera ignores its
  controls and the mouse is free. Resume closes it; Quit quits.
- **Tests:** every test of the main scene sets `manifest_path` before adding it, so no
  result depends on what the machine has generated. M0-03's `test_main_scene.gd` (the
  default path) is replaced by the pinned file and your own tests. The refusals' ERROR
  lines match the allowlist's `user://test_` entries; add no entry.
- **Screenshots** (evidence, SPEC §12): run `download terrain` and `terrain` in the
  container, then render the main scene (extend `game/tools/shot.gd` to load `main.tscn`)
  from design's three views (start: the scene's own start view; overview:
  `2625000,1098000,700,215,30`; Kirchplatz: `2623825,1096490,60,200,35`), plus the pause
  screen open and the error panel for a manifest without terrain; commit them as
  `docs/briefs/shots/M1-05-<view>.jpg`.

## Scope — files you may touch

`game/main.tscn` · `game/scripts/main.gd` · `game/scripts/camera/free_fly_camera.gd` ·
`game/scripts/ui/` (new, if the pause screen wants its own scripts) · `game/project.godot`
(the input actions, and display settings if needed; not the version) · `game/tests/` (the
pinned copies, your own tests, `test_main_scene.gd` replaced) · `game/tools/shot.gd` ·
`docs/briefs/shots/M1-05-*.jpg`

## Depends on

M1-03 (a real terrain to look at) and M1-04 (TerrainGrid, TerrainLoader, the shot tool).

## Done when (gates)

- [ ] The two pinned files are in place and unchanged (`cmp`).
      - does NOT prove: that the pinned tests are right (design ran them against a scratch
        camera and main scene, 2026-09-25: all passed).
- [ ] Mutation proofs, each undone with `git apply -R`, each row naming the owner-visible
      harm: (a) the start bearing computed as if local −z were south → the facing test
      fails; (b) no clearance → `test_never_below_the_ground_where_there_is_ground` fails;
      (c) the terrain loaded before the camera exists → an ERROR line (`Cannot find the
      active camera`) fails the gate; (d) the error panel left hidden on a refusal →
      `test_no_terrain_built_opens_the_error_panel_naming_the_command` fails; (e) the version
      also put in the window title → `test_the_version_shows_only_in_the_pause_menu` fails.
      - does NOT prove: how the controls feel (the owner's check).
- [ ] The real village loads in the container: `godot --headless --path game` runs the main
      scene for 300 frames (`--quit-after 300`) with the generated manifest, with no ERROR
      line; record the load time.
      - does NOT prove: that it renders or looks right.
- [ ] Software screenshots committed and named in Findings (evidence, not a gate).
      - does NOT prove: that it renders or looks right in Forward+ on the owner's PC.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`.
      - does NOT prove: that it renders or looks right; that the Windows build starts
        (M1-06, and the owner).

## Forbidden

Physics or collision (walking is M6); the real sun position (M4); textures or surface
colours from data (M3); the version anywhere but the pause screen; changing the version
(M1-06's); changing `config/`, `tests/shared/`, `pipeline/`, TerrainGrid/TerrainLoader's
contract or a pinned copy.

## Findings (executor writes)

Executor session, 2026-09-25. Code commit `29e829f` (no commits came in on the rebase).

1. **For design: mutation (c) as written does not fail the gate; Terrain3D looks for the
   camera at its first physics frame, not on entering the tree.** Measured with a probe
   (a Terrain3D added to a scene, not committed): no camera at all → `ERROR:
   Terrain3D#…:_grab_camera:155: Cannot find the active camera. … Stopping
   _physics_process()`, printed after the first frame, not during `add_child`; the camera
   added in the same frame after the terrain → no ERROR; the camera added one frame
   later → the ERROR. So the order inside `_ready` cannot produce the line; only a camera
   missing at the terrain's first physics frame can. Run c below is the brief's mutation
   (gate exit 0), run c2 the variant that reproduces the harm (gate exit 1, on that ERROR
   line). The scene keeps the order the brief decides (the terrain after the camera is in
   the tree). H11's line "With no camera in the viewport it prints ERROR" holds; its
   timing wants the note.
   - does NOT prove: what Terrain3D does with a camera that becomes current later than
     its first physics frame, beyond the ERROR (it says it stops `_physics_process`).
2. **Pinned copies:** `cmp` of `test_free_fly_camera.gd` and `test_main_scene_terrain.gd`
   against `docs/briefs/pinning/M1-05/game/tests/`: both identical.
3. **The gate on the pushed head** (`tools/gate.sh > gate.log && git commit`): exit 0.
   pytest 362 passed, 3 deselected; GUT 14 scripts, 66 tests, 1616 asserts, all passed.
   65 `ERROR` lines, each excepted by an existing entry (no entry added): 44
   `WorldConfig: user://test_…`, 19 `TerrainGrid: user://test_…`, 2 `WorldConfig: not
   read from a manifest`. Five of them come from the main-scene tests (2 from the pinned
   file, 3 from mine), one per refusal.
4. **Mutation proofs.** Each a full `tools/gate.sh` on the committed tree with one saved
   diff applied, undone with `git apply -R` of that diff; `git status` clean after each.

   | Run | Mutation | Exit, step | Evidence | Owner-visible harm it reproduces |
   |---|---|---|---|---|
   | a | north taken as local +z (`_north = Vector3(0, 0, 1)`), as if −z were south | 1, `gut` | pinned `test_the_camera_starts_above_the_centre_facing_the_matterhorn`: `[-0.5736] expected to equal [0.5736]: bearing 235: south part`; also my sun test (`south part`) | the start view facing north-west instead of the Matterhorn, and the sun from the north |
   | b | `_keep_above_ground` returns at once | 1, `gut` | pinned `test_never_below_the_ground_where_there_is_ground`: `[10.0] expected to equal [51.5]: lifted to 1.5 m above the ground` (and its two other asserts); `test_the_camera_keeps_above_the_ground` | flying through the ground into the space under the terrain |
   | c | the camera out of the tree while the terrain loads, back in the same frame (the brief's mutation) | **0** | no ERROR line: see Findings 1 | — (none: Terrain3D finds the camera at its first physics frame) |
   | c2 | no active camera when the terrain first looks (`clear_current()` before the load, `make_current` 0.1 s later) | 1, `gut` | the gate's `error lines in the output: ERROR: Terrain3D#9410:_grab_camera:155: Cannot find the active camera. … Stopping _physics_process()`; also my `test_the_main_scene_frees_cleanly` and `test_the_camera_is_current_and_sees_far` | a terrain that stops updating its mesh around the camera (Terrain3D stops `_physics_process`) |
   | d | `_error_panel.show()` removed | 1, `gut` | pinned `test_no_terrain_built_opens_the_error_panel_naming_the_command` and `test_a_missing_manifest_…`: `the error panel is open`; also my two refusal tests | an empty sky with no word of what is wrong or what fixes it (Hard Rule 2) |
   | e | `get_window().title = "mattini <version>"` added | 1, `gut` | pinned `test_the_version_shows_only_in_the_pause_menu`: `nor the window title` | the version in the window title, against the owner's choice |

   - does NOT prove: how the controls feel (the owner's check).
5. **The real village loads in the container.** After `download terrain` (6 tiles, 6
   fetches) and `terrain` (`village.f32` `b6334c1f…411a`, SPEC §8's value; 12.8 s for
   both): `godot --headless --path game --quit-after 300` with the generated manifest:
   exit 0 in 7.7 s, no `ERROR` line; its only other output is H4's deprecation
   `WARNING`. **Load time** (a probe timing `add_child` of `main.tscn`, three runs): 5.4,
   3.3 and 4.3 s; Godot's static memory peak 832 MB. The camera starts at local
   (1000.0, 1754.06, −500.0): the grid's centre (x_min 0, z_min −2000, 4001 × 6001 at
   0.5 m), 150 m above the ground there (1604.06), yaw 2.1817 rad (facing 235°), pitch
   −20°.
   - does NOT prove: that it renders or looks right.
6. **Software screenshots** (evidence, not a gate; Compatibility on llvmpipe under Xvfb,
   `tools/shot.sh` with the extended `shot.gd`; 20 s for four views of the village):
   `docs/briefs/shots/M1-05-start.jpg` (the scene's own start view),
   `M1-05-overview.jpg` (`2625000,1098000,700,215,30`), `M1-05-kirchplatz.jpg`
   (`2623825,1096490,60,200,35`), `M1-05-pause.jpg` (the start view with the pause
   screen open: version, controls, the first page of the credits, Resume, Quit) and
   `M1-05-error.jpg` (the village manifest with `terrain` null: the error panel with
   TerrainGrid's refusal and the two commands, the grey-blue sky ground below). The start
   view is design's `M1-look-proposal-start.jpg` view for view. **Exposure:** the mean
   luminance of the lower half (terrain only), measured on the JPEGs: design's proposal
   0.81 (6 % of pixels above 0.9); M1-04's shot 0.86 (42 %, near white); this scene at
   filmic exposure 0.8: 0.745 (2 %); 0.9: 0.81 (12 %); **0.85, kept: 0.78 (7 %)**. Each
   shot run also prints one `ERROR: Condition "status < 0" is true` from ALSA (the
   container has no sound device; the gate's runs are headless and print none).
   - does NOT prove: that it renders or looks right in Forward+ on the owner's PC.
7. **Choices inside the brief's scope** (reversible):
   - **Credits is a RichTextLabel**, not a Label: the brief asks for a scrollable Credits
     directly under PauseMenu (the pinned path `UI/PauseMenu/Credits`), and a Label
     cannot scroll by itself; a ScrollContainer between them would move the path. The
     pinned tests read only its `text`. Version and Controls are Labels.
   - **The error panel shows the refusal itself**, as its reader logged it: main installs a
     `Logger` (`OS.add_logger`, Godot 4.5+) around `WorldConfig.from_manifest` and
     `TerrainGrid.from_manifest` and shows what it caught, then the commands; main logs
     nothing of its own, so each refusal stays one `push_error` (my tests assert exactly
     one). Measured: a `push_error` reaches `_log_error` with its text as `code` and an
     empty `rationale`. Should nothing be caught, the panel says the data at the path was
     refused. The WorldConfig refusal names `… mattini manifest`; every TerrainGrid
     refusal names `download terrain`, then `terrain`.
   - **Controls are generated from the InputMap** (and the camera's own numbers for Shift
     and the wheel), so a rebinding shows. Keys are bound as physical keys; the label shown
     is the keyboard layout's (`DisplayServer.keyboard_get_label_from_physical`), except
     in a headless run, where that call prints `ERROR: Not supported by this display
     server.` (measured), so the US QWERTY name is shown there. On the owner's QWERTZ
     keyboard W A S D Q E sit where the names say.
   - **The sun's direction is measured through WorldConfig** like the start view; with a
     refused manifest it keeps the scene's default orientation (nothing is drawn then).
   - **Camera:** 0.25° of turn per pixel; the diagonal limit is applied to the move in
     world space (so W with E while pitched is not faster either); yaw wrapped to ±180°;
     the mouse is captured exactly while `fly_look` is held (a flag, not the mouse mode,
     which headless cannot hold); one wheel event is one notch (a touchpad's `factor` is
     ignored); the wheel works whenever the controls are on. Opening the pause screen
     turns the controls off and frees the mouse; the SceneTree is not paused (nothing
     moves on its own in M1).
   - **Display:** base size 1280 × 720 with `canvas_items` stretching, aspect `expand`, so
     the UI grows with the window (the owner's screen is not measured); the window opens
     at 1280 × 720.
   - The sky's ground colours (0.40, 0.43, 0.47) and (0.60, 0.63, 0.67); shadows to
     3000 m (as `shot.gd` had); the Terrain node is moved before UI in the child order.
   - **`shot.gd` now renders `main.tscn`** (brief: "extend … to load `main.tscn`"): a view
     is `name,E,N,above,bearing,pitch`, `name` (the camera where it is) or `name,pause`.
     A refused manifest is no longer a failure of the tool: the scene shows its error
     panel, which is what a view then captures; a coordinate view without terrain still
     fails, naming the view. Its bearing is measured through WorldConfig. `tools/shot.sh`
     is unchanged (outside the Scope) and passes the views through as before.
   - My own tests: `game/tests/test_main_scene.gd` (12 tests), replacing M0-03's file.
   - Compile-forced files outside the Scope list, named in the commit: the `.uid` files
     Godot writes for `main.gd`, `free_fly_camera.gd` and the two pinned copies.
8. **Container, at session start** (the prompt asks for such steps to be named): the
   checkout was a shallow clone whose local `main` was an old ref, so `git pull` reported
   7 and 51 diverged commits. Moving `main` to `origin/main` with `git checkout -B` was
   refused by the auto-mode classifier as destructive; `git fetch --unshallow` showed the
   local `main` to be an ancestor of `origin/main`, and `git pull --ff-only` fast-forwarded
   it. Nothing was rewritten or discarded.

