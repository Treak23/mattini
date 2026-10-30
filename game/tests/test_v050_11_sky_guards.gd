extends GutTest
## Pinning tests for brief v0.5.0-11 (0.4.0's whole-range review residue, docs/reviews/
## v0.4.0-round1.md: S-02, S-05, CD-3, AZ-360; the owner's "question A OK" of 2026-10-29): the sky
## and star guards. Tests and words only, but for one guard.
##
## Pinned decisions:
## - S-02: main.gd's placeholder sun, FALLBACK_SUN_AZIMUTH_GRID_DEG and
##   FALLBACK_SUN_ELEVATION_DEG, is config/shadows.json's flight sun (sun.azimuth_grid_deg and
##   sun.elevation_deg), number for number. main.gd still reads no config: the two are a hand copy
##   and this test is what holds them equal.
## - S-05: SkyRig.star_image refuses a line whose right ascension is not in [0, 360) degrees, or
##   whose declination is not strictly between -90 and 90 degrees (NaN and the infinities among
##   them), before it draws anything: null and one push_error naming the file, "line <n>:" and
##   "right ascension" or "declination". At a declination of 90 degrees the run of texels
##   (floor(0.5 / cos(dec)) either side) is about 8e15 wide and the loop never ends; beyond 90 it
##   is negative and the star vanishes. Inside the range nothing changes: the image of
##   res://sky/stars.csv keeps its bytes (SHA-256 of Image.get_data(), 4096 x 2048
##   FORMAT_RGBE9995, 7204 texels lit), measured by the pin author with this test's HashingContext
##   and a second way, a Python re-implementation with Godot's RGBE9995 packing.
## - CD-3: the sky shader's night_sky sampler is declared with repeat_enable (beside
##   filter_linear, source_color and hint_default_black), so the linear filter wraps across right
##   ascension 0/360 instead of clamping a one-texel seam there; a 'mattini:' comment directly
##   above it says so and that the wrap across the poles (v) is harmless.
## - AZ-360: SkyClock.sun's and SkyClock.moon's doc comments say that the azimuth, a double in
##   [0, 360), can read 360.0 once stored in the float32 Vector2 or Vector3, and that 360.0 means
##   north. The engine fact itself is held here: a double within 1e-6 degrees below 360 is 360.0
##   in a Vector2's and a Vector3's x.
##
## Does NOT prove: that the placeholder sun is the right sun (config/shadows.json is design's);
## that the stars are drawn where they belong (test_m4_05_stars.gd) or that a line with another
## problem (a magnitude) is refused; that the seam is gone on screen (no render reads the night
## sky; the census reads the shader's text, lesson 5); that the comments mean what they say (their
## text is read).

const SHADOWS_CONFIG := "config/shadows.json"
const MAIN_PATH := "res://scripts/main.gd"
const CLOCK_PATH := "res://scripts/sky/sky_clock.gd"
const SHADER_PATH := "res://shaders/sky_physical.gdshader"
const STARS := "res://sky/stars.csv"
const STAR_IMAGE_SHA256 := "37dcea6f33dd492452bcc2913e1ab4c83e9bf806ddc00560f10e1d85a1faa3c6"
const STAR_IMAGE_TEXELS := 7204
const SCRATCH_DIR := "user://test_v050_11_sky_guards"
## A table's first lines: a header line, the column header and Sirius, then the case.
const TABLE_HEAD := "# a test table\nra_deg,dec_deg,vmag\n101.2885,-16.7131,-1.44\n"

var _cases := 0


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


## A star table holding [param text]; returns its path.
func _table(text: String) -> String:
	_cases += 1
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("case_%d.csv" % _cases)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()
	return path


## The read was refused: a null image, and exactly one error, a push_error naming [param path]
## and saying each of [param needles]. Every error is handled, so the next case starts clean.
func _assert_refused_once(image: Image, path: String, why: String, needles: Array) -> void:
	assert_null(image, "%s: a null image" % why)
	var pushed := 0
	var others := []
	for error in get_errors():
		if error.handled:
			continue
		var named: bool = error.is_push_error() and error.contains_text(path)
		for needle: String in needles:
			named = named and error.contains_text(needle)
		if named:
			pushed += 1
		else:
			others.append("%s %s" % [error.code, error.rationale])
		error.handled = true
	assert_eq(pushed, 1, "%s: one push_error names %s and says %s" % [why, path, needles])
	assert_eq(others, [], "%s: no other error, no SCRIPT ERROR" % why)


## The line [param line] of a table is accepted: an image and no error.
func _assert_accepted(line: String, why: String) -> void:
	var path := _table(TABLE_HEAD + line + "\n")
	assert_not_null(SkyRig.star_image(path), "%s: accepted" % why)
	var errors := []
	for error in get_errors():
		if not error.handled:
			errors.append(error.rationale)
			error.handled = true
	assert_eq(errors, [], "%s: no error" % why)


## The doc comment (the "##" lines) directly above the line starting with [param head].
func _doc_comment(source: String, head: String) -> String:
	var lines := source.split("\n")
	var at := -1
	for i in lines.size():
		if lines[i].begins_with(head):
			at = i
			break
	assert_gt(at, -1, "%s is in the source" % head)
	var doc := []
	var i := at - 1
	while i >= 0 and lines[i].begins_with("##"):
		doc.push_front(lines[i])
		i -= 1
	return "\n".join(doc)


func test_the_placeholder_sun_is_the_flight_sun_of_config_shadows_json() -> void:
	var json := JSON.new()
	var text := FileAccess.get_file_as_string(_repo_file(SHADOWS_CONFIG))
	assert_eq(json.parse(text), OK, "config/shadows.json parses")
	var sun: Variant = json.data.get("sun") if json.data is Dictionary else null
	assert_true(sun is Dictionary, "config/shadows.json holds a sun object")
	if not sun is Dictionary:
		return
	var constants: Dictionary = load(MAIN_PATH).get_script_constant_map()
	var azimuth: Variant = constants.get("FALLBACK_SUN_AZIMUTH_GRID_DEG")
	var elevation: Variant = constants.get("FALLBACK_SUN_ELEVATION_DEG")
	assert_eq(typeof(azimuth), TYPE_FLOAT, "main.gd's FALLBACK_SUN_AZIMUTH_GRID_DEG is a float")
	assert_eq(typeof(elevation), TYPE_FLOAT, "main.gd's FALLBACK_SUN_ELEVATION_DEG is a float")
	assert_eq(azimuth, sun.get("azimuth_grid_deg"), "the placeholder's grid azimuth is the file's")
	assert_eq(elevation, sun.get("elevation_deg"), "the placeholder's elevation is the file's")


func test_the_star_image_keeps_its_bytes() -> void:
	var image := SkyRig.star_image(STARS)
	assert_not_null(image, "the image is made")
	if image == null:
		return
	assert_eq(image.get_size(), Vector2i(4096, 2048), "4096 x 2048")
	assert_eq(image.get_format(), Image.FORMAT_RGBE9995, "RGBE9995")
	var data := image.get_data()
	var hashing := HashingContext.new()
	hashing.start(HashingContext.HASH_SHA256)
	hashing.update(data)
	assert_eq(hashing.finish().hex_encode(), STAR_IMAGE_SHA256, "the image's bytes, as before")
	var lit := 0
	for texel in data.to_int32_array():
		if texel != 0:
			lit += 1
	assert_eq(lit, STAR_IMAGE_TEXELS, "the texels the stars light")
	assert_eq(get_errors().size(), 0, "and nothing is printed")


func test_a_right_ascension_outside_0_to_360_is_refused_naming_the_line() -> void:
	for ra: String in ["360.0", "360", "360.0001", "400.5", "-0.0001", "-10", "1e400", "-1e400"]:
		var line := "%s,12.5,3.20" % ra
		var path := _table(TABLE_HEAD + line + "\n")
		var why := "right ascension %s" % ra
		_assert_refused_once(SkyRig.star_image(path), path, why, ["line 4:", "right ascension"])
	for ra: String in ["0.0", "0", "359.9999", "180.25"]:
		_assert_accepted("%s,12.5,3.20" % ra, "right ascension %s" % ra)


func test_a_declination_beyond_a_pole_is_refused_naming_the_line() -> void:
	# Beyond 90 degrees the run of texels is negative: the star vanished without a word.
	for dec: String in ["90.5", "-90.5", "120", "-180", "270"]:
		var line := "37.9462,%s,1.97" % dec
		var path := _table(TABLE_HEAD + "279.2341,38.7830,0.03\n" + line + "\n")
		var why := "declination %s" % dec
		_assert_refused_once(SkyRig.star_image(path), path, why, ["line 5:", "declination"])
	for dec: String in ["89.9", "-89.9", "89.2641", "0", "-16.7131"]:
		_assert_accepted("37.9462,%s,1.97" % dec, "declination %s" % dec)


func test_a_declination_at_a_pole_or_infinite_is_refused_before_it_draws() -> void:
	# At 90 degrees the run is about 8e15 texels: without the guard star_image never returns.
	# So the guard is first seen to refuse 90.5, and only then is 90 itself given.
	var probe := _table(TABLE_HEAD + "37.9462,90.5,1.97\n")
	var refused := SkyRig.star_image(probe) == null
	for error in get_errors():
		error.handled = true
	if not refused:
		fail_test("the declination guard is absent (90.5 accepted): 90 itself would hang the run")
		return
	for dec: String in ["90", "90.0", "-90", "-90.0", "1e400", "-1e400"]:
		var line := "37.9462,%s,1.97" % dec
		var path := _table(TABLE_HEAD + line + "\n")
		var why := "declination %s" % dec
		_assert_refused_once(SkyRig.star_image(path), path, why, ["line 4:", "declination"])


func test_the_night_sky_wraps_across_right_ascension_0_to_360() -> void:
	var shader: Shader = load(SHADER_PATH)
	var lines := shader.code.split("\n")
	var at := -1
	for i in lines.size():
		if lines[i].begins_with("uniform sampler2D night_sky"):
			at = i
	assert_gt(at, -1, "the shader declares night_sky")
	if at < 0:
		return
	var declaration := lines[at]
	assert_true(declaration.contains("repeat_enable"), "night_sky repeats: %s" % declaration)
	for hint in ["filter_linear", "source_color", "hint_default_black"]:
		assert_true(declaration.contains(hint), "night_sky keeps %s: %s" % [hint, declaration])
	var comment := []
	var i := at - 1
	while i >= 0 and lines[i].begins_with("// mattini:"):
		comment.push_front(lines[i])
		i -= 1
	var said := "\n".join(comment)
	assert_true(said.contains("repeat_enable"), "a 'mattini:' comment above it names repeat_enable")
	assert_true(said.contains("360"), "it names the seam at right ascension 0/360")
	assert_true(said.contains("pole"), "it says what the wrap does at the poles")


func test_the_sun_and_moon_say_their_azimuth_can_read_360() -> void:
	var near := fposmod(-0.000001, 360.0)
	assert_lt(near, 360.0, "the double is below 360")
	assert_eq(Vector2(near, 0.0).x, 360.0, "a Vector2 (float32) holds it as 360.0")
	assert_eq(Vector3(near, 0.0, 0.0).x, 360.0, "a Vector3 (float32) holds it as 360.0")
	var source: String = load(CLOCK_PATH).source_code
	for head in ["static func sun(", "static func moon("]:
		var doc := _doc_comment(source, head)
		for word in ["float32", "360.0", "north"]:
			assert_true(doc.contains(word), "the doc comment of %s names %s" % [head, word])
