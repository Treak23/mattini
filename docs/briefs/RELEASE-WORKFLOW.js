// RELEASE-WORKFLOW.js — the standing per-batch helper-agent script (WORKFLOW §Review policy,
// DESIGN.md §The release step 3). The release session runs it once per brief with the
// Workflow tool:
//
//   Workflow({ scriptPath: 'docs/briefs/RELEASE-WORKFLOW.js',
//              args: { brief: 'v0.4.0-03', tier: 2, helperModel: 'sonnet' } })
//
// args.brief       the brief id (its file is docs/briefs/<brief>-*.md; an id is never another
//                  id plus '-', so the pattern matches one file)
// args.tier        1 or 2, from the brief's Lane line; anything else stops the run
// args.helperModel the helpers' model from the go, named on the builder and the fixer only;
//                  reviewers, the prover and the verifier inherit the session's model
//
// One builder in its own worktree; then the review the tier calls for; a fixer only when
// warranted; tier 1 adds a verifier of the fix diff. No recorder: the session writes the
// board line from what this returns, after checking the landing on origin/main itself
// (DESIGN.md standing rule 5). The status it returns: DONE; BLOCKED (the builder's question,
// for the session to file); NOTHING_LANDED (the builder's commits are not on origin/main);
// TRUNCATED (a review, fix or verify agent returned nothing: the round did not happen);
// ROUND_OPEN (findings that warrant a fix still stand after the fixer: the session runs the
// next round). Plain JavaScript; no Date.now(), no filesystem.
//
// Check an edit before running it: node cannot parse the top-level return, so wrap the body
// (sed -e 's/^export const meta/const meta/' -e '1i (async () => {' -e '$a })()' file > x.mjs;
// node --check x.mjs).

export const meta = {
  name: 'mattini-batch',
  description: 'Build one brief with a builder agent, review it by tier, fix only when warranted',
  phases: [
    { title: 'Build', detail: 'one builder, own worktree, pinning tests red first' },
    { title: 'Review', detail: 'tier 2: one reviewer; tier 1: three lenses and a mutation prover' },
    { title: 'Fix', detail: 'a fixer only for a standing P0/P1 (tier 1: P0-P2), then a verifier' },
  ],
}

const brief = args && args.brief
const tier = Number(args && args.tier)
const helperModel = args && args.helperModel
if (!brief) throw new Error('args.brief is required (the brief id)')
if (tier !== 1 && tier !== 2) throw new Error('args.tier must be 1 or 2 (the brief\'s Lane line); a missing tier is never read as 2')
if (!helperModel) throw new Error('args.helperModel is required (the helpers\' model from the go)')

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    brief: { type: 'string' },
    status: { type: 'string', enum: ['DONE', 'BLOCKED'] },
    baseSha: { type: 'string', description: 'origin/main before the first commit of this brief' },
    sha: { type: 'string', description: 'the Status sha, read from git log origin/main after git fetch origin main' },
    landed: { type: 'boolean', description: 'git merge-base --is-ancestor HEAD origin/main exited 0 after the last push and fetch' },
    gateTable: { type: 'string', description: 'the Findings gate table, verbatim' },
    question: { type: 'string', description: 'the BLOCKED question with what you measured, if any' },
  },
  required: ['brief', 'status', 'baseSha', 'sha', 'landed'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    lens: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
          file: { type: 'string' },
          line: { type: 'integer' },
          claim: { type: 'string' },
          evidence: { type: 'string', description: 'file:line, the command run, its output' },
          harm: { type: 'string', description: 'the owner-visible harm it reproduces' },
        },
        required: ['id', 'severity', 'file', 'claim', 'evidence', 'harm'],
      },
    },
    doesNotProve: { type: 'array', items: { type: 'string' } },
  },
  required: ['lens', 'findings', 'doesNotProve'],
}

const MUTATION_SCHEMA = {
  type: 'object',
  properties: {
    rows: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          mutation: { type: 'string' },
          test: { type: 'string' },
          failedAsExpected: { type: 'boolean' },
          restoredGreen: { type: 'boolean' },
          output: { type: 'string' },
        },
        required: ['mutation', 'test', 'failedAsExpected', 'restoredGreen'],
      },
    },
    vacuousGates: { type: 'array', items: { type: 'string' }, description: 'gates no mutation could fail' },
  },
  required: ['rows', 'vacuousGates'],
}

const FIX_SCHEMA = {
  type: 'object',
  properties: {
    fixed: { type: 'array', items: { type: 'string' }, description: 'finding ids fixed, with the commit' },
    notFixed: { type: 'array', items: { type: 'string' }, description: 'finding ids not fixed and why (does not reproduce, out of Scope, design)' },
    sha: { type: 'string', description: 'origin/main after the push, or the build sha if nothing was pushed' },
  },
  required: ['fixed', 'notFixed', 'sha'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    clean: { type: 'boolean' },
    notes: { type: 'string' },
  },
  required: ['clean', 'notes'],
}

const RULES = `Rules that bind you: CLAUDE.md as it stands in your checkout after the fetch (where it
differs from the copy injected at your start, the file wins), docs/WORKFLOW.md §Gates and
§Permissions, and brain.md §Hazards for the gate's known traps. Never force-push, never git reset
--hard, checkout -- ., restore ., clean -fd or stash drop. Run the gate in the foreground redirected
to a log, or as a tracked background task; never poll it. Leave the tree clean.`

const READ_ONLY = `You run nothing that builds or tests (no tools/gate.sh, pytest, GUT or Godot): another agent
holds the container's one build slot. Read with git show, git diff, git log and grep; a claim that
needs a run is marked unverified${tier === 1 ? ' and named for the mutation prover' : ''}.`

// ---- Build ------------------------------------------------------------------------------
phase('Build')
log(`batch ${brief}: builder on ${helperModel}, tier ${tier}`)

const build = await agent(
  `You are the builder for brief ${brief} (docs/briefs/${brief}-*.md). Read docs/roles/BUILD.md
and follow it exactly: its card, its rules and §A builder's whole life. You work in your own
worktree, on its own branch: first git fetch origin main and git merge --ff-only origin/main, record
origin/main's sha as baseSha, then copy the pinning tests in, see them red by the harm's name, make
the change, commit each step chained to tools/gate.sh with the subject ending "(${brief})", push
after every commit with git push origin HEAD:main (git push origin main pushes nothing from your
branch), run the batch gate once, fill Findings (tables only) and set Status: DONE (<sha>) with the
sha from git log origin/main after git fetch origin main. Before you return, fetch and run
git merge-base --is-ancestor HEAD origin/main: landed is true only if it exits 0. A question you
cannot settle: stop, commit nothing more, return status BLOCKED with the question and what you
measured; the session files it. ${RULES}
Return: brief, status, baseSha, sha, landed, the Findings gate table verbatim, and the question if BLOCKED.`,
  { label: `build:${brief}`, phase: 'Build', schema: BUILD_SCHEMA, model: helperModel, isolation: 'worktree' },
)

if (!build) return { brief, status: 'TRUNCATED', note: 'the builder returned nothing; check origin/main for its commits before re-running' }
if (build.status === 'BLOCKED') {
  log(`batch ${brief}: BLOCKED — ${build.question || '(no question returned)'}`)
  return { brief, status: 'BLOCKED', baseSha: build.baseSha, sha: build.sha, question: build.question || '' }
}
if (!build.landed || !build.sha || build.sha === build.baseSha) {
  log(`batch ${brief}: NOTHING_LANDED — the builder's commits are not on origin/main`)
  return { brief, status: 'NOTHING_LANDED', baseSha: build.baseSha, sha: build.sha, gateTable: build.gateTable || '' }
}
log(`batch ${brief}: landed ${build.sha}`)

// ---- Review -----------------------------------------------------------------------------
phase('Review')
const range = `${build.baseSha}..${build.sha}`
const theDiff = `the brief's own commits in ${range} on origin/main: git log --grep='(${brief})' --format=%H ${range},
then git show each (another lane's or the session's commits in the range are not this batch's)`
const reviewPrompt = (lens, extra, isolated) => `You are a read-only reviewer of brief ${brief}
(docs/briefs/${brief}-*.md). git fetch origin main, then review ${theDiff}, and nothing outside it
except what the diff calls. Lens: ${lens}. ${extra}
Report P0 to P2 only, each with evidence at file:line or a command you ran and its output, the
owner-visible harm it reproduces, and the fix's shape in one line; P3 only if it is in Tier-1
territory (config/world.json, the coordinate transforms, the pipeline's determinism). Prove it or
downgrade it: a finding you could not reproduce is not a finding. Hunt output that looks done
(lesson 1), the unimplemented premise (lesson 2), the gap between tested halves (lesson 3) and
vacuous gates (lesson 4). End with the list of what your review does NOT prove.
${isolated ? `You run alone after the builder: in your own worktree (git fetch origin main; git checkout --detach ${build.sha}), with your own XDG_DATA_HOME, you may run the brief's named tests and single test files; never the full gate.` : READ_ONLY}
${RULES} You change no file in the repository and push nothing.`

const LENS_SEAMS = 'correctness and seams: does the code do what the brief and its comments claim, and where does this batch meet the files it reads or writes (the manifest, the fixtures in tests/shared/, the readers on the other side)?'
const LENS_OWNER = 'what the owner sees: the exported game on the owner\'s PC, the pause screen, the credits, the error panel, the log lines, the software screenshots in Findings, the words in messages and docs.'
const LENS_COORDS = 'coordinates and determinism (Hard Rules 4 and 5): any second home for the origin or the axis mapping, a 32-bit subtraction of LV95 coordinates (brain.md H5), a mirrored or shifted placement, an output that would differ by machine, day or run (lessons 33, 43).'

let reports = []
let mutation = null
let truncated = false
if (tier === 1) {
  const results = await parallel([
    () => agent(reviewPrompt(LENS_SEAMS, '', false), { label: `review:seams:${brief}`, phase: 'Review', schema: FINDINGS_SCHEMA }),
    () => agent(reviewPrompt(LENS_OWNER, '', false), { label: `review:owner:${brief}`, phase: 'Review', schema: FINDINGS_SCHEMA }),
    () => agent(reviewPrompt(LENS_COORDS, 'You are the data-and-boundary reviewer: walk the WRITERS of every value this batch stores or places (lesson 23), not its inputs.', false),
      { label: `review:coords:${brief}`, phase: 'Review', schema: FINDINGS_SCHEMA, effort: 'high' }),
    () => agent(
      `You are the mutation prover for brief ${brief} (docs/briefs/${brief}-*.md), tier 1. In your own
worktree (git fetch origin main; git checkout --detach ${build.sha}), with your own XDG_DATA_HOME, run
every mutation row the brief's Done when and Findings name, both ways: break the code as the row says,
run the named test and record that it fails by the harm's name; undo the mutation with git apply -R of
its own diff and record the green run. Add the mutations the brief forgot that would show its likeliest
wrong twin (lesson 34). A gate no mutation can fail is reported as vacuous (lesson 4). You are the only
agent of this round that runs builds or tests. ${RULES} Push nothing.`,
      { label: `prove:${brief}`, phase: 'Review', schema: MUTATION_SCHEMA, effort: 'high', isolation: 'worktree' },
    ),
  ])
  reports = results.slice(0, 3).filter(Boolean)
  mutation = results[3]
  if (reports.length < 3 || !mutation) truncated = true
} else {
  const one = await agent(reviewPrompt(`${LENS_SEAMS} AND ${LENS_OWNER}`, 'Both lenses, one report.', true),
    { label: `review:${brief}`, phase: 'Review', schema: FINDINGS_SCHEMA, isolation: 'worktree' })
  if (one) reports = [one]
  else truncated = true
}
if (truncated) log(`batch ${brief}: a review agent returned nothing — the round is truncated`)

const findings = reports.flatMap(r => r.findings.map(f => ({ ...f, lens: r.lens })))
const vacuous = mutation ? mutation.vacuousGates : []
const standing = findings.filter(f => tier === 1 ? ['P0', 'P1', 'P2'].includes(f.severity) : ['P0', 'P1'].includes(f.severity))
log(`batch ${brief}: ${findings.length} findings, ${standing.length} warrant a fixer, ${vacuous.length} vacuous gates`)

// ---- Fix --------------------------------------------------------------------------------
let fix = null
let verdict = null
let roundOpen = false
if (standing.length || vacuous.length) {
  phase('Fix')
  const list = standing.map(f => `${f.id} [${f.severity}] ${f.file}${f.line ? ':' + f.line : ''} — ${f.claim}\n  evidence: ${f.evidence}\n  harm: ${f.harm}`).join('\n')
  fix = await agent(
    `You are the fixer for brief ${brief} (docs/briefs/${brief}-*.md), in your own worktree
(git fetch origin main; git merge --ff-only origin/main), with your own XDG_DATA_HOME. Findings that stand:\n${list}\n
Vacuous gates the prover named: ${vacuous.join('; ') || 'none'}.
Verify each finding against the code before changing anything; one you cannot reproduce goes to
notFixed with the reason. Fix inside the brief's Scope only (BUILD.md rule 4); a fix that needs a
file outside it or a design change is notFixed, named for the session. Fix the PATTERN, not the
instance (lesson 9). Each fix with a test that fails without it; every commit chained to
tools/gate.sh with the subject ending "(${brief})", pushed with git push origin HEAD:main; append a
row per fix to the brief's Findings. ${RULES}
Return the ids fixed with their commits, the ids not fixed with reasons, and origin/main's sha after
git fetch origin main (the build sha if you pushed nothing).`,
    { label: `fix:${brief}`, phase: 'Fix', schema: FIX_SCHEMA, model: helperModel, isolation: 'worktree' },
  )
  if (!fix) {
    truncated = true
    log(`batch ${brief}: the fixer returned nothing — the round is truncated`)
  } else {
    if (fix.notFixed.length) roundOpen = true
    if (tier === 1 && fix.fixed.length) {
      verdict = await agent(
        `You are the read-only verifier of brief ${brief}'s fix commits in ${build.sha}..${fix.sha} on
origin/main (git fetch origin main; git log --grep='(${brief})' ${build.sha}..${fix.sha}), tier 1. Does
each fix close the finding it names, by the finding's own evidence? Did it move the origin, the axis
mapping, a placement or any deterministic output? Does the gate still prove what the brief says it
proves? Report clean=true only when every fixed id is closed and nothing else moved; otherwise name
what stands. ${READ_ONLY} ${RULES} Change nothing.`,
        { label: `verify:${brief}`, phase: 'Fix', schema: VERDICT_SCHEMA, effort: 'high' },
      )
      if (!verdict) {
        truncated = true
        log(`batch ${brief}: the verifier returned nothing — the round is truncated`)
      } else if (!verdict.clean) roundOpen = true
    }
  }
}

const status = truncated ? 'TRUNCATED' : (roundOpen ? 'ROUND_OPEN' : 'DONE')
log(`batch ${brief}: ${status}`)
return {
  brief,
  status,
  tier,
  baseSha: build.baseSha,
  sha: fix && fix.sha ? fix.sha : build.sha,
  gateTable: build.gateTable || '',
  findings,
  doesNotProve: reports.flatMap(r => r.doesNotProve.map(d => `${r.lens}: ${d}`)),
  mutation,
  fix,
  verdict,
  truncated,
}
