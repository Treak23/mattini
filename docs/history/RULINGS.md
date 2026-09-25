# RULINGS.md — the index of every answered question

One line per ruling, newest first, full text under `docs/history/blocked/`. Checked BEFORE
a question is filed; never startup reading. Formats:
`<date> · design · <brief> · <question> → <answer>` ·
`<date> · supervisor · <brief> · <question> → <answer>, per <citation>` ·
`<date> · owner's word, in the waker session · <brief> · <question> → <answer>`

The M0 close's rulings (2026-09-24) have their full text in `docs/history/ARCS.md` §M0,
numbered D1–D12 there.
The M1 close's rulings (2026-09-25) have theirs in `docs/history/ARCS.md` §M1, numbered
D13–D21 there.

2026-09-25 · design · M1 close · the builders' reversible choices (M1-01 F6, M1-02 F6, M1-03 F6, M1-04 F8, M1-05 F6–7, M1-06 F9) → all kept; M1-06 F9's unscanned export output joins G-02's fix (D13)
2026-09-25 · design · M1 close · a fix tranche before 0.1.0? → no: 0.1.0 ships now; T-01's real-data half, G-02 and G-08 were done by hand at the close; the rest go into M2's first briefs (D14)
2026-09-25 · design · M1 close · `*-previous.*` cannot work (a `.pck` is found by its executable's name, Terrain3D's library has a fixed name) → `dist` holds `windows/` and `linux/` (current, fixed names) and `mattini-<version>/` (the last three kept; the one before the current is the rollback), a README and `* binary` (D15; SPEC §11, RELEASE.md §C)
2026-09-25 · design · M1 close · an export over 100 MB? → none is over (`mattini.exe` 99.81 MiB, Godot's own template; `.pck` 91.67 MiB); SPEC §14 stays OPEN and is asked at M2 planning, since M2's buildings go into the `.pck` (D16)
2026-09-25 · design · M1 R1 G-06 · Terrain3D's library compiles in godot-cpp: its own notice, or Godot's as cover? → its own: the credits carry godot-cpp's MIT notice (M2's first game brief) and RELEASE.md §A names it; 0.1.0 lacks it and stays the owner's own build (D17)
2026-09-25 · design · M1 R1 · regrade G-01–G-03, which the lens's session summary called P1? → no; the committed P2 grades stand (D18; lesson 30)
2026-09-25 · design · M1 R1 · the eighteen findings → G-08 and T-08's SPEC half fixed at the close; T-09 and T-10 declined (each guarded elsewhere); fifteen carried into M2 with the fix named, T-01 (b) as an expected SHA-256 per area and spacing in `config/terrain.json` checked by `terrain` and `manifest` (D19)
2026-09-25 · design · M1-04 F1, M1-05 F1 · brain.md H11's abort and camera lines → the abort did not reproduce in any fresh checkout since, the list step stays; Terrain3D looks for the camera at its first physics frame (D20)
2026-09-25 · design · M1 close · the waker's due rule, landing wakes, the spawn prompts' sync line → no change (no tick was wasted); working (every tick 0.5–5 min after its landing); carried to M2 planning with a measured recipe (D21; brain.md H14)
2026-09-24 · design · M0 close · does M0 ship a version? → no: it has nothing to play (the main scene is empty); the first version is planned for M1's close, and a close without a version writes its record to `docs/history/ARCS.md` (D1; SPEC §11, DESIGN.md rule 4)
2026-09-24 · design · M0-02, M0-03 · what does `height_offset_m` mean? → the vertical part of the origin, y = H − height_offset_m on both sides, as built and pinned; kept (D2; SPEC §6)
2026-09-24 · design · M0-03 · keep the gate checks the builder added (import `valid=false`, GUT `[ERROR]`, ANSI codes stripped)? → keep all three; `valid=false` is the import step's only detector in cloud sessions (D3; brain.md H1)
2026-09-24 · design · M0-03 · CLAUDE.md's `gdlint game` lints the vendored GUT → CLAUDE.md now gives the gate's file list; no `gdlintrc` (D4)
2026-09-24 · design · M0-01 · `uv lock --check` in the gate, and `.gitattributes`? → both, in M1's first briefs: `uv lock --check` (measured offline, 12 ms) and `* text=auto eol=lf` for the whole repository, with a test (D5)
2026-09-24 · design · M0-01 · the gate re-run after the push, not before → recorded in the ledger; no rule change (D6)
2026-09-24 · design · M0-04 · what if swisstopo republishes a tile inside an edition? → the repository pins every used tile's SHA-256 and the download refuses a changed one, built in M1 (D7; SPEC §5)
2026-09-24 · design · M0-04 · the builder's reversible choices (Findings 8) → all kept (D8)
2026-09-24 · design · M0 R1 · C-05 with G-06: what is M1's tile list? → `provenance.json` only, checked against the config (edition, resolution, tile list); the download removes it before its first change on disk; stray `.tif` files stay (D9)
2026-09-24 · design · M0 R1 · the design's-call findings (C-02 part 2, C-04, C-07, C-09, G-02, G-03, G-05, G-08, G-10) → as in the carry-over table: km spelling caught; `.gitattributes`; NaN plus an error for an unbuilt WorldConfig; C-09 fixed now; only `All tests passed!` passes; `^ERROR` scanned in GUT with one allowlist entry; `valid=false` ratified; `--error-unmatch` in a live test; `XDG_DATA_HOME` per gate run (D10)
2026-09-24 · design · M0 R1 · regrade the P2s the lens summaries called "critical"? → no; the committed grades stand (D11)
2026-09-24 · design · M0 R1 · a fix tranche before M1, or M1's briefs carry the residue? → M1's first briefs carry it, before any M1 brief that writes shaders, project settings, manifest fields, a main-scene script or Terrain3D tests (D12)
2026-09-24 · supervisor · M0 R1 · does a round with P2/P3 findings only, in Tier-1 territory included, count as clean? → yes: fix briefs only for P0/P1, P2/P3 to the board's residue list, per SUPERVISE §The tick 6 ("Fix briefs only for P0/P1 findings … P2/P3 → the board's residue list") and WORKFLOW §Review policy ("Residual P2/P3s go to the board and the report-back"); adjudication in `docs/reviews/M0-round1.md`
2026-09-25 · supervisor · M1 R1 · both lenses report no P0 and no P1 (8 P2, 10 P3, Tier-1 territory included): is the round clean? → yes, and no fix briefs, per the M0 R1 ruling above (2026-09-24, "a round with P2/P3 findings only … count as clean? → yes") and SUPERVISE §The tick 6; adjudication in `docs/reviews/M1-round1.md`
