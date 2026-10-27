#!/bin/bash
# Design's second program for brief v0.4.0-06's star table (the first is the brief's
# tools/stars_table.py, Python slicing each record's bytes). This one is independent of it:
# awk splits each record of hip_main.dat on the "|" CDS writes between its fields (H3 RAhms is
# field 4, H4 DEdms field 5, H5 Vmag field 6), mawk's printf rounds, sort(1) orders the lines,
# and the header lines are typed here from the brief's words, not taken from the Python.
# Expected (design, 2026-10-27, mawk 1.3.4 and GNU sort): stars 5044 bytes 112045 sha256
# e2a98eea26d486805cc340e648f79235cedf6274a6d39d02712c908f72487d3f.
# Usage: bash v0.4.0-06-stars-awk.sh <hip_main.dat> <out.csv>
set -euo pipefail
export LC_ALL=C
src="$1"
out="$2"
size=$(stat -c %s "$src")
[ "$size" = 53316318 ] || { echo "refused: $size bytes" >&2; exit 1; }
sha=$(sha256sum "$src" | cut -d' ' -f1)
[ "$sha" = 58ceabb104d647160d9437ce6e513a02a036bb4ad9f8879a5a22fd52943616e0 ] || {
  echo "refused: SHA-256 $sha" >&2
  exit 1
}
{
  printf '%s\n' "# Stars derived from the Hipparcos Catalogue (ESA 1997, ESA SP-1200): stars to V 6.0, positions rounded and reformatted. Credit: ESA. CC BY-NC 3.0 IGO, https://creativecommons.org/licenses/by-nc/3.0/igo/"
  printf '%s\n' "# Changes made: from CDS I/239 hip_main.dat (53316318 bytes, SHA-256 58ceabb104d647160d9437ce6e513a02a036bb4ad9f8879a5a22fd52943616e0), the records with Vmag <= 6.0; right ascension and declination (ICRS, epoch J1991.25, not precessed) converted from h m s and d m s to degrees, rounded to 4 decimals; Vmag as given; all other fields dropped; sorted by V, right ascension, declination."
  printf '%s\n' "# ESA's licence and credit for the catalogue: https://www.cosmos.esa.int/web/hipparcos/catalogues"
  printf '%s\n' "ra_deg,dec_deg,vmag"
  awk -F'|' '
    {
      v = $6; gsub(/ /, "", v)
      if (v == "" || v + 0 > 6.0) next
      split($4, r, " ")
      sgn = substr($5, 1, 1)
      split(substr($5, 2), d, " ")
      if (sgn != "+" && sgn != "-") { print "no sign: HIP " $2 > "/dev/stderr"; exit 2 }
      ra = (r[1] + r[2] / 60 + r[3] / 3600) * 15
      de = d[1] + d[2] / 60 + d[3] / 3600
      if (sgn == "-") de = -de
      printf "%.4f,%.4f,%.2f\n", ra, de, v + 0
    }' "$src" | sort -t, -k3,3g -k1,1g -k2,2g
} > "$out"
echo "stars $(($(wc -l < "$out") - 4)) bytes $(stat -c %s "$out") sha256 $(sha256sum "$out" | cut -d' ' -f1)"
