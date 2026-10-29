"""Gap tests for brief v0.4.0-07, round 2: eleven guards of the sky step that no pinned test
covered (the mutation prover's finding, tier 1: a gate no test can fail is a defect).

Each guard was removed or bent in its own mutation (the brief's Findings, rows 19 to 46 of
the prover's list) and survived the whole suite; each test below fails by the harm's name
against its mutation and passes on the real code:
- 19 `build_sky` checks the sky config itself (not only the CLI's loader): a damaged config
  handed to the step is refused naming config/sky.json and writes nothing.
- 22 a description that is not a JSON object (null, a number, the keys as a list) is a
  SkyError naming `python -m mattini sky`, never a TypeError.
- 23 NaN and the infinities are not accepted as a place.
- 26 the ranges are inclusive: exactly 90, 180 and 10 degrees hold, the next float up does not.
- 27 `schema` is the int 1: JSON `true` and `1.0` are refused.
- 34 `world_sha256` is exactly 64 hex digits (65 are refused).
- 35 a `world_sha256` that is not a string is a SkyError, never a TypeError.
- 36 `manifest` checks config/sky.json with the step's own loader even when the step has not
  run in the folder: a damaged config is its refusal, naming the file.
- 39 `sky --out` defaults to the manifest's default folder, game/assets/generated.
- 43 a refusal for another world names the area (`area 'x': ...`).
- 46 an unreadable description names `python -m mattini sky`.

Does NOT prove: that the values are the place's (test_m4_09_sky_config.py); that these are the
only unpinned guards (lesson 4); anything about the game.
"""

import functools
import hashlib
import json
import math
from pathlib import Path

import pytest

import mattini.__main__ as cli
from mattini import manifest as manifest_module
from mattini import sky
from mattini.manifest import write_manifest
from mattini.sky import SkyError, build_sky, built_sky_block, check_sky_config, load_sky_config
from mattini.world import REPO, load_world

SHARED = REPO / "tests" / "shared"
FIXTURE = SHARED / "shadows_fixture"
SKY_COMMAND = "python -m mattini sky"
LIMITS = {"latitude_deg": 90.0, "longitude_deg": 180.0, "true_to_grid_deg": 10.0}


def _config() -> dict:
    return json.loads((FIXTURE / "sky.json").read_text(encoding="utf-8"))


def _values(data: dict) -> dict:
    return next(iter(data["areas"].values()))


def _world_sha256() -> str:
    return hashlib.sha256((FIXTURE / "world.json").read_bytes()).hexdigest()


def _description_in(tmp_path, raw: bytes) -> Path:
    path = tmp_path / "sky" / "fixture.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    return path


def _built(tmp_path):
    world = load_world(FIXTURE / "world.json")
    config = load_sky_config(FIXTURE / "sky.json")
    return built_sky_block(tmp_path, config, world, _world_sha256())


# 19: the step checks the config itself.


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda v: v.update(latitude_deg=46), id="an-integer"),
        pytest.param(lambda v: v.update(true_to_grid_deg=99.0), id="out-of-range"),
        pytest.param(lambda v: v.update(elevation_m=1610.0), id="a-key-more"),
    ],
)
def test_build_sky_refuses_a_damaged_config_itself_and_writes_nothing(tmp_path, change):
    """The CLI's loader checks too, but `build_sky` is called with any dict: a damaged config
    must not become a description (the world and area checks alone let these through)."""
    data = _config()
    change(_values(data))
    with pytest.raises(SkyError) as refused:
        build_sky(load_world(FIXTURE / "world.json"), data, tmp_path / "out")
    assert str(refused.value).startswith("config/sky.json: "), refused.value
    assert not (tmp_path / "out").exists(), "a refusal writes nothing"


# 22: a description that is not an object.


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("null", id="null"),
        pytest.param("46.0", id="a-number"),
        pytest.param('"area"', id="a-string"),
        pytest.param(
            '["area", "latitude_deg", "longitude_deg", "true_to_grid_deg", "world_sha256"]',
            id="the-keys-as-a-list",
        ),
    ],
)
def test_a_description_that_is_not_an_object_names_the_sky_step(tmp_path, text):
    _description_in(tmp_path, text.encode("utf-8"))
    with pytest.raises(SkyError) as refused:
        _built(tmp_path)
    assert SKY_COMMAND in str(refused.value), refused.value


# 23: NaN and the infinities are not a place.


@pytest.mark.parametrize("key", sorted(LIMITS))
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf], ids=["nan", "inf", "-inf"])
def test_a_value_that_is_not_finite_is_refused_naming_the_file(tmp_path, key, bad):
    data = _config()
    _values(data)[key] = bad
    with pytest.raises(SkyError, match="here"):
        check_sky_config(data, "here")
    path = tmp_path / "sky.json"
    path.write_text(json.dumps(data), encoding="utf-8")  # Python writes NaN / Infinity
    with pytest.raises(SkyError, match="sky.json"):
        load_sky_config(path)


# 26: the ranges' boundaries.


@pytest.mark.parametrize("key", sorted(LIMITS))
@pytest.mark.parametrize("sign", [1.0, -1.0], ids=["plus", "minus"])
def test_a_value_exactly_at_its_limit_holds_and_the_next_float_does_not(key, sign):
    """The rule (brief decision 2): |latitude| <= 90, |longitude| <= 180, |true_to_grid| <= 10."""
    limit = LIMITS[key] * sign
    data = _config()
    _values(data)[key] = limit
    check_sky_config(data, "here")
    _values(data)[key] = math.nextafter(limit, math.copysign(math.inf, sign))
    with pytest.raises(SkyError, match=key):
        check_sky_config(data, "here")


# 27: schema is the int 1.


@pytest.mark.parametrize("schema", [True, 1.0], ids=["true", "one-point-zero"])
def test_a_schema_that_equals_one_but_is_not_the_int_is_refused(schema):
    data = _config()
    data["schema"] = schema
    with pytest.raises(SkyError, match="schema must be 1"):
        check_sky_config(data, "here")


# 34 and 35: the world's SHA-256 is exactly 64 hex digits, a string.


@pytest.mark.parametrize(
    "sha",
    [
        pytest.param("a" * 65, id="65-digits"),
        pytest.param("a" * 64 + "\n", id="newline-after"),
        pytest.param("a" * 63, id="63-digits"),
    ],
)
def test_a_world_sha256_of_another_length_is_refused(sha):
    data = _config()
    _values(data)["computed_for"]["world_sha256"] = sha
    with pytest.raises(SkyError, match="64 lower-case hex digits"):
        check_sky_config(data, "here")


@pytest.mark.parametrize("sha", [7, None, ["a" * 64], {"a": "a" * 64}], ids=repr)
def test_a_world_sha256_that_is_not_a_string_is_a_refusal_not_a_type_error(sha):
    data = _config()
    _values(data)["computed_for"]["world_sha256"] = sha
    with pytest.raises(SkyError, match="64 lower-case hex digits"):
        check_sky_config(data, "here")


# 36: `manifest` checks config/sky.json with the step's loader though the step has not run.


def _damaged_sky_config(tmp_path, raw: str | None = None) -> Path:
    data = json.loads((REPO / "config" / "sky.json").read_text(encoding="utf-8"))
    _values(data)["latitude_deg"] = 46  # an int: not a float
    path = tmp_path / "damaged-sky.json"
    path.write_text(raw if raw is not None else json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.parametrize("raw", [None, "{not json"], ids=["an-integer", "bad-json"])
def test_the_manifest_refuses_a_damaged_sky_config_though_the_step_has_not_run(tmp_path, raw):
    path = _damaged_sky_config(tmp_path, raw)
    out = tmp_path / "generated"
    assert not (out / "sky").exists()
    with pytest.raises(SkyError) as refused:
        write_manifest(out, sky_config_path=path)
    assert str(path) in str(refused.value), refused.value
    assert not (out / "manifest.json").exists(), "a refusal writes nothing"


def test_the_manifest_command_ends_in_one_line_for_a_damaged_sky_config(
    tmp_path, monkeypatch, capsys
):
    path = _damaged_sky_config(tmp_path)
    out = tmp_path / "generated"
    write = functools.partial(write_manifest, sky_config_path=path)
    monkeypatch.setattr(cli, "write_manifest", write)
    assert cli.main(["manifest", "--out", str(out)]) == 1
    captured = capsys.readouterr()
    lines = captured.err.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: error: "), captured.err
    assert str(path) in lines[0] and captured.out == ""
    assert not (out / "manifest.json").exists()


# 39: sky's --out default.


def test_sky_writes_into_the_default_folder_when_given_no_out(monkeypatch, capsys):
    seen = {}

    def build(world, config, out_dir, *, progress=None):
        seen["build"] = Path(out_dir)

    def write(out_dir, *args, **kwargs):
        seen["manifest"] = Path(out_dir)
        return Path(out_dir) / "manifest.json"

    monkeypatch.setattr(sky, "build_sky", build)
    monkeypatch.setattr(sky, "load_sky_config", lambda *a, **k: {})
    monkeypatch.setattr(cli, "write_manifest", write)
    assert cli.main(["sky"]) == 0
    assert capsys.readouterr().out == f"{manifest_module.DEFAULT_OUT / 'manifest.json'}\n"
    assert seen == {"build": manifest_module.DEFAULT_OUT, "manifest": manifest_module.DEFAULT_OUT}
    assert manifest_module.DEFAULT_OUT == REPO / "game" / "assets" / "generated"


# 43: a world refusal names the area.


def _config_for_another_world() -> dict:
    data = _config()
    _values(data)["computed_for"]["world_sha256"] = "ab" * 32
    return data


def test_a_refusal_for_another_world_names_the_area_in_the_step(tmp_path):
    world = load_world(FIXTURE / "world.json")
    with pytest.raises(SkyError) as refused:
        build_sky(world, _config_for_another_world(), tmp_path / "out")
    message = str(refused.value)
    assert message.startswith("area 'fixture': "), message
    assert "design recomputes" in message and SKY_COMMAND not in message


def test_a_refusal_for_another_world_names_the_area_in_the_manifest_check():
    world = load_world(FIXTURE / "world.json")
    with pytest.raises(SkyError) as refused:
        built_sky_block(FIXTURE / "generated", _config_for_another_world(), world, _world_sha256())
    message = str(refused.value)
    assert message.startswith("area 'fixture': "), message
    assert "design recomputes" in message and SKY_COMMAND not in message


# 46: an unreadable description names the step.


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(b"{not json", id="bad-json"),
        pytest.param(b"", id="empty"),
        pytest.param(b"\xff\xfe\x00", id="not-utf-8"),
        pytest.param(None, id="a-folder-where-the-file-belongs"),
    ],
)
def test_an_unreadable_description_names_the_sky_step_and_the_file(tmp_path, raw):
    if raw is None:
        path = tmp_path / "sky" / "fixture.json"
        path.mkdir(parents=True)  # exists, cannot be read as a file: an OSError
    else:
        path = _description_in(tmp_path, raw)
    with pytest.raises(SkyError) as refused:
        _built(tmp_path)
    message = str(refused.value)
    assert SKY_COMMAND in message and str(path) in message, message
    assert "cannot read the sky description" in message
