extends GutTest
## Pinning tests for brief M2-02 (M1 R1 T-02, G-01): the loader places a grid that lies
## north-west of its origin, at 2 m, across the edges of four Terrain3D regions.
##
## Pinned decisions (docs/SPEC.md §8, the terrain grid): Terrain3D's vertex spacing is the
## grid's spacing and its regions are 1024 m wide (512 vertices at 2 m); import_images
## snaps an image to the corner of its region, so the loader places the grid itself. The
## second shared fixture (tests/shared/terrain_fixture_nw/, its vectors in
## tests/shared/terrain_vectors_nw.json, computed by design two independent ways) sits
## where the first does not: negative x and z, a region corner inside it, 2 m, a height
## offset of -12.25 m. The review's mutations (the import position in vertices, the first
## region rounded towards zero, the region size fixed at 2048 vertices) each move or cut
## this grid, so each fails here. The clay look's settings are read on the built terrain
## (G-01).
##
## Does NOT prove: that anything renders or looks right (no GPU); that the height_offset_m
## uniform reaches the shader correctly (read only as a parameter).

var _camera: Camera3D
var _terrain: Terrain3D
var _grid: TerrainGrid


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _vectors() -> Dictionary:
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/terrain_vectors_nw.json"))
	var json := JSON.new()
	assert_eq(json.parse(text), OK, "the second fixture's vectors parse")
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func before_all() -> void:
	var manifest := _repo_file("tests/shared/terrain_fixture_nw/generated/manifest.json")
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


func test_the_grid_is_read_where_the_vectors_say() -> void:
	assert_not_null(_grid, "the second fixture's grid is read")
	if _grid == null:
		return
	var grid: Dictionary = _vectors()["grid"]
	assert_eq(_grid.columns, int(grid["columns"]))
	assert_eq(_grid.rows, int(grid["rows"]))
	assert_eq(_grid.spacing_m, float(grid["spacing_m"]))
	assert_eq(_grid.x_min, float(grid["x_min"]), "west of the origin")
	assert_eq(_grid.z_min, float(grid["z_min"]), "north of the origin")
	assert_eq(_grid.height_offset_m, float(grid["height_offset_m"]))


func test_terrain3d_settings_follow_the_grid() -> void:
	if _terrain == null:
		fail_test("no terrain was built")
		return
	var expected: Dictionary = _vectors()["terrain3d"]
	assert_eq(_terrain.vertex_spacing, float(expected["vertex_spacing"]))
	assert_eq(_terrain.region_size, int(expected["region_size"]), "1024 m regions at 2 m")
	var locations: Array = []
	for location: Vector2i in _terrain.data.get_region_locations():
		locations.append(location)
	locations.sort()
	var expected_locations: Array = []
	for pair: Array in expected["region_locations"]:
		expected_locations.append(Vector2i(int(pair[0]), int(pair[1])))
	expected_locations.sort()
	assert_eq(locations, expected_locations, "the four regions the grid touches, and no other")


func test_the_clay_look_is_set() -> void:
	if _terrain == null:
		fail_test("no terrain was built")
		return
	var material := _terrain.material
	assert_false(material.show_checkered, "the checkerboard debug view is off")
	assert_true(material.shader_override_enabled, "the override shader is on")
	assert_not_null(material.shader_override, "an override shader is set")
	if material.shader_override != null:
		assert_eq(material.shader_override.resource_path, TerrainLoader.CLAY_SHADER)
	assert_eq(material.world_background, Terrain3DMaterial.NONE, "no invented ground")


func test_heights_read_back_on_their_own_vertices() -> void:
	if _terrain == null:
		fail_test("no terrain was built")
		return
	var data := _vectors()
	var tol: float = data["tolerance_m"]
	assert_gt(data["vertices"].size(), 9, "the vectors name the corners and the region edges")
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
