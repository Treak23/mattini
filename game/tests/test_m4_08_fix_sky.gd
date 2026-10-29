extends GutTest
## Tests for the fixes of brief v0.4.0-08's prover (the main scene's sky wiring and SkySite's
## guards, each a mutation that survived the pinned tests): the sidereal angle and the moon's
## illuminated fraction reach the rig; the Hipparcos credit follows the rig, not only the stars'
## table; the stars' image is built once; SkySite refuses an unreadable manifest, and a
## manifest whose own world_sha256 is not text (brain.md H26, the manifest side).
##
## Does NOT prove: anything renders or looks right; main.tscn's own Moon and Environment values
## (SkyRig.create and apply overwrite them before anything reads them: the rig's tests pin the
## values that matter).

const CompleteWorld := preload("res://tests/complete_world.gd")
const SCRATCH_DIR := "user://test_m4_08_fix_sky"
const DEPRECATION := "instance_reset_physics_interpolation() is deprecated"
const COMMAND := "python -m mattini sky"
const HOUR_S := 3600.0

var _cases := 0
var _complete := ""


func before_all() -> void:
	_complete = CompleteWorld.write(SCRATCH_DIR.path_join("complete"))


func after_all() -> void:
	CompleteWorld.remove_tree(SCRATCH_DIR)


func _main_with(manifest_path: String) -> Node3D:
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = manifest_path
	add_child_autofree(main)
	for error in get_errors():
		if error.contains_text(DEPRECATION):
			error.handled = true
	main.set_process(false)
	return main


func _write_changed(change: Callable) -> String:
	_cases += 1
	return CompleteWorld.write(SCRATCH_DIR.path_join("case_%d" % _cases), change)


func _problem(change: Callable) -> String:
	var path := _write_changed(change)
	return SkySite.new()._read(path, WorldConfig.from_manifest(path))


func test_the_sidereal_angle_reaches_the_rig() -> void:
	var main := _main_with(_complete)
	var site: SkySite = main._site
	var material: ShaderMaterial = main.get_node("Environment").environment.sky.sky_material
	var seen := []
	for hours in [0.0, 6.0, 9.0]:
		main.time_unix = SkyClock.START_UNIX + hours * HOUR_S
		main._place_sky()
		var expected: Basis = main._rig._celestial_basis(
			SkyClock.sidereal_deg(main.time_unix, site.longitude_deg)
		)
		var drawn: Variant = material.get_shader_parameter("celestial_basis")
		assert_true(drawn is Basis, "the celestial basis is set at +%s h" % hours)
		if drawn is Basis:
			assert_true(
				(drawn as Basis).is_equal_approx(expected),
				"the stars turn with the clock's sidereal angle at +%s h" % hours
			)
			seen.append(drawn)
	assert_false((seen[0] as Basis).is_equal_approx(seen[1]), "and they move between hours")


func test_the_moon_s_fraction_reaches_the_rig() -> void:
	var main := _main_with(_complete)
	var site: SkySite = main._site
	var moon_light: DirectionalLight3D = main.get_node("Moon")
	var found := false
	# Hourly over 60 days: a moment with the moon well up and a fraction clearly neither 0 nor 1.
	for step in range(60 * 24):
		var t := SkyClock.START_UNIX + step * HOUR_S
		var moon := SkyClock.moon(t, site.latitude_deg, site.longitude_deg)
		if moon.y < 20.0 or moon.z < 0.15 or moon.z > 0.85:
			continue
		found = true
		main.time_unix = t
		main._place_sky()
		assert_almost_eq(
			moon_light.light_energy, SkyRig.MOON_ENERGY * moon.z, 0.0001, "the fraction %s" % moon.z
		)
		break
	assert_true(found, "a moment with a half-lit moon high up exists in 60 days")


func test_stars_credit_follows_the_rig_not_only_the_table() -> void:
	var main := _main_with(_complete)
	assert_not_null(main._stars(), "the table exists in the game: the stars' image is built")
	assert_true(
		(main.get_node("UI/PauseMenu/Credits") as RichTextLabel).text.contains("Hipparcos"),
		"the stars were drawn: credited"
	)
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var path := SCRATCH_DIR.path_join("not_json.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string("{ not json")
	file.close()
	var refused := _main_with(path)
	assert_push_error("not valid JSON", "WorldConfig logs its refusal")
	assert_null(refused._rig, "no world config, no rig")
	var credits := (refused.get_node("UI/PauseMenu/Credits") as RichTextLabel).text
	assert_false(credits.contains("Hipparcos"), "no rig draws no stars: no star credit")


func test_the_stars_image_is_built_once() -> void:
	var main := _main_with(_complete)
	var first: Image = main._stars()
	assert_not_null(first, "the table exists")
	assert_same(main._stars(), first, "the same image, not a second build of 32 MiB")


func test_an_unreadable_manifest_with_a_world_config_is_refused() -> void:
	var good := _write_changed(func(_m: Dictionary) -> void: pass)
	var world := WorldConfig.from_manifest(good)
	var missing := SCRATCH_DIR.path_join("no_such_manifest.json")
	var problem := SkySite.new()._read(missing, world)
	assert_string_contains(problem, "cannot read the manifest")
	assert_false(problem.contains(COMMAND), "the world's refusals do not name the sky command")
	DirAccess.make_dir_recursive_absolute(SCRATCH_DIR)
	var bad := SCRATCH_DIR.path_join("bad.json")
	var file := FileAccess.open(bad, FileAccess.WRITE)
	file.store_string("[1, 2]")
	file.close()
	assert_string_contains(SkySite.new()._read(bad, world), "not a JSON object")


func test_a_manifest_whose_world_sha256_is_not_text_is_refused() -> void:
	var cases := [
		func(m: Dictionary) -> void: m["world_sha256"] = 7,
		func(m: Dictionary) -> void: m["world_sha256"] = true,
		func(m: Dictionary) -> void: m["world_sha256"] = [1],
		func(m: Dictionary) -> void: m.erase("world_sha256"),
	]
	for change: Callable in cases:
		var problem := _problem(change)
		assert_string_contains(problem, "another world config", "refused, not a runtime error")
		assert_string_contains(problem, COMMAND)
