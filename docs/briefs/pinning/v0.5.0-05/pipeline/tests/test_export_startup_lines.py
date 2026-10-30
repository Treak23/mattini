"""Pinning tests for brief M3-14: tools/export.sh ships every block and requires every
startup line, in order, from the exported Linux build.

Pinned decisions (docs/SPEC.md §11; docs/RELEASE.md §C; brief M3-14): step 2 refuses,
before anything is exported, a manifest without one of the six blocks the build ships
(terrain, buildings, photo, surfaces, trees, roofs), naming the commands that build it in
order. Step 6 requires the started Linux build to print, in this order, one line per data
pack step 4b wrote (`mattini <version>: data pack <name> loaded`, in name order, brief M3-08),
then M2's two lines, then the four M3 lines, each computed from the manifest:
    mattini <v>: photo <area> loaded, <columns> x <rows> texels at <cell> m
    mattini <v>: surfaces <area> loaded, <columns> x <rows> cells at <cell> m
    mattini <v>: trees <area> loaded, <sum of the chunks' trees> trees in <chunks> chunks
    mattini <v>: roofs <area> loaded, <buildings with a roof colour> of <buildings> buildings
        coloured
(numbers as main.gd writes them: at most two decimals, no trailing zeros). A line missing,
another number, or a line printed out of order fails it. The test manifest's numbers are
asymmetric so that each likely mix-up gives another line: the surfaces' cell (0.5) is not
the photo's (0.2), columns and rows differ, the trees' sum is not their chunk count, and
one of the four buildings has no roof colour.

The script under test is the repository's own, run on stand-ins (fake_tools.py, brief
M3-02); here the stand-in Godot also writes the data packs, as game/tools/pack.gd does, so
step 4c reads real pack directories.

Since brief v0.3.1-04 (M4-08 decisions 5 and 6; design's full replacement of M3-14's file;
only `_tree`'s folders, the export run named under "Does NOT prove" and this paragraph
change): fake_tools.export_tree makes both packed folders itself, so `_tree` only writes its
files into them.

Since brief v0.4.0-09 (M4-10 decision 10's sky; only MANIFEST, one refusal case and this
paragraph change): the build ships seven blocks, so step 2 also refuses a manifest without the
sky block, naming `python -m mattini sky`, before anything is exported. The sky block prints no
startup line, so step 6 still requires exactly the packs' lines and the six (M4-10's two lines
of the far mountains and the capture mask belong to a later release): the first test passes on
a manifest with all seven blocks, and fails if step 6 expects another count.

Since brief v0.5.0-05 (M4-10 decision 10, cut to the capture mask; only MANIFEST, LINES, the
cases and this paragraph change): the build ships eight blocks, so step 2 also refuses a
manifest without the shadows block, naming `python -m mattini download surface`, then
`python -m mattini shadows`, before anything is exported, and step 6 requires one more line
after the roofs':
    mattini <v>: shadows <area> loaded, <columns> x <rows> cells at <cell> m
The test manifest's shadows hold 2000 x 3000 cells at 1 m, numbers no other block holds (the
real village's 4000 x 6000 at 0.5 m are the surfaces' too, so a line computed from the surfaces'
block would pass there; fake_tools.MANIFEST keeps the real numbers); the twins are a line with
the columns and rows swapped, the surfaces' cell, the line missing, and the line before the
roofs'. The far
mountains' line (M4-10) belongs to a later release: step 6 requires exactly the packs' lines
and the seven.

Does NOT prove: that the real build prints these lines (the release gate's export run does,
docs/RELEASE.md §C); the Windows build (the owner's PC).
"""

import json
import platform
import shutil
import subprocess
from pathlib import Path

import fake_tools
import pytest

pytestmark = pytest.mark.skipif(
    fake_tools.BASH is None or platform.system() != "Linux",
    reason="tools/export.sh runs on Linux with bash",
)

V = fake_tools.VERSION
RUN = "uv run --project pipeline python -m mattini"

MANIFEST = {
    "buildings": {
        "area": "village",
        "chunks": [
            {"buildings": 3, "triangles": 3100},
            {"buildings": 1, "triangles": 410},
        ],
    },
    "photo": {"area": "village", "cell_m": 0.2, "columns": 10000, "rows": 15000},
    "roofs": {
        "area": "village",
        "chunks": [
            {"buildings": [{"roof": "a1b2c3"}, {"roof": None}, {"roof": "0f0e0d"}]},
            {"buildings": [{"roof": "445566"}]},
        ],
    },
    "schema": 1,
    "shadows": {"area": "village", "cell_m": 1.0, "columns": 2000, "rows": 3000},
    "sky": {
        "area": "village",
        "latitude_deg": 46.0196233,
        "longitude_deg": 7.7485397,
        "true_to_grid_deg": -0.2258,
        "world_sha256": "d2607d1362f3c7ec26b7e00c38d873b36d29db83aa169eebf60e0dd6f299509b",
    },
    "surfaces": {"area": "village", "cell_m": 0.5, "columns": 4000, "rows": 6000},
    "terrain": {"area": "village", "columns": 4001, "rows": 6001, "spacing_m": 0.5},
    "trees": {
        "area": "village",
        "chunks": [{"trees": 5734}, {"trees": 3662}, {"trees": 25027}],
    },
}
PACK_LINES = (
    f"mattini {V}: data pack mattini-photo.pck loaded",
    f"mattini {V}: data pack mattini-terrain.pck loaded",
)
LINES = (
    f"mattini {V}: terrain village loaded, 4001 x 6001 vertices at 0.5 m",
    f"mattini {V}: buildings village loaded, 4 buildings in 2 chunks, 3510 triangles",
    f"mattini {V}: photo village loaded, 10000 x 15000 texels at 0.2 m",
    f"mattini {V}: surfaces village loaded, 4000 x 6000 cells at 0.5 m",
    f"mattini {V}: trees village loaded, 34423 trees in 3 chunks",
    f"mattini {V}: roofs village loaded, 3 of 4 buildings coloured",
    f"mattini {V}: shadows village loaded, 2000 x 3000 cells at 1 m",
)
# Godot's pack tool, as the stand-in Godot runs it: `-s res://tools/pack.gd -- <pack>
# res://assets/generated/<folder>` writes every file of the folder, in name order, at its
# res:// path (brief M3-08).
PACK_GODOT = r"""#!/usr/bin/env bash
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
	if [ "${args[$i]}" = "res://tools/pack.gd" ]; then
		exec "$FAKE_PYTHON" "$PACK_WRITER" "${args[$((i + 2))]}" "${args[$((i + 3))]}"
	fi
done
exec "$(dirname "$0")/godot-stand-in" "$@"
"""
PACK_WRITER = """import sys
from pathlib import Path

import fake_tools

folder = sys.argv[2].removeprefix("res://")
files = sorted(p for p in (Path("game") / folder).iterdir() if p.is_file())
fake_tools.write_pck(Path(sys.argv[1]), [(f"{folder}/{p.name}", p.read_bytes()) for p in files])
print("pack: wrote " + sys.argv[1])
"""


def _tree(tmp_path: Path, manifest: dict) -> Path:
    templates = tmp_path / "xdg" / "godot" / "export_templates" / "4.6.3.stable"
    root = fake_tools.export_tree(tmp_path, templates)
    generated = root / "game" / "assets" / "generated"
    (generated / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for folder, name, size in (("photo", "village.jpg", 70), ("terrain", "village.f32", 44)):
        (generated / folder).mkdir(exist_ok=True)
        (generated / folder / name).write_bytes(bytes(range(size)))
    return root


def _run(tmp_path: Path, root: Path, lines):
    """tools/export.sh in `root` on fake_tools' stand-ins, the stand-in Godot also writing
    the data packs; the exported Linux build prints `lines` after Godot's banner."""
    bin_dir = fake_tools._stand_ins(tmp_path)
    shutil.move(bin_dir / "godot", bin_dir / "godot-stand-in")
    fake_tools._executable(bin_dir / "godot", PACK_GODOT)
    writer = tmp_path / "pack_writer.py"
    writer.write_text(PACK_WRITER, encoding="utf-8")
    start = tmp_path / "start-output.txt"
    start.write_bytes(fake_tools.start_output(lines).encode("utf-8"))
    env = fake_tools._env(tmp_path, bin_dir, FAKE_START_OUTPUT=start, PACK_WRITER=writer)
    env["PYTHONPATH"] = str(Path(fake_tools.__file__).parent)
    return subprocess.run(  # the caller checks the status
        [fake_tools.BASH, str(root / "tools" / "export.sh")],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        check=False,
    )


def test_every_startup_line_in_order_after_the_pack_lines_passes(tmp_path):
    root = _tree(tmp_path, MANIFEST)
    result = _run(tmp_path, root, (*PACK_LINES, *LINES))
    assert result.returncode == 0, result.stdout
    expecting = [line.removeprefix("expecting: ") for line in result.stdout.splitlines()]
    expecting = [line for line in expecting if line in (*PACK_LINES, *LINES)]
    assert expecting[: len(PACK_LINES) + len(LINES)] == [*PACK_LINES, *LINES]
    for line in (*PACK_LINES, *LINES):
        assert f"started: {line}" in result.stdout


@pytest.mark.parametrize(
    "line, twin",
    [
        (LINES[2], f"mattini {V}: photo village loaded, 15000 x 10000 texels at 0.2 m"),
        (LINES[3], f"mattini {V}: surfaces village loaded, 4000 x 6000 cells at 0.2 m"),
        (LINES[4], f"mattini {V}: trees village loaded, 3 trees in 3 chunks"),
        (LINES[5], f"mattini {V}: roofs village loaded, 4 of 4 buildings coloured"),
        (LINES[5], None),
        (LINES[6], f"mattini {V}: shadows village loaded, 3000 x 2000 cells at 1 m"),
        (LINES[6], f"mattini {V}: shadows village loaded, 2000 x 3000 cells at 0.5 m"),
        (LINES[6], None),
    ],
    ids=[
        "photo-swapped",
        "surfaces-photo-cell",
        "trees-chunks",
        "roofs-total",
        "roofs-missing",
        "shadows-swapped",
        "shadows-cell",
        "shadows-missing",
    ],
)
def test_a_missing_or_wrong_line_fails(tmp_path, line, twin):
    root = _tree(tmp_path, MANIFEST)
    printed = [twin if printed == line else printed for printed in (*PACK_LINES, *LINES)]
    result = _run(tmp_path, root, [p for p in printed if p is not None])
    assert result.returncode != 0
    assert f"did not print its startup line: {line}" in result.stdout


@pytest.mark.parametrize(
    "order",
    [
        (*PACK_LINES, *LINES[:3], LINES[4], LINES[3], *LINES[5:]),
        (*LINES[:2], *PACK_LINES, *LINES[2:]),
        (*PACK_LINES, *LINES[2:], *LINES[:2]),
        (*PACK_LINES, *LINES[:5], LINES[6], LINES[5]),
    ],
    ids=["trees-before-surfaces", "packs-after-m2", "m3-before-m2", "shadows-before-roofs"],
)
def test_a_line_out_of_order_fails(tmp_path, order):
    root = _tree(tmp_path, MANIFEST)
    result = _run(tmp_path, root, order)
    assert result.returncode != 0
    assert "printed its startup line out of order: " in result.stdout


@pytest.mark.parametrize(
    "block, commands",
    [
        ("photo", ["download photo", "photo"]),
        ("surfaces", ["download tlm", "surfaces"]),
        ("trees", ["download surface", "download tlm", "trees"]),
        ("roofs", ["download photo", "roofs"]),
        ("shadows", ["download surface", "shadows"]),
        ("sky", ["sky"]),
    ],
)
def test_a_manifest_without_a_block_is_refused_before_any_export(tmp_path, block, commands):
    manifest = dict(MANIFEST, **{block: None})
    root = _tree(tmp_path, manifest)
    result = _run(tmp_path, root, (*PACK_LINES, *LINES))
    assert result.returncode != 0
    named = ", then ".join(f"{RUN} {command}" for command in commands)
    assert f"has no {block} block: run {named}" in result.stdout
    assert not any("--export-release" in call for call in fake_tools.calls(tmp_path))
    assert not (root / "build").exists()
