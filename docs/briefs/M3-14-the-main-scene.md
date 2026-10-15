# Brief: M3-14 — The main scene: the new data, the sun, the light, the credits
Status: DONE (4f7af57)

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane I of wave 2, after wave 1 has landed and been integrated
(`docs/briefs/M3-plan.md`).

## Goal

The village in M3's look, in the game the owner starts.

- **The data:** `main.gd` reads the photo, the surfaces, the trees and the roof colours and
  hands each to its loader.
- **The light:** the sun stands where it stood when the photo was taken, and the light
  renders the photo at its own brightness.
- **The errors:** a refused block opens the error panel with its fix while everything else
  still shows. In an exported build the fix names the release folder, not pipeline commands.
- **The credits:** they name every dataset, the CC0 textures and the three placeholders.
- **The export:** `tools/export.sh` requires the six blocks and the six startup lines, in
  order.

Measured with design's throwaway on the real village: the exported Linux build starts with
its packs and prints all eight lines in order, with no ERROR line.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 3, 4); `brain.md` H4, H11, H21, H24, H25.
2. `docs/SPEC.md` §10 (M3's game), §8 (the game parts of *The photo*, *Roof colours*, *The
   surfaces*, *The trees*), §11 (Data packs).
3. `game/scripts/main.gd`, `game/main.tscn`, `tools/export.sh`, `game/export_presets.cfg`;
   wave 1's readers and loaders (PhotoGrid, SurfaceGrid, TreeChunks, TreeLoader,
   BuildingRoofs, BuildingLoader, TerrainLoader, DataPacks) and their briefs' Findings.
4. `game/tests/test_main_scene*.gd`, `test_scene_placement.gd`, `complete_world.gd`;
   `pipeline/tests/fake_tools.py`, `test_export_checks.py`.
5. The pinned tests: `docs/briefs/pinning/M3-14/`.

## Decisions already made

1. **Reading and building.** After WorldConfig, `main.gd` reads TerrainGrid, BuildingChunks,
   PhotoGrid, SurfaceGrid, TreeChunks, then BuildingRoofs (only when BuildingChunks accepted
   its block: it needs the chunks), each through `_caught`. Then:
   - `TerrainLoader.create(grid, self, photo, surfaces)` ("Terrain");
   - `TreeLoader.create(trees, self, photo.texture if photo else null, photo.rect() if photo
     else Vector4.ZERO)` ("Trees"): the same texture object as the terrain's, decoded once
     (the village photo is about 600 MiB of texture);
   - `BuildingLoader.create(chunks, self, roofs)` ("Buildings"); each node moved before `UI`.
2. **The error panel.**
   - What cannot be shown: the terrain, the buildings (M2's), `the aerial photo`, `the
     surfaces (roads, paths, water and rock)`, `the trees`, `the roof colours`. The first line
     is `mattini cannot show <A>.`, `<A> and <B>.` (M2's form), or `<A>, <B> and <C>.`
   - A refused manifest shows nothing and names all six.
   - The fixes, in order: PHOTO_FIX download photo, photo; SURFACES_FIX download tlm,
     surfaces; TREES_FIX download surface, download tlm, trees; ROOFS_FIX download photo,
     roofs; each `uv run --project pipeline python -m mattini <cmd>`, in M2's wording.
   - Fallbacks: without the photo, the clay terrain and the trees' placeholder green; without
     the surfaces, the photo without classes; without the trees, no "Trees"; without the roof
     colours, M2's roof material; without the buildings, the roof colours are not read (one
     cause, one panel entry).
   - Without the photo the surfaces are read but not drawn (they are drawn on the photo,
     M3-10), and the panel names only the photo: design accepts this.
   - **An exported build:** `static func error_text(refusals: Array, path: String, exported:
     bool) -> String` builds the panel, and `_show_error` passes `OS.has_feature("template")`.
     Exported, every fix line, the manifest's included, is exactly `To fix it, keep
     mattini.pck and the data packs mattini-*.pck beside the executable: download the
     release folder again and keep its files together.` (`To fix <what>, …` with several),
     with no command. The readers' own refusal lines above it still name their pipeline
     command: design accepts that (the refusal is shown as logged, Hard Rule 2).
3. **The startup lines,** pinned exactly, printed together once everything is built, after
   DataPacks' pack lines, one per block its reader accepted:

   ```
   mattini <v>: terrain <area> loaded, <columns> x <rows> vertices at <spacing> m
   mattini <v>: buildings <area> loaded, <n> buildings in <k> chunks, <t> triangles
   mattini <v>: photo <area> loaded, <columns> x <rows> texels at <cell> m
   mattini <v>: surfaces <area> loaded, <columns> x <rows> cells at <cell> m
   mattini <v>: trees <area> loaded, <trees> trees in <chunks> chunks
   mattini <v>: roofs <area> loaded, <coloured> of <buildings> buildings coloured
   ```
4. **The credits:** "Data", one line per distinct dataset, sorted (the photo and the roofs
   share `swissimage 2023`); "Textures", `game/textures/LICENSE.txt` whole; "Placeholders",
   `BuildingLoader.WALLS_NOTE`, `TreeLoader.TREES_NOTE` and main.gd's `STREAMS_NOTE`
   ("Streams: drawn 2 m wide, an assumed width: swissTLM3D gives none."), always listed (they
   describe the build); then the software licences as M2's.
5. **The light:** the sun at azimuth 183°, elevation 52°, through WorldConfig as today. They
   were measured from the photo's shadows; the flight time (7 September 2023, about 11:30
   UTC) gives 181° and 50° by the solar position formulas, within the shadows' measuring
   error, and the shadows' values are kept. `main.tscn`'s Environment: `tonemap_exposure = 0.54`, `ambient_light_sky_contribution =
   0.25`, everything else M2's (Filmic, `tonemap_mode = 2`, the mode the calibration used).
6. **`tools/export.sh`:**
   - step 2 refuses, before anything is exported, a manifest without any of the six blocks,
     naming its commands in order;
   - step 6 requires every expected line in order (each line's first occurrence after the
     previous one's): a line never printed fails "did not print its startup line", one out
     of order "printed its startup line out of order";
   - a trap measured in design's throwaway: under `set -euo pipefail`, `at="$(grep … | awk
     …)"` for a line never printed ends the script silently at the assignment; add `|| true`
     inside the substitution.
7. **`game/export_presets.cfg`:** both include filters gain `textures/LICENSE.txt`. Measured
   without it: the exported build printed `ERROR: Main: cannot read
   res://textures/LICENSE.txt (File not found)`.
8. **Pinned replacements of other briefs' files,** each needed by a failure design measured
   with M3-14's `main.gd`, each changing only what it must (the allowlist scopes naming them
   stay valid): `game/tests/complete_world.gd` (the test world: a nine-key manifest with all six data
   blocks),
   `test_main_scene_buildings.gd` (M2-05's), `test_scene_placement.gd` (M3-02's),
   `test_release_settings.gd` (M3-08's), `pipeline/tests/fake_tools.py` (M3-02's; it reads
   the version from `game/project.godot`, so the release's bump keeps it green). The test
   world's trees are the trees fixture's chunks under another world's hash: they stand beside
   and below its terrain, labelled test data.
9. **Your own edits to `game/tests/test_main_scene.gd`:** delete
   `test_the_sun_shines_from_azimuth_150_at_35_degrees` (`test_main_scene_light.gd` replaces
   it) and change the not-JSON case's first line to name all six.
10. **The gate:** six lines appended at the end of `tools/gate_allowlist.txt`:

    ```
    PhotoGrid: user://test_ @ res://tests/test_main_scene_refusals.gd # its missing photo is refused on purpose (brief M3-14)
    SurfaceGrid: user://test_ @ res://tests/test_main_scene_refusals.gd # its damaged surfaces are refused on purpose (brief M3-14)
    TreeChunks: user://test_ @ res://tests/test_main_scene_refusals.gd # its missing trees are refused on purpose (brief M3-14)
    BuildingRoofs: user://test_ @ res://tests/test_main_scene_refusals.gd # its missing roof colours are refused on purpose (brief M3-14)
    BuildingChunks: user://test_ @ res://tests/test_main_scene_refusals.gd # its missing buildings are refused on purpose (brief M3-14)
    tests/shared/buildings_fixture/generated/manifest.json: @ res://tests/test_scene_placement.gd # it opens the main scene on the shared buildings fixture, which holds no terrain, photo, surfaces, trees or roofs, on purpose (brief M3-14)
    ```
11. **Measured with design's throwaway** (the real village):
    - the scene builds in 6.8–8.8 s headless (TerrainLoader 3.75 s, PhotoGrid 2.05 s) and in
      11–13 s under Xvfb (Compatibility), peaking at 2.4 GiB with 1'171 MiB of texture
      memory; the exported build peaks at 1'611 MiB;
    - the export: `mattini.pck` 21'267'996 bytes (the textures' 15 MB in it),
      `mattini-terrain.pck` 96'041'728, `mattini-photo.pck` 50'224'444; `mattini.exe` keeps
      198 KB of room; two exports in a row are byte-identical.

## Scope — files you may touch

- `game/scripts/main.gd`, `game/main.tscn` (the Environment's two values),
  `game/export_presets.cfg` (the include filters only), `tools/export.sh` (steps 2 and 6,
  `expected_startup_lines`, its header comment), `tools/gate_allowlist.txt` (the six lines).
- `game/tests/test_main_scene.gd` (decision 9).
- The pinned copies (`cp -r docs/briefs/pinning/M3-14/. .`): new
  `game/tests/test_main_scene_light.gd`, `test_main_scene_data.gd`,
  `test_main_scene_refusals.gd` (with `.uid`), `pipeline/tests/test_export_startup_lines.py`;
  the replacements of decision 8.
- Your own new tests, under new names.

Not the readers, loaders or shaders (wave 1), the pipeline modules (lane H), `tests/shared/`,
`project.godot` (the version is the release's), the docs beyond this brief and its shots.

## Depends on

Wave 1 landed and integrated (M3-02, M3-08 to M3-12). Lane H (M3-13) runs at the same time
and shares no file; its fixture manifests leave every game test green (measured).

## Done when (gates)

- [x] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-14/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [x] Mutations, each failing a named pinned test, recorded:
      - the sun at M2's 150° and 35°, or hard-coded for the owner's axes;
      - exposure 0.85, or the ACES tonemapper;
      - the trees without the photo, or the photo decoded a second time;
      - the startup lines in build order;
      - a dataset listed twice in the credits;
      - a refused manifest naming M2's two;
      - the exported fix ignored;
      - export.sh finding the lines anywhere, or checking M2's two blocks only.
      - does NOT prove: what a GPU draws.
- [x] The real village exported with its packs. It needs lane H's command line and manifest:
      if lane H has landed when your pins pass, rebase on it and run `tools/export.sh` in a
      scratch checkout with the real village built; otherwise say so in Findings, and the
      orchestrator's after-wave-2 step runs it. Either way: eight startup lines in order, no
      ERROR line, every file under 100 MiB.
      - does NOT prove: the Windows build.
- [x] Software screenshots (`tools/shot.sh`, Compatibility) of the start view, 60 m over the
      centre, a street and the river at 30 m, a rock face, a forest edge at 30 m and the
      pause screen, under `docs/briefs/shots/M3-14-*.jpg`, named in Findings. They are
      evidence, not a gate.
      - does NOT prove: the Forward+ look or its colours (H21).
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

A version bump; changing a reader, loader or shader; editing a pinned file or `tests/shared/`;
switching GUT's error tracking off; an allowlist entry beyond the six.

## Findings (executor writes)

1. **Pinned copies.** `cp -r docs/briefs/pinning/M3-14/. .` first; `cmp` of all nine files (the three new GUT scripts, `pipeline/tests/test_export_startup_lines.py` and the five replacements of decision 8) against the pinning folder is identical at the landing commit. The three new scripts passed on the first run against the first implementation (3 of 3, 3 of 3, 7 of 7); GUT writes their `.uid` files at the first import and they are committed with them. My edits to `test_main_scene.gd` are decision 9's two (the 150°/35° sun test deleted, the not-JSON case naming all six) and one comment: its header said "the sun is placed through WorldConfig", a claim the file no longer tests, so it now says test_main_scene_light.gd holds the sun.
2. **Built.** `main.gd`: the six readers in the brief's order, each through `_caught` (BuildingRoofs only when BuildingChunks accepted its block); `TerrainLoader.create(grid, self, photo, surfaces)`, `TreeLoader.create(trees, self, photo.texture, photo.rect())` (the one texture object, asserted `assert_same` by `test_every_loader_receives_its_block`) and `BuildingLoader.create(chunks, self, roofs)`, each node moved before `UI`, in the order Terrain, Trees, Buildings; `_print_startup_lines` prints the six lines together at the end, one per block its reader accepted; `_credited` returns one line per distinct dataset, sorted as text (the lines start with the dataset name, so that is name order); `_credits_text` adds "Textures" (`res://textures/LICENSE.txt` whole, stripped) and "Placeholders" (`BuildingLoader.WALLS_NOTE`, `TreeLoader.TREES_NOTE`, `STREAMS_NOTE`); `static error_text(refusals, path, exported)` builds the panel, with `_names` for "A", "A and B", "A, B and C", and `_show_error` passes `OS.has_feature("template")`. The sun is 183° and 52°; `main.tscn` has `tonemap_exposure = 0.54` and `ambient_light_sky_contribution = 0.25`. `export_presets.cfg`'s two include filters gain `textures/LICENSE.txt`; the six allowlist lines are appended, the 13 earlier ones kept (19 lines).
   `tools/export.sh`: a `BLOCKS` table (name and the commands that build it), `no_block_message`, and `require_blocks`, called by step 2 and by `expected_startup_lines` (so step 6 refuses a missing block with step 2's message, as before); step 6 expects 6 + the packs' lines and finds each line's first occurrence after the previous one's (`|| true` inside the substitution, decision 6's trap); the header comment says so.
3. **Mutations** (each applied to the committed head, its diff saved, the named test run, then undone with `git apply -R`; the harm is what the owner would see):

   | Mutation | Harm | Fails (named test) |
   |---|---|---|
   | sun at M2's 150° and 35° | the shadows point where the photo's do not | `test_main_scene_light.gd`: `test_the_sun_shines_from_azimuth_183_at_52_degrees`, `test_the_sun_is_placed_through_the_world_config` |
   | sun hard-coded for the owner's axes | right on this world, mirrored or turned on any other | `test_the_sun_is_placed_through_the_world_config` (the complete world's test still passes) |
   | exposure 0.85 | ground 3× too bright, roofs clipped to white | `test_the_environment_is_the_calibrated_light` |
   | the ACES tonemapper | another curve than the one calibrated | the same |
   | the sky's share back at 1.0 (own) | blue-cast fill light, the shadows lifted | the same |
   | trees without the photo | every tree the placeholder green | `test_main_scene_data.gd`: `test_every_loader_receives_its_block` |
   | the photo decoded a second time for the trees | about 600 MiB of texture twice | the same (`assert_same`) |
   | the startup lines in build order (trees before buildings) | an export check that reads another order | `test_the_startup_lines_name_every_block_in_order` |
   | a dataset listed twice in the credits | swissimage 2023 shown twice | `test_the_credits_name_every_dataset_texture_and_placeholder` |
   | a refused manifest naming M2's two | four blocks missing, two named | `test_main_scene_refusals.gd`: `test_a_refused_manifest_names_all_six` |
   | the exported fix ignored | a player told to run `uv` commands | `test_in_an_exported_build_every_fix_is_the_release_folder` |
   | export.sh finding the lines anywhere | an export whose lines are in another order passes | `test_export_startup_lines.py::test_a_line_out_of_order_fails[trees-before-surfaces]` |
   | export.sh checking M2's two blocks only | an export without a photo, surfaces, trees or roofs passes | `test_a_manifest_without_a_block_is_refused_before_any_export[photo-commands0]` |

   Each run stopped at its first failing test where it was a pytest run (`-x`); the GUT runs name every failing assert. The logs are not committed.
4. **The real village, and which case held.** Lane H had not landed when my pins passed and I pushed (`4f7af57` was the head of origin/main); it landed while I was measuring (`3ccb38f`), so I rebased onto it and ran the brief's gate with its code. In a scratch `git clone` (H22):
   - `download` terrain, buildings, photo, surface and tlm: verified, 3.2 GB, about two minutes;
   - `terrain` and `buildings` from the command line, then before lane H landed each of photo, roofs, surfaces and trees through a throwaway Python driver (each step checks design's expected values before it writes, and wrote): photo 155 s, roofs 48 s, surfaces 35 s, trees 45 s;
   - a throwaway nine-key manifest (the four descriptions added verbatim to the manifest) gave 324'359 bytes, SHA-256 `3ca0445c9109eec4696d654d1c7536f50220f4db04503fab836412f5b0c01065`, design's value; lane H's own `python -m mattini manifest` then wrote the same bytes, the same SHA-256;
   - the main scene headless on it: the six lines (4001 x 6001 vertices at 0.5 m; 1486 buildings in 6 chunks, 178910 triangles; 10000 x 15000 texels at 0.2 m; surfaces 10000 x 15000 cells at 0.2 m; 34412 trees in 6 chunks; 1486 of 1486 buildings coloured), no ERROR line, 19.7 s with the engine's start and 300 frames, peak 1641 MiB resident;
   - **the unmodified `tools/export.sh`, on lane H's head, exit 0, in 50 s (119 s the first time, which installed the templates):** steps 1 to 6 passed; the started Linux build printed the two pack lines and the six lines, in order, and no ERROR line; sizes: `mattini.pck` 21'280'420, `mattini-terrain.pck` 96'041'728, `mattini-photo.pck` 50'224'444, `mattini.x86_64` 71'075'864, `mattini.exe` 104'659'456 (198 KB under 100 MiB), the largest file; two exports in a row: all ten files byte-identical; the exported build started with a peak of 1613 MiB resident (design: 1'611).
   Not run: the Windows build; an exported build without its packs (the panel in an exported build is read through `error_text`, not started). The plan's "after wave 2" item 1 is therefore met by this run: the orchestrator may repeat it, and need not if this suffices.
5. **Screenshots** (`tools/shot.sh`, Compatibility on llvmpipe under Xvfb, the real village; evidence, not the Forward+ look; 1280 x 720): `docs/briefs/shots/M3-14-start.jpg` (the scene's own start), `M3-14-centre-60m.jpg` (`2624000,1096500,60,235,25`: the church and the river), `M3-14-street-30m.jpg` (`2623957,1096371,30,315,30`), `M3-14-river-30m.jpg` (`2623897,1096371,30,45,30`), `M3-14-rock-face.jpg` (`2623721,1096695,30,265,10`, a 22 m window of rock cells, uphill of the camera), `M3-14-forest-edge-30m.jpg` (`2624261,1096081,30,246,20`), `M3-14-pause.jpg` (the credits: five datasets once each, the textures' note). What I see, not proved: the photo on the ground, a grey road and a dark-teal river with banks, rock with the CC0 texture's grain, conifers on the slopes, the roofs in their measured colours (mostly grey and slate blue) over plaster walls. The conifers read near black in the shadow of the 183° sun; whether that is the photo's own dark crowns or the colour handling is for the owner's Forward+ look (brain.md H21). The ERROR line `ALSA … ERR_CANT_OPEN` in the shot runs' logs is the audio driver finding no sound card under Xvfb, not the game's; the headless runs, which use the dummy driver, print none.
6. **Choices the brief leaves open, said out loud** (all reversible; none touches Hard Rules 3 to 5):
   - `BuildingLoader.roofs_problem` is not called from main. BuildingRoofs already checks, against the same BuildingChunks, the chunk count, every tile and every triangle and vertex sum that `roofs_problem` checks, so a pair that passed both readers cannot make `create` refuse; a branch in main for it could never run and so could not be tested.
   - As decision 2 accepts, without the photo the surfaces are read, so their startup line is printed and swisstlm3d is credited although they are not drawn; likewise the photo is credited and its line printed when only the terrain is refused (the trees draw from it). The lines say "loaded", not "drawn".
   - A refused manifest is one panel entry whose "what" is the six names already joined, so its fix reads "To fix it, run this in the mattini folder:" as before.
7. **The gate.** First run, before the new files were staged: pytest 1966 passed and `test_repo_tracked` failed (the seven new files untracked; stage them, as M3-12's Findings 9 says). Second run, on the landing commit's tree: pytest 1967 passed, 5 deselected; GUT 44 scripts = 44 `test_*.gd` files, 236 tests, 8745 asserts, `GUT version:  9.6.1`, gdlint and gdformat clean (wave 1's was 41, 224 and 8618: the three new scripts add 13 tests, the deleted sun test takes one). After the rebase onto lane H (it brought 24 files, none of mine): exit 0 on the combined head: pytest 2169 passed, 5 deselected (lane H's tests included); GUT unchanged, 44 scripts, 236 tests, 8745 asserts; the real-village run of finding 4 is on that head. Does NOT prove: that anything renders or looks right; what a GPU draws; the Windows build; the owner's PC is the check.
