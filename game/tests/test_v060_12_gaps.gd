extends GutTest
## Gaps file for brief v0.6.0-12 (the prover's finding on main.gd's _load_world; lesson 51).
##
## The harm: three lines at the start of _load_world, `_missing_packs`, `_far_colour_note` and
## `_far` reset to nothing, that no test could fail (mutation 06 of the brief: `_far = null` taken
## out, every test green), because _load_world has one caller, _ready, and the three fields start
## empty. A line nothing pins is a line a later edit drops without a sound; here the one that
## would matter is `_far`: _ground_height rests the camera on it (the brief's decision 2), so a
## far grid left over from an earlier read would be a floor the scene no longer holds.
##
## Decision tested: a call of _load_world starts from nothing. The main scene is built on the
## complete test world (its far colour is filled, so the far terrain is read, drawn and its note is
## set), the three fields are set as a read leaves them, and _load_world is called again on a
## manifest that is refused (it is not JSON): it returns before it reads anything, so only the
## resets can have emptied the fields.
##
## Does NOT prove: that _load_world can run twice on a manifest that reads (it adds the terrain,
## the trees, the buildings and the far terrain as children and removes none, so a second good read
## would draw them twice: it is called once, from _ready, and this test calls it again only to see
## the three resets); that the far terrain's node is gone after the refused call (it is not: the
## test does not claim it); anything about how the game looks.

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_v060_12_gaps"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func test_a_load_that_is_refused_keeps_nothing_of_an_earlier_one() -> void:
	var path := CompleteWorld.write(SCRATCH_DIR.path_join("world"))
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.set_process(false)
	assert_not_null(main.get("_far"), "before: the far terrain is read")
	assert_false(String(main.get("_far_colour_note")).is_empty(), "before: its note is set")
	var packs := PackedStringArray(["a data pack that was missing"])
	main.set("_missing_packs", packs)

	var broken := SCRATCH_DIR.path_join("broken.json")
	var file := FileAccess.open(broken, FileAccess.WRITE)
	file.store_string("{ not json")
	file.close()
	main.manifest_path = broken
	var credited: PackedStringArray = main._load_world()

	assert_push_error("not valid JSON", "WorldConfig logs the refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	assert_true(credited.is_empty(), "nothing is credited")
	assert_null(main.get("_far"), "the far grid of the first read is dropped")
	assert_eq(main.get("_far_colour_note"), "", "so is its note")
	var left: PackedStringArray = main.get("_missing_packs")
	assert_true(left.is_empty(), "and the missing packs (an exported build asks again)")
