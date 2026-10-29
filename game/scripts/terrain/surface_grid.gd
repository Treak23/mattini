class_name SurfaceGrid
extends RefCounted
## The manifest's surfaces block and its class PNG, checked, decoded and placed in the world
## (docs/SPEC.md §8, the surfaces; CLAUDE.md Hard Rules 2 and 4).
##
## Texel (c, r) is the cell_m square whose north-west corner lies c·cell_m east and
## r·cell_m south of the box's north-west corner, as the photo's: columns run west to east
## (+x), rows north to south (+z), image row 0 is the north edge. Its value is the class of
## that square: 0 none, 1 rock, 2 water, 3 path, 4 road. The rectangle is placed through the
## WorldConfig it is given (to_local of the box's north-west corner), never by subtracting
## an origin here. Every problem is refused with one push_error naming the manifest and a
## null result, never a plausible grid.
##
## The PNG is 8-bit greyscale, which Godot decodes natively to L8; the decoded bytes are the
## classes, kept here for class_at and made into an ImageTexture the shader reads with
## texelFetch (a class value is never filtered).
##
## The flow (brief v0.4.0-02; SPEC §13 row 53): the block's "flow" object describes a second
## PNG on the same box, flow_columns × flow_rows cells of flow_cell_m (2 m), rows north to
## south as the classes', one byte per cell: 0 no stream within 12 m, else code k, the
## downstream bearing (k − 1) × 1.5° clockwise from grid north of the nearest drawn stream
## (the pipeline's surfaces step, brief v0.4.0-01). Its SHA-256 is compared with flow.sha256
## before it is decoded, its decoded bytes with flow.pixels_sha256, and a code above 240 is
## refused. The flow texture is RGB8, one texel per cell: for code k the local direction of
## the LV95 grid bearing, east sin b and north cos b from the world's origin through
## WorldConfig.to_local (64-bit, the one home of the axis mapping), its (x, z) part normalised
## in 64-bit floats, R = round(128 + 127 x), G = round(128 + 127 z), B = 255; code 0 is
## (128, 128, 0). A shader reads (rg · 255 − 128) / 127 · b, so black is no drift. No mipmaps:
## brief v0.4.0-03's shader is to sample it linearly through a hint_default_black sampler (unset,
## it reads black). flow_at gives the same decoded vector of the cell holding a local point.

const FORMAT := "png-l8"
const CELLS := [0.2, 0.5, 1.0]
const CLASSES := {"0": "none", "1": "rock", "2": "water", "3": "path", "4": "road"}
const DATASET := "swisstlm3d"
const DOWNLOAD_COMMAND := "python -m mattini download tlm"
const SURFACES_COMMAND := "python -m mattini surfaces"
## How far columns × cell_m and rows × cell_m may be off the box's sides.
const BOX_TOLERANCE_M := 0.001
## The block's keys; "flow" is the flow grid's description (briefs v0.4.0-01 and -02).
const KEYS := [
	"area",
	"cell_m",
	"classes",
	"columns",
	"file",
	"flow",
	"format",
	"lv95_box",
	"pixels_sha256",
	"rows",
	"sha256",
	"source",
	"world_sha256",
]
const BOX_KEYS := ["e_max", "e_min", "n_max", "n_min"]
const SOURCE_KEYS := ["attribution", "collection", "dataset", "edition", "file", "sha256"]
const FLOW_KEYS := ["cell_m", "columns", "encoding", "file", "pixels_sha256", "rows", "sha256"]
const FLOW_CELLS := [2.0]
const FLOW_ENCODING := "downstream-bearing-1.5deg"
## A flow code's step: code k is the bearing (k − 1) × FLOW_STEP_DEG.
const FLOW_STEP_DEG := 1.5
## The largest flow code (bearing 358.5°); 241 to 255 are never written.
const FLOW_CODES := 240

var area: String
var cell_m: float
var columns: int
var rows: int
## Local x and z of the north-west corner, and the extent along +x and +z in metres.
var x0: float
var z0: float
var width_m: float
var depth_m: float
var dataset: String
var edition: String
var attribution: String
## The classes as an L8 texture, columns × rows, no mipmaps; image row 0 is the north edge.
var texture: ImageTexture
## The flow grid's cell and its column and row counts, from the block's "flow" object.
var flow_cell_m: float
var flow_columns: int
var flow_rows: int
## The flow as an RGB8 texture, flow_columns × flow_rows, no mipmaps; image row 0 is the north
## edge. Nothing draws it yet (brief v0.4.0-03).
var flow_texture: ImageTexture
## The same classes, row-major, rows from the north: byte r·columns + c is texel (c, r).
var _classes: PackedByteArray
## The flow texture's bytes, three per cell, row-major, rows from the north.
var _flow: PackedByteArray


## Reads the surfaces block of the manifest at [param path] and its PNG, placed through
## [param world], which must be read from the same manifest. Returns null and calls
## push_error naming the path on every problem.
static func from_manifest(path: String, world: WorldConfig) -> SurfaceGrid:
	var grid := SurfaceGrid.new()
	var problem := grid._read(path, world)
	if not problem.is_empty():
		push_error("SurfaceGrid: %s: %s" % [path, problem])
		return null
	return grid


## The rectangle the shader's surfaces_rect takes: (x0, z0, width_m, depth_m).
func rect() -> Vector4:
	return Vector4(x0, z0, width_m, depth_m)


## The class (0 to 4) of the texel holding the local point ([param x], [param z]): column
## floor((x − x0) / cell_m), row floor((z − z0) / cell_m). The rectangle is half-open: its
## west and north edges are in, its east and south edges out. Outside it the result is −1.
func class_at(x: float, z: float) -> int:
	var column := floori((x - x0) / cell_m)
	var row := floori((z - z0) / cell_m)
	if column < 0 or row < 0 or column >= columns or row >= rows:
		return -1
	return _classes[row * columns + column]


## The downstream direction, local (x, z), of the flow cell holding the local point
## ([param x], [param z]), decoded from the flow texture's bytes as a shader reads them:
## ((R − 128) / 127, (G − 128) / 127) · B / 255. Column floor((x − x0) / flow_cell_m), row
## floor((z − z0) / flow_cell_m), half-open as class_at; outside the grid and on a cell with no
## stream (code 0) the zero vector.
func flow_at(x: float, z: float) -> Vector2:
	var column := floori((x - x0) / flow_cell_m)
	var row := floori((z - z0) / flow_cell_m)
	if column < 0 or row < 0 or column >= flow_columns or row >= flow_rows:
		return Vector2.ZERO
	var at := 3 * (row * flow_columns + column)
	var mask := _flow[at + 2] / 255.0
	return Vector2((_flow[at] - 128) / 127.0, (_flow[at + 1] - 128) / 127.0) * mask


## Reads and checks everything and fills this object; returns what is wrong, or "".
func _read(path: String, world: WorldConfig) -> String:
	if world == null:
		return "no WorldConfig was given (read it with WorldConfig.from_manifest first)"
	var manifest: Variant = _load_manifest(path)
	if typeof(manifest) == TYPE_STRING:
		return manifest
	var problem := _check_built(manifest)
	if problem.is_empty():
		problem = _check_world(world, manifest.get("world"))
	if problem.is_empty():
		problem = _read_block(manifest["surfaces"])
	if problem.is_empty():
		problem = _place(manifest["surfaces"]["lv95_box"], world)
	if problem.is_empty():
		problem = _read_image(path.get_base_dir(), manifest["surfaces"])
	if problem.is_empty():
		problem = _read_flow(path.get_base_dir(), manifest["surfaces"]["flow"], world)
	return problem


## The manifest as a Dictionary, or what is wrong with it as a String.
static func _load_manifest(path: String) -> Variant:
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		var open_error := FileAccess.get_open_error()
		if open_error == OK:
			return "the manifest is empty"
		return "cannot read the manifest (%s)" % error_string(open_error)
	var json := JSON.new()
	if json.parse(text) != OK:
		return "not valid JSON, line %d: %s" % [json.get_error_line(), json.get_error_message()]
	if typeof(json.data) != TYPE_DICTIONARY:
		return "the manifest is not a JSON object"
	return json.data


## Surfaces were built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var surfaces: Variant = manifest.get("surfaces")
	if surfaces == null:
		return "no surfaces have been built: run %s, then %s" % [DOWNLOAD_COMMAND, SURFACES_COMMAND]
	if typeof(surfaces) != TYPE_DICTIONARY:
		return "surfaces must be an object or null, found %s" % [surfaces]
	if (
		typeof(surfaces.get("world_sha256")) != TYPE_STRING
		or ManifestValue.differs(surfaces["world_sha256"], manifest.get("world_sha256"))
	):
		return (
			(
				"the surfaces were built for another world config (surfaces.world_sha256 %s,"
				% [surfaces.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), SURFACES_COMMAND]
		)
	return ""


## The world given must be this manifest's own, with the owner's axes: the classes are
## defined for x = +e, y = +h, z = −n only (SPEC §8), so a rotated world is refused rather
## than mis-placed.
func _check_world(world: WorldConfig, block: Variant) -> String:
	if typeof(block) != TYPE_DICTIONARY or typeof(block.get("origin_lv95")) != TYPE_DICTIONARY:
		return "the manifest has no world block with an origin"
	var origin: Dictionary = block["origin_lv95"]
	if (
		ManifestValue.differs(origin.get("e"), world.origin_e)
		or ManifestValue.differs(origin.get("n"), world.origin_n)
		or ManifestValue.differs(block.get("height_offset_m"), world.height_offset)
	):
		return "the WorldConfig given was not read from this manifest (its origin differs)"
	var e := world.origin_e
	var n := world.origin_n
	var h := world.height_offset
	var base := world.to_local(e, n, h)
	var east := world.to_local(e + 1.0, n, h) - base
	var north := world.to_local(e, n + 1.0, h) - base
	var up := world.to_local(e, n, h + 1.0) - base
	if east != Vector3.RIGHT or north != Vector3.FORWARD or up != Vector3.UP:
		return (
			"the surfaces need the axes x=+e, y=+h, z=-n; this world maps east to %s," % [east]
			+ " north to %s and up to %s" % [north, up]
		)
	return ""


## Checks the block's own fields and fills area, cell_m, columns, rows, dataset, edition and
## attribution.
func _read_block(surfaces: Dictionary) -> String:
	var problem := _check_labels(surfaces)
	if problem.is_empty():
		problem = _check_size(surfaces)
	if problem.is_empty():
		problem = _check_nested(surfaces)
	if problem.is_empty():
		problem = _check_flow(surfaces["flow"])
	if problem.is_empty():
		var source: Dictionary = surfaces["source"]
		area = surfaces["area"]
		cell_m = float(surfaces["cell_m"])
		columns = int(surfaces["columns"])
		rows = int(surfaces["rows"])
		var flow: Dictionary = surfaces["flow"]
		flow_cell_m = float(flow["cell_m"])
		flow_columns = int(flow["columns"])
		flow_rows = int(flow["rows"])
		dataset = source["dataset"]
		edition = source["edition"]
		attribution = source["attribution"]
	return problem


## The block's key set, its area, its format and its class table.
static func _check_labels(surfaces: Dictionary) -> String:
	if not _has_exactly(surfaces, KEYS):
		return "surfaces must hold exactly the keys %s, found %s" % [KEYS, _sorted_keys(surfaces)]
	if typeof(surfaces["area"]) != TYPE_STRING or surfaces["area"].is_empty():
		return "surfaces.area must be a name, found %s" % [surfaces["area"]]
	if ManifestValue.differs(surfaces["format"], FORMAT):
		return "surfaces.format must be %s, found %s" % [FORMAT, surfaces["format"]]
	if ManifestValue.differs(surfaces["classes"], CLASSES):
		return "surfaces.classes must be %s, found %s" % [CLASSES, surfaces["classes"]]
	return ""


## The block's cell and its column and row counts.
static func _check_size(surfaces: Dictionary) -> String:
	var cell: Variant = surfaces["cell_m"]
	if not _is_number(cell) or float(cell) not in CELLS:
		return "surfaces.cell_m must be 0.2, 0.5 or 1, found %s" % [cell]
	for key in ["columns", "rows"]:
		var count: Variant = surfaces[key]
		# Godot's JSON reads every number as a float: a whole float is a count.
		if not _is_number(count) or float(count) != floorf(count) or count < 1:
			return "surfaces.%s must be a whole number of at least 1, found %s" % [key, count]
	return ""


## The block's source and box, and its two digests.
static func _check_nested(surfaces: Dictionary) -> String:
	for key in ["sha256", "pixels_sha256"]:
		var digest: Variant = surfaces[key]
		if (
			typeof(digest) != TYPE_STRING
			or digest.length() != 64
			or not digest.is_valid_hex_number()
		):
			return "surfaces.%s must be 64 hex digits, found %s" % [key, digest]
	var source: Variant = surfaces["source"]
	if typeof(source) != TYPE_DICTIONARY or not _has_exactly(source, SOURCE_KEYS):
		return "surfaces.source must hold exactly the keys %s, found %s" % [SOURCE_KEYS, source]
	for key in ["attribution", "collection", "edition", "file"]:
		if typeof(source[key]) != TYPE_STRING or source[key].is_empty():
			return "surfaces.source.%s must be text, found %s" % [key, source[key]]
	if ManifestValue.differs(source["dataset"], DATASET):
		return "surfaces.source.dataset must be %s, found %s" % [DATASET, source["dataset"]]
	var box: Variant = surfaces["lv95_box"]
	if typeof(box) != TYPE_DICTIONARY or not _has_exactly(box, BOX_KEYS):
		return "surfaces.lv95_box must hold exactly the keys %s, found %s" % [BOX_KEYS, box]
	for key in BOX_KEYS:
		if not _is_number(box[key]) or not is_finite(float(box[key])):
			return "surfaces.lv95_box.%s must be a finite number, found %s" % [key, box[key]]
	return ""


## The flow object's keys, cell, encoding, counts, file and digests.
static func _check_flow(flow: Variant) -> String:
	if typeof(flow) != TYPE_DICTIONARY or not _has_exactly(flow, FLOW_KEYS):
		return "surfaces.flow must hold exactly the keys %s, found %s" % [FLOW_KEYS, flow]
	var cell: Variant = flow["cell_m"]
	if not _is_number(cell) or float(cell) not in FLOW_CELLS:
		return "surfaces.flow.cell_m must be 2, found %s" % [cell]
	if ManifestValue.differs(flow["encoding"], FLOW_ENCODING):
		return "surfaces.flow.encoding must be %s, found %s" % [FLOW_ENCODING, flow["encoding"]]
	for key in ["columns", "rows"]:
		var count: Variant = flow[key]
		if not _is_number(count) or float(count) != floorf(count) or count < 1:
			return "surfaces.flow.%s must be a whole number of at least 1, found %s" % [key, count]
	if not _is_plain_relative_path(flow["file"]):
		return (
			"surfaces.flow.file must be a plain relative path inside the manifest's folder, found %s"
			% [flow["file"]]
		)
	for key in ["sha256", "pixels_sha256"]:
		var digest: Variant = flow[key]
		if (
			typeof(digest) != TYPE_STRING
			or digest.length() != 64
			or not digest.is_valid_hex_number()
		):
			return "surfaces.flow.%s must be 64 hex digits, found %s" % [key, digest]
	return ""


## Places the grid through the world: column 0, row 0 at the box's north-west corner. The
## box's sides must be columns × cell_m and rows × cell_m.
func _place(box: Dictionary, world: WorldConfig) -> String:
	var wide := float(box["e_max"]) - float(box["e_min"])
	var deep := float(box["n_max"]) - float(box["n_min"])
	var fit_width := columns * cell_m
	var fit_depth := rows * cell_m
	if absf(wide - fit_width) > BOX_TOLERANCE_M or absf(deep - fit_depth) > BOX_TOLERANCE_M:
		return (
			"surfaces.columns and rows (%d × %d) at %s m (%s × %s m) do not fit lv95_box (%s × %s m)"
			% [columns, rows, cell_m, fit_width, fit_depth, wide, deep]
		)
	var flow_width := flow_columns * flow_cell_m
	var flow_depth := flow_rows * flow_cell_m
	if absf(wide - flow_width) > BOX_TOLERANCE_M or absf(deep - flow_depth) > BOX_TOLERANCE_M:
		return (
			(
				"surfaces.flow.columns and rows (%d × %d) at %s m (%s × %s m)"
				% [flow_columns, flow_rows, flow_cell_m, flow_width, flow_depth]
			)
			+ " do not fit lv95_box (%s × %s m)" % [wide, deep]
		)
	var north_west := world.to_local(box["e_min"], box["n_max"], world.height_offset)
	x0 = north_west.x
	z0 = north_west.z
	width_m = fit_width
	depth_m = fit_depth
	return ""


## Checks the PNG's path, presence and SHA-256, then decodes it into the classes.
func _read_image(folder: String, surfaces: Dictionary) -> String:
	var file: Variant = surfaces["file"]
	if not _is_plain_relative_path(file):
		return (
			"surfaces.file must be a plain relative path inside the manifest's folder, found %s"
			% [file]
		)
	var png_path := folder.path_join(file)
	var rebuild := ReleaseBuild.file_hint(SURFACES_COMMAND)
	if not FileAccess.file_exists(png_path):
		return "the class image %s is missing%s" % [png_path, rebuild]
	var data := FileAccess.get_file_as_bytes(png_path)
	var found := _sha256(data)
	if found != surfaces["sha256"].to_lower():
		return (
			"the class image %s has SHA-256 %s, not surfaces.sha256 %s%s"
			% [png_path, found, surfaces["sha256"], rebuild]
		)
	return _make_texture(data, png_path, surfaces["pixels_sha256"].to_lower())


## Decodes the PNG (its SHA-256 already checked) to L8, checks its size and its decoded
## bytes' SHA-256, and keeps the classes and their texture.
func _make_texture(data: PackedByteArray, png_path: String, pixels_sha256: String) -> String:
	var rebuild := ReleaseBuild.file_hint(SURFACES_COMMAND)
	var image := Image.new()
	var decode_error := image.load_png_from_buffer(data)
	if decode_error != OK:
		return (
			"the class image %s cannot be decoded (%s)%s"
			% [png_path, error_string(decode_error), rebuild]
		)
	if image.get_format() != Image.FORMAT_L8 or image.get_size() != Vector2i(columns, rows):
		return (
			"the class image %s decodes to %d × %d pixels of image format %d, not %d × %d of L8 (%d)%s"
			% [
				png_path,
				image.get_width(),
				image.get_height(),
				image.get_format(),
				columns,
				rows,
				Image.FORMAT_L8,
				rebuild
			]
		)
	var pixels := image.get_data()
	var decoded := _sha256(pixels)
	if decoded != pixels_sha256:
		return (
			"the class image %s decodes to bytes with SHA-256 %s, not surfaces.pixels_sha256 %s%s"
			% [png_path, decoded, pixels_sha256, rebuild]
		)
	texture = ImageTexture.create_from_image(image)
	if texture == null:
		return "the class image %s could not be made into a texture" % png_path
	_classes = pixels
	return ""


## Checks the flow PNG's presence and SHA-256, then decodes it (_make_flow).
func _read_flow(folder: String, flow: Dictionary, world: WorldConfig) -> String:
	var png_path := folder.path_join(flow["file"])
	var rebuild := ReleaseBuild.file_hint(SURFACES_COMMAND)
	if not FileAccess.file_exists(png_path):
		return "the flow image %s is missing%s" % [png_path, rebuild]
	var data := FileAccess.get_file_as_bytes(png_path)
	var found := _sha256(data)
	if found != flow["sha256"].to_lower():
		return (
			"the flow image %s has SHA-256 %s, not surfaces.flow.sha256 %s%s"
			% [png_path, found, flow["sha256"], rebuild]
		)
	return _make_flow(data, png_path, flow["pixels_sha256"].to_lower(), world)


## Decodes the flow PNG (its SHA-256 already checked) to L8, checks its size, its decoded bytes'
## SHA-256 and its codes, and keeps the flow's colours and their texture.
func _make_flow(
	data: PackedByteArray, png_path: String, pixels_sha256: String, world: WorldConfig
) -> String:
	var rebuild := ReleaseBuild.file_hint(SURFACES_COMMAND)
	var image := Image.new()
	var decode_error := image.load_png_from_buffer(data)
	if decode_error != OK:
		return (
			"the flow image %s cannot be decoded (%s)%s"
			% [png_path, error_string(decode_error), rebuild]
		)
	if (
		image.get_format() != Image.FORMAT_L8
		or image.get_size() != Vector2i(flow_columns, flow_rows)
	):
		return (
			"the flow image %s decodes to %d × %d pixels of image format %d, not %d × %d of L8 (%d)%s"
			% [
				png_path,
				image.get_width(),
				image.get_height(),
				image.get_format(),
				flow_columns,
				flow_rows,
				Image.FORMAT_L8,
				rebuild
			]
		)
	var pixels := image.get_data()
	var decoded := _sha256(pixels)
	if decoded != pixels_sha256:
		return (
			"the flow image %s decodes to bytes with SHA-256 %s, not surfaces.flow.pixels_sha256 %s%s"
			% [png_path, decoded, pixels_sha256, rebuild]
		)
	var colours := _flow_colours(world)
	var rgb := PackedByteArray()
	rgb.resize(3 * pixels.size())
	for i in pixels.size():
		var code := pixels[i]
		if code > FLOW_CODES:
			return (
				"the flow image %s holds the code %d at column %d, row %d, above %d%s"
				% [png_path, code, i % flow_columns, i / flow_columns, FLOW_CODES, rebuild]
			)
		rgb[3 * i] = colours[3 * code]
		rgb[3 * i + 1] = colours[3 * code + 1]
		rgb[3 * i + 2] = colours[3 * code + 2]
	var flow_image := Image.create_from_data(flow_columns, flow_rows, false, Image.FORMAT_RGB8, rgb)
	flow_texture = ImageTexture.create_from_image(flow_image)
	if flow_texture == null:
		return "the flow image %s could not be made into a texture" % png_path
	_flow = rgb
	return ""


## The flow texture's R, G and B for each code 0 to FLOW_CODES (three bytes per code): code 0
## (128, 128, 0); code k the local (x, z) direction of the LV95 grid bearing
## b = (k − 1) · FLOW_STEP_DEG, east sin b and north cos b from the world's origin through
## [param world] (Hard Rule 4), normalised in 64-bit floats; R = round(128 + 127 x),
## G = round(128 + 127 z), B = 255.
static func _flow_colours(world: WorldConfig) -> PackedByteArray:
	var colours := PackedByteArray([128, 128, 0])
	for k in range(1, FLOW_CODES + 1):
		var bearing := deg_to_rad((k - 1) * FLOW_STEP_DEG)
		var local := world.to_local(
			world.origin_e + sin(bearing), world.origin_n + cos(bearing), world.height_offset
		)
		var x: float = local.x
		var z: float = local.z
		var length := sqrt(x * x + z * z)
		colours.append(roundi(128.0 + 127.0 * x / length))
		colours.append(roundi(128.0 + 127.0 * z / length))
		colours.append(255)
	return colours


static func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256)
	context.update(data)
	return context.finish().hex_encode()


static func _sorted_keys(dictionary: Dictionary) -> Array:
	var keys := dictionary.keys()
	keys.sort()
	return keys


static func _has_exactly(dictionary: Dictionary, keys: Array) -> bool:
	return _sorted_keys(dictionary) == keys


## True for "a/b.png": no scheme, no drive, no backslash, no absolute path, no empty, "."
## or ".." part, so the file cannot lie outside the manifest's folder.
static func _is_plain_relative_path(value: Variant) -> bool:
	if typeof(value) != TYPE_STRING or value.is_empty():
		return false
	if value.is_absolute_path() or value.contains("\\") or value.contains(":"):
		return false
	for part in value.split("/"):
		if part.is_empty() or part == "." or part == "..":
			return false
	return true


static func _is_number(value: Variant) -> bool:
	return typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT
