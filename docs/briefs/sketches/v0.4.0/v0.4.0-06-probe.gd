extends SceneTree
## The software Forward+ probe of brief v0.4.0-06 (the stars on the Hipparcos Catalogue).
## Design's measuring tool, not a test, kept with the brief's sketches: run it from the
## repository's root with its absolute path; never copy it under game/:
##
##   VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json XDG_DATA_HOME=<yours> \
##   xvfb-run -a timeout 300 godot --path game --rendering-driver vulkan \
##   --rendering-method forward_plus --audio-driver Dummy --resolution 512x512 \
##   -s "$PWD/docs/briefs/sketches/v0.4.0/v0.4.0-06-probe.gd" -- <mode> [<argument> ...]
##
## Each mode prints lines beginning "PROBE <mode>" and exits 0; it exits 1 when the mode is
## unknown or the renderer is not Forward+. MSAA is off and the window's pixels are the view's
## (no stretch). The owner's frame: east +x, north -z, up +y; the site's latitude 46.0196233.
## Night throughout: the sun at grid azimuth 180, -30 degrees, the moon at 0, -20 (both lights
## hidden, the sky in its night branch, stars_strength 1, exposure 4.0). A view is aimed at a
## star through the rig's own celestial_basis (its transpose turns celestial coordinates into a
## scene direction, as the pinned test's _scene_direction), so a shader that samples the star
## image anywhere else than the basis says puts the star off the view's centre.
##
## Modes:
## - star <name> [off]: a camera at the origin, fov 10, aimed at the star <name> (polaris,
##   sirius, vega, wrap: omega Psc at right ascension 359.83, next to the image's seam) at the
##   local sidereal time that puts it on the meridian (Polaris at 168.06, the photo's moment:
##   hour angle 130°, 0.8° off the meridian in azimuth), the rig with the star image of
##   res://sky/stars.csv; after 30 frames the brightest pixel (by the sum of its sRGB
##   codes), its offset from the centre (256, 256) and its sRGB, and the median sRGB of the
##   view. With "off", stars_strength is set to 0 after apply: the brightest pixel then is the
##   background's.
## - coords <ra> <dec>: the night sky is a coordinate image (RGBF 1024 x 512, red = u, green =
##   v at each texel's centre, u = right ascension / 360, v = (90 - declination) / 180), the
##   tone map linear at exposure 1; a view aimed at (<ra>, <dec>) through the basis reads the
##   mean of its centre 32 x 32 pixels in an HDR twin (half floats, the glow subtracted; blue,
##   0 in the image, shows what is left of the glow and the noise) and prints the right
##   ascension and declination the shader sampled there.
## - shot <lst>: the real star image, a view towards the south 35 degrees up, fov 90, at the
##   local sidereal time <lst>; PROBE_SHOT=<file.jpg> in the environment saves it.

const LAT := 46.0196233
const STARS := "res://sky/stars.csv"
const SUN := Vector2(180.0, -30.0)
const MOON := Vector2(0.0, -20.0)
const GLOW := Vector3(0.004, 0.005, 0.009)
## Right ascension, declination and the sidereal time each star is aimed at.
const TARGETS := {
	"polaris": [37.9462, 89.2641, 168.06],
	"sirius": [101.2885, -16.7131, 101.2885],
	"vega": [279.2341, 38.7830, 279.2341],
	"wrap": [359.8275, 6.8636, 359.8275],
}

var _frame := Basis(Vector3(1, 0, 0), Vector3(0, 0, -1), Vector3(0, 1, 0))
var _environment: Environment
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
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_DISABLED
	var ok := true
	match mode:
		"star":
			ok = TARGETS.has(arg)
			if ok:
				await _star(arg, arg2 == "off")
		"coords":
			await _coords(float(arg), float(arg2))
		"shot":
			await _shot(float(arg))
		_:
			ok = false
	if not ok:
		print("PROBE: unknown mode or star '%s %s'" % [mode, arg])
	quit(0 if ok else 1)


## The unit vector towards grid azimuth [param az] and elevation [param el], in degrees.
func _towards(az: float, el: float) -> Vector3:
	var a := deg_to_rad(az)
	var e := deg_to_rad(el)
	return (_frame.x * sin(a) + _frame.y * cos(a)) * cos(e) + _frame.z * sin(e)


func _night(stars: Image, sidereal: float) -> void:
	var environment_node := WorldEnvironment.new()
	_environment = Environment.new()
	environment_node.environment = _environment
	root.add_child(environment_node)
	var sun := DirectionalLight3D.new()
	var moon := DirectionalLight3D.new()
	root.add_child(sun)
	root.add_child(moon)
	_camera = Camera3D.new()
	_camera.current = true
	root.add_child(_camera)
	_rig = SkyRig.create(sun, moon, _environment, _frame, LAT, stars)
	_rig.apply(_towards(SUN.x, SUN.y), _towards(MOON.x, MOON.y), 0.5, sidereal)


## The scene direction of right ascension [param ra] and declination [param dec] through the
## rig's celestial_basis as apply left it.
func _scene_direction(ra: float, dec: float) -> Vector3:
	var basis: Basis = _rig.sky_material.get_shader_parameter("celestial_basis")
	var r := deg_to_rad(ra)
	var d := deg_to_rad(dec)
	return basis.transposed() * Vector3(cos(d) * cos(r), cos(d) * sin(r), sin(d))


func _aim(direction: Vector3, fov: float) -> void:
	_camera.fov = fov
	var up := _frame.z
	if absf(direction.dot(up)) > 0.99:
		up = _frame.y
	_camera.basis = Basis.looking_at(direction, up)


func _capture(frames: int = 30) -> Image:
	for i in frames:
		await process_frame
	await RenderingServer.frame_post_draw
	return root.get_texture().get_image()


func _codes(c: Color) -> Vector3i:
	return Vector3i(roundi(c.r * 255.0), roundi(c.g * 255.0), roundi(c.b * 255.0))


func _star(name: String, off: bool) -> void:
	var target: Array = TARGETS[name]
	_night(SkyRig.star_image(STARS), target[2])
	if off:
		_rig.sky_material.set_shader_parameter("stars_strength", 0.0)
	var direction := _scene_direction(target[0], target[1])
	_aim(direction, 10.0)
	var image := await _capture(30)
	var size := image.get_size()
	var best := Vector2i.ZERO
	var best_sum := -1
	var sums: Array[int] = []
	for y in size.y:
		for x in size.x:
			var c := _codes(image.get_pixel(x, y))
			var s := c.x + c.y + c.z
			sums.append(s)
			if s > best_sum:
				best_sum = s
				best = Vector2i(x, y)
	# The centre of the pixels at the brightest code sum (a bright star saturates a blob).
	var centre := Vector2.ZERO
	var count := 0
	for y in size.y:
		for x in size.x:
			if sums[y * size.x + x] == best_sum:
				centre += Vector2(x, y)
				count += 1
	centre /= count
	var above := 0
	sums.sort()
	for s in sums:
		above += 1 if s > sums[sums.size() / 2] + 30 else 0
	var el := rad_to_deg(asin(clampf(direction.dot(_frame.z), -1.0, 1.0)))
	var offset := centre - Vector2(size / 2)
	var path := OS.get_environment("PROBE_SHOT")
	if path != "":
		image.save_jpg(path, 0.9)
	print(
		(
			(
				"PROBE star %s%s: elevation %.3f, brightest at %s (%d px, offset %s, %.1f px),"
				+ " sRGB %s, median code sum %d, %d px above it by 30"
			)
			% [
				name,
				" off" if off else "",
				el,
				centre,
				count,
				offset,
				offset.length(),
				_codes(image.get_pixelv(best)),
				sums[sums.size() / 2],
				above,
			]
		)
	)


func _coords(ra: float, dec: float) -> void:
	var w := 1024
	var h := 512
	var data := PackedFloat32Array()
	data.resize(w * h * 3)
	for y in h:
		for x in w:
			var i := (y * w + x) * 3
			data[i] = (x + 0.5) / w
			data[i + 1] = (y + 0.5) / h
	var coords := Image.create_from_data(w, h, false, Image.FORMAT_RGBF, data.to_byte_array())
	_night(coords, 168.06)
	_environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	_environment.tonemap_exposure = 1.0
	_aim(_scene_direction(ra, dec), 10.0)
	var hdr := SubViewport.new()
	hdr.size = root.size
	hdr.use_hdr_2d = true
	hdr.msaa_3d = Viewport.MSAA_DISABLED
	hdr.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	var hdr_camera := Camera3D.new()
	hdr_camera.fov = _camera.fov
	hdr_camera.transform = _camera.transform
	hdr.add_child(hdr_camera)
	root.add_child(hdr)
	hdr_camera.current = true
	await _capture(30)
	var hdr_image := hdr.get_texture().get_image()
	# The mean of the centre 32 x 32 pixels: the sky's debanding noise averages out, and the
	# coordinates, linear across the view, average to the centre's.
	var c := Color(0, 0, 0)
	var half := 16
	var mid := hdr_image.get_size() / 2
	for y in range(mid.y - half, mid.y + half):
		for x in range(mid.x - half, mid.x + half):
			c += hdr_image.get_pixel(x, y)
	c /= float(4 * half * half)
	var u := c.r - GLOW.x
	var v := c.g - GLOW.y
	print(
		(
			(
				"PROBE coords: aimed at RA %.3f Dec %.3f, the centre sampled RA %.3f Dec %.3f"
				+ " (raw %.5f, %.5f, %.5f)"
			)
			% [ra, dec, u * 360.0, 90.0 - v * 180.0, c.r, c.g, c.b]
		)
	)


func _shot(sidereal: float) -> void:
	_night(SkyRig.star_image(STARS), sidereal)
	_camera.fov = 90.0
	_camera.basis = Basis.looking_at(_towards(180.0, 35.0), _frame.z)
	var image := await _capture(30)
	var lit := 0
	for y in image.get_height():
		for x in image.get_width():
			var c := _codes(image.get_pixel(x, y))
			if c.x + c.y + c.z > 3 * 60:
				lit += 1
	print("PROBE shot: LST %.2f, %d pixels above sRGB 60" % [sidereal, lit])
	var path := OS.get_environment("PROBE_SHOT")
	if path != "":
		image.save_jpg(path, 0.9)
		print("PROBE shot: saved %s" % path)
