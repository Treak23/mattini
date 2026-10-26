class_name ReleaseBuild
extends RefCounted
## Whether this is an exported build, and the end of a reader's message about a generated
## file (brief v0.3.1-03, from M4-08 decisions 2 and 3; FB-005).
##
## is_exported() is OS.has_feature("template") unless a test has called
## set_exported_for_tests(true or false); set_exported_for_tests(null) gives the question
## back to the OS.
##
## file_hint(command) is the end of a reader's message about a missing or damaged generated
## file: outside an exported build "; <command> rebuilds it", the pipeline's hint; in one,
## where the player has no pipeline, RELEASE_HINT, because every generated file ships in the
## release's packs (the photo and the terrain's heights in the data packs, the rest in
## mattini.pck). No other script under res://scripts spells the pipeline's hint (the census
## in test_m4_08_release_hints.gd).

const RELEASE_HINT := "; it ships in the release's packs: download the release folder again"

## What a test has set: true or false answers is_exported() itself, null leaves it to the OS.
static var _exported_for_tests: Variant = null


## True in an exported build: OS.has_feature("template"), unless a test has set the answer.
static func is_exported() -> bool:
	if _exported_for_tests != null:
		return _exported_for_tests
	return OS.has_feature("template")


## Sets the answer of is_exported() for a test, true or false; null gives the question back
## to the OS. A test resets it with null after each test.
static func set_exported_for_tests(exported: Variant) -> void:
	_exported_for_tests = exported


## The end of a reader's message about a missing or damaged generated file: "; [param command]
## rebuilds it" outside an exported build, RELEASE_HINT in one.
static func file_hint(command: String) -> String:
	if is_exported():
		return RELEASE_HINT
	return "; %s rebuilds it" % command
