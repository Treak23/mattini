extends GutTest
## Gaps in the pinned tests of brief v0.6.0-08 that the builder's own probes found (lesson 51,
## decision 15): guards and branches of SurroundingsGrid and SurroundingsLoader that no pinned
## test fails without. Each test here fails when the guard it names is removed or loosened.
##
## Every refusal is read through _read, which returns the problem without a push_error (every
## reader's shape), so this script prints no ERROR line and has no allowlist entry.
##
## Does NOT prove: that the guards the pins and this file leave out are not needed (lesson 4);
## the loader's skirt facing (the skirt is double-sided, so which way its front faces is not
## pinned); that anything is drawn, or drawn right (no GPU; the owner's PC).

const SCRATCH_DIR := "user://test_v060_08_gaps"
const FIXTURE_DIR := "tests/shared/surroundings_fixture/generated"
const F32 := "surroundings/fixture.f32"
const JPG := "surroundings/fixture_colour.jpg"
const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"

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


## The fixture with no cut: every height finite, cut_box a point (no vertex lies strictly in it).
func _cutless_manifest() -> String:
	var heights := _fixture_bytes(F32).to_float32_array()
	for k in heights.size():
		if is_nan(heights[k]):
			heights[k] = 1000.0 + k
	var filled := heights.to_byte_array()
	var change := func(m: Dictionary) -> void:
		m["surroundings"]["sha256"] = _sha256(filled)
		m["surroundings"]["cut_box"] = {
			"e_max": 2616000.0, "e_min": 2616000.0, "n_max": 1100000.0, "n_min": 1100000.0
		}
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
