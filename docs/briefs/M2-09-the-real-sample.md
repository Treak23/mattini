# Brief: M2-09 — the real sample, the buildings reader's fixture
Status: DONE (eced376)

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

- [x] The pinned copies are in place and byte-identical (`cmp`), and the sample's SHA-256
      is the one above.
      - does NOT prove: that the pinned tests are the right tests.
- [x] Mutations (Findings: both runs of each):
      - one byte of the sample changed: both tests' SHA-256 checks fail;
      - a copy of the sample as `tests/shared/buildings_sample/other.zip`: the hygiene
        test fails;
      - `read_sheet` made to keep each ring's closing point: the sample test fails.
      - does NOT prove: that another edition or a larger sheet reads the same way (the
        real run over the six sheets, checked against the chunk hashes, does).
- [x] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: anything about the game.

## Forbidden

Any other raw file in git; a change to the sample's bytes, to `read_sheet`, or to the
pinned files.

## Findings (executor writes)

Executor agent of the one M2 session, 2026-09-26, in its own worktree and branch (the
owner's run mode; nothing synced or pushed). Implementation commit `eced376`.

1. **Start state.** The worktree started at `8553563`, the head of the session branch (and
   of `origin/main` at that moment), which holds `cccd92e` two docs-only commits back
   (`f298cc2`, `8553563`: CLAUDE.md, brain.md, ROADMAP.md, SPEC.md). `git merge --ff-only
   cccd92e` said `Already up to date`; the brief and its pinned files are the same at both
   commits (`git diff --stat cccd92e HEAD` names only those four files). So the head was
   not `cccd92e` but its descendant, and the work stands on `8553563`. H19 did not
   reproduce this time: the worktree was not of an older `main`.
2. **Depends on.** M2-07 did not touch `pipeline/tests/test_repo_hygiene.py` (its last
   change is `d643870`, M0 R1). The pinned copy differs from the live file only by the
   M2-09 lines (`REAL_SAMPLE`, `import hashlib`, the exclusion in
   `test_no_raw_geodata_about_to_be_committed`, the new test, the docstring), read with
   `diff` before copying. Not blocked.
3. **The sample.** The source file was checked before anything else: 45'668 bytes, SHA-256
   `72b2502856d315b9f265f8279a9491cfa3f45065a42cc492824fd9731d7c4292`. It was copied with
   `cp` (not re-zipped) and `cmp` finds it identical to the source. `git check-ignore`
   exits 1 (not ignored), and `.gitattributes`' `*.zip binary` covers it. The zip holds one
   folder, `swissBUILDINGS3D_3-0_1328-33.gdb/`, with 61 entries, all deflated. The
   scratchpad folder the sample came from also holds a `README.md` of 757 bytes that
   differs from the pinned README (935 bytes). The pinned one was used, as the brief says.
4. **Pinned copies.** `cp -r docs/briefs/pinning/M2-09/. .` placed
   `pipeline/tests/test_buildings_read_sample.py`, `pipeline/tests/test_repo_hygiene.py`
   and `tests/shared/buildings_sample/README.md`. `cmp` against the pinned files found
   all three identical after the copy, after the three mutations were undone, before
   `eced376` and before this commit. Run alone, the two test files give 24 passed (2 + 22),
   ruff is clean, and the sample test prints no warning (2 passed in 0.26 s).
5. **Standard gate** (`tools/gate.sh > gate-M2-09.log 2>&1 && git commit`), exit 0 for
   `eced376`. The steps: `uv lock --check`; pytest **743 passed**, 4 deselected (the
   `network` marker), 92 warnings; ruff check, and ruff format (65 files); `manifest`;
   Godot `4.6.3.stable.official.7d41c59c4` and `GUT: game/addons/gut/plugin.cfg:
   version="9.6.1"`; import and parse check; GUT **23 scripts, 110 tests, 110 passing,
   2800 asserts**, `---- All tests passed! ----`; gdlint clean; gdformat 32 files
   unchanged; `== gate: all steps passed`. It printed 83 `ERROR` lines, all in the GUT
   step and all excepted, the same count as M2-08's run, because nothing in the game
   changed. M2-09 adds three tests: the sample file's two and the hygiene file's
   `test_the_one_real_sample_is_swisstopo_s_file_with_its_readme`. Design's pinning run
   counted 665, which is M2-08's 662 plus these 3; this tree also holds M2-07's tests
   (740 + 3).
6. **Mutation runs.** Each ran the full gate, which stopped at pytest, and each was undone
   with `git apply -R` of its saved diff. `git status` afterwards showed only the four
   Scope files. The run before any mutation was the first full gate: 743 passed,
   `all steps passed`.
   - *One byte of the sample changed.* The low bit of byte 10 was flipped (the first
     entry's local-header modification time, `0x6b` → `0x6a`). That byte was chosen
     because the zip stays readable with it changed, so only a hash check can tell. Gate
     exit 1, **2 failed**, 741 passed:
     `test_buildings_read_sample.py::test_the_sample_is_the_published_file` (line 41,
     `assert '6b81b039aa52...77914825715e0' == '72b2502856d3...fd9731d7c4292'`) and
     `test_repo_hygiene.py::test_the_one_real_sample_is_swisstopo_s_file_with_its_readme`
     (line 115, the path and the same two hashes).
     `test_the_real_sheet_reads_in_order_as_triangles` passed: the changed file still
     reads, so only the two SHA-256 checks hold the sample's bytes. Harm reproduced: bytes
     other than swisstopo's (an edited or re-zipped sample) sitting in git under the one
     name the owner allowed. Undone with `git apply -R` (the diff was made with
     `--binary`), and `sha256sum` shows `72b2…4292` again. Both tests passed in the next
     two mutation runs.
   - *A copy of the sample as `tests/shared/buildings_sample/other.zip`.* This had two
     runs. (a) Untracked: gate exit 1, **2 failed**, 741 passed:
     `test_repo_hygiene.py::test_no_raw_geodata_about_to_be_committed` (line 108,
     `AssertionError: ['tests/shared/buildings_sample/other.zip']`) and
     `test_repo_tracked.py::test_every_file_the_gate_or_the_game_depends_on_is_tracked`
     (line 93, `on disk but not in git's index (stage them)`). (b) Staged with `git add`,
     as a commit would carry it: **1 failed**, 742 passed, only
     `test_no_raw_geodata_about_to_be_committed`, with the same message. Harm reproduced:
     a second raw swisstopo file entering git history beside the one allowed (Hard Rule
     3). Undone with `git apply -R --index` of a diff from `/dev/null`. The test passed in
     the next mutation run.
   - *`read_sheet` keeps each ring's closing point* (`ring[:3]` → `ring`, `buildings.py`
     line 255). Gate exit 1, **1 failed**, 742 passed:
     `test_buildings_read_sample.py::test_the_real_sheet_reads_in_order_as_triangles`
     (line 52, `assert 4 == 3`, on the first triangle of `{B1DC7692…}`, whose first point
     `(2622709.7309999987, 1098156.074000001, 2828.6408999999985)` comes back as its
     fourth). **No other test failed.** Two files read synthetic sheets through
     `read_sheet` and neither saw it. `test_buildings_read.py`'s
     `test_a_synthetic_sheet_reads_its_triangles` checks the triangle count and the *set*
     of points, and a repeated first point leaves both unchanged. `test_buildings_reader.py`
     (line 47) compares each triangle as the set of its points, which a repeated point
     leaves unchanged too. The step's tests
     replace `read_sheet` with a stub (`test_buildings_step.py:78`), and the rule tests
     feed `build_chunks` features by hand. Harm reproduced: the reader hands over
     four-point triangles. In the real run, `build_chunks`' `_snapped` refuses them
     (`buildings.py:326`, `… is not three (E, N, H) points`), so the owner's
     `python -m mattini buildings` would stop at its first building and build no
     buildings. Until this brief only that real run could show it. Undone with
     `git apply -R`; the test passed in the gate of `eced376`.
7. **Out-of-scope touches:** none. `pipeline/mattini/buildings.py` changed only during
   the third mutation and was restored; `eced376` holds the four Scope files and nothing
   else (`4 files changed, 98 insertions(+), 4 deletions(-)`).
8. **Follow-up candidates (design's call).**
   - Mutation 3 shows that neither synthetic reader test can tell a triangle from a
     triangle with its closing point kept, so the committed sample is now the only
     reader-level guard of "three points per triangle" in the gate. A check that every
     triangle `read_sheet` returns has three points, for example in
     `test_buildings_reader.py` (not a pinned file), would give the synthetic tests that
     guard too, without the sample. It lies outside this brief's Scope.
   - The sample test's does-NOT-prove stands: another edition or a larger sheet (the
     real run over the six sheets against `config/buildings.json`'s chunk hashes).
