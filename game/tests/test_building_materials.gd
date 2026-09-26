extends GutTest
## Pinning tests for brief M2-08 (M2 R1 G-01): the buildings' look is the one SPEC §10 decides,
## read from the meshes the loader built.
##
## Pinned decisions (docs/SPEC.md §10, M2's game): lit, not unshaded; back faces culled; no
## transparency; no texture (nothing invented); the roofs darker than the walls. The exact
## colours are the owner's to tune (the .tres files), so only their order is pinned. The
## terrain's clay look is pinned the same way (M2-02's G-01).
##
## Does NOT prove: that anything renders or looks right (no GPU); the Forward+ look.

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


## The material of each named surface over all chunks: {"walls": [...], "roofs": [...]}.
func _materials() -> Dictionary:
	var found := {"walls": [], "roofs": []}
	if _buildings == null:
		return found
	for mesh in _buildings.get_children():
		var array_mesh := (mesh as MeshInstance3D).mesh as ArrayMesh
		for s in array_mesh.get_surface_count():
			var surface_name := array_mesh.surface_get_name(s)
			if found.has(surface_name):
				found[surface_name].append(array_mesh.surface_get_material(s))
	return found


func _luminance(colour: Color) -> float:
	return 0.2126 * colour.r + 0.7152 * colour.g + 0.0722 * colour.b


func test_every_surface_is_lit_culled_opaque_and_untextured() -> void:
	var materials := _materials()
	assert_gt(materials["walls"].size() + materials["roofs"].size(), 0, "surfaces were read")
	for surface_name: String in materials:
		for material: Variant in materials[surface_name]:
			assert_is(material, StandardMaterial3D, "%s: a StandardMaterial3D" % surface_name)
			var m := material as StandardMaterial3D
			if m == null:
				continue
			assert_eq(
				m.shading_mode, BaseMaterial3D.SHADING_MODE_PER_PIXEL, "%s: lit" % surface_name
			)
			assert_eq(m.cull_mode, BaseMaterial3D.CULL_BACK, "%s: back faces culled" % surface_name)
			assert_eq(
				m.transparency, BaseMaterial3D.TRANSPARENCY_DISABLED, "%s: opaque" % surface_name
			)
			assert_null(m.albedo_texture, "%s: no texture" % surface_name)
			assert_eq(m.albedo_color.a, 1.0, "%s: no alpha" % surface_name)


func test_the_roofs_are_darker_than_the_walls() -> void:
	var materials := _materials()
	if materials["walls"].is_empty() or materials["roofs"].is_empty():
		fail_test("both surfaces are needed")
		return
	var walls := (materials["walls"][0] as StandardMaterial3D).albedo_color
	var roofs := (materials["roofs"][0] as StandardMaterial3D).albedo_color
	assert_lt(_luminance(roofs), _luminance(walls), "roofs darker than walls")
	assert_gt(_luminance(roofs), 0.3, "not near black")
