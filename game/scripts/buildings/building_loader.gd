class_name BuildingLoader
extends RefCounted
## Builds the buildings' meshes from BuildingChunks, one per chunk (docs/SPEC.md §8, the
## buildings; §10, M2's game: the look).
##
## Every triangle gets its own three vertices and its own normal, normalize((b − a) ×
## (c − a)) in the file's order (a, b, c), which points out of the building: flat-shaded
## facets. Godot draws clockwise triangles as front faces, so each triangle goes into the
## arrays as (a, c, b); drawn in the file's counter-clockwise order, every building would
## show its inside (measured: SurfaceTool.generate_normals gives (0, 1, 0) for (0,0,0),
## (1,0,0), (0,0,1), whose right-hand normal is (0, −1, 0)). A triangle whose normal has
## y >= ROOF_MIN_NORMAL_Y (a slope of 60° or less) is roof, the rest wall: surface 0
## "walls", surface 1 "roofs", with the two materials under res://materials/. A chunk with
## no triangle of one kind has no surface of that kind (Godot refuses an empty surface).
## The positions are the file's own, unchanged: no coordinate is converted here.

const NODE_NAME := "Buildings"
const WALLS_MATERIAL := "res://materials/building_walls.tres"
const ROOFS_MATERIAL := "res://materials/building_roofs.tres"
const WALLS_SURFACE := "walls"
const ROOFS_SURFACE := "roofs"
## cos(60°): a triangle whose outward normal is at most 60° from straight up is roof.
const ROOF_MIN_NORMAL_Y := 0.5


## Adds a Node3D named "Buildings" to [param parent], holding one MeshInstance3D per chunk
## named by its tile, in the chunks' order, and returns it. Shadows are cast (the default).
static func create(chunks: BuildingChunks, parent: Node) -> Node3D:
	var buildings := Node3D.new()
	buildings.name = NODE_NAME
	var walls: Material = load(WALLS_MATERIAL)
	var roofs: Material = load(ROOFS_MATERIAL)
	for chunk: Dictionary in chunks.chunks:
		var instance := MeshInstance3D.new()
		instance.name = chunk["tile"]
		instance.mesh = _mesh(chunk["positions"], chunk["indices"], walls, roofs)
		buildings.add_child(instance)
	parent.add_child(buildings)
	return buildings


## One ArrayMesh, flat-shaded and unindexed: walls, then roofs.
static func _mesh(
	positions: PackedVector3Array, indices: PackedInt32Array, walls: Material, roofs: Material
) -> ArrayMesh:
	var wall_vertices := PackedVector3Array()
	var wall_normals := PackedVector3Array()
	var roof_vertices := PackedVector3Array()
	var roof_normals := PackedVector3Array()
	for t in indices.size() / 3:
		var a := positions[indices[3 * t]]
		var b := positions[indices[3 * t + 1]]
		var c := positions[indices[3 * t + 2]]
		# Right-handed, in the file's order: out of the building.
		var normal := (b - a).cross(c - a).normalized()
		var roof := normal.y >= ROOF_MIN_NORMAL_Y
		# Packed arrays held in a variable are shared, not copied: these append to the surface.
		var vertices := roof_vertices if roof else wall_vertices
		var normals := roof_normals if roof else wall_normals
		# Godot's front faces are clockwise: (a, c, b).
		vertices.append(a)
		vertices.append(c)
		vertices.append(b)
		normals.append(normal)
		normals.append(normal)
		normals.append(normal)
	var mesh := ArrayMesh.new()
	_add_surface(mesh, WALLS_SURFACE, wall_vertices, wall_normals, walls)
	_add_surface(mesh, ROOFS_SURFACE, roof_vertices, roof_normals, roofs)
	return mesh


static func _add_surface(
	mesh: ArrayMesh,
	surface_name: String,
	vertices: PackedVector3Array,
	normals: PackedVector3Array,
	material: Material
) -> void:
	if vertices.is_empty():
		return
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var surface := mesh.get_surface_count() - 1
	mesh.surface_set_name(surface, surface_name)
	mesh.surface_set_material(surface, material)
