# Review M2 R1 — lens `inputs`, inputs (Tier 2)

- **Range:** `git diff 63816ac..88678e2 -- . ':!game/addons' ':!pipeline/uv.lock'`; head reviewed `88678e2`.
- **Date:** 2026-09-25.
- **How:** one Opus agent of the M2 session in its own worktree (the owner's run mode, RULINGS 2026-09-25); every P0 to P2 finding then put to three skeptic agents told to refute it. Reproduced here from the agents' structured reports, unedited except for layout.
- **Standard gate at the head:** exit 0.

## Findings

### M2-R1-I-01 · P2 · Adopting a republished tile or sheet, as the tool instructs, ends in a refusal that blames the machine or the code

- **Where:** pipeline/mattini/terrain.py:370-376; pipeline/mattini/buildings.py:578-583; pipeline/mattini/download.py:190-195 and 253-258 (the remedy text); config/terrain.json, config/buildings.json; docs/SPEC.md:92-107 (§5) and §8's expected-output paragraphs
- **Claim:** The expected SHA-256s (M2-01 terrain, M2-04 buildings) carry no record of the input tiles or sheets they were computed from, and nothing compares them with the lock. When swisstopo republishes, the download's refusal says to run `lock terrain|buildings` and commit. The next `terrain`/`buildings` then refuses with 'Design computed the expected value two independent ways, so this machine or this code produces other heights than the design's'. `manifest` refuses the old build and names `python -m mattini terrain`, which cannot help. No message and no doc (SPEC §5, §8) says that design must recompute config/terrain.json or config/buildings.json.
- **Proof:** Scratch review-R1/I/repin.py: took the 2x2 test's four tiles, rewrote 2624-1095 0.25 m higher, and re-pinned provenance and lock to it, which is what `lock terrain` + `download terrain` leave. build_terrain at 2 m refused: 'the heights built here have SHA-256 cf33326c..., config/terrain.json expects 42756c1c.... Design computed the expected value two independent ways, so this machine or this code produces other heights than the design's; nothing was written'. buildings.py:580-582 uses the same wording. Grep of SPEC finds no step for recomputing expected values after a republish. swisstopo has already republished the 2020 sheets inside the edition once (items updated 2025-01-28, M2-03 Findings 3).
- **Harm:** When a republish happens, the owner follows the pipeline's own instruction and is then told that his PC or the code is wrong. No command resolves it: the only fix is design data. Nothing wrong is written.
- **Fix:** Store with each expected value the SHA-256s of the inputs it was computed from, or compare the lock's entry with them before building. On a difference, refuse with 'the inputs changed since design computed <file> (tile X: A -> B): design recomputes the expected value'. Have the download's republish refusal and SPEC §5 name that step too.
- **Verification:** Upheld by 3 of 3 skeptics (grades P2, P2, P2).

  - Skeptic 1: holds, P2. I could not refute it; every part of the claim checks out at 88678e2.

1. The download refusals at download.py:190-195 and 253-258 say a republished tile or sheet "is adopted only on purpose: `lock ...`, then commit the lock". `lock` prints only the lock's path and says nothing about the expected values.
2. After a re-lock and re-download, `build_terrain` passes its checks that provenance matches the lock and each file's SHA-256 matches provenance. It then compares the heights with `config/terrain.json` and refuses with a message that blames "this machine or this code". I reran the reviewer's repin.py on a `git archive` of 88678e2 in scratch and got the same refusal (cf33326c... built, 42756c1c... expected). buildings.py `_compare_with_expected` (lines 570-583) runs after the same provenance and lock checks and uses the same wording.
3. `built_terrain_block`'s lock check (the manifest side) refuses the old build through `fail()`, which appends "`python -m mattini terrain` rebuilds the terrain". That command is the one that then refuses, so no command gets out of this state.
4. SPEC §8 (around line 233) says a mismatch means "a machine or a code change that computes other heights". SPEC §5 has no step for recomputing the expected values. I searched WORKFLOW, the DESIGN and BUILD role docs, RELEASE, brain.md and ROADMAP for this and found nothing.

**Arguments against the finding, and why they fail:**
- A republish that changes only file bytes and not the heights or geometry would build fine, because the expected SHA-256 covers the output, not the input files. But any republish that changes the data hits this dead end.
- Refusing is the correct, safe outcome, and nothing wrong is written. What is wrong is the stated cause: the message makes a false claim (Hard Rule 2, honest states), and no documented step leads to the fix, which is design data.
- The scenario is realistic: M2-03 Findings 3 records that the 2020 sheets were already republished once inside the edition.

**Grade:** P2 is right. It needs an unusual input or a future change (a republish), it fails safe, and the harm is a misleading diagnosis plus a missing process step, not a wrong world. It is more than P3 (cosmetic): the message sends the owner and design after a machine or code fault that does not exist, and nothing tells anyone to recompute `config/terrain.json` or `config/buildings.json`.
  - Skeptic 2: holds, P2. The finding holds. At 88678e2, download.py:190-195 and 253-258 tell the user that a republished tile or sheet "is adopted only on purpose: `lock terrain|buildings`, then commit the lock". Nothing else is named as a step.

The two build steps compare their output only with the config's expected value:
- terrain.py:370-376 checks against config/terrain.json `expected_sha256[spacing]`.
- buildings.py:571-583 (`_compare_with_expected`) checks against config/buildings.json.

Neither expected value records the input SHA-256s it came from, and neither is ever compared with the lock. So after a deliberate re-lock and download, the refusal gives a false cause.

Reproduction: I extracted 88678e2 into scratch and ran the reviewer's repin.py (one 2x2-test tile raised 0.25 m, provenance and lock re-pinned). build_terrain refused with "the heights built here have SHA-256 cf33326c..., config/terrain.json expects 42756c1c.... Design computed the expected value two independent ways, so this machine or this code produces other heights than the design's". That message blames the machine or the code, not the input change. The manifest side (built_terrain_block) refuses the old build because its tiles no longer match the lock, and it names `python -m mattini terrain`, which cannot succeed.

On the docs:
- SPEC §5 (lines 90-97) says only that a republish is "a deliberate change like a new edition", and "a new edition is a deliberate config change".
- SPEC §8's expected-output paragraphs (lines 225-235, 332-341) never say that a change of inputs requires design to recompute terrain.json or buildings.json.
- A grep of SPEC, brain.md, RELEASE.md, ROADMAP, WORKFLOW and the role docs finds no such step.

Mitigation that does not refute it: gate tests pin the committed lock values (test_the_committed_lock_pins_the_six_measured_tiles and _sheets). So an agent's gate would fail after a re-lock commit, and M1-01 says a republish is a BLOCKED question for builders. But the owner runs the real pipeline on his PC, since the gate has no network, and he follows the tool's own message. Neither of these reaches him.

Grade: P2 is right. It needs an unusual input, a swisstopo republish, which has happened once for the 2020 sheets. Nothing wrong is written, because the refusal itself is correct. But the message states a false cause, which touches Hard Rule 2's honest-error clause, and the documented procedure dead-ends. That is more than cosmetic, so it is not P3, and it is not a normal-use defect, so it is not P1.
  - Skeptic 3: holds, P2. The finding holds; I could not refute it. I checked it against 88678e2 myself.

1. **Where the expected value comes from.** At terrain.py:299, `build_terrain` takes `expected` straight from `config/terrain.json[areas][area][expected_sha256][spacing]`.
   - Neither config records which input tiles or sheets that value came from. `config/terrain.json` holds only `expected_sha256` and `spacing_m`. `config/buildings.json` holds only `expected_sha256` per chunk.
   - Nothing compares the lock with the expected value before the build. The per-tile checks only compare provenance, lock and file bytes with each other, and all three agree after a lock plus download.
   - terrain.py:370-376 and buildings.py:578-583 then refuse with "Design computed the expected value two independent ways, so this machine or this code produces other heights/buildings than the design's".

2. **The download's advice leads here.** download.py:190-195 and 253-258 tell the user to adopt a republished tile or sheet with `lock terrain|buildings`, then commit the lock. `manifest` (manifest.py:7-9 via `built_terrain_block`) refuses the old build and names `python -m mattini terrain`. Following those instructions leads straight to the refusal above.

3. **I reproduced it independently.** I extracted 88678e2 with `git archive` into scratchpad/skeptic3-I01/tree and ran the review's repin.py. Output: "refused: area 'village' at 2 m: the heights built here have SHA-256 cf33326c..., config/terrain.json expects 42756c1c.... Design computed the expected value two independent ways, so this machine or this code produces other heights than the design's; nothing was written". That matches the finding exactly.

4. **No document gives the missing step.** I grepped SPEC, briefs, lock.py, `__main__.py` and brain.md for "republish" and "recomput". SPEC §5 (lines 92-107) and the §8 expected-output paragraphs (lines 225-236, 332-341) never say that adopting a new lock needs design to recompute `terrain.json` or `buildings.json`. M1-01's "a republish is a BLOCKED question" covers only the first lock run, not later adoption, which the download message tells the user to do himself. M1-R1 T-04 already treated "owner adopts it on purpose" as the expected flow.

5. **The republish precedent is real.** M2-03 Findings 3 records the 2020 sheets updated 2025-01-28. That was before design read them, but it shows swisstopo does republish inside an edition.

**Why not refuted, and why not another grade.** The refusal is correct in that nothing wrong is written, and Hard Rule 5 holds. But the message states a false cause (this machine or this code) when the real cause is the inputs. Every command involved sends the user around a loop that no command can end.

- Not P1: this needs a rare external event, not normal use, and no gate is broken.
- Not P3: it is more than wording. There is no mechanism that tells an input change from a code change, and no documented recovery path.
- P2 ("an unusual input or a future change") fits.

### M2-R1-I-02 · P2 · No test makes the buildings download refuse a republished sheet from an empty folder before fetching anything

- **Where:** pipeline/mattini/download.py:249-258; pipeline/tests/test_buildings_download.py:204-215 (pinned); pipeline/tests/test_buildings_inputs.py:215-230
- **Claim:** Both tests of 'refused before anything on disk changes' first run a complete download. Checking each sheet lazily just before its fetch therefore passes both, even though the brief's guarantee is broken.
- **Proof:** Mutation review-R1/I/mut-lazy.diff moved the lock comparison into the fetch loop. Full pipeline pytest: 662 passed, 0 failed. With the mutation, scratch lazy_harm.py (empty folder, 1348-12 republished) made 3 fetches, wrote 1328-33, 1328-34 and 1348-11, then refused with a message that says 'nothing was fetched'. Unmutated code: 0 fetches, no folder created. Restored with git apply -R; tree clean.
- **Harm:** A later refactor could fetch about 9.5 MB and create folders before refusing, while the message claims nothing was fetched, and the gate would stay green (M2-03's stated guarantee). Already on the board as M2-03 check residue (P2); reproduced here.
- **Fix:** Add a test that starts from an empty folder with a middle sheet republished. Assert file_fetches == [] and that <out>/swissbuildings3d does not exist.
- **Verification:** Upheld by 3 of 3 skeptics (grades P2, P2, P2).

  - Skeptic 1: holds, P2. The finding holds. I reproduced it in an untracked scratch copy made with git archive; the main checkout was not touched. In download_buildings at 88678e2 (download.py:249-258), every published sheet is compared with the lock before the mkdir and before any fetch. Both tests of that guarantee first run a full download: test_a_republished_sheet_is_refused_before_anything_changes (test_buildings_download.py:204-215) and test_a_sheet_whose_lock_sha256_differs_by_one_digit_is_refused_before_anything (test_buildings_inputs.py:215-230). With the earlier sheets already on disk and verified, _fetch_into does not fetch them again. So a check made lazily, just before each sheet's fetch, also gives file_fetches == [] and leaves the folder unchanged. The parametrised no-entry/edition/collection/missing-sheet test does start from nothing, but it covers _locked_sheets, not the per-sheet SHA comparison. I applied the lazy mutation myself: the mkdir moved above the loop and the comparison moved into the fetch loop. Results: the four buildings and download test files gave 42 passed. The full pipeline suite gave 638 passed and 24 failed, and the same 24 fail on the unmutated scratch tree because it has no .git (test_origin_census, test_repo_hygiene, test_release_hygiene, test_repo_tracked). So the mutation adds no failure. Harm, reproduced with FakeBuildingsStac, an empty folder and 1348-12 republished: the mutated code fetched 1328-33, 1328-34 and 1348-11, created swissbuildings3d/2020/, then refused with a message that says 'nothing was fetched'. The unmutated code made 0 fetches and created no folder. With the real sizes, those three sheets come to 9,554,035 bytes, which matches the claimed 9.5 MB. The brief's text ('compares every asset's file name and SHA-256 with the lock before anything on disk changes') makes this a stated guarantee. The shipped code is correct today, so this is not a live defect. It is a weak gate against a plausible refactor, which matches P2 ('a future change or a weak gate'). It is not P1: removing the check outright is still caught, because the pre-populated test would then fetch the republished sheet. It is already on the board as M2-03 check residue at P2, which confirms the finding rather than refuting it. The proposed fix is sound: start from an empty folder with a middle sheet republished, and assert file_fetches == [] and that <out>/swissbuildings3d does not exist.
  - Skeptic 2: holds, P2. The finding holds, and I reproduced it on a copy of 88678e2 in the scratchpad (git archive, so the main checkout was not touched).

Both tests of "refused before anything changes" do a complete download before they republish 1348-12:
- test_buildings_download.py:204-215
- test_buildings_inputs.py:215-230

After a full run, each earlier sheet is already on disk and matches. `_fetch_into` then neither fetches it nor deletes provenance.json, so a lazy check that runs just before each fetch refuses at 1348-12 with `file_fetches == []` and nothing changed. The other refusal tests fail in `_locked_sheets` or `published_sheets` (fetch_json 404), which run before the comparison loop, so they cannot catch this reordering either.

What I ran:
- **Unmutated:** lazy_harm.py (empty folder, 1348-12 republished) gave 0 fetches and no folder created.
- **With review-R1/I/mut-lazy.diff applied:**
  - The same script made 3 fetches and left 1328-33, 1328-34 and 1348-11 on disk.
  - It then raised the DownloadError whose message says "nothing was fetched".
  - The full `pytest pipeline/tests` run gave 662 passed, 4 deselected, 0 failed.

The claim, the proof and the fix are all correct.

On the grade: the code today is correct. The docstring guarantee (download.py:241-243) and the brief's guarantee (M2-03 line 81) are only half-tested. Under the mutation, the files fetched before the refusal are the locked, verified ones, so no wrong data would be kept. The harm is bandwidth, a created folder, and an error message that states something false (Hard Rule 2 wording). The republish refusal itself is still tested, so this is not a gate that cannot fail over the Hard Rule 5 guard. That is "a future change / a weak gate", so P2. It is not P1 or P3, and it matches the residue already graded P2 on docs/ROADMAP.md:27-28.
  - Skeptic 3: holds, P2. I could not refute it; it holds as a P2. I reproduced it on a copy of 88678e2 made with git archive into scratchpad/sk3-I02/tree. The main checkout was not touched and its status is still clean.

(1) The claim is true. download_buildings (download.py:249-258) compares every published name and SHA-256 with the lock before the mkdir and fetch loop. Only two tests change a sheet's published SHA-256 against the lock:
- test_a_republished_sheet_is_refused_before_anything_changes (test_buildings_download.py:204-215, pinned)
- test_a_sheet_whose_lock_sha256_differs_by_one_digit_is_refused_before_anything (test_buildings_inputs.py:215-230)
Both run a complete download first. So under a lazy check, the earlier sheets are already on disk and match, _fetch_into skips them, and file_fetches == [] plus the unchanged folder snapshot still pass.

The other tests that start from an empty folder do not cover this path:
- The parametrized lock-does-not-fit test is refused in _locked_sheets.
- test_a_missing_sheet_item_is_refused_naming_it is refused in published_sheets (a 404).
Both refusals happen before the comparison the mutation moves.

(2) The proof reproduces. I applied review-R1/I/mut-lazy.diff and the full pipeline pytest gave 662 passed, 4 deselected, 0 failed, so the mutant survives. I then ran lazy_harm.py (empty folder, 1348-12 republished):
- Mutated: 3 fetches; 1328-33, 1328-34 and 1348-11 written; then a refusal whose text still says 'nothing was fetched'.
- Unmutated: 0 fetches and no folder.
The 9.5 MB figure matches the brief's byte counts: 45,668 + 391,181 + 9,117,186 = 9,554,035 bytes.

(3) The harm is real but limited. Today's code is correct. Under the mutation the files written are the locked, verified bytes, so there is no wrong world and no lost data. What is lost is the brief's stated guarantee ('compares every asset ... before anything on disk changes'): a refactor could waste the bandwidth and leave a refusal message that is false under Hard Rule 2 (honest states), and the gate would stay green.

(4) The grade fits. This is a weak gate against a future change, which is exactly the P2 definition. It is not P1, because no normal use hits a defect today. It is not P3, because it is a behavioural guarantee and a false error message, not cosmetics.

(5) It is a duplicate of known residue, not a new discovery. docs/ROADMAP.md:27 already records it as M2-03's check residue graded P2 ('the download's refusal before any fetch is proven only when the earlier sheets are already on disk'). The finding says so itself.

The proposed fix is right: from an empty folder with a middle sheet republished, assert file_fetches == [] and that <out>/swissbuildings3d does not exist.

### M2-R1-I-03 · P3 · Removing provenance.json before fetching a missing file is untested

- **Where:** pipeline/mattini/download.py:429-431 (the guarantee is stated at download.py:19-23)
- **Claim:** The docstring guarantees that provenance.json 'exists only after a run that completed'. The unlink before fetching a missing file can be removed without any test failing. The helper is shared by the terrain and buildings downloads.
- **Proof:** Mutation review-R1/I/mut-prov.diff dropped the unlink in the `if not dest.exists()` branch. Full pytest: 662 passed. Scratch prov_harm.py: complete download, 1348-11 deleted, then two failed refetches left provenance.json listing the missing 1348-11. Unmutated: provenance.json removed. Restored; tree clean.
- **Harm:** Under a regression, provenance.json would list a file that is not on disk after a failed run. The build step then refuses visibly (it cannot read the file), so there is no wrong world. The gate cannot fail on this guarantee. Board residue, reproduced.
- **Fix:** Add a test: complete download, delete one file, make the refetch fail twice, then assert provenance.json is absent.
- **Verification:** P3: not put to the skeptics.

### M2-R1-I-04 · P3 · Seam M2-03/M2-04: the download accepts a lock that the buildings step and the manifest refuse

- **Where:** pipeline/mattini/download.py:364-367 (only missing sheets are refused) vs pipeline/mattini/buildings.py:637-640 (exact sheet set) and buildings.py:771-776 (manifest)
- **Claim:** `download buildings` accepts a lock whose buildings entry pins more sheets than the area needs. `buildings` and `manifest` require exactly the area's sheets. On the terrain side both halves accept a superset.
- **Proof:** Scratch superset.py used the committed lock plus a pin for 1347-22 against the live STAC. download_buildings returned '6 sheets verified'. build_buildings then refused: 'the lock pins the sheets [1328-33, 1328-34, 1347-22, 1348-11, ...], the area needs [...six]; `python -m mattini lock buildings` writes its buildings entry'.
- **Harm:** The download reports success and the build then refuses. The named remedy (`lock buildings`) works, so this is two halves disagreeing on what a valid lock is, not a wrong world.
- **Fix:** Pick one rule for both halves: either the download also requires exactly the area's sheets (naming `lock buildings`), or the step and the manifest compare only the area's sheets, as the terrain does.
- **Verification:** P3: not put to the skeptics.

### M2-R1-I-05 · P3 · `lock buildings` and `download buildings` end in a Python traceback on two refusals

- **Where:** pipeline/mattini/lock.py:78; pipeline/mattini/download.py:247; pipeline/mattini/__main__.py:78-85 (ValueError not caught); pipeline/mattini/sheets.py:118-122
- **Claim:** A datasets config without `swissbuildings3d`, or an area box that is not wholly inside the sheet grid, gives an uncaught KeyError or ValueError instead of a `mattini: error:` line naming the file and the fix. The buildings step handles the same case cleanly.
- **Proof:** config/datasets.json was changed temporarily (mut-nods.diff) to drop swissbuildings3d, then restored. `python -m mattini lock buildings` and `download buildings` both ended in `KeyError: 'swissbuildings3d'` tracebacks; the lock stayed 8984f784.... `buildings` printed 'mattini: error: the datasets config has no 'swissbuildings3d' dataset'. sheets_near((2829000, 2831000, 1165000, 1166000)) raises ValueError, and main() does not catch ValueError.
- **Harm:** The owner sees a traceback instead of a refusal naming the fix (Hard Rule 2). Only unusual inputs reach it. Probably the board's 'two refusals reach the owner as a traceback'.
- **Fix:** Check that the dataset is present in lock.buildings_entry and download_buildings, as build_buildings does (buildings.py:509-510). Turn the sheet grid's ValueError into a DownloadError naming the area and config/world.json.
- **Verification:** P3: not put to the skeptics.

### M2-R1-I-06 · P3 · The sheet grid puts swisstopo's 2xxx sheets 600 km away, without an error

- **Where:** pipeline/mattini/sheets.py:3-15 (docstring), 26-33, 77-82; pipeline/tests/test_sheets_grid.py ('all 144'000 parts of the grid, each named once')
- **Claim:** sheets.py treats every id from 1000 to 9999 as a row of the regular LK25 grid. swisstopo instead uses 2180, 2240 and 2260 for the sheets east of column 19 (E 2'830'000-2'834'375). sheet_box returns a wrong box for them without error, and sheets_near never names them.
- **Proof:** Scratch grid_check.py and grid_check2.py compared all 6,724 per-sheet items of the live collection (editions 2013-2025) with sheet_box. 6,695 are equal within 1 m and 15 have data-extent bboxes inside their sheet. Only 14 disagree, all 2180-13/31/33, 2240-11/13/31 and 2260-11 (2014, 2015, 2022). The STAC 2240-11 lies at E 2'830'006-2'834'368, N 1'166'831-1'170'169, while sheet_box('2240-11') = (2480000, 2484375, 555000, 558000). sheets_near((2829000, 2829950, 1167500, 1168500)) returns ['1239-22'], missing 2240-11 50 m away.
- **Harm:** None for the village, which is 200 km away. A future area on the eastern border would silently leave out those sheets' buildings, and the docstring's claim about ids 1000-9999 is false for 2xxx (Hard Rule 2, comments).
- **Fix:** Refuse sheet ids of 2000 and above (or model swisstopo's eastern column), refuse or flag boxes within the margin of E 2'830'000, and correct the docstrings and the grid test's wording.
- **Verification:** P3: not put to the skeptics.

### M2-R1-I-07 · P3 · Refusing a missing sheet item blocks any area near Zermatt's coverage gaps (a design note for M5)

- **Where:** pipeline/mattini/download.py:145-162 with 385-391 (a 404 becomes 'cannot read the STAC item'); docs/SPEC.md §8 *Sheets*
- **Claim:** The rule 'a sheet within 100 m with no item is refused' holds for the village only. The 2020 per-sheet coverage around Zermatt has gaps, so `lock buildings` would refuse any larger area that comes near one, and the message reads like a network error.
- **Proof:** From the live collection listing (review-R1/I/items.json), 2020 items exist for 12 of the 16 parts of 1348 (1348-22, -32, -34 and -43 are missing), 8 of 16 for 1329 and 10 of 16 for 1347. 1348-32 (E 2'624'375-2'628'750, N 1'089'000-1'092'000) lies 3'000 m south of the village box; an area reaching within 100 m of it gets 'cannot read the STAC item: HTTP Error 404'.
- **Harm:** None today. M5's larger area (SPEC §14, OPEN) will hit it, with no way forward except a design change.
- **Fix:** At M5 planning design decides: record a 404 sheet as 'no buildings' in the lock, or keep refusing with a dedicated message that says the edition has no item for that sheet.
- **Verification:** P3: not put to the skeptics.

### M2-R1-I-08 · P3 · The docs lag the arc: SPEC §5's lock paragraph, the sheets' size, brain.md's M2 status

- **Where:** docs/SPEC.md:99-107; docs/SPEC.md:85; brain.md:45-47
- **Claim:** SPEC §5 still says the lock holds only `swissalti3d` and is 'written only by `python -m mattini lock terrain`'. It now has two entry shapes and `lock buildings`, and each lock command keeps the other entry (lock.py:1-17). SPEC §5 gives the six sheets as 14.1 MB. brain.md says M2-03 to M2-05 bring the buildings in 'once the owner has chosen the access route', but all three are DONE on the PROPOSED route while the owner's answer (SPEC §13 row 22) is still pending.
- **Proof:** Read SPEC.md:99-107 and brain.md:46. The six downloaded zips are 45'668 + 391'181 + 9'117'186 + 2'893'650 + 1'437'969 + 324'725 = 14'210'379 bytes (14.2 MB; ls -l in review-R1/raw/swissbuildings3d/2020).
- **Harm:** The design of record misdescribes the lock that two commands now write, and the handoff misstates what has been built.
- **Fix:** Update SPEC §5's lock paragraph with both shapes and both commands, change 14.1 to 14.2 MB, and correct brain.md's M2 line.
- **Verification:** P3: not put to the skeptics.

## Checked and clean

- Standard gate at 88678e2 (tools/gate.sh > scratchpad/review-R1-inputs.log): exit 0. pytest 662 passed, 4 deselected; ruff, manifest, Godot 4.6.3 import and parse, GUT 20 scripts, 98 tests, 2692 asserts, '---- All tests passed! ----'; gdlint, gdformat.
- Live STAC: `lock buildings`, then `lock terrain`. config/datasets.lock.json was 8984f784... before and after, byte-identical (neither entry drops the other). `pytest -m network`: 4 passed.
- Live `download buildings --out review-R1/raw`: run 1 made 6 fetches, and all six zips' SHA-256s and sizes equal the lock and the brief's table. Run 2 made 0 fetches. provenance.json was 8a3da3f2... after both runs (2'770 bytes). `download terrain` against the copied 2024 tiles: 6 verified, 0 fetches, provenance 28523b17....
- Real builds from the scratch raw data: `terrain` wrote village.f32 b6334c1f... (the expected value) and village.json ea6e6c90... (M2-01's bytes). `buildings` built 1'486 buildings in 6 chunks, each chunk equal to config/buildings.json, and printed 'the 6 chunks have the SHA-256s config/buildings.json expects'. manifest b7c3cfd9..., exit 0.
- Sheet grid: the village's box touches its six sheets at 0 m, so the 100 m margin changes nothing for it. The grid matches every regular per-sheet item of all editions (6,695 equal within 1 m, 15 data-extent bboxes inside their sheet); the only exceptions are the 2xxx sheets (finding 06).
- Pinned copies for M2-01 and M2-03 are byte-identical to their live files (cmp), except tests/shared/terrain_fixture/generated/manifest.json, whose only difference is the '"buildings": null' line M2-04 was designed to add.
- Mutation proofs, each restored with git apply -R and the tree left clean. The 2x2 build test catches every tile flipped north-south (test_terrain_build_tiles: 4 fail, plus the fixtures). Dropping attribution from the terrain source check fails test_a_changed_datasets_config_is_refused[attribution]. Dropping it from the buildings block check fails test_a_source_that_is_not_the_datasets_config_s_is_refused[attribution]. The origin census catches a reversed kilometre pair two lines apart added to sheets.py. The tracked-files test names an unstaged pipeline/mattini/_probe.py. When `lock terrain` drops the buildings entry, test_lock_buildings_adds_its_entry_and_keeps_the_terrain_s fails.
- Attribution (Hard Rule 3): config/datasets.json gives both datasets '© swisstopo' under the OGD terms. Provenance, the manifest's source checks and the credits lines ('swissalti3d 2024, © swisstopo', 'swissbuildings3d 2020, © swisstopo') are pinned by tests and proved by the mutations above.
- fiona on Windows: pipeline/uv.lock lists fiona-1.10.1-cp313-cp313-win_amd64.whl (sha256 15751c90...). `uv pip install --dry-run --python-platform x86_64-pc-windows-msvc --python-version 3.13 --only-binary :all:` of the exported lock resolves all 26 packages. The downloaded Windows wheels of fiona and rasterio match the lock's SHA-256s, and each bundles its own delvewheel-mangled GDAL and PROJ DLLs (fiona.libs/gdal-3105....dll vs rasterio.libs/gdal-a72f....dll), so the DLL names cannot clash.
- No real sample is committed: there is no tests/shared/buildings_sample, and none of the 96 files added in 63816ac..88678e2 is raw geodata. test_repo_hygiene refuses .zip and .gdb. The buildings fixture's source.json is synthetic by its own 'about' text. SPEC §13 row 24 stays PROPOSED.
- The area served: nothing in pipeline/mattini names 'village'. lock, download, terrain, buildings and manifest all take the one area of config/terrain.json.

## Notes

Lens: M2 inputs (M2-01 pipeline residue, M2-03 building inputs, attribution, fiona). Worktree detached at 88678e2 and left clean (git status empty). Every mutation came from a saved diff under scratchpad/review-R1/I/ and was undone with git apply -R. Real downloads and builds went only to scratchpad/review-R1/{raw,out,I}.

The grid and coverage checks used a full listing of the live ch.swisstopo.swissbuildings3d_3_0 collection, cached at review-R1/I/items.json.

Findings 02, 03 and 05 confirm residue already on the board (M2-03's check) by reproduction. 01, 04, 06, 07 and 08 are new.

No P0 or P1: every real run matches design's values, and no defect in this lens changes the world the owner gets.

Not measured:
- fiona and rasterio loaded in one process on Windows. Only the static check was done (mangled DLL names, lock-matching wheels, a Windows wheels-only resolution).
- An owner-side PROJ_LIB or GDAL_DATA environment variable, which both wheels would honour.

The owner's answer on the buildings route (SPEC §13 row 22) and on the real sample (row 24) is still pending; the board says nothing reaches main before it.
