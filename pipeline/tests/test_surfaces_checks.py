"""Brief M3-06: the surfaces step's checks come in their order, and its output is what is pinned.

The shared fixture's synthetic TLM is written as a zipped FileGDB in `download tlm`'s layout
(brief M3-03). Pinned decisions (the brief, SPEC §8): a missing download is refused before
anything is created, not even the output folder, and before any progress line; the file's
size is compared with provenance.json's before the file is hashed; its SHA-256 before it is
read; after the read its (size, mtime_ns, inode) must be what they were; the files are written
`.png.import`, `.png`, `.json`, each through a `.part` rename; a lock without the TLM entry
is refused naming `python -m mattini lock tlm`, never a KeyError. `built_surfaces_block`
refuses a built description that does not match, naming the rebuild, and a world or lock
that is not the one the expected values were computed for, naming design's step.

Does NOT prove: the command line and the manifest wiring (brief M3-13); the reader on
swisstopo's own file (the real-data gate in the brief's Findings).
"""

import hashlib
import json
import os
import shutil
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from computed_for import recorded
from synthetic_tlm import zipped_tlm

from mattini import surfaces
from mattini.surfaces import (
    SurfacesError,
    build_surfaces,
    built_surfaces_block,
    load_surfaces_config,
)
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surfaces_fixture"
GENERATED = FIXTURE / "generated"
ZIP_NAME = "swisstlm3d_2026-02_2056_5728.gdb.zip"
REBUILD = "python -m mattini surfaces"
DOWNLOAD = "python -m mattini download tlm"
LOCK_TLM = "python -m mattini lock tlm"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _case(tmp_path: Path) -> SimpleNamespace:
    """Everything a build needs: the fixture's world, datasets, lock and config, and a raw
    folder as `download tlm` leaves it (flat provenance.json beside the zip)."""
    world = load_world(FIXTURE / "world.json")
    source = json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))
    (tmp_path / "make").mkdir()
    data = zipped_tlm(tmp_path / "make", source, zip_name=ZIP_NAME).read_bytes()
    folder = tmp_path / "raw" / "swisstlm3d" / "2026-02"
    folder.mkdir(parents=True)
    (folder / ZIP_NAME).write_bytes(data)
    provenance = {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swisstlm3d",
        "dataset": "swisstlm3d",
        "edition": "2026-02",
        "file": ZIP_NAME,
        "item": "swisstlm3d_2026-02",
        "schema": 1,
        "sha256": _sha(data),
        "size_bytes": len(data),
        "url": f"https://data.geo.admin.ch/ch.swisstopo.swisstlm3d/swisstlm3d_2026-02/{ZIP_NAME}",
    }
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    entry = {
        "collection": "ch.swisstopo.swisstlm3d",
        "edition": "2026-02",
        "file": ZIP_NAME,
        "sha256": _sha(data),
    }
    lock = {"schema": 1, "datasets": {"swisstlm3d": entry}}
    datasets = json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]
    config = recorded(load_surfaces_config(FIXTURE / "surfaces.json"), world, lock, "swisstlm3d")
    return SimpleNamespace(
        world=world,
        datasets=datasets,
        lock=lock,
        config=config,
        raw=tmp_path / "raw",
        out=tmp_path / "out",
        zip=folder / ZIP_NAME,
        provenance=folder / "provenance.json",
    )


def _build(case, **keywords):
    return build_surfaces(
        case.world, case.datasets, case.lock, case.config, case.raw, case.out, **keywords
    )


def _rewrite_provenance(case, **changes) -> None:
    provenance = json.loads(case.provenance.read_text(encoding="utf-8"))
    case.provenance.write_text(json.dumps({**provenance, **changes}), encoding="utf-8")


# ----------------------------------------------------------------------- the step's order


def test_a_missing_download_is_refused_before_anything_is_created_or_said(tmp_path):
    case = _case(tmp_path)
    shutil.rmtree(case.raw)
    said: list[str] = []
    with pytest.raises(SurfacesError, match=DOWNLOAD) as refusal:
        _build(case, progress=said.append)
    assert "provenance.json" in str(refusal.value)
    assert said == [], "no progress line before the checks of the download have passed"
    assert not case.out.exists(), "not even the output folder"


def test_a_missing_file_with_its_provenance_is_refused_naming_the_download(tmp_path):
    case = _case(tmp_path)
    case.zip.unlink()
    said: list[str] = []
    with pytest.raises(SurfacesError, match=DOWNLOAD):
        _build(case, progress=said.append)
    assert said == [] and not case.out.exists()


def test_the_progress_lines_come_in_order_and_the_hash_comes_before_the_read(tmp_path, monkeypatch):
    case = _case(tmp_path)
    events: list[str] = []
    real_hash, real_read = surfaces._sha256_of, surfaces.read_tlm
    monkeypatch.setattr(surfaces, "_sha256_of", lambda p: (events.append("hash"), real_hash(p))[1])
    monkeypatch.setattr(surfaces, "read_tlm", lambda *a: (events.append("read"), real_read(*a))[1])
    said: list[str] = []
    _build(case, progress=lambda line: (events.append("say"), said.append(line)))
    assert events == ["say", "hash", "say", "read", "say", "say", "say"]
    starts = [
        "checking the SHA-256 of",
        "reading",
        "read ",
        "the classes have the SHA-256",
        "wrote",
    ]
    assert len(said) == len(starts) and all(
        s.startswith(p) for s, p in zip(said, starts, strict=True)
    )


def test_a_size_that_differs_is_refused_before_the_file_is_hashed(tmp_path, monkeypatch):
    case = _case(tmp_path)
    size = case.zip.stat().st_size
    _rewrite_provenance(case, size_bytes=size + 1)

    def no_hashing(path):
        raise AssertionError("the file was hashed before its size was compared")

    monkeypatch.setattr(surfaces, "_sha256_of", no_hashing)
    with pytest.raises(SurfacesError, match=DOWNLOAD) as refusal:
        _build(case)
    assert f"{size} bytes" in str(refusal.value) and f"lists {size + 1}" in str(refusal.value)
    assert not case.out.exists()


@pytest.mark.parametrize("size", [0, -5, True, 1.5, "7", None])
def test_a_provenance_without_a_size_is_refused(tmp_path, size):
    case = _case(tmp_path)
    _rewrite_provenance(case, size_bytes=size)
    with pytest.raises(SurfacesError, match="size_bytes"):
        _build(case)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("dataset", "swissalti3d"),
        ("collection", "ch.swisstopo.other"),
        ("edition", "2025-08"),
        ("file", "another.gdb.zip"),
    ],
)
def test_a_provenance_for_something_else_is_refused_naming_the_download(tmp_path, key, value):
    case = _case(tmp_path)
    _rewrite_provenance(case, **{key: value})
    with pytest.raises(SurfacesError, match=DOWNLOAD) as refusal:
        _build(case)
    assert key in str(refusal.value) and repr(value) in str(refusal.value)


def test_a_provenance_that_is_not_json_or_not_an_object_is_refused(tmp_path):
    case = _case(tmp_path)
    for text in ("{broken", "[1, 2]"):
        case.provenance.write_text(text, encoding="utf-8")
        with pytest.raises(SurfacesError, match=DOWNLOAD):
            _build(case)
    assert not case.out.exists()


def test_the_checksum_may_be_written_in_upper_case_in_provenance(tmp_path):
    """swisstopo writes some checksums in upper case (brain.md H20); the lock stores lower."""
    case = _case(tmp_path)
    provenance = json.loads(case.provenance.read_text(encoding="utf-8"))
    _rewrite_provenance(case, sha256=provenance["sha256"].upper())
    assert _build(case)["source"]["sha256"] == case.lock["datasets"]["swisstlm3d"]["sha256"]


@pytest.mark.parametrize("how", ["touched", "grown"])
def test_a_file_that_changes_while_it_is_read_is_refused(tmp_path, monkeypatch, how):
    case = _case(tmp_path)
    real_read = surfaces.read_tlm

    def read_then_change(path, layers, box):
        found = real_read(path, layers, box)
        if how == "touched":
            status = os.stat(path)
            os.utime(path, ns=(status.st_atime_ns, status.st_mtime_ns + 5_000_000_000))
        else:
            with open(path, "ab") as file:
                file.write(b"x")
        return found

    monkeypatch.setattr(surfaces, "read_tlm", read_then_change)
    with pytest.raises(SurfacesError, match="changed while it was read") as refusal:
        _build(case)
    assert DOWNLOAD in str(refusal.value)
    assert not case.out.exists(), "nothing is written for a file that moved under the read"


def test_a_lock_without_the_tlm_entry_is_refused_naming_the_lock_command(tmp_path):
    case = _case(tmp_path)
    case.lock = {"schema": 1, "datasets": {}}
    with pytest.raises(SurfacesError, match=LOCK_TLM) as refusal:
        _build(case)
    assert "no 'swisstlm3d' entry" in str(refusal.value)


def test_a_lock_for_another_edition_is_refused_before_the_inputs_are_compared(tmp_path):
    case = _case(tmp_path)
    case.lock["datasets"]["swisstlm3d"]["edition"] = "2025-08"
    with pytest.raises(SurfacesError, match=LOCK_TLM) as refusal:
        _build(case)
    assert "2025-08" in str(refusal.value) and "computed from" not in str(refusal.value)


def test_a_datasets_config_without_the_tlm_is_refused_naming_the_config(tmp_path):
    case = _case(tmp_path)
    case.datasets = {}
    with pytest.raises(SurfacesError, match=r"config/datasets\.json"):
        _build(case)
    case.datasets = {"swisstlm3d": {"collection": "c", "edition": "2026-02"}}
    with pytest.raises(SurfacesError, match="attribution"):
        _build(case)
    assert not case.out.exists()


def test_other_axes_are_refused_before_anything_else(tmp_path):
    case = _case(tmp_path)
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["axes"] = {"x": "+n", "y": "+h", "z": "+e"}  # a proper rotation, not the owner's
    path = tmp_path / "rotated.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    case.world = load_world(path)
    with pytest.raises(SurfacesError, match="only the axes x = \\+e, y = \\+h, z = -n"):
        _build(case)
    assert not case.out.exists()


def test_a_box_that_is_not_whole_cells_is_refused(tmp_path):
    case = _case(tmp_path)
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["areas"]["fixture"]["e_max"] += 0.1
    path = tmp_path / "odd.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    case.world = load_world(path)
    with pytest.raises(SurfacesError, match="whole number of 0.2 m cells"):
        _build(case)
    assert not case.out.exists()


def test_the_configured_area_must_be_in_the_world(tmp_path):
    case = _case(tmp_path)
    case.config["areas"] = {"elsewhere": case.config["areas"]["fixture"]}
    with pytest.raises(SurfacesError, match="no area named 'elsewhere'"):
        _build(case)


# -------------------------------------------------------------------------- the files


def test_the_files_are_written_in_order_each_through_a_part_rename(tmp_path, monkeypatch):
    case = _case(tmp_path)
    moves: list[tuple[str, str]] = []
    real_replace = os.replace
    monkeypatch.setattr(
        surfaces.os,
        "replace",
        lambda src, dst: (moves.append((Path(src).name, Path(dst).name)), real_replace(src, dst))[
            1
        ],
    )
    _build(case)
    assert moves == [
        ("fixture.png.import.part", "fixture.png.import"),
        ("fixture.png.part", "fixture.png"),
        ("fixture.json.part", "fixture.json"),
    ]


def test_part_files_left_by_a_cut_run_are_removed_from_the_surfaces_folder_only(tmp_path):
    case = _case(tmp_path)
    folder, other = case.out / "surfaces", case.out / "terrain"
    folder.mkdir(parents=True)
    other.mkdir()
    for name in ("fixture.png.part", "fixture.json.part", "another.png.part"):
        (folder / name).write_bytes(b"cut short")
    (other / "fixture.f32.part").write_bytes(b"cut short")
    _build(case)
    assert sorted(p.name for p in folder.iterdir()) == [
        "fixture.json",
        "fixture.png",
        "fixture.png.import",
    ]
    assert (other / "fixture.f32.part").read_bytes() == b"cut short", "not its folder"


def test_a_refused_build_leaves_the_part_files_where_they_were(tmp_path):
    case = _case(tmp_path)
    folder = case.out / "surfaces"
    folder.mkdir(parents=True)
    (folder / "fixture.png.part").write_bytes(b"cut short")
    case.config["areas"]["fixture"]["expected_pixels_sha256"]["0.2"] = "0" * 64
    with pytest.raises(SurfacesError):
        _build(case)
    assert [p.name for p in folder.iterdir()] == ["fixture.png.part"]


def test_two_builds_give_the_same_files(tmp_path):
    case = _case(tmp_path)
    first = _build(case)
    one = {p.name: p.read_bytes() for p in (case.out / "surfaces").iterdir()}
    shutil.rmtree(case.out)
    second = _build(case)
    two = {p.name: p.read_bytes() for p in (case.out / "surfaces").iterdir()}
    assert first == second and one == two


# --------------------------------------------------------------------- the built block


def _check(out, *, config=None, world=None, world_sha256=None, lock=None, datasets=None):
    world_path = FIXTURE / "world.json"
    return built_surfaces_block(
        out,
        config or load_surfaces_config(FIXTURE / "surfaces.json"),
        world or load_world(world_path),
        world_sha256 or _sha(world_path.read_bytes()),
        datasets or json.loads((FIXTURE / "datasets.json").read_text("utf-8"))["datasets"],
        lock or json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8")),
    )


def _built(tmp_path: Path) -> Path:
    shutil.copytree(GENERATED / "surfaces", tmp_path / "surfaces")
    return tmp_path


def _edit_description(out: Path, **changes) -> None:
    path = out / "surfaces" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    for key, value in changes.items():
        block[key] = value
    path.write_text(json.dumps(block, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _lines_png(pixels: np.ndarray) -> bytes:
    rows, columns = pixels.shape
    lines = np.zeros((rows, columns + 1), dtype=np.uint8)
    lines[:, 1:] = pixels

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        )

    header = struct.pack(">IIBBBBB", columns, rows, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(lines.tobytes(), 9))
        + chunk(b"IEND", b"")
    )


@pytest.mark.parametrize(
    ("changes", "pattern"),
    [
        ({"extra": 1}, "exactly the keys"),
        ({"cell_m": 0.5}, "cell_m is 0.5"),
        ({"cell_m": 1}, "cell_m is 1"),
        ({"area": "elsewhere"}, "area is"),
        ({"file": "surfaces/other.png"}, "file is"),
        ({"format": "png-rgb"}, "format is"),
        ({"columns": 201}, "columns is 201"),
        ({"rows": 149}, "rows is 149"),
        ({"classes": {"0": "none"}}, "classes is"),
        ({"world_sha256": "0" * 64}, "world_sha256 is"),
        ({"source": {"attribution": "© swisstopo"}}, "source is"),
        ({"lv95_box": {"e_max": 1, "e_min": 1, "n_max": 1, "n_min": 1}}, "lv95_box is"),
        ({"lv95_box": "box"}, "lv95_box is"),
        ({"sha256": "0" * 64}, "has SHA-256"),
        ({"pixels_sha256": "0" * 64}, "pixels_sha256"),
    ],
)
def test_a_description_that_does_not_fit_is_refused_naming_the_rebuild(tmp_path, changes, pattern):
    out = _built(tmp_path)
    _edit_description(out, **changes)
    with pytest.raises(SurfacesError, match=pattern) as refusal:
        _check(out)
    assert REBUILD in str(refusal.value) and "fixture.json" in str(refusal.value)


def test_a_description_that_lacks_a_key_or_is_not_json_is_refused(tmp_path):
    out = _built(tmp_path)
    path = out / "surfaces" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    del block["rows"]
    path.write_text(json.dumps(block), encoding="utf-8")
    with pytest.raises(SurfacesError, match="exactly the keys"):
        _check(out)
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(SurfacesError, match="not valid JSON"):
        _check(out)


@pytest.mark.parametrize("keep", [None, b"", b'[remap]\n\nimporter="texture"\n'])
def test_a_png_without_its_keep_file_is_refused(tmp_path, keep):
    """Without `importer="keep"` Godot imports the PNG as a texture and an export ships the
    texture, not the PNG (brain.md H24)."""
    out = _built(tmp_path)
    path = out / "surfaces" / "fixture.png.import"
    if keep is None:
        path.unlink()
    else:
        path.write_bytes(keep)
    with pytest.raises(SurfacesError, match="png.import") as refusal:
        _check(out)
    assert REBUILD in str(refusal.value)


def test_a_png_that_is_not_the_described_file_is_refused(tmp_path):
    out = _built(tmp_path)
    png = out / "surfaces" / "fixture.png"
    png.write_bytes(png.read_bytes()[:-5])
    with pytest.raises(SurfacesError, match="has SHA-256") as refusal:
        _check(out)
    assert REBUILD in str(refusal.value)
    png.unlink()
    with pytest.raises(SurfacesError, match="cannot read its files"):
        _check(out)


def test_a_png_of_another_size_or_with_a_class_beyond_road_is_refused(tmp_path):
    out = _built(tmp_path)
    wrong = _lines_png(np.zeros((150, 199), dtype=np.uint8))
    (out / "surfaces" / "fixture.png").write_bytes(wrong)
    _edit_description(out, sha256=_sha(wrong))
    with pytest.raises(SurfacesError, match="199 × 150"):
        _check(out)
    pixels = np.zeros((150, 200), dtype=np.uint8)
    pixels[3, 3] = 5
    beyond = _lines_png(pixels)
    (out / "surfaces" / "fixture.png").write_bytes(beyond)
    _edit_description(out, sha256=_sha(beyond))
    with pytest.raises(SurfacesError, match="the class 5"):
        _check(out)


def test_pixels_that_are_not_the_configs_expected_classes_are_refused(tmp_path):
    """The description and the PNG agree with each other and with nothing design computed."""
    out = _built(tmp_path)
    pixels = np.zeros((150, 200), dtype=np.uint8)
    png = _lines_png(pixels)
    (out / "surfaces" / "fixture.png").write_bytes(png)
    _edit_description(out, sha256=_sha(png), pixels_sha256=_sha(pixels.tobytes()))
    with pytest.raises(SurfacesError, match="expects") as refusal:
        _check(out)
    assert "pixels_sha256" in str(refusal.value) and REBUILD in str(refusal.value)


def test_a_world_that_is_not_the_one_the_values_were_computed_for_names_design(tmp_path):
    out = _built(tmp_path)
    with pytest.raises(SurfacesError, match="design recomputes") as refusal:
        _check(out, world_sha256="1" * 64)
    assert REBUILD not in str(refusal.value), "a rebuild would be refused for the same reason"


def test_a_lock_entry_that_is_not_the_one_the_values_were_computed_from_names_design(tmp_path):
    out = _built(tmp_path)
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    lock["datasets"]["swisstlm3d"]["sha256"] = "2" * 64
    with pytest.raises(SurfacesError, match="design recomputes") as refusal:
        _check(out, lock=lock)
    assert REBUILD not in str(refusal.value)


def test_the_lock_may_be_given_as_a_path_and_an_unreadable_one_is_refused(tmp_path):
    out = _built(tmp_path)
    block = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    path = FIXTURE / "datasets.lock.json"
    assert _check(out, lock=path) == block
    assert _check(out, lock=str(path)) == block
    with pytest.raises(SurfacesError, match=LOCK_TLM):
        _check(out, lock=tmp_path / "no-lock.json")
    bad = tmp_path / "bad-lock.json"
    bad.write_text("{broken", encoding="utf-8")
    with pytest.raises(SurfacesError, match=LOCK_TLM):
        _check(out, lock=bad)


def test_a_world_without_the_configured_area_is_refused(tmp_path):
    out = _built(tmp_path)
    data = json.loads((FIXTURE / "world.json").read_text(encoding="utf-8"))
    data["areas"] = {"elsewhere": data["areas"]["fixture"]}
    path = tmp_path / "elsewhere.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    other = load_world(path)
    config = recorded(
        load_surfaces_config(FIXTURE / "surfaces.json"), path, _fixture_lock(), "swisstlm3d"
    )
    with pytest.raises(SurfacesError, match="no area 'fixture'"):
        _check(out, config=config, world=other, world_sha256=_sha(path.read_bytes()))


def _fixture_lock() -> dict:
    return json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
