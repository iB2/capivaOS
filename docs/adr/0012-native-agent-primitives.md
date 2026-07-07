# ADR-0012: Native Claude Code Primitives for Roles and Subagent Reports

## Status

Accepted

## Context

The 2026-07-07 harness audit (HARN-009, P3) flagged three places where the
harness hand-rolls what Claude Code now provides natively:

1. **Roles as pasted prose.** Dev/QA/Arch briefings live in
   `.claude/agents/roles/*.md` and are pasted verbatim into `Agent()` prompts by
   the skills. Nothing restricts what a spawned role can DO: a QA reviewer
   prompted to "never implement" still holds Edit/Write/Bash and can rewrite the
   code it is reviewing; a dev subagent told "modify only the task's files" can
   run anything. The constraint is prose — the exact enforcement gap that
   ADR-0008 closed for phase ordering.

2. **Completion reports as prose.** /implement subagents report results as
   markdown; the orchestrator parses tables and headings by eye. Prose parsing
   is where claims drift — "all tests pass" with no counts, a files list that
   omits a file. HARN-006's adversarial QA (ADR-0009) attacks these claims
   downstream, but the claims themselves should be structured at the source.

3. **Compaction heuristics written for 2025-era Claude Code.** Law 6's numbers
   ("2 auto-compactions = degraded", 200K budget) predate current Claude Code
   context management (automatic summarization with cross-window continuation,
   live context visibility, and the PreCompact/SessionStart hooks the harness
   itself gained in PR #5).

Claude Code's native agent definitions (`.claude/agents/*.md` with YAML
frontmatter) support a `tools:` allowlist enforced by the platform — a subagent
without Edit simply cannot edit, regardless of prompt drift.

### Options Considered

**Option A: Keep prose roles, add stronger prompt language**
- Pro: No migration; works on any Claude Code version.
- Con: "You must not implement" remains a request, not a restriction. The
  harness's own first principle (Mechanical Enforcement Over Trust) says no.

**Option B: Native agent definitions with tool allowlists; structured JSON reports (chosen)**
- Roles move to `.claude/agents/{dev,qa,arch}.md` with frontmatter. Tool
  restrictions become platform-enforced: QA is read-only (Read/Grep/Glob), dev
  gets the write set (Edit/Write/Bash + read tools), arch gets read + Write
  (ADRs and deviation records only by prose constraint). Skills spawn by agent
  type and pass only task-specific context. Dev subagents end with a fenced
  JSON completion report validated by `scripts/validate_impl_report.py`.
- Pro: A QA agent that cannot write is a guarantee, not a briefing.
- Pro: Validated reports make implementation claims machine-checkable at the
  source; the orchestrator cross-checks `files_changed` against `git diff`.
- Con: Ties the harness to Claude Code's agent-definition format (accepted:
  SCOPE.md already declares Claude Code the execution agent).
- Con: Report validation needs a script + CI wiring (small, self-tested).

**Option C: Full SDK migration (programmatic agents, output schemas)**
- Pro: Strongest typing (JSON-schema-forced structured output).
- Con: The harness is a template, not an application — adopters copy directories
  into arbitrary repos. Requiring an SDK harness host is a scope change.
- Deferred: the JSON report contract is written so an SDK host could enforce it
  with a schema later.

## Decision

**Option B.**

1. `.claude/agents/roles/*.md` → `.claude/agents/{dev,qa,arch}.md` with
   frontmatter (`name`, `description`, `tools`). Tool allowlists: qa =
   `Read, Grep, Glob` (review is read-only; test runs are the orchestrator's
   job); dev = `Read, Grep, Glob, Edit, Write, Bash`; arch =
   `Read, Grep, Glob, Write`. Skills reference agents by type instead of
   pasting role text.
2. Dev completion reports are a single fenced JSON block (task id, status,
   attempts, files_changed, tests_added, commits, test_results counts,
   tdd_order_confirmed, flags), validated by `scripts/validate_impl_report.py`
   (self-tested in CI). Invalid or missing report → one respawn for the report
   alone; still invalid → counts as a failed attempt (three-strike rule).
3. Compaction heuristics re-benchmarked (see context-management.md
   "2026-07 re-benchmark"): the 200K planning ceiling is CONFIRMED; the
   "2 auto-compactions = mandatory handover" rule is RETAINED as the
   conservative default but demoted from primary signal to fallback — current
   Claude Code summarizes-and-continues across window boundaries and exposes
   live context usage, so direct signals (live usage, observed quality
   degradation) take precedence over compaction counting.

## Consequences

- Tool misuse by roles becomes mechanically impossible instead of prose-forbidden
  — the third enforcement surface after phase guards (ADR-0008) and AC gating
  (ADR-0009).
- The /implement orchestrator gets structured claims to verify and feed into the
  quality pipeline; report/diff mismatches surface at collection time, not at QA.
- Adopters on older Claude Code versions that ignore agent frontmatter degrade
  gracefully: the same files still work as pasted briefings (the body is
  unchanged prose).
- `harness_lint.py` scan glob updated (`.claude/agents/*.md`); CI gains the
  report-validator self-test.
- Revisit when: Claude Code agent definitions gain native structured-output
  schemas — then `validate_impl_report.py` collapses into frontmatter.
