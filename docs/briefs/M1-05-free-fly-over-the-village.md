# Brief: M1-05 — Free-fly over the village
Status: OPEN

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

