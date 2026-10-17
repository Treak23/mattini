extends GutTest
## Pinning tests for brief M3-14: a refused or missing photo, surfaces, trees or roofs block
## opens the error panel naming what cannot be shown and how to fix it, and everything else
## is still shown; in an exported build every fix is the release folder.
##
## Pinned decisions (docs/SPEC.md §10, M3's game; Hard Rule 2; m3-design.md §10): each
## refusal is logged once, by its reader, and shown in UI/ErrorPanel: the first line names
## what cannot be shown ("the aerial photo", "the surfaces (roads, paths, water and rock)",
## "the trees", "the roof colours", after M2's "the terrain" and "the buildings"; two joined
## by "and", more as "A, B and C"); then the refusal; then the commands, in this order:
##   the photo: download photo, photo;
##   the surfaces: download tlm, surfaces;
##   the trees: download surface, download tlm, trees;
##   the roof colours: download photo, roofs.
## The rest is still shown: without the photo the terrain keeps M2's clay look and the trees
## their placeholder colour (no photo bound); without the surfaces the photo look stays,
## without its classes; without the trees there is no "Trees" node; without the roof colours
## the buildings keep M2's roofs. Without the buildings the roofs are not read, so the panel
## names the buildings only. A refused manifest shows nothing and names all six. In an
## exported build (OS.has_feature("template")) a player has no pipeline, so every fix line
## reads "To fix <it or what>, keep mattini.pck and the data packs mattini-*.pck beside the
## executable: download the release folder again and keep its files together." and no command
## is named; main.gd's static error_text(refusals, manifest path, exported) builds the
## panel's text, so both forms are read here headless (called at run time: a main.gd without
## it fails this test by name, not by a parse error).
##
## Since brief M4-10 (design's full replacement of M3-14's file; only the refused manifest's
## test and this paragraph change): a refused manifest names all nine, M3's six and then "the
## mountains' shadows", "the photo's softened shadows" and "the sun's and the moon's course".
##
## Does NOT prove: that anything renders or looks right (no GPU); that an exported build
## reaches the panel (tools/export.sh step 6 starts one with its packs, not without them).

const CompleteWorld := preload("res://tests/complete_world.gd")
const MAIN_SCRIPT := "res://scripts/main.gd"
const SCRATCH_DIR := "user://test_main_scene_refusals"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const CLAY_SHADER := "res://shaders/terrain_clay.gdshader"
const PHOTO_SHADER := "res://shaders/terrain_photo.gdshader"
const RUN := "uv run --project pipeline python -m mattini "
const IN_ORDER := "To fix it, run these in the mattini folder, in this order:"
const EXPORTED := (
	"keep mattini.pck and the data packs mattini-*.pck beside the executable:"
	+ " download the release folder again and keep its files together."
)

var _cases := 0


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _write(change: Callable) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	return main


func _message(main: Node3D) -> String:
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	return main.get_node("UI/ErrorPanel/Message").text


## The panel's lines for one refusal: its first line, then its fix, the commands in order.
func _assert_one_refusal(message: String, what: String, commands: Array) -> void:
	assert_true(
		message.begins_with("mattini cannot show %s.\n" % what), "the first line: %s" % what
	)
	var fix := "\n".join(commands.map(func(c: String) -> String: return "    " + RUN + c))
	assert_true(message.ends_with("\n%s\n%s" % [IN_ORDER, fix]), "the commands: %s" % [commands])


## main.gd's static error_text, called at run time.
func _error_text(refusals: Array, path: String, exported: bool) -> String:
	var script: GDScript = load(MAIN_SCRIPT)
	for method: Dictionary in script.get_script_method_list():
		if method["name"] == "error_text":
			return script.call("error_text", refusals, path, exported)
	fail_test("main.gd has no static error_text(refusals, manifest path, exported)")
	return ""


func _shader_path(terrain: Terrain3D) -> String:
	var shader: Shader = terrain.material.shader_override
	return "" if shader == null else shader.resource_path


func _params(terrain: Terrain3D) -> Dictionary:
	var params: Variant = terrain.material.get("_shader_parameters")
	return params if typeof(params) == TYPE_DICTIONARY else {}


func _tree_photos(trees: Node) -> Array:
	var photos := []
	for child in trees.get_children():
		var instance := child as MultiMeshInstance3D
		if instance == null:
			continue
		var material: Material = instance.material_override
		if material == null:
			material = instance.multimesh.mesh.surface_get_material(0)
		if material is ShaderMaterial:
			photos.append(material.get_shader_parameter("photo"))
	return photos


func _has_albedo_vertex_colours(buildings: Node) -> bool:
	for child in buildings.get_children():
		var instance := child as MeshInstance3D
		for s in instance.mesh.get_surface_count():
			var material := instance.get_active_material(s) as StandardMaterial3D
			if material != null and material.vertex_color_use_as_albedo:
				return true
	return false


func test_without_the_photo_the_clay_look_and_the_placeholder_trees_stay() -> void:
	var path := _write(func(m: Dictionary) -> void: m["photo"] = null)
	var main := _main_with(path)
	_assert_one_refusal(_message(main), "the aerial photo", ["download photo", "photo"])
	assert_push_error("PhotoGrid: " + path, "PhotoGrid logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	var terrain: Terrain3D = main.get_node_or_null("Terrain")
	assert_not_null(terrain, "the terrain stays")
	if terrain != null:
		assert_eq(_shader_path(terrain), CLAY_SHADER, "in M2's clay look")
	var trees: Node3D = main.get_node_or_null("Trees")
	assert_not_null(trees, "the trees stay")
	if trees != null:
		var photos := _tree_photos(trees)
		assert_gt(photos.size(), 0, "a ShaderMaterial draws them")
		for photo: Variant in photos:
			assert_null(photo, "no photo bound: their placeholder colour")
	var buildings: Node3D = main.get_node_or_null("Buildings")
	assert_not_null(buildings, "the buildings stay")
	if buildings != null:
		assert_true(_has_albedo_vertex_colours(buildings), "with their roof colours")


func test_without_the_surfaces_the_photo_look_stays() -> void:
	var damaged := func(m: Dictionary) -> void: m["surfaces"]["sha256"] = "0".repeat(64)
	var path := _write(damaged)
	var main := _main_with(path)
	var what := "the surfaces (roads, paths, water and rock)"
	_assert_one_refusal(_message(main), what, ["download tlm", "surfaces"])
	assert_push_error("SurfaceGrid: " + path, "SurfaceGrid logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	var terrain: Terrain3D = main.get_node_or_null("Terrain")
	assert_not_null(terrain, "the terrain stays")
	if terrain != null:
		assert_eq(_shader_path(terrain), PHOTO_SHADER, "in the photo look")
		assert_true(_params(terrain).get("photo") is Texture2D, "with the photo")
		assert_null(_params(terrain).get("surfaces"), "without the classes")
	assert_not_null(main.get_node_or_null("Trees"), "the trees stay")
	assert_not_null(main.get_node_or_null("Buildings"), "the buildings stay")


func test_without_the_trees_the_rest_stays() -> void:
	var path := _write(func(m: Dictionary) -> void: m["trees"] = null)
	var main := _main_with(path)
	var commands := ["download surface", "download tlm", "trees"]
	_assert_one_refusal(_message(main), "the trees", commands)
	assert_push_error("TreeChunks: " + path, "TreeChunks logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	assert_null(main.get_node_or_null("Trees"), "no trees")
	var terrain: Terrain3D = main.get_node_or_null("Terrain")
	assert_not_null(terrain, "the terrain stays")
	if terrain != null:
		assert_eq(_shader_path(terrain), PHOTO_SHADER, "in the photo look")
	assert_not_null(main.get_node_or_null("Buildings"), "the buildings stay")


func test_without_the_roof_colours_the_buildings_keep_m2_s_roofs() -> void:
	var path := _write(func(m: Dictionary) -> void: m["roofs"] = null)
	var main := _main_with(path)
	_assert_one_refusal(_message(main), "the roof colours", ["download photo", "roofs"])
	assert_push_error("BuildingRoofs: " + path, "BuildingRoofs logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	var buildings: Node3D = main.get_node_or_null("Buildings")
	assert_not_null(buildings, "the buildings stay")
	if buildings != null:
		assert_false(_has_albedo_vertex_colours(buildings), "in M2's roofs, uncoloured")
	assert_not_null(main.get_node_or_null("Terrain"), "the terrain stays")
	assert_not_null(main.get_node_or_null("Trees"), "the trees stay")


func test_without_the_buildings_their_roofs_are_not_read() -> void:
	var path := _write(func(m: Dictionary) -> void: m["buildings"] = null)
	var main := _main_with(path)
	var message := _message(main)
	assert_true(message.begins_with("mattini cannot show the buildings.\n"), "the buildings only")
	assert_false(message.contains("roof colours"), "the roofs need the buildings: not refused")
	assert_push_error("BuildingChunks: " + path, "BuildingChunks logs its refusal")
	assert_push_error_count(1, "and BuildingRoofs logs nothing")
	assert_null(main.get_node_or_null("Buildings"), "no buildings")
	assert_not_null(main.get_node_or_null("Trees"), "the trees stay")


func test_a_refused_manifest_names_all_nine() -> void:
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("not_json.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string("{ not json")
	file.close()
	var main := _main_with(path)
	var first := (
		"mattini cannot show the terrain, the buildings, the aerial photo, the surfaces (roads,"
		+ " paths, water and rock), the trees, the roof colours, the mountains' shadows, the"
		+ " photo's softened shadows and the sun's and the moon's course.\n"
	)
	assert_true(_message(main).begins_with(first), "nothing is shown: all nine are named")
	assert_push_error("not valid JSON", "WorldConfig logs its refusal")
	assert_push_error_count(1, "once")


func test_in_an_exported_build_every_fix_is_the_release_folder() -> void:
	var path := "res://assets/generated/manifest.json"
	var photo := [
		"the aerial photo",
		PackedStringArray(["PhotoGrid: %s: the JPEG is missing" % path]),
		[RUN + "download photo", RUN + "photo"],
	]
	var trees := [
		"the trees",
		PackedStringArray(["TreeChunks: %s: a chunk is missing" % path]),
		[RUN + "download surface", RUN + "download tlm", RUN + "trees"],
	]
	var roofs := ["the roof colours", PackedStringArray(), [RUN + "download photo", RUN + "roofs"]]
	var one := _error_text([photo], path, true)
	assert_eq(
		one,
		(
			"\n"
			. join(
				[
					"mattini cannot show the aerial photo.",
					"",
					"PhotoGrid: %s: the JPEG is missing" % path,
					"",
					"To fix it, " + EXPORTED,
				]
			)
		),
		"one refusal, exported: the release folder, no command"
	)
	var three := _error_text([photo, trees, roofs], path, true)
	assert_true(
		three.begins_with(
			"mattini cannot show the aerial photo, the trees and the roof colours.\n"
		),
		"three names: A, B and C"
	)
	for what: String in ["the aerial photo", "the trees", "the roof colours"]:
		assert_string_contains(three, "\nTo fix %s, %s" % [what, EXPORTED], "%s, exported" % what)
	assert_false(three.contains("uv run"), "no pipeline command in an exported build")
	assert_false(three.contains("mattini folder"), "nor the source folder")
	var source := _error_text([photo], path, false)
	assert_true(
		source.ends_with("\n%s\n    %sdownload photo\n    %sphoto" % [IN_ORDER, RUN, RUN]),
		"in a source checkout, the commands"
	)
	assert_false(source.contains("release folder"), "and no release folder")
