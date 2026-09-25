extends GutTest
## Pinning tests for brief M1-02: a WorldConfig that did not read a manifest, and an empty
## manifest, are visible errors (M0 R1 C-07 and C-08; Hard Rule 2; lesson 1).
##
## Pinned decisions (docs/history/ARCS.md §M0, D10): WorldConfig.new() used directly calls
## push_error and returns NaN from to_local and to_lv95, never the origin, which looks
## plausible (every point would sit on the church square). An empty manifest file is
## refused with the reason "the manifest is empty", not "cannot read" with the reason OK.

const UNBUILT := "WorldConfig: not read from a manifest"
const SCRATCH_DIR := "user://test_world_config_unbuilt"


func before_all() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)


func after_all() -> void:
	for file in DirAccess.get_files_at(SCRATCH_DIR):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR)


func test_to_local_on_an_unbuilt_config_is_nan_and_an_error() -> void:
	var p := WorldConfig.new().to_local(2623825.13, 1096489.77, 1606.37)
	assert_true(is_nan(p.x) and is_nan(p.y) and is_nan(p.z), "every component is NaN: %s" % p)
	assert_push_error(UNBUILT)


func test_to_lv95_on_an_unbuilt_config_is_nan_and_an_error() -> void:
	var lv95 := WorldConfig.new().to_lv95(Vector3(825.0, 1600.0, -489.0))
	assert_eq(lv95.size(), 3)
	assert_true(is_nan(lv95[0]) and is_nan(lv95[1]) and is_nan(lv95[2]), "all NaN: %s" % lv95)
	assert_push_error(UNBUILT)


func test_an_empty_manifest_is_refused_as_empty() -> void:
	var path := SCRATCH_DIR.path_join("empty.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.close()
	assert_null(WorldConfig.from_manifest(path), "an empty manifest is refused")
	var found := false
	for error in get_errors():
		if (
			not found
			and error.is_push_error()
			and error.contains_text(path)
			and error.contains_text("the manifest is empty")
		):
			error.handled = true
			found = true
	assert_true(found, "one push_error names the file and says it is empty")
