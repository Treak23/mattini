extends GutTest
## Gaps in the pinned tests of brief v0.6.0-08 that the builder's own probes found (lesson 51,
## decision 15): guards and branches of SurroundingsGrid and SurroundingsLoader that no pinned
## test fails without. Each test here fails when the guard it names is removed or loosened.
##
## Every refusal is read through _read, which returns the problem without a push_error (every
## reader's shape), so this script prints no ERROR line and has no allowlist entry.
##
## The tests from "The batch gate's mutation prover's findings" on are the fixer round's: the
## prover's findings, each with the class it belongs to (lesson 9), not the one site it named:
## all four sides of the cut's containment, outside and on the edge; the colour's fit tolerance
## on both sides of its edge and both signs; each axis at 16384 pixels and one past; the smallest
## grid and colour; every character of a digest, for each of the three digests; every proper
## rotation of the axes; each value of the world given, one at a time; the decoded size by its
## width, its height and its format; the one material across a grid of many chunks.
##
## Does NOT prove: that the guards the pins and this file leave out are not needed (lesson 4);
## the loader's skirt facing (the skirt is double-sided, so which way its front faces is not
## pinned); that anything is drawn, or drawn right (no GPU; the owner's PC).

const SCRATCH_DIR := "user://test_v060_08_gaps"
const FIXTURE_DIR := "tests/shared/surroundings_fixture/generated"
const F32 := "surroundings/fixture.f32"
const JPG := "surroundings/fixture_colour.jpg"
const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"

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


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


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
	assert_string_contains(SurroundingsGrid.new()._read(missing, world), "cannot read the manifest")
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
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
	}
	for why: String in cases:
		_assert_refused(cases[why][0], why, cases[why][1])


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
	}
	for why: String in cases:
		_assert_refused(cases[why][0], why, cases[why][1])


func test_a_share_of_0_and_a_share_of_1_are_read() -> void:
	assert_eq(_problem(_set_key("filled_fraction", 0.0)), "", "no placeholder pixel")
	assert_eq(_problem(_set_key("filled_fraction", 1.0)), "", "only placeholder pixels")


func test_a_path_that_is_not_plain_is_refused_for_both_files() -> void:
	for bad: String in [
		"/a/b.f32", "a\\b.f32", "C:/b.f32", "a:b.f32", "a//b.f32", "./b.f32", "", "a/../b.f32"
	]:
		var problem := _problem(_set_key("file", bad))
		assert_string_contains(problem, "surroundings.file must be a plain relative path")
		problem = _problem(_set_key("colour_file", bad.replace("f32", "jpg")))
		assert_string_contains(problem, "surroundings.colour_file must be a plain relative path")
	assert_eq(_problem(_unchanged()), "", "a plain path is read")


func test_a_digest_in_capitals_is_read() -> void:
	var change := func(m: Dictionary) -> void:
		m["surroundings"]["sha256"] = m["surroundings"]["sha256"].to_upper()
		m["surroundings"]["colour_sha256"] = m["surroundings"]["colour_sha256"].to_upper()
	assert_eq(_problem(change), "", "both files' SHA-256 are compared in lower case")


func test_the_file_messages_end_with_the_release_hint_in_an_export() -> void:
	var short := _fixture_bytes(F32).slice(0, 164)
	var flipped := _fixture_bytes(F32)
	flipped[20] = flipped[20] ^ 1
	var small := Image.create(15, 17, false, Image.FORMAT_RGB8)
	var small_jpg := small.save_jpg_to_buffer(0.92)
	var damaged := _fixture_bytes(JPG)
	damaged[400] = damaged[400] ^ 1
	var cases := {
		"the heights of another size": [_set_key("sha256", _sha256(short)), short, null],
		"the heights of another SHA-256": [_unchanged(), flipped, null],
		"the colour of another SHA-256": [_unchanged(), null, damaged],
		"the colour of another size":
		[_set_key("colour_sha256", _sha256(small_jpg)), null, small_jpg],
	}
	for why: String in cases:
		var spec: Array = cases[why]
		var f32: Variant = spec[1] if spec[1] != null else PackedByteArray()
		var jpg: Variant = spec[2] if spec[2] != null else PackedByteArray()
		var path := _write_case(spec[0], f32, jpg)
		var world := WorldConfig.from_manifest(path)
		ReleaseBuild.set_exported_for_tests(true)
		var problem := SurroundingsGrid.new()._read(path, world)
		assert_true(problem.ends_with(RELEASE_HINT), "%s, exported: %s" % [why, problem])
		ReleaseBuild.set_exported_for_tests(false)
		problem = SurroundingsGrid.new()._read(path, world)
		assert_true(problem.ends_with(" rebuilds it"), "%s, not exported: %s" % [why, problem])


func test_a_nan_on_the_edge_of_the_cut_is_refused() -> void:
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
