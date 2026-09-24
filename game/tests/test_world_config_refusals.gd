extends GutTest
## WorldConfig refuses what it cannot trust, naming the manifest (Hard Rules 2 and 4).
##
## Every signed axis mapping: the 24 rotations are accepted and keep the world
## right-handed, the 24 mirrors are refused, as pipeline/tests/test_world_rotations.py
## checks on the pipeline side. Malformed manifests are refused too. Each case is written
## as a manifest under user:// and read back through from_manifest.

const MANIFEST_PATH := "res://assets/generated/manifest.json"
const SCRATCH_DIR := "user://test_world_config_refusals"
const PERMUTATIONS := [
	["e", "n", "h"],
	["e", "h", "n"],
	["n", "e", "h"],
	["n", "h", "e"],
	["h", "e", "n"],
	["h", "n", "e"],
]

var _written := 0


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)


func after_all() -> void:
	for file in DirAccess.get_files_at(SCRATCH_DIR):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR)


func _manifest() -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST_PATH))
	assert_typeof(parsed, TYPE_DICTIONARY, "the generated manifest parses")
	return parsed


func _write(text: String) -> String:
	_written += 1
	var path := SCRATCH_DIR.path_join("manifest_%d.json" % _written)
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()
	return path


func _assert_refused(text: String, why: String) -> void:
	var path := _write(text)
	assert_null(WorldConfig.from_manifest(path), "%s is refused" % why)
	assert_push_error(path, "%s: the error names the file" % why)


func _mappings() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for perm: Array in PERMUTATIONS:
		for bits in 8:
			var axes := {}
			for i in 3:
				var sign := "-" if bits & (1 << i) else "+"
				axes[["x", "y", "z"][i]] = sign + perm[i]
			result.append(axes)
	return result


## Parity of the permutation times the product of the signs: +1 for a rotation.
func _is_rotation(axes: Dictionary) -> bool:
	var order := []
	var sign := 1
	for game_axis in ["x", "y", "z"]:
		var spec: String = axes[game_axis]
		order.append(["e", "n", "h"].find(spec[1]))
		if spec[0] == "-":
			sign = -sign
	var inversions := 0
	for i in 3:
		for j in range(i + 1, 3):
			if order[i] > order[j]:
				inversions += 1
	return sign * (1 if inversions % 2 == 0 else -1) == 1


func test_rotations_accepted_mirrors_refused() -> void:
	var mappings := _mappings()
	assert_eq(mappings.size(), 48, "48 signed permutations")
	var rotations := 0
	for axes in mappings:
		var manifest := _manifest()
		manifest["world"]["axes"] = axes
		var path := _write(JSON.stringify(manifest))
		var world := WorldConfig.from_manifest(path)
		if not _is_rotation(axes):
			assert_null(world, "mirror %s is refused" % [axes])
			assert_push_error(path, "mirror %s: the error names the file" % [axes])
			continue
		rotations += 1
		assert_not_null(world, "rotation %s is accepted" % [axes])
		if world == null:
			continue
		var o := PackedFloat64Array([world.origin_e, world.origin_n, 0.0])
		var base := world.to_local(o[0], o[1], o[2])
		var east := world.to_local(o[0] + 1.0, o[1], o[2]) - base
		var north := world.to_local(o[0], o[1] + 1.0, o[2]) - base
		var up := world.to_local(o[0], o[1], o[2] + 1.0) - base
		assert_eq(east.cross(north), up, "%s keeps east x north = up" % [axes])
		var units := {"e": east, "n": north, "h": up}
		for i in 3:
			var spec: String = axes[["x", "y", "z"][i]]
			var expected := 1.0 if spec[0] == "+" else -1.0
			assert_eq(units[spec[1]][i], expected, "%s: game axis %d reads %s" % [axes, i, spec])
	assert_eq(rotations, 24, "24 rotations")


func test_missing_manifest_is_refused_with_the_file_named() -> void:
	var path := SCRATCH_DIR.path_join("absent.json")
	assert_null(WorldConfig.from_manifest(path), "a missing manifest is refused")
	assert_push_error(path, "the error names the file")


func test_malformed_manifests_are_refused_with_the_file_named() -> void:
	_assert_refused("{", "broken JSON")
	_assert_refused("[]", "a manifest that is not an object")
	var cases := {
		"manifest schema 2": func(m: Dictionary) -> void: m["schema"] = 2,
		"manifest schema as text": func(m: Dictionary) -> void: m["schema"] = "1",
		"no world block": func(m: Dictionary) -> void: m.erase("world"),
		"world schema 2": func(m: Dictionary) -> void: m["world"]["schema"] = 2,
		"LV03 crs": func(m: Dictionary) -> void: m["world"]["crs"]["horizontal"] = "EPSG:21781",
		"origin as text": func(m: Dictionary) -> void: m["world"]["origin_lv95"]["e"] = "x",
		"origin missing": func(m: Dictionary) -> void: m["world"]["origin_lv95"].erase("n"),
		"height offset missing": func(m: Dictionary) -> void: m["world"].erase("height_offset_m"),
		"axis missing": func(m: Dictionary) -> void: m["world"]["axes"].erase("y"),
		"axis unsigned": func(m: Dictionary) -> void: m["world"]["axes"]["x"] = "e",
		"unknown source axis": func(m: Dictionary) -> void: m["world"]["axes"]["x"] = "+x",
		"axis used twice": func(m: Dictionary) -> void: m["world"]["axes"]["y"] = "+e",
		"extra game axis": func(m: Dictionary) -> void: m["world"]["axes"]["w"] = "+e",
	}
	for why: String in cases:
		var manifest := _manifest()
		cases[why].call(manifest)
		_assert_refused(JSON.stringify(manifest), why)


func test_non_finite_numbers_are_refused() -> void:
	var manifest := _manifest()
	manifest["world"]["height_offset_m"] = "HUGE"
	var text := JSON.stringify(manifest).replace('"HUGE"', "1e400")
	_assert_refused(text, "an infinite height offset")
