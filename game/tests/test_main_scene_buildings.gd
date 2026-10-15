extends GutTest
## Pinning tests for brief M2-05: the main scene shows the buildings with the terrain,
## names swissBUILDINGS3D in the credits, and says on screen what it cannot show.
##
## Pinned decisions (docs/SPEC.md §10, M2's game; brief M2-05): after the terrain the main
## scene reads the manifest's buildings block (BuildingChunks) and adds the node
## "Buildings" (BuildingLoader) beside "Terrain". A refused or missing buildings block opens
## UI/ErrorPanel with the refusal and the commands `python -m mattini download buildings`
## and `python -m mattini buildings`, while the terrain stays; its first line names what
## cannot be shown: "the terrain", "the buildings" or "the terrain and the buildings". The
## credits list each loaded dataset on its own line, `<dataset> <edition>, <attribution>`.
##
## The shared terrain fixture has no buildings, so these tests compose a complete world in
## user://: the terrain fixture's manifest and heights, plus a buildings block written here
## for one 2 m box at the terrain's centre, in the same world. The buildings' placement is
## test_building_chunks.gd's subject, not this file's.
##
## Since brief M3-14 (design's full replacement of M2-05's file; only the world and this
## paragraph change): a missing photo, surfaces, trees or roofs block is refused on screen
## too, so the world is complete_world.gd's, which holds every block, its box the one this
## file built (2 m wide, its floor now below the ground, brief M2-08). "No buildings" means
## the buildings block null; the roofs then go unread (test_main_scene_refusals.gd).
##
## Does NOT prove: that anything renders or looks right (no GPU).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_main_scene_buildings"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const BUILDINGS_COMMANDS := [
	"python -m mattini download buildings",
	"python -m mattini buildings",
]

var _cases := 0


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _absorb_terrain3d_deprecation() -> void:
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	_absorb_terrain3d_deprecation()
	return main


## The complete world (complete_world.gd) with its buildings block (unless [param
## with_buildings] is false) and [param change] applied, written under a fresh folder.
## Returns the manifest's path.
func _write_case(with_buildings := true, change := Callable()) -> String:
	_cases += 1
	var edit := func(manifest: Dictionary) -> void:
		if not with_buildings:
			manifest["buildings"] = null
		if change.is_valid():
			change.call(manifest)
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), edit)


func _message(main: Node3D) -> String:
	return main.get_node("UI/ErrorPanel/Message").text


func test_terrain_and_buildings_are_shown_with_no_error() -> void:
	var main := _main_with(_write_case())
	assert_is(main.get_node_or_null("Terrain"), Terrain3D, "the terrain is built")
	var buildings := main.get_node_or_null("Buildings")
	assert_is(buildings, Node3D, "the buildings are built")
	if buildings != null:
		assert_eq(buildings.get_child_count(), 1, "one chunk")
		assert_is(buildings.get_node_or_null("2601-1199"), MeshInstance3D)
	assert_false(main.get_node("UI/ErrorPanel").visible, "no error panel")
	for error in get_errors():
		assert_true(error.handled, "no engine error or push_error: %s" % error.to_s())


func test_the_credits_name_both_datasets_each_on_its_own_line() -> void:
	var main := _main_with(_write_case())
	var credits: String = main.get_node("UI/PauseMenu/Credits").text
	var lines := credits.split("\n")
	assert_has(lines, "swissalti3d 2024, © swisstopo", "the terrain's line")
	assert_has(lines, "swissbuildings3d 2020, © swisstopo", "the buildings' line")
	assert_lt(
		lines.find("swissalti3d 2024, © swisstopo"),
		lines.find("swissbuildings3d 2020, © swisstopo"),
		"the terrain's first"
	)


func test_no_buildings_built_names_the_buildings_commands_and_keeps_the_terrain() -> void:
	var path := _write_case(false)
	var main := _main_with(path)
	assert_is(main.get_node_or_null("Terrain"), Terrain3D, "the terrain stays")
	assert_null(main.get_node_or_null("Buildings"), "no buildings")
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	var message := _message(main)
	assert_string_contains(message, "the buildings")
	assert_false(message.contains("the terrain and"), "only the buildings are missing")
	for command: String in BUILDINGS_COMMANDS:
		assert_string_contains(message, command)
	assert_push_error(path, "the refusal is also logged, naming the manifest")


func test_stale_buildings_are_refused_on_screen() -> void:
	var stale := func(m: Dictionary) -> void: m["buildings"]["world_sha256"] = "0".repeat(64)
	var path := _write_case(true, stale)
	var main := _main_with(path)
	assert_null(main.get_node_or_null("Buildings"), "stale buildings are not shown")
	assert_true(main.get_node("UI/ErrorPanel").visible, "the error panel is open")
	assert_string_contains(_message(main), "python -m mattini buildings")
	assert_push_error(path, "the refusal is also logged, naming the manifest")


func test_without_terrain_and_buildings_the_panel_names_both() -> void:
	var none := func(m: Dictionary) -> void: m["terrain"] = null
	var path := _write_case(false, none)
	var main := _main_with(path)
	assert_null(main.get_node_or_null("Terrain"))
	assert_null(main.get_node_or_null("Buildings"))
	var message := _message(main)
	assert_string_contains(message, "the terrain and the buildings")
	assert_string_contains(message, "python -m mattini terrain")
	assert_string_contains(message, "python -m mattini buildings")
	assert_push_error("TerrainGrid: " + path, "the terrain's refusal is logged")
	assert_push_error("BuildingChunks: " + path, "the buildings' refusal is logged")
