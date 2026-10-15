"""`built_photo_block`: what the manifest may take from a built photo (brief M3-04).

A built photo is read back through the configs and the lock, and refused naming
`python -m mattini photo` for each way it no longer matches them: a description whose key
set, area, file, format, JPEG settings, cell, world, box, columns, rows or source differ,
tiles that are not the area's in order with the lock's SHA-256s, a `pixels_sha256` or JPEG
that is not design's, and a `.import` file beside the JPEG that is missing or not Godot's
"keep" (without it Godot imports the JPEG as a 170 MB texture and an export ships that
instead of the file, brain.md H24). Before the description is read, a changed world and
inputs are design's step and a lock that does not fit is `python -m mattini lock photo`.
The lock may be given as a path, then it is read only for a built photo.

Does NOT prove: that the JPEG decodes to the pixels the description claims (design's JPEG
SHA-256 does, while the expected values stand); the manifest's wiring (brief M3-13).
"""

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from computed_for import computed_for
from test_photo_fixture import FIXTURE, GENERATED, _block, _config, _lock

from mattini import photo
from mattini.datasets import load_datasets
from mattini.photo import PhotoError, built_photo_block
from mattini.world import load_world

REBUILD = "python -m mattini photo"
KEEP = b'[remap]\n\nimporter="keep"\n'


def _world_sha256() -> str:
    return hashlib.sha256((FIXTURE / "world.json").read_bytes()).hexdigest()


def _built(out: Path, config=None, lock=None, world_sha256=None) -> dict | None:
    return built_photo_block(
        out,
        _config() if config is None else config,
        load_world(FIXTURE / "world.json"),
        _world_sha256() if world_sha256 is None else world_sha256,
        load_datasets(FIXTURE / "datasets.json"),
        _lock() if lock is None else lock,
    )


@pytest.fixture
def built(tmp_path) -> Path:
    shutil.copytree(GENERATED / "photo", tmp_path / "photo")
    return tmp_path


def _describe(out: Path, **change) -> None:
    path = out / "photo" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    for key, value in change.items():
        block[key] = value(block[key]) if callable(value) else value
    path.write_text(json.dumps(block, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_the_unchanged_copy_is_accepted(built):
    assert _built(built) == _block()


@pytest.mark.parametrize(
    ("key", "change"),
    [
        ("area", "other"),
        ("file", "photo/other.jpg"),
        ("format", "png"),
        ("world_sha256", "0" * 64),
        ("cell_m", 0.5),
        ("cell_m", "0.2"),
        ("columns", lambda v: v + 1),
        ("columns", 80.0),
        ("rows", lambda v: v - 1),
        ("rows", "40"),
        ("lv95_box", lambda b: {**b, "e_min": b["e_min"] + 0.2}),
        ("lv95_box", lambda b: {k: int(v) for k, v in b.items()}),
        ("lv95_box", lambda b: {k: v for k, v in b.items() if k != "n_max"}),
        ("jpeg", {"quality": 90, "subsampling": "4:2:0"}),
        ("jpeg", {"quality": 92, "subsampling": "4:4:4"}),
        ("jpeg", {"quality": 92}),
        ("pixels_sha256", "0" * 64),
        ("sha256", "0" * 64),
        ("source", "none"),
        ("source", lambda s: {**s, "edition": "2020"}),
        ("source", lambda s: {**s, "collection": "ch.swisstopo.other"}),
        ("source", lambda s: {**s, "attribution": "someone"}),
        ("source", lambda s: {**s, "dataset": "swissalti3d"}),
        ("source", lambda s: {**s, "resolution_m": 0.2}),
        ("source", lambda s: {**s, "note": "x"}),
        ("source", lambda s: {**s, "tiles": []}),
        ("source", lambda s: {**s, "tiles": [{"tile": "2610-1170"}]}),
        ("source", lambda s: {**s, "tiles": [{"tile": "2610-1171", "sha256": "1" * 64}]}),
        ("source", lambda s: {**s, "tiles": [{**s["tiles"][0], "sha256": "5" * 64}]}),
    ],
    ids=lambda v: v if isinstance(v, str) and len(v) < 20 else None,
)
def test_a_description_that_no_longer_matches_is_refused_naming_the_rebuild(built, key, change):
    _describe(built, **{key: change})
    with pytest.raises(PhotoError, match=REBUILD):
        _built(built)


def test_an_extra_or_missing_key_is_refused(built):
    path = built / "photo" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**block, "extra": 1}), encoding="utf-8")
    with pytest.raises(PhotoError, match=REBUILD):
        _built(built)
    del block["rows"]
    path.write_text(json.dumps(block), encoding="utf-8")
    with pytest.raises(PhotoError, match=REBUILD):
        _built(built)


@pytest.mark.parametrize("text", ["{", "[]", "\xff"], ids=["not-json", "not-an-object", "bytes"])
def test_a_description_that_is_not_an_object_is_refused(built, text):
    (built / "photo" / "fixture.json").write_bytes(text.encode("latin-1"))
    with pytest.raises(PhotoError, match=REBUILD):
        _built(built)


def test_a_missing_import_file_is_refused_naming_it(built):
    (built / "photo" / "fixture.jpg.import").unlink()
    with pytest.raises(PhotoError, match=REBUILD) as refusal:
        _built(built)
    assert "fixture.jpg.import" in str(refusal.value)


@pytest.mark.parametrize(
    "text",
    [b"", KEEP.replace(b"keep", b"texture"), KEEP + b"\n", KEEP.replace(b"\n", b"\r\n")],
    ids=["empty", "texture", "extra-line", "crlf"],
)
def test_an_import_file_that_is_not_the_keep_remap_is_refused(built, text):
    (built / "photo" / "fixture.jpg.import").write_bytes(text)
    with pytest.raises(PhotoError, match=REBUILD) as refusal:
        _built(built)
    assert "fixture.jpg.import" in str(refusal.value)


def test_a_missing_jpeg_is_refused(built):
    (built / "photo" / "fixture.jpg").unlink()
    with pytest.raises(PhotoError, match=REBUILD):
        _built(built)


def test_a_jpeg_design_does_not_expect_is_refused_even_when_the_description_names_it(built):
    jpeg = built / "photo" / "fixture.jpg"
    other = bytes(jpeg.read_bytes()) + b"\x00"
    jpeg.write_bytes(other)
    _describe(built, sha256=hashlib.sha256(other).hexdigest())
    with pytest.raises(PhotoError, match=REBUILD) as refusal:
        _built(built)
    assert "expects" in str(refusal.value)


def test_a_changed_world_is_design_s_step_and_comes_before_the_block(built):
    (built / "photo" / "fixture.json").write_text("{", encoding="utf-8")
    with pytest.raises(PhotoError) as refusal:
        _built(built, world_sha256="0" * 64)
    assert "config/world.json" in str(refusal.value) and "design" in str(refusal.value)


def test_a_lock_that_does_not_fit_is_named_before_the_inputs_and_the_block(built):
    lock = copy.deepcopy(_lock())
    lock["datasets"]["swissimage"]["tiles"]["2610-1171"] = {"file": "x.tif", "sha256": "1" * 64}
    (built / "photo" / "fixture.json").write_text("{", encoding="utf-8")
    with pytest.raises(PhotoError) as refusal:
        _built(built, lock=lock)
    assert "python -m mattini lock photo" in str(refusal.value)
    assert "design" not in str(refusal.value)


def test_other_inputs_are_design_s_step(built):
    lock = copy.deepcopy(_lock())
    lock["datasets"]["swissimage"]["tiles"]["2610-1170"]["file"] = "another.u8"
    with pytest.raises(PhotoError) as refusal:
        _built(built, lock=lock)
    assert "config/photo.json" in str(refusal.value) and "design" in str(refusal.value)
    assert REBUILD not in str(refusal.value)


def test_the_config_records_what_the_values_were_computed_for_not_the_block():
    """The stand-in for the manifest's check: an input recorded in `computed_for` is the
    lock's entry and the world config's bytes, computed outside the pipeline."""
    assert _config()["areas"]["fixture"]["computed_for"] == computed_for(
        FIXTURE / "world.json", _lock(), "swissimage"
    )


def test_a_lock_given_as_a_path_is_read_only_for_a_built_photo(built, tmp_path, monkeypatch):
    read = []

    def load_lock(path):
        read.append(path)
        return _lock()

    monkeypatch.setattr(photo, "load_lock", load_lock)
    lock_path = tmp_path / "lock.json"
    assert _built(tmp_path / "nothing-built", lock=lock_path) is None
    assert read == []
    assert _built(built, lock=lock_path) == _block()
    assert read == [lock_path]
