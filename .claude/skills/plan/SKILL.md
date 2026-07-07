---
name: plan
description: Phase 2 — Decompose approved spec into micro-tasks with phase guard. Produces PLAN.md with exact file paths, code snippets, and verification steps.
---

# Plan — Phase 2

Decompose an approved spec into implementable micro-tasks. Each task is self-contained enough for a subagent with zero prior context to execute.

## Architecture Enforcement — Arch Role

Before decomposing into tasks, the /plan skill MUST validate architectural compliance using the Architect role (`.claude/agents/roles/arch.md`).

### Pre-Decomposition Architecture Check

1. **Read** the active blueprint's `reference.md` for architecture constraints (§architecture section)
2. **Validate** that every new file in the plan maps to the correct architectural layer per the blueprint
3. **Verify** dependency direction as defined in the blueprint's §architecture
4. **Check** that enterprise patterns from the blueprint's §enterprise-patterns are used
5. **Flag** any planned code that would deviate from the blueprint — create a Deviation Record task

If any deviation is identified:
1. Create a dedicated task in PLAN.md: "Create Deviation Record: DEV-NNN-[slug]"
2. The task must reference `templates/deviation-record.md` as the template
3. The task produces: `docs/deviations/DEV-NNN-[slug].md`
4. This task is MANDATORY — it cannot be deferred or skipped

### Arch Role Spawn (Conditional)

IF any task in the plan creates new files (CREATE operation):
  → Arch role spawn is **MANDATORY**
  → Arch validates: layer placement, dependency direction, pattern compliance
  → Output: layer assignment table, ADRs (if any), deviation records (if any)

IF all tasks only modify existing files (MODIFY operation):
  → Arch role spawn is **OPTIONAL**
  → /plan orchestrator performs lightweight check: are modifications in the correct layer?

When spawning the arch role:

```
Agent(
  role: .claude/agents/roles/arch.md
  input: spec + existing architecture + CONTEXT.md + blueprint reference.md
  output: ADRs + layer assignments + interface definitions
)
```

The arch role produces:
- ADRs for significant decisions → `docs/adr/`
- Layer placement table (every new class → correct project per blueprint §architecture)
- Interface definitions (precise enough for dev role implementation)
- Deviation Records for any blueprint non-compliance → `docs/deviations/`

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = PLAN
3. Verify Spec Approved = Yes
4. Verify `docs/specs/TASK-ID-spec.md` exists (check Artifacts Registry)
5. Verify `docs/specs/TASK-ID-acs.json` exists and parses (the verification contract — see ADR-0009)
6. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /grill-spec first."
6. If ALL checks pass → proceed

## Process

### Step 1: Load Inputs

- Read `docs/specs/TASK-ID-spec.md` (the approved spec — NOT just the board task)
- Read `docs/CONTEXT.md` for domain terms
- Read `docs/adr/` for architectural constraints
- Read the active blueprint's `reference.md` for stack-specific patterns
- Scan the codebase for existing patterns to follow

### Step 1.5: Documentation Discovery (Context7)

Before designing the approach, verify that your knowledge of the libraries involved is current.
Training data may be stale — APIs change, packages get deprecated, new patterns emerge.

1. **Identify libraries this task will use:**
   - Scan the project's dependency files (per blueprint §build-commands — e.g., `.csproj`, `requirements.txt`, `package.json`)
   - Cross-reference with the spec's Technical Context and Integration Points
   - Include test libraries if the task involves new test patterns

2. **Query Context7 for each relevant library:**
   ```
   For each library:
     1. resolve-library-id("[library name]")  → get the Context7 library ID
     2. query-docs(libraryId, "[specific API or pattern needed]") → get current docs
   ```
   
   **Focus queries on what THIS task needs** — don't dump entire library docs.

3. **Write tech context file:**
   Save to `docs/tech-context/TASK-ID-tech.md`:
   ```markdown
   # Tech Context: [Task Title]
   
   Generated via Context7 MCP — current library documentation for this task.
   
   ## Libraries Referenced
   
   | Library | Version (from dependency file) | Context7 ID | Queries |
   |---------|-------------------------------|-------------|---------|
   | [name]  | [version]                     | [id]        | [topics queried] |
   
   ## [Library Name] — [Specific Topic]
   
   [Relevant API docs, patterns, gotchas from Context7 output.
   Include code examples from the CURRENT docs, not training data.]
   ```

4. **Feed into subsequent steps:**
   - The approach brainstorm (Step 2) references verified API patterns
   - The micro-task code snippets (Step 3) use CURRENT syntax from the tech context
   - PLAN.md references this file so subagents can read it

**If Context7 is unavailable or returns nothing for a library:**
- Log it: "Context7 had no docs for [library]. Using training data — verify manually."
- Do NOT silently proceed with potentially stale knowledge.
- Flag it in the plan's Risk Assessment section.

**Skip this step ONLY if the task is purely domain logic with no library-specific APIs** (rare).

### Step 2: Brainstorm Approach

Present the implementation approach before decomposing:
- If multiple viable paths exist: present each with trade-offs
- Reference relevant ADRs and verified API patterns from Step 1.5
- Identify the riskiest part
- Note any Context7 findings that affect the approach (deprecated APIs, version constraints)
- **Wait for human approval of approach before decomposing**

### Step 3: Decompose into Micro-Tasks

Break the approved approach into ordered tasks. Each task contains:

```markdown
## Task N: [One-sentence description]

**Files:** `[path per blueprint §architecture]` (create | modify)
**Layer:** [Layer name per blueprint §architecture]

**Code:**
```[language]
// Enough code for a zero-context agent to implement
// Include method signatures, class structure, key logic
// Follow patterns from blueprint reference.md §coding-standards
```

**Test:**
```[language]
// The failing test to write FIRST (TDD red phase)
// Follow test conventions from blueprint reference.md §test-stack
```

**Verify:**
```bash
[verification command from blueprint reference.md §build-commands]
```

**Depends on:** Task M (if any)
**Parallelizable:** Yes | No (and why)
**Estimate:** 3 min
**Risk:** Low | Medium | High — [reason if Medium/High]
```

### Step 4: Dependency Ordering

- Order by dependency (no circular references)
- Mark tasks that can run in parallel
- Infrastructure (models, interfaces) before logic
- Test setup before implementation (TDD flow)
- Group parallelizable tasks explicitly

### Step 5: Write PLAN.md

Write the complete plan to `PLAN.md` in the working directory:

```markdown
# Plan: [Task Title]

## Spec Reference
docs/specs/[TASK-ID]-spec.md

## Tech Context
docs/tech-context/[TASK-ID]-tech.md — [libraries queried, any notable findings]

## Architecture
- **Blueprint**: [active blueprint name]
- **Dependency direction verified**: [per blueprint §architecture]
- **Enterprise patterns used**: [per blueprint §enterprise-patterns]
- **Deviations**: [None | list with Deviation Record references]
- **ADRs created**: [None | list]

## Layer Assignments

| File | Layer | Project | Justification |
|------|-------|---------|---------------|
| [file] | [layer] | [project path] | [reason per blueprint §architecture] |

## Approach
[Approved approach from Step 2, informed by verified library docs from Step 1.5]

## Task Summary
- Total tasks: [N]
- Parallelizable groups: [list]
- Estimated total: [M] minutes
- Highest risk: Task [X] — [reason]

## Tasks

### Task 1: [title]
[full task definition from Step 3]

### Task 2: [title]
...

## Dependency Graph
```
Task 1 (interfaces)
├── Task 2 (service impl) ── depends on Task 1
├── Task 3 (repository)   ── depends on Task 1
│   └── Task 4 (tests)    ── depends on Task 3
└── Task 5 (integration)  ── depends on Task 2 + Task 3
```

## Quality Checklist
- [ ] All existing tests still pass after each task
- [ ] Every new method has a corresponding test
- [ ] CONTEXT.md terms used consistently in code
- [ ] No ADR violations
- [ ] No new compiler/linter warnings
```

### Step 6: Present for Approval

Present the plan summary:
- Total tasks and estimated time
- Parallelizable groups
- Riskiest tasks flagged
- Dependency graph

Then state:
```
Plan written to PLAN.md ([N] tasks, ~[M] minutes estimated).
Dependency graph shows [X] parallel groups.
Riskiest task: [description].

🧑 Awaiting plan approval to proceed to /implement phase.
```

Human can: approve, reorder, cut, expand, or reject.

## Phase Transition (MANDATORY)

**After human approves the plan:**

1. Update `.board/sprint-state.md`:
   - Plan Approved: Yes
   - Register artifacts: PLAN.md, docs/tech-context/TASK-ID-tech.md
2. Add Phase History row: `| [now] | [task] | PLAN | IMPLEMENT | plan-approved | [N] tasks, ~[M] min |`
3. **→ Return control to /sprint** which will invoke /implement next.

If invoked standalone:
- Update sprint-state as above
- State: "Plan approved. Next step: invoke /implement to begin subagent-driven development."

## Input Quality Validation

Before starting decomposition, validate the spec against `.claude/rules/artifact-standards.md` "Artifact 1":

- [ ] Spec file exists at `docs/specs/TASK-ID-spec.md`
- [ ] `docs/specs/TASK-ID-acs.json` exists, matches the spec's AC list one-to-one, and every status is `pending`
- [ ] AC section has numbered items with GIVEN/WHEN/THEN structure (not vague one-liners)
- [ ] Domain Terms table has entries (at least the task's core terms)
- [ ] Scope section has both In Scope and Out of Scope
- [ ] No "Open Questions" section with unresolved items

If ANY check fails → STOP. Report: "Spec quality below standard: [specific issue]. Return to /grill-spec."

## Output Quality Gate

Before presenting the plan for approval, validate against `.claude/rules/artifact-standards.md` "Artifact 2: PLAN.md":

- [ ] Every task has Purpose, Files, Context, Implementation, Test, and Verify sections
- [ ] File paths are absolute from project root (not vague "in the domain folder")
- [ ] Context section shows existing code the subagent needs to understand (not just "see codebase")
- [ ] Implementation section shows complete code with proper structure per blueprint
- [ ] Test section shows a complete failing test skeleton (not "write a test")
- [ ] Verify section has an exact test filter command per blueprint §build-commands (not just "run tests")
- [ ] Dependency graph is present and consistent with task ordering
- [ ] Risk assessment identifies highest risk task with specific concern
- [ ] Rejected alternatives section explains what was NOT chosen and why
- [ ] Layer Assignment table present: every new file mapped to correct layer per blueprint §architecture
- [ ] Dependency direction verified per blueprint §architecture
- [ ] Enterprise patterns used where applicable per blueprint §enterprise-patterns
- [ ] Deviation Records created for any blueprint non-compliance
- [ ] Tech Context reference points to existing `docs/tech-context/TASK-ID-tech.md`
- [ ] Code snippets use API patterns verified by Context7 (not stale training data)

If ANY check fails → iterate on the plan before presenting.

## Rules

- **2-5 minutes per task.** If larger, split it. If smaller, merge with adjacent.
- **Dependency order.** No circular or forward references.
- **Every task has a verification step.** "It compiles" is not verification — must confirm behavior.
- **Code snippets must be sufficient.** Zero-context agent must be able to implement from the task alone.
- **File paths must be exact.** Not "somewhere in services" — full path.
- **TDD ordering.** Test task comes before (or is embedded within) implementation task.
- **PLAN.md is self-contained.** PLAN.md + CONTEXT.md + tech-context + blueprint reference.md = everything a subagent needs.
- **No code.** This skill produces the plan, never implementation code.
- **Spec is input, not repeated.** Reference the spec file, don't paste it into the plan.
- **Quality floor is non-negotiable.** See artifact-standards.md for the gold standard. Your output must match or exceed it.
