extends GutTest
## Gaps the mutation prover of brief v0.5.0-03 found in the pinned tests of CaptureShadowGrid
## (lesson 51): guards no pinned test failed. Each test here fails when its guard is removed.
##
## Not covered, and why: the axes compare for north and for up are equivalent mutations while the
## east compare stays, because WorldConfig refuses a world that is not a proper rotation, so a
## world that keeps east and up and flips north cannot be built; the origin subtracted in the
## reader is invisible to any test (the world's origin cancels in the fixture's place); the
## finite compare of the sun's and the box's numbers cannot be reached, as JSON text holds no
## infinity or NaN (Godot refuses 1e999 at the parse), so only their type is pinned.

const SCRATCH_DIR := "user://test_v0_5_0_03_gaps"
const FIXTURE_DIR := "tests/shared/shadows_fixture"

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _parse_file(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func after_all() -> void:
	_remove(SCRATCH_DIR)


func _remove(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## Writes a case folder: the fixture's manifest changed by [param change], the fixture's PNG.
func _write_case(change: Callable) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("shadows"))
	var world_path := _repo_file(FIXTURE_DIR.path_join("world.json"))
	var manifest := {
		"schema": 1,
		"world": _parse_file(world_path),
		"world_sha256": FileAccess.get_sha256(world_path),
		"shadows": _parse_file(_repo_file(FIXTURE_DIR.path_join("generated/shadows/fixture.json"))),
	}
	change.call(manifest)
	var text := JSON.stringify(manifest, "  ", true, true)
	var out := FileAccess.open(dir.path_join("manifest.json"), FileAccess.WRITE)
	out.store_string(text)
	out.close()
	var png := FileAccess.get_file_as_bytes(
		_repo_file(FIXTURE_DIR.path_join("generated/shadows/fixture.png"))
	)
	var file := FileAccess.open(dir.path_join("shadows/fixture.png"), FileAccess.WRITE)
	file.store_buffer(png)
	file.close()
	return dir.path_join("manifest.json")


func _refused(world_path: String, path: String, why: String, needle: String) -> void:
	var grid := CaptureShadowGrid.from_manifest(path, WorldConfig.from_manifest(world_path))
	assert_null(grid, "%s is refused" % why)
	var found := false
	for error in get_errors():
		if (
			not found
			and not error.handled
			and error.is_push_error()
			and error.contains_text("CaptureShadowGrid: %s: " % path)
			and error.contains_text(needle)
		):
			error.handled = true
			found = true
	assert_true(found, "%s: one push_error naming the manifest and %s" % [why, needle])


func _assert_refused(change: Callable, why: String, needle: String) -> void:
	var path := _write_case(change)
	_refused(path, path, why, needle)


func _shadows(key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["shadows"][key] = value


func _nested(outer: String, key: String, value: Variant) -> Callable:
	return func(m: Dictionary) -> void: m["shadows"][outer][key] = value


func test_a_world_config_with_another_height_offset_is_refused() -> void:
	var path := _write_case(func(_m: Dictionary) -> void: pass)
	var other := _write_case(func(m: Dictionary) -> void: m["world"]["height_offset_m"] += 7.0)
	_refused(other, path, "a WorldConfig with another height offset", "WorldConfig")


func test_a_shadows_block_that_is_not_an_object_is_refused() -> void:
	for value: Variant in ["built", 5.0, [], true]:
		_assert_refused(
			func(m: Dictionary) -> void: m["shadows"] = value, "shadows %s" % [value], "shadows"
		)


func test_the_sun_is_checked() -> void:
	for key in ["azimuth_grid_deg", "elevation_deg"]:
		_assert_refused(_nested("sun", key, "high"), "a text sun.%s" % key, "sun.%s" % key)
	_assert_refused(_nested("sun", "note", 3.0), "a numeric sun.note", "sun.note")
	_assert_refused(_nested("sun", "extra", 1.0), "a sun key too many", "sun")
	_assert_refused(
		func(m: Dictionary) -> void: m["shadows"]["sun"].erase("note"), "a sun key short", "sun"
	)


func test_the_box_is_checked() -> void:
	_assert_refused(_nested("lv95_box", "extra", 1.0), "a box key too many", "lv95_box")
	_assert_refused(
		func(m: Dictionary) -> void: m["shadows"]["lv95_box"].erase("n_min"),
		"a box key short",
		"lv95_box"
	)
	for key in ["e_min", "e_max", "n_min", "n_max"]:
		_assert_refused(_nested("lv95_box", key, "far"), "a text %s" % key, "lv95_box.%s" % key)


func test_the_source_is_checked() -> void:
	_assert_refused(_nested("source", "extra", 1.0), "a source key too many", "source")
	_assert_refused(
		func(m: Dictionary) -> void: m["shadows"]["source"].erase("collection"),
		"a source key short",
		"source"
	)
	for key in ["attribution", "collection"]:
		_assert_refused(_nested("source", key, 3.0), "a numeric %s" % key, "source.%s" % key)
		_assert_refused(_nested("source", key, ""), "an empty %s" % key, "source.%s" % key)
	_assert_refused(_nested("source", "editions", []), "no editions", "editions")
	_assert_refused(_nested("source", "editions", [2021.0]), "a numeric edition", "editions")
	_assert_refused(_nested("source", "editions", ["2021", ""]), "an empty edition", "editions")
	_assert_refused(
		_nested("source", "entry_sha256", "abc"), "a short entry digest", "entry_sha256"
	)
	_assert_refused(
		_nested("source", "entry_sha256", 5.0), "a numeric entry digest", "entry_sha256"
	)


func test_the_digests_are_64_hex_digits() -> void:
	for key in ["sha256", "pixels_sha256"]:
		_assert_refused(_shadows(key, "g".repeat(64)), "a non-hex %s" % key, key)
		_assert_refused(_shadows(key, "a".repeat(63)), "a short %s" % key, key)
		_assert_refused(_shadows(key, 5.0), "a numeric %s" % key, key)
	_assert_refused(_nested("source", "entry_sha256", "g".repeat(64)), "a non-hex entry", "entry")


func test_the_area_is_a_name() -> void:
	_assert_refused(_shadows("area", ""), "an empty area", "shadows.area")
	_assert_refused(_shadows("area", 3.0), "a numeric area", "shadows.area")


func test_the_counts_are_whole_numbers_of_at_least_one() -> void:
	for key in ["columns", "rows"]:
		_assert_refused(_shadows(key, 0.0), "0 %s" % key, "shadows.%s" % key)
		_assert_refused(_shadows(key, -2.0), "negative %s" % key, "shadows.%s" % key)
		_assert_refused(_shadows(key, 3.5), "fractional %s" % key, "shadows.%s" % key)
		_assert_refused(_shadows(key, "64"), "text %s" % key, "shadows.%s" % key)


func test_the_file_is_a_plain_relative_path() -> void:
	# A name with a colon or a scheme is refused before any lookup.
	for file: Variant in ["shadows:fixture.png", "res://shadows/fixture.png", "C:fixture.png"]:
		_assert_refused(_shadows("file", file), "the file %s" % [file], "shadows.file")
