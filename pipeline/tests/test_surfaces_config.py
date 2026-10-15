"""Brief M3-06: config/surfaces.json is checked, and the TLM lock entry must fit.

The expected classes are design's (SPEC §8): a config that is malformed is refused naming
the file, never half-read. The lock's `swisstlm3d` entry pins one national file; the step and
the manifest check that it is for the datasets config before they use it, refusing a lock
without it naming `python -m mattini lock tlm` (design's rehearsal measured a KeyError
traceback there).

Does NOT prove: the lock command or the downloads (brief M3-03); that the committed values
are right (the real run compares the classes with them).
"""

import copy
import json

import pytest

from mattini.surfaces import (
    SurfacesError,
    built_surfaces_block,
    check_surfaces_config,
    load_surfaces_config,
)
from mattini.world import REPO

GOOD = json.loads((REPO / "config" / "surfaces.json").read_text(encoding="utf-8"))
SHA = "a" * 64


def _changed(change):
    config = copy.deepcopy(GOOD)
    change(config)
    return config


@pytest.mark.parametrize(
    ("change", "pattern"),
    [
        (lambda c: c.pop("schema"), "top level"),
        (lambda c: c.update(extra=1), "top level"),
        (lambda c: c.update(schema=2), "schema"),
        (lambda c: c.update(schema=True), "schema"),
        (lambda c: c.update(areas={}), "exactly one area"),
        (lambda c: c.update(areas=[]), "exactly one area"),
        (lambda c: c["areas"].update(second=c["areas"]["village"]), "exactly one area"),
        (lambda c: c["areas"].update(Village=c["areas"].pop("village")), "lower-case"),
        (lambda c: c["areas"]["village"].update(extra=1), "exactly the keys"),
        (lambda c: c["areas"]["village"].pop("cell_m"), "exactly the keys"),
        (lambda c: c["areas"]["village"].update(cell_m=0.3), "cell_m"),
        (lambda c: c["areas"]["village"].update(cell_m="0.2"), "cell_m"),
        (lambda c: c["areas"]["village"].update(cell_m=True), "cell_m"),
        (lambda c: c["areas"]["village"].update(expected_pixels_sha256=[]), "must be an object"),
        (
            lambda c: c["areas"]["village"]["expected_pixels_sha256"].update({"2": SHA}),
            "holds only",
        ),
        (
            lambda c: c["areas"]["village"]["expected_pixels_sha256"].update({"0.5": "xyz"}),
            "SHA-256",
        ),
        (
            lambda c: c["areas"]["village"]["expected_pixels_sha256"].update({"0.5": "A" * 64}),
            "SHA-256",
        ),
        (lambda c: c["areas"]["village"]["expected_pixels_sha256"].pop("0.2"), "no value for"),
        (lambda c: c["areas"]["village"]["computed_for"].pop("world_sha256"), "computed_for"),
        (
            lambda c: c["areas"]["village"]["computed_for"].update(inputs_sha256="no"),
            "inputs_sha256",
        ),
    ],
)
def test_a_malformed_config_is_refused_naming_where(change, pattern):
    with pytest.raises(SurfacesError, match=pattern) as refusal:
        check_surfaces_config(_changed(change), "config/surfaces.json")
    assert str(refusal.value).startswith("config/surfaces.json: ")


def test_the_committed_config_is_accepted_and_an_integer_cell_of_one_metre_is_too():
    check_surfaces_config(GOOD)
    one = _changed(lambda c: c["areas"]["village"].update(cell_m=1))
    check_surfaces_config(one)  # a JSON 1 for 1.0: the cell's key is "1"


def test_an_unreadable_config_is_refused_naming_the_file(tmp_path):
    with pytest.raises(SurfacesError, match=r"surfaces\.json: cannot read"):
        load_surfaces_config(tmp_path / "surfaces.json")
    (tmp_path / "surfaces.json").write_bytes(b"{not json")
    with pytest.raises(SurfacesError, match=r"surfaces\.json: not valid JSON"):
        load_surfaces_config(tmp_path / "surfaces.json")
    (tmp_path / "surfaces.json").write_bytes(b"\xff\xfe")
    with pytest.raises(SurfacesError, match=r"surfaces\.json: not valid JSON"):
        load_surfaces_config(tmp_path / "surfaces.json")


# ----------------------------------------------------------------- the lock's fit


TLM = {"collection": "ch.swisstopo.swisstlm3d", "edition": "2026-02", "attribution": "© swisstopo"}
ENTRY = {
    "collection": "ch.swisstopo.swisstlm3d",
    "edition": "2026-02",
    "file": "swisstlm3d_2026-02_2056_5728.gdb.zip",
    "sha256": SHA,
}


def _lock(**changes):
    entry = {**ENTRY, **changes}
    return {
        "schema": 1,
        "datasets": {"swisstlm3d": {k: v for k, v in entry.items() if v is not None}},
    }


@pytest.mark.parametrize(
    ("lock", "pattern"),
    [
        ({"schema": 1, "datasets": {}}, "no 'swisstlm3d' entry"),
        ({"schema": 1}, "no 'swisstlm3d' entry"),
        ([], "no 'swisstlm3d' entry"),
        ({"schema": 1, "datasets": {"swisstlm3d": "x"}}, "no 'swisstlm3d' entry"),
        (_lock(file=None), "exactly the keys"),
        ({"schema": 1, "datasets": {"swisstlm3d": {**ENTRY, "tiles": {}}}}, "exactly the keys"),
        (_lock(edition="2025-08"), "edition"),
        (_lock(collection="ch.swisstopo.other"), "collection"),
        (_lock(file="../x.zip"), "plain file name"),
        (_lock(file=5), "plain file name"),
        (_lock(sha256="A" * 64), "lower-case hex"),
        (_lock(sha256="a" * 63), "lower-case hex"),
    ],
)
def test_a_lock_that_does_not_fit_is_refused_naming_lock_tlm(tmp_path, lock, pattern):
    with pytest.raises(SurfacesError, match=pattern) as refusal:
        built_surfaces_block(*_for_a_built_description(tmp_path), lock)
    assert "python -m mattini lock tlm" in str(refusal.value)
    assert not isinstance(refusal.value, KeyError)


def _for_a_built_description(tmp_path):
    """Arguments of built_surfaces_block up to the lock, for a folder that holds a surfaces
    description (the content is never read: the lock's fit is checked first)."""
    from mattini.world import load_world

    out = tmp_path / "out"
    (out / "surfaces").mkdir(parents=True)
    (out / "surfaces" / "village.json").write_text("{}", encoding="utf-8")
    world = load_world()
    import hashlib

    return (
        out,
        GOOD,
        world,
        hashlib.sha256(world.path.read_bytes()).hexdigest(),
        {"swisstlm3d": TLM},
    )


def test_a_datasets_config_without_the_dataset_is_refused_naming_the_config(tmp_path):
    args = list(_for_a_built_description(tmp_path))
    args[4] = {}
    with pytest.raises(SurfacesError, match=r"config/datasets\.json has no 'swisstlm3d'"):
        built_surfaces_block(*args, _lock())


def test_nothing_is_read_when_no_surfaces_are_built(tmp_path):
    """No description, no lock read: the path may not exist (a fresh checkout)."""
    out, config, world, sha, datasets = _for_a_built_description(tmp_path)
    (out / "surfaces" / "village.json").unlink()
    assert (
        built_surfaces_block(out, config, world, sha, datasets, tmp_path / "no-lock.json") is None
    )
