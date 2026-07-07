# Harness Improvement Audit — 2026-07-07

> Self-contained record of a full harness evaluation + research-informed improvement plan.
> A fresh agent (or post-compaction session) can resume the improvement work from this
> document alone. Board tasks HARN-001 through HARN-009 in `.board/tasks.md` trace to
> the findings and recommendations below.

## Scope of the Audit

- Full repo exploration (all skills, rules, roles, blueprints, hooks, docs, board, templates)
- Research on 2026 state of the art in agent harness design (sources at bottom)
- Output: findings (Part 1), improvement plan (Part 2), board backlog (HARN-001..009)

## Verdict Summary

The pipeline design (state machine, phase guards, artifact gating, human checkpoints,
token-bounded handover, blueprint plugin system) is coherent and well-documented via ADRs.
The weaknesses fall into four themes:

1. **Drift from incomplete .NET→stack-agnostic generalization** (many concrete defects below)
2. **Enforcement is rhetorical, not mechanical** — every phase guard is a prompt, not a hook
3. **Verification stops at "tests pass"** — no end-to-end exercise, no machine-readable AC status
4. **Flat-rate ceremony** — 6 phases + 4 gates regardless of task size; heavy always-loaded context

---

## Part 1 — Findings (verified against repo state at commit ca50285)

### F1. Dead / missing references

| # | Finding | Location |
|---|---------|----------|
| F1.1 | `/discovery` skill referenced but does not exist | `README.md:83`, `.claude/skills/init/SKILL.md:62`, `.claude/skills/grill-spec/SKILL.md:27` |
| F1.2 | Hook docstring references nonexistent `session-start.py` | `.claude/hooks/context-persistence.py` |
| F1.3 | Hook reads `.state/cycle-state.json` (`cycle_number`, `health`, `last_result`) and `.state/state.md` ("Last Cycle Narrative") — concepts from a different (Boss/Claudio cycle) harness; dead code paths here | `.claude/hooks/context-persistence.py` |

### F2. Broken/fragile mechanical layer

| # | Finding | Location |
|---|---------|----------|
| F2.1 | `settings.json` invokes `python3`; on Windows this frequently does not resolve → all three hooks (PreCompact/SessionStart:compact/Stop) may silently no-op | `.claude/settings.json` |
| F2.2 | `.state/` (hook auto-save target) is NOT gitignored — session state can be committed | `.gitignore` |
| F2.3 | Hook parses board via substring counts on markdown (`**Status**: In Progress`) — works by accident against actual bulleted format | `.claude/hooks/context-persistence.py` |

### F3. Doc inconsistencies / stale counts

| # | Finding | Location |
|---|---------|----------|
| F3.1 | Two "Law 6" headers ("Context Budget" and "Artifact Quality Standards"); top of file says "Three immutable laws", DESIGN.md says "six" | `CLAUDE.md`, `docs/DESIGN.md` |
| F3.2 | ADR count stale: grill-spec says ships with 0001–0006 (3 places), artifact-standards says "6 exemplar ADRs", DESIGN.md index lists 0001–0006. Reality: 7 ADRs exist | `.claude/skills/grill-spec/SKILL.md:94,96,247`, `.claude/rules/artifact-standards.md:153`, `docs/DESIGN.md:168-175` |
| F3.3 | SCOPE.md "Included Blueprints" table lists 2 blueprints (dotnet, python); README/CLAUDE.md list 3 (nextjs missing) | `docs/SCOPE.md:96-99` |
| F3.4 | File-census disagreement: ADR-0007 says 41 files = 13 universal / 7 .NET / 21 mixed; blueprint-migration-map says 19/6/13 | `docs/adr/0007-*.md`, `docs/blueprint-migration-map.md` |
| F3.5 | README source-attribution links point to GitHub profile URLs (or wrong usernames), not project repos | `README.md` |
| F3.6 | Two divergent ADR templates: grill-spec (`# ADR-NNNN:`, Status: Accepted/Superseded/Deprecated, 2+ options required) vs arch role (`# NNNN:`, Status: Proposed/Accepted/Superseded) | `.claude/skills/grill-spec/SKILL.md`, `.claude/agents/roles/arch.md` |
| F3.7 | finish/SKILL.md tail section (lines ~265–307) restates phase guard / produces tables already stated above | `.claude/skills/finish/SKILL.md` |

### F4. Stack leakage in files classified "Universal"

| # | Finding | Location |
|---|---------|----------|
| F4.1 | sprint skill hardcodes `SonarQube + StyleCop` and SonarQube in log/summary templates | `.claude/skills/sprint/SKILL.md:206,219,268,280` |
| F4.2 | handover skill hardcodes `dotnet test` and StyleCop/SonarQube | `.claude/skills/handover/SKILL.md:120,150` |
| F4.3 | sprint-state.md template: "Average SonarQube status" metric | `.board/sprint-state.md:42` |
| F4.4 | artifact-standards.md pervasively .NET (`dotnet test`, Testcontainers.MsSql/.Redis, StyleCop, SonarQube, `*.cs` examples, ~20 hits) while classified Universal | `.claude/rules/artifact-standards.md` |
| F4.5 | board-protocol, context-management, state-management rules also carry SonarQube/StyleCop/`dotnet test` | `.claude/rules/*.md` |
| F4.6 | `.gitignore` is entirely .NET/VS-centric (bin/, obj/, *.nupkg, .vs/) — no node_modules, __pycache__, .venv, .next. Migration map said to fix; not done | `.gitignore` |
| F4.7 | qa role has stack-specific check rows baked into universal role | `.claude/agents/roles/qa.md` |

### F5. Duplication / orphans

| # | Finding | Location |
|---|---------|----------|
| F5.1 | `dotnet-hexagonal/blueprint.md` (598 lines) and `python-fastapi/blueprint.md` (818 lines) duplicate their `reference.md` content under a different section scheme; referenced by NOTHING in the harness. nextjs's blueprint.md is a 14-line summary — structurally inconsistent | `.claude/blueprints/*/blueprint.md` |

### F6. Structural gaps

| # | Finding |
|---|---------|
| F6.1 | No CI, no tests for the harness itself (`.github/` absent) — a harness whose thesis is "no test, no implementation" cannot dogfood its own gates |
| F6.2 | Phase guards, board lock, TDD enforcement, artifact gating are ALL prompt-enforced; the only hook (context-persistence) is broken per F2.1. "Mechanical Enforcement Over Trust" (DESIGN.md principle #1) is not mechanically realized |
| F6.3 | TEST_VERIFY never exercises the running system (no endpoint/UI drive); AC traceability is prose-table only, no machine-readable pass/fail status |
| F6.4 | CLAUDE.md + 8 rules files inject ~25-30K tokens into EVERY session regardless of phase — ironic for a token-budget-first harness. Gold-standard examples in artifact-standards.md belong inside the skills that use them |
| F6.5 | Pipeline intensity is flat: P0–P4 varies review intensity but every task ≥P3 runs all 6 phases + 4 human gates. 2026 process-framework research: ceremony should scale with task size |
| F6.6 | Machine-parsed state lives in markdown tables (sprint-state.md) — every guard/hook must parse markdown; fragile (see F2.3) |

---

## Part 2 — Improvement Plan (maps to board tasks HARN-001..009)

| Task | Priority | Title | Fixes |
|------|----------|-------|-------|
| HARN-001 | P0 | Repair context-persistence hook + Windows compat | F1.2, F1.3, F2.1, F2.2, F2.3 |
| HARN-002 | P0 | Fix dead references and doc inconsistencies | F1.1, F3.1–F3.7 |
| HARN-003 | P1 | De-.NET the universal layer (skills, rules, roles, state, gitignore) + delete orphan blueprint.md duplicates | F4.1–F4.7, F5.1 |
| HARN-004 | P1 | Mechanical phase-guard enforcement (PreToolUse deny hooks + sprint-state.json) | F6.2, F6.6 |
| HARN-005 | P1 | Harness self-CI (cross-reference linter, hook tests Win+Linux, blueprint §-section parity check) | F6.1, prevents F3.x recurrence |
| HARN-006 | P2 | Verification upgrade: machine-readable AC list (JSON, immutable except status) + mandatory end-to-end exercise in TEST_VERIFY + adversarial QA verify | F6.3 |
| HARN-007 | P2 | Fast-lane pipeline for small/low-risk tasks (alternate state-machine path, not a bypass) | F6.5 |
| HARN-008 | P2 | Context-cost reduction: slim CLAUDE.md toward ~200 lines, move artifact templates/examples into their consuming skills | F6.4 |
| HARN-009 | P3 | Modernize onto native Claude Code primitives (native agent definitions with tool restrictions, structured-output subagents for /implement reports) | — |

### Key design rationale (from 2026 research)

- **Enforcement beats instruction**: Anthropic steering guidance — "never do X" prompts are
  not guardrails; critical requirements need hooks/settings. HARN-004 converts Laws 1–2
  from aspiration to physics.
- **Verification is the new bottleneck**: generating plausible code is easy; verifying it
  is the hard problem. Anthropic long-running-harness playbook: machine-readable feature
  list with pass/fail, agent forbidden to edit it except status; end-to-end exercise
  before marking complete. → HARN-006.
- **Ceremony has measured cost**: process-framework taxonomy (arXiv 2606.04967) — excessive
  spec ceremony slows iteration; effective frameworks support gradual adoption and scale
  process to task size. → HARN-007.
- **Context cost is per-session**: keep always-loaded instructions ~200 lines; move
  procedures into on-demand skills; scope rules to paths. → HARN-008.

### Sources

- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://claude.com/blog/steering-claude-code-skills-hooks-rules-subagents-and-more
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- https://arxiv.org/pdf/2606.04967 (From Prompt to Process: process-framework taxonomy)
- https://arxiv.org/pdf/2606.26300 (The Verification Horizon)
- https://developer.microsoft.com/blog/spec-driven-development-spec-kit
- https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/

---

*Audit performed 2026-07-07 on branch fix/python-blueprint-parity @ ca50285.*
*Board tasks: HARN-001..009 in `.board/tasks.md`. This document is the source of truth for finding details.*
