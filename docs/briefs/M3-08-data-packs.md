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
- `mattini-photo.pck` is 50'223'260 bytes;
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

## Scope — files you may touch

`tools/export.sh` · `tools/gate_allowlist.txt` (the one entry) · `game/export_presets.cfg`
(both exclude filters) · `game/project.godot` (`[autoload]` only) ·
`game/scripts/data_packs.gd` and its `.uid` (new) · `game/tools/pack.gd` and its `.uid`
(new) · `game/tests/test_data_packs.gd`, `game/tests/test_pack_tool.gd` (pinned, new, with
their `.uid`) · `game/tests/test_release_settings.gd` (pinned, replaces the live file) ·
other new test files under `game/tests/`. Not `main.gd`, not the pipeline, not the docs.

## Depends on

M3-02 (the same lane, landed just before this brief: `export.sh`, `gate.sh`,
`gate_allowlist.txt`). It shares no file with any other wave-1 lane.

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
