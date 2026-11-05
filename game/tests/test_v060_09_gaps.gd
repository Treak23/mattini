extends GutTest
## Gaps in the pinned tests of brief v0.6.0-09 that the reviews' and the mutation prover's findings
## named (lesson 51, decision 14): what the main scene shows of the far terrain that no pinned test
## fails without. Each test here fails when the behaviour it names is removed or loosened, and
## covers the class of its finding (lesson 9), not the one site a finding named.
##
## The far colour's placeholder note (findings F1 and O-1, Hard Rule 2, SPEC line 15 and §10, design
## §2): about a third of the real village's far colour is not SWISSIMAGE (every pixel of a cell
## without a 2023 item is filled with the mean colour of the pixels at the same 100 m of altitude),
## and the block records the share, filled_fraction, so that the credits can say how much is
## placeholder. When the far terrain was read and any pixel was filled, the credits' "Placeholders"
## section ends with one more line, after the walls', the trees' and the streams' notes:
##   Far colour: <about N % | less than 1 %> of its pixels are a placeholder, not SWISSIMAGE data:
##   where swisstopo has no <colour edition> image they are filled with the mean colour of the
##   <colour edition> pixels at the same 100 m of altitude.
## (one line; N the whole percent of filled_fraction; the edition the block's colour_source's, not
## the heights'). With no filled pixel (filled_fraction 0) nothing is a placeholder and no note is
## written; with the far terrain refused or absent there is no far colour and no note.
##
## What the pinned tests leave to be shown here (the prover's survivors, each the class of its
## row): the far terrain built exactly once and drawn (the node and every chunk visible in the
## tree), and, whichever other block was refused (the terrain, the buildings, the photo, the
## surfaces, the trees, the roof colours, the capture mask or the sun's place), still built, still
## named by its startup line and still credited, its heights, its colour and its note; and the
## error panel carrying each refusal's own message, the far terrain's among them, not only its
## name and commands.
##
## Every case opens the complete test world (complete_world.gd), whose far terrain is the shared
## surroundings fixture's (filled_fraction 0.2, colour edition 2023), with one block changed. The
## refusals are logged on purpose by their readers: each is asserted with assert_push_error and
## counted, and tools/gate_allowlist.txt excepts the engine's ERROR lines for this script's scratch
## folder, scoped to it.
##
## Does NOT prove: that anything renders or looks right (no GPU; the owner's PC); that the share
## the note states is the pipeline's (v0.6.0-06 pins it against config/surroundings.json); the
## real village's note (its filled_fraction is 0.32447397563676633, so "about 32 %": the table
## holds that number, the village's block is not read); that the far terrain is drawn where it
## belongs (test_v060_09_far_terrain.gd).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_v060_09_gaps"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const STREAMS_NOTE := "Streams: drawn 2 m wide, an assumed width: swissTLM3D gives none."
## The complete world's far terrain, credited: the shared surroundings fixture's attributions.
const FAR_HEIGHTS_LINE := (
	"swissaltiregio 2026-06, © swisstopo" + " (synthetic test heights, not swissALTIRegio data)"
)
const FAR_COLOUR_LINE := (
	"swissimage 2023, © swisstopo" + " (synthetic test colours, not SWISSIMAGE data)"
)
## The fixture's far colour, in pixels: what tells the far terrain's material from every other.
const FAR_COLOUR_SIZE := Vector2i(15, 18)
## Every other block, with what its reader calls its refusal (the prefix of its push_error).
const REFUSALS := {
	"terrain": "TerrainGrid",
	"buildings": "BuildingChunks",
	"photo": "PhotoGrid",
	"surfaces": "SurfaceGrid",
	"trees": "TreeChunks",
	"roofs": "BuildingRoofs",
	"shadows": "CaptureShadowGrid",
	"sky": "SkySite",
}


## Collects every line printed while it listens.
class LineCatcher:
	extends Logger

	var _lines := PackedStringArray()
	var _mutex := Mutex.new()

	func _log_message(message: String, error: bool) -> void:
		if error:
			return
		_mutex.lock()
		for line in message.strip_edges(false, true).split("\n"):
			_lines.append(line)
		_mutex.unlock()

	func lines() -> PackedStringArray:
		_mutex.lock()
		var copy := _lines.duplicate()
		_mutex.unlock()
		return copy


var _cases := 0


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


## The complete world with [param change] applied to its manifest, opened as the main scene:
## {main, path, lines (what it printed), credits, message (the error panel's text, "" when closed)}.
func _open(change := Callable()) -> Dictionary:
	_cases += 1
	var path := CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)
	var catcher := LineCatcher.new()
	OS.add_logger(catcher)
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = path
	add_child_autofree(main)
	OS.remove_logger(catcher)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	var panel: Control = main.get_node("UI/ErrorPanel")
	return {
		"main": main,
		"path": path,
		"lines": catcher.lines(),
		"credits": main.get_node("UI/PauseMenu/Credits").text,
		"message": main.get_node("UI/ErrorPanel/Message").text if panel.visible else "",
	}


## The far terrain's nodes among [param main]'s children: those with a chunk whose material holds
## the far colour (the loader names its node "Surroundings", but a second one would be renamed).
func _far_nodes(main: Node) -> Array[Node]:
	var found: Array[Node] = []
	for child in main.get_children():
		for part in child.get_children():
			var instance := part as MeshInstance3D
			if instance == null:
				continue
			var material := instance.get_active_material(0) as StandardMaterial3D
			if material != null and material.albedo_texture != null:
				if material.albedo_texture.get_size() == Vector2(FAR_COLOUR_SIZE):
					found.append(child)
					break
	return found


## The lines of the credits' "Placeholders" section, after its heading and before "Sky".
func _placeholders(credits: String) -> PackedStringArray:
	var heading := "\nPlaceholders\n"
	var start := credits.find(heading)
	var end := credits.find("\n\nSky\n", start)
	assert_true(start >= 0 and end > start, "the credits hold a Placeholders section before Sky")
	if start < 0 or end <= start:
		return PackedStringArray()
	var text := credits.substr(start + heading.length(), end - start - heading.length())
	return PackedStringArray(text.split("\n"))


## The three notes that describe the build, as the credits always list them.
func _build_notes() -> Array:
	return [BuildingLoader.WALLS_NOTE, TreeLoader.TREES_NOTE, STREAMS_NOTE]


## The far colour's note as the credits write it, for a share's words and the colour's edition.
func _note(share: String, edition: String) -> String:
	return (
		(
			"Far colour: %s of its pixels are a placeholder, not SWISSIMAGE data: where swisstopo has"
			+ " no %s image they are filled with the mean colour of the %s pixels at the same 100 m of"
			+ " altitude."
		)
		% [share, edition, edition]
	)


func _startup_line() -> String:
	var version: String = ProjectSettings.get_setting("application/config/version")
	return (
		(
			"mattini %s: surroundings fixture loaded, 6 x 7 vertices at 3000 m,"
			+ " colour 15 x 18 at 1000 m"
		)
		% version
	)


## The manifest change that refuses only [param block] (a block of REFUSALS).
func _refusing(block: String) -> Callable:
	match block:
		"terrain", "buildings", "photo", "trees", "roofs":
			return func(m: Dictionary) -> void: m[block] = null
		"surfaces", "shadows":
			return func(m: Dictionary) -> void: m[block]["sha256"] = "0".repeat(64)
	return func(m: Dictionary) -> void: m["sky"]["world_sha256"] = "0".repeat(64)


func test_the_far_colour_s_placeholder_share_is_a_note_in_the_credits() -> void:
	var credits: String = _open()["credits"]
	var expected := _build_notes() + [_note("about 20 %", "2023")]
	assert_eq(
		_placeholders(credits), PackedStringArray(expected), "the three notes, then the far's"
	)
	assert_eq(credits.count("Far colour:"), 1, "listed once")
	var data := credits.substr(0, credits.find("\nTextures\n"))
	assert_false(data.contains("placeholder"), "and not among the datasets")
	assert_string_contains(
		data, "\n" + FAR_COLOUR_LINE + "\n", "where the colour is still credited"
	)


func test_the_note_gives_the_block_s_share_and_the_colour_s_edition() -> void:
	# Each share through the block's own number: 0.2 and 0.8 tell the share from its complement, the
	# rounding and the "less than 1 %" edge from a floor, a ceiling and a plain integer.
	var cases := [
		[0.2, "about 20 %", "2023"],
		[0.8, "about 80 %", "2023"],
		[0.32447397563676633, "about 32 %", "2023"],
		[0.3251, "about 33 %", "2023"],
		[0.01, "about 1 %", "2023"],
		[0.0101, "about 1 %", "2023"],
		[0.0149, "about 1 %", "2023"],
		[0.0151, "about 2 %", "2023"],
		[0.0099, "less than 1 %", "2023"],
		[0.004, "less than 1 %", "2023"],
		[1.0, "about 100 %", "2023"],
		[0.8, "about 80 %", "2020"],
	]
	for one: Array in cases:
		var fraction: float = one[0]
		var edition: String = one[2]
		var change := func(m: Dictionary) -> void:
			m["surroundings"]["filled_fraction"] = fraction
			m["surroundings"]["colour_source"]["edition"] = edition
		var credits: String = _open(change)["credits"]
		var expected := _build_notes() + [_note(one[1], edition)]
		var name := "filled_fraction %s, edition %s" % [fraction, edition]
		assert_eq(_placeholders(credits), PackedStringArray(expected), name)
	var edition_s := "\nswissimage 2020, © swisstopo (synthetic test colours, not SWISSIMAGE data)\n"
	var last: String = _open(
		func(m: Dictionary) -> void: m["surroundings"]["colour_source"]["edition"] = "2020"
	)["credits"]
	assert_string_contains(last, edition_s, "the heights' edition 2026-06 is not the colour's")
	var notes := _placeholders(last)
	assert_eq(notes.size(), 4, "the far colour's note is there")
	assert_false(notes[notes.size() - 1].contains("2026"), "and never names the heights' edition")


func test_with_no_filled_pixel_nothing_is_a_placeholder() -> void:
	var none := func(m: Dictionary) -> void: m["surroundings"]["filled_fraction"] = 0.0
	var opened := _open(none)
	assert_eq(_placeholders(opened["credits"]), PackedStringArray(_build_notes()), "the three")
	assert_false(opened["credits"].contains("Far colour"), "no far colour note")
	assert_string_contains(opened["credits"], "\n" + FAR_COLOUR_LINE + "\n", "the colour credited")
	assert_not_null(opened["main"].get_node_or_null("Surroundings"), "and the far terrain drawn")


func test_without_the_far_terrain_there_is_no_far_colour_note() -> void:
	# Absent, then damaged: the reader refuses both, so there is no far colour to label.
	var gone := _open(func(m: Dictionary) -> void: m["surroundings"] = null)
	assert_push_error("SurroundingsGrid: " + gone["path"], "SurroundingsGrid logs its refusal")
	assert_push_error_count(1, "once, and nothing else is refused")
	assert_eq(_placeholders(gone["credits"]), PackedStringArray(_build_notes()), "the three only")
	assert_false(gone["credits"].contains("Far colour"), "no note for a colour never read")
	var damaged := _open(
		func(m: Dictionary) -> void: m["surroundings"]["colour_sha256"] = "0".repeat(64)
	)
	assert_push_error("SurroundingsGrid: " + damaged["path"], "SurroundingsGrid logs its refusal")
	assert_push_error_count(2, "once each (the count is the test's, both cases)")
	assert_eq(
		_placeholders(damaged["credits"]), PackedStringArray(_build_notes()), "the three only"
	)
	assert_false(damaged["credits"].contains("Far colour"), "no note for a colour refused")


func test_the_far_terrain_is_built_once_and_drawn() -> void:
	var main: Node3D = _open()["main"]
	var nodes := _far_nodes(main)
	assert_eq(nodes.size(), 1, "one far terrain: built once, not twice")
	assert_not_null(main.get_node_or_null("Surroundings"), "named Surroundings")
	for node in nodes:
		assert_true((node as Node3D).visible, "the node is not hidden")
		assert_true((node as Node3D).is_visible_in_tree(), "and is drawn in the tree")
		var parts := 0
		for part in node.get_children():
			var instance := part as MeshInstance3D
			assert_not_null(instance, "%s is a mesh" % part.name)
			if instance != null:
				parts += 1
				assert_true(instance.visible, "%s is not hidden" % part.name)
				assert_true(instance.is_visible_in_tree(), "%s is drawn in the tree" % part.name)
		assert_gt(parts, 1, "a chunk and the skirt, each there")


func test_the_far_terrain_is_shown_whichever_other_block_was_refused() -> void:
	# One block refused at a time, the far terrain's own untouched: it is still built once and
	# drawn, still named by its startup line (in its place, last) and still credited, with its note.
	var version: String = ProjectSettings.get_setting("application/config/version")
	var refused := 0
	for block: String in REFUSALS:
		var opened := _open(_refusing(block))
		var path: String = opened["path"]
		assert_push_error(REFUSALS[block] + ": " + path, "%s logs its refusal" % block)
		refused += 1
		# GUT counts the whole test's errors: one more per case, and nothing else is refused.
		assert_push_error_count(refused, "%s: once, and nothing else is refused" % block)
		var nodes := _far_nodes(opened["main"])
		assert_eq(nodes.size(), 1, "%s refused: the far terrain built once" % block)
		for node in nodes:
			assert_true((node as Node3D).is_visible_in_tree(), "%s refused: drawn" % block)
		var startup := PackedStringArray()
		for line: String in opened["lines"]:
			if line.begins_with("mattini %s: " % version):
				startup.append(line)
		assert_eq(
			startup[startup.size() - 1], _startup_line(), "%s refused: its line, last" % block
		)
		var credits: String = opened["credits"]
		var heights := "\n" + FAR_HEIGHTS_LINE + "\n"
		assert_string_contains(credits, heights, "%s refused: the heights credited" % block)
		var colour := "\n" + FAR_COLOUR_LINE + "\n"
		assert_string_contains(credits, colour, "%s refused: the colour credited" % block)
		var notes := _placeholders(credits)
		assert_eq(notes[notes.size() - 1], _note("about 20 %", "2023"), "%s: the note" % block)
		var message: String = opened["message"]
		assert_ne(message, "", "%s refused: the panel is open" % block)
		assert_false(message.contains("far terrain"), "%s refused: the far terrain is not" % block)


func test_the_panel_carries_each_refusal_s_own_message() -> void:
	# The far terrain's entry between the mask's and the sky's, each with the reader's own words
	# (the path of the manifest it refused), not only a name and commands.
	var opened := _open(
		func(m: Dictionary) -> void:
			m["shadows"]["sha256"] = "0".repeat(64)
			m["surroundings"]["colour_sha256"] = "0".repeat(64)
			m["sky"]["world_sha256"] = "0".repeat(64)
	)
	var path: String = opened["path"]
	assert_push_error("CaptureShadowGrid: " + path, "CaptureShadowGrid logs its refusal")
	assert_push_error("SurroundingsGrid: " + path, "SurroundingsGrid logs its refusal")
	assert_push_error("SkySite: " + path, "SkySite logs its refusal")
	assert_push_error_count(3, "each once")
	var message: String = opened["message"]
	var at := []
	for reader in ["CaptureShadowGrid", "SurroundingsGrid", "SkySite"]:
		var found := message.find("\n%s: %s" % [reader, path])
		assert_gt(found, 0, "%s's own refusal is on the panel" % reader)
		at.append(found)
	assert_true(at[0] < at[1] and at[1] < at[2], "in the blocks' order")
	var far_fix := message.find("To fix the far terrain,")
	assert_true(at[1] < far_fix and far_fix < message.find("\nSkySite: "), "each before its fix")
	assert_string_contains(message, "farcolour", "the far terrain's colour step is named")
