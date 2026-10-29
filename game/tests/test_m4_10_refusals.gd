extends GutTest
## Pinning tests for brief v0.4.0-08 (M4-10's refusals pin, cut to the sky: its two sky tests,
## the node "Surroundings" dropped from the first one's list; the far mountains' and the capture
## mask's tests are not in 0.4.0, and the data packs' two are test_pause_cap_and_pack_panel.gd's
## since brief v0.3.1-05): the main scene reads the manifest's sky block and shows its refusal on
## the error panel, and without it the sun stands still at a labelled placeholder.
##
## Pinned decisions (m4-design §9; brief v0.4.0-08 decisions 2 to 4, from M4-10 decisions 3 and
## 4): after the roof colours the main scene reads SkySite through the same catcher as the other
## readers. Its name on the panel's first line, after M3's six: "the sun's and the moon's
## course"; its command: sky. What still shows without the sun's place: everything else, and the
## sun standing still at the placeholder (grid azimuth 184.67°, elevation 50.1°: the flight's
## mean sun of config/shadows.json) whatever the clock reads, with no moon shown.
##
## Does NOT prove: that anything renders or looks right (no GPU); that the placeholder is where
## the sun stood (it is the flight's mean sun, a label, not the clock's).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_m4_10_refusals"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const RUN := "uv run --project pipeline python -m mattini "
const IN_ORDER := "To fix it, run these in the mattini folder, in this order:"
const ONE := "To fix it, run this in the mattini folder:"

var _cases := 0


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


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


func _angles(v: Vector3) -> Vector2:
	var azimuth := fposmod(rad_to_deg(atan2(v.x, -v.z)), 360.0)
	return Vector2(azimuth, rad_to_deg(asin(clampf(v.y, -1.0, 1.0))))


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
	for node in ["Terrain", "Trees", "Buildings"]:
		assert_not_null(main.get_node_or_null(node), "%s stays" % node)


func test_a_sun_s_place_for_another_world_is_refused() -> void:
	var path := _write(func(m: Dictionary) -> void: m["sky"]["world_sha256"] = "0".repeat(64))
	var main := _main_with(path)
	_assert_one_refusal(_message(main), "the sun's and the moon's course", ["sky"])
	assert_push_error("another world config", "SkySite logs it")
