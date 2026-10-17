# Brief: M4-04 — The sky clock
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane D of wave 1 of arc M4.

## Goal

The game knows where the sun and the moon stand over Zermatt at any moment from 2020 to 2035,
what the clocks in Zermatt read then, and the local sidereal time the stars need.

- **`SkyClock`** (`game/scripts/sky/sky_clock.gd`): static, pure, headless. It takes a time in
  Unix seconds UTC and a place, and returns the sun's and the moon's azimuth and elevation, the
  moon's illuminated fraction, the local mean sidereal time, Zurich's UTC offset and the text
  of the in-game clock.
- It holds no state and reads no clock, file or setting: the main scene (M4-10, wave 2) owns
  the running time and the place (`config/sky.json` through the manifest, M4-09).

## Read first, in order

1. `CLAUDE.md` (Hard Rule 2); `brain.md` H2, H3 (a test script that does not parse is skipped
   and passes), H9 (`--check-only` needs an import first for a new `class_name`), H25 (wrap
   Godot runs in `timeout`).
2. `docs/briefs/sketches/m4-design.md` §0 (the flight's sun) and §5 (this brief); SPEC §13
   row 43 (the start).
3. `tests/shared/sky_vectors.json` (design data): its `sources` say how every number was made.
4. The methods (cite them in the code):
   - the sun: NOAA's solar calculator, "General Solar Position Calculations" and the
     spreadsheet's formulas (https://gml.noaa.gov/grad/solcalc/calcdetails.html; Meeus,
     *Astronomical Algorithms*);
   - the moon: Paul Schlyter, "How to compute planetary positions"
     (https://stjarnhimlen.se/comp/ppcomp.html), §4 (the elements), §6 to §9 (the moon's
     perturbations) and §13 (topocentric position);
   - the sidereal time: Meeus, *Astronomical Algorithms*, formula 12.4.
5. The pinned tests: `docs/briefs/pinning/M4-04/`.

## Decisions already made

1. **The class.** `class_name SkyClock`, `extends RefCounted`, every function `static`:
   - `const START_UNIX := 1694000400.0`: 2023-09-06T11:40:00Z, 13:40 CEST, the photo's moment
     (SPEC §13 row 43).
   - `zurich_offset_s(unix: float) -> int`: 7200 from 01:00 UTC on the last Sunday of March
     up to (not including) 01:00 UTC on the last Sunday of October of the year of `unix`
     (UTC), else 3600. A rule, not a table (SR 941.299.1, the EU rule): one function, so a
     change of the rule is one edit. A fractional time counts as the second it falls in.
   - `local_text(unix: float) -> String`: `"6 Sep 2023 13:40 CEST"`: the day without a
     leading zero, the English three-letter month (`Jan` … `Dec`), the year, hours and
     minutes with two digits each (24-hour, `01:59`), `CET` or `CEST`. Minutes are
     truncated, never rounded: 13:40:59.9 reads 13:40.
   - `sun(unix: float, lat_deg: float, lon_deg: float) -> Vector2`: (azimuth, elevation) in
     degrees; azimuth true, clockwise from north, in [0, 360); elevation apparent: the true
     elevation plus NOAA's refraction, exactly as the spreadsheet: none above 85°;
     58.1/tan e − 0.07/tan³ e + 0.000086/tan⁵ e above 5°; 1735 − 518.2 e + 103.4 e² −
     12.79 e³ + 0.711 e⁴ above −0.575°; −20.772/tan e below (arcseconds). The longitude is
     east-positive. UTC stands in for UT1 (under 0.9 s).
   - `moon(unix: float, lat_deg: float, lon_deg: float) -> Vector3`: (azimuth, elevation,
     illuminated fraction): Schlyter's elements of the moon and the sun, Kepler's equation
     solved to convergence, the perturbations in longitude (12 terms), latitude (5) and
     distance (2), the ecliptic of date to the equator, then the topocentric correction
     (parallax asin(1/r), geocentric latitude and ρ as Schlyter's §13) against the hour
     angle from `sidereal_deg`. No refraction. The fraction is (1 − cos elongation) / 2, the
     elongation from Schlyter's sun and the moon's ecliptic longitude and latitude. Our own
     code; Schlyter's page named in a comment.
   - `sidereal_deg(unix: float, lon_deg: float) -> float`: Meeus 12.4, 280.46061837 +
     360.98564736629 (JD − 2451545) + 0.000387933 T² − T³ / 38710000, plus the east
     longitude, in [0, 360). JD = unix / 86400 + 2440587.5.
2. **Precision.** GDScript `float` is 64-bit; `Vector2` and `Vector3` are 32-bit, which keeps
   an azimuth to about 1e-5°: compute in `float`, build the vector last.
3. **The tolerances** (m4-design §5), in the pinned tests: the sun 0.05° where the expected
   elevation is above 2°, 0.3° at or below (design's addition: below −5° too, where §5 names
   none); the moon 0.5° in azimuth × cos(elevation) and in elevation, the fraction 0.03;
   sidereal 0.01°; the offset and the text exact.
4. **The vectors** (`tests/shared/sky_vectors.json`, design data, 295 instants from 2020 to
   2035 at 46.0200 N, 7.7490 E, 1610 m, plus 12 at three other places): the sun from pvlib's
   SPA, its expected elevation SPA's true elevation plus NOAA's refraction (SPA refracts nothing
   below −0.83°, where NOAA adds up to 0.47°: more than the 0.3° band, so a correct NOAA clock
   would fail SPA's own apparent elevation between −1.1° and −0.83°; SPA's own value is kept
   in the file for reference); the moon from skyfield with JPL's DE421 (topocentric, no
   refraction); the sidereal time from skyfield at UT1 = UTC; the offset and the text from
   Python's zoneinfo. The site is the village centre of m4-design §0, not yet
   `config/sky.json`'s (brief M4-09): design substitutes that file's values if they differ by
   more than 1e-3°; the tests pass the vectors' own site to the clock.
5. **Measured with design's throwaway** (this brief's method, 2026-10-17): the worst sun
   error 0.33 of its tolerance, the moon 0.30; all 295 texts and offsets exact; each pinned
   file failed against a stub `SkyClock` that parses and returns zeros (vectors 5 of 6 tests,
   the sixth reads only the data; rules 6 of 6).

## Scope — files you may touch

- `game/scripts/sky/sky_clock.gd` and its `.uid` (new);
- `game/tests/`: the pinned `test_m4_04_sky_clock_vectors.gd` and `test_m4_04_sky_clock_rules.gd`
  (new, with `.uid`), and your own new tests.

Not `main.gd`, `main.tscn` or `project.godot` (M4-10); not `tests/shared/sky_vectors.json`
(design data); nothing under `game/scripts/sky/` but this file (lane E writes `sky_rig.gd`
beside it).

## Depends on

None. Lane E (M4-05) does not call `SkyClock`: its tests pass directions directly. M4-10
(wave 2) joins them.

## Done when (gates)

- [ ] The pinned copies are in place (`docs/briefs/pinning/M4-04/game/tests/*.gd` copied to
      `game/tests/`, one by one if the auto-mode classifier refuses `cp -r … .`) and stay
      byte-identical (`cmp`).
      - does NOT prove: that they are the right tests.
- [ ] Mutations, each applied alone, each failing a named pinned test, recorded with the harm
      it reproduces (lesson 4):
      - the azimuth counted from the south;
      - east and west mirrored (360° − azimuth);
      - local time used as UTC (the sun computed at `unix + offset`);
      - summer time switched at local 01:00 (00:00 UTC);
      - the sidereal time in hours;
      - minutes rounded in the text;
      - the moon without the topocentric correction;
      - the phase inverted ((1 + cos elongation) / 2);
      - latitude and longitude swapped in `sun`.
      - does NOT prove: anything between the vectors' instants that 295 instants do not
        sample, before 2020 or after 2035, or a change of the Swiss rule.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the sun and moon it computes reach the scene (M4-10), or that
        anything renders or looks right.

## Forbidden

A table of switch dates; Godot's or the operating system's time zone functions
(`Time.get_time_zone_from_system`, local-time variants of `Time`); reading the system clock;
a new dependency or plugin; editing a pinned file or the vectors; touching the main scene.

## Findings (executor writes)
