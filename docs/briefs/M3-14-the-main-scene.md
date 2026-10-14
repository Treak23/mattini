# Brief: M3-14 — The main scene: the new data, the sun, the light, the credits
Status: OPEN

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
5. **The light:** the sun at azimuth 183°, elevation 52°, through WorldConfig as today;
   `main.tscn`'s Environment `tonemap_exposure = 0.54`, `ambient_light_sky_contribution =
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
   stay valid): `game/tests/complete_world.gd` (the test world with all nine blocks),
   `test_main_scene_buildings.gd` (M2-05's), `test_scene_placement.gd` (M3-02's),
   `test_release_settings.gd` (M3-08's), `pipeline/tests/fake_tools.py` (M3-02's). The test
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
`project.godot` (the version is the release's), the docs.

## Depends on

Wave 1 landed and integrated (M3-02, M3-08 to M3-12). Lane H (M3-13) runs at the same time
and shares no file; its fixture manifests leave every game test green (measured).

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-14/. .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each failing a named pinned test, recorded:
      - the sun at M2's 150° and 35°, or hard-coded for the owner's axes;
      - exposure 0.85, or the ACES tonemapper;
      - the trees without the photo, or the photo decoded a second time;
      - the startup lines in build order;
      - a dataset listed twice in the credits;
      - a refused manifest naming M2's two;
      - the exported fix ignored;
      - export.sh finding the lines anywhere, or checking M2's two blocks only.
      - does NOT prove: what a GPU draws.
- [ ] The real village exported with its packs. It needs lane H's command line and manifest:
      if lane H has landed when your pins pass, rebase on it and run `tools/export.sh` in a
      scratch checkout with the real village built; otherwise say so in Findings, and the
      orchestrator's after-wave-2 step runs it. Either way: eight startup lines in order, no
      ERROR line, every file under 100 MiB.
      - does NOT prove: the Windows build.
- [ ] Software screenshots (`tools/shot.sh`, Compatibility) of the start view, 60 m over the
      centre, a street and the river at 30 m, a rock face, a forest edge at 30 m and the
      pause screen, under `docs/briefs/shots/M3-14-*.jpg`, named in Findings. They are
      evidence, not a gate.
      - does NOT prove: the Forward+ look or its colours (H21).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that it renders or looks right.

## Forbidden

A version bump; changing a reader, loader or shader; editing a pinned file or `tests/shared/`;
switching GUT's error tracking off; an allowlist entry beyond the six.

## Findings (executor writes)
