extends SceneTree
## The gate's render check of where the photo shader puts the photo and the surface classes
## (brief M3-R1-fix-3; docs/reviews/M3-R1-placement.md §M3-R1-P-03, Appendix B; the water's
## part rewritten by brief M4-06 for m4-design §8's water). Run by
## tools/gate.sh under xvfb-run, Compatibility renderer (Mesa's llvmpipe), never in GUT.
##
## The complete test world with its terrain replaced by one flat level and its box and trees
## buried under it (render_common.gd), out of the camera's view; the main scene reading it; a
## camera straight above the photo's middle; the light's highlight, the sky's reflection and
## ambient light off, the tone map linear and the water's ripples off (their strength 0), so that a
## ratio of two renders is the albedo's alone. For every STEP-th pixel the world point under it is
## found by intersecting the pixel's ray with the flat ground, and the rendered pixel is compared
## with what the DATA says is at that point: the photo texel (PhotoGrid's rectangle and decoded
## image) and the surface class (SurfaceGrid's class_at). It reads nothing of the shaders.
##
## Two checks, each one result line (render_common.gd):
## - "photo": the correlation of the rendered luminance with the luminance of the photo texel the
##   data puts under each pixel (on class 0, where the photo alone is drawn) is at least
##   PHOTO_MIN_CORR at no shift and above every alternative: the data moved by 0.05 m steps up
##   to 0.4 m east-west and north-south, mirrored north-south, mirrored east-west.
## - "classes": the render with the classes against the render with the water class removed,
##   on the samples EDGE_M inside the terrain. Where the data's 1 m box is all water, the ratio's
##   median is WATER_ALBEDO within WATER_TOLERANCE. The rendered water weight, (1 - ratio) /
##   (1 - that median), above 0.5 agrees with class_at's water on at least CLASSES_MIN_AGREE of
##   the samples, better than with the data mirrored north-south, and its best fit over the
##   shifts of the data is within one 0.05 m step of none, in x and in z. On the bank (the samples
##   where the data's weight or a twin's lies strictly between 0 and 1) it correlates with the
##   data's eased weight (the shader's water_weight, written again in _water_weight) at least
##   BANK_MIN_CORR and better than with every twin: not eased (M3's 0.2 m blend), the 1 m box
##   without the smoothstep, a 0.6 m box, a 1.4 m box.
## The numbers on each line are what a failure points at: the scans tell a flip from a shift
## and a shift's size.
##
## Since brief v0.5.0-05 (M4-10 decision 9, re-cut on v0.4.0-11's file; one override and this
## paragraph change): the main scene hands the terrain the complete world's capture mask, so both
## views set shadow_lift to 1 (no lift: the photo is read as the data; render_lift.gd checks the
## lift). Measured in the pin author's rehearsal: with the mask handed and no override, the photo's
## correlation fell to 0.6584 (FAIL); with it, the base's 0.9752.
##
## Proves where, not how it looks: not Forward+, not the colour encoding (brain.md H21), not
## the owner's GPU, not any shader on the real village, not the water's roughness, ripples or
## drift (switched off or cancelled here). The flat terrain means the photo is seen from above at
## a place where the terrain's own relief cannot move it.
const CompleteWorld := preload("res://tests/complete_world.gd")
const Common := preload("res://tests/render/render_common.gd")
## The fixture terrain's grid, which the flat heights replace: columns x rows.
const COLUMNS := 41
const ROWS := 24
## The flat terrain's local height, between the fixture's own extremes.
const LEVEL := 605.0
## One pixel in STEP in each direction is sampled.
const STEP := 3
## The camera's local position: over the photo's middle, 9 m above the ground.
const CAMERA_AT := Vector3(1025.0, LEVEL + 9.0, 16.25)
## The samples' area, local x and z: inside the terrain, where the camera sees ground.
const AREA_X := Vector2(1015.0, 1035.0)
const AREA_Z := Vector2(10.5, 22.0)
## The photo samples stay this far inside the photo's rectangle, as a fraction of it.
const PHOTO_MARGIN := 0.03
## The photo shifts scanned, in 0.05 m steps, each way.
const PHOTO_STEPS := 8
## The class shifts scanned, in 0.05 m steps, each way.
const CLASS_STEPS := 6
const SHIFT_M := 0.05
## A render darker than this without the classes tells nothing about them.
const MIN_LUMINANCE := 8.0
## The water class.
const WATER := 2
## Fully on water the render is the water's albedo times the render without it (m4-design §8:
## 0.9), within WATER_TOLERANCE (the light's highlight on roughness 0.3 included).
const WATER_ALBEDO := 0.9
const WATER_TOLERANCE := 0.03
## The rendered water weight on the bank correlates at least this with the data's eased weight.
const BANK_MIN_CORR := 0.95
const MIN_FULL_WATER := 2000
## The classes' samples stay this far inside the terrain (m): its edge is the end of the mesh.
const EDGE_M := 0.6
const MIN_BANK_SAMPLES := 2000
const PHOTO_MIN_CORR := 0.95
const CLASSES_MIN_AGREE := 0.98
## The least samples either check needs, so that it cannot pass on nearly none.
const MIN_PHOTO_SAMPLES := 5000
const MIN_CLASS_SAMPLES := 20000
const WORLD_DIR := "user://render_photo"


func _initialize() -> void:
	# The root enters the tree only after _initialize returns; Terrain3D needs the tree.
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
		func(m: Dictionary) -> void:
			m["terrain"]["sha256"] = CompleteWorld.sha256(bytes)
			Common.bury_buildings(WORLD_DIR, m)
			Common.bury_trees(WORLD_DIR, m),
		bytes
	)
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = path
	root.add_child(main)
	# The game clock runs in main's _process; this check wants one sun, and _ready has already
	# placed it at the start moment (brief v0.4.0-11).
	main.set_process(false)
	for i in 4:
		await process_frame
	var world := WorldConfig.from_manifest(path)
	var photo := PhotoGrid.from_manifest(path, world)
	var surfaces := SurfaceGrid.from_manifest(path, world)
	var terrain: Terrain3D = main.get_node("Terrain")
	main.get_node("UI/ErrorPanel").hide()
	var camera: FreeFlyCamera = main.get_node("Camera")
	camera.set_view(CAMERA_AT, 0.0, -deg_to_rad(89.0))
	# The water's ripples off in both views (brief M4-06): they drift with TIME and shade the water
	# unevenly; the check is about where the water lies and how it eases, not its ripples.
	terrain.material.set_shader_param("water_normal_strength", 0.0)
	# And no lift (brief v0.5.0-05, M4-10 decision 9): the main scene hands the terrain the complete
	# world's capture mask, which would lift the photo threefold over the mask's block, so the
	# photo would no longer be the data; render_lift.gd checks the lift.
	terrain.material.set_shader_param("shadow_lift", 1.0)
	# And no highlight from the sun or the sky, no ambient light and a linear tone map: the
	# water's roughness (0.3, the ground's 0.95) changes the highlights unevenly over the view and
	# a filmic curve bends a ratio, so the ratio below would not be the albedo's alone. The photo
	# check reads this view too: its correlation does not depend on the light.
	main.get_node("Sun").light_specular = 0.0
	var environment: Environment = main.get_node("Environment").environment
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	var with_classes := await Common.capture(self)
	Common.save(with_classes, "render_photo_with_classes")
	# The same view with the water class removed and every other class kept: the ratio of the two
	# is the water's alone.
	var classes := surfaces.texture.get_image().get_data()
	var dry := classes.duplicate()
	for i in dry.size():
		if dry[i] == WATER:
			dry[i] = 0
	var dry_image := Image.create_from_data(
		surfaces.columns, surfaces.rows, false, Image.FORMAT_L8, dry
	)
	terrain.material.set_shader_param("surfaces", ImageTexture.create_from_image(dry_image))
	var without_water := await Common.capture(self)
	Common.save(without_water, "render_photo_without_water")
	var samples := _samples(camera, with_classes)
	var ok := _check_photo(samples, with_classes, photo, surfaces)
	ok = _check_classes(samples, with_classes, without_water, surfaces, classes) and ok
	return ok


## The pixels over the terrain with the world point under each: [px, py, x, z].
func _samples(camera: Camera3D, image: Image) -> Array:
	var samples := []
	for py in range(0, image.get_height(), STEP):
		for px in range(0, image.get_width(), STEP):
			var at := Vector2(px + 0.5, py + 0.5)
			var origin := camera.project_ray_origin(at)
			var direction := camera.project_ray_normal(at)
			if direction.y >= -0.01:
				continue
			var p := origin + direction * ((LEVEL - origin.y) / direction.y)
			if p.x < AREA_X.x or p.x > AREA_X.y or p.z < AREA_Z.x or p.z > AREA_Z.y:
				continue
			samples.append([px, py, p.x, p.z])
	return samples


func _check_photo(samples: Array, image: Image, photo: PhotoGrid, surfaces: SurfaceGrid) -> bool:
	# On class 0, inside the photo and off its edge: the photo alone is under test.
	var inside := []
	for s: Array in samples:
		var u: float = (s[2] - photo.x0) / photo.width_m
		var v: float = (s[3] - photo.z0) / photo.depth_m
		if (
			u > PHOTO_MARGIN
			and u < 1.0 - PHOTO_MARGIN
			and v > PHOTO_MARGIN
			and v < 1.0 - PHOTO_MARGIN
			and surfaces.class_at(s[2], s[3]) == 0
		):
			inside.append(s)
	var rendered := PackedFloat64Array()
	for s: Array in inside:
		rendered.append(Common.lum(image.get_pixel(s[0], s[1])))
	var source := photo.texture.get_image()
	var by_x := []
	var by_z := []
	for i in range(-PHOTO_STEPS, PHOTO_STEPS + 1):
		by_x.append(_photo_corr(rendered, inside, photo, source, i * SHIFT_M, 0.0, false, false))
		by_z.append(_photo_corr(rendered, inside, photo, source, 0.0, i * SHIFT_M, false, false))
	var right := _photo_corr(rendered, inside, photo, source, 0.0, 0.0, false, false)
	var north_south := _photo_corr(rendered, inside, photo, source, 0.0, 0.0, true, false)
	var east_west := _photo_corr(rendered, inside, photo, source, 0.0, 0.0, false, true)
	var failures := PackedStringArray()
	if inside.size() < MIN_PHOTO_SAMPLES:
		failures.append("%d samples, %d needed" % [inside.size(), MIN_PHOTO_SAMPLES])
	if right < PHOTO_MIN_CORR:
		failures.append("correlation %.4f below %.2f" % [right, PHOTO_MIN_CORR])
	if north_south >= right:
		failures.append("the photo reads better mirrored north-south (%.4f)" % north_south)
	if east_west >= right:
		failures.append("the photo reads better mirrored east-west (%.4f)" % east_west)
	var better_x := _beaten_by(by_x, PHOTO_STEPS)
	if better_x != 0:
		failures.append("the photo reads as well or better %+.2f m east" % (better_x * SHIFT_M))
	var better_z := _beaten_by(by_z, PHOTO_STEPS)
	if better_z != 0:
		failures.append("the photo reads as well or better %+.2f m south" % (better_z * SHIFT_M))
	print("render photo: correlation by x shift (-0.40 to 0.40 m): %s" % [by_x])
	print("render photo: correlation by z shift (-0.40 to 0.40 m): %s" % [by_z])
	return Common.report(
		"photo",
		failures,
		(
			"correlation %.4f north-south-mirrored %.4f east-west-mirrored %.4f over %d pixels"
			% [right, north_south, east_west, inside.size()]
		)
	)


## The shift, in steps from none, at which [param values] (one value per step from -n to n)
## is the greatest of those not below its value at no shift; 0 when none is.
func _beaten_by(values: Array, n: int) -> int:
	var best := 0
	var best_value: float = values[n]
	for i in values.size():
		if i != n and values[i] >= best_value:
			best = i - n
			best_value = values[i]
	return best


func _check_classes(
	samples: Array,
	with_classes: Image,
	without_water: Image,
	surfaces: SurfaceGrid,
	classes: PackedByteArray
) -> bool:
	# [x, z, ratio] for every sample bright enough without the water, off the terrain's edge.
	var render := []
	for s: Array in samples:
		var dry := Common.lum(without_water.get_pixel(s[0], s[1]))
		if (
			dry >= MIN_LUMINANCE
			and s[2] > AREA_X.x + EDGE_M
			and s[2] < AREA_X.y - EDGE_M
			and s[3] > AREA_Z.x + EDGE_M
			and s[3] < AREA_Z.y - EDGE_M
		):
			render.append([s[2], s[3], Common.lum(with_classes.get_pixel(s[0], s[1])) / dry])
	# The water's full ratio: the median where the data's 1 m box is all water.
	var eased := PackedFloat64Array()
	var full := PackedFloat64Array()
	for r: Array in render:
		var weight := _water_weight(surfaces, classes, r[0], r[1], 2, true)
		eased.append(weight)
		if weight == 1.0:
			full.append(r[2])
	var full_ratio := _median(full)
	# The rendered water weight, 0 dry and 1 where the ratio is the full one; water above 0.5.
	var weights := PackedFloat64Array()
	for r: Array in render:
		var weight: float = (1.0 - r[2]) / maxf(1.0 - full_ratio, 1e-6)
		weights.append(weight)
		r.append(weight > 0.5)
	var total := render.size()
	var shifted_x := PackedInt32Array()
	var shifted_z := PackedInt32Array()
	for i in range(-CLASS_STEPS, CLASS_STEPS + 1):
		var agree_x := 0
		var agree_z := 0
		for r: Array in render:
			if r[3] == (surfaces.class_at(r[0] - i * SHIFT_M, r[1]) == WATER):
				agree_x += 1
			if r[3] == (surfaces.class_at(r[0], r[1] - i * SHIFT_M) == WATER):
				agree_z += 1
		shifted_x.append(agree_x)
		shifted_z.append(agree_z)
	var counts := {"both": 0, "render_only": 0, "data_only": 0, "neither": 0}
	var mirrored := 0
	var mirror_z: float = 2.0 * (surfaces.z0 + surfaces.depth_m / 2.0)
	for r: Array in render:
		var data_water := surfaces.class_at(r[0], r[1]) == WATER
		if r[3] and data_water:
			counts["both"] += 1
		elif r[3]:
			counts["render_only"] += 1
		elif data_water:
			counts["data_only"] += 1
		else:
			counts["neither"] += 1
		if r[3] == (surfaces.class_at(r[0], mirror_z - r[1]) == WATER):
			mirrored += 1
	var bank := _bank(render, weights, surfaces, classes, eased)
	var right: int = shifted_x[CLASS_STEPS]
	var failures := PackedStringArray()
	if total < MIN_CLASS_SAMPLES:
		failures.append("%d samples, %d needed" % [total, MIN_CLASS_SAMPLES])
	if full.size() < MIN_FULL_WATER:
		failures.append("%d samples fully on water, %d needed" % [full.size(), MIN_FULL_WATER])
	if not absf(full_ratio - WATER_ALBEDO) <= WATER_TOLERANCE:
		failures.append(
			"the water renders %.3f of the ground, not %.2f" % [full_ratio, WATER_ALBEDO]
		)
	if right < CLASSES_MIN_AGREE * total:
		failures.append("agreement %d of %d, below %.2f" % [right, total, CLASSES_MIN_AGREE])
	if mirrored >= right:
		failures.append("the data mirrored north-south agrees better (%d)" % mirrored)
	var best_x := _best_class_shift(shifted_x)
	if best_x != 0.0:
		failures.append("best fit at an x shift of the data of %+.2f m" % best_x)
	var best_z := _best_class_shift(shifted_z)
	if best_z != 0.0:
		failures.append("best fit at a z shift of the data of %+.2f m" % best_z)
	failures.append_array(bank["failures"])
	print("render classes: agreement by x shift of the data (-0.30 to 0.30 m): %s" % [shifted_x])
	print("render classes: agreement by z shift of the data (-0.30 to 0.30 m): %s" % [shifted_z])
	return Common.report(
		"classes",
		failures,
		(
			"agreement %d of %d, mirrored %d, water %s; full water %.3f over %d; bank %s over %d"
			% [
				right,
				total,
				mirrored,
				counts,
				full_ratio,
				full.size(),
				bank["correlations"],
				bank["samples"]
			]
		)
	)


## The bank: the rendered water weight against the data's eased weight and its likeliest twins,
## over the samples where any of them lies strictly between 0 and 1. Returns {failures,
## correlations, samples}.
func _bank(
	render: Array,
	weights: PackedFloat64Array,
	surfaces: SurfaceGrid,
	classes: PackedByteArray,
	eased: PackedFloat64Array
) -> Dictionary:
	# Each twin: [half of the box in texels, through the smoothstep].
	var twins := {
		"not eased (the 0.2 m blend)": [0, false],
		"the 1 m box without the smoothstep": [2, false],
		"a 0.6 m box": [1, true],
		"a 1.4 m box": [3, true],
	}
	var expected := {"eased": eased}
	for name: String in twins:
		var values := PackedFloat64Array()
		for r: Array in render:
			values.append(
				_water_weight(surfaces, classes, r[0], r[1], twins[name][0], twins[name][1])
			)
		expected[name] = values
	var on_bank := PackedInt32Array()
	for i in render.size():
		for name: String in expected:
			var w: float = expected[name][i]
			if w > 0.0 and w < 1.0:
				on_bank.append(i)
				break
	var rendered := PackedFloat64Array()
	for i in on_bank:
		rendered.append(weights[i])
	var correlations := {}
	for name: String in expected:
		var values := PackedFloat64Array()
		for i in on_bank:
			values.append(expected[name][i])
		correlations[name] = Common.corr(rendered, values)
	var failures := PackedStringArray()
	if on_bank.size() < MIN_BANK_SAMPLES:
		failures.append("%d samples on the bank, %d needed" % [on_bank.size(), MIN_BANK_SAMPLES])
	if correlations["eased"] < BANK_MIN_CORR:
		failures.append(
			"the bank's correlation %.4f below %.2f" % [correlations["eased"], BANK_MIN_CORR]
		)
	for name: String in twins:
		if correlations[name] >= correlations["eased"]:
			failures.append(
				"the bank reads as well or better %s (%.4f)" % [name, correlations[name]]
			)
	return {"failures": failures, "correlations": correlations, "samples": on_bank.size()}


## The data's water weight at the local point (x, z): the share of water among the
## (2 half + 1)² class texels around it, the boxes of the four nearest texel centres blended
## bilinearly, through smoothstep(0, 1, share) when [param ease]. Half 2 with the ease is the
## shader's water_weight (m4-design §8, brief M4-06); half 0 without it M3's bilinear blend of
## the four nearest texels. Outside the grid: no water.
func _water_weight(
	surfaces: SurfaceGrid, classes: PackedByteArray, x: float, z: float, half: int, ease: bool
) -> float:
	var tx := (x - surfaces.x0) / surfaces.cell_m - 0.5
	var tz := (z - surfaces.z0) / surfaces.cell_m - 0.5
	var c0 := floori(tx)
	var r0 := floori(tz)
	var fx := tx - c0
	var fz := tz - r0
	var share := 0.0
	for j in range(-half, half + 2):
		var r := r0 + j
		if r < 0 or r >= surfaces.rows:
			continue
		var wz := 1.0 - fz if j == -half else (fz if j == half + 1 else 1.0)
		for i in range(-half, half + 2):
			var c := c0 + i
			if c < 0 or c >= surfaces.columns or classes[r * surfaces.columns + c] != WATER:
				continue
			share += (1.0 - fx if i == -half else (fx if i == half + 1 else 1.0)) * wz
	share /= (2 * half + 1) * (2 * half + 1)
	return smoothstep(0.0, 1.0, share) if ease else share


func _median(values: PackedFloat64Array) -> float:
	if values.is_empty():
		return NAN
	var sorted := values.duplicate()
	sorted.sort()
	return sorted[sorted.size() / 2]


## The best shift of the data in metres: 0 when the greatest agreement lies within one step of
## none and above every agreement outside it, else the shift (in metres) of the greatest.
func _best_class_shift(values: PackedInt32Array) -> float:
	var inside := 0
	var outside := 0
	var farthest := 0.0
	for i in values.size():
		var shift := (i - CLASS_STEPS) * SHIFT_M
		if absf(shift) <= SHIFT_M + 1e-9:
			inside = maxi(inside, values[i])
		elif values[i] > outside:
			outside = values[i]
			farthest = shift
	return 0.0 if inside > outside else farthest


## Pearson correlation between the rendered luminance and the luminance of the photo texel the
## data puts under each pixel's world point, the texel looked up after moving the point by
## (dx, dz) metres, with the rows ([param ns_flip]) or the columns ([param ew_flip]) reversed.
func _photo_corr(
	rendered: PackedFloat64Array,
	points: Array,
	photo: PhotoGrid,
	source: Image,
	dx: float,
	dz: float,
	ns_flip: bool,
	ew_flip: bool
) -> float:
	var expected := PackedFloat64Array()
	expected.resize(points.size())
	for i in points.size():
		var col := floori((points[i][2] - dx - photo.x0) / photo.cell_m)
		var row := floori((points[i][3] - dz - photo.z0) / photo.cell_m)
		if ns_flip:
			row = photo.rows - 1 - row
		if ew_flip:
			col = photo.columns - 1 - col
		col = clampi(col, 0, photo.columns - 1)
		row = clampi(row, 0, photo.rows - 1)
		expected[i] = Common.lum(source.get_pixel(col, row))
	return Common.corr(rendered, expected)
