extends SceneTree
## The gate's render check of where the photo shader lifts the photo inside the capture
## shadows' mask (brief M4-06; m4-design §8). Run by tools/gate.sh under xvfb-run, Compatibility
## renderer (Mesa's llvmpipe), never in GUT.
##
## The complete test world (complete_world.gd) with its terrain replaced by one flat level, its
## terrain built by TerrainLoader with the world's PhotoGrid, SurfaceGrid and CaptureShadowGrid
## (the main scene does not read the mask before brief M4-10), lit by one light from straight
## above, seen by a camera straight above the photo's middle. The photo's texture is replaced by
## one uniform grey of GREY (sRGB 0.2) in both views, so that no texel of the photo clips under
## the lift and the photo's own pattern does not enter the comparison: the check is about WHERE
## the lift lands, not about the photo. Two views: the mask as the loader set it, and the mask
## replaced by one texel of 0 (no lift). For every STEP-th pixel over class 0 and inside the
## photo, the ratio of the two renders is compared with what the DATA says is at the world point
## under it: the mask's value there, filtered bilinearly between the 0.5 m texel centres
## (CaptureShadowGrid's rectangle and decoded bytes). It reads nothing of the shaders.
##
## One result line, "RENDER lift: PASS|FAIL ..." (render_common.gd):
## - the correlation of the ratio with the data's mask is at least LIFT_MIN_CORR and above every
##   alternative: the mask mirrored north-south, mirrored east-west, transposed, read at the
##   nearest texel instead of filtered, and moved by 0.05 m steps up to 0.4 m east-west and
##   north-south; the best of the shifts lies within one step of none and every shift of 0.1 m
##   or more is below none (half a texel is 0.25 m);
## - the ratio's median is LIFT within LEVEL_TOLERANCE where the data's mask is 1 (the texel
##   and its eight neighbours all 255) and 1 within LEVEL_TOLERANCE where it is 0 (all nine 0).
##
## Proves where the lift lands and its strength on a flat 16 m test world under Compatibility, not
## how it looks: not Forward+, not the colour encoding (under Compatibility no sRGB conversion
## shows: brain.md H21, so the lift's linear-light arithmetic is NOT checked here), not the
## order of the shader's rules (all multiply), not the owner's GPU, not the real village's mask.
const CompleteWorld := preload("res://tests/complete_world.gd")
const Common := preload("res://tests/render/render_common.gd")
const COLUMNS := 41
const ROWS := 24
const LEVEL := 605.0
const STEP := 3
const CAMERA_AT := Vector3(1025.0, LEVEL + 9.0, 15.5)
## The uniform photo both views wear (sRGB-valued grey: lifted 3 times it stays below 1).
const GREY := 0.2
## The shader's shadow_lift, which the mask's full value must render.
const LIFT := 3.0
const LEVEL_TOLERANCE := 0.05
## The samples stay this far inside the photo's rectangle (m).
const MARGIN_M := 0.25
const SHIFT_STEPS := 8
const SHIFT_M := 0.05
const MIN_LUMINANCE := 8.0
const LIFT_MIN_CORR := 0.95
const MIN_SAMPLES := 20000
const MIN_LEVEL_SAMPLES := 2000
const WORLD_DIR := "user://render_lift"


func _initialize() -> void:
	await process_frame
	var ok := await _check()
	CompleteWorld.remove_tree(WORLD_DIR)
	quit(0 if ok else 1)


func _check() -> bool:
	var heights := PackedFloat32Array()
	heights.resize(COLUMNS * ROWS)
	heights.fill(LEVEL)
	var bytes := heights.to_byte_array()
	var path := CompleteWorld.write(
		WORLD_DIR,
		func(m: Dictionary) -> void: m["terrain"]["sha256"] = CompleteWorld.sha256(bytes),
		bytes
	)
	var world := WorldConfig.from_manifest(path)
	var grid := TerrainGrid.from_manifest(path, world)
	var photo := PhotoGrid.from_manifest(path, world)
	var surfaces := SurfaceGrid.from_manifest(path, world)
	var shadows := CaptureShadowGrid.from_manifest(path, world)
	var failures := PackedStringArray()
	if grid == null or photo == null or surfaces == null or shadows == null:
		failures.append(
			"the complete world's terrain, photo, classes or capture shadows were refused"
		)
		return Common.report("lift", failures, "no render")
	var scene := Node3D.new()
	root.add_child(scene)
	var camera := Camera3D.new()
	scene.add_child(camera)
	camera.position = CAMERA_AT
	camera.rotation = Vector3(-deg_to_rad(89.0), 0.0, 0.0)
	camera.current = true
	var light := DirectionalLight3D.new()
	scene.add_child(light)
	light.rotation = Vector3(-deg_to_rad(90.0), 0.0, 0.0)
	# No specular: a light and a camera both straight above add a constant highlight that is not
	# lifted, so the ratio would read below the lift.
	light.light_specular = 0.0
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color.BLACK
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	scene.add_child(world_environment)
	await process_frame
	var terrain := TerrainLoader.create(grid, scene, photo, surfaces, shadows)
	var grey := Image.create_empty(1, 1, false, Image.FORMAT_RGB8)
	grey.fill(Color(GREY, GREY, GREY))
	terrain.material.set_shader_param("photo", ImageTexture.create_from_image(grey))
	var lifted := await Common.capture(self)
	Common.save(lifted, "render_lift_with_mask")
	var none := ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_L8))
	terrain.material.set_shader_param("capture_shadow", none)
	var unlifted := await Common.capture(self)
	Common.save(unlifted, "render_lift_without_mask")
	return _compare(camera, lifted, unlifted, photo, surfaces, shadows)


func _compare(
	camera: Camera3D,
	lifted: Image,
	unlifted: Image,
	photo: PhotoGrid,
	surfaces: SurfaceGrid,
	shadows: CaptureShadowGrid
) -> bool:
	# [x, z, ratio] for every sample over class 0, inside the photo, bright enough unlifted.
	var points := []
	var ratios := PackedFloat64Array()
	for py in range(0, lifted.get_height(), STEP):
		for px in range(0, lifted.get_width(), STEP):
			var at := Vector2(px + 0.5, py + 0.5)
			var origin := camera.project_ray_origin(at)
			var direction := camera.project_ray_normal(at)
			if direction.y >= -0.01:
				continue
			var p := origin + direction * ((LEVEL - origin.y) / direction.y)
			if (
				p.x < photo.x0 + MARGIN_M
				or p.x > photo.x0 + photo.width_m - MARGIN_M
				or p.z < photo.z0 + MARGIN_M
				or p.z > photo.z0 + photo.depth_m - MARGIN_M
				or surfaces.class_at(p.x, p.z) != 0
			):
				continue
			var dark := Common.lum(unlifted.get_pixel(px, py))
			if dark < MIN_LUMINANCE:
				continue
			points.append(Vector2(p.x, p.z))
			ratios.append(Common.lum(lifted.get_pixel(px, py)) / dark)
	var mask := _mask_image(shadows)
	var by_x := []
	var by_z := []
	for i in range(-SHIFT_STEPS, SHIFT_STEPS + 1):
		by_x.append(Common.corr(ratios, _expected(points, shadows, mask, i * SHIFT_M, 0.0, "")))
		by_z.append(Common.corr(ratios, _expected(points, shadows, mask, 0.0, i * SHIFT_M, "")))
	var right: float = by_x[SHIFT_STEPS]
	var others := {}
	for kind in ["north-south-mirrored", "east-west-mirrored", "transposed", "nearest"]:
		others[kind] = Common.corr(ratios, _expected(points, shadows, mask, 0.0, 0.0, kind))
	var failures := PackedStringArray()
	if points.size() < MIN_SAMPLES:
		failures.append("%d samples, %d needed" % [points.size(), MIN_SAMPLES])
	if right < LIFT_MIN_CORR:
		failures.append("correlation %.4f below %.2f" % [right, LIFT_MIN_CORR])
	for kind: String in others:
		if others[kind] >= right:
			failures.append("the mask reads as well or better %s (%.4f)" % [kind, others[kind]])
	for scan: Array in [[by_x, "east"], [by_z, "south"]]:
		var problem := _shift_problem(scan[0])
		if not problem.is_empty():
			failures.append("%s %s" % [problem, scan[1]])
	var full := PackedFloat64Array()
	var empty := PackedFloat64Array()
	for i in points.size():
		var around := _around(shadows, points[i])
		if around == 9:
			full.append(ratios[i])
		elif around == 0:
			empty.append(ratios[i])
	var full_median := _median(full)
	var empty_median := _median(empty)
	if full.size() < MIN_LEVEL_SAMPLES or empty.size() < MIN_LEVEL_SAMPLES:
		failures.append(
			(
				"%d samples inside the mask and %d outside, %d each needed"
				% [full.size(), empty.size(), MIN_LEVEL_SAMPLES]
			)
		)
	if absf(full_median - LIFT) > LEVEL_TOLERANCE * LIFT:
		failures.append("the lift inside the mask is %.3f, not %.1f" % [full_median, LIFT])
	if absf(empty_median - 1.0) > LEVEL_TOLERANCE:
		failures.append("the ratio outside the mask is %.3f, not 1" % empty_median)
	print("render lift: correlation by x shift (-0.40 to 0.40 m): %s" % [by_x])
	print("render lift: correlation by z shift (-0.40 to 0.40 m): %s" % [by_z])
	return Common.report(
		"lift",
		failures,
		(
			"correlation %.4f %s; lift %.3f inside the mask (%d), %.3f outside (%d), over %d pixels"
			% [right, others, full_median, full.size(), empty_median, empty.size(), points.size()]
		)
	)


## The mask's decoded bytes as an Image, row 0 north.
func _mask_image(shadows: CaptureShadowGrid) -> Image:
	return shadows.texture.get_image()


## What the data says the lift's weight is at each point moved by (dx, dz) metres: the mask in
## 0..1, bilinear between texel centres ((c + 0.5)·cell_m, (r + 0.5)·cell_m from the rectangle's
## corner), 0 outside the rectangle; [param kind] names an alternative ("" the right one).
func _expected(
	points: Array, shadows: CaptureShadowGrid, mask: Image, dx: float, dz: float, kind: String
) -> PackedFloat64Array:
	var out := PackedFloat64Array()
	out.resize(points.size())
	for i in points.size():
		var u: float = (points[i].x - dx - shadows.x0) / shadows.width_m
		var v: float = (points[i].y - dz - shadows.z0) / shadows.depth_m
		if kind == "north-south-mirrored":
			v = 1.0 - v
		elif kind == "east-west-mirrored":
			u = 1.0 - u
		elif kind == "transposed":
			var t := u
			u = v
			v = t
		if u < 0.0 or u > 1.0 or v < 0.0 or v > 1.0:
			out[i] = 0.0
			continue
		var tx := u * shadows.columns
		var ty := v * shadows.rows
		if kind == "nearest":
			out[i] = _texel(mask, floori(tx), floori(ty))
			continue
		tx -= 0.5
		ty -= 0.5
		var cx := floori(tx)
		var cy := floori(ty)
		var fx := tx - cx
		var fy := ty - cy
		var north := lerpf(_texel(mask, cx, cy), _texel(mask, cx + 1, cy), fx)
		var south := lerpf(_texel(mask, cx, cy + 1), _texel(mask, cx + 1, cy + 1), fx)
		out[i] = lerpf(north, south, fy)
	return out


## The mask's texel (c, r) in 0..1, clamped to the edge as the shader's repeat_disable samples.
func _texel(mask: Image, c: int, r: int) -> float:
	return mask.get_pixel(clampi(c, 0, mask.get_width() - 1), clampi(r, 0, mask.get_height() - 1)).r


## How many of the 3 x 3 texels around the one holding [param p] are 255 (-1 off the mask).
func _around(shadows: CaptureShadowGrid, p: Vector2) -> int:
	var count := 0
	for j in range(-1, 2):
		for i in range(-1, 2):
			var value := shadows.value_at(p.x + i * shadows.cell_m, p.y + j * shadows.cell_m)
			if value < 0:
				return -1
			if value == 255:
				count += 1
	return count


func _median(values: PackedFloat64Array) -> float:
	if values.is_empty():
		return NAN
	var sorted := values.duplicate()
	sorted.sort()
	return sorted[sorted.size() / 2]


## "" when the greatest correlation of [param values] (one per step from -n to n) lies within one
## step of none and every value two or more steps away is below none's; else what is wrong.
func _shift_problem(values: Array) -> String:
	var none: float = values[SHIFT_STEPS]
	var best := SHIFT_STEPS
	for i in values.size():
		if values[i] > values[best]:
			best = i
	if absi(best - SHIFT_STEPS) > 1:
		return (
			"the best fit is at a shift of the data of %+.2f m" % ((best - SHIFT_STEPS) * SHIFT_M)
		)
	for i in values.size():
		if absi(i - SHIFT_STEPS) >= 2 and values[i] >= none:
			return "the mask reads as well or better %+.2f m" % ((i - SHIFT_STEPS) * SHIFT_M)
	return ""
