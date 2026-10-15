class_name PhotoGrid
extends RefCounted
## The manifest's photo block and its JPEG, checked, decoded and placed in the world
## (docs/SPEC.md §8, the photo; CLAUDE.md Hard Rules 2 and 4).
##
## Texel (c, r) is the cell_m square whose north-west corner lies c·cell_m east and
## r·cell_m south of the box's north-west corner: columns run west to east (+x), rows north
## to south (+z), and image row 0 is the north edge. The rectangle is placed through the
## WorldConfig it is given (to_local of the box's north-west corner), never by subtracting
## an origin here; its size is columns·cell_m by rows·cell_m. The shader's uv is
## (world.xz − (x0, z0)) / (width_m, depth_m). Every problem is refused with one push_error
## naming the manifest and a null result, never a plausible photo.
##
## The JPEG is decoded and given mipmaps here, uncompressed: an exported build cannot
## compress an image at runtime (brain.md H21). A texture wider or taller than 16384 texels
## draws black under the Compatibility renderer with no error (H21); the village's 0.2 m
## photo is 10000 × 15000.

const FORMAT := "jpeg"
const CELLS := [0.2, 0.5, 1.0]
const DATASET := "swissimage"
const DOWNLOAD_COMMAND := "python -m mattini download photo"
const PHOTO_COMMAND := "python -m mattini photo"
## How far columns × cell_m and rows × cell_m may be off the box's sides.
const BOX_TOLERANCE_M := 0.001
const KEYS := [
	"area",
	"cell_m",
	"columns",
	"file",
	"format",
	"jpeg",
	"lv95_box",
	"pixels_sha256",
	"rows",
	"sha256",
	"source",
	"world_sha256",
]
const JPEG_KEYS := ["quality", "subsampling"]
const BOX_KEYS := ["e_max", "e_min", "n_max", "n_min"]
const SOURCE_KEYS := ["attribution", "collection", "dataset", "edition", "resolution_m", "tiles"]

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
## The photo, RGB8, columns × rows, with mipmaps; image row 0 is the north edge.
var texture: ImageTexture


## Reads the photo block of the manifest at [param path] and its JPEG, placed through
## [param world], which must be read from the same manifest. Returns null and calls
## push_error naming the path on every problem.
static func from_manifest(path: String, world: WorldConfig) -> PhotoGrid:
	var grid := PhotoGrid.new()
	var problem := grid._read(path, world)
	if not problem.is_empty():
		push_error("PhotoGrid: %s: %s" % [path, problem])
		return null
	return grid


## The rectangle the shader's photo_rect takes: (x0, z0, width_m, depth_m).
func rect() -> Vector4:
	return Vector4(x0, z0, width_m, depth_m)


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
		problem = _read_block(manifest["photo"])
	if problem.is_empty():
		problem = _place(manifest["photo"]["lv95_box"], world)
	if problem.is_empty():
		problem = _read_image(path.get_base_dir(), manifest["photo"])
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


## A photo was built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var photo: Variant = manifest.get("photo")
	if photo == null:
		return "no photo has been built: run %s, then %s" % [DOWNLOAD_COMMAND, PHOTO_COMMAND]
	if typeof(photo) != TYPE_DICTIONARY:
		return "photo must be an object or null, found %s" % [photo]
	if (
		typeof(photo.get("world_sha256")) != TYPE_STRING
		or photo["world_sha256"] != manifest.get("world_sha256")
	):
		return (
			(
				"the photo was built for another world config (photo.world_sha256 %s,"
				% [photo.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), PHOTO_COMMAND]
		)
	return ""


## The world given must be this manifest's own, with the owner's axes: the photo is defined
## for x = +e, y = +h, z = −n only (SPEC §8), so a rotated world is refused rather than
## mis-placed.
func _check_world(world: WorldConfig, block: Variant) -> String:
	if typeof(block) != TYPE_DICTIONARY or typeof(block.get("origin_lv95")) != TYPE_DICTIONARY:
		return "the manifest has no world block with an origin"
	var origin: Dictionary = block["origin_lv95"]
	if (
		origin.get("e") != world.origin_e
		or origin.get("n") != world.origin_n
		or block.get("height_offset_m") != world.height_offset
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
			"the photo needs the axes x=+e, y=+h, z=-n; this world maps east to %s," % [east]
			+ " north to %s and up to %s" % [north, up]
		)
	return ""


## Checks the block's own fields and fills area, cell_m, columns, rows, dataset, edition and
## attribution.
func _read_block(photo: Dictionary) -> String:
	if not _has_exactly(photo, KEYS):
		return "photo must hold exactly the keys %s, found %s" % [KEYS, _sorted_keys(photo)]
	if typeof(photo["area"]) != TYPE_STRING or photo["area"].is_empty():
		return "photo.area must be a name, found %s" % [photo["area"]]
	if photo["format"] != FORMAT:
		return "photo.format must be %s, found %s" % [FORMAT, photo["format"]]
	var cell: Variant = photo["cell_m"]
	if not _is_number(cell) or float(cell) not in CELLS:
		return "photo.cell_m must be 0.2, 0.5 or 1, found %s" % [cell]
	for key in ["columns", "rows"]:
		var count: Variant = photo[key]
		# Godot's JSON reads every number as a float: a whole float is a count.
		if not _is_number(count) or float(count) != floorf(count) or count < 1:
			return "photo.%s must be a whole number of at least 1, found %s" % [key, count]
	var problem := _check_nested(photo)
	if problem.is_empty():
		var source: Dictionary = photo["source"]
		area = photo["area"]
		cell_m = float(cell)
		columns = int(photo["columns"])
		rows = int(photo["rows"])
		dataset = source["dataset"]
		edition = source["edition"]
		attribution = source["attribution"]
	return problem


## The block's JPEG description, source and box, and its two digests.
static func _check_nested(photo: Dictionary) -> String:
	if typeof(photo["jpeg"]) != TYPE_DICTIONARY or not _has_exactly(photo["jpeg"], JPEG_KEYS):
		return "photo.jpeg must hold exactly the keys %s, found %s" % [JPEG_KEYS, photo["jpeg"]]
	for key in ["sha256", "pixels_sha256"]:
		var digest: Variant = photo[key]
		if (
			typeof(digest) != TYPE_STRING
			or digest.length() != 64
			or not digest.is_valid_hex_number()
		):
			return "photo.%s must be 64 hex digits, found %s" % [key, digest]
	var source: Variant = photo["source"]
	if typeof(source) != TYPE_DICTIONARY or not _has_exactly(source, SOURCE_KEYS):
		return "photo.source must hold exactly the keys %s, found %s" % [SOURCE_KEYS, source]
	for key in ["attribution", "collection", "edition"]:
		if typeof(source[key]) != TYPE_STRING or source[key].is_empty():
			return "photo.source.%s must be text, found %s" % [key, source[key]]
	if source["dataset"] != DATASET:
		return "photo.source.dataset must be %s, found %s" % [DATASET, source["dataset"]]
	var box: Variant = photo["lv95_box"]
	if typeof(box) != TYPE_DICTIONARY or not _has_exactly(box, BOX_KEYS):
		return "photo.lv95_box must hold exactly the keys %s, found %s" % [BOX_KEYS, box]
	for key in BOX_KEYS:
		if not _is_number(box[key]) or not is_finite(float(box[key])):
			return "photo.lv95_box.%s must be a finite number, found %s" % [key, box[key]]
	return ""


## Places the photo through the world: column 0, row 0 at the box's north-west corner. The
## box's sides must be columns × cell_m and rows × cell_m.
func _place(box: Dictionary, world: WorldConfig) -> String:
	var wide := float(box["e_max"]) - float(box["e_min"])
	var deep := float(box["n_max"]) - float(box["n_min"])
	var fit_width := columns * cell_m
	var fit_depth := rows * cell_m
	if absf(wide - fit_width) > BOX_TOLERANCE_M or absf(deep - fit_depth) > BOX_TOLERANCE_M:
		return (
			"photo.columns and rows (%d × %d) at %s m (%s × %s m) do not fit lv95_box (%s × %s m)"
			% [columns, rows, cell_m, fit_width, fit_depth, wide, deep]
		)
	var north_west := world.to_local(box["e_min"], box["n_max"], world.height_offset)
	x0 = north_west.x
	z0 = north_west.z
	width_m = fit_width
	depth_m = fit_depth
	return ""


## Checks the JPEG's path, presence and SHA-256, then decodes it into the texture.
func _read_image(folder: String, photo: Dictionary) -> String:
	var file: Variant = photo["file"]
	if not _is_plain_relative_path(file):
		return (
			"photo.file must be a plain relative path inside the manifest's folder, found %s"
			% [file]
		)
	var jpeg_path := folder.path_join(file)
	var rebuild := "; %s rebuilds it" % PHOTO_COMMAND
	if not FileAccess.file_exists(jpeg_path):
		return "the photo %s is missing%s" % [jpeg_path, rebuild]
	var data := FileAccess.get_file_as_bytes(jpeg_path)
	var found := _sha256(data)
	if found != photo["sha256"].to_lower():
		return (
			"the photo %s has SHA-256 %s, not photo.sha256 %s%s"
			% [jpeg_path, found, photo["sha256"], rebuild]
		)
	return _make_texture(data, jpeg_path)


## Decodes the JPEG (its SHA-256 already checked), checks its size and format, and makes the
## texture with mipmaps.
func _make_texture(data: PackedByteArray, jpeg_path: String) -> String:
	var rebuild := "; %s rebuilds it" % PHOTO_COMMAND
	var image := Image.new()
	var decode_error := image.load_jpg_from_buffer(data)
	if decode_error != OK:
		return (
			"the photo %s cannot be decoded (%s)%s"
			% [jpeg_path, error_string(decode_error), rebuild]
		)
	if image.get_format() != Image.FORMAT_RGB8 or image.get_size() != Vector2i(columns, rows):
		return (
			"the photo %s decodes to %d × %d pixels of image format %d, not %d × %d of RGB8 (%d)%s"
			% [
				jpeg_path,
				image.get_width(),
				image.get_height(),
				image.get_format(),
				columns,
				rows,
				Image.FORMAT_RGB8,
				rebuild
			]
		)
	image.generate_mipmaps()
	texture = ImageTexture.create_from_image(image)
	if texture == null:
		return "the photo %s could not be made into a texture" % jpeg_path
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


## True for "a/b.jpg": no scheme, no drive, no backslash, no absolute path, no empty, "."
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
