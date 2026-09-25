extends GutTest
## Pinning tests for brief M2-05: BuildingLoader turns the chunks into meshes that face
## outward in Godot's convention, flat-shaded, roofs apart from walls.
##
## Pinned decisions (docs/SPEC.md §8, the buildings; brief M2-05): one MeshInstance3D per
## chunk under a Node3D named "Buildings", named by its tile; every triangle its own three
## vertices and its own normal, normalize((b - a) x (c - a)) in the file's order, which
## points out of the building (the file is counter-clockwise seen from outside); Godot's
## front faces are clockwise (measured: SurfaceTool.generate_normals gives (0, 1, 0) for
## (0,0,0), (1,0,0), (0,0,1), whose right-hand normal is (0, -1, 0)), so each triangle goes
## into the arrays as (a, c, b); a triangle whose normal has y >= 0.5 is roof, the rest wall;
## surfaces named "walls" and "roofs" with the materials under res://materials/.
## Measured in M2-05: SurfaceTool.generate_normals averages over shared positions unless
## the smooth group is -1, and an ArrayMesh gives its normals back through 16-bit octahedral
## storage (about 1e-4 per component), so normals are compared within 1e-4.
##
## Does NOT prove: that the buildings render or look right (no GPU); the look itself (the
## owner's to judge).

const WALLS := "res://materials/building_walls.tres"
const ROOFS := "res://materials/building_roofs.tres"

var _chunks: BuildingChunks
var _buildings: Node3D


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func before_all() -> void:
	var manifest := _repo_file("tests/shared/buildings_fixture/generated/manifest.json")
	_chunks = BuildingChunks.from_manifest(manifest, WorldConfig.from_manifest(manifest))
	if _chunks != null:
		_buildings = BuildingLoader.create(_chunks, self)


func after_all() -> void:
	if _buildings != null:
		_buildings.free()


func _meshes() -> Array[MeshInstance3D]:
	var found: Array[MeshInstance3D] = []
	if _buildings != null:
		for child in _buildings.get_children():
			if child is MeshInstance3D:
				found.append(child)
	return found


func test_one_mesh_per_chunk_under_buildings() -> void:
	assert_not_null(_buildings, "the loader returns the Buildings node")
	if _buildings == null:
		return
	assert_eq(_buildings.name, &"Buildings")
	assert_eq(_buildings.get_parent(), self, "added to the given parent")
	var names: Array = []
	for mesh in _meshes():
		names.append(String(mesh.name))
	assert_eq(names, ["2650-1149", "2650-1150", "2651-1150"], "one per chunk, in order")
	for mesh in _meshes():
		assert_eq(mesh.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_ON, "casts shadows")


func _surfaces(mesh: MeshInstance3D) -> Dictionary:
	var by_name := {}
	var array_mesh := mesh.mesh as ArrayMesh
	for i in array_mesh.get_surface_count():
		by_name[array_mesh.surface_get_name(i)] = i
	return by_name


func test_every_triangle_is_drawn_once_flat_shaded() -> void:
	for i in _meshes().size():
		var mesh := _meshes()[i]
		var chunk: Dictionary = _chunks.chunks[i]
		var array_mesh := mesh.mesh as ArrayMesh
		assert_not_null(array_mesh, "%s: an ArrayMesh" % mesh.name)
		var triangles := 0
		for s in array_mesh.get_surface_count():
			var arrays := array_mesh.surface_get_arrays(s)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			assert_eq(arrays[Mesh.ARRAY_INDEX], null, "unindexed: every triangle its own vertices")
			assert_eq(vertices.size() % 3, 0)
			assert_eq(normals.size(), vertices.size())
			triangles += vertices.size() / 3
			for t in vertices.size() / 3:
				var n := normals[3 * t]
				assert_true(n == normals[3 * t + 1] and n == normals[3 * t + 2], "flat: one normal")
		assert_eq(triangles, chunk["indices"].size() / 3, "%s: every triangle once" % mesh.name)


func test_roofs_and_walls_by_the_normal() -> void:
	for mesh in _meshes():
		var surfaces := _surfaces(mesh)
		assert_has(surfaces, "walls", "%s: a walls surface" % mesh.name)
		assert_has(surfaces, "roofs", "%s: a roofs surface" % mesh.name)
		var array_mesh := mesh.mesh as ArrayMesh
		for surface_name: String in surfaces:
			var s: int = surfaces[surface_name]
			var normals: PackedVector3Array = array_mesh.surface_get_arrays(s)[Mesh.ARRAY_NORMAL]
			for n in normals:
				if surface_name == "roofs":
					assert_true(n.y >= 0.5, "%s: roof normal %s points up" % [mesh.name, n])
				else:
					assert_true(n.y < 0.5, "%s: wall normal %s" % [mesh.name, n])
			var material := array_mesh.surface_get_material(s)
			assert_not_null(material, "%s: %s has a material" % [mesh.name, surface_name])
			if material != null:
				var expected := ROOFS if surface_name == "roofs" else WALLS
				assert_eq(material.resource_path, expected)


func test_normals_face_out_and_front_faces_are_godot_s() -> void:
	# The file's triangle (a, b, c) is counter-clockwise from outside, so its right-hand
	# normal points out; in the arrays it must appear as (a, c, b), and Godot's own normal
	# generation (clockwise front faces) must agree with the normal the loader wrote.
	for i in _meshes().size():
		var mesh := _meshes()[i]
		var chunk: Dictionary = _chunks.chunks[i]
		var positions: PackedVector3Array = chunk["positions"]
		var indices: PackedInt32Array = chunk["indices"]
		var outward := {}
		for t in indices.size() / 3:
			var a := positions[indices[3 * t]]
			var b := positions[indices[3 * t + 1]]
			var c := positions[indices[3 * t + 2]]
			outward[[a, c, b]] = (b - a).cross(c - a).normalized()
		var array_mesh := mesh.mesh as ArrayMesh
		var checked := 0
		for s in array_mesh.get_surface_count():
			var arrays := array_mesh.surface_get_arrays(s)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var tool := SurfaceTool.new()
			tool.begin(Mesh.PRIMITIVE_TRIANGLES)
			tool.set_smooth_group(-1)  # flat: one normal per triangle, never averaged
			for v in vertices:
				tool.add_vertex(v)
			tool.generate_normals()
			var godot_normals: PackedVector3Array = tool.commit_to_arrays()[Mesh.ARRAY_NORMAL]
			for t in vertices.size() / 3:
				var key := [vertices[3 * t], vertices[3 * t + 1], vertices[3 * t + 2]]
				assert_true(
					outward.has(key),
					"%s: triangle %d is a file triangle as (a, c, b)" % [mesh.name, t]
				)
				if outward.has(key):
					assert_almost_eq(normals[3 * t], outward[key], Vector3.ONE * 1e-4)
				assert_almost_eq(
					godot_normals[3 * t], normals[3 * t], Vector3.ONE * 1e-4, "Godot's front face"
				)
				checked += 1
		assert_eq(checked, indices.size() / 3)


func test_a_flat_roof_faces_the_sky() -> void:
	# Building b of the fixture is a flat-roofed box that the pipeline did not reverse; its
	# highest triangles must be roofs with normal (0, 1, 0).
	var found := false
	for mesh in _meshes():
		var surfaces := _surfaces(mesh)
		if not surfaces.has("roofs"):
			continue
		var normals: PackedVector3Array = (
			(mesh.mesh as ArrayMesh).surface_get_arrays(surfaces["roofs"])[Mesh.ARRAY_NORMAL]
		)
		for n in normals:
			if n.distance_to(Vector3.UP) < 1e-4:
				found = true
	assert_true(found, "some roof triangle faces straight up")
