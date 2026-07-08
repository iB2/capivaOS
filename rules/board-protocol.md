# Board Protocol — Task Management & Concurrency

## Board Location

**Source of truth**: `.board/tasks.md`
**Lock file**: `.board/board.lock` (runtime, gitignored)
**State file**: `.board/sprint-state.md` (tracks active pipeline state)

---

## Task Format

Every task on the board follows this structure:

```markdown
- [ ] **TASK-ID** Task title (P0)
  - **Spec**: [inline description OR link to docs/specs/TASK-ID-spec.md]
  - **AC**: [numbered acceptance criteria]
  - **Depends**: [TASK-IDs or "none"]
  - **Assignee**: [name or "unassigned"]
  - **Status**: Backlog | In Progress | Blocked | Review | Done
  - **Phase**: IDLE | TRIAGE | GRILL_SPEC | PLAN | IMPLEMENT | TEST_VERIFY | FINISH | SPEC_PLAN | VERIFY_FINISH (fast lane)
  - **Branch**: [feature/branch-name or "--"]
  - **PR**: [#number or "--"]
  - **Quality**: [coverage% / quality gate pass|fail or "--"]
  - **Started**: [ISO date or "--"]
  - **Completed**: [ISO date or "--"]
  - **Notes**: [any additional context]
```

### Priority Levels

| Priority | Meaning | Pipeline Enforcement |
|----------|---------|---------------------|
| P0 | Critical blocker | Full pipeline, human review at EVERY checkpoint |
| P1 | Sprint commitment | Full pipeline, human review at spec + quality gates |
| P2 | Planned | Full pipeline, automated review acceptable at Phase 3; fast lane if the ADR-0010 predicate passes |
| P3 | Nice to have | Spec + plan required, lighter review; fast lane if the ADR-0010 predicate passes |
| P4 | Backlog / spike | No spec required, no quality gates |

---

## Board Sections

```markdown
# Task Board

## In Progress
[Max 1 task. Tracks the active pipeline task with phase.]

## Up Next
[Queued for this sprint, priority order. Sprint picks from here.]

## Blocked
[Cannot proceed. Must include blocker reason and date.]

## Done
[Completed. Immutable once moved here. PR + quality metrics.]

## Backlog
[Future work, prioritized but not committed.]
```

---

## Board Write Protocol

### CRITICAL: Lock Before Write

**Every write to `.board/tasks.md` MUST follow this protocol:**

#### Step 1 — Check Lock
```
Read `.board/board.lock`
  IF exists AND acquired < 60 seconds ago → WAIT 5s, retry (max 3)
  IF exists AND acquired > 60 seconds ago → stale lock, delete and proceed
  IF not exists → proceed to Step 2
  IF still locked after 3 retries → STOP: "Board locked by [holder]. Cannot update."
```

#### Step 2 — Acquire Lock
Create `.board/board.lock`:
```
holder: main
acquired: 2026-06-18T14:30:00Z
operation: moving TASK-001 to In Progress
```

#### Step 3 — Read Fresh
Read `.board/tasks.md` FRESH. Do not use any cached version.

#### Step 4 — Apply Changes
Make the specific update. One logical change per lock cycle.

#### Step 5 — Write Board
Write the updated `.board/tasks.md`.

#### Step 6 — Release Lock
Delete `.board/board.lock`. Verify deletion.

#### Step 7 — Log
Add entry to `.board/sprint-state.md` Phase History table.

### Subagent Board Access

Subagents (spawned by /capiva:implement) have RESTRICTED access:

| Operation | Allowed? |
|-----------|----------|
| Read board | YES (no lock needed) |
| Update own subtask checkbox | YES (with lock) |
| Move tasks between sections | NO — orchestrator only |
| Change priority or assignee | NO — human only |
| Add or remove tasks | NO — orchestrator only |

---

## Board Update Events

| Event | Skill | Board Change | Sprint State Change |
|-------|-------|-------------|-------------------|
| Task selected | /capiva:sprint | Move to "In Progress", set Phase | Phase → TRIAGE |
| Spec approved | /capiva:grill-spec | Update Phase field | Phase → GRILL_SPEC → PLAN |
| Plan approved | /capiva:plan | Update Phase field | Phase → PLAN → IMPLEMENT |
| Implementation started | /capiva:implement | Set Branch field | Phase → IMPLEMENT |
| Subtask completed | Subagent | Tick subtask checkbox | (no phase change) |
| All subtasks done | /capiva:implement | Update Phase | Phase → TEST_VERIFY |
| Quality gates pass | /capiva:test-verify | Add Quality field | Phase → FINISH |
| PR created | /capiva:finish | Move to "Done", add PR/Completed | Phase → IDLE |
| Task blocked | Any skill | Move to "Blocked", add reason | Phase → BLOCKED |
| Sprint end | /capiva:sprint | Summary appended | Phase → IDLE |

---

## Approvals Queue (`.board/approvals.md`, auto mode — ADR-0014)

Escalations from delegated gates queue here; the human resolves them by editing
Status. One entry per escalation:

```markdown
## ESC-[N] — [TASK-ID] [gate type] — [timestamp]
- **Exception**: [one-paragraph exception-first summary from the gate-judge]
- **Details**: [file:line findings]
- **Options**: approve as-is | request change | route to attended
- **Status**: pending | approved | changes-requested: [note] | attended
```

Rules: agents APPEND entries and READ resolutions — they never edit an entry's
Status (that is the human's answer). Every resolution the driver acts on is
logged in Phase History (`gate-escalation-resolved`). Every delegated CLEAR is
logged too (`gate-delegated`, with the policy/judge basis) — the audit trail
must show who decided what, human or machine, and on what grounds.

## Board Integrity Rules

1. **One task in progress.** If "In Progress" has a task, do NOT start another.
2. **Depends is mechanical.** Triage only selects tasks whose dependencies are all Done; a dependency cycle is a board defect that stops selection (lint check 8). Depends IDs must exist on the board.
3. **Status = Phase consistency.** In Progress → Phase must be TRIAGE..FINISH. Done → Phase must be IDLE.
4. **Done is immutable.** Once in Done, never edit. Only append.
5. **Blocked needs a reason.** No silent blocks. Always include `Blocker:` with description and date.
6. **Timestamps mandatory.** Started and Completed must have ISO dates.
7. **Lock always released.** Every lock acquisition MUST have a corresponding release in the same turn.
8. **Audit trail.** Every board change logged in sprint-state.md Phase History.

---

## Commit Message Format — Karma Convention

All commits MUST follow the enterprise Karma convention:

```
scope(context): description #taskNumber
```

### Scopes

| Scope | When to Use |
|-------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or modifying tests |
| `docs` | Documentation changes |
| `chore` | Build, CI, dependency updates |
| `style` | Formatting, whitespace, code style |
| `perf` | Performance improvement |

### Task Number

Every commit references its board task ID with `#`:

```
feat(quotes): add quote expiration sweep #COS-42
test(quotes): integration tests for QuoteRepository #COS-42
fix(orders): correct decimal precision in FIX message #COS-43
```

### Enforcement

- `/capiva:implement` subagents produce commits in this format
- `/capiva:finish` validates all branch commits follow Karma convention
- Non-compliant commits are flagged in the PR review
