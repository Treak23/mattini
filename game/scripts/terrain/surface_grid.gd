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

const FORMAT := "png-l8"
const CELLS := [0.2, 0.5, 1.0]
const CLASSES := {"0": "none", "1": "rock", "2": "water", "3": "path", "4": "road"}
const DATASET := "swisstlm3d"
const DOWNLOAD_COMMAND := "python -m mattini download tlm"
const SURFACES_COMMAND := "python -m mattini surfaces"
## How far columns × cell_m and rows × cell_m may be off the box's sides.
const BOX_TOLERANCE_M := 0.001
const KEYS := [
	"area",
	"cell_m",
	"classes",
	"columns",
	"file",
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
## The same classes, row-major, rows from the north: byte r·columns + c is texel (c, r).
var _classes: PackedByteArray


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
		var source: Dictionary = surfaces["source"]
		area = surfaces["area"]
		cell_m = float(surfaces["cell_m"])
		columns = int(surfaces["columns"])
		rows = int(surfaces["rows"])
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
	var rebuild := "; %s rebuilds it" % SURFACES_COMMAND
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
	var rebuild := "; %s rebuilds it" % SURFACES_COMMAND
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
