extends GutTest
## Pinning tests for brief M0-03: the game reads the world mapping from the manifest.
##
## Pinned decisions (SPEC section 6): the origin and axes come only from
## res://assets/generated/manifest.json, whose world block is config/world.json verbatim;
## conversions match tests/shared/world_vectors.json (the vectors the pipeline's tests use,
## including the 32-bit trap); a stale manifest is caught.

const MANIFEST_PATH := "res://assets/generated/manifest.json"


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _vectors() -> Dictionary:
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/world_vectors.json"))
	assert_ne(text, "", "shared vectors are readable")
	var parsed: Variant = JSON.parse_string(text)
	assert_typeof(parsed, TYPE_DICTIONARY)
	return parsed


func test_manifest_matches_config_world_json() -> void:
	var text := FileAccess.get_file_as_string(MANIFEST_PATH)
	assert_ne(text, "", "manifest exists; the pipeline's manifest step writes it")
	var manifest: Dictionary = JSON.parse_string(text)
	var config_sha := FileAccess.get_sha256(_repo_file("config/world.json"))
	assert_eq(manifest.get("world_sha256", ""), config_sha, "manifest is current")


func test_origin_comes_from_the_manifest() -> void:
	var world := WorldConfig.from_manifest(MANIFEST_PATH)
	assert_not_null(world)
	assert_eq(world.origin_e, 2623000.0)
	assert_eq(world.origin_n, 1096000.0)


func test_to_local_matches_shared_vectors() -> void:
	var world := WorldConfig.from_manifest(MANIFEST_PATH)
	var data := _vectors()
	var tol: float = data["tolerance_m"]
	for v: Dictionary in data["vectors"]:
		var lv95: Array = v["lv95"]
		var expected: Array = v["local"]
		var p: Vector3 = world.to_local(lv95[0], lv95[1], lv95[2])
		assert_almost_eq(p.x, float(expected[0]), tol, "%s: x" % v["name"])
		assert_almost_eq(p.y, float(expected[1]), tol, "%s: y" % v["name"])
		assert_almost_eq(p.z, float(expected[2]), tol, "%s: z" % v["name"])


func test_to_lv95_matches_shared_vectors() -> void:
	var world := WorldConfig.from_manifest(MANIFEST_PATH)
	var data := _vectors()
	var tol: float = data["tolerance_m"]
	for v: Dictionary in data["vectors"]:
		var local: Array = v["local"]
		var expected: Array = v["lv95"]
		var lv95: PackedFloat64Array = world.to_lv95(Vector3(local[0], local[1], local[2]))
		assert_almost_eq(lv95[0], float(expected[0]), tol, "%s: e" % v["name"])
		assert_almost_eq(lv95[1], float(expected[1]), tol, "%s: n" % v["name"])
		assert_almost_eq(lv95[2], float(expected[2]), tol, "%s: h" % v["name"])
