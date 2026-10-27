extends GutTest
## Pinning tests for brief v0.4.0-04 (M4-04 whole): the sky clock agrees with design's vectors.
##
## Pinned decisions (m4-design §5, as decided on 2026-10-17): SkyClock
## (game/scripts/sky/sky_clock.gd) is static and pure; times are Unix seconds UTC (float).
## sun(unix, lat, lon) -> Vector2(azimuth true clockwise from north in [0, 360), apparent
## elevation with NOAA's refraction); moon(unix, lat, lon) -> Vector3(azimuth, topocentric
## elevation without refraction, illuminated fraction); sidereal_deg(unix, lon) -> local mean
## sidereal time in degrees [0, 360); zurich_offset_s(unix) -> 3600 or 7200; local_text(unix).
## Tolerances: sun 0.05 degrees where the expected elevation is above 2 degrees and 0.3 at or
## below (design's addition: below -5 degrees too, where §5 names none); moon 0.5 degrees in
## azimuth times cos(elevation) and in elevation, fraction 0.03; sidereal 0.01 degrees;
## offsets and texts exact.
##
## The vectors (tests/shared/sky_vectors.json, design data) come from pvlib's SPA (the sun,
## with NOAA's refraction added to SPA's true elevation: SPA refracts nothing below -0.83
## degrees, NOAA up to 0.47 degrees there), skyfield with DE421 (the moon, the sidereal time)
## and Python's zoneinfo (the offset and the text): none of them is the clock's own method.
## The other sites (southern hemisphere, west of Greenwich, far east) fail a site written into
## the clock and latitude and longitude swapped.
##
## Does NOT prove: the sky's look, the clock between the vectors' instants beyond what 295
## instants sample, or anything before 2020 or after 2035.

const VECTORS := "tests/shared/sky_vectors.json"
const SUN_FINE_DEG := 0.05
const SUN_LOW_DEG := 0.3
const SUN_FINE_ABOVE_DEG := 2.0
const MOON_DEG := 0.5
const MOON_FRACTION := 0.03
const SIDEREAL_DEG := 0.01

var _doc: Dictionary = {}


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func before_all() -> void:
	var json := JSON.new()
	if json.parse(FileAccess.get_file_as_string(_repo_file(VECTORS))) == OK:
		_doc = json.data


## The signed difference a - b of two angles in degrees, in [-180, 180).
func _angle_diff(a: float, b: float) -> float:
	return fposmod(a - b + 180.0, 360.0) - 180.0


func _vectors() -> Array:
	assert_true(_doc.has("vectors"), "the vectors are read")
	return _doc.get("vectors", [])


func _site() -> Dictionary:
	return _doc.get("site", {})


func test_the_vectors_are_designs() -> void:
	var vectors := _vectors()
	assert_between(vectors.size(), 150, 300, "about 150 to 300 instants")
	assert_eq(_site().get("latitude_deg"), 46.02, "the village's latitude")
	assert_eq(_site().get("longitude_deg"), 7.749, "the village's longitude")
	var starts := vectors.filter(func(v: Dictionary) -> bool: return v["tags"].has("start"))
	assert_eq(starts.size(), 1, "one start instant")


func test_the_sun_is_where_spa_puts_it() -> void:
	var lat: float = _site().get("latitude_deg", 0.0)
	var lon: float = _site().get("longitude_deg", 0.0)
	var worst := 0.0
	for v in _vectors():
		var got := SkyClock.sun(float(v["unix"]), lat, lon)
		var tol := SUN_FINE_DEG if v["sun_elevation_deg"] > SUN_FINE_ABOVE_DEG else SUN_LOW_DEG
		var d_az := absf(_angle_diff(got.x, v["sun_azimuth_deg"]))
		var d_el := absf(got.y - v["sun_elevation_deg"])
		worst = maxf(worst, maxf(d_az, d_el) / tol)
		assert_true(got.x >= 0.0 and got.x < 360.0, "%s: azimuth in [0, 360)" % v["utc"])
		assert_lt(
			d_az, tol, "%s: sun azimuth %.4f, SPA %.4f" % [v["utc"], got.x, v["sun_azimuth_deg"]]
		)
		assert_lt(
			d_el,
			tol,
			"%s: sun elevation %.4f, SPA %.4f" % [v["utc"], got.y, v["sun_elevation_deg"]]
		)
	gut.p("sun: worst error %.3f of its tolerance" % worst)


func test_the_moon_is_where_de421_puts_it() -> void:
	var lat: float = _site().get("latitude_deg", 0.0)
	var lon: float = _site().get("longitude_deg", 0.0)
	var worst := 0.0
	for v in _vectors():
		var got := SkyClock.moon(float(v["unix"]), lat, lon)
		var el: float = v["moon_elevation_deg"]
		var d_az := absf(_angle_diff(got.x, v["moon_azimuth_deg"])) * cos(deg_to_rad(el))
		var d_el := absf(got.y - el)
		var d_f := absf(got.z - v["moon_illuminated_fraction"])
		worst = maxf(worst, maxf(maxf(d_az, d_el) / MOON_DEG, d_f / MOON_FRACTION))
		assert_true(got.x >= 0.0 and got.x < 360.0, "%s: moon azimuth in [0, 360)" % v["utc"])
		assert_lt(
			d_az,
			MOON_DEG,
			"%s: moon azimuth %.3f, DE421 %.3f" % [v["utc"], got.x, v["moon_azimuth_deg"]]
		)
		assert_lt(d_el, MOON_DEG, "%s: moon elevation %.3f, DE421 %.3f" % [v["utc"], got.y, el])
		assert_lt(
			d_f,
			MOON_FRACTION,
			"%s: fraction %.3f, DE421 %.3f" % [v["utc"], got.z, v["moon_illuminated_fraction"]]
		)
	gut.p("moon: worst error %.3f of its tolerance" % worst)


func test_the_sidereal_time_is_skyfields() -> void:
	var lon: float = _site().get("longitude_deg", 0.0)
	for v in _vectors():
		var got := SkyClock.sidereal_deg(float(v["unix"]), lon)
		assert_true(got >= 0.0 and got < 360.0, "%s: in [0, 360)" % v["utc"])
		assert_lt(
			absf(_angle_diff(got, v["sidereal_deg"])),
			SIDEREAL_DEG,
			"%s: LMST %.5f, skyfield %.5f" % [v["utc"], got, v["sidereal_deg"]]
		)


func test_the_offset_and_the_text_are_zurichs() -> void:
	for v in _vectors():
		var unix := float(v["unix"])
		assert_eq(
			SkyClock.zurich_offset_s(unix), int(v["zurich_offset_s"]), "%s: offset" % v["utc"]
		)
		assert_eq(SkyClock.local_text(unix), v["local_text"], "%s: text" % v["utc"])


func test_other_sites_use_their_latitude_and_longitude() -> void:
	var others: Array = _doc.get("other_sites", [])
	assert_eq(others.size(), 12, "three sites, four instants")
	for v in others:
		var unix := float(v["unix"])
		var lat: float = v["latitude_deg"]
		var lon: float = v["longitude_deg"]
		var label := "%s %s" % [v["site"], v["utc"]]
		var sun := SkyClock.sun(unix, lat, lon)
		var tol := SUN_FINE_DEG if v["sun_elevation_deg"] > SUN_FINE_ABOVE_DEG else SUN_LOW_DEG
		assert_lt(absf(_angle_diff(sun.x, v["sun_azimuth_deg"])), tol, "%s: sun azimuth" % label)
		assert_lt(absf(sun.y - v["sun_elevation_deg"]), tol, "%s: sun elevation" % label)
		var moon := SkyClock.moon(unix, lat, lon)
		var el: float = v["moon_elevation_deg"]
		var d_az := absf(_angle_diff(moon.x, v["moon_azimuth_deg"])) * cos(deg_to_rad(el))
		assert_lt(d_az, MOON_DEG, "%s: moon azimuth" % label)
		assert_lt(absf(moon.y - el), MOON_DEG, "%s: moon elevation" % label)
		assert_lt(
			absf(moon.z - v["moon_illuminated_fraction"]), MOON_FRACTION, "%s: fraction" % label
		)
		var lst := SkyClock.sidereal_deg(unix, lon)
		assert_lt(absf(_angle_diff(lst, v["sidereal_deg"])), SIDEREAL_DEG, "%s: sidereal" % label)
