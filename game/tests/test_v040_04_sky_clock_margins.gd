extends GutTest
## Fixer's own tests for brief v0.4.0-04: closes the prover's thin margins and the two
## uncovered harms the pinned tests leave. The pinned files stay byte-identical.
## Pinned whole by brief v0.5.0-11 (0.4.0 review TG-09): the two loops' counts and the measured
## numbers below.
##
## - The sun and moon vectors again at bands tighter than the pinned ones. The worst errors
##   (measured by brief v0.5.0-11's pin author, 2026-10-30): the sun above 2 degrees 0.0167
##   degrees against SUN_TIGHT_DEG 0.035 (2.1 times); the sun's elevation at 2 degrees and below
##   0.0108 against SUN_LOW_DEG / 2 = 0.15 (14 times); the moon 0.071 degrees (azimuth times
##   cos elevation; elevation 0.067) against MOON_TIGHT_DEG 0.25 (3.5 times); its phase 0.0091
##   against 0.015 (1.6 times). So dropping the sun's refraction (0.273 degrees off above 2
##   degrees, 0.579 at 2 and below) or the moon's -1.274 longitude term (1.27 off) fails by a
##   wide margin.
## - Each loop counts what it checked (brief v0.5.0-11, 0.4.0 review TG-09): 71 instants with the
##   sun above 2 degrees (more than 50 asserted), 224 at 2 degrees and below, 295 moons, all of
##   tests/shared/sky_vectors.json's 295; a loop that checks nothing passes nothing.
## - Kepler's solver is held to its own equation, which no pinned vector can do.
## - The southern hemisphere is held by geometry (a December sun is north of a southern site and
##   south of a northern one), independent of the other_sites rows.
##
## Does NOT prove: the moon's small perturbation terms individually (all under the pinned
## tolerance by design), or the sun's refraction cutoff and nutation terms.

const VECTORS := "tests/shared/sky_vectors.json"
const SUN_TIGHT_DEG := 0.035
const SUN_LOW_DEG := 0.3
const MOON_TIGHT_DEG := 0.25
const MOON_FRACTION_TIGHT := 0.015
## The vectors with the sun at 2 degrees and below, and all of them (the moons), counted in
## tests/shared/sky_vectors.json by GDScript and by Python's json (brief v0.5.0-11).
const LOW_SUN_VECTORS := 224
const MOON_VECTORS := 295

var _doc: Dictionary = {}


func before_all() -> void:
	var path := ProjectSettings.globalize_path("res://").path_join("..").path_join(VECTORS)
	var json := JSON.new()
	if json.parse(FileAccess.get_file_as_string(path)) == OK:
		_doc = json.data


func _angle_diff(a: float, b: float) -> float:
	return fposmod(a - b + 180.0, 360.0) - 180.0


func test_the_sun_holds_a_tighter_band() -> void:
	var lat: float = _doc["site"]["latitude_deg"]
	var lon: float = _doc["site"]["longitude_deg"]
	var checked := 0
	for v in _doc["vectors"]:
		if v["sun_elevation_deg"] <= 2.0:
			continue
		var got := SkyClock.sun(float(v["unix"]), lat, lon)
		assert_lt(absf(_angle_diff(got.x, v["sun_azimuth_deg"])), SUN_TIGHT_DEG, v["utc"])
		assert_lt(absf(got.y - v["sun_elevation_deg"]), SUN_TIGHT_DEG, v["utc"])
		checked += 1
	assert_gt(checked, 50, "enough daylight instants were checked")


func test_the_sun_below_the_horizon_holds_a_tighter_band() -> void:
	var lat: float = _doc["site"]["latitude_deg"]
	var lon: float = _doc["site"]["longitude_deg"]
	var checked := 0
	for v in _doc["vectors"]:
		if v["sun_elevation_deg"] > 2.0:
			continue
		var got := SkyClock.sun(float(v["unix"]), lat, lon)
		assert_lt(absf(got.y - v["sun_elevation_deg"]), SUN_LOW_DEG / 2.0, v["utc"])
		checked += 1
	assert_eq(checked, LOW_SUN_VECTORS, "every instant at 2 degrees and below was checked")


func test_the_moon_holds_a_tighter_band() -> void:
	var lat: float = _doc["site"]["latitude_deg"]
	var lon: float = _doc["site"]["longitude_deg"]
	var checked := 0
	for v in _doc["vectors"]:
		var got := SkyClock.moon(float(v["unix"]), lat, lon)
		var el: float = v["moon_elevation_deg"]
		var d_az := absf(_angle_diff(got.x, v["moon_azimuth_deg"])) * cos(deg_to_rad(el))
		assert_lt(d_az, MOON_TIGHT_DEG, "%s: azimuth" % v["utc"])
		assert_lt(absf(got.y - el), MOON_TIGHT_DEG, "%s: elevation" % v["utc"])
		assert_lt(
			absf(got.z - v["moon_illuminated_fraction"]),
			MOON_FRACTION_TIGHT,
			"%s: phase" % v["utc"]
		)
		checked += 1
	assert_eq(checked, MOON_VECTORS, "every vector's moon was checked")


func test_kepler_is_solved_to_convergence() -> void:
	var worst := 0.0
	for e: float in [0.0, 0.016709, 0.0549, 0.3, 0.6]:
		for i in 72:
			var m := 5.0 * i + 0.37
			var ea := SkyClock._kepler(m, e)
			# E - e sin E = M, in degrees.
			var residual := absf(ea - rad_to_deg(e * sin(deg_to_rad(ea))) - m)
			worst = maxf(worst, residual)
	assert_lt(worst, 1e-7, "Kepler's equation holds to 1e-7 degrees (worst %s)" % str(worst))


# 2025-12-21 at 12:00 UTC, three hours either side, at longitude 0.
func test_a_december_sun_is_north_of_the_south_and_south_of_the_north() -> void:
	var noon := 1766318400.0
	for hours in [-3.0, 3.0]:
		var t: float = noon + hours * 3600.0
		var south := SkyClock.sun(t, -34.0, 0.0)
		var north := SkyClock.sun(t, 34.0, 0.0)
		if hours < 0.0:
			assert_between(south.x, 20.0, 90.0, "morning sun at -34 is north-east")
			assert_between(north.x, 90.0, 160.0, "morning sun at +34 is south-east")
		else:
			assert_between(south.x, 270.0, 340.0, "afternoon sun at -34 is north-west")
			assert_between(north.x, 200.0, 270.0, "afternoon sun at +34 is south-west")
		assert_gt(south.y, 40.0, "the southern December sun is high")
		assert_lt(north.y, 35.0, "the northern December sun is low")
	var transit := SkyClock.sun(noon, -34.0, 0.0)
	assert_almost_eq(transit.y, 90.0 - 34.0 + 23.44, 0.5, "transit height at -34 in December")
