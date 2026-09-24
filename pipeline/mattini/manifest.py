"""The generated manifest: the game's only source of generated data (docs/SPEC.md §8).

Its `world` block is config/world.json verbatim, with the SHA-256 of the file's bytes, so
the game learns the origin and axes only from here (Hard Rule 4). Written
deterministically: sorted keys, fixed formatting, LF line endings, no times, no absolute
paths (Hard Rule 5).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mattini.world import DEFAULT_PATH, REPO, parse_world, read_config_bytes

SCHEMA = 1
DEFAULT_OUT = REPO / "game" / "assets" / "generated"
FILENAME = "manifest.json"


def build_manifest(config_path: Path = DEFAULT_PATH) -> dict:
    """The manifest's contents; refuses a world config the loader refuses."""
    config_path = Path(config_path)
    raw = read_config_bytes(config_path)
    parse_world(raw, config_path)
    return {
        "schema": SCHEMA,
        "world": json.loads(raw.decode("utf-8")),
        "world_sha256": hashlib.sha256(raw).hexdigest(),
    }


def write_manifest(out_dir: Path | str = DEFAULT_OUT, config_path: Path = DEFAULT_PATH) -> Path:
    """Write `<out_dir>/manifest.json` and return its path."""
    out_dir = Path(out_dir)
    text = json.dumps(build_manifest(config_path), indent=2, sort_keys=True, ensure_ascii=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / FILENAME
    path.write_bytes((text + "\n").encode("utf-8"))
    return path
