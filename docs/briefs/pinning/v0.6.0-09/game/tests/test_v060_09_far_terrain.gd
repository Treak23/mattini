extends GutTest
## Pinning tests for brief v0.6.0-09 (brief M4-10's far mountains, re-scoped by design §3): the
## main scene builds the far terrain where the world config puts it, and its camera sees every
## corner of it.
##
## Pinned decisions (design §3; brief v0.6.0-09 decisions 1 and 4; CLAUDE.md Hard Rule 4):
## - The main scene reads SurroundingsGrid (brief v0.6.0-08) and builds it with
##   SurroundingsLoader.create(far, <the main scene>): a node "Surroundings", a child of the main
##   scene, its global transform the identity (unturned, unscaled, at the scene's origin), and so
##   is every chunk's and the skirt's. Its material holds the far colour the reader decoded (the
##   complete world's 15 x 18 pixels), not another texture.
## - In the complete test world (complete_world.gd: the shared surroundings fixture's 6 x 7
##   heights at 3000 m, its box moved to SURROUNDINGS_BOX), every vertex of every chunk stands,
##   within 1 mm, at WorldConfig.to_local of its grid point (E = e_min + 3000 c, N = n_max -
##   3000 r, h = the file's local height + the world's height offset), computed here by hand from
##   SURROUNDINGS_BOX and the fixture's heights through the manifest's own WorldConfig; every
##   vertex of every square with four finite corners is drawn, and nothing else. No far triangle
##   reaches into the terrain's area (the near terrain is drawn there).
## - The camera's far plane is 40'000 m (FreeFlyCamera's own, so the main scene's camera too),
##   its near 0.1 m: the far terrain's window (the area's box grown by config/surroundings.json's
##   margin_m) has corners up to 31.8 km from the village's area box (design §0: at 20'000 m
##   three corner chunks were clipped from the village), and 40'000 m reaches them from anywhere
##   in the box and from 5'000 m above or below it.
##
## Does NOT prove: that anything is drawn or looks right (no GPU; the owner's PC); the real
## village's 841 x 861 mesh in the scene (the export's started build prints its line, brief
## v0.6.0-10; its build time is recorded by brief v0.6.0-08's rehearsal, not tested); that the
## far shadows land in the village; the depth precision at 40 km (design §0 measured it does not
## change with far under Compatibility); that 5'000 m above the area is as high as anyone flies.

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_v060_09_far_terrain"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const HEIGHTS := "tests/shared/surroundings_fixture/generated/surroundings/fixture.f32"
## The shared fixture's grid: 6 x 7 vertices at 3000 m, its colour 15 x 18 pixels.
const COLUMNS := 6
const ROWS := 7
const SPACING_M := 3000.0
const COLOUR_SIZE := Vector2i(15, 18)
## The fixture's squares with four finite corners (brief v0.6.0-08's FINITE_SQUARES).
const DRAWN_SQUARES := 18
const TOLERANCE_M := 0.001
const FAR_M := 40000.0
const NEAR_M := 0.1
## How far above or below the area the camera is allowed for, in metres (the window's heights lie
## from 860 to 4611 m, design §0).
const HEIGHT_ALLOWANCE_M := 5000.0

var _cases := 0


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _write(change := Callable()) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.set_process(false)
	return main


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _far(main: Node3D) -> Node3D:
	var far: Node3D = main.get_node_or_null("Surroundings")
	assert_not_null(far, "the far terrain is built")
	return far


## The chunks of [param far]: its MeshInstance3D children but the skirt.
func _chunks(far: Node3D) -> Array[MeshInstance3D]:
	var chunks: Array[MeshInstance3D] = []
	for child in far.get_children():
		if child is MeshInstance3D and child.name != "Skirt":
			chunks.append(child)
	return chunks


## The fixture's grid points as the world config places them, by hand: for every vertex of a
## square whose four corners are finite, its (column, row) and its local position.
func _expected(world: WorldConfig) -> Dictionary:
	var heights := FileAccess.get_file_as_bytes(CompleteWorld.repo_file(HEIGHTS)).to_float32_array()
	assert_eq(heights.size(), COLUMNS * ROWS, "the fixture's 6 x 7 heights")
	var box: Dictionary = CompleteWorld.SURROUNDINGS_BOX
	var expected := {}
	var squares := 0
	for r in ROWS - 1:
		for c in COLUMNS - 1:
			var corners := [[c, r], [c + 1, r], [c, r + 1], [c + 1, r + 1]]
			var finite := true
			for corner: Array in corners:
				finite = finite and not is_nan(heights[corner[1] * COLUMNS + corner[0]])
			if not finite:
				continue
			squares += 1
			for corner: Array in corners:
				var e: float = box["e_min"] + SPACING_M * corner[0]
				var n: float = box["n_max"] - SPACING_M * corner[1]
				var h: float = heights[corner[1] * COLUMNS + corner[0]] + world.height_offset
				expected[Vector2i(corner[0], corner[1])] = world.to_local(e, n, h)
	assert_eq(squares, DRAWN_SQUARES, "the fixture's 18 squares with four finite corners")
	return expected


func test_the_far_terrain_is_built_in_the_main_scene_at_the_origin() -> void:
	var main := _main_with(_write())
	assert_false(main.get_node("UI/ErrorPanel").visible, "the complete world opens no panel")
	var far := _far(main)
	if far == null:
		return
	assert_eq(far.get_parent(), main, "Surroundings is a child of the main scene")
	assert_eq(far.global_transform, Transform3D.IDENTITY, "unturned, unscaled, at the origin")
	var chunks := _chunks(far)
	assert_gt(chunks.size(), 0, "at least one chunk")
	assert_not_null(far.get_node_or_null("Skirt"), "and the skirt")
	for child in far.get_children():
		assert_eq((child as Node3D).global_transform, Transform3D.IDENTITY, "%s" % child.name)
	for chunk in chunks:
		var material := chunk.get_active_material(0) as StandardMaterial3D
		assert_not_null(material, "%s: a StandardMaterial3D" % chunk.name)
		if material == null or material.albedo_texture == null:
			fail_test("%s: no far colour" % chunk.name)
			continue
		assert_eq(
			Vector2i(material.albedo_texture.get_size()), COLOUR_SIZE, "the far colour's pixels"
		)


func test_every_far_vertex_lies_where_the_world_config_puts_it() -> void:
	var path := _write()
	var world := WorldConfig.from_manifest(path)
	var far := _far(_main_with(path))
	if far == null or world == null:
		return
	var expected := _expected(world)
	var found := {}
	var vertices := 0
	for chunk in _chunks(far):
		var arrays := (chunk.mesh as ArrayMesh).surface_get_arrays(0)
		for v: Vector3 in arrays[Mesh.ARRAY_VERTEX]:
			vertices += 1
			var p := chunk.global_transform * v
			var nearest := Vector2i(-1, -1)
			var distance := INF
			for key: Vector2i in expected:
				var d := p.distance_to(expected[key])
				if d < distance:
					distance = d
					nearest = key
			assert_lt(distance, TOLERANCE_M, "(%f, %f, %f): at its grid point" % [p.x, p.y, p.z])
			found[nearest] = true
	assert_gt(vertices, 0, "the chunks hold vertices")
	assert_eq(found.size(), expected.size(), "every vertex of every drawn square is there")


func test_no_far_triangle_reaches_into_the_terrain_s_area() -> void:
	var path := _write()
	var world := WorldConfig.from_manifest(path)
	var far := _far(_main_with(path))
	if far == null or world == null:
		return
	var area: Dictionary = _parse(path)["world"]["areas"]["fixture"]
	var north_west := world.to_local(area["e_min"], area["n_max"], world.height_offset)
	var south_east := world.to_local(area["e_max"], area["n_min"], world.height_offset)
	var triangles := 0
	for chunk in _chunks(far):
		var arrays := (chunk.mesh as ArrayMesh).surface_get_arrays(0)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var count := indices.size() if not indices.is_empty() else points.size()
		for t in count / 3:
			var lo := Vector2(INF, INF)
			var hi := Vector2(-INF, -INF)
			for k in 3:
				var at := 3 * t + k
				var p := (
					chunk.global_transform * points[indices[at] if not indices.is_empty() else at]
				)
				lo = Vector2(minf(lo.x, p.x), minf(lo.y, p.z))
				hi = Vector2(maxf(hi.x, p.x), maxf(hi.y, p.z))
			triangles += 1
			var overlaps := (
				lo.x < south_east.x
				and hi.x > north_west.x
				and lo.y < south_east.z
				and hi.y > north_west.z
			)
			assert_false(overlaps, "triangle %d of %s lies over the area" % [t, chunk.name])
	assert_eq(triangles, 2 * DRAWN_SQUARES, "two triangles per drawn square")


func test_the_camera_s_far_plane_reaches_every_corner_of_the_window() -> void:
	var main := _main_with(_write())
	var camera: Camera3D = main.get_node("Camera")
	assert_almost_eq(camera.far, FAR_M, 0.001, "the main scene's camera: far 40 km")
	assert_almost_eq(camera.near, NEAR_M, 0.00001, "near 0.1 m, which sets the depth precision")
	var own := FreeFlyCamera.new()
	assert_almost_eq(own.far, FAR_M, 0.001, "FreeFlyCamera's own far")
	own.free()
	var areas: Dictionary = _parse(CompleteWorld.repo_file("config/world.json"))["areas"]
	var far_areas: Dictionary = _parse(CompleteWorld.repo_file("config/surroundings.json"))["areas"]
	assert_true(far_areas.has("village"), "config/surroundings.json names the village")
	for name: String in far_areas:
		var area: Dictionary = areas[name]
		var margin: float = far_areas[name]["margin_m"]
		var farthest := 0.0
		for e: float in [area["e_min"], area["e_max"]]:
			for n: float in [area["n_min"], area["n_max"]]:
				for corner_e: float in [area["e_min"] - margin, area["e_max"] + margin]:
					for corner_n: float in [area["n_min"] - margin, area["n_max"] + margin]:
						var d := Vector2(corner_e - e, corner_n - n).length()
						farthest = maxf(farthest, d)
		var reach := sqrt(farthest * farthest + HEIGHT_ALLOWANCE_M * HEIGHT_ALLOWANCE_M)
		assert_lt(reach, camera.far, "%s: every corner within the far plane" % name)
		assert_gt(reach, 20000.0, "%s: which the old 20 km did not reach (design §0)" % name)
