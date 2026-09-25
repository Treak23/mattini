extends SceneTree
## Software screenshots of a manifest's terrain (docs/SPEC.md §12; brief M1-04): evidence of
## what is drawn and where, never a gate, and not the Forward+ look. Run by tools/shot.sh:
##
##   godot --path game --rendering-method gl_compatibility --resolution 1280x720 \
##     -s res://tools/shot.gd -- <manifest> <out_dir> "<name>,E,N,above_m,bearing,pitch;..."
##
## Each view is an LV95 point (converted through WorldConfig), the metres above the terrain
## there, the bearing in degrees clockwise from north and the pitch in degrees below the
## horizon. The scene: the terrain with the clay look (TerrainLoader), one fixed sun
## (elevation 35°, azimuth 150°, shadows) and a procedural sky with neutral ground colours.
## Each view is saved as <out_dir>/<name>.jpg, 1280 × 720, quality 0.85. A view over no
## terrain, a bad argument or a refused manifest ends the run with exit 1 and a message.

const SIZE := Vector2i(1280, 720)
const JPG_QUALITY := 0.85
const SUN_ELEVATION_DEG := 35.0
const SUN_AZIMUTH_DEG := 150.0
## Frames rendered before each capture, so Terrain3D's mesh follows the camera.
const SETTLE_FRAMES := 10


func _initialize() -> void:
	# The root enters the tree only after _initialize returns; Terrain3D needs the tree.
	await process_frame
	var args := OS.get_cmdline_user_args()
	if args.size() != 3:
		_fail('usage: -- <manifest> <out_dir> "<name>,E,N,above_m,bearing,pitch;..."')
		return
	var views := _parse_views(args[2])
	if views.is_empty():
		_fail("no valid view in %s" % args[2])
		return
	var world := WorldConfig.from_manifest(args[0])
	var grid: TerrainGrid = null
	if world != null:
		grid = TerrainGrid.from_manifest(args[0], world)
	if grid == null:
		_fail("the manifest %s was refused (see the error above)" % args[0])
		return
	var scene := _build_scene()
	var camera: Camera3D = scene.get_node("Camera")
	var terrain := TerrainLoader.create(grid, scene)
	for view: Dictionary in views:
		var local := world.to_local(view["e"], view["n"], world.height_offset)
		var ground := terrain.data.get_height(Vector3(local.x, 0.0, local.z))
		if is_nan(ground):
			_fail("view %s: no terrain under E %s N %s" % [view["name"], view["e"], view["n"]])
			return
		camera.position = Vector3(local.x, ground + view["above"], local.z)
		camera.basis = Basis.from_euler(
			Vector3(deg_to_rad(-view["pitch"]), deg_to_rad(-view["bearing"]), 0.0)
		)
		for i in SETTLE_FRAMES:
			await process_frame
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		if image.get_size() != SIZE:
			image.resize(SIZE.x, SIZE.y, Image.INTERPOLATE_LANCZOS)
		var path: String = args[1].path_join("%s.jpg" % view["name"])
		var error := image.save_jpg(path, JPG_QUALITY)
		if error != OK:
			_fail("cannot write %s (%s)" % [path, error_string(error)])
			return
		print("shot: %s" % path)
	quit(0)


## Parses "name,E,N,above_m,bearing,pitch;..."; returns [] (after printing why) on any error.
func _parse_views(text: String) -> Array[Dictionary]:
	var views: Array[Dictionary] = []
	for spec in text.split(";", false):
		var parts := spec.strip_edges().split(",")
		var valid := parts.size() == 6 and parts[0].is_valid_filename()
		for i in range(1, parts.size()):
			valid = valid and parts[i].strip_edges().is_valid_float()
		if not valid:
			printerr("shot: bad view %s (want name,E,N,above_m,bearing_deg,pitch_deg)" % spec)
			return []
		(
			views
			. append(
				{
					"name": parts[0],
					"e": parts[1].to_float(),
					"n": parts[2].to_float(),
					"above": parts[3].to_float(),
					"bearing": parts[4].to_float(),
					"pitch": parts[5].to_float(),
				}
			)
		)
	return views


## The sun, the sky and the camera under a new root; the camera is current before the
## terrain enters the tree, which Terrain3D needs.
func _build_scene() -> Node3D:
	var scene := Node3D.new()
	scene.name = "Shot"
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.ground_bottom_color = Color(0.42, 0.42, 0.42)
	sky_material.ground_horizon_color = Color(0.62, 0.62, 0.62)
	var sky := Sky.new()
	sky.sky_material = sky_material
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	scene.add_child(world_environment)

	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	var elevation := deg_to_rad(SUN_ELEVATION_DEG)
	var azimuth := deg_to_rad(SUN_AZIMUTH_DEG)
	# Towards the sun, in Godot's axes (x east, y up, z south).
	var to_sun := Vector3(
		sin(azimuth) * cos(elevation), sin(elevation), -cos(azimuth) * cos(elevation)
	)
	sun.basis = Basis.looking_at(-to_sun, Vector3.UP)
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 3000.0
	scene.add_child(sun)

	var camera := Camera3D.new()
	camera.name = "Camera"
	camera.near = 0.5
	camera.far = 20000.0
	scene.add_child(camera)
	root.add_child(scene)
	camera.make_current()
	return scene


func _fail(message: String) -> void:
	printerr("shot: %s" % message)
	quit(1)
