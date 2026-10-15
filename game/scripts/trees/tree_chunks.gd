class_name TreeChunks
extends RefCounted
## The manifest's trees block and its chunk files, checked (docs/SPEC.md §8, the trees;
## CLAUDE.md Hard Rules 2 and 4).
##
## Each chunk file holds one record per tree, no header: x, y, z, height_m and
## crown_radius_m as little-endian float32 (20 bytes). x, y and z are the local coordinates
## of the tree's base, which the pipeline computed for the world config that the block's
## world_sha256 pins; this reader never converts a coordinate. It ties the block to its
## manifest instead: the block's world_sha256 must be the manifest's, the WorldConfig given
## must be the manifest's own (BuildingChunks' check: its origin, height offset and axes map
## one metre east, north and up as a WorldConfig read from the manifest does), and its axes
## must be the owner's, x = +e, y = +h, z = -n, the only ones the trees' base heights are
## defined for (Hard Rule 4). Every problem is refused with one push_error naming the
## manifest and a null result, never a plausible set of trees. When WorldConfig itself
## refuses the manifest's world block, its own push_error comes first.
##
## The trees are a generic conifer's places and sizes: the data holds no species. `dataset`
## and `edition` name the surface model the heights were measured on; its tiles may have
## been flown in different years, so `edition` is the first and last of the editions the
## tiles use (the block's own `editions` list is the datasets config's, not the tiles').

const FORMAT := "trees-f32x5-le"
const DATASET := "swisssurface3d"
const TREES_COMMAND := "python -m mattini trees"
## Bytes per tree: x, y, z, height_m, crown_radius_m as float32.
const TREE_BYTES := 20
## The most trees a chunk may hold: its size must fit an int32.
const MAX_COUNT := 107374182
const BLOCK_KEYS := ["area", "chunks", "format", "lv95_box", "parameters", "source", "world_sha256"]
const CHUNK_KEYS := ["file", "sha256", "tile", "trees"]
const BOX_KEYS := ["e_max", "e_min", "n_max", "n_min"]
const PARAMETER_KEYS := [
	"building_margin_m",
	"crown_radius",
	"max_height_m",
	"max_slope_deg",
	"min_height_m",
	"smoothing",
	"window",
]
## The block's source: the four datasets the trees were derived from, each its own block.
const SOURCE_KEYS := ["swissalti3d", "swissbuildings3d", "swisssurface3d", "swisstlm3d"]
const SURFACE_KEYS := ["attribution", "collection", "dataset", "editions", "resolution_m", "tiles"]
const SURFACE_TILE_KEYS := ["edition", "sha256", "tile"]

var area: String
var dataset: String
var edition: String
var attribution: String
## One Dictionary per chunk, in the block's order: {"tile": String, "trees": int,
## "positions": PackedVector3Array (local x, y, z of each tree's base), "heights":
## PackedFloat32Array (metres), "radii": PackedFloat32Array (crown radius, metres)}.
var chunks: Array[Dictionary] = []


## Reads the trees block of the manifest at [param path] and its chunk files, checked
## against [param world], which must be read from the same manifest. Returns null and calls
## push_error naming the path on every problem.
static func from_manifest(path: String, world: WorldConfig) -> TreeChunks:
	var result := TreeChunks.new()
	var problem := result._read(path, world)
	if not problem.is_empty():
		push_error("TreeChunks: %s: %s" % [path, problem])
		return null
	return result


## Reads and checks everything and fills this object; returns what is wrong, or "".
func _read(path: String, world: WorldConfig) -> String:
	if world == null:
		return "no WorldConfig was given (read it with WorldConfig.from_manifest first)"
	# The manifest and the path rule are read as TerrainGrid reads them: one home for each.
	var manifest: Variant = TerrainGrid._load_manifest(path)
	if typeof(manifest) == TYPE_STRING:
		return manifest
	var problem := _check_built(manifest)
	if problem.is_empty():
		problem = _check_world(world, path, manifest.get("world"))
	if problem.is_empty():
		problem = _read_block(manifest["trees"])
	if problem.is_empty():
		problem = _read_chunks(path.get_base_dir(), manifest["trees"]["chunks"])
	return problem


## Trees were built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var block: Variant = manifest.get("trees")
	if block == null:
		return "no trees have been built: run %s" % TREES_COMMAND
	if typeof(block) != TYPE_DICTIONARY:
		return "trees must be an object or null, found %s" % [block]
	if (
		typeof(block.get("world_sha256")) != TYPE_STRING
		or block["world_sha256"] != manifest.get("world_sha256")
	):
		return (
			(
				"the trees were built for another world config (trees.world_sha256 %s,"
				% [block.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), TREES_COMMAND]
		)
	return ""


## The WorldConfig given must be this manifest's own (BuildingChunks' check, the one home of
## it) and must have the owner's axes: a base height and a position are defined for x = +e,
## y = +h, z = -n only, so a rotated world is refused rather than mis-placed. Returns what
## differs, or "".
static func _check_world(world: WorldConfig, path: String, block: Variant) -> String:
	var problem := BuildingChunks._check_world(world, path, block)
	if not problem.is_empty():
		return problem
	var e := world.origin_e
	var n := world.origin_n
	var h := world.height_offset
	var base := world.to_local(e, n, h)
	var east := world.to_local(e + 1.0, n, h) - base
	var north := world.to_local(e, n + 1.0, h) - base
	var up := world.to_local(e, n, h + 1.0) - base
	if east != Vector3.RIGHT or north != Vector3.FORWARD or up != Vector3.UP:
		return (
			"the trees need the axes x=+e, y=+h, z=-n; this world maps east to %s," % [east]
			+ " north to %s and up to %s" % [north, up]
		)
	return ""


## Checks the block's own fields and fills area, dataset, edition and attribution.
func _read_block(block: Dictionary) -> String:
	var keys: Array = block.keys()
	keys.sort()
	if keys != BLOCK_KEYS:
		return "trees must have exactly the keys %s, found %s" % [BLOCK_KEYS, keys]
	if block["format"] != FORMAT:
		return "trees.format must be %s, found %s" % [FORMAT, block["format"]]
	if not _is_text(block["area"]):
		return "trees.area must be a name, found %s" % [block["area"]]
	var problem := _check_box(block["lv95_box"])
	if problem.is_empty():
		problem = _check_keys(block["parameters"], PARAMETER_KEYS, "trees.parameters")
	if problem.is_empty():
		problem = _check_source(block["source"])
	if not problem.is_empty():
		return problem
	var entries: Variant = block["chunks"]
	if typeof(entries) != TYPE_ARRAY or entries.is_empty():
		return "trees.chunks must be a list of chunks, found %s" % [entries]
	var surface: Dictionary = block["source"][DATASET]
	area = block["area"]
	dataset = surface["dataset"]
	attribution = surface["attribution"]
	edition = _edition_of(surface["tiles"])
	return ""


## [param value] is an object with exactly the keys [param keys] (sorted), or what is wrong.
static func _check_keys(value: Variant, keys: Array, where: String) -> String:
	if typeof(value) != TYPE_DICTIONARY:
		return "%s must be an object, found %s" % [where, value]
	var found: Array = value.keys()
	found.sort()
	if found != keys:
		return "%s must have exactly the keys %s, found %s" % [where, keys, found]
	return ""


static func _check_box(box: Variant) -> String:
	var problem := _check_keys(box, BOX_KEYS, "trees.lv95_box")
	if not problem.is_empty():
		return problem
	for key in BOX_KEYS:
		if not _is_number(box[key]) or not is_finite(float(box[key])):
			return "trees.lv95_box.%s must be a finite number, found %s" % [key, box[key]]
	return ""


## The source is the four datasets' blocks; swisssurface3d's is the one the game reads: its
## attribution, and the editions of its tiles.
static func _check_source(source: Variant) -> String:
	var problem := _check_keys(source, SOURCE_KEYS, "trees.source")
	if not problem.is_empty():
		return problem
	for name: String in SOURCE_KEYS:
		if typeof(source[name]) != TYPE_DICTIONARY or source[name].get("dataset") != name:
			return "trees.source.%s must be the %s block, found %s" % [name, name, source[name]]
	var surface: Dictionary = source[DATASET]
	problem = _check_keys(surface, SURFACE_KEYS, "trees.source.%s" % DATASET)
	if not problem.is_empty():
		return problem
	if not _is_text(surface["attribution"]):
		return (
			"trees.source.%s.attribution must be text, found %s" % [DATASET, surface["attribution"]]
		)
	var tiles: Variant = surface["tiles"]
	if typeof(tiles) != TYPE_ARRAY or tiles.is_empty():
		return "trees.source.%s.tiles must be a list of tiles, found %s" % [DATASET, tiles]
	for i in tiles.size():
		var where := "trees.source.%s.tiles[%d]" % [DATASET, i]
		problem = _check_keys(tiles[i], SURFACE_TILE_KEYS, where)
		if not problem.is_empty():
			return problem
		if not _is_text(tiles[i]["edition"]):
			return "%s.edition must be text, found %s" % [where, tiles[i]["edition"]]
		if not _is_tile(tiles[i]["tile"]):
			return "%s.tile must be a tile id like 2600-1200, found %s" % [where, tiles[i]["tile"]]
		if not _is_sha256(tiles[i]["sha256"]):
			return "%s.sha256 must be 64 hex digits, found %s" % [where, tiles[i]["sha256"]]
	return ""


## The first and last of the distinct editions of [param tiles], joined by "-", or the one
## edition they all share. Editions are years: they sort as text.
static func _edition_of(tiles: Array) -> String:
	var distinct := {}
	for tile: Dictionary in tiles:
		distinct[tile["edition"]] = true
	var editions := distinct.keys()
	editions.sort()
	if editions.size() == 1:
		return editions[0]
	return "%s-%s" % [editions[0], editions[editions.size() - 1]]


## Checks every chunk entry, then reads its file; fills chunks in the block's order.
func _read_chunks(folder: String, entries: Array) -> String:
	var tiles := {}
	for i in entries.size():
		var problem := _check_entry(entries[i], i)
		if not problem.is_empty():
			return problem
		var tile: String = entries[i]["tile"]
		if tiles.has(tile):
			return "trees.chunks[%d]: the tile %s has a chunk already" % [i, tile]
		tiles[tile] = true
	for entry: Dictionary in entries:
		var problem := _read_chunk(folder, entry)
		if not problem.is_empty():
			return problem
	return ""


## An entry is exactly {file, sha256, tile, trees}: a whole count of at least 1, a tile id
## "<e_km>-<n_km>", 64 hex digits and a plain relative path.
static func _check_entry(entry: Variant, i: int) -> String:
	var where := "trees.chunks[%d]" % i
	var problem := _check_keys(entry, CHUNK_KEYS, where)
	if not problem.is_empty():
		return problem
	var tile: Variant = entry["tile"]
	if not _is_tile(tile):
		return "%s.tile must be a tile id like 2600-1200, found %s" % [where, tile]
	where = "chunk %s" % tile
	if not _is_count(entry["trees"]):
		return (
			"%s: trees must be a whole number from 1 to %d, found %s"
			% [where, MAX_COUNT, entry["trees"]]
		)
	if not TerrainGrid._is_plain_relative_path(entry["file"]):
		return (
			"%s: file must be a plain relative path inside the manifest's folder, found %s"
			% [where, entry["file"]]
		)
	if not _is_sha256(entry["sha256"]):
		return "%s: sha256 must be 64 hex digits, found %s" % [where, entry["sha256"]]
	return ""


## Checks the chunk file's size and SHA-256, then reads it.
func _read_chunk(folder: String, entry: Dictionary) -> String:
	var tile: String = entry["tile"]
	var count := int(entry["trees"])
	var chunk_path := folder.path_join(entry["file"])
	var rebuild := "; %s rebuilds it" % TREES_COMMAND
	if not FileAccess.file_exists(chunk_path):
		return "chunk %s: the file %s is missing%s" % [tile, chunk_path, rebuild]
	var expected_size := TREE_BYTES * count
	var data := FileAccess.get_file_as_bytes(chunk_path)
	if data.size() != expected_size:
		return (
			"chunk %s: the file %s holds %d bytes, not %d (%d trees)%s"
			% [tile, chunk_path, data.size(), expected_size, count, rebuild]
		)
	var found := FileAccess.get_sha256(chunk_path)
	if found != entry["sha256"].to_lower():
		return (
			"chunk %s: the file %s has SHA-256 %s, not the block's %s%s"
			% [tile, chunk_path, found, entry["sha256"], rebuild]
		)
	# Little-endian: every platform mattini builds for (x86_64) is.
	var values := data.to_float32_array()
	var positions := PackedVector3Array()
	var heights := PackedFloat32Array()
	var radii := PackedFloat32Array()
	positions.resize(count)
	heights.resize(count)
	radii.resize(count)
	for k in count:
		var at := 5 * k
		positions[k] = Vector3(values[at], values[at + 1], values[at + 2])
		heights[k] = values[at + 3]
		radii[k] = values[at + 4]
	chunks.append(
		{"tile": tile, "trees": count, "positions": positions, "heights": heights, "radii": radii}
	)
	return ""


static func _is_text(value: Variant) -> bool:
	return typeof(value) == TYPE_STRING and not value.is_empty()


static func _is_sha256(value: Variant) -> bool:
	return typeof(value) == TYPE_STRING and value.length() == 64 and value.is_valid_hex_number()


## A tile id: two whole numbers of kilometres joined by "-", as the pipeline names chunks.
static func _is_tile(value: Variant) -> bool:
	if typeof(value) != TYPE_STRING:
		return false
	var parts: PackedStringArray = value.split("-")
	return parts.size() == 2 and parts[0].is_valid_int() and parts[1].is_valid_int()


static func _is_number(value: Variant) -> bool:
	return typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT


## Godot's JSON reads every number as a float: a whole float from 1 to MAX_COUNT is a count.
static func _is_count(value: Variant) -> bool:
	if not _is_number(value):
		return false
	return float(value) == floorf(value) and value >= 1 and value <= MAX_COUNT
