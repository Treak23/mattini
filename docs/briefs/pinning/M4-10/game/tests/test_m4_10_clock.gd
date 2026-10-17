extends GutTest
## Pinning tests for brief M4-10: the game's clock, its keys, its label, and the pause screen's
## frame cap.
##
## Pinned decisions (m4-design §9; SPEC §13 rows 43 and 45; brief M4-10): the main scene's
## clock, `time_unix` (Unix seconds UTC), starts at SkyClock.START_UNIX (2023-09-06T11:40:00Z,
## 13:40 CEST, the photo's moment) and runs at 1×: each frame adds delta × the speed. Six
## InputMap actions in game/project.godot, each bound to one physical key: time_earlier
## (Comma) and time_later (Period) move it by 15 minutes; day_earlier (BracketLeft) and
## day_later (BracketRight) by one day; time_speed (T) steps 1×, 60×, 600×, stopped, then 1×
## again; time_now (N) sets the computer's clock (Time.get_unix_time_from_system). A key held
## repeats (echo events count). The label UI/Clock reads "<SkyClock.local_text> · <speed>"
## ("6 Sep 2023 13:40 CEST · 1×", "· 60×", "· 600×", "· stopped"); it is hidden at the start,
## shown for 4 s of real time after a time key, and always while the pause screen is open. While
## the pause screen is open the clock stands still, the time keys do nothing, and Engine.max_fps
## is 15; closing it gives back the project's cap (application/run/max_fps), and so does the
## scene leaving the tree while paused. The pause screen lists the six actions with their keys.
## The label sits at the bottom left and meets neither of the pause screen's buttons.
##
## Does NOT prove: how the label looks or reads on the owner's screen; the keys' labels on the
## owner's keyboard layout (a headless run names US QWERTY's places); that the cap lowers the
## owner's GPU load (no GPU here).

const CompleteWorld := preload("res://tests/complete_world.gd")
const MAIN_SCENE := "res://main.tscn"
const SCRATCH_DIR := "user://test_m4_10_clock"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
## 2023-09-06T11:40:00Z.
const START := 1694000400.0
const ACTIONS := {
	&"time_earlier": KEY_COMMA,
	&"time_later": KEY_PERIOD,
	&"day_earlier": KEY_BRACKETLEFT,
	&"day_later": KEY_BRACKETRIGHT,
	&"time_speed": KEY_T,
	&"time_now": KEY_N,
}

var _complete := ""


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func after_each() -> void:
	Engine.max_fps = ProjectSettings.get_setting("application/run/max_fps")


func _main() -> Node3D:
	var main: Node3D = load(MAIN_SCENE).instantiate()
	main.manifest_path = _complete
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	# The scene's own frames stop here: the test steps the clock itself through _process.
	main.set_process(false)
	return main


func _press(action: StringName, echo := false) -> void:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = true
	var key := InputEventKey.new()
	key.physical_keycode = ACTIONS.get(action, KEY_NONE)
	key.pressed = true
	key.echo = echo
	# An InputEventAction cannot echo: a held key is sent as the key itself.
	get_viewport().push_input(key if echo else event)
	var release := InputEventAction.new()
	release.action = action
	release.pressed = false
	get_viewport().push_input(release)


func _clock(main: Node3D) -> Label:
	return main.get_node("UI/Clock")


func test_the_six_actions_are_bound_to_their_keys() -> void:
	for action: StringName in ACTIONS:
		assert_true(InputMap.has_action(action), "the action %s exists" % action)
		if not InputMap.has_action(action):
			continue
		var keys := []
		for event in InputMap.action_get_events(action):
			if event is InputEventKey:
				keys.append(event.physical_keycode)
		assert_eq(keys, [ACTIONS[action]], "%s: its one physical key" % action)


func test_the_clock_starts_at_the_photo_s_moment_at_1x() -> void:
	assert_eq(SkyClock.START_UNIX, START, "SkyClock's start is 2023-09-06T11:40:00Z")
	var main := _main()
	assert_eq(main.time_unix, START, "the clock starts at the photo's moment")
	assert_eq(main.clock_text(), "6 Sep 2023 13:40 CEST · 1×", "the label's text")
	assert_false(_clock(main).visible, "hidden at the start")
	main._process(2.5)
	assert_almost_eq(main.time_unix, START + 2.5, 0.000001, "1×: a frame adds its delta")


func test_the_keys_move_the_time_and_the_date() -> void:
	var main := _main()
	var steps := [
		[&"time_later", 900.0, "6 Sep 2023 13:55 CEST · 1×"],
		[&"time_later", 900.0, "6 Sep 2023 14:10 CEST · 1×"],
		[&"time_earlier", -900.0, "6 Sep 2023 13:55 CEST · 1×"],
		[&"day_later", 86400.0, "7 Sep 2023 13:55 CEST · 1×"],
		[&"day_earlier", -86400.0, "6 Sep 2023 13:55 CEST · 1×"],
		[&"day_earlier", -86400.0, "5 Sep 2023 13:55 CEST · 1×"],
	]
	var expected := START
	for step: Array in steps:
		_press(step[0])
		expected += step[1]
		assert_eq(main.time_unix, expected, "%s moves by %s s" % [step[0], step[1]])
		assert_eq(_clock(main).text, step[2], "the label after %s" % step[0])
		assert_true(_clock(main).visible, "shown after %s" % step[0])
	_press(&"time_later", true)
	assert_eq(main.time_unix, expected + 900.0, "a held key repeats")


func test_the_speed_steps_1_60_600_stopped() -> void:
	var main := _main()
	var speeds := [[60.0, "60×"], [600.0, "600×"], [0.0, "stopped"], [1.0, "1×"]]
	for speed: Array in speeds:
		_press(&"time_speed")
		var before: float = main.time_unix
		main._process(2.0)
		assert_almost_eq(main.time_unix, before + 2.0 * speed[0], 0.000001, "at %s" % speed[1])
		assert_true(_clock(main).text.ends_with(" · %s" % speed[1]), "the label: %s" % speed[1])


func test_now_is_the_computer_s_clock() -> void:
	var main := _main()
	_press(&"time_now")
	var now := Time.get_unix_time_from_system()
	assert_almost_eq(main.time_unix, now, 2.0, "the computer's clock, in Unix seconds UTC")
	assert_eq(_clock(main).text, main.clock_text(), "the label shows it")


func test_the_label_shows_for_4_seconds_after_a_key() -> void:
	var main := _main()
	_press(&"time_later")
	assert_true(_clock(main).visible, "shown at once")
	main._process(3.9)
	assert_true(_clock(main).visible, "still after 3.9 s")
	main._process(0.2)
	assert_false(_clock(main).visible, "hidden after 4.1 s")
	_press(&"time_speed")
	_press(&"time_speed")
	_press(&"time_speed")
	main._process(30.0)
	assert_false(_clock(main).visible, "stopped: the label still counts real time")


func test_pause_stops_the_time_caps_the_frames_and_shows_the_label() -> void:
	var main := _main()
	assert_eq(Engine.max_fps, 60, "the project's cap before")
	main.toggle_pause()
	assert_eq(Engine.max_fps, 15, "15 fps while the pause screen is open")
	assert_true(_clock(main).visible, "the label is shown while paused")
	var paused_at: float = main.time_unix
	main._process(10.0)
	assert_eq(main.time_unix, paused_at, "the clock stands still")
	assert_true(_clock(main).visible, "and stays shown")
	_press(&"time_later")
	_press(&"day_later")
	_press(&"time_speed")
	assert_eq(main.time_unix, paused_at, "the time keys do nothing while paused")
	assert_eq(main.clock_text(), "6 Sep 2023 13:40 CEST · 1×", "nor the speed")
	main.toggle_pause()
	assert_eq(Engine.max_fps, 60, "closing it gives back the project's cap")
	assert_false(_clock(main).visible, "and hides the label")
	main._process(1.0)
	assert_almost_eq(main.time_unix, paused_at + 1.0, 0.000001, "the clock runs again")


func test_a_scene_freed_while_paused_gives_the_cap_back() -> void:
	var main: Node3D = load(MAIN_SCENE).instantiate()
	main.manifest_path = _complete
	add_child(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.toggle_pause()
	assert_eq(Engine.max_fps, 15, "paused")
	remove_child(main)
	main.free()
	assert_eq(Engine.max_fps, 60, "the project's cap is back once the scene is gone")


func test_the_pause_screen_lists_the_time_keys() -> void:
	var main := _main()
	var controls: String = main.get_node("UI/PauseMenu/Controls").text
	for line in [
		"Comma: the time 15 minutes earlier",
		"Period: the time 15 minutes later",
		"BracketLeft: the date one day earlier",
		"BracketRight: the date one day later",
		"T: the time's speed: 1×, 60×, 600×, stopped",
		"N: the time and date now, this computer's clock",
	]:
		assert_string_contains(controls, "\n" + line + "\n", "the controls list: %s" % line)
	assert_lt(controls.find("Comma:"), controls.find("Escape:"), "before the pause key")


func test_the_label_sits_bottom_left_clear_of_the_buttons() -> void:
	var main := _main()
	main.toggle_pause()
	var clock := _clock(main)
	assert_eq(clock.get_parent(), main.get_node("UI"), "a child of UI")
	assert_gt(clock.get_index(), main.get_node("UI/PauseMenu").get_index(), "drawn over it")
	var size := get_viewport().get_visible_rect().size
	var rect := clock.get_global_rect()
	assert_lt(rect.position.x, size.x / 4.0, "at the left")
	assert_gt(rect.end.y, size.y * 0.9, "at the bottom")
	for button in ["Resume", "Quit"]:
		var other: Rect2 = main.get_node("UI/PauseMenu/" + button).get_global_rect()
		assert_false(rect.intersects(other), "clear of %s" % button)
