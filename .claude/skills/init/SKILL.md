---
name: init
description: Phase 0 — First-time project setup. Validates project docs exist, detects stack, selects blueprint, configures harness. Must run before /sprint.
---

# Init — Phase 0: Project Setup

First-time harness configuration for a new project. This skill is the entry point — it runs once, before `/sprint` ever executes.

## Prerequisites

The harness directories must already be copied into the project:
- `.claude/` (skills, rules, blueprints, agents)
- `.board/` (task board, sprint state)
- `docs/` (context, ADRs, specs)
- `templates/` (deviation records, solution docs)

If these don't exist, tell the user:
```
Harness directories not found. Copy them first:

  git clone https://github.com/iB2/capivaOS.git .harness-tmp
  cp -r .harness-tmp/.claude .claude
  cp -r .harness-tmp/.board .board
  cp -r .harness-tmp/docs docs
  cp -r .harness-tmp/templates templates
  rm -rf .harness-tmp

Then run /init again.
```

## Process

### Step 1: Check Project Documentation (GATE)

**This step is a hard gate. Do not proceed past it without docs.**

Check for these two files:

1. `docs/CONTEXT.md` — must have **at least one glossary entry or domain rule** (not just the empty template)
2. `docs/specs/INTAKE-summary.md` — must exist with project scope, stakeholders, and key requirements

**How to check**:
- Read `docs/CONTEXT.md`. If it only contains the empty table headers (no actual terms), it counts as missing.
- Check if `docs/specs/INTAKE-summary.md` exists and has content.

**If EITHER is missing or empty → STOP.** Present this message:

```
⛔ Project documentation required before harness setup.

The harness needs project context to configure properly. Without it,
every downstream phase (spec grilling, planning, implementation)
starts from zero — leading to wrong assumptions and rework.

Missing:
- [ ] docs/CONTEXT.md — Domain glossary, acronyms, business rules
- [ ] docs/specs/INTAKE-summary.md — Project scope, stakeholders, requirements

What to do:
1. Gather your raw materials (transcripts, requirements docs, emails, specs)
2. Draft the documents from those materials — templates/intake-summary.md
   defines the INTAKE format; ask Claude to generate first drafts if useful
3. Run /init again once the docs are populated

Template structure for INTAKE-summary.md:

  # Project Intake Summary
  ## Project Name
  ## Stakeholders (who, role, decision authority)
  ## Problem Statement (what problem this solves)
  ## Scope (in scope / out of scope)
  ## Key Requirements (numbered, measurable)
  ## Constraints (timeline, budget, compliance, tech)
  ## Open Questions (unresolved items that need answers)

Template structure for CONTEXT.md:

  See docs/CONTEXT.md — fill in the Glossary, Acronyms, and Domain Rules.
```

**Do NOT proceed to Step 2 until both docs have real content.**

### Step 2: Read Project Documentation

Now that docs exist, read them to understand the project:

- Read `docs/CONTEXT.md` — extract domain terms, acronyms, business rules
- Read `docs/specs/INTAKE-summary.md` — extract project name, scope, stakeholders, requirements, constraints
- Read `docs/adr/` — check for any existing architectural decisions

Note the project name, domain, and any technology constraints mentioned.

### Step 3: Detect Stack

Scan the project root for technology markers:

| Marker | Stack |
|--------|-------|
| `*.csproj` or `*.sln` | .NET → `dotnet-hexagonal` |
| `package.json` with `next` dependency | Next.js → `nextjs-typescript` |
| `package.json` without `next` | Node.js (suggest `nextjs-typescript` or flag as unsupported) |
| `requirements.txt` or `pyproject.toml` with `fastapi` | Python FastAPI → `python-fastapi` |
| `requirements.txt` or `pyproject.toml` without `fastapi` | Python (suggest `python-fastapi` or flag as unsupported) |
| `go.mod` | Go (no blueprint yet — flag) |
| `Cargo.toml` | Rust (no blueprint yet — flag) |

**If multiple markers exist** (e.g., a monorepo), ask the user which stack is the primary target.

**If no marker matches an available blueprint**, tell the user:
```
No matching blueprint found for this stack.
Available blueprints: dotnet-hexagonal, python-fastapi, nextjs-typescript

Options:
1. Create a custom blueprint: .claude/blueprints/<name>/reference.md
   (use an existing blueprint as template — all §sections are required)
2. Proceed without a blueprint (not recommended — skills lose stack context)
```

### Step 4: Confirm and Configure

Present the detected configuration to the user for approval:

```
Project Setup Summary:

  Project: [name from INTAKE-summary]
  Stack detected: [stack]
  Blueprint: [blueprint name]
  Domain terms loaded: [count from CONTEXT.md]
  ADRs found: [count]
  Constraints: [any from INTAKE-summary]

Proceed with this configuration?
```

**Wait for explicit approval before writing any files.**

### Step 5: Write Configuration

After approval:

1. **Set Active Blueprint** in `.claude/CLAUDE.md`:
   - Find the line `Active Blueprint: .claude/blueprints/dotnet-hexagonal` (or whatever the current default is)
   - Replace with `Active Blueprint: .claude/blueprints/[detected-blueprint]`

2. **Verify board exists** — check `.board/tasks.md` exists. If empty, remind the user to populate it:
   ```
   .board/tasks.md is empty. Add your backlog before running /sprint:

     ## Backlog
     - [ ] P1: [first task description] #TASK-001
     - [ ] P2: [second task description] #TASK-002
   ```

3. **Verify sprint-state exists** — check `.board/sprint-state.md` exists and has the initial structure.

### Step 6: Report Readiness

```
✓ Harness initialized.

  Active Blueprint: [blueprint name]
  Project docs: ✓ CONTEXT.md + INTAKE-summary.md
  Board: [✓ populated | ⚠ empty — add tasks before /sprint]
  Sprint state: ✓ ready

Next step: Run /sprint to begin the development pipeline.
```

## Rules

- **Docs gate is non-negotiable.** No docs = no setup. This prevents the cascade of wrong assumptions downstream.
- **One-time skill.** After init completes, the harness is configured. Re-running `/init` should detect the existing config and ask if the user wants to reconfigure.
- **Never auto-select without confirmation.** Always present the detected stack/blueprint and wait for approval.
- **No code generation.** This skill configures the harness — it doesn't create application code, scaffolds, or boilerplate.
