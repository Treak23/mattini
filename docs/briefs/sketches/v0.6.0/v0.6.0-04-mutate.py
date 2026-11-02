"""The pin author's mutation rows for brief v0.6.0-04, placed in the rehearsal's throwaway
`pipeline/mattini/surroundings.py` (evidence; the builder places each row in their own code).

python3 -I v0.6.0-04-mutate.py <surroundings.py> <row>: rewrites the file with the row's edit;
each edit is an exact (old, new) text pair that must occur once.
"""

import sys
from pathlib import Path

ROWS = {
    1: ("the square closed on the east", [(
        "    c_lo = np.clip(-((2 * x0 - (2 * es - s)) // (2 * resolution)), 0, width)\n"
        "    c_hi = np.clip(-((2 * x0 - (2 * es + s)) // (2 * resolution)), 0, width)\n",
        "    c_lo = np.clip((2 * es - s - 2 * x0) // (2 * resolution) + 1, 0, width)\n"
        "    c_hi = np.clip((2 * es + s - 2 * x0) // (2 * resolution) + 1, 0, width)\n")]),
    2: ("the square closed on the north", [(
        "    r_lo = np.clip((2 * y0 - 2 * ns - s) // (2 * resolution) + 1, 0, height)\n"
        "    r_hi = np.clip((2 * y0 - 2 * ns + s) // (2 * resolution) + 1, 0, height)\n",
        "    r_lo = np.clip(-((2 * ns + s - 2 * y0) // (2 * resolution)), 0, height)\n"
        "    r_hi = np.clip(-((2 * ns - s - 2 * y0) // (2 * resolution)), 0, height)\n")]),
    3: ("rows south to north", [(
        "    ns = box[3] - s * np.arange(rows, dtype=np.int64)\n",
        "    ns = box[2] + s * np.arange(rows, dtype=np.int64)\n")]),
    4: ("the vertex at its square's centre (E + s/2, N - s/2)", [(
        "    es = box[0] + s * np.arange(columns, dtype=np.int64)\n"
        "    ns = box[3] - s * np.arange(rows, dtype=np.int64)\n",
        "    es = box[0] + s // 2 + s * np.arange(columns, dtype=np.int64)\n"
        "    ns = box[3] - s // 2 - s * np.arange(rows, dtype=np.int64)\n")]),
    5: ("no cut", [(
        "    cut = (E > e_min) & (E < e_max) & (N > n_min) & (N < n_max)\n",
        "    cut = np.zeros(E.shape, bool)\n")]),
    6: ("a cut that takes the area's edge", [(
        "    cut = (E > e_min) & (E < e_max) & (N > n_min) & (N < n_max)\n",
        "    cut = (E >= e_min) & (E <= e_max) & (N >= n_min) & (N <= n_max)\n")]),
    7: ("another NaN payload (0x7FC00001)", [(
        'NAN = np.frombuffer(bytes.fromhex("0000c07f"), dtype="<f4")[0]\n',
        'NAN = np.frombuffer(bytes.fromhex("0100c07f"), dtype="<f4")[0]\n')]),
    8: ("no height offset", [(
        '    grid = (mean - np.float64(world.height_offset)).astype("<f4")\n',
        '    grid = mean.astype("<f4")\n')]),
    9: ("the largest sample for the mean (M4-02's rule)", [(
        "    del cents\n", ""), (
        "    with np.errstate(invalid=\"ignore\", divide=\"ignore\"):\n"
        "        mean = total.astype(np.float64) / (100.0 * n.astype(np.float64))\n",
        "    mean = np.zeros(total.shape)\n"
        "    for i in range(rows):\n"
        "        for j in range(columns):\n"
        "            if n[i, j]:\n"
        "                part = cents[r_lo[i] : r_hi[i], c_lo[j] : c_hi[j]]\n"
        "                held = count[r_lo[i] : r_hi[i], c_lo[j] : c_hi[j]] == 1\n"
        "                mean[i, j] = part[held].max() / 100.0\n"), (
        "    del count\n", "")]),
    10: ("the mean rounded down to whole centimetres", [(
        "        mean = total.astype(np.float64) / (100.0 * n.astype(np.float64))\n",
        "        mean = (total // np.maximum(n, 1)).astype(np.float64) / 100.0\n")]),
    11: ("divided by the full square's count, not the samples held", [(
        "        mean = total.astype(np.float64) / (100.0 * n.astype(np.float64))\n",
        "        mean = total.astype(np.float64) / (100.0 * (s // resolution) ** 2)\n")]),
    12: ("the height text parsed by float()", [(
        "        match = HEIGHT.fullmatch(fields[2])\n"
        "        if not match:\n",
        "        try:\n"
        "            value = round(float(fields[2]) * 100)\n"
        "        except (ValueError, OverflowError):\n"
        "            value = None\n"
        "        match = HEIGHT.fullmatch(b\"0\")\n"
        "        if value is None:\n"), (
        "        xs[i], ys[i], cs[i] = int(fields[0]), int(fields[1]), -cents if sign else cents\n",
        "        xs[i], ys[i], cs[i] = int(fields[0]), int(fields[1]), value\n")]),
    13: ("three decimals accepted", [(
        'HEIGHT = re.compile(rb"(-?)([0-9]+)(?:\\.([0-9]{1,2}))?")\n',
        'HEIGHT = re.compile(rb"(-?)([0-9]+)(?:\\.([0-9]{1,3}))?")\n')]),
    14: ("the sign applied to the whole metres only (-3.05 read as -2.95)", [(
        "        cents = int(whole) * 100 + (int(frac.ljust(2, b\"0\")) if frac else 0)\n"
        "        xs[i], ys[i], cs[i] = int(fields[0]), int(fields[1]), -cents if sign else cents\n",
        "        cents = int(sign + whole) * 100 + (int(frac.ljust(2, b\"0\")) if frac else 0)\n"
        "        xs[i], ys[i], cs[i] = int(fields[0]), int(fields[1]), cents\n")]),
    15: ("a refused height text without its line", [(
        "            raise _bad_line(\n"
        "                tile, i + 2, line, \"has a height that is not a number of whole centimetres\"\n"
        "            )\n",
        "            raise SurroundingsError(f\"{DATASET} tile {tile}: a bad height; `{DOWNLOAD_COMMAND}`\")\n")]),
    16: ("written before the expected check", [(
        "    if sha256 != settings[\"expected_sha256\"]:\n",
        "    Path(out_dir, \"surroundings\").mkdir(parents=True, exist_ok=True)\n"
        "    _replace(Path(out_dir, \"surroundings\", f\"{area}.f32\"), data)\n"
        "    if sha256 != settings[\"expected_sha256\"]:\n")]),
    17: ("no .part rename", [(
        "    part = path.with_name(path.name + \".part\")\n"
        "    part.write_bytes(data)\n"
        "    os.replace(part, path)\n",
        "    path.write_bytes(data)\n")]),
    18: ("leftover parts kept", [(
        "    for part in target.glob(\"*.part\"):\n"
        "        part.unlink()\n", "")]),
    19: ("a missing sample (a vertex without one) accepted", [(
        "    if empty.any():\n", "    if False:\n")]),
    20: ("a duplicate point accepted", [(
        "    if dup.size:\n", "    if False:\n")]),
    21: ("an off-lattice point accepted", [(
        "        ((xs - e0 - half) % resolution != 0)\n"
        "        | ((n0 + TILE_M - half - ys) % resolution != 0)\n"
        "        | (col < 0)\n",
        "        (col < 0)\n")]),
    22: ("the lock's fit skipped (only the entry looked up)", [(
        "    entry = _fit(lock, datasets, tiles)\n",
        "    entry = lock[\"datasets\"].get(DATASET) or {}\n")]),
    23: ("the world checked after the lock", [(
        "    problem = world_refusal(CONFIG_NAME, settings[\"computed_for\"], world_sha256)\n"
        "    if problem:\n"
        "        raise SurroundingsError(f\"area {area!r}: {problem}\")\n"
        "    expected_box = {\n",
        "    expected_box = {\n"), (
        "    entry = _fit(lock, datasets, tiles)\n",
        "    entry = _fit(lock, datasets, tiles)\n"
        "    problem = world_refusal(CONFIG_NAME, settings[\"computed_for\"], world_sha256)\n"
        "    if problem:\n"
        "        raise SurroundingsError(f\"area {area!r}: {problem}\")\n")]),
    24: ("a progress line before provenance.json", [(
        "    provenance_path = folder / PROVENANCE\n",
        "    provenance_path = folder / PROVENANCE\n"
        "    say(\"reading the swissALTIRegio tiles\")\n")]),
    25: ("the tiles without the half-spacing border", [(
        "    lo_e2, hi_e2 = 2 * box[0] - s, 2 * box[1] + s\n"
        "    lo_n2, hi_n2 = 2 * box[2] - s, 2 * box[3] + s\n",
        "    lo_e2, hi_e2 = 2 * box[0], 2 * box[1]\n"
        "    lo_n2, hi_n2 = 2 * box[2], 2 * box[3]\n")]),
    26: ("schema 1 (M4-02's config) still read", [(
        "    if type(data[\"schema\"]) is not int or data[\"schema\"] != SCHEMA:\n",
        "    if type(data[\"schema\"]) is not int or data[\"schema\"] not in (1, SCHEMA):\n")]),
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
