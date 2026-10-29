extends GutTest
## Pinning tests for brief v0.4.0-06: M4-05's stars section (section S) on the Hipparcos
## Catalogue (SPEC §13 row 51, the owner's "2a" of 2026-10-27, amending row 48: the Yale Bright
## Star Catalogue has no licence; Hipparcos is CC BY-NC 3.0 IGO, "Credit: ESA").
##
## Pinned decisions (m4-design §6, as decided on 2026-10-17; the catalogue, the table's header
## lines and the credit of brief v0.4.0-06):
## - The star table res://sky/stars.csv: made by tools/stars_table.py from the Hipparcos
##   Catalogue's main file (ESA 1997, ESA SP-1200; CDS I/239 hip_main.dat, 53316318 bytes,
##   SHA-256 58ceabb1..., which the script checks before it writes; it refuses any other). Three
##   lines starting "# " (HEADER: the credit, the changes made, ESA's page; CC BY-NC 3.0 IGO
##   lets an adaptation be shared only if it labels its changes, section 3(b), and credits the
##   work, section 4(c)), the column header "ra_deg,dec_deg,vmag", then one line per record
##   with V (Vmag, field H5) <= 6.0: right ascension and declination in degrees from RAhms and
##   DEdms (fields H3 and H4; ICRS, epoch J1991.25, used as given: no precession, no proper
##   motion; every record carries them, so no star is lost), 4 decimals, and V, 2 decimals;
##   sorted by V, then right ascension, then declination, as numbers; LF endings, a final LF;
##   5044 stars, 112045 bytes, SHA-256 e2a98eea... (design computed it twice, with two
##   independent programs, Python slicing the records' bytes and awk splitting their fields:
##   the same bytes). Beside it stars.csv.import holding exactly
##   `[remap]\n\nimporter="keep"\n`, and nothing else in res://sky/: without it Godot
##   imports a .csv as translations (measured: one .translation file per field of the first
##   line, named after the credit's words, and ERROR lines for the one holding the licence's
##   URI) and an export ships those, not the table.
## - SkyRig.star_image(path) -> Image: 4096 x 2048, FORMAT_RGBE9995, no mipmaps; a star at
##   (ra, dec) adds 10^(-0.4 V) to the red, green and blue of the texels of row
##   min(floor((90 - dec) / 180 * 2048), 2047), columns c - h to c + h (wrapped), with
##   c = floor(ra / 360 * 4096) mod 4096 and h = floor(0.5 / cos(dec)): about one texel's
##   height wide at any declination. Measured (Forward+, lavapipe): with one texel per star
##   Polaris's texel is 0.001 degrees wide and does not show. The "# " lines and the column
##   header draw nothing: the image holds the table's stars and no other light. Given to
##   SkyRig.create the image is bound to the sky shader's night_sky.
## - The sky shader samples night_sky at the celestial coordinates of EYEDIR (u = right
##   ascension / 360, v = (90 - declination) / 180), never at SKY_COORDS, through
##   `uniform mat3 celestial_basis`; rig.apply sets it to the Basis that turns a scene
##   direction into celestial coordinates (x towards RA 0 on the equator, y towards RA 90,
##   z the north celestial pole) for the frame, the latitude and the local sidereal time.
##   So the celestial pole stands at the latitude's elevation in the north at any sidereal
##   time, and Polaris where its hour angle puts it, always within 1 degree of the latitude:
##   it is 0.74 degrees from the pole (ICRS), so m4-design §6's "+-0.5 degrees at any time"
##   cannot hold for Polaris itself and is pinned for the pole. A star at RA 0, Dec 0
##   crosses the meridian in the south at LST 0 and sets in the west at LST 90.
## The frame is turned off every axis, as in test_m4_05_sky_rig.gd.
##
## Does NOT prove: that the stars render where the basis says (the shader's uv is read as
## text here; the brief's Forward+ probe looked), their look or brightness on screen, that
## the credit's words satisfy the licence (a reading, not a test), the credit in the game
## (brief v0.4.0-08), or where the sky of a given date has the stars (the positions are
## ICRS, epoch J1991.25, not precessed: 0.13 to 0.35 degrees from 2023-09-06's mean places).

const STARS := "res://sky/stars.csv"
const STARS_SHA256 := "e2a98eea26d486805cc340e648f79235cedf6274a6d39d02712c908f72487d3f"
const STARS_BYTES := 112045
const STARS_COUNT := 5044
## The table's first lines: the credit and the label of its changes (CC BY-NC 3.0 IGO sections
## 3(b) and 4(c)), then the column header.
const HEADER: Array[String] = [
	(
		"# Stars derived from the Hipparcos Catalogue (ESA 1997, ESA SP-1200): stars to V 6.0,"
		+ " positions rounded and reformatted. Credit: ESA. CC BY-NC 3.0 IGO,"
		+ " https://creativecommons.org/licenses/by-nc/3.0/igo/"
	),
	(
		"# Changes made: from CDS I/239 hip_main.dat (53316318 bytes, SHA-256"
		+ " 58ceabb104d647160d9437ce6e513a02a036bb4ad9f8879a5a22fd52943616e0), the records with"
		+ " Vmag <= 6.0; right ascension and declination (ICRS, epoch J1991.25, not precessed)"
		+ " converted from h m s and d m s to degrees, rounded to 4 decimals; Vmag as given; all"
		+ " other fields dropped; sorted by V, right ascension, declination."
	),
	(
		"# ESA's licence and credit for the catalogue:"
		+ " https://www.cosmos.esa.int/web/hipparcos/catalogues"
	),
	"ra_deg,dec_deg,vmag",
]
const KEEP_IMPORT := '[remap]\n\nimporter="keep"\n'
const SHADER_PATH := "res://shaders/sky_physical.gdshader"
const WIDTH := 4096
const HEIGHT := 2048
const LAT := 46.02
const SIRIUS := [101.2885, -16.7131, -1.44]
const VEGA := [279.2341, 38.7830, 0.03]
const POLARIS := [37.9462, 89.2641, 1.97]

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
	assert_eq(lines.size(), HEADER.size() + STARS_COUNT, "four header lines and 5044 stars")
	for i in HEADER.size():
		assert_eq(lines[i] if i < lines.size() else "", HEADER[i], "header line %d" % (i + 1))
	assert_eq(
		lines[HEADER.size()] if lines.size() > HEADER.size() else "",
		"101.2885,-16.7131,-1.44",
		"Sirius first"
	)
	assert_true(lines.has("279.2341,38.7830,0.03"), "Vega")
	assert_true(lines.has("37.9462,89.2641,1.97"), "Polaris")
	assert_eq(FileAccess.get_file_as_string(STARS + ".import"), KEEP_IMPORT, "kept, not translated")
	var beside := Array(DirAccess.get_files_at("res://sky"))
	beside.sort()
	assert_eq(beside, ["stars.csv", "stars.csv.import"], "no translation imported beside it")


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
	assert_almost_eq(top, pow(10.0, 0.4 * 1.44), 0.02, "Sirius: 10^(0.4 * 1.44)")
	var vega_value := values[vega.y * WIDTH + vega.x]
	assert_almost_eq(vega_value, pow(10.0, -0.4 * 0.03), 0.01, "Vega: 10^(-0.4 * 0.03)")
	assert_lt(near_vega, vega_value, "Vega the brightest within 40 texels (3.5 degrees)")
	var c := _image.get_pixel(sirius.x, sirius.y)
	assert_almost_eq(c.g, c.r, 0.0001, "white: green")
	assert_almost_eq(c.b, c.r, 0.0001, "white: blue")
	var polaris := _texel(POLARIS)
	assert_almost_eq(
		_image.get_pixel(polaris.x, polaris.y).r, pow(10.0, -0.4 * 1.97), 0.002, "Polaris"
	)


func test_a_star_near_the_pole_spans_its_row() -> void:
	assert_not_null(_image, "the image is made")
	if _image == null:
		return
	var polaris := _texel(POLARIS)
	var flux := pow(10.0, -0.4 * 1.97)
	var half := 38  # floor(0.5 / cos(89.2641 degrees)) = floor(38.93)
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


func test_the_header_lines_draw_no_star() -> void:
	assert_not_null(_image, "the image is made")
	if _image == null:
		return
	var want := 0.0
	var stars := 0
	for line in FileAccess.get_file_as_string(STARS).split("\n", false):
		if line.begins_with("# ") or line == HEADER[HEADER.size() - 1]:
			continue
		var field := line.split(",")
		var half := int(floor(0.5 / cos(deg_to_rad(float(field[1])))))
		want += pow(10.0, -0.4 * float(field[2])) * (2 * half + 1)
		stars += 1
	assert_eq(stars, STARS_COUNT, "the table's stars, read past its header")
	var flux := _image.duplicate() as Image
	flux.convert(Image.FORMAT_RF)
	var total := 0.0
	for v in flux.get_data().to_float32_array():
		total += v
	assert_almost_eq(total, want, want * 0.002, "the image's light is the stars' alone")


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
