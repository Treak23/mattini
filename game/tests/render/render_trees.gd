extends SceneTree
## The gate's render check of where the tree shader reads the crowns' colour (brief
## M3-R1-fix-3; docs/reviews/M3-R1-placement.md §M3-R1-P-03, Appendix C). Run by tools/gate.sh
## under xvfb-run, Compatibility renderer (Mesa's llvmpipe), never in GUT.
##
## The complete test world with its terrain replaced by one flat level, its box buried under it
## (render_common.gd), the photo fixture on it, no surface classes, and its trees replaced by 20
## synthetic ones written here (test data, labelled: invented, not swisstopo's, Hard Rule 2),
## each standing at the centre of a block of the photo fixture, in alternate columns, so that
## the block beside it has another colour; a camera straight above. For each tree the mean
## rendered luminance of a disc of CROWN_READ_M about the crown's axis, at CROWN_AXIS_M above the
## foot, is compared with the luminance of the photo (the data) around the tree's position. It
## reads nothing of the shaders.
##
## The disc, not the review's 5 x 5 pixels at the apex (Appendix C): the crown's facets are lit
## one by one since brief M3-R1-fix-4 gave them their normals, so the luminance of a few
## pixels at the apex carries the facet's lighting as noise. The review measured 0.7513 with the
## apex pixels before fix-4 and 0.5824 after it (measured again on this tree, brief M3-R1-fix-3
## Findings); averaged over the disc the right place gives about 0.93 and no wrong place more
## than 0.25.
##
## One check, one result line (render_common.gd): "trees": the correlation of the two over the
## trees is at least TREES_MIN_CORR and above the same correlation with the photo read at a
## wrong place: x and z exchanged, mirrored north-south, mirrored east-west.
##
## Proves where the crowns' colour is read, on 20 synthetic trees: not how a crown looks, not
## the colour encoding (brain.md H21), not Forward+, not the real village's trees.
const CompleteWorld := preload("res://tests/complete_world.gd")
const Common := preload("res://tests/render/render_common.gd")
const COLUMNS := 41
const ROWS := 24
const LEVEL := 605.0
## The photo fixture's blocks: 8 x 8 texels of 0.2 m, 10 across and 5 down.
const BLOCK_M := 1.6
const BLOCKS_ACROSS := 10
const BLOCKS_DOWN := 5
## The photo fixture's rectangle in this world, local x0 and z0 (the complete world's PHOTO_BOX).
const PHOTO_X0 := 1017.0
const PHOTO_Z0 := 11.5
## A tree's height and crown radius, metres: the records' last two floats.
const TREE_HEIGHT_M := 4.0
const TREE_CROWN_M := 0.7
## The crown is read over a disc of this radius, in metres, about its axis at CROWN_AXIS_M above
## the tree's foot: inside the crown, which is 0.7 m wide at its base.
const CROWN_READ_M := 0.4
const CROWN_AXIS_M := 2.0
## The photo under a tree is averaged over this many texels each way from its centre.
const PHOTO_TEXELS := 3
const CAMERA_AT := Vector3(1025.0, LEVEL + 22.0, 15.5)
const TREES_MIN_CORR := 0.6
const WORLD_DIR := "user://render_trees"


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
	# One tree at the centre of every block but the first row's and every other column.
	var trees := PackedFloat32Array()
	for bz in range(1, BLOCKS_DOWN):
		for bx in range(0, BLOCKS_ACROSS, 2):
			trees.append_array(
				PackedFloat32Array(
					[
						PHOTO_X0 + BLOCK_M * (bx + 0.5),
						LEVEL,
						PHOTO_Z0 + BLOCK_M * (bz + 0.5),
						TREE_HEIGHT_M,
						TREE_CROWN_M
					]
				)
			)
	var count := trees.size() / 5
	var chunk := trees.to_byte_array()
	var path := CompleteWorld.write(
		WORLD_DIR,
		func(m: Dictionary) -> void:
			m["terrain"]["sha256"] = CompleteWorld.sha256(bytes)
			Common.bury_buildings(WORLD_DIR, m)
			var file := FileAccess.open(
				WORLD_DIR.path_join(CompleteWorld.TREES_FILE), FileAccess.WRITE
			)
			file.store_buffer(chunk)
			file.close()
			m["trees"]["chunks"] = [
				{
					"file": CompleteWorld.TREES_FILE,
					"sha256": CompleteWorld.sha256(chunk),
					"tile": CompleteWorld.TILE,
					"trees": count
				}
			],
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
	main.get_node("UI/ErrorPanel").hide()
	var terrain: Terrain3D = main.get_node("Terrain")
	# The photo alone under the trees: no classes.
	var black := ImageTexture.create_from_image(Image.create_empty(1, 1, false, Image.FORMAT_L8))
	terrain.material.set_shader_param("surfaces", black)
	var camera: FreeFlyCamera = main.get_node("Camera")
	camera.set_view(CAMERA_AT, 0.0, -deg_to_rad(89.0))
	var image := await Common.capture(self)
	Common.save(image, "render_trees")
	return _compare(image, camera, trees, count, photo)


func _compare(
	image: Image, camera: Camera3D, trees: PackedFloat32Array, count: int, photo: PhotoGrid
) -> bool:
	var source := photo.texture.get_image()
	var rendered := PackedFloat64Array()
	var expected := {
		"right": PackedFloat64Array(),
		"x and z exchanged": PackedFloat64Array(),
		"mirrored north-south": PackedFloat64Array(),
		"mirrored east-west": PackedFloat64Array(),
	}
	for k in count:
		var x := trees[5 * k]
		var z := trees[5 * k + 2]
		rendered.append(_crown_lum(image, camera, Vector3(x, LEVEL + CROWN_AXIS_M, z)))
		expected["right"].append(_photo_lum(source, photo, x, z))
		# Where else the crown's colour might have been read from.
		var swapped_x := photo.x0 + (z - photo.z0) * photo.width_m / photo.depth_m
		var swapped_z := photo.z0 + (x - photo.x0) * photo.depth_m / photo.width_m
		expected["x and z exchanged"].append(_photo_lum(source, photo, swapped_x, swapped_z))
		var north_south := 2.0 * photo.z0 + photo.depth_m - z
		expected["mirrored north-south"].append(_photo_lum(source, photo, x, north_south))
		var east_west := 2.0 * photo.x0 + photo.width_m - x
		expected["mirrored east-west"].append(_photo_lum(source, photo, east_west, z))
	var right := Common.corr(rendered, expected["right"])
	var failures := PackedStringArray()
	if right < TREES_MIN_CORR:
		failures.append("correlation %.4f below %.2f" % [right, TREES_MIN_CORR])
	var others := PackedStringArray()
	for key: String in expected:
		if key == "right":
			continue
		var other := Common.corr(rendered, expected[key])
		others.append("%s %.4f" % [key, other])
		if other >= right:
			failures.append("the crowns read better with the photo %s (%.4f)" % [key, other])
	return Common.report(
		"trees",
		failures,
		"correlation %.4f over %d trees; with the photo read %s" % [right, count, ", ".join(others)]
	)


## The mean luminance of the pixels within CROWN_READ_M, in metres at the crown's axis, of the
## pixel [param axis] projects to.
func _crown_lum(image: Image, camera: Camera3D, axis: Vector3) -> float:
	var centre := camera.unproject_position(axis)
	var radius := centre.distance_to(camera.unproject_position(axis + Vector3(CROWN_READ_M, 0, 0)))
	var total := 0.0
	var n := 0
	var reach := ceili(radius)
	for dy in range(-reach, reach + 1):
		for dx in range(-reach, reach + 1):
			if dx * dx + dy * dy <= radius * radius:
				total += Common.lum(image.get_pixel(int(centre.x) + dx, int(centre.y) + dy))
				n += 1
	return total / n


## The photo's mean luminance over (2 * PHOTO_TEXELS + 1) texels square about the point.
func _photo_lum(source: Image, photo: PhotoGrid, x: float, z: float) -> float:
	var col := floori((x - photo.x0) / photo.cell_m)
	var row := floori((z - photo.z0) / photo.cell_m)
	var total := 0.0
	var n := 0
	for dr in range(-PHOTO_TEXELS, PHOTO_TEXELS + 1):
		for dc in range(-PHOTO_TEXELS, PHOTO_TEXELS + 1):
			var c := clampi(col + dc, 0, photo.columns - 1)
			var r := clampi(row + dr, 0, photo.rows - 1)
			total += Common.lum(source.get_pixel(c, r))
			n += 1
	return total / n
