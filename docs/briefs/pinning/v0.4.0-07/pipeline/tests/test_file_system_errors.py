"""Pinning tests for brief v0.4.0-07 (M3 R1 I-03; the owner's "4a", 2026-10-27): a file-system
error ends a command in one line, never a traceback.

The review found every command ending in a Python traceback on a file-system error: an
unusable `--out` (a regular file where a folder belongs), a directory where a file belongs
(`IsADirectoryError`, `NotADirectoryError`, `FileExistsError`, `FileNotFoundError`): `main()`'s
`except` tuple held only the project's error classes (M2 R1 I-05's class, one layer out).
Pinned decision (brief v0.4.0-07): `OSError` joins that tuple, with the same line: one
`mattini: error: <the error>` line on stderr, exit status 1, nothing on stdout, no traceback;
the OSError's own words name the path. Each command runs as the owner runs it, `python -m
mattini`'s `main` in a process of its own (an uncaught exception prints its traceback there),
with the network refused.

The cases: `manifest --out <a regular file>` (the manifest's folder cannot be made:
FileExistsError), `manifest --out <a folder whose manifest.json is a folder>` (the rename onto
it: IsADirectoryError) and `sky --out <a regular file>` (the step's folder: NotADirectoryError).

Does NOT prove: that the line names a path where the system gives none (a full disk mid-write:
`[Errno 28] No space left on device`); the downloads' own file-system errors (they reach for
swisstopo first; the same `except` catches them); anything a step writes before the error
(each step writes through `.part` renames).
"""

import json
import subprocess
import sys

import pytest

DRIVER = """
import json, sys
import mattini.__main__ as cli
from mattini import download

def no_network(*args, **kwargs):
    raise AssertionError("the test reached for the network")

download.urllib_fetch_json = no_network
download.urllib_fetch_file = no_network
sys.exit(cli.main(json.loads(sys.argv[1])))
"""


def _run(tmp_path, argv):
    return subprocess.run(  # the exit status is checked by the tests
        [sys.executable, "-c", DRIVER, json.dumps(argv)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        check=False,
    )


def _a_file(tmp_path):
    path = tmp_path / "a-file"
    path.write_text("not a folder\n", encoding="utf-8")
    return path, path


def _a_folder_where_the_manifest_belongs(tmp_path):
    out = tmp_path / "out"
    (out / "manifest.json").mkdir(parents=True)
    return out, out / "manifest.json"


@pytest.mark.parametrize(
    ("command", "make", "named"),
    [
        pytest.param("manifest", _a_file, "", id="manifest-out-is-a-file"),
        pytest.param(
            "manifest", _a_folder_where_the_manifest_belongs, "", id="manifest-json-is-a-folder"
        ),
        pytest.param("sky", _a_file, "/sky", id="sky-out-is-a-file"),
    ],
)
def test_a_file_system_error_is_one_error_line_naming_the_path(tmp_path, command, make, named):
    out, path = make(tmp_path)
    done = _run(tmp_path, [command, "--out", str(out)])
    assert "Traceback" not in done.stderr, done.stderr
    assert done.returncode == 1, (done.returncode, done.stderr)
    assert done.stdout == ""
    lines = done.stderr.splitlines()
    assert len(lines) == 1 and lines[0].startswith("mattini: error: [Errno "), done.stderr
    assert f"'{path}{named}'" in lines[0], lines[0]
