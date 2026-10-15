extends GutTest
## Pinning tests for brief M3-R1-fix-5 (M3 review R1 G-04, its Hard Rule 4 part): PhotoGrid and
## SurfaceGrid refuse a WorldConfig that was not read from the manifest they read.
##
## Pinned decisions (CLAUDE.md Hard Rule 4: a world that is silently shifted is the harm): the
## readers compare the origin (e, n) and the height offset of the WorldConfig given with the
## manifest's world block, and refuse a difference in any one of the three with the guard's own
## words, "the WorldConfig given was not read from this manifest". The guard had no test: made
## never true, every test stayed green and a manifest whose origin lay 1000 m further east was
## read and placed. Each case gives the reader another manifest's WorldConfig, as
## test_scene_placement.gd does for the buildings: the fixture's world block with one field
## moved, by a different amount each (east 1000 m, north 37.5 m, height offset 0.25 m), so that a
## guard that compares the wrong pair of fields, leaves one of the three out or tolerates a
## quarter of a metre is told from the right one (lesson 34). The control: the fixture's own
## WorldConfig, and a copy of its world block, are accepted. A later
## check cannot stand in: the other world has the owner's axes, and the photo and the surfaces
## fit their box through any origin.
##
## Does NOT prove: that the manifest's world block is bound to config/world.json at read time
## (M3 review R1 G-12, by design: the pipeline's first step writes it and its tests pin it);
## the refusal of a rotated world (test_photo_grid.gd and test_surface_grid.gd).

const SCRATCH_DIR := "user://test_m3_r1_fix5_world_guard"
const NOT_OURS := "the WorldConfig given was not read from this manifest"
const PHOTO := "tests/shared/photo_fixture/generated/manifest.json"
const SURFACES := "tests/shared/surfaces_fixture/generated/manifest.json"
const EAST_M := 1000.0
const NORTH_M := 37.5
const HEIGHT_M := 0.25

var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func after_all() -> void:
	_remove_tree(SCRATCH_DIR)


func _remove_tree(dir: String) -> void:
	for sub in DirAccess.get_directories_at(dir):
		_remove_tree(dir.path_join(sub))
	for file in DirAccess.get_files_at(dir):
		DirAccess.remove_absolute(dir.path_join(file))
	DirAccess.remove_absolute(dir)


## The WorldConfig of another manifest: the fixture at [param fixture] with [param change]
## (a Callable taking its world block) applied, written to a scratch folder and read there.
func _other_world(fixture: String, change: Callable) -> WorldConfig:
	_cases += 1
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(_repo_file(fixture))), OK, "it parses")
	var manifest: Dictionary = json.data
	change.call(manifest["world"])
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir)
	var path := dir.path_join("manifest.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(manifest, "  ", true, true))
	file.close()
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "the other manifest's world block is itself valid")
	return world


func _moved_east(world: Dictionary) -> void:
	world["origin_lv95"]["e"] += EAST_M


func _moved_north(world: Dictionary) -> void:
	world["origin_lv95"]["n"] += NORTH_M


func _raised(world: Dictionary) -> void:
	world["height_offset_m"] += HEIGHT_M


## The read was refused: a null result, and exactly one error, a push_error naming [param path]
## and saying the guard's words. Any other error, a SCRIPT ERROR among them, fails it.
func _assert_refused_once(result: RefCounted, path: String, why: String) -> void:
	assert_null(result, "%s: a null result" % why)
	var pushed := 0
	var others := []
	for error in get_errors():
		if error.handled:
			continue
		if error.is_push_error() and error.contains_text(path) and error.contains_text(NOT_OURS):
			pushed += 1
		else:
			others.append("%s %s" % [error.code, error.rationale])
		error.handled = true
	assert_eq(pushed, 1, "%s: one push_error names %s and says '%s'" % [why, path, NOT_OURS])
	assert_eq(others, [], "%s: no other error" % why)


func _photo_with(change: Callable) -> void:
	var path := _repo_file(PHOTO)
	var other := _other_world(PHOTO, change)
	_assert_refused_once(PhotoGrid.from_manifest(path, other), path, "PhotoGrid, another world")


func _surfaces_with(change: Callable) -> void:
	var path := _repo_file(SURFACES)
	var other := _other_world(SURFACES, change)
	_assert_refused_once(SurfaceGrid.from_manifest(path, other), path, "SurfaceGrid, another world")


func test_the_manifest_s_own_world_config_is_accepted() -> void:
	# The control, with a guard that refuses everything or compares the wrong pair of fields.
	var photo := _repo_file(PHOTO)
	assert_not_null(PhotoGrid.from_manifest(photo, WorldConfig.from_manifest(photo)))
	var surfaces := _repo_file(SURFACES)
	assert_not_null(SurfaceGrid.from_manifest(surfaces, WorldConfig.from_manifest(surfaces)))
	var same := _other_world(PHOTO, func(_world: Dictionary) -> void: pass)
	assert_not_null(PhotoGrid.from_manifest(photo, same), "a copy of the world block is accepted")


func test_photo_grid_refuses_another_east_origin() -> void:
	_photo_with(_moved_east)


func test_photo_grid_refuses_another_north_origin() -> void:
	_photo_with(_moved_north)


func test_photo_grid_refuses_another_height_offset() -> void:
	_photo_with(_raised)


func test_surface_grid_refuses_another_east_origin() -> void:
	_surfaces_with(_moved_east)


func test_surface_grid_refuses_another_north_origin() -> void:
	_surfaces_with(_moved_north)


func test_surface_grid_refuses_another_height_offset() -> void:
	_surfaces_with(_raised)
