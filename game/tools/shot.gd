extends SceneTree
## Software screenshots of the main scene (docs/SPEC.md §12; briefs M1-04, M1-05): evidence
## of what is drawn and where, never a gate, and not the Forward+ look. Run by tools/shot.sh:
##
##   godot --path game --rendering-method gl_compatibility --resolution 1280x720 \
##     -s res://tools/shot.gd -- <manifest> <out_dir> "<view>;<view>;..."
##
## The scene is main.tscn reading <manifest>: its terrain, sun, sky, camera, error panel and
## pause screen. Each view is one of:
##   name,E,N,above_m,bearing,pitch  the camera at an LV95 point (converted through
##       WorldConfig), above_m over the terrain there, facing the bearing in degrees
##       clockwise from north, pitched that many degrees below the horizon;
##   name                            the camera where it is: the scene's own start view
##       when it comes first;
##   name,pause                      the same with the pause screen open.
## Views run in order. Each is saved as <out_dir>/<name>.jpg, 1280 × 720, quality 0.85. A
## view over no terrain or a bad argument ends the run with exit 1 and a message; a refused
## manifest does not: the scene shows its error panel, which is then what is captured.

const SIZE := Vector2i(1280, 720)
const JPG_QUALITY := 0.85
## Frames rendered before each capture, so Terrain3D's mesh follows the camera.
const SETTLE_FRAMES := 10


func _initialize() -> void:
	# The root enters the tree only after _initialize returns; Terrain3D needs the tree.
	await process_frame
	var args := OS.get_cmdline_user_args()
	if args.size() != 3:
		_fail('usage: -- <manifest> <out_dir> "<view>;<view>;..."')
		return
	var views := _parse_views(args[2])
	if views.is_empty():
		_fail("no valid view in %s" % args[2])
		return
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = args[0]
	root.add_child(main)
	var camera: FreeFlyCamera = main.get_node("Camera")
	for view: Dictionary in views:
		if view.has("e") and not _place(camera, main.get_node_or_null("Terrain"), args[0], view):
			return
		if view["pause"]:
			main.toggle_pause()
		for i in SETTLE_FRAMES:
			await process_frame
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		if view["pause"]:
			main.toggle_pause()
		if image.get_size() != SIZE:
			image.resize(SIZE.x, SIZE.y, Image.INTERPOLATE_LANCZOS)
		var path: String = args[1].path_join("%s.jpg" % view["name"])
		var error := image.save_jpg(path, JPG_QUALITY)
		if error != OK:
			_fail("cannot write %s (%s)" % [path, error_string(error)])
			return
		print("shot: %s" % path)
	quit(0)


## Puts the camera over the view's LV95 point; returns false (after failing the run) when
## there is no terrain there.
func _place(camera: FreeFlyCamera, terrain: Terrain3D, manifest: String, view: Dictionary) -> bool:
	var world: WorldConfig = null
	if terrain != null:
		world = WorldConfig.from_manifest(manifest)
	if world == null:
		_fail("view %s: the scene has no terrain (see its error panel)" % view["name"])
		return false
	var e: float = view["e"]
	var n: float = view["n"]
	var h := world.height_offset
	var local := world.to_local(e, n, h)
	var ground := terrain.data.get_height(Vector3(local.x, 0.0, local.z))
	if is_nan(ground):
		_fail("view %s: no terrain under E %s N %s" % [view["name"], e, n])
		return false
	# The bearing's direction through WorldConfig: north and east are measured, not assumed.
	var bearing := deg_to_rad(view["bearing"])
	var facing := (
		(world.to_local(e + 1.0, n, h) - local) * sin(bearing)
		+ (world.to_local(e, n + 1.0, h) - local) * cos(bearing)
	)
	var at := Vector3(local.x, ground + view["above"], local.z)
	camera.set_view(at, atan2(-facing.x, -facing.z), -deg_to_rad(view["pitch"]))
	return true


## Parses the views; returns [] (after printing why) on any error.
func _parse_views(text: String) -> Array[Dictionary]:
	var views: Array[Dictionary] = []
	for spec in text.split(";", false):
		var parts := spec.strip_edges().split(",")
		for i in parts.size():
			parts[i] = parts[i].strip_edges()
		var valid := parts[0].is_valid_filename()
		if parts.size() == 6:
			for i in range(1, parts.size()):
				valid = valid and parts[i].is_valid_float()
		elif parts.size() == 2:
			valid = valid and parts[1] == "pause"
		else:
			valid = valid and parts.size() == 1
		if not valid:
			printerr("shot: bad view %s (want name,E,N,above_m,bearing_deg,pitch_deg" % spec)
			printerr("shot: or name, or name,pause)")
			return []
		var view := {"name": parts[0], "pause": parts.size() == 2}
		if parts.size() == 6:
			view["e"] = parts[1].to_float()
			view["n"] = parts[2].to_float()
			view["above"] = parts[3].to_float()
			view["bearing"] = parts[4].to_float()
			view["pitch"] = parts[5].to_float()
		views.append(view)
	return views


func _fail(message: String) -> void:
	printerr("shot: %s" % message)
	quit(1)
