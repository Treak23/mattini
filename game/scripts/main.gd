extends Node3D
## The main scene (docs/SPEC.md §10, M1's to M3's game; briefs M1-05, M2-05, M3-14). Reads the
## manifest at manifest_path and builds, in this order, its terrain (TerrainLoader, node
## "Terrain", the aerial photo on it with the surfaces drawn on the photo), its trees
## (TreeLoader, "Trees") and its buildings (BuildingLoader, "Buildings", each roof in its
## measured colour), beside each other, under the sun of the photo and a sky. It starts the
## free-fly camera START_ABOVE_M above the ground at the grid's centre, facing
## START_BEARING_DEG, pitched START_PITCH_DOWN_DEG down. The pause action opens UI/PauseMenu:
## the version (shown nowhere else, owner 2026-09-25), the controls, the credits, Resume and
## Quit. A missing, refused or stale manifest or block (the terrain, buildings, photo,
## surfaces, trees or roofs) opens UI/ErrorPanel: its first line names what cannot be shown,
## then each refusal with the commands that fix it, or in an exported build the release folder
## (Hard Rule 2). What can be shown still is: without the photo the terrain in M2's clay look
## and the trees in their placeholder green, without the surfaces the photo without their
## classes, without the trees no "Trees", without the roof colours M2's roofs; the terrain
## without its buildings, and the buildings without their terrain, the camera then starting
## START_ABOVE_M above the highest of their vertices, over the centre of their bounds, with
## the same bearing and pitch (brief M2-08, M2 R1 G-02). Without the buildings the roof
## colours are not read: one cause, one entry. With nothing, the camera starts at the scene's
## origin. It flies either way. Each refusal is logged once, by the reader that refuses it
## (WorldConfig, TerrainGrid, BuildingChunks, PhotoGrid, SurfaceGrid, TreeChunks,
## BuildingRoofs); the panel shows what they logged. Every direction (the start view, the
## sun) is measured through WorldConfig, never assumed, and the buildings and the trees stand
## where the pipeline placed them for the world config the manifest pins (Hard Rule 4): the
## Buildings and Trees nodes and their meshes sit at the scene's origin, unturned and
## unscaled (test_scene_placement.gd). Once everything is built, one startup line per block
## its reader accepted is printed, in the order terrain, buildings, photo, surfaces, trees,
## roofs (tools/export.sh checks them in an exported build).


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


const RUN := "uv run --project pipeline python -m mattini "
const MANIFEST_FIX := [RUN + "manifest"]
const TERRAIN_FIX := [RUN + "download terrain", RUN + "terrain"]
const BUILDINGS_FIX := [RUN + "download buildings", RUN + "buildings"]
const PHOTO_FIX := [RUN + "download photo", RUN + "photo"]
const SURFACES_FIX := [RUN + "download tlm", RUN + "surfaces"]
const TREES_FIX := [RUN + "download surface", RUN + "download tlm", RUN + "trees"]
const ROOFS_FIX := [RUN + "download photo", RUN + "roofs"]
## What the error panel's first line names when it cannot be shown.
const TERRAIN_WHAT := "the terrain"
const BUILDINGS_WHAT := "the buildings"
const PHOTO_WHAT := "the aerial photo"
const SURFACES_WHAT := "the surfaces (roads, paths, water and rock)"
const TREES_WHAT := "the trees"
const ROOFS_WHAT := "the roof colours"
## In an exported build a player has no pipeline: every fix is the release folder.
const EXPORTED_FIX := (
	"keep mattini.pck and the data packs mattini-*.pck beside the executable:"
	+ " download the release folder again and keep its files together."
)
const START_ABOVE_M := 150.0
## Clockwise from LV95 north: towards the Matterhorn.
const START_BEARING_DEG := 235.0
## Below the horizon.
const START_PITCH_DOWN_DEG := 20.0
## Where the sun stood when the photo was taken (7 September 2023, about 11:30 UTC): measured
## from the photo's shadows (brief M3-14). The solar position formulas give 181° and 50° for
## the flight time, within the shadows' measuring error; the shadows' values are kept.
const SUN_ELEVATION_DEG := 52.0
## Clockwise from LV95 north.
const SUN_AZIMUTH_DEG := 183.0
const TERRAIN3D_TITLE := "Terrain3D 1.0.2"
const TERRAIN3D_LICENSE := "res://addons/terrain_3d/LICENSE.txt"
## godot-cpp is compiled into Terrain3D's library (M1 close, D17). Its LICENSE.md, verbatim,
## at the godot-cpp commit Terrain3D 1.0.2 builds with (brief M2-02's Findings name it).
const GODOT_CPP_TITLE := "godot-cpp (compiled into Terrain3D's library)"
const GODOT_CPP_LICENSE := "res://credits/godot-cpp-LICENSE.txt"
## The CC0 textures' names, authors and asset pages, whole (brief M3-10).
const TEXTURES_LICENSE := "res://textures/LICENSE.txt"
## The streams' placeholder, always in the credits: the surfaces step draws a stream 2 m wide
## (its STREAM_WIDTH_MM), because swissTLM3D gives lines and no width.
const STREAMS_NOTE := "Streams: drawn 2 m wide, an assumed width: swissTLM3D gives none."
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


## Reads the manifest and every block, then builds the terrain, the trees and the buildings,
## and prints one startup line per block read. A refused manifest shows nothing; a refused
## block leaves the others shown (see the file's comment). Every refusal opens the error
## panel. Returns the credits' line of each dataset loaded, one per distinct line, sorted.
func _load_world() -> PackedStringArray:
	var read_world := _caught(WorldConfig.from_manifest.bind(manifest_path))
	var world: WorldConfig = read_world[0]
	if world == null:
		var every := [
			TERRAIN_WHAT, BUILDINGS_WHAT, PHOTO_WHAT, SURFACES_WHAT, TREES_WHAT, ROOFS_WHAT
		]
		_show_error([[_names(every), read_world[1], MANIFEST_FIX]])
		return PackedStringArray()
	_read_directions(world)
	_place_sun()
	var refusals := []
	var read_grid := _caught(TerrainGrid.from_manifest.bind(manifest_path, world))
	var grid: TerrainGrid = read_grid[0]
	if grid == null:
		refusals.append([TERRAIN_WHAT, read_grid[1], TERRAIN_FIX])
	var read_buildings := _caught(BuildingChunks.from_manifest.bind(manifest_path, world))
	var buildings: BuildingChunks = read_buildings[0]
	if buildings == null:
		refusals.append([BUILDINGS_WHAT, read_buildings[1], BUILDINGS_FIX])
	var read_photo := _caught(PhotoGrid.from_manifest.bind(manifest_path, world))
	var photo: PhotoGrid = read_photo[0]
	if photo == null:
		refusals.append([PHOTO_WHAT, read_photo[1], PHOTO_FIX])
	var read_surfaces := _caught(SurfaceGrid.from_manifest.bind(manifest_path, world))
	var surfaces: SurfaceGrid = read_surfaces[0]
	if surfaces == null:
		refusals.append([SURFACES_WHAT, read_surfaces[1], SURFACES_FIX])
	var read_trees := _caught(TreeChunks.from_manifest.bind(manifest_path, world))
	var trees: TreeChunks = read_trees[0]
	if trees == null:
		refusals.append([TREES_WHAT, read_trees[1], TREES_FIX])
	# The roof colours are checked against the buildings: without them there is one cause.
	var roofs: BuildingRoofs = null
	if buildings != null:
		var read_roofs := _caught(BuildingRoofs.from_manifest.bind(manifest_path, world, buildings))
		roofs = read_roofs[0]
		if roofs == null:
			refusals.append([ROOFS_WHAT, read_roofs[1], ROOFS_FIX])
	# One texture object for the photo, shared by the terrain and the trees: it is decoded
	# once (the village's is about 600 MiB of texture).
	if grid != null:
		_show_terrain(grid, photo, surfaces)
	if trees != null:
		_show_trees(trees, photo)
	if buildings != null:
		var node := _show_buildings(buildings, roofs)
		if grid == null:
			_start_view_over(node)
	_print_startup_lines(grid, buildings, photo, surfaces, trees, roofs)
	if not refusals.is_empty():
		_show_error(refusals)
	return _credited(grid, buildings, photo, surfaces, trees, roofs)


## Calls [param read] while an ErrorCatcher listens; returns [its result, the errors logged
## meanwhile].
static func _caught(read: Callable) -> Array:
	var catcher := ErrorCatcher.new()
	OS.add_logger(catcher)
	var result: Variant = read.call()
	OS.remove_logger(catcher)
	return [result, catcher.messages()]


## Builds the terrain (in the photo look when there is a photo, with the surfaces drawn on it
## when there are surfaces) and starts the view over it.
func _show_terrain(grid: TerrainGrid, photo: PhotoGrid, surfaces: SurfaceGrid) -> void:
	_terrain = TerrainLoader.create(grid, self, photo, surfaces)
	move_child(_terrain, _ui.get_index())
	_camera.height_at = _ground_height
	_start_view(grid)


## Builds the trees beside the terrain. With a photo they take their colour from it, from the
## very texture the terrain holds; without one, their placeholder green.
func _show_trees(chunks: TreeChunks, photo: PhotoGrid) -> void:
	var texture: Texture2D = photo.texture if photo != null else null
	var rect := photo.rect() if photo != null else Vector4.ZERO
	move_child(TreeLoader.create(chunks, self, texture, rect), _ui.get_index())


## Builds the buildings beside the terrain, each roof in its colour when there are roof
## colours, and returns their node.
func _show_buildings(chunks: BuildingChunks, roofs: BuildingRoofs) -> Node3D:
	var node := BuildingLoader.create(chunks, self, roofs)
	move_child(node, _ui.get_index())
	return node


## Prints one startup line per block that was read, together, in the order terrain,
## buildings, photo, surfaces, trees, roofs: an exported build is checked by them, headless
## (tools/export.sh step 6; briefs M1-06, M2-05, M3-14). The numbers are written as _number
## writes them.
func _print_startup_lines(
	grid: TerrainGrid,
	buildings: BuildingChunks,
	photo: PhotoGrid,
	surfaces: SurfaceGrid,
	trees: TreeChunks,
	roofs: BuildingRoofs
) -> void:
	var v := _version()
	if grid != null:
		var text := "mattini %s: terrain %s loaded, %d x %d vertices at %s m"
		print(text % [v, grid.area, grid.columns, grid.rows, _number(grid.spacing_m)])
	if buildings != null:
		var count := 0
		var triangles := 0
		for chunk: Dictionary in buildings.chunks:
			count += chunk["buildings"]
			triangles += chunk["indices"].size() / 3
		var text := "mattini %s: buildings %s loaded, %d buildings in %d chunks, %d triangles"
		print(text % [v, buildings.area, count, buildings.chunks.size(), triangles])
	if photo != null:
		var text := "mattini %s: photo %s loaded, %d x %d texels at %s m"
		print(text % [v, photo.area, photo.columns, photo.rows, _number(photo.cell_m)])
	if surfaces != null:
		var text := "mattini %s: surfaces %s loaded, %d x %d cells at %s m"
		print(text % [v, surfaces.area, surfaces.columns, surfaces.rows, _number(surfaces.cell_m)])
	if trees != null:
		var count := 0
		for chunk: Dictionary in trees.chunks:
			count += chunk["trees"]
		var text := "mattini %s: trees %s loaded, %d trees in %d chunks"
		print(text % [v, trees.area, count, trees.chunks.size()])
	if roofs != null:
		var count := 0
		var coloured := 0
		for chunk: Dictionary in roofs.chunks:
			for building: Dictionary in chunk["buildings"]:
				count += 1
				if building["roof"] != null:
					coloured += 1
		var text := "mattini %s: roofs %s loaded, %d of %d buildings coloured"
		print(text % [v, roofs.area, coloured, count])


## The credits' line of each dataset a block that was read comes from, once each, sorted:
## the photo and the roof colours share one.
func _credited(
	grid: TerrainGrid,
	buildings: BuildingChunks,
	photo: PhotoGrid,
	surfaces: SurfaceGrid,
	trees: TreeChunks,
	roofs: BuildingRoofs
) -> PackedStringArray:
	var lines := {}
	if grid != null:
		var source := _terrain_source()
		lines[_dataset_line(source.get("dataset"), source.get("edition"), grid.attribution)] = true
	for block: Variant in [buildings, photo, surfaces, trees, roofs]:
		if block != null:
			lines[_dataset_line(block.dataset, block.edition, block.attribution)] = true
	var sorted := PackedStringArray(lines.keys())
	sorted.sort()
	return sorted


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
	_start_view_at(Vector3(x, _ground_height(x, z) + START_ABOVE_M, z))


## Without a terrain: the camera START_ABOVE_M above the highest vertex of the buildings
## under [param buildings], over the centre of their bounds in the scene (every chunk mesh's
## box, through its global transform), facing the start bearing, pitched down.
func _start_view_over(buildings: Node3D) -> void:
	var bounds := AABB()
	var first := true
	for child in buildings.get_children():
		var mesh := child as MeshInstance3D
		if mesh == null:
			continue
		var box := mesh.global_transform * mesh.get_aabb()
		bounds = box if first else bounds.merge(box)
		first = false
	if first:
		return
	var centre := bounds.get_center()
	_start_view_at(Vector3(centre.x, bounds.end.y + START_ABOVE_M, centre.z))


## The camera at [param at], facing the start bearing, pitched START_PITCH_DOWN_DEG down.
func _start_view_at(at: Vector3) -> void:
	var facing := _bearing(START_BEARING_DEG)
	# A camera turned by yaw about +y faces (−sin yaw, 0, −cos yaw).
	var yaw := atan2(-facing.x, -facing.z)
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


## Opens the error panel with [method error_text]; an exported build gets the release
## folder as the fix, a source checkout the commands.
func _show_error(refusals: Array) -> void:
	_error_message.text = error_text(refusals, manifest_path, OS.has_feature("template"))
	_error_panel.show()


## The error panel's text. Its first line names what cannot be shown; then, per refusal, what
## its reader logged and how to fix it. [param refusals] holds one [what, the messages logged,
## the commands] per refusal, in the order of the blocks (the terrain's first); [param path]
## is the manifest. [param exported]: a player has no pipeline (brief M3-14), so every fix
## line, the manifest's included, is the release folder and no command is named.
static func error_text(refusals: Array, path: String, exported: bool) -> String:
	var what := PackedStringArray()
	for refusal: Array in refusals:
		what.append(refusal[0])
	var lines := PackedStringArray(["mattini cannot show %s." % _names(what)])
	for refusal: Array in refusals:
		var messages: PackedStringArray = refusal[1]
		var fix: Array = refusal[2]
		lines.append("")
		if messages.is_empty():
			lines.append("The generated data at %s was refused." % path)
		else:
			lines.append_array(messages)
		lines.append("")
		var it: String = "it" if refusals.size() == 1 else refusal[0]
		if exported:
			lines.append("To fix %s, %s" % [it, EXPORTED_FIX])
		elif fix.size() == 1:
			lines.append("To fix %s, run this in the mattini folder:" % it)
		else:
			lines.append("To fix %s, run these in the mattini folder, in this order:" % it)
		if not exported:
			for command: String in fix:
				lines.append("    " + command)
	return "\n".join(lines)


## The names joined as a sentence does: "A", "A and B", "A, B and C".
static func _names(names: PackedStringArray) -> String:
	if names.size() < 2:
		return "".join(names)
	return "%s and %s" % [", ".join(names.slice(0, names.size() - 1)), names[names.size() - 1]]


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


## The credits: under "Data" one line per dataset loaded ([param datasets], sorted, each
## once), then "Textures" with the CC0 textures' note whole, then "Placeholders" (the walls,
## the trees and the streams: they describe the build, so they are always listed), then the
## software's licences.
func _credits_text(datasets: PackedStringArray) -> String:
	var lines := PackedStringArray(["Credits", "", "Data"])
	if datasets.is_empty():
		lines.append("No generated data is loaded, so no dataset is shown.")
	else:
		lines.append_array(datasets)
	lines.append_array(["", "Textures", _licence(TEXTURES_LICENSE).strip_edges()])
	lines.append_array(
		["", "Placeholders", BuildingLoader.WALLS_NOTE, TreeLoader.TREES_NOTE, STREAMS_NOTE]
	)
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
