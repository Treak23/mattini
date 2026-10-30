"""Mutation rows of brief v0.5.0-03 on the throwaway: python3 -I mutate.py N (run from the clone)."""
import sys

SG = "game/scripts/terrain/shadow_grid.gd"
CW = "game/tests/complete_world.gd"
ROWS = {
    1: (SG, "\t_mask = pixels\n\timage.generate_mipmaps()\n", "\t_mask = pixels\n\timage.flip_y()\n\timage.generate_mipmaps()\n"),
    2: (SG, "\treturn _mask[row * columns + column]", "\treturn _mask[(rows - 1 - row) * columns + column]"),
    3: (SG, "\tx0 = north_west.x\n", "\tx0 = north_west.x + 0.25\n"),
    4: (SG, "box[\"e_min\"], box[\"n_max\"], world.height_offset)", "box[\"e_min\"], box[\"n_min\"], world.height_offset)"),
    5: (SG, "\t\tor ManifestValue.differs(shadows[\"world_sha256\"], manifest.get(\"world_sha256\"))\n", "\t\tor false\n"),
    6: (SG, "\t\ttypeof(shadows.get(\"world_sha256\")) != TYPE_STRING\n\t\tor ManifestValue.differs(shadows[\"world_sha256\"], manifest.get(\"world_sha256\"))\n", "\t\tshadows[\"world_sha256\"] != manifest.get(\"world_sha256\")\n"),
    7: (SG, "\tif decoded != pixels_sha256:", "\tif false:"),
    8: (SG, "\tif east != Vector3.RIGHT or north != Vector3.FORWARD or up != Vector3.UP:", "\tif false:"),
    9: (CW, "\tmanifest[\"shadows\"] = _moved_description(SHADOWS_FIXTURE, dir, SHADOWS_BOX, world_sha256)\n", ""),
    10: (SG, "\t_mask = pixels\n\timage.generate_mipmaps()\n", "\t_mask = pixels\n"),
    11: (SG, "\tvar rebuild := ReleaseBuild.file_hint(SHADOWS_COMMAND)\n\tif not FileAccess.file_exists(png_path):", "\tvar rebuild := \"; %s rebuilds it\" % SHADOWS_COMMAND\n\tif not FileAccess.file_exists(png_path):"),
    12: (SG, "\t\treturn \"the mask %s is missing%s\" % [png_path, rebuild]", "\t\treturn \"the mask %s is missing: run %s\" % [png_path, SHADOWS_COMMAND]"),
    13: (SG, "\t\treturn \"the WorldConfig given was not read from this manifest (its origin differs)\"", "\t\tpass"),
    14: (SG, "\tif ManifestValue.differs(shadows[\"format\"], FORMAT):", "\tif shadows[\"format\"] != FORMAT:"),
    15: (SG, "\tif ManifestValue.differs(shadows[\"cell_m\"], CELL_M):", "\tif typeof(shadows[\"cell_m\"]) != TYPE_FLOAT:"),
    16: (SG, "\tif absf(wide - fit_width) > BOX_TOLERANCE_M or absf(deep - fit_depth) > BOX_TOLERANCE_M:", "\tif absf(deep - fit_depth) > BOX_TOLERANCE_M:"),
    17: (SG, "\tif not PhotoGrid._is_plain_relative_path(file):", "\tif typeof(file) != TYPE_STRING:"),
    18: (SG, "\tif found != shadows[\"sha256\"].to_lower():", "\tif false:"),
    19: (SG, "\tif image.get_format() != Image.FORMAT_L8 or image.get_size() != Vector2i(columns, rows):", "\tif image.get_size() != Vector2i(columns, rows):"),
    20: (SG, "\tif ManifestValue.differs(source[\"dataset\"], DATASET):", "\tif typeof(source[\"dataset\"]) != TYPE_STRING:"),
    21: (SG, "\tif not PhotoGrid._has_exactly(shadows, KEYS):", "\tif not shadows.has_all(KEYS):"),
    22: (SG, "\t\t\t% [DOWNLOAD_COMMAND, SHADOWS_COMMAND]\n", "\t\t\t% [SHADOWS_COMMAND, SHADOWS_COMMAND]\n"),
    23: (SG, "\tvar column := floori((x - x0) / cell_m)\n\tvar row := floori((z - z0) / cell_m)\n\tif column < 0 or row < 0 or column >= columns or row >= rows:", "\tvar column := floori((x - x0) / cell_m)\n\tvar row := floori((z - z0) / cell_m)\n\tif column < 0 or row < 0 or column > columns or row > rows:"),
    24: (SG, "\t\tor ManifestValue.differs(origin.get(\"n\"), world.origin_n)\n", ""),
    25: (SG, "\tif absf(wide - fit_width) > BOX_TOLERANCE_M or absf(deep - fit_depth) > BOX_TOLERANCE_M:", "\tif absf(wide - fit_width) > BOX_TOLERANCE_M:"),
    26: (SG, "\tif not PhotoGrid._is_plain_relative_path(file):", "\tif typeof(file) != TYPE_STRING or file.contains(\"..\"):"),
    27: (SG, "\tif typeof(source) != TYPE_DICTIONARY or not PhotoGrid._has_exactly(source, SOURCE_KEYS):", "\tif typeof(source) != TYPE_DICTIONARY or not source.has_all(SOURCE_KEYS):"),
}
n = int(sys.argv[1])
path, old, new = ROWS[n]
text = open(path).read()
assert text.count(old) == 1, (n, old)
open(path, "w").write(text.replace(old, new))
