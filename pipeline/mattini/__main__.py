"""Command line: `python -m mattini <command>`."""

from __future__ import annotations

import argparse
import sys

from mattini.manifest import DEFAULT_OUT, write_manifest
from mattini.world import WorldConfigError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m mattini")
    commands = parser.add_subparsers(dest="command", required=True)
    manifest = commands.add_parser("manifest", help="write the generated manifest.json")
    manifest.add_argument(
        "--out", default=DEFAULT_OUT, help="output directory (default: game/assets/generated)"
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "manifest":
            print(write_manifest(args.out))
    except WorldConfigError as exc:
        print(f"mattini: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
