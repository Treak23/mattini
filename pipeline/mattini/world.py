"""config/world.json: the one home of the local origin, the axis mapping and the areas.

CLAUDE.md Hard Rule 4 and docs/SPEC.md §6. The loader refuses a malformed, mirroring or
scrambled config with a WorldConfigError whose message names the file (Hard Rule 2).
Conversions run in Python floats (64-bit): the origin is subtracted before anything
narrower sees a coordinate.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PATH = REPO / "config" / "world.json"

SCHEMA = 1
CRS = {"horizontal": "EPSG:2056", "vertical": "EPSG:5728"}
SOURCE_AXES = ("e", "n", "h")  # LV95 east, LV95 north, LN02 height: right-handed
GAME_AXES = ("x", "y", "z")  # Godot: x right, y up, z back: right-handed
TOP_LEVEL_KEYS = {"schema", "crs", "origin_lv95", "height_offset_m", "axes", "areas"}
AREA_KEYS = ("e_min", "e_max", "n_min", "n_max")


class WorldConfigError(ValueError):
    """config/world.json is missing, malformed, or maps the world in a way we refuse."""


@dataclass(frozen=True)
class World:
    """The validated contents of config/world.json."""

    path: Path
    origin_e: float
    origin_n: float
    height_offset: float
    # For each game axis in GAME_AXES order: (sign, index into SOURCE_AXES).
    mapping: tuple[tuple[float, int], ...]
    areas: dict[str, tuple[float, float, float, float]]

    def to_local(self, e: float, n: float, h: float) -> tuple[float, float, float]:
        """LV95 easting, northing and LN02 height to Godot local (x, y, z) in metres."""
        source = (float(e) - self.origin_e, float(n) - self.origin_n, float(h) - self.height_offset)
        x, y, z = (sign * source[index] for sign, index in self.mapping)
        return (x, y, z)

    def to_lv95(self, x: float, y: float, z: float) -> tuple[float, float, float]:
        """Godot local (x, y, z) in metres to LV95 easting, northing and LN02 height."""
        source = [0.0, 0.0, 0.0]
        for value, (sign, index) in zip((x, y, z), self.mapping, strict=True):
            source[index] = sign * float(value)
        return (
            source[0] + self.origin_e,
            source[1] + self.origin_n,
            source[2] + self.height_offset,
        )

    def area(self, name: str) -> tuple[float, float, float, float]:
        """The named area's LV95 box as (e_min, e_max, n_min, n_max)."""
        if name not in self.areas:
            raise WorldConfigError(f"{self.path}: no area named {name!r}")
        return self.areas[name]


def load_world(path: Path | str = DEFAULT_PATH) -> World:
    """Read and validate a world config; raise WorldConfigError naming the file."""
    path = Path(path)
    return parse_world(read_config_bytes(path), path)


def read_config_bytes(path: Path) -> bytes:
    """The world config's bytes; an unreadable file is a WorldConfigError naming it."""
    try:
        return path.read_bytes()
    except OSError as exc:
        raise WorldConfigError(f"{path}: cannot read the world config: {exc}") from exc


def parse_world(raw: bytes, path: Path) -> World:
    """Validate the bytes of a world config read from `path` (named in every error)."""

    def fail(message: str) -> WorldConfigError:
        return WorldConfigError(f"{path}: {message}")

    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_no_constants,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise fail(f"not valid JSON: {exc}") from exc

    _require_keys(data, TOP_LEVEL_KEYS, "the top level", fail)
    schema = data["schema"]
    if type(schema) is not int or schema != SCHEMA:
        raise fail(f"schema must be {SCHEMA}, found {schema!r}")
    if data["crs"] != CRS:
        raise fail(f"crs must be {CRS}, found {data['crs']!r}")

    origin = data["origin_lv95"]
    _require_keys(origin, {"e", "n"}, "origin_lv95", fail)
    origin_e = _finite(origin["e"], "origin_lv95.e", fail)
    origin_n = _finite(origin["n"], "origin_lv95.n", fail)
    height_offset = _finite(data["height_offset_m"], "height_offset_m", fail)

    mapping = _rotation(data["axes"], fail)

    areas_data = data["areas"]
    if not isinstance(areas_data, dict):
        raise fail("areas must be an object")
    areas = {}
    for name, box in areas_data.items():
        _require_keys(box, set(AREA_KEYS), f"area {name!r}", fail)
        e_min, e_max, n_min, n_max = (_finite(box[k], f"{name}.{k}", fail) for k in AREA_KEYS)
        if not (e_min < e_max and n_min < n_max):
            raise fail(f"area {name!r} is an empty box: {box!r}")
        areas[name] = (e_min, e_max, n_min, n_max)

    return World(
        path=path,
        origin_e=origin_e,
        origin_n=origin_n,
        height_offset=height_offset,
        mapping=mapping,
        areas=areas,
    )


def _rotation(axes: object, fail) -> tuple[tuple[float, int], ...]:
    """Parse `axes` ({"x": "+e", ...}); refuse anything that is not a proper rotation."""
    _require_keys(axes, set(GAME_AXES), "axes", fail)
    mapping = []
    for game_axis in GAME_AXES:
        spec = axes[game_axis]
        if not (
            isinstance(spec, str) and len(spec) == 2 and spec[0] in "+-" and spec[1] in SOURCE_AXES
        ):
            raise fail(f"axes.{game_axis} must be a signed source axis like '+e', found {spec!r}")
        mapping.append((1.0 if spec[0] == "+" else -1.0, SOURCE_AXES.index(spec[1])))
    if sorted(index for _, index in mapping) != [0, 1, 2]:
        raise fail(f"axes must use each of e, n, h exactly once, found {axes!r}")
    matrix = [[0.0] * 3 for _ in GAME_AXES]
    for row, (sign, index) in enumerate(mapping):
        matrix[row][index] = sign
    if _determinant(matrix) != 1.0:
        raise fail(f"axes mirror the world (not a rotation): {axes!r}")
    return tuple(mapping)


def _determinant(m: list[list[float]]) -> float:
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def _require_keys(obj: object, keys: set[str], where: str, fail) -> None:
    if not isinstance(obj, dict):
        raise fail(f"{where} must be an object, found {obj!r}")
    missing = sorted(keys - obj.keys())
    unknown = sorted(obj.keys() - keys)
    if missing or unknown:
        raise fail(f"{where}: missing keys {missing}, unknown keys {unknown}")


def _finite(value: object, where: str, fail) -> float:
    if type(value) in (int, float):
        try:
            number = float(value)
        except OverflowError:
            number = math.inf
        if math.isfinite(number):
            return number
    raise fail(f"{where} must be a finite number, found {value!r}")


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def _no_constants(name: str) -> None:
    raise ValueError(f"{name} is not a number")
