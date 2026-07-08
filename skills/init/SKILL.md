---
name: init
description: Phase 0 — Bootstrap a project for the capivaOS harness. Scaffolds board + docs from the plugin's project-template, validates project docs, detects stack, writes per-project config with schema version. Must run before /capiva:sprint.
---

# Init — Phase 0: Project Bootstrap

First-time harness setup for a project. Runs once, before `/capiva:sprint` ever
executes. The engine (skills, hooks, rules, blueprints) lives in the capiva
plugin; this skill creates the MUTABLE project state the pipeline works on.

## Step 0: Scaffold Project State

Copy from `${CLAUDE_PLUGIN_ROOT}/project-template/` into the project root.
**Never overwrite an existing file** — for each item: if it exists, report
"already present" and skip.

| Source (in plugin) | Destination (in project) |
|--------------------|--------------------------|
| `${CLAUDE_PLUGIN_ROOT}/project-template/.board/tasks.md` | `.board/tasks.md` |
| `${CLAUDE_PLUGIN_ROOT}/project-template/.board/sprint-state.md` | `.board/sprint-state.md` |
| `${CLAUDE_PLUGIN_ROOT}/project-template/docs/specs/.gitkeep` | `docs/specs/.gitkeep` (and reports/, tech-context/, adr/, handover/) |
| `${CLAUDE_PLUGIN_ROOT}/project-template/gitignore-additions.txt` | APPEND to `.gitignore` (skip lines already present) |

Then, if `docs/CONTEXT.md` does not exist, create the stub:

```markdown
# Domain Context

## Glossary
| Term | Definition | Used In Code As | Avoid |
|------|-----------|-----------------|-------|

## Acronyms
| Acronym | Meaning |
|---------|---------|

## Domain Rules
<!-- Business rules that constrain implementation -->
```

Doc templates (CAB ticket, release checklist, deviation record, solution
document, intake summary) are NOT copied — skills read them from
`${CLAUDE_PLUGIN_ROOT}/project-template/templates/` at runtime.

**Approval policy (auto mode)**: NOT scaffolded — `.board/approval-policy.md`
is human-authored law the agent may not write (the guard denies it, ADR-0014).
Absence simply means every delegated gate escalates. When the user wants
delegation, tell them to copy
`${CLAUDE_PLUGIN_ROOT}/project-template/templates/approval-policy.md` to
`.board/approval-policy.md` themselves and edit the grants.

### Legacy copy-mode migration (if detected)

If `.claude/skills/sprint/` exists, this project used the pre-plugin copy-mode
harness. Offer migration — **order matters** (a moved hook script deadlocks the
session that registered it: the hook snapshot points at the old path and a
missing-file python error reads as a deny):

1. Rewrite `.claude/settings.json`: remove the harness hook entries (the plugin's
   `${CLAUDE_PLUGIN_ROOT}/hooks/hooks.json` now provides them; keep any user-added non-harness hooks)
2. **Leave `.claude/hooks/*.py` in place for now** — the running session's hook
   snapshot still points there. They become dead files after restart.
3. Delete `.claude/skills/`, `.claude/rules/`, `.claude/agents/`,
   `.claude/blueprints/` ONLY after the user confirms the plugin versions work
   (project-level copies would silently shadow the plugin's)
4. Tell the user: "Restart the session, verify `/capiva:sprint` works, then delete
   `.claude/hooks/` — or run `/capiva:init` again and I'll finish the cleanup."

## Step 1: Check Project Documentation (GATE)

**Hard gate. Do not proceed without docs.**

1. `docs/CONTEXT.md` — must have **at least one glossary entry or domain rule** (the stub from Step 0 does not count)
2. `docs/specs/INTAKE-summary.md` — must exist with project scope, stakeholders, and key requirements

**If EITHER is missing or empty → STOP.** Present:

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
2. Draft the documents — the INTAKE format template is at
   ${CLAUDE_PLUGIN_ROOT}/project-template/templates/intake-summary.md;
   ask Claude to generate first drafts if useful
3. Run /capiva:init again once the docs are populated
```

## Step 2: Read Project Documentation

- Read `docs/CONTEXT.md` — domain terms, acronyms, business rules
- Read `docs/specs/INTAKE-summary.md` — project name, scope, stakeholders, requirements, constraints
- Read `docs/adr/` if present — existing project architectural decisions

## Step 3: Detect Stack

Scan the project root for technology markers:

| Marker | Stack |
|--------|-------|
| `*.csproj` or `*.sln` | .NET → `dotnet-hexagonal` |
| `package.json` with `next` dependency | Next.js → `nextjs-typescript` |
| `package.json` without `next` | Node.js (suggest `nextjs-typescript` or flag as unsupported) |
| `requirements.txt` or `pyproject.toml` with `fastapi` | Python FastAPI → `python-fastapi` |
| `requirements.txt` or `pyproject.toml` without `fastapi` | Python (suggest `python-fastapi` or flag as unsupported) |
| `go.mod` | Go (no shipped blueprint — flag) |
| `Cargo.toml` | Rust (no shipped blueprint — flag) |

**Multiple markers** (monorepo) → ask which stack is the primary target.

**No matching blueprint** → tell the user:
```
No matching blueprint found for this stack.
Shipped blueprints: dotnet-hexagonal, python-fastapi, nextjs-typescript

Options:
1. Create a custom blueprint in YOUR project: capiva-blueprints/<name>/reference.md
   Then VALIDATE it before accepting the configuration (AUD-015):
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/harness_lint.py --check-blueprint capiva-blueprints/<name>`
   — a blueprint missing contract sections fails init here, not mid-pipeline
   when a skill reads a contract section that does not exist.
   (project blueprints override shipped ones; copy a shipped reference.md as the
   starting structure — every § section is required)
2. Proceed without a blueprint (not recommended — skills lose stack context)
```

## Step 4: Confirm

```
Project Setup Summary:

  Project: [name from INTAKE-summary]
  Stack detected: [stack]
  Blueprint: [name] (resolved from: capiva-blueprints/ | plugin)
  Domain terms loaded: [count from CONTEXT.md]
  Harness version: [from ${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json]
  Constraints: [any from INTAKE-summary]

Proceed with this configuration?
```

**Wait for explicit approval before writing configuration.**

## Step 5: Write Configuration (project files only — NEVER into the plugin)

1. Write `.board/harness-config.md`:

```markdown
# Harness Config

- **Active Blueprint**: [blueprint-name]
- **Configured**: [ISO date]
- **Installed Via**: plugin | copy-mode
- **Phase Isolation**: off
- **Dual Review**: off
```

2. Write `.board/harness-schema-version` containing exactly the plugin's
   `version` from `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` (no
   newline decoration — the session-context hook and `/capiva:update` compare
   this stamp).

3. If `.board/tasks.md` has no tasks, remind the user to populate the backlog
   before running /capiva:sprint.

## Step 5b: Repo Hardening — Branch Protection (ADR-0014 safety prerequisite)

The merge decision is the harness's one never-delegable gate — mechanically real
only if the forge enforces PR-only merges. Check and offer; **never block init**
on this step (air-gapped installs must work).

1. Detect: `git remote get-url origin` — if not GitHub, or `gh` unavailable, or
   the API call fails: warn once ("could not verify branch protection — auto
   mode requires a protected default branch") and continue to Step 6.
2. Check: `gh api "repos/OWNER/REPO/rulesets" --jq ...` and/or
   `gh api "repos/OWNER/REPO/branches/DEFAULT/protection"` — determine
   whether PRs are required to merge into the default branch.
3. If unprotected, present:

```
⚠ Default branch accepts direct pushes. The harness's merge gate — the one
  decision never delegated to any agent — is only enforced if GitHub requires
  pull requests. This is the safety prerequisite for auto mode.

  Configure now? [creates a ruleset: require PRs + require the Harness CI check]
```

4. On explicit confirmation: create the ruleset via `gh api -X POST
   repos/OWNER/REPO/rulesets` (require pull_request + required_status_checks
   for the CI workflow). On decline OR insufficient scope: report the manual UI
   path (Settings → Rules) and record the outcome.
5. Record in `.board/harness-config.md`:
   `- **Branch Protection**: configured [date] | verified [date] | declined [date] (+reason)`

Note for auto mode: the auto skill re-checks at run start and refuses (with
explicit override) on unprotected branches — contract per LOOP-002 AC5.

## Step 6: Report Readiness

```
✓ Harness initialized.

  Active Blueprint: [name]
  Schema version: [version] (stamped)
  Project docs: ✓ CONTEXT.md + INTAKE-summary.md
  Board: [✓ populated | ⚠ empty — add tasks before /capiva:sprint]
  Branch protection: [✓ configured | ⚠ declined/unverified — required before auto mode]

Next: run /capiva:sprint to begin the pipeline.
Update the harness later with `/capiva:update`.
```

## Rules

- **Docs gate is non-negotiable.** No docs = no setup.
- **Scaffold never overwrites.** Existing files are reported and skipped.
- **Config is project-side only.** The plugin directory is a versioned read-only cache — writing there is a defect.
- **Re-running is safe.** Init detects existing config and asks before reconfiguring; it also finishes legacy-migration cleanup when invited to.
- **Never auto-select without confirmation.** Present the detected stack/blueprint and wait.
- **No code generation.** Configures the harness only.
