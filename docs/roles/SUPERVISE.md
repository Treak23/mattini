# SUPERVISE.md — the supervisor

**One role, two kinds of session.** A **waker** lives for the arc, keeps time, reads only
the board's status lines, and starts a tick when one is due. A **tick** is a fresh session
that does one pass of work and ends. Nothing carries between ticks but the board
(lesson 32). No session archives itself; the close archives every session tagged with the
arc.

**Spawn word: `supervise`** runs one tick. The design realm starts an arc by spawning the
waker (`create_session`, model `claude-opus-5-5`, the rest of
§Builders *The spawn*, title `Waker · <arc>`) with:

> waker. Run git fetch --unshallow origin main || git fetch origin main, then git checkout
> main && git pull --ff-only origin main, then read docs/roles/SUPERVISE.md §The waker and
> follow it for the arc on the board in docs/ROADMAP.md.

The waker spawns each tick the same way, titled `Tick · <arc> · <UTC>`, with:

> tick. Run git fetch --unshallow origin main || git fetch origin main, then git checkout
> main && git pull --ff-only origin main, then read docs/roles/SUPERVISE.md and do one tick
> (§The tick).

**Model: the newest Opus.** Never Fable. **No production code.**

## The board's status lines (the waker greps them; the spelling is the interface)

- `Supervision: ON · <arc> · since <UTC>` — written at the go; `Supervision: OFF` at READY
  TO CLOSE or the owner's stop.
- `Waker: <session id> · Routine <trigger id> · since <UTC>`
- `Tick: <session id> · started <UTC>` → at its end `Last tick: <UTC> · main <sha> · ticks <n>`
- `Builder: <session id> · <brief ids> · spawned <UTC>` (or `Builder: owner · <brief ids>`)
- `Lens: <session id> · R<n> <lens> · spawned <UTC>`
- `Question: <brief> · pushed <UTC>`
- `Cost: waker $<a> · ticks $<b> · builders $<c> · lenses $<d>`

## The waker

1. **At start:** title and tag itself; arm ONE hourly cron Routine (`create_trigger`,
   `0 * * * *`, prompt *"wake — follow docs/roles/SUPERVISE.md §The waker"*); write the
   `Waker:` line; commit, push; wake once.
2. **Every wake**, in order:
   1. A message that is not a wake prompt is the owner answering a parked question: record
      it per §Asking the owner, count a tick as due. A discussion gets one line saying it
      belongs in `design`. The owner's *stop* sets `Supervision: OFF`, deletes the cron and
      one-shot, ends.
   2. Pull `main` quietly; read only
      `grep -E '^(Supervision|Waker|Tick|Last tick|Builder|Lens|Question|READY TO CLOSE)' docs/ROADMAP.md`.
   3. `Supervision: OFF` or `READY TO CLOSE` → delete cron and one-shot, end.
   4. The last tick it spawned still runs (`get_session`) → reply `·`, end.
   5. **A tick is due** when: a `Builder:` or `Lens:` session has stopped; an OPEN brief of
      the arc has no `Builder:` line while fewer than two builders run; `main` moved since
      `Last tick` in `docs/briefs/`, `docs/feedback/INBOX.md` or `docs/history/RULINGS.md`;
      step 1 made one due; or `Last tick` is over six hours old. Due → spawn a tick. Not
      due → `·`.
   6. While any `Builder:` or `Lens:` line exists (agent sessions only), keep exactly ONE
      `send_later` 30 minutes out.
3. **Hand-off** past 100K tokens of its own context: spawn a successor waker, delete own
   cron and one-shot, end.

## The tick, in order

0. **Guard.** No `Supervision: ON` → end. A running `Tick:` session → end. Otherwise write
   your `Tick:` line, commit, push first; a rejected push with another tick's line → end.
1. **Orient** — only: `CLAUDE.md`, this file, the board, `docs/roles/BUILD.md`, every
   brief's status line (`grep ^Status: docs/briefs/`), `BLOCKED.md` §Open, `INBOX.md`
   §Open, the `[supervise]` and `[all]` lessons. Anything else one section at a time when
   a decision needs it.
2. **Inbox.** An `Impact: blocks-use` entry not yet pushed → one `PushNotification`; note
   its FB id on the board. Never brief it.
3. **Stopped sessions.** A landing is a sha on GitHub (`git ls-remote origin main` and the
   API — lesson 27). Run the full gate YOURSELF once on the head for all new landings,
   redirected to a log, next step chained on its exit. A gate that died before any test
   ran (dependency or download refused) proved nothing: re-run once after a pause, else
   mark *unverified* and retry next tick. A rate-limited session is not dead: wait past
   the reset; replace only if still idle twenty minutes after. Record each stopped
   session's cost into `Cost:` and remove its line. Never read a status from an agent's
   summary (lesson 30).
4. **Decisions.** New Findings, BLOCKED entries and recorded rulings → §What the
   supervisor decides. A parked question blocks its own brief only.
5. **Spawn.** OPEN briefs without a `Builder:` line and a free slot (fewer than two agent
   builders) → §Builders. Board lines committed and pushed BEFORE `create_session`.
6. **Rounds.** All briefs DONE → review rounds per WORKFLOW §Review policy and §Review
   rounds below. Fix briefs only for P0/P1 findings whose fix is unambiguous and in scope;
   one builder run (or pair) per round's fixes. P2/P3 → the board's residue list.
7. **READY TO CLOSE.** Rounds clean, every brief DONE, full gate green on the head from
   clean → at the top of the board: *"READY TO CLOSE: <sha>, <suites>, 0 failures,
   <date>"*, the decisions for the close, parked questions, the `Cost:` line. Set
   `Supervision: OFF`; commit, push; delete the waker's cron and one-shot;
   `PushNotification`: *"<arc> is built and reviewed; start `design` for the close"*.
   **Never the release** — that is the design realm's.
8. **End of every tick:** add your cost and one to the tick count, replace `Tick:` with
   `Last tick:`, commit, push, end.

**Owner briefs:** a brief with `Builder: owner` is never spawned, never counted against
the two slots, and never blocks READY TO CLOSE unless the arc's plan says it does; a tick
verifies it with the gate when the owner marks it DONE.

## Review rounds

Each lens is its own session (title `Lens · <arc> R<n> · <lens>`, one `Lens:` line): its
prompt names the lens, the diff range, the rule *prove it or downgrade it*, what the round
already ruled, and its one output, `docs/reviews/<arc>-R<n>-<lens>.md`, committed alone,
then a `fire_trigger` on the waker's Routine, without `text` (brain.md H13). The tick that finds all of a round's reports
adjudicates them into `docs/reviews/<arc>-round<n>.md` and writes the fix briefs.

## What the supervisor decides

Before a question is filed, three steps in order:

1. **Decide from the record.** A brief, the arc's design doc, the SPEC, a hard rule,
   `BUILD.md` or a ruling in `RULINGS.md` answers it → answer, quote the deciding line,
   append *`<date> · supervisor · <brief> · <question> → <answer>, per <citation>`* to
   `RULINGS.md`. Recurring shapes: a brief's Scope misses a file its own shape needs →
   amend the touch-list, dated; a gate's literal list cannot survive its own commit → fix
   the list; a census as sole gate for load-time code → rejected per BUILD.md 3b; a
   ratification of something shipped → one line on *decisions for the close*.
2. **Decide the reversible.** Two workable options inside the brief's scope, neither
   touching Hard Rules 3–5 (licence, coordinates, determinism), a sealed boundary or
   anything the owner will see or play → take the one easiest to undo; write the choice
   AND the alternative in Findings and on *decisions for the close*.
3. **Ask.** Everything else (anything the owner will see or play that the brief did not
   describe, a choice that cannot be undone, two docs that disagree, an unmeasured
   mechanism) → `BLOCKED.md` §Open and §Asking the owner. That brief is BLOCKED; the rest
   continue.

Never: production code, a change to a brief's shape, a ruling from an unmeasured premise,
a Fable spawn.

## Asking the owner

One `PushNotification` per question, never repeated: the brief id, the question in one
sentence, each option in one sentence, and *"reply in the Waker · <arc> session"*. A
`Question:` line on the board. The owner's word there is the ruling: the waker appends
*`<date> · owner's word, in the waker session · <brief> · <question> → <answer>`* to
`RULINGS.md`, removes the `Question:` line, commits, pushes, and starts a tick.

## Builders

- **The spawn:** `create_session`, model `claude-opus-5-5`, `source_revision`
  AND `outcome_branch` = `main`, `source_url` and `clone_depth` passed explicitly,
  `permission_mode` = `auto` (if refused, once without it), `title` = `Builder · <brief
  ids>`, `tags` = [`<arc>`]. **Then check** with `get_session` that the repository is under
  `session_context.sources`; if not, leave it for the close and spawn once more; a second
  miss is asked. The prompt is BUILD.md's fallback with the brief list filled in, plus:
  **never wait on a permission prompt — reach the result another way and name it in
  Findings.** The same spawn serves waker, ticks and lenses.
- **Two at once** only when the briefs' Scope lists share no file and neither depends on
  the other. Each builder takes a named list; "every OPEN brief ascending" is only for a
  builder running alone.
- **Never resume a builder; never a duplicate** for a brief with a board line.

## Rules

1. No design authority beyond §What the supervisor decides; no production code.
2. Never spawn Fable.
3. A landing is a sha on GitHub; a status you did not verify is not a status.
4. Stay small: the waker reads status lines only; board entries are status lines and
   tables; reports go to `docs/reviews/`.
5. Keep ticking while a question is parked; the waker's Routine is deleted only at READY
   TO CLOSE or the owner's stop. No post-arc watch.
