extends GutTest
## Pinning tests for brief v0.3.1-02 (M4-08 decision 1): the frame cap, the log flushed on
## every line, and 4× MSAA.
##
## Pinned decisions (m4-design §0 *Frame cap*; FB-007, FB-006, FB-004's jagged edges):
## game/project.godot sets application/run/max_fps = 60 (a CPU sleep, independent of vsync:
## the frame rate is the lower of the display's and 60, so the owner's 300 Hz laptop no longer
## renders flat out), application/run/flush_stdout_on_print = true (a release export buffers
## stdout and godot.log by default, so the startup lines appeared only at exit; `.debug`
## builds flush already), and rendering/anti_aliasing/quality/msaa_3d = 2 (Viewport.MSAA_4X).
## Read here as Godot reads the project at start, not as text: Engine.max_fps and the root
## viewport's msaa_3d are what the running engine took from them.
## The pause-time cap (15 fps while the pause screen is open) is brief v0.3.1-05's (M4-10
## decision 2), not this one's.
##
## Does NOT prove: that the cap lowers the owner's GPU load or that MSAA smooths the edges on
## the owner's GPU (no GPU here; the owner's PC is the test); that a release export flushes
## (the release template ignores --script; the export's started build prints its lines, not
## when); MSAA under Terrain3D's shader or in any SubViewport.


func test_the_frame_cap_is_60() -> void:
	assert_eq(ProjectSettings.get_setting("application/run/max_fps"), 60, "the project's cap")
	assert_eq(Engine.max_fps, 60, "the engine runs with it")


func test_every_print_is_flushed() -> void:
	assert_eq(
		ProjectSettings.get_setting("application/run/flush_stdout_on_print"),
		true,
		"a release build writes each line when it is printed"
	)


func test_3d_msaa_is_4x() -> void:
	assert_eq(ProjectSettings.get_setting("rendering/anti_aliasing/quality/msaa_3d"), 2)
	assert_eq(get_tree().root.msaa_3d, Viewport.MSAA_4X, "the root viewport takes it")
