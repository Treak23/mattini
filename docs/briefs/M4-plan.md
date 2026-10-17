# M4 — The sun cycle: the arc plan

Status: DRAFT — design is still writing it (not READY)

**Base:** the commit that sets this status line to GO (its message starts `docs: M4 GO`;
`git log --grep '^docs: M4 GO' -1`). It is the base of the integration notes and of the
review's diff range.

Written by the design realm (`docs/roles/DESIGN.md` §The arc plan); run by one `ultracode
build` orchestrator (`docs/roles/BUILD.md` §The orchestrator). The owner's answers of
2026-10-17 are SPEC §13 rows 41–46 and `docs/history/RULINGS.md`. Design's working notes, which
the briefs cite as "m4-design §N", are `docs/briefs/sketches/m4-design.md` (SPEC and the briefs
outrank them); the measurements are in its §0 and in `docs/briefs/sketches/M4-deshadow/` and
`M4-soften/`. No model is named (WORKFLOW §Models): every spawn inherits.

## What M4 delivers

Version **0.4.0**: the real sun over Zermatt.
- The sun and the moon stand where they stand at the game's date and time, computed for the
  village. The game starts at the photo's moment (6 September 2023, 13:40 CEST); keys move the
  time and the date, change its speed, or set the computer's clock.
- The sun leaves the village behind the real mountains: swissALTIRegio's heights for 20 km
  around cast shadows (a shadows-only mesh; drawn in M5).
- A physical sky that follows the sun, a twilight, a faint night glow, the sun's disk; at night
  the moon lights the scene by its phase, and (with the owner's catalogue answer) the stars turn
  with the sky. Exposure follows the sun's height (0.70 by day, measured; 4.0 at night).
- The photo's baked shadows are softened (lifted 3× inside a capture-time mask from the surface
  model), so the moving sun's shadows read and the photo's do not darken twice.
- The river: the photo's own colour, less mirror, turbulent ripples, a soft bank.
- The 0.3.0 test's fixes: a frame cap (60; 15 while paused), the log flushed line by line, a
  missing data pack named, anti-aliasing (MSAA 4×).

## Briefs, lanes and waves

A lane is one builder session; its briefs run in order on shared files. The lanes of a wave run
at once and share no file in their Scopes (checked from each brief's Scope and Depends on lines).
Design data (`config/surroundings.json`, `config/shadows.json`, `config/sky.json`, the fixtures
and vectors under `tests/shared/`) is committed with this plan; no lane writes it.

(Lanes, waves, integration notes and the review plan follow when the last rehearsals land.)
