# ADR-0011: Slim the Always-Loaded Instruction Layer

## Status

Accepted

## Context

Claude Code loads `.claude/CLAUDE.md` and the `.claude/rules/*.md` files into
EVERY session before any work happens. At the time of the 2026-07-07 audit
(finding F6.4) this always-loaded layer measured ~2,485 lines / ~106K characters
— roughly **26K tokens** of instructions consumed before the first tool call.
For a harness whose Law 6 treats the context budget as the primary limiting
resource, spending ~13% of a 200K window on its own rulebook is self-defeating:
it accelerates the compaction it tries to defend against.

Two files dominate: `artifact-standards.md` (~8.4K tokens — mostly WORKED
EXAMPLES: a full exemplar spec, plan, implementation report, quality report, and
PR description) and `CLAUDE.md` (~7.1K tokens — the seven laws plus material
duplicated from the rules files and skills: per-phase details, the sprint loop
pseudocode, anti-pattern tables, troubleshooting, adaptation guides).

Current platform guidance is to keep always-loaded instructions near ~200 lines
and move procedures into on-demand skills. The harness has exactly the right
structure for this — each worked example is only needed by ONE skill, in ONE
phase — but the content predates that structure.

What made trimming safe NOW: PR #5 (HARN-004) moved Laws 1–2 from prompt-level
rules to the `phase_guard.py` PreToolUse hook. Prompt text that merely restates
what a hook mechanically denies is redundancy, not enforcement.

### Options Considered

**Option A: Leave the layer as-is**
- Pro: Zero migration risk; examples visible to every phase.
- Con: ~26K tokens per session paid even for a one-question session; the audit's
  irony finding stands.

**Option B: Move worked examples into the consuming skills; CLAUDE.md keeps laws + pointers (chosen)**
- Each gold-standard template/example moves into the skill that produces that
  artifact (`/grill-spec`, `/plan`, `/implement`, `/test-verify`, `/finish`),
  loaded only when the phase runs. `artifact-standards.md` keeps the anti-slop
  rules, the normative schemas (acs.json), and the validation checklists.
  CLAUDE.md keeps the laws, the blueprint config, and pointer tables; duplicated
  operational detail (anti-patterns, troubleshooting, adaptation) moves to
  on-demand docs.
- Pro: Examples appear exactly where they anchor output — a dev subagent
  writing a plan sees the plan exemplar; a session answering a question pays ~0.
- Pro: No enforcement loss — everything removed is either hook-enforced
  (phase guard) or loaded by the owning skill at execution time.
- Con: An agent freelancing OUTSIDE the skills no longer sees the examples —
  accepted, because the phase guard denies freelance source writes anyway.

**Option C: Compress the examples in place (shorter examples, same location)**
- Pro: Single-file diff.
- Con: Law 7's own rationale (DESIGN.md) says models anchor on rich examples —
  minimal examples produce minimal output. Shrinking the exemplars lowers the
  quality floor to save tokens; moving them preserves both.

## Decision

**Option B.** Movement over compression: the examples stay gold-standard but load
on demand. Measured effect (chars/4 token estimate):

| File | Before | After | Δ |
|------|--------|-------|---|
| `.claude/CLAUDE.md` | ~7.1K tokens (518 lines) | ~2.8K tokens (170 lines) | −61% |
| `.claude/rules/artifact-standards.md` | ~8.4K tokens (824 lines) | ~3.2K tokens (252 lines) | −62% |
| Always-loaded layer total (CLAUDE.md + 8 rules files) | ~26.4K tokens (2,485 lines) | ~16.9K tokens (1,565 lines) | **−36%** |

(Exact numbers recorded in the HARN-008 PR. The examples themselves moved
verbatim — the token cost shifted from every-session to the-phase-that-needs-it.)

## Consequences

- Every session starts ~11K tokens lighter; short sessions (questions, triage)
  pay near-zero artifact-standards cost.
- Gold-standard templates now live in the skill that produces the artifact,
  under a "Gold Standard" section; `artifact-standards.md` §Artifact-N stubs
  point at them. Law 7 still names artifact-standards.md as the normative index.
- Anti-pattern and troubleshooting tables move to `docs/troubleshooting.md`
  (on-demand); the context anti-patterns remain in `context-management.md`
  where they are load-bearing for Law 6.
- Risk accepted: rules files still total ~13K tokens; further slimming (moving
  procedure detail out of state-management/workflow-pipeline into the skills)
  is possible but deferred — those files are the state-machine's normative spec
  and are cross-referenced by the hook and lint tooling.
- Revisit when: Claude Code changes what it auto-loads, or the layer creeps
  back above ~20K tokens (re-measure with `chars/4` per file).
