extends GutTest
## Tests for brief v0.6.0-12, the whole-range review's fix batch (docs/reviews/v0.6.0-round1.md,
## A1; the brief's decisions 1 to 4): the free-fly camera's floor over the far terrain. The brief
## has no pinning folder: these are the fixer's own, written before the change and seen red.
##
## The harm (A1, P1 in eight skeptics of eight): the camera was kept above the near terrain only
## (main.gd set height_at in _show_terrain and the near terrain's height is NaN outside the area
## box), so flying out of the box toward the Matterhorn took the camera into the far mountainside,
## where the back-face-culled far mesh vanishes. The floor is now the near terrain's inside the
## area box and the far terrain's outside it, the surface the far mesh draws.
##
## Decisions tested:
## - SurroundingsGrid.height_at(x, z): the local height of the surface SurroundingsLoader draws
##   under local (x, z), on the loader's own triangles (a, b, c) and (b, d, c) of a square (a the
##   north-west, b the north-east, c the south-west, d the south-east corner; the diagonal runs
##   from b to c), and NaN where nothing is drawn: outside the box, in the cut and in a square
##   with a NaN corner. A point on the line between two squares belongs to a drawn one of them,
##   the box's last row and column to the last square. Read against the triangles of the built
##   mesh (its ArrayMesh arrays), never against a formula written the same way twice.
## - The main scene's _ground_height is the near terrain's height where that is finite, else the
##   far terrain's, else NaN, null-safe for both; the camera's height_at is set when either is
##   built. A camera put under the far surface outside the box is lifted to the surface plus the
##   camera's clearance; with the terrain refused the far floor still holds; with the far block
##   absent nothing changes (today's floor: the near terrain inside the box, free outside it);
##   inside the area box the near terrain's height governs even where the far surface stands
##   elsewhere.
##
## Test data that can tell the right code from its likeliest wrong twins (lesson 34): the grid
## built here is 9 columns by 8 rows at 50 m (not square, so an exchanged x and z falls outside
## it), rising to the south-east, with a quadratic term that makes every drawn square non-planar
## by 13.5 m or more with both signs (so a flipped diagonal, a mirrored axis and a north-up z
## each give another height), its cut off the middle of both axes, its box 12 km west and 10 km
## north of the world's origin (the trap origin of test_m4_07_surroundings_loader.gd, E
## 2'618'250.13 and N 1'101'750.44, which a 32-bit float holds only as .25 and .5: the local
## coordinates are thousands of metres, a Vector3 holds them to a millimetre, brain.md H5).
##
## Does NOT prove: that the camera feels right or that the far terrain renders (no GPU; the
## owner's PC); that the real village's far surface and its near terrain agree at the area box's
## edge (they do not: the camera is lifted at the step and never lowered, the brief's decision 3;
## the test world's step is a synthetic one); that nothing else can put the camera under the
## surface (a fast move over a ridge between two checks, for one).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_v060_12_camera_floor"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const FIXTURE_MANIFEST := "tests/shared/surroundings_fixture/generated/manifest.json"
const FIXTURE_HEIGHTS := "tests/shared/surroundings_fixture/generated/surroundings/fixture.f32"
const TRAP_E := 2618250.13
const TRAP_N := 1101750.44
const COLUMNS := 9
const ROWS := 8
const SPACING_M := 50.0
const E_MIN := 2606000.0
const N_MAX := 1112000.0
## The vertices of columns 2 to 4 and rows 2 to 4 are NaN: the cut. Its box keeps the vertices at
## its edges (columns 1 and 5, rows 1 and 5), as the pipeline cuts.
const CUT_FIRST := 2
const CUT_LAST := 4
## How far above a surface a camera may stand and still be at the floor, and how much a height may
## differ: float32 vertices narrow x and z by up to a millimetre, at most 1.5 m per metre of slope.
const HEIGHT_TOLERANCE_M := 0.01
## How far outside a triangle, in its own barycentric units (a leg of 50 m is 1), a point is still
## taken as on it when the mesh decides what is drawn: float32 noise is 2e-5, a metre is 2e-2.
const COVER_TOLERANCE := 1e-3
const MIN_NON_PLANAR_M := 13.0
## The points tried in a drawn square, (u, v) with u east and v south from the north-west corner:
## three in the triangle (a, b, c) (u + v < 1), three in (b, d, c) (u + v > 1), two on the diagonal.
const INTERIOR_UV := [
	Vector2(0.2, 0.3),
	Vector2(0.55, 0.1),
	Vector2(0.1, 0.8),
	Vector2(0.9, 0.8),
	Vector2(0.6, 0.7),
	Vector2(0.3, 0.95),
	Vector2(0.5, 0.5),
	Vector2(0.25, 0.75),
]
## The four corners and the four edges' middles of a square.
const EDGE_UV := [
	Vector2(0.0, 0.0),
	Vector2(1.0, 0.0),
	Vector2(0.0, 1.0),
	Vector2(1.0, 1.0),
	Vector2(0.5, 0.0),
	Vector2(0.0, 0.5),
	Vector2(1.0, 0.5),
	Vector2(0.5, 1.0),
]
## The complete world's far terrain (complete_world.gd): vertex (c, r) at local x = -6500 + 3000 c
## and z = -9000 + 3000 r, its cut x -3500 to 5500 and z -6000 to 6000 around the terrain's area.
## Points in drawn far squares, outside the cut, where the fixture's heights differ widely.
const FAR_POINTS := [
	Vector2(-5000.0, 100.0),
	Vector2(7000.0, -2000.0),
	Vector2(1000.0, -8000.0),
	Vector2(2000.0, 7500.0)
]
## Under the surface by this much when a camera is put there.
const BELOW_M := 80.0

var _cases := 0
var _built: Array[Node] = []


func after_each() -> void:
	for node in _built:
		if is_instance_valid(node):
			node.free()
	_built.clear()


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _repo_file(rel: String) -> String:
	return CompleteWorld.repo_file(rel)


func _parse(path: String) -> Dictionary:
	return CompleteWorld.read_manifest(path)


## The test grid's height at vertex ([param column], [param row]): rising to the south-east, with a
## quadratic term (multiples of 4.5 m, so float32 holds every value exactly); NaN in the cut.
func _vertex_height(column: int, row: int) -> float:
	if column >= CUT_FIRST and column <= CUT_LAST and row >= CUT_FIRST and row <= CUT_LAST:
		return NAN
	var twist := (3 * column * column + 2 * row * row + 3 * column * row) % 7
	return 600.0 + 11.0 * column + 7.0 * row + 4.5 * twist


## True when the test grid's square whose north-west vertex is ([param column], [param row]) is
## drawn: its four corners are finite.
func _square_drawn(column: int, row: int) -> bool:
	for corner in 4:
		var h := _vertex_height(column + (corner & 1), row + (corner >> 1))
		if is_nan(h):
			return false
	return true


## Writes the manifest of the test grid (the shared surroundings fixture's, with this grid's
## block, the trap origin and the box 12 km west and 10 km north of it) and its files into a fresh
## folder; returns the manifest's path. [param heights] is the heights file's content.
func _write_grid(heights: PackedFloat32Array) -> String:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("grid_%d" % _cases)
	DirAccess.make_dir_recursive_absolute(dir.path_join("surroundings"))
	var f32 := heights.to_byte_array()
	var image := Image.create(COLUMNS - 1, ROWS - 1, false, Image.FORMAT_RGB8)
	image.fill(Color8(120, 130, 90))
	var jpg := image.save_jpg_to_buffer(0.92)
	var manifest := _parse(_repo_file(FIXTURE_MANIFEST))
	manifest["world"]["origin_lv95"] = {"e": TRAP_E, "n": TRAP_N}
	var block: Dictionary = manifest["surroundings"]
	var s := SPACING_M
	block["columns"] = float(COLUMNS)
	block["rows"] = float(ROWS)
	block["spacing_m"] = s
	block["lv95_box"] = {
		"e_max": E_MIN + (COLUMNS - 1) * s,
		"e_min": E_MIN,
		"n_max": N_MAX,
		"n_min": N_MAX - (ROWS - 1) * s,
	}
	block["cut_box"] = {
		"e_max": E_MIN + (CUT_LAST + 1) * s,
		"e_min": E_MIN + (CUT_FIRST - 1) * s,
		"n_max": N_MAX - (CUT_FIRST - 1) * s,
		"n_min": N_MAX - (CUT_LAST + 1) * s,
	}
	block["sha256"] = CompleteWorld.sha256(f32)
	block["colour_cell_m"] = s
	block["colour_columns"] = float(COLUMNS - 1)
	block["colour_rows"] = float(ROWS - 1)
	block["colour_sha256"] = CompleteWorld.sha256(jpg)
	block["colour_pixels_sha256"] = CompleteWorld.sha256(image.get_data())
	for pair in [[block["file"], f32], [block["colour_file"], jpg]]:
		var file := FileAccess.open(dir.path_join(pair[0]), FileAccess.WRITE)
		file.store_buffer(pair[1])
		file.close()
	var path := dir.path_join("manifest.json")
	var out := FileAccess.open(path, FileAccess.WRITE)
	out.store_string(JSON.stringify(manifest, "  ", true, true))
	out.close()
	return path


## The test grid's heights, row-major, rows from the north.
func _grid_heights() -> PackedFloat32Array:
	var heights := PackedFloat32Array()
	heights.resize(COLUMNS * ROWS)
	for row in ROWS:
		for column in COLUMNS:
			heights[row * COLUMNS + column] = _vertex_height(column, row)
	return heights


## {world, grid, root} of the test grid read through the real reader and drawn by the real
## loader, [param change] (a Callable taking the SurroundingsGrid) applied between the two.
func _build(change := Callable()) -> Dictionary:
	var path := _write_grid(_grid_heights())
	var world := WorldConfig.from_manifest(path)
	assert_not_null(world, "the world is read")
	var grid := SurroundingsGrid.from_manifest(path, world) if world != null else null
	assert_not_null(grid, "the test grid is read")
	if grid == null:
		return {}
	if change.is_valid():
		change.call(grid)
	var parent := Node3D.new()
	_built.append(parent)
	return {"world": world, "grid": grid, "root": SurroundingsLoader.create(grid, parent)}


## The local position of the point ([param u], [param v]) of the square ([param column],
## [param row]), in 64 bits, as the grid places its vertices (x_min + c·s) before the loader
## narrows them.
func _point(grid: SurroundingsGrid, column: int, row: int, uv: Vector2) -> Vector2:
	return Vector2(
		grid.x_min + (column + uv.x) * grid.spacing_m, grid.z_min + (row + uv.y) * grid.spacing_m
	)


func _chunks(root: Node) -> Array[MeshInstance3D]:
	var chunks: Array[MeshInstance3D] = []
	for child in root.get_children():
		if child is MeshInstance3D and String(child.name).begins_with("Chunk_"):
			chunks.append(child)
	return chunks


## The triangles of every chunk of [param root] as arrays of three Vector3, from the ArrayMesh's
## own arrays (its index array, or the vertices in order).
func _triangles(root: Node) -> Array:
	var triangles := []
	for chunk in _chunks(root):
		var arrays := (chunk.mesh as ArrayMesh).surface_get_arrays(0)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		var count := indices.size() if not indices.is_empty() else points.size()
		for t in count / 3:
			var corners := []
			for k in 3:
				var at := 3 * t + k
				corners.append(points[indices[at] if not indices.is_empty() else at])
			triangles.append(corners)
	return triangles


## The height of the surface the chunks of [param root] draw under local ([param x], [param z]),
## read off their triangles, or NaN where no triangle holds the point (COVER_TOLERANCE outside one
## still holds it: a point on an edge). The oracle of every comparison below.
func _mesh_height(root: Node, x: float, z: float) -> float:
	var best := -INF
	var height := NAN
	for corners: Array in _triangles(root):
		var a: Vector3 = corners[0]
		var b: Vector3 = corners[1]
		var c: Vector3 = corners[2]
		var span := (b.z - c.z) * (a.x - c.x) + (c.x - b.x) * (a.z - c.z)
		var wa := ((b.z - c.z) * (x - c.x) + (c.x - b.x) * (z - c.z)) / span
		var wb := ((c.z - a.z) * (x - c.x) + (a.x - c.x) * (z - c.z)) / span
		var wc := 1.0 - wa - wb
		var worst := minf(wa, minf(wb, wc))
		if worst > best:
			best = worst
			height = wa * a.y + wb * b.y + wc * c.y
	return height if best >= -COVER_TOLERANCE else NAN


## Asserts that height_at at ([param x], [param z]) is the mesh's height there, or NaN where the
## mesh draws nothing.
func _assert_floor(built: Dictionary, x: float, z: float, why: String) -> void:
	var grid: SurroundingsGrid = built["grid"]
	var drawn := _mesh_height(built["root"], x, z)
	var found: float = grid.height_at(x, z)
	if is_nan(drawn):
		assert_true(is_nan(found), "%s: nothing is drawn there, so NaN; found %s" % [why, found])
	else:
		assert_almost_eq(found, drawn, HEIGHT_TOLERANCE_M, "%s: the drawn surface's height" % why)


func test_the_grid_tells_a_flipped_diagonal_from_the_right_one() -> void:
	# Lesson 34: before trusting the comparisons below, the data must show the mistakes. In every
	# drawn square the four corners are far from one plane, so the two possible diagonals give
	# heights that differ by a quarter of that at (0.25, 0.25).
	var drawn := 0
	var signs := {}
	for row in ROWS - 1:
		for column in COLUMNS - 1:
			if not _square_drawn(column, row):
				continue
			drawn += 1
			var warp := (
				_vertex_height(column, row)
				+ _vertex_height(column + 1, row + 1)
				- _vertex_height(column + 1, row)
				- _vertex_height(column, row + 1)
			)
			assert_gt(
				absf(warp), MIN_NON_PLANAR_M, "square (%d, %d) is far from planar" % [column, row]
			)
			signs[warp > 0.0] = true
	assert_eq(drawn, 40, "40 of the 56 squares are drawn, 16 are the cut's")
	assert_eq(signs.size(), 2, "the warp has both signs: neither diagonal is the better fit")


func test_height_at_is_the_drawn_surface_in_both_triangles_of_every_drawn_square() -> void:
	var built := _build()
	if built.is_empty():
		return
	var grid: SurroundingsGrid = built["grid"]
	var tried := 0
	for row in ROWS - 1:
		for column in COLUMNS - 1:
			if not _square_drawn(column, row):
				continue
			for uv: Vector2 in INTERIOR_UV:
				var at := _point(grid, column, row, uv)
				var why := "square (%d, %d) at (%s, %s)" % [column, row, uv.x, uv.y]
				var found: float = grid.height_at(at.x, at.y)
				assert_false(is_nan(found), "%s: finite" % why)
				_assert_floor(built, at.x, at.y, why)
				tried += 1
	assert_eq(tried, 40 * INTERIOR_UV.size(), "every drawn square, every point")


func test_height_at_on_the_diagonal_is_the_height_along_the_edge_from_b_to_c() -> void:
	# Closed form, independent of the mesh: the point (1 - t, t) of a square lies on the diagonal
	# from b (north-east) to c (south-west), whose height is hb + t (hc - hb) on both triangles.
	var built := _build()
	if built.is_empty():
		return
	var grid: SurroundingsGrid = built["grid"]
	for row in ROWS - 1:
		for column in COLUMNS - 1:
			if not _square_drawn(column, row):
				continue
			var hb := _vertex_height(column + 1, row)
			var hc := _vertex_height(column, row + 1)
			for t: float in [0.1, 0.25, 0.5, 0.75, 0.9]:
				var at := _point(grid, column, row, Vector2(1.0 - t, t))
				var want := hb + t * (hc - hb)
				var why := "square (%d, %d), t %s" % [column, row, t]
				assert_almost_eq(grid.height_at(at.x, at.y), want, HEIGHT_TOLERANCE_M, why)


func test_the_loaders_mesh_draws_every_square_as_a_b_c_and_b_d_c() -> void:
	# The layout height_at stands on: the diagonal runs from the north-east to the south-west
	# vertex. Read off the mesh itself, by the grid positions of each triangle's three vertices.
	var built := _build()
	if built.is_empty():
		return
	var grid: SurroundingsGrid = built["grid"]
	var by_square := {}
	for corners: Array in _triangles(built["root"]):
		var cells := []
		for corner: Vector3 in corners:
			var column := roundi((corner.x - grid.x_min) / grid.spacing_m)
			var row := roundi((corner.z - grid.z_min) / grid.spacing_m)
			cells.append(Vector2i(column, row))
		var first := Vector2i(
			mini(cells[0].x, mini(cells[1].x, cells[2].x)),
			mini(cells[0].y, mini(cells[1].y, cells[2].y))
		)
		var offsets := []
		for cell: Vector2i in cells:
			offsets.append(cell - first)
		offsets.sort()
		if not by_square.has(first):
			by_square[first] = []
		by_square[first].append(offsets)
	var north_west := Vector2i(0, 0)
	var north_east := Vector2i(1, 0)
	var south_west := Vector2i(0, 1)
	var south_east := Vector2i(1, 1)
	var a_b_c := [north_west, north_east, south_west]
	var b_d_c := [north_east, south_east, south_west]
	a_b_c.sort()
	b_d_c.sort()
	assert_eq(by_square.size(), 40, "the drawn squares have triangles, the others none")
	for square: Vector2i in by_square:
		var found: Array = by_square[square]
		found.sort()
		var want := [a_b_c, b_d_c]
		want.sort()
		assert_eq(found, want, "square %s: the triangles (a, b, c) and (b, d, c)" % square)


func test_height_at_on_the_box_s_edges_and_corners_and_the_cut_s_edges() -> void:
	var built := _build()
	if built.is_empty():
		return
	var grid: SurroundingsGrid = built["grid"]
	# The four corners of the box are vertices: their own heights, the last row and column's far
	# edge belonging to the last square.
	var last_column := COLUMNS - 1
	var last_row := ROWS - 1
	for corner: Vector2i in [
		Vector2i(0, 0),
		Vector2i(last_column, 0),
		Vector2i(0, last_row),
		Vector2i(last_column, last_row)
	]:
		var x := grid.x_min + corner.x * grid.spacing_m
		var z := grid.z_min + corner.y * grid.spacing_m
		var want := _vertex_height(corner.x, corner.y)
		assert_almost_eq(grid.height_at(x, z), want, HEIGHT_TOLERANCE_M, "box corner %s" % corner)
	# Every corner and edge middle of every drawn square: these hold the box's four edges, the
	# lines between two drawn squares and the lines between a drawn square and the cut's, where a
	# point belongs to the drawn one.
	var tried := 0
	for row in ROWS - 1:
		for column in COLUMNS - 1:
			if not _square_drawn(column, row):
				continue
			for uv: Vector2 in EDGE_UV:
				var at := _point(grid, column, row, uv)
				var why := "square (%d, %d) at (%s, %s)" % [column, row, uv.x, uv.y]
				assert_false(is_nan(grid.height_at(at.x, at.y)), "%s: on a drawn edge" % why)
				_assert_floor(built, at.x, at.y, why)
				tried += 1
	assert_eq(tried, 40 * EDGE_UV.size(), "every drawn square, every edge point")
	# A point just inside the cut from a drawn square's edge is the cut's, not the square's.
	var edge := _point(grid, 0, 2, Vector2(1.0, 0.5))
	assert_false(is_nan(grid.height_at(edge.x, edge.y)), "the cut's west edge is drawn")
	assert_true(is_nan(grid.height_at(edge.x + 0.5, edge.y)), "half a metre into the cut is not")


func test_height_at_is_nan_in_the_cut_and_outside_the_box() -> void:
	var built := _build()
	if built.is_empty():
		return
	var grid: SurroundingsGrid = built["grid"]
	var cut := 0
	for row in ROWS - 1:
		for column in COLUMNS - 1:
			if _square_drawn(column, row):
				continue
			cut += 1
			for uv in [Vector2(0.5, 0.5), Vector2(0.2, 0.7), Vector2(0.8, 0.3)]:
				var at := _point(grid, column, row, uv)
				var why := "cut square (%d, %d) at (%s, %s)" % [column, row, uv.x, uv.y]
				assert_true(is_nan(grid.height_at(at.x, at.y)), "%s: nothing is drawn" % why)
				_assert_floor(built, at.x, at.y, why)
	assert_eq(cut, 16, "the cut's 16 squares")
	var west := grid.x_min
	var east := grid.x_min + (COLUMNS - 1) * grid.spacing_m
	var north := grid.z_min
	var south := grid.z_min + (ROWS - 1) * grid.spacing_m
	var middle_x := (west + east) / 2.0
	var middle_z := (north + south) / 2.0
	var outside := {
		"1 m west": Vector2(west - 1.0, 60.0 + north),
		"1 m east": Vector2(east + 1.0, 60.0 + north),
		"1 m north": Vector2(60.0 + west, north - 1.0),
		"1 m south": Vector2(60.0 + west, south + 1.0),
		"north-west corner": Vector2(west - 1.0, north - 1.0),
		"south-east corner": Vector2(east + 1.0, south + 1.0),
		"100 m west": Vector2(west - 100.0, middle_z),
		"100 km east": Vector2(east + 100000.0, middle_z),
		"the world's origin": Vector2(0.0, 0.0),
		"the point with x and z exchanged": Vector2(middle_z, middle_x),
	}
	for name: String in outside:
		var at: Vector2 = outside[name]
		assert_true(is_nan(grid.height_at(at.x, at.y)), "%s: outside the box, NaN" % name)
		_assert_floor(built, at.x, at.y, name)


func test_height_at_is_nan_in_the_four_squares_beside_a_nan_corner() -> void:
	# One finite vertex, (6, 5), made NaN: the loader draws none of the four squares around it, so
	# nothing is drawn under them, not even in the triangle that does not use the NaN corner.
	var built := _build(func(grid: SurroundingsGrid) -> void: grid.heights[5 * COLUMNS + 6] = NAN)
	if built.is_empty():
		return
	var grid: SurroundingsGrid = built["grid"]
	assert_true(is_nan(grid.height(6, 5)), "the corner is NaN")
	for square: Vector2i in [Vector2i(5, 4), Vector2i(6, 4), Vector2i(5, 5), Vector2i(6, 5)]:
		for uv in [Vector2(0.1, 0.1), Vector2(0.5, 0.5), Vector2(0.9, 0.9), Vector2(0.9, 0.1)]:
			var at := _point(grid, square.x, square.y, uv)
			var why := "square %s at (%s, %s)" % [square, uv.x, uv.y]
			assert_true(is_nan(grid.height_at(at.x, at.y)), "%s: undrawn, NaN" % why)
			_assert_floor(built, at.x, at.y, why)
	# The next squares away are drawn as before.
	var beside := _point(grid, 6, 3, Vector2(0.5, 0.5))
	assert_false(is_nan(grid.height_at(beside.x, beside.y)), "a square two rows north is drawn")
	_assert_floor(built, beside.x, beside.y, "a square two rows north")


func test_height_at_for_fractional_lv95_points_far_from_the_origin() -> void:
	# LV95 points with fractions of a metre, through the world's own conversion (the camera holds
	# its position as a Vector3, so x and z are narrowed to float32: a millimetre at 12 km).
	var built := _build()
	if built.is_empty():
		return
	var world: WorldConfig = built["world"]
	var grid: SurroundingsGrid = built["grid"]
	assert_gt(absf(grid.x_min), 10000.0, "the box is far from the origin in x")
	assert_gt(absf(grid.z_min), 9000.0, "and in z")
	var offsets := [Vector2(123.37, 77.77), Vector2(341.93, 301.19), Vector2(7.13, 11.29)]
	for offset: Vector2 in offsets:
		var e := E_MIN + offset.x
		var n := N_MAX - offset.y
		var local := world.to_local(e, n, world.height_offset)
		_assert_floor(built, local.x, local.z, "LV95 E %s N %s" % [e, n])
		# The same height from the LV95 numbers and the heights alone, never through the mesh.
		var east := offset.x / SPACING_M
		var south := offset.y / SPACING_M
		var column := floori(east)
		var row := floori(south)
		var u := east - column
		var v := south - row
		var ha := _vertex_height(column, row)
		var hb := _vertex_height(column + 1, row)
		var hc := _vertex_height(column, row + 1)
		var hd := _vertex_height(column + 1, row + 1)
		var want := (
			ha + u * (hb - ha) + v * (hc - ha)
			if u + v <= 1.0
			else hd + (1.0 - u) * (hc - hd) + (1.0 - v) * (hb - hd)
		)
		if _square_drawn(column, row):
			assert_almost_eq(grid.height_at(local.x, local.z), want, HEIGHT_TOLERANCE_M, "E %s" % e)
		else:
			assert_true(is_nan(grid.height_at(local.x, local.z)), "E %s: in the cut" % e)


## The main scene on the complete test world with [param change] (a Callable taking the manifest
## and the world's folder) applied, built by main.tscn itself: {main, camera, path}.
func _open(change := Callable()) -> Dictionary:
	_cases += 1
	var dir := SCRATCH_DIR.path_join("main_%d" % _cases)
	var wrapped := Callable()
	if change.is_valid():
		wrapped = func(manifest: Dictionary) -> void: change.call(manifest, dir)
	var path := CompleteWorld.write(dir, wrapped)
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.set_process(false)
	return {"main": main, "camera": main.get_node("Camera"), "path": path}


## The far terrain's node of [param main], asserted there.
func _far(main: Node) -> Node3D:
	var far: Node3D = main.get_node_or_null("Surroundings")
	assert_not_null(far, "the far terrain is built")
	return far


## Puts the camera at ([param x], [param y], [param z]) as set_view does and returns its height.
func _put(camera: FreeFlyCamera, x: float, y: float, z: float) -> float:
	camera.set_view(Vector3(x, y, z), 0.0, 0.0)
	return camera.position.y


## The complete world with its far terrain finite everywhere (the fixture's heights, its six NaN
## filled with 1500 to 1750 m) and cut by the terrain's own area box, as the pipeline cuts: the
## far surface then lies over the near terrain too, 900 m and more above it, so that which of the
## two the camera rests on shows.
func _finite_far_under_the_area(manifest: Dictionary, dir: String) -> void:
	var block: Dictionary = manifest["surroundings"]
	var heights := FileAccess.get_file_as_bytes(_repo_file(FIXTURE_HEIGHTS)).to_float32_array()
	var filled := 0
	for i in heights.size():
		if is_nan(heights[i]):
			heights[i] = 1500.0 + 50.0 * filled
			filled += 1
	assert_eq(filled, 6, "the fixture's six NaN")
	var data := heights.to_byte_array()
	var file := FileAccess.open(dir.path_join(block["file"]), FileAccess.WRITE)
	file.store_buffer(data)
	file.close()
	block["sha256"] = CompleteWorld.sha256(data)
	block["cut_box"] = manifest["world"]["areas"]["fixture"].duplicate()


func test_a_camera_under_the_far_surface_outside_the_box_is_lifted_onto_it() -> void:
	var opened := _open()
	var main: Node3D = opened["main"]
	var camera: FreeFlyCamera = opened["camera"]
	var far := _far(main)
	if far == null:
		return
	assert_true(camera.height_at.is_valid(), "the camera has a floor")
	for point: Vector2 in FAR_POINTS:
		var surface := _mesh_height(far, point.x, point.y)
		assert_false(is_nan(surface), "%s: the far surface is drawn there" % point)
		var under := _put(camera, point.x, surface - BELOW_M, point.y)
		var why := "%s: lifted from %s m under the surface" % [point, BELOW_M]
		assert_almost_eq(under, surface + camera.clearance_m, HEIGHT_TOLERANCE_M, why)
		var over := _put(camera, point.x, surface + 300.0, point.y)
		assert_almost_eq(over, surface + 300.0, 0.001, "%s: never lowered" % point)
		camera.set_view(Vector3(point.x, surface + 10.0, point.y), 0.0, 0.0)
		camera.fly(2.0, Vector3(0.0, -1.0, 0.0), false)
		var flown := camera.position.y
		assert_almost_eq(
			flown, surface + camera.clearance_m, HEIGHT_TOLERANCE_M, "%s: down" % point
		)


func test_flying_out_of_the_area_toward_the_far_peaks_keeps_the_camera_above_the_drawn_surface(
) -> void:
	# From the start view over the terrain, west and level at 150 m a second (the fast flight of 30
	# m/s: 5 times) to the far terrain's west edge, over the cut and then over the far squares
	# whose highest vertex stands 1870 m local (the fixture's). Every step the camera is at least
	# the clearance above whatever surface the far mesh draws under it.
	var opened := _open()
	var main: Node3D = opened["main"]
	var camera: FreeFlyCamera = opened["camera"]
	var far := _far(main)
	if far == null:
		return
	var start := camera.position
	camera.set_view(start, PI / 2.0, 0.0)
	var steps := 0
	var lifted := 0
	var checked := 0
	while camera.position.x > -6400.0 and steps < 200:
		camera.fly(1.0, Vector3(0.0, 0.0, -1.0), true)
		steps += 1
		var at := camera.position
		var surface := _mesh_height(far, at.x, at.z)
		if is_nan(surface):
			continue
		checked += 1
		assert_gte(
			at.y, surface + camera.clearance_m - HEIGHT_TOLERANCE_M, "step %d, x %s" % [steps, at.x]
		)
		if absf(at.y - (surface + camera.clearance_m)) < HEIGHT_TOLERANCE_M:
			lifted += 1
	assert_lt(camera.position.x, -6400.0, "the flight reached the far terrain's west edge")
	assert_gt(checked, 10, "the far terrain lay under the camera for many steps")
	assert_gt(lifted, 0, "and the camera was lifted onto it at least once")
	assert_gt(camera.position.y, start.y + 500.0, "the first far squares stand far above the start")


func test_inside_the_area_box_the_near_terrain_s_height_governs() -> void:
	var opened := _open(_finite_far_under_the_area)
	var main: Node3D = opened["main"]
	var camera: FreeFlyCamera = opened["camera"]
	var far := _far(main)
	if far == null:
		return
	var terrain: Terrain3D = main.get("_terrain")
	assert_not_null(terrain, "the terrain is built")
	if terrain == null:
		return
	var x := 1025.0
	var z := 16.0
	var near := terrain.data.get_height(Vector3(x, 0.0, z))
	var surface := _mesh_height(far, x, z)
	assert_false(is_nan(near), "the near terrain is there, inside its area box")
	assert_gt(surface - near, 800.0, "and the far surface over it stands far above it")
	var under := _put(camera, x, near - BELOW_M, z)
	assert_almost_eq(
		under, near + camera.clearance_m, HEIGHT_TOLERANCE_M, "the near terrain's floor"
	)
	# Twenty metres east of the box the near terrain is a hole: the far surface is the floor.
	var outside_x := 1055.0
	var hole := terrain.data.get_height(Vector3(outside_x, 0.0, z))
	assert_true(is_nan(hole), "the near terrain has nothing 20 m outside its area box")
	var far_surface := _mesh_height(far, outside_x, z)
	assert_false(is_nan(far_surface), "the far surface is drawn there")
	var outside := _put(camera, outside_x, near, z)
	assert_almost_eq(outside, far_surface + camera.clearance_m, HEIGHT_TOLERANCE_M, "the far floor")


func test_with_the_terrain_refused_the_far_floor_still_holds() -> void:
	var opened := _open(
		func(manifest: Dictionary, _dir: String) -> void: manifest["terrain"] = null
	)
	assert_push_error("TerrainGrid: " + opened["path"], "TerrainGrid logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	var main: Node3D = opened["main"]
	var camera: FreeFlyCamera = opened["camera"]
	var far := _far(main)
	if far == null:
		return
	assert_null(main.get("_terrain"), "there is no terrain")
	assert_true(camera.height_at.is_valid(), "the camera has a floor all the same")
	for point: Vector2 in FAR_POINTS:
		var surface := _mesh_height(far, point.x, point.y)
		var under := _put(camera, point.x, surface - BELOW_M, point.y)
		var why := "%s: lifted onto the far surface with no terrain" % point
		assert_almost_eq(under, surface + camera.clearance_m, HEIGHT_TOLERANCE_M, why)
	assert_true(is_nan(main._ground_height(0.0, 0.0)), "neither is under the cut's middle: NaN")


func test_without_the_far_terrain_the_floor_is_the_near_terrain_s_and_nothing_else() -> void:
	var gone := func(manifest: Dictionary, _dir: String) -> void: manifest["surroundings"] = null
	var opened := _open(gone)
	assert_push_error("SurroundingsGrid: " + opened["path"], "SurroundingsGrid logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	var main: Node3D = opened["main"]
	var camera: FreeFlyCamera = opened["camera"]
	assert_null(main.get_node_or_null("Surroundings"), "there is no far terrain")
	var terrain: Terrain3D = main.get("_terrain")
	if terrain == null:
		fail_test("the terrain is built")
		return
	var near := terrain.data.get_height(Vector3(1025.0, 0.0, 16.0))
	var inside := _put(camera, 1025.0, near - BELOW_M, 16.0)
	assert_almost_eq(
		inside, near + camera.clearance_m, HEIGHT_TOLERANCE_M, "inside: the near floor"
	)
	for point: Vector2 in FAR_POINTS:
		var free := _put(camera, point.x, -200.0, point.y)
		assert_almost_eq(free, -200.0, 0.001, "%s: free outside the box, as before" % point)
		assert_true(is_nan(main._ground_height(point.x, point.y)), "%s: no ground" % point)


func test_with_neither_terrain_nor_far_terrain_the_camera_flies_freely() -> void:
	var neither := func(manifest: Dictionary, _dir: String) -> void:
		manifest["terrain"] = null
		manifest["surroundings"] = null
	var opened := _open(neither)
	assert_push_error("TerrainGrid: " + opened["path"], "TerrainGrid logs its refusal")
	assert_push_error("SurroundingsGrid: " + opened["path"], "SurroundingsGrid logs its refusal")
	assert_push_error_count(2, "once each, and nothing else is refused")
	var main: Node3D = opened["main"]
	var camera: FreeFlyCamera = opened["camera"]
	assert_true(is_nan(main._ground_height(1025.0, 16.0)), "no ground anywhere, no error either")
	var free := _put(camera, 1025.0, -200.0, 16.0)
	assert_almost_eq(free, -200.0, 0.001, "free")
