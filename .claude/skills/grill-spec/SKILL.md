---
name: grill-spec
description: Phase 1 — Adversarial spec validation with phase guard. Produces formal spec document, CONTEXT.md entries, and ADRs.
---

# Grill Spec — Phase 1

Stress-test a task specification through adversarial questioning. Produces a formal spec document, domain glossary entries, and ADRs.

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = GRILL_SPEC
3. If Phase ≠ GRILL_SPEC → **STOP**: "⛔ Phase guard failed. Current: [actual]. Required: GRILL_SPEC. Run /sprint to advance to this phase."
4. If Phase = GRILL_SPEC → proceed

## Process

### Step 1: Load Context

- Read the task spec from sprint-state (Task ID → find in board or linked doc)
- **Check for project docs** — verify `docs/CONTEXT.md` and `docs/specs/INTAKE-summary.md` exist:
  - If BOTH exist → read them as starting context (domain terms, requirements, stakeholders, open questions)
  - If MISSING → **STOP and ask**: "Project docs not found (`docs/CONTEXT.md`, `docs/specs/INTAKE-summary.md`). Please provide raw materials (transcripts, requirements, policies) so project artifacts can be generated first. Without these, grilling starts from zero context."
- Read `docs/adr/` for existing architectural decisions
- Scan relevant source files referenced in the spec

### Step 2: Adversarial Interview

Walk each branch of the decision tree. **One question at a time.**

For each question:
1. State the ambiguity or risk identified
2. Provide a **recommended answer** based on codebase exploration
3. Wait for human confirmation or correction before moving on

Priority order:
1. Scope boundaries — what is explicitly OUT of scope?
2. Domain term ambiguity — does "X" mean the same thing everywhere?
3. Edge cases the spec doesn't address
4. Integration points with existing systems
5. Performance and scaling implications
6. Error handling and failure modes
7. Security considerations

### Step 3: Explore Before Asking

Before asking a question, check if the answer exists:
- Search codebase for related patterns
- Check ADRs for prior rulings
- If the codebase answers definitively → state the finding, don't ask

### Step 4: Update CONTEXT.md

As domain terms crystallize, add to `docs/CONTEXT.md`:

```markdown
| Term | Definition | Used In Code As | Avoid |
|------|-----------|-----------------|-------|
| TradeOrder | A request to execute a buy/sell transaction | TradeOrder | Order (too generic), Trade (ambiguous) |
```

- Only add terms that were ambiguous or contested during the interview
- Cross-reference against existing entries — flag contradictions explicitly

### Step 5: Create ADRs

Create `docs/adr/NNNN-slug.md` ONLY when ALL THREE criteria are met:
1. Hard to reverse (changing requires significant rework)
2. Non-obvious (reasonable engineers would disagree)
3. Real trade-offs (not just "best practice")

**Numbering**: Continue from the highest existing ADR number in `docs/adr/` (the harness ships with 0001-0006).

**Exemplars**: Read any of `docs/adr/0001-*.md` through `docs/adr/0006-*.md` as gold-standard examples. Your ADRs must match this depth.

ADR format:
```markdown
# ADR-NNNN: Title

## Status
Accepted | Superseded by ADR-XXXX | Deprecated

## Context

[The problem or decision point. 2-3 paragraphs minimum. Explain:
- What triggered this decision (a requirement, a risk, a conflict)
- What constraints exist (performance, compatibility, team skill, enterprise policy)
- Why the status quo is insufficient]

### Options Considered

**Option A: [Name]**
- [How it works — 1-2 sentences]
- Pro: [specific benefit]
- Pro: [specific benefit]
- Con: [specific drawback]
- Con: [specific drawback]

**Option B: [Name]**
- [How it works]
- Pro: [...]
- Con: [...]

**Option C: [Name]**
- [How it works]
- Pro: [...]
- Con: [...]

[Minimum 2 options. If there's only one viable option, explain why the alternatives
were eliminated before this decision point. "We had no choice" is not a decision —
it's a constraint that should be in Context.]

## Decision

**[Option X] — [one-sentence summary].**

[1-2 paragraphs explaining WHY this option. Not just "we chose X" but "we chose X
because [tradeoff]. Option Y was rejected because [reason]. Option Z would have
required [cost we weren't willing to pay]."

If the decision was close between two options, say so — it helps future reviewers
understand when this ADR might need revisiting.]

## Consequences

[What becomes easier, harder, or different as a result of this decision.
Be specific — not "this makes things simpler" but "repository implementations
now follow the IAsyncLifetime pattern, which adds 10 lines of boilerplate per
test class but eliminates container lifecycle bugs."]

- [Positive consequence]
- [Positive consequence]
- [Negative consequence or trade-off accepted]
- [Future consideration — when might this decision need revisiting?]
```

### ADR Anti-Patterns (do NOT produce these)

- **Missing options**: "We decided to use X" without explaining what else was considered. If there were no alternatives, it's not a decision — it's a constraint (put it in Context instead).
- **Vague consequences**: "This is better." Better HOW? For whom? At what cost?
- **Premature ADR**: Using dependency injection is not ADR-worthy (it's standard practice). Choosing BETWEEN two DI containers IS.
- **One-paragraph ADR**: If the entire ADR fits in 5 lines, either the decision wasn't significant enough (don't write it) or you're not thinking deeply enough (expand it).

### Step 6: Write Formal Spec Document

Create `docs/specs/TASK-ID-spec.md` with this structure:

```markdown
# Spec: [Task Title]

## Task Reference
- ID: [TASK-ID]
- Priority: [P0-P4]
- Source: [Jira link or board reference]

## Summary
[2-3 sentences describing what this task delivers]

## Acceptance Criteria
1. [Measurable criterion]
2. [Measurable criterion]
...

## Clarifications
[Numbered Q&A from the adversarial interview]

## Domain Terms
[Terms added to CONTEXT.md during this spec]

## ADRs Created
[List of ADR files created, or "None"]

## Out of Scope
[Explicitly listed items that are NOT part of this task]

## Open Questions
[Any remaining ambiguities — these BLOCK progression to /plan]
```

### Step 7: Present for Approval

Present the spec document summary to the human:
- Acceptance criteria (numbered)
- Key clarifications made
- Any new ADRs
- Open questions (if any — these block planning)

Then state:
```
Spec document written to docs/specs/[TASK-ID]-spec.md
CONTEXT.md updated with [N] new terms.
[M] ADRs created.

🧑 Awaiting spec approval to proceed to /plan phase.
```

## Phase Transition (MANDATORY)

**After human approves the spec:**

1. Update `.board/sprint-state.md`:
   - Spec Approved: Yes
   - Register artifact: `docs/specs/TASK-ID-spec.md`
2. Add Phase History row: `| [now] | [task] | GRILL_SPEC | PLAN | spec-approved | [summary] |`
3. **→ Return control to /sprint** which will invoke /plan next.

If invoked standalone (not from /sprint):
- Update sprint-state as above
- State: "Spec approved. Next step: invoke /plan to decompose into micro-tasks."

## Output Quality Gate

Before presenting the spec for approval, validate against `.claude/rules/artifact-standards.md` "Artifact 1: Spec Document":

- [ ] Summary is 3-5 sentences explaining business value (not a rewording of the title)
- [ ] Every AC uses GIVEN/WHEN/THEN with specific values, inputs, and expected outputs
- [ ] Domain Terms table has entries with Definition, Used In Code As, and Avoid columns
- [ ] Scope has BOTH In Scope and Out of Scope sections with specific bullet points
- [ ] Technical Context includes Integration Points, Data Model, and Error Scenarios
- [ ] Error Scenarios have trigger condition, expected behavior, and user/caller impact
- [ ] Clarifications are numbered Q&A with rationale and implementation impact
- [ ] No placeholders ("[TBD]", "as discussed", "various", "etc.") anywhere
- [ ] Every entity is named specifically (class names, table names, endpoint paths — not "the service")
- [ ] If ADRs were created: each has Context, Options Considered (2+ options with pros/cons), Decision (with rationale), and Consequences
- [ ] If ADRs were created: they match the depth of `docs/adr/0001-*.md` through `0006-*.md` (the harness exemplars)

If ANY check fails → iterate on the spec before presenting. Do NOT present a below-standard spec.

## Rules

- **One question at a time.** Never dump a list.
- **Always provide a recommended answer.** Human confirms, corrects, or expands.
- **Explore before asking.** Don't waste human time on questions the codebase answers.
- **ADRs are rare.** Most specs produce zero.
- **CONTEXT.md is cumulative.** Never remove entries. Only add or amend.
- **Flag contradictions.** New answers vs existing glossary/ADR = explicit callout.
- **No code.** This skill produces specs and documentation only.
- **Formal spec document is mandatory.** The output is `docs/specs/TASK-ID-spec.md`, not just conversation.
- **Open questions block progression.** If there are unresolved ambiguities, /plan CANNOT start.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.
