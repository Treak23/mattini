extends GutTest
## Pinning tests for brief M4-07: SurroundingsLoader builds the far mountains' mesh, which
## only casts shadows, from a SurroundingsGrid.
##
## Pinned decisions (m4-design §0 *Far mountains in Godot* and §7; brain.md H5, H16):
## SurroundingsLoader.create(grid, parent) adds to parent and returns a MeshInstance3D named
## "Surroundings": cast_shadow SHADOW_CASTING_SETTING_SHADOWS_ONLY (nothing drawn: the far
## mountains are drawn in M5), its transform the identity (unturned, unscaled, at the scene's
## origin), its mesh an ArrayMesh of one PRIMITIVE_TRIANGLES surface. For every grid square
## whose four vertices are finite, two triangles of those four vertices sharing a diagonal;
## a square with a NaN vertex (the cut, where the real terrain is) has none, and no vertex of
## the mesh is NaN (an AABB of NaN would break culling). Each triangle's front faces up:
## Godot's front faces are clockwise, so its right-hand normal (b − a) × (c − a) points down
## (H16). The vertex at row r, column c stands at WorldConfig.to_local of LV95
## (e_min + c·s, n_max − r·s), the origin subtracted in 64 bits first (H5), within 1 mm, and
## its y is the grid's height, exactly.
##
## The trap world (H5): the same fixture with the world's origin moved to E 2'618'250.13,
## N 1'101'750.44, which a 32-bit float holds only as 2'618'250.25 and 1'101'750.5, so a
## 32-bit subtraction puts every vertex 0.12 m east and 0.06 m south.
##
## Does NOT prove: that Godot draws the shadows these triangles cast, nor that the far shadow
## reaches the village (m4-design §0 measured it in Forward+ on lavapipe; Compatibility shows
## none; the owner's PC is the test); the real village's mesh (M4-10's run).

const SCRATCH_DIR := "user://test_m4_07_surroundings_loader"
const FIXTURE_DIR := "tests/shared/surroundings_fixture/generated"
const F32 := "surroundings/fixture.f32"
const TRAP_E := 2618250.13
const TRAP_N := 1101750.44
## The fixture's squares whose four vertices are finite: 30 squares, 12 touch the cut.
const FINITE_SQUARES := 18
const TOLERANCE_M := 0.001

var _built: Array[Node] = []


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _manifest_path() -> String:
	return _repo_file(FIXTURE_DIR.path_join("manifest.json"))


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func after_each() -> void:
	for node in _built:
		if is_instance_valid(node):
			node.free()
	_built.clear()


func after_all() -> void:
	for file in DirAccess.get_files_at(SCRATCH_DIR.path_join("surroundings")):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join("surroundings").path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR.path_join("surroundings"))
	for file in DirAccess.get_files_at(SCRATCH_DIR):
		DirAccess.remove_absolute(SCRATCH_DIR.path_join(file))
	DirAccess.remove_absolute(SCRATCH_DIR)


## The trap world: the fixture's manifest and heights, its origin moved off the float32 grid.
func _trap_manifest() -> String:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR.path_join("surroundings"))
	var manifest := _parse(_manifest_path())
	manifest["world"]["origin_lv95"] = {"e": TRAP_E, "n": TRAP_N}
	var path := SCRATCH_DIR.path_join("manifest.json")
	var out := FileAccess.open(path, FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	var f32 := FileAccess.open(SCRATCH_DIR.path_join(F32), FileAccess.WRITE)
	f32.store_buffer(FileAccess.get_file_as_bytes(_repo_file(FIXTURE_DIR.path_join(F32))))
	f32.close()
	return path


## [the MeshInstance3D, its world, its manifest] for the manifest at [param path], or [] when
## something on the way is missing (each step asserted).
func _build(path: String) -> Array:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "the world is read")
	var grid := SurroundingsGrid.from_manifest(path, world) if world != null else null
	assert_not_null(grid, "the surroundings are read")
	if grid == null:
		return []
	var parent := Node3D.new()
	_built.append(parent)
	var mesh_instance := SurroundingsLoader.create(grid, parent)
	assert_not_null(mesh_instance, "a MeshInstance3D is made")
	if mesh_instance == null:
		return []
	return [mesh_instance, world, _parse(path), parent]


## The mesh's triangles, each [a, b, c] as Vector3, read from its arrays (indexed or not).
func _triangles(mesh_instance: MeshInstance3D) -> Array:
	var mesh := mesh_instance.mesh as ArrayMesh
	assert_not_null(mesh, "the mesh is an ArrayMesh")
	if mesh == null or mesh.get_surface_count() != 1:
		assert_eq(mesh.get_surface_count() if mesh != null else 0, 1, "one surface")
		return []
	assert_eq(mesh.surface_get_primitive_type(0), Mesh.PRIMITIVE_TRIANGLES, "triangles")
	var arrays := mesh.surface_get_arrays(0)
	var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var indices: Variant = arrays[Mesh.ARRAY_INDEX]
	var order := PackedInt32Array()
	if indices == null or (indices as PackedInt32Array).is_empty():
		for i in vertices.size():
			order.append(i)
	else:
		order = indices
	var triangles := []
	for t in range(0, order.size() - 2, 3):
		triangles.append([vertices[order[t]], vertices[order[t + 1]], vertices[order[t + 2]]])
	return triangles


func _vertices(mesh_instance: MeshInstance3D) -> PackedVector3Array:
	var mesh := mesh_instance.mesh as ArrayMesh
	if mesh == null or mesh.get_surface_count() != 1:
		return PackedVector3Array()
	return mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]


## Where WorldConfig puts the grid vertex at [param column], [param row] of [param block]'s
## box (its x and z; y is the height), computed here from the block, not from the grid.
func _expected_xz(world: WorldConfig, block: Dictionary, column: int, row: int) -> Vector2:
	var box: Dictionary = block["lv95_box"]
	var s := float(block["spacing_m"])
	var e := float(box["e_min"]) + column * s
	var n := float(box["n_max"]) - row * s
	var local := world.to_local(e, n, world.height_offset)
	return Vector2(local.x, local.z)


## [column, row] of the grid vertex at [param p], or [] when p is not within 1 mm of one.
func _grid_index(world: WorldConfig, block: Dictionary, p: Vector3) -> Array:
	for row in int(block["rows"]):
		for column in int(block["columns"]):
			var xz := _expected_xz(world, block, column, row)
			if absf(xz.x - p.x) <= TOLERANCE_M and absf(xz.y - p.z) <= TOLERANCE_M:
				return [column, row]
	return []


func test_the_node_casts_shadows_only_and_is_unturned_at_the_origin() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var mesh_instance: MeshInstance3D = built[0]
	assert_eq(mesh_instance.name, &"Surroundings")
	assert_eq(mesh_instance.get_parent(), built[3], "it is added to the parent given")
	assert_eq(
		mesh_instance.cast_shadow,
		GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY,
		"it casts shadows and draws nothing"
	)
	assert_eq(mesh_instance.transform, Transform3D.IDENTITY, "unturned, unscaled, at the origin")


func test_two_triangles_per_finite_square_and_none_in_the_cut() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var mesh_instance: MeshInstance3D = built[0]
	var world: WorldConfig = built[1]
	var block: Dictionary = built[2]["surroundings"]
	var vertices := _vertices(mesh_instance)
	assert_gt(vertices.size(), 0, "the mesh has vertices")
	var not_finite := 0
	for v in vertices:
		if not v.is_finite():
			not_finite += 1
	assert_eq(not_finite, 0, "no vertex of the mesh is NaN")
	var box := mesh_instance.mesh.get_aabb() if mesh_instance.mesh != null else AABB()
	assert_true(box.position.is_finite() and box.size.is_finite(), "its AABB is finite: %s" % box)
	var triangles := _triangles(mesh_instance)
	assert_eq(triangles.size(), 2 * FINITE_SQUARES, "two triangles per square outside the cut")
	# Each triangle lies on one square's corners; each square's two cover its four corners.
	var squares := {}
	var stray := 0
	for triangle: Array in triangles:
		var corners := []
		for p: Vector3 in triangle:
			corners.append(_grid_index(world, block, p))
		if [] in corners:
			stray += 1
			continue
		var column := mini(mini(corners[0][0], corners[1][0]), corners[2][0])
		var row := mini(mini(corners[0][1], corners[1][1]), corners[2][1])
		var key := Vector2i(column, row)
		if not squares.has(key):
			squares[key] = {"triangles": 0, "corners": {}}
		squares[key]["triangles"] += 1
		for corner: Array in corners:
			if corner[0] - column > 1 or corner[1] - row > 1:
				stray += 1
			squares[key]["corners"][Vector2i(corner[0], corner[1])] = true
	assert_eq(stray, 0, "every triangle's corners are grid vertices of one square")
	assert_eq(squares.size(), FINITE_SQUARES, "one pair of triangles per finite square")
	var heights: PackedFloat32Array = (
		SurroundingsGrid.from_manifest(_manifest_path(), world).heights
	)
	for key: Vector2i in squares:
		assert_eq(squares[key]["triangles"], 2, "square %s holds two triangles" % key)
		assert_eq(squares[key]["corners"].size(), 4, "square %s: its four corners" % key)
		for corner: Vector2i in squares[key]["corners"]:
			var h := heights[corner.y * int(block["columns"]) + corner.x]
			assert_false(is_nan(h), "square %s has no vertex in the cut" % key)


func test_every_front_faces_up() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var triangles := _triangles(built[0])
	assert_gt(triangles.size(), 0, "the mesh has triangles")
	var wrong := 0
	for triangle: Array in triangles:
		var normal: Vector3 = (triangle[1] - triangle[0]).cross(triangle[2] - triangle[0])
		# Clockwise seen from above (Godot's front, H16): the right-hand normal points down.
		if not normal.y < 0.0:
			wrong += 1
	assert_eq(wrong, 0, "every triangle is clockwise seen from above (front faces up)")


func test_every_vertex_stands_where_the_world_config_puts_it_at_its_height() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var world: WorldConfig = built[1]
	var block: Dictionary = built[2]["surroundings"]
	var heights: PackedFloat32Array = (
		SurroundingsGrid.from_manifest(_manifest_path(), world).heights
	)
	var misplaced := []
	for v in _vertices(built[0]):
		var index := _grid_index(world, block, v)
		if index.is_empty():
			misplaced.append(v)
		elif v.y != heights[index[1] * int(block["columns"]) + index[0]]:
			misplaced.append([v, index])
	assert_eq(misplaced, [], "every vertex is a grid vertex at its own height")


func test_every_named_vertex_is_in_the_mesh_or_in_the_cut() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var vertices := _vertices(built[0])
	var named: Array = _parse(_repo_file("tests/shared/surroundings_vectors.json"))["vertices"]
	for v: Dictionary in named:
		var name := "row %d, column %d" % [v["row"], v["column"]]
		var at := Vector2(v["local_x"], v["local_z"])
		var found := []
		for p in vertices:
			if absf(p.x - at.x) <= TOLERANCE_M and absf(p.z - at.y) <= TOLERANCE_M:
				found.append(p.y)
		if v["local_y"] == null:
			assert_eq(found, [], "%s is in the cut: no vertex at %s" % [name, at])
		else:
			assert_gt(found.size(), 0, "%s: a vertex at %s" % [name, at])
			for y in found:
				assert_eq(y, float(v["local_y"]), "%s: its height" % name)


func test_the_trap_world_is_placed_in_64_bits() -> void:
	var built := _build(_trap_manifest())
	if built.is_empty():
		return
	var world: WorldConfig = built[1]
	var block: Dictionary = built[2]["surroundings"]
	var vertices := _vertices(built[0])
	# The north-west corner: E 2613000 − 2618250.13, −(N 1110000 − 1101750.44).
	var corner := Vector2(2613000.0 - TRAP_E, -(1110000.0 - TRAP_N))
	assert_almost_eq(corner, Vector2(-5250.13, -8249.56), Vector2.ONE * 1e-6, "the arithmetic")
	var at_corner := 0
	var misplaced := 0
	for v in vertices:
		if absf(v.x - corner.x) <= TOLERANCE_M and absf(v.z - corner.y) <= TOLERANCE_M:
			at_corner += 1
		if _grid_index(world, block, v).is_empty():
			misplaced += 1
	assert_gt(at_corner, 0, "a vertex at the north-west corner, within 1 mm (32 bits: 0.12 m off)")
	assert_eq(misplaced, 0, "every vertex within 1 mm of its 64-bit place")
