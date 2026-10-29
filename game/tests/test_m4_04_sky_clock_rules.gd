extends GutTest
## Pinning tests for brief v0.4.0-04 (M4-04 whole): the clock's start, Zurich's summer time and
## the clock's text, exactly, and the likeliest wrong twins of the sky clock, each by name
## (lesson 34).
##
## Pinned decisions (m4-design §5; SPEC §13 row 43): START_UNIX is 2023-09-06T11:40:00Z,
## 1694000400 seconds, 13:40 CEST, the photo's moment. zurich_offset_s is 7200 from 01:00 UTC
## on the last Sunday of March up to (not including) 01:00 UTC on the last Sunday of October,
## else 3600 (SR 941.299.1, the EU rule), for a fractional second too. local_text is "6 Sep
## 2023 13:40 CEST": the day without a leading zero, the English three-letter month, the year,
## hours and minutes with two digits each (24-hour), minutes truncated (13:40:59 is 13:40),
## CET or CEST. The switch instants below are written out (computed by design with Python's
## datetime, 2026-10-17), not computed here, so that the test is not the clock's twin.
##
## The wrong twins, each with the instant that tells it: the azimuth counted from the south;
## east and west mirrored (an azimuth counted counter-clockwise); local time used as UTC; the
## switch at local 01:00 (00:00 UTC); the sidereal time in hours; minutes rounded.
##
## Does NOT prove: Zurich's offsets before 2020 or after 2035, or a change of the Swiss rule.

const START := 1694000400.0
const LAT := 46.02
const LON := 7.749
## 01:00 UTC on the last Sunday of March and of October.
const SWITCHES := {
	2020: [1585443600, 1603587600],
	2021: [1616893200, 1635642000],
	2022: [1648342800, 1667091600],
	2023: [1679792400, 1698541200],
	2024: [1711846800, 1729990800],
	2025: [1743296400, 1761440400],
	2026: [1774746000, 1792890000],
	2027: [1806195600, 1824944400],
	2028: [1837645200, 1856394000],
	2029: [1869094800, 1887843600],
	2030: [1901149200, 1919293200],
	2031: [1932598800, 1950742800],
	2032: [1964048400, 1982797200],
	2033: [1995498000, 2014246800],
	2034: [2026947600, 2045696400],
	2035: [2058397200, 2077146000],
}


func test_the_clock_starts_at_the_photos_moment() -> void:
	assert_eq(SkyClock.START_UNIX, START, "2023-09-06T11:40:00Z")
	assert_eq(SkyClock.local_text(SkyClock.START_UNIX), "6 Sep 2023 13:40 CEST", "13:40 CEST")
	assert_eq(SkyClock.zurich_offset_s(SkyClock.START_UNIX), 7200, "summer time")


func test_summer_time_switches_at_0100_utc_on_the_last_sundays() -> void:
	for year in SWITCHES:
		var spring: float = SWITCHES[year][0]
		var autumn: float = SWITCHES[year][1]
		assert_eq(SkyClock.zurich_offset_s(spring - 1.0), 3600, "%d: a second before spring" % year)
		assert_eq(SkyClock.zurich_offset_s(spring - 0.001), 3600, "%d: a millisecond before" % year)
		assert_eq(SkyClock.zurich_offset_s(spring), 7200, "%d: at 01:00 UTC in March" % year)
		assert_eq(SkyClock.zurich_offset_s(autumn - 1.0), 7200, "%d: a second before autumn" % year)
		assert_eq(SkyClock.zurich_offset_s(autumn), 3600, "%d: at 01:00 UTC in October" % year)
		# Twin: the switch at local 01:00 (00:00 UTC). At 00:30 UTC the old offset holds.
		assert_eq(SkyClock.zurich_offset_s(spring - 1800.0), 3600, "%d: 00:30 UTC in March" % year)
		assert_eq(
			SkyClock.zurich_offset_s(autumn - 1800.0), 7200, "%d: 00:30 UTC in October" % year
		)
		# Mid-winter and mid-summer.
		assert_eq(SkyClock.zurich_offset_s(spring - 60.0 * 86400.0), 3600, "%d: January" % year)
		assert_eq(SkyClock.zurich_offset_s(spring + 90.0 * 86400.0), 7200, "%d: June" % year)


func test_the_texts_are_exact() -> void:
	var texts := {
		1679792399.0: "26 Mar 2023 01:59 CET",
		1679792400.0: "26 Mar 2023 03:00 CEST",
		1698541199.0: "29 Oct 2023 02:59 CEST",
		1698541200.0: "29 Oct 2023 02:00 CET",
		1735685999.0: "31 Dec 2024 23:59 CET",
		1735686000.0: "1 Jan 2025 00:00 CET",
		1709161200.0: "29 Feb 2024 00:00 CET",
		1709247600.0: "1 Mar 2024 00:00 CET",
		1693951200.0: "6 Sep 2023 00:00 CEST",
		1693951199.0: "5 Sep 2023 23:59 CEST",
		# Minutes truncated, never rounded: 13:40:59.9 is 13:40.
		1694000459.9: "6 Sep 2023 13:40 CEST",
		2077146000.0 + 9.0 * 3600.0 + 5.0 * 60.0: "28 Oct 2035 11:05 CET",
	}
	for unix in texts:
		assert_eq(SkyClock.local_text(unix), texts[unix], "at %.1f" % unix)


func test_the_azimuth_is_true_clockwise_from_north() -> void:
	# At the start the sun stands a little west of south: 184.9 (SPA). Counted from the south
	# it would read 4.9; mirrored east-west, 175.1.
	var start := SkyClock.sun(START, LAT, LON)
	assert_almost_eq(start.x, 184.886, 0.05, "the start's sun, 184.9 degrees")
	assert_almost_eq(start.y, 50.334, 0.05, "the start's sun, 50.3 degrees high")
	# 2026-06-21 05:00 UTC, the morning: the sun in the north-east (SPA 68.2), not the
	# north-west (291.8) a mirror gives or the south-west (248.2) the south's count gives.
	var morning := SkyClock.sun(1782018000.0, LAT, LON)
	assert_almost_eq(morning.x, 68.153, 0.05, "the morning sun in the north-east")
	# 2026-06-21 18:30 UTC, the evening: the north-west.
	var evening := SkyClock.sun(1782066600.0, LAT, LON)
	assert_almost_eq(evening.x, 296.619, 0.05, "the evening sun in the north-west")


func test_the_time_is_utc_not_local() -> void:
	# Local time taken as UTC moves the start's sun two hours west: about 226 degrees, 41 high.
	var start := SkyClock.sun(START, LAT, LON)
	assert_almost_eq(start.x, 184.886, 0.05, "UTC, not 13:40 taken as UTC")
	assert_almost_eq(SkyClock.sidereal_deg(START, LON), 168.06001, 0.01, "the start's LMST")


func test_the_sidereal_time_is_in_degrees() -> void:
	# In hours it would never pass 24.
	assert_almost_eq(SkyClock.sidereal_deg(START, LON), 168.06001, 0.01, "degrees, not hours")
	assert_almost_eq(SkyClock.sidereal_deg(START, 0.0), 160.31101, 0.01, "Greenwich, GMST")
	assert_almost_eq(
		SkyClock.sidereal_deg(START + 6.0 * 3600.0, LON),
		fposmod(168.06001 + 6.0 * 15.041068, 360.0),
		0.01,
		"six hours later, 90.25 degrees on"
	)
