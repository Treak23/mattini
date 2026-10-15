class_name BuildingRoofs
extends RefCounted
## The manifest's roofs block, checked against the buildings it describes (docs/SPEC.md §8,
## the buildings and the roof colours; CLAUDE.md Hard Rules 2 and 4).
##
## The block is the pipeline's roofs step output, embedded in the manifest: for every chunk
## of the buildings block, in its order, one entry per building (in the chunk file's order,
## UUIDs ascending) holding the building's triangle and vertex counts in that file and its
## roof colour, "rrggbb" in sRGB as the 2023 photo gives it, or null when no photo pixel
## lies on its roof. The block holds no coordinate, so this reader never converts one; it
## ties the block to the buildings instead: the block's world_sha256 must be the manifest's,
## the WorldConfig given must be the manifest's own (checked by BuildingChunks), and every
## chunk must fit the BuildingChunks given: the same tiles in the same order, per chunk the
## building count and the sums of triangles and vertices, and every building's triangles
## inside its own vertices (the chunk file lists each building's vertices, then its
## triangles' indices into them; counts moved between two buildings keep the sums and would
## colour another building's roof). Every problem is refused with one push_error naming the
## manifest and a null result, never a plausible set of colours.

const FORMAT := "roofs-v1"
const ROOFS_COMMAND := "python -m mattini roofs"
const DOWNLOAD_COMMAND := "python -m mattini download photo"
const BLOCK_KEYS := ["area", "chunks", "format", "lv95_box", "source", "world_sha256"]
const SOURCE_KEYS := ["buildings", "photo"]
const CHUNK_KEYS := ["buildings", "tile"]
const BUILDING_KEYS := ["roof", "roof_pixels", "triangles", "uuid", "vertices"]
## The most triangles, vertices or pixels one building may hold: an int32.
const MAX_COUNT := 2147483647
const HEX_DIGITS := "0123456789abcdef"

var area: String
var dataset: String
var edition: String
var attribution: String
## One Dictionary per chunk, in BuildingChunks' order: {"tile": String, "buildings": [{"uuid":
## String, "triangles": int, "vertices": int, "roof": Color or null}]}. The buildings are in
## the chunk file's order, so their triangles and vertices follow each other without a gap.
var chunks: Array = []


## Reads the roofs block of the manifest at [param path], checked against [param world] and
## [param chunks], which must be read from the same manifest. Returns null and calls
## push_error naming the path on every problem.
static func from_manifest(
	path: String, world: WorldConfig, chunks: BuildingChunks
) -> BuildingRoofs:
	var result := BuildingRoofs.new()
	var problem := result._read(path, world, chunks)
	if not problem.is_empty():
		push_error("BuildingRoofs: %s: %s" % [path, problem])
		return null
	return result


## Reads and checks everything and fills this object; returns what is wrong, or "".
func _read(path: String, world: WorldConfig, buildings: BuildingChunks) -> String:
	if world == null:
		return "no WorldConfig was given (read it with WorldConfig.from_manifest first)"
	if buildings == null:
		return "no BuildingChunks were given (read them with BuildingChunks.from_manifest first)"
	# The manifest and the path rule are read as TerrainGrid reads them: one home for each.
	var manifest: Variant = TerrainGrid._load_manifest(path)
	if typeof(manifest) == TYPE_STRING:
		return manifest
	var problem := _check_built(manifest)
	if problem.is_empty():
		# The roof colours are drawn on the meshes BuildingChunks read for this world.
		problem = BuildingChunks._check_world(world, path, manifest.get("world"))
	if problem.is_empty():
		problem = _read_block(manifest["roofs"], manifest.get("buildings"), buildings)
	if problem.is_empty():
		problem = _read_chunks(manifest["roofs"]["chunks"], buildings)
	return problem


## Roofs were built, and for this manifest's world config.
static func _check_built(manifest: Dictionary) -> String:
	var block: Variant = manifest.get("roofs")
	if block == null:
		return (
			"no roof colours have been built: run %s, then %s" % [DOWNLOAD_COMMAND, ROOFS_COMMAND]
		)
	if typeof(block) != TYPE_DICTIONARY:
		return "roofs must be an object or null, found %s" % [block]
	if (
		typeof(block.get("world_sha256")) != TYPE_STRING
		or block["world_sha256"] != manifest.get("world_sha256")
	):
		return (
			(
				"the roof colours were built for another world config (roofs.world_sha256 %s,"
				% [block.get("world_sha256")]
			)
			+ " the manifest's %s): run %s" % [manifest.get("world_sha256"), ROOFS_COMMAND]
		)
	return ""


## Checks the block's own fields, against the buildings block, and fills area, dataset,
## edition and attribution.
func _read_block(block: Dictionary, buildings_block: Variant, buildings: BuildingChunks) -> String:
	var problem := _check_keys(block, BLOCK_KEYS, "roofs")
	if problem.is_empty():
		problem = _check_header(block, buildings)
	if problem.is_empty():
		problem = _check_source(block["source"], buildings_block)
	if problem.is_empty():
		var photo: Dictionary = block["source"]["photo"]
		area = block["area"]
		dataset = photo["dataset"]
		edition = photo["edition"]
		attribution = photo["attribution"]
	return problem


## The block's format, area, box and chunk list.
static func _check_header(block: Dictionary, buildings: BuildingChunks) -> String:
	if block["format"] != FORMAT:
		return "roofs.format must be %s, found %s" % [FORMAT, block["format"]]
	if block["area"] != buildings.area:
		return (
			"roofs.area %s is not the buildings' area %s: run %s"
			% [block["area"], buildings.area, ROOFS_COMMAND]
		)
	if typeof(block["lv95_box"]) != TYPE_DICTIONARY:
		return "roofs.lv95_box must be an object, found %s" % [block["lv95_box"]]
	if typeof(block["chunks"]) != TYPE_ARRAY or block["chunks"].is_empty():
		return "roofs.chunks must be a list of chunks, found %s" % [block["chunks"]]
	return ""


## The block's source: the photo's dataset, edition and attribution, and the buildings
## source, which must be the manifest's own buildings.source: the colours were measured on
## those buildings' roofs.
static func _check_source(source: Variant, buildings_block: Variant) -> String:
	if typeof(source) != TYPE_DICTIONARY:
		return "roofs.source must be an object, found %s" % [source]
	var problem := _check_keys(source, SOURCE_KEYS, "roofs.source")
	if not problem.is_empty():
		return problem
	var photo: Variant = source["photo"]
	if typeof(photo) != TYPE_DICTIONARY:
		return "roofs.source.photo must be an object, found %s" % [photo]
	for key in ["attribution", "dataset", "edition"]:
		if not _is_text(photo.get(key)):
			return "roofs.source.photo.%s must be text, found %s" % [key, photo.get(key)]
	# The buildings block was read by BuildingChunks, so it is an object with its source.
	if source["buildings"] != buildings_block.get("source"):
		return (
			"roofs.source.buildings is not the manifest's buildings.source (the roof colours"
			+ " were measured on other buildings): run %s" % ROOFS_COMMAND
		)
	return ""


## Checks every chunk entry against the matching BuildingChunks chunk; fills chunks.
func _read_chunks(entries: Array, buildings: BuildingChunks) -> String:
	if entries.size() != buildings.chunks.size():
		return (
			"roofs.chunks holds %d chunks, the buildings %d: run %s"
			% [entries.size(), buildings.chunks.size(), ROOFS_COMMAND]
		)
	for i in entries.size():
		var problem := _read_chunk(entries[i], i, buildings.chunks[i])
		if not problem.is_empty():
			return problem
	return ""


## One chunk entry, {buildings, tile}, against the building chunk [param chunk]; appends it
## to chunks. The buildings follow each other in the chunk file, so each takes the next
## triangles and the next vertices.
func _read_chunk(entry: Variant, i: int, chunk: Dictionary) -> String:
	var problem := _check_entry(entry, i, chunk)
	if not problem.is_empty():
		return problem
	var where := "chunk %s" % chunk["tile"]
	var read := []
	var triangles := 0
	var vertices := 0
	var previous := ""
	for j in entry["buildings"].size():
		var building: Variant = _read_building(
			entry["buildings"][j], "%s: building %d" % [where, j]
		)
		if typeof(building) == TYPE_STRING:
			return building
		if j > 0 and building["uuid"] <= previous:
			return (
				"%s: the uuid %s of building %d does not ascend (after %s)"
				% [where, building["uuid"], j, previous]
			)
		previous = building["uuid"]
		problem = _check_range(building, triangles, vertices, chunk)
		if not problem.is_empty():
			return "%s: building %d (%s): %s" % [where, j, building["uuid"], problem]
		triangles += building["triangles"]
		vertices += building["vertices"]
		read.append(building)
	problem = _check_sums(triangles, vertices, chunk, where)
	if problem.is_empty():
		chunks.append({"tile": chunk["tile"], "buildings": read})
	return problem


## The chunk entry is {buildings, tile}, for the tile and the building count of the
## building chunk [param chunk], number [param i].
static func _check_entry(entry: Variant, i: int, chunk: Dictionary) -> String:
	var where := "roofs.chunks[%d]" % i
	if typeof(entry) != TYPE_DICTIONARY:
		return "%s must be an object, found %s" % [where, entry]
	var problem := _check_keys(entry, CHUNK_KEYS, where)
	if not problem.is_empty():
		return problem
	if entry["tile"] != chunk["tile"]:
		return (
			"%s is the tile %s, the buildings' chunk %d is %s: run %s"
			% [where, entry["tile"], i, chunk["tile"], ROOFS_COMMAND]
		)
	where = "chunk %s" % chunk["tile"]
	if typeof(entry["buildings"]) != TYPE_ARRAY:
		return "%s: buildings must be a list, found %s" % [where, entry["buildings"]]
	if entry["buildings"].size() != chunk["buildings"]:
		return (
			"%s: roofs lists %d buildings, the buildings' chunk %d: run %s"
			% [where, entry["buildings"].size(), chunk["buildings"], ROOFS_COMMAND]
		)
	return ""


## The buildings' triangles and vertices add up to the chunk file's.
static func _check_sums(triangles: int, vertices: int, chunk: Dictionary, where: String) -> String:
	var file_triangles: int = chunk["indices"].size() / 3
	var file_vertices: int = chunk["positions"].size()
	if triangles != file_triangles:
		return (
			"%s: the buildings' triangles add up to %d, the chunk file's to %d: run %s"
			% [where, triangles, file_triangles, ROOFS_COMMAND]
		)
	if vertices != file_vertices:
		return (
			"%s: the buildings' vertices add up to %d, the chunk file's to %d: run %s"
			% [where, vertices, file_vertices, ROOFS_COMMAND]
		)
	return ""


## One building entry as {uuid, triangles, vertices, roof}, or what is wrong with it.
static func _read_building(entry: Variant, where: String) -> Variant:
	if typeof(entry) != TYPE_DICTIONARY:
		return "%s must be an object, found %s" % [where, entry]
	var problem := _check_keys(entry, BUILDING_KEYS, where)
	if not problem.is_empty():
		return problem
	if not _is_text(entry["uuid"]):
		return "%s: uuid must be text, found %s" % [where, entry["uuid"]]
	for key in ["triangles", "vertices"]:
		if not _is_count(entry[key], 1):
			return (
				"%s: %s must be a whole number from 1 to %d, found %s"
				% [where, key, MAX_COUNT, entry[key]]
			)
	if not _is_count(entry["roof_pixels"], 0):
		return (
			"%s: roof_pixels must be a whole number from 0 to %d, found %s"
			% [where, MAX_COUNT, entry["roof_pixels"]]
		)
	var roof: Variant = entry["roof"]
	if roof == null:
		if int(entry["roof_pixels"]) != 0:
			return (
				"%s: roof is null, but %d photo pixels lie on its roof"
				% [where, int(entry["roof_pixels"])]
			)
	else:
		if not _is_colour(roof):
			return "%s: roof must be a lower-case rrggbb or null, found %s" % [where, roof]
		if int(entry["roof_pixels"]) == 0:
			return "%s: a roof colour %s from no photo pixel" % [where, roof]
		roof = Color.html(roof)
	return {
		"uuid": entry["uuid"],
		"triangles": int(entry["triangles"]),
		"vertices": int(entry["vertices"]),
		"roof": roof,
	}


## The building's triangles (the [param triangles] already taken, then its own count) must
## index only its own vertices (the [param vertices] already taken, then its own count).
## The chunk's indices are all inside the chunk (BuildingChunks), so a building past the
## chunk's end is told by the sums; this finds counts moved between two buildings. Returns
## what is wrong, or "".
static func _check_range(
	building: Dictionary, triangles: int, vertices: int, chunk: Dictionary
) -> String:
	var indices: PackedInt32Array = chunk["indices"]
	var end: int = 3 * (triangles + building["triangles"])
	if end > indices.size():
		return "its triangles reach past the chunk file's %d" % [indices.size() / 3]
	var own := indices.slice(3 * triangles, end)
	# The smallest and the largest index, found on a sorted copy (native, not a loop in script).
	own.sort()
	var low: int = vertices
	var high: int = vertices + building["vertices"] - 1
	if own[0] < low or own[own.size() - 1] > high:
		return (
			"its triangles index the vertices %d to %d, but its own are %d to %d"
			% [own[0], own[own.size() - 1], low, high]
		)
	return ""


## [param value] is an object with exactly the keys [param keys]; returns what differs, or "".
static func _check_keys(value: Dictionary, keys: Array, where: String) -> String:
	var found: Array = value.keys()
	found.sort()
	if found != keys:
		return "%s must have exactly the keys %s, found %s" % [where, keys, found]
	return ""


static func _is_text(value: Variant) -> bool:
	return typeof(value) == TYPE_STRING and not value.is_empty()


## "rrggbb": six lower-case hex digits, as the pipeline writes them (no sign, no prefix).
static func _is_colour(value: Variant) -> bool:
	if typeof(value) != TYPE_STRING or value.length() != 6:
		return false
	for digit in value:
		if not HEX_DIGITS.contains(digit):
			return false
	return true


## Godot's JSON reads every number as a float: a whole float from [param low] to MAX_COUNT.
static func _is_count(value: Variant, low: int) -> bool:
	if typeof(value) != TYPE_FLOAT and typeof(value) != TYPE_INT:
		return false
	return float(value) == floorf(value) and value >= low and value <= MAX_COUNT
