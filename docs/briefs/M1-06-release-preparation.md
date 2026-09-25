# Brief: M1-06 — Release preparation for 0.1.0
Status: OPEN

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

