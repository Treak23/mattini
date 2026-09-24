#!/bin/bash
# SessionStart hook: headless Godot + Python env for cloud containers. Idempotent.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

GODOT_VERSION="4.6.3-stable"          # pinned in docs/SPEC.md §Stack
# Godot's official download mirror: github.com release downloads are refused inside cloud
# containers (measured 2026-09-24). The checksum is of the zip as downloaded that day.
GODOT_URL="https://downloads.godotengine.org/?version=4.6.3&flavor=stable&slug=linux.x86_64.zip&platform=linux.64"
GODOT_SHA256="d0bc2113065e481c9c2c2b2c37daa4e8be3fe9e27f0ab9ab0b6096e9a37907f3"
GODOT_DIR="/opt/godot"
GODOT_BIN="$GODOT_DIR/godot"

if [ ! -x "$GODOT_BIN" ] || ! "$GODOT_BIN" --version 2>/dev/null | grep -q '^4\.6\.3\.stable'; then
  mkdir -p "$GODOT_DIR"
  curl -fsSL --retry 3 -o /tmp/godot.zip "$GODOT_URL"
  if ! echo "$GODOT_SHA256  /tmp/godot.zip" | sha256sum -c --quiet -; then
    echo "session-start: Godot ${GODOT_VERSION} download failed its checksum; not installed" >&2
    exit 1
  fi
  unzip -q -o /tmp/godot.zip -d "$GODOT_DIR"
  mv -f "$GODOT_DIR"/Godot_v*_linux.x86_64 "$GODOT_BIN"
  chmod +x "$GODOT_BIN"
  rm -f /tmp/godot.zip
fi

# Python environment for pipeline/ (uv, Python 3.13, lockfile); exists from brief M0-01 on.
UV_BIN="$(command -v uv || echo "$HOME/.local/bin/uv")"
if [ -f "$CLAUDE_PROJECT_DIR/pipeline/pyproject.toml" ]; then
  if [ -x "$UV_BIN" ]; then
    "$UV_BIN" sync --project "$CLAUDE_PROJECT_DIR/pipeline" --frozen > /dev/null 2>&1 \
      || echo "session-start: uv sync failed (non-fatal; run it by hand to see why)"
  else
    echo "session-start: uv not found; the pipeline environment was not created"
  fi
fi

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  {
    echo "export PATH=\"$GODOT_DIR:$(dirname "$UV_BIN"):\$PATH\""
    echo "export GODOT=\"$GODOT_BIN\""
  } >> "$CLAUDE_ENV_FILE"
fi

# Warm-up: first asset import, soft-fail; the Godot project exists from brief M0-03 on.
if [ -f "$CLAUDE_PROJECT_DIR/game/project.godot" ]; then
  "$GODOT_BIN" --headless --path "$CLAUDE_PROJECT_DIR/game" --import > /dev/null 2>&1 \
    || echo "session-start: godot import warm-up failed (non-fatal)"
fi

echo "session-start: done"
