# BLOCKED — questions from executor sessions

Plain text, newest first. An executor that hits genuine ambiguity writes its question
here, marks its brief `Status: BLOCKED`, and takes the next OPEN brief — it never invents
the answer. Check `docs/history/RULINGS.md` BEFORE filing: a question it already answers
is answered, not filed. Answered blocks move to `docs/history/blocked/` (DESIGN.md rule 3).

## Open

### 2026-09-25 · M2-03 · the pinned `test_sheets.py` fails the gate's `ruff check`

Filed by the executor agent of the one M2 session, on its branch
`worktree-wf_6d184921-dea-1`; the brief's code is committed there at `4035f08`.

What happens: the pinned `docs/briefs/pinning/M2-03/pipeline/tests/test_sheets.py`, copied
byte for byte to `pipeline/tests/test_sheets.py`, fails the standard gate at its
`ruff check` step: `I001 [*] Import block is un-sorted or un-formatted` at
`pipeline/tests/test_sheets.py:21:1` (the pytest step before it passed, 507 tests). ruff
0.16.8's default rules include import sorting. In `pipeline/tests/`, ruff counts `mattini`
as the project's own package (its `src` is `pipeline/`), so `from mattini.sheets import …`
needs a blank line after `import pytest`. Linted where it is pinned, under `docs/`,
`mattini` counts as a third-party package and the file passes, which is probably how it
was committed. The only change ruff proposes (`ruff check --diff`) is that one blank line
after line 21. The brief's other pinned test and M2-04's pinned pipeline tests pass
`ruff check` in their live places (checked in a scratch copy of the layout).

Why it is blocked: the brief needs both the live copy byte-identical to the pinned one
(its first gate; WORKFLOW §Brief lifecycle) and the standard gate green. Within the
brief's scope, the only ways to get both are to edit the pinned test's bytes or to change
the gate's lint configuration, and neither is the executor's decision.

Question: may the pinned copy gain that one blank line, so that the live copy is
byte-identical and the gate is green? Or is there another answer?

State: everything else in the brief is done and committed on a green gate (`4035f08`),
with the live `pipeline/tests/test_sheets.py` left out of the tree. Its 22 tests pass
when run from the pinned folder. Once the pinned copy is fixed, closing the brief takes
five steps: copy the file in, `cmp`, run the gate, commit, then tick the first and last
gates and set DONE. The brief's Findings has the rest.
