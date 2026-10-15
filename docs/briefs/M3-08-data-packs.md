# Brief: M3-08 — Data packs: the large generated folders ship beside the executable
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane B of wave 1, after M3-02 (`docs/briefs/M3-plan.md`).

## Goal

The export stays under GitHub's 100 MiB per file once the 0.2 m photo (about 50 MB) joins
the 96 MB heights (the owner chose packs over Git LFS, SPEC §13 row 32).

- `tools/export.sh` writes the generated folders `terrain/` and `photo/` into
  `mattini-terrain.pck` and `mattini-photo.pck`, beside each executable.
- The export presets keep those folders, and every `*.part`, out of `mattini.pck`.
- An autoload, `DataPacks`, loads every `mattini-*.pck` beside the executable of an
  exported build, before the main scene reads the manifest.
- A new export step checks that every generated file ships exactly once and unchanged.
- The exported Linux build starts with its packs and prints one line per pack, then its
  startup lines.

## Read first, in order

1. `CLAUDE.md`; `brain.md` H1, H2, H15, H21, H24.
2. `docs/SPEC.md` §11 (delivery), §13 row 32; `docs/RELEASE.md` §C.
3. `tools/export.sh`, `game/export_presets.cfg`, `game/project.godot`,
   `game/tests/test_release_settings.gd`, `tools/gate.sh`, `tools/gate_allowlist.txt`, as
   M3-02 left them (the same lane, just before this brief).
4. Godot 4.6's `PCKPacker` and `ProjectSettings.load_resource_pack` (class reference).
5. The pinned files: `docs/briefs/pinning/M3-08/`.

## Decisions already made

Every rule below was measured end to end by design's agent on the real village
(2026-10-14):
- `mattini.pck` shrank from 99'405'400 to 3'365'376 bytes;
- `mattini-terrain.pck` is 96'041'728 bytes, 8.41 MiB under the limit;
- `mattini-photo.pck` is about 50.2 MB (50'223'260 bytes here; 50'224'444 in design's later
  rehearsal with the final photo description);
- two exports gave byte-identical files;
- the Linux build started with its packs in 4.6 s at 875 MiB, the same as without.

1. **Which files, which pack.**
   - Every file in `game/assets/generated/photo/` goes into `mattini-photo.pck`.
   - Every file in `game/assets/generated/terrain/` goes into `mattini-terrain.pck`.
   - Each file keeps its own `res://` path. Names that start with `.`, end with `.part` or
     end with `.import` are left out.
   - The packed folders are this fixed list, not a size rule, because the presets are a
     static file.
   - A packed folder that does not exist gets no pack, and export.sh says so:
     `no game/assets/generated/photo: no mattini-photo.pck`.
   - Everything else under `assets/generated/` stays in `mattini.pck`.
2. **Names:** `mattini-<folder>.pck`, never renamed per version (D15).
3. **The pack tool:** `game/tools/pack.gd` (with its `.uid`), `extends SceneTree`, excluded
   from exports by `tools/*`.
   - **Command line:** `"$GODOT" --headless --path game -s res://tools/pack.gd -- <pack
     path> res://assets/generated/<folder>`, with `user://` in export.sh's scratch folder and
     under `timeout`.
   - **Static API, pinned:** `write_pack(pack_path: String, source_dir: String, target_dir:
     String) -> String`. It returns `""` once written, else what is wrong.
     - It packs every file directly in `source_dir` (`DirAccess.get_files_at`, which leaves
       out hidden files), minus `.part` and `.import` names.
     - The names are sorted with `PackedStringArray.sort()`, in code-point order.
     - Each is added as `target_dir/<name>`, through `PCKPacker.pck_start(pack_path +
       ".part")` at its defaults (alignment 32, no key), then `flush()`, then renamed to
       `pack_path`.
     - Refused, writing no pack: a `source_dir` that does not exist, holds a folder, or holds
       nothing to pack.
   - **Output:** `pack: wrote <pack path>, <n> files of <folder>` and exit 0; on failure,
     `pack: <problem>` on stderr and exit 1; exit 2 on a wrong command line.
4. **The autoload:** `DataPacks="*res://scripts/data_packs.gd"` in `project.godot`'s
   `[autoload]`, `extends Node`.
   - It has no `class_name`. Measured: `Class "DataPacks" hides an autoload singleton.` is
     a parse error.
   - **Pinned:** `static func load_from(dir: String) -> PackedStringArray`.
     - A `dir` that does not exist: nothing loaded, no log, no error.
     - Otherwise, every file whose name `match`es `mattini-*.pck`, in `sort()` order, each
       with `ProjectSettings.load_resource_pack(path, false)`. A pack therefore never
       replaces a file already loaded.
     - Each pack loaded prints **`mattini <version>: data pack <name> loaded`** (the version
       is `application/config/version`) and adds its name to the result.
     - A pack that does not load gets **`push_error("DataPacks: cannot load the data pack
       <path>")`**, and the next one still loads.
   - `_init()`: when `OS.has_feature("template")`, it calls
     `load_from(OS.get_executable_path().get_base_dir())`. When that loads nothing, it prints
     `mattini <version>: no data pack (mattini-*.pck) in <folder>`.
5. **The presets**, both, exactly: `exclude_filter="tests/*, addons/gut/*, tools/*, *.part,
   assets/generated/photo/*, assets/generated/terrain/*"`; `include_filter` unchanged. This
   is also the export half of M2's V1-P-06.
6. **`tools/export.sh`.** Both steps build on M3-02's version (Linux checked first, CR
   stripped in `clean_output`): `PACKED_FOLDERS=(photo terrain)`, and in step 4, after both
   exports:
   - **4b, the data packs.** For each packed folder that exists, the tool writes its pack
     into `build/linux/`. The tool's output is cleaned and scanned for ERROR lines, and its
     exit status and the file are checked. The pack is then copied beside the other
     executable, through a `.part` and a rename.
   - **4c, every generated file ships once, as it is.** The step reads the directory of
     `mattini.pck` and of every `mattini-*.pck` in each build folder (Godot 4.6.3's pack
     format, as design's agent read it in `core/io/pck_packer.cpp` and
     `editor_export_platform.cpp` at 4.6.3-stable; little-endian: the magic `GDPC`, format 3,
     4, 6, 3, flags (2 = relative file base), the file base as a u64 at byte 24, the directory
     offset as a u64 at byte 32, 16 reserved u32; the first file at 128, each file padded to
     32; the directory: a u32 count, then per file a u32 path length (padded to 4), the path
     without `res://`, a u64 offset from the file base, a u64 size, a 16-byte MD5, u32 flags).
     Inline Python through `uv run --project pipeline --frozen python -c`, as step 6 does. It fails, listing every problem, unless:
     - each file under `game/assets/generated/` (but `.`-names, `*.part`, `*.import`) is in
       exactly one pack of that folder, the right one, with its size and MD5;
     - no pack holds a generated path that is not such a file;
     - no data pack holds anything outside `assets/generated/`;
     - and no generated file of 10 MiB (10'485'760 bytes) or more stays in `mattini.pck`.

     The messages name the folder, the file and the packs, for example:
     - `build/linux: terrain/village.f32 is in mattini-terrain.pck, mattini.pck, not in
       mattini-terrain.pck alone`;
     - `game/assets/generated/buildings/big.bin is 12582912 bytes, 10485760 or more,
       outside the packed folders (photo terrain)`.
   - **Step 5** is unchanged and now lists the packs.
   - **Step 6** expects first one line per pack 4b wrote, in name order, then the terrain and
     buildings lines. M3-14 adds its own lines after them.
7. **An exported build without its packs** shows the readers' own refusal, unchanged: for
   the terrain, TerrainGrid's "the heights file … is missing" in the error panel. Its fix
   lines are for the source code, not a player; M3-14 changes them (it owns `main.gd`).
8. **The gate:** one scoped allowlist entry, the only new ERROR line:
   `DataPacks: cannot load the data pack @ res://tests/test_data_packs.gd # its broken pack is refused on purpose (brief M3-08)`.
   Wave 1's one shared file (the plan): append the line at the end; a rebase that brings
   other lanes' lines keeps every line, re-runs the gate and records it.

## Scope — files you may touch

`tools/export.sh` · `tools/gate_allowlist.txt` (the one entry) · `game/export_presets.cfg`
(both exclude filters) · `game/project.godot` (`[autoload]` only) ·
`game/scripts/data_packs.gd` and its `.uid` (new) · `game/tools/pack.gd` and its `.uid`
(new) · `game/tests/test_data_packs.gd`, `game/tests/test_pack_tool.gd` (pinned, new, with
their `.uid`) · `game/tests/test_release_settings.gd` (pinned, replaces the live file) ·
other new test files under `game/tests/`. Not `main.gd`, not the pipeline, not the docs.

## Depends on

M3-02 (the same lane, landed just before this brief: `export.sh`, `gate.sh`). Keep its
pinned tools tests green: `test_export_checks.py` runs the real `export.sh` with stand-ins,
and its stand-in export writes real packs for step 4c (measured with design's throwaway of
this brief: 7 passed). It shares no file with any other wave-1 lane but the allowlist's
appended lines.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M3-08/. .`) and stay
      byte-identical to `docs/briefs/pinning/M3-08/` (`cmp`, before every commit).
      - does NOT prove: that they are the right tests.
- [ ] `tools/export.sh` passes on a real village build (terrain and buildings from a scratch
      download in a scratch checkout; the templates may be downloaded, 1.26 GB) with
      `mattini-terrain.pck`. It passes again with a stand-in photo folder holding a 50 MB
      `game/assets/generated/photo/standin.bin` (random bytes, never a `.jpg` without its keep
      `.import`), giving two packs; then the stand-in is deleted. `sha256sum build/*/*` is
      identical over two runs. The Linux build, started as step 6 starts it without
      `mattini-terrain.pck`, prints TerrainGrid's refusal as an ERROR line, on which step 6
      fails. Record all of it in Findings.
      - does NOT prove: that the Windows build finds its packs (no Windows here; the
        owner's PC).
- [ ] Four mutations of step 4c each fail it with its message, recorded:
      - the presets without `assets/generated/terrain/*`;
      - a `.part` in `buildings/` with the presets without `*.part`;
      - a PNG without a keep `.import` in a folder that is not packed;
      - a 12 MiB file in `buildings/`.
      - does NOT prove: that no other way to ship a wrong file exists.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that anything renders or looks right.

## Forbidden

- A version bump; changing `main.gd`; compressing or encrypting a pack; Git LFS.
- Renaming files per version; switching GUT's error tracking off.
- Editing a pinned file.

## Findings (executor writes)

Lane builder B (the same wave-1 builder session as M3-02, which landed first as `d67e17e`),
2026-10-15, on `main`. Nothing outside the Scope was touched.

1. **Pinned copies.** `test_data_packs.gd`, `test_pack_tool.gd` and `test_release_settings.gd`
   copied from `docs/briefs/pinning/M3-08/` one file at a time; `cmp` identical before the
   gate and before the commit. Before the work: `test_data_packs.gd` 0 of 4 passing,
   `test_pack_tool.gd` 0 of 4, `test_release_settings.gd` 2 of 4. After: 4/4, 4/4, 4/4.
2. **Standard gate** (`tools/gate.sh > gate.log && git commit`), exit 0, on the tree with
   everything that had landed on `main` by then (`2fa05c0`):
   pytest **1041 passed**, 4 deselected; GUT **39 scripts, 201 tests, 201 passing, 8350 asserts**,
   `GUT version:  9.6.1`, `Scripts 39` equal to the 39 `test_*.gd` files; gdlint clean; gdformat
   54 files unchanged; 108 `ERROR` lines in the log, all excepted. The new allowlist line is
   the brief's, appended once at the end; the lines the other lanes appended are all still there.
3. **What was built.**
   - `game/tools/pack.gd` (+ `.uid`): `write_pack(pack_path, source_dir, target_dir) -> String`
     as pinned (sorted `DirAccess.get_files_at`, minus `.part` and `.import`; `PCKPacker` at its
     defaults; `<pack path>.part`, then a rename; a `source_dir` that does not exist, holds a
     folder or holds nothing to pack is refused, naming it, and the `.part` is removed after a
     failed write). Extra: a public `packed_names(source_dir)` the command line uses to count
     the files. Command line `-- <pack path> res://assets/generated/<folder>`: the folder is
     both source and target, so each file keeps its own `res://` path (decision 1); exit 0
     prints `pack: wrote <pack path>, <n> files of res://assets/generated/<folder>` (the
     brief's `<folder>` is read as the `res://` folder), exit 1 prints `pack: <problem>` on
     stderr, exit 2 on anything but two arguments with a `res://assets/generated/` second one.
   - `game/scripts/data_packs.gd` (+ `.uid`, no `class_name`) and `[autoload]
     DataPacks="*res://scripts/data_packs.gd"` in `project.godot` (a new section, between
     `[application]` and `[display]`): `load_from(dir)` as pinned, `_init()` in an exported
     build, with the `no data pack (mattini-*.pck) in <folder>` line when none loads.
   - Both presets' `exclude_filter` exactly as the brief (the pinned
     `test_release_settings.gd` reads which generated files each filter keeps).
   - `tools/gate_allowlist.txt`: `DataPacks: cannot load the data pack @
     res://tests/test_data_packs.gd # …`, the only new ERROR line (the broken pack's
     `push_error`; Godot prints no ERROR line of its own for it, measured in the test's log).
   - `tools/export.sh`: `PACKED_FOLDERS=(photo terrain)`, step **4b** (the tool per existing
     folder into `build/linux/`, its output cleaned and scanned for ERROR lines, exit status
     and the file checked, then copied beside the Windows executable through a `.part` and a
     rename; a missing folder prints `no game/assets/generated/<folder>: no mattini-<folder>.pck`),
     step **4c** (Python through `uv run … python -c`, as step 6's; messages as the brief's
     examples) and step **6** (one `data pack` line per pack 4b wrote, then the terrain and
     buildings lines). My reading where the brief is silent: step 6 also checks that its lines
     appear in the order listed, not only that each appears ("in name order, then…"); 4c
     requires a pack's header to say format 3, Godot 4.6.3 and flags 2, fails on a path twice
     in one pack or an entry past the file's end, and takes a `res://` prefix on a path as
     absent; the data-pack timeout is `PACK_TIMEOUT_S=300`.
4. **The real village, in a scratch `git clone`** (so no copied venv, H22). `download terrain`
   (6 tiles) and `download buildings` (6 sheets) verified; `terrain` and `buildings` exit 0, the
   steps' own comparisons with `config/terrain.json` and `config/buildings.json` passed (the
   6 chunks have the SHA-256s `config/buildings.json` expects; `village.f32` 96'040'004 bytes).
   The Godot export templates were downloaded by `export.sh` itself (1'255'918'323 bytes, the
   pinned SHA-256 matched).
   - **`tools/export.sh`, exit 0, 75 s with the template download:** 4b: `no
     game/assets/generated/photo: no mattini-photo.pck`, `pack: wrote …/mattini-terrain.pck, 2
     files …`; 4c: `checked build/linux build/windows: every generated file is in its pack,
     with its size and MD5`; sizes: `mattini-terrain.pck` **96'041'728** (design's number),
     `mattini.pck` 3'419'044 (design measured 3'365'376 on an earlier tree: the tree now holds
     M3-09 to M3-12's code), `mattini.x86_64` 71'075'864, `mattini.exe` 104'659'456 (99.81 MiB);
     step 6 started the Linux build with `data pack mattini-terrain.pck loaded`, then the
     terrain and buildings lines (`1486 buildings in 6 chunks, 178910 triangles`), no ERROR.
   - **With a stand-in photo folder** (`game/assets/generated/photo/standin.bin`, 52'428'800
     random bytes, no image): two packs, `mattini-photo.pck` 52'429'008 bytes, step 6 printed
     both pack lines in name order; the stand-in was then deleted. `sha256sum build/*/*` over
     the second and third exports: **identical** for all nine files, `mattini.pck` included.
     The first export of the fresh checkout (the one that also imported the project) wrote
     another `mattini.pck`, same size, other bytes, so H15's "not byte-reproducible" is
     about the first export from an unimported tree here, not between two later runs; I did
     not isolate why.
   - **The seam M3-04 will make** (a `photo/village.jpg` with its keep `.import`, and a json;
     3'000'000 random bytes, standing in): the whole export passes; `mattini-photo.pck` holds
     `photo/village.jpg` (3'000'000) and `photo/village.json` and no `.import`.
   - **Without `mattini-terrain.pck`**, the Linux build (copied alone, started as step 6
     starts it) exits 0 and prints `mattini 0.2.0: no data pack (mattini-*.pck) in <folder>`,
     then, as an ERROR line, `ERROR: TerrainGrid: res://assets/generated/manifest.json: the
     heights file res://assets/generated/terrain/village.f32 is missing; python -m mattini
     terrain rebuilds it` (its fix line is for the source tree, brief decision 7). Step 6
     failed on it in a scratch copy of `export.sh` with `PACKED_FOLDERS=(photo)` and 4c made
     non-fatal: `export: the Linux build printed error lines:` and that line. The same copy
     with 4c on stops there: `terrain/village.f32 is in no pack, not in mattini.pck alone`
     (and `game/assets/generated/terrain/village.f32 is 96040004 bytes, 10485760 or more,
     outside the packed folders (photo)`).
5. **The four mutations of 4c**, real exports in the scratch clone, each restored after (the
   presets by a saved copy, the files by removing them):
   - presets without `assets/generated/terrain/*`: `build/linux: terrain/village.f32 is in
     mattini-terrain.pck, mattini.pck, not in mattini-terrain.pck alone` (and
     `village.json`, and for `build/windows`), exit 1 at 4c. Harm: `mattini.pck` grows past
     GitHub's limit and the heights ship twice.
   - a `buildings/2623-1096.bin.part` with the presets without `*.part`: `build/linux:
     mattini.pck holds assets/generated/buildings/2623-1096.bin.part, which is not a
     generated file that ships` (and windows). Harm: a step's half-written file ships.
   - a PNG without a keep `.import` in `buildings/` (not packed): `build/linux:
     buildings/probe.png is in no pack, not in mattini.pck alone`, and `mattini.pck holds
     assets/generated/buildings/probe.png.import, which is not a generated file that ships`
     (the export ships the imported texture and the `.import`, H24). Harm: a game that cannot
     read the file it expects.
   - a 12 MiB `buildings/big.bin`: `game/assets/generated/buildings/big.bin is 12582912
     bytes, 10485760 or more, outside the packed folders (photo terrain)`. Harm: a large file
     that silently grows `mattini.pck`.
   `manifest` (step 1) accepted all four extra files; none stopped the run before 4c.
6. **Not proved, said aloud.**
   - The Windows build finding its packs (no Windows here): `DataPacks` reads
     `OS.get_executable_path().get_base_dir()`, the same call on both systems.
   - That the pack tool and 4c cover a **photo** of real size: the photo exists only as the
     stand-ins above (the step lands in M3-04).
   - `pipeline/tests/` is outside this brief's Scope, so 4b and 4c have no pytest of their own
     with stand-ins; I ran one ad hoc harness (not committed) on the pinned `fake_tools.py`:
     a tree with all three kinds of folders passed; an extra 12 MiB file, a pack line missing
     from the started build's output and the pack lines out of order each failed with their
     message. A committed one is a candidate for M3-14 (it owns `fake_tools.py`) or the review.
   - 4c reads each pack's directory, so it proves what Godot wrote about the files, not that
     the bytes read back from the pack at run time are the same (the started build reading
     the heights is that check for the terrain, step 6's line).
   - The brief's gate wording "sha256sum build/*/* is identical over two runs" held for the
     second and third exports, not for the first (above).
