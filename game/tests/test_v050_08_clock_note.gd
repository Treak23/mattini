extends GutTest
## Pinning tests for brief v0.5.0-08 (board residue S-06, the 0.4.0 record's Question 2; the owner
## chose the note at the go of 2026-10-29, question A: "the clock's note outside the validated 2020
## to 2035 (the keys keep working)"): the clock's note.
##
## SkyClock's formulas were checked against tests/shared/sky_vectors.json, whose 295 instants lie
## between 27 Jan 2020 and 24 Dec 2035 (UTC). The day keys, 600x and the computer's clock (N) can
## take the game's clock anywhere; nothing said so on the screen.
##
## Pinned decisions: SkyClock (game/scripts/sky/sky_clock.gd) holds the validated range as two
## named constants, floats in Unix seconds UTC beside START_UNIX: VALID_FROM_UNIX = 1577836800.0
## (2020-01-01T00:00:00Z) and VALID_TO_UNIX = 2082758400.0 (2036-01-01T00:00:00Z), and a static
## in_validated_range(unix) that is true from VALID_FROM_UNIX inclusive up to VALID_TO_UNIX
## exclusive, and false for NaN and the infinities. The main scene's clock label
## (main.gd's clock_text, UI/Clock) appends NOTE to its text whenever the clock is outside that
## range, and the label is then shown and stays shown, however the clock got there (a time key,
## the clock running, the time set directly), until the clock is back inside; then the label
## hides CLOCK_SHOWN_S after the last key, as before. Nothing is clamped: every key moves the
## clock by its full step on both sides of each bound. Inside the range the label is as
## test_m4_10_clock.gd pins it, word for word. main.gd asks SkyClock.in_validated_range and holds
## neither bound as a number (one home for the range), and both files' header comments say what
## the code now does (Hard Rule 2).
##
## Does NOT prove: that the formulas are wrong outside the range or right inside it between the
## vectors (test_m4_04_sky_clock_vectors.gd and test_v040_04_sky_clock_margins.gd read the
## vectors); the computer's clock outside the range (N reads the real clock, which a test cannot
## set); how the label looks or reads on the owner's screen (no GPU here); the comments' meaning
## (their text is read).

const CompleteWorld := preload("res://tests/complete_world.gd")
const CLOCK_PATH := "res://scripts/sky/sky_clock.gd"
const MAIN_PATH := "res://scripts/main.gd"
const MAIN_SCENE := "res://main.tscn"
const SCRATCH_DIR := "user://test_v050_08_clock_note"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const VECTORS := "tests/shared/sky_vectors.json"
## 2020-01-01T00:00:00Z and 2036-01-01T00:00:00Z.
const FROM := 1577836800.0
const TO := 2082758400.0
## 2023-09-06T11:40:00Z, the clock's start.
const START := 1694000400.0
const DAY := 86400.0
const HALF_DAY := 43200.0
## What the label adds outside the range, after the speed.
const NOTE := " · the sky is unchecked outside 2020 to 2035 UTC"
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


func _press(action: StringName) -> void:
	var event := InputEventAction.new()
	event.action = action
	event.pressed = true
	get_viewport().push_input(event)
	var release := InputEventAction.new()
	release.action = action
	release.pressed = false
	get_viewport().push_input(release)


func _clock(main: Node3D) -> Label:
	return main.get_node("UI/Clock")


## SkyClock's constant [param name] read from the script's constants (so that a clock without it
## fails here by name, not by a parse error), or null.
func _constant(name: String) -> Variant:
	var constants: Dictionary = load(CLOCK_PATH).get_script_constant_map()
	return constants.get(name)


## Whether SkyClock has the static in_validated_range, read from the script's methods.
func _has_range_check() -> bool:
	for method: Dictionary in (load(CLOCK_PATH) as Script).get_script_method_list():
		if method["name"] == "in_validated_range":
			return true
	return false


## SkyClock.in_validated_range(unix), called by name.
func _inside(unix: float) -> Variant:
	return (load(CLOCK_PATH) as Script).call("in_validated_range", unix)


## The text of a file before its first line starting with [param stop].
func _header(path: String, stop: String) -> String:
	var text := FileAccess.get_file_as_string(path)
	var end := text.find("\n" + stop)
	return text.substr(0, end) if end >= 0 else ""


func test_the_range_is_2020_to_2035_utc() -> void:
	for pair: Array in [["VALID_FROM_UNIX", FROM], ["VALID_TO_UNIX", TO]]:
		var value: Variant = _constant(pair[0])
		assert_true(value is float, "SkyClock.%s exists and is a float (got %s)" % [pair[0], value])
		if value is float:
			assert_eq(value, pair[1], "SkyClock.%s" % pair[0])
	# A second way: the clock's own calendar reads the bounds as the first hour of a year in Zurich.
	assert_eq(SkyClock.local_text(FROM), "1 Jan 2020 01:00 CET", "2020-01-01T00:00:00Z")
	assert_eq(SkyClock.local_text(TO), "1 Jan 2036 01:00 CET", "2036-01-01T00:00:00Z")


func test_the_range_holds_every_vector_and_little_more() -> void:
	assert_true(_has_range_check(), "SkyClock.in_validated_range exists")
	if not _has_range_check():
		return
	var json := JSON.new()
	assert_eq(json.parse(FileAccess.get_file_as_string(CompleteWorld.repo_file(VECTORS))), OK)
	var first := INF
	var last := -INF
	for vector: Dictionary in json.data["vectors"]:
		var unix: float = vector["unix"]
		first = minf(first, unix)
		last = maxf(last, unix)
		assert_true(_inside(unix), "the validated instant %s is inside" % vector["utc"])
	assert_eq(json.data["vectors"].size(), 295, "the 295 validated instants")
	assert_between(first - FROM, 0.0, 31.0 * DAY, "the first vector within 31 days of the start")
	assert_between(TO - last, 0.0, 31.0 * DAY, "the last vector within 31 days of the end")


func test_in_validated_range_inside_at_both_edges_and_outside() -> void:
	assert_true(_has_range_check(), "SkyClock.in_validated_range exists")
	if not _has_range_check():
		return
	var cases := [
		[START, true, "the clock's start"],
		[FROM, true, "the first second of 2020 (UTC)"],
		[FROM + 0.5, true, "half a second into 2020"],
		[FROM - 0.5, false, "half a second before 2020"],
		[FROM - 1.0, false, "the last second of 2019"],
		[TO - 1.0, true, "the last second of 2035"],
		[TO - 0.5, true, "half a second before 2036"],
		[TO, false, "the first second of 2036"],
		[TO + 1.0, false, "a second into 2036"],
		[0.0, false, "1970"],
		[-1.0e9, false, "1938"],
		[4.0e9, false, "2096"],
		[NAN, false, "NaN"],
		[INF, false, "+infinity"],
		[-INF, false, "-infinity"],
	]
	for case: Array in cases:
		assert_eq(_inside(case[0]), case[1], "in_validated_range at %s (%s)" % [case[2], case[0]])


func test_the_day_keys_cross_both_bounds_unclamped_and_the_label_says_so() -> void:
	var main := _main()
	var steps := [
		# [start, key, step, label, outside]
		[TO - HALF_DAY, &"day_later", DAY, "1 Jan 2036 13:00 CET · 1×" + NOTE, true],
		[TO + HALF_DAY, &"day_later", DAY, "2 Jan 2036 13:00 CET · 1×" + NOTE, true],
		[TO - HALF_DAY, &"time_later", 900.0, "31 Dec 2035 13:15 CET · 1×", false],
		[TO - 600.0, &"time_later", 900.0, "1 Jan 2036 01:05 CET · 1×" + NOTE, true],
		[FROM + HALF_DAY, &"day_earlier", -DAY, "31 Dec 2019 13:00 CET · 1×" + NOTE, true],
		[FROM - HALF_DAY, &"day_earlier", -DAY, "30 Dec 2019 13:00 CET · 1×" + NOTE, true],
		[FROM + HALF_DAY, &"time_earlier", -900.0, "1 Jan 2020 12:45 CET · 1×", false],
		[FROM + 600.0, &"time_earlier", -900.0, "1 Jan 2020 00:55 CET · 1×" + NOTE, true],
	]
	for step: Array in steps:
		main.time_unix = step[0]
		_press(step[1])
		var name := "%s from %s" % [step[1], SkyClock.local_text(step[0])]
		assert_eq(main.time_unix, step[0] + step[2], "%s: the full step, unclamped" % name)
		assert_eq(_clock(main).text, step[3], "%s: the label" % name)
		assert_true(_clock(main).visible, "%s: shown" % name)
		main._process(4.1)
		assert_eq(_clock(main).visible, step[4], "%s: shown after 4.1 s while outside" % name)


func test_outside_the_label_stays_until_the_clock_is_back() -> void:
	var main := _main()
	main.time_unix = TO - HALF_DAY
	_press(&"day_later")
	for i in 3:
		main._process(30.0)
		assert_true(_clock(main).visible, "still shown after %d s outside" % (30 * (i + 1)))
	assert_true(_clock(main).text.ends_with(NOTE), "the note follows the clock")
	_press(&"day_earlier")
	assert_eq(_clock(main).text, "31 Dec 2035 13:01 CET · 1×", "back inside: no note")
	main._process(3.9)
	assert_true(_clock(main).visible, "back inside: shown for 4 s after the key")
	main._process(0.2)
	assert_false(_clock(main).visible, "back inside: hidden after 4.1 s, as before")


func test_the_note_whenever_the_clock_is_outside_however_it_got_there() -> void:
	var main := _main()
	assert_false(_clock(main).visible, "hidden at the start")
	var cases := [
		# [time set, frame, label, shown]
		[FROM, 0.0, "1 Jan 2020 01:00 CET · 1×", false],
		[FROM - 1.0, 0.0, "1 Jan 2020 00:59 CET · 1×" + NOTE, true],
		[FROM - 1.0, 1.0, "1 Jan 2020 01:00 CET · 1×", false],
		[TO - 1.0, 0.0, "1 Jan 2036 00:59 CET · 1×", false],
		# Hidden and inside, then a frame that runs past the bound: shown in that same frame.
		[TO - 1.0, 2.0, "1 Jan 2036 01:00 CET · 1×" + NOTE, true],
		[TO, 0.0, "1 Jan 2036 01:00 CET · 1×" + NOTE, true],
		[START, 0.0, "6 Sep 2023 13:40 CEST · 1×", false],
	]
	for case: Array in cases:
		main.time_unix = case[0]
		main._process(case[1])
		var name := "the time set to %s, a frame of %s s" % [case[0], case[1]]
		assert_eq(main.clock_text(), case[2], "%s: the text" % name)
		assert_eq(_clock(main).visible, case[3], "%s: shown only outside" % name)
		if case[3]:
			assert_eq(_clock(main).text, case[2], "%s: the label shows it" % name)


func test_at_600x_the_clock_runs_out_and_the_label_follows() -> void:
	var main := _main()
	_press(&"time_speed")
	_press(&"time_speed")
	main.time_unix = TO - 300.0
	main._process(5.0)
	assert_eq(main.time_unix, TO + 2700.0, "600×: 5 s run on past the bound, unclamped")
	assert_eq(_clock(main).text, "1 Jan 2036 01:45 CET · 600×" + NOTE, "the label")
	main._process(10.0)
	assert_true(_clock(main).visible, "still shown after 15 s at 600× outside")
	# Stopped there: the clock stays and the note with it.
	_press(&"time_speed")
	main._process(1.0)
	assert_eq(main.time_unix, TO + 8700.0, "600× for 15 s, then stopped")
	assert_eq(_clock(main).text, "1 Jan 2036 03:25 CET · stopped" + NOTE, "stopped: the note")


func test_paused_outside_the_note_fits_the_screen_and_stays() -> void:
	var main := _main()
	main.time_unix = FROM - HALF_DAY
	main.toggle_pause()
	var clock := _clock(main)
	assert_eq(clock.text, "31 Dec 2019 13:00 CET · 1×" + NOTE, "paused: the label with the note")
	var size := get_viewport().get_visible_rect().size
	var rect := clock.get_global_rect()
	assert_lt(rect.end.x, size.x, "the note fits the screen's width")
	for button in ["Resume", "Quit"]:
		var other: Rect2 = main.get_node("UI/PauseMenu/" + button).get_global_rect()
		assert_false(rect.intersects(other), "clear of %s" % button)
	main.toggle_pause()
	main._process(0.1)
	assert_true(clock.visible, "resumed outside: shown again at the next frame")
	assert_true(clock.text.ends_with(NOTE), "with the note")


func test_main_asks_the_clock_and_the_comments_say_it() -> void:
	var main_text := FileAccess.get_file_as_string(MAIN_PATH)
	assert_true(main_text.contains("SkyClock.in_validated_range("), "main.gd asks SkyClock")
	for bound in ["1577836800", "2082758400"]:
		assert_false(main_text.contains(bound), "main.gd holds no bound as a number: %s" % bound)
	var main_header := _header(MAIN_PATH, "class ErrorCatcher")
	assert_true(main_header.contains("in_validated_range"), "main.gd's header names the note")
	var clock_header := _header(CLOCK_PATH, "const START_UNIX")
	for word in ["VALID_FROM_UNIX", "VALID_TO_UNIX", "in_validated_range"]:
		assert_true(clock_header.contains(word), "sky_clock.gd's header names %s" % word)
