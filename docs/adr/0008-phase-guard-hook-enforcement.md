# ADR-0008: Hook-Enforced Phase Guards Parsing sprint-state.md Directly

## Status
Accepted

## Context

The harness's first design principle is "Mechanical Enforcement Over Trust" (DESIGN.md), yet through 2026-07 every phase guard was a prompt instruction: skills were *told* to read sprint-state.md and refuse to run out of sequence. Prompted "never do X" rules are not guardrails — under context pressure the model can skip them, and nothing at the tool layer stops a code edit during GRILL_SPEC or a PR created before quality gates pass. Anthropic's own steering guidance for Claude Code is explicit: critical requirements need hooks and settings, not instructions.

Claude Code's PreToolUse hook can deny a tool call before it executes, with a reason fed back to the model. That makes Laws 1-2 mechanically enforceable: source-file writes outside IMPLEMENT and `gh pr create` outside FINISH can be denied at the harness layer regardless of what the conversation says.

The open design question was where the hook reads pipeline state from.

### Options Considered

**Option A: Dual state file — skills write sprint-state.json alongside sprint-state.md**
- Skills update both files at every transition; hooks parse the JSON.
- Pro: JSON parsing is trivial and unambiguous for any consumer.
- Pro: Extensible schema for future tooling (CI, dashboards).
- Con: Dual-write consistency is prompt-enforced — the exact failure mode this ADR exists to eliminate. A skill that updates the markdown but forgets the JSON leaves the hook enforcing a stale phase, deadlocking the pipeline in the worst case and silently under-enforcing in the best.
- Con: Two sources of truth violate Law 1 ("sprint state is canonical") — which file wins on disagreement is undefined.

**Option B: Hooks parse sprint-state.md directly (chosen)**
- The `- **Field**: Value` format is already normatively specified in state-management.md, and HARN-001 established a reliable regex parser for it (used by context-persistence.py).
- Pro: Single source of truth — the file skills already maintain. No dual-write, no drift, no consistency protocol.
- Pro: Human-readable and machine-readable are the same artifact; what the human reviews is exactly what the hook enforces.
- Con: Markdown parsing is format-coupled — a format change in state-management.md must be mirrored in two hook scripts (documented in both file headers; a parity check belongs in harness CI).

**Option C: Replace sprint-state.md with sprint-state.json entirely**
- Pro: One machine-native source of truth.
- Con: Destroys human readability of the pipeline's most-read file (reviewed at every checkpoint) and breaks every doc, skill, and rule that references the markdown format. Migration cost out of proportion to benefit.

## Decision

**Option B — the PreToolUse phase guard (`phase_guard.py`) parses `.board/sprint-state.md` directly.**

The markdown file skills already maintain is the single canonical state; hooks derive from it rather than requiring a parallel JSON to be kept in sync by prompt discipline. The parser is ~10 lines of anchored regex against a normatively specified format — the robustness JSON would buy does not justify introducing a dual-write consistency problem enforced only by instructions.

Enforcement scope: Edit/Write/NotebookEdit to source paths denied unless Phase = IMPLEMENT (test paths also allowed in TEST_VERIFY); `gh pr create` denied unless Phase = FINISH with Quality Gate PASS/ACCEPTED_SOFT_FAIL. Pipeline artifacts (.board/, docs/, .claude/, templates/, PLAN.md, root *.md) are writable in every phase. The guard fails open with a stderr warning when sprint-state.md is missing or unparseable, and honors two logged escape hatches — `CAPIVA_PHASE_GUARD=off` in Claude Code's launch environment, or a gitignored `.state/phase-guard-off` marker file for mid-session use (per-command env vars cannot reach the hook process, which Claude Code spawns from its own environment — discovered when the guard denied this repo's own maintenance PR). Enforcement must never brick a project. (Amended by ADR-0010: the fast lane adds VERIFY_FINISH to the phases where test writes and gated `gh pr create` are allowed.)

## Consequences

- Laws 1-2 hold even when the conversation would violate them; the model receives the denial reason and can self-correct toward /sprint.
- The `- **Field**:` format in state-management.md is now a load-bearing interface consumed by two hooks (phase_guard.py, context-persistence.py) — format changes require updating both, and harness CI (HARN-005) should assert parser/format parity.
- Prompt-level phase guards in skills remain as the first line of defense and for gates hooks cannot see (human approvals mid-conversation); the hook is the backstop.
- Adopter projects get enforcement with zero per-project configuration; teams that need to bypass it temporarily have a logged, explicit escape hatch instead of silent workarounds.
