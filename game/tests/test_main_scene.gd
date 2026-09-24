extends GutTest
## The main scene loads, enters the tree and frees with no engine errors (brief M0-03).
##
## Does NOT prove that anything renders or looks right: containers have no GPU.


func test_main_scene_instantiates_and_frees_cleanly() -> void:
	var packed: PackedScene = load("res://main.tscn")
	assert_not_null(packed, "res://main.tscn loads")
	if packed == null:
		return
	var main := packed.instantiate()
	assert_is(main, Node3D, "the main scene's root is a Node3D")
	add_child(main)
	await wait_process_frames(2)
	assert_true(main.is_inside_tree(), "the main scene is in the tree")
	remove_child(main)
	main.free()
	assert_engine_error_count(0, "no engine errors while loading, running or freeing")
	assert_push_error_count(0, "no push_error while loading, running or freeing")
	assert_no_new_orphans("freeing the main scene leaves no orphan nodes")
