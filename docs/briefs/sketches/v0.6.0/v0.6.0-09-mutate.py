"""Brief v0.6.0-09's mutation rows on the throwaway: apply one, run the five pinned GUT scripts,
record what failed, restore, run again (both ways). Scratch, run from the clone's root:
python3 mutate09.py <row numbers...>"""
import os, re, subprocess, sys

M = "game/scripts/main.gd"
C = "game/scripts/camera/free_fly_camera.gd"
READ_FAR = """	# The far terrain is read after the mask, whatever else was read: its refusal is its own entry.
	var read_far := _caught(SurroundingsGrid.from_manifest.bind(manifest_path, world))
	var far: SurroundingsGrid = read_far[0]
	if far == null:
		refusals.append([SURROUNDINGS_WHAT, read_far[1], SURROUNDINGS_FIX])
"""
READ_MASK = """	# The capture mask is read whether or not the terrain or the photo was: its refusal is its own
	# entry (without a photo the loader ignores it, without a terrain nothing takes it).
	var read_shadows := _caught(CaptureShadowGrid.from_manifest.bind(manifest_path, world))
	var shadows: CaptureShadowGrid = read_shadows[0]
	if shadows == null:
		refusals.append([SHADOWS_WHAT, read_shadows[1], SHADOWS_FIX])
"""
READ_SKY = """	var read_sky := _caught(SkySite.from_manifest.bind(manifest_path, world))
	_site = read_sky[0]
	if _site == null:
		refusals.append([SKY_WHAT, read_sky[1], SKY_FIX])
"""
BUILD = """	if far != null:
		move_child(SurroundingsLoader.create(far, self), _ui.get_index())
"""
LINE_FAR = """	if far != null:
		var text := "mattini %s: surroundings %s loaded, %d x %d vertices at %s m, colour %d x %d at %s m"
		var size := [far.columns, far.rows, _number(far.spacing_m)]
		var colour := [far.colour_columns, far.colour_rows, _number(far.colour_cell_m)]
		print(text % ([v, far.area] + size + colour))
"""
LINE_SHADOWS = """	if shadows != null:
		var text := "mattini %s: shadows %s loaded, %d x %d cells at %s m"
		print(text % [v, shadows.area, shadows.columns, shadows.rows, _number(shadows.cell_m)])
"""
ROWS = {
    1: ("the far terrain read but never built", [(M, BUILD, "")]),
    2: ("the far terrain read only when the terrain was", [(M, READ_FAR, READ_FAR.replace(
        "\tvar read_far := _caught(SurroundingsGrid.from_manifest.bind(manifest_path, world))\n\tvar far: SurroundingsGrid = read_far[0]\n\tif far == null:\n\t\trefusals.append",
        "\tvar far: SurroundingsGrid = null\n\tif grid != null:\n\t\tvar read_far := _caught(SurroundingsGrid.from_manifest.bind(manifest_path, world))\n\t\tfar = read_far[0]\n\t\tif far == null:\n\t\t\trefusals.append"))]),
    25: ("the far terrain read only when the buildings were (the session's ruling)", [(M, READ_FAR, READ_FAR.replace(
        "\tvar read_far := _caught(SurroundingsGrid.from_manifest.bind(manifest_path, world))\n\tvar far: SurroundingsGrid = read_far[0]\n\tif far == null:\n\t\trefusals.append",
        "\tvar far: SurroundingsGrid = null\n\tif buildings != null:\n\t\tvar read_far := _caught(SurroundingsGrid.from_manifest.bind(manifest_path, world))\n\t\tfar = read_far[0]\n\t\tif far == null:\n\t\t\trefusals.append"))]),
    3: ("the far terrain read before the mask", [(M, READ_MASK + READ_FAR, READ_FAR + READ_MASK)]),
    4: ("the far terrain read after the sky", [(M, READ_FAR + READ_SKY, READ_SKY + READ_FAR)]),
    5: ("SURROUNDINGS_FIX without farcolour", [(M, ', RUN + "farcolour"\n]', "\n]")]),
    6: ("SURROUNDINGS_FIX: download farphoto before download regio",
        [(M, 'RUN + "download regio", RUN + "download farphoto"', 'RUN + "download farphoto", RUN + "download regio"')]),
    7: ("a refused manifest names eight (SURROUNDINGS_WHAT left out)", [(M, "\t\t\tSURROUNDINGS_WHAT,\n\t\t\tSKY_WHAT", "\t\t\tSKY_WHAT")]),
    8: ("the far terrain named after the sky in that list", [(M, "\t\t\tSURROUNDINGS_WHAT,\n\t\t\tSKY_WHAT", "\t\t\tSKY_WHAT,\n\t\t\tSURROUNDINGS_WHAT")]),
    9: ("Surroundings built under the camera", [(M, "move_child(SurroundingsLoader.create(far, self), _ui.get_index())", "SurroundingsLoader.create(far, _camera)")]),
    10: ("the Surroundings node turned half round", [(M, BUILD, "\tif far != null:\n\t\tvar far_node := SurroundingsLoader.create(far, self)\n\t\tmove_child(far_node, _ui.get_index())\n\t\tfar_node.rotate_y(PI)\n")]),
    11: ("the Surroundings node lifted by the height offset (an offset applied twice)", [(M, BUILD, "\tif far != null:\n\t\tvar far_node := SurroundingsLoader.create(far, self)\n\t\tmove_child(far_node, _ui.get_index())\n\t\tfar_node.position.y += world.height_offset\n")]),
    12: ("the far terrain's line before the shadows'", [(M, LINE_SHADOWS + LINE_FAR, LINE_FAR + LINE_SHADOWS)]),
    13: ("the line's columns and rows swapped", [(M, "[far.columns, far.rows, _number(far.spacing_m)]", "[far.rows, far.columns, _number(far.spacing_m)]")]),
    14: ("the line's colour size the heights' (columns, rows)", [(M, "[far.colour_columns, far.colour_rows,", "[far.columns, far.rows,")]),
    15: ("the line's colour cell the heights' spacing", [(M, "_number(far.colour_cell_m)]", "_number(far.spacing_m)]")]),
    16: ("the far heights not credited", [(M, "\t\tlines[_dataset_line(far.dataset, far.edition, far.attribution)] = true\n", "")]),
    17: ("the far colour credited under its dataset key (swissimage_far)", [(M, "_dataset_line(FAR_COLOUR_CREDIT, far.colour_edition", "_dataset_line(far.colour_dataset, far.colour_edition")]),
    18: ("the far colour credited with the heights' edition", [(M, "FAR_COLOUR_CREDIT, far.colour_edition, far.colour_attribution", "FAR_COLOUR_CREDIT, far.edition, far.colour_attribution")]),
    19: ("the far colour credited with the heights' attribution", [(M, "FAR_COLOUR_CREDIT, far.colour_edition, far.colour_attribution", "FAR_COLOUR_CREDIT, far.colour_edition, far.attribution")]),
    20: ("the heights' attribution cut to its first sentence", [(M, "lines[_dataset_line(far.dataset, far.edition, far.attribution)] = true", "lines[_dataset_line(far.dataset, far.edition, far.attribution.get_slice(\";\", 0))] = true")]),
    21: ("the camera's far left at 20000 m", [(C, "\tfar = 40000.0", "\tfar = 20000.0")]),
    22: ("the camera's far 30000 m (short of the 32.2 km corner)", [(C, "\tfar = 40000.0", "\tfar = 30000.0")]),
    23: ("the terrain built only when the far terrain was read", [(M, "\tif grid != null:\n\t\t_show_terrain(", "\tif grid != null and far != null:\n\t\t_show_terrain(")]),
}
GUT = ["godot", "--headless", "--path", "game", "-s", "addons/gut/gut_cmdln.gd",
       "-gtest=res://tests/test_main_scene.gd,res://tests/test_main_scene_data.gd,res://tests/test_main_scene_refusals.gd,res://tests/test_scene_placement.gd,res://tests/test_v060_09_far_terrain.gd",
       "-gexit", "-gconfig="]


def gut():
    out = subprocess.run(GUT, capture_output=True, text=True, errors="replace").stdout
    out = re.sub(r"\x1b\[[0-9;]*m", "", out)
    counts = {k: (re.search(rf"^{k}\s+(\S+)", out, re.M) or [None, "?"])[1] for k in ["Scripts", "Tests", "Passing Tests", "Failing Tests", "Asserts"]}
    failed, current = [], None
    for line in out.splitlines():
        m = re.match(r"^\s*- (test_\w+)", line)
        if m:
            current = m.group(1)
        if "[Failed]" in line and current and current not in failed:
            failed.append(current)
    skipped = "Ignoring script" in out or "Failed to load script" in out or "SCRIPT ERROR" in out
    return counts, failed, skipped


for n in [int(a) for a in sys.argv[1:]]:
    what, edits = ROWS[n]
    saved = {}
    for path, old, new in edits:
        text = saved.get(path) or open(path).read()
        saved.setdefault(path, text)
        cur = open(path).read()
        assert cur.count(old) == 1, (n, path, old[:60], cur.count(old))
        open(path, "w").write(cur.replace(old, new))
    counts, failed, skipped = gut()
    for path, text in saved.items():
        open(path, "w").write(text)
    st = subprocess.run(["git", "diff", "--quiet", "--", M, C]).returncode
    back, bfailed, bskipped = gut()
    print(f"ROW {n} | {what} | broken: {counts['Failing Tests']} failed of {counts['Tests']}, asserts {counts['Asserts']}, skipped={skipped}; {', '.join(failed)} | restored: passing {back['Passing Tests']} of {back['Tests']}, asserts {back['Asserts']}, failed {bfailed}", flush=True)
