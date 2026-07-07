# ADR-0004: Token-Bounded Sprints Over Time-Bounded

## Status

Accepted

## Context

The sprint loop needs a termination condition. Without one, the agent either runs forever (until the human stops it) or runs for a fixed time period. Neither is ideal — the actual limiting factor in Claude Code sessions is context window consumption, not wall-clock time.

### Options Considered

**Option A: Time-bounded sprints (e.g., 30 minutes, 1 hour)**
- Pro: Predictable session length, easy to explain
- Con: Time doesn't correlate with context consumption. A complex IMPLEMENT phase might fill 100K tokens in 15 minutes; a simple GRILL_SPEC might use 20K in 30 minutes
- Con: No mechanism to detect quality degradation — the sprint runs for its full duration even if output quality has dropped
- Con: Arbitrary — why 30 minutes? Why not 20 or 45?

**Option B: Task-count bounded (e.g., 3 tasks per sprint)**
- Pro: Predictable workload
- Con: Tasks vary wildly in complexity — 3 simple tasks might use 50K tokens, 1 complex task might use 200K
- Con: Doesn't prevent context rot within a single complex task

**Option C: Token-bounded with compaction counter as proxy**
- Budget ceiling: 200K tokens (hard limit)
- Signal: auto-compaction count (0 = healthy, 1 = caution, 2 = critical)
- Action: decision matrix based on compaction count × next phase weight
- Pro: Directly measures the actual limiting resource
- Pro: Quality-aware — triggers handover before output degrades, not after
- Pro: Adapts to task complexity — simple tasks run more phases, complex tasks trigger handover earlier
- Con: No exact token counter in Claude Code — we use auto-compaction as a proxy
- Con: Compaction is a lagging indicator — by the time it triggers, context is already pressured

**Option D: Token-bounded with explicit counting**
- Count tokens consumed by each tool call and conversation turn
- Pro: Precise measurement
- Con: Claude Code doesn't expose a token counter API
- Con: Estimating tokens from text is unreliable (varies by encoding, language, code density)
- Con: Would require injecting counting logic into every skill

## Decision

**Token-bounded with compaction counter as proxy (Option C).**

### The 200K ceiling

This number is empirical, not theoretical. Observations:
- Auto-compaction typically triggers around 180-200K tokens of accumulated context
- After 1 auto-compaction, the agent occasionally forgets earlier decisions but can recover with prompting
- After 2 auto-compactions, quality degradation is consistent and observable: vaguer output, contradicted earlier decisions, missed edge cases, repeated questions
- 200K is therefore the practical ceiling before "quality degradation becomes unacceptable"

### Decision matrix

```
At phase boundary:
  2+ compactions → HANDOVER (non-negotiable)
  1 compaction + next phase is IMPLEMENT or TEST_VERIFY → HANDOVER
  1 compaction + next phase is lighter → /compact with focus, continue
  0 compactions → continue
```

The asymmetry between heavy phases (IMPLEMENT ~60-100K, TEST_VERIFY ~40-70K) and light phases (FINISH ~10-20K) is intentional. Starting a heavy phase with only partial context budget remaining is worse than handing over with a clean 200K for the next session.

## Consequences

- Sprints have no timebox — they run until the board is empty or context is exhausted
- Multi-session execution is expected for complex tasks, not a failure mode
- The `/handover` skill exists specifically to enable zero-loss session transitions
- Context hygiene rules (surgical reads, subagents for exploration, /clear between tasks) extend the budget within each session
- The decision matrix is conservative — it prefers a clean handover over pushing through with degraded quality

---

*Amended 2026-07 (ADR-0012 / HARN-009): heuristics re-benchmarked against current Claude Code context management — 200K ceiling confirmed; compaction counting demoted to fallback behind live context usage and observed quality degradation; see context-management.md "2026-07 Re-Benchmark".*
