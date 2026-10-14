extends GutTest
## Pinning tests for brief M3-11: the crown colour comes from the photo, in the trees' shader.
##
## Pinned decisions (m3-design §5 and §9, as decided on 2026-10-14):
## TreeLoader.create(chunks, parent, photo: Texture2D = null, photo_rect: Vector4 =
## Vector4.ZERO) binds the photo to the material that draws the trees, as the shader uniforms
## `photo` (the texture) and `photo_rect` (local x0, z0, width, depth: the terrain photo's
## rectangle rule); brief M3-14 passes the photo grid's texture and rect(). Without a photo,
## no photo is bound (the crowns take a labelled placeholder colour). The material is the
## MultiMeshInstance3D's material_override, or else the mesh's surface material. The loader
## needs no photo type of its own: a plain texture and a Vector4.
##
## Does NOT prove: what colour the crowns show (no GPU; the shader samples the photo at the
## tree's position at the mip level of its crown).

const RECT := Vector4(960.0, -40.0, 64.0, 48.0)

var _chunks: TreeChunks
var _with_photo: Node3D
var _without_photo: Node3D
var _texture: ImageTexture


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func before_all() -> void:
	var manifest := _repo_file("tests/shared/trees_fixture/generated/manifest.json")
	_chunks = TreeChunks.from_manifest(manifest, WorldConfig.from_manifest(manifest))
	var image := Image.create(16, 12, true, Image.FORMAT_RGB8)
	image.fill(Color8(52, 71, 40))
	_texture = ImageTexture.create_from_image(image)
	if _chunks != null:
		_with_photo = TreeLoader.create(_chunks, self, _texture, RECT)
		_without_photo = TreeLoader.create(_chunks, self)


func after_all() -> void:
	for node in [_with_photo, _without_photo]:
		if node != null:
			node.free()


func _materials(trees: Node3D) -> Array[ShaderMaterial]:
	var found: Array[ShaderMaterial] = []
	if trees == null:
		return found
	for child in trees.get_children():
		var instance := child as MultiMeshInstance3D
		var material: Material = instance.material_override
		if material == null:
			material = instance.multimesh.mesh.surface_get_material(0)
		assert_true(material is ShaderMaterial, "%s: a ShaderMaterial draws it" % child.name)
		if material is ShaderMaterial:
			found.append(material)
	return found


func test_the_photo_is_bound_to_the_trees_material() -> void:
	var materials := _materials(_with_photo)
	assert_eq(materials.size(), 3, "every cell")
	for material in materials:
		assert_eq(material.get_shader_parameter("photo"), _texture, "photo")
		assert_eq(material.get_shader_parameter("photo_rect"), RECT, "photo_rect")


func test_without_a_photo_none_is_bound() -> void:
	var materials := _materials(_without_photo)
	assert_eq(materials.size(), 3, "every cell")
	for material in materials:
		assert_null(material.get_shader_parameter("photo"), "no photo")
