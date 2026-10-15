extends GutTest
## Pinning tests for brief M3-12: the roofs drawn in the colours the pipeline measured on the
## photo, the walls in one neutral plaster, read from what the nodes draw.
##
## Pinned decisions (m3-design.md §3): BuildingLoader.create(chunks, parent, roofs) gives
## every roof triangle (the game's own rule: normalize((b - a) × (c - a)).y >= 0.5) of a
## building with a colour that colour as vertex colour, drawn by a material that takes the
## vertex colour as albedo, as sRGB, under a white albedo, so the drawn colour is the
## photo's; a building whose roof is null keeps the neutral roof material
## (res://materials/building_roofs.tres); every wall, with or without roof colours, is the
## plaster placeholder: albedo (0.78, 0.76, 0.72), roughness 0.9. The look is read from what
## each node draws, get_active_material(s), and nothing overrides it: no material_override,
## no surface override material (M2 V1-G-04). Measured: an ArrayMesh gives Color8 vertex
## colours back exactly (all 256 values), so colours are compared exactly; a material's
## roughness reads back as float32 (0.9 is 0.89999997615814), so within 1e-6. The named
## triangles (tests/shared/roofs_vectors.json) are the seam: the pipeline's colour for a
## building, on the triangles the game draws for it.
##
## Does NOT prove: that anything renders or looks right (no GPU, the owner's eyes); that the
## photo's colours are plausible on the real village (design's preview, not a render).

const WALLS := "res://materials/building_walls.tres"
const ROOFS := "res://materials/building_roofs.tres"
const PLASTER := Color(0.78, 0.76, 0.72, 1.0)

var _chunks: BuildingChunks
var _roofs: BuildingRoofs
var _buildings: Node3D
## Every drawn triangle by its vertices in Godot's order [a, c, b]:
## {"instance": MeshInstance3D, "surface": int, "colours": PackedColorArray or null, "at": int}.
var _drawn := {}


func _repo_file(rel: String) -> String:
	return ProjectSettings.globalize_path("res://").path_join("..").path_join(rel)


func _vectors() -> Dictionary:
	var json := JSON.new()
	var text := FileAccess.get_file_as_string(_repo_file("tests/shared/roofs_vectors.json"))
	assert_eq(json.parse(text), OK, "the vectors parse")
	return json.data if typeof(json.data) == TYPE_DICTIONARY else {}


func before_all() -> void:
	var manifest := _repo_file("tests/shared/roofs_fixture/generated/manifest.json")
	var world := WorldConfig.from_manifest(manifest)
	_chunks = BuildingChunks.from_manifest(manifest, world)
	if _chunks != null:
		_roofs = BuildingRoofs.from_manifest(manifest, world, _chunks)
	if _roofs == null:
		return
	_buildings = BuildingLoader.create(_chunks, self, _roofs)
	for child in _buildings.get_children():
		var instance := child as MeshInstance3D
		var mesh := instance.mesh as ArrayMesh
		for s in mesh.get_surface_count():
			var arrays := mesh.surface_get_arrays(s)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			for t in vertices.size() / 3:
				var key := [vertices[3 * t], vertices[3 * t + 1], vertices[3 * t + 2]]
				_drawn[key] = {
					"instance": instance, "surface": s, "colours": arrays[Mesh.ARRAY_COLOR], "at": t
				}


func after_all() -> void:
	if _buildings != null:
		_buildings.free()


func _chunk(tile: String) -> Dictionary:
	for chunk: Dictionary in _chunks.chunks:
		if chunk["tile"] == tile:
			return chunk
	return {}


## The file's triangle [param t] of chunk [param tile] as (a, b, c).
func _points(tile: String, t: int) -> Array:
	var chunk := _chunk(tile)
	var positions: PackedVector3Array = chunk["positions"]
	var indices: PackedInt32Array = chunk["indices"]
	return [positions[indices[3 * t]], positions[indices[3 * t + 1]], positions[indices[3 * t + 2]]]


## Where the triangle is drawn, found by its vertices as Godot's front face (a, c, b).
func _where(tile: String, t: int) -> Dictionary:
	var p := _points(tile, t)
	return _drawn.get([p[0], p[2], p[1]], {})


func _material(found: Dictionary) -> StandardMaterial3D:
	var instance: MeshInstance3D = found["instance"]
	return instance.get_active_material(found["surface"]) as StandardMaterial3D


func _assert_coloured(found: Dictionary, colour: Color, what: String) -> void:
	var colours: Variant = found["colours"]
	assert_true(colours != null, "%s: drawn with vertex colours" % what)
	if colours != null:
		for k in 3:
			assert_eq(colours[3 * found["at"] + k], colour, "%s: vertex %d's colour" % [what, k])
	var material := _material(found)
	assert_not_null(material, "%s: a StandardMaterial3D draws it" % what)
	if material != null:
		assert_true(
			material.vertex_color_use_as_albedo, "%s: the vertex colour is the albedo" % what
		)
		assert_true(
			material.vertex_color_is_srgb, "%s: the vertex colour is sRGB, as the photo" % what
		)
		assert_eq(material.albedo_color, Color(1, 1, 1, 1), "%s: under a white albedo" % what)
		assert_null(material.albedo_texture, "%s: no texture" % what)


func _assert_plaster(found: Dictionary, what: String) -> void:
	var material := _material(found)
	assert_not_null(material, "%s: a StandardMaterial3D draws it" % what)
	if material != null:
		assert_eq(material.resource_path, WALLS, "%s: the walls material" % what)
		assert_eq(material.albedo_color, PLASTER, "%s: the plaster placeholder's albedo" % what)
		assert_almost_eq(material.roughness, 0.9, 1e-6, "%s: roughness 0.9" % what)
		assert_false(material.vertex_color_use_as_albedo, "%s: no vertex colour" % what)


func _assert_neutral_roof(found: Dictionary, what: String) -> void:
	var material := _material(found)
	assert_not_null(material, "%s: a StandardMaterial3D draws it" % what)
	if material != null:
		assert_eq(material.resource_path, ROOFS, "%s: the neutral roof material" % what)
		assert_false(material.vertex_color_use_as_albedo, "%s: no vertex colour" % what)


func test_the_named_triangles_are_drawn_as_the_pipeline_says() -> void:
	assert_not_null(_buildings, "the fixture's buildings and roofs are loaded")
	if _buildings == null:
		return
	var named: Array = _vectors()["triangles"]
	assert_gt(named.size(), 10, "the vectors name roofs, walls and a null roof")
	for v: Dictionary in named:
		var what: String = v["name"]
		var p := _points(v["tile"], int(v["triangle"]))
		for k in 3:
			var local: Array = v["local"][k]
			assert_eq(
				p[k], Vector3(local[0], local[1], local[2]), "%s: the file's vertex %d" % [what, k]
			)
		var found := _where(v["tile"], int(v["triangle"]))
		assert_false(found.is_empty(), "%s is drawn, as (a, c, b)" % what)
		if found.is_empty():
			continue
		match v["kind"]:
			"roof":
				_assert_coloured(found, Color.html(v["roof"]), what)
			"wall":
				_assert_plaster(found, what)
			"neutral_roof":
				_assert_neutral_roof(found, what)
			_:
				fail_test("%s: unknown kind %s" % [what, v["kind"]])


func test_every_triangle_is_drawn_by_its_building_s_colour() -> void:
	assert_not_null(_buildings, "the fixture's buildings and roofs are loaded")
	if _buildings == null:
		return
	var checked := 0
	for i in _roofs.chunks.size():
		var tile: String = _roofs.chunks[i]["tile"]
		var t := 0
		for building: Dictionary in _roofs.chunks[i]["buildings"]:
			for k in building["triangles"]:
				var p := _points(tile, t)
				var found := _where(tile, t)
				var what := "%s triangle %d (%s)" % [tile, t, building["uuid"]]
				t += 1
				assert_false(found.is_empty(), "%s is drawn" % what)
				if found.is_empty():
					continue
				checked += 1
				if (p[1] - p[0]).cross(p[2] - p[0]).normalized().y < 0.5:
					_assert_plaster(found, what)
				elif building["roof"] == null:
					_assert_neutral_roof(found, what)
				else:
					_assert_coloured(found, building["roof"], what)
		assert_eq(t, _chunk(tile)["indices"].size() / 3, "%s: every triangle once" % tile)
	assert_eq(checked, _drawn.size(), "every drawn triangle is a file triangle")


func test_nothing_overrides_what_the_meshes_draw() -> void:
	assert_not_null(_buildings, "the fixture's buildings and roofs are loaded")
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
