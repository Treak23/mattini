# Brief: M0-01 — Repo skeleton, Python environment and the standard gate
Status: OPEN

Written in the design realm; executed by one fresh executor session. Executor rules:
`docs/roles/BUILD.md`.

## Goal

A fresh clone has a `.gitignore`, a uv-managed Python 3.13 project for `pipeline/`
(package `mattini`, lockfile committed) and `tools/gate.sh`: the one command that runs
every check the repository has and exits non-zero when any of them fails. Raw downloads,
generated assets, tool caches and the gate log stay out of git. From this brief on, every
commit chains to the gate.

## Read first, in order

1. `CLAUDE.md` — Build & Test, Hard Rules, Conventions.
2. `docs/SPEC.md` §4 Stack, §9 Storage, §13 row 5.
3. `docs/roles/BUILD.md` — rules 3 to 3c; `docs/WORKFLOW.md` §Brief lifecycle (pinning).
4. `brain.md` §Hazards.
5. `docs/briefs/pinning/M0-01/pipeline/tests/test_repo_hygiene.py` — the pinning tests.

## Decisions already made

- Python 3.13 via uv: `pipeline/.python-version` reads `3.13`, `requires-python =
  ">=3.13,<3.14"`, and `pipeline/uv.lock` is committed (SPEC §4, §13 row 5).
- `pipeline/` is a package project named `mattini-pipeline` whose import package is
  `mattini` at `pipeline/mattini/` (flat layout), built with a build backend so that
  `uv sync` installs it and `python -m mattini` works from any directory. Tests live in
  `pipeline/tests/`; pytest's configuration lives in `pipeline/pyproject.toml`.
- Dev dependency group: `pytest`, `ruff`, `gdtoolkit==4.5.0` (gdlint and gdformat, used
  from M0-03 on). No runtime dependencies in this brief.
- ruff: the locked version's default rules with `line-length = 100`. The gate runs
  `ruff check pipeline` and `ruff format --check pipeline`.
- `tools/gate.sh`: bash with `set -euo pipefail`; works from any working directory (it
  changes to the repository root); runs its steps in order and stops at the first failing
  step, printing that step's name; runs Python tools through `uv run --project pipeline
  --frozen`. Later briefs append steps (M0-03 adds the Godot ones).
- Git-ignored: `data/`, `game/assets/generated/`, `game/.godot/`, `pipeline/.venv/`, Python
  and tool caches, `gate.log` (SPEC §9; the pinning tests list the exact paths).

## Scope — files you may touch

`.gitignore` · `pipeline/pyproject.toml` · `pipeline/uv.lock` · `pipeline/.python-version`
· `pipeline/mattini/__init__.py` · `pipeline/tests/test_repo_hygiene.py` (the pinned copy,
unchanged) · `pipeline/tests/conftest.py` (only if needed) · `tools/gate.sh`

## Depends on

None.

## Done when (gates)

- [ ] The pinned copy is in place and unchanged:
      `cmp docs/briefs/pinning/M0-01/pipeline/tests/test_repo_hygiene.py pipeline/tests/test_repo_hygiene.py`
      exits 0.
      - does NOT prove: that the pinned tests are right (the design realm's
        responsibility; they were run against a scratch implementation on 2026-09-24).
- [ ] `uv run --project pipeline --frozen pytest pipeline/tests` passes and the report
      lists the hygiene tests.
      - does NOT prove: that a file cannot enter git another way (`git add -f` bypasses
        the ignore rules; the committable-files tests catch it only when the gate runs).
- [ ] `uv run --project pipeline python -c "import mattini"` works from the repository
      root and from `/tmp`.
      - does NOT prove: that the owner's PCs get the same environment (the lockfile makes
        it reproducible; the owner's first run is the check).
- [ ] Gate mutation proof, every run recorded in Findings with its exit code and the name
      of the failing step: (a) a failing assertion in a scratch test file → non-zero at the
      pytest step; (b) a ruff violation → non-zero at `ruff check`; (c) an unformatted file
      → non-zero at `ruff format --check`; everything restored → zero. Undo with
      `git apply -R` of the saved diff or by deleting the scratch file.
      - does NOT prove: that the steps later briefs add are wired (each proves its own).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: anything about the Godot side (no Godot project exists yet).

## Forbidden

Runtime dependencies; anything under `game/`; changing the pinned copy or anything under
`config/` or `tests/shared/`.

## Findings (executor writes)
