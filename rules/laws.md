# CLAUDE.md — Spec-Driven Development Harness

## What This Is

A state-machine-driven development pipeline for Claude Code that enforces spec-driven, test-first development. Every phase reads and updates `.board/sprint-state.md`, every skill enforces phase guards, and no skill can run out of sequence.

**The credo (the seven laws below, in three lines):**
1. If it's not on the board, it doesn't get built.
2. If there's no approved spec, there's no code.
3. If there's no test, there's no implementation.

**Why**: Claude Code without structure jumps to code, skips specs, forgets decisions after compaction, and self-approves mediocre quality. This pipeline makes disciplined development the path of least resistance. Rationale and philosophy: `docs/DESIGN.md`. Boundaries and adaptation: `docs/SCOPE.md`. Failure modes: `docs/troubleshooting.md`.

**Reading order**: first-time setup → run `/init`, then `/sprint`. As an agent → the laws below, then the skill for the current phase. As a maintainer → rules in `.claude/rules/`, skills in `.claude/skills/`, agents in `.claude/agents/`, blueprints in `.claude/blueprints/`.

---

## Active Blueprint

The harness is **stack-agnostic**. Stack-specific patterns, commands, and standards live in the active blueprint's `reference.md`, referenced by section: §architecture, §coding-standards, §enterprise-patterns, §test-stack, §static-analysis, §build-commands, §ci-cd, §qa-checklist.

Set the active blueprint by specifying its path:

```
Active Blueprint: .claude/blueprints/dotnet-hexagonal
```

| Blueprint | Stack |
|-----------|-------|
| `dotnet-hexagonal` | .NET 10 / C# 13 / Hexagonal Architecture |
| `python-fastapi` | Python 3.13 / FastAPI / Layered Architecture |
| `nextjs-typescript` | Node.js 22 / Next.js 15+ / App Router / shadcn/ui |

Each blueprint has a real, buildable reference project on the local filesystem (path in §project) — never committed to this repo. To add a stack, see `docs/SCOPE.md` "Adding a New Blueprint".

---

## MANDATORY — Pipeline Enforcement

> These laws override ALL other behavior. Violating any of them is equivalent to a build failure.

### Law 1: State Machine Governs All ([ADR-0002](docs/adr/0002-state-machine-governance.md))

- Before executing ANY skill: read `.board/sprint-state.md` and verify the phase matches. Mismatch → REFUSE, print the phase-guard failure, suggest the correct action.
- After completing ANY skill: update sprint-state with new phase + timestamp + artifacts.
- **Sprint state is canonical.** If sprint-state says GRILL_SPEC, you are in GRILL_SPEC. Period.

### Law 2: No Phase Skipping ([ADR-0001](docs/adr/0001-six-phase-pipeline.md))

```
Full lane: IDLE → TRIAGE → GRILL_SPEC → PLAN → IMPLEMENT → TEST_VERIFY → FINISH → IDLE
Fast lane: IDLE → TRIAGE → SPEC_PLAN → IMPLEMENT → VERIFY_FINISH → IDLE
```

The **fast lane** ([ADR-0010](docs/adr/0010-fast-lane-pipeline.md)) is an alternate state-machine path for qualifying small tasks — P2/P3, no new files, no schema/arch changes, no new dependencies. /sprint evaluates the predicate at TRIAGE and records `Lane` in sprint-state. TDD, the acs.json contract, and quality thresholds are identical in both lanes. Full is the default; P0/P1 can never go fast.

**Mechanically enforced**: the `phase_guard.py` PreToolUse hook denies source-file writes outside IMPLEMENT (test paths also allowed in TEST_VERIFY / VERIFY_FINISH) and `gh pr create` outside FINISH / VERIFY_FINISH with passing gates — see [ADR-0008](docs/adr/0008-phase-guard-hook-enforcement.md).

You CANNOT:
- Write implementation code unless sprint-state Phase = IMPLEMENT
- Write test code (beyond TDD in /implement) unless Phase = TEST_VERIFY (or VERIFY_FINISH, fast lane)
- Create a PR unless Phase = FINISH (or VERIFY_FINISH, fast lane)
- Start a new task unless Phase = IDLE
- Run /plan without an approved spec, /implement without an approved plan, /finish without Quality Gate = PASS (all tracked in sprint-state)

### Law 3: Artifacts Gate Progression ([ADR-0006](docs/adr/0006-artifact-gating.md))

Each phase produces files on disk; the next phase verifies they exist. Missing artifact → STOP and report. Do NOT improvise.

| Phase | Produces | Next Phase Checks |
|-------|----------|-------------------|
| GRILL_SPEC | `docs/specs/TASK-ID-spec.md`, `TASK-ID-acs.json`, CONTEXT.md entries | /plan verifies spec + AC list exist |
| PLAN | `PLAN.md`, `docs/tech-context/TASK-ID-tech.md` | /implement verifies plan + tech context |
| IMPLEMENT | Code + tests on feature branch | /test-verify verifies branch exists, tests pass |
| TEST_VERIFY | `docs/reports/TASK-ID-quality.md`, AC statuses in acs.json | /finish verifies report, gates pass, all ACs `pass` |
| FINISH | PR on remote | /sprint verifies task in Done |

The AC list (`TASK-ID-acs.json`, [ADR-0009](docs/adr/0009-machine-readable-ac-gating.md)) is immutable except `status` after spec approval; /test-verify flips statuses only with a meaningful test AND end-to-end exercise evidence.

### Law 4: Board Lock Protocol ([ADR-0003](docs/adr/0003-board-lock-file-based.md))

Before ANY write to `.board/tasks.md`: check `.board/board.lock` (wait/retry if fresh, 3x max) → acquire lock → read board FRESH → write → release → log in sprint-state Phase History. Full protocol: `.claude/rules/board-protocol.md`.

### Law 5: Human Checkpoints Are Blocking

Silence is NOT approval. Present the deliverable, then WAIT for explicit approval.

| Gate | When | Fast lane |
|------|------|-----------|
| Spec approval | After /grill-spec | Combined spec+plan gate after /spec-plan |
| Plan approval | After /plan | (combined above) |
| Quality review | After /test-verify | Combined quality+merge gate after /verify-finish |
| Merge decision | After /finish | (combined above) |

### Law 6: Context Budget Is a Hard Limit (200K Tokens) ([ADR-0004](docs/adr/0004-token-bounded-execution.md))

The pipeline is **token-bounded, not time-bounded**. `context-persistence.py` hooks auto-save state on every compaction and session end; SessionStart:compact restores it. Budget model, compaction triggers, and the handover protocol: `.claude/rules/context-management.md`.

- Before EVERY phase transition: run the context budget check
- Quality degradation (forgotten decisions, vague output, repeated questions) = mandatory `/handover` at the next phase boundary; before token-heavy phases (IMPLEMENT, TEST_VERIFY) in a long session = handover; lighter phases = `/compact` with focus
- Multi-session execution via handover is EXPECTED for complex tasks — the artifact chain persists on disk

### Law 7: Artifact Quality Standards

Every artifact meets the gold standard: anti-slop rules, schemas, and validation checklists in `.claude/rules/artifact-standards.md`; gold-standard worked examples in each producing skill's "Gold Standard" section ([ADR-0011](docs/adr/0011-slim-always-loaded-layer.md)). The examples are the FLOOR, not the ceiling. Every AC threads spec → acs.json → plan → tests → quality report → PR; below-standard output means the producing skill iterates before the pipeline advances.

---

## The Pipeline

| Phase | Skill | Does | Gate |
|-------|-------|------|------|
| 0 TRIAGE | `/sprint` | Pick highest-priority task, select lane, load spec | — |
| 1 GRILL_SPEC | `/grill-spec` | Adversarial interview → spec, acs.json, CONTEXT.md terms, ADRs | 🧑 spec approval |
| 2 PLAN | `/plan` | Context7 docs → micro-tasks with file paths, snippets, tests | 🧑 plan approval |
| 3 IMPLEMENT | `/implement` | One subagent per micro-task, TDD (RED→GREEN→REFACTOR), feature branch | — (autonomous) |
| 4 TEST_VERIFY | `/test-verify` | Two-agent tests + adversarial review, static analysis, e2e exercise → quality report | 🧑 quality review |
| 5 FINISH | `/finish` | PR + CAB/release artifacts, board → Done, cleanup | 🧑 merge decision |
| fast: SPEC_PLAN | `/spec-plan` | Spec-lite + plan in one pass | 🧑 one combined gate |
| fast: VERIFY_FINISH | `/verify-finish` | Verify (full thresholds) + PR | 🧑 one combined gate |

`/sprint` orchestrates the loop (state reading, lane selection, transitions, context checks, handover) — see `.claude/skills/sprint/SKILL.md`. Between tasks `/clear` is mandatory. Between sessions `/handover` produces the resume document.

## Quality Gates

Thresholds and measurement in `.claude/rules/quality-gates.md` (single source of truth). Summary: business-logic coverage ≥ 80%, infrastructure ≥ 60%, overall ≥ 75%; zero new linter warnings; integration tests all pass; every AC `pass` in acs.json (test + end-to-end evidence). Any gate below minimum blocks /finish.

## Agent Roles

Roles are native Claude Code agent definitions with platform-enforced tool allowlists ([ADR-0012](docs/adr/0012-native-agent-primitives.md)) — spawn by agent type, don't paste role text.

| Agent | File | Tools (enforced) | Spawned By | Purpose |
|-------|------|------------------|-----------|---------|
| dev | `.claude/agents/dev.md` | read + Edit/Write/Bash | /implement, /test-verify | Executes micro-tasks with TDD; returns validated JSON report |
| qa | `.claude/agents/qa.md` | read-only | /test-verify | Adversarially refutes implementation claims |
| arch | `.claude/agents/arch.md` | read + Write | /plan | Validates layers/patterns; writes ADRs, deviation records |

Each agent receives task-specific context (spec, CONTEXT.md, blueprint reference.md) in its prompt. Max 4 concurrent; one micro-task each; three failures → BLOCKED. Spawn mechanics: `.claude/skills/implement/SKILL.md`.

## Rules & Docs Index

| File | Content |
|------|---------|
| `.claude/rules/artifact-standards.md` | Anti-slop rules, artifact schemas, validation checklists |
| `.claude/rules/context-management.md` | Token budget model, compaction, handover protocol |
| `.claude/rules/state-management.md` | State machine, board lock, artifact chain, session recovery |
| `.claude/rules/workflow-pipeline.md` | Phase guards, transitions, failure handling, parallelism |
| `.claude/rules/board-protocol.md` | Task format, board sections, write protocol |
| `.claude/rules/quality-gates.md` | Coverage thresholds, static analysis, review policy |
| `.claude/rules/coding-standards.md` | Universal coding conventions + blueprint pointer |
| `.claude/rules/enterprise-blueprint.md` | Universal enterprise constraints + blueprint pointer |
| `docs/DESIGN.md` | Design philosophy, source attribution, rationale for every law |
| `docs/SCOPE.md` | What the harness is/isn't, lanes, configuration, adaptation guide |
| `docs/troubleshooting.md` | Troubleshooting table, anti-pattern tables |
| `docs/adr/` | Architecture Decision Records for the harness's own design |

## Session Recovery

1. Read `.board/sprint-state.md`
2. Phase ≠ IDLE → announce and resume from that phase (never restart)
3. Stale `.board/board.lock` (> 60s) → delete it
4. Phase = IDLE → clean state, ready for /sprint

## Configuration

Required: populated `.board/tasks.md`, initialized `.board/sprint-state.md`, an Active Blueprint (above), and project source in the working directory. Setup, adaptation, custom blueprints, and Jira integration: `docs/SCOPE.md` + `/init`. Blueprint deviations require a Deviation Record (`templates/deviation-record.md`); see `.claude/rules/enterprise-blueprint.md`.

---

*Spec-driven development harness for Claude Code*
*State-machine enforced, board-locked, artifact-gated, stack-agnostic via blueprints*
