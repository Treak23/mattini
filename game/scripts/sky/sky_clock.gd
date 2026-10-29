class_name SkyClock
extends RefCounted
## Where the sun and the moon stand over a place at a moment, what the clocks in
## Zermatt read then, and the local sidereal time. Brief v0.4.0-04 (M4-04 whole);
## design: docs/briefs/sketches/m4-design.md section 5.
##
## Static, pure and headless: it holds no state and reads no clock, file or setting.
## Time is Unix seconds UTC, latitude and longitude are degrees (longitude east-positive),
## angles come back in true-north, clockwise-from-north terms. Nothing here converts them
## to the game's grid. The vectors in tests/shared/sky_vectors.json cover 2020 to 2035;
## nothing here claims more. The game's day keys can leave that range; the clock's output there
## is unvalidated (nothing is clamped).
##
## Sources:
##  - the sun: NOAA's solar calculator, "General Solar Position Calculations" and its
##    spreadsheet (https://gml.noaa.gov/grad/solcalc/calcdetails.html; Meeus,
##    Astronomical Algorithms).
##  - the moon: Paul Schlyter, "How to compute planetary positions"
##    (https://stjarnhimlen.se/comp/ppcomp.html), sections 4, 6 to 9 and 13.
##  - the sidereal time: Meeus, Astronomical Algorithms, formula 12.4.
##  - Zurich's offset: the EU summer-time rule as Swiss law has it (SR 941.299.1): CEST
##    from 01:00 UTC on the last Sunday of March to 01:00 UTC on the last Sunday of October.
##  - dates from a day count: Howard Hinnant's days_from_civil and civil_from_days
##    ("chrono-compatible low-level date algorithms").

## 2023-09-06T11:40:00Z, 13:40 CEST: the photo's moment (SPEC section 13 row 43).
const START_UNIX := 1694000400.0

const _MONTHS := [
	"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]


## Zurich's UTC offset in seconds at `unix`: 7200 from 01:00 UTC on the last Sunday of
## March up to (not including) 01:00 UTC on the last Sunday of October of the UTC year,
## else 3600. A fractional time counts as the second it falls in.
static func zurich_offset_s(unix: float) -> int:
	var s := floori(unix)
	var year: int = _civil_from_days(floori(float(s) / 86400.0))[0]
	var spring := _last_sunday_days(year, 3) * 86400 + 3600
	var autumn := _last_sunday_days(year, 10) * 86400 + 3600
	if s >= spring and s < autumn:
		return 7200
	return 3600


## The in-game clock text, e.g. "6 Sep 2023 13:40 CEST": day without a leading zero,
## English three-letter month, year, 24-hour hours and minutes (truncated, never
## rounded), CET or CEST.
static func local_text(unix: float) -> String:
	var offset := zurich_offset_s(unix)
	var local := floori(unix) + offset
	var days := floori(float(local) / 86400.0)
	var second := local - days * 86400
	var ymd := _civil_from_days(days)
	var hours := second / 3600
	var minutes := (second % 3600) / 60
	var zone := "CEST" if offset == 7200 else "CET"
	return "%d %s %d %02d:%02d %s" % [ymd[2], _MONTHS[ymd[1] - 1], ymd[0], hours, minutes, zone]


## The sun as (azimuth, elevation) in degrees: azimuth true, clockwise from north, in
## [0, 360); elevation apparent (the true elevation plus NOAA's refraction). UTC stands in
## for UT1.
static func sun(unix: float, lat_deg: float, lon_deg: float) -> Vector2:
	var jd := unix / 86400.0 + 2440587.5
	var t := (jd - 2451545.0) / 36525.0
	var l0 := fposmod(280.46646 + t * (36000.76983 + 0.0003032 * t), 360.0)
	var m := 357.52911 + t * (35999.05029 - 0.0001537 * t)
	var ecc := 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
	var c := (
		_sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t))
		+ _sin(2.0 * m) * (0.019993 - 0.000101 * t)
		+ _sin(3.0 * m) * 0.000289
	)
	var omega := 125.04 - 1934.136 * t
	var lambda := l0 + c - 0.00569 - 0.00478 * _sin(omega)
	var eps0 := 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - 0.001813 * t))) / 60.0) / 60.0
	var eps := eps0 + 0.00256 * _cos(omega)
	var decl := rad_to_deg(asin(_sin(eps) * _sin(lambda)))
	var y := _tan(eps / 2.0) * _tan(eps / 2.0)
	var eq_time := (
		4.0
		* rad_to_deg(
			(
				y * _sin(2.0 * l0)
				- 2.0 * ecc * _sin(m)
				+ 4.0 * ecc * y * _sin(m) * _cos(2.0 * l0)
				- 0.5 * y * y * _sin(4.0 * l0)
				- 1.25 * ecc * ecc * _sin(2.0 * m)
			)
		)
	)
	var minutes := fposmod(unix, 86400.0) / 60.0
	var tst := fposmod(minutes + eq_time + 4.0 * lon_deg, 1440.0)
	var hour_angle := tst / 4.0 - 180.0
	var cos_z := clampf(
		_sin(lat_deg) * _sin(decl) + _cos(lat_deg) * _cos(decl) * _cos(hour_angle), -1.0, 1.0
	)
	var z := rad_to_deg(acos(cos_z))
	var elevation := 90.0 - z
	var cos_a := (_sin(lat_deg) * _cos(z) - _sin(decl)) / (_cos(lat_deg) * _sin(z))
	var a := rad_to_deg(acos(clampf(cos_a, -1.0, 1.0)))
	var azimuth := fposmod(a + 180.0, 360.0) if hour_angle > 0.0 else fposmod(540.0 - a, 360.0)
	elevation += _refraction_arcsec(elevation) / 3600.0
	return Vector2(azimuth, elevation)


## The moon as (azimuth, elevation, illuminated fraction): topocentric, no refraction;
## azimuth true, clockwise from north; the fraction (1 - cos elongation) / 2.
## Schlyter's elements and perturbations; our own code.
static func moon(unix: float, lat_deg: float, lon_deg: float) -> Vector3:
	var d := unix / 86400.0 + 2440587.5 - 2451543.5
	# The sun (Schlyter section 4).
	var w_s := 282.9404 + 4.70935e-5 * d
	var e_s := 0.016709 - 1.151e-9 * d
	var m_s := fposmod(356.0470 + 0.9856002585 * d, 360.0)
	var ecl := 23.4393 - 3.563e-7 * d
	var ea_s := _kepler(m_s, e_s)
	var v_s := rad_to_deg(atan2(sqrt(1.0 - e_s * e_s) * _sin(ea_s), _cos(ea_s) - e_s))
	var lambda_s := v_s + w_s
	# The moon (section 4).
	var n := 125.1228 - 0.0529538083 * d
	var inc := 5.1454
	var w := 318.0634 + 0.1643573223 * d
	var a := 60.2666
	var e := 0.054900
	var mm := fposmod(115.3654 + 13.0649929509 * d, 360.0)
	var ea := _kepler(mm, e)
	var xv := a * (_cos(ea) - e)
	var yv := a * sqrt(1.0 - e * e) * _sin(ea)
	var v := rad_to_deg(atan2(yv, xv))
	var r := sqrt(xv * xv + yv * yv)
	var xh := r * (_cos(n) * _cos(v + w) - _sin(n) * _sin(v + w) * _cos(inc))
	var yh := r * (_sin(n) * _cos(v + w) + _cos(n) * _sin(v + w) * _cos(inc))
	var zh := r * _sin(v + w) * _sin(inc)
	var lon_m := rad_to_deg(atan2(yh, xh))
	var lat_m := rad_to_deg(atan2(zh, sqrt(xh * xh + yh * yh)))
	# The perturbations (section 9).
	var ls := m_s + w_s
	var lm := mm + w + n
	var dd := lm - ls
	var f := lm - n
	lon_m += (
		-1.274 * _sin(mm - 2.0 * dd)
		+ 0.658 * _sin(2.0 * dd)
		- 0.186 * _sin(m_s)
		- 0.059 * _sin(2.0 * mm - 2.0 * dd)
		- 0.057 * _sin(mm - 2.0 * dd + m_s)
		+ 0.053 * _sin(mm + 2.0 * dd)
		+ 0.046 * _sin(2.0 * dd - m_s)
		+ 0.041 * _sin(mm - m_s)
		- 0.035 * _sin(dd)
		- 0.031 * _sin(mm + m_s)
		- 0.015 * _sin(2.0 * f - 2.0 * dd)
		+ 0.011 * _sin(mm - 4.0 * dd)
	)
	lat_m += (
		-0.173 * _sin(f - 2.0 * dd)
		- 0.055 * _sin(mm - f - 2.0 * dd)
		- 0.046 * _sin(mm + f - 2.0 * dd)
		+ 0.033 * _sin(f + 2.0 * dd)
		+ 0.017 * _sin(2.0 * mm + f)
	)
	r += -0.58 * _cos(mm - 2.0 * dd) - 0.46 * _cos(2.0 * dd)
	# Ecliptic of date to the equator.
	var xg := r * _cos(lon_m) * _cos(lat_m)
	var yg := r * _sin(lon_m) * _cos(lat_m)
	var zg := r * _sin(lat_m)
	var ye := yg * _cos(ecl) - zg * _sin(ecl)
	var ze := yg * _sin(ecl) + zg * _cos(ecl)
	var ra := rad_to_deg(atan2(ye, xg))
	var dec := rad_to_deg(atan2(ze, sqrt(xg * xg + ye * ye)))
	# Topocentric correction (section 13).
	var lmst := sidereal_deg(unix, lon_deg)
	var mpar := rad_to_deg(asin(1.0 / r))
	var gclat := lat_deg - 0.1924 * _sin(2.0 * lat_deg)
	var rho := 0.99833 + 0.00167 * _cos(2.0 * lat_deg)
	var ha := lmst - ra
	var top_ra := ra - mpar * rho * _cos(gclat) * _sin(ha) / _cos(dec)
	var top_dec: float
	if is_zero_approx(gclat):
		top_dec = dec - mpar * rho * _sin(-dec) * _cos(ha)
	else:
		var g := rad_to_deg(atan(_tan(gclat) / _cos(ha)))
		top_dec = dec - mpar * rho * _sin(gclat) * _sin(g - dec) / _sin(g)
	# To the horizon.
	var ha2 := lmst - top_ra
	var x := _cos(ha2) * _cos(top_dec)
	var y := _sin(ha2) * _cos(top_dec)
	var z := _sin(top_dec)
	var xhor := x * _sin(lat_deg) - z * _cos(lat_deg)
	var zhor := x * _cos(lat_deg) + z * _sin(lat_deg)
	var azimuth := fposmod(rad_to_deg(atan2(y, xhor)) + 180.0, 360.0)
	var elevation := rad_to_deg(asin(clampf(zhor, -1.0, 1.0)))
	var cos_elong := _cos(lambda_s - lon_m) * _cos(lat_m)
	var fraction := (1.0 - cos_elong) / 2.0
	return Vector3(azimuth, elevation, fraction)


## The local mean sidereal time at `lon_deg` east, in degrees in [0, 360)
## (Meeus 12.4; UTC stands in for UT1).
static func sidereal_deg(unix: float, lon_deg: float) -> float:
	var dd := unix / 86400.0 + 2440587.5 - 2451545.0
	var t := dd / 36525.0
	var theta0 := 280.46061837 + 360.98564736629 * dd + 0.000387933 * t * t - t * t * t / 38710000.0
	return fposmod(theta0 + lon_deg, 360.0)


# NOAA's refraction in arcseconds, chosen on the true elevation `e` in degrees.
static func _refraction_arcsec(e: float) -> float:
	if e > 85.0:
		return 0.0
	var te := _tan(e)
	if e > 5.0:
		return 58.1 / te - 0.07 / (te * te * te) + 0.000086 / (te * te * te * te * te)
	if e > -0.575:
		return 1735.0 - 518.2 * e + 103.4 * e * e - 12.79 * e * e * e + 0.711 * e * e * e * e
	return -20.772 / te


# Kepler's equation by Newton's method; degrees in, degrees out (Schlyter section 4).
static func _kepler(m_deg: float, ecc: float) -> float:
	var ea := m_deg + rad_to_deg(ecc * _sin(m_deg) * (1.0 + ecc * _cos(m_deg)))
	for _i in 50:
		var step := (ea - rad_to_deg(ecc * _sin(ea)) - m_deg) / (1.0 - ecc * _cos(ea))
		ea -= step
		if absf(step) < 1e-9:
			break
	return ea


# Day number (since 1970-01-01) of the last Sunday of `month` (31 days: March, October).
static func _last_sunday_days(year: int, month: int) -> int:
	var last := _days_from_civil(year, month, 31)
	# 1970-01-01 was a Thursday: weekday (Sunday 0) = (days + 4) mod 7.
	return last - (last + 4) % 7


# Hinnant's days_from_civil: days since 1970-01-01 of a proleptic Gregorian date.
static func _days_from_civil(year: int, month: int, day: int) -> int:
	var y := year - 1 if month <= 2 else year
	var era := floori(float(y) / 400.0)
	var yoe := y - era * 400
	var doy := (153 * (month + (-3 if month > 2 else 9)) + 2) / 5 + day - 1
	var doe := yoe * 365 + yoe / 4 - yoe / 100 + doy
	return era * 146097 + doe - 719468


# Hinnant's civil_from_days: [year, month, day] of a day count since 1970-01-01.
static func _civil_from_days(days: int) -> Array:
	var z := days + 719468
	var era := floori(float(z) / 146097.0)
	var doe := z - era * 146097
	var yoe := (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365
	var y := yoe + era * 400
	var doy := doe - (365 * yoe + yoe / 4 - yoe / 100)
	var mp := (5 * doy + 2) / 153
	var d := doy - (153 * mp + 2) / 5 + 1
	var m := mp + 3 if mp < 10 else mp - 9
	return [y + 1 if m <= 2 else y, m, d]


static func _sin(deg: float) -> float:
	return sin(deg_to_rad(deg))


static func _cos(deg: float) -> float:
	return cos(deg_to_rad(deg))


static func _tan(deg: float) -> float:
	return tan(deg_to_rad(deg))
