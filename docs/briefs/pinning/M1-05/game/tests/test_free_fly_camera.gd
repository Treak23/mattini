extends GutTest
## Pinning tests for brief M1-05: the free-fly camera.
##
## Pinned decisions (docs/SPEC.md §10; the owner kept the proposed controls, 2026-09-25):
## like the Godot editor's fly mode. Hold the right mouse button to look; W/S fly along the
## view direction, A/D sideways, E/Q straight up and down; Shift is five times faster; the
## mouse wheel changes the speed by a factor of 1.25 per notch, between 2 and 1000 m/s;
## 30 m/s to start. Pitch stops at 89 degrees. The camera never goes below the ground under
## it plus 1.5 m where there is ground (no physics in M1: it asks the terrain's height),
## and flies freely where there is none. Escape is the pause action. Every control is an
## InputMap action, so it can be rebound.

var _camera: FreeFlyCamera


func before_each() -> void:
	_camera = FreeFlyCamera.new()
	add_child_autofree(_camera)


func _assert_vec(got: Vector3, want: Vector3, why: String) -> void:
	assert_almost_eq(got.x, want.x, 0.001, "%s: x" % why)
	assert_almost_eq(got.y, want.y, 0.001, "%s: y" % why)
	assert_almost_eq(got.z, want.z, 0.001, "%s: z" % why)


func test_starting_values() -> void:
	assert_eq(_camera.speed_mps, 30.0)
	assert_eq(_camera.fast_factor, 5.0)
	assert_eq(_camera.min_speed_mps, 2.0)
	assert_eq(_camera.max_speed_mps, 1000.0)
	assert_eq(_camera.wheel_factor, 1.25)
	assert_eq(_camera.clearance_m, 1.5)


func test_forward_flies_along_the_view() -> void:
	_camera.set_view(Vector3(0, 100, 0), 0.0, 0.0)
	_camera.fly(1.0, Vector3(0, 0, -1), false)
	_assert_vec(_camera.position, Vector3(0, 100, -30), "level, facing -z")
	_camera.set_view(Vector3(0, 100, 0), 0.0, deg_to_rad(-45.0))
	_camera.fly(1.0, Vector3(0, 0, -1), false)
	_assert_vec(_camera.position, Vector3(0, 100 - 30 * sin(PI / 4), -30 * cos(PI / 4)), "pitched")


func test_sideways_and_vertical() -> void:
	_camera.set_view(Vector3(0, 100, 0), 0.0, deg_to_rad(-30.0))
	_camera.fly(1.0, Vector3(1, 0, 0), false)
	_assert_vec(_camera.position, Vector3(30, 100, 0), "D flies right, level")
	_camera.fly(1.0, Vector3(0, 1, 0), false)
	_assert_vec(_camera.position, Vector3(30, 130, 0), "E flies straight up, even when pitched")


func test_fast_and_diagonal() -> void:
	_camera.set_view(Vector3.ZERO, 0.0, 0.0)
	_camera.fly(0.5, Vector3(0, 0, -1), true)
	_assert_vec(_camera.position, Vector3(0, 0, -75), "Shift: five times faster")
	_camera.set_view(Vector3.ZERO, 0.0, 0.0)
	_camera.fly(1.0, Vector3(1, 0, -1), false)
	assert_almost_eq(_camera.position.length(), 30.0, 0.001, "a diagonal is not faster")


func test_look_turns_and_pitch_stops_at_89_degrees() -> void:
	_camera.set_view(Vector3.ZERO, 0.0, 0.0)
	_camera.look(Vector2(100, 0))
	assert_almost_eq(_camera.rotation.y, -100 * _camera.mouse_sensitivity, 0.00001, "yaw")
	_camera.look(Vector2(0, 100000))
	assert_almost_eq(_camera.rotation.x, deg_to_rad(-89.0), 0.00001, "pitch stops looking down")
	_camera.look(Vector2(0, -200000))
	assert_almost_eq(_camera.rotation.x, deg_to_rad(89.0), 0.00001, "pitch stops looking up")


func test_the_wheel_changes_speed_within_limits() -> void:
	_camera.change_speed(1)
	assert_almost_eq(_camera.speed_mps, 37.5, 0.0001)
	_camera.change_speed(-2)
	assert_almost_eq(_camera.speed_mps, 24.0, 0.0001)
	_camera.change_speed(100)
	assert_eq(_camera.speed_mps, 1000.0)
	_camera.change_speed(-100)
	assert_eq(_camera.speed_mps, 2.0)


func test_never_below_the_ground_where_there_is_ground() -> void:
	_camera.height_at = func(_x: float, _z: float) -> float: return 50.0
	_camera.set_view(Vector3(0, 10, 0), 0.0, 0.0)
	assert_almost_eq(_camera.position.y, 51.5, 0.001, "lifted to 1.5 m above the ground")
	_camera.fly(1.0, Vector3(0, -1, 0), false)
	assert_almost_eq(_camera.position.y, 51.5, 0.001, "flying down stops at the ground")
	_camera.height_at = func(_x: float, _z: float) -> float: return NAN
	_camera.fly(1.0, Vector3(0, -1, 0), false)
	assert_almost_eq(_camera.position.y, 21.5, 0.001, "free where there is no ground")


func _has_key(action: StringName, key: Key) -> bool:
	for event in InputMap.action_get_events(action):
		if event is InputEventKey and (event.keycode == key or event.physical_keycode == key):
			return true
	return false


func test_the_controls_are_input_actions() -> void:
	var keys := {
		&"fly_forward": KEY_W,
		&"fly_back": KEY_S,
		&"fly_left": KEY_A,
		&"fly_right": KEY_D,
		&"fly_up": KEY_E,
		&"fly_down": KEY_Q,
		&"fly_fast": KEY_SHIFT,
		&"pause": KEY_ESCAPE,
	}
	for action: StringName in keys:
		assert_true(InputMap.has_action(action), "%s is an action" % action)
		assert_true(_has_key(action, keys[action]), "%s is bound to its key" % action)
	var right_button := false
	for event in InputMap.action_get_events(&"fly_look"):
		if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
			right_button = true
	assert_true(right_button, "fly_look is the right mouse button")
