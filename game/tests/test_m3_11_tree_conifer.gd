extends GutTest
## Brief M3-11, what the pinned TreeLoader tests leave open: the conifer's shape, its three
## variants, the turn, and the seam between the loader and the shader.
##
## What each case must catch: a conifer that is not 138 vertices and 192 triangles, with a
## triangle facing into the tree (Godot's front faces are clockwise, brain.md H16) or
## degenerate; a variant that is not the unit tree (its top at y = 1, its widest at radius
## 1) or that leaves the mesh's custom AABB (the mesh's own is VERTEX only, so a tree
## drawn as variant 1 or 2 would be culled at the edge of variant 0); a loader that sets a
## shader parameter the shader does not declare (set_shader_parameter accepts any name, and
## the pinned tests read the name back from the material, so they cannot see it); a turn
## that is not a hash of both coordinates in 4096 steps.
##
## Does NOT prove: that the shader compiles on a GPU or that the trees look right (no GPU:
## the headless renderer parses the shader's declarations, nothing more); the colour
## encoding (brain.md H21: the one text check below only proves the photo's declaration
## says source_color).

const CROWN_TRIANGLES := 180
const TRIANGLES := 192
const VERTICES := 138
## The trunk's rings are the last twelve vertices.
const TRUNK_VERTICES := 12

var _arrays: Array


func before_all() -> void:
	var mesh := TreeLoader.conifer()
	_arrays = mesh.surface_get_arrays(0)


## The vertices of variant [param variant]: VERTEX, CUSTOM0, CUSTOM1.
func _variant(variant: int) -> PackedVector3Array:
	if variant == 0:
		return _arrays[Mesh.ARRAY_VERTEX]
	var floats: PackedFloat32Array = _arrays[
		Mesh.ARRAY_CUSTOM0 if variant == 1 else Mesh.ARRAY_CUSTOM1
	]
	var points := PackedVector3Array()
	for i in floats.size() / 3:
		points.append(Vector3(floats[3 * i], floats[3 * i + 1], floats[3 * i + 2]))
	return points


func test_the_conifer_has_the_designed_topology() -> void:
	var indices: PackedInt32Array = _arrays[Mesh.ARRAY_INDEX]
	assert_eq(_variant(0).size(), VERTICES, "vertices")
	assert_eq(indices.size() / 3, TRIANGLES, "triangles")
	assert_eq(indices.size() % 3, 0, "whole triangles")
	assert_eq(_arrays[Mesh.ARRAY_TEX_UV].size(), VERTICES, "one UV per vertex")
	for variant in [1, 2]:
		assert_eq(_variant(variant).size(), VERTICES, "variant %d has the same topology" % variant)
	for index in indices:
		assert_between(index, 0, VERTICES - 1, "every index names a vertex")


func test_every_variant_is_the_unit_tree() -> void:
	for variant in TreeLoader.VARIANTS:
		var points := _variant(variant)
		var top := -INF
		var widest := 0.0
		for p in points:
			top = maxf(top, p.y)
			widest = maxf(widest, Vector2(p.x, p.z).length())
		assert_almost_eq(top, 1.0, 1e-5, "variant %d: the top at y = 1" % variant)
		assert_almost_eq(widest, 1.0, 1e-5, "variant %d: the widest at radius 1" % variant)


func test_the_variants_differ_in_their_crown_and_share_their_trunk() -> void:
	var crown := VERTICES - TRUNK_VERTICES
	for pair in [[0, 1], [0, 2], [1, 2]]:
		var a := _variant(pair[0])
		var b := _variant(pair[1])
		var differing := 0
		for i in crown:
			if a[i].distance_to(b[i]) > 1e-3:
				differing += 1
		# Every apex of the six sits on the axis in all three (6 of 126 vertices).
		assert_gt(differing, 100, "variants %s differ in their crowns" % [pair])
		for i in range(crown, VERTICES):
			assert_eq(a[i], b[i], "variants %s share the trunk (vertex %d)" % [pair, i])


func test_every_triangle_faces_out_of_the_tree() -> void:
	var indices: PackedInt32Array = _arrays[Mesh.ARRAY_INDEX]
	for variant in TreeLoader.VARIANTS:
		var points := _variant(variant)
		var inward := 0
		var flat := 0
		var downward := 0
		for t in indices.size() / 3:
			var a := points[indices[3 * t]]
			var b := points[indices[3 * t + 1]]
			var c := points[indices[3 * t + 2]]
			# The indices go in clockwise seen from outside, so the right-hand normal of the
			# stored order points into the tree, and the outward normal is its negative.
			var out := -(b - a).cross(c - a)
			if out.length() < 1e-6:
				flat += 1
				continue
			var centroid := (a + b + c) / 3.0
			if out.dot(Vector3(centroid.x, 0.0, centroid.z)) <= 0.0:
				inward += 1
			if t < CROWN_TRIANGLES and out.y <= 0.0:
				downward += 1
		assert_eq(flat, 0, "variant %d: no degenerate triangle" % variant)
		assert_eq(inward, 0, "variant %d: no triangle faces the axis" % variant)
		assert_eq(downward, 0, "variant %d: every bough's top side faces up" % variant)


func test_the_custom_aabb_holds_every_variant() -> void:
	var mesh := TreeLoader.conifer()
	var box := mesh.custom_aabb
	assert_gt(box.size.x, 0.0, "the mesh has a custom AABB")
	for variant in TreeLoader.VARIANTS:
		for p in _variant(variant):
			assert_true(
				box.grow(1e-5).has_point(p), "variant %d: %s is inside %s" % [variant, p, box]
			)
	assert_lt(box.position.y, 0.0, "the box reaches the trunk's foot below the base")


func test_the_turn_is_a_hash_of_the_position_in_4096_steps() -> void:
	var step := TAU / TreeLoader.YAW_STEPS
	var seen := {}
	for i in 1000:
		var x := -300.0 + 0.77 * i
		var z := 250.0 - 1.13 * i
		var yaw := TreeLoader.yaw_of(x, z)
		assert_between(yaw, 0.0, TAU - step / 2.0, "a turn within one revolution")
		assert_almost_eq(yaw / step, roundf(yaw / step), 1e-4, "a whole number of steps")
		seen[roundi(yaw / step)] = true
	assert_gt(seen.size(), 700, "the turns are spread over the 4096 steps")
	assert_eq(TreeLoader.yaw_of(12.3, -45.6), TreeLoader.yaw_of(12.3, -45.6), "deterministic")
	# round(2x) and round(2z): positions that round alike turn alike, others do not.
	assert_eq(TreeLoader.yaw_of(10.2, 5.1), TreeLoader.yaw_of(10.24, 5.05), "the same half metre")
	assert_ne(TreeLoader.yaw_of(10.2, 5.1), TreeLoader.yaw_of(10.3, 5.1), "x decides")
	assert_ne(TreeLoader.yaw_of(10.2, 5.1), TreeLoader.yaw_of(10.2, 5.4), "z decides")
	assert_ne(TreeLoader.yaw_of(10.2, 5.1), TreeLoader.yaw_of(5.1, 10.2), "x and z are not alike")


func test_the_loader_sets_only_parameters_the_shader_declares() -> void:
	var shader: Shader = load(TreeLoader.SHADER)
	assert_not_null(shader, "the shader loads")
	var declared := {}
	for uniform: Dictionary in shader.get_shader_uniform_list():
		declared[uniform["name"]] = uniform["type"]
	assert_eq(declared.get("photo"), TYPE_OBJECT, "photo is a texture sampler")
	assert_eq(declared.get("photo_rect"), TYPE_VECTOR4, "photo_rect is a vec4")
	# The material the loader makes sets these two names, so they must be the declared ones.
	var manifest := _repo_file("tests/shared/trees_fixture/generated/manifest.json")
	var chunks := TreeChunks.from_manifest(manifest, WorldConfig.from_manifest(manifest))
	var image := Image.create(4, 4, false, Image.FORMAT_RGB8)
	var parent := Node.new()
	var rect := Vector4(960.0, -40.0, 64.0, 48.0)
	var trees := TreeLoader.create(chunks, parent, ImageTexture.create_from_image(image), rect)
	var material := (trees.get_child(0) as MultiMeshInstance3D).material_override as ShaderMaterial
	assert_eq(material.shader, shader, "the loader's material runs the shader")
	assert_not_null(material.get_shader_parameter("photo"), "photo is set, as declared above")
	assert_eq(material.get_shader_parameter("photo_rect"), rect, "photo_rect is set, as declared")
	parent.free()


func test_one_material_serves_every_cell() -> void:
	var manifest := _repo_file("tests/shared/trees_fixture/generated/manifest.json")
	var chunks := TreeChunks.from_manifest(manifest, WorldConfig.from_manifest(manifest))
	var parent := Node.new()
	var trees := TreeLoader.create(chunks, parent)
	var first := trees.get_child(0) as MultiMeshInstance3D
	for child in trees.get_children():
		var cell := child as MultiMeshInstance3D
		assert_same(cell.material_override, first.material_override, "%s: one material" % cell.name)
		assert_same(cell.multimesh.mesh, first.multimesh.mesh, "%s: one conifer mesh" % cell.name)
	parent.free()


func test_the_photo_is_declared_as_a_source_colour_sampler() -> void:
	# A census of text (lesson 5): it proves the declaration says source_color, which is how a
	# colour enters a renderer correctly (brain.md H21); it cannot prove the colour is right.
	var found := false
	for line in FileAccess.get_file_as_string(TreeLoader.SHADER).split("\n"):
		if line.begins_with("uniform sampler2D photo"):
			found = true
			assert_true(line.contains("source_color"), "photo is a source_color sampler: %s" % line)
	assert_true(found, "the shader declares the photo sampler")


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)
