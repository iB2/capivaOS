# ADR-0001: Six-Phase Pipeline with Strict Ordering

## Status

Accepted

## Context

Claude Code, when used for development without structure, exhibits a pattern of jumping directly to implementation — skipping requirements clarification, planning, and test design. This produces code that technically works but doesn't match what was needed, has poor test coverage, and is difficult to review because there's no spec to review against.

We needed a pipeline that forces structured development while remaining practical (not so many phases that each task takes forever).

### Options Considered

**Option A: Three phases (Spec → Implement → Ship)**
- Pro: Simple, low overhead
- Con: No separation between "understand the spec" and "break it into tasks." Planning and implementation are conflated, leading to monolithic commits and poor parallelism
- Con: No dedicated test verification phase — quality is checked as an afterthought during ship

**Option B: Four phases (Spec → Plan → Build → Ship)**
- Pro: Separates planning from building
- Con: No adversarial spec review — the spec is taken at face value
- Con: No dedicated quality verification — tests and coverage are only checked during build, not independently reviewed

**Option C: Six phases (Triage → Grill → Plan → Implement → Verify → Finish)**
- Pro: Each phase has one clear job with one clear output
- Pro: Adversarial spec review catches ambiguities before any code is written
- Pro: Planning produces artifacts (PLAN.md) that enable parallel subagent execution
- Pro: Dedicated verification phase means quality is independently assessed, not self-reported by the implementer
- Pro: Finish phase handles the administrative work (PR, board update, Jira) separately from implementation
- Con: More overhead per task (mitigated by P3/P4 bypass for lightweight tasks)

**Option D: Eight+ phases (add Design, Security Review, Deploy, etc.)**
- Pro: More granular control
- Con: Overhead becomes prohibitive for most tasks
- Con: Context budget (200K tokens) may not accommodate 8 phases in a single session

## Decision

**Six phases (Option C)**, ordered as: TRIAGE → GRILL_SPEC → PLAN → IMPLEMENT → TEST_VERIFY → FINISH.

This ordering is not arbitrary. Each phase produces artifacts consumed by the next:

```
TRIAGE selects the task → GRILL_SPEC needs a task to grill
GRILL_SPEC produces a spec → PLAN needs a spec to decompose
PLAN produces micro-tasks → IMPLEMENT needs tasks to execute
IMPLEMENT produces code+tests → TEST_VERIFY needs code to verify
TEST_VERIFY produces a quality report → FINISH needs a report for the PR
```

Reversing or interleaving any pair breaks this dependency chain.

## Consequences

- Every task goes through all 6 phases (except P4, which can bypass spec and quality gates)
- Complex tasks that exhaust context mid-pipeline require multi-session execution via handover
- The pipeline has four human checkpoints (after phases 1, 2, 4, 5) — this is the minimum set where human judgment is irreplaceable
- Adding a new phase requires updating the state machine, all guard matrices, CLAUDE.md, and the workflow diagram — deliberately expensive to prevent phase proliferation
