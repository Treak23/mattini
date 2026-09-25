extends GutTest
## Pinning tests for brief M1-04: TerrainLoader builds the Terrain3D terrain from a
## TerrainGrid, and every height lands on its own vertex.
##
## Pinned decisions (docs/SPEC.md §8; brain.md H11): Terrain3D's vertex spacing is the
## grid's spacing and its regions are 1024 m wide (region size 1024 / spacing vertices);
## import_images snaps an image to the corner of its region, so the loader places the grid
## itself, and these tests read the fixture's heights back at their local positions (the
## seam test: pipeline output in, Terrain3D heights out). Vertices of the loaded regions
## outside the grid are holes, and nothing is drawn outside the regions (world background
## none): no invented ground (Hard Rule 2). free_editor_textures is off, so creating the
## node from code prints no ERROR lines; collision is off (M1 has no physics, and Terrain3D's
## collision over areas that are all holes makes Godot print ERROR lines, brain.md H11).
##
## The terrain is built once, in before_all: at 0.5 m two regions hold 8.4 million
## vertices. Does NOT prove: that anything renders or looks right (no GPU).

var _camera: Camera3D
var _terrain: Terrain3D
var _grid: TerrainGrid


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _vectors() -> Dictionary:
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/terrain_vectors.json"))
	var parsed: Variant = JSON.parse_string(text)
	assert_typeof(parsed, TYPE_DICTIONARY, "the shared terrain vectors parse")
	return parsed


func before_all() -> void:
	var manifest := _repo_file("tests/shared/terrain_fixture/generated/manifest.json")
	_grid = TerrainGrid.from_manifest(manifest, WorldConfig.from_manifest(manifest))
	# Terrain3D looks for the viewport's camera and prints an ERROR when there is none.
	_camera = Camera3D.new()
	add_child(_camera)
	if _grid != null:
		_terrain = TerrainLoader.create(_grid, self)


func after_all() -> void:
	if _terrain != null:
		_terrain.free()
	_camera.free()


func _at(xz: Array) -> Vector3:
	return Vector3(float(xz[0]), 0.0, float(xz[1]))


func test_the_terrain_is_built_under_the_given_parent() -> void:
	assert_not_null(_grid, "the fixture grid is read")
	assert_not_null(_terrain, "TerrainLoader.create returns the terrain")
	if _terrain == null:
		return
	assert_eq(_terrain.get_parent(), self, "the terrain is a child of the given parent")
	assert_true(_terrain.is_inside_tree())


func test_terrain3d_settings_follow_the_grid() -> void:
	if _terrain == null:
		fail_test("no terrain was built")
		return
	var expected: Dictionary = _vectors()["terrain3d"]
	assert_eq(_terrain.vertex_spacing, float(expected["vertex_spacing"]))
	assert_eq(_terrain.region_size, int(expected["region_size"]), "regions are 1024 m wide")
	var locations: Array = []
	for location: Vector2i in _terrain.data.get_region_locations():
		locations.append(location)
	locations.sort()
	var expected_locations: Array = []
	for pair: Array in expected["region_locations"]:
		expected_locations.append(Vector2i(int(pair[0]), int(pair[1])))
	assert_eq(locations, expected_locations, "one region per 1024 m square the grid touches")
	assert_eq(_terrain.collision_mode, 0, "no collision in M1: the free-fly camera needs none")
	assert_false(_terrain.free_editor_textures, "free_editor_textures is off (brain.md H11)")
	assert_eq(_terrain.material.world_background, 0, "world background none: no invented ground")


func test_heights_read_back_on_their_own_vertices() -> void:
	if _terrain == null:
		fail_test("no terrain was built")
		return
	var data := _vectors()
	var tol: float = data["tolerance_m"]
	for v: Dictionary in data["vertices"]:
		var got: float = _terrain.data.get_height(_at(v["local_xz"]))
		assert_almost_eq(got, float(v["y"]), tol, v["name"])
		assert_false(
			_terrain.data.get_control_hole(_at(v["local_xz"])), "%s: not a hole" % v["name"]
		)


func test_vertices_of_the_regions_outside_the_grid_are_holes() -> void:
	if _terrain == null:
		fail_test("no terrain was built")
		return
	for h: Dictionary in _vectors()["holes"]:
		assert_true(_terrain.data.get_control_hole(_at(h["local_xz"])), "%s: a hole" % h["name"])
		assert_true(
			is_nan(_terrain.data.get_height(_at(h["local_xz"]))), "%s: no height" % h["name"]
		)


func test_nothing_outside_the_regions() -> void:
	if _terrain == null:
		fail_test("no terrain was built")
		return
	for o: Dictionary in _vectors()["outside_regions"]:
		assert_false(_terrain.data.has_regionp(_at(o["local_xz"])), "%s: no region" % o["name"])
		assert_true(
			is_nan(_terrain.data.get_height(_at(o["local_xz"]))), "%s: no height" % o["name"]
		)
