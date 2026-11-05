class_name SurroundingsGrid
extends RefCounted
## The manifest's surroundings block, its 50 m heights and its 10 m colour, checked, decoded
## and placed in the world (docs/SPEC.md §8; CLAUDE.md Hard Rules 2 and 4; brief v0.6.0-08).
##
## Vertex (c, r) of the heights is the point of lv95_box at E = e_min + c·spacing_m and
## N = n_max − r·spacing_m: columns run west to east (+x), rows north to south (+z). The file
## holds one local height (h − height_offset_m) per vertex, row-major, NaN at the vertices
## strictly inside cut_box, where the near terrain is. The grid is placed through the
## WorldConfig it is given (to_local of the box's north-west corner), never by subtracting an
## origin here. The colour covers lv95_box itself: image row 0 is its north edge, and its
## columns × colour_cell_m and rows × colour_cell_m are the box's sides.
##
## Every problem is refused with one push_error naming the manifest and a null result, never
## a plausible grid. The JPEG is decoded and given mipmaps here, uncompressed: an exported
## build cannot compress an image at runtime (brain.md H21). A texture wider or taller than
## 16384 texels draws black under the Compatibility renderer with no error (H21).
##
## The reader checks the heights only where they are NaN; it does not look at their values or
## at the colour's pixels, whose SHA-256s tie them to the pipeline's steps.

const FORMAT := "f32-le"
const DATASET := "swissaltiregio"
const COLOUR_FORMAT := "jpeg"
const COLOUR_DATASET := "swissimage_far"
const DOWNLOAD_HEIGHTS_COMMAND := "python -m mattini download regio"
const DOWNLOAD_COLOUR_COMMAND := "python -m mattini download farphoto"
const HEIGHTS_COMMAND := "python -m mattini surroundings"
const COLOUR_COMMAND := "python -m mattini farcolour"
## How far colour_columns × colour_cell_m and colour_rows × colour_cell_m may be off the box's
## sides.
const BOX_TOLERANCE_M := 0.001
## The widest and tallest texture the Compatibility renderer draws (brain.md H21).
const MAX_TEXTURE_SIDE := 16384
const HEX_DIGITS := "0123456789abcdefABCDEF"
const KEYS := [
	"area",
	"colour_cell_m",
	"colour_columns",
	"colour_file",
	"colour_format",
	"colour_pixels_sha256",
	"colour_rows",
	"colour_sha256",
	"colour_source",
	"columns",
	"cut_box",
	"file",
	"filled_fraction",
	"format",
	"lv95_box",
	"rows",
	"sha256",
	"source",
	"spacing_m",
	"world_sha256",
]
const SOURCE_KEYS := ["attribution", "collection", "dataset", "edition", "entry_sha256"]
const COLOUR_SOURCE_KEYS := ["attribution", "collection", "dataset", "edition"]
const BOX_KEYS := ["e_max", "e_min", "n_max", "n_min"]
## How every square of the heights is drawn: the one convention of SurroundingsLoader's mesh and
## of height_at, so that the surface the camera rests on is the surface that is drawn (brief
## v0.6.0-12). The corners of a square are numbered 0 the north-west one (a), 1 the north-east
## (b), 2 the south-west (c) and 3 the south-east (d); corner k lies (k & 1) columns east and
## (k >> 1) rows south of the north-west one. The square is the two triangles (a, b, c) and
## (b, d, c), so its diagonal runs from b to c; their front faces are clockwise seen from above
## (brain.md H16).
const SQUARE_TRIANGLES := [[0, 1, 2], [1, 3, 2]]
## How far, in squares, a point may lie off a grid line and still be on it: a point made as
## x_min + c · spacing_m is not always exactly c squares from x_min in 64 bits.
const LINE_TOLERANCE := 1e-9

var area: String
var columns: int
var rows: int
var spacing_m: float
## Local x of column 0 and z of row 0: the box's north-west corner through the WorldConfig.
var x_min: float
var z_min: float
## Local heights (h − height_offset_m), row-major, rows north to south, NaN in the cut.
var heights: PackedFloat32Array
## The area box the heights are cut around, LV95: {e_max, e_min, n_max, n_min}.
var cut_box: Dictionary
var dataset: String
var edition: String
var attribution: String
var colour_cell_m: float
var colour_columns: int
var colour_rows: int
## The share of the colour's pixels that are placeholders, 0 to 1 (the block's own word).
var filled_fraction: float
var colour_dataset: String
var colour_edition: String
var colour_attribution: String
## The colour, RGB8, colour_columns × colour_rows, with mipmaps; image row 0 is the north edge.
var colour_texture: ImageTexture


## Reads the surroundings block of the manifest at [param path], its heights and its colour,
## placed through [param world], which must be read from the same manifest. Returns null and
## calls push_error naming the path on every problem.
static func from_manifest(path: String, world: WorldConfig) -> SurroundingsGrid:
	var grid := SurroundingsGrid.new()
	var problem := grid._read(path, world)
	if not problem.is_empty():
		push_error("SurroundingsGrid: %s: %s" % [path, problem])
		return null
	return grid


## The height of the vertex at [param column], [param row]; NaN in the cut.
func height(column: int, row: int) -> float:
	return heights[row * columns + column]


## The local height of the surface the far terrain is drawn as under local ([param x],
## [param z]), or NaN where nothing is drawn there: outside the box, in the cut, and in a square
## with a NaN corner (SurroundingsLoader draws no triangle there). The square is found from
## x_min, z_min and spacing_m, which the reader took from the WorldConfig: no origin and no LV95
## number is used here (Hard Rule 4). The height is linear between the three corners of the
## triangle of SQUARE_TRIANGLES that holds the point. A point on the line between two squares
## belongs to either of them that is drawn, and the box's last row and column belong to the last
## square (brief v0.6.0-12: the free-fly camera's floor outside the area box).
func height_at(x: float, z: float) -> float:
	var east := (x - x_min) / spacing_m
	var south := (z - z_min) / spacing_m
	# Written so that a NaN, which compares false with everything, ends as NaN.
	var inside := east >= -LINE_TOLERANCE and east <= (columns - 1) + LINE_TOLERANCE
	inside = inside and south >= -LINE_TOLERANCE and south <= (rows - 1) + LINE_TOLERANCE
	if not inside:
		return NAN
	var column_first := clampi(floori(east - LINE_TOLERANCE), 0, columns - 2)
	var column_last := clampi(floori(east + LINE_TOLERANCE), 0, columns - 2)
	var row_first := clampi(floori(south - LINE_TOLERANCE), 0, rows - 2)
	var row_last := clampi(floori(south + LINE_TOLERANCE), 0, rows - 2)
	for row in range(row_first, row_last + 1):
		for column in range(column_first, column_last + 1):
			var found := _square_height(column, row, east - column, south - row)
			if not is_nan(found):
				return found
	return NAN


## The height at ([param u], [param v]) squares east and south of the north-west vertex of the
## square at [param column], [param row] (clamped to the square), or NaN when one of the square's
## four corners is NaN.
func _square_height(column: int, row: int, u: float, v: float) -> float:
	var at := row * columns + column
	var corners := [heights[at], heights[at + 1], heights[at + columns], heights[at + columns + 1]]
	for corner: float in corners:
		if is_nan(corner):
			return NAN
	var east := clampf(u, 0.0, 1.0)
	var south := clampf(v, 0.0, 1.0)
	# The two triangles tile the square: the one the point is most inside of holds it (a point on
	# the diagonal is on both, and both give its height).
	var best := -INF
	var found := NAN
	for triangle: Array in SQUARE_TRIANGLES:
		var weights := _weights(east, south, triangle)
		var worst := minf(weights[0], minf(weights[1], weights[2]))
		if worst > best:
			best = worst
			found = (
				weights[0] * corners[triangle[0]]
				+ weights[1] * corners[triangle[1]]
				+ weights[2] * corners[triangle[2]]
			)
	return found


## The barycentric weights, three floats, of the point ([param u], [param v]) (squares east and
## south of the north-west corner) in the triangle of the square's corners numbered
## [param triangle] (SQUARE_TRIANGLES). All three are 0 or more where the point is on the triangle.
static func _weights(u: float, v: float, triangle: Array) -> Array:
	var x0 := float(triangle[0] & 1)
	var y0 := float(triangle[0] >> 1)
	var x1 := float(triangle[1] & 1)
	var y1 := float(triangle[1] >> 1)
	var x2 := float(triangle[2] & 1)
	var y2 := float(triangle[2] >> 1)
	var span := (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
	var w0 := ((y1 - y2) * (u - x2) + (x2 - x1) * (v - y2)) / span
	var w1 := ((y2 - y0) * (u - x2) + (x0 - x2) * (v - y2)) / span
	return [w0, w1, 1.0 - w0 - w1]


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
	if not problem.is_empty():
		return problem
	var block: Dictionary = manifest["surroundings"]
	problem = _read_block(block)
	if problem.is_empty():
		problem = _read_colour_block(block)
	if problem.is_empty():
		problem = _place(block["lv95_box"], world)
	if problem.is_empty():
		problem = _read_heights(path.get_base_dir(), block)
	if problem.is_empty():
		problem = _read_colour(path.get_base_dir(), block)
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


## Surroundings were built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var block: Variant = manifest.get("surroundings")
	if block == null:
		return (
			"no surroundings have been built: run %s and %s, then %s and %s"
			% [DOWNLOAD_HEIGHTS_COMMAND, DOWNLOAD_COLOUR_COMMAND, HEIGHTS_COMMAND, COLOUR_COMMAND]
		)
	if typeof(block) != TYPE_DICTIONARY:
		return "surroundings must be an object or null, found %s" % [block]
	if (
		typeof(block.get("world_sha256")) != TYPE_STRING
		or ManifestValue.differs(block["world_sha256"], manifest.get("world_sha256"))
	):
		return (
			(
				"the surroundings were built for another world config (surroundings.world_sha256"
				+ (
					" %s, the manifest's %s)"
					% [block.get("world_sha256"), manifest.get("world_sha256")]
				)
			)
			+ ": run %s" % HEIGHTS_COMMAND
		)
	return ""


## The world given must be this manifest's own, with the owner's axes: the grid is defined for
## x = +e, y = +h, z = −n only (SPEC §8), so a rotated world is refused rather than mis-placed.
func _check_world(world: WorldConfig, block: Variant) -> String:
	if typeof(block) != TYPE_DICTIONARY or typeof(block.get("origin_lv95")) != TYPE_DICTIONARY:
		return "the manifest has no world block with an origin"
	var origin: Dictionary = block["origin_lv95"]
	if (
		ManifestValue.differs(origin.get("e"), world.origin_e)
		or ManifestValue.differs(origin.get("n"), world.origin_n)
	):
		return "the WorldConfig given was not read from this manifest (its origin differs)"
	if ManifestValue.differs(block.get("height_offset_m"), world.height_offset):
		return "the WorldConfig given was not read from this manifest (its height offset differs)"
	var e := world.origin_e
	var n := world.origin_n
	var h := world.height_offset
	var base := world.to_local(e, n, h)
	var east := world.to_local(e + 1.0, n, h) - base
	var north := world.to_local(e, n + 1.0, h) - base
	var up := world.to_local(e, n, h + 1.0) - base
	if east != Vector3.RIGHT or north != Vector3.FORWARD or up != Vector3.UP:
		return (
			"the surroundings need the axes x=+e, y=+h, z=-n; this world maps east to %s," % [east]
			+ " north to %s and up to %s" % [north, up]
		)
	return ""


## Checks the block's heights fields and fills area, spacing_m, columns, rows, cut_box,
## dataset, edition and attribution.
func _read_block(block: Dictionary) -> String:
	if not _has_exactly(block, KEYS):
		return "surroundings must hold exactly the keys %s, found %s" % [KEYS, _sorted_keys(block)]
	var problem := _check_source(block["source"])
	for name: String in ["lv95_box", "cut_box"]:
		if problem.is_empty():
			problem = _check_box(block, name)
	if problem.is_empty():
		problem = _check_heights_fields(block)
	if problem.is_empty():
		problem = _check_fit(block)
	if not problem.is_empty():
		return problem
	var source: Dictionary = block["source"]
	area = block["area"]
	spacing_m = float(block["spacing_m"])
	columns = int(block["columns"])
	rows = int(block["rows"])
	cut_box = {}
	for key in BOX_KEYS:
		cut_box[key] = float(block["cut_box"][key])
	dataset = source["dataset"]
	edition = source["edition"]
	attribution = source["attribution"]
	return ""


## The heights' source: its five keys, the dataset and the texts.
static func _check_source(source: Variant) -> String:
	if typeof(source) != TYPE_DICTIONARY or not _has_exactly(source, SOURCE_KEYS):
		return "surroundings.source must hold exactly the keys %s, found %s" % [SOURCE_KEYS, source]
	for key in ["attribution", "collection", "edition", "entry_sha256"]:
		if typeof(source[key]) != TYPE_STRING or source[key].is_empty():
			return "surroundings.source.%s must be text, found %s" % [key, source[key]]
	if ManifestValue.differs(source["dataset"], DATASET):
		return "surroundings.source.dataset must be %s, found %s" % [DATASET, source["dataset"]]
	return ""


## [param name] (lv95_box or cut_box): exactly four finite numbers.
static func _check_box(block: Dictionary, name: String) -> String:
	var box: Variant = block[name]
	if typeof(box) != TYPE_DICTIONARY or not _has_exactly(box, BOX_KEYS):
		return "surroundings.%s must hold exactly the keys %s, found %s" % [name, BOX_KEYS, box]
	for key in BOX_KEYS:
		if not _is_number(box[key]) or not is_finite(float(box[key])):
			return "surroundings.%s.%s must be a finite number, found %s" % [name, key, box[key]]
	return ""


## The area, the format, the spacing, the counts, the digest, and the cut inside the box.
static func _check_heights_fields(block: Dictionary) -> String:
	if typeof(block["area"]) != TYPE_STRING or block["area"].is_empty():
		return "surroundings.area must be a name, found %s" % [block["area"]]
	if ManifestValue.differs(block["format"], FORMAT):
		return "surroundings.format must be %s, found %s" % [FORMAT, block["format"]]
	var spacing: Variant = block["spacing_m"]
	if not _is_number(spacing) or not is_finite(float(spacing)) or float(spacing) <= 0.0:
		return "surroundings.spacing_m must be a positive finite number, found %s" % [spacing]
	for key in ["columns", "rows"]:
		var count: Variant = block[key]
		# Godot's JSON reads every number as a float: a whole float is a count.
		if not _is_number(count) or float(count) != floorf(count) or count < 2:
			return "surroundings.%s must be a whole number of at least 2, found %s" % [key, count]
	if not _is_digest(block["sha256"]):
		return "surroundings.sha256 must be 64 hex digits, found %s" % [block["sha256"]]
	var box: Dictionary = block["lv95_box"]
	var cut: Dictionary = block["cut_box"]
	if (
		float(cut["e_min"]) < float(box["e_min"])
		or float(cut["e_max"]) > float(box["e_max"])
		or float(cut["n_min"]) < float(box["n_min"])
		or float(cut["n_max"]) > float(box["n_max"])
	):
		return "surroundings.cut_box %s does not lie inside lv95_box %s" % [cut, box]
	return ""


## columns and rows are the vertices of lv95_box at spacing_m: (e_max − e_min) / s + 1 and
## (n_max − n_min) / s + 1, in 64 bits.
static func _check_fit(block: Dictionary) -> String:
	var box: Dictionary = block["lv95_box"]
	var s := float(block["spacing_m"])
	var fit_columns := (float(box["e_max"]) - float(box["e_min"])) / s + 1.0
	var fit_rows := (float(box["n_max"]) - float(box["n_min"])) / s + 1.0
	if fit_columns != float(block["columns"]):
		return (
			"surroundings.columns %s does not fit lv95_box: its east-west side holds %s vertices at %s m"
			% [block["columns"], fit_columns, s]
		)
	if fit_rows != float(block["rows"]):
		return (
			"surroundings.rows %s does not fit lv95_box: its north-south side holds %s vertices at %s m"
			% [block["rows"], fit_rows, s]
		)
	return ""


## Checks the colour's own fields (design §2) and fills colour_cell_m, colour_columns,
## colour_rows, filled_fraction, colour_dataset, colour_edition and colour_attribution.
func _read_colour_block(block: Dictionary) -> String:
	if ManifestValue.differs(block["colour_format"], COLOUR_FORMAT):
		return (
			"surroundings.colour_format must be %s, found %s"
			% [COLOUR_FORMAT, block["colour_format"]]
		)
	var cell: Variant = block["colour_cell_m"]
	if not _is_number(cell) or not is_finite(float(cell)) or float(cell) <= 0.0:
		return "surroundings.colour_cell_m must be a positive finite number, found %s" % [cell]
	var problem := _check_colour_size(block, "colour_columns", "e_min", "e_max")
	if problem.is_empty():
		problem = _check_colour_size(block, "colour_rows", "n_min", "n_max")
	if problem.is_empty():
		problem = _check_colour_digests_and_source(block)
	if not problem.is_empty():
		return problem
	var source: Dictionary = block["colour_source"]
	colour_cell_m = float(cell)
	colour_columns = int(block["colour_columns"])
	colour_rows = int(block["colour_rows"])
	filled_fraction = float(block["filled_fraction"])
	colour_dataset = source["dataset"]
	colour_edition = source["edition"]
	colour_attribution = source["attribution"]
	return ""


## [param key] (colour_columns or colour_rows) is a whole number of at least 1 whose pixels of
## colour_cell_m fill the box's side from [param low] to [param high], and no more than the
## renderer draws.
static func _check_colour_size(block: Dictionary, key: String, low: String, high: String) -> String:
	var count: Variant = block[key]
	if not _is_number(count) or float(count) != floorf(count) or count < 1:
		return "surroundings.%s must be a whole number of at least 1, found %s" % [key, count]
	var box: Dictionary = block["lv95_box"]
	var side := float(box[high]) - float(box[low])
	var cell := float(block["colour_cell_m"])
	if absf(float(count) * cell - side) > BOX_TOLERANCE_M:
		return (
			"surroundings.%s (%s) at colour_cell_m %s m (%s m) does not fit the box's side (%s m)"
			% [key, count, cell, float(count) * cell, side]
		)
	if count > MAX_TEXTURE_SIDE:
		return (
			"surroundings.%s is %s, above %d:" % [key, count, MAX_TEXTURE_SIDE]
			+ " the Compatibility renderer draws a wider or taller texture black"
		)
	return ""


## The colour's two digests, its source and its placeholder share.
static func _check_colour_digests_and_source(block: Dictionary) -> String:
	for key in ["colour_sha256", "colour_pixels_sha256"]:
		if not _is_digest(block[key]):
			return "surroundings.%s must be 64 hex digits, found %s" % [key, block[key]]
	var source: Variant = block["colour_source"]
	if typeof(source) != TYPE_DICTIONARY or not _has_exactly(source, COLOUR_SOURCE_KEYS):
		return (
			"surroundings.colour_source must hold exactly the keys %s, found %s"
			% [COLOUR_SOURCE_KEYS, source]
		)
	for key in ["attribution", "collection", "edition"]:
		if typeof(source[key]) != TYPE_STRING or source[key].is_empty():
			return "surroundings.colour_source.%s must be text, found %s" % [key, source[key]]
	if ManifestValue.differs(source["dataset"], COLOUR_DATASET):
		return (
			"surroundings.colour_source.dataset must be %s, found %s"
			% [COLOUR_DATASET, source["dataset"]]
		)
	var fraction: Variant = block["filled_fraction"]
	if (
		not _is_number(fraction)
		or not is_finite(float(fraction))
		or float(fraction) < 0.0
		or float(fraction) > 1.0
	):
		return "surroundings.filled_fraction must be a number from 0 to 1, found %s" % [fraction]
	return ""


## Places the grid through the world: column 0, row 0 at the box's north-west corner.
func _place(box: Dictionary, world: WorldConfig) -> String:
	var north_west := world.to_local(box["e_min"], box["n_max"], world.height_offset)
	x_min = north_west.x
	z_min = north_west.z
	return ""


## Checks the heights file's path, presence, size and SHA-256, reads it, and checks that its
## NaN are exactly the vertices strictly inside cut_box.
func _read_heights(folder: String, block: Dictionary) -> String:
	var file: Variant = block["file"]
	if not _is_plain_relative_path(file):
		return (
			"surroundings.file must be a plain relative path inside the manifest's folder, found %s"
			% [file]
		)
	var heights_path := folder.path_join(file)
	var rebuild := ReleaseBuild.file_hint(HEIGHTS_COMMAND)
	if not FileAccess.file_exists(heights_path):
		return "the heights file %s is missing%s" % [heights_path, rebuild]
	var expected_size := columns * rows * 4
	var data := FileAccess.get_file_as_bytes(heights_path)
	if data.size() != expected_size:
		return (
			"the heights file %s holds %d bytes, not %d (%d × %d float32)%s"
			% [heights_path, data.size(), expected_size, columns, rows, rebuild]
		)
	var found := _sha256(data)
	if found != block["sha256"].to_lower():
		return (
			"the heights file %s has SHA-256 %s, not surroundings.sha256 %s%s"
			% [heights_path, found, block["sha256"], rebuild]
		)
	# float32-le: every platform mattini builds for (x86_64) is little-endian.
	heights = data.to_float32_array()
	return _check_cut(block["lv95_box"], heights_path, rebuild)


## The heights are NaN at the vertices strictly inside cut_box and nowhere else (the edge of
## the cut is kept): vertex (c, r) is at E = e_min + c·s, N = n_max − r·s.
func _check_cut(box: Dictionary, heights_path: String, rebuild: String) -> String:
	var e_min := float(box["e_min"])
	var n_max := float(box["n_max"])
	var cut_e_min := float(cut_box["e_min"])
	var cut_e_max := float(cut_box["e_max"])
	var cut_n_min := float(cut_box["n_min"])
	var cut_n_max := float(cut_box["n_max"])
	var inside_columns := PackedByteArray()
	inside_columns.resize(columns)
	for c in columns:
		var e := e_min + c * spacing_m
		inside_columns[c] = 1 if e > cut_e_min and e < cut_e_max else 0
	var values := heights
	for r in rows:
		var n := n_max - r * spacing_m
		var row_inside: bool = n > cut_n_min and n < cut_n_max
		var row_start := r * columns
		for c in columns:
			var in_cut: bool = row_inside and inside_columns[c] == 1
			var value := values[row_start + c]
			if is_nan(value) == in_cut:
				continue
			var what := (
				"row %d, column %d is finite (%s), inside cut_box" % [r, c, value]
				if in_cut
				else "row %d, column %d is NaN, outside cut_box" % [r, c]
			)
			return (
				"the heights file %s must hold NaN exactly at the vertices strictly inside cut_box: %s%s"
				% [heights_path, what, rebuild]
			)
	return ""


## Checks the colour's path, presence and SHA-256, then decodes it into the texture.
func _read_colour(folder: String, block: Dictionary) -> String:
	var file: Variant = block["colour_file"]
	if not _is_plain_relative_path(file):
		return (
			"surroundings.colour_file must be a plain relative path inside the manifest's folder, found %s"
			% [file]
		)
	var colour_path := folder.path_join(file)
	var rebuild := ReleaseBuild.file_hint(COLOUR_COMMAND)
	if not FileAccess.file_exists(colour_path):
		return "the colour %s is missing%s" % [colour_path, rebuild]
	var data := FileAccess.get_file_as_bytes(colour_path)
	var found := _sha256(data)
	if found != block["colour_sha256"].to_lower():
		return (
			"the colour %s has SHA-256 %s, not surroundings.colour_sha256 %s%s"
			% [colour_path, found, block["colour_sha256"], rebuild]
		)
	return _make_texture(data, colour_path)


## Decodes the JPEG (its SHA-256 already checked), checks its size and format, and makes the
## texture with mipmaps.
func _make_texture(data: PackedByteArray, colour_path: String) -> String:
	var rebuild := ReleaseBuild.file_hint(COLOUR_COMMAND)
	var image := Image.new()
	var decode_error := image.load_jpg_from_buffer(data)
	if decode_error != OK:
		return (
			"the colour %s cannot be decoded (%s)%s"
			% [colour_path, error_string(decode_error), rebuild]
		)
	if (
		image.get_format() != Image.FORMAT_RGB8
		or image.get_size() != Vector2i(colour_columns, colour_rows)
	):
		return (
			"the colour %s decodes to %d × %d pixels of image format %d, not %d × %d of RGB8 (%d)%s"
			% [
				colour_path,
				image.get_width(),
				image.get_height(),
				image.get_format(),
				colour_columns,
				colour_rows,
				Image.FORMAT_RGB8,
				rebuild
			]
		)
	image.generate_mipmaps()
	colour_texture = ImageTexture.create_from_image(image)
	if colour_texture == null:
		return "the colour %s could not be made into a texture" % colour_path
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


## True when [param dictionary] holds exactly [param keys], in any order.
static func _has_exactly(dictionary: Dictionary, keys: Array) -> bool:
	if dictionary.size() != keys.size():
		return false
	for key: String in keys:
		if not dictionary.has(key):
			return false
	return true


## True for exactly 64 characters, each a hex digit. Every character is looked at:
## is_valid_hex_number() alone also takes a leading minus or plus.
static func _is_digest(value: Variant) -> bool:
	if typeof(value) != TYPE_STRING or value.length() != 64:
		return false
	for character: String in value:
		if not HEX_DIGITS.contains(character):
			return false
	return true


## True for "a/b.jpg": no scheme, no drive, no backslash, no absolute path, no empty, "." or
## ".." part, so the file cannot lie outside the manifest's folder.
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
