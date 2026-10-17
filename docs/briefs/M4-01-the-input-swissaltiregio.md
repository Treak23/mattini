# Brief: M4-01 — The input: swissALTIRegio
Status: OPEN

Written in the design realm; executed by one fresh builder session under
`docs/roles/BUILD.md`. Lane A of wave 1 (m4-design §1; the arc plan names the waves).

## Goal

The heights of the mountains around the village reach every machine pinned, checksummed and
reproducible, as every other input does (SPEC §5). **swissALTIRegio**, swisstopo's 10 m
terrain model of Switzerland and its neighbours, comes in 10 km tiles of zipped XYZ text.

`config/datasets.json` names it, with the source text its terms require. Two new commands:
- `python -m mattini lock regio` pins the SHA-256 of the 30 tiles the village's surroundings
  need;
- `python -m mattini download regio` fetches and verifies them into
  `data/raw/swissaltiregio/2026-06/`.

No step reads them yet. M4-02, built at the same time, reads this layout.

## Read first, in order

1. `CLAUDE.md` (Hard Rules 2, 3, 5); `brain.md` H9, H14, H18, H20, H22.
2. `docs/briefs/sketches/m4-design.md` §0 (swissALTIRegio), §1, §1a, §2 (the box and the
   vertices, which decide the tiles).
3. `docs/SPEC.md` §5 (the lock, the downloads, the paragraph *The photo, the surface model and
   swissTLM3D*: this brief follows it for a fourth tile dataset).
4. `pipeline/mattini/datasets.py`, `lock.py`, `download.py`, `__main__.py`, and their tests:
   `test_lock_photo_surface_tlm.py`, `test_download_photo_surface_tlm.py`,
   `local_swisstopo.py` (the pins here build on it), `test_m3_03_*.py`.
5. `config/surroundings.json` (design data, committed with the plan; never edited here).
6. The pinned files: `docs/briefs/pinning/M4-01/`.

## Decisions already made

1. **The dataset** (the pinned `config/datasets.json`, m4-design §1, §1a).
   - `swissaltiregio`: collection `ch.swisstopo.swissaltiregio`, edition `2026-06`,
     `resolution_m` 10 (an integer).
   - `attribution`: the product page's source text for the 2025 and later versions,
     verbatim as design corrected it (§1a), one line. The credits print it whole.
   - `resolution_m` is required for it, as for the other datasets read at a resolution
     (`datasets.RESOLUTION_DATASETS`).
2. **What the live STAC API publishes** (measured by design's rehearsal, 2026-10-17; all
   2'366 items of the collection read):
   - one national item `swissaltiregio` (a 10.1 GB COG; not used: its bytes cannot be
     verified in part) and 2'365 tile items `swissaltiregio_<E km>-<N km>`;
   - the id names the tile's **south-west corner** in whole kilometres, four digits each
     (`2615-1084`, `2385-0974`); the corners lie at E = 5 km + 10 km·i and N = 4 km + 10 km·j;
   - each tile item has exactly one asset, `swissaltiregio_<tile>_2056_5728.xyz.zip`
     (`application/x.ascii-xyz+zip`), with `file:checksum` `1220` + SHA-256 in upper-case
     hex. The file host's HEAD gives `x-amz-meta-sha256` in lower case;
   - **the ids carry no edition.** Every tile item's `properties.datetime` is
     `2026-06-01T00:00:00Z`; hence the edition `2026-06`.
3. **The file format** (all 30 village tiles read, 179'684'396 bytes; M4-02 reads it):
   - the zip holds one deflated member `<E km>_<N km>.xyz` (`2615_1084.xyz`, 24.9 MB);
   - ASCII with CRLF line ends, the header `x y z`, then 1'000'000 lines `<x> <y> <z>`
     separated by single spaces;
   - x and y are whole metres at the 10 m cells' centres (`2615005 1093995`), each exactly
     once, a complete 1000 × 1000 grid inside the tile's square;
   - z in metres with up to two decimals and no trailing zeros (`2430.6`, `2431`);
   - rows north to south, west to east within a row. No nodata in the village's tiles.
4. **The tiles of an area** (m4-design §2, decided by design here):
   - the surroundings box is the area's box grown by `margin_m`;
   - a vertex every `spacing_m` takes the samples in the half-open square
     [E − s/2, E + s/2) × [N − s/2, N + s/2), so the samples needed lie in
     [e_min − s/2, e_max + s/2) × [n_min − s/2, n_max + s/2) of that box;
   - `download.regio_tiles(world, area, *, margin_m, spacing_m)` lists every tile whose
     square [E0, E0 + 10 km) × [N0, N0 + 10 km) meets that region: east outer, north inner,
     sorted.
   - `margin_m` and `spacing_m` come from the area's entry in `config/surroundings.json`
     (20'000 and 100 for the village); the area is the one `config/terrain.json` names, as
     for every other input.
   - The village needs 6 × 5 = **30 tiles**, E 2595 … 2645, N 1074 … 1114. Its east edge
     (2'645'000) lies on a tile edge: the column 2645 is needed only for the half square
     beyond it.
   - Read `config/surroundings.json` with a small reader in `download.py` (two whole numbers
     for the area, refused naming the file otherwise). `surroundings.py` is M4-02's, in the
     same wave; M4-09 may move the reader onto it.
5. **The lock entry** `swissaltiregio`, exact keys:
   - {collection, edition, resolution_m, tiles: {<tile>: {file, sha256}}}, the checksum in
     lower case;
   - written only by `python -m mattini lock regio`, from the STAC items only: no request to
     the file host, not even a HEAD;
   - it replaces its own entry and keeps every other;
   - before writing, every item's `properties.datetime` must lie in the pinned edition (it
     starts with `<edition>-`); else it is refused naming the tile, its datetime and the
     edition, and nothing is written. Without this a new edition would be locked under the
     old name;
   - `lock.validate_lock` knows the entry, and the malformed-lock error names all six lock
     commands.
6. **`download regio`** (`--out`, default data/raw) follows the terrain's flow:
   - first `lock.fit_problem` (collection, edition, resolution, exactly the tiles
     `regio_tiles` gives), naming `python -m mattini lock regio` and no other command,
     before swisstopo is asked anything;
   - then every item: its datetime in the edition, its published name and SHA-256 the
     lock's, all before any request for a file and before anything on disk changes;
   - the republish refusal names the tile, both checksums, "nothing was fetched",
     `python -m mattini lock regio`, "then commit the lock" and design's step for
     **config/surroundings.json**;
   - then the files: `.part`, verified, renamed, one retry, a verified file kept;
   - `swissaltiregio/2026-06/provenance.json` gets exactly the terrain's keys
     (`attribution` the whole source text).
   - `fit_problem` gains the `swissaltiregio` row. How it learns the margin and spacing is
     the builder's: a keyword argument, or the reader of decision 4.
7. **Existing tests that change** (measured in design's rehearsal with a throwaway
   implementation). A sixth dataset in the config and the lock breaks exactly these, and
   each update is a count or a set:
   - `test_datasets_editions.py::test_the_committed_config_holds_the_five_datasets`;
   - `test_lock_photo_surface_tlm.py::test_each_command_writes_its_exact_entry_and_keeps_every_other`;
   - `test_measured_photo_surface_tlm.py::test_the_committed_lock_pins_the_measured_entries`;
   - `test_m3_03_commands.py::test_raw_folder_is_the_edition_or_the_editions_joined`
     (`2026-06` sorts after swissalti3d);
   - `test_m3_03_fit_and_lock_shapes.py`: the "all five commands" cases and
     `test_the_five_commands_are_the_five_lock_datasets`.

   The first three are pinned copies of DONE briefs; their live copies may evolve
   (WORKFLOW §Brief lifecycle).
8. **The measured values** (live, 2026-10-17):
   - `lock.entry_sha256` of the entry: `9afdf81d58968b902b85e46b1ef9134dd30040114a73ad16940051246caaf908`,
     which `config/surroundings.json` records as `computed_for.inputs_sha256`;
   - every tile's SHA-256 is in the pinned `test_m4_01_measured_regio.py`;
   - the lock after `lock regio`: 11'327 bytes, SHA-256
     `c8dbea540753aab587bcdab8d0d663a029f2db067c9d23205f635b88c28f4d39`; `git diff --numstat`
     127 added, 0 removed;
   - `download regio` into a scratch root: 30 files, 179'696'978 bytes with provenance.json,
     whose SHA-256 is `52e95dc7f2b95b8633a40e5df3f4fa39d5dd655a1cbea847b8d199b45e7871a0`.
     The first run took 37.5 s, the second 10.2 s with 0 fetches.
9. **SPEC §5** says mattini does not use swissALTIRegio. Design changes that sentence with the
   arc's SPEC edit, not here.

## Scope — files you may touch

- `config/datasets.json`: design's pinned copy, put in place by the copy step, never edited.
  It lands in the same commit as the `datasets.py` change.
- `config/datasets.lock.json`: written only by `lock regio` against the live STAC.
- `pipeline/mattini/datasets.py`, `lock.py`, `download.py`, `__main__.py`.
- `pipeline/tests/`:
  - the pinned copies (`local_regio.py` and the `test_m4_01_*.py` files);
  - the existing tests of decision 7;
  - `test_download_network.py`, if you add the regio entry there too;
  - your own new `test_m4_01_*.py`.

Not `surroundings.py` (M4-02), `config/surroundings.json`, `tests/shared/`, `manifest.py`,
the steps, `game/`, `tools/`.

## Depends on

None. M4-02 runs at the same time in lane B. Its tests use its own fixture; its real-data run
needs this brief's download. `test_m4_01_expected_inputs.py` here is the seam: the committed
`config/surroundings.json` must have been computed for the entry `lock regio` writes.

## Done when (gates)

- [ ] The pinned copies are in place (`cp -r docs/briefs/pinning/M4-01/. .`) and stay
      byte-identical (`cmp`, before every commit).
      - does NOT prove: that they are the right tests.
- [ ] `lock regio` against the live API writes the lock `c8dbea54…` (127 added lines), unless
      swisstopo republished meanwhile. If it did, that is a BLOCKED question: design's
      expected heights depend on the entry. `test_m4_01_measured_regio.py` and
      `test_m4_01_expected_inputs.py` pass.
      - does NOT prove: that swisstopo will not republish later (the download refuses that).
- [ ] `download regio` into a scratch root writes 30 files and provenance `52e95dc7…`; a
      second run fetches nothing. `pytest -m network pipeline/tests/test_m4_01_regio_network.py`
      passes. Record the times; delete the scratch files.
      - does NOT prove: that M4-02's step reads the files right (the integration run does).
- [ ] Mutations, each failing a named pinned test, recorded:
      - the tiles without the half-spacing border;
      - the edition not checked against the items;
      - the lock compared lazily while fetching;
      - the fit without the resolution;
      - the republish refusal naming another config;
      - tile ids not zero-padded.
      - does NOT prove: that these are the only ways to get it wrong (lesson 4).
- [ ] Standard gate: `tools/gate.sh > gate.log && git commit …`
      - does NOT prove: that the far mountains' heights are right (M4-02), or anything drawn.

## Forbidden

- Committing anything under `data/`, or downloading into the repository's `data/` for the
  gates (use a scratch root).
- Changing a pinned file, the measured values or `config/surroundings.json`.
- Using the national COG; any new dependency.
- The step, the manifest or the game.

## Findings (executor writes)
