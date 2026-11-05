extends GutTest
## Gaps in the pinned tests of brief v0.6.0-08 that mutation probes found (lesson 51, decision
## 15): guards and branches of SurroundingsGrid and SurroundingsLoader that no pinned test fails
## without. Each test here fails when the guard it names is removed or loosened, and covers the
## class of its finding (lesson 9), not the one site a prover named.
##
## Every refusal is read through _read, which returns the problem without a push_error (every
## reader's shape), so this script prints no ERROR line but the two Godot's JPEG loader prints for
## an undecodable colour (two scoped entries of tools/gate_allowlist.txt).
##
## Fixer round 1 (from "The batch gate's mutation prover's findings" on): the cut's containment on
## all four sides; the colour's fit tolerance; each axis at 16384 pixels and one past; the smallest
## grid and colour; every character of each digest; every proper rotation of the axes; each value
## of the world given; the decoded size and format; the one material across many chunks.
## Fixer round 2 (a second prover and sweeps of every guard, comparison and literal): the NaN
## layout against its mirrors; the order of the refusals; each text, box, count, path and number
## of the block with a value of the wrong type or infinite, and a key renamed; the wording of a
## missing manifest, a missing file and an undecodable colour; the chunks past a whole chunk; the
## skirt where the cut touches the box, its triangles covering their quad. The public tests are at
## gdlint's limit of 20 (after_each counts), so a new check is a private _check_... that one calls.
##
## Does NOT prove: that the guards the pins and this file leave out are not needed (lesson 4);
## the loader's skirt facing, its normals' direction and which diagonal splits a square (brief
## decisions 4 and 8 leave them to the builder, and the skirt is double-sided; the skirt's two
## triangles are only held to cover their quad); that anything is drawn, or drawn right (no GPU;
## the owner's PC).

const SCRATCH_DIR := "user://test_v060_08_gaps"
const FIXTURE_DIR := "tests/shared/surroundings_fixture/generated"
const F32 := "surroundings/fixture.f32"
const JPG := "surroundings/fixture_colour.jpg"
const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"
## A cut off the middle of the fixture's grid on both axes: E 2615000 to 2620000 holds the columns
## 1 and 2 of 0 to 5, N 1103000 to 1109000 the rows 1 and 2 of 0 to 6, so neither the cut nor its
## NaN is symmetric east-west or north-south (the fixture's own is, both ways).
const OFF_CENTRE_CUT := {
	"e_min": 2615000.0, "e_max": 2620000.0, "n_min": 1103000.0, "n_max": 1109000.0
}

## A 15 × 18 JPEG of ONE component (grayscale), made once with Pillow (Image.new("L", (15, 18)),
## pixel (x, y) = 40 + 7x + 5y, saved with quality 92) and kept here as base64: Godot 4.6.3 writes
## three components even from an L8 image (measured: its JPEG decodes as RGB8), so a decoded
## image that is not RGB8 needs this file. Godot decodes it as L8, which the test asserts first.
const GRAY_JPEG_BASE64 := [
	"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8M",
	"CgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/wAALCAASAA8BAREA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAEC",
	"AwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAk",
	"M2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJ",
	"ipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3",
	"+Pn6/9oACAEBAAA/APBPh/4R/wBX+69O1fSfgTwj+6X91/D6Vy/w/wDCP+r/AHXp2r6T8CeEf3S/uv4fSvNP",
	"h+ifu/kXt2r6T8CInlL8i/d9K//Z",
]

var _cases := 0
var _built: Array[Node] = []


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _manifest_path() -> String:
	return _repo_file(FIXTURE_DIR.path_join("manifest.json"))


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _fixture_bytes(rel: String) -> PackedByteArray:
	return FileAccess.get_file_as_bytes(_repo_file(FIXTURE_DIR.path_join(rel)))


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


func after_each() -> void:
	ReleaseBuild.set_exported_for_tests(null)
	for node in _built:
		if is_instance_valid(node):
			node.free()
	_built.clear()
	# The scratch folder goes after each test (not after_all: the public methods are at gdlint's
	# limit of 20, see the header).
	if DirAccess.dir_exists_absolute(SCRATCH_DIR):
		_remove_tree(SCRATCH_DIR)


## Marks every tracked engine error or warning of this test whose text holds one of
## [param texts] as handled (GUT fails a test for an error nobody handled); returns how many.
func _handle_errors(texts: Array) -> int:
	var handled := 0
	for error in get_errors():
		for text: String in texts:
			if not error.handled and error.contains_text(text):
				error.handled = true
				handled += 1
	return handled


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## Writes a copy of the fixture's generated folder whose manifest is changed by [param change]
## and whose heights and colour files are [param f32] and [param jpg] (null leaves a file out;
## an empty array keeps the fixture's); returns the manifest's path.
func _write_case(
	change: Callable, f32: Variant = PackedByteArray(), jpg: Variant = PackedByteArray()
) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("surroundings"))
	var manifest := _parse(_manifest_path())
	change.call(manifest)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	for pair in [[F32, f32], [JPG, jpg]]:
		if pair[1] == null:
			continue
		var bytes: PackedByteArray = pair[1] if not pair[1].is_empty() else _fixture_bytes(pair[0])
		var file := FileAccess.open(dir.path_join(pair[0]), FileAccess.WRITE)
		file.store_buffer(bytes)
		file.close()
	return dir.path_join("manifest.json")


func _unchanged() -> Callable:
	return func(_m: Dictionary) -> void: pass


func _set_key(key: String, value: Variant) -> Callable:
	return _set_in([key], value)


## Sets the value at [param path] (keys below the surroundings block) to [param value].
func _set_in(path: Array, value: Variant) -> Callable:
	return func(m: Dictionary) -> void:
		var node: Dictionary = m["surroundings"]
		for key in path.slice(0, path.size() - 1):
			node = node[key]
		node[path[path.size() - 1]] = value


## Removes the key at [param path] (keys below the surroundings block).
func _erase_in(path: Array) -> Callable:
	return func(m: Dictionary) -> void:
		var node: Dictionary = m["surroundings"]
		for key in path.slice(0, path.size() - 1):
			node = node[key]
		node.erase(path[path.size() - 1])


## What SurroundingsGrid says is wrong with the case written from [param change], "" when
## nothing is.
func _problem(
	change: Callable, f32: Variant = PackedByteArray(), jpg: Variant = PackedByteArray()
) -> String:
	var path := _write_case(change, f32, jpg)
	return SurroundingsGrid.new()._read(path, WorldConfig.from_manifest(path))


## The case is refused with a problem holding [param needle].
func _assert_refused(change: Callable, why: String, needle: String) -> void:
	var problem := _problem(change)
	assert_false(problem.is_empty(), "%s is refused" % why)
	assert_string_contains(problem, needle, true)


func test_the_fixture_has_no_problem() -> void:
	assert_eq(_problem(_unchanged()), "", "the pinned fixture reads clean through _read")


func test_no_world_config_a_missing_manifest_and_a_manifest_that_is_not_an_object() -> void:
	var path := _write_case(_unchanged())
	assert_string_contains(SurroundingsGrid.new()._read(path, null), "WorldConfig")
	var world := WorldConfig.from_manifest(path)
	var missing := SCRATCH_DIR.path_join("no_such_manifest.json")
	var unreadable := SurroundingsGrid.new()._read(missing, world)
	assert_string_contains(unreadable, "cannot read the manifest")
	assert_false(unreadable.contains("empty"), "a missing manifest is not an empty one")
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var empty_path := SCRATCH_DIR.path_join("empty.json")
	FileAccess.open(empty_path, FileAccess.WRITE).close()
	var empty := SurroundingsGrid.new()._read(empty_path, world)
	assert_string_contains(empty, "the manifest is empty")
	assert_false(
		empty.contains("cannot read"), "an empty manifest is read, not unreadable: %s" % empty
	)
	for pair in [
		["not_json.json", "{ not json", "not valid JSON"],
		["array.json", "[1, 2]", "not a JSON object"]
	]:
		var bad := SCRATCH_DIR.path_join(pair[0])
		var file := FileAccess.open(bad, FileAccess.WRITE)
		file.store_string(pair[1])
		file.close()
		assert_string_contains(SurroundingsGrid.new()._read(bad, world), pair[2])


func test_a_manifest_without_a_world_block_or_a_block_that_is_not_an_object_is_refused() -> void:
	var path := _write_case(_unchanged())
	var world := WorldConfig.from_manifest(path)
	var no_world := _write_case(func(m: Dictionary) -> void: m.erase("world"))
	assert_string_contains(SurroundingsGrid.new()._read(no_world, world), "no world block")
	var origin_gone := _write_case(func(m: Dictionary) -> void: m["world"].erase("origin_lv95"))
	assert_string_contains(SurroundingsGrid.new()._read(origin_gone, world), "no world block")
	var not_object := _write_case(func(m: Dictionary) -> void: m["surroundings"] = 5.0)
	assert_string_contains(SurroundingsGrid.new()._read(not_object, world), "must be an object")
	# A block with no world_sha256 at all is a block for another world, not a runtime error.
	var no_hash := _write_case(_erase_in(["world_sha256"]))
	assert_string_contains(SurroundingsGrid.new()._read(no_hash, world), "another world config")


func test_the_axes_refusal_is_this_reader_s_own() -> void:
	var rotate := func(m: Dictionary) -> void:
		m["world"]["axes"] = {"x": "+n", "y": "+h", "z": "+e"}
	var problem := _problem(rotate)
	assert_string_contains(problem, "axes")
	assert_string_contains(problem, "surroundings")
	assert_false(
		problem.contains("photo"), "the photo's wording is not this reader's: %s" % problem
	)


func test_the_heights_fields_are_each_refused() -> void:
	var cases := {
		"an empty area": [_set_key("area", ""), "area"],
		"a number for the area": [_set_key("area", 5.0), "area"],
		"one column": [_set_key("columns", 1.0), "at least 2"],
		"half a column": [_set_key("columns", 6.5), "whole number"],
		"one row": [_set_key("rows", 1.0), "at least 2"],
		"a spacing of 0": [_set_key("spacing_m", 0.0), "positive finite"],
		"a negative spacing": [_set_key("spacing_m", -3000.0), "positive finite"],
		"a short sha256": [_set_key("sha256", "abc"), "64 hex digits"],
		"a sha256 with a minus": [_set_key("sha256", "-" + "a".repeat(63)), "64 hex digits"],
		"a numeric sha256": [_set_key("sha256", 5.0), "64 hex digits"],
		"a box missing a side": [_erase_in(["lv95_box", "n_min"]), "lv95_box"],
		"a box side that is text": [_set_in(["lv95_box", "e_max"], "x"), "finite number"],
		"a cut with a key too many": [_set_in(["cut_box", "z"], 1.0), "cut_box"],
		"a cut side that is text": [_set_in(["cut_box", "n_max"], "x"), "finite number"],
		"a cut past the west edge":
		[_set_in(["cut_box", "e_min"], 2612000.0), "does not lie inside"],
		"a cut past the south edge":
		[_set_in(["cut_box", "n_min"], 1091000.0), "does not lie inside"],
		"a cut past the north edge":
		[_set_in(["cut_box", "n_max"], 1111000.0), "does not lie inside"],
		"a source missing its sha": [_erase_in(["source", "entry_sha256"]), "source"],
		"an empty source text": [_set_in(["source", "attribution"], ""), "must be text"],
		"a source that is not an object": [_set_key("source", "x"), "source"],
		"a text column count": [_set_key("columns", "6"), "whole number"],
		"a null row count": [_set_key("rows", null), "whole number"],
		"a box that is a number": [_set_key("lv95_box", 5.0), "lv95_box"],
		"a box that is null": [_set_key("lv95_box", null), "lv95_box"],
		"a cut that is text": [_set_key("cut_box", "x"), "cut_box"],
		"a cut that is an array": [_set_key("cut_box", [1.0, 2.0]), "cut_box"],
	}
	for why: String in cases:
		_assert_refused(cases[why][0], why, cases[why][1])
	_check_every_text_is_text("source", ["attribution", "collection", "edition", "entry_sha256"])
	_check_a_renamed_key_is_refused()
	var infinite := {"spacing_m": [["spacing_m"], "positive finite"]}
	for box: String in ["lv95_box", "cut_box"]:
		for side: String in ["e_max", "e_min", "n_max", "n_min"]:
			infinite["%s.%s" % [box, side]] = [[box, side], "finite number"]
	_check_infinite_numbers_are_refused(infinite)


## Each of [param keys] of the text block [param container] (source or colour_source) refused
## when it is empty, a number or null, naming it: the check is one loop over the keys, and a type
## check before the emptiness one, and either can go unseen with a key or a type left out.
func _check_every_text_is_text(container: String, keys: Array) -> void:
	for key: String in keys:
		for bad: Variant in ["", 5.0, null]:
			var why := "surroundings.%s.%s as %s" % [container, key, var_to_str(bad)]
			var says := "%s.%s must be text" % [container, key]
			_assert_refused(_set_in([container, key], bad), why, says)


## Renames the key [param old] of the object at [param path] (keys below the block) to [param new]:
## as many keys as there should be, one of them not the right one.
func _rename_in(path: Array, old: String, new: String) -> Callable:
	return func(m: Dictionary) -> void:
		var node: Dictionary = m["surroundings"]
		for key in path:
			node = node[key]
		node[new] = node[old]
		node.erase(old)


func _check_a_renamed_key_is_refused() -> void:
	var cases := {
		"the block": [[], "filled_fraction", "surroundings must hold exactly"],
		"the heights' source":
		[["source"], "entry_sha256", "surroundings.source must hold exactly"],
		"the colour's source":
		[["colour_source"], "edition", "surroundings.colour_source must hold exactly"],
		"the box": [["lv95_box"], "n_min", "surroundings.lv95_box must hold exactly"],
		"the cut": [["cut_box"], "e_max", "surroundings.cut_box must hold exactly"],
	}
	for why: String in cases:
		var spec: Array = cases[why]
		var change := _rename_in(spec[0], spec[1], spec[1] + "_x")
		_assert_refused(change, "%s with %s renamed" % [why, spec[1]], spec[2])


## Each value of [param cases] (why: [path below the block, needle]) made infinite, both signs
## (JSON.stringify writes INF as 1e99999, and Godot reads it back as infinity with a warning).
func _check_infinite_numbers_are_refused(cases: Dictionary) -> void:
	for why: String in cases:
		for infinity: float in [INF, -INF]:
			_assert_refused(
				_set_in(cases[why][0], infinity), "%s as %s" % [why, infinity], cases[why][1]
			)
			_handle_errors(["Exponent too high"])


func test_the_colour_fields_are_each_refused() -> void:
	var cases := {
		"a negative colour cell": [_set_key("colour_cell_m", -1000.0), "positive finite"],
		"no colour columns": [_set_key("colour_columns", 0.0), "at least 1"],
		"half a colour column": [_set_key("colour_columns", 14.5), "whole number"],
		"no colour rows": [_set_key("colour_rows", 0.0), "at least 1"],
		"a text count": [_set_key("colour_rows", "18"), "colour_rows"],
		"a short colour digest": [_set_key("colour_sha256", "abc"), "64 hex digits"],
		"a short pixels digest": [_set_key("colour_pixels_sha256", "abc"), "64 hex digits"],
		"a colour digest with a minus":
		[_set_key("colour_sha256", "-" + "a".repeat(63)), "64 hex digits"],
		"a colour source missing a key": [_erase_in(["colour_source", "edition"]), "colour_source"],
		"an empty colour source text":
		[_set_in(["colour_source", "attribution"], ""), "must be text"],
		"a colour source that is not an object": [_set_key("colour_source", 5.0), "colour_source"],
		"a negative share": [_set_key("filled_fraction", -0.1), "from 0 to 1"],
		"a colour cell of 0": [_set_key("colour_cell_m", 0.0), "positive finite"],
		"a null colour column count": [_set_key("colour_columns", null), "colour_columns"],
	}
	for why: String in cases:
		_assert_refused(cases[why][0], why, cases[why][1])
	_check_every_text_is_text("colour_source", ["attribution", "collection", "edition"])
	_check_infinite_numbers_are_refused(
		{
			"colour_cell_m": [["colour_cell_m"], "positive finite"],
			"filled_fraction": [["filled_fraction"], "from 0 to 1"],
		}
	)


func test_the_edge_values_of_the_fields_are_read() -> void:
	assert_eq(_problem(_set_key("filled_fraction", 0.0)), "", "no placeholder pixel")
	assert_eq(_problem(_set_key("filled_fraction", 1.0)), "", "only placeholder pixels")
	var capitals := func(m: Dictionary) -> void:
		m["surroundings"]["sha256"] = m["surroundings"]["sha256"].to_upper()
		m["surroundings"]["colour_sha256"] = m["surroundings"]["colour_sha256"].to_upper()
	assert_eq(_problem(capitals), "", "both files' SHA-256 are compared in lower case")
	# A grid of 0.5 m (a box of 7.5 × 9 m: 16 × 19 vertices) and a colour of 0.5 m pixels: any
	# positive spacing and cell is read, not only those from 1 m.
	assert_eq(_read_path(_box_case(16, 19, 0.5, 15, 18, 0.5)), "", "a grid and a colour of 0.5 m")


func test_a_path_that_is_not_plain_is_refused_for_both_files() -> void:
	for bad: String in [
		"/a/b.f32", "a\\b.f32", "C:/b.f32", "a:b.f32", "a//b.f32", "./b.f32", "", "a/../b.f32"
	]:
		var problem := _problem(_set_key("file", bad))
		assert_string_contains(problem, "surroundings.file must be a plain relative path")
		problem = _problem(_set_key("colour_file", bad.replace("f32", "jpg")))
		assert_string_contains(problem, "surroundings.colour_file must be a plain relative path")
	# A path that is no text at all is refused as one, not a runtime error.
	for bad: Variant in [5.0, null, ["a.f32"], true]:
		for key: String in ["file", "colour_file"]:
			var problem := _problem(_set_key(key, bad))
			assert_string_contains(problem, "surroundings.%s must be a plain relative path" % key)
	assert_eq(_problem(_unchanged()), "", "a plain path is read")


## Every refusal about a file of the fixture folder: why -> [manifest change, heights file, colour
## file (an empty array keeps the fixture's, null leaves it out), the file's path in the folder,
## what the message says right after the path].
func _file_refusals() -> Dictionary:
	var short := _fixture_bytes(F32).slice(0, 164)
	var flipped := _fixture_bytes(F32)
	flipped[20] = flipped[20] ^ 1
	var damaged := _fixture_bytes(JPG)
	damaged[400] = damaged[400] ^ 1
	var small := Image.create(15, 17, false, Image.FORMAT_RGB8).save_jpg_to_buffer(0.92)
	var garbage := PackedByteArray([1, 2, 3, 4, 5, 6, 7, 8])
	var keep := PackedByteArray()
	var short_sha := _set_key("sha256", _sha256(short))
	var garbage_sha := _set_key("colour_sha256", _sha256(garbage))
	var small_sha := _set_key("colour_sha256", _sha256(small))
	return {
		"heights left out": [_unchanged(), null, keep, F32, " is missing"],
		"colour left out": [_unchanged(), keep, null, JPG, " is missing"],
		"heights of another size": [short_sha, short, keep, F32, " holds 164 bytes, not 168"],
		"heights of another SHA-256": [_unchanged(), flipped, keep, F32, " has SHA-256 "],
		"colour of another SHA-256": [_unchanged(), keep, damaged, JPG, " has SHA-256 "],
		"colour that is no JPEG": [garbage_sha, keep, garbage, JPG, " cannot be decoded"],
		"colour of another size": [small_sha, keep, small, JPG, " decodes to 15 × 17 pixels"],
	}


func test_each_file_refusal_names_its_file_and_ends_with_its_hint() -> void:
	var cases := _file_refusals()
	for why: String in cases:
		var spec: Array = cases[why]
		var path := _write_case(spec[0], spec[1], spec[2])
		var world := WorldConfig.from_manifest(path)
		ReleaseBuild.set_exported_for_tests(true)
		var problem := SurroundingsGrid.new()._read(path, world)
		assert_true(problem.ends_with(RELEASE_HINT), "%s, exported: %s" % [why, problem])
		ReleaseBuild.set_exported_for_tests(false)
		problem = SurroundingsGrid.new()._read(path, world)
		var is_heights: bool = spec[3] == F32
		var noun := "the heights file " if is_heights else "the colour "
		var named: String = noun + path.get_base_dir().path_join(spec[3]) + spec[4]
		assert_true(problem.begins_with(named), "%s starts '%s': %s" % [why, named, problem])
		var command := "surroundings" if is_heights else "farcolour"
		var hint := "; python -m mattini %s rebuilds it" % command
		assert_true(problem.ends_with(hint), "%s, not exported: %s" % [why, problem])
	# Godot's JPEG loader prints two ERROR lines for the colour that is no JPEG (the allowlist's).
	_handle_errors(["is true. Returning"])


func test_the_nan_layout_must_be_the_cut_s_not_its_mirror() -> void:
	# The fixture's cut keeps its edge: row 2, column 1 (west), row 1, column 2 (north), row 3,
	# column 4 (east) and row 5, column 2 (south) are finite and lie on cut_box's four edges.
	for at: Vector2i in [Vector2i(1, 2), Vector2i(2, 1), Vector2i(4, 3), Vector2i(2, 5)]:
		var heights := _fixture_bytes(F32).to_float32_array()
		assert_false(is_nan(heights[at.y * 6 + at.x]), "%s is finite in the fixture" % at)
		heights[at.y * 6 + at.x] = NAN
		var holed := heights.to_byte_array()
		var problem := _problem(_set_key("sha256", _sha256(holed)), holed)
		assert_string_contains(problem, "NaN", true)
		assert_string_contains(problem, "row %d, column %d" % [at.y, at.x])
	_check_the_layout_is_the_cut_s_and_not_its_mirror()


## The fixture's grid (6 × 7 vertices of 3000 m: E 2613000 to 2628000, N 1092000 to 1110000)
## with the manifest's cut_box [param cut], and NaN at the vertices strictly inside it, or at
## [param nan_at] (Vector2i column and row) when that is given. The block's SHA-256 is the
## file's, or the fixture's (so stale) when [param stale_sha].
func _cut_case(cut: Dictionary, nan_at: Variant = null, stale_sha: bool = false) -> String:
	var heights := PackedFloat32Array()
	heights.resize(6 * 7)
	for r in 7:
		for c in 6:
			var e := 2613000.0 + c * 3000.0
			var n := 1110000.0 - r * 3000.0
			var hole: bool = e > cut["e_min"] and e < cut["e_max"]
			hole = hole and n > cut["n_min"] and n < cut["n_max"]
			if nan_at != null:
				hole = Vector2i(c, r) in nan_at
			heights[r * 6 + c] = NAN if hole else 1000.0 + r * 6 + c
	var bytes := heights.to_byte_array()
	var change := func(m: Dictionary) -> void:
		m["surroundings"]["cut_box"] = cut
		if not stale_sha:
			m["surroundings"]["sha256"] = _sha256(bytes)
	return _write_case(change, bytes)


func _check_the_layout_is_the_cut_s_and_not_its_mirror() -> void:
	assert_eq(
		_read_path(_cut_case(OFF_CENTRE_CUT)), "", "NaN at columns 1, 2 and rows 1, 2 is read"
	)
	var mirrors := {
		"east-west": [Vector2i(3, 1), Vector2i(4, 1), Vector2i(3, 2), Vector2i(4, 2)],
		"north-south": [Vector2i(1, 4), Vector2i(2, 4), Vector2i(1, 5), Vector2i(2, 5)],
		"both": [Vector2i(3, 4), Vector2i(4, 4), Vector2i(3, 5), Vector2i(4, 5)],
	}
	for why: String in mirrors:
		var problem := _read_path(_cut_case(OFF_CENTRE_CUT, mirrors[why]))
		assert_string_contains(problem, "row 1, column 1 is finite", true)
		assert_string_contains(problem, "inside cut_box", true)


## The fixture with no cut: every height finite, cut_box a point at [param e], [param n] (no
## vertex lies strictly in it), inside the box by default.
func _cutless_manifest(e: float = 2616000.0, n: float = 1100000.0) -> String:
	var heights := _fixture_bytes(F32).to_float32_array()
	for k in heights.size():
		if is_nan(heights[k]):
			heights[k] = 1000.0 + k
	var filled := heights.to_byte_array()
	var change := func(m: Dictionary) -> void:
		m["surroundings"]["sha256"] = _sha256(filled)
		m["surroundings"]["cut_box"] = {"e_max": e, "e_min": e, "n_max": n, "n_min": n}
	return _write_case(change, filled)


func test_a_grid_without_a_cut_is_all_chunk_and_has_no_skirt() -> void:
	var path := _cutless_manifest()
	var world := WorldConfig.from_manifest(path)
	var grid := SurroundingsGrid.from_manifest(path, world)
	assert_not_null(grid, "a grid with no NaN and a cut of no area is read")
	if grid == null:
		return
	var parent := Node3D.new()
	_built.append(parent)
	var root := SurroundingsLoader.create(grid, parent)
	var names := []
	for child in root.get_children():
		names.append(String(child.name))
	assert_eq(names, ["Chunk_0_0"], "one chunk, and no skirt: no edge between drawn and undrawn")
	var chunk := root.get_node("Chunk_0_0") as MeshInstance3D
	var mesh := chunk.mesh as ArrayMesh
	assert_eq(mesh.surface_get_array_index_len(0), 6 * 5 * 6, "5 × 6 squares, two triangles each")
	assert_eq(mesh.surface_get_array_len(0), 6 * 7, "every vertex of the grid, once")


## --- The batch gate's mutation prover's findings (fixer round) ---------------------------------


## The reader's problem for the manifest at [param path], "" when nothing is wrong.
func _read_path(path: String) -> String:
	return SurroundingsGrid.new()._read(path, WorldConfig.from_manifest(path))


func _check_a_cut_past_a_side_is_refused() -> void:
	# 1 m past each of the box's four sides (the box: E 2613000 to 2628000, N 1092000 to 1110000).
	var cases := {
		"west": ["e_min", 2612999.0],
		"east": ["e_max", 2628001.0],
		"south": ["n_min", 1091999.0],
		"north": ["n_max", 1110001.0],
	}
	for side: String in cases:
		var change := _set_in(["cut_box", cases[side][0]], cases[side][1])
		_assert_refused(change, "a cut 1 m past the box's %s side" % side, "does not lie inside")


func _check_a_cut_on_a_side_is_inside() -> void:
	# A cut of no area on each of the four sides in turn (every height finite: nothing lies
	# strictly inside it): the edge of the box is inside the box.
	var cases := {
		"west": [2613000.0, 1100000.0],
		"east": [2628000.0, 1100000.0],
		"south": [2616000.0, 1092000.0],
		"north": [2616000.0, 1110000.0],
	}
	for side: String in cases:
		var path := _cutless_manifest(cases[side][0], cases[side][1])
		assert_eq(_read_path(path), "", "a cut on the box's %s side is read" % side)


func test_the_cut_is_inside_the_box_on_all_four_sides() -> void:
	_check_a_cut_past_a_side_is_refused()
	_check_a_cut_on_a_side_is_inside()


func _check_the_colour_fit_tolerance() -> void:
	# colour_columns × cell is 15 pixels of 1000 m + d each, colour_rows × cell 18 pixels: off the
	# box's sides (15000 m and 18000 m) by 15 d and 18 d.
	for d: float in [0.00003, -0.00003]:
		var problem := _problem(_set_key("colour_cell_m", 1000.0 + d))
		assert_eq(problem, "", "0.5 mm off a side (d = %s) is read, both signs" % d)
	for d: float in [0.0002, -0.0002]:
		var problem := _problem(_set_key("colour_cell_m", 1000.0 + d))
		assert_string_contains(problem, "colour_columns", true)
		assert_string_contains(problem, "does not fit the box's side", true)
	# Columns 0.9 mm off (read), rows 1.08 mm off (refused): the rows' own check, both signs.
	for d: float in [0.00006, -0.00006]:
		var problem := _problem(_set_key("colour_cell_m", 1000.0 + d))
		assert_string_contains(problem, "colour_rows", true)
		assert_string_contains(problem, "does not fit the box's side", true)


## A case whose heights are [param columns] × [param rows] vertices at [param spacing] m from the
## fixture's north-west corner, every one finite, cut_box the box's centre as a point; its colour
## block says [param colour_columns] × [param colour_rows] pixels of [param cell] m, and the
## fixture's JPEG (15 × 18 pixels, its SHA-256 as the block has it) is the file.
func _box_case(
	columns: int,
	rows: int,
	spacing: float,
	colour_columns: int,
	colour_rows: int,
	cell: float = 1.0
) -> String:
	var heights := PackedFloat32Array()
	heights.resize(columns * rows)
	for k in heights.size():
		heights[k] = 1000.0 + k
	var f32 := heights.to_byte_array()
	var e_min := 2613000.0
	var n_max := 1110000.0
	var change := func(m: Dictionary) -> void:
		var block: Dictionary = m["surroundings"]
		block["columns"] = float(columns)
		block["rows"] = float(rows)
		block["spacing_m"] = spacing
		block["lv95_box"] = {
			"e_max": e_min + (columns - 1) * spacing,
			"e_min": e_min,
			"n_max": n_max,
			"n_min": n_max - (rows - 1) * spacing,
		}
		var centre_e := e_min + (columns - 1) * spacing / 2.0
		var centre_n := n_max - (rows - 1) * spacing / 2.0
		block["cut_box"] = {
			"e_max": centre_e, "e_min": centre_e, "n_max": centre_n, "n_min": centre_n
		}
		block["sha256"] = _sha256(f32)
		block["colour_cell_m"] = cell
		block["colour_columns"] = float(colour_columns)
		block["colour_rows"] = float(colour_rows)
	return _write_case(change, f32)


func _check_the_renderer_limit() -> void:
	# Each axis in turn at the renderer's limit, then one pixel past it, the other axis well
	# under (spacing 4096 m: boxes of 12288 and 16384 m; 3277 m: 13108 and 16385 m).
	var at_limit := {
		"both axes": _box_case(5, 5, 4096.0, 16384, 16384),
		"columns": _box_case(5, 4, 4096.0, 16384, 12288),
		"rows": _box_case(4, 5, 4096.0, 12288, 16384),
	}
	for why: String in at_limit:
		var problem := _read_path(at_limit[why])
		assert_string_contains(problem, "decodes to", true)
		assert_false(problem.contains("Compatibility"), "16384 %s is not too wide" % why)
	var past := {
		"columns": [_box_case(6, 5, 3277.0, 16385, 13108), "colour_columns"],
		"rows": [_box_case(5, 6, 3277.0, 13108, 16385), "colour_rows"],
	}
	for why: String in past:
		var problem := _read_path(past[why][0])
		assert_string_contains(problem, past[why][1], true)
		assert_string_contains(problem, "above 16384", true)


func _check_the_smallest_counts() -> void:
	# 2 × 2 vertices (decision 3: "at least 2") and a colour of 1 × 1 pixels ("at least 1"): the
	# counts pass, and only the decoded size of the fixture's JPEG (15 × 18) refuses the case.
	var problem := _read_path(_box_case(2, 2, 3000.0, 1, 1, 3000.0))
	assert_string_contains(problem, "decodes to", true)


func test_the_colour_and_the_grid_are_read_at_the_edges_of_their_limits() -> void:
	_check_the_colour_fit_tolerance()
	_check_the_renderer_limit()
	_check_the_smallest_counts()


func test_a_digest_of_another_shape_is_refused_for_every_digest() -> void:
	var bad := {
		"63 hex digits": "a".repeat(63),
		"65 hex digits": "a".repeat(65),
		"64 characters that are not hex": "g".repeat(64),
		"64 characters with a plus": "+" + "a".repeat(63),
		"64 characters with a minus": "-" + "a".repeat(63),
		"64 characters with a space": "a".repeat(63) + " ",
		"0x and 62 digits": "0x" + "a".repeat(62),
		"64 digits and a newline": "a".repeat(64) + "\n",
		"nothing": "",
	}
	# colour_pixels_sha256 is compared with nothing: this check is its only guard.
	for key: String in ["sha256", "colour_sha256", "colour_pixels_sha256"]:
		for why: String in bad:
			var problem := _problem(_set_key(key, bad[why]))
			var says := "surroundings.%s must be 64 hex digits" % key
			assert_true(problem.contains(says), "%s as %s: %s" % [why, key, problem])


## The 23 proper rotations of the world's axes other than the owner's (x = +e, y = +h, z = −n):
## each game axis reads a signed source axis, the three all different, the signed permutation's
## determinant +1 (WorldConfig refuses the 24 others, with an ERROR line).
func _other_rotations() -> Array:
	var names := ["e", "n", "h"]
	var rotations := []
	for first in 3:
		for second in 3:
			for third in 3:
				if first == second or first == third or second == third:
					continue
				var even := (second - first) * (third - first) * (third - second) > 0
				for signs in 8:
					var signed := [
						1 if signs & 1 == 0 else -1,
						1 if signs & 2 == 0 else -1,
						1 if signs & 4 == 0 else -1,
					]
					if (1 if even else -1) * signed[0] * signed[1] * signed[2] != 1:
						continue
					var axes := {}
					var picked := [first, second, third]
					for axis in 3:
						axes["xyz"[axis]] = (
							("+" if signed[axis] == 1 else "-") + names[picked[axis]]
						)
					if axes != {"x": "+e", "y": "+h", "z": "-n"}:
						rotations.append(axes)
	return rotations


func _check_every_other_rotation_is_refused() -> void:
	var rotations := _other_rotations()
	assert_eq(rotations.size(), 23, "24 proper rotations, the owner's the one left out")
	for axes: Dictionary in rotations:
		var turn := func(m: Dictionary) -> void: m["world"]["axes"] = axes
		_assert_refused(turn, "the world turned to %s" % [axes], "axes")


func _world_change(path: Array, value: Variant) -> Callable:
	return func(m: Dictionary) -> void:
		var node: Dictionary = m["world"]
		for key in path.slice(0, path.size() - 1):
			node = node[key]
		node[path[path.size() - 1]] = value


func _check_each_world_value_is_refused() -> void:
	var cases := {
		"the origin's east": [["origin_lv95", "e"], 2618251.0, "its origin differs"],
		"the origin's north": [["origin_lv95", "n"], 1101751.0, "its origin differs"],
		"the height offset": [["height_offset_m"], 1250.5, "its height offset differs"],
	}
	var path := _write_case(_unchanged())
	for why: String in cases:
		var other := _write_case(_world_change(cases[why][0], cases[why][1]))
		var world := WorldConfig.from_manifest(other)
		var problem := SurroundingsGrid.new()._read(path, world)
		assert_string_contains(problem, cases[why][2], true)
		assert_string_contains(problem, "not read from this manifest", true)
		assert_eq(problem.count("differs"), 1, "%s: one thing differs: %s" % [why, problem])


func test_the_world_given_is_refused_for_any_other_rotation_and_any_one_value() -> void:
	_check_every_other_rotation_is_refused()
	_check_each_world_value_is_refused()


func _rgb_jpeg(width: int, height: int) -> PackedByteArray:
	var image := Image.create(width, height, false, Image.FORMAT_RGB8)
	image.fill(Color8(60, 90, 150))
	return image.save_jpg_to_buffer(0.92)


func test_a_colour_that_decodes_to_another_size_or_format_is_refused() -> void:
	var gray := Marshalls.base64_to_raw("".join(PackedStringArray(GRAY_JPEG_BASE64)))
	var decoded := Image.new()
	assert_eq(decoded.load_jpg_from_buffer(gray), OK, "the grayscale JPEG decodes")
	assert_eq(decoded.get_format(), Image.FORMAT_L8, "to one channel, not RGB8")
	assert_eq(decoded.get_size(), Vector2i(15, 18), "of the block's size")
	var right := _rgb_jpeg(15, 18)
	var control := _problem(_set_key("colour_sha256", _sha256(right)), PackedByteArray(), right)
	assert_eq(control, "", "an RGB8 JPEG of 15 × 18 is read")
	var cases := {
		"a right-sized grayscale": gray,
		"one column short": _rgb_jpeg(14, 18),
		"one row short": _rgb_jpeg(15, 17),
		"turned a quarter": _rgb_jpeg(18, 15),
	}
	for why: String in cases:
		var jpg: PackedByteArray = cases[why]
		var problem := _problem(_set_key("colour_sha256", _sha256(jpg)), PackedByteArray(), jpg)
		assert_true(
			problem.contains("decodes to"), "%s is refused as it decodes: %s" % [why, problem]
		)


func _hand_grid(columns: int, rows: int, cut_from: int, cut_to: int) -> SurroundingsGrid:
	var grid := SurroundingsGrid.new()
	grid.columns = columns
	grid.rows = rows
	grid.spacing_m = 50.0
	grid.x_min = -6000.0
	grid.z_min = -6000.0
	var heights := PackedFloat32Array()
	heights.resize(columns * rows)
	for row in rows:
		for column in columns:
			var in_cut := column >= cut_from and column <= cut_to
			in_cut = in_cut and row >= cut_from and row <= cut_to
			heights[row * columns + column] = NAN if in_cut else 500.0 + column * 0.5 - row * 0.25
	grid.heights = heights
	grid.colour_texture = ImageTexture.create_from_image(
		Image.create(4, 4, false, Image.FORMAT_RGB8)
	)
	return grid


func test_every_chunk_of_a_grid_of_many_chunks_draws_with_the_one_material() -> void:
	# A grid made by hand (no manifest): 241 × 241 vertices at 50 m are nine chunks of 80 × 80
	# squares, the middle one wholly in the cut (vertices 81 to 159), so eight chunk nodes.
	var grid := _hand_grid(241, 241, 81, 159)
	var parent := Node3D.new()
	_built.append(parent)
	var root := SurroundingsLoader.create(grid, parent)
	var chunks: Array[MeshInstance3D] = []
	for child in root.get_children():
		if child is MeshInstance3D and String(child.name).begins_with("Chunk_"):
			chunks.append(child)
	assert_eq(chunks.size(), 8, "eight chunks are drawn")
	if chunks.is_empty():
		return
	var one := chunks[0].get_active_material(0)
	assert_not_null(one, "a chunk has a material")
	for chunk in chunks:
		assert_same(
			chunk.get_active_material(0), one, "%s draws with the one material" % chunk.name
		)
		assert_eq(
			chunk.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_ON, "%s" % chunk.name
		)
		assert_eq(chunk.transform, Transform3D.IDENTITY, "%s is unturned" % chunk.name)
	var skirt := root.get_node_or_null("Skirt") as MeshInstance3D
	assert_not_null(skirt, "the cut has a skirt")
	if skirt == null:
		return
	assert_not_same(skirt.get_active_material(0), one, "the skirt's material is its own")
	assert_eq(skirt.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_OFF, "no skirt shadow")


## --- The second fixer round: the order of the refusals, and the loader's edges ----------------


## Brief decision 3 lists the refusals "in this order": a case wrong in two adjacent ways must be
## refused as the first, and only the first.
func test_the_refusals_come_in_the_brief_s_order() -> void:
	_check_the_heights_file_is_refused_by_size_then_digest_then_layout()
	_check_the_colour_file_is_refused_by_digest_then_decode()
	_check_the_block_and_the_world_are_refused_in_order()


func _check_the_heights_file_is_refused_by_size_then_digest_then_layout() -> void:
	# The block holds the fixture's SHA-256, which is stale for both files below.
	var problem := _problem(_unchanged(), _fixture_bytes(F32).slice(0, 164))
	assert_string_contains(problem, "holds 164 bytes")
	assert_false(problem.contains("has SHA-256"), "the size comes before the digest: %s" % problem)
	var mirror := [Vector2i(3, 1), Vector2i(4, 1), Vector2i(3, 2), Vector2i(4, 2)]
	problem = _read_path(_cut_case(OFF_CENTRE_CUT, mirror, true))
	assert_string_contains(problem, "has SHA-256")
	assert_false(problem.contains("NaN"), "the digest is checked before the layout: %s" % problem)
	problem = _read_path(_cut_case(OFF_CENTRE_CUT, mirror))
	assert_string_contains(problem, "NaN", true)


func _check_the_colour_file_is_refused_by_digest_then_decode() -> void:
	# The block holds the fixture's colour SHA-256, which is stale for both files below.
	var garbage := PackedByteArray([1, 2, 3, 4, 5, 6, 7, 8])
	var cases := {"a file that is no JPEG": garbage, "a JPEG of another size": _rgb_jpeg(14, 18)}
	for why: String in cases:
		var problem := _problem(_unchanged(), PackedByteArray(), cases[why])
		assert_string_contains(problem, "has SHA-256")
		assert_false(problem.contains("decod"), "%s: the digest comes first: %s" % [why, problem])


func _check_the_block_and_the_world_are_refused_in_order() -> void:
	var both := func(m: Dictionary) -> void:
		m["surroundings"]["area"] = ""
		m["surroundings"]["colour_cell_m"] = -1.0
	var problem := _problem(both)
	assert_string_contains(problem, "surroundings.area")
	assert_false(problem.contains("colour_cell_m"), "the heights' fields come first: %s" % problem)
	var flipped := _fixture_bytes(F32)
	flipped[20] = flipped[20] ^ 1
	var damaged := _fixture_bytes(JPG)
	damaged[400] = damaged[400] ^ 1
	problem = _problem(_unchanged(), flipped, damaged)
	assert_string_contains(problem, "the heights file")
	assert_false(problem.contains("the colour"), "the heights' file comes first: %s" % problem)
	# A world given that is not the manifest's, with the block wrong in each way in turn: the
	# missing block, then its world_sha256, are told before the world's own guard, which is
	# told before the key set.
	var other := _write_case(_world_change(["origin_lv95", "e"], 2618251.0))
	var world := WorldConfig.from_manifest(other)
	var cases := {
		"no block": [func(m: Dictionary) -> void: m["surroundings"] = null, "no surroundings"],
		"a block of another world config":
		[_set_key("world_sha256", "a".repeat(64)), "another world config"],
		"a block of another key set": [_erase_in(["colour_file"]), "not read from this manifest"],
	}
	for why: String in cases:
		var path := _write_case(cases[why][0])
		assert_string_contains(SurroundingsGrid.new()._read(path, world), cases[why][1], true)


func test_the_loader_builds_every_chunk_and_stops_the_skirt_at_the_box() -> void:
	_check_the_squares_past_a_whole_chunk_are_chunks_of_their_own()
	_check_the_skirt_stops_at_the_box_s_edge()


func _check_the_squares_past_a_whole_chunk_are_chunks_of_their_own() -> void:
	# 82 × 82 vertices, every one finite, are 81 × 81 squares: a chunk of 80 × 80 squares, a strip
	# of 1 × 80, one of 80 × 1 and a single square (a count of 80 squares or fewer is one chunk).
	var parent := Node3D.new()
	_built.append(parent)
	var root := SurroundingsLoader.create(_hand_grid(82, 82, 1000, 1000), parent)
	var squares := {"Chunk_0_0": 80 * 80, "Chunk_1_0": 80, "Chunk_0_1": 80, "Chunk_1_1": 1}
	assert_eq(root.get_child_count(), squares.size(), "four chunks and no skirt")
	for chunk_name: String in squares:
		var chunk := root.get_node_or_null(chunk_name) as MeshInstance3D
		assert_not_null(chunk, "%s is built" % chunk_name)
		if chunk != null:
			var indices := (chunk.mesh as ArrayMesh).surface_get_array_index_len(0)
			assert_eq(indices, 6 * squares[chunk_name], "%s: two triangles a square" % chunk_name)


## The skirt's segments as brief decision 8 defines them (a grid edge between a drawn square, one
## of four finite corners, and an undrawn one, both inside the box: the box's own outer edge has
## none), as sorted text.
func _expected_segments(grid: SurroundingsGrid) -> Array:
	var drawn := func(c: int, r: int) -> bool:
		var corners := [grid.height(c, r), grid.height(c + 1, r)]
		corners.append_array([grid.height(c, r + 1), grid.height(c + 1, r + 1)])
		return not corners.any(func(height: float) -> bool: return is_nan(height))
	var segments := []
	for r in range(1, grid.rows - 1):
		for c in grid.columns - 1:
			if drawn.call(c, r - 1) != drawn.call(c, r):
				segments.append("%s-%s" % [Vector2i(c, r), Vector2i(c + 1, r)])
	for c in range(1, grid.columns - 1):
		for r in grid.rows - 1:
			if drawn.call(c - 1, r) != drawn.call(c, r):
				segments.append("%s-%s" % [Vector2i(c, r), Vector2i(c, r + 1)])
	segments.sort()
	return segments


## The segments the skirt mesh hangs from, read off its quads' top vertices (grid column and row
## of each, the lower first), as sorted text; and a check that each quad's two triangles are the
## two halves of the quad (either diagonal, either way round: which is not pinned).
func _skirt_segments(grid: SurroundingsGrid, skirt: MeshInstance3D) -> Array:
	var arrays := (skirt.mesh as ArrayMesh).surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
	var quads := vertices.size() / 4
	assert_eq(indices.size(), 6 * quads, "a quad is two triangles")
	var halves := ["0,1,2|1,2,3", "0,1,3|0,2,3"]
	var segments := []
	for quad in quads:
		var triangles := []
		for t in 2:
			var corners := []
			for k in 3:
				corners.append(indices[6 * quad + 3 * t + k] - 4 * quad)
			corners.sort()
			var text := corners.map(func(index: int) -> String: return str(index))
			triangles.append(",".join(PackedStringArray(text)))
		triangles.sort()
		assert_true("|".join(PackedStringArray(triangles)) in halves, "quad %d is covered" % quad)
		var ends := []
		for corner in 2:
			var top := vertices[4 * quad + corner]
			var column := roundi((top.x - grid.x_min) / grid.spacing_m)
			ends.append(Vector2i(column, roundi((top.z - grid.z_min) / grid.spacing_m)))
		ends.sort_custom(func(a: Vector2i, b: Vector2i) -> bool: return a.x + a.y < b.x + b.y)
		segments.append("%s-%s" % ends)
	segments.sort()
	return segments


func _check_the_skirt_stops_at_the_box_s_edge() -> void:
	# The fixture's grid (6 × 7 vertices) with a cut that touches the box on one side, then on
	# two: the NaN is a block of 2 × 2 undrawn squares, and its skirt runs round the sides the
	# drawn squares meet (6 segments; at the corner 4), never along the box's own edge.
	var cases := {
		"west":
		[{"e_min": 2613000.0, "e_max": 2619000.0, "n_min": 1098000.0, "n_max": 1104000.0}, 6],
		"east":
		[{"e_min": 2622000.0, "e_max": 2628000.0, "n_min": 1098000.0, "n_max": 1104000.0}, 6],
		"north":
		[{"e_min": 2616000.0, "e_max": 2622000.0, "n_min": 1104000.0, "n_max": 1110000.0}, 6],
		"south":
		[{"e_min": 2616000.0, "e_max": 2622000.0, "n_min": 1092000.0, "n_max": 1098000.0}, 6],
		"north-west corner":
		[{"e_min": 2613000.0, "e_max": 2619000.0, "n_min": 1104000.0, "n_max": 1110000.0}, 4],
	}
	for why: String in cases:
		var path := _cut_case(cases[why][0])
		var grid := SurroundingsGrid.from_manifest(path, WorldConfig.from_manifest(path))
		assert_not_null(grid, "a cut touching the box on the %s is read" % why)
		if grid == null:
			continue
		var parent := Node3D.new()
		_built.append(parent)
		var skirt := SurroundingsLoader.create(grid, parent).get_node_or_null("Skirt")
		assert_not_null(skirt, "the cut on the %s has a skirt" % why)
		if skirt == null:
			continue
		var segments := _skirt_segments(grid, skirt as MeshInstance3D)
		assert_eq(segments.size(), cases[why][1], "%s: the segments are %s" % [why, segments])
		assert_eq(segments, _expected_segments(grid), "%s: where decision 8 says" % why)
