extends GutTest
## Pinning tests for brief M3-12 (replacing M2-08's, M2 V1-G-04): the buildings' look without
## roof colours, read from what each node draws.
##
## Pinned decisions (docs/SPEC.md §10, M2's game; m3-design.md §3): lit, not unshaded; back
## faces culled; no transparency; no texture (nothing invented); the roofs darker than the
## walls. Since M3 the walls are one neutral plaster, a placeholder (swisstopo has no wall
## data): albedo (0.78, 0.76, 0.72), roughness 0.9 (read back as float32, so within 1e-6);
## the neutral roof colour stays the owner's to tune, so only its order is pinned. M2 V1-G-04:
## the materials are read with get_active_material(s), what the node draws, and no
## MeshInstance3D carries a material_override or a surface override material (an unshaded
## override passed M2-08's version, which read the meshes' surface materials). The label:
## BuildingLoader.WALLS_NOTE, exactly as brief M3-12 writes it (M3-14's credits show it).
##
## Does NOT prove: that anything renders or looks right (no GPU); the Forward+ look.

const PLASTER := Color(0.78, 0.76, 0.72, 1.0)
const WALLS_NOTE := (
	"Walls: one neutral plaster colour, a placeholder:" + " no open data shows the façades."
)

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


## What each node draws for each named surface, over all chunks: {"walls": [...], "roofs": [...]}.
func _materials() -> Dictionary:
	var found := {"walls": [], "roofs": []}
	if _buildings == null:
		return found
	for child in _buildings.get_children():
		var instance := child as MeshInstance3D
		var mesh := instance.mesh as ArrayMesh
		for s in mesh.get_surface_count():
			var surface_name := mesh.surface_get_name(s)
			if found.has(surface_name):
				found[surface_name].append(instance.get_active_material(s))
	return found


func _luminance(colour: Color) -> float:
	return 0.2126 * colour.r + 0.7152 * colour.g + 0.0722 * colour.b


func test_nothing_overrides_what_the_meshes_draw() -> void:
	assert_not_null(_buildings, "the fixture's buildings are loaded")
	if _buildings == null:
		return
	for child in _buildings.get_children():
		var instance := child as MeshInstance3D
		assert_null(instance.material_override, "%s: no material_override" % instance.name)
		for s in instance.mesh.get_surface_count():
			assert_null(
				instance.get_surface_override_material(s),
				"%s: no override for surface %d" % [instance.name, s]
			)


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
			assert_false(m.vertex_color_use_as_albedo, "%s: no vertex colour" % surface_name)


func test_the_walls_are_the_plaster_placeholder() -> void:
	var walls: Array = _materials()["walls"]
	assert_gt(walls.size(), 0, "walls were read")
	for material: Variant in walls:
		var m := material as StandardMaterial3D
		assert_not_null(m, "a StandardMaterial3D")
		if m != null:
			assert_eq(m.albedo_color, PLASTER, "the plaster placeholder's albedo")
			assert_almost_eq(m.roughness, 0.9, 1e-6, "roughness 0.9")


func test_the_roofs_are_darker_than_the_walls() -> void:
	var materials := _materials()
	if materials["walls"].is_empty() or materials["roofs"].is_empty():
		fail_test("both surfaces are needed")
		return
	var walls := (materials["walls"][0] as StandardMaterial3D).albedo_color
	var roofs := (materials["roofs"][0] as StandardMaterial3D).albedo_color
	assert_lt(_luminance(roofs), _luminance(walls), "roofs darker than walls")
	assert_gt(_luminance(roofs), 0.3, "not near black")


func test_the_walls_are_labelled_a_placeholder() -> void:
	# Read from the script's constants, so a loader without the label fails here by name.
	var loader: Script = load("res://scripts/buildings/building_loader.gd")
	assert_not_null(loader, "the loader's script loads")
	if loader != null:
		var note: Variant = loader.get_script_constant_map().get("WALLS_NOTE")
		assert_eq(note, WALLS_NOTE, "BuildingLoader.WALLS_NOTE, as the brief writes it")
