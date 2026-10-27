extends SceneTree
## The software Forward+ probe of brief v0.4.0-05 (the sky rig and the physical sky with the
## valley's ground). Design's measuring tool, not a test, kept with the brief's sketches: run it
## from the repository's root with its absolute path; never copy it under game/:
##
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json XDG_DATA_HOME=<yours> \
##   xvfb-run -a timeout 300 godot --path game --rendering-driver vulkan \
##   --rendering-method forward_plus --audio-driver Dummy --resolution 512x512 \
##   -s "$PWD/docs/briefs/sketches/v0.4.0/v0.4.0-05-probe.gd" -- <mode> [<argument> ...]
##
## Each mode prints lines beginning "PROBE <mode>" and exits 0; it exits 1 when the mode is
## unknown or the renderer is not Forward+. MSAA is off in every view (the project's 4x is not
## what is measured) and the window's pixels are the view's (no stretch). The owner's frame
## throughout: east +x, north -z, up +y; azimuths are grid azimuths. Linear values are read from
## the window's sRGB 8-bit pixels through the sRGB transfer function; luminance is Rec. 709.
##
## Modes:
## - calib [default|valley|r,g,b]: brief M4-05's calibration, its recipe exactly: a 4000 m plane
##   of albedo Color8(128, 128, 128), roughness 0.95; the rig with the sun at grid azimuth 185.13,
##   elevation 50.1, the moon at 295.96 / 9.16, fraction 0.553, sidereal 168.06; a camera 100 m up
##   looking straight down, fov 30; after 30 frames the mean linear luminance of the centre 64 x 64
##   pixels over the albedo's linear 0.2159 (and "float", the same from an HDR twin of the view,
##   not stepped by 8 bits). "calib_start": the same at the start's sun and moon.
##   The argument sets ground_color: Godot's default, the rig's GROUND_COLOUR (no argument or
##   "valley"), or a source_color value "r,g,b".
## - flat [ground]: the radiance of flat ground per unit albedo (E / pi): a white Lambert plane
##   without specular, a linear tone map at exposure 0.5, the start's sun and moon; "PROBE flat
##   float" from an HDR twin of the view (the line decision 6 uses).
## - lower [white|ground]: the sky's radiance below the horizon, from five faces of a cube (fov 90,
##   the window square), no geometry, a linear tone map at exposure 2.0: its cosine-weighted mean
##   over the lower hemisphere (the radiance a face looking straight down sees on average), its
##   solid-angle mean, and the ring at the horizon. With "white", ground_color multiplies by 1: the
##   horizon's light carried below the horizon, the "horizon's radiance" of decision 6.
## - wall <light> [ground]: the check of SPEC §13 row 52: flat ground of albedo sRGB 128
##   (roughness 0.95), a 30 x 20 x 2 m wall whose north face stands in its own shade, and a cone
##   20 m high, 2.5 m in radius (a tree, 18 m west and 20 m north of the wall's centre), all of
##   that material; the camera 60 m north of the wall, 6 m up, looking south, fov 60. <light>:
##   "rig" (the rig at the start's sun and moon), "rig_nomoon" (the same with the moon light
##   hidden: the start's moon, 9 degrees up in the west-north-west, lights a north face by day),
##   "m3" (0.3.1's environment: main.tscn's procedural sky, ambient from the sky at 0.25, Filmic at
##   exposure 0.54, a white sun of energy 1 at M3's 183 / 52), "m3start" (0.3.1's environment
##   with its sun at the start's 184.65 / 50.34). Prints the displayed linear luminance of the
##   wall's shaded face, of the cone's shaded side and of lit flat ground, and their ratios:
##   "PROBE wall:" from the window's 8-bit pixels (the face's pixels share one code, steps about
##   4 % apart), "PROBE wall float:" from the same view rendered into a SubViewport with HDR 2D
##   (the tone-mapped values in half floats); the float line decides. PROBE_SHOT=<file.jpg> in
##   the environment saves the window's view.
## - twilight: brief M4-05's twilight probe (decision 4b): the sun at -3 (azimuth 270), a camera
##   10 m up, fov 60, looking 15 degrees up towards the sun (270) and away from it (90); the sky's
##   sRGB 5, 15 and 30 degrees above the horizon; the same at +3, -0.5, -1.5 and -9. PROBE_SHOT
##   saves the view towards the sun at -3.
## - night: flat ground of albedo sRGB 128 at sun -30, moon -20: its luminance over the albedo's.
## - disk: the sun at +10 (azimuth 270), a view 15 degrees up, fov 60: the peak sRGB at the sun
##   and the sky 20 px aside, with sun_disk_deg 0.53 and 0.
## - edge [ground]: where the sky's ground shows: a flat 2 x 3 km stand-in of the area in the
##   photo's mean colour (albedo linear 0.1483, 0.1666, 0.1199, roughness 0.95), the rig at the
##   start, a camera 600 m up, 2 km south of the stand-in's north edge, looking north 20 degrees
##   down, fov 60 (the edge 16.7 degrees down); the displayed linear luminance of the stand-in 25
##   degrees down and of the sky's ground beyond the edge, 10 and 3 degrees down. PROBE_SHOT
##   saves the view.
## - shadow [angular]: brief M4-05's box (20 x 200 x 20 m) at its calibration sun, a camera 100 m
##   up looking straight down, fov 10, over the shadow's east edge where it is cast from 144 m up:
##   the shadow's interior and the lit ground (the sRGB-coded luminance of the pixels, 0 to 1), and
##   the edge's 10 % to 90 % width; [angular] the sun light's angular distance (default 0, the
##   rig's; 0.5 is the setting decision 4c rejected).

const ALBEDO_128 := 0.2158605
const LAT := 46.0196233
## The start (2023-09-06 11:40 UTC) at the village's site of config/sky.json, from SkyClock
## (brief v0.4.0-04's throwaway): the sun at true 184.8759 / 50.3355, the moon at true 295.9760 /
## 9.1514 with fraction 0.5458, LMST 168.0596; grid = true - 0.2258.
const START_SUN := Vector2(184.6501, 50.3355)
const START_MOON := Vector2(295.7502, 9.1514)
const START_FRACTION := 0.5458
const START_SIDEREAL := 168.0596
## Brief M4-05's calibration recipe.
const CALIB_SUN := Vector2(185.13, 50.1)
const CALIB_MOON := Vector2(295.96, 9.16)
const CALIB_FRACTION := 0.553
const CALIB_SIDEREAL := 168.06
## M3's sun (main.gd, 0.3.1).
const M3_SUN := Vector2(183.0, 52.0)
## The linear tone map's exposure for flat ground (white, about 0.8 per unit exposure: 0.40) and
## for the sky below the horizon (about 0.1 with a white ground, 0.3 with the valley's: 0.2 to
## 0.6), so nothing clips (each mode prints its brightest value) and 8 bits resolve both.
const FLAT_EXPOSURE := 0.5
const LOWER_EXPOSURE := 2.0

var _frame := Basis(Vector3(1, 0, 0), Vector3(0, 0, -1), Vector3(0, 1, 0))
var _environment: Environment
var _sun: DirectionalLight3D
var _moon: DirectionalLight3D
var _rig: SkyRig
var _camera: Camera3D


func _initialize() -> void:
	await process_frame
	var args := OS.get_cmdline_user_args()
	var mode: String = args[0] if args.size() > 0 else ""
	var arg: String = args[1] if args.size() > 1 else ""
	var arg2: String = args[2] if args.size() > 2 else ""
	var method := RenderingServer.get_current_rendering_method()
	print("PROBE renderer: %s, %s" % [method, RenderingServer.get_video_adapter_name()])
	if method != "forward_plus":
		print("PROBE: not Forward+; run it with --rendering-method forward_plus")
		quit(1)
		return
	root.msaa_3d = Viewport.MSAA_DISABLED
	# Pixels are the window's: no stretch of the project's 1280 x 720 base size.
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	var ok := true
	match mode:
		"calib":
			await _calib(CALIB_SUN, CALIB_MOON, CALIB_FRACTION, CALIB_SIDEREAL, arg, "calib")
		"calib_start":
			await _calib(START_SUN, START_MOON, START_FRACTION, START_SIDEREAL, arg, "calib_start")
		"flat":
			await _flat(arg)
		"lower":
			await _lower(arg)
		"wall":
			await _wall(arg, arg2)
		"twilight":
			await _twilight()
		"night":
			await _night()
		"disk":
			await _disk()
		"shadow":
			await _shadow(float(arg) if arg != "" else 0.0)
		"edge":
			await _edge(arg)
		_:
			print("PROBE: unknown mode '%s'" % mode)
			ok = false
	quit(0 if ok else 1)


## The unit vector towards grid azimuth [param az] and elevation [param el], in degrees.
func _towards(az: float, el: float) -> Vector3:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	return (_frame.x * sin(a) + _frame.y * cos(a)) * cos(e) + _frame.z * sin(e)


## The ground colour an argument names: Godot's default, the rig's constant, or "r,g,b" (a
## source_color value, as the uniform takes it), or white.
func _ground(arg: String) -> Variant:
	match arg:
		"", "valley":
			return SkyRig.GROUND_COLOUR
		"default":
			return Color(0.1, 0.07, 0.034)
		"white":
			return Color(1.0, 1.0, 1.0)
	var parts := arg.split(",")
	return Color(float(parts[0]), float(parts[1]), float(parts[2]))


func _lights() -> void:
	var environment_node := WorldEnvironment.new()
	_environment = Environment.new()
	environment_node.environment = _environment
	root.add_child(environment_node)
	_sun = DirectionalLight3D.new()
	_moon = DirectionalLight3D.new()
	root.add_child(_sun)
	root.add_child(_moon)
	_camera = Camera3D.new()
	_camera.current = true
	_camera.far = 6000.0
	root.add_child(_camera)


func _rig_at(
	sun: Vector2, moon: Vector2, fraction: float, sidereal: float, ground: Variant
) -> void:
	_lights()
	_rig = SkyRig.create(_sun, _moon, _environment, _frame, LAT)
	if ground != null:
		_rig.sky_material.set_shader_parameter("ground_color", ground)
	_rig.apply(_towards(sun.x, sun.y), _towards(moon.x, moon.y), fraction, sidereal)


## 0.3.1's environment (main.tscn) with its sun at [param sun].
func _m3_at(sun: Vector2) -> void:
	_lights()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.ground_bottom_color = Color(0.4, 0.43, 0.47, 1)
	sky_material.ground_horizon_color = Color(0.6, 0.63, 0.67, 1)
	var sky := Sky.new()
	sky.sky_material = sky_material
	_environment.background_mode = Environment.BG_SKY
	_environment.sky = sky
	_environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	_environment.ambient_light_sky_contribution = 0.25
	_environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	_environment.tonemap_exposure = 0.54
	_sun.shadow_enabled = true
	_sun.directional_shadow_max_distance = 3000.0
	_sun.basis = Basis.looking_at(-_towards(sun.x, sun.y), Vector3.UP)
	_moon.visible = false


func _plane(material: Material) -> void:
	var plane := MeshInstance3D.new()
	var mesh := PlaneMesh.new()
	mesh.size = Vector2(4000.0, 4000.0)
	plane.mesh = mesh
	plane.material_override = material
	root.add_child(plane)


func _grey() -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = Color8(128, 128, 128)
	material.roughness = 0.95
	return material


func _look_down(height: float, fov: float) -> void:
	_camera.fov = fov
	_camera.position = Vector3(0.0, height, 0.0)
	_camera.basis = Basis.looking_at(Vector3.DOWN, Vector3(0.0, 0.0, -1.0))


## A twin of the window's view in a SubViewport with HDR 2D: its texture holds the tone-mapped
## values linear in half floats, so a value is not read through 8 bits (a uniform plane's pixels
## share one sRGB code, steps about 1 % apart at 128 and 4 % at 25).
func _hdr_twin() -> SubViewport:
	var hdr := SubViewport.new()
	hdr.size = root.size
	hdr.use_hdr_2d = true
	hdr.msaa_3d = Viewport.MSAA_DISABLED
	hdr.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	var hdr_camera := Camera3D.new()
	hdr_camera.fov = _camera.fov
	hdr_camera.far = _camera.far
	hdr_camera.transform = _camera.transform
	hdr.add_child(hdr_camera)
	root.add_child(hdr)
	hdr_camera.current = true
	return hdr


func _capture(frames: int = 30) -> Image:
	for i in frames:
		await process_frame
	await RenderingServer.frame_post_draw
	return root.get_texture().get_image()


## The mean linear colour of [param image] over [param rect].
func _mean(image: Image, rect: Rect2i) -> Vector3:
	var sum := Vector3.ZERO
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			var c := image.get_pixel(x, y).srgb_to_linear()
			sum += Vector3(c.r, c.g, c.b)
	return sum / float(rect.get_area())


## The mean of [param image]'s values over [param rect], taken as they are (linear already).
func _mean_float(image: Image, rect: Rect2i) -> Vector3:
	var sum := Vector3.ZERO
	for y in range(rect.position.y, rect.end.y):
		for x in range(rect.position.x, rect.end.x):
			var c := image.get_pixel(x, y)
			sum += Vector3(c.r, c.g, c.b)
	return sum / float(rect.get_area())


func _lum(c: Vector3) -> float:
	return 0.2126 * c.x + 0.7152 * c.y + 0.0722 * c.z


func _centre(image: Image, half: int) -> Rect2i:
	var size := image.get_size()
	return Rect2i(size.x / 2 - half, size.y / 2 - half, 2 * half, 2 * half)


func _calib(
	sun: Vector2, moon: Vector2, fraction: float, sid: float, arg: String, name: String
) -> void:
	_rig_at(sun, moon, fraction, sid, _ground(arg))
	_plane(_grey())
	_look_down(100.0, 30.0)
	var hdr := _hdr_twin()
	var image := await _capture(30)
	var mean := _mean(image, _centre(image, 32))
	var hdr_image := hdr.get_texture().get_image()
	var float_mean := _mean_float(hdr_image, _centre(hdr_image, 32))
	print(
		(
			"PROBE %s: ground %s exposure %.4f luminance %.5f over albedo %.4f (float %.5f)"
			% [
				name,
				_ground(arg),
				_environment.tonemap_exposure,
				_lum(mean),
				_lum(mean) / ALBEDO_128,
				_lum(float_mean) / ALBEDO_128,
			]
		)
	)


func _flat(arg: String) -> void:
	_rig_at(START_SUN, START_MOON, START_FRACTION, START_SIDEREAL, _ground(arg))
	_environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	_environment.tonemap_exposure = FLAT_EXPOSURE
	var white := StandardMaterial3D.new()
	white.albedo_color = Color(1.0, 1.0, 1.0)
	white.roughness = 1.0
	white.metallic_specular = 0.0
	white.diffuse_mode = BaseMaterial3D.DIFFUSE_LAMBERT
	_plane(white)
	_look_down(100.0, 30.0)
	var hdr := _hdr_twin()
	var image := await _capture(30)
	var radiance := _mean(image, _centre(image, 32)) / FLAT_EXPOSURE
	var hdr_image := hdr.get_texture().get_image()
	var float_radiance := _mean_float(hdr_image, _centre(hdr_image, 32)) / FLAT_EXPOSURE
	print(
		(
			"PROBE flat: ground %s E/pi rgb %.5f %.5f %.5f luminance %.5f"
			% [_ground(arg), radiance.x, radiance.y, radiance.z, _lum(radiance)]
		)
	)
	print(
		(
			"PROBE flat float: ground %s E/pi rgb %.5f %.5f %.5f luminance %.5f"
			% [
				_ground(arg),
				float_radiance.x,
				float_radiance.y,
				float_radiance.z,
				_lum(float_radiance),
			]
		)
	)


func _lower(arg: String) -> void:
	_rig_at(START_SUN, START_MOON, START_FRACTION, START_SIDEREAL, _ground(arg))
	_environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	_environment.tonemap_exposure = LOWER_EXPOSURE
	_camera.fov = 90.0
	_camera.position = Vector3(0.0, 2.0, 0.0)
	# Five faces of a cube: straight down, then towards north, east, south and west.
	var faces := [
		Basis.looking_at(Vector3.DOWN, Vector3(0.0, 0.0, -1.0)),
		Basis.looking_at(_frame.y, Vector3.UP),
		Basis.looking_at(_frame.x, Vector3.UP),
		Basis.looking_at(-_frame.y, Vector3.UP),
		Basis.looking_at(-_frame.x, Vector3.UP),
	]
	var cos_sum := Vector3.ZERO
	var cos_weight := 0.0
	var sa_sum := Vector3.ZERO
	var sa_weight := 0.0
	var below_band := Vector3.ZERO
	var below_band_weight := 0.0
	var brightest := 0.0
	var ring := Vector3.ZERO
	var ring_weight := 0.0
	for basis in faces:
		_camera.basis = basis
		var image := await _capture(20)
		var size := image.get_size()
		for j in size.y:
			for i in size.x:
				var u := 2.0 * (i + 0.5) / size.x - 1.0
				var v := 1.0 - 2.0 * (j + 0.5) / size.y
				var direction: Vector3 = (basis * Vector3(u, v, -1.0)).normalized()
				if absf(direction.y) < 0.02:
					var h := image.get_pixel(i, j).srgb_to_linear()
					var solid_h := 1.0 / pow(1.0 + u * u + v * v, 1.5)
					ring += Vector3(h.r, h.g, h.b) / LOWER_EXPOSURE * solid_h
					ring_weight += solid_h
				if direction.y >= 0.0:
					continue
				var c := image.get_pixel(i, j).srgb_to_linear()
				var radiance := Vector3(c.r, c.g, c.b) / LOWER_EXPOSURE
				brightest = maxf(brightest, maxf(c.r, maxf(c.g, c.b)))
				var solid := 1.0 / pow(1.0 + u * u + v * v, 1.5)
				cos_sum += radiance * solid * -direction.y
				cos_weight += solid * -direction.y
				sa_sum += radiance * solid
				sa_weight += solid
				if direction.y < -0.1:
					below_band += radiance * solid * -direction.y
					below_band_weight += solid * -direction.y
	var cos_mean := cos_sum / cos_weight
	var sa_mean := sa_sum / sa_weight
	var band_mean := below_band / below_band_weight
	print(
		(
			"PROBE lower: ground %s cosine-weighted rgb %.5f %.5f %.5f luminance %.5f"
			% [_ground(arg), cos_mean.x, cos_mean.y, cos_mean.z, _lum(cos_mean)]
		)
	)
	print(
		(
			"PROBE lower: ground %s solid-angle rgb %.5f %.5f %.5f luminance %.5f"
			% [_ground(arg), sa_mean.x, sa_mean.y, sa_mean.z, _lum(sa_mean)]
		)
	)
	print(
		(
			"PROBE lower: ground %s below the band (y < -0.1), cosine-weighted rgb %.5f %.5f %.5f"
			% [_ground(arg), band_mean.x, band_mean.y, band_mean.z]
		)
	)
	var ring_mean := ring / ring_weight
	print(
		(
			"PROBE lower: ground %s the horizon's ring (|y| < 0.02), solid-angle rgb %.5f %.5f %.5f"
			% [_ground(arg), ring_mean.x, ring_mean.y, ring_mean.z]
		)
	)
	print("PROBE lower: brightest displayed linear value %.4f (1.0 would clip)" % brightest)


func _wall(light: String, arg: String) -> void:
	match light:
		"rig":
			_rig_at(START_SUN, START_MOON, START_FRACTION, START_SIDEREAL, _ground(arg))
		"rig_nomoon":
			_rig_at(START_SUN, START_MOON, START_FRACTION, START_SIDEREAL, _ground(arg))
			_moon.visible = false
		"m3":
			_m3_at(M3_SUN)
		"m3start":
			_m3_at(START_SUN)
		_:
			print("PROBE wall: unknown light '%s'" % light)
			return
	_plane(_grey())
	var wall := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(30.0, 20.0, 2.0)
	wall.mesh = box
	wall.material_override = _grey()
	wall.position = Vector3(0.0, 10.0, 0.0)
	root.add_child(wall)
	var tree := MeshInstance3D.new()
	var cone := CylinderMesh.new()
	cone.top_radius = 0.0
	cone.bottom_radius = 2.5
	cone.height = 20.0
	cone.radial_segments = 32
	tree.mesh = cone
	tree.material_override = _grey()
	tree.position = Vector3(-18.0, 10.0, -20.0)
	root.add_child(tree)
	_camera.fov = 60.0
	_camera.position = Vector3(0.0, 6.0, -60.0)
	_camera.basis = Basis.looking_at(Vector3(0.0, 0.0, 1.0), Vector3.UP)
	var hdr := _hdr_twin()
	var image := await _capture(60)
	var hdr_image := hdr.get_texture().get_image()
	# The wall's north face from x -5 to 5, y 6 to 14 (z = -1); lit ground from x -5 to 5, z -36 to
	# -26 (the wall's shadow ends about 17 m north of it); the cone's north side 3 to 9 m up.
	var face := _rect_of([Vector3(-5, 6, -1.01), Vector3(5, 14, -1.01)])
	var ground := _rect_of([Vector3(-5, 0, -36), Vector3(5, 0, -26)])
	var cone_top := _camera.unproject_position(Vector3(-18.0, 9.0, -20.0))
	var cone_bottom := _camera.unproject_position(Vector3(-18.0, 3.0, -20.0))
	var cone_rect := Rect2i(
		int(cone_top.x) - 2, int(cone_top.y), 5, int(cone_bottom.y) - int(cone_top.y)
	)
	var y_face := _lum(_mean(image, face))
	var y_ground := _lum(_mean(image, ground))
	var y_cone := _lum(_mean(image, cone_rect))
	var f_face := _lum(_mean_float(hdr_image, face))
	var f_ground := _lum(_mean_float(hdr_image, ground))
	var f_cone := _lum(_mean_float(hdr_image, cone_rect))
	print(
		(
			(
				"PROBE wall float: light %s ground %s face %.6f cone %.6f lit ground %.6f"
				+ " face/ground %.5f cone/ground %.5f (image format %s)"
			)
			% [
				light,
				_ground(arg) if light.begins_with("rig") else "procedural",
				f_face,
				f_cone,
				f_ground,
				f_face / f_ground,
				f_cone / f_ground,
				hdr_image.get_format(),
			]
		)
	)
	print(
		(
			(
				"PROBE wall: light %s ground %s exposure %.4f face %.5f cone %.5f lit ground %.5f"
				+ " face/ground %.4f cone/ground %.4f"
			)
			% [
				light,
				_ground(arg) if light.begins_with("rig") else "procedural",
				_environment.tonemap_exposure,
				y_face,
				y_cone,
				y_ground,
				y_face / y_ground,
				y_cone / y_ground,
			]
		)
	)
	print("PROBE wall: pixels face %s ground %s cone %s" % [face, ground, cone_rect])
	var shot := OS.get_environment("PROBE_SHOT")
	if shot != "":
		image.save_jpg(shot, 0.9)


## The pixel rectangle that the box of [param corners] projects to, shrunk by two pixels.
func _rect_of(corners: Array) -> Rect2i:
	var a: Vector3 = corners[0]
	var b: Vector3 = corners[1]
	var lo := Vector2(INF, INF)
	var hi := Vector2(-INF, -INF)
	for x in [a.x, b.x]:
		for y in [a.y, b.y]:
			for z in [a.z, b.z]:
				var p := _camera.unproject_position(Vector3(x, y, z))
				lo = Vector2(minf(lo.x, p.x), minf(lo.y, p.y))
				hi = Vector2(maxf(hi.x, p.x), maxf(hi.y, p.y))
	return Rect2i(
		int(ceil(lo.x)) + 2, int(ceil(lo.y)) + 2, int(hi.x - lo.x) - 4, int(hi.y - lo.y) - 4
	)


## The sRGB of the pixel [param el] degrees above the horizon at the view's centre column, for a
## camera pitched [param pitch] degrees up with a vertical fov of [param fov].
func _srgb_at(image: Image, el: float, pitch: float, fov: float) -> Color:
	var size := image.get_size()
	var t := tan(deg_to_rad(el - pitch)) / tan(deg_to_rad(fov / 2.0))
	var row := clampi(int(round(size.y / 2.0 - t * size.y / 2.0)), 0, size.y - 1)
	var c := Color(0, 0, 0)
	for dx in range(-2, 3):
		c += image.get_pixel(size.x / 2 + dx, row) / 5.0
	return c


func _srgb_text(c: Color) -> String:
	return "(%d, %d, %d)" % [roundi(c.r * 255.0), roundi(c.g * 255.0), roundi(c.b * 255.0)]


func _twilight() -> void:
	_rig_at(Vector2(270.0, -3.0), Vector2(90.0, -30.0), 0.5, 0.0, null)
	_camera.fov = 60.0
	_camera.position = Vector3(0.0, 10.0, 0.0)
	for el in [-3.0, 3.0, -0.5, -1.5, -9.0]:
		_rig.apply(_towards(270.0, el), _towards(90.0, -30.0), 0.5, 0.0)
		var line := "PROBE twilight: sun %.1f exposure %.3f" % [el, _environment.tonemap_exposure]
		for az in [270.0, 90.0]:
			var look := _towards(az, 15.0)
			_camera.basis = Basis.looking_at(look, Vector3.UP)
			var image := await _capture(20)
			var shot := OS.get_environment("PROBE_SHOT")
			if shot != "" and el == -3.0 and az == 270.0:
				image.save_jpg(shot, 0.9)
			line += (
				" | view %d: 5 up %s 15 up %s 30 up %s"
				% [
					az,
					_srgb_text(_srgb_at(image, 5.0, 15.0, 60.0)),
					_srgb_text(_srgb_at(image, 15.0, 15.0, 60.0)),
					_srgb_text(_srgb_at(image, 30.0, 15.0, 60.0)),
				]
			)
		print(line)


func _night() -> void:
	_rig_at(Vector2(180.0, -30.0), Vector2(0.0, -20.0), 0.5, 0.0, null)
	_plane(_grey())
	_look_down(100.0, 30.0)
	var image := await _capture(30)
	var mean := _mean(image, _centre(image, 32))
	var c := image.get_pixel(256, 256)
	print(
		(
			"PROBE night: exposure %.3f luminance over albedo %.5f, sRGB %s"
			% [_environment.tonemap_exposure, _lum(mean) / ALBEDO_128, _srgb_text(c)]
		)
	)


func _disk() -> void:
	_rig_at(Vector2(270.0, 10.0), Vector2(90.0, -30.0), 0.5, 0.0, null)
	_camera.fov = 60.0
	_camera.position = Vector3(0.0, 10.0, 0.0)
	_camera.basis = Basis.looking_at(_towards(270.0, 15.0), Vector3.UP)
	for disk in [0.53, 0.0]:
		_rig.sky_material.set_shader_parameter("sun_disk_deg", disk)
		var image := await _capture(20)
		var size := image.get_size()
		var t := tan(deg_to_rad(10.0 - 15.0)) / tan(deg_to_rad(30.0))
		var row := int(round(size.y / 2.0 - t * size.y / 2.0))
		var peak := Color(0, 0, 0)
		for y in range(row - 4, row + 5):
			for x in range(size.x / 2 - 4, size.x / 2 + 5):
				var c := image.get_pixel(x, y)
				if c.get_luminance() > peak.get_luminance():
					peak = c
		var aside := image.get_pixel(size.x / 2 + 20, row)
		print(
			(
				"PROBE disk: sun_disk_deg %.2f peak %s sky 20 px aside %s"
				% [disk, _srgb_text(peak), _srgb_text(aside)]
			)
		)


func _edge(arg: String) -> void:
	_rig_at(START_SUN, START_MOON, START_FRACTION, START_SIDEREAL, _ground(arg))
	var stand_in := MeshInstance3D.new()
	var mesh := PlaneMesh.new()
	mesh.size = Vector2(2000.0, 3000.0)
	stand_in.mesh = mesh
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.148308, 0.166591, 0.119924).linear_to_srgb()
	material.roughness = 0.95
	stand_in.material_override = material
	root.add_child(stand_in)
	_camera.fov = 60.0
	# 2000 m south of the stand-in's north edge (z = -1500), so the edge lies 16.7 degrees down.
	_camera.position = Vector3(0.0, 600.0, 500.0)
	_camera.basis = Basis.looking_at(_towards(0.0, -20.0), Vector3.UP)
	var image := await _capture(30)
	var size := image.get_size()
	var rows := {
		"the stand-in 25 below (1287 m off)": -25.0,
		"the sky's ground 10 below": -10.0,
		"3 below": -3.0,
	}
	var line := "PROBE edge: ground %s" % _ground(arg)
	for name in rows:
		var t := tan(deg_to_rad(rows[name] + 20.0)) / tan(deg_to_rad(30.0))
		var row := clampi(int(round(size.y / 2.0 - t * size.y / 2.0)), 2, size.y - 3)
		var mean := _mean(image, Rect2i(size.x / 2 - 32, row - 2, 64, 5))
		line += " | %s %.5f" % [name, _lum(mean)]
	print(line)
	var shot := OS.get_environment("PROBE_SHOT")
	if shot != "":
		image.save_jpg(shot, 0.9)


func _shadow(angular: float) -> void:
	_rig_at(CALIB_SUN, CALIB_MOON, CALIB_FRACTION, CALIB_SIDEREAL, null)
	_sun.light_angular_distance = angular
	_plane(_grey())
	var box := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = Vector3(20.0, 200.0, 20.0)
	box.mesh = mesh
	box.material_override = _grey()
	box.position = Vector3(0.0, 100.0, 0.0)
	root.add_child(box)
	# The shadow runs away from the sun; the box's south-east vertical edge (x = 10, z = 10) at
	# 144 m casts the shadow's east edge at 144 / tan(elevation) along it.
	var away := -_towards(CALIB_SUN.x, 0.0)
	var reach := 144.0 / tan(deg_to_rad(CALIB_SUN.y))
	var at := Vector3(10.0, 0.0, 10.0) + away * reach
	_camera.fov = 10.0
	_camera.position = Vector3(at.x, 100.0, at.z)
	_camera.basis = Basis.looking_at(Vector3.DOWN, Vector3(0.0, 0.0, -1.0))
	var image := await _capture(30)
	var size := image.get_size()
	var metres_per_px := 2.0 * 100.0 * tan(deg_to_rad(5.0)) / size.y
	var row := size.y / 2
	var profile := PackedFloat64Array()
	for x in size.x:
		var c := image.get_pixel(x, row)
		profile.append(0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b)
	var shade := 0.0
	var lit := 0.0
	for x in range(20, 60):
		shade += profile[x] / 40.0
	for x in range(size.x - 60, size.x - 20):
		lit += profile[x] / 40.0
	var low := shade + 0.1 * (lit - shade)
	var high := shade + 0.9 * (lit - shade)
	var first := -1
	var last := -1
	for x in size.x:
		if first < 0 and profile[x] > low:
			first = x
		if last < 0 and profile[x] > high:
			last = x
	print(
		(
			"PROBE shadow: angular %.2f shadow %.3f lit %.3f edge 10-90 %% %.2f m (%d px, %.4f m/px)"
			% [angular, shade, lit, (last - first) * metres_per_px, last - first, metres_per_px]
		)
	)
