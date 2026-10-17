extends GutTest
## Pinning tests for brief M4-05, its stars section (option (a) of m4-design §10, the Yale
## Bright Star Catalogue): only with the owner's catalogue answer.
##
## Pinned decisions (m4-design §6 and §10, as decided on 2026-10-17):
## - The star table res://sky/stars.csv: made by the brief's script from CDS V/50's
##   catalog.gz (BSC5); the header "ra_deg,dec_deg,vmag", then one line per star with J2000
##   right ascension and declination in degrees (4 decimals) and V (2 decimals) for every
##   star with a J2000 position and V <= 6.0, sorted by V, then right ascension, then
##   declination; LF endings, a final LF; 5080 stars, 112127 bytes, SHA-256 2281ac54...
##   (design computed it twice, with two independent programs). Beside it
##   stars.csv.import holding exactly `[remap]\n\nimporter="keep"\n`: without it Godot
##   imports a .csv as translations (measured: stars.dec.translation and
##   stars.vmag.translation) and an export ships those, not the table.
## - SkyRig.star_image(path) -> Image: 4096 x 2048, FORMAT_RGBE9995, no mipmaps; a star at
##   (ra, dec) adds 10^(-0.4 V) to the red, green and blue of the texels of row
##   min(floor((90 - dec) / 180 * 2048), 2047), columns c - h to c + h (wrapped), with
##   c = floor(ra / 360 * 4096) mod 4096 and h = floor(0.5 / cos(dec)): about one texel's
##   height wide at any declination. Measured (Forward+, lavapipe): with one texel per star
##   Polaris's texel is 0.001 degrees wide and does not show. Given to SkyRig.create the image
##   is bound to the sky shader's night_sky.
## - The sky shader samples night_sky at the celestial coordinates of EYEDIR (u = right
##   ascension / 360, v = (90 - declination) / 180), never at SKY_COORDS, through
##   `uniform mat3 celestial_basis`; rig.apply sets it to the Basis that turns a scene
##   direction into celestial coordinates (x towards RA 0 on the equator, y towards RA 90,
##   z the north celestial pole) for the frame, the latitude and the local sidereal time.
##   So the celestial pole stands at the latitude's elevation in the north at any sidereal
##   time, and Polaris where its hour angle puts it, always within 1 degree of the latitude:
##   it is 0.74 degrees from the pole (J2000), so m4-design §6's "+-0.5 degrees at any time"
##   cannot hold for Polaris itself and is pinned for the pole. A star at RA 0, Dec 0
##   crosses the meridian in the south at LST 0 and sets in the west at LST 90.
## The frame is turned off every axis, as in test_m4_05_sky_rig.gd.
##
## Does NOT prove: that the stars render where the basis says (the shader's uv is read as
## text here; the brief's Forward+ probe looked), their look or brightness on screen, or the
## catalogue's licence (m4-design §10).

const STARS := "res://sky/stars.csv"
const STARS_SHA256 := "2281ac5417e1aeadb94f2c611ec01daea1e2b766a22ae45e874cb54dcc30bc9e"
const STARS_BYTES := 112127
const STARS_COUNT := 5080
const KEEP_IMPORT := '[remap]\n\nimporter="keep"\n'
const SHADER_PATH := "res://shaders/sky_physical.gdshader"
const WIDTH := 4096
const HEIGHT := 2048
const LAT := 46.02
const SIRIUS := [101.2871, -16.7161, -1.46]
const VEGA := [279.2346, 38.7836, 0.03]
const POLARIS := [37.9529, 89.2642, 2.02]

var _frame: Basis
var _rig: SkyRig
var _image: Image
var _root: Node3D


func _turned_frame() -> Basis:
	var turn := Basis(Vector3(1.0, 2.0, 3.0).normalized(), 0.7)
	return Basis(turn * Vector3(1, 0, 0), turn * Vector3(0, 0, -1), turn * Vector3(0, 1, 0))


func before_all() -> void:
	_image = SkyRig.star_image(STARS)


func before_each() -> void:
	_root = Node3D.new()
	var sun := DirectionalLight3D.new()
	var moon := DirectionalLight3D.new()
	_root.add_child(sun)
	_root.add_child(moon)
	add_child_autofree(_root)
	_frame = _turned_frame()
	_rig = SkyRig.create(sun, moon, Environment.new(), _frame, LAT, _image)


## The scene direction of the star at [param ra], [param dec] at sidereal time [param lst],
## through the rig's basis (its inverse: a rotation's transpose).
func _scene_direction(ra: float, dec: float, lst: float) -> Vector3:
	_rig.apply((_frame.x + _frame.z).normalized(), (_frame.y - _frame.z).normalized(), 0.5, lst)
	var basis: Basis = _rig.sky_material.get_shader_parameter("celestial_basis")
	var r := deg_to_rad(ra)
	var d := deg_to_rad(dec)
	var celestial := Vector3(cos(d) * cos(r), cos(d) * sin(r), sin(d))
	return basis.transposed() * celestial


func _azimuth(direction: Vector3) -> float:
	return fposmod(rad_to_deg(atan2(direction.dot(_frame.x), direction.dot(_frame.y))), 360.0)


func _elevation(direction: Vector3) -> float:
	return rad_to_deg(asin(clampf(direction.dot(_frame.z), -1.0, 1.0)))


func _texel(star: Array) -> Vector2i:
	var col := int(floor(star[0] / 360.0 * WIDTH)) % WIDTH
	var row := mini(int(floor((90.0 - star[1]) / 180.0 * HEIGHT)), HEIGHT - 1)
	return Vector2i(col, row)


func test_the_star_table_is_designs() -> void:
	var bytes := FileAccess.get_file_as_bytes(STARS)
	assert_eq(bytes.size(), STARS_BYTES, "its size")
	var hashing := HashingContext.new()
	hashing.start(HashingContext.HASH_SHA256)
	hashing.update(bytes)
	assert_eq(hashing.finish().hex_encode(), STARS_SHA256, "its SHA-256")
	var text := bytes.get_string_from_ascii()
	assert_false(text.contains("\r"), "LF endings")
	var lines := text.split("\n", false)
	assert_eq(lines.size(), STARS_COUNT + 1, "a header and 5080 stars")
	assert_eq(lines[0], "ra_deg,dec_deg,vmag", "the header")
	assert_eq(lines[1], "101.2871,-16.7161,-1.46", "Sirius first")
	assert_true(lines.has("279.2346,38.7836,0.03"), "Vega")
	assert_true(lines.has("37.9529,89.2642,2.02"), "Polaris")
	assert_eq(FileAccess.get_file_as_string(STARS + ".import"), KEEP_IMPORT, "kept, not translated")
	for leftover in ["res://sky/stars.dec.translation", "res://sky/stars.vmag.translation"]:
		assert_false(FileAccess.file_exists(leftover), "no translation: %s" % leftover)


func test_the_star_image_holds_each_star_at_its_texel() -> void:
	assert_not_null(_image, "the image is made")
	if _image == null:
		return
	assert_eq(_image.get_size(), Vector2i(WIDTH, HEIGHT), "4096 x 2048")
	assert_eq(_image.get_format(), Image.FORMAT_RGBE9995, "RGBE9995: bright and faint")
	assert_false(_image.has_mipmaps(), "no mipmaps")
	var flux := _image.duplicate() as Image
	flux.convert(Image.FORMAT_RF)
	var values := flux.get_data().to_float32_array()
	var sirius := _texel(SIRIUS)
	var vega := _texel(VEGA)
	var brightest := -1
	var top := 0.0
	var near_vega := 0.0
	for index in values.size():
		var v := values[index]
		if v > top:
			top = v
			brightest = index
		var col := index % WIDTH
		var row := index / WIDTH
		if absi(col - vega.x) <= 40 and absi(row - vega.y) <= 40 and Vector2i(col, row) != vega:
			near_vega = maxf(near_vega, v)
	assert_eq(Vector2i(brightest % WIDTH, brightest / WIDTH), sirius, "the brightest is Sirius")
	assert_almost_eq(top, pow(10.0, 0.4 * 1.46), 0.02, "Sirius: 10^(0.4 * 1.46)")
	var vega_value := values[vega.y * WIDTH + vega.x]
	assert_almost_eq(vega_value, pow(10.0, -0.4 * 0.03), 0.01, "Vega: 10^(-0.4 * 0.03)")
	assert_lt(near_vega, vega_value, "Vega the brightest within 40 texels (3.5 degrees)")
	var c := _image.get_pixel(sirius.x, sirius.y)
	assert_almost_eq(c.g, c.r, 0.0001, "white: green")
	assert_almost_eq(c.b, c.r, 0.0001, "white: blue")
	var polaris := _texel(POLARIS)
	assert_almost_eq(
		_image.get_pixel(polaris.x, polaris.y).r, pow(10.0, -0.4 * 2.02), 0.002, "Polaris"
	)


func test_a_star_near_the_pole_spans_its_row() -> void:
	assert_not_null(_image, "the image is made")
	if _image == null:
		return
	var polaris := _texel(POLARIS)
	var flux := pow(10.0, -0.4 * 2.02)
	var half := 38  # floor(0.5 / cos(89.2642 degrees)) = floor(38.93)
	for k in range(-half, half + 1):
		var v := _image.get_pixel(posmod(polaris.x + k, WIDTH), polaris.y).r
		assert_almost_eq(v, flux, 0.002, "Polaris's run, %+d texels" % k)
	for k in [-half - 1, half + 1]:
		var v := _image.get_pixel(posmod(polaris.x + k, WIDTH), polaris.y).r
		assert_lt(v, flux / 2.0, "Polaris's run ends at %+d texels" % k)
	var sirius := _texel(SIRIUS)
	for k in [-1, 1]:
		var v := _image.get_pixel(sirius.x + k, sirius.y).r
		assert_lt(v, 1.0, "Sirius (-16.7 degrees) is one texel wide: %+d" % k)


func test_the_star_image_is_bound_to_the_sky() -> void:
	var texture := _rig.sky_material.get_shader_parameter("night_sky") as Texture2D
	assert_not_null(texture, "night_sky holds the stars")
	if texture != null:
		assert_eq(texture.get_size(), Vector2(WIDTH, HEIGHT), "the star image's size")


func test_the_pole_stands_at_the_latitude_in_the_north() -> void:
	for lst in [0.0, 77.0, 168.06, 245.5, 333.3]:
		var pole := _scene_direction(0.0, 90.0, lst)
		assert_almost_eq(_elevation(pole), LAT, 0.001, "the pole at the latitude, LST %.2f" % lst)
		var az := _azimuth(pole)
		assert_true(az < 0.001 or az > 359.999, "the pole in the north, LST %.2f: %.4f" % [lst, az])


func test_polaris_circles_the_pole_where_its_hour_angle_puts_it() -> void:
	var phi := deg_to_rad(LAT)
	var dec := deg_to_rad(POLARIS[1])
	for lst in [0.0, 37.95, 127.95, 217.95, 307.95]:
		var hour := deg_to_rad(lst - POLARIS[0])
		var want := rad_to_deg(asin(sin(phi) * sin(dec) + cos(phi) * cos(dec) * cos(hour)))
		var star := _scene_direction(POLARIS[0], POLARIS[1], lst)
		var el := _elevation(star)
		assert_almost_eq(el, want, 0.01, "Polaris's elevation, LST %.2f" % lst)
		assert_almost_eq(el, LAT, 1.0, "Polaris within a degree of the latitude, LST %.2f" % lst)
		var az := fposmod(_azimuth(star) + 180.0, 360.0) - 180.0
		assert_almost_eq(az, 0.0, 1.1, "Polaris in the north, LST %.2f" % lst)


func test_the_equator_crosses_the_meridian_in_the_south_at_its_sidereal_time() -> void:
	var at_zero := _scene_direction(0.0, 0.0, 0.0)
	assert_almost_eq(_azimuth(at_zero), 180.0, 0.001, "RA 0 at LST 0: south")
	assert_almost_eq(_elevation(at_zero), 90.0 - LAT, 0.001, "RA 0 at LST 0: 43.98 high")
	var setting := _scene_direction(0.0, 0.0, 90.0)
	assert_almost_eq(_azimuth(setting), 270.0, 0.001, "RA 0 at LST 90: setting in the west")
	assert_almost_eq(_elevation(setting), 0.0, 0.001, "on the horizon")
	var rising := _scene_direction(0.0, 0.0, 270.0)
	assert_almost_eq(_azimuth(rising), 90.0, 0.001, "RA 0 at LST 270: rising in the east")
	var vega := _scene_direction(VEGA[0], VEGA[1], VEGA[0])
	assert_almost_eq(_azimuth(vega), 180.0, 0.001, "Vega on the meridian at LST = its RA")
	assert_almost_eq(_elevation(vega), 90.0 - LAT + VEGA[1], 0.001, "Vega 82.76 high")


func test_the_sky_shader_samples_the_stars_in_celestial_coordinates() -> void:
	var shader: Shader = load(SHADER_PATH)
	var declared := {}
	for uniform in shader.get_shader_uniform_list():
		declared[uniform["name"]] = uniform["type"]
	assert_eq(declared.get("celestial_basis"), TYPE_BASIS, "declares mat3 celestial_basis")
	assert_eq(declared.get("night_sky"), TYPE_OBJECT, "declares night_sky")
	var code := ""
	for line in shader.code.split("\n"):
		code += line.get_slice("//", 0) + "\n"
	assert_false(code.contains("SKY_COORDS"), "the stars are not fixed to the scene")
	assert_true(code.contains("celestial_basis *"), "a direction turned by the basis")
	assert_true(code.contains("EYEDIR"), "the view's direction")
