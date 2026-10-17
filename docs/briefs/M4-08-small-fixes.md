# Brief: M4-08 — The 0.3.0 test's small fixes
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane H of wave 1 (the arc plan names the waves). It answers FB-005,
FB-006, FB-007 and FB-004's jagged edges (`docs/feedback/INBOX.md`).

## Goal

Four things the owner's 0.3.0 test found, each small:

- **The frame cap (FB-007):** the game runs at most 60 frames a second, so the laptop's GPU no
  longer renders flat out at 300 Hz.
- **The log (FB-006):** a release build writes each line to stdout and `godot.log` when it is
  printed, not at exit, so a crash keeps them.
- **The edges (FB-004):** 4× MSAA on 3D.
- **The missing pack (FB-005):** in an exported build, a missing data pack is named, with the
  folder it was looked for in and what it holds; and every reader's message about a missing or
  damaged generated file says to download the release folder again instead of naming the
  pipeline. `tools/export.sh` refuses a release whose packs are not exactly the ones the game
  expects.

Not this brief (M4-10, wave 2): the pause-time cap of 15 fps, and DataPacks' errors on the
error panel (main.gd's).

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 3); `brain.md` H1, H3, H8, H15, H21, H28.
2. `docs/briefs/sketches/m4-design.md` §0 *Frame cap* (the settings, measured), §9 (what
   M4-10 adds on top).
3. `docs/feedback/INBOX.md` FB-004 to FB-007.
4. `docs/briefs/M3-08-data-packs.md` and its pins; `game/scripts/data_packs.gd`,
   `tools/export.sh` (steps 2, 4b, 4c, 6), `pipeline/tests/fake_tools.py`,
   `pipeline/tests/test_export_checks.py`, `pipeline/tests/test_export_startup_lines.py`.
5. The readers' file messages: `game/scripts/terrain/terrain_grid.gd` (`_read_heights`),
   `photo_grid.gd` (`_read_image`, `_make_texture`), `surface_grid.gd` (`_read_image`,
   `_make_texture`), `game/scripts/trees/tree_chunks.gd` (`_read_chunk`),
   `game/scripts/buildings/building_chunks.gd` (`_read_chunk`).
6. The pinned tests: `docs/briefs/pinning/M4-08/`.

## Decisions already made

1. **Three project settings** (`game/project.godot`; m4-design §0, measured):
   - `[application]` `run/max_fps=60`: a CPU sleep, independent of vsync (fps = min(display,
     60));
   - `[application]` `run/flush_stdout_on_print=true` (its default is false; the `.debug`
     variant is already true, so only release exports buffered);
   - a new `[rendering]` section, `anti_aliasing/quality/msaa_3d=2` (`Viewport.MSAA_4X`).
   - The pinned test reads them as the engine took them (`Engine.max_fps`, the root viewport's
     `msaa_3d`), not as text. It does not prove that the cap or MSAA work on the owner's GPU.
   - Nothing else in project.godot changes; this brief owns the file in wave 1.
2. **`ReleaseBuild`** (`game/scripts/world/release_build.gd`, `class_name ReleaseBuild`,
   `extends RefCounted`, static): the one home of "is this an exported build".
   - `static func is_exported() -> bool`: `OS.has_feature("template")`, unless a test has
     called `set_exported_for_tests(true or false)`;
   - `static func set_exported_for_tests(exported: Variant) -> void`: null gives the question
     back to the OS (a static var; the tests reset it after each);
   - `static func file_hint(command: String) -> String`: outside an export
     `"; <command> rebuilds it"`, as before; in an export
     `"; it ships in the release's packs: download the release folder again"`.
   - The wording, decided by design: the photo and the terrain's heights ship in the data
     packs, the buildings, surfaces and trees in `mattini.pck`; "the release's packs" is true of
     all of them ("the data packs" would not be).
3. **Every file message goes through `file_hint`.** The seven sites that build `"; %s rebuilds
   it"` today: TerrainGrid `_read_heights`; PhotoGrid `_read_image` and `_make_texture`;
   SurfaceGrid `_read_image` and `_make_texture`; TreeChunks `_read_chunk`; BuildingChunks
   `_read_chunk`. Each becomes `var rebuild := ReleaseBuild.file_hint(<COMMAND>)`; nothing
   else in the messages changes.
   - BuildingRoofs reads no file of its own (its block is in the manifest): no site.
   - The "not built" and "another world" refusals keep naming the pipeline: a release ships a
     manifest whose blocks are built for its world (tools/export.sh steps 1 and 2).
   - SurroundingsGrid (M4-07, same wave) keeps the pipeline's hint; the pinned census names it
     as its one exception until M4-10.
4. **DataPacks** (`game/scripts/data_packs.gd`):
   - `const EXPECTED_PACKS := ["mattini-photo.pck", "mattini-terrain.pck"]`, on one line
     (tools/export.sh reads it with a regular expression);
   - what each holds: mattini-photo.pck "the aerial photo", mattini-terrain.pck "the terrain's
     heights";
   - `static func missing_pack_errors(dir: String) -> PackedStringArray`: one message per
     expected pack that is not a file in `dir`, in EXPECTED_PACKS' order:
     `"DataPacks: the data pack <name> (<what it holds>) is missing from <dir>: download the
     release folder again"`;
   - `_init()`: in an exported build (`ReleaseBuild.is_exported()`), after loading the packs as
     today, one `push_error` per message. Outside one it does nothing, as today.
   - M4-10 shows them on the error panel; `missing_pack_errors` is its way to get them.
5. **tools/export.sh:**
   - **step 2b**, after step 2 and before anything is exported: it reads EXPECTED_PACKS from
     `game/scripts/data_packs.gd` and refuses, naming that file, both lists and "nothing was
     exported", unless it is exactly `mattini-<folder>.pck` for PACKED_FOLDERS, in order. A
     data_packs.gd without the one-line constant is refused there too. It prints "the game
     expects mattini-photo.pck mattini-terrain.pck, as written here";
   - **after step 4b**: it refuses, naming the packs written and the packs expected, unless
     the packs written are exactly EXPECTED_PACKS; the build is not started then;
   - its header comment describes both.
6. **The stand-ins** (design's full replacements, pinned): `pipeline/tests/fake_tools.py`'s
   export tree holds `game/scripts/data_packs.gd` and both packed folders, its stand-in Godot
   runs the pack tool, and its startup lines begin with the two pack lines;
   `pipeline/tests/test_export_startup_lines.py`'s `_tree` no longer makes the folders. The
   gate's other export and gate tests run unchanged on them.
7. **The pinned tests that already name reader messages need no change:** they run outside
   an export, where `file_hint` gives the old text. Checked in design's rehearsal (all green):
   `test_terrain_grid.gd`, `test_photo_grid.gd`, `test_surface_grid.gd`, `test_tree_chunks.gd`,
   `test_m3_11_tree_chunks_checks.gd`, `test_building_chunks.gd`, `test_main_scene.gd`,
   `test_main_scene_terrain.gd`, `test_main_scene_buildings.gd`, `test_main_scene_refusals.gd`,
   `test_m3_r1_fix5_type_guards.gd`, and `test_data_packs.gd` (whose "nothing logged" test calls
   `load_from`, not the new check).
8. **No allowlist line:** the pinned tests call the readers' `_read` (which returns the problem
   without a push_error) and `missing_pack_errors` (which pushes none), so they print no ERROR
   line. `tools/gate_allowlist.txt` is M4-07's in wave 1.

## Scope — files you may touch

- `game/project.godot` (the three settings);
- `game/scripts/world/release_build.gd` and its `.uid` (new);
- `game/scripts/data_packs.gd`;
- the five readers' hint lines only: `game/scripts/terrain/terrain_grid.gd`, `photo_grid.gd`,
  `surface_grid.gd`, `game/scripts/trees/tree_chunks.gd`,
  `game/scripts/buildings/building_chunks.gd`;
- `tools/export.sh`;
- `game/tests/`: the pinned `test_m4_08_project_settings.gd`, `test_m4_08_release_hints.gd`,
  `test_m4_08_data_packs_expected.gd` (new, with `.uid`), your own new `test_m4_08_*.gd`;
- `pipeline/tests/`: the pinned `test_m4_08_export_packs.py` (new), `fake_tools.py` and
  `test_export_startup_lines.py` (pinned replacements), your own new `test_m4_08_*.py`.

Not `main.gd`, `main.tscn`, `terrain_loader.gd`, `terrain_photo.gdshader`, any sky file,
`tools/gate_allowlist.txt`, `surroundings_grid.gd` or anything else of M4-07's.

## Depends on

None. M4-07 runs beside it and shares no file; the census in
`test_m4_08_release_hints.gd` names M4-07's reader as its exception, whichever lands first.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M4-08/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded with the harm each reproduces.
      Design's throwaway failed the named tests:
      - PhotoGrid's `_make_texture`, SurfaceGrid's `_make_texture` or TreeChunks' site left on
        the old literal: `test_photo_that_decodes_to_another_size`,
        `test_surfaces_that_decode_to_other_classes`, `test_tree_chunk_missing`, each with the
        census `test_no_script_spells_the_pipeline_hint_itself`;
      - `file_hint` ignoring the export, the seam ignoring the test's setting, or the export
        hint naming the pipeline too: the seam test and all seven reader tests;
      - EXPECTED_PACKS without the terrain, a message without the folder, the contents swapped,
        any file in the folder counted as the pack: `test_m4_08_data_packs_expected.gd` (two or
        three tests each);
      - no cap, a cap of 30, no flush, 2× MSAA, the MSAA key misspelt:
        `test_m4_08_project_settings.gd`, one test each;
      - export.sh without step 2b: `test_m4_08_export_packs.py`
        `test_another_expectation_is_refused_before_any_export` (3 cases) and
        `test_another_packed_folder_list_is_refused_before_any_export`; without the check after
        4b: `test_a_pack_not_written_fails_before_the_build_starts`; reading EXPECTED_PACKS as a
        set: its `another-order` case.
      - does NOT prove: the look of anything; that the owner's GPU load drops or the edges
        smooth (the owner's PC).
- [ ] The export run: `tools/export.sh > export.log` exit 0 on a real village build in a
      scratch clone (H22), with "the game expects mattini-photo.pck mattini-terrain.pck" in its
      log; then start `build/linux/mattini.x86_64 --headless --quit-after 300` (user:// in a
      scratch folder) with `mattini-photo.pck` moved aside and record the ERROR line naming
      `mattini-photo.pck`, its folder and "the aerial photo", and PhotoGrid's line ending
      "download the release folder again"; restore the pack. If the container cannot build
      the village (no swisstopo data), say so in Findings and name the run as the
      orchestrator's integration step.
      - does NOT prove: what the player sees (the error panel is M4-10's); that the Windows
        build does the same (the owner's PC).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the frame cap, the flush or MSAA behave on the owner's machine;
        the render step's numbers under MSAA are Compatibility's on llvmpipe, not the look.

## Forbidden

A pause-time cap or any change to main.gd (M4-10); a version bump; vsync or renderer
changes; another MSAA level, FXAA, TAA or screen-space AA; changing any reader's other
messages; an allowlist entry; editing a pinned file.

## Findings (executor writes)
