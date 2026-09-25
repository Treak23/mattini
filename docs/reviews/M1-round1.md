# Review M1 round 1 — adjudication

- **Reports:** `docs/reviews/M1-R1-terrain.md` (e9022f5, Tier 1) and
  `docs/reviews/M1-R1-game.md` (f95b7c6, Tier 2), over `git diff e83a36a..6fb378d` without
  `game/addons/` and `pipeline/uv.lock`, plus `game/addons/terrain_3d/` as vendored.
- **Adjudicated by:** tick 9, 2026-09-25.
- **Head verified:** ddbbc6e (the same code as 6fb378d; every change since is under
  `docs/`). Full `tools/gate.sh` twice: in the tick's checkout, and from a fresh worktree
  (no `game/.godot`, no generated assets). Both exit 0: pytest 367 passed, 3 deselected;
  GUT 15 scripts, 69 tests, 1641 asserts, `---- All tests passed! ----`; 65 `ERROR` lines,
  each excepted by `tools/gate_allowlist.txt`.

## Result

No P0 and no P1 in either lens, so no fix briefs (SUPERVISE §The tick 6). The terrain area
(Tier 1) is clean after R1, per the M0 R1 ruling in `docs/history/RULINGS.md` (a round with
P2/P3 findings only counts as clean). The game area (Tier 2) had no fixes, so it needs no
verification pass. Nothing escalates: WORKFLOW's escalation needs a finding in Tier-1
territory from the Tier 2 lens (the game lens found none) or a P1 in a verification pass.
Every P2 and P3 goes to the board's residue list for the close: 8 P2 and 10 P3.

**Grades.** The grades stand as the committed reports give them. The game lens session's
own closing summary called G-01, G-02 and G-03 "P1s"; its committed report grades all three
P2 and says "no P0 and no P1". The report is the record (lesson 30), as at M0 (D11). Each P2
in both reports rests on a harm a future change or a future consumer would meet; the code
under review was measured right (the village `b6334c1f…`, placed exactly at 0.5, 1 and 2 m;
a real export from a fresh checkout loads it). Design may regrade at the close.

## Dispositions

**A · The fix is unambiguous and inside an M1 brief's scope.** One cheap fix tranche if
design wants one:

| id | grade | fix, in one line | scope |
|---|---|---|---|
| T-03 | P2 | pin `build_terrain`'s own output for a fixed synthetic input to exact bytes; `manifest` requires exact key sets for `source` and each of its `tiles` | M1-03 (pinned tests) |
| T-05 (part 1) | P2 | the census also catches the km pair reversed (`1096 … 2623`) and a mantissa with trailing zeros (`2.6230e6`) | M1-01 / M0-02 census test |
| G-01 (part 1) | P2 | a test reads `show_checkered`, `shader_override_enabled` and the override's `resource_path` on the loaded terrain (all three read back headless, measured) | M1-04 tests |
| T-07 | P3 | the tracked-files test scoped by exclusion, per lesson 37 ("Scope a census by exclusion"), so the fixture and Terrain3D's binaries are covered | M1-01 test |
| G-04 | P3 | the GUT step compares GUT's last `---- ` line, as its comment says | `tools/gate.sh` |
| G-07 | P3 | `tools/shot.sh`'s header and usage name M1-05's views (`name`, `name,pause`) and the error-panel capture | `tools/shot.sh` |
| G-08 | P3 | `docs/RELEASE.md` §B names the pause screen (SPEC §13 row 15) instead of "OPEN" | `docs/RELEASE.md` |

**B · Design's call.** Not unambiguous, or they need design data, touch a pinned test, a
licence reading or a file no brief scopes:

| id | grade | the open choice |
|---|---|---|
| T-01 | P2 | a build test over at least 2 × 2 tiles with an area that cuts the outer tiles, pinned to bytes design computes; and on the real side, something that compares a built `village.f32` with SPEC §8's `b6334c1f…` (`terrain` says so, or a RELEASE.md line) |
| T-02 | P2 | a second game fixture north-west of its origin, across a row of regions, at 1 m or 2 m, with heights design computes |
| T-04 | P2 | `manifest` compares the terrain block's `source` with the lock and with `config/datasets.json` (attribution, collection), naming `terrain`; the fourth member (the pipeline's own code version) has no mechanism yet |
| T-05 (part 2) | P2 | how far apart on separate lines the km pair still counts (a wide window gives false alarms) |
| G-01 (part 2) | P2 | the `height_offset_m` uniform reads back only under a renderer: a check in `tools/shot.sh`'s run, or it stays unproved |
| G-02 | P2 | `tools/export.sh` step 6 starts `build/linux/mattini.x86_64 --headless --quit-after 300` and requires the startup line and no `ERROR` (6.3 s, measured); RELEASE.md §C gets the same line; optionally the include filter pinned exactly. Includes M1-06 Findings 9 as its member (a) |
| G-03 | P2 | drop the global `WorldConfig: not read from a manifest` allowlist entry (and find another way for the scan to know the unbuilt tests' line is deliberate), or keep it with a reason that says it is global |
| T-06 | P3 | the download and the lock take their area from `config/terrain.json`, or `terrain` refuses any area but the one the download serves |
| T-08 | P3 | reword the rules test's "one rounding" docstring, or compute its reference with one rounding and add such an offset case (pinned test, SPEC §8 wording) |
| T-09 | P3 | the pinned rotated-world test names the axes check but accepts any refusal (known, M1-04 Findings 5 runs e and j) |
| T-10 | P3 | the stray-tile test fails its mutation only through the unknown id (known, M1-03 Findings 7); worst variant is a refusal, not a wrong terrain |
| G-05 | P3 | the pinned "version only on the pause screen" test checks every visible `Control` with a `text`, not only `Label`s |
| G-06 | P3 | the credits carry godot-cpp's MIT notice, or RELEASE.md §A records why Godot's own notice covers it |

The known items the game lens graded (no new finding): M1-05 Findings 1 P3, M1-04
Findings 1 P3 (two more fresh checkouts did not abort), M1-06 Findings 2 P3, M1-06
Findings 9 P2 inside G-02.

## For the close

- **Close-facing.** The close ships 0.1.0, the owner's first look. Three residues have the
  close as their first consumer: G-02 (nothing starts the exported build; RELEASE.md §C has
  no such line; the lens measured today's export from a fresh checkout starting and loading
  the village), G-08 (RELEASE.md §B still says OPEN) and T-01's real-data half (nothing
  compares the owner's first `village.f32` with `b6334c1f…`, which M1-03's brief names as
  "the owner's first run is the check"). G-06 is a licence reading for any shared build.
- **One class, three places** (lesson 9): the gate's data is tidier than the village, and
  nothing checks the real thing. T-01 (the pipeline builds from one whole tile), T-02 (the
  game places one small grid at one spacing in one row of regions) and G-02 (the release
  never starts the build) are the same gap on three sides; decide them together.
- **A pinned test whose name claims more than it checks** (M0 G-08's class): T-09, G-05,
  and G-04's comment.
- **Inclusion lists again** (lesson 37): T-05 (spellings) and T-07 (tracked files).
- **Next arcs.** M2 is the first consumer of T-03 (new manifest blocks), T-05 (chunk-grid
  code), G-03 (loaders built in `before_all`); M3 and M4 of G-01 (the terrain material);
  M5 of T-02 and T-06 (a larger area, other spacings).
