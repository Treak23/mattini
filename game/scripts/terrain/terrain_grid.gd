class_name TerrainGrid
extends RefCounted
## The manifest's terrain block and its heights file, checked, and placed in the world
## (docs/SPEC.md §8, the terrain grid; CLAUDE.md Hard Rules 2 and 4).
##
## Row r, column c is the vertex at LV95 (e_min + c·s, n_max − r·s), which is local
## x = x_min + c·s, z = z_min + r·s: rows run north to south (+z), columns west to east
## (+x). The grid is placed through the WorldConfig it is given (to_local of the box's
## north-west corner), never by subtracting an origin here. Heights are local y
## (H − height_offset_m) as the pipeline wrote them: 32-bit floats, row-major. Every
## problem is refused with one push_error naming the manifest and a null result, never a
## plausible grid.

const FORMAT := "float32-le"
const SPACINGS := [0.5, 1.0, 2.0]
const TERRAIN_COMMAND := "python -m mattini terrain"
const DOWNLOAD_COMMAND := "python -m mattini download terrain"

var area: String
var spacing_m: float
var columns: int
var rows: int
## Local x of column 0 and local z of row 0: the box's north-west corner.
var x_min: float
var z_min: float
var height_offset_m: float
## columns × rows local heights, row-major, rows along +z.
var heights: PackedFloat32Array
var attribution: String


## Reads the terrain block of the manifest at [param path] and its heights file, placed
## through [param world], which must be read from the same manifest. Returns null and calls
## push_error naming the path on every problem.
static func from_manifest(path: String, world: WorldConfig) -> TerrainGrid:
	var grid := TerrainGrid.new()
	var problem := grid._read(path, world)
	if not problem.is_empty():
		push_error("TerrainGrid: %s: %s" % [path, problem])
		return null
	return grid


## The local height (y) of the vertex at [param column], [param row].
func height(column: int, row: int) -> float:
	return heights[row * columns + column]


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
		problem = _read_block(manifest["terrain"])
	if problem.is_empty():
		problem = _place(manifest["terrain"]["lv95_box"], world)
	if problem.is_empty():
		problem = _read_heights(path.get_base_dir(), manifest["terrain"])
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


## A terrain was built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var terrain: Variant = manifest.get("terrain")
	if terrain == null:
		return "no terrain has been built: run %s, then %s" % [DOWNLOAD_COMMAND, TERRAIN_COMMAND]
	if typeof(terrain) != TYPE_DICTIONARY:
		return "terrain must be an object or null, found %s" % [terrain]
	if (
		typeof(terrain.get("world_sha256")) != TYPE_STRING
		or ManifestValue.differs(terrain["world_sha256"], manifest.get("world_sha256"))
	):
		return (
			(
				"the terrain was built for another world config (terrain.world_sha256 %s,"
				% [terrain.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), TERRAIN_COMMAND]
		)
	return ""


## The world given must be this manifest's own, with the owner's axes: the terrain grid is
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
		return (
			"the WorldConfig given was not read from this manifest"
			+ " (its origin or height offset differs)"
		)
	var e := world.origin_e
	var n := world.origin_n
	var h := world.height_offset
	var base := world.to_local(e, n, h)
	var east := world.to_local(e + 1.0, n, h) - base
	var north := world.to_local(e, n + 1.0, h) - base
	var up := world.to_local(e, n, h + 1.0) - base
	if east != Vector3.RIGHT or north != Vector3.FORWARD or up != Vector3.UP:
		return (
			"the terrain grid needs the axes x=+e, y=+h, z=-n; this world maps east to %s," % [east]
			+ " north to %s and up to %s" % [north, up]
		)
	return ""


## Checks the block's own fields and fills area, spacing_m, columns, rows, attribution.
func _read_block(terrain: Dictionary) -> String:
	if typeof(terrain.get("area")) != TYPE_STRING or terrain["area"].is_empty():
		return "terrain.area must be a name, found %s" % [terrain.get("area")]
	if ManifestValue.differs(terrain.get("format"), FORMAT):
		return "terrain.format must be %s, found %s" % [FORMAT, terrain.get("format")]
	var spacing: Variant = terrain.get("spacing_m")
	if not _is_number(spacing) or float(spacing) not in SPACINGS:
		return "terrain.spacing_m must be 0.5, 1 or 2, found %s" % [spacing]
	for key in ["columns", "rows"]:
		var count: Variant = terrain.get(key)
		# Godot's JSON reads every number as a float: a whole float is a count.
		if not _is_number(count) or float(count) != floorf(count) or count < 1:
			return "terrain.%s must be a whole number of at least 1, found %s" % [key, count]
	var problem := _check_source_and_box(terrain)
	if problem.is_empty():
		area = terrain["area"]
		spacing_m = float(spacing)
		columns = int(terrain["columns"])
		rows = int(terrain["rows"])
		attribution = terrain["source"]["attribution"]
	return problem


static func _check_source_and_box(terrain: Dictionary) -> String:
	var source: Variant = terrain.get("source")
	if (
		typeof(source) != TYPE_DICTIONARY
		or typeof(source.get("attribution")) != TYPE_STRING
		or source["attribution"].is_empty()
	):
		return "terrain.source.attribution must be text, found %s" % [source]
	var box: Variant = terrain.get("lv95_box")
	if typeof(box) != TYPE_DICTIONARY:
		return "terrain.lv95_box must be an object, found %s" % [box]
	for key in ["e_min", "e_max", "n_min", "n_max"]:
		if not _is_number(box.get(key)) or not is_finite(float(box[key])):
			return "terrain.lv95_box.%s must be a finite number, found %s" % [key, box.get(key)]
	return ""


## Places the grid through the world: column 0, row 0 at the box's north-west corner. The
## south-east corner must be the last vertex, and every vertex must sit on Terrain3D's
## vertex lattice (multiples of spacing_m).
func _place(box: Dictionary, world: WorldConfig) -> String:
	var north_west := world.to_local(box["e_min"], box["n_max"], world.height_offset)
	var south_east := world.to_local(box["e_max"], box["n_min"], world.height_offset)
	var fit_columns := (south_east.x - north_west.x) / spacing_m + 1.0
	var fit_rows := (south_east.z - north_west.z) / spacing_m + 1.0
	if fit_columns != columns or fit_rows != rows:
		return (
			"terrain.columns and rows (%d × %d) do not fit lv95_box at %s m (%s × %s)"
			% [columns, rows, spacing_m, fit_columns, fit_rows]
		)
	var lattice_x := north_west.x / spacing_m
	var lattice_z := north_west.z / spacing_m
	if lattice_x != floorf(lattice_x) or lattice_z != floorf(lattice_z):
		return (
			"the grid's first vertex (local x %s, z %s) is not on the %s m vertex lattice"
			% [north_west.x, north_west.z, spacing_m]
		)
	x_min = north_west.x
	z_min = north_west.z
	height_offset_m = world.height_offset
	return ""


## Checks the heights file's path, size and SHA-256, then reads it.
func _read_heights(folder: String, terrain: Dictionary) -> String:
	var file: Variant = terrain.get("file")
	if not _is_plain_relative_path(file):
		return (
			"terrain.file must be a plain relative path inside the manifest's folder, found %s"
			% [file]
		)
	var sha256: Variant = terrain.get("sha256")
	if typeof(sha256) != TYPE_STRING or sha256.length() != 64 or not sha256.is_valid_hex_number():
		return "terrain.sha256 must be 64 hex digits, found %s" % [sha256]
	var heights_path := folder.path_join(file)
	var rebuild := ReleaseBuild.file_hint(TERRAIN_COMMAND)
	if not FileAccess.file_exists(heights_path):
		return "the heights file %s is missing%s" % [heights_path, rebuild]
	var expected_size := columns * rows * 4
	var data := FileAccess.get_file_as_bytes(heights_path)
	if data.size() != expected_size:
		return (
			"the heights file %s holds %d bytes, not %d (%d × %d float32)%s"
			% [heights_path, data.size(), expected_size, columns, rows, rebuild]
		)
	var found := FileAccess.get_sha256(heights_path)
	if found != sha256.to_lower():
		return (
			"the heights file %s has SHA-256 %s, not terrain.sha256 %s%s"
			% [heights_path, found, sha256, rebuild]
		)
	# float32-le: every platform mattini builds for (x86_64) is little-endian.
	heights = data.to_float32_array()
	return ""


## True for "a/b.f32": no scheme, no drive, no backslash, no absolute path, no empty,
## "." or ".." part, so the file cannot lie outside the manifest's folder.
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
