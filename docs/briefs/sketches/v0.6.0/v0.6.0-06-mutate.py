"""The pin author's mutation rows for brief v0.6.0-06, placed in the rehearsal's throwaway
`pipeline/mattini/farcolour.py` (evidence; the builder places each row in their own code).

python3 -I v0.6.0-06-mutate.py <farcolour.py> <row>: rewrites the file with the row's edit; each
edit is an exact (old, new) text pair that must occur once.
"""

import sys
from pathlib import Path

ROWS = {
    1: ("a covered pixel the floor of its 5 x 5 mean", [(
        "((sums + 12) // 25)", "(sums // 25)")]),
    2: ("the 5 x 5 blocks one source pixel off (the tile read a column late)", [(
        "        data = _read_tile(tile, path, sha, res).astype(np.uint32)\n",
        "        data = np.roll(_read_tile(tile, path, sha, res).astype(np.uint32), 1, axis=1)\n")]),
    3: ("a tile placed from the south (rows north-south flipped)", [(
        "        r0, c0 = (box[3] - (n_km + 1) * TILE_M) // cell, (e_km * TILE_M - box[0]) // cell\n",
        "        r0, c0 = (n_km * TILE_M - box[2]) // cell, (e_km * TILE_M - box[0]) // cell\n")]),
    4: ("the band from the height minus height_offset_m", [(
        "    filled = fill(pixels, covered, cents, colour[\"band_m\"])\n",
        "    filled = fill(pixels, covered, cents - round(world.height_offset * 100), colour[\"band_m\"])\n")]),
    5: ("the band rounded, not floored", [(
        "    band = cents // (100 * band_m)\n",
        "    band = np.rint(cents / (100 * band_m)).astype(np.int64)\n")]),
    6: ("the band's mean floored", [(
        "        means[have, channel] = (total[have] + n[have] // 2) // n[have]\n",
        "        means[have, channel] = total[have] // n[have]\n")]),
    7: ("the band's mean rounded half to even", [(
        "        means[have, channel] = (total[have] + n[have] // 2) // n[have]\n",
        "        means[have, channel] = np.rint(total[have] / n[have]).astype(np.int64)\n")]),
    8: ("one mean for every band", [(
        "    taken = means[band_sources(have)[index]]\n",
        "    every = (pixels[covered].astype(np.int64).sum(0) + int(covered.sum()) // 2) // int(covered.sum())\n"
        "    taken = np.broadcast_to(every, pixels.shape)\n")]),
    9: ("an empty band takes the nearest above first", [(
        "        below = np.flatnonzero(have[:k])\n"
        "        if below.size:\n"
        "            src[k] = below[-1]\n"
        "        else:\n"
        "            above = np.flatnonzero(have[k + 1 :])\n"
        "            src[k] = k + 1 + above[0]\n",
        "        above = np.flatnonzero(have[k + 1 :])\n"
        "        if above.size:\n"
        "            src[k] = k + 1 + above[0]\n"
        "        else:\n"
        "            src[k] = np.flatnonzero(have[:k])[-1]\n")]),
    10: ("an empty band takes the nearest band, ties above", [(
        "        below = np.flatnonzero(have[:k])\n"
        "        if below.size:\n"
        "            src[k] = below[-1]\n"
        "        else:\n"
        "            above = np.flatnonzero(have[k + 1 :])\n"
        "            src[k] = k + 1 + above[0]\n",
        "        found = np.flatnonzero(have)\n"
        "        src[k] = max(found, key=lambda j: (-abs(j - k), j))\n")]),
    11: ("every pixel filled, the covered ones too", [(
        "    return np.where(covered[..., None], pixels, taken).astype(np.uint8)\n",
        "    return np.ascontiguousarray(taken).astype(np.uint8)\n")]),
    12: ("the area's own box cut (black)", [(
        "    filled = fill(pixels, covered, cents, colour[\"band_m\"])\n",
        "    filled = fill(pixels, covered, cents, colour[\"band_m\"])\n"
        "    a = world.area(area)\n"
        "    filled[(box[3] - int(a[3])) // cell : (box[3] - int(a[2])) // cell,\n"
        "           (int(a[0]) - box[0]) // cell : (int(a[1]) - box[0]) // cell] = 0\n")]),
    13: ("each pixel given the sample one cell west and north of its centre", [(
        "        c = (xs - box[0] - cell // 2) // cell\n"
        "        r = (box[3] - cell // 2 - ys) // cell\n",
        "        c = (xs - box[0] + cell // 2) // cell\n"
        "        r = (box[3] + cell // 2 - ys) // cell\n")]),
    14: ("a pixel without a sample taken as 0 m", [(
        "    if not seen.all():\n", "    if False:\n")]),
    15: ("the absent cells not compared with the box's cells (tiles a subset)", [(
        "    if set(tiles) & set(absent) or sorted(list(tiles) + absent) != sorted(cells):\n",
        "    if not set(tiles) <= set(cells):\n")]),
    16: ("the farphoto fit skipped", [(
        "    far = _far_entry(lock, datasets, world, area, settings[\"margin_m\"])\n",
        "    far = lock[\"datasets\"][FAR]\n")]),
    17: ("the inputs compared over the regio entry alone", [(
        "entries_sha256(lock, (REGIO, FAR))\n    if recorded",
        "entries_sha256(lock, (REGIO,))\n    if recorded")]),
    18: ("the world checked after the lock", [(
        "    problem = world_refusal(CONFIG_NAME, colour[\"computed_for\"], world_sha256)\n"
        "    if problem:\n"
        "        raise FarColourError(f\"area {area!r}: {problem}\")\n"
        "    columns, rows",
        "    columns, rows"), (
        "    far = _far_entry(lock, datasets, world, area, settings[\"margin_m\"])\n",
        "    far = _far_entry(lock, datasets, world, area, settings[\"margin_m\"])\n"
        "    problem = world_refusal(CONFIG_NAME, colour[\"computed_for\"], world_sha256)\n"
        "    if problem:\n"
        "        raise FarColourError(f\"area {area!r}: {problem}\")\n")]),
    19: ("provenance.json's absent list not compared", [(
        " and provenance[\"absent\"] == far[\"absent\"]\n", "\n")]),
    20: ("a tile's transform not checked", [(
        "            if (t.a, t.b, t.c, t.d, t.e, t.f) != want:\n",
        "            if False:\n")]),
    21: ("a tile's CRS not checked", [(
        "            if epsg != 2056:\n", "            if False:\n")]),
    22: ("a tile's bytes not checked against the lock", [(
        "    if hashlib.sha256(raw).hexdigest() != sha:\n", "    if False:\n")]),
    23: ("the pixels not compared (the JPEG alone)", [(
        "    if pixels_sha256 != colour[\"expected_pixels_sha256\"]:\n", "    if False:\n")]),
    24: ("the filled fraction not compared", [(
        "    if fraction != colour[\"expected_filled_fraction\"]:\n", "    if False:\n")]),
    25: ("another JPEG encoder (optimised tables)", [(
        "    data = encode_jpeg(pixels)\n",
        "    import io\n\n"
        "    from PIL import Image\n\n"
        "    buffer = io.BytesIO()\n"
        "    Image.fromarray(pixels).save(buffer, \"JPEG\", quality=92, optimize=True)\n"
        "    data = buffer.getvalue()\n")]),
    26: ("written before the expected checks", [(
        "    pixels_sha256 = hashlib.sha256(pixels.tobytes()).hexdigest()\n",
        "    (Path(out_dir) / \"surroundings\").mkdir(parents=True, exist_ok=True)\n"
        "    (Path(out_dir) / \"surroundings\" / f\"{area}_colour.jpg\").write_bytes(encode_jpeg(pixels))\n"
        "    pixels_sha256 = hashlib.sha256(pixels.tobytes()).hexdigest()\n")]),
    27: ("no .part rename", [(
        "    part = path.with_name(path.name + \".part\")\n"
        "    part.write_bytes(data)\n"
        "    os.replace(part, path)\n",
        "    path.write_bytes(data)\n")]),
    28: ("leftover parts kept", [(
        "    for part in target.glob(\"*.part\"):\n        part.unlink()\n", "")]),
    29: ("no .import beside the JPEG", [(
        "    _replace(jpeg.with_name(jpeg.name + \".import\"), KEEP_IMPORT)\n", "")]),
    30: ("the filled fraction rounded to four places", [(
        "        \"filled_fraction\": fraction,\n", "        \"filled_fraction\": round(fraction, 4),\n")]),
    31: ("a progress line before provenance.json", [(
        "    prepared = _prepare(world, datasets, lock, surroundings_config)\n",
        "    prepared = _prepare(world, datasets, lock, surroundings_config)\n"
        "    say(\"reading the downloads\")\n")]),
    32: ("the cell's fit to the datasets not checked", [(
        "    if cell != regio_res or cell != BLOCK * far_res or TILE_M % cell or any(v % cell for v in box):\n",
        "    if TILE_M % cell or any(v % cell for v in box):\n")]),
    33: ("the regio samples read by a second parser (float, rounded to centimetres)", [(
        "            xs, ys, cs = read_regio(tile)\n",
        "            xs, ys, cs = _float_parse(raw_root, datasets, regio, tile)\n"), (
        "def _description(",
        "def _float_parse(raw_root, datasets, regio, tile):\n"
        "    import io as _io\n"
        "    import zipfile as _zf\n\n"
        "    name = regio[\"tiles\"][tile][\"file\"]\n"
        "    raw = (Path(raw_root) / REGIO / datasets[REGIO][\"edition\"] / name).read_bytes()\n"
        "    with _zf.ZipFile(_io.BytesIO(raw)) as z:\n"
        "        text = z.read(z.namelist()[0]).decode()\n"
        "    rows = [line.split(\" \") for line in text.split(\"\\r\\n\")[1:-1]]\n"
        "    xs = np.array([int(r[0]) for r in rows], np.int64)\n"
        "    ys = np.array([int(r[1]) for r in rows], np.int64)\n"
        "    cs = np.array([round(float(r[2]) * 100) for r in rows], np.int64)\n"
        "    return xs, ys, cs\n\n\n"
        "def _description(")]),
    34: ("built block: the .import not checked", [(
        "    if keep != KEEP_IMPORT:\n", "    if False:\n")]),
    35: ("built block: the JPEG's bytes not checked", [(
        "    if hashlib.sha256(data).hexdigest() != expected[\"colour_sha256\"]:\n",
        "    if False:\n")]),
    36: ("a config without a colour block read as an empty one", [(
        "    if \"colour\" not in settings:\n        raise FarColourError(\n"
        "            f\"{CONFIG_NAME}: area {area!r} has no colour block: design's data (design §5)\"\n"
        "        )\n    colour = settings[\"colour\"]\n",
        "    colour = settings.get(\"colour\") or {}\n")]),
}


def main() -> None:
    path, row = Path(sys.argv[1]), int(sys.argv[2])
    text = path.read_text(encoding="utf-8")
    for old, new in ROWS[row][1]:
        assert text.count(old) == 1, (row, old)
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
