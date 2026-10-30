"""Pinning tests for brief v0.5.0-06: tools/release_pack.sh packs a release for GitHub.

Pinned decisions (the owner's 1a, docs/history/blocked/2026-10-29-2.md; brief v0.5.0-06
decisions 4 and 5), run as the workflow runs it, on a stand-in build (fake_release.py):
`tools/release_pack.sh <version> <sha> [<build> [<out>]]` writes into <out> (default
build/release) four files and prints SHA256SUMS:
- `mattini-<version>-linux.tar.gz`: exactly the five Linux files (Terrain3D's library, the two
  data packs, mattini.pck, the executable), each under `mattini-<version>-linux/`, in name
  order (C locale), byte for byte; mode 0755 for `mattini.x86_64` (a player's unpacked game
  starts without a chmod), 0644 for the rest; owner and group 0; the time SOURCE_DATE_EPOCH;
- `mattini-<version>-windows.zip`: the same for the five Windows files under
  `mattini-<version>-windows/`, the time SOURCE_DATE_EPOCH in UTC;
- `SHA256SUMS`: `sha256sum` lines (`<hex>  <path>`) of the two archives and of the ten files
  by their path inside them, sorted by path (C locale); `sha256sum -c` passes beside the two
  unpacked archives;
- `release-notes.md`: tools/release_notes.md with @VERSION@, @SHA@ and the line @SHA256SUMS@
  filled, no placeholder left;
- the same build gives the same bytes: twice, with the build files' times and the time zone
  changed between the runs (lesson 33: the times inside are SOURCE_DATE_EPOCH's, not the
  clock's or the files');
- it refuses with exit 1, naming the cause and writing nothing into <out>: any of the ten files
  missing (a release without a file the game needs; the owner's FB-005); a data pack in a
  build folder that the archive would leave out (a new pack the list forgot); a version that
  is not game/project.godot's (a Release v0.5.0 holding another version's build); a malformed
  version or sha.

Does NOT prove: that the real build's files are these (tools/export.sh and the workflow's live
run); that GitHub accepts the archives (the live run); that the archives unpack on Windows (the
owner's PC); the bytes on another machine's tar, gzip or zip (only that one machine repeats).
"""

import gzip
import hashlib
import os
import stat
import subprocess
import sys
import tarfile
import time
import zipfile

import pytest
from fake_release import EPOCH, LINUX_FILES, WINDOWS_FILES, release_tree, run_pack
from fake_tools import BASH, REPO, VERSION

pytestmark = pytest.mark.skipif(
    BASH is None or sys.platform != "linux", reason="runs tools/release_pack.sh with bash, on Linux"
)

SHA = "0123456789abcdef0123456789abcdef01234567"
LINUX = f"mattini-{VERSION}-linux"
WINDOWS = f"mattini-{VERSION}-windows"
OUTPUTS = [f"{LINUX}.tar.gz", f"{WINDOWS}.zip", "SHA256SUMS", "release-notes.md"]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _packed(tmp_path, *, out="out"):
    root = release_tree(tmp_path)
    done = run_pack(tmp_path, root, VERSION, SHA, "build", out)
    assert done.returncode == 0, done.stdout + done.stderr
    return root, root / out, done


def test_the_script_exists_and_is_executable():
    script = REPO / "tools" / "release_pack.sh"
    assert script.is_file(), "tools/release_pack.sh is missing"
    assert os.access(script, os.X_OK), "tools/release_pack.sh is not executable"


def test_it_writes_the_two_archives_the_sums_and_the_notes(tmp_path):
    _root, out, done = _packed(tmp_path)
    assert sorted(path.name for path in out.iterdir()) == sorted(OUTPUTS)
    sums = (out / "SHA256SUMS").read_text(encoding="utf-8")
    assert sums in done.stdout, "SHA256SUMS is printed for the log"


def test_the_linux_archive_holds_the_five_files_in_order_with_the_exec_bit(tmp_path):
    root, out, _ = _packed(tmp_path)
    data = (out / f"{LINUX}.tar.gz").read_bytes()
    assert data[:2] == b"\x1f\x8b", "gzip"
    assert gzip.decompress(data)[257:262] == b"ustar", "a tar inside"
    with tarfile.open(out / f"{LINUX}.tar.gz", "r:gz") as tar:
        members = tar.getmembers()
        assert [m.name for m in members] == [f"{LINUX}/{name}" for name in LINUX_FILES]
        for member in members:
            name = member.name.split("/")[1]
            assert member.isfile(), member.name
            want = 0o755 if name == "mattini.x86_64" else 0o644
            assert stat.S_IMODE(member.mode) == want, (member.name, oct(member.mode))
            assert (member.uid, member.gid) == (0, 0), member.name
            assert member.mtime == EPOCH, (member.name, member.mtime)
            source = root / "build" / "linux" / name
            assert tar.extractfile(member).read() == source.read_bytes(), member.name


def test_the_windows_archive_holds_the_five_files_in_order(tmp_path):
    root, out, _ = _packed(tmp_path)
    with zipfile.ZipFile(out / f"{WINDOWS}.zip") as archive:
        infos = archive.infolist()
        assert [i.filename for i in infos] == [f"{WINDOWS}/{name}" for name in WINDOWS_FILES]
        when = time.gmtime(EPOCH)[:6]
        for info in infos:
            name = info.filename.split("/")[1]
            assert info.date_time == when, (info.filename, info.date_time, when)
            source = root / "build" / "windows" / name
            assert archive.read(info) == source.read_bytes(), info.filename


def test_sha256sums_holds_the_archives_and_the_ten_files_sorted(tmp_path):
    root, out, _ = _packed(tmp_path)
    expected = {
        f"{LINUX}.tar.gz": _sha256((out / f"{LINUX}.tar.gz").read_bytes()),
        f"{WINDOWS}.zip": _sha256((out / f"{WINDOWS}.zip").read_bytes()),
    }
    for folder, platform, files in (
        (LINUX, "linux", LINUX_FILES),
        (WINDOWS, "windows", WINDOWS_FILES),
    ):
        for name in files:
            expected[f"{folder}/{name}"] = _sha256((root / "build" / platform / name).read_bytes())
    lines = (out / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    paths = sorted(expected, key=lambda path: path.encode())
    assert lines == [f"{expected[path]}  {path}" for path in paths]
    with tarfile.open(out / f"{LINUX}.tar.gz", "r:gz") as tar:
        tar.extractall(out, filter="data")
    with zipfile.ZipFile(out / f"{WINDOWS}.zip") as archive:
        archive.extractall(out)
    check = subprocess.run(
        ["sha256sum", "-c", "SHA256SUMS"], cwd=out, capture_output=True, text=True, check=False
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert os.access(out / LINUX / "mattini.x86_64", os.X_OK), "the unpacked game starts as it is"


def test_the_notes_are_the_template_filled(tmp_path):
    root, out, _ = _packed(tmp_path)
    notes = (out / "release-notes.md").read_text(encoding="utf-8")
    template = (root / "tools" / "release_notes.md").read_text(encoding="utf-8")
    for placeholder in ("@VERSION@", "@SHA@", "@SHA256SUMS@"):
        assert placeholder in template, placeholder
    assert "@" + "VERSION@" not in notes and "@SHA" not in notes
    assert VERSION in notes and SHA in notes
    for line in (out / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        assert f"\n{line}\n" in notes, line
    assert "© swisstopo" in notes


def test_the_same_build_packs_to_the_same_bytes(tmp_path):
    root, first, _ = _packed(tmp_path, out="first")
    for path in (root / "build").rglob("*"):
        if path.is_file():
            os.utime(path, (EPOCH + 86400 * 400, EPOCH + 86400 * 400))
    done = run_pack(tmp_path, root, VERSION, SHA, "build", "second", TZ="Pacific/Kiritimati")
    assert done.returncode == 0, done.stdout + done.stderr
    for name in OUTPUTS:
        assert (first / name).read_bytes() == (root / "second" / name).read_bytes(), name


def test_without_source_date_epoch_outside_git_it_refuses(tmp_path):
    root = release_tree(tmp_path)
    done = run_pack(tmp_path, root, VERSION, SHA, "build", "out", SOURCE_DATE_EPOCH="")
    assert done.returncode == 1, done.stdout + done.stderr
    assert not (root / "out").exists()


@pytest.mark.parametrize(
    "missing",
    [f"linux/{name}" for name in LINUX_FILES] + [f"windows/{name}" for name in WINDOWS_FILES],
)
def test_a_missing_file_is_refused_and_named(tmp_path, missing):
    root = release_tree(tmp_path)
    (root / "build" / missing).unlink()
    done = run_pack(tmp_path, root, VERSION, SHA, "build", "out")
    assert done.returncode == 1, done.stdout + done.stderr
    assert f"build/{missing}" in done.stdout + done.stderr
    assert not (root / "out").exists() or not any((root / "out").iterdir())


@pytest.mark.parametrize("platform", ["linux", "windows"])
def test_a_data_pack_the_archive_would_leave_out_is_refused(tmp_path, platform):
    root = release_tree(tmp_path)
    (root / "build" / platform / "mattini-shadows.pck").write_bytes(b"a pack nobody listed")
    done = run_pack(tmp_path, root, VERSION, SHA, "build", "out")
    assert done.returncode == 1, done.stdout + done.stderr
    assert "mattini-shadows.pck" in done.stdout + done.stderr
    assert not (root / "out").exists() or not any((root / "out").iterdir())


@pytest.mark.parametrize(
    "version, sha",
    [
        ("9.9.9", SHA),
        (f"v{VERSION}", SHA),
        (f"{VERSION}-rc1", SHA),
        (VERSION, SHA[:12]),
        (VERSION, SHA.upper()),
        (VERSION, SHA + "0"),
    ],
    ids=["another-version", "a-v-prefix", "a-suffix", "a-short-sha", "upper-case", "41-digits"],
)
def test_a_wrong_version_or_sha_is_refused(tmp_path, version, sha):
    root = release_tree(tmp_path)
    done = run_pack(tmp_path, root, version, sha, "build", "out")
    assert done.returncode == 1, done.stdout + done.stderr
    assert (version if version != VERSION else sha) in done.stdout + done.stderr
    assert not (root / "out").exists() or not any((root / "out").iterdir())


def test_another_version_names_the_project_s(tmp_path):
    root = release_tree(tmp_path)
    done = run_pack(tmp_path, root, "9.9.9", SHA, "build", "out")
    assert "game/project.godot" in done.stderr and VERSION in done.stderr, done.stderr


def test_the_defaults_are_build_and_build_release(tmp_path):
    root = release_tree(tmp_path)
    done = run_pack(tmp_path, root, VERSION, SHA)
    assert done.returncode == 0, done.stdout + done.stderr
    assert sorted(p.name for p in (root / "build" / "release").iterdir()) == sorted(OUTPUTS)
