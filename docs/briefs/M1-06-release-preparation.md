# Brief: M1-06 — Release preparation for 0.1.0
Status: DONE (5c421ca)

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

The first version can be shipped by running one script: the project says 0.1.0, and
`tools/export.sh` regenerates the manifest, installs Godot 4.6.3's export templates from the
official mirror (checksum-pinned), exports Linux and Windows x86_64 builds of the current
tree into `build/`, and measures every file against GitHub's 100 MB limit. The Linux export
is proved to start and load the village headless. The M1 close then only walks
`docs/RELEASE.md` and ships.

## Read first, in order

1. `docs/RELEASE.md` (all of it: §A credits, §C delivery and the 100 MB rule).
2. `docs/SPEC.md` §11 (delivery, the version, the export), §9, §4.
3. `.claude/hooks/session-start.sh`: how Godot itself is fetched from the mirror with a
   pinned checksum (the pattern for the templates).
4. The pinning tests: `docs/briefs/pinning/M1-06/game/tests/test_release_settings.gd` and
   `docs/briefs/pinning/M1-06/pipeline/tests/test_release_hygiene.py`.
5. M1-05's Findings (the main scene, the load time).

## Decisions already made

- **Version** 0.1.0 in `game/project.godot` (`application/config/version`); the scheme was
  confirmed by the owner (SPEC §13 row 16). M0-03's `test_project_settings.gd` follows.
- **Presets** (`game/export_presets.cfg`), exactly what the pinned test reads: `Linux`
  (platform `Linux`, `../build/linux/mattini.x86_64`) and `Windows Desktop` (platform
  `Windows Desktop`, `../build/windows/mattini.exe`); both x86_64, `.pck` beside the
  executable (`binary_format/embed_pck=false`), `export_filter="all_resources"`,
  `include_filter` with `assets/generated/*` and `addons/terrain_3d/LICENSE.txt`,
  `exclude_filter` with `tests/*` and `addons/gut/*`; the Windows preset with
  `application/modify_resources=false` (rcedit is not available).
- **`build/`** is git-ignored (`.gitignore`).
- **`tools/export.sh`**, exit status non-zero on any failure, in order:
  1. refuse unless `game/assets/generated/manifest.json` has a `terrain` block, naming
     `download terrain` and `terrain`;
  2. `uv run --project pipeline --frozen python -m mattini manifest` (re-checks the
     generated data against the config);
  3. install Godot 4.6.3-stable's export templates into Godot's templates folder when they
     are missing, from `downloads.godotengine.org` (the mirror the hook uses; github.com
     release downloads are refused in containers, H6), verified against a SHA-256 pinned in
     the script: measure it the way the hook's Godot checksum was measured, and say how in
     Findings;
  4. `godot --headless --path game --export-release "<preset>" <path>` for both presets;
  5. list every file in `build/` with its size; fail naming any file over 100 MiB
     (104'857'600 bytes; `docs/RELEASE.md` §C).
- **A startup line:** `main.gd` prints one line when the terrain has loaded,
  `mattini <version>: terrain <area> loaded, <columns> x <rows> vertices at <spacing> m`,
  so an exported build can be checked headless.

## Scope — files you may touch

`game/project.godot` (the version only) · `game/export_presets.cfg` (new) ·
`tools/export.sh` (new) · `.gitignore` (`/build/`) · `game/scripts/main.gd` (the startup
line only) · `game/tests/` (the pinned copy; `test_project_settings.gd`'s version) ·
`pipeline/tests/test_release_hygiene.py` (the pinned copy)

## Depends on

M1-05.

## Done when (gates)

- [ ] The two pinned files are in place and unchanged (`cmp`).
      - does NOT prove: that the presets export anything (next gate).
- [ ] One real export in the container, recorded in Findings: `download terrain`,
      `terrain`, then `tools/export.sh`; every file in `build/` with its size in bytes and
      MiB; the templates' URL, SHA-256 and size; the time taken.
      - does NOT prove: that the Windows build starts (no Windows here).
- [ ] The Linux export starts: `build/linux/mattini.x86_64 --headless --quit-after 300`
      prints the startup line with 4001 x 6001 at 0.5 m and no ERROR line (output recorded).
      - does NOT prove: that it renders or looks right; that it starts on the owner's
        EndeavourOS (a different glibc and driver).
- [ ] Mutation proofs: (a) `assets/generated/*` dropped from the Linux include filter → the
      exported build's headless run shows the missing-manifest message instead of the
      startup line (output recorded); (b) a 101 MiB file placed in `build/` before the size
      check → `tools/export.sh` fails naming it.
      - does NOT prove: every way an export can miss a file.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`; nothing under `build/`
      committed.
      - does NOT prove: that the release is done: the close ships it (`docs/RELEASE.md`).

## Forbidden

Pushing to `dist` or tagging (the close's); committing binaries; a version other than
0.1.0; changing `config/`, `tests/shared/`, `pipeline/mattini/` or a pinned copy.

## Findings (executor writes)

Executor session, 2026-09-25. Code commit `5c421ca` (rebased onto the board's tick-6
commits; the gate re-run after the rebase: exit 0).

1. **For the close: `mattini.exe` is 198'144 bytes under GitHub's limit.** It is Godot's
   own `windows_release_x86_64.exe` template, copied unchanged (`modify_resources` off):
   104'659'456 bytes, 99.81 MiB, against 104'857'600. Nothing in mattini makes it
   bigger or smaller; a later Godot's template may cross the limit on its own. The
   `.pck` has 8'733'492 bytes of room (91.67 MiB, 96'040'004 of them the village's
   heights).
2. **For design: mutation (a) shows the missing heights file, not the missing
   manifest.** With `export_filter="all_resources"` Godot counts `.json` files as
   resources, so `assets/generated/manifest.json` and `terrain/village.json` ship even
   without the include filter; only `village.f32` is left out (measured in the mutated
   `.pck`'s file table: 63 files, both JSON files in, no `.f32`). The exported build then
   stops at TerrainGrid's refusal instead of the startup line (run a below). The filter is
   still needed: without it no terrain ships.
3. **Pinned copies:** `cmp` of `game/tests/test_release_settings.gd` and
   `pipeline/tests/test_release_hygiene.py` against `docs/briefs/pinning/M1-06/`: both
   identical.
4. **The gate on the pushed head:** exit 0. pytest 367 passed, 3 deselected; GUT 15
   scripts, 69 tests, 1641 asserts, all passed; 65 `ERROR` lines, the same excepted ones
   as M1-05's (no entry added). Nothing under `build/` is tracked (`/build/` in
   `.gitignore`; the pinned hygiene test).
5. **The templates.** URL `https://downloads.godotengine.org/?version=4.6.3&flavor=stable&slug=export_templates.tpz&platform=templates`
   (the hook's mirror; it redirects to
   `godot-releases.nbg1.your-objectstorage.com/4.6.3-stable/Godot_v4.6.3-stable_export_templates.tpz`),
   1'255'918'323 bytes, SHA-256
   `3fbe2c0e2dec9d537ab9ec97bcf8da91dcf23357fc51f67092dd068d839290a8`. **How it was
   measured:** as the hook's Godot checksum was, `sha256sum` of the file as downloaded
   that day (two downloads, the same bytes). Also cross-checked, which the hook's was not:
   its SHA-512 equals the checksum Godot publishes for
   `Godot_v4.6.3-stable_export_templates.tpz` in `releases/godot-4.6.3-stable.json` of
   `github.com/godotengine/godot-builds` (commit `f43e5f55`, read through `git clone`,
   since release downloads are refused, H6). `SHA512-SUMS.txt` is not reachable from here:
   the mirror answers 404 for it, the storage bucket 403. The script installs seven files
   of the archive into Godot's templates folder (`~/.local/share/godot/export_templates/4.6.3.stable/`
   on Linux): `version.txt` and the x86_64 Linux and Windows templates, debug and release,
   with the Windows console wrappers; the other platforms' are not installed.
   - does NOT prove: that the Windows templates folder path (`%APPDATA%\Godot`, under Git
     Bash) is right; not run on Windows.
6. **One real export in the container** (the committed script, with a fresh
   `XDG_DATA_HOME` so the templates were missing): `download terrain` 5 s (6 tiles
   verified, 0 fetches: the tiles were already there), `terrain` 6 s, `tools/export.sh`
   61 s (38 s of it the download); 72 s in all, exit 0. Its step 5:

   | File | Bytes | MiB |
   |---|---|---|
   | `build/linux/libterrain.linux.release.x86_64.so` | 3'251'016 | 3.10 |
   | `build/linux/mattini.pck` | 96'124'108 | 91.67 |
   | `build/linux/mattini.x86_64` | 71'075'864 | 67.78 |
   | `build/windows/libterrain.windows.release.x86_64.dll` | 3'549'184 | 3.38 |
   | `build/windows/mattini.exe` | 104'659'456 | 99.81 |
   | `build/windows/mattini.pck` | 96'124'108 | 91.67 |

   The two `.pck` files are identical (SHA-256 `44950109…912f`). Their file table (parsed
   from the file, pack format 3): 64 files, among them `assets/generated/manifest.json`,
   `terrain/village.f32` (96'040'004 bytes), `terrain/village.json` and
   `addons/terrain_3d/LICENSE.txt`; no file of `tests/` or `addons/gut/`. Godot's shipped
   class cache still names GUT's classes (9 lines with `addons/gut`); the build runs
   without them (next item). The export printed no `ERROR` line.
   - does NOT prove: that the Windows build starts (no Windows here).
7. **The Linux export starts:** `build/linux/mattini.x86_64 --headless --quit-after 300`,
   exit 0 in 4.4 s, no `ERROR` line. Its whole output:

   ```
   WARNING: instance_reset_physics_interpolation() is deprecated.
        at: _instance_reset_physics_interpolation_bind_compat_104269 (servers/rendering/rendering_server.compat.inc:58)
   Godot Engine v4.6.3.stable.official.7d41c59c4 - https://godotengine.org

   mattini 0.1.0: terrain village loaded, 4001 x 6001 vertices at 0.5 m
   ```
   - does NOT prove: that it renders or looks right; that it starts on the owner's
     EndeavourOS.
8. **Mutation proofs**, each undone (`git apply -R` of its saved diff, or the placed file
   removed); `git status` clean after each.

   | Run | Mutation | Result | Owner-visible harm it reproduces |
   |---|---|---|---|
   | a | `assets/generated/*` dropped from the Linux preset's `include_filter` | `tools/export.sh` exit 0, the Linux `.pck` 84'016 bytes; the build's headless run, exit 0, prints `ERROR: TerrainGrid: res://assets/generated/manifest.json: the heights file res://assets/generated/terrain/village.f32 is missing; python -m mattini terrain rebuilds it` and no startup line (Findings 2) | a shipped build with no terrain in it, saying so instead of showing the village |
   | b | a 101 MiB file (`truncate -s 101M build/oversize.bin`) in `build/` before the run | exit 1: `export: over 100 MiB (104857600 bytes), which GitHub refuses (docs/RELEASE.md §C): build/oversize.bin` after listing it at 105'906'176 bytes | a release that GitHub refuses at the push to `dist` |
   | c (mine) | the pinned SHA-256's first digit changed, templates missing | exit 1: `the downloaded templates do not have the pinned SHA-256 …; nothing installed`; 0 files in the templates folder | a build made with templates nobody checked |
   | d (mine) | the generated manifest's `terrain` set to null | exit 1 at step 1, naming `download terrain`, then `terrain`; the manifest rewritten afterwards by `manifest` came back byte-identical | a release exported with no terrain |

   - does NOT prove: every way an export can miss a file.
9. **Choices inside the brief's scope** (reversible):
   - Step 3 also refuses a Godot other than 4.6.3 (its templates would not be these), as
     the gate does.
   - Only the seven template files above are installed; each is copied to `<name>.partial`
     and renamed, so an interrupted install leaves no half file under the real name.
     "Missing" means any of the seven absent or empty.
   - Step 4 empties `build/linux` and `build/windows` before exporting into them, passes
     the absolute export path, and fails unless the executable and its `.pck` were
     written (Godot's exit status alone is not trusted, H1, H2). Other files in `build/`
     are kept and measured in step 5. The export's output is not scanned for `ERROR`
     lines: an export that prints errors and still writes both files would pass.
   - Step 1 reads the manifest with the pipeline's Python (`json`), not a text match.
   - `export_presets.cfg` holds only what the brief names (plus `runnable`); Godot fills
     the rest with defaults. A headless `--editor --quit` and every export left it
     byte-unchanged.
   - The startup line prints the spacing as `0.5` (M1-05's number format), from
     `_load_terrain` right after the start view is set.

