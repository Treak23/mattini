extends GutTest
## A WorldConfig made with new() instead of from_manifest starts with a NaN origin and a
## NaN height offset (brief M1-02, M0 review C-07): code that reads the origin of an
## unbuilt config gets a visibly wrong value, never 0 m, which looks like a real place.
##
## Does NOT prove that nothing builds a WorldConfig by hand; the conversions' own guard is
## pinned in test_world_config_unbuilt.gd.


func test_an_unbuilt_config_has_a_nan_origin_and_offset() -> void:
	var world := WorldConfig.new()
	assert_true(is_nan(world.origin_e), "origin_e is NaN: %s" % world.origin_e)
	assert_true(is_nan(world.origin_n), "origin_n is NaN: %s" % world.origin_n)
	assert_true(is_nan(world.height_offset), "height_offset is NaN: %s" % world.height_offset)
