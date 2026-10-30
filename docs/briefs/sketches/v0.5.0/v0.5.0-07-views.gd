extends SceneTree
## Pin author's evidence script (brief v0.5.0-07), never a gate and never committed under game/:
## renders main.tscn's real village from one view at given local times of the start date
## (2023-09-06, CEST), each with the haze as SkyRig.create set it and with the fog switched off,
## MSAA off (brain.md H29), and prints per frame the mean sRGB of the whole frame and, in the box
## BOX (the start view's left forest band, as the scout measured 0.4.0's E1), the mean sRGB and the
## share of pixels below sRGB 20 on every channel ("near-black").
##   -- <out_dir> <prefix> <view> <HH:MM,HH:MM,...>
## view: "start", or "above_m,bearing_deg,pitch_deg": over the start view's point, above_m over
## the ground there, facing the grid bearing, pitched that many degrees down.

const SETTLE := 40
const BOX := Rect2i(0, 100, 400, 130)
const START_LOCAL_S := 13 * 3600 + 40 * 60


func _initialize() -> void:
	await process_frame
	var args := OS.get_cmdline_user_args()
	var out: String = args[0]
	var prefix: String = args[1]
	root.msaa_3d = Viewport.MSAA_DISABLED
	var main: Node3D = load("res://main.tscn").instantiate()
	root.add_child(main)
	main.set_process(false)
	var camera: FreeFlyCamera = main.get_node("Camera")
	var terrain: Terrain3D = main.get_node("Terrain")
	if args[2] != "start":
		var p := args[2].split(",")
		var at := camera.position
		var ground := terrain.data.get_height(Vector3(at.x, 0.0, at.z))
		var facing: Vector3 = main._bearing(p[1].to_float())
		var yaw := atan2(-facing.x, -facing.z)
		camera.set_view(
			Vector3(at.x, ground + p[0].to_float(), at.z), yaw, -deg_to_rad(p[2].to_float())
		)
	print("views: camera %s rotation %s" % [camera.position, camera.rotation])
	var environment: Environment = main.get_node("Environment").environment
	print(
		(
			"views: fog %s mode %d density %s aerial %s sky_affect %s"
			% [
				environment.fog_enabled,
				environment.fog_mode,
				str(environment.fog_density),
				environment.fog_aerial_perspective,
				environment.fog_sky_affect
			]
		)
	)
	for hhmm in args[3].split(","):
		var hm := hhmm.split(":")
		var local_s := hm[0].to_int() * 3600 + hm[1].to_int() * 60
		main.time_unix = SkyClock.START_UNIX + float(local_s - START_LOCAL_S)
		main._place_sky()
		for haze in [true, false]:
			environment.fog_enabled = haze
			for i in SETTLE:
				await process_frame
			await RenderingServer.frame_post_draw
			var image := root.get_texture().get_image()
			var name := "%s-%s-%s" % [prefix, hhmm.replace(":", ""), "haze" if haze else "clear"]
			image.save_png(out.path_join(name + ".png"))
			print("views: %s %s" % [name, _stats(image)])
		environment.fog_enabled = true
	quit(0)


func _stats(image: Image) -> String:
	var whole := 0.0
	var n := 0
	for y in range(0, image.get_height(), 2):
		for x in range(0, image.get_width(), 2):
			var c := image.get_pixel(x, y)
			whole += (c.r + c.g + c.b) / 3.0
			n += 1
	var box := 0.0
	var dark := 0
	var m := 0
	for y in range(BOX.position.y, BOX.end.y):
		for x in range(BOX.position.x, BOX.end.x):
			var c := image.get_pixel(x, y)
			box += (c.r + c.g + c.b) / 3.0
			if c.r8 < 20 and c.g8 < 20 and c.b8 < 20:
				dark += 1
			m += 1
	return (
		"mean sRGB %.1f; box mean %.1f, near-black %.1f %%"
		% [whole / n * 255.0, box / m * 255.0, 100.0 * dark / m]
	)
