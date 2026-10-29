"""The sky step: where the sun stands for the configured area (brief v0.4.0-07).

`python -m mattini sky` writes `sky/<area>.json` next to the other steps' files: exactly
config/sky.json's latitude, longitude and true-to-grid angle for the configured area, with
the area and the SHA-256 of config/world.json's bytes. config/sky.json is design data with
`computed_for` {world_sha256}, like every expected value; the manifest's `sky` block is that
description, or null until the step has run in the folder.

The checks run in this order, each before the next, and nothing is written (not even the
folder) until all have passed:
1. config/sky.json is exactly its shape (`check_sky_config`);
2. the world: `computed_for.world_sha256` against config/world.json's bytes; a difference is
   design's step, since running the step again cannot help (it names no command);
3. the area: the config's one area must be one of the world config's areas (it names no
   command either);
then, for a built description (`built_sky_block`, the manifest's check), 4. the description
must be exactly the block `build_sky` would write, value for value and type for type, or it is
refused naming `python -m mattini sky`.

The file is written through a `.part` rename, with sorted keys, two-space indent and LF line
endings, no times and no absolute paths (Hard Rule 5).

Does NOT prove: that the values are the place's (test_m4_09_sky_config.py recomputes them
with swisstopo's formulas); that the game turns azimuths with them.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path

from mattini import terrain
from mattini.world import REPO, World, read_config_bytes

SKY_CONFIG_PATH = REPO / "config" / "sky.json"
SKY_COMMAND = "python -m mattini sky"
CONFIG_NAME = "config/sky.json"
_VALUES = ("latitude_deg", "longitude_deg", "true_to_grid_deg")
_LIMITS = {"latitude_deg": 90.0, "longitude_deg": 180.0, "true_to_grid_deg": 10.0}
_SHA256 = re.compile(r"[0-9a-f]{64}")


class SkyError(ValueError):
    """A sky config, world or description that cannot be used; the message names the file."""


def load_sky_config(path: Path | str = SKY_CONFIG_PATH) -> dict:
    """Read and check the sky config; every refusal names `path`."""
    try:
        data = json.loads(Path(path).read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise SkyError(f"{path}: cannot read the sky config: {exc}") from exc
    check_sky_config(data, path)
    return data


def check_sky_config(data: object, where: object) -> None:
    """Refuse anything but the sky config's exact shape; the message names `where`."""

    def fail(message: str) -> SkyError:
        return SkyError(f"{where}: {message}")

    if not isinstance(data, dict) or set(data) != {"schema", "areas"}:
        raise fail("the top level must be exactly `schema` and `areas`")
    if type(data["schema"]) is not int or data["schema"] != 1:
        raise fail(f"schema must be 1, found {data['schema']!r}")
    areas = data["areas"]
    if not isinstance(areas, dict) or len(areas) != 1:
        raise fail("`areas` must hold exactly one area")
    ((name, settings),) = areas.items()
    if not isinstance(settings, dict) or set(settings) != {"computed_for", *_VALUES}:
        raise fail(f"area {name!r} must hold exactly computed_for and {', '.join(_VALUES)}")
    computed_for = settings["computed_for"]
    if not isinstance(computed_for, dict) or set(computed_for) != {"world_sha256"}:
        raise fail(f"area {name!r}: computed_for must be exactly world_sha256")
    sha = computed_for["world_sha256"]
    if not (isinstance(sha, str) and _SHA256.fullmatch(sha)):
        raise fail(f"area {name!r}: world_sha256 must be 64 lower-case hex digits")
    for key in _VALUES:
        value = settings[key]
        if type(value) is not float or not math.isfinite(value) or abs(value) > _LIMITS[key]:
            raise fail(
                f"area {name!r}: {key} must be a finite float with |value| <= "
                f"{_LIMITS[key]:g}, found {value!r}"
            )


def _checked_area(sky_config: dict, world: World, world_sha256: str) -> str:
    """Steps 2 and 3: the world, then the area; returns the config's area."""
    area = terrain.configured_area(sky_config)
    problem = terrain.world_refusal(
        CONFIG_NAME, sky_config["areas"][area]["computed_for"], world_sha256
    )
    if problem:
        raise SkyError(f"area {area!r}: {problem}")
    if area not in world.areas:
        raise SkyError(f"{CONFIG_NAME}: area {area!r} is not an area of the world config")
    return area


def _block(area: str, sky_config: dict, world_sha256: str) -> dict:
    settings = sky_config["areas"][area]
    return {
        "area": area,
        **{key: settings[key] for key in _VALUES},
        "world_sha256": world_sha256,
    }


def build_sky(world: World, sky_config: dict, out_dir: Path | str, *, progress=None) -> dict:
    """Write `<out_dir>/sky/<area>.json` and return its block; a refusal writes nothing."""
    check_sky_config(sky_config, CONFIG_NAME)
    world_sha256 = hashlib.sha256(read_config_bytes(world.path)).hexdigest()
    area = _checked_area(sky_config, world, world_sha256)
    block = _block(area, sky_config, world_sha256)
    folder = Path(out_dir) / "sky"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{area}.json"
    part = path.with_name(path.name + ".part")
    text = json.dumps(block, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    part.write_bytes(text.encode("utf-8"))
    os.replace(part, path)
    if progress:
        progress(f"wrote {path}")
    return block


def built_sky_block(
    out_dir: Path | str, sky_config: dict, world: World, world_sha256: str
) -> dict | None:
    """The description built in `out_dir`, or None when the step has not run there."""
    area = terrain.configured_area(sky_config)
    path = Path(out_dir) / "sky" / f"{area}.json"
    if not path.exists():
        return None
    _checked_area(sky_config, world, world_sha256)
    try:
        found = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise SkyError(
            f"{path}: cannot read the sky description: {exc}; run `{SKY_COMMAND}`"
        ) from exc
    expected = _block(area, sky_config, world_sha256)
    if (
        not isinstance(found, dict)
        or set(found) != set(expected)
        or any(type(found[k]) is not type(v) or found[k] != v for k, v in expected.items())
    ):
        raise SkyError(
            f"{path}: the description is not config/sky.json's values for this world; "
            f"run `{SKY_COMMAND}`"
        )
    return found
