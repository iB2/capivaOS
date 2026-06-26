# ADR-0006: File-Existence Gating Over Conversation-State Gating

## Status

Accepted

## Context

The pipeline needs to verify that each phase's output is complete before the next phase starts. The question is HOW to verify — what counts as "the spec is done" or "the plan is ready"?

### Options Considered

**Option A: Conversation-state gating (trust the agent's claim)**
- The agent says "spec is done, moving to planning" → pipeline proceeds
- Pro: Zero overhead
- Con: The agent can claim the spec is done without actually writing one — especially under context pressure
- Con: After compaction, the claim is lost. A fresh agent can't verify "was the spec done?" from conversation history
- Con: Unverifiable — there's no way to audit whether the spec actually existed when the claim was made

**Option B: Sprint-state flag gating (check a field in sprint-state.md)**
- Sprint-state has `Spec Approved: Yes/No`. Check this field before proceeding.
- Pro: Persistent — survives compaction and session boundaries
- Pro: Auditable — the field change is logged in Phase History
- Con: The field can be set without the artifact actually existing. An agent (or human error) could set `Spec Approved: Yes` without a spec file on disk
- Con: One level of indirection — you're checking a flag ABOUT the artifact, not the artifact itself

**Option C: File-existence gating (verify the artifact file exists on disk)**
- Before /plan runs, it checks: does `docs/specs/TASK-ID-spec.md` exist as a file? If not, refuse to proceed.
- Pro: Binary and unfalsifiable — the file either exists or it doesn't
- Pro: Survives everything — crashes, compaction, session boundaries, agent confusion
- Pro: Self-documenting — the file IS the proof of completion
- Pro: Composable — combine with sprint-state flags for defense in depth (file exists AND flag set)
- Con: A file can exist but be empty or low-quality (mitigated by input quality validation in each skill)
- Con: Slightly more I/O per phase transition (file existence check)

## Decision

**File-existence gating (Option C), combined with sprint-state flags for defense in depth.**

Each phase gate checks BOTH:
1. The artifact file exists on disk (binary check)
2. The corresponding sprint-state flag is set (semantic check)

If either fails, the skill refuses to proceed.

### Artifact chain

```
/plan requires:     docs/specs/TASK-ID-spec.md exists + Spec Approved = Yes
/implement requires: PLAN.md exists + docs/tech-context/TASK-ID-tech.md exists + Plan Approved = Yes
/test-verify requires: feature branch exists + dotnet test passes
/finish requires:   docs/reports/TASK-ID-quality.md exists + Quality Gate = PASS
```

### Quality validation is separate

File existence proves the artifact was created. It does NOT prove the artifact is good. Quality validation is handled by each skill's "Input Quality Validation" section, which checks the artifact's CONTENT against the standards in `artifact-standards.md`. These are two separate concerns:

- **Gating** = does the artifact exist? (binary, fast, unfalsifiable)
- **Validation** = is the artifact good enough? (qualitative, requires reading content)

Both happen at the start of each skill, but gating happens first (no point validating a file that doesn't exist).

## Consequences

- Each phase transition has a file-existence check (~1-2 seconds overhead)
- Artifacts are the pipeline's "proof of work" — you can audit the pipeline by listing files in `docs/specs/`, `docs/tech-context/`, `docs/reports/`
- The artifact chain creates a natural audit trail: spec → tech-context → PLAN.md → feature branch → quality report → PR
- Even if the state machine's sprint-state file is corrupted, the artifact files prove what work was actually done
- Empty or low-quality artifacts are caught by input quality validation, not by gating — these are defense layers, not a single mechanism
