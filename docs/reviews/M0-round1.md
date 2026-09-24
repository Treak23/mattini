# Review M0 round 1 — adjudication

- **Reports:** `docs/reviews/M0-R1-coordinates.md` (d643870, Tier 1) and
  `docs/reviews/M0-R1-gate.md` (2589429, Tier 2), over `git diff 366b0b5..a8cfa63` without
  `game/addons/` and `pipeline/uv.lock`.
- **Adjudicated by:** tick 4, 2026-09-24.
- **Head verified:** eb65041, full `tools/gate.sh` from a fresh worktree (no `game/.godot`,
  no generated assets): exit 0; pytest 209 passed, 2 network tests deselected; GUT 5
  scripts, 13 tests, 943 asserts, `All tests passed!`; 0 `ERROR` lines besides the 41 the
  refusal tests provoke on purpose (`ERROR: WorldConfig: user://test_world_config_…`).

## Result

No P0 and no P1 in either lens, so no fix briefs (SUPERVISE §The tick 6). The coordinates
area (Tier 1) is clean after R1. The gate area (Tier 2) had no fixes, so it needs no
verification pass. Nothing escalates, because WORKFLOW's escalation needs a P1 or worse.
Every P2 and P3 goes to the board's residue list for the close.

**Grades.** The grades stand as the committed reports give them. The lens sessions' own
closing summaries called their P2s "critical" and "priority-1". The reports are the record
(lesson 30), and each P2 there makes its harm depend on a future writer. Design may regrade
at the close.

## Dispositions

**A · The fix is unambiguous and inside an M0 brief's scope.** These can go into one
cheap fix tranche if design wants one before M1:

| id | grade | fix, in one line | scope |
|---|---|---|---|
| C-01 | P2 | pin the exact key sets of the manifest and of `provenance.json` (or golden bytes) | M0-02, M0-04 tests |
| C-02 (part 1) | P2 | census over every tracked file outside config/tests/docs/addons, plus e-notation spellings | M0-02 tests |
| C-03 | P2 | the game's rotation loop also asserts `to_lv95(to_local(p)) ≈ p` | M0-03 tests |
| G-01 | P2 | the allowlist refuses an entry whose text is empty or blank | `tools/gate.sh` |
| G-04 | P2 | `-gconfig=` on the gate's GUT command (fix measured by the lens: e3, e4) | `tools/gate.sh` |
| G-06 | P2 | `download_terrain` deletes `provenance.json` before its first unlink or fetch; test a failed re-run | M0-04 |
| C-06 | P3 | the random round trips use 64-bit offsets | M0-03 tests |
| C-08 | P3 | an empty manifest says "empty", not "(OK)" | M0-03 |
| G-07 | P3 | `grep -a -E` in the scans | `tools/gate.sh` |
| G-09 | P3 | a first Godot step requires `4.6.3.stable` | `tools/gate.sh` |

**B · Design's call.** These are not unambiguous, or they touch design data, a pinned test
or a file no brief scopes:

| id | grade | the open choice |
|---|---|---|
| C-02 (part 2) | P2 | whether the census also catches the kilometre spelling (`2623 … 1096`) |
| C-04 | P2 | where `.gitattributes` goes (`* text=auto eol=lf`, or `config/**` + `tests/shared/**`); this extends the board's `*.sh` item |
| C-05 | P2 | M1's tile list: `provenance.json` alone, or `download_terrain` removes or reports stray `.tif` files. It becomes a P1 if M1 lists the folder. |
| G-02 | P2 | the GUT step requires GUT's final summary: `All tests passed!` only, or also pending/risky |
| G-03 | P2 | scan `^ERROR` in the GUT step with an allowlist entry for the refusal tests, or rely on each hook asserting; CLAUDE.md:27-28 overstates what the GUT step catches either way |
| G-05 | P2 | ratify the `valid=false` check (in cloud sessions it is the import step's only detector, measured: k1, k2); brain.md H1 wording; the hook's warm-up log |
| C-07 | P3 | `WorldConfig.new()`: a `_valid` flag with `push_error`, or NaN defaults |
| C-09 | P3 | Matterhorn vector: E 2617048.75, or "(rounded)" in its name (design data) |
| G-08 | P3 | the pinned hygiene test also asserts `git ls-files --error-unmatch` (pinned test) |
| G-10 | P3 | per-run `user://` folder names in the tests, or a line in lesson 20 or brain.md |

## For the close

- **M1-facing.** C-02, C-05, G-02, G-03, G-04 and G-05 each name M1 as their first
  consumer: terrain shaders, the tile list, a main-scene script, `before_all` loads, and
  the Terrain3D warning (brain.md H4). Design decides whether a fix tranche comes before
  M1 or M1's briefs carry them.
- **One question, two halves.** C-05 (files on disk that provenance does not list) and
  G-06 (provenance lists a file that is not on disk) meet at one question: what is M1's
  source of truth for tiles? Decide them together (lesson 9).
- **Tier 1 test gaps.** C-01, C-02 and C-03 are gaps in the tests that guard Hard Rules 4
  and 5. CLAUDE.md requires those tests to be mutation-proved; they are. The lens then
  found mutations they miss. Each fix is unambiguous (row A).
