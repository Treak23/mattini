# Brief: M2-07 — M2 R1's fixes, the pipeline half
Status: OPEN

Written in the design realm; executed under `docs/roles/BUILD.md` (in M2 by an Opus agent
of the one M2 session, the owner's word of 2026-09-25, `docs/history/RULINGS.md`).

## Goal

The pipeline findings of review round M2 R1 (`docs/reviews/M2-R1-*.md`) are fixed.

- **Their inputs (P-02, I-01):** the expected values in `config/terrain.json` and
  `config/buildings.json` name the world config and the locked inputs they were computed
  for. A changed world or an adopted republished input then gets a refusal that says so
  and names design's step, where today it blames "this machine or this code" and points to
  a command that cannot succeed.
- **The buildings' box (P-03):** the manifest checks the buildings block's box against
  the world's area.
- **The download (I-02, I-03):** it is proven to refuse before fetching anything, and to
  remove `provenance.json` before a fetch.
- **The sheets (I-04):** the download and the buildings step agree on what a valid lock is.
- **Refusals, not tracebacks (I-05):** the two refusals that end in a traceback now reach
  the owner as `mattini: error:` lines.
- **The grid (I-06):** the sheet grid refuses the ids and boxes it cannot place.
- **Stale chunks (G-06, the pipeline half):** a buildings build removes the chunk files of
  an earlier build that its block no longer lists.

## Read first, in order

1. `CLAUDE.md`: Hard Rules 2, 4 and 5.
2. `docs/SPEC.md` §5 (the lock), §8 (*The terrain grid*, its expected output; *The
   buildings*, its expected output).
3. `docs/reviews/M2-R1-placement.md` P-02, P-03; `docs/reviews/M2-R1-inputs.md` I-01 to
   I-06; `docs/reviews/M2-R1-game.md` G-06.
4. `pipeline/mattini/terrain.py`, `buildings.py`, `download.py`, `lock.py`, `sheets.py`,
   `manifest.py`, `__main__.py`.
5. The pinned files, `docs/briefs/pinning/M2-07/`.

## Decisions already made

- **What an expected value was computed for (P-02, I-01; SPEC §8).**
  - Each area of `config/terrain.json` and of `config/buildings.json` gains
    `computed_for`: exactly `{"inputs_sha256": <hex>, "world_sha256": <hex>}`, 64
    lower-case hex digits each. `world_sha256` is the SHA-256 of `config/world.json`'s
    bytes. `inputs_sha256` is the SHA-256 of the lock's entry for the dataset
    (`swissalti3d` or `swissbuildings3d`) rendered canonically:
    `json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`,
    UTF-8. The area's key sets become exactly
    `{"computed_for", "expected_sha256", "spacing_m"}` for the terrain and
    `{"computed_for", "expected_sha256"}` for the buildings.
  - `terrain`, `buildings`, and `manifest` for a block that is built, compare
    `computed_for` with the world config and the lock before they compare any output.
    Each difference is its own refusal, and none blames the machine or the code:
    - the world: "the expected values in config/<x>.json were computed for the world
      config with SHA-256 <recorded>; config/world.json now has <current>. A changed
      world is a design change: design recomputes the expected values (docs/SPEC.md §8)";
    - the inputs: "… were computed from the <dataset> lock entry with SHA-256
      <recorded>; config/datasets.lock.json's entry now has <current> (a new edition or
      an adopted republished file). Adopting new inputs is a design change: design
      recomputes the expected values (docs/SPEC.md §5, §8)".

    After both match, the existing output comparison and its message stay as they are.
  - The download's republish refusals (terrain and buildings) add: "then design
    recomputes the expected values in config/<x>.json (docs/SPEC.md §8)".
  - Design's values (pinned under `docs/briefs/pinning/M2-07/`: `config/terrain.json`,
    `config/buildings.json`, the three fixtures' configs):

    | Config | world_sha256 | inputs_sha256 |
    |---|---|---|
    | `config/terrain.json` | `d2607d13…299509b` | `025f9045…6f6424d` |
    | `config/buildings.json` | `d2607d13…299509b` | `4000a698…1f81605b` |
    | `tests/shared/terrain_fixture/terrain.json` | `3cab21e5…1e5e75` | `c241206d…f05b9ffa` |
    | `tests/shared/terrain_fixture_nw/terrain.json` | `f5bef481…adb2a40` | `25a8845a…45adc4a` |
    | `tests/shared/buildings_fixture/buildings.json` | `e7cd091d…d5254a` | `352a8f06…70da1e67` |

    The buildings fixture's `terrain.json` exists only to name its area. Its
    `expected_sha256` and `computed_for` are the first terrain fixture's: labelled
    placeholders, since no terrain is ever built in that fixture (P-06). Its vectors'
    `about` says so.
- **The buildings' box (P-03):** `built_buildings_block` compares `lv95_box` with the world
  config's box for the area, as floats, as `terrain._check_shape` does; the refusal names
  the field, both values and `python -m mattini buildings`.
- **The download (I-02, I-03, I-04):**
  - a test starts from an empty folder with a middle sheet republished, and asserts that
    nothing is fetched and `<out>/swissbuildings3d` does not exist;
  - a test completes a download, deletes one file, makes its re-fetch fail twice, and
    asserts `provenance.json` is gone;
  - `download buildings` requires the lock's buildings entry to pin exactly the area's
    sheets, as the step and the manifest do, naming `python -m mattini lock buildings`.
- **Refusals, not tracebacks (I-05):** `lock buildings` and `download buildings` check that
  `config/datasets.json` holds `swissbuildings3d` (a `DatasetsConfigError` or
  `DownloadError` naming the file). The sheet grid's `ValueError` reaches the owner as a
  `DownloadError` or `LockError` naming the area and `config/world.json`. A command-line
  test runs each and finds `mattini: error:` and no `Traceback`.
- **The grid (I-06):**
  - `sheet_box` refuses ids 2000 and above ("not an LK25 sheet mattini's grid places");
  - `sheets_near` refuses a box within the margin of the grid's east edge (E 2'830'000,
    "no sheets east of E 2'830'000 in mattini's grid: design extends it");
  - the docstrings and `test_sheets_grid.py`'s wording say what the grid covers.
- **Stale chunks (G-06):** after writing, `write_buildings` removes every `*.bin` in
  `buildings/` that the new block does not list (the description's own `.json` is kept),
  and says how many it removed on stderr.

## Scope: files you may touch

`pipeline/mattini/*.py` · `pipeline/tests/` · the pinned design data put in place by the
copy step (`config/terrain.json`, `config/buildings.json`,
`tests/shared/terrain_fixture/terrain.json`, `tests/shared/terrain_fixture_nw/terrain.json`,
`tests/shared/buildings_fixture/buildings.json`, `tests/shared/buildings_fixture/terrain.json`,
`tests/shared/buildings_vectors.json`), never edited.

## Depends on

None beyond what is merged. It shares no file with M2-08.

## Done when (gates)

- [ ] The pinned copies are in place and byte-identical (`cmp`).
      - does NOT prove: that the pinned tests are the right tests.
- [ ] Mutations (Findings: both runs of each):
      - the world check removed: the shifted-origin test fails;
      - the inputs check removed: the republished-and-relocked test fails;
      - the buildings' box check removed: the shifted-box test fails;
      - the up-front comparison moved into the fetch loop: the empty-folder test fails.
      - does NOT prove: anything about a real republish (none exists to try).
- [ ] With the real inputs (scratch), `terrain` and `buildings` still write design's
      bytes, and `manifest` accepts them.
      - does NOT prove: that it renders.
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the game shows the buildings where the terrain is (M2-08).

## Forbidden

A change to any expected value, to the rules (SPEC §8) or to any fixture's generated bytes.

## Findings (executor writes)
