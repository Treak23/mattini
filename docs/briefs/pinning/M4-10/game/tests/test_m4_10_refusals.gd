extends GutTest
## Pinning tests for brief M4-10: the main scene reads M4's three new blocks (the far
## mountains, the capture mask, the sun's place), builds what they hold, and shows each refusal
## and every missing data pack on the error panel.
##
## Pinned decisions (m4-design §9; briefs M4-06, M4-07, M4-08, M4-09, M4-10): after the roof
## colours the main scene reads SurroundingsGrid, CaptureShadowGrid and SkySite, each through
## the same catcher as the others. Their names on the panel's first line, in this order after
## M3's six: "the mountains' shadows", "the photo's softened shadows", "the sun's and the moon's
## course"; their commands, in order: download regio, surroundings; download surface, shadows;
## sky. What still shows: without the far mountains, no "Surroundings" node and everything else;
## without the mask, the photo unlifted (TerrainLoader's one texel of 0); without the sun's
## place, the sun stands still at the placeholder (grid azimuth 184.67°, elevation 50.1°: the
## flight's mean sun of config/shadows.json) and no moon is shown. With the block, the node
## "Surroundings" is SurroundingsLoader's, a child of the main scene before UI, at the scene's
## origin, unturned and unscaled, so its vertices stand where WorldConfig puts the grid; the
## terrain's photo shader holds CaptureShadowGrid's texture and rectangle. In an exported build
## (ReleaseBuild.is_exported()), DataPacks.missing_pack_errors(the executable's folder) is shown
## on the panel after its first line, which is "mattini cannot find every data pack." when
## nothing else is refused, then the release folder as the fix; error_text takes the messages
## as a fourth argument (default none).
##
## Does NOT prove: that anything renders or looks right (no GPU): that the far mountains' shadows
## land in the village (m4-design §0, the brief's Forward+ measurement, the owner's PC); the
## lift's look; what an exported build's panel shows (the release template ignores --script).

const CompleteWorld := preload("res://tests/complete_world.gd")
const MAIN_SCRIPT := "res://scripts/main.gd"
## The autoload DataPacks' script (it has no class_name; --check-only knows no autoload).
const DATA_PACKS := preload("res://scripts/data_packs.gd")
const SCRATCH_DIR := "user://test_m4_10_refusals"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const RUN := "uv run --project pipeline python -m mattini "
const IN_ORDER := "To fix it, run these in the mattini folder, in this order:"
const ONE := "To fix it, run this in the mattini folder:"
const EXPORTED := (
	"keep mattini.pck and the data packs mattini-*.pck beside the executable:"
	+ " download the release folder again and keep its files together."
)
## The complete world's capture mask: local x0, z0, width, depth (SHADOWS_BOX).
const SHADOWS_RECT := Vector4(1019.0, -4.5, 32.0, 48.0)

var _cases := 0


func after_all() -> void:
	ReleaseBuild.set_exported_for_tests(null)
	CompleteWorld.remove_tree(SCRATCH_DIR)


func after_each() -> void:
	ReleaseBuild.set_exported_for_tests(null)


func _write(change := Callable()) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.set_process(false)
	return main


func _message(main: Node3D) -> String:
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	return main.get_node("UI/ErrorPanel/Message").text


func _assert_one_refusal(message: String, what: String, commands: Array) -> void:
	assert_true(
		message.begins_with("mattini cannot show %s.\n" % what), "the first line: %s" % what
	)
	var fix := "\n".join(commands.map(func(c: String) -> String: return "    " + RUN + c))
	var heading := IN_ORDER if commands.size() > 1 else ONE
	assert_true(message.ends_with("\n%s\n%s" % [heading, fix]), "the commands: %s" % [commands])


func _params(terrain: Terrain3D) -> Dictionary:
	var params: Variant = terrain.material.get("_shader_parameters")
	return params if typeof(params) == TYPE_DICTIONARY else {}


func _angles(v: Vector3) -> Vector2:
	var azimuth := fposmod(rad_to_deg(atan2(v.x, -v.z)), 360.0)
	return Vector2(azimuth, rad_to_deg(asin(clampf(v.y, -1.0, 1.0))))


func test_the_far_mountains_stand_at_the_scene_s_origin_where_the_grid_says() -> void:
	var path := _write()
	var main := _main_with(path)
	assert_false(main.get_node("UI/ErrorPanel").visible, "the complete world opens no panel")
	var far := main.get_node_or_null("Surroundings") as MeshInstance3D
	assert_not_null(far, "the node Surroundings")
	if far == null:
		return
	assert_eq(far.get_parent(), main, "a child of the main scene")
	assert_lt(far.get_index(), main.get_node("UI").get_index(), "before UI")
	assert_eq(far.global_transform, Transform3D.IDENTITY, "at the origin, unturned, unscaled")
	assert_eq(
		far.cast_shadow, GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY, "shadows only"
	)
	var world := WorldConfig.from_manifest(path)
	var grid := SurroundingsGrid.from_manifest(path, world)
	var vertices: PackedVector3Array = far.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	assert_gt(vertices.size(), 0, "it holds triangles")
	# The grid's north-west corner and its south-east one, through the world config.
	for corner: Array in [[0, 0], [grid.columns - 1, grid.rows - 1]]:
		var box: Dictionary = CompleteWorld.SURROUNDINGS_BOX
		var e: float = box["e_min"] + corner[0] * grid.spacing_m
		var n: float = box["n_max"] - corner[1] * grid.spacing_m
		var h := grid.height(corner[0], corner[1])
		var expected := world.to_local(e, n, world.height_offset)
		expected.y = h
		var found := false
		for v in vertices:
			if v.distance_to(expected) < 0.001:
				found = true
				break
		assert_true(
			found, "the vertex of column %d, row %d at %s" % [corner[0], corner[1], expected]
		)


func test_without_the_far_mountains_the_rest_stays() -> void:
	var path := _write(func(m: Dictionary) -> void: m["surroundings"] = null)
	var main := _main_with(path)
	_assert_one_refusal(
		_message(main), "the mountains' shadows", ["download regio", "surroundings"]
	)
	assert_push_error("SurroundingsGrid: " + path, "SurroundingsGrid logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	assert_null(main.get_node_or_null("Surroundings"), "no far mountains")
	for node in ["Terrain", "Trees", "Buildings"]:
		assert_not_null(main.get_node_or_null(node), "%s stays" % node)


func test_the_mask_reaches_the_terrain_and_without_it_nothing_is_lifted() -> void:
	var main := _main_with(_write())
	var params := _params(main.get_node("Terrain"))
	var mask: Variant = params.get("capture_shadow")
	assert_true(mask is Texture2D, "the terrain holds the capture mask")
	if mask is Texture2D:
		assert_eq(mask.get_size(), Vector2(64, 96), "the mask's 64 x 96 cells")
	assert_eq(params.get("capture_shadow_rect"), SHADOWS_RECT, "its own rectangle")
	var path := _write(func(m: Dictionary) -> void: m["shadows"]["sha256"] = "0".repeat(64))
	main = _main_with(path)
	_assert_one_refusal(
		_message(main), "the photo's softened shadows", ["download surface", "shadows"]
	)
	assert_push_error("CaptureShadowGrid: " + path, "CaptureShadowGrid logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	params = _params(main.get_node("Terrain"))
	mask = params.get("capture_shadow")
	assert_true(mask is Texture2D, "a mask is still set (every sampler is)")
	if mask is Texture2D:
		assert_eq(mask.get_size(), Vector2(1, 1), "one texel of 0: nothing lifted")
	assert_true(params.get("photo") is Texture2D, "the photo stays")


func test_without_the_sun_s_place_the_sun_stands_still_at_the_placeholder() -> void:
	var path := _write(func(m: Dictionary) -> void: m["sky"] = null)
	var main := _main_with(path)
	_assert_one_refusal(_message(main), "the sun's and the moon's course", ["sky"])
	assert_push_error("SkySite: " + path, "SkySite logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	var placeholder := Vector2(184.67, 50.1)
	var sun: DirectionalLight3D = main.get_node("Sun")
	var angles := _angles(sun.global_transform.basis.z)
	assert_almost_eq(angles.x, placeholder.x, 0.001, "the placeholder's azimuth")
	assert_almost_eq(angles.y, placeholder.y, 0.001, "and elevation")
	main.time_unix += 6.0 * 3600.0
	main._place_sky()
	assert_almost_eq(_angles(sun.global_transform.basis.z).x, placeholder.x, 0.001, "it stays")
	assert_false(main.get_node("Moon").visible, "no moon")
	for node in ["Terrain", "Trees", "Buildings", "Surroundings"]:
		assert_not_null(main.get_node_or_null(node), "%s stays" % node)


func test_a_sun_s_place_for_another_world_is_refused() -> void:
	var path := _write(func(m: Dictionary) -> void: m["sky"]["world_sha256"] = "0".repeat(64))
	var main := _main_with(path)
	_assert_one_refusal(_message(main), "the sun's and the moon's course", ["sky"])
	assert_push_error("another world config", "SkySite logs it")


func test_in_an_exported_build_the_missing_packs_are_on_the_panel() -> void:
	ReleaseBuild.set_exported_for_tests(true)
	var main := _main_with(_write())
	var dir := OS.get_executable_path().get_base_dir()
	var packs: PackedStringArray = DATA_PACKS.missing_pack_errors(dir)
	assert_eq(packs.size(), 2, "this test's executable has no data pack beside it")
	var expected := PackedStringArray(["mattini cannot find every data pack.", ""])
	expected.append_array(packs)
	expected.append_array(["", "To fix it, " + EXPORTED])
	assert_eq(_message(main), "\n".join(expected), "the packs' messages and the release folder")
	assert_push_error_count(0, "main logs nothing more: DataPacks logged them at start")
	# With a refusal too: its fix is the release folder, from ReleaseBuild, not the OS.
	var path := _write(func(m: Dictionary) -> void: m["surroundings"] = null)
	main = _main_with(path)
	var message := _message(main)
	assert_true(message.begins_with("mattini cannot show the mountains' shadows.\n\n"), "named")
	assert_string_contains(message, "\n" + packs[0] + "\n", "and the packs")
	assert_true(message.ends_with("\nTo fix it, " + EXPORTED), "the release folder")
	assert_false(message.contains("uv run"), "no pipeline command")
	assert_push_error("SurroundingsGrid: " + path, "SurroundingsGrid logs its refusal")


func test_error_text_shows_the_packs_after_the_first_line() -> void:
	var path := "res://assets/generated/manifest.json"
	var photo := [
		"the aerial photo",
		PackedStringArray(["PhotoGrid: %s: the JPEG is missing" % path]),
		[RUN + "download photo", RUN + "photo"],
	]
	var packs := PackedStringArray(["DataPacks: the data pack mattini-photo.pck (x) is missing"])
	var script: GDScript = load(MAIN_SCRIPT)
	var text: String = script.call("error_text", [photo], path, true, packs)
	var expected := [
		"mattini cannot show the aerial photo.",
		"",
		packs[0],
		"",
		"PhotoGrid: %s: the JPEG is missing" % path,
		"",
		"To fix it, " + EXPORTED,
	]
	assert_eq(text, "\n".join(expected), "the pack's line after the first, then the refusal")
	var without: String = script.call("error_text", [photo], path, true)
	assert_false(without.contains("DataPacks"), "no packs by default")
