# CLAUDE.md — Spec-Driven Development Harness

## What This Is

A state-machine-driven development pipeline for Claude Code that enforces spec-driven, test-first development. Every phase reads and updates `.board/sprint-state.md`, every skill enforces phase guards, and no skill can run out of sequence.

**The credo (the seven laws below, in three lines):**
1. If it's not on the board, it doesn't get built.
2. If there's no approved spec, there's no code.
3. If there's no test, there's no implementation.

**Why**: Claude Code without structure jumps to code, skips specs, forgets decisions after compaction, and self-approves mediocre quality. This pipeline makes disciplined development the path of least resistance. Rationale and philosophy: `${CLAUDE_PLUGIN_ROOT}/docs/DESIGN.md`. Boundaries and adaptation: `${CLAUDE_PLUGIN_ROOT}/docs/SCOPE.md`. Failure modes: `${CLAUDE_PLUGIN_ROOT}/docs/troubleshooting.md`.

**Reading order**: first-time setup → run `/capiva:init`, then `/capiva:sprint`. As an agent → the laws below, then the skill for the current phase. As a maintainer → rules in `${CLAUDE_PLUGIN_ROOT}/rules/`, skills in `${CLAUDE_PLUGIN_ROOT}/skills/`, agents in `${CLAUDE_PLUGIN_ROOT}/agents/`, blueprints in `${CLAUDE_PLUGIN_ROOT}/blueprints/`.

---

## Active Blueprint

The harness is **stack-agnostic**. Stack-specific patterns, commands, and standards live in the active blueprint's `reference.md`, referenced by section: §architecture, §coding-standards, §enterprise-patterns, §test-stack, §static-analysis, §build-commands, §ci-cd, §qa-checklist.

The active blueprint is set per project in `.board/harness-config.md` (written by /capiva:init):

```
- **Active Blueprint**: dotnet-hexagonal
```

Blueprint resolution order (first match wins):
1. `${CLAUDE_PROJECT_DIR}/capiva-blueprints/<name>/reference.md` — project-local custom blueprint or override
2. `${CLAUDE_PLUGIN_ROOT}/blueprints/<name>/reference.md` — shipped with the plugin

| Blueprint | Stack |
|-----------|-------|
| `dotnet-hexagonal` | .NET 10 / C# 13 / Hexagonal Architecture |
| `python-fastapi` | Python 3.13 / FastAPI / Layered Architecture |
| `nextjs-typescript` | Node.js 22 / Next.js 15+ / App Router / shadcn/ui |

Shipped blueprints have real, buildable reference projects on the maintainers' machines (path in §project) — never committed. Custom stacks: create `capiva-blueprints/<name>/reference.md` in your project following the same sections as the shipped blueprints; see `${CLAUDE_PLUGIN_ROOT}/docs/SCOPE.md` "Adding a New Blueprint".

---

## MANDATORY — Pipeline Enforcement

> These laws override ALL other behavior. Violating any of them is equivalent to a build failure.

### Law 1: State Machine Governs All ([ADR-0002](${CLAUDE_PLUGIN_ROOT}/docs/adr/0002-state-machine-governance.md))

- Before executing ANY skill: read `.board/sprint-state.md` and verify the phase matches. Mismatch → REFUSE, print the phase-guard failure, suggest the correct action.
- After completing ANY skill: update sprint-state with new phase + timestamp + artifacts.
- **Sprint state is canonical.** If sprint-state says GRILL_SPEC, you are in GRILL_SPEC. Period.

### Law 2: No Phase Skipping ([ADR-0001](${CLAUDE_PLUGIN_ROOT}/docs/adr/0001-six-phase-pipeline.md))

```
Full lane: IDLE → TRIAGE → GRILL_SPEC → PLAN → IMPLEMENT → TEST_VERIFY → FINISH → IDLE
Fast lane: IDLE → TRIAGE → SPEC_PLAN → IMPLEMENT → VERIFY_FINISH → IDLE
```

The **fast lane** ([ADR-0010](${CLAUDE_PLUGIN_ROOT}/docs/adr/0010-fast-lane-pipeline.md)) is an alternate state-machine path for qualifying small tasks — P2/P3, no new files, no schema/arch changes, no new dependencies. /capiva:sprint evaluates the predicate at TRIAGE and records `Lane` in sprint-state. TDD, the acs.json contract, and quality thresholds are identical in both lanes. Full is the default; P0/P1 can never go fast.

**Mechanically enforced**: the `phase_guard.py` PreToolUse hook denies source-file writes outside IMPLEMENT (test paths also allowed in TEST_VERIFY / VERIFY_FINISH) and `gh pr create` outside FINISH / VERIFY_FINISH with passing gates — see [ADR-0008](${CLAUDE_PLUGIN_ROOT}/docs/adr/0008-phase-guard-hook-enforcement.md).

You CANNOT:
- Write implementation code unless sprint-state Phase = IMPLEMENT
- Write test code (beyond TDD in /capiva:implement) unless Phase = TEST_VERIFY (or VERIFY_FINISH, fast lane)
- Create a PR unless Phase = FINISH (or VERIFY_FINISH, fast lane)
- Start a new task unless Phase = IDLE
- Run /capiva:plan without an approved spec, /capiva:implement without an approved plan, /capiva:finish without Quality Gate = PASS (all tracked in sprint-state)

### Law 3: Artifacts Gate Progression ([ADR-0006](${CLAUDE_PLUGIN_ROOT}/docs/adr/0006-artifact-gating.md))

Each phase produces files on disk; the next phase verifies they exist. Missing artifact → STOP and report. Do NOT improvise.

| Phase | Produces | Next Phase Checks |
|-------|----------|-------------------|
| GRILL_SPEC | `docs/specs/TASK-ID-spec.md`, `TASK-ID-acs.json`, CONTEXT.md entries | /capiva:plan verifies spec + AC list exist |
| PLAN | `PLAN.md`, `docs/tech-context/TASK-ID-tech.md` | /capiva:implement verifies plan + tech context |
| IMPLEMENT | Code + tests on feature branch | /capiva:test-verify verifies branch exists, tests pass |
| TEST_VERIFY | `docs/reports/TASK-ID-quality.md`, AC statuses in acs.json | /capiva:finish verifies report, gates pass, all ACs `pass` |
| FINISH | PR on remote | /capiva:sprint verifies task in Done |

The AC list (`TASK-ID-acs.json`, [ADR-0009](${CLAUDE_PLUGIN_ROOT}/docs/adr/0009-machine-readable-ac-gating.md)) is immutable except `status` after spec approval; /capiva:test-verify flips statuses only with a meaningful test AND end-to-end exercise evidence.

### Law 4: Board Lock Protocol ([ADR-0003](${CLAUDE_PLUGIN_ROOT}/docs/adr/0003-board-lock-file-based.md))

Before ANY write to `.board/tasks.md`: check `.board/board.lock` (wait/retry if fresh, 3x max) → acquire lock → read board FRESH → write → release → log in sprint-state Phase History. Full protocol: `${CLAUDE_PLUGIN_ROOT}/rules/board-protocol.md`.

### Law 5: Human Checkpoints Are Blocking ([ADR-0014](${CLAUDE_PLUGIN_ROOT}/docs/adr/0014-autonomy-contract.md))

Silence is NOT approval. Present the deliverable, then WAIT for explicit approval.

| Gate | When | Fast lane |
|------|------|-----------|
| Spec approval | After /capiva:grill-spec | Combined spec+plan gate after /capiva:spec-plan |
| Plan approval | After /capiva:plan | (combined above) |
| Quality review | After /capiva:test-verify | Combined quality+merge gate after /capiva:verify-finish |
| Merge decision | After /capiva:finish | (combined above) |

**Modes (ADR-0014).** The table above is ATTENDED mode — the default, unchanged. In AUTO mode (opt-in per run via /capiva:auto), gates are ROUTED instead of blocking: the human-authored `.board/approval-policy.md` clears what it explicitly covers; an independent judge (never the artifact's producer) clears zero-anomaly cases within explicit bounds; everything else queues in `.board/approvals.md` with an exception-first summary. **The never-list — no machine may clear, ever**: (1) the merge decision, (2) any gate on a P0/P1 task, (3) spec approval for any spec produced without a human interlocutor or with open questions (fast-lane specs derived from human-authored board ACs count as having an interlocutor — the human wrote the task and its acceptance criteria; every spec AC must trace to the board task), (4) anything the policy does not explicitly cover — silence means escalate. The never-list is engine-hard-coded; a policy attempting to extend delegation into it is ignored, escalated, and logged. Item (1) is also hook-enforced: the phase guard denies `gh pr merge` and `git push` targeting the default branch in every phase and mode; GitHub branch protection covers the routes a hook cannot see (web UI, MCP). The policy file is human law: agents may not edit it (hook-enforced) — they propose amendments via escalation only. Every delegated decision is logged in Phase History with its rationale.

### Law 6: Context Budget Is a Hard Limit (200K Tokens) ([ADR-0004](${CLAUDE_PLUGIN_ROOT}/docs/adr/0004-token-bounded-execution.md))

The pipeline is **token-bounded, not time-bounded**. `context-persistence.py` hooks auto-save state on every compaction and session end; SessionStart:compact restores it. Budget model, compaction triggers, and the handover protocol: `${CLAUDE_PLUGIN_ROOT}/rules/context-management.md`.

- Before EVERY phase transition: run the context budget check
- Quality degradation (forgotten decisions, vague output, repeated questions) = mandatory `/capiva:handover` at the next phase boundary; before token-heavy phases (IMPLEMENT, TEST_VERIFY) in a long session = handover; lighter phases = `/compact` with focus
- Multi-session execution via handover is EXPECTED for complex tasks — the artifact chain persists on disk

**Context strategy (ADR-0014).** Isolation beats survival: each phase CAN run in a fresh subagent context that reads the artifacts, does its one job, writes its outputs, and ends — no context lives long enough to compact. In AUTO mode this is mandatory. In ATTENDED mode it is opt-in via `- **Phase Isolation**: on` in `.board/harness-config.md` (absent = off; today's behavior). **Budget invariants for auto runs**: every run carries BOTH a max-task cap and a phase budget (`Loop Phase Budget` — the countable proxy for a token budget: isolation bounds each phase, so phases × bound ≈ tokens; ANY provider limit signal additionally parks the run) — an unlimited value does not exist; the loop parks only at phase boundaries, producing the standard handover document; the morning report leads with why the loop stopped.

### Law 7: Artifact Quality Standards

Every artifact meets the gold standard: anti-slop rules, schemas, and validation checklists in `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md`; gold-standard worked examples in each producing skill's "Gold Standard" section ([ADR-0011](${CLAUDE_PLUGIN_ROOT}/docs/adr/0011-slim-always-loaded-layer.md)). The examples are the FLOOR, not the ceiling. Every AC threads spec → acs.json → plan → tests → quality report → PR; below-standard output means the producing skill iterates before the pipeline advances.

---

## The Pipeline

| Phase | Skill | Does | Gate |
|-------|-------|------|------|
| 0 TRIAGE | `/capiva:sprint` | Pick highest-priority task, select lane, load spec | — |
| 1 GRILL_SPEC | `/capiva:grill-spec` | Adversarial interview → spec, acs.json, CONTEXT.md terms, ADRs | 🧑 spec approval |
| 2 PLAN | `/capiva:plan` | Context7 docs → micro-tasks with file paths, snippets, tests | 🧑 plan approval |
| 3 IMPLEMENT | `/capiva:implement` | One subagent per micro-task, TDD (RED→GREEN→REFACTOR), feature branch | — (autonomous) |
| 4 TEST_VERIFY | `/capiva:test-verify` | Two-agent tests + adversarial review, static analysis, e2e exercise → quality report | 🧑 quality review |
| 5 FINISH | `/capiva:finish` | PR + CAB/release artifacts, board → Done, cleanup | 🧑 merge decision |
| fast: SPEC_PLAN | `/capiva:spec-plan` | Spec-lite + plan in one pass | 🧑 one combined gate |
| fast: VERIFY_FINISH | `/capiva:verify-finish` | Verify (full thresholds) + PR | 🧑 one combined gate |

`/capiva:sprint` orchestrates the loop (state reading, lane selection, transitions, context checks, handover) — see `${CLAUDE_PLUGIN_ROOT}/skills/sprint/SKILL.md`. Between tasks `/clear` is mandatory. Between sessions `/capiva:handover` produces the resume document.

## Quality Gates

Thresholds and measurement in `${CLAUDE_PLUGIN_ROOT}/rules/quality-gates.md` (single source of truth). Summary: business-logic coverage ≥ 80%, infrastructure ≥ 60%, overall ≥ 75%; zero new linter warnings; integration tests all pass; every AC `pass` in acs.json (test + end-to-end evidence). Any gate below minimum blocks /capiva:finish.

## Agent Roles

Roles are native Claude Code agent definitions with platform-enforced tool allowlists ([ADR-0012](${CLAUDE_PLUGIN_ROOT}/docs/adr/0012-native-agent-primitives.md)) — spawn by agent type, don't paste role text.

| Agent | File | Tools (enforced) | Spawned By | Purpose |
|-------|------|------------------|-----------|---------|
| dev | `${CLAUDE_PLUGIN_ROOT}/agents/dev.md` | read + Edit/Write/Bash | /capiva:implement, /capiva:test-verify | Executes micro-tasks with TDD; returns validated JSON report |
| qa | `${CLAUDE_PLUGIN_ROOT}/agents/qa.md` | read-only | /capiva:test-verify | Adversarially refutes implementation claims |
| arch | `${CLAUDE_PLUGIN_ROOT}/agents/arch.md` | read + Write | /capiva:plan | Validates layers/patterns; writes ADRs, deviation records |
| gate-judge | `${CLAUDE_PLUGIN_ROOT}/agents/gate-judge.md` | read-only | /capiva:auto (gate triage) | Judges delegated gates in auto mode: CLEAR only at zero anomalies, else ESCALATE; never-list hard-coded (ADR-0014) |
| phase-runner | `${CLAUDE_PLUGIN_ROOT}/agents/phase-runner.md` | read + Edit/Write/Bash | /capiva:sprint (Phase Isolation), /capiva:auto | Runs ONE phase in fresh context, then stops; the orchestrator remains the single sprint-state writer |

Each agent receives task-specific context (spec, CONTEXT.md, blueprint reference.md) in its prompt. Max 4 concurrent; one micro-task each; three failures → BLOCKED. Spawn mechanics: `${CLAUDE_PLUGIN_ROOT}/skills/implement/SKILL.md`.

## Rules & Docs Index

| File | Content |
|------|---------|
| `${CLAUDE_PLUGIN_ROOT}/rules/artifact-standards.md` | Anti-slop rules, artifact schemas, validation checklists |
| `${CLAUDE_PLUGIN_ROOT}/rules/context-management.md` | Token budget model, compaction, handover protocol |
| `${CLAUDE_PLUGIN_ROOT}/rules/state-management.md` | State machine, board lock, artifact chain, session recovery |
| `${CLAUDE_PLUGIN_ROOT}/rules/workflow-pipeline.md` | Phase guards, transitions, failure handling, parallelism |
| `${CLAUDE_PLUGIN_ROOT}/rules/board-protocol.md` | Task format, board sections, write protocol |
| `${CLAUDE_PLUGIN_ROOT}/rules/quality-gates.md` | Coverage thresholds, static analysis, review policy |
| `${CLAUDE_PLUGIN_ROOT}/rules/coding-standards.md` | Universal coding conventions + blueprint pointer |
| `${CLAUDE_PLUGIN_ROOT}/rules/enterprise-blueprint.md` | Universal enterprise constraints + blueprint pointer |
| `${CLAUDE_PLUGIN_ROOT}/docs/DESIGN.md` | Design philosophy, source attribution, rationale for every law |
| `${CLAUDE_PLUGIN_ROOT}/docs/SCOPE.md` | What the harness is/isn't, lanes, configuration, adaptation guide |
| `${CLAUDE_PLUGIN_ROOT}/docs/troubleshooting.md` | Troubleshooting table, anti-pattern tables |
| `${CLAUDE_PLUGIN_ROOT}/docs/adr/` | Architecture Decision Records for the harness's own design |

## Session Recovery

1. Read `.board/sprint-state.md`
2. Phase ≠ IDLE → announce and resume from that phase (never restart)
3. Stale `.board/board.lock` (> 60s) → delete it
4. Phase = IDLE → clean state, ready for /capiva:sprint

## Configuration

Required: populated `.board/tasks.md`, initialized `.board/sprint-state.md`, an Active Blueprint (above), and project source in the working directory. Setup, adaptation, custom blueprints, and Jira integration: `${CLAUDE_PLUGIN_ROOT}/docs/SCOPE.md` + `/capiva:init`. Blueprint deviations require a Deviation Record (`${CLAUDE_PLUGIN_ROOT}/project-template/templates/deviation-record.md`); see `${CLAUDE_PLUGIN_ROOT}/rules/enterprise-blueprint.md`.

---

*Spec-driven development harness for Claude Code*
*State-machine enforced, board-locked, artifact-gated, stack-agnostic via blueprints*
