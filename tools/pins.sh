# The pinned tools' one home (brief v0.5.0-06). Sourced, never run: the SessionStart hook
# (.claude/hooks/session-start.sh) and the release workflow (.github/workflows/release.yml)
# both `. tools/pins.sh` and spell no pin of their own. The export templates keep their pin
# in tools/export.sh, which installs them (its step 3).

GODOT_VERSION="4.6.3-stable"          # pinned in docs/SPEC.md §Stack
# Godot's official download mirror: github.com release downloads are refused inside cloud
# containers (measured 2026-09-24). The checksum is of the zip as downloaded that day.
GODOT_URL="https://downloads.godotengine.org/?version=4.6.3&flavor=stable&slug=linux.x86_64.zip&platform=linux.64"
GODOT_SHA256="d0bc2113065e481c9c2c2b2c37daa4e8be3fe9e27f0ab9ab0b6096e9a37907f3"
# uv, as the release session's container ran it on 2026-10-30; the release workflow installs
# exactly this one.
UV_VERSION="0.11.32"
