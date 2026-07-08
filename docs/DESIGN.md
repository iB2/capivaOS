# Design Philosophy — Spec-Driven Development Harness

## The Problem

Claude Code is powerful but undisciplined. Without structure, it exhibits predictable failure modes:

1. **Scope creep** — asks one question, implements three features, breaks two existing ones.
2. **Spec amnesia** — starts coding before requirements are clear, then retrofits tests to match what was built (not what was needed).
3. **Context rot** — long sessions degrade output quality. The agent forgets earlier decisions, contradicts itself, produces increasingly vague output.
4. **Board drift** — task state lives in conversation memory, not on disk. Session ends, state is lost.
5. **Quality decay** — without enforcement, code review becomes "looks fine", tests become "it compiles", and coverage becomes "we'll add it later."

These aren't edge cases — they're the default behavior when Claude Code operates without guardrails. Every team that uses Claude for production code encounters them.

**Note on stack-agnosticism**: The pipeline structure, state machine, and quality discipline are universal. Stack-specific patterns (coding standards, test frameworks, build commands) are injected via pluggable blueprints — see the Active Blueprint system in CLAUDE.md.

**This harness exists to make disciplined development the path of least resistance.**

The agent can't skip steps because the state machine won't let it. It can't write code without a spec because the phase guard refuses. It can't ship without tests because the quality gate blocks the PR. The pipeline IS the discipline.

## Source Attribution

This harness synthesizes ideas from three distinct approaches, each solving part of the problem:

### 1. Grill-With-Docs (Matt Pocock)

**What we took**: The adversarial spec interview pattern.

Pocock's insight: the biggest source of bugs isn't bad code — it's ambiguous requirements. His "grill" process forces the spec to survive hostile questioning before any code is written. Every assumption is surfaced, every edge case is challenged, every "it depends" gets a concrete answer.

**How we adapted it**: Our `/capiva:grill-spec` skill (Phase 1) implements this as a structured adversarial interview with concurrent domain modeling. The output isn't just a clarified spec — it's a formal document with GIVEN/WHEN/THEN acceptance criteria, a domain glossary (CONTEXT.md), and Architecture Decision Records for hard-to-reverse choices.

### 2. Superpowers (obra)

**What we took**: The Spec-Driven Development (SDD) + TDD pipeline.

obra's framework demonstrates that Claude Code produces dramatically better output when forced into a structured pipeline: understand → specify → implement → verify. The key insight is that spec-first development isn't just about documentation — it's about forcing the agent to think before it acts.

**How we adapted it**: Our 6-phase pipeline extends this with explicit phase guards, a state machine, and artifact gating. Where Superpowers relies on convention ("you should write a spec first"), our harness enforces it mechanically ("the /capiva:plan skill refuses to run unless a spec file exists and sprint-state says Spec Approved = Yes").

### 3. Claudio (Bruno Americo)

**What we took**: Board-driven agent orchestration, state management, and the concept of agent cycles.

Claudio demonstrated that AI agents work best when they operate from a persistent task board rather than ephemeral conversation context. The board is the source of truth — not the chat history. Claudio also pioneered the idea of token-aware execution: agents that monitor their own context consumption and hand over cleanly instead of degrading.

**How we adapted it**: Our `.board/tasks.md` + `.board/sprint-state.md` system is directly inspired by Claudio's board-driven architecture. The board lock protocol, the phase history audit trail, and the handover skill all descend from Claudio's state management patterns.

### What's Novel to This Harness

Several design elements don't exist in any of the source frameworks:

- **Formal handover protocol** — no source framework had a mechanism for multi-session pipeline continuation. All assumed single-session execution. Our `/capiva:handover` skill produces a self-contained document that enables a fresh agent to resume from exactly where the previous agent stopped.
- **Context7 documentation discovery** — fetching current library docs via MCP before writing code. Training data staleness is a known problem; no prior framework addressed it systematically.
- **Artifact-gated progression** — each phase produces files on disk, and the next phase mechanically verifies they exist. This is a stronger guarantee than "the spec should be done before planning" — it's "the plan skill literally cannot execute without the spec file."
- **Gold-standard artifact templates** — comprehensive examples of what GOOD output looks like for every phase, with anti-slop rules. Models are lazy — if you show them a minimal example, they'll produce minimal output. We show rich examples so the floor is high.
- **Compaction-aware execution** — using auto-compaction count as a proxy for context pressure, with a decision matrix that triggers handover before quality degrades.

---

## Core Design Principles

### 1. Mechanical Enforcement Over Trust

**Principle**: If a constraint matters, it must be enforced by the system — not requested by a prompt.

**Why**: Language models are instruction-following machines that optimize for helpfulness. If a rule says "you should write tests" but there's no mechanism to check, the model will skip tests when context is tight or the task feels simple. The only reliable way to enforce behavior is to make non-compliance mechanically impossible.

**How this manifests**:
- Phase guards refuse to execute skills out of sequence (not "please don't skip phases")
- Artifact gates verify files exist on disk (not "please make sure the spec is done")
- Quality gates block PRs below thresholds (not "please aim for 80% coverage")
- Board lock prevents concurrent writes (not "please don't write at the same time")

### 2. Artifacts Over Conversation

**Principle**: Everything important lives on disk as a file — never only in conversation context.

**Why**: Conversation context is ephemeral. It compacts, it gets lost on crash, it degrades over long sessions. Files on disk survive sessions, crashes, and handovers. When the spec is a file at `docs/specs/TASK-ID-spec.md`, any agent in any session can read it. When the spec is "what we discussed earlier," it's gone after compaction.

**How this manifests**:
- Specs are files, not conversation agreements
- Plans are files, not mental models
- Quality reports are files, not terminal output
- Sprint state is a file, not remembered context
- Tech context (library docs) are files, not training data assumptions

### 3. One Task, One Lane, No Shortcuts

**Principle**: Every task goes through a complete state-machine path. The full 6-phase pipeline is the default; a qualifying small task may take the fast lane (combined SPEC_PLAN and VERIFY_FINISH phases) — but never an ad-hoc path outside the state machine.

**Why**: "This is simple enough to skip the spec" is how spec amnesia starts. But identical ceremony for every task size produces the opposite failure — lane evasion, where small fixes get batched OUTSIDE the harness with no spec, no board entry, and no gate at all. The answer is a scaled lane, not a bypass: the fast lane compresses interviews and gate count while keeping the board, sprint-state, TDD, the acs.json contract, and the quality gate intact (see [ADR-0010](adr/0010-fast-lane-pipeline.md)). Lane selection is a mechanical predicate, not a judgment call — anything P0/P1, creating files, or touching schema/architecture takes the full pipeline.

**Exception**: P4 tasks (backlog/spike) can skip specs and quality gates — they're explicitly marked as exploratory.

### 4. Human in the Loop, Machine in the Pipeline

**Principle**: Humans make decisions (what to build, whether the spec is right, whether quality is sufficient). Machines execute the pipeline between decisions.

**Why**: Fully autonomous AI development sounds appealing but produces output nobody trusts. Fully manual development is too slow. The sweet spot is: human judgment at decision points, machine execution between them. The four human checkpoints (spec approval, plan approval, quality review, merge decision) are the minimum set of gates where human judgment is irreplaceable.

### 5. Token Budget as First-Class Constraint

**Principle**: The pipeline is bounded by context consumption, not by time.

**Why**: Time-bounded sprints (30 minutes, 1 hour) are arbitrary and don't correspond to the actual limiting resource: context window tokens. A complex task might exhaust context in 20 minutes during IMPLEMENT; a simple task might complete the full pipeline in 10 minutes. Token-bounding means the pipeline runs until the work is done or context is exhausted — then it hands over cleanly instead of producing degraded output.

**How this manifests**:
- No timebox on sprints
- Compaction counter as signal (0 = healthy, 1 = caution, 2 = mandatory handover)
- Multi-session execution is expected, not a failure mode
- `/capiva:handover` skill produces documents that enable zero-loss resumption

### 6. Traceability from Spec to PR

**Principle**: Every acceptance criterion must be traceable through the entire pipeline: spec → plan → tests → quality report → PR.

**Why**: Without traceability, it's impossible to verify that what was shipped matches what was requested. "All tests pass" is meaningless if you can't map tests back to acceptance criteria. The AC coverage matrix in the quality report is the single most important table in the pipeline — it proves that every requirement has a corresponding test.

**How this is enforced**: The AC list is data, not prose. `/capiva:grill-spec` emits `docs/specs/TASK-ID-acs.json` (one entry per AC: `id`, `text`, `status`); after spec approval only `status` may change. `/capiva:test-verify` generates the quality-report matrix FROM this file and writes verdicts back to it, and `/capiva:finish` refuses to create a PR while any AC is not `pass`. A dropped or paraphrased AC is a mechanical failure, not an oversight (see [ADR-0009](adr/0009-machine-readable-ac-gating.md)).

---

## The Seven Laws — Rationale

The CLAUDE.md file states seven "immutable laws" (summarized by a three-line credo at the top of that file). Here is WHY each exists:

### Law 1: State Machine Governs All

**Problem it solves**: Without a persistent state machine, the agent has no way to know where it is in the pipeline after a crash, compaction, or session restart. It would either start over (wasting work) or guess (producing errors).

**Why state machine specifically**: A state machine has a small, finite set of states with explicit transitions. This is auditable (you can read sprint-state.md and know exactly where you are), recoverable (resume from the current state), and enforceable (each state has a clear set of allowed actions).

### Law 2: No Phase Skipping

**Problem it solves**: The most common failure mode in AI-assisted development is jumping straight to code. Without this law, an agent given "implement feature X" will write code immediately — no spec, no plan, no tests first. Phase skipping is the root cause of spec amnesia, untested code, and rework.

**Why ALL phases, even for "simple" tasks**: Complexity is often invisible at the start. A task that looks like "add a field to a model" might involve database migrations, API contract changes, and downstream consumer updates. The pipeline reveals this complexity during grill-spec and planning — before code is written.

### Law 3: Artifacts Gate Progression

**Problem it solves**: Prevents the "I'll do it properly later" pattern. Without artifact gating, the agent can claim "the spec is done" without actually writing one. The gate doesn't check whether the spec is good — quality validation does that separately. The gate checks whether the spec EXISTS as a file on disk. This is a binary, unfalsifiable check.

**Why files, not conversation claims**: Because files survive sessions. "I discussed the spec with the user" is unverifiable after compaction. `docs/specs/TASK-ID-spec.md` either exists or it doesn't.

### Law 4: Board Lock Protocol

**Problem it solves**: During IMPLEMENT, the orchestrator and multiple subagents may need to update `.board/tasks.md` (ticking subtask checkboxes, updating progress). Without a lock, concurrent writes corrupt the file — one agent's changes overwrite another's.

**Why file-based, not git-based**: Git-based locking (branches, merge conflicts) is too heavyweight for a task board that changes every few minutes. A simple lock file with holder/timestamp/operation is sufficient, stale-detectable (60-second timeout), and human-readable. See ADR-0003 for full analysis.

### Law 5: Human Checkpoints Are Blocking

**Problem it solves**: Prevents the agent from "approving its own work." Without blocking checkpoints, the agent would generate a spec, approve it, plan it, approve the plan, implement it, pass its own quality review, and ship a PR — all without human oversight. This defeats the purpose of spec-driven development.

**Why silence ≠ approval**: In conversation-based AI interaction, the human might step away, context might compact, or the approval message might be ambiguous. The only safe default is: if the human hasn't explicitly said "approved" / "sim" / "go ahead," the pipeline waits.

**How autonomy fits without breaking this** ([ADR-0014](adr/0014-autonomy-contract.md)): auto mode does not remove human judgment — it re-routes it. The human writes an approval policy once, deliberately; a context-fresh judge (same base model — independence is of context) clears only zero-anomaly cases within explicit bounds; everything else escalates to a queue. A hard-coded never-list (merge, P0/P1 gates, human-less spec approval, policy silence) is beyond all delegation, and the policy file itself is hook-protected from agent edits (self-licensing prevention). The gates were never the weakness; auto mode makes them asynchronous, not optional.

### Law 6: Context Budget Is a Hard Limit

**Problem it solves**: Context rot. After ~200K tokens, Claude Code's output quality degrades measurably: it forgets earlier decisions, contradicts itself, produces vaguer code, and misses edge cases. Rather than produce degraded output, the pipeline hands over to a fresh agent with a clean context window.

**Why 200K specifically**: Empirical observation. Auto-compaction typically triggers around 180-200K tokens. After 2 auto-compactions, the quality drop is observable in review. 200K is the practical ceiling before "quality degradation becomes unacceptable" — not a theoretical limit, but a measured one.

**Isolation-first evolution** ([ADR-0014](adr/0014-autonomy-contract.md)): the stronger strategy is to never approach the ceiling — each phase runs in a fresh subagent context fed only by the on-disk artifacts (the same property that makes handover work). Mandatory in auto mode, opt-in for attended runs (`Phase Isolation` in harness-config), with compaction-survival retained as the fallback layer.

### Law 7: Artifact Quality Standards

**Problem it solves**: Artifact gating (Law 3) checks that files EXIST — it says nothing about whether they're any good. Without a quality floor, the agent satisfies the gate with placeholder specs ("TBD"), single-sentence sections, and vague acceptance criteria — artifacts that pass the existence check but poison every downstream phase.

**Why gold-standard examples, not just rules**: Models anchor on examples. A rule that says "write detailed ACs" produces marginally better output; a worked example of a rich GIVEN/WHEN/THEN block with concrete values sets the floor at that level. The harness therefore ships full exemplar artifacts for every phase — the anti-slop rules and validation checklists live in `artifact-standards.md`, and the worked examples live in each producing skill's "Gold Standard" section, loaded exactly when that phase runs ([ADR-0011](adr/0011-slim-always-loaded-layer.md)).

---

## Design Decisions Index

Formal Architecture Decision Records for the harness's own design choices are in `docs/adr/`:

| ADR | Decision |
|-----|----------|
| [0001](adr/0001-six-phase-pipeline.md) | Six-phase pipeline with strict ordering |
| [0002](adr/0002-state-machine-governance.md) | State machine over trust-based enforcement |
| [0003](adr/0003-board-lock-file-based.md) | File-based board lock over git-based alternatives |
| [0004](adr/0004-token-bounded-execution.md) | Token-bounded sprints over time-bounded |
| [0005](adr/0005-context7-in-plan-phase.md) | Context7 documentation lookup in /capiva:plan, not /capiva:grill-spec |
| [0006](adr/0006-artifact-gating.md) | File-existence gating over conversation-state gating |
| [0007](adr/0007-blueprint-plugin-architecture.md) | Pluggable blueprint architecture for stack-agnosticism |
| [0008](adr/0008-phase-guard-hook-enforcement.md) | Hook-enforced phase guards parsing sprint-state.md directly |
| [0009](adr/0009-machine-readable-ac-gating.md) | Machine-readable AC list gating verification; adversarial QA framing |
| [0010](adr/0010-fast-lane-pipeline.md) | Fast lane as an alternate state-machine path for small, low-risk tasks |
| [0011](adr/0011-slim-always-loaded-layer.md) | Gold-standard examples moved into skills; always-loaded layer slimmed |
| [0012](adr/0012-native-agent-primitives.md) | Native agent definitions with tool allowlists; structured subagent reports |
| [0013](adr/0013-plugin-distribution.md) | Plugin distribution: engine/state split, self-marketplace, session injection |
| [0014](adr/0014-autonomy-contract.md) | Autonomy contract: policy+judge gate routing, never-list, isolation-first context |
| [0015](adr/0015-transition-validation.md) | Sprint-state transition validation: the guard learns the state machine (design approved; implementation scheduled) |

---

*Design philosophy document for the Spec-Driven Development Harness*
*Last updated: June 2026*
