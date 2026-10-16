extends SceneTree
## The gate's render check of where the photo shader puts the photo and the surface classes
## (brief M3-R1-fix-3; docs/reviews/M3-R1-placement.md §M3-R1-P-03, Appendix B). Run by
## tools/gate.sh under xvfb-run, Compatibility renderer (Mesa's llvmpipe), never in GUT.
##
## The complete test world with its terrain replaced by one flat level and its box and trees
## buried under it (render_common.gd), out of the camera's view; the main scene reading it; a
## camera straight above the photo's middle. For every STEP-th pixel the world point under it is
## found by intersecting the pixel's ray with the flat ground, and the rendered pixel is compared
## with what the DATA says is at that point: the photo texel (PhotoGrid's rectangle and decoded
## image) and the surface class (SurfaceGrid's class_at). It reads nothing of the shaders.
##
## Two checks, each one result line (render_common.gd):
## - "photo": the correlation of the rendered luminance with the luminance of the photo texel the
##   data puts under each pixel (on class 0, where the photo alone is drawn) is at least
##   PHOTO_MIN_CORR at no shift and above every alternative: the data moved by 0.05 m steps up
##   to 0.4 m east-west and north-south, mirrored north-south, mirrored east-west.
## - "classes": the water mask (the render with the classes against the render without them,
##   where the ratio is below WATER_RATIO) agrees with class_at on at least CLASSES_MIN_AGREE of
##   the samples, better than with the data mirrored north-south, and its best fit over the
##   shifts of the data is within one 0.05 m step of none, in x and in z.
## The numbers on each line are what a failure points at: the scans tell a flip from a shift
## and a shift's size.
##
## Proves where, not how it looks: not Forward+, not the colour encoding (brain.md H21), not
## the owner's GPU, not any shader on the real village. The flat terrain means the photo is
## seen from above at a place where the terrain's own relief cannot move it.
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
## The classes' water darkens the photo (the shader's water_darken, 0.6): a ratio below this is
## water in the render.
const WATER_RATIO := 0.85
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
	for i in 4:
		await process_frame
	var world := WorldConfig.from_manifest(path)
	var photo := PhotoGrid.from_manifest(path, world)
	var surfaces := SurfaceGrid.from_manifest(path, world)
	var terrain: Terrain3D = main.get_node("Terrain")
	main.get_node("UI/ErrorPanel").hide()
	var camera: FreeFlyCamera = main.get_node("Camera")
	camera.set_view(CAMERA_AT, 0.0, -deg_to_rad(89.0))
	var with_classes := await Common.capture(self)
	Common.save(with_classes, "render_photo_with_classes")
	# The same view with every class removed: the lighting and the photo alone.
	var black := ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_L8))
	terrain.material.set_shader_param("surfaces", black)
	var without_classes := await Common.capture(self)
	Common.save(without_classes, "render_photo_without_classes")
	var samples := _samples(camera, with_classes)
	var ok := _check_photo(samples, with_classes, photo, surfaces)
	ok = _check_classes(samples, with_classes, without_classes, surfaces) and ok
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
	samples: Array, with_classes: Image, without_classes: Image, surfaces: SurfaceGrid
) -> bool:
	# [x, z, water in the render] for every sample bright enough without the classes.
	var render := []
	for s: Array in samples:
		var dark := Common.lum(without_classes.get_pixel(s[0], s[1]))
		if dark >= MIN_LUMINANCE:
			var ratio := Common.lum(with_classes.get_pixel(s[0], s[1])) / dark
			render.append([s[2], s[3], ratio < WATER_RATIO])
	var total := render.size()
	var shifted_x := PackedInt32Array()
	var shifted_z := PackedInt32Array()
	for i in range(-CLASS_STEPS, CLASS_STEPS + 1):
		var agree_x := 0
		var agree_z := 0
		for r: Array in render:
			if r[2] == (surfaces.class_at(r[0] - i * SHIFT_M, r[1]) == 2):
				agree_x += 1
			if r[2] == (surfaces.class_at(r[0], r[1] - i * SHIFT_M) == 2):
				agree_z += 1
		shifted_x.append(agree_x)
		shifted_z.append(agree_z)
	var counts := {"both": 0, "render_only": 0, "data_only": 0, "neither": 0}
	var mirrored := 0
	var mirror_z: float = 2.0 * (surfaces.z0 + surfaces.depth_m / 2.0)
	for r: Array in render:
		var data_water := surfaces.class_at(r[0], r[1]) == 2
		if r[2] and data_water:
			counts["both"] += 1
		elif r[2]:
			counts["render_only"] += 1
		elif data_water:
			counts["data_only"] += 1
		else:
			counts["neither"] += 1
		if r[2] == (surfaces.class_at(r[0], mirror_z - r[1]) == 2):
			mirrored += 1
	var right: int = shifted_x[CLASS_STEPS]
	var failures := PackedStringArray()
	if total < MIN_CLASS_SAMPLES:
		failures.append("%d samples, %d needed" % [total, MIN_CLASS_SAMPLES])
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
	print("render classes: agreement by x shift of the data (-0.30 to 0.30 m): %s" % [shifted_x])
	print("render classes: agreement by z shift of the data (-0.30 to 0.30 m): %s" % [shifted_z])
	return Common.report(
		"classes",
		failures,
		"agreement %d of %d, mirrored %d, water %s" % [right, total, mirrored, counts]
	)


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
