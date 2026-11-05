class_name SurroundingsLoader
extends RefCounted
## Builds the far terrain from a SurroundingsGrid and draws it (docs/SPEC.md §8; brief
## v0.6.0-08, design §3): a Node3D "Surroundings" with one MeshInstance3D per chunk of
## CHUNK_SQUARES × CHUNK_SQUARES grid squares and a double-sided skirt along the edge of the
## cut. Everything is built at load on the main thread, from index arrays.
##
## Vertex (c, r) stands at (x_min + c·s, height, z_min + r·s): x_min and z_min come from the
## WorldConfig (the grid read them through it, in 64 bits), c·s and r·s are added here in
## GDScript's 64-bit float and narrowed once more; y is the grid's local height. Only finite
## vertices are built, and a square with a NaN corner (the cut, where the near terrain is) has
## no triangle. Front faces are clockwise seen from above (brain.md H16): with a the north-west,
## b the north-east, c the south-west and d the south-east corner of a square, (a, b, c) and
## (b, d, c) (SurroundingsGrid.SQUARE_TRIANGLES, the one convention this mesh and
## SurroundingsGrid.height_at, the camera's floor over it, both use). A vertex's normal is
## (−dh/dx, 1, −dh/dz) normalised, by central differences of the whole grid (one-sided where a
## neighbour lies outside the box or is NaN), so a vertex that two chunks share has one normal; its
## UV is (c / (columns − 1), r / (rows − 1)), so the box's edges are the colour texture's edges (u
## east, v south).
##
## The skirt is a vertical quad of two triangles hung SKIRT_DEPTH_M down from each grid edge
## between a drawn square and an undrawn one, inside the box: seen from inside the cut it covers
## the crack where the far edge lies above the near terrain. Each quad has its own four
## vertices, normals horizontal across the segment, facing the cut, and the UVs of the grid
## vertex above them. It is drawn from both sides, with a material of its own.

const CHUNK_SQUARES := 80
const SKIRT_DEPTH_M := 100.0
const ROOT_NAME := "Surroundings"
const SKIRT_NAME := "Skirt"


## Builds the far terrain of [param grid] under a new "Surroundings" Node3D, adds it to
## [param parent] and returns it. Its transform is the identity and so is each child's.
static func create(grid: SurroundingsGrid, parent: Node) -> Node3D:
	var root := Node3D.new()
	root.name = ROOT_NAME
	var drawn := _drawn_squares(grid)
	var normals := _normals(grid)
	var material := _material(grid, BaseMaterial3D.CULL_BACK)
	var square_columns := grid.columns - 1
	var square_rows := grid.rows - 1
	for j in ceili(float(square_rows) / CHUNK_SQUARES):
		for i in ceili(float(square_columns) / CHUNK_SQUARES):
			var mesh := _chunk_mesh(grid, drawn, normals, i, j)
			if mesh == null:
				continue
			mesh.surface_set_material(0, material)
			var chunk := MeshInstance3D.new()
			chunk.name = "Chunk_%d_%d" % [i, j]
			chunk.mesh = mesh
			chunk.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
			root.add_child(chunk)
	var skirt_mesh := _skirt_mesh(grid, drawn)
	if skirt_mesh != null:
		skirt_mesh.surface_set_material(0, _material(grid, BaseMaterial3D.CULL_DISABLED))
		var skirt := MeshInstance3D.new()
		skirt.name = SKIRT_NAME
		skirt.mesh = skirt_mesh
		skirt.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(skirt)
	parent.add_child(root)
	return root


## One byte per square, row-major over (columns − 1) × (rows − 1): 1 where the square's four
## corners are finite, 0 where one is NaN.
static func _drawn_squares(grid: SurroundingsGrid) -> PackedByteArray:
	var heights := grid.heights
	var columns := grid.columns
	var square_columns := columns - 1
	var drawn := PackedByteArray()
	drawn.resize(square_columns * (grid.rows - 1))
	for r in grid.rows - 1:
		var north := r * columns
		var south := north + columns
		var row := r * square_columns
		for c in square_columns:
			if (
				not is_nan(heights[north + c])
				and not is_nan(heights[north + c + 1])
				and not is_nan(heights[south + c])
				and not is_nan(heights[south + c + 1])
			):
				drawn[row + c] = 1
	return drawn


## The normal of every vertex of the whole grid, (0, 0, 0) at a NaN one: (−dh/dx, 1, −dh/dz)
## normalised, dh/dx along +x (east, column + 1) and dh/dz along +z (south, row + 1), by central
## differences, (h[c + 1] − h[c − 1]) / 2s, or one-sided, (h[c + 1] − h[c]) / s or
## (h[c] − h[c − 1]) / s, where the neighbour lies outside the box or is NaN.
static func _normals(grid: SurroundingsGrid) -> PackedVector3Array:
	var heights := grid.heights
	var columns := grid.columns
	var rows := grid.rows
	var s := grid.spacing_m
	var normals := PackedVector3Array()
	normals.resize(columns * rows)
	for r in rows:
		for c in columns:
			var at := r * columns + c
			var h := heights[at]
			if is_nan(h):
				continue
			var west := heights[at - 1] if c > 0 else NAN
			var east := heights[at + 1] if c < columns - 1 else NAN
			var north := heights[at - columns] if r > 0 else NAN
			var south := heights[at + columns] if r < rows - 1 else NAN
			var slope_x := 0.0
			if not is_nan(west):
				slope_x = (east - west) / (2.0 * s) if not is_nan(east) else (h - west) / s
			elif not is_nan(east):
				slope_x = (east - h) / s
			var slope_z := 0.0
			if not is_nan(north):
				slope_z = (south - north) / (2.0 * s) if not is_nan(south) else (h - north) / s
			elif not is_nan(south):
				slope_z = (south - h) / s
			var inverse_length := 1.0 / sqrt(slope_x * slope_x + 1.0 + slope_z * slope_z)
			normals[at] = Vector3(
				-slope_x * inverse_length, inverse_length, -slope_z * inverse_length
			)
	return normals


## The one StandardMaterial3D a part of the far terrain draws with (design §3): the colour as
## the albedo texture (read as sRGB), mipmaps and anisotropy, rough, not metallic, no specular,
## opaque, lit per pixel, the scene's fog applied (it is the aerial perspective). Only
## [param cull_mode] differs between the chunks' and the skirt's.
static func _material(
	grid: SurroundingsGrid, cull_mode: BaseMaterial3D.CullMode
) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_texture = grid.colour_texture
	material.albedo_color = Color.WHITE
	material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	material.roughness = 1.0
	material.metallic = 0.0
	material.specular_mode = BaseMaterial3D.SPECULAR_DISABLED
	material.cull_mode = cull_mode
	material.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
	material.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL
	material.disable_fog = false
	return material


## The mesh of chunk ([param i], [param j]): the squares of columns [80i, 80i + 80) and rows
## [80j, 80j + 80), the last ones shorter. Null where no square of it is drawn.
static func _chunk_mesh(
	grid: SurroundingsGrid, drawn: PackedByteArray, normals: PackedVector3Array, i: int, j: int
) -> ArrayMesh:
	var columns := grid.columns
	var square_columns := columns - 1
	var c0 := i * CHUNK_SQUARES
	var r0 := j * CHUNK_SQUARES
	var c1 := mini(c0 + CHUNK_SQUARES, square_columns)
	var r1 := mini(r0 + CHUNK_SQUARES, grid.rows - 1)
	# The chunk's lattice of vertices, columns c0 to c1 and rows r0 to r1, `width` to a row.
	var width := c1 - c0 + 1
	var used := PackedByteArray()
	used.resize(width * (r1 - r0 + 1))
	var squares := PackedInt32Array()
	squares.resize((c1 - c0) * (r1 - r0))
	var count := 0
	for r in range(r0, r1):
		var row := r * square_columns
		var lattice := (r - r0) * width - c0
		for c in range(c0, c1):
			if drawn[row + c] == 0:
				continue
			var at := lattice + c
			squares[count] = at
			count += 1
			used[at] = 1
			used[at + 1] = 1
			used[at + width] = 1
			used[at + width + 1] = 1
	if count == 0:
		return null
	var heights := grid.heights
	var x_min := grid.x_min
	var z_min := grid.z_min
	var s := grid.spacing_m
	var u_span := float(columns - 1)
	var v_span := float(grid.rows - 1)
	var slots := PackedInt32Array()
	slots.resize(used.size())
	var vertices := PackedVector3Array()
	var vertex_normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	vertices.resize(used.size())
	vertex_normals.resize(used.size())
	uvs.resize(used.size())
	var made := 0
	for r in range(r0, r1 + 1):
		var lattice := (r - r0) * width - c0
		for c in range(c0, c1 + 1):
			var at := lattice + c
			if used[at] == 0:
				continue
			var vertex := r * columns + c
			slots[at] = made
			vertices[made] = Vector3(x_min + c * s, heights[vertex], z_min + r * s)
			vertex_normals[made] = normals[vertex]
			uvs[made] = Vector2(c / u_span, r / v_span)
			made += 1
	vertices.resize(made)
	vertex_normals.resize(made)
	uvs.resize(made)
	# The six corners of a square's two triangles, in the order they are drawn (the grid's
	# SQUARE_TRIANGLES, which height_at stands on too), as steps in this chunk's lattice from the
	# square's north-west vertex.
	var steps := _square_steps(width)
	var step_0 := steps[0]
	var step_1 := steps[1]
	var step_2 := steps[2]
	var step_3 := steps[3]
	var step_4 := steps[4]
	var step_5 := steps[5]
	var indices := PackedInt32Array()
	indices.resize(6 * count)
	var next := 0
	for k in count:
		var at := squares[k]
		indices[next] = slots[at + step_0]
		indices[next + 1] = slots[at + step_1]
		indices[next + 2] = slots[at + step_2]
		indices[next + 3] = slots[at + step_3]
		indices[next + 4] = slots[at + step_4]
		indices[next + 5] = slots[at + step_5]
		next += 6
	return _mesh(vertices, vertex_normals, uvs, indices)


## The corners of the two triangles of a square, in drawing order, as offsets in a lattice
## [param width] vertices wide from the square's north-west vertex: corner k of
## SurroundingsGrid.SQUARE_TRIANGLES is (k & 1) columns east and (k >> 1) rows south of it.
static func _square_steps(width: int) -> PackedInt32Array:
	var steps := PackedInt32Array()
	for triangle: Array in SurroundingsGrid.SQUARE_TRIANGLES:
		for corner: int in triangle:
			steps.append((corner & 1) + width * (corner >> 1))
	return steps


## An ArrayMesh of one triangle surface from the arrays given.
static func _mesh(
	vertices: PackedVector3Array,
	vertex_normals: PackedVector3Array,
	uvs: PackedVector2Array,
	indices: PackedInt32Array
) -> ArrayMesh:
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = vertex_normals
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


## The skirt's mesh: for every grid edge between a drawn square and an undrawn one, both inside
## the box (the box's own outer edge has none), a vertical quad down SKIRT_DEPTH_M from the
## edge's two vertices. Null where the grid has no such edge.
static func _skirt_mesh(grid: SurroundingsGrid, drawn: PackedByteArray) -> ArrayMesh:
	var square_columns := grid.columns - 1
	var square_rows := grid.rows - 1
	var vertices := PackedVector3Array()
	var vertex_normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	# Edges that run north to south, from vertex (c, r) to (c, r + 1), between the square to
	# their west and the one to their east. A quad's front faces east when it winds
	# (top 0, bottom 0, top 1), so that is the winding where the cut lies east.
	for r in square_rows:
		for c in range(1, square_columns):
			var west := drawn[r * square_columns + c - 1]
			var east := drawn[r * square_columns + c]
			if west == east:
				continue
			var toward := Vector3.RIGHT if east == 0 else Vector3.LEFT
			_add_quad(
				grid,
				[Vector2i(c, r), Vector2i(c, r + 1)],
				toward,
				east == 0,
				[vertices, vertex_normals, uvs, indices]
			)
	# Edges that run west to east, from vertex (c, r) to (c + 1, r), between the square to
	# their north and the one to their south. A quad's front faces north when it winds
	# (top 0, bottom 0, top 1), so that is the winding where the cut lies north.
	for r in range(1, square_rows):
		for c in square_columns:
			var north := drawn[(r - 1) * square_columns + c]
			var south := drawn[r * square_columns + c]
			if north == south:
				continue
			var toward := Vector3.FORWARD if south == 1 else Vector3.BACK
			_add_quad(
				grid,
				[Vector2i(c, r), Vector2i(c + 1, r)],
				toward,
				south == 1,
				[vertices, vertex_normals, uvs, indices]
			)
	if vertices.is_empty():
		return null
	return _mesh(vertices, vertex_normals, uvs, indices)


## Appends the quad hung from the grid vertices [param ends] (two Vector2i, column and row) to
## [param arrays] (vertices, normals, uvs, indices): its own four vertices, top 0, top 1, bottom
## 0, bottom 1, every normal [param toward] (horizontal, facing the cut), and the front, the
## clockwise side, toward the cut: the winding (top 0, bottom 0, top 1), (top 1, bottom 0,
## bottom 1) when [param forward], the reverse otherwise.
static func _add_quad(
	grid: SurroundingsGrid, ends: Array, toward: Vector3, forward: bool, arrays: Array
) -> void:
	var vertices: PackedVector3Array = arrays[0]
	var vertex_normals: PackedVector3Array = arrays[1]
	var uvs: PackedVector2Array = arrays[2]
	var indices: PackedInt32Array = arrays[3]
	var s := grid.spacing_m
	var u_span := float(grid.columns - 1)
	var v_span := float(grid.rows - 1)
	var first := vertices.size()
	var tops := []
	for end: Vector2i in ends:
		tops.append(
			Vector3(grid.x_min + end.x * s, grid.height(end.x, end.y), grid.z_min + end.y * s)
		)
	var down := Vector3(0.0, -SKIRT_DEPTH_M, 0.0)
	for top: Vector3 in tops:
		vertices.append(top)
	for top: Vector3 in tops:
		vertices.append(top + down)
	for _copy in 2:
		for end: Vector2i in ends:
			uvs.append(Vector2(end.x / u_span, end.y / v_span))
			vertex_normals.append(toward)
	var order := [0, 2, 1, 1, 2, 3] if forward else [0, 1, 2, 1, 3, 2]
	for corner: int in order:
		indices.append(first + corner)
