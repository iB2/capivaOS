---
name: spec-plan
description: Fast lane — combined spec-lite + plan phase (SPEC_PLAN) with ONE human gate. Produces spec, acs.json, and PLAN.md for qualifying small tasks. See ADR-0010.
---

# Spec-Plan — Fast Lane, Combined Phase

Compress GRILL_SPEC + PLAN into one phase for tasks that qualified for the fast
lane at TRIAGE (see /capiva:sprint lane selection and ADR-0010). One pass, one human
gate, same artifacts — smaller.

**What is compressed**: the interview (targeted questions instead of the full
adversarial tree), Context7 discovery (only if the task touches a library), and
the gate count (one approval covers spec AND plan).

**What is NOT compressed**: the artifacts. The spec is shorter but real; the AC
list (`TASK-ID-acs.json`) is identical to the full lane's — same schema, same
immutability, same verification contract (ADR-0009). PLAN.md tasks still carry
Files / Implementation / Test / Verify sections.

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = SPEC_PLAN
3. Verify Lane = fast
4. If either check fails → **STOP**: "⛔ Phase guard failed. Current: [phase]/[lane]. Required: SPEC_PLAN/fast. Run /capiva:sprint to check state."
5. If both pass → proceed

## Fast-Lane Qualification Re-Check (MANDATORY)

/capiva:sprint qualified this task at TRIAGE, but you see more than /capiva:sprint did. Re-verify
the predicate before writing anything (ALL must hold):

- Priority is P2 or P3
- No new source files — modifications to existing files only
- No schema/migration changes
- No architectural changes (no new layers, services, or dependency-direction changes per blueprint §architecture)
- No new dependencies

**If ANY fails → ABORT to full lane** (this is mandatory, not advisory):
1. Update sprint-state: Phase = GRILL_SPEC, Lane = full
2. Phase History: `| [now] | [task] | SPEC_PLAN | GRILL_SPEC | lane-abort | [which predicate failed] |`
3. State: "⚠️ Task does not qualify for the fast lane ([reason]). Rerouting to the full pipeline at /capiva:grill-spec."

## Process

### Step 1: Load Context

- Read the task's spec/AC from the board entry
- Read `docs/CONTEXT.md` for domain terms; `${CLAUDE_PLUGIN_ROOT}/docs/adr/` for prior rulings
- Read the affected source files (the predicate guarantees they exist)
- Read the active blueprint's `reference.md` §coding-standards and §test-stack

### Step 2: Targeted Clarification

Not the full adversarial tree — only the questions this specific change raises:

- Exact expected behavior change (before → after, with concrete values)
- Edge cases in the touched code paths
- Error behavior if the change can fail

**One question at a time, with a recommended answer** (same interview discipline
as /capiva:grill-spec). If the codebase answers a question, state the finding instead of
asking. If clarification reveals a scope surprise (new file needed, schema
change, contested domain term) → ABORT to full lane (see above).

### Step 3: Write Spec-Lite + AC List

Create `docs/specs/TASK-ID-spec.md` with the reduced section set:

```markdown
# Spec: [Task Title] (fast lane)

## Task Reference
- ID / Priority / Source / Lane: fast

## Summary
[2-3 sentences: the behavior change and why]

## Acceptance Criteria
[Numbered GIVEN/WHEN/THEN — same rigor as the full lane. No vague AC.]

## Scope
- In: [specific files/behaviors]
- Out: [what this deliberately does not touch]

## Clarifications
[Numbered Q&A from Step 2]

## Error Scenarios
[Trigger → expected behavior → caller impact, for the touched paths]
```

Then emit `docs/specs/TASK-ID-acs.json` — identical schema and rules as the full
lane (see /capiva:grill-spec Step 6b and ADR-0009): one entry per AC, `status: "pending"`,
immutable except status after approval.

### Step 4: Write PLAN.md

Decompose into 1-4 micro-tasks (a fast-lane task needing more than 4 does not
belong in the fast lane — abort to full). Each task keeps the full-lane task
anatomy: **Files** (MODIFY only), **Context** (the existing code), **Implementation**,
**Test (write FIRST)**, **Verify** (command), **Depends on / Estimate**.

Query Context7 only if the change involves library APIs you are not certain are
current; record findings inline in PLAN.md (a separate tech-context file is not
required in the fast lane — note "fast lane: tech context inline" so /capiva:implement's
guard knows).

### Step 5: Present for the Single Gate

```
Fast lane: [TASK-ID] — [title]
Spec-lite: docs/specs/[TASK-ID]-spec.md ([N] ACs → [TASK-ID]-acs.json, all pending)
Plan: PLAN.md ([M] micro-tasks, ~[K] min)
Qualification re-check: PASS (P[2|3], modify-only, no schema/arch changes)

🧑 ONE gate covers both: approve spec + plan to proceed to /capiva:implement,
   or request changes, or say "full pipeline" to reroute to /capiva:grill-spec.
```

## Phase Transition (MANDATORY)

**After human approves:**

1. Update `.board/sprint-state.md`:
   - Phase = IMPLEMENT, Spec Approved = Yes, Plan Approved = Yes
   - Register artifacts: spec, acs.json, PLAN.md
2. Phase History: `| [now] | [task] | SPEC_PLAN | IMPLEMENT | spec-plan-approved | fast lane, [N] ACs, [M] tasks |`
3. **→ Return control to /capiva:sprint** which will invoke /capiva:implement next.

## Rules

- **One gate, full rigor.** The gate is combined; the AC quality bar is not lowered.
- **acs.json is identical to the full lane.** Same schema, same immutability, same lint.
- **Abort to full lane on scope growth.** New file, schema change, arch decision, >4 micro-tasks, or a contested domain term → GRILL_SPEC. Logged, never silent.
- **No ADRs in the fast lane.** If the task needs an ADR, it needs the full lane.
- **No CONTEXT.md edits in the fast lane.** A new/contested domain term is a full-lane signal.
- **TDD unchanged.** Every PLAN.md task has a test-first section; /capiva:implement enforces it.
