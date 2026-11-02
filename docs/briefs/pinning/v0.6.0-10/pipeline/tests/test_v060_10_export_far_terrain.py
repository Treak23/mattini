"""Pinning tests for brief v0.6.0-10: the export and the release's words learn the far terrain.

Pinned decisions (design §3, §5 and §6; brief v0.6.0-10 decisions 1 to 4):
- tools/export.sh's BLOCKS (the blocks the build ships, in the startup lines' order, each with the
  commands that build it) names the nine blocks terrain, buildings, photo, surfaces, trees,
  roofs, shadows, surroundings and sky, in that order, and for each block exactly the commands
  game/scripts/main.gd's `<BLOCK>_FIX` names, in its order (two homes of one list, kept equal: a
  refused export and a refused game say the same commands). The far terrain's are `download
  regio`, `download farphoto`, `surroundings`, `farcolour` (brief v0.6.0-09 decision 2).
- The far terrain's files go into mattini.pck (design §6's batch: no tenth data pack): through
  tools/export.sh on fake_tools' stand-ins, a generated `surroundings/` folder holding the
  heights, their description, the colour JPEG, its KEEP import file and the colour's description
  exports with exit 0, and each build folder's mattini.pck holds the four files, byte for byte,
  at assets/generated/surroundings/<name>, no data pack holds them, and the `.import` file is not
  shipped (step 4c's rule). The heights' size the committed config gives (columns x rows x 4
  bytes) is under step 4c's UNPACKED_LIMIT_BYTES, read from the script.
- docs/RELEASE.md §C, the release gate's words: the regeneration bullet names the downloads and
  the pipeline in the workflow's order (test_release_workflow.py's DOWNLOADS and PIPELINE, so the
  two cannot drift); the designed-values bullet names the far heights' SHA-256 and the far
  colour's pixels' and JPEG's (the first eight hex digits each, from config/surroundings.json);
  the start bullet requires ten startup lines and names the far terrain's line for the real
  village, its numbers those config/surroundings.json gives.

Does NOT prove: that a real export ships the far files (the pin author's probe: Godot 4.6.3's
`--export-pack Linux` of the real far files, step 4c's check on it green; the release gate's
export run); that the real build prints the line (brief v0.6.0-09's rehearsal and the release
gate); that the session pastes 0.6.0's manifest pair into §C (a placeholder until the build go,
said in §C); anything on GitHub.
"""

import hashlib
import json
import platform
import re
import struct

import fake_tools
import pytest
from test_release_workflow import DOWNLOADS, PIPELINE

REPO = fake_tools.REPO
EXPORT = REPO / "tools" / "export.sh"
MAIN = REPO / "game" / "scripts" / "main.gd"
RELEASE_MD = REPO / "docs" / "RELEASE.md"
SURROUNDINGS = REPO / "config" / "surroundings.json"
BLOCK_ORDER = [
    "terrain",
    "buildings",
    "photo",
    "surfaces",
    "trees",
    "roofs",
    "shadows",
    "surroundings",
    "sky",
]
RUN = "uv run --project pipeline python -m mattini "
# The far terrain's generated files as `surroundings` and `farcolour` write them (brief
# v0.6.0-06, -07): small stand-ins of the real files, and the KEEP import file's real bytes.
FAR_FILES = {
    "village.f32": bytes(range(48)),
    "village.json": b'{"a stand-in description": true}\n',
    "village_colour.jpg": b"\xff\xd8 a stand-in JPEG \xff\xd9",
    "village_colour.json": b'{"a stand-in colour description": true}\n',
}
KEEP_IMPORT = b'[remap]\n\nimporter="keep"\n'

linux_bash = pytest.mark.skipif(
    fake_tools.BASH is None or platform.system() != "Linux",
    reason="tools/export.sh runs on Linux with bash",
)


def _blocks():
    """tools/export.sh's BLOCKS: [(block, [commands])], in the script's order."""
    text = EXPORT.read_text(encoding="utf-8")
    found = re.search(r"^BLOCKS=\(\n(.*?)\n\)$", text, re.MULTILINE | re.DOTALL)
    assert found, "tools/export.sh has no BLOCKS=( ... ) array"
    entries = re.findall(r'^\s*"([^"]+)"\s*$', found.group(1), re.MULTILINE)
    return [(entry.split("|")[0], entry.split("|")[1:]) for entry in entries]


def _fixes():
    """main.gd's `const <NAME>_FIX := [RUN + "<command>", ...]`: {name lower-cased: commands}."""
    text = MAIN.read_text(encoding="utf-8")
    fixes = {}
    pattern = re.compile(r"^const ([A-Z]+)_FIX := \[(.*?)\]", re.MULTILINE | re.DOTALL)
    for name, body in pattern.findall(text):
        fixes[name.lower()] = re.findall(r'RUN \+ "([^"]+)"', body)
    assert "surroundings" in fixes, "main.gd has no SURROUNDINGS_FIX"
    return fixes


def test_the_export_ships_nine_blocks_in_the_startup_lines_order():
    assert [block for block, _ in _blocks()] == BLOCK_ORDER


def test_each_block_s_commands_are_the_game_s():
    fixes = _fixes()
    blocks = dict(_blocks())
    assert set(blocks) == set(fixes) - {"manifest"}, (sorted(blocks), sorted(fixes))
    for block, commands in blocks.items():
        assert commands == fixes[block], (block, commands, fixes[block])
    assert blocks["surroundings"] == [
        "download regio",
        "download farphoto",
        "surroundings",
        "farcolour",
    ]


def _pack_directory(path):
    """{path without res://: (size, MD5)} of a Godot 4.6.3 pack (format 3), as step 4c reads it."""
    data = path.read_bytes()
    base, directory = struct.unpack_from("<QQ", data, 24)
    (count,) = struct.unpack_from("<I", data, directory)
    at, entries = directory + 4, {}
    for _ in range(count):
        (length,) = struct.unpack_from("<I", data, at)
        name = data[at + 4 : at + 4 + length].rstrip(b"\0").decode("utf-8")
        offset, size = struct.unpack_from("<QQ", data, at + 4 + length)
        md5 = data[at + 20 + length : at + 36 + length].hex()
        entries[name.removeprefix("res://")] = (size, md5, base + offset)
        at += 40 + length
    return entries


@linux_bash
def test_the_far_terrain_s_files_ship_in_mattini_pck(tmp_path):
    templates = tmp_path / "xdg" / "godot" / "export_templates" / "4.6.3.stable"
    root = fake_tools.export_tree(tmp_path, templates)
    far = root / "game" / "assets" / "generated" / "surroundings"
    far.mkdir()
    for name, data in FAR_FILES.items():
        (far / name).write_bytes(data)
    (far / "village_colour.jpg.import").write_bytes(KEEP_IMPORT)
    done = fake_tools.run_export(tmp_path, root, fake_tools.start_output())
    assert done.returncode == 0, done.stdout[-3000:]
    for folder in ("linux", "windows"):
        build = root / "build" / folder
        main = _pack_directory(build / "mattini.pck")
        for name, data in FAR_FILES.items():
            held = main.get(f"assets/generated/surroundings/{name}")
            assert held is not None, f"{folder}: mattini.pck lacks surroundings/{name}"
            assert held[:2] == (len(data), hashlib.md5(data).hexdigest()), (folder, name)
        assert not any(path.endswith(".import") for path in main), f"{folder}: an .import shipped"
        for pack in sorted(build.glob("mattini-*.pck")):
            assert not any("surroundings/" in path for path in _pack_directory(pack)), pack.name


def test_the_far_heights_are_under_step_4c_s_limit():
    text = EXPORT.read_text(encoding="utf-8")
    limit = re.search(r"^UNPACKED_LIMIT_BYTES=(\d+)$", text, re.MULTILINE)
    assert limit, "tools/export.sh has no UNPACKED_LIMIT_BYTES"
    for area, config in json.loads(SURROUNDINGS.read_text(encoding="utf-8"))["areas"].items():
        size = config["expected_columns"] * config["expected_rows"] * 4
        assert size < int(limit.group(1)), (area, size)


def _section_c():
    text = RELEASE_MD.read_text(encoding="utf-8")
    start = text.index("\n## C. ")
    return text[start : text.index("\n## ", start + 1)]


def _bullet(containing):
    """The one checklist bullet of §C (from its `- [ ]` to the next) holding `containing`."""
    bullets = [b for b in re.split(r"\n- \[ \] ", _section_c()) if containing in b]
    assert len(bullets) == 1, f"one bullet of §C holds {containing!r}: {len(bullets)}"
    return bullets[0]


def test_section_c_names_the_downloads_and_the_pipeline_in_the_workflow_s_order():
    spans = re.findall(r"`([^`\n]+)`", _bullet("regenerated by the pipeline"))
    downloads = [span for span in spans if span.startswith("download ")]
    steps = [span for span in spans if re.fullmatch(r"[a-z]+", span)]
    assert downloads == [f"download {name}" for name in DOWNLOADS], downloads
    assert steps == PIPELINE, steps


def _village():
    return json.loads(SURROUNDINGS.read_text(encoding="utf-8"))["areas"]["village"]


def test_section_c_names_the_far_terrain_s_designed_values():
    bullet = _bullet("designed value")
    village = _village()
    colour = village["colour"]
    for sha in (
        village["expected_sha256"],
        colour["expected_pixels_sha256"],
        colour["expected_sha256"],
    ):
        assert re.search(rf"`{sha[:8]}…`", bullet), f"§C names {sha[:8]}…"
    assert "config/surroundings.json" in bullet


def test_section_c_requires_ten_startup_lines_with_the_far_terrain_s():
    bullet = _bullet("--quit-after 300")
    village = _village()
    colour = village["colour"]
    line = (
        f"mattini <version>: surroundings village loaded, {village['expected_columns']} x "
        f"{village['expected_rows']} vertices at {village['spacing_m']} m, colour "
        f"{colour['expected_columns']} x {colour['expected_rows']} at {colour['cell_m']} m"
    )
    assert re.search(r"\bten startup lines\b", " ".join(bullet.split())), bullet
    assert line in " ".join(bullet.split()), f"§C names the line {line}"
