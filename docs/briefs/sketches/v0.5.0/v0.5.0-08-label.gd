extends SceneTree
## Pin author's evidence script (brief v0.5.0-08), never a gate and never committed under game/:
## renders main.tscn on the game tests' complete test world (game/tests/complete_world.gd) in
## three states of the clock label and saves each frame as <out_dir>/<name>.png:
##   inside: the clock at its start, 15 minutes later by time_later (the label for 4 s, no note);
##   outside: the clock set to 2036-01-01T12:00:00Z, no key, then 5 s of frames (the note);
##   paused: the same clock with the pause screen open (the note beside Resume and Quit).
## Prints each frame's label text and whether the label is shown.
##   -- <out_dir>

const CompleteWorld := preload("res://tests/complete_world.gd")
const SETTLE := 30
const SCRATCH := "user://v0.5.0-08-label"
## 2036-01-01T12:00:00Z.
const OUTSIDE := 2082801600.0


func _initialize() -> void:
	await process_frame
	var out: String = OS.get_cmdline_user_args()[0]
	root.msaa_3d = Viewport.MSAA_DISABLED
	var main: Node3D = load("res://main.tscn").instantiate()
	main.manifest_path = CompleteWorld.write(SCRATCH.path_join("complete"))
	root.add_child(main)
	var label: Label = main.get_node("UI/Clock")
	var press := InputEventAction.new()
	press.action = &"time_later"
	press.pressed = true
	root.push_input(press)
	await _shoot(label, out, "inside")
	main.time_unix = OUTSIDE
	var started := Time.get_ticks_msec()
	while Time.get_ticks_msec() - started < 5000:
		await process_frame
	await _shoot(label, out, "outside")
	main.toggle_pause()
	await _shoot(label, out, "paused")
	main.toggle_pause()
	CompleteWorld.remove_tree(SCRATCH)
	quit(0)


func _shoot(label: Label, out: String, name: String) -> void:
	for i in SETTLE:
		await process_frame
	await RenderingServer.frame_post_draw
	var image := root.get_texture().get_image()
	image.save_png(out.path_join(name + ".png"))
	print('label: %s shown %s text "%s"' % [name, label.visible, label.text])
