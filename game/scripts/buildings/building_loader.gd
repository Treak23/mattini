class_name BuildingLoader
extends RefCounted
## Builds the buildings' meshes from BuildingChunks, one per chunk (docs/SPEC.md §8, the
## buildings; §10, M2's and M3's game: the look).
##
## Every triangle gets its own three vertices and its own normal, normalize((b − a) ×
## (c − a)) in the file's order (a, b, c), which points out of the building: flat-shaded
## facets. Godot draws clockwise triangles as front faces, so each triangle goes into the
## arrays as (a, c, b); drawn in the file's counter-clockwise order, every building would
## show its inside (measured: SurfaceTool.generate_normals gives (0, 1, 0) for (0,0,0),
## (1,0,0), (0,0,1), whose right-hand normal is (0, −1, 0)). A triangle whose normal has
## y >= ROOF_MIN_NORMAL_Y (a slope of 60° or less) is roof, the rest wall. The surfaces,
## named, with the materials under res://materials/: "walls" (every wall), "roofs" (every
## roof triangle without a colour of its own) and, with BuildingRoofs, "roofs_photo" (every
## roof triangle of a building with a colour, which it carries as its vertex colour). A
## chunk with no triangle of one kind has no surface of that kind (Godot refuses an empty
## surface). The positions are the file's own, unchanged: no coordinate is converted here.
##
## The roof colours are the photo's bytes, sRGB: the roofs_photo material reads the vertex
## colour as sRGB (vertex_color_is_srgb) under a white albedo; read as linear, the roofs
## would wash out.
##
## Walls: one neutral plaster colour, a placeholder: no open data shows the façades. The
## colour is the owner's choice (docs/SPEC.md §13 row 31), not a measurement. The label
## lives here and in WALLS_NOTE, which the credits show, because Godot drops a comment from
## a .tres file when the editor saves it again.

const NODE_NAME := "Buildings"
const WALLS_MATERIAL := "res://materials/building_walls.tres"
const ROOFS_MATERIAL := "res://materials/building_roofs.tres"
const ROOFS_PHOTO_MATERIAL := "res://materials/building_roofs_photo.tres"
const WALLS_SURFACE := "walls"
const ROOFS_SURFACE := "roofs"
const ROOFS_PHOTO_SURFACE := "roofs_photo"
## The label of the walls' placeholder colour, shown in the credits.
const WALLS_NOTE := (
	"Walls: one neutral plaster colour, a placeholder:" + " no open data shows the façades."
)
## cos(60°): a triangle whose outward normal is at most 60° from straight up is roof.
const ROOF_MIN_NORMAL_Y := 0.5


## Adds a Node3D named "Buildings" to [param parent], holding one MeshInstance3D per chunk
## named by its tile, in the chunks' order, and returns it. Shadows are cast (the default).
## With [param roofs], read from the same manifest as [param chunks], each roof triangle of a
## building with a colour is drawn in it; a roofs object that does not fit the chunks
## (roofs_problem) is refused with one push_error and the buildings are drawn without it.
static func create(chunks: BuildingChunks, parent: Node, roofs: BuildingRoofs = null) -> Node3D:
	if roofs != null:
		var problem := roofs_problem(chunks, roofs)
		if not problem.is_empty():
			push_error("BuildingLoader: the roof colours do not fit the buildings: %s" % problem)
			roofs = null
	var buildings := Node3D.new()
	buildings.name = NODE_NAME
	var materials := {
		WALLS_SURFACE: load(WALLS_MATERIAL),
		ROOFS_SURFACE: load(ROOFS_MATERIAL),
		ROOFS_PHOTO_SURFACE: load(ROOFS_PHOTO_MATERIAL),
	}
	for i in chunks.chunks.size():
		var chunk: Dictionary = chunks.chunks[i]
		var colours := _triangle_colours(roofs.chunks[i]["buildings"]) if roofs != null else []
		var instance := MeshInstance3D.new()
		instance.name = chunk["tile"]
		instance.mesh = _mesh(chunk["positions"], chunk["indices"], colours, materials)
		buildings.add_child(instance)
	parent.add_child(buildings)
	return buildings


## What keeps [param roofs] from describing [param chunks]: not the same tiles in the same
## order, or a chunk whose buildings' triangles do not add up to the chunk's. "" when it fits.
static func roofs_problem(chunks: BuildingChunks, roofs: BuildingRoofs) -> String:
	if roofs.chunks.size() != chunks.chunks.size():
		return "%d chunks of colours for %d chunks" % [roofs.chunks.size(), chunks.chunks.size()]
	for i in chunks.chunks.size():
		var chunk: Dictionary = chunks.chunks[i]
		var entry: Dictionary = roofs.chunks[i]
		if entry["tile"] != chunk["tile"]:
			return (
				"chunk %d is %s in the colours, %s in the buildings"
				% [i, entry["tile"], chunk["tile"]]
			)
		var triangles := 0
		for building: Dictionary in entry["buildings"]:
			triangles += building["triangles"]
		if triangles != chunk["indices"].size() / 3:
			return (
				"chunk %s: the colours cover %d triangles, the buildings %d"
				% [chunk["tile"], triangles, chunk["indices"].size() / 3]
			)
	return ""


## The colour of every triangle of a chunk, in the file's order: the colour of the building
## the triangle belongs to (the buildings follow each other in the file), or null for a
## building without one. [param buildings] is BuildingRoofs' list for the chunk.
static func _triangle_colours(buildings: Array) -> Array:
	var colours := []
	for building: Dictionary in buildings:
		var roof: Variant = building["roof"]
		for k in building["triangles"]:
			colours.append(roof)
	return colours


## One ArrayMesh, flat-shaded and unindexed: walls, then roofs, then the coloured roofs.
## [param colours] is _triangle_colours' list, or empty when there are no roof colours.
static func _mesh(
	positions: PackedVector3Array, indices: PackedInt32Array, colours: Array, materials: Dictionary
) -> ArrayMesh:
	var wall_vertices := PackedVector3Array()
	var wall_normals := PackedVector3Array()
	var roof_vertices := PackedVector3Array()
	var roof_normals := PackedVector3Array()
	var photo_vertices := PackedVector3Array()
	var photo_normals := PackedVector3Array()
	var photo_colours := PackedColorArray()
	for t in indices.size() / 3:
		var a := positions[indices[3 * t]]
		var b := positions[indices[3 * t + 1]]
		var c := positions[indices[3 * t + 2]]
		# Right-handed, in the file's order: out of the building.
		var normal := (b - a).cross(c - a).normalized()
		var colour: Variant = null
		if normal.y >= ROOF_MIN_NORMAL_Y and not colours.is_empty():
			colour = colours[t]
		# Packed arrays held in a variable are shared, not copied: these append to the surface.
		var vertices := wall_vertices
		var normals := wall_normals
		if colour != null:
			vertices = photo_vertices
			normals = photo_normals
			photo_colours.append(colour)
			photo_colours.append(colour)
			photo_colours.append(colour)
		elif normal.y >= ROOF_MIN_NORMAL_Y:
			vertices = roof_vertices
			normals = roof_normals
		# Godot's front faces are clockwise: (a, c, b).
		vertices.append(a)
		vertices.append(c)
		vertices.append(b)
		normals.append(normal)
		normals.append(normal)
		normals.append(normal)
	var mesh := ArrayMesh.new()
	_add_surface(mesh, WALLS_SURFACE, wall_vertices, wall_normals, null, materials[WALLS_SURFACE])
	_add_surface(mesh, ROOFS_SURFACE, roof_vertices, roof_normals, null, materials[ROOFS_SURFACE])
	_add_surface(
		mesh,
		ROOFS_PHOTO_SURFACE,
		photo_vertices,
		photo_normals,
		photo_colours,
		materials[ROOFS_PHOTO_SURFACE]
	)
	return mesh


static func _add_surface(
	mesh: ArrayMesh,
	surface_name: String,
	vertices: PackedVector3Array,
	normals: PackedVector3Array,
	colours: Variant,
	material: Material
) -> void:
	if vertices.is_empty():
		return
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colours
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var surface := mesh.get_surface_count() - 1
	mesh.surface_set_name(surface, surface_name)
	mesh.surface_set_material(surface, material)
