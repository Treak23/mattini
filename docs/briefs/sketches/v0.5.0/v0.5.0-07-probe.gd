extends SceneTree
# Pin author's probe (brief v0.5.0-07): what share of a surface Godot's exponential fog covers at a
# distance, as the engine draws it. A black unshaded wall faces the camera at each distance D; the
# fog's colour is white (aerial perspective 0), the background black, the tone map linear at
# exposure 1, MSAA off. The centre pixel's linear value is the fog's share at D. Usage:
# godot --path game ... -s <this> -- <density> <D1> <D2> ...


func _srgb_to_linear(c: float) -> float:
	return c / 12.92 if c <= 0.04045 else pow((c + 0.055) / 1.055, 2.4)


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var density := float(args[0])
	var distances: Array[float] = []
	for i in range(1, args.size()):
		distances.append(float(args[i]))
	root.msaa_3d = Viewport.MSAA_DISABLED
	var scene := Node3D.new()
	root.add_child(scene)
	var camera := Camera3D.new()
	camera.far = 20000.0
	scene.add_child(camera)
	camera.current = true
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color.BLACK
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	environment.fog_enabled = true
	environment.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	environment.fog_density = density
	environment.fog_light_color = Color.WHITE
	environment.fog_light_energy = 1.0
	environment.fog_aerial_perspective = 0.0
	environment.fog_sky_affect = 0.0
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	scene.add_child(world_environment)
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = Color.BLACK
	var wall := MeshInstance3D.new()
	var quad := QuadMesh.new()
	wall.mesh = quad
	wall.material_override = material
	scene.add_child(wall)
	for d in distances:
		quad.size = Vector2(d, d)
		wall.position = Vector3(0.0, 0.0, -d)
		for i in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		var c := image.get_pixel(image.get_width() / 2, image.get_height() / 2)
		var corner := image.get_pixel(2, 2)
		var lin := _srgb_to_linear(c.r)
		var share := 1.0 - exp(-density * d)
		var text := "PROBE fog density %s at %.0f m: centre sRGB %.4f (%d), linear %.5f, "
		text += "expected 1 - exp(-d D) %.5f; corner %.4f; format %d"
		var values := [str(density), d, c.r, roundi(c.r * 255.0), lin, share, corner.r]
		print(text % (values + [image.get_format()]))
	quit(0)
