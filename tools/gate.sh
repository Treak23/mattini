#!/usr/bin/env bash
# The standard gate (CLAUDE.md §Build & Test): runs every check the repository has, in
# order, and stops at the first failing step with a non-zero exit, naming that step.
# Commit only on its own exit status: tools/gate.sh > gate.log && git commit ...
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

UV_RUN=(uv run --project pipeline --frozen)

step() {
	local name="$1"
	shift
	echo "== gate: step: $name"
	if ! "$@"; then
		echo "== gate: FAILED at step: $name"
		echo "== gate: FAILED at step: $name" >&2
		exit 1
	fi
}

step "pytest" "${UV_RUN[@]}" pytest pipeline/tests
step "ruff check" "${UV_RUN[@]}" ruff check pipeline
step "ruff format --check" "${UV_RUN[@]}" ruff format --check pipeline

echo "== gate: all steps passed"
