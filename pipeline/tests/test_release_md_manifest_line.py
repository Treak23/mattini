"""Pinning tests for brief v0.6.0-03: docs/RELEASE.md §C's manifest-pair command (M3 R2 S-02).

Pinned decision (brief v0.6.0-03 decision 4): §C's one command that compares the fresh clone's
game/assets/generated/manifest.json with the release's pair prints what it found and says which
check failed. Today's `test "$(wc -c < ...)" -eq <size> && echo ... | sha256sum -c -` prints
nothing and exits 1 on a manifest of another size, so "its output in the release record" records
nothing (M3 R2 S-02). The command is read from §C (the one inline code span that holds both `wc
-c < game/assets/generated/manifest.json` and `sha256sum -c`) and run with bash in a scratch
checkout, its size and SHA-256 replaced by the scratch manifest's (or by others):
- the pair: exit 0, the size it found printed, sha256sum's `OK`;
- another size: exit non-zero, the size it found printed and the word "size" (the size check
  failed), whether or not bash runs with -e;
- the size right, another SHA-256: exit non-zero, the size it found printed, sha256sum's
  `FAILED`.

Does NOT prove (a census of a doc, then a run of the command it holds): that the size and SHA-256
written in §C are the release's (each release's plan names its pair; the session writes them
there); that the session pastes this command, or records its output (RELEASE.md §D's record);
anything about the workflow's own pair step (test_release_workflow.py).
"""

import hashlib
import re
import subprocess
import sys

import pytest
from fake_tools import BASH, REPO

RELEASE_MD = REPO / "docs" / "RELEASE.md"
MANIFEST = "game/assets/generated/manifest.json"
HEX64 = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{64}(?![0-9a-fA-F])")


def _section_c():
    text = RELEASE_MD.read_text(encoding="utf-8")
    start = text.index("\n## C. ")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def _command():
    spans = [
        span
        for span in re.findall(r"`([^`\n]+)`", _section_c())
        if f"wc -c < {MANIFEST}" in span and "sha256sum -c" in span
    ]
    assert len(spans) == 1, f"one manifest-pair command in §C, found {spans}"
    command = spans[0]
    shas = set(HEX64.findall(command))
    assert len(shas) == 1, f"one SHA-256 in the command: {shas}"
    sizes = set(re.findall(r"(?<![\w.])\d{4,}(?![\w.])", HEX64.sub("", command)))
    assert len(sizes) == 1, f"one size in the command: {sizes}"
    return command, shas.pop(), sizes.pop()


def test_the_command_names_the_plan_s_pair_once_each():
    _command()


def _run(tmp_path, size, sha, *bash_flags):
    command, plan_sha, plan_size = _command()
    manifest = tmp_path / MANIFEST
    if not manifest.exists():
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes(b'{"schema": 1, "a stand-in manifest": true}\n')
    text = command.replace(plan_sha, sha)
    text = re.sub(rf"(?<![\w.]){plan_size}(?![\w.])", size, text)
    return subprocess.run(
        [BASH, "--noprofile", "--norc", *bash_flags, "-c", text],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        capture_output=True,
        text=True,
        check=False,
    )


def _pair(tmp_path):
    _run(tmp_path, "1", "0" * 64)  # writes the stand-in manifest
    data = (tmp_path / MANIFEST).read_bytes()
    return str(len(data)), hashlib.sha256(data).hexdigest()


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs the command with bash")
def test_the_pair_passes_and_prints_the_size(tmp_path):
    size, sha = _pair(tmp_path)
    done = _run(tmp_path, size, sha)
    out = done.stdout + done.stderr
    assert done.returncode == 0, out
    assert re.search(rf"(?<!\d){size}(?!\d)", out), f"the size it found, {size}, printed: {out}"
    assert f"{MANIFEST}: OK" in out, out


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs the command with bash")
@pytest.mark.parametrize("flags", [(), ("-e", "-o", "pipefail")], ids=["bash", "bash-e"])
def test_another_size_prints_the_size_and_names_the_size_check(tmp_path, flags):
    size, sha = _pair(tmp_path)
    done = _run(tmp_path, str(int(size) + 1), sha, *flags)
    out = done.stdout + done.stderr
    assert done.returncode != 0, out
    assert re.search(rf"(?<!\d){size}(?!\d)", out), f"the size it found, {size}, printed: {out}"
    assert re.search(r"\bsize\b", out), f"the failed check named: {out}"


@pytest.mark.skipif(BASH is None or sys.platform != "linux", reason="runs the command with bash")
def test_another_sha256_prints_the_size_and_sha256sum_s_failure(tmp_path):
    size, _ = _pair(tmp_path)
    done = _run(tmp_path, size, "ab" * 32)
    out = done.stdout + done.stderr
    assert done.returncode != 0, out
    assert re.search(rf"(?<!\d){size}(?!\d)", out), f"the size it found, {size}, printed: {out}"
    assert "FAILED" in out, out
