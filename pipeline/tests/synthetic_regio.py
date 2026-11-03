"""swissALTIRegio tiles as swisstopo publishes them, for the pinning tests of brief M4-02.

The live format (measured by M4-01's design rehearsal on all 30 village tiles, 2026-10-17):
one zip per 10 km tile, `swissaltiregio_<E km>-<N km>_2056_5728.xyz.zip`, holding one member
`<E km>_<N km>.xyz`: ASCII, CRLF line ends, the header `x y z`, then one line per cell
`<x> <y> <z>` separated by single spaces, x and y whole metres at the cells' centres, z in
metres with up to two decimals and no trailing zeros (`2430.6`, `2431`), rows north to south
and west to east within a row. The live zips are deflated.

The shared fixture (tests/shared/surroundings_fixture/) keeps the members' text in
`source.json`, since no `.zip` may be committed (test_repo_hygiene.py), and its lock pins
the zips this module writes from it: stored, not deflated, with fixed metadata, so their
bytes, and with them the lock, `computed_for` and the generated description, are the same
on every machine (a deflated zip's bytes depend on the zlib build, brain.md H27).
`deflated=True` writes the live form for the tests that read it; its SHA-256 is computed
where it is written, never pinned.

`raw_regio(root, source)` writes `download regio`'s layout (brief M4-01):
`<root>/swissaltiregio/<edition>/` with the zips and provenance.json (the terrain's keys:
attribution, collection, dataset, edition, resolution_m, schema, tiles [{file, item,
sha256, size_bytes, tile, url}] in tile order), and returns the root and a lock holding the
matching `swissaltiregio` entry.
"""

import copy
import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surroundings_fixture"
DATASET = "swissaltiregio"
COLLECTION = "ch.swisstopo.swissaltiregio"
EDITION = "2026-06"
ZIP_TIME = (2026, 4, 2, 16, 1, 0)  # the live members' date (2615_1084.xyz)
URL = "https://data.geo.admin.ch/ch.swisstopo.swissaltiregio/{item}/{file}"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def zip_name(tile: str) -> str:
    return f"swissaltiregio_{tile}_2056_5728.xyz.zip"


def member_name(tile: str) -> str:
    return tile.replace("-", "_") + ".xyz"


def z_text(cents: int) -> str:
    """A height in whole centimetres as swisstopo writes it: `2430.6`, `2431`, `-3.05`."""
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    text = f"{whole}.{frac:02d}".rstrip("0").rstrip(".")
    return sign + text


def xyz_text(points) -> str:
    """The member's text for [(x, y, cents)], in the order given."""
    lines = ["x y z"] + [f"{x} {y} {z_text(cents)}" for x, y, cents in points]
    return "\r\n".join(lines) + "\r\n"


def xyz_zip(member: str, text: str, *, deflated: bool = False) -> bytes:
    """One zip holding `member` with `text`; stored with fixed metadata unless `deflated`."""
    info = zipfile.ZipInfo(member, date_time=ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED if deflated else zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o644 << 16
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(info, text.encode("ascii"))
    return buffer.getvalue()


def fixture_source() -> dict:
    """tests/shared/surroundings_fixture/source.json: {tile: {member, text}} and its label."""
    return json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))


def fixture_datasets() -> dict:
    return json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]


def raw_regio(
    root: Path,
    source: dict | None = None,
    *,
    deflated: bool = False,
    datasets: dict | None = None,
) -> tuple[Path, dict]:
    """Write `download regio`'s layout for `source` (default: the fixture's) under `root`.

    Returns (root, lock): the lock holds exactly the `swissaltiregio` entry pinning the zips
    written, with the datasets config's collection, edition and resolution.
    """
    source = copy.deepcopy(source if source is not None else fixture_source())
    config = (datasets or fixture_datasets())[DATASET]
    folder = Path(root) / DATASET / config["edition"]
    folder.mkdir(parents=True, exist_ok=True)
    tiles, entries = {}, []
    for tile in sorted(source["tiles"]):
        member = source["tiles"][tile]["member"]
        data = xyz_zip(member, source["tiles"][tile]["text"], deflated=deflated)
        name = zip_name(tile)
        (folder / name).write_bytes(data)
        tiles[tile] = {"file": name, "sha256": sha256(data)}
        item = f"{DATASET}_{tile}"
        entries.append(
            {
                "file": name,
                "item": item,
                "sha256": sha256(data),
                "size_bytes": len(data),
                "tile": tile,
                "url": URL.format(item=item, file=name),
            }
        )
    provenance = {
        "attribution": config["attribution"],
        "collection": config["collection"],
        "dataset": DATASET,
        "edition": config["edition"],
        "resolution_m": config["resolution_m"],
        "schema": 1,
        "tiles": entries,
    }
    text = json.dumps(provenance, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    (folder / "provenance.json").write_bytes(text.encode("utf-8"))
    entry = {
        "collection": config["collection"],
        "edition": config["edition"],
        "resolution_m": config["resolution_m"],
        "tiles": tiles,
    }
    return Path(root), {"schema": 1, "datasets": {DATASET: entry}}


def points_of(text: str) -> list[tuple[int, int, str]]:
    """The (x, y, z text) of a member's text, in its order (the header dropped)."""
    lines = text.split("\r\n")
    assert lines[0] == "x y z" and lines[-1] == "", "not swisstopo's XYZ form"
    return [(int(x), int(y), z) for x, y, z in (line.split(" ") for line in lines[1:-1])]


def with_lines(text: str, lines: list[str]) -> str:
    """A member's text with its point lines replaced by `lines` (the header kept)."""
    return "\r\n".join(["x y z", *lines]) + "\r\n"
