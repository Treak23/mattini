extends Node3D
## The main scene (docs/SPEC.md §10, M1's and M2's game; briefs M1-05, M2-05). Reads the
## manifest at manifest_path, builds its terrain in the clay look (TerrainLoader, node
## "Terrain") under a fixed sun and a sky, then its buildings (BuildingLoader, node
## "Buildings", beside "Terrain"), and starts the free-fly camera START_ABOVE_M above the
## grid's centre, facing START_BEARING_DEG. The pause action opens UI/PauseMenu: the version
## (shown nowhere else, owner 2026-09-25), the controls, the credits, Resume and Quit. A
## missing, refused or stale manifest, terrain or buildings block opens UI/ErrorPanel: its
## first line names what cannot be shown, then each refusal with the commands that fix it
## (Hard Rule 2). What can be shown still is (the terrain without its buildings, and the
## other way round), and the camera flies either way. Each refusal is logged once, by the
## reader that refuses it (WorldConfig, TerrainGrid, BuildingChunks); the panel shows what
## they logged. Every direction (the start view, the sun) is measured through WorldConfig,
## never assumed, and the buildings stand where the pipeline placed them for the world
## config the manifest pins (Hard Rule 4).


## Collects the errors logged while the generated data is read, so that the error panel
## shows the refusal itself and not only the command.
class ErrorCatcher:
	extends Logger

	var _messages := PackedStringArray()
	var _mutex := Mutex.new()

	func _log_error(
		_function: String,
		_file: String,
		_line: int,
		code: String,
		rationale: String,
		_editor_notify: bool,
		_error_type: int,
		_script_backtraces: Array[ScriptBacktrace]
	) -> void:
		# push_error's text arrives as code; an engine error's own message as rationale.
		_mutex.lock()
		_messages.append(code if rationale.is_empty() else rationale)
		_mutex.unlock()

	func messages() -> PackedStringArray:
		_mutex.lock()
		var copy := _messages.duplicate()
		_mutex.unlock()
		return copy


const MANIFEST_FIX := ["uv run --project pipeline python -m mattini manifest"]
const TERRAIN_FIX := [
	"uv run --project pipeline python -m mattini download terrain",
	"uv run --project pipeline python -m mattini terrain",
]
const BUILDINGS_FIX := [
	"uv run --project pipeline python -m mattini download buildings",
	"uv run --project pipeline python -m mattini buildings",
]
## What the error panel's first line names when it cannot be shown.
const TERRAIN_WHAT := "the terrain"
const BUILDINGS_WHAT := "the buildings"
const START_ABOVE_M := 150.0
## Clockwise from LV95 north: towards the Matterhorn.
const START_BEARING_DEG := 235.0
## Below the horizon.
const START_PITCH_DOWN_DEG := 20.0
const SUN_ELEVATION_DEG := 35.0
## Clockwise from LV95 north.
const SUN_AZIMUTH_DEG := 150.0
const TERRAIN3D_TITLE := "Terrain3D 1.0.2"
const TERRAIN3D_LICENSE := "res://addons/terrain_3d/LICENSE.txt"
## godot-cpp is compiled into Terrain3D's library (M1 close, D17). Its LICENSE.md, verbatim,
## at the godot-cpp commit Terrain3D 1.0.2 builds with (brief M2-02's Findings name it).
const GODOT_CPP_TITLE := "godot-cpp (compiled into Terrain3D's library)"
const GODOT_CPP_LICENSE := "res://credits/godot-cpp-LICENSE.txt"
## The pause screen's list of controls: each InputMap action and what it does.
const CONTROLS := [
	[&"fly_forward", "fly forward, along the view"],
	[&"fly_back", "fly back"],
	[&"fly_left", "fly left"],
	[&"fly_right", "fly right"],
	[&"fly_up", "fly straight up"],
	[&"fly_down", "fly straight down"],
	[&"fly_fast", "hold to fly %s times faster"],
	[&"fly_look", "hold and move the mouse to look around"],
	[&"pause", "this screen; again to resume"],
]

@export var manifest_path := "res://assets/generated/manifest.json"

## LV95 east, north and up as local directions, once a WorldConfig was read.
var _east := Vector3.ZERO
var _north := Vector3.ZERO
var _up := Vector3.ZERO
var _terrain: Terrain3D

@onready var _camera: FreeFlyCamera = $Camera
@onready var _sun: DirectionalLight3D = $Sun
@onready var _ui: CanvasLayer = $UI
@onready var _error_panel: Control = $UI/ErrorPanel
@onready var _error_message: Label = $UI/ErrorPanel/Message
@onready var _pause_menu: Control = $UI/PauseMenu
@onready var _resume: Button = $UI/PauseMenu/Resume
@onready var _quit: Button = $UI/PauseMenu/Quit


func _ready() -> void:
	_error_panel.hide()
	_pause_menu.hide()
	_resume.pressed.connect(toggle_pause)
	_quit.pressed.connect(get_tree().quit)
	($UI/PauseMenu/Version as Label).text = "mattini %s" % _version()
	($UI/PauseMenu/Controls as Label).text = _controls_text()
	# The camera is in the tree and current by now: Terrain3D needs it on entering.
	var datasets := _load_world()
	($UI/PauseMenu/Credits as RichTextLabel).text = _credits_text(datasets)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"pause"):
		toggle_pause()
		get_viewport().set_input_as_handled()


## Opens the pause screen, or closes it when it is open. While it is open the camera
## ignores its controls and the mouse is free.
func toggle_pause() -> void:
	var open := not _pause_menu.visible
	_pause_menu.visible = open
	_camera.input_enabled = not open
	if open:
		_resume.grab_focus()


## Reads the manifest, then builds the terrain and then the buildings. A refused manifest
## shows neither; a refused terrain or buildings block leaves the other shown. Every refusal
## opens the error panel. Returns the credits' line of each dataset loaded, the terrain's
## first.
func _load_world() -> PackedStringArray:
	var datasets := PackedStringArray()
	var read_world := _caught(WorldConfig.from_manifest.bind(manifest_path))
	var world: WorldConfig = read_world[0]
	if world == null:
		_show_error([[TERRAIN_WHAT + " and " + BUILDINGS_WHAT, read_world[1], MANIFEST_FIX]])
		return datasets
	_read_directions(world)
	_place_sun()
	var refusals := []
	var read_grid := _caught(TerrainGrid.from_manifest.bind(manifest_path, world))
	var grid: TerrainGrid = read_grid[0]
	if grid == null:
		refusals.append([TERRAIN_WHAT, read_grid[1], TERRAIN_FIX])
	else:
		_show_terrain(grid)
		var source := _terrain_source()
		datasets.append(
			_dataset_line(source.get("dataset"), source.get("edition"), grid.attribution)
		)
	var read_buildings := _caught(BuildingChunks.from_manifest.bind(manifest_path, world))
	var buildings: BuildingChunks = read_buildings[0]
	if buildings == null:
		refusals.append([BUILDINGS_WHAT, read_buildings[1], BUILDINGS_FIX])
	else:
		_show_buildings(buildings)
		datasets.append(_dataset_line(buildings.dataset, buildings.edition, buildings.attribution))
	if not refusals.is_empty():
		_show_error(refusals)
	return datasets


## Calls [param read] while an ErrorCatcher listens; returns [its result, the errors logged
## meanwhile].
static func _caught(read: Callable) -> Array:
	var catcher := ErrorCatcher.new()
	OS.add_logger(catcher)
	var result: Variant = read.call()
	OS.remove_logger(catcher)
	return [result, catcher.messages()]


## Builds the terrain, starts the view over it and prints the terrain's startup line.
func _show_terrain(grid: TerrainGrid) -> void:
	_terrain = TerrainLoader.create(grid, self)
	move_child(_terrain, _ui.get_index())
	_camera.height_at = _ground_height
	_start_view(grid)
	# The startup line: an exported build is checked by it, headless (brief M1-06).
	print(
		(
			"mattini %s: terrain %s loaded, %d x %d vertices at %s m"
			% [_version(), grid.area, grid.columns, grid.rows, _number(grid.spacing_m)]
		)
	)


## Builds the buildings beside the terrain and prints the buildings' startup line.
func _show_buildings(chunks: BuildingChunks) -> void:
	var node := BuildingLoader.create(chunks, self)
	move_child(node, _ui.get_index())
	var count := 0
	var triangles := 0
	for chunk: Dictionary in chunks.chunks:
		count += chunk["buildings"]
		triangles += chunk["indices"].size() / 3
	# The second startup line: tools/export.sh checks it in the exported build (brief M2-05).
	print(
		(
			"mattini %s: buildings %s loaded, %d buildings in %d chunks, %d triangles"
			% [_version(), chunks.area, count, chunks.chunks.size(), triangles]
		)
	)


static func _version() -> String:
	return ProjectSettings.get_setting("application/config/version")


## A dataset's line in the credits: "<dataset> <edition>, <attribution>".
static func _dataset_line(dataset: Variant, edition: Variant, attribution: String) -> String:
	return "%s %s, %s" % [dataset, edition, attribution]


## The local height of the terrain under (x, z), or NaN where there is none.
func _ground_height(x: float, z: float) -> float:
	return _terrain.data.get_height(Vector3(x, 0.0, z))


## LV95 east, north and up in local coordinates, through the world config (to_local of
## points 1 m apart).
func _read_directions(world: WorldConfig) -> void:
	var e := world.origin_e
	var n := world.origin_n
	var h := world.height_offset
	var base := world.to_local(e, n, h)
	_east = world.to_local(e + 1.0, n, h) - base
	_north = world.to_local(e, n + 1.0, h) - base
	_up = world.to_local(e, n, h + 1.0) - base


## The local horizontal direction of a bearing in degrees clockwise from LV95 north.
func _bearing(degrees: float) -> Vector3:
	var bearing := deg_to_rad(degrees)
	return _east * sin(bearing) + _north * cos(bearing)


func _place_sun() -> void:
	var elevation := deg_to_rad(SUN_ELEVATION_DEG)
	var to_sun := _bearing(SUN_AZIMUTH_DEG) * cos(elevation) + _up * sin(elevation)
	_sun.basis = Basis.looking_at(-to_sun, _up)


## The camera START_ABOVE_M above the ground at the grid's centre, facing the start bearing,
## pitched down.
func _start_view(grid: TerrainGrid) -> void:
	var x := grid.x_min + (grid.columns - 1) * grid.spacing_m / 2.0
	var z := grid.z_min + (grid.rows - 1) * grid.spacing_m / 2.0
	var facing := _bearing(START_BEARING_DEG)
	# A camera turned by yaw about +y faces (−sin yaw, 0, −cos yaw).
	var yaw := atan2(-facing.x, -facing.z)
	var at := Vector3(x, _ground_height(x, z) + START_ABOVE_M, z)
	_camera.set_view(at, yaw, -deg_to_rad(START_PITCH_DOWN_DEG))


## The manifest's terrain.source block. TerrainGrid has just accepted this manifest, so it
## parses and holds the block.
func _terrain_source() -> Dictionary:
	var json := JSON.new()
	if (
		json.parse(FileAccess.get_file_as_string(manifest_path)) != OK
		or typeof(json.data) != TYPE_DICTIONARY
	):
		return {}
	var terrain: Variant = json.data.get("terrain")
	if typeof(terrain) != TYPE_DICTIONARY or typeof(terrain.get("source")) != TYPE_DICTIONARY:
		return {}
	return terrain["source"]


## Opens the error panel. Its first line names what cannot be shown; then, per refusal,
## what its reader logged and the commands that fix it. [param refusals] holds one
## [what, the messages logged, the commands] per refusal, the terrain's first.
func _show_error(refusals: Array) -> void:
	var what := PackedStringArray()
	for refusal: Array in refusals:
		what.append(refusal[0])
	var lines := PackedStringArray(["mattini cannot show %s." % " and ".join(what)])
	for refusal: Array in refusals:
		var messages: PackedStringArray = refusal[1]
		var fix: Array = refusal[2]
		lines.append("")
		if messages.is_empty():
			lines.append("The generated data at %s was refused." % manifest_path)
		else:
			lines.append_array(messages)
		lines.append("")
		var it: String = "it" if refusals.size() == 1 else refusal[0]
		if fix.size() == 1:
			lines.append("To fix %s, run this in the mattini folder:" % it)
		else:
			lines.append("To fix %s, run these in the mattini folder, in this order:" % it)
		for command: String in fix:
			lines.append("    " + command)
	_error_message.text = "\n".join(lines)
	_error_panel.show()


func _controls_text() -> String:
	var lines := PackedStringArray(["Controls", ""])
	for control: Array in CONTROLS:
		var action: StringName = control[0]
		var what: String = control[1]
		if what.contains("%s"):
			what = what % _number(_camera.fast_factor)
		lines.append("%s: %s" % [_bindings(action), what])
	var limits := [_camera.wheel_factor, _camera.min_speed_mps, _camera.max_speed_mps]
	var wheel := "Mouse Wheel: flying speed ×%s per notch, %s to %s m/s"
	lines.append(wheel % limits.map(_number))
	return "\n".join(lines)


## 5 for 5.0, 1.25 for 1.25: at most two decimals, no trailing zeros.
static func _number(value: float) -> String:
	return ("%.2f" % value).rstrip("0").rstrip(".")


## The keys and buttons bound to [param action], as this keyboard labels them.
func _bindings(action: StringName) -> String:
	var names := PackedStringArray()
	for event in InputMap.action_get_events(action):
		if event is InputEventKey:
			names.append(_key_name(event))
		elif event is InputEventMouseButton:
			names.append(event.as_text())
	return " or ".join(names)


## The actions are bound to physical keys (their place on the keyboard); the label shown is
## the one this keyboard layout puts there. A headless run has no keyboard layout (asking
## prints an ERROR there), so it shows the US QWERTY name of the place.
func _key_name(event: InputEventKey) -> String:
	var key := event.physical_keycode if event.physical_keycode != KEY_NONE else event.keycode
	if event.physical_keycode != KEY_NONE and DisplayServer.get_name() != "headless":
		var label := DisplayServer.keyboard_get_label_from_physical(event.physical_keycode)
		if label != KEY_NONE:
			key = label
	return OS.get_keycode_string(key)


## The credits: one line per loaded dataset ([param datasets], the terrain's first), then
## the software's licences.
func _credits_text(datasets: PackedStringArray) -> String:
	var lines := PackedStringArray(["Credits", "", "Data"])
	if datasets.is_empty():
		lines.append("No generated data is loaded, so no dataset is shown.")
	else:
		lines.append_array(datasets)
	lines.append_array(["", "Godot Engine", Engine.get_license_text(), ""])
	lines.append("Godot Engine's components")
	for component: Dictionary in Engine.get_copyright_info():
		for part: Dictionary in component["parts"]:
			var holders := "; ".join(part["copyright"])
			lines.append("%s: © %s (%s)" % [component["name"], holders, part["license"]])
	var licences := Engine.get_license_info()
	for licence: String in licences:
		lines.append_array(["", "Licence %s" % licence, licences[licence]])
	lines.append_array(["", TERRAIN3D_TITLE, _licence(TERRAIN3D_LICENSE)])
	lines.append_array(["", GODOT_CPP_TITLE, _licence(GODOT_CPP_LICENSE)])
	return "\n".join(lines)


## The licence text in the file at [param path]; when it cannot be read, an ERROR line and a
## sentence saying so in its place (Hard Rule 2).
func _licence(path: String) -> String:
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		var reason := error_string(FileAccess.get_open_error())
		push_error("Main: cannot read %s (%s)" % [path, reason])
		return "Its licence text could not be read from %s." % path
	return text
