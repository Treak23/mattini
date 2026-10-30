"""Pinning tests for brief v0.5.0-06: tools/release_checks.sh, docs/RELEASE.md §C's runtime checks.

Pinned decisions (brief v0.5.0-06 decision 3; RELEASE.md §C, which the session did by hand up
to 0.4.0), run on a stand-in exported game (fake_release.py): `tools/release_checks.sh
[<linux build folder>]` (default build/linux) prints one `release check: <name>: PASS|FAIL
...` line per check, runs every check whatever the one before found, and exits 0 only when all
five pass, 1 otherwise, its last line `== release checks: all passed` or `== release checks:
<n> failed`:
- `stars`: mattini.pck's directory holds `sky/stars.csv` with game/sky/stars.csv's size and
  MD5 (a build without it shows a starless night and no ESA credit: the licence's breach);
- `frame cap`: `--print-fps --quit-after 600` prints `Project FPS: 60`, no ERROR line, exit 0,
  one data-pack line per mattini-*.pck and more startup lines after them;
- `override.cfg`: one written beside the executable with a marker version is read (the
  startup lines show the marker), then removed (the README's MSAA route works);
- `missing pack`: with mattini-photo.pck moved aside, DataPacks' ERROR line names it, "the
  aerial photo" and the build's folder (its real path: a line naming another folder fails),
  and PhotoGrid's ERROR line ends "download the release folder again" (FB-005); the pack goes
  back, its SHA-256 unchanged;
- `live log`: started without --quit-after, its output and user://logs/godot.log hold every
  startup line while it still runs (FB-006); then it is stopped by its PID;
- the build folder is left as it was found, byte for byte, file for file, after a pass and
  after a failure.

Since the release's checkers (2026-10-30; brief v0.5.0-06 decision 3): the stars' line holds the
reader's own words only, its verdict's reason on stdout: what uv itself writes on stderr (a
deprecation warning, a download note) never lands in the PASS or FAIL line.

Does NOT prove: that the real exported game passes (the workflow's first live run is that
proof, the session's step after this batch lands); that the game looks right or starts on a
GPU; the error panel's text (the release template ignores --script: the owner's eyes); the
15 fps pause cap (no pause headless).
"""

import hashlib
import os
import re
import sys

import pytest
from fake_release import release_tree, run_checks
from fake_tools import BASH, FAKE_UV, REPO, write_pck

pytestmark = pytest.mark.skipif(
    BASH is None or sys.platform != "linux",
    reason="runs tools/release_checks.sh with bash, on Linux",
)

CHECKS = ["stars", "frame cap", "override.cfg", "missing pack", "live log"]


def _snapshot(folder):
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(folder.iterdir())
    }


def _verdicts(output):
    found = {}
    for line in output.splitlines():
        if line.startswith("release check: "):
            name, _, rest = line[len("release check: ") :].partition(": ")
            found[name] = rest.split(" ", 1)[0]
    return found


def _run(tmp_path, **knobs):
    root = release_tree(tmp_path)
    linux = root / "build" / "linux"
    before = _snapshot(linux)
    done = run_checks(tmp_path, root, **knobs)
    assert _snapshot(linux) == before, "the build folder is left as it was found"
    return done


def test_the_script_exists_and_is_executable():
    script = REPO / "tools" / "release_checks.sh"
    assert script.is_file(), "tools/release_checks.sh is missing"
    assert os.access(script, os.X_OK), "tools/release_checks.sh is not executable"


def test_a_good_build_passes_every_check(tmp_path):
    """Positive control: the stand-in behaves as the real build did at 0.4.0's release gate."""
    done = _run(tmp_path)
    assert done.returncode == 0, done.stdout
    assert _verdicts(done.stdout) == {name: "PASS" for name in CHECKS}, done.stdout
    assert done.stdout.rstrip().splitlines()[-1] == "== release checks: all passed"
    assert "Project FPS: 60" in done.stdout, "the frame cap's line is quoted for the record"
    assert "mattini-photo.pck (the aerial photo) is missing from" in done.stdout


def test_the_build_folder_is_an_argument(tmp_path):
    root = release_tree(tmp_path)
    (root / "build" / "linux").rename(root / "elsewhere")
    done = run_checks(tmp_path, root, "elsewhere")
    assert done.returncode == 0, done.stdout


@pytest.mark.parametrize(
    "knobs, failing",
    [
        ({"FAKE_FPS": "30"}, "frame cap"),
        ({"FAKE_NO_OVERRIDE": "1"}, "override.cfg"),
        ({"FAKE_NO_PACK_ERROR": "1"}, "missing pack"),
        ({"FAKE_PACK_FOLDER": "/another/folder"}, "missing pack"),
        ({"FAKE_NO_PHOTO_LINE": "1"}, "missing pack"),
        ({"FAKE_LOG_AT_EXIT": "1"}, "live log"),
    ],
    ids=[
        "another-frame-cap",
        "override-not-read",
        "pack-not-named",
        "pack-named-in-another-folder",
        "no-photo-line",
        "log-at-exit",
    ],
)
def test_each_harm_fails_its_check_alone(tmp_path, knobs, failing):
    done = _run(tmp_path, **knobs)
    assert done.returncode == 1, done.stdout
    verdicts = _verdicts(done.stdout)
    assert verdicts == {name: "FAIL" if name == failing else "PASS" for name in CHECKS}, done.stdout
    assert done.stdout.rstrip().splitlines()[-1] == "== release checks: 1 failed"


def test_an_error_line_fails_the_frame_cap(tmp_path):
    done = _run(
        tmp_path, FAKE_ERROR="ERROR: SkySite: res://assets/generated/manifest.json: a refusal"
    )
    assert done.returncode == 1, done.stdout
    assert _verdicts(done.stdout)["frame cap"] == "FAIL", done.stdout


def test_a_failing_exit_status_fails_the_frame_cap(tmp_path):
    done = _run(tmp_path, FAKE_EXIT="3")
    assert done.returncode == 1, done.stdout
    assert _verdicts(done.stdout)["frame cap"] == "FAIL", done.stdout


def test_a_pack_without_the_stars_fails(tmp_path):
    root = release_tree(tmp_path)
    write_pck(root / "build" / "linux" / "mattini.pck", [("scripts/main.gdc", b"no stars")])
    done = run_checks(tmp_path, root)
    assert done.returncode == 1, done.stdout
    assert _verdicts(done.stdout)["stars"] == "FAIL", done.stdout
    assert _verdicts(done.stdout)["frame cap"] == "PASS", "every check runs"


def test_other_stars_fail(tmp_path):
    root = release_tree(tmp_path)
    stars = (REPO / "game" / "sky" / "stars.csv").read_bytes()
    write_pck(
        root / "build" / "linux" / "mattini.pck",
        [("sky/stars.csv", stars[:-2] + bytes([stars[-2] ^ 1]) + b"\n")],
    )
    done = run_checks(tmp_path, root)
    assert done.returncode == 1, done.stdout
    assert _verdicts(done.stdout)["stars"] == "FAIL", done.stdout


UV_NOISE = "warning: uv's own words on stderr"


@pytest.mark.parametrize("starless", [False, True], ids=["pass", "fail"])
def test_uv_s_own_words_stay_out_of_the_stars_line(tmp_path, starless):
    """A uv that writes on stderr (as the container's does): the stars' line is the reader's."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    noisy = FAKE_UV.replace("\n", f'\necho "{UV_NOISE}" >&2\n', 1)
    (bin_dir / "uv").write_text(noisy, encoding="utf-8")
    (bin_dir / "uv").chmod(0o755)
    root = release_tree(tmp_path)
    if starless:
        write_pck(root / "build" / "linux" / "mattini.pck", [("scripts/main.gdc", b"no stars")])
    done = run_checks(tmp_path, root)
    assert UV_NOISE in done.stdout, "the stand-in uv spoke"
    lines = [line for line in done.stdout.splitlines() if line.startswith("release check: stars: ")]
    assert len(lines) == 1, done.stdout
    verdict = "FAIL" if starless else "PASS"
    assert re.fullmatch(rf"release check: stars: {verdict} sky/stars\.csv in \S+.*", lines[0]), (
        lines
    )
    assert UV_NOISE not in lines[0], lines[0]


def test_an_override_cfg_already_there_is_not_touched(tmp_path):
    root = release_tree(tmp_path)
    mine = root / "build" / "linux" / "override.cfg"
    mine.write_text('[application]\nconfig/version="the owner\'s own"\n', encoding="utf-8")
    done = run_checks(tmp_path, root)
    assert done.returncode == 1, done.stdout
    assert _verdicts(done.stdout)["override.cfg"] == "FAIL", done.stdout
    assert mine.read_text(encoding="utf-8") == '[application]\nconfig/version="the owner\'s own"\n'


def test_without_the_photo_pack_the_missing_pack_check_fails_and_the_rest_run(tmp_path):
    root = release_tree(tmp_path)
    (root / "build" / "linux" / "mattini-photo.pck").unlink()
    done = run_checks(tmp_path, root)
    assert done.returncode == 1, done.stdout
    assert _verdicts(done.stdout)["missing pack"] == "FAIL", done.stdout
    assert set(_verdicts(done.stdout)) == set(CHECKS), done.stdout


def test_a_build_that_exits_at_once_fails_the_live_log(tmp_path):
    root = release_tree(tmp_path)
    game = root / "build" / "linux" / "mattini.x86_64"
    text = game.read_text(encoding="utf-8").replace('if [ -n "$quit" ]; then', "if true; then")
    game.write_text(text, encoding="utf-8")
    done = run_checks(tmp_path, root)
    assert done.returncode == 1, done.stdout
    assert _verdicts(done.stdout)["live log"] == "FAIL", done.stdout


def test_no_executable_is_refused(tmp_path):
    root = release_tree(tmp_path)
    (root / "build" / "linux" / "mattini.x86_64").unlink()
    done = run_checks(tmp_path, root)
    assert done.returncode == 1, done.stdout
    assert "mattini.x86_64" in done.stdout
