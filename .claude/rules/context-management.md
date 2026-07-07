# Context Management — Token-Aware Pipeline Execution

## The Problem

Claude Code has a finite context window. Long sprint sessions degrade output quality
as context fills. Auto-compaction helps but loses nuance. After 2 auto-compactions,
output quality drops measurably.

The harness MUST manage context proactively — not react to overflow, but prevent it.

## Context Budget Model

### Budget Ceiling: 200K Tokens (Hard Limit)

The pipeline MUST NOT allow context to exceed ~200K tokens. This is not a soft target —
it's the maximum before quality degradation becomes unacceptable.

**Practical token estimation** (Claude Code doesn't expose a counter, so we estimate):

| Operation | Approximate Tokens |
|-----------|-------------------|
| File read (100 lines) | ~2,000 |
| File read (500 lines) | ~10,000 |
| Subagent spawn + result | ~5,000-15,000 |
| Code generation (100 lines) | ~3,000 |
| Conversation turn (question + answer) | ~1,000-3,000 |
| Skill invocation + execution | ~10,000-30,000 |
| Full test suite output | ~5,000-15,000 |
| Static analysis output (linter + quality gate) | ~5,000-10,000 |

### Phase Budget Estimates

| Phase | Typical Budget | Heavy Budget | Notes |
|-------|---------------|--------------|-------|
| TRIAGE | ~5K | ~10K | Board read + spec load |
| GRILL_SPEC | ~30K | ~50K | Interview has many turns |
| PLAN | ~20K | ~35K | Codebase scanning + decomposition |
| IMPLEMENT | ~60K | ~100K | Multiple subagents + reviews |
| TEST_VERIFY | ~30K | ~50K | Two agents + static analysis |
| FINISH | ~10K | ~20K | PR creation + board update |
| **Total (full lane)** | **~165K** | **~285K** | Heavy exceeds single session |
| SPEC_PLAN (fast lane) | ~15K | ~25K | Combined spec-lite + plan, targeted interview |
| VERIFY_FINISH (fast lane) | ~20K | ~35K | No two-agent generation; compact report + PR |
| **Total (fast lane)** | **~75K** | **~135K** | TRIAGE + SPEC_PLAN + IMPLEMENT + VERIFY_FINISH |

**Key insight**: A complex task's full pipeline may NOT fit in one session.
The harness must handle multi-session execution gracefully.

---

## Context Tracking — Hook-Enforced

### Automated State Persistence (hooks)

Context management is **enforced mechanically** via Claude Code hooks, not by agent self-monitoring:

| Hook | Trigger | Action |
|------|---------|--------|
| `PreCompact` | Before every auto-compaction | Saves sprint state, board snapshot, git state to `.state/session-state.md` |
| `SessionStart:compact` | After compaction completes | Restores saved state as `additionalContext`, deletes the file |
| `Stop` | On session end | Saves final state (skips if manual `/handover` doc exists) |

**Configured in**: `.claude/settings.json` → hooks registered there fire automatically.
**Script**: `.claude/hooks/context-persistence.py` (always exits 0, never blocks).

This means: the agent does NOT need to "track compaction count" — the hooks save and restore state automatically. The agent's job is to follow the phase boundary rules below.

### Phase Boundary Checkpoints

**At EVERY phase transition**, before starting the next phase:

1. Estimate remaining budget based on phases remaining and their token cost
2. If next phase is token-heavy (IMPLEMENT, TEST_VERIFY) and context feels pressured → HANDOVER
3. If output quality shows signs of degradation (forgotten decisions, vague output) → HANDOVER

### Decision Matrix

```
At phase boundary:
  IF context feels degraded (repeating questions, vague output) → HANDOVER (non-negotiable)
  IF next phase is IMPLEMENT or TEST_VERIFY and session has been long → HANDOVER
  IF next phase is PLAN, GRILL_SPEC, or FINISH → /compact with focus, continue
  IF session is fresh → continue
```

**Note**: The PreCompact hook saves state BEFORE compaction fires, so even if the agent doesn't notice degradation, state is preserved. The SessionStart:compact hook restores it, so post-compaction the agent knows what was happening.

---

## Proactive Context Hygiene

### Within-Phase Hygiene

- **Read surgically.** Use offset/limit for files > 100 lines. Never read "just in case."
- **Subagents for exploration.** Research and multi-file investigation go to subagents. Main context is for orchestration and synthesis.
- **Don't re-read artifacts.** Once a spec or plan is written to disk, reference it by path — don't paste it back into conversation.
- **Trim tool output.** If a test suite produces 500 lines, extract the relevant failures — don't load the full output.

### Between-Phase Compaction

At each phase transition (even without compaction pressure), proactively compact:

```
/compact Focus: [current task ID], Phase [N→N+1].
Preserve: sprint-state fields, modified files list, quality gate status,
current branch name, and artifact paths.
Discard: exploration output, rejected alternatives, intermediate build logs.
```

### Mandatory /clear

- Between tasks (after FINISH → before next TRIAGE): always /clear
- After a handover is received (fresh agent starts clean)

---

## Handover Protocol

When context budget is exhausted or approaching the limit, the agent MUST hand over
instead of continuing with degraded quality.

### When to Trigger Handover

1. **Auto-compaction count >= 2** — mandatory at next phase boundary
2. **Before entering IMPLEMENT with a large plan** (> 8 micro-tasks) — if any compactions have occurred
3. **Before entering TEST_VERIFY** — if IMPLEMENT consumed heavy context
4. **Agent detects quality degradation** — forgetting earlier decisions, repeating questions, inconsistent output
5. **Human requests it** — "hand over", "save and continue later", "wrap up"

### What Handover Produces

The `/handover` skill produces a self-contained handover document that a fresh agent
can read to resume work with zero loss of context. See `.claude/skills/handover/SKILL.md`.

### What Handover Updates

1. `.board/sprint-state.md` — current phase, all fields current
2. `.board/tasks.md` — progress notes on the active task
3. `docs/handover/TASK-ID-handover.md` — the handover document
4. All in-progress artifacts saved to disk (not just in conversation)

---

## Multi-Session Execution

For complex tasks that span multiple sessions:

### Session 1: TRIAGE → GRILL_SPEC → PLAN
- Budget: ~55K typical
- Natural handover point: after plan approval (PLAN.md is on disk)
- Fresh agent reads: sprint-state + spec + PLAN.md

### Session 2: IMPLEMENT
- Budget: ~60-100K (most expensive phase)
- Natural handover points: between parallel task groups
- If plan has > 8 tasks: handover mid-IMPLEMENT is expected
- Fresh agent reads: sprint-state + PLAN.md + branch state + completed tasks

### Session 3: TEST_VERIFY → FINISH
- Budget: ~50K typical
- Natural handover point: after quality report (before /finish)
- Fresh agent reads: sprint-state + quality report + branch

### Recovery from Unclean Exit

If a session ends without handover (crash, timeout, rate limit):

1. Fresh agent reads `.board/sprint-state.md` → knows current phase
2. Reads `.board/tasks.md` → knows active task and progress
3. Checks for handover document in `docs/handover/`
4. If no handover doc: reads the current phase's input artifacts to reconstruct context
5. Resumes from the current phase (may need to re-do partial work within the phase)

---

## Anti-Patterns

1. **Reading the entire codebase "for context."** Never. Read only what the current task requires.
2. **Keeping grill-spec conversation in context during IMPLEMENT.** The spec is on disk. Read it there.
3. **Loading all test output into main context.** Subagents run tests. Main context gets the summary.
4. **Pushing through after 2 compactions.** Quality WILL degrade. Handover is not optional.
5. **Starting IMPLEMENT without checking context budget.** IMPLEMENT is the most expensive phase. Plan for it.
6. **Ignoring the handover protocol.** A clean handover takes 2 minutes. A lost context costs hours.
