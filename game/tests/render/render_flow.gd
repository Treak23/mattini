extends SceneTree
## The gate's render check of which way the water's ripples drift (brief v0.5.0-09; the probe of
## brief v0.4.0-03, its Findings and record). Run by tools/gate.sh under xvfb-run, Compatibility
## renderer (Mesa's llvmpipe) with --fixed-fps 60, never in GUT.
##
## The complete test world (complete_world.gd) with its terrain replaced by one flat level, its
## terrain built by TerrainLoader with the world's photo and classes (no capture mask: nothing is
## lifted), the photo replaced by one uniform grey and the neutral colour outside it by the same
## grey, every class texel water, and the flow texture replaced by three bands of the flow grid's
## own columns (its 2 m cells on the SurfaceGrid's rectangle, as the loader places the flow):
## BANDS, each one downstream bearing, encoded as SurfaceGrid encodes a bearing (R = round(128 +
## 127 x), G = round(128 + 127 z), B = 255; x east, z south). The bands hold in the flow grid's
## first BAND_ROWS rows (the northern ones, under the windows); every row south of them holds each
## band's reverse bearing, so a flow read mirrored north-south lands on the reversed bands (the
## grid's rows mirrored put the windows over rows 8 to 13). Test data, invented here (Hard Rule
## 2). One light 20° above the horizon from the bearing 30° (across every band), no highlight, no
## ambient light, a linear tone map, MSAA off, a camera 9 m above the terrain's middle, tilted 89°
## (nearly straight down).
##
## Two frames FRAMES_APART drawn frames apart: with --fixed-fps 60 shader TIME advances exactly
## 1/60 s per drawn frame (brain.md H29), so they are FRAMES_APART / 60 s apart; the check fails
## unless every process step between them was 1/60 s and exactly FRAMES_APART frames were drawn.
## In each band's window (local x from BANDS, z from WINDOW_Z; it must lie between the centres of
## the band's first and last flow column and of the flow grid's first and last band row, where the
## filtered flow is the band's own), the ripple pattern of the first frame is found again in the
## second: the whole-pixel shift, up to SEARCH_PX each way, that maximises the normalised
## cross-correlation of the two frames' luminance, refined by a parabola through its neighbours
## and turned into metres on the ground through the camera's rays. It reads nothing of the
## shaders: the expected direction is the band's flow decoded from the bytes handed to the shader
## as SurfaceGrid says a shader reads them, ((R, G) · 255 − 128) / 127 · B, at the band's first
## column in the flow grid's first row.
##
## One result line, "RENDER flow: PASS|FAIL ..." (render_common.gd): for every band the measured
## shift's direction lies within MAX_ANGLE_DEG of the band's flow, its speed between MIN_SPEED
## and MAX_SPEED m/s (the shader's two ripple maps drift at 0.8 and 0.5 m/s; their sum moves
## between the two), its correlation is at least MIN_CORR, its window holds at least
## MIN_SAMPLES samples, and the first frame's luminance there spreads at least MIN_SPREAD (a
## ripple pattern to follow). The line names, per band, the angle off the flow, the speed, the
## shift in metres, the correlation and the correlation of the frames unmoved.
##
## Proves which way and how fast the rendered ripples move on three synthetic flow bands on a
## flat 20 m test world under Compatibility, over one quarter of a second: not how the water
## looks, not Forward+, not the real village's flow grid or its streams, not that the loader hands
## the SurfaceGrid's own flow (replaced here; test_terrain_loader_surfaces.gd pins it), not the
## crossfade's restarts, the phase field or the TIME rollover (test_m4_06_terrain_look.gd's
## census), not the owner's GPU. It does not see where the flow is read: a north-south shift
## that keeps the windows on band rows passes, and so does an east-west shift within the
## bands. Its data cannot see ripple map b reversed alone (only the MIN_CORR floor) nor a
## dropped validity factor (every test texel has B = 255) (brief v0.5.0-15).
const CompleteWorld := preload("res://tests/complete_world.gd")
const Common := preload("res://tests/render/render_common.gd")
const COLUMNS := 41
const ROWS := 24
const LEVEL := 605.0
const CAMERA_AT := Vector3(1025.0, LEVEL + 9.0, 16.25)
## The photo's grey and the neutral colour's outside it, one value (no static edge in a window).
const GREY := 0.6
## The light's energy: the water renders at about 160 of 255, its ripples spread about 6.
const LIGHT_ENERGY := 4.0
## The light's height above the horizon (degrees): a low light turns the ripples' tilt into
## shading.
const LIGHT_ELEVATION_DEG := 20.0
## The fixed frame rate the gate runs this script at (--fixed-fps 60).
const FPS := 60
## The drawn frames between the two frames compared: 15 at 60 fps is 0.25 s.
const FRAMES_APART := 15
## The flow grid's rows, from the north, that hold the bands; every row after them holds each
## band's reverse bearing. Row r covers local z z0 + 2r to z0 + 2r + 2 (z0 9 here); the terrain
## ends at z 22, inside row 6.
const BAND_ROWS := 7
## The bands, west to east: [name, downstream bearing (degrees clockwise from grid north), the
## flow grid's first and last column, the window's local x from and to (m)]. The flow grid's
## column c covers local x 1013 + 2c to 1015 + 2c; filtered linearly, a band's flow is uniform
## between its first and last column's centres; the terrain spans x 1015 to 1035, z 10.5 to 22.
const BANDS := [
	["east", 90.0, 0, 3, Vector2(1015.6, 1019.6)],
	["north", 0.0, 4, 7, Vector2(1022.4, 1027.6)],
	["south-west", 225.0, 8, 19, Vector2(1030.4, 1034.4)],
]
## Every band's window, local z from and to (m).
const WINDOW_Z := Vector2(11.1, 21.4)
## One pixel in STEP in each direction of a window is a sample.
const STEP := 2
## The shifts searched, whole pixels each way (16 px is about 1.2 m/s over 0.25 s here).
const SEARCH_PX := 16
const MAX_ANGLE_DEG := 5.0
const MIN_SPEED := 0.5
const MAX_SPEED := 1.0
const MIN_CORR := 0.6
const MIN_SAMPLES := 5000
## The least spread (standard deviation, 0 to 255) of the first frame's luminance in a window:
## below it the window shows no ripple pattern to follow.
const MIN_SPREAD := 2.0
const WATER := 2
const WORLD_DIR := "user://render_flow"


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
	var failures := PackedStringArray()
	if grid == null or photo == null or surfaces == null:
		failures.append("the complete world's terrain, photo or classes were refused")
		return Common.report("flow", failures, "no render")
	root.msaa_3d = Viewport.MSAA_DISABLED
	var scene := Node3D.new()
	root.add_child(scene)
	var camera := Camera3D.new()
	scene.add_child(camera)
	camera.position = CAMERA_AT
	camera.rotation = Vector3(-deg_to_rad(89.0), 0.0, 0.0)
	camera.current = true
	var light := DirectionalLight3D.new()
	scene.add_child(light)
	light.rotation = Vector3(-deg_to_rad(LIGHT_ELEVATION_DEG), deg_to_rad(150.0), 0.0)
	light.light_specular = 0.0
	light.light_energy = LIGHT_ENERGY
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color.BLACK
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_DISABLED
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var world_environment := WorldEnvironment.new()
	world_environment.environment = environment
	scene.add_child(world_environment)
	await process_frame
	var terrain := TerrainLoader.create(grid, scene, photo, surfaces)
	var material := terrain.material
	var grey := Image.create_empty(1, 1, false, Image.FORMAT_RGB8)
	grey.fill(Color(GREY, GREY, GREY))
	material.set_shader_param("photo", ImageTexture.create_from_image(grey))
	material.set_shader_param("outside_albedo", Color(GREY, GREY, GREY))
	var water := PackedByteArray()
	water.resize(surfaces.columns * surfaces.rows)
	water.fill(WATER)
	material.set_shader_param(
		"surfaces",
		ImageTexture.create_from_image(
			Image.create_from_data(surfaces.columns, surfaces.rows, false, Image.FORMAT_L8, water)
		)
	)
	var flow := _band_flow(surfaces.flow_columns, surfaces.flow_rows)
	material.set_shader_param(
		"water_flow",
		ImageTexture.create_from_image(
			Image.create_from_data(
				surfaces.flow_columns, surfaces.flow_rows, false, Image.FORMAT_RGB8, flow
			)
		)
	)
	var first := await Common.capture(self)
	var first_frame := Engine.get_frames_drawn()
	var steps := PackedFloat64Array()
	for i in FRAMES_APART:
		await process_frame
		steps.append(root.get_process_delta_time())
	await RenderingServer.frame_post_draw
	var second := root.get_texture().get_image()
	var drawn := Engine.get_frames_drawn() - first_frame
	Common.save(first, "render_flow_first")
	Common.save(second, "render_flow_second")
	for step in steps:
		if absf(step - 1.0 / FPS) > 1e-9:
			failures.append(
				"a process step of %.6f s, not 1/%d s: run with --fixed-fps %d" % [step, FPS, FPS]
			)
			break
	if drawn != FRAMES_APART:
		failures.append("%d frames drawn between the two, not %d" % [drawn, FRAMES_APART])
	return _compare(camera, first, second, flow, surfaces, failures)


## The flow texture's bytes: in the first BAND_ROWS rows each column its band's bearing, in every
## row after them its reverse, each encoded as SurfaceGrid encodes one (local x east, z south).
func _band_flow(columns: int, rows: int) -> PackedByteArray:
	var out := PackedByteArray()
	for r in rows:
		var turn := 0.0 if r < BAND_ROWS else 180.0
		var row := PackedByteArray()
		row.resize(3 * columns)
		for column in columns:
			var bearing := deg_to_rad(_band_of(column)[1] + turn)
			row[3 * column] = roundi(128.0 + 127.0 * sin(bearing))
			row[3 * column + 1] = roundi(128.0 - 127.0 * cos(bearing))
			row[3 * column + 2] = 255
		out.append_array(row)
	return out


func _band_of(column: int) -> Array:
	for band: Array in BANDS:
		if column >= band[2] and column <= band[3]:
			return band
	return BANDS[BANDS.size() - 1]


func _compare(
	camera: Camera3D,
	first: Image,
	second: Image,
	flow: PackedByteArray,
	surfaces: SurfaceGrid,
	failures: PackedStringArray
) -> bool:
	var width := first.get_width()
	var a := _luminance(first)
	var b := _luminance(second)
	var seconds := float(FRAMES_APART) / FPS
	var parts := PackedStringArray()
	# The windows inside the band rows' uniform flow: between the first and last band row's centres.
	var rows_from: float = surfaces.z0 + 0.5 * surfaces.flow_cell_m
	var rows_to: float = surfaces.z0 + (BAND_ROWS - 0.5) * surfaces.flow_cell_m
	if WINDOW_Z.x < rows_from or WINDOW_Z.y > rows_to:
		failures.append("the windows leave the band rows' uniform flow")
	for band: Array in BANDS:
		# The band's flow as the shader decodes it: (rg * 255 - 128) / 127 * b, at its first column
		# in the first row (a band row).
		var at := 3 * int(band[2])
		var expected := Vector2((flow[at] - 128) / 127.0, (flow[at + 1] - 128) / 127.0)
		expected *= flow[at + 2] / 255.0
		# The window inside the band's uniform flow: between its first and last column's centres.
		var uniform_from: float = surfaces.x0 + (band[2] + 0.5) * surfaces.flow_cell_m
		var uniform_to: float = surfaces.x0 + (band[3] + 0.5) * surfaces.flow_cell_m
		if band[4].x < uniform_from or band[4].y > uniform_to:
			failures.append("%s: the window leaves the band's uniform flow" % band[0])
		var samples := PackedInt32Array()
		var centre := Vector2.ZERO
		for py in range(SEARCH_PX + 1, first.get_height() - SEARCH_PX - 1, STEP):
			for px in range(SEARCH_PX + 1, width - SEARCH_PX - 1, STEP):
				var p := _ground(camera, Vector2(px + 0.5, py + 0.5))
				if (
					p.x >= band[4].x
					and p.x <= band[4].y
					and p.y >= WINDOW_Z.x
					and p.y <= WINDOW_Z.y
				):
					samples.append(py * width + px)
					centre += Vector2(px, py)
		if samples.size() < MIN_SAMPLES:
			failures.append("%s: %d samples, %d needed" % [band[0], samples.size(), MIN_SAMPLES])
			parts.append("%s no samples" % band[0])
			continue
		centre /= samples.size()
		var spread := _spread(a, samples)
		print("render flow: %s: the first frame's luminance spread %.2f" % [band[0], spread])
		if spread < MIN_SPREAD:
			failures.append(
				(
					"%s: no ripple pattern (luminance spread %.2f below %.1f)"
					% [band[0], spread, MIN_SPREAD]
				)
			)
		var found := _best_shift(a, b, samples, width)
		var shift: Vector2 = found[0]
		var here := _ground(camera, centre + Vector2(0.5, 0.5))
		var there := _ground(camera, centre + Vector2(0.5, 0.5) + shift)
		var moved := there - here
		var speed := moved.length() / seconds
		var off := rad_to_deg(expected.angle_to(moved))
		if absf(off) > MAX_ANGLE_DEG:
			failures.append("%s: %+.1f° off the flow" % [band[0], off])
		if speed < MIN_SPEED or speed > MAX_SPEED:
			failures.append("%s: %.2f m/s" % [band[0], speed])
		if found[1] < MIN_CORR:
			failures.append("%s: correlation %.3f below %.2f" % [band[0], found[1], MIN_CORR])
		parts.append(
			(
				(
					"%s %+.1f° off at %.2f m/s (shift %+.3f m east %+.3f m south, correlation %.3f,"
					% [band[0], off, speed, moved.x, moved.y, found[1]]
				)
				+ " unmoved %.3f, %d samples)" % [found[2], samples.size()]
			)
		)
	return Common.report(
		"flow",
		failures,
		(
			(
				"the ripples' shift in %.2f s (%d frames at %d fps) against each band's flow: %s;"
				% [seconds, FRAMES_APART, FPS, ", ".join(parts)]
			)
			+ (" allowed %.0f° off and %.2f to %.2f m/s" % [MAX_ANGLE_DEG, MIN_SPEED, MAX_SPEED])
		)
	)


## The local (x, z) of the flat ground under the pixel at [param at].
func _ground(camera: Camera3D, at: Vector2) -> Vector2:
	var origin := camera.project_ray_origin(at)
	var direction := camera.project_ray_normal(at)
	var p := origin + direction * ((LEVEL - origin.y) / direction.y)
	return Vector2(p.x, p.z)


func _luminance(image: Image) -> PackedFloat32Array:
	var out := PackedFloat32Array()
	out.resize(image.get_width() * image.get_height())
	var i := 0
	for y in image.get_height():
		for x in image.get_width():
			out[i] = Common.lum(image.get_pixel(x, y))
			i += 1
	return out


## The standard deviation of [param values] over [param samples].
func _spread(values: PackedFloat32Array, samples: PackedInt32Array) -> float:
	var sum := 0.0
	var squares := 0.0
	for i in samples:
		sum += values[i]
		squares += values[i] * values[i]
	var mean := sum / samples.size()
	return sqrt(maxf(squares / samples.size() - mean * mean, 0.0))


## [shift in pixels (sub-pixel), its correlation, the correlation at no shift].
func _best_shift(
	a: PackedFloat32Array, b: PackedFloat32Array, samples: PackedInt32Array, width: int
) -> Array:
	var n := SEARCH_PX * 2 + 1
	var table := PackedFloat64Array()
	table.resize(n * n)
	var sa := 0.0
	var saa := 0.0
	for i in samples:
		sa += a[i]
		saa += a[i] * a[i]
	var count := samples.size()
	var best := 0
	for j in n:
		for k in n:
			var offset := (j - SEARCH_PX) * width + (k - SEARCH_PX)
			var sb := 0.0
			var sbb := 0.0
			var sab := 0.0
			for i in samples:
				var v := b[i + offset]
				sb += v
				sbb += v * v
				sab += a[i] * v
			var cov := sab - sa * sb / count
			var var_a := saa - sa * sa / count
			var var_b := sbb - sb * sb / count
			table[j * n + k] = cov / sqrt(maxf(var_a * var_b, 1e-12))
			if table[j * n + k] > table[best]:
				best = j * n + k
	var bj := best / n
	var bk := best % n
	var fx := float(bk - SEARCH_PX)
	var fy := float(bj - SEARCH_PX)
	if bk > 0 and bk < n - 1:
		fx += _vertex(table[bj * n + bk - 1], table[best], table[bj * n + bk + 1])
	if bj > 0 and bj < n - 1:
		fy += _vertex(table[(bj - 1) * n + bk], table[best], table[(bj + 1) * n + bk])
	return [Vector2(fx, fy), table[best], table[SEARCH_PX * n + SEARCH_PX]]


## The offset (-0.5 to 0.5) of the vertex of the parabola through three equally spaced values.
func _vertex(left: float, middle: float, right: float) -> float:
	var curve := left - 2.0 * middle + right
	if curve >= 0.0:
		return 0.0
	return clampf(0.5 * (left - right) / curve, -0.5, 0.5)
