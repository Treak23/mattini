extends Node3D
## The main scene (docs/SPEC.md §10, M1's to M3's game; briefs M1-05, M2-05, M3-14, v0.3.1-05).
## Reads the manifest at manifest_path and builds, in this order, its terrain (TerrainLoader,
## node "Terrain", the aerial photo on it with the surfaces drawn on the photo), its trees
## (TreeLoader, "Trees") and its buildings (BuildingLoader, "Buildings", each roof in its
## measured colour), beside each other, under a sun, a moon and a sky that follow the game's clock
## (the sky rig, below). It starts the
## free-fly camera START_ABOVE_M above the ground at the grid's centre, facing
## START_BEARING_DEG, pitched START_PITCH_DOWN_DEG down. The pause action opens UI/PauseMenu:
## the version (shown nowhere else, owner 2026-09-25), the controls, the credits, Resume and
## Quit. While it is open the frame rate is capped at PAUSED_MAX_FPS (15); closing it, or the
## scene leaving the tree, gives back the project's cap (application/run/max_fps). A missing,
## refused or stale manifest or block (the terrain, buildings, photo, surfaces, trees, roofs, the
## capture mask or the sky)
## opens UI/ErrorPanel: its first line names what cannot be shown, then each refusal with the
## commands that fix it, or in an exported build the release folder (Hard Rule 2). In an
## exported build (ReleaseBuild.is_exported()) the data packs missing beside the executable
## (DataPacks.missing_pack_errors, asked before the manifest is read) are listed after the
## first line, before the refusals, and open the panel on their own, its first line then
## "mattini cannot find every data pack."; main logs nothing more about them (DataPacks logged
## them at start). What can be shown still is: without the photo the terrain in M2's clay look
## and the trees in their placeholder green, without the surfaces the photo without their
## classes, without the trees no "Trees", without the roof colours M2's roofs, without the capture
## mask the photo unlifted (the mask is read after the roof colours and handed to the terrain as
## TerrainLoader.create's fifth argument, brief v0.5.0-05; without a photo or a terrain it is
## still read, so its refusal is its own entry); the terrain
## without its buildings, and the buildings without their terrain, the camera then starting
## START_ABOVE_M above the highest of their vertices, over the centre of their bounds, with
## the same bearing and pitch (brief M2-08, M2 R1 G-02). Without the buildings the roof
## colours are not read: one cause, one entry. With nothing, the camera starts at the scene's
## origin. It flies either way. Each refusal is logged once, by the reader that refuses it
## (WorldConfig, TerrainGrid, BuildingChunks, PhotoGrid, SurfaceGrid, TreeChunks,
## BuildingRoofs, CaptureShadowGrid, SkySite); the panel shows what they logged. Every direction
## (the start view, the sun and the moon) is measured through WorldConfig, never assumed, and the
## buildings and the trees stand
## where the pipeline placed them for the world config the manifest pins (Hard Rule 4): the
## Buildings and Trees nodes and their meshes sit at the scene's origin, unturned and
## unscaled (test_scene_placement.gd). Once everything is built, one startup line per block
## its reader accepted is printed, in the order terrain, buildings, photo, surfaces, trees,
## roofs, shadows (tools/export.sh checks them in an exported build).
##
## The sky (brief v0.4.0-08, from M4-10): the clock, time_unix, starts at SkyClock.START_UNIX (the
## photo's moment) and runs at 1x (SPEEDS), standing still while the pause screen is
## open. Every frame the
## sun and the moon stand where SkyClock puts them for the clock's time at the manifest's sky
## block (SkySite): the true azimuth plus the block's true_to_grid_deg is a grid azimuth, turned
## into a local direction through WorldConfig's east, north and up, and the SkyRig lights the
## scene from them (the physical sky, the exposure by day and night, and the stars when
## res://sky/stars.csv exists, credited on the pause screen). Without a sky block the sun stands
## still at a labelled placeholder and the panel says why. Without a world config no sky is made:
## the directions need it, and the owner's axes written here would be a second home for the axis
## mapping (Hard Rule 4).
##
## The time keys (brief v0.4.0-09): time_earlier and time_later move the clock 15 minutes,
## day_earlier and day_later a day (held keys repeat), time_speed steps SPEEDS (1x, 60x, 600x,
## stopped) and time_now sets the computer's clock; they do nothing while the pause screen is
## open. UI/Clock says
## the time and the speed (clock_text) for CLOCK_SHOWN_S real seconds after a key, and always while
## the pause screen is open. While the clock is outside the range the sky was checked in
## (SkyClock.in_validated_range is false) the label also carries CLOCK_NOTE and stays shown at
## every frame, however the clock got there; the keys are not clamped.


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
const SHADOWS_FIX := [RUN + "download surface", RUN + "shadows"]
const SKY_FIX := [RUN + "sky"]
## What the error panel's first line names when it cannot be shown.
const TERRAIN_WHAT := "the terrain"
const BUILDINGS_WHAT := "the buildings"
const PHOTO_WHAT := "the aerial photo"
const SURFACES_WHAT := "the surfaces (roads, paths, water and rock)"
const TREES_WHAT := "the trees"
const ROOFS_WHAT := "the roof colours"
const SHADOWS_WHAT := "the photo's softened shadows"
const SKY_WHAT := "the sun's and the moon's course"
## In an exported build a player has no pipeline: every fix is the release folder.
const EXPORTED_FIX := (
	"keep mattini.pck and the data packs mattini-*.pck beside the executable:"
	+ " download the release folder again and keep its files together."
)
## The script of the autoload DataPacks, preloaded because it has no class_name and the gate's
## parse step (--check-only) knows no autoload.
const DATA_PACKS := preload("res://scripts/data_packs.gd")
const START_ABOVE_M := 150.0
## Clockwise from LV95 north: towards the Matterhorn.
const START_BEARING_DEG := 235.0
## Below the horizon.
const START_PITCH_DOWN_DEG := 20.0
## A PLACEHOLDER, not the clock's sun (Hard Rule 2): where the sun stands without a sky block,
## the flight's mean sun from config/shadows.json (grid azimuth clockwise from LV95 north, and
## elevation); the two numbers were copied by hand from that file, nothing reads it here, and they
## are this placeholder's only use. The clock still runs; the panel says why the sun does not move.
const FALLBACK_SUN_AZIMUTH_GRID_DEG := 184.67
const FALLBACK_SUN_ELEVATION_DEG := 50.1
## The stars' table: its presence switches the stars on (brief v0.4.0-06). The rig's script is
## loaded by path so that this script parses without it.
const STARS_TABLE := "res://sky/stars.csv"
const SKY_RIG_SCRIPT := "res://scripts/sky/sky_rig.gd"
## The credits' "Sky" section: the sun's and the moon's formulas and, with the stars, the
## Hipparcos credit (the first line of game/sky/stars.csv without its "# ").
const SUN_NOTE := (
	"Sun: NOAA's solar position calculations (Meeus, Astronomical Algorithms),"
	+ " https://gml.noaa.gov/grad/solcalc/calcdetails.html"
)
const MOON_NOTE := (
	"Moon: Paul Schlyter, How to compute planetary positions,"
	+ " https://stjarnhimlen.se/comp/ppcomp.html"
)
const STARS_NOTE := (
	"Stars derived from the Hipparcos Catalogue (ESA 1997, ESA SP-1200): stars to V 6.0,"
	+ " positions rounded and reformatted. Credit: ESA. CC BY-NC 3.0 IGO,"
	+ " https://creativecommons.org/licenses/by-nc/3.0/igo/"
)
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
## The frame cap while the pause screen is open (SPEC §13 row 45). The scene behind the pause
## screen still draws, at most this many times a second.
const PAUSED_MAX_FPS := 15
## The clock's speeds, stepped in this order by time_speed, the first at the start: the game's
## seconds per real second; 0 is stopped. They move the sun, the moon and the stars only: the
## river's ripples run on the terrain shader's TIME, in real time, at every speed and when stopped
## (brief v0.4.0-08 decision 6).
const SPEEDS := [1.0, 60.0, 600.0, 0.0]
## What time_earlier and time_later move the clock by, in seconds.
const TIME_STEP_S := 900.0
## What day_earlier and day_later move the clock by, in seconds.
const DAY_STEP_S := 86400.0
## How long UI/Clock stays shown after a time key, in real seconds.
const CLOCK_SHOWN_S := 4.0
## What UI/Clock adds to its text while the clock is outside the range SkyClock checked the sky in.
const CLOCK_NOTE := " · the sky is unchecked outside 2020 to 2035 UTC"
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
	[&"time_earlier", "the time 15 minutes earlier"],
	[&"time_later", "the time 15 minutes later"],
	[&"day_earlier", "the date one day earlier"],
	[&"day_later", "the date one day later"],
	[&"time_speed", "the time's speed: 1×, 60×, 600×, stopped"],
	[&"time_now", "the time and date now, this computer's clock"],
	[&"pause", "this screen; again to resume"],
]

## The stars' image, built once per process (4096 x 2048, 32 MiB: every main-scene test would
## otherwise build it again), and whether it was tried.
static var _star_image: Image = null
static var _stars_read := false

@export var manifest_path := "res://assets/generated/manifest.json"

## The game's clock, Unix seconds UTC: the photo's moment at the start, 1x (the time keys are
## brief v0.4.0-09's). Public: the tests and a probe set it.
var time_unix := SkyClock.START_UNIX
## The index into SPEEDS, and the label's remaining real seconds.
var _speed := 0
var _clock_left := 0.0

## LV95 east, north and up as local directions, once a WorldConfig was read.
var _east := Vector3.ZERO
var _north := Vector3.ZERO
var _up := Vector3.ZERO
var _terrain: Terrain3D
## The messages of the data packs an exported build is missing, asked before the manifest is
## read; empty outside an exported build.
var _missing_packs := PackedStringArray()
## The sun's place and the rig that lights the scene; null until made.
var _site: SkySite
var _rig: SkyRig

@onready var _camera: FreeFlyCamera = $Camera
@onready var _sun: DirectionalLight3D = $Sun
@onready var _moon: DirectionalLight3D = $Moon
@onready var _environment: WorldEnvironment = $Environment
@onready var _ui: CanvasLayer = $UI
@onready var _error_panel: Control = $UI/ErrorPanel
@onready var _error_message: Label = $UI/ErrorPanel/Message
@onready var _pause_menu: Control = $UI/PauseMenu
@onready var _resume: Button = $UI/PauseMenu/Resume
@onready var _quit: Button = $UI/PauseMenu/Quit
@onready var _clock: Label = $UI/Clock


func _ready() -> void:
	_error_panel.hide()
	_pause_menu.hide()
	_clock.hide()
	_resume.pressed.connect(toggle_pause)
	_quit.pressed.connect(get_tree().quit)
	($UI/PauseMenu/Version as Label).text = "mattini %s" % _version()
	($UI/PauseMenu/Controls as Label).text = _controls_text()
	# The camera is in the tree and current by now: Terrain3D needs it on entering.
	var datasets := _load_world()
	_place_sky()
	# The Hipparcos credit is shown whenever the star table is present and read (the licence's
	# condition), not whenever stars are visible at this moment.
	var stars_drawn := _rig != null and _star_image != null
	($UI/PauseMenu/Credits as RichTextLabel).text = _credits_text(datasets, stars_drawn)


## The clock runs at SPEEDS[_speed] unless the pause screen is open; then, with the time after that
## step, the label is shown while the clock is outside the validated range and does not count down
## there; inside, it counts down in real time. It follows the clock while shown; then the sky is
## placed for it.
func _process(delta: float) -> void:
	if not _pause_menu.visible:
		time_unix += delta * SPEEDS[_speed]
	if not SkyClock.in_validated_range(time_unix):
		_clock.show()
	elif not _pause_menu.visible and _clock.visible:
		_clock_left -= delta
		if _clock_left <= 0.0:
			_clock.hide()
	if _clock.visible:
		_clock.text = clock_text()
	_place_sky()


func _exit_tree() -> void:
	Engine.max_fps = _project_max_fps()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"pause"):
		toggle_pause()
		get_viewport().set_input_as_handled()
		return
	if _pause_menu.visible:
		return
	if event.is_action_pressed(&"time_earlier", true):
		time_unix -= TIME_STEP_S
	elif event.is_action_pressed(&"time_later", true):
		time_unix += TIME_STEP_S
	elif event.is_action_pressed(&"day_earlier", true):
		time_unix -= DAY_STEP_S
	elif event.is_action_pressed(&"day_later", true):
		time_unix += DAY_STEP_S
	elif event.is_action_pressed(&"time_speed"):
		_speed = (_speed + 1) % SPEEDS.size()
	elif event.is_action_pressed(&"time_now"):
		time_unix = Time.get_unix_time_from_system()
	else:
		return
	get_viewport().set_input_as_handled()
	_clock_left = CLOCK_SHOWN_S
	_clock.text = clock_text()
	_clock.show()
	_place_sky()


## The label's text: the clock's local time and the speed, "6 Sep 2023 13:40 CEST · 1×"; outside
## the validated range (SkyClock.in_validated_range), at every speed, CLOCK_NOTE follows.
func clock_text() -> String:
	var speed: float = SPEEDS[_speed]
	var speed_text := "stopped" if speed == 0.0 else _number(speed) + "×"
	var text := "%s · %s" % [SkyClock.local_text(time_unix), speed_text]
	if not SkyClock.in_validated_range(time_unix):
		text += CLOCK_NOTE
	return text


## Opens the pause screen, or closes it when it is open. While it is open the camera
## ignores its controls, the mouse is free and the frame rate is capped at PAUSED_MAX_FPS;
## closing it gives back the project's cap (_project_max_fps).
func toggle_pause() -> void:
	var open := not _pause_menu.visible
	_pause_menu.visible = open
	_camera.input_enabled = not open
	Engine.max_fps = PAUSED_MAX_FPS if open else _project_max_fps()
	if open:
		_clock.text = clock_text()
		_clock.show()
		_resume.grab_focus()
	else:
		_clock.hide()
		_clock_left = 0.0


## The project's frame cap, application/run/max_fps, read each time this is called and never a
## literal.
static func _project_max_fps() -> int:
	return ProjectSettings.get_setting("application/run/max_fps")


## In an exported build it first asks which data packs are missing. Reads the manifest and every
## block, then builds the terrain, the trees and the buildings, and prints one startup line per
## block read. A refused manifest shows nothing; a refused block leaves the others shown (see
## the file's comment). Every refusal, and in an exported build every missing data pack, opens
## the error panel. Returns the credits' line of each dataset loaded, one per distinct line,
## sorted.
func _load_world() -> PackedStringArray:
	_missing_packs = PackedStringArray()
	if ReleaseBuild.is_exported():
		_missing_packs = DATA_PACKS.missing_pack_errors(OS.get_executable_path().get_base_dir())
	var read_world := _caught(WorldConfig.from_manifest.bind(manifest_path))
	var world: WorldConfig = read_world[0]
	if world == null:
		var every := [
			TERRAIN_WHAT,
			BUILDINGS_WHAT,
			PHOTO_WHAT,
			SURFACES_WHAT,
			TREES_WHAT,
			ROOFS_WHAT,
			SHADOWS_WHAT,
			SKY_WHAT
		]
		_show_error([[_names(every), read_world[1], MANIFEST_FIX]])
		return PackedStringArray()
	_read_directions(world)
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
	# The capture mask is read whether or not the terrain or the photo was: its refusal is its own
	# entry (without a photo the loader ignores it, without a terrain nothing takes it).
	var read_shadows := _caught(CaptureShadowGrid.from_manifest.bind(manifest_path, world))
	var shadows: CaptureShadowGrid = read_shadows[0]
	if shadows == null:
		refusals.append([SHADOWS_WHAT, read_shadows[1], SHADOWS_FIX])
	var read_sky := _caught(SkySite.from_manifest.bind(manifest_path, world))
	_site = read_sky[0]
	if _site == null:
		refusals.append([SKY_WHAT, read_sky[1], SKY_FIX])
	_create_sky()
	# One texture object for the photo, shared by the terrain and the trees: it is decoded
	# once (the village's is about 600 MiB of texture).
	if grid != null:
		_show_terrain(grid, photo, surfaces, shadows)
	if trees != null:
		_show_trees(trees, photo)
	if buildings != null:
		var node := _show_buildings(buildings, roofs)
		if grid == null:
			_start_view_over(node)
	_print_startup_lines(grid, buildings, photo, surfaces, trees, roofs, shadows)
	if not refusals.is_empty() or not _missing_packs.is_empty():
		_show_error(refusals)
	return _credited(grid, buildings, photo, surfaces, trees, roofs, shadows)


## Calls [param read] while an ErrorCatcher listens; returns [its result, the errors logged
## meanwhile].
static func _caught(read: Callable) -> Array:
	var catcher := ErrorCatcher.new()
	OS.add_logger(catcher)
	var result: Variant = read.call()
	OS.remove_logger(catcher)
	return [result, catcher.messages()]


## Builds the terrain (in the photo look when there is a photo, with the surfaces drawn on it
## when there are surfaces and the photo's baked shadows lifted when there is a capture mask) and
## starts the view over it.
func _show_terrain(
	grid: TerrainGrid, photo: PhotoGrid, surfaces: SurfaceGrid, shadows: CaptureShadowGrid
) -> void:
	_terrain = TerrainLoader.create(grid, self, photo, surfaces, shadows)
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
## buildings, photo, surfaces, trees, roofs, shadows: an exported build is checked by them, headless
## (tools/export.sh step 6; briefs M1-06, M2-05, M3-14). The numbers are written as _number
## writes them.
func _print_startup_lines(
	grid: TerrainGrid,
	buildings: BuildingChunks,
	photo: PhotoGrid,
	surfaces: SurfaceGrid,
	trees: TreeChunks,
	roofs: BuildingRoofs,
	shadows: CaptureShadowGrid
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
	if shadows != null:
		var text := "mattini %s: shadows %s loaded, %d x %d cells at %s m"
		print(text % [v, shadows.area, shadows.columns, shadows.rows, _number(shadows.cell_m)])


## The credits' line of each dataset a block that was read comes from, once each, sorted:
## the photo and the roof colours share one, and the capture mask's is the trees' when their
## attribution agrees.
func _credited(
	grid: TerrainGrid,
	buildings: BuildingChunks,
	photo: PhotoGrid,
	surfaces: SurfaceGrid,
	trees: TreeChunks,
	roofs: BuildingRoofs,
	shadows: CaptureShadowGrid
) -> PackedStringArray:
	var lines := {}
	if grid != null:
		var source := _terrain_source()
		lines[_dataset_line(source.get("dataset"), source.get("edition"), grid.attribution)] = true
	for block: Variant in [buildings, photo, surfaces, trees, roofs]:
		if block != null:
			lines[_dataset_line(block.dataset, block.edition, block.attribution)] = true
	if shadows != null:
		# The editions as the trees' line writes them: the first and the last, or the one alone.
		var editions := shadows.editions
		var edition := editions[0]
		if editions.size() > 1 and editions[editions.size() - 1] != edition:
			edition += "-" + editions[editions.size() - 1]
		lines[_dataset_line(shadows.dataset, edition, shadows.attribution)] = true
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


## The local direction of a grid azimuth [param azimuth_deg] (clockwise from LV95 north) and an
## elevation [param elevation_deg], through the world config's east, north and up.
func _direction(azimuth_deg: float, elevation_deg: float) -> Vector3:
	var elevation := deg_to_rad(elevation_deg)
	return _bearing(azimuth_deg) * cos(elevation) + _up * sin(elevation)


## Makes the rig, its frame at TRUE north: the rig uses its frame's north only for the stars'
## pole, which stands 0.23 degrees off true north in the grid frame. True north lies at grid
## azimuth true_to_grid_deg. Without a sky block: grid north and latitude 0, unused while the
## placeholder sun stands by day (the rig's stars strength is 0 then).
func _create_sky() -> void:
	var true_to_grid := _site.true_to_grid_deg if _site != null else 0.0
	var latitude := _site.latitude_deg if _site != null else 0.0
	var frame := Basis(_bearing(true_to_grid + 90.0), _bearing(true_to_grid), _up)
	_rig = SkyRig.create(_sun, _moon, _environment.environment, frame, latitude, _stars())


## The stars' image, built once per process when the table exists, else null (4096 x 2048,
## 32 MiB: every main-scene test would otherwise build it again). star_image is called by name
## on the loaded script so that this file parses without SkyRig's star code.
static func _stars() -> Image:
	if not _stars_read:
		_stars_read = true
		if FileAccess.file_exists(STARS_TABLE):
			_star_image = load(SKY_RIG_SCRIPT).star_image(STARS_TABLE)
	return _star_image


## Places the sun, the moon and the stars for the clock's time at the sky block's site (the
## true azimuth plus true_to_grid_deg is the grid azimuth; moon.z is the illuminated fraction;
## the sidereal angle turns the stars). Without a sky block, the placeholder sun, still, and the
## moon below the horizon. Nothing without a rig (no world config).
func _place_sky() -> void:
	if _rig == null:
		return
	if _site == null:
		var still := _direction(FALLBACK_SUN_AZIMUTH_GRID_DEG, FALLBACK_SUN_ELEVATION_DEG)
		_rig.apply(still, -still, 0.0, 0.0)
		return
	var sun := SkyClock.sun(time_unix, _site.latitude_deg, _site.longitude_deg)
	var moon := SkyClock.moon(time_unix, _site.latitude_deg, _site.longitude_deg)
	_rig.apply(
		_direction(sun.x + _site.true_to_grid_deg, sun.y),
		_direction(moon.x + _site.true_to_grid_deg, moon.y),
		moon.z,
		SkyClock.sidereal_deg(time_unix, _site.longitude_deg)
	)


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


## Opens the error panel with [method error_text]; an exported build (ReleaseBuild.is_exported())
## gets the missing data packs after the first line and the release folder as the fix, a source
## checkout the commands.
func _show_error(refusals: Array) -> void:
	_error_message.text = error_text(
		refusals, manifest_path, ReleaseBuild.is_exported(), _missing_packs
	)
	_error_panel.show()


## The error panel's text. Its first line names what cannot be shown; then, per refusal, what
## its reader logged and how to fix it. [param refusals] holds one [what, the messages logged,
## the commands] per refusal, in the order of the blocks (the terrain's first); [param path]
## is the manifest. [param exported]: a player has no pipeline (brief M3-14), so every fix
## line, the manifest's included, is the release folder and no command is named. [param packs]:
## the missing data packs' messages (DataPacks.missing_pack_errors, an exported build's), shown
## after the first line and an empty line, before the refusals; with no refusal the first line is
## "mattini cannot find every data pack." and the fix is the release folder (brief v0.3.1-05,
## M4-10 decision 5).
static func error_text(
	refusals: Array, path: String, exported: bool, packs := PackedStringArray()
) -> String:
	var what := PackedStringArray()
	for refusal: Array in refusals:
		what.append(refusal[0])
	var lines := PackedStringArray()
	if refusals.is_empty():
		lines.append("mattini cannot find every data pack.")
	else:
		lines.append("mattini cannot show %s." % _names(what))
	if not packs.is_empty():
		lines.append("")
		lines.append_array(packs)
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
	if refusals.is_empty():
		lines.append("")
		lines.append("To fix it, " + EXPORTED_FIX)
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
## the trees and the streams: they describe the build, so they are always listed), then "Sky"
## (the sun's and the moon's formulas, and the Hipparcos credit only when [param stars] is true:
## the stars were drawn, so the table res://sky/stars.csv exists), then the software's licences.
func _credits_text(datasets: PackedStringArray, stars: bool) -> String:
	var lines := PackedStringArray(["Credits", "", "Data"])
	if datasets.is_empty():
		lines.append("No generated data is loaded, so no dataset is shown.")
	else:
		lines.append_array(datasets)
	lines.append_array(["", "Textures", _licence(TEXTURES_LICENSE).strip_edges()])
	lines.append_array(
		["", "Placeholders", BuildingLoader.WALLS_NOTE, TreeLoader.TREES_NOTE, STREAMS_NOTE]
	)
	lines.append_array(["", "Sky", SUN_NOTE, MOON_NOTE])
	if stars:
		lines.append(STARS_NOTE)
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
