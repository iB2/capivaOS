# Workflow Pipeline — Phase Guards, Transitions & Enforcement

## Phase Guard Definitions

Every skill MUST implement a phase guard. The guard runs BEFORE any skill logic.

### Guard Template

```
PHASE GUARD — [Skill Name]
Required phase: [PHASE_NAME]

1. Read `.board/sprint-state.md`
2. Parse "Phase" from "Current Task" section
3. IF Phase ≠ [PHASE_NAME]:
   → STOP: "⛔ Phase guard failed. Current: [actual]. Required: [PHASE_NAME]."
   → Do NOT proceed under any circumstances.
   → Suggest: "Run /capiva:sprint to check state" or "Complete [previous skill] first."
4. IF Phase = [PHASE_NAME]:
   → Proceed with skill steps.
```

### Guard Matrix

| Skill | Required Phase | Sets Phase To |
|-------|---------------|---------------|
| /capiva:sprint | IDLE (or any for resume) | TRIAGE |
| /capiva:grill-spec | GRILL_SPEC | (stays GRILL_SPEC until approved) |
| /capiva:plan | PLAN | (stays PLAN until approved) |
| /capiva:implement | IMPLEMENT | (stays IMPLEMENT until all tasks done) |
| /capiva:test-verify | TEST_VERIFY | (stays TEST_VERIFY until gates pass) |
| /capiva:finish | FINISH | IDLE (task complete) |
| /capiva:spec-plan | SPEC_PLAN (fast lane) | IMPLEMENT on approval; GRILL_SPEC on abort |
| /capiva:verify-finish | VERIFY_FINISH (fast lane) | IDLE on completion; TEST_VERIFY on escalation |
| /capiva:refine | REFINING (clustered lane) | IDLE when the backlog is refined (specs approved per task) |

---

## Phase Transitions

Each transition has a trigger (what causes it), a gate (what must be true), and an action (what changes).

### IDLE → TRIAGE
- **Trigger**: /capiva:sprint picks a task from the board
- **Gate**: Board has uncompleted tasks in P0-P3
- **Action**: Update sprint-state (task ID, title, priority, phase = TRIAGE)
- **Board**: Move task to "In Progress"

### TRIAGE → GRILL_SPEC
- **Trigger**: /capiva:sprint loads task spec and begins adversarial interview
- **Gate**: Task spec exists (inline or linked document)
- **Action**: Update sprint-state phase = GRILL_SPEC
- **Board**: Update task Phase field

### GRILL_SPEC → PLAN
- **Trigger**: Human approves refined spec
- **Gate**: `docs/specs/TASK-ID-spec.md` AND `docs/specs/TASK-ID-acs.json` exist (all statuses `pending`), "Spec Approved" = Yes in sprint-state
- **Action**: Update sprint-state phase = PLAN, set "Spec Approved" = Yes
- **Board**: Update task Phase field
- **🧑 CHECKPOINT**: Human must say "approved" / "sim" / "go ahead". Silence = wait.

### PLAN → IMPLEMENT
- **Trigger**: Human approves the plan
- **Gate**: `PLAN.md` exists, `docs/tech-context/TASK-ID-tech.md` exists, "Plan Approved" = Yes in sprint-state
- **Action**: Update sprint-state phase = IMPLEMENT, set "Plan Approved" = Yes, register both artifacts
- **Board**: Update task Phase field
- **🧑 CHECKPOINT**: Human must approve. No proceeding without explicit approval.

### IMPLEMENT → TEST_VERIFY
- **Trigger**: All micro-tasks complete, all tests green
- **Gate**: Test suite passes (per blueprint §build-commands), all PLAN.md tasks checked off
- **Action**: Update sprint-state phase = TEST_VERIFY, register branch artifact
- **Board**: Update task Phase field, set Branch

### TEST_VERIFY → FINISH
- **Trigger**: Quality gates pass, human reviews report
- **Gate**: `docs/reports/TASK-ID-quality.md` exists, gates meet thresholds, every `TASK-ID-acs.json` status = `pass` (or human explicitly accepts a flagged e2e gap), end-to-end exercise evidence in the report
- **Action**: Update sprint-state phase = FINISH, set "Quality Gate" = PASS
- **Board**: Update task Quality field
- **🧑 CHECKPOINT**: Human reviews quality report before proceeding.

### Fast-Lane Transitions (Lane = fast, ADR-0010)

- **TRIAGE → SPEC_PLAN** — /capiva:sprint's qualifying predicate passed (P2/P3, no new files, no schema/arch changes, no new dependencies). 🧑 override to full always honored at task pickup.
- **SPEC_PLAN → IMPLEMENT** — 🧑 ONE gate approves spec-lite + PLAN.md together. Gate: `docs/specs/TASK-ID-spec.md` + `TASK-ID-acs.json` + `PLAN.md` exist; Spec Approved = Yes AND Plan Approved = Yes set together.
- **SPEC_PLAN → GRILL_SPEC** (abort) — scope grew (new file, schema change, arch decision, >4 micro-tasks). Lane reset to full. Logged in Phase History.
- **IMPLEMENT → VERIFY_FINISH** — all micro-tasks done, tests green (identical gate to IMPLEMENT → TEST_VERIFY).
- **VERIFY_FINISH → IDLE** — 🧑 ONE gate: compact quality report reviewed (full-lane thresholds; all acs.json statuses `pass`; e2e evidence) + merge decision. PR created, board updated, Lane reset to full.
- **VERIFY_FINISH → TEST_VERIFY** (escalation) — human routes to the full verification phase at the gate. Lane reset to full.

### FINISH → IDLE
- **Trigger**: PR created, board updated
- **Gate**: PR exists on remote, board task moved to Done
- **Action**: Reset sprint-state to IDLE, increment sprint metrics
- **Board**: Task in Done section with PR link and metrics
- **🧑 CHECKPOINT**: Human decides merge/review/discard.

---

## Failure Handling

### Test Failure During IMPLEMENT

1. Stop current micro-task
2. Read test output — fix the CODE, not the test (unless test is wrong)
3. Re-run specific test
4. Continue only when green
5. Log failure in sprint-state Notes

### Quality Gate Failure During TEST_VERIFY

1. Identify which gate failed
2. Coverage gap → targeted tests for uncovered lines
3. Static analysis issue → address or justify suppression
4. Integration failure → check test infrastructure setup
5. Re-run full suite
6. After 2 iterations: escalate to human with report

### Build Failure

1. Check error output
2. Fix the build error
3. Re-run build (per blueprint §build-commands)
4. If fix requires architectural change → return to PLAN phase (reset sprint-state)

### Spec Ambiguity in IMPLEMENT

1. STOP implementation immediately
2. Document the ambiguity
3. Reset sprint-state phase to GRILL_SPEC for that specific question
4. Resume IMPLEMENT after resolution
5. NEVER guess. Ambiguity kills quality.

### Three-Strike Rule

If a micro-task fails 3 times (subagent can't complete):
1. Log all 3 attempts and their failures
2. Set sprint-state phase = BLOCKED
3. Present findings to human
4. WAIT for human resolution — do not retry a 4th time

---

## Parallel vs Sequential

### Strictly Sequential
- Phase transitions (TRIAGE → GRILL → PLAN → IMPLEMENT → VERIFY → FINISH)
- Micro-tasks with dependencies
- TDD cycle within a task (RED → GREEN → REFACTOR)

### Parallelizable
- Independent micro-tasks in IMPLEMENT (different files, no shared state)
- Test Writer + Test Reviewer in TEST_VERIFY
- Domain modeling concurrent with spec grilling in GRILL_SPEC
- Max 4 concurrent subagents

---

## Context Management

### Mandatory /clear
- Between FINISH → TRIAGE (new task)
- After 2 auto-compactions in one phase

### Mandatory /compact
- GRILL_SPEC → PLAN transition (preserve spec, discard interview)
- IMPLEMENT → TEST_VERIFY transition (preserve file list + test results)

### Preserve Across Compaction
- Current task description + AC
- ALL modified files list
- Sprint-state.md current state
- Quality gate status
- Active design decisions

---

## Sprint Loop (Pseudocode)

```
READ .board/sprint-state.md
IF phase ≠ IDLE → RESUME from current phase

LOOP:
    // Phase 0: TRIAGE
    task = pick_highest_priority(board)
    IF not task → REPORT "Sprint complete" → STOP
    UPDATE sprint-state → TRIAGE
    UPDATE board → In Progress

    // Phase 1: GRILL_SPEC
    UPDATE sprint-state → GRILL_SPEC
    INVOKE /capiva:grill-spec
    WAIT human approval → SET "Spec Approved" = Yes
    UPDATE sprint-state → PLAN

    // Phase 2: PLAN
    INVOKE /capiva:plan
    WAIT human approval → SET "Plan Approved" = Yes
    UPDATE sprint-state → IMPLEMENT

    // Phase 3: IMPLEMENT
    INVOKE /capiva:implement
    (autonomous — subagents execute micro-tasks)
    VERIFY all tests green (per blueprint §build-commands)
    UPDATE sprint-state → TEST_VERIFY

    // Phase 4: TEST_VERIFY
    INVOKE /capiva:test-verify
    VERIFY quality gates
    WAIT human review
    UPDATE sprint-state → FINISH

    // Phase 5: FINISH
    INVOKE /capiva:finish
    WAIT human merge decision
    UPDATE sprint-state → IDLE
    UPDATE board → Done

    /clear
    CONTINUE LOOP
```
