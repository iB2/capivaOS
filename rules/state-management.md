# State Management — Concurrency, Locking & Sprint State

## Sprint State Machine

**Source of truth**: `.board/sprint-state.md`

Every skill MUST read this file before executing. Every skill MUST update it on completion.
This is not optional documentation — it is the enforcement mechanism.

### Sprint-State Field Format

The file uses Markdown field syntax: `- **Field Name**: Value`. All phase guards parse these fields.

| Field | Values | Set By |
|-------|--------|--------|
| Task ID | Board task ID or `(none)` | /capiva:sprint |
| Lane | full, fast | /capiva:sprint (TRIAGE, per ADR-0010 predicate) |
| Task Title | Task name or `(none)` | /capiva:sprint |
| Priority | P0-P4 or `--` | /capiva:sprint |
| Phase | IDLE, TRIAGE, GRILL_SPEC, PLAN, IMPLEMENT, TEST_VERIFY, FINISH, SPEC_PLAN, VERIFY_FINISH, BLOCKED, REFINING | Every skill |
| Phase Started | ISO timestamp or `--` | Every skill |
| Spec Approved | Yes / No | /capiva:sprint (after human approval) |
| Plan Approved | Yes / No | /capiva:sprint (after human approval) |
| Quality Gate | PASS, ACCEPTED_SOFT_FAIL, HARD_FAIL, or `--` | /capiva:test-verify |
| Branch | `feature/TASK-ID-slug` or `--` | /capiva:implement |
| Loop Active | yes / (absent = no loop) | auto-mode driver (/capiva:auto) |
| Loop Task Cap / Loop Tasks Done / Loop Phase Budget / Loop Stop Reason | counters for the active auto run (Loop Phase Budget = phase executions, the countable token proxy per ADR-0014 amendment) | auto-mode driver; read by session_context for [AUTO_LOOP_RESUME] after compaction |

Phase guards check: `Phase`, `Spec Approved`, `Plan Approved`, `Quality Gate`.
Template: `.board/sprint-state.md` (initialized with IDLE state, empty history, and artifacts registry).

### Harness-config Fields (`.board/harness-config.md`)

Separate from the sprint-state fields above; these are project settings, read by skills (not by hooks),
documented at their point of use:

| Field | Values | Read By |
|-------|--------|---------|
| Active Blueprint | blueprint name | /capiva:init, every phase (stack patterns) |
| Phase Isolation | on / (absent = off) | /capiva:sprint (attended opt-in), /capiva:auto (always on) |
| Auto Task Cap | integer (default 3) | /capiva:auto (per-run task budget) |
| Auto Preflight | on / off (absent = on) | /capiva:auto — `off` skips the interactive pre-flight confirm for scheduled/unattended runs (ADR-0014 grill→execute-cycle amendment); absent/on = show the gate (fail-safe) |

### Valid Phase Transitions

```
Full lane (default):
IDLE ──→ TRIAGE ──→ GRILL_SPEC ──→ PLAN ──→ IMPLEMENT ──→ TEST_VERIFY ──→ FINISH ──→ IDLE
  ↑                                                                                      │
  └──────────────────────────────────────────────────────────────────────────────────────┘

Fast lane (Lane = fast, ADR-0010):
IDLE ──→ TRIAGE ──→ SPEC_PLAN ──→ IMPLEMENT ──→ VERIFY_FINISH ──→ IDLE

Clustered lane (batch-refine, RFN-004 — /capiva:refine):
IDLE ──→ REFINING ──→ IDLE   (front-load grilling for the whole backlog; then normal execution)

Special transitions:
  ANY ──→ BLOCKED (human escalation or three-strike)
  BLOCKED ──→ (return to phase that blocked, after human resolution)
  ANY ──→ IDLE (human abort: "stop", "cancel", "discard")
  SPEC_PLAN ──→ GRILL_SPEC (fast-lane abort: scope grew; Lane reset to full)
  VERIFY_FINISH ──→ TEST_VERIFY (fast-lane escalation at the quality gate; Lane reset to full)
```

### Phase Ownership

| Phase | Owner Skill | Can Write Code? | Can Write Board? | Can Create PR? |
|-------|------------|-----------------|------------------|----------------|
| IDLE | /capiva:sprint | No | Yes (pick task) | No |
| TRIAGE | /capiva:sprint | No | Yes (assign task) | No |
| GRILL_SPEC | /capiva:grill-spec | No | No | No |
| PLAN | /capiva:plan | No | No | No |
| IMPLEMENT | /capiva:implement | YES | Yes (progress) | No |
| TEST_VERIFY | /capiva:test-verify | Yes (tests only) | No | No |
| FINISH | /capiva:finish | No | Yes (complete) | YES |
| SPEC_PLAN | /capiva:spec-plan | No | No | No |
| VERIFY_FINISH | /capiva:verify-finish | Yes (tests only) | Yes (complete) | YES |
| BLOCKED | (none) | No | Yes (flag) | No |

### Phase Guard Protocol

Every skill includes this guard at the top:

```
1. Read `.board/sprint-state.md`
2. Parse the "Phase" field from "Current Task" section
3. Compare against this skill's required phase
4. If MISMATCH → STOP. Print: "⛔ Phase guard failed. Current: [X]. Required: [Y]. Run /capiva:sprint to check state."
5. If MATCH → proceed with skill steps
```

**No exceptions.** Even if the human says "just run /capiva:implement" — if the phase isn't IMPLEMENT, refuse.

**Hook backstop**: independent of skill discipline, the `phase_guard.py` PreToolUse hook parses this file's `- **Field**:` format and denies source-file writes outside IMPLEMENT and `gh pr create` outside FINISH at the tool layer (see ADR-0008). The field format above is therefore a load-bearing interface — changing it requires updating `phase_guard.py` and `context-persistence.py` in the same commit.

### Sprint State Updates

When transitioning phases, update `.board/sprint-state.md` atomically:

1. Change the Phase field to the new phase
2. Update "Phase started" timestamp
3. Add a row to the Phase History table: `| timestamp | task | from_phase | to_phase | gate | notes |`
4. Log the transition in the terminal output

Format for Phase History rows:
```
| 2026-06-18 14:30 | TASK-001 | GRILL_SPEC | PLAN | spec-approved | 3 ADRs created, 12 glossary terms |
```

---

## Board Lock Protocol

**File**: `.board/board.lock`

The board (`.board/tasks.md`) is a shared resource. Multiple agents (subagents, parallel workers) may attempt to write to it. The lock prevents corruption.

Since 1.3.0 the lock is **mechanical**, not a prose ritual (ADR-0016,
superseding ADR-0003). Do not hand-roll the check/create dance — call the code:

### Acquire Lock

Before ANY write to `.board/tasks.md` / `sprint-state.md`:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/board_lock.py acquire   # exit 1 = held by another; prints your holder token on success
```

`acquire` is atomic (`O_EXCL`) — two racers cannot both win. A stale lock
(older than the single staleness window below) is stolen automatically. On
success it records your holder token in `.state/lock-holder`, which
`phase_guard.py` reads to allow YOUR board writes and deny everyone else's
while the lock is live.

### Release Lock

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/board_lock.py release   # deletes the lock iff you hold it
```

### Lock Rules

- **One staleness window, defined once** in `${CLAUDE_PLUGIN_ROOT}/scripts/board_lock.py`
  (`STALE_SECONDS`, currently 120s) — quoted here, never restated. A lock
  older than that is stale and stealable.
- **The guard enforces it.** `phase_guard.py` denies board writes held by
  another live holder (PRD-003) — the lock is code now, not trust.
- **Subagents must release.** Every subagent that acquires the lock MUST release it in the same turn. No carrying locks across tool calls.
- **Read is lock-free.** Only writes require the lock. Multiple agents can read `.board/tasks.md` simultaneously.
- **Lock file is gitignored.** Add `.board/board.lock` to `.gitignore`. It's runtime state, not source.

---

## Board Update Protocol

### Who Updates When

| Event | Who Updates Board | What Changes |
|-------|------------------|--------------|
| Sprint start | /capiva:sprint | Task moved from Backlog → In Progress |
| Phase transition | Current skill | Status field updated with phase name |
| Subtask complete | /capiva:implement (subagent) | Checklist item ticked |
| Quality report ready | /capiva:test-verify | Quality metrics added to task |
| Task done | /capiva:finish | Task moved to Done, PR link added |
| Task blocked | Any skill | Task status → BLOCKED, reason added |
| Sprint end | /capiva:sprint | Summary appended, metrics updated |

### Board Write Format

Every board update MUST include:
1. The task ID being updated
2. The field being changed
3. A timestamp
4. The reason for the change

Example:
```markdown
- [x] **STH-1192** MCP Order API — PR #45 (2026-06-18)
  - Coverage: 87% | Quality gate: Pass | Linter: 0 warnings
  - Completed: 2026-06-18 15:38
```

### Board Audit Trail

Every board write operation is logged in `.board/sprint-state.md` Phase History table.
This creates a full audit trail of who changed what and when.

---

## Artifact Chain — Spec Traceability

Each phase produces artifacts. The next phase MUST verify these artifacts exist before proceeding.

```
Phase 0 (TRIAGE)    → selects task, loads spec into context
Phase 1 (GRILL)     → produces: docs/specs/TASK-ID-spec.md, docs/specs/TASK-ID-acs.json, CONTEXT.md entries, ADRs
Phase 2 (PLAN)      → produces: PLAN.md (references spec), ordered micro-tasks, docs/tech-context/TASK-ID-tech.md (when external libraries are involved)
Phase 3 (IMPLEMENT) → produces: code + tests on feature branch (follows PLAN.md)
Phase 4 (VERIFY)    → produces: docs/reports/TASK-ID-quality.md (references code), AC statuses written back to TASK-ID-acs.json
Phase 5 (FINISH)    → produces: PR (references spec + report), board update
```

### Artifact Verification

Before starting, each skill verifies its input artifacts:

| Skill | Required Artifacts | Check |
|-------|--------------------|-------|
| /capiva:grill-spec | Task spec loaded in context | sprint-state shows task selected |
| /capiva:plan | `docs/specs/TASK-ID-spec.md` + `TASK-ID-acs.json` exist | Files exist AND spec was approved (gate in sprint-state) |
| /capiva:implement | `PLAN.md` exists | File exists AND was approved (gate in sprint-state) |
| /capiva:test-verify | Feature branch with green tests | Test suite passes on branch (per blueprint §build-commands) |
| /capiva:finish | `docs/reports/TASK-ID-quality.md` exists | File exists AND quality gates pass AND every acs.json status = `pass` |
| /capiva:spec-plan | Task selected, Lane = fast | Fast-lane predicate re-verified (abort to full on failure) |
| /capiva:verify-finish | Feature branch + `TASK-ID-acs.json` | Tests green, gates at full-lane thresholds, e2e evidence |

If ANY required artifact is missing → STOP. Report what's missing. Do NOT proceed.

---

## Session Recovery

When a session starts or resumes after a crash:

1. Read `.board/sprint-state.md`
2. If Phase ≠ IDLE:
   - A task was in progress when the session ended
   - Report: "Resuming [TASK-ID] at Phase [X]. Last transition: [timestamp]"
   - Check for stale `.board/board.lock` — delete if > 60 seconds old
   - Resume from the current phase (do NOT restart from Phase 0)
3. If Phase = IDLE:
   - Clean state, ready for new sprint
