"""Brief M3-03's own tests of the swissTLM3D transfer, beyond the stand-in's pinned ones.

Pinned decisions (docs/SPEC.md §5, *The TLM file*; brief M3-03 decision 6): the file is
fetched into `<file>.part` with `Range: bytes=<part size>-` once the part holds bytes; a body
cut short ends silently (brain.md H9), so the part's size shows the cut; a round makes at
most five GETs; a 206 must start at the byte asked for (else the part is deleted); a 200
is the whole file and rewrites the part; a complete part is verified against the lock and
takes the file's name only if it matches; a wrong one is deleted and fetched once more,
then refused; a run that cannot finish keeps its part and names `python -m mattini download
tlm`; a Ctrl-C keeps it too; provenance.json is removed before the first change on disk.

test_download_photo_surface_tlm.py runs the two commonest paths over real HTTP (a cut, and a
failing run resumed by the next). These run `download.download_tlm` with a scripted file host
in place of urllib, so each way a transfer goes wrong is reached once, cheaply: a host that
ignores the Range, one that answers it from another byte, one that drops the connection
after some bytes, a body of the right size and the wrong bytes, a stale part, a damaged
file, the host's checksum in upper case, a HEAD without a size.

Does NOT prove: the real 2.88 GB transfer (the builder's live run, recorded in the brief's
Findings), or urllib's own handling of 206 and 200 (the pinned tests run it).
"""

import hashlib
import json

import pytest

from mattini import download
from mattini.download import DownloadError, ResumeMismatch, download_tlm

EDITION = "2026-02"
NAME = f"swisstlm3d_{EDITION}_2056_5728.gdb.zip"
URL = f"https://files.example/{NAME}"
BODY = b"".join(hashlib.sha256(f"block {i}".encode()).digest() for i in range(400))  # 12'800 bytes
SHA = hashlib.sha256(BODY).hexdigest()
SIZE = len(BODY)
ITEM_ID = f"swisstlm3d_{EDITION}"
DATASETS = {
    "swisstlm3d": {
        "collection": "ch.swisstopo.swisstlm3d",
        "edition": EDITION,
        "attribution": "© swisstopo",
    }
}
LOCK = {
    "schema": 1,
    "datasets": {
        "swisstlm3d": {
            "collection": "ch.swisstopo.swisstlm3d",
            "edition": EDITION,
            "file": NAME,
            "sha256": SHA,
        }
    },
}


def fetch_json(url):
    item = {
        "id": ITEM_ID,
        "assets": {
            "swisstlm3d_2026-02_2056_5728.gpkg.zip": {
                "href": "https://files.example/decoy",
                "file:checksum": "1220" + "AB" * 32,
            },
            NAME: {"href": URL, "file:checksum": "1220" + SHA.upper()},
        },
    }
    assert url.endswith("/items/" + ITEM_ID), url
    return item


class Host:
    """A scripted file host: each GET takes the next action (default `ok`) from `script`."""

    def __init__(self, script=(), *, size=SIZE, host_sha256=SHA, body=BODY):
        self.script, self.gets, self.heads = list(script), [], 0
        self.size, self.host_sha256, self.body = size, host_sha256, body

    def head(self, url):
        self.heads += 1
        return self.size, self.host_sha256

    def range(self, url, part, start):
        self.gets.append(start)
        action = self.script.pop(0) if self.script else ("ok",)
        kind = action[0]
        have = part.stat().st_size if part.exists() else 0
        assert have == start, (have, start)  # the caller asks from the part's size
        if kind == "mismatch":
            raise ResumeMismatch(f"asked for bytes from {start}, the answer starts elsewhere")
        if kind == "full":  # a 200: the whole file, whatever was asked
            part.write_bytes(self.body)
            return
        if kind == "interrupt":
            part.write_bytes(
                part.read_bytes() + self.body[start : start + action[1]]
            ) if start else (part.write_bytes(self.body[: action[1]]))
            raise KeyboardInterrupt
        data = self.body[start:]
        if kind == "cut":  # ends silently, short (brain.md H9)
            data = data[: action[1]]
        elif kind == "drop":  # raises after some bytes were written
            with open(part, "ab") as out:
                out.write(data[: action[1]])
            raise ConnectionResetError("the network dropped")
        elif kind == "wrong":  # the right size, other bytes
            data = bytes(b ^ 0xFF for b in data)
        with open(part, "ab") as out:
            out.write(data)


def run(tmp_path, host, *, lock=LOCK):
    return download_tlm(
        DATASETS, tmp_path, fetch_json, host.head, host.range, lock=lock, progress=None
    )


FOLDER = f"swisstlm3d/{EDITION}"


def folder(tmp_path):
    return tmp_path / "swisstlm3d" / EDITION


def test_a_plain_transfer_gets_the_whole_file_once(tmp_path):
    host = Host()
    result = run(tmp_path, host)
    assert host.gets == [0] and host.heads == 1
    assert (folder(tmp_path) / NAME).read_bytes() == BODY
    assert sorted(p.name for p in folder(tmp_path).iterdir()) == ["provenance.json", NAME]
    assert result == {
        "attribution": "© swisstopo",
        "collection": "ch.swisstopo.swisstlm3d",
        "dataset": "swisstlm3d",
        "edition": EDITION,
        "file": NAME,
        "item": ITEM_ID,
        "schema": 1,
        "sha256": SHA,
        "size_bytes": len(BODY),
        "url": URL,
    }
    on_disk = (folder(tmp_path) / "provenance.json").read_bytes()
    assert (
        on_disk
        == (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    )


def test_each_cut_is_resumed_from_the_part_s_size(tmp_path):
    host = Host([("cut", 1000), ("cut", 2500), ("cut", 1)])
    run(tmp_path, host)
    assert host.gets == [0, 1000, 3500, 3501]
    assert (folder(tmp_path) / NAME).read_bytes() == BODY


def test_a_connection_dropped_after_some_bytes_keeps_them(tmp_path):
    host = Host([("drop", 4000)])
    run(tmp_path, host)
    assert host.gets == [0, 4000]


def test_a_host_that_ignores_the_range_rewrites_the_part(tmp_path):
    """A 200 for a ranged request is the whole file: nothing of the part is kept."""
    host = Host([("cut", 5000), ("full",)])
    run(tmp_path, host)
    assert host.gets == [0, 5000]
    assert (folder(tmp_path) / NAME).read_bytes() == BODY


def test_a_206_from_another_byte_deletes_the_part_and_starts_again(tmp_path):
    host = Host([("cut", 5000), ("mismatch",)])
    run(tmp_path, host)
    assert host.gets == [0, 5000, 0]
    assert (folder(tmp_path) / NAME).read_bytes() == BODY


def test_five_cuts_in_a_row_refuse_and_keep_the_part_for_the_next_run(tmp_path):
    host = Host([("cut", 100)] * 5)
    with pytest.raises(DownloadError) as refused:
        run(tmp_path, host)
    message = str(refused.value)
    assert message.startswith(f"swisstlm3d {EDITION}: "), message
    assert "after 5 requests" in message and "`python -m mattini download tlm`" in message
    assert host.gets == [0, 100, 200, 300, 400]
    part = folder(tmp_path) / (NAME + ".part")
    assert part.stat().st_size == 500 and not (folder(tmp_path) / NAME).exists()
    assert not (folder(tmp_path) / "provenance.json").exists()

    again = Host()  # the next run resumes at 500 with one GET
    run(tmp_path, again)
    assert again.gets == [500]
    assert (folder(tmp_path) / NAME).read_bytes() == BODY


def test_a_wrong_body_is_deleted_and_fetched_once_more(tmp_path):
    host = Host([("wrong",)])
    run(tmp_path, host)
    assert host.gets == [0, 0]  # the second round starts from nothing
    assert (folder(tmp_path) / NAME).read_bytes() == BODY


def test_a_complete_part_never_has_the_file_s_name_before_it_is_verified(tmp_path, monkeypatch):
    """A Ctrl-C while the part is hashed: the wrong bytes must not sit under the real name."""
    real = download._sha256

    def interrupted(path):
        if path.name.endswith(".part"):
            raise KeyboardInterrupt
        return real(path)

    monkeypatch.setattr(download, "_sha256", interrupted)
    host = Host([("wrong",)])
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, host)
    assert not (folder(tmp_path) / NAME).exists()
    assert (folder(tmp_path) / (NAME + ".part")).stat().st_size == len(BODY)


def test_two_wrong_bodies_are_refused_and_no_part_is_kept(tmp_path):
    host = Host([("wrong",), ("wrong",)])
    with pytest.raises(DownloadError) as refused:
        run(tmp_path, host)
    message = str(refused.value)
    assert message.startswith(f"swisstlm3d {EDITION}: ") and "two complete fetches" in message
    assert SHA in message and "`python -m mattini download tlm`" in message
    assert sorted(p.name for p in folder(tmp_path).iterdir()) == []


def test_a_part_longer_than_the_file_is_not_a_start_of_it(tmp_path):
    (folder(tmp_path)).mkdir(parents=True)
    (folder(tmp_path) / (NAME + ".part")).write_bytes(b"x" * (len(BODY) + 10))
    host = Host()
    run(tmp_path, host)
    assert host.gets == [0] and (folder(tmp_path) / NAME).read_bytes() == BODY


def test_a_complete_part_is_verified_without_a_request_for_it(tmp_path):
    (folder(tmp_path)).mkdir(parents=True)
    (folder(tmp_path) / (NAME + ".part")).write_bytes(BODY)
    host = Host()
    run(tmp_path, host)
    assert host.gets == [] and host.heads == 1  # the HEAD gave the size
    assert (folder(tmp_path) / NAME).read_bytes() == BODY


def test_a_damaged_file_is_replaced_and_provenance_goes_before_the_first_change(tmp_path):
    (folder(tmp_path)).mkdir(parents=True)
    (folder(tmp_path) / NAME).write_bytes(b"damaged")
    (folder(tmp_path) / "provenance.json").write_text("{}", encoding="utf-8")
    host = Host([("interrupt", 100)])
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path, host)
    assert not (folder(tmp_path) / NAME).exists(), "a damaged file never looks valid"
    assert not (folder(tmp_path) / "provenance.json").exists(), "it would list a file that changed"
    assert (folder(tmp_path) / (NAME + ".part")).stat().st_size == 100  # a Ctrl-C keeps the part

    again = Host()
    run(tmp_path, again)
    assert again.gets == [100] and (folder(tmp_path) / NAME).read_bytes() == BODY


def test_the_file_host_s_checksum_in_upper_case_is_the_lock_s(tmp_path):
    host = Host(host_sha256=SHA.upper())
    run(tmp_path, host)
    assert host.gets == [0]


def test_a_missing_host_checksum_is_not_a_disagreement(tmp_path):
    host = Host(host_sha256=None)
    run(tmp_path, host)
    assert host.gets == [0]


def test_a_head_without_a_size_is_refused_before_any_get(tmp_path):
    host = Host(size=None)
    with pytest.raises(DownloadError, match=rf"^swisstlm3d {EDITION}: .*no Content-Length"):
        run(tmp_path, host)
    assert host.gets == [] and not (tmp_path / "swisstlm3d").exists()


def test_a_head_that_fails_is_a_refusal_naming_the_url(tmp_path):
    host = Host()

    def head(url):
        raise ConnectionResetError("no route")

    with pytest.raises(DownloadError) as refused:
        download_tlm(DATASETS, tmp_path, fetch_json, head, host.range, lock=LOCK)
    assert str(refused.value).startswith(f"swisstlm3d {EDITION}: {URL}: cannot ask the file host")
    assert not (tmp_path / "swisstlm3d").exists()


def test_a_lock_that_does_not_fit_is_refused_naming_lock_tlm_and_the_edition(tmp_path):
    lock = json.loads(json.dumps(LOCK))
    lock["datasets"]["swisstlm3d"]["edition"] = "2025-08"
    host = Host()
    with pytest.raises(DownloadError) as refused:
        run(tmp_path, host, lock=lock)
    message = str(refused.value)
    assert message.startswith(f"swisstlm3d {EDITION}: the lock is for swisstlm3d edition")
    assert "`python -m mattini lock tlm`" in message
    assert host.heads == 0 and host.gets == [] and not (tmp_path / "swisstlm3d").exists()


def test_a_config_that_lists_editions_is_a_refusal_naming_the_file(tmp_path):
    datasets = {"swisstlm3d": {**DATASETS["swisstlm3d"], "editions": ["2026"]}}
    del datasets["swisstlm3d"]["edition"]
    host = Host()
    with pytest.raises(DownloadError, match=r"config/datasets\.json.*'swisstlm3d' lists editions"):
        download_tlm(datasets, tmp_path, fetch_json, host.head, host.range, lock=LOCK)
    assert host.heads == 0 and host.gets == []


@pytest.mark.parametrize(
    ("assets", "complaint"),
    [
        ({}, "expected exactly one asset ending '_2056_5728.gdb.zip', found []"),
        (
            {NAME: {"href": URL, "file:checksum": "1220" + SHA}, "a" + NAME: {}},
            "found ['" + "a" + NAME + "', '" + NAME + "']",
        ),
    ],
    ids=["no-gdb-asset", "two-gdb-assets"],
)
def test_an_item_without_exactly_one_filegdb_asset_is_refused_with_the_edition(
    tmp_path, assets, complaint
):
    host = Host()

    def odd_json(url):
        return {"id": ITEM_ID, "assets": assets}

    with pytest.raises(DownloadError) as refused:
        download_tlm(DATASETS, tmp_path, odd_json, host.head, host.range, lock=LOCK)
    message = str(refused.value)
    assert message.startswith(f"swisstlm3d {EDITION}: ") and complaint in message, message
    assert host.heads == 0


def test_the_urllib_transport_names_are_the_ones_the_command_line_uses():
    """The CLI wires these two; the pinned tests run them over HTTP."""
    assert callable(download.urllib_head) and callable(download.urllib_fetch_range)
