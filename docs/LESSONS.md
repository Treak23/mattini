# LESSONS.md — encode these; they repeat

Seeded from start.md Part 5 (I1–I32, renumbered 1–32 in the same order); appended at every
arc close with the date and the incident. Numbers are never reused or renumbered.
Builders read `[build]` + `[all]`; the supervisor `[supervise]` + `[all]`; design all.

1. `[all]` **Output that LOOKS done is the worst failure class.** Plausible placeholders, a
   comment claiming a protection nobody wired, a gate that cannot fail, a status line with
   no commit behind it, an invented colour set committed during the fix of the previous
   invented colour set. Everything in the failure ledger compiled and most of it passed
   tests. Hunt it in every review; record every instance.

2. `[all]` **The unimplemented premise.** A design note says "X protects Y" and nothing does
   ("OS permissions protect the file": 0644). Grep for the mechanism, never the comment.

3. `[all]` **The gap between tested halves.** Both ends tested, the seam never — the
   transcript that never rendered once, camouflaged as a healthy empty state. Test the seam
   a feature crosses, and seed real data before believing a screen.

4. `[all]` **Vacuous gates.** A gate that cannot fail is decoration: prove it by mutation
   (break the code, watch the named test fail, restore, record both runs). Its limit:
   mutation proves a gate is sensitive to ITS OWN subject, never that the subject is the
   harm — so every mutation row states the owner-visible harm it reproduces.

5. `[all]` **A census proves TEXT; it can never prove BEHAVIOUR.** The startup crash shipped
   under a regex asserting a call was written in the right block — written, and never
   executed by anything. Before writing a source census, say aloud what claim it proves; a
   census is never the sole gate for code that runs at construction, initialisation or a
   lifecycle callback. Prefer the fix that makes the defect inexpressible (declaration
   order, a type that cannot carry the bad value, a guard at the write) over a test that
   watches for it. Every gate carries its "does NOT prove" line — for that crash it would
   have read "that the object can be constructed".

6. `[build]` **Blocked ≠ improvise; untestable ≠ downgrade.** Genuine ambiguity is a written
   question, never an invented answer. And when the only available gate is weaker than the
   change's failure class, that is the same question — five arcs quietly took the downgrade
   with a note; the fifth was the crash.

7. `[build]` **Chain the commit to the gate's own exit status.** `gate > log && git commit`.
   A pipe eats the status (`| grep`), and `;` discards it just as thoroughly; both shipped.
   The property is the rule: if the commit can run when the gate did not pass, it is wrong
   however it is spelled.

8. `[supervise]` **The seams BETWEEN briefs are where a green suite lies.** Each brief's
   gates green; the worst defects lived in their interactions (one brief's new layer outran
   another's resting rules). Rounds probe brief PAIRS — who moved under whom.

9. `[all]` **Fix the PATTERN, not the instance.** The same defect surfaced one layer out in
   four consecutive rounds because every fix named one site. When a review finds a defect,
   ask what CLASS it is and enumerate the class before writing the brief.

10. `[all]` **"Does NOT prove" is a deliverable, not a caveat.** Written honestly it is an
    instruction to enumerate the rest, and the enumeration found the next defect four rounds
    running. Its sibling: a disposition on a multi-mechanism finding ticks the mechanisms
    off one at a time — closing one of two and marking the finding answered is how a P1
    survives a round.

11. `[all]` **A rule without its subject gets enforced against the wrong actor.** A hold
    meant to stop agent-side deletion was applied to refuse the owner's own button; "endless
    checks" spent the budget the owner's own items needed and deferred them silently. Every
    rule states who it binds and what harm it prevents; a reading that ends in refusing the
    owner is presumptively a misreading; deferrals are said aloud.

12. `[supervise]` **Rulings need evidence.** A ruling on an unmeasured premise cost an
    executor session to disprove (the timing was pixel readback, not drawing). Locate the
    mechanism at file:line before ruling; and "is the owner exposed on the build they hold?"
    is answered only by a measurement at that build's commit — the inspection answer was
    "probably no", the measured answer was yes.

13. `[all]` **Interaction failures are process failures.** Stopping early ("keep going" said
    a dozen times), interactive pickers after plain text was ordered, jargon at a
    non-programmer ("I have no idea what you are doing"). A turn ends on a shipped result or
    a real blocker; questions are plain text; reports say what changed for the owner, not
    for the build.

14. `[supervise]` **A rule that depends on remembering is not a guard.** The watchdog's
    30-minute chain lapsed five times in one night, the fifth within hours of the reminder
    that was meant to fix it. What holds is structural: one hourly cron Routine armed at the
    arc's start and deleted at its end, nothing that has to be remembered per turn. (The
    chain itself was later retired for costing more than it caught — lesson 26.)

15. `[design]` **The design realm writes no production code.** The one exception ever taken
    — a one-line fix, last in the arc, reviewed by nobody, with no commit-hash status —
    shipped the startup crash. Including one-liners; the arc waits if the budget is spent.

16. `[all]` **A reopened chat is a time capsule.** Its checkout is from the day it was
    created. A week-old chat woke, found no process docs, and rebuilt the process from
    memory on its scratch branch. Sync `main` before judging; a doc you cannot see is never
    a doc you rewrite.

17. `[all]` **Check ancestry before deleting a branch.** The project's first four days of
    history existed only on a branch the owner was about to delete: the files were all in
    `main`, the commits — the record of WHY — were not. "The content is in main" is not "the
    history is".

18. `[all]` **A docs-only commit is not exempt from the gate.** Some tests pin the docs; a
    reworded heading broke `main` for ninety minutes. Grep the test tree for the file's name
    before pushing prose; when writing such a test, pin the substance, never the status
    prefix meant to change.

19. `[all]` **An aggregate a script only counted can be stale or half-built.** A run that
    stops at the first failing module leaves the other module's stale results looking green
    to a counter; a suite run beside a concurrent build reads a half-written jar as
    ninety-eight failures that are nobody's. One mutation per run, full isolation, and read
    the failure TEXT before believing a count in either direction.

20. `[supervise]` **Reviewers that run builds work in isolation.** Three lenses on a shared
    tree plus a poisoned build cache produced phantom compile errors; five concurrent builds
    plus a gate ran the container out of memory. Own worktree, cache off, at most two builds
    at once, the release gate solo.

21. `[all]` **Truth has one home.** The inbox once lived on per-session branches and ids
    were allocated twice, twice; the report-back once lived only in a chat the process told
    the owner to throw away, and bugs were re-reported. One inbox on `main`; the release
    record is a file and the chat message is its copy.

22. `[supervise]` **A dead app and a nice-to-have must not look identical.** "critical:
    crashes on startup" sat for hours at equal weight with an export nicety, and the only
    clock in the process had disabled itself at the close. The `Impact:` field, the `!`
    commit prefix, the inbox read at step 0 of every tick. (A 24-hour post-release watch was
    added then and retired by the owner within two weeks: breakage after a publish reaches
    the design chat as their own message, and no Routine outlives its arc.)

23. `[build]` **Walk the WRITERS, not the inputs.** Guarding "every door" by walking the
    ways in missed three pre-existing bare writes of the same state; inputs are many and
    found only by use, writers are few and found by grep. The writer inventory IS the door
    list, and `private set` is how it stays complete. A seal has two ends — where it is set
    and where it is cleared — and each end must be driven, not read.

24. `[build]` **A guard that compares a captured value guards the past.** A check protecting
    a LIVE property must read live state at decision time; a snapshot taken before a
    suspension is the world as it was. The test for such a guard must change the value
    between capture and check, or it proves nothing.

25. `[all]` **Measured beats plausible.** The blur "obviously too expensive" cost 0.35 ms;
    the grain "obviously fine" tanked the frame. Numbers or it did not happen.

26. `[supervise]` **Supervision must cost less than the work.** One day, two projects: each
    design session spent five to six times its builders, most of a weekly budget, almost all
    of it answering a single dot — two twenty-hour Fable sessions, each holding a very large
    context, each woken by an hourly cron AND a 30-minute chain, roughly fifty wakes apiece
    re-reading the whole conversation. The work itself (nineteen briefs, three review
    rounds) was cheap beside it. One tick per hour; a design session per phase; the arc run
    by an Opus supervisor, never the Fable chat; the ratio measured at every close.

27. `[supervise]` **A rate-limited session is not dead, and a landing is a sha on GitHub.**
    Two watchdog errors in one day: a builder stopped on its usage limit was read as dead
    and a duplicate spawned — the original resumed on its own after the reset; and a listing
    of three commits that no fetch, reflog or API ever carried was acted on as a landing.
    Wait past the reset and re-check; verify a landing by `ls-remote` and the API before
    touching anything.

28. `[all]` **The reading list per role.** Born 2026-09-17 on the source project, from a
    measurement: a builder read about 90 KB before its first line of work, the supervisor
    about 135 KB plus a 195 KB board section, a design session 300–600 KB — most of it
    answered questions, shipped narrative and a failure ledger nobody needed that minute. A
    session that starts at 75k–150k tokens of history is slow to orient, blind to the
    precedent it actually needs, and pays for every page again at every wake. So: each role
    reads at startup only what its role doc names; the board holds open items only and the
    blocked file holds Open only; everything answered or shipped moves to the histories,
    where a one-line index finds it when a decision needs it, and never at startup. The same
    three reads afterwards: roughly 35, 30 and 140 KB — and nothing was lost, because the
    move was verbatim and byte-accounted.

29. `[supervise]` **The supervisor decides what the record already decides.** Born the same
    day, from the other half of the same bill: of the thirty-odd questions filed in ten
    days, about half had their answer already in a brief, the spec, a hard rule or an
    earlier ruling — and each one stopped a builder and cost the owner an expensive design
    session to repeat what the repo said. A watchdog with no voice at all costs as much as
    no watchdog. So the supervisor decides from the record (quoting the deciding line and
    logging the ruling in the index), decides between two reversible options inside a
    brief's scope (recording the choice AND the alternative for the close to audit), and
    asks only for what is genuinely design — one push carrying the options, answerable with
    a word in its standing session (the waker's, since lesson 32), which is the ruling. What
    it still may never do: write production code, change a brief's shape, touch the owner's
    data or schema, or rule from an unmeasured premise (lesson 12).

30. `[supervise]` **Silence is not a status.** Four times in one arc a supervisor reported
    the absence of a signal as a state: a builder dead on a permission prompt shown as
    *running*; a dead-builder diagnosis written from one status field, when the spawn had
    attached no repository at all (the owner saw it at a glance: the session sat under the
    wrong project); five finished review lenses reported *still running* for ninety-one
    minutes because their completion notices never arrived; five hourly ticks answered with
    a dot while three OPEN briefs had no builder. Each time the means to check was at hand.
    Measure, then say. An agent's own summary is not a status either: five builders once
    reported a state their commits contradicted.

31. `[design]` **A constraint is not written until something can satisfy it.** Five
    self-corrections of one shape in one arc: a gate box no correct build could tick, a file
    scope that could not hold the change it asked for, a test location where the object
    under test cannot be constructed, two shapes in one brief that broke each other, a
    diagnosis that assumed a repository nobody had attached. Before writing a gate box, a
    Scope line or a shape, ask what would satisfy it and check that the tree can hold it.
    Four of the five were caught by executors who measured, filed and built the right thing
    (lesson 6 working).

32. `[supervise]` **A session's cost is its context times its calls.** One supervisor
    session ran a forty-two-hour arc: its context grew to 700K tokens (a board it re-read
    every tick and largely wrote itself, a review file pasted verbatim), every model call
    re-read all of it, and it cost more than the twenty-three builder sessions it ran
    together. A short leg of the same job had cost a fortieth of that: the mechanism is
    length, not the role. The structural fix: nothing that supervises lives for the arc
    except a waker that reads only status lines; the work runs in a fresh tick session per
    due wake, and the board carries the arc between sessions.

33. `[all]` **Two runs compared in one minute on one machine cannot see what changes by
    day or by machine.** Every Hard Rule 5 test of arc M0 wrote twice in one run and
    compared the bytes; a date, a host name or a Python version added to the manifest or
    to `provenance.json` passed the full gate (M0 review C-01, 2026-09-24). Pin the exact
    bytes for a fixed input and the exact key set; comparing two runs is only the floor.

34. `[all]` **Test data must be able to tell the right code from its likeliest wrong
    twin.** The owner's axis mapping swaps two axes, so it is its own inverse, and a game
    `to_lv95` that applied the mapping instead of its inverse passed every game test; the
    "32-bit" random round trips drew 32-bit numbers, which a `Vector3` holds exactly, so
    the narrowing they described never happened (M0 review C-03, C-06, 2026-09-24).
    Before trusting a test, name the mistake it must catch and check that its data can
    show it: an asymmetric case, inputs from the wider type.

35. `[all]` **A signal printed once belongs to whoever runs first.** Godot prints an import
    error only on the run that imports the file. In every cloud container that run is the
    session-start hook's warm-up, which discards its output, so the gate's scan of later
    imports sees nothing, and the `valid=false` check a builder added as a re-run nicety
    is the import step's only detector (M0-03 Findings 6, M0 review G-05, 2026-09-24).
    Gate on state that persists, and measure a gate in the environment where it runs.

36. `[all]` **A gate owns its tools' configuration.** GUT loads `res://.gutconfig.json` by
    default, so one committed file could switch its error tracking off with the gate green;
    gdtoolkit reads its config from the working directory upward, so CLAUDE.md's
    `gdlint game` linted the vendored GUT (M0 review G-04, M0-03 Findings 8, 2026-09-24).
    The gate passes each tool's configuration on its command line, and a documented
    command is run as written before anyone relies on it.

37. `[all]` **A scan scoped by an inclusion list misses the files the next arc will
    write.** The Hard Rule 4 census read seven suffixes in three folders; a second origin
    in `project.godot`, in a `.gdshader` or in a script outside `pipeline/mattini/`, or
    written `2.623e6`, passed the gate (M0 review C-02, 2026-09-24). Scope a census by
    exclusion (every tracked file minus named folders) and list the spellings, not one.
