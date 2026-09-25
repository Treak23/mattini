"""The manifest re-derives the terrain block's shape (brief M2-06; SPEC §8, the terrain grid).

`manifest` refuses, naming the field, both values and `python -m mattini terrain` and
writing nothing, a terrain description whose `lv95_box` is not the world config's box for
the area (as floats, exact keys), or whose `columns` and `rows` are not
(e_max − e_min) / s + 1 and (n_max − n_min) / s + 1 for the configured spacing s. The world
config it compares with is the one the manifest is written from (`build_manifest` hands
`built_terrain_block` the world it parsed from the bytes whose SHA-256 it writes).

Harm prevented (M2-01 Findings 9, measured by its checker): a description with its box
shifted 1 km, or with its rows and columns swapped (the same product, so the size check
passes), was accepted with the world, spacing, source, lock and heights all matching. The
game would place the village 1 km off, or refuse it, and the manifest would never have
said so. The pipeline's own build writes the shape right, so only a hand-edited or foreign
description gets here.

Both shared fixtures pass: the first at 0.5 m, the second at 2 m, where the rows and
columns differ from what 0.5 m would give, so a rule that ignored the spacing refuses it.

Does NOT prove: anything about the buildings' block (M2-04 has its own checks); that the
game's TerrainGrid checks the shape too (M2-02's fixtures prove the game's placement).
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from mattini.manifest import write_manifest
from mattini.terrain import TerrainError

REPO = Path(__file__).resolve().parents[2]
SHARED = REPO / "tests" / "shared"
TERRAIN_COMMAND = "python -m mattini terrain"
# the two shared fixtures: folder, area, (columns, rows) the world config and spacing give
FIXTURES = {
    "fixture": (SHARED / "terrain_fixture", (41, 24)),  # 20 m × 11.5 m at 0.5 m
    "fixture_nw": (SHARED / "terrain_fixture_nw", (13, 14)),  # 24 m × 26 m at 2 m
}


def _world_box(area: str) -> dict:
    folder, _ = FIXTURES[area]
    world = json.loads((folder / "world.json").read_text(encoding="utf-8"))
    return world["areas"][area]


def _out(tmp_path, area: str) -> Path:
    folder, _ = FIXTURES[area]
    out = tmp_path / "generated"
    shutil.copytree(folder / "generated" / "terrain", out / "terrain")
    return out


def _manifest(out: Path, area: str) -> Path:
    folder, _ = FIXTURES[area]
    return write_manifest(
        out,
        folder / "world.json",
        terrain_config_path=folder / "terrain.json",
        datasets_path=folder / "datasets.json",
        lock_path=folder / "datasets.lock.json",
    )


def _edit_block(out: Path, area: str, change) -> dict:
    path = out / "terrain" / f"{area}.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    change(block)
    path.write_text(json.dumps(block, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))  # as the manifest reads it


def _refused(out: Path, area: str, *parts: str) -> str:
    with pytest.raises(TerrainError) as refused:
        _manifest(out, area)
    message = str(refused.value)
    for part in (TERRAIN_COMMAND, *parts):
        assert part in message, (part, message)
    assert not (out / "manifest.json").exists()
    return message


@pytest.mark.parametrize("area", sorted(FIXTURES))
def test_both_fixtures_have_the_shape_their_world_and_spacing_give(tmp_path, area):
    """Positive control: the fixtures' descriptions pass, and their shape is the formula's."""
    out = _out(tmp_path, area)
    block = json.loads(_manifest(out, area).read_bytes())["terrain"]
    assert block["lv95_box"] == _world_box(area)
    assert (block["columns"], block["rows"]) == FIXTURES[area][1]


@pytest.mark.parametrize(
    ("key", "shift"),
    [("e", 1000.0), ("e", -1000.0), ("n", 1000.0), ("n", -1000.0)],
    ids=["east", "west", "north", "south"],
)
def test_a_box_shifted_by_a_kilometre_is_refused(tmp_path, key, shift):
    """The checker's case: the whole box moved 1 km, its size and so rows and columns kept."""
    out = _out(tmp_path, "fixture")
    world_box = _world_box("fixture")

    def move(block):
        for edge in (f"{key}_min", f"{key}_max"):
            block["lv95_box"][edge] += shift

    block = _edit_block(out, "fixture", move)
    assert block["lv95_box"] != world_box
    _refused(
        out, "fixture", "lv95_box", repr(block["lv95_box"]), repr(dict(sorted(world_box.items())))
    )


@pytest.mark.parametrize("area", sorted(FIXTURES))
def test_rows_and_columns_swapped_are_refused(tmp_path, area):
    """The checker's case: the same product, so the heights file's size still fits."""
    out = _out(tmp_path, area)
    columns, rows = FIXTURES[area][1]
    _edit_block(out, area, lambda b: b.update(columns=rows, rows=columns))
    _refused(out, area, f"columns is {rows},", f"needs {columns}")


@pytest.mark.parametrize(
    ("field", "delta"),
    [("columns", 1), ("columns", -1), ("rows", 1), ("rows", -1)],
    ids=["a-column-more", "a-column-less", "a-row-more", "a-row-less"],
)
def test_each_count_is_checked_on_its_own(tmp_path, field, delta):
    """Each field against its own formula, both values named."""
    out = _out(tmp_path, "fixture")
    columns, rows = FIXTURES["fixture"][1]
    wanted = {"columns": columns, "rows": rows}[field]
    _edit_block(out, "fixture", lambda b: b.update({field: wanted + delta}))
    _refused(out, "fixture", f"{field} is {wanted + delta},", f"needs {wanted}")


@pytest.mark.parametrize(
    "change",
    [
        lambda box: box.update(e_max=box["e_max"] + 0.5),
        lambda box: box.update(n_min=box["n_min"] - 0.5),
        lambda box: box.update(e_min=int(box["e_min"])),
        lambda box: box.update(n_max=str(box["n_max"])),
        lambda box: box.update(height=0.0),
        lambda box: box.pop("n_min"),
        lambda box: box.update(e_min=box.pop("e_max"), e_max=box["e_min"]),
    ],
    ids=[
        "an-edge-moved",
        "another-edge-moved",
        "a-whole-number",
        "a-string",
        "a-key-added",
        "a-key-missing",
        "edges-swapped",
    ],
)
def test_a_box_that_is_not_exactly_the_world_s_is_refused(tmp_path, change):
    """The box as floats with exactly the four keys: what the terrain step writes."""
    out = _out(tmp_path, "fixture")
    block = _edit_block(out, "fixture", lambda b: change(b["lv95_box"]))
    _refused(out, "fixture", "lv95_box", repr(block["lv95_box"]))


def test_a_box_that_is_not_an_object_is_refused(tmp_path):
    out = _out(tmp_path, "fixture")
    box = _world_box("fixture")
    _edit_block(out, "fixture", lambda b: b.update(lv95_box=[box[k] for k in sorted(box)]))
    _refused(out, "fixture", "lv95_box")


@pytest.mark.parametrize("value", [24.0, True, "24", None, 0, -24])
def test_rows_must_be_a_positive_whole_number(tmp_path, value):
    out = _out(tmp_path, "fixture")
    _edit_block(out, "fixture", lambda b: b.update(rows=value))
    _refused(out, "fixture", "rows")


def test_an_area_that_is_not_whole_cells_is_named(tmp_path):
    """A world whose area no grid fits (25 m at 2 m), with a description claiming it.

    The terrain step refuses to build such an area; a foreign description made for it,
    with the world's box and SHA-256, is refused by its column count, which cannot be whole.
    """
    folder, _ = FIXTURES["fixture_nw"]
    world = json.loads((folder / "world.json").read_text(encoding="utf-8"))
    world["areas"]["fixture_nw"]["e_max"] += 1.0
    world_path = tmp_path / "world.json"
    world_path.write_bytes((json.dumps(world, indent=2) + "\n").encode("utf-8"))
    out = _out(tmp_path, "fixture_nw")

    def claim(block):
        block["lv95_box"]["e_max"] += 1.0
        block["world_sha256"] = hashlib.sha256(world_path.read_bytes()).hexdigest()

    _edit_block(out, "fixture_nw", claim)
    with pytest.raises(TerrainError) as refused:
        write_manifest(
            out,
            world_path,
            terrain_config_path=folder / "terrain.json",
            datasets_path=folder / "datasets.json",
            lock_path=folder / "datasets.lock.json",
        )
    message = str(refused.value)
    for part in (TERRAIN_COMMAND, "columns is 13,", "needs 13.5", "not a whole number of 2 m"):
        assert part in message, (part, message)
    assert not (out / "manifest.json").exists()
