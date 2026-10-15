"""`built_roofs_block`: what the manifest may take from built roof colours (brief M3-05).

The description is read back through the configs, the lock and the buildings' own
description. With no `roofs/<area>.json` the result is None; with one and no built buildings
it is a refusal naming `python -m mattini buildings`. Before the description is read, in this
order: the world config (design's step), the fit of both lock entries (naming its lock
command, a lock without an entry never a KeyError), then the entries (design's step). Then
every way the description no longer matches names `python -m mattini roofs`: its key sets,
area, format, world config and box, its source against the datasets config and the lock's
sheets and tiles, its chunks' and buildings' shapes, the file's SHA-256 against the roofs
config, and its chunks against the buildings' (the same tiles in order, and per chunk the
same count of buildings and sums of triangles and vertices).

Does NOT prove: the manifest's wiring (brief M3-13); that the file holds the right colours
(the SHA-256 against design's value does, while it stands).
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from roofs_inputs import AREA, GENERATED, canonical, make_inputs

from mattini import roofs
from mattini.roofs import RoofsError, built_roofs_block

ROOFS = "python -m mattini roofs"
BUILDINGS = "python -m mattini buildings"
LOCK_BUILDINGS = "python -m mattini lock buildings"
LOCK_PHOTO = "python -m mattini lock photo"


@pytest.fixture(scope="module")
def case(tmp_path_factory):
    return make_inputs(tmp_path_factory.mktemp("roofs_block"))


@pytest.fixture(scope="module")
def buildings_block():
    return json.loads((GENERATED / "buildings" / "fixture.json").read_text(encoding="utf-8"))


def _write(out: Path, data: bytes) -> None:
    (out / "roofs").mkdir(parents=True, exist_ok=True)
    (out / "roofs" / "fixture.json").write_bytes(data)


@pytest.fixture
def out(case, tmp_path) -> Path:
    _write(tmp_path, case["data"])
    return tmp_path


def _built(case, out, buildings_block, *, lock=None, config=None, world_sha256=None):
    return built_roofs_block(
        out,
        case["config"] if config is None else config,
        case["terrain"],
        case["world"],
        case["world_sha256"] if world_sha256 is None else world_sha256,
        case["datasets"],
        case["lock"] if lock is None else lock,
        buildings_block,
    )


def _edited(case, out: Path, edit, *, fix_sha=True) -> dict:
    """Edit the description in place; the config then expects the edited file, so that the
    check under test is the one that is not the SHA-256's (unless `fix_sha` is False)."""
    block = copy.deepcopy(case["block"])
    edit(block)
    data = canonical(block)
    _write(out, data)
    config = copy.deepcopy(case["config"])
    if fix_sha:
        config["areas"][AREA]["expected_sha256"] = hashlib.sha256(data).hexdigest()
    return config


def test_the_expected_description_is_accepted(case, out, buildings_block):
    assert _built(case, out, buildings_block) == case["block"]


def test_nothing_built_is_none_whatever_else_is_missing(case, tmp_path):
    assert _built(case, tmp_path, None) is None


def test_roof_colours_without_buildings_are_refused_naming_the_buildings(case, out):
    with pytest.raises(RoofsError) as refusal:
        _built(case, out, None)
    assert BUILDINGS in str(refusal.value) and ROOFS not in str(refusal.value)


def test_a_changed_world_is_design_s_step_and_comes_before_the_rest(case, out, buildings_block):
    lock = copy.deepcopy(case["lock"])
    del lock["datasets"]["swissimage"]
    (out / "roofs" / "fixture.json").write_text("{", encoding="utf-8")
    with pytest.raises(RoofsError) as refusal:
        _built(case, out, buildings_block, lock=lock, world_sha256="0" * 64)
    message = str(refusal.value)
    assert "config/world.json" in message and "design" in message and LOCK_PHOTO not in message


@pytest.mark.parametrize(
    ("dataset", "command"),
    [("swissbuildings3d", LOCK_BUILDINGS), ("swissimage", LOCK_PHOTO)],
)
def test_a_lock_without_an_entry_is_refused_naming_its_lock_command(
    case, out, buildings_block, dataset, command
):
    lock = copy.deepcopy(case["lock"])
    del lock["datasets"][dataset]
    with pytest.raises(RoofsError) as refusal:
        _built(case, out, buildings_block, lock=lock)
    assert command in str(refusal.value) and "design" not in str(refusal.value)


@pytest.mark.parametrize(
    ("dataset", "key", "value", "command"),
    [
        ("swissbuildings3d", "edition", "2015", LOCK_BUILDINGS),
        ("swissbuildings3d", "collection", "ch.swisstopo.x", LOCK_BUILDINGS),
        ("swissimage", "edition", "2020", LOCK_PHOTO),
        ("swissimage", "resolution_m", 0.2, LOCK_PHOTO),
        ("swissimage", "collection", "ch.swisstopo.x", LOCK_PHOTO),
    ],
)
def test_a_lock_that_does_not_fit_is_named_before_the_inputs_and_the_description(
    case, out, buildings_block, dataset, key, value, command
):
    lock = copy.deepcopy(case["lock"])
    lock["datasets"][dataset][key] = value
    (out / "roofs" / "fixture.json").write_text("{", encoding="utf-8")
    with pytest.raises(RoofsError) as refusal:
        _built(case, out, buildings_block, lock=lock)
    assert command in str(refusal.value) and "design" not in str(refusal.value)


def test_other_inputs_are_design_s_step_not_the_rebuild(case, out, buildings_block):
    lock = copy.deepcopy(case["lock"])
    lock["datasets"]["swissimage"]["tiles"]["2650-1149"]["sha256"] = "6" * 64
    with pytest.raises(RoofsError) as refusal:
        _built(case, out, buildings_block, lock=lock)
    message = str(refusal.value)
    assert "config/roofs.json" in message and "design" in message and ROOFS not in message


def test_a_lock_given_as_a_path_is_read_only_for_built_roofs(
    case, out, tmp_path, buildings_block, monkeypatch
):
    read = []

    def load_lock(path):
        read.append(path)
        return case["lock"]

    monkeypatch.setattr(roofs, "load_lock", load_lock)
    lock_path = tmp_path / "lock.json"
    assert _built(case, tmp_path / "nothing", None, lock=lock_path) is None
    assert read == []
    assert _built(case, out, buildings_block, lock=lock_path) == case["block"]
    assert read == [lock_path]


def _set(key, value):
    def edit(block):
        block[key] = value

    return edit


def _source(part, key, value):
    def edit(block):
        block["source"][part][key] = value

    return edit


def _drop_source_key(part, key):
    def edit(block):
        del block["source"][part][key]

    return edit


def _first_building(change):
    def edit(block):
        change(block["chunks"][0]["buildings"][0])

    return edit


def _first_chunk(change):
    def edit(block):
        change(block["chunks"][0])

    return edit


def _swap_chunks(block):
    block["chunks"][0], block["chunks"][1] = block["chunks"][1], block["chunks"][0]


def _duplicate_building(block):
    buildings = block["chunks"][0]["buildings"]
    buildings.append(copy.deepcopy(buildings[0]))


def _unsort_buildings(block):
    buildings = block["chunks"][0]["buildings"]
    buildings[0], buildings[1] = buildings[1], buildings[0]


def _roof(value):
    return _first_building(lambda b: b.update(roof=value))


DESCRIPTION_EDITS = [
    ("area", _set("area", "other")),
    ("format", _set("format", "roofs-v2")),
    ("world", _set("world_sha256", "0" * 64)),
    ("extra-key", _set("note", "x")),
    ("box-moved", _set("lv95_box", {"e_max": 1.0, "e_min": 0.0, "n_max": 1.0, "n_min": 0.0})),
    ("box-ints", lambda b: b.update(lv95_box={k: int(v) for k, v in b["lv95_box"].items()})),
    ("source-not-an-object", _set("source", [])),
    ("source-extra-part", lambda b: b["source"].update(trees={})),
    ("buildings-edition", _source("buildings", "edition", "2015")),
    ("buildings-collection", _source("buildings", "collection", "ch.swisstopo.x")),
    ("buildings-attribution", _source("buildings", "attribution", "someone")),
    ("buildings-dataset", _source("buildings", "dataset", "swissimage")),
    ("buildings-no-sheets", _drop_source_key("buildings", "sheets")),
    (
        "buildings-other-sheet",
        _source("buildings", "sheets", [{"sha256": "7" * 64, "sheet": "1249-42"}]),
    ),
    ("buildings-no-sheet", _source("buildings", "sheets", [])),
    ("photo-edition", _source("photo", "edition", "2020")),
    ("photo-resolution", _source("photo", "resolution_m", 0.2)),
    ("photo-dataset", _source("photo", "dataset", "swissalti3d")),
    ("photo-no-tiles", _drop_source_key("photo", "tiles")),
    ("photo-fewer-tiles", lambda b: b["source"]["photo"]["tiles"].pop()),
    ("photo-reversed-tiles", lambda b: b["source"]["photo"]["tiles"].reverse()),
    ("chunks-not-a-list", _set("chunks", {})),
    ("chunk-extra-key", _first_chunk(lambda c: c.update(file="x"))),
    ("chunk-bad-tile", _first_chunk(lambda c: c.update(tile="2650/1149"))),
    ("chunk-buildings-not-a-list", _first_chunk(lambda c: c.update(buildings={}))),
    ("chunks-swapped", _swap_chunks),
    ("building-extra-key", _first_building(lambda b: b.update(note="x"))),
    ("building-no-uuid", _first_building(lambda b: b.update(uuid=""))),
    ("negative-pixels", _first_building(lambda b: b.update(roof_pixels=-1))),
    ("float-triangles", _first_building(lambda b: b.update(triangles=16.0))),
    ("bool-vertices", _first_building(lambda b: b.update(vertices=True))),
    ("roof-empty-string", _roof("")),
    ("roof-upper-case", _roof("AABBCC")),
    ("roof-short", _roof("abc")),
    ("roof-hash", _roof("#aabbcc")),
    ("colour-without-pixels", _first_building(lambda b: b.update(roof_pixels=0))),
    ("pixels-without-colour", _roof(None)),
    ("buildings-unsorted", _unsort_buildings),
    ("building-twice", _duplicate_building),
]


@pytest.mark.parametrize(
    "edit", [e for _, e in DESCRIPTION_EDITS], ids=[name for name, _ in DESCRIPTION_EDITS]
)
def test_a_description_that_no_longer_matches_is_refused_naming_the_rebuild(
    case, out, buildings_block, edit
):
    config = _edited(case, out, edit)
    with pytest.raises(RoofsError, match=ROOFS):
        _built(case, out, buildings_block, config=config)


@pytest.mark.parametrize("text", [b"{", b"[]", b"\xff"], ids=["not-json", "not-an-object", "bytes"])
def test_a_description_that_is_not_an_object_is_refused(case, out, buildings_block, text):
    _write(out, text)
    with pytest.raises(RoofsError, match=ROOFS):
        _built(case, out, buildings_block)


def test_a_file_that_is_not_design_s_is_refused_even_when_it_is_well_formed(
    case, out, buildings_block
):
    config = _edited(
        case, out, _first_building(lambda b: b.update(roof="010203")), fix_sha=False
    )  # the config still expects design's bytes
    with pytest.raises(RoofsError) as refusal:
        _built(case, out, buildings_block, config=config)
    message = str(refusal.value)
    assert ROOFS in message and "expects" in message
    assert config["areas"][AREA]["expected_sha256"] in message


def test_chunks_that_are_not_the_buildings_are_refused_naming_the_rebuild(
    case, out, buildings_block
):
    for number, edit in enumerate(
        (
            lambda b: b["chunks"].pop(),
            lambda b: b["chunks"][0]["buildings"].pop(),
            lambda b: b["chunks"][0]["buildings"][0].update(triangles=999),
            lambda b: b["chunks"][0]["buildings"][0].update(vertices=1),
        )
    ):
        config = _edited(case, out, edit)
        with pytest.raises(RoofsError, match=ROOFS) as refusal:
            _built(case, out, buildings_block, config=config)
        assert "buildings" in str(refusal.value), number


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["chunks"].pop(),
        lambda b: b["chunks"][0].update(tile="2650-1148"),
        lambda b: b["chunks"][0].update(buildings=b["chunks"][0]["buildings"] + 1),
        lambda b: b["chunks"][0].update(triangles=b["chunks"][0]["triangles"] + 1),
        lambda b: b["chunks"][0].update(vertices=b["chunks"][0]["vertices"] - 1),
        lambda b: b.pop("chunks"),
    ],
    ids=[
        "fewer-chunks",
        "other-tile",
        "more-buildings",
        "more-triangles",
        "fewer-vertices",
        "none",
    ],
)
def test_other_buildings_than_the_roofs_were_built_for_are_refused(
    case, out, buildings_block, change
):
    other = copy.deepcopy(buildings_block)
    change(other)
    with pytest.raises(RoofsError, match=ROOFS):
        _built(case, out, other)


def test_a_config_for_another_area_is_refused_naming_both(case, out, buildings_block):
    config = {"schema": 1, "areas": {"other": case["config"]["areas"][AREA]}}
    with pytest.raises(RoofsError) as refusal:
        _built(case, out, buildings_block, config=config)
    assert "other" in str(refusal.value) and AREA in str(refusal.value)
