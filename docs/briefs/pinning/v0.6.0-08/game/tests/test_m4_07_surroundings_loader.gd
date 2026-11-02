extends GutTest
## Pinning tests for brief v0.6.0-08 (brief M4-07's loader re-scoped by design §3): the far
## terrain is DRAWN, in chunks, with normals, UVs over its colour, one material and a skirt;
## the skirt double-sided with its own material (the release session's ruling of 2026-11-02).
##
## Pinned decisions (design §3; brief v0.6.0-08 decisions 4 to 8; brain.md H5, H16):
## SurroundingsLoader.create(grid, parent) adds to parent and returns a Node3D named
## "Surroundings" whose transform is the identity (unturned, unscaled, at the scene's origin).
## Its children, each with the identity transform:
## - one MeshInstance3D per chunk of CHUNK_SQUARES (80) × 80 grid squares, named
##   "Chunk_<i>_<j>" (i counting chunks west to east, j north to south; chunk (i, j) holds the
##   squares of columns [80i, 80i + 80) and rows [80j, 80j + 80)), cast_shadow
##   SHADOW_CASTING_SETTING_ON; a chunk with no triangle has no node. Its mesh is an ArrayMesh
##   of one PRIMITIVE_TRIANGLES surface with ARRAY_VERTEX, ARRAY_NORMAL and ARRAY_TEX_UV. For
##   every square whose four vertices are finite, two triangles of those four sharing a
##   diagonal; a square with a NaN vertex (the cut, where the real terrain is) has none, and no
##   vertex is NaN (an AABB of NaN would break culling). Each triangle's front faces up:
##   clockwise seen from above, so its right-hand normal (b − a) × (c − a) points down (H16).
##   The vertex at row r, column c stands at WorldConfig.to_local of LV95 (e_min + c·s,
##   n_max − r·s), the origin subtracted in 64 bits (H5), within 1 mm; its y is the grid's
##   height, exactly. Its normal is (−dh/dx, 1, −dh/dz) normalised, dh/dx and dh/dz by central
##   differences of the grid ((h[c+1] − h[c−1]) / 2s along +x = east, (h[r+1] − h[r−1]) / 2s
##   along +z = south), one-sided ((h[c+1] − h[c]) / s or (h[c] − h[c−1]) / s) where a
##   neighbour lies outside the box or is NaN; computed on the whole grid, so a vertex on a
##   chunk's edge has the same normal in both chunks. Its UV is (c / (columns − 1),
##   r / (rows − 1)), which is ((E − e_min) / (e_max − e_min), (n_max − N) / (n_max − n_min)):
##   the box's edges are the colour texture's edges.
## - one MeshInstance3D "Skirt", cast_shadow SHADOW_CASTING_SETTING_OFF: for every edge segment
##   of the cut (a grid edge between a drawn square and an undrawn one inside the box), a
##   vertical quad of two triangles from the segment's two vertices down 100 m, each quad with
##   its own four vertices, their normals horizontal (across the segment, either way), their
##   UVs those of the grid vertex above them. The skirt is DOUBLE-SIDED, so which way its front
##   faces is not pinned: seen from inside the cut it covers the crack where the far edge lies
##   above the near terrain, seen from outside it lies under the far surface's own edge.
## - every chunk draws with one StandardMaterial3D: albedo_texture the grid's colour_texture (an
##   albedo texture is read as sRGB, source colour), albedo white, filtered linear with mipmaps
##   and anisotropy, roughness 1, metallic 0, specular disabled, back faces culled, opaque,
##   per-pixel shading, fog not disabled (the scene's fog is the aerial perspective, design §3).
## - the skirt draws with a StandardMaterial3D of its own: the chunks' in every property above
##   (the same colour_texture object) but cull_mode CULL_DISABLED (both faces drawn).
##
## The fixture (6 × 7 at 3000 m, 6 NaN) is one chunk; the synthetic grid built here (241 × 172
## at 50 m, the village's spacing, its heights a sum of sines so that a one-sided difference
## differs from a central one) is nine chunks of which the middle one lies wholly in its cut.
## The trap world (H5): the fixture with the world's origin moved to E 2'618'250.13,
## N 1'101'750.44, which a 32-bit float holds only as 2'618'250.25 and 1'101'750.5, so a
## 32-bit subtraction puts every vertex 0.12 m west and 0.06 m south.
##
## Does NOT prove: that Godot draws this as it should (no GPU here; the owner's PC is the test);
## that the far shadows land right in the village; that the skirt hides the crack seen from the
## village (no GPU here); the real village's mesh and its build time (the main scene's run,
## brief v0.6.0-09).

const SCRATCH_DIR := "user://test_m4_07_surroundings_loader"
const FIXTURE_DIR := "tests/shared/surroundings_fixture/generated"
const F32 := "surroundings/fixture.f32"
const JPG := "surroundings/fixture_colour.jpg"
const TRAP_E := 2618250.13
const TRAP_N := 1101750.44
## The fixture's squares whose four vertices are finite: 30 squares, 12 touch the cut.
const FINITE_SQUARES := 18
## The fixture's cut ring: 3 × 4 undrawn squares, 2 × (3 + 4) edge segments.
const FIXTURE_SEGMENTS := 14
const TOLERANCE_M := 0.001
## Godot stores a normal in 16 bits a component (octahedral), so a read-back normal is off by
## about 1e-4 at most; a one-sided difference where a central one belongs is off by far more.
const NORMAL_TOLERANCE := 0.001
const UV_TOLERANCE := 1e-6
const SKIRT_DEPTH_M := 100.0
## The synthetic grid: 241 × 172 vertices at 50 m, its cut the vertices of columns and rows
## 81 to 159, so the 80 × 80 squares of chunk (1, 1) have no triangle.
const SYN_COLUMNS := 241
const SYN_ROWS := 172
const SYN_SPACING := 50.0
const SYN_E_MIN := 2610000.0
const SYN_N_MAX := 1110000.0

var _built: Array[Node] = []
var _cases := 0


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _manifest_path() -> String:
	return _repo_file(FIXTURE_DIR.path_join("manifest.json"))


func _parse(path: String) -> Dictionary:
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(path)), OK, "%s parses" % path)
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


func after_each() -> void:
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


## Writes [param manifest] and its two files into a fresh case folder; returns its path.
func _write_case(manifest: Dictionary, f32: PackedByteArray, jpg: PackedByteArray) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("case_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("surroundings"))
	var path := dir.path_join("manifest.json")
	var out := FileAccess.open(path, FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	for pair in [[manifest["surroundings"]["file"], f32], [JPG, jpg]]:
		var file := FileAccess.open(dir.path_join(pair[0]), FileAccess.WRITE)
		file.store_buffer(pair[1])
		file.close()
	return path


## The trap world: the fixture's manifest and files, its origin moved off the float32 grid.
func _trap_manifest() -> String:
	var manifest := _parse(_manifest_path())
	manifest["world"]["origin_lv95"] = {"e": TRAP_E, "n": TRAP_N}
	return _write_case(
		manifest,
		FileAccess.get_file_as_bytes(_repo_file(FIXTURE_DIR.path_join(F32))),
		FileAccess.get_file_as_bytes(_repo_file(FIXTURE_DIR.path_join(JPG)))
	)


func _synthetic_height(column: int, row: int) -> float:
	return 800.0 + 300.0 * sin(column / 7.0) + 200.0 * cos(row / 5.0) + 1.3 * column - 0.7 * row


func _in_synthetic_cut(column: int, row: int) -> bool:
	return column >= 81 and column <= 159 and row >= 81 and row <= 159


## The synthetic grid in the fixture's world: its heights file, a colour of 240 × 171 pixels
## of 50 m, and a block of the fixture's shape that describes them.
func _synthetic_manifest() -> String:
	var heights := PackedFloat32Array()
	heights.resize(SYN_COLUMNS * SYN_ROWS)
	for row in SYN_ROWS:
		for column in SYN_COLUMNS:
			var value := NAN if _in_synthetic_cut(column, row) else _synthetic_height(column, row)
			heights[row * SYN_COLUMNS + column] = value
	var f32 := heights.to_byte_array()
	var image := Image.create(SYN_COLUMNS - 1, SYN_ROWS - 1, false, Image.FORMAT_RGB8)
	image.fill(Color8(120, 130, 90))
	var jpg := image.save_jpg_to_buffer(0.92)
	var manifest := _parse(_manifest_path())
	var block: Dictionary = manifest["surroundings"]
	var e_max := SYN_E_MIN + (SYN_COLUMNS - 1) * SYN_SPACING
	var n_min := SYN_N_MAX - (SYN_ROWS - 1) * SYN_SPACING
	block["columns"] = float(SYN_COLUMNS)
	block["rows"] = float(SYN_ROWS)
	block["spacing_m"] = SYN_SPACING
	block["lv95_box"] = {"e_max": e_max, "e_min": SYN_E_MIN, "n_max": SYN_N_MAX, "n_min": n_min}
	block["cut_box"] = {
		"e_max": SYN_E_MIN + 160 * SYN_SPACING,
		"e_min": SYN_E_MIN + 80 * SYN_SPACING,
		"n_max": SYN_N_MAX - 80 * SYN_SPACING,
		"n_min": SYN_N_MAX - 160 * SYN_SPACING,
	}
	block["sha256"] = _sha256(f32)
	block["colour_cell_m"] = SYN_SPACING
	block["colour_columns"] = float(SYN_COLUMNS - 1)
	block["colour_rows"] = float(SYN_ROWS - 1)
	block["colour_sha256"] = _sha256(jpg)
	block["colour_pixels_sha256"] = _sha256(image.get_data())
	return _write_case(manifest, f32, jpg)


## {root, world, block, parent, grid} for the manifest at [param path], or {} when something on
## the way is missing (each step asserted).
func _build(path: String) -> Dictionary:
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "the world is read")
	var grid := SurroundingsGrid.from_manifest(path, world) if world != null else null
	assert_not_null(grid, "the surroundings are read")
	if grid == null:
		return {}
	var parent := Node3D.new()
	_built.append(parent)
	var root := SurroundingsLoader.create(grid, parent)
	assert_not_null(root, "a Node3D is made")
	if root == null:
		return {}
	var block: Dictionary = _parse(path)["surroundings"]
	return {"root": root, "world": world, "block": block, "parent": parent, "grid": grid}


func _chunks(root: Node) -> Array[MeshInstance3D]:
	var chunks: Array[MeshInstance3D] = []
	for child in root.get_children():
		if child is MeshInstance3D and String(child.name).begins_with("Chunk_"):
			chunks.append(child)
	return chunks


func _skirt(root: Node) -> MeshInstance3D:
	return root.get_node_or_null("Skirt") as MeshInstance3D


## The arrays of the one surface of [param mesh_instance]'s mesh, or [] (asserted).
func _arrays(mesh_instance: MeshInstance3D) -> Array:
	var mesh := mesh_instance.mesh as ArrayMesh
	assert_not_null(mesh, "%s: the mesh is an ArrayMesh" % mesh_instance.name)
	if mesh == null or mesh.get_surface_count() != 1:
		assert_eq(mesh.get_surface_count() if mesh != null else 0, 1, "one surface")
		return []
	assert_eq(mesh.surface_get_primitive_type(0), Mesh.PRIMITIVE_TRIANGLES, "triangles")
	return mesh.surface_get_arrays(0)


## The vertex order of the triangles of [param arrays] (its index array, or 0, 1, 2, …).
func _order(arrays: Array) -> PackedInt32Array:
	var indices: Variant = arrays[Mesh.ARRAY_INDEX]
	if indices != null and not (indices as PackedInt32Array).is_empty():
		return indices
	var order := PackedInt32Array()
	for i in (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size():
		order.append(i)
	return order


## Each triangle of [param mesh_instance] as [a, b, c] vertex indices into its arrays.
func _triangle_indices(arrays: Array) -> Array:
	var order := _order(arrays)
	var triangles := []
	for t in range(0, order.size() - 2, 3):
		triangles.append([order[t], order[t + 1], order[t + 2]])
	return triangles


## Where WorldConfig puts the grid vertex at [param column], [param row] of [param block]'s box
## (its x and z), computed here from the block and the world, not from the grid.
func _expected_xz(world: WorldConfig, block: Dictionary, column: int, row: int) -> Vector2:
	var box: Dictionary = block["lv95_box"]
	var s := float(block["spacing_m"])
	var local := world.to_local(
		float(box["e_min"]) + column * s, float(box["n_max"]) - row * s, world.height_offset
	)
	return Vector2(local.x, local.z)


## The grid vertex (column, row) at [param p] within 1 mm, or (-1, -1).
func _grid_index(world: WorldConfig, block: Dictionary, p: Vector3) -> Vector2i:
	var origin := _expected_xz(world, block, 0, 0)
	var s := float(block["spacing_m"])
	var column := roundi((p.x - origin.x) / s)
	var row := roundi((p.z - origin.y) / s)
	if column < 0 or row < 0 or column >= int(block["columns"]) or row >= int(block["rows"]):
		return Vector2i(-1, -1)
	var xz := _expected_xz(world, block, column, row)
	if absf(xz.x - p.x) > TOLERANCE_M or absf(xz.y - p.z) > TOLERANCE_M:
		return Vector2i(-1, -1)
	return Vector2i(column, row)


func _height(grid: SurroundingsGrid, at: Vector2i) -> float:
	return grid.heights[at.y * grid.columns + at.x]


func _finite(grid: SurroundingsGrid, column: int, row: int) -> bool:
	if column < 0 or row < 0 or column >= grid.columns or row >= grid.rows:
		return false
	return not is_nan(grid.heights[row * grid.columns + column])


## True when the square whose north-west vertex is (column, row) has four finite vertices.
func _drawn(grid: SurroundingsGrid, column: int, row: int) -> bool:
	return (
		_finite(grid, column, row)
		and _finite(grid, column + 1, row)
		and _finite(grid, column, row + 1)
		and _finite(grid, column + 1, row + 1)
	)


## The normal decision 6 gives the vertex (column, row), computed here in 64 bits.
func _expected_normal(grid: SurroundingsGrid, column: int, row: int) -> Vector3:
	var s := grid.spacing_m
	var h := grid.heights[row * grid.columns + column]
	var slopes := []
	for step: Vector2i in [Vector2i(1, 0), Vector2i(0, 1)]:
		var back := _finite(grid, column - step.x, row - step.y)
		var ahead := _finite(grid, column + step.x, row + step.y)
		var h_back := grid.heights[(row - step.y) * grid.columns + column - step.x] if back else h
		var h_ahead := grid.heights[(row + step.y) * grid.columns + column + step.x] if ahead else h
		var run := s * ((1 if back else 0) + (1 if ahead else 0))
		slopes.append((h_ahead - h_back) / run if run > 0.0 else 0.0)
	return Vector3(-slopes[0], 1.0, -slopes[1]).normalized()


func test_the_root_is_unturned_and_holds_drawn_chunks_and_a_skirt() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var root: Node3D = built["root"]
	assert_eq(root.name, &"Surroundings")
	assert_eq(root.get_parent(), built["parent"], "it is added to the parent given")
	assert_eq(root.transform, Transform3D.IDENTITY, "unturned, unscaled, at the origin")
	var names := []
	for child in root.get_children():
		names.append(String(child.name))
		assert_eq((child as Node3D).transform, Transform3D.IDENTITY, "%s unturned" % child.name)
	names.sort()
	assert_eq(names, ["Chunk_0_0", "Skirt"], "the fixture is one chunk, and the skirt")
	var chunks := _chunks(root)
	for chunk in chunks:
		assert_eq(
			chunk.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_ON, "a chunk is drawn"
		)
	var skirt := _skirt(root)
	assert_not_null(skirt, "the skirt is a MeshInstance3D")
	if skirt != null:
		assert_eq(
			skirt.cast_shadow,
			GeometryInstance3D.SHADOW_CASTING_SETTING_OFF,
			"the skirt never throws a shadow line into the village"
		)


func test_chunks_of_80_squares_and_none_wholly_in_the_cut() -> void:
	assert_eq(SurroundingsLoader.CHUNK_SQUARES, 80, "4 km chunks at 50 m")
	var built := _build(_synthetic_manifest())
	if built.is_empty():
		return
	var world: WorldConfig = built["world"]
	var block: Dictionary = built["block"]
	var grid: SurroundingsGrid = built["grid"]
	var names := []
	for chunk in _chunks(built["root"]):
		names.append(String(chunk.name))
	names.sort()
	var expected := []
	for j in 3:
		for i in 3:
			if not (i == 1 and j == 1):
				expected.append("Chunk_%d_%d" % [i, j])
	expected.sort()
	assert_eq(names, expected, "chunks (i, j) of 80 squares; (1, 1) lies in the cut")
	for chunk in _chunks(built["root"]):
		var parts := String(chunk.name).split("_")
		var i := int(parts[1])
		var j := int(parts[2])
		var arrays := _arrays(chunk)
		if arrays.is_empty():
			continue
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var outside := 0
		for v in vertices:
			var at := _grid_index(world, block, v)
			var c_ok := at.x >= 80 * i and at.x <= mini(80 * i + 80, grid.columns - 1)
			var r_ok := at.y >= 80 * j and at.y <= mini(80 * j + 80, grid.rows - 1)
			if at.x < 0 or not c_ok or not r_ok:
				outside += 1
		assert_eq(outside, 0, "%s: every vertex is a vertex of its own squares" % chunk.name)
		var finite := 0
		for row in range(80 * j, mini(80 * j + 80, grid.rows - 1)):
			for column in range(80 * i, mini(80 * i + 80, grid.columns - 1)):
				if _drawn(grid, column, row):
					finite += 1
		assert_eq(
			_triangle_indices(arrays).size(), 2 * finite, "%s: two per finite square" % chunk.name
		)
		var box := chunk.mesh.get_aabb()
		assert_true(box.position.is_finite() and box.size.is_finite(), "%s: AABB" % chunk.name)


func test_two_triangles_per_finite_square_and_none_in_the_cut() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var world: WorldConfig = built["world"]
	var block: Dictionary = built["block"]
	var grid: SurroundingsGrid = built["grid"]
	var squares := {}
	var stray := 0
	var not_finite := 0
	var triangles := 0
	for chunk in _chunks(built["root"]):
		var arrays := _arrays(chunk)
		if arrays.is_empty():
			continue
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		for v in vertices:
			if not v.is_finite():
				not_finite += 1
		var box := chunk.mesh.get_aabb()
		assert_true(box.position.is_finite() and box.size.is_finite(), "its AABB is finite")
		for triangle: Array in _triangle_indices(arrays):
			triangles += 1
			var corners := []
			for index: int in triangle:
				corners.append(_grid_index(world, block, vertices[index]))
			if Vector2i(-1, -1) in corners:
				stray += 1
				continue
			var key := Vector2i(
				mini(mini(corners[0].x, corners[1].x), corners[2].x),
				mini(mini(corners[0].y, corners[1].y), corners[2].y)
			)
			if not squares.has(key):
				squares[key] = {"triangles": 0, "corners": {}}
			squares[key]["triangles"] += 1
			for corner: Vector2i in corners:
				if corner.x - key.x > 1 or corner.y - key.y > 1:
					stray += 1
				squares[key]["corners"][corner] = true
	assert_eq(not_finite, 0, "no vertex of the mesh is NaN")
	assert_eq(triangles, 2 * FINITE_SQUARES, "two triangles per square outside the cut")
	assert_eq(stray, 0, "every triangle's corners are grid vertices of one square")
	assert_eq(squares.size(), FINITE_SQUARES, "one pair of triangles per finite square")
	for key: Vector2i in squares:
		assert_eq(squares[key]["triangles"], 2, "square %s holds two triangles" % key)
		assert_eq(squares[key]["corners"].size(), 4, "square %s: its four corners" % key)
		assert_true(_drawn(grid, key.x, key.y), "square %s has no vertex in the cut" % key)


func test_every_front_faces_up() -> void:
	for path in [_manifest_path(), _synthetic_manifest()]:
		var built := _build(path)
		if built.is_empty():
			return
		var wrong := 0
		var count := 0
		for chunk in _chunks(built["root"]):
			var arrays := _arrays(chunk)
			if arrays.is_empty():
				continue
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			for t: Array in _triangle_indices(arrays):
				count += 1
				var normal := (vertices[t[1]] - vertices[t[0]]).cross(
					vertices[t[2]] - vertices[t[0]]
				)
				# Clockwise seen from above (Godot's front, H16): the right-hand normal points down.
				if not normal.y < 0.0:
					wrong += 1
		assert_gt(count, 0, "the mesh has triangles")
		assert_eq(wrong, 0, "every triangle is clockwise seen from above (front faces up)")


func test_every_vertex_stands_where_the_world_config_puts_it_at_its_height() -> void:
	for path in [_manifest_path(), _synthetic_manifest()]:
		var built := _build(path)
		if built.is_empty():
			return
		var misplaced := []
		var count := 0
		for chunk in _chunks(built["root"]):
			var arrays := _arrays(chunk)
			if arrays.is_empty():
				continue
			for v: Vector3 in arrays[Mesh.ARRAY_VERTEX]:
				count += 1
				var at := _grid_index(built["world"], built["block"], v)
				if at.x < 0:
					misplaced.append(v)
				elif v.y != _height(built["grid"], at):
					misplaced.append([v, at])
		assert_gt(count, 0, "the mesh has vertices")
		assert_eq(misplaced.slice(0, 5), [], "every vertex is a grid vertex at its own height")


func test_every_named_vertex_is_in_the_mesh_or_in_the_cut() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var vertices := PackedVector3Array()
	for chunk in _chunks(built["root"]):
		var arrays := _arrays(chunk)
		if not arrays.is_empty():
			vertices.append_array(arrays[Mesh.ARRAY_VERTEX])
	var named: Array = _parse(_repo_file("tests/shared/surroundings_vectors.json"))["vertices"]
	assert_eq(named.size(), 14, "the vectors name 14 vertices")
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
	# The north-west corner: E 2613000 − 2618250.13, −(N 1110000 − 1101750.44).
	var corner := Vector2(2613000.0 - TRAP_E, -(1110000.0 - TRAP_N))
	assert_almost_eq(corner, Vector2(-5250.13, -8249.56), Vector2.ONE * 1e-6, "the arithmetic")
	var at_corner := 0
	var misplaced := 0
	for chunk in _chunks(built["root"]):
		var arrays := _arrays(chunk)
		if arrays.is_empty():
			continue
		for v: Vector3 in arrays[Mesh.ARRAY_VERTEX]:
			if absf(v.x - corner.x) <= TOLERANCE_M and absf(v.z - corner.y) <= TOLERANCE_M:
				at_corner += 1
			if _grid_index(built["world"], built["block"], v).x < 0:
				misplaced += 1
	assert_gt(at_corner, 0, "a vertex at the north-west corner, within 1 mm (32 bits: 0.12 m off)")
	assert_eq(misplaced, 0, "every vertex within 1 mm of its 64-bit place")


func test_normals_by_central_differences_one_sided_at_the_edges() -> void:
	for path in [_manifest_path(), _synthetic_manifest()]:
		var built := _build(path)
		if built.is_empty():
			return
		var grid: SurroundingsGrid = built["grid"]
		var wrong := []
		var count := 0
		for chunk in _chunks(built["root"]):
			var arrays := _arrays(chunk)
			if arrays.is_empty():
				continue
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: Variant = arrays[Mesh.ARRAY_NORMAL]
			assert_true(normals is PackedVector3Array, "%s has normals" % chunk.name)
			if not normals is PackedVector3Array or normals.size() != vertices.size():
				continue
			for k in vertices.size():
				var at := _grid_index(built["world"], built["block"], vertices[k])
				if at.x < 0:
					continue
				count += 1
				var want := _expected_normal(grid, at.x, at.y)
				var off: Vector3 = (normals[k] - want).abs()
				if maxf(off.x, maxf(off.y, off.z)) > NORMAL_TOLERANCE:
					wrong.append([at, normals[k], want])
		assert_gt(count, 0, "normals were read")
		assert_eq(wrong.slice(0, 5), [], "each normal is the grid's differences (%s)" % path)


func test_uvs_span_the_box_north_west_at_0_0() -> void:
	for path in [_manifest_path(), _synthetic_manifest()]:
		var built := _build(path)
		if built.is_empty():
			return
		var grid: SurroundingsGrid = built["grid"]
		var wrong := []
		var count := 0
		for chunk in _chunks(built["root"]):
			var arrays := _arrays(chunk)
			if arrays.is_empty():
				continue
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var uvs: Variant = arrays[Mesh.ARRAY_TEX_UV]
			assert_true(uvs is PackedVector2Array, "%s has UVs" % chunk.name)
			if not uvs is PackedVector2Array or uvs.size() != vertices.size():
				continue
			for k in vertices.size():
				var at := _grid_index(built["world"], built["block"], vertices[k])
				if at.x < 0:
					continue
				count += 1
				var want := Vector2(float(at.x) / (grid.columns - 1), float(at.y) / (grid.rows - 1))
				if (uvs[k] - want).abs().x > UV_TOLERANCE or (uvs[k] - want).abs().y > UV_TOLERANCE:
					wrong.append([at, uvs[k], want])
		assert_gt(count, 0, "UVs were read")
		assert_eq(wrong.slice(0, 5), [], "u east, v south, 0 to 1 over the box (%s)" % path)


## The cut's edge segments of [param grid]: {[a, b] (the two grid vertices): outward (x, z)}.
func _expected_segments(grid: SurroundingsGrid) -> Dictionary:
	var segments := {}
	for row in grid.rows - 1:
		for column in range(1, grid.columns - 1):
			var west := _drawn(grid, column - 1, row)
			var east := _drawn(grid, column, row)
			if west != east:
				var key := [Vector2i(column, row), Vector2i(column, row + 1)]
				segments[key] = Vector2(1.0 if east else -1.0, 0.0)
	for row in range(1, grid.rows - 1):
		for column in grid.columns - 1:
			var north := _drawn(grid, column, row - 1)
			var south := _drawn(grid, column, row)
			if north != south:
				var key := [Vector2i(column, row), Vector2i(column + 1, row)]
				segments[key] = Vector2(0.0, 1.0 if south else -1.0)
	return segments


func test_the_skirt_hangs_100_m_from_the_cut_s_edge_double_sided() -> void:
	for path in [_manifest_path(), _synthetic_manifest()]:
		var built := _build(path)
		if built.is_empty():
			return
		var grid: SurroundingsGrid = built["grid"]
		var skirt := _skirt(built["root"])
		assert_not_null(skirt, "a skirt")
		if skirt == null:
			return
		assert_eq(
			skirt.cast_shadow,
			GeometryInstance3D.SHADOW_CASTING_SETTING_OFF,
			"the skirt casts no shadow (%s)" % path
		)
		var skirt_material := skirt.get_active_material(0) as BaseMaterial3D
		assert_not_null(skirt_material, "the skirt has a material (%s)" % path)
		if skirt_material != null:
			assert_eq(
				skirt_material.cull_mode,
				BaseMaterial3D.CULL_DISABLED,
				"the skirt is double-sided: both faces drawn (%s)" % path
			)
		var arrays := _arrays(skirt)
		if arrays.is_empty():
			return
		var expected := _expected_segments(grid)
		if path == _manifest_path():
			assert_eq(expected.size(), FIXTURE_SEGMENTS, "the fixture's ring")
		else:
			assert_eq(expected.size(), 320, "the synthetic ring: 4 × 80")
		var found := {}
		var problems := []
		var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
		for t: Array in _triangle_indices(arrays):
			var cells := {}
			var tops := 0
			var bottoms := 0
			for index: int in t:
				var v := vertices[index]
				var at := _grid_index(built["world"], built["block"], v)
				if at.x < 0:
					problems.append(["not above a grid vertex", v])
					continue
				cells[at] = true
				var h := _height(grid, at)
				if v.y == h:
					tops += 1
				elif absf(v.y - (h - SKIRT_DEPTH_M)) <= TOLERANCE_M:
					bottoms += 1
				else:
					problems.append(["neither at its height nor 100 m below", v, h])
				var want_uv := Vector2(
					float(at.x) / (grid.columns - 1), float(at.y) / (grid.rows - 1)
				)
				if (uvs[index] - want_uv).length() > UV_TOLERANCE * 2.0:
					problems.append(["uv", at, uvs[index], want_uv])
			var key := cells.keys()
			key.sort()
			if key.size() != 2 or tops == 0 or bottoms == 0:
				problems.append(["not a vertical quad's triangle", key, tops, bottoms])
				continue
			if not expected.has(key):
				problems.append(["not an edge segment of the cut", key])
				continue
			found[key] = found.get(key, 0) + 1
			var a := vertices[t[0]]
			var face := (vertices[t[1]] - a).cross(vertices[t[2]] - a).normalized()
			var out: Vector2 = expected[key]
			var across := Vector3(out.x, 0.0, out.y)
			if absf(face.y) > 1e-4 or absf(face.dot(across)) < 0.999:
				problems.append(["not a vertical face along the segment", key, face, across])
			for index: int in t:
				if absf(normals[index].dot(across)) < 0.999:
					problems.append(["normal not horizontal across", key, normals[index], across])
		assert_eq(problems.slice(0, 5), [], "every skirt triangle is right (%s)" % path)
		var not_two := []
		for key in expected:
			if found.get(key, 0) != 2:
				not_two.append([key, found.get(key, 0)])
		assert_eq(not_two.slice(0, 5), [], "two triangles on every edge segment, none elsewhere")
		assert_eq(found.size(), expected.size(), "one quad per edge segment")


func test_one_material_textured_with_the_colour_the_skirt_its_own() -> void:
	var built := _build(_manifest_path())
	if built.is_empty():
		return
	var grid: SurroundingsGrid = built["grid"]
	var drawn: Array[MeshInstance3D] = _chunks(built["root"])
	var first: Variant = null
	for mesh_instance in drawn:
		if mesh_instance == null:
			continue
		var material := mesh_instance.get_active_material(0)
		if first == null:
			first = material
		assert_same(material, first, "%s draws with the one material" % mesh_instance.name)
	var material := first as StandardMaterial3D
	assert_not_null(material, "a StandardMaterial3D")
	if material == null:
		return
	assert_same(material.albedo_texture, grid.colour_texture, "albedo: the colour texture")
	assert_eq(material.albedo_color, Color.WHITE, "the colour as it is")
	assert_eq(
		material.texture_filter,
		BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC,
		"mipmaps and anisotropy (seen at a grazing angle from 30 km)"
	)
	assert_eq(material.roughness, 1.0, "roughness 1")
	assert_eq(material.metallic, 0.0, "not metallic")
	assert_eq(material.specular_mode, BaseMaterial3D.SPECULAR_DISABLED, "no specular")
	assert_eq(material.cull_mode, BaseMaterial3D.CULL_BACK, "back faces culled")
	assert_eq(material.transparency, BaseMaterial3D.TRANSPARENCY_DISABLED, "opaque")
	assert_eq(material.shading_mode, BaseMaterial3D.SHADING_MODE_PER_PIXEL, "lit per pixel")
	assert_false(material.disable_fog, "the scene's fog applies (aerial perspective)")
	var skirt := _skirt(built["root"])
	assert_not_null(skirt, "a skirt")
	if skirt == null:
		return
	var own := skirt.get_active_material(0) as StandardMaterial3D
	assert_not_null(own, "the skirt draws with a StandardMaterial3D")
	if own == null:
		return
	assert_not_same(own, material, "the skirt's material is its own, not the chunks'")
	assert_eq(own.cull_mode, BaseMaterial3D.CULL_DISABLED, "the skirt: both faces drawn")
	assert_same(own.albedo_texture, grid.colour_texture, "the skirt: the same colour texture")
	assert_eq(own.albedo_color, Color.WHITE, "the skirt: the colour as it is")
	assert_eq(own.texture_filter, material.texture_filter, "the skirt: the chunks' filter")
	assert_eq(own.roughness, 1.0, "the skirt: roughness 1")
	assert_eq(own.metallic, 0.0, "the skirt: not metallic")
	assert_eq(own.specular_mode, BaseMaterial3D.SPECULAR_DISABLED, "the skirt: no specular")
	assert_eq(own.transparency, BaseMaterial3D.TRANSPARENCY_DISABLED, "the skirt: opaque")
	assert_eq(own.shading_mode, BaseMaterial3D.SHADING_MODE_PER_PIXEL, "the skirt: per pixel")
	assert_false(own.disable_fog, "the skirt: the scene's fog applies")
