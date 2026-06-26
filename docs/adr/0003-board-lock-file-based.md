# ADR-0003: File-Based Board Lock Over Git-Based Alternatives

## Status

Accepted

## Context

During the IMPLEMENT phase, the pipeline orchestrator and multiple subagents may need to update `.board/tasks.md` concurrently — the orchestrator tracks progress, subagents tick subtask checkboxes. Without mutual exclusion, concurrent writes corrupt the file (one agent's changes silently overwrite another's).

### Options Considered

**Option A: No locking (last write wins)**
- Pro: Zero complexity
- Con: Data loss is guaranteed when 2+ agents write simultaneously
- Con: Agent may read stale board state and make decisions on outdated information

**Option B: Git branch-based locking**
- Each agent works on a separate branch of tasks.md, merges back
- Pro: Git handles conflict resolution
- Con: Massive overhead for a file that changes every few minutes — branch creation, merge, potential conflict resolution, push
- Con: Subagents don't have git access in isolated worktrees
- Con: Merge conflicts on a markdown task board are absurd — the cure is worse than the disease

**Option C: Database/Redis-based locking**
- Store board state in a database, use proper transactions
- Pro: ACID guarantees
- Con: Requires external infrastructure (database or Redis instance) for what is a single markdown file
- Con: Breaks the "everything is a file" principle — board state would live in two places
- Con: Adds a dependency that most projects don't have locally

**Option D: File-based lock with stale detection**
- `.board/board.lock` file with holder, timestamp, and operation
- Acquire before write, release after write, stale detection at 60 seconds
- Pro: Simple, human-readable, zero dependencies
- Pro: Stale detection handles crashes (agent dies without releasing → lock expires in 60s)
- Pro: Gitignored — no lock file in version control
- Pro: Consistent with "everything is a file" principle
- Con: Not atomic — theoretically two agents could check simultaneously and both proceed (unlikely in practice given agent execution model)
- Con: Clock-dependent — stale detection requires reasonable system clock

## Decision

**File-based lock with stale detection (Option D).**

Lock protocol:
1. Check if `.board/board.lock` exists
2. If exists and < 60s old → wait 5s, retry (max 3 retries)
3. If exists and > 60s old → stale, delete and re-acquire
4. If not exists → create lock file with holder/timestamp/operation
5. Read board fresh, apply changes, write board
6. Delete lock file

### Why the race condition is acceptable

The theoretical race (two agents check simultaneously, both see no lock, both proceed) is practically impossible in Claude Code's execution model: tool calls are serialized within a session, and subagents execute in separate processes with their own tool call serialization. The window for a race is microseconds between "check no lock" and "create lock file" — far smaller than the agent's response latency.

## Consequences

- Board writes have ~0.5-2 seconds overhead (lock check, acquire, release)
- Stale locks auto-expire after 60 seconds — crashed agents don't permanently block the board
- Main context can force-release after 30 seconds (main always wins over subagents)
- Lock file is gitignored — never committed to version control
- Subagents are restricted to updating their own subtask checkboxes — only the orchestrator can move tasks between sections
