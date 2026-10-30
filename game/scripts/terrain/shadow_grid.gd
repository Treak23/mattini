class_name CaptureShadowGrid
extends RefCounted
## The manifest's shadows block and its mask PNG, checked, decoded and placed in the world
## (docs/SPEC.md §13 row 41; CLAUDE.md Hard Rules 2 and 4; brief v0.5.0-03).
##
## The mask is the 0.5 m L8 PNG of where the 2023 photo lay in shadow when it was flown (the
## pipeline's shadows step): 0 lit, 255 shadow. Texel (c, r) is the cell_m square whose
## north-west corner lies c·cell_m east and r·cell_m south of the box's north-west corner, as
## the photo's and the classes': columns run west to east (+x), rows north to south (+z),
## image row 0 is the north edge. The rectangle is placed through the WorldConfig it is given
## (to_local of the box's north-west corner), never by subtracting an origin here. Every problem
## is refused with one push_error naming the manifest and a null result, never a plausible grid.
##
## The PNG is 8-bit greyscale, which Godot decodes natively to L8; the decoded bytes are kept
## here for value_at (level 0, before any mipmap is made) and made into an ImageTexture with a
## full mip chain, as the photo's texture has one: a 0.5 m binary mask without mipmaps under
## the mipmapped photo would alias in the distance. Which sampler reads the mipmaps is the
## shader's. The sun's two numbers are checked and not kept; nothing reads them.

const FORMAT := "png-l8"
const CELL_M := 0.5
const DATASET := "swisssurface3d"
const DOWNLOAD_COMMAND := "python -m mattini download surface"
const SHADOWS_COMMAND := "python -m mattini shadows"
## How far columns × cell_m and rows × cell_m may be off the box's sides.
const BOX_TOLERANCE_M := 0.001
const KEYS := [
	"area",
	"cell_m",
	"columns",
	"file",
	"format",
	"lv95_box",
	"pixels_sha256",
	"rows",
	"sha256",
	"source",
	"sun",
	"world_sha256",
]
const BOX_KEYS := ["e_max", "e_min", "n_max", "n_min"]
const SOURCE_KEYS := ["attribution", "collection", "dataset", "editions", "entry_sha256"]
const SUN_KEYS := ["azimuth_grid_deg", "elevation_deg", "note"]

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
var editions: PackedStringArray
var attribution: String
## The mask as an L8 texture, columns × rows with a full mip chain; image row 0 is the north
## edge; level 0 is the decoded PNG.
var texture: ImageTexture
## Level 0, row-major, rows from the north: byte r·columns + c is texel (c, r).
var _mask: PackedByteArray


## Reads the shadows block of the manifest at [param path] and its PNG, placed through
## [param world], which must be read from the same manifest. Returns null and calls
## push_error naming the path on every problem.
static func from_manifest(path: String, world: WorldConfig) -> CaptureShadowGrid:
	var grid := CaptureShadowGrid.new()
	var problem := grid._read(path, world)
	if not problem.is_empty():
		push_error("CaptureShadowGrid: %s: %s" % [path, problem])
		return null
	return grid


## The mask's rectangle: (x0, z0, width_m, depth_m).
func rect() -> Vector4:
	return Vector4(x0, z0, width_m, depth_m)


## The byte (0 lit, 255 shadow) of the texel holding the local point ([param x], [param z]):
## column floor((x − x0) / cell_m), row floor((z − z0) / cell_m). The rectangle is half-open:
## its west and north edges are in, its east and south edges out. Outside it the result is −1.
func value_at(x: float, z: float) -> int:
	var column := floori((x - x0) / cell_m)
	var row := floori((z - z0) / cell_m)
	if column < 0 or row < 0 or column >= columns or row >= rows:
		return -1
	return _mask[row * columns + column]


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
		problem = _read_block(manifest["shadows"])
	if problem.is_empty():
		problem = _place(manifest["shadows"]["lv95_box"], world)
	if problem.is_empty():
		problem = _read_image(path.get_base_dir(), manifest["shadows"])
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


## The mask was built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var shadows: Variant = manifest.get("shadows")
	if shadows == null:
		return "no shadows have been built: run %s, then %s" % [DOWNLOAD_COMMAND, SHADOWS_COMMAND]
	if typeof(shadows) != TYPE_DICTIONARY:
		return "shadows must be an object or null, found %s" % [shadows]
	if (
		typeof(shadows.get("world_sha256")) != TYPE_STRING
		or ManifestValue.differs(shadows["world_sha256"], manifest.get("world_sha256"))
	):
		return (
			(
				"the shadows were built for another world config (shadows.world_sha256 %s,"
				% [shadows.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), SHADOWS_COMMAND]
		)
	return ""


## The world given must be this manifest's own, with the owner's axes: the mask is defined
## for x = +e, y = +h, z = −n only (SPEC §8), so a rotated world is refused rather than
## mis-placed. Each of the origin's east and north and the height offset is compared on its own.
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
			"the shadows need the axes x=+e, y=+h, z=-n; this world maps east to %s," % [east]
			+ " north to %s and up to %s" % [north, up]
		)
	return ""


## Checks the block's own fields and fills area, cell_m, columns, rows, dataset, editions and
## attribution.
func _read_block(shadows: Dictionary) -> String:
	var problem := _check_labels(shadows)
	if problem.is_empty():
		problem = _check_size(shadows)
	if problem.is_empty():
		problem = _check_nested(shadows)
	if problem.is_empty():
		var source: Dictionary = shadows["source"]
		area = shadows["area"]
		cell_m = float(shadows["cell_m"])
		columns = int(shadows["columns"])
		rows = int(shadows["rows"])
		dataset = source["dataset"]
		editions = PackedStringArray(source["editions"])
		attribution = source["attribution"]
	return problem


## The block's key set, its area and its format.
static func _check_labels(shadows: Dictionary) -> String:
	if not _has_exactly(shadows, KEYS):
		return "shadows must hold exactly the keys %s, found %s" % [KEYS, _sorted_keys(shadows)]
	if typeof(shadows["area"]) != TYPE_STRING or shadows["area"].is_empty():
		return "shadows.area must be a name, found %s" % [shadows["area"]]
	if ManifestValue.differs(shadows["format"], FORMAT):
		return "shadows.format must be %s, found %s" % [FORMAT, shadows["format"]]
	return ""


## The block's cell and its column and row counts.
static func _check_size(shadows: Dictionary) -> String:
	var cell: Variant = shadows["cell_m"]
	if ManifestValue.differs(cell, CELL_M):
		return "shadows.cell_m must be 0.5, found %s" % [cell]
	for key in ["columns", "rows"]:
		var count: Variant = shadows[key]
		# Godot's JSON reads every number as a float: a whole float is a count.
		if not _is_number(count) or float(count) != floorf(count) or count < 1:
			return "shadows.%s must be a whole number of at least 1, found %s" % [key, count]
	return ""


## The block's digests, source, sun and box.
static func _check_nested(shadows: Dictionary) -> String:
	for key in ["sha256", "pixels_sha256"]:
		var digest: Variant = shadows[key]
		if not _is_digest(digest):
			return "shadows.%s must be 64 hex digits, found %s" % [key, digest]
	var problem := _check_source(shadows["source"])
	if problem.is_empty():
		problem = _check_sun(shadows["sun"])
	if not problem.is_empty():
		return problem
	var box: Variant = shadows["lv95_box"]
	if typeof(box) != TYPE_DICTIONARY or not _has_exactly(box, BOX_KEYS):
		return "shadows.lv95_box must hold exactly the keys %s, found %s" % [BOX_KEYS, box]
	for key in BOX_KEYS:
		if not _is_finite_number(box[key]):
			return "shadows.lv95_box.%s must be a finite number, found %s" % [key, box[key]]
	return ""


static func _check_source(source: Variant) -> String:
	if typeof(source) != TYPE_DICTIONARY or not _has_exactly(source, SOURCE_KEYS):
		return "shadows.source must hold exactly the keys %s, found %s" % [SOURCE_KEYS, source]
	for key in ["attribution", "collection"]:
		if typeof(source[key]) != TYPE_STRING or source[key].is_empty():
			return "shadows.source.%s must be text, found %s" % [key, source[key]]
	if not _is_digest(source["entry_sha256"]):
		return (
			"shadows.source.entry_sha256 must be 64 hex digits, found %s" % [source["entry_sha256"]]
		)
	if ManifestValue.differs(source["dataset"], DATASET):
		return "shadows.source.dataset must be %s, found %s" % [DATASET, source["dataset"]]
	var list: Variant = source["editions"]
	if typeof(list) != TYPE_ARRAY or list.is_empty():
		return "shadows.source.editions must be a non-empty list of texts, found %s" % [list]
	for edition: Variant in list:
		if typeof(edition) != TYPE_STRING or edition.is_empty():
			return "shadows.source.editions must be a non-empty list of texts, found %s" % [list]
	return ""


static func _check_sun(sun: Variant) -> String:
	if typeof(sun) != TYPE_DICTIONARY or not _has_exactly(sun, SUN_KEYS):
		return "shadows.sun must hold exactly the keys %s, found %s" % [SUN_KEYS, sun]
	for key in ["azimuth_grid_deg", "elevation_deg"]:
		if not _is_finite_number(sun[key]):
			return "shadows.sun.%s must be a finite number, found %s" % [key, sun[key]]
	if typeof(sun["note"]) != TYPE_STRING:
		return "shadows.sun.note must be text, found %s" % [sun["note"]]
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
			"shadows.columns and rows (%d × %d) at %s m (%s × %s m) do not fit lv95_box (%s × %s m)"
			% [columns, rows, cell_m, fit_width, fit_depth, wide, deep]
		)
	var north_west := world.to_local(box["e_min"], box["n_max"], world.height_offset)
	x0 = north_west.x
	z0 = north_west.z
	width_m = fit_width
	depth_m = fit_depth
	return ""


## Checks the PNG's path, presence and SHA-256, then decodes it into the mask.
func _read_image(folder: String, shadows: Dictionary) -> String:
	var file: Variant = shadows["file"]
	if not _is_plain_relative_path(file):
		return (
			"shadows.file must be a plain relative path inside the manifest's folder, found %s"
			% [file]
		)
	var png_path := folder.path_join(file)
	var rebuild := ReleaseBuild.file_hint(SHADOWS_COMMAND)
	if not FileAccess.file_exists(png_path):
		return "the mask image %s is missing%s" % [png_path, rebuild]
	var data := FileAccess.get_file_as_bytes(png_path)
	var found := _sha256(data)
	if found != shadows["sha256"].to_lower():
		return (
			"the mask image %s has SHA-256 %s, not shadows.sha256 %s%s"
			% [png_path, found, shadows["sha256"], rebuild]
		)
	return _make_texture(data, png_path, shadows["pixels_sha256"].to_lower())


## Decodes the PNG (its SHA-256 already checked) to L8, checks its size and its decoded
## bytes' SHA-256, keeps level 0 and makes the texture with its mip chain.
func _make_texture(data: PackedByteArray, png_path: String, pixels_sha256: String) -> String:
	var rebuild := ReleaseBuild.file_hint(SHADOWS_COMMAND)
	var image := Image.new()
	var decode_error := image.load_png_from_buffer(data)
	if decode_error != OK:
		return (
			"the mask image %s cannot be decoded (%s)%s"
			% [png_path, error_string(decode_error), rebuild]
		)
	if image.get_format() != Image.FORMAT_L8 or image.get_size() != Vector2i(columns, rows):
		return (
			"the mask image %s decodes to %d × %d pixels of image format %d, not %d × %d of L8 (%d)%s"
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
			"the mask image %s decodes to bytes with SHA-256 %s, not shadows.pixels_sha256 %s%s"
			% [png_path, decoded, pixels_sha256, rebuild]
		)
	image.generate_mipmaps()
	texture = ImageTexture.create_from_image(image)
	if texture == null:
		return "the mask image %s could not be made into a texture" % png_path
	_mask = pixels
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


static func _is_digest(value: Variant) -> bool:
	return typeof(value) == TYPE_STRING and value.length() == 64 and value.is_valid_hex_number()


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


static func _is_finite_number(value: Variant) -> bool:
	return _is_number(value) and is_finite(float(value))
