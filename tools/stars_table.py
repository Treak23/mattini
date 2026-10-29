"""Makes game/sky/stars.csv from the Hipparcos Catalogue's main file (brief v0.4.0-06).

Usage: python3 -I tools/stars_table.py <hip_main.dat> <out.csv>

The input is CDS I/239 hip_main.dat of the Hipparcos Catalogue (ESA 1997, ESA SP-1200), which is
downloaded into data/ and never committed. The script reads the whole file and refuses any other
size, then any other SHA-256, before it writes anything (exit 1 and one line naming the value it
found and the one it wants). Standard library only.

Each record is one line of 450 characters and an LF, its fields separated by '|'. The fields
used (1-based bytes of the catalogue's ReadMe): RAhms 18-28 ('hh mm ss.ss', ICRS, J1991.25),
DEdms 30-40 ('+dd mm ss.s', the sign at byte 30) and Vmag 42-46 (F5.2, blank for one record).

The table has every record whose Vmag is not blank and is 6.0 or less (5044 stars). Positions
come from RAhms and DEdms for every star, one rule: ra = (h + m/60 + s/3600) * 15 and
dec = sign * (d + m/60 + s/3600), in degrees, written to 4 decimals; V as given, 2 decimals.
ICRS at epoch J1991.25, used as given: no precession, no proper motion. The stars are sorted by
the written V, then right ascension, then declination, as numbers. The file starts with the
three '# ' header lines below (the credit and the label of the changes that CC BY-NC 3.0 IGO
asks for) and the column header, uses LF endings and ends with an LF.

Prints: stars <count> bytes <size> sha256 <hex>
"""

import hashlib
import sys

SOURCE_BYTES = 53316318
SOURCE_SHA256 = "58ceabb104d647160d9437ce6e513a02a036bb4ad9f8879a5a22fd52943616e0"
V_MAX = 6.0

HEADER = (
    "# Stars derived from the Hipparcos Catalogue (ESA 1997, ESA SP-1200): stars to V 6.0,"
    " positions rounded and reformatted. Credit: ESA. CC BY-NC 3.0 IGO,"
    " https://creativecommons.org/licenses/by-nc/3.0/igo/\n"
    "# Changes made: from CDS I/239 hip_main.dat (53316318 bytes, SHA-256"
    " 58ceabb104d647160d9437ce6e513a02a036bb4ad9f8879a5a22fd52943616e0), the records with"
    " Vmag <= 6.0; right ascension and declination (ICRS, epoch J1991.25, not precessed)"
    " converted from h m s and d m s to degrees, rounded to 4 decimals; Vmag as given; all"
    " other fields dropped; sorted by V, right ascension, declination.\n"
    "# ESA's licence and credit for the catalogue:"
    " https://www.cosmos.esa.int/web/hipparcos/catalogues\n"
    "ra_deg,dec_deg,vmag\n"
)


def _check(data: bytes) -> None:
    """Refuses a file of another size, then of another SHA-256."""
    if len(data) != SOURCE_BYTES:
        sys.exit(f"stars_table: the file has {len(data)} bytes, not {SOURCE_BYTES}")
    found = hashlib.sha256(data).hexdigest()
    if found != SOURCE_SHA256:
        sys.exit(f"stars_table: the file has SHA-256 {found}, not {SOURCE_SHA256}")


def _star(line: str) -> tuple[float, float, float] | None:
    """(V, ra, dec) of a record as written, or None when its V is blank or above 6.0."""
    vmag = line[41:46].strip()
    if not vmag or float(vmag) > V_MAX:
        return None
    h, m, s = line[17:28].split()
    ra = (int(h) + int(m) / 60 + float(s) / 3600) * 15
    dec_field = line[29:40]
    d, dm, ds = dec_field[1:].split()
    sign = -1 if dec_field[0] == "-" else 1
    dec = sign * (int(d) + int(dm) / 60 + float(ds) / 3600)
    return float(f"{float(vmag):.2f}"), float(f"{ra:.4f}"), float(f"{dec:.4f}")


def build(data: bytes) -> str:
    """The table's text for the catalogue's bytes (already checked)."""
    stars = []
    for line in data.decode("ascii").split("\n"):
        if line:
            star = _star(line)
            if star is not None:
                stars.append(star)
    stars.sort()
    return HEADER + "".join(f"{ra:.4f},{dec:.4f},{v:.2f}\n" for v, ra, dec in stars)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        sys.exit("usage: python3 -I tools/stars_table.py <hip_main.dat> <out.csv>")
    with open(argv[1], "rb") as source:
        data = source.read()
    _check(data)
    text = build(data).encode("ascii")
    with open(argv[2], "wb") as out:
        out.write(text)
    count = text.count(b"\n") - HEADER.count("\n")
    print(f"stars {count} bytes {len(text)} sha256 {hashlib.sha256(text).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
