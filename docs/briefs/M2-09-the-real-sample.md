# Brief: M2-09 — the real sample, the buildings reader's fixture
Status: OPEN

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

The buildings reader is tested on swisstopo's own file. The owner allowed one real sample
in git on 2026-09-25 (SPEC §13 row 24): sheet 1328-33 of swissBUILDINGS3D 3.0, edition
2020, 45'668 bytes, three buildings, © swisstopo. Today only the real run over the
village's six sheets reads an Esri MultiPatch; every test reads the synthetic features the
reader hands over (M2-04).

- The sample and its README are in `tests/shared/buildings_sample/`.
- A test reads it with `read_sheet` and finds its three buildings, their triangles and
  their first points.
- The hygiene test allows exactly that file, with exactly those bytes, and nothing else.

## Read first, in order

1. `CLAUDE.md` Hard Rule 3 (and its one exception); `docs/SPEC.md` §8 *The buildings*
   (*Source*, *Reading*), §9 *Test data*, §13 row 24.
2. `pipeline/mattini/buildings.py` (`read_sheet`), `pipeline/tests/test_buildings_read.py`,
   `pipeline/tests/test_repo_hygiene.py`.
3. The pinned files, `docs/briefs/pinning/M2-09/`.

## Decisions already made

- **The file:** copy
  `/tmp/claude-0/-home-user-mattini/bea2be16-f780-5dd6-9dd8-5304b8b207c1/scratchpad/sample_pending/buildings_sample/swissbuildings3d_3_0_2020_1328-33_2056_5728.gdb.zip`
  (design's download of 2026-09-25, checked against the lock) to
  `tests/shared/buildings_sample/` under the same name, and check its SHA-256 is
  `72b2502856d315b9f265f8279a9491cfa3f45065a42cc492824fd9731d7c4292` before anything else.
  It is swisstopo's file unchanged; never re-zip or edit it. `.gitattributes` already
  marks `*.zip` binary.
- **The README** (pinned) names the source, the bytes, `© swisstopo` and the terms.
- **The tests** (pinned):
  - `test_buildings_read_sample.py` reads the sample through `read_sheet`;
  - `test_repo_hygiene.py` names the sample with its SHA-256 in `REAL_SAMPLE`, excludes
    exactly that path from the raw-data refusal, and requires the file with those bytes
    and a README holding `© swisstopo` and the SHA-256.

  Design ran both in the live layout before pinning: ruff clean, 665 passed. Each fails as
  expected under four mutations: a byte changed (both files), a second zip beside it, the
  README without `© swisstopo`, the sample removed.

## Scope: files you may touch

`tests/shared/buildings_sample/` (the sample and the pinned README) ·
`pipeline/tests/test_buildings_read_sample.py` · `pipeline/tests/test_repo_hygiene.py`
(both pinned, put in place by the copy step, never edited).

## Depends on

M2-07 landed (it may touch `pipeline/tests/`; if it changed `test_repo_hygiene.py`, stop:
BLOCKED, since the pinned copy is a full file).

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical (`cmp`), and the sample's SHA-256
      is the one above.
      - does NOT prove: that the pinned tests are the right tests.
- [ ] Mutations (Findings: both runs of each):
      - one byte of the sample changed: both tests' SHA-256 checks fail;
      - a copy of the sample as `tests/shared/buildings_sample/other.zip`: the hygiene
        test fails;
      - `read_sheet` made to keep each ring's closing point: the sample test fails.
      - does NOT prove: that another edition or a larger sheet reads the same way (the
        real run over the six sheets, checked against the chunk hashes, does).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: anything about the game.

## Forbidden

Any other raw file in git; a change to the sample's bytes, to `read_sheet`, or to the
pinned files.

## Findings (executor writes)
