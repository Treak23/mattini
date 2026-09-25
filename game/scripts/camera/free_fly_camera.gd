class_name FreeFlyCamera
extends Camera3D
## The free-fly camera of M1 (docs/SPEC.md §10, the camera; brief M1-05), like the Godot
## editor's fly mode: hold fly_look (the right mouse button) to look; fly_forward and
## fly_back fly along the view, pitch included; fly_left and fly_right sideways; fly_up and
## fly_down straight up and down; fly_fast is fast_factor times faster; the mouse wheel
## changes the speed by wheel_factor per notch, between min_speed_mps and max_speed_mps.
## There is no physics in M1: after every move the camera asks height_at for the ground
## under it and stays clearance_m above it where there is ground (a finite height); where
## there is none it flies freely.

const MAX_PITCH_DEG := 89.0

@export var speed_mps := 30.0
@export var fast_factor := 5.0
@export var min_speed_mps := 2.0
@export var max_speed_mps := 1000.0
@export var wheel_factor := 1.25
## Radians turned per pixel of mouse motion (0.25° per pixel).
@export var mouse_sensitivity := 0.25 * PI / 180.0
@export var clearance_m := 1.5

## (x, z) → the local height of the ground under that point, or NaN where there is none.
## Unset, the camera flies freely everywhere.
var height_at: Callable
## False while a menu is open: the camera then ignores its controls and frees the mouse.
var input_enabled := true:
	set(value):
		input_enabled = value
		if not value:
			_set_looking(false)

var _yaw := 0.0
var _pitch := 0.0
## True while fly_look is held (and the controls are on): mouse motion turns the camera.
var _looking := false


func _init() -> void:
	near = 0.1
	far = 20000.0
	fov = 70.0


func _process(delta: float) -> void:
	if not input_enabled:
		return
	var direction := Vector3(
		Input.get_axis(&"fly_left", &"fly_right"),
		Input.get_axis(&"fly_down", &"fly_up"),
		Input.get_axis(&"fly_forward", &"fly_back"),
	)
	if direction != Vector3.ZERO:
		fly(delta, direction, Input.is_action_pressed(&"fly_fast"))


func _unhandled_input(event: InputEvent) -> void:
	if not input_enabled:
		return
	if event.is_action(&"fly_look"):
		_set_looking(event.is_pressed())
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseMotion and _looking:
		look(event.screen_relative)
		get_viewport().set_input_as_handled()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			change_speed(1)
			get_viewport().set_input_as_handled()
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			change_speed(-1)
			get_viewport().set_input_as_handled()


## Moves for [param delta] seconds. [param direction]: x right, y world up, z back, along
## the view (pitch included); a diagonal is no faster than a straight line.
func fly(delta: float, direction: Vector3, fast: bool) -> void:
	var move := basis.x * direction.x + Vector3.UP * direction.y + basis.z * direction.z
	var speed := speed_mps * (fast_factor if fast else 1.0)
	position += move.limit_length(1.0) * speed * delta
	_keep_above_ground()


## Turns by a mouse motion of [param relative] pixels; the pitch stops at ±89°.
func look(relative: Vector2) -> void:
	_yaw = wrapf(_yaw - relative.x * mouse_sensitivity, -PI, PI)
	_pitch = _clamp_pitch(_pitch - relative.y * mouse_sensitivity)
	rotation = Vector3(_pitch, _yaw, 0.0)


## Multiplies the speed by wheel_factor per step, within min_speed_mps and max_speed_mps.
func change_speed(steps: int) -> void:
	speed_mps = clampf(speed_mps * pow(wheel_factor, steps), min_speed_mps, max_speed_mps)


## Puts the camera at [param at], turned [param yaw] radians about the vertical (0 faces
## −z) and pitched [param pitch] radians (negative looks down), then above the ground.
func set_view(at: Vector3, yaw: float, pitch: float) -> void:
	_yaw = wrapf(yaw, -PI, PI)
	_pitch = _clamp_pitch(pitch)
	rotation = Vector3(_pitch, _yaw, 0.0)
	position = at
	_keep_above_ground()


func _keep_above_ground() -> void:
	if not height_at.is_valid():
		return
	var ground: float = height_at.call(position.x, position.z)
	if is_finite(ground) and position.y < ground + clearance_m:
		position.y = ground + clearance_m


## The mouse is captured exactly while the camera is looking, and free otherwise.
func _set_looking(looking: bool) -> void:
	_looking = looking
	if looking:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


static func _clamp_pitch(pitch: float) -> float:
	var limit := deg_to_rad(MAX_PITCH_DEG)
	return clampf(pitch, -limit, limit)
