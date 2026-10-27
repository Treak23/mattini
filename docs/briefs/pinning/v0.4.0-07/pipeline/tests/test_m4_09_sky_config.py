"""Pinning tests for brief M4-09: config/sky.json, the sun's place for the game (design data).

Pinned decisions (m4-design §4): config/sky.json is exactly {"schema": 1, "areas": {<area>:
{"computed_for": {"world_sha256"}, "latitude_deg", "longitude_deg", "true_to_grid_deg"}}}, its
one area the terrain config's. latitude_deg and longitude_deg are WGS84 at the centre of the
area's box in config/world.json; true_to_grid_deg is the angle that, ADDED to an azimuth
measured clockwise from true north, gives the azimuth from LV95 grid north at that centre. At
the village grid north lies 0.226 degrees east of true north, so the value is negative:
-0.2258 (design computed it with pyproj 3.8.0 / PROJ 9.8.1, EPSG:2056 to EPSG:4326, as the
grid azimuth of a step along the true meridian; PROJ's own `meridian_convergence` there is
+0.2265, the true azimuth of grid north, the opposite sign). `computed_for.world_sha256` is the
SHA-256 of config/world.json's bytes.

The check here uses no projection library: swisstopo's published approximate formulas for
LV95 to WGS84 (swisstopo, "Approximate formulas for the transformation between Swiss
projection coordinates and WGS84", Wabern, the 1 m-level formulas, LV95 form with y' = (E -
2'600'000 m) / 1'000'000 and x' = (N - 1'200'000 m) / 1'000'000; results in units of 10'000",
times 100 / 36 for degrees). The convergence comes from the formulas' derivatives along grid
north: the true azimuth of grid north is atan2(Nr cos(lat) dlon, M dlat) with the WGS84 radii
of curvature M and Nr; true_to_grid_deg is its negative. The formulas are good to about a metre:
latitude and longitude within 1e-4 degrees, the convergence within 0.01 degrees (m4-design §4).

Does NOT prove: that the game turns azimuths with this value (brief M4-10), or that the sun
stands where it should in the sky (brief M4-04's vectors).
"""

import hashlib
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WGS84_A = 6378137.0
WGS84_E2 = 0.00669437999014


def _formulas(east: float, north: float) -> tuple[float, float, float, float]:
    """(lat, lon, dlat/dN, dlon/dN) in degrees and degrees per metre, by swisstopo's formulas."""
    y = (east - 2_600_000.0) / 1_000_000.0
    x = (north - 1_200_000.0) / 1_000_000.0
    lon = 2.6779094 + 4.728982 * y + 0.791484 * y * x + 0.1306 * y * x**2 - 0.0436 * y**3
    lat = (
        16.9023892
        + 3.238272 * x
        - 0.270978 * y**2
        - 0.002528 * x**2
        - 0.0447 * y**2 * x
        - 0.0140 * x**3
    )
    dlon_dx = 0.791484 * y + 2 * 0.1306 * y * x
    dlat_dx = 3.238272 - 2 * 0.002528 * x - 0.0447 * y**2 - 3 * 0.0140 * x**2
    scale = 100.0 / 36.0
    return lat * scale, lon * scale, dlat_dx * scale / 1e6, dlon_dx * scale / 1e6


def _centre() -> tuple[float, float]:
    world = json.loads((REPO / "config" / "world.json").read_text("utf-8"))
    (area,) = world["areas"].values()
    return (area["e_min"] + area["e_max"]) / 2, (area["n_min"] + area["n_max"]) / 2


def _sky() -> dict:
    return json.loads((REPO / "config" / "sky.json").read_text("utf-8"))


def test_the_config_is_exactly_its_shape_and_area():
    sky = _sky()
    assert set(sky) == {"schema", "areas"} and sky["schema"] == 1
    terrain = json.loads((REPO / "config" / "terrain.json").read_text("utf-8"))
    assert list(sky["areas"]) == list(terrain["areas"])
    (area,) = sky["areas"].values()
    assert set(area) == {"computed_for", "latitude_deg", "longitude_deg", "true_to_grid_deg"}
    assert set(area["computed_for"]) == {"world_sha256"}
    assert all(
        type(area[k]) is float for k in ("latitude_deg", "longitude_deg", "true_to_grid_deg")
    )


def test_computed_for_is_this_world():
    (area,) = _sky()["areas"].values()
    world = (REPO / "config" / "world.json").read_bytes()
    assert area["computed_for"]["world_sha256"] == hashlib.sha256(world).hexdigest()


def test_the_place_is_the_area_s_centre_by_swisstopo_s_formulas():
    (area,) = _sky()["areas"].values()
    lat, lon, _, _ = _formulas(*_centre())
    assert abs(area["latitude_deg"] - lat) < 1e-4, (area["latitude_deg"], lat)
    assert abs(area["longitude_deg"] - lon) < 1e-4, (area["longitude_deg"], lon)


def test_true_to_grid_is_minus_the_true_azimuth_of_grid_north():
    (area,) = _sky()["areas"].values()
    lat, _, dlat, dlon = _formulas(*_centre())
    phi = math.radians(lat)
    w = math.sqrt(1 - WGS84_E2 * math.sin(phi) ** 2)
    meridian = WGS84_A * (1 - WGS84_E2) / w**3  # M
    normal = WGS84_A / w  # Nr
    grid_north = math.degrees(
        math.atan2(normal * math.cos(phi) * math.radians(dlon), meridian * math.radians(dlat))
    )
    assert grid_north > 0, "east of Bern's meridian grid north lies east of true north"
    assert abs(area["true_to_grid_deg"] - (-grid_north)) < 0.01, (
        area["true_to_grid_deg"],
        grid_north,
    )
    # an azimuth of 184.9 deg from true north is 184.67 deg from grid north
    assert round(184.9 + area["true_to_grid_deg"], 2) == 184.67
