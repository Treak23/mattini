# Review M2 R1 — adjudication

Round R1 over arc M2, `63816ac..88678e2`, by three lenses (placement at Tier 1, inputs,
game and tools), each finding from P0 to P2 put to three skeptics told to refute it. Run
and adjudicated in the one M2 session (the owner's word, RULINGS 2026-09-25).

**Result:** no P0, no P1. Five P2s, each upheld by all three skeptics at P2. Sixteen P3s.
Every lens ran the standard gate at the head: exit 0 (pytest 662 passed, 4 deselected; GUT
20 scripts, 98 tests, 2692 asserts). The round is clean by the rule of the M0 and M1
rounds (RULINGS 2026-09-24, 2026-09-25: P2 and P3 only, Tier 1 included, is clean).

What the round measured as right, beyond the gate:
- the real village's terrain and buildings rebuilt from the real inputs to design's
  hashes;
- a third independent derivation of the six chunks, byte for byte;
- 17 buildings placed by hand through `config/world.json` and found where the reader puts
  them;
- 1'475 of 1'486 buildings with the ground between floor and roof in the game;
- a rotated or shifted world never producing a wrong world, only refusals;
- the live lock and download equal to design's values;
- fiona's Windows wheel in the lock;
- the export passing with both startup lines;
- every error-panel combination shown as designed.

**Disposition.** The round is clean, so no fix is required before shipping. Design takes
the P2s and the cheap P3s now anyway, because the release waits on the owner's answer
about where it goes, so fixing costs the owner no time:

| Finding | Grade | Disposition |
|---|---|---|
| P-01 buildings' scene transform ungated | P2 | M2-08 |
| P-02 expected hashes blame the machine after a world change | P2 | M2-07 (`computed_for`) |
| P-03 buildings block's box unchecked | P3 | M2-07 |
| P-04 BuildingChunks' world check untested | P3 | M2-08 |
| P-05 SPEC misses the 8 buried buildings | P3 | design, at the close (SPEC §8, the release record) |
| P-06 buildings fixture's terrain config is an unlabelled placeholder | P3 | M2-07 (labelled) |
| I-01 adopting a republish ends in a machine-blaming refusal | P2 | M2-07 (`computed_for`) |
| I-02 download's refusal before any fetch unproven from an empty folder | P2 | M2-07 |
| I-03 provenance removal before a fetch untested | P3 | M2-07 |
| I-04 download and step disagree on a valid lock | P3 | M2-07 |
| I-05 two refusals end in a traceback | P3 | M2-07 |
| I-06 the grid places 2xxx ids 600 km away | P3 | M2-07 |
| I-07 missing sheets near coverage gaps | P3 | carried to M5 planning (the board) |
| I-08 docs lag | P3 | design, at the close |
| G-01 buildings' look untested | P2 | M2-08 |
| G-02 camera at the origin when the terrain is refused | P3 | M2-08 |
| G-03 export.sh checks blocks before rewriting | P3 | M2-08 |
| G-04 GUT's version unpinned by the gate | P3 | M2-08 |
| G-05 a one-word allowlist entry silences the scans | P3 | M2-08 |
| G-06 stale files and tools in the export | P3 | M2-07 (stale chunks), M2-08 (`tools/*`) |
| G-07 shot.sh's header | P3 | M2-08 |

Also taken into M2-08 is residue from M2-02's check: a test that prints GUT's pass line
itself and quits passes the gate. The verification pass over M2-07 and M2-08 (WORKFLOW
§Review policy, Tier 2: one) follows their landing.
