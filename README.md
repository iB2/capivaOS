# Spec-Driven Development Harness for Claude Code

A state-machine enforced, 6-phase development pipeline that turns Claude Code into a disciplined development agent. Board-driven, spec-first, test-enforced, artifact-gated. **Stack-agnostic** — works with any technology via pluggable blueprints.

Synthesizes ideas from [grill-with-docs](https://github.com/mattpocock) (adversarial spec interviews), [Superpowers](https://github.com/obra) (SDD+TDD pipeline), and [Claudio](https://github.com/brunoamerico) (board-driven agent orchestration). See [docs/DESIGN.md](docs/DESIGN.md) for full design philosophy, source attribution, and rationale. See [docs/SCOPE.md](docs/SCOPE.md) for what this harness is and isn't.

## What This Does

Instead of ad-hoc prompting, this harness enforces a strict pipeline via a state machine:

1. **Pick a task** from the board → state: TRIAGE
2. **Grill the spec** until zero ambiguities → produces formal spec document
3. **Plan** — query Context7 for current library docs, then decompose into micro-tasks → produces PLAN.md + tech context
4. **Implement** via subagents with TDD enforced → feature branch
5. **Verify** with static analysis + integration tests → quality report
6. **Ship** a PR with full traceability → board updated, state reset

**Every phase reads and writes `.board/sprint-state.md`.** Skills refuse to run if the phase doesn't match. Artifacts from each phase gate the next. Board writes use a lock file for concurrency safety.

## Pipeline State Machine

```
IDLE ──→ TRIAGE ──→ GRILL_SPEC ──→ PLAN ──→ IMPLEMENT ──→ TEST_VERIFY ──→ FINISH ──→ IDLE
                       🧑               🧑                       🧑              🧑
                    approve spec     approve plan           review report    merge decision
```

Each 🧑 is a blocking human checkpoint. Silence is NOT approval.

### Enforcement Mechanisms

| Mechanism | What It Prevents |
|-----------|-----------------|
| **Phase guards** | Skills running out of sequence |
| **Artifact gates** | Advancing without required outputs |
| **Board lock** | Concurrent writes corrupting state |
| **Sprint state** | Session crashes losing pipeline position |
| **Quality gates** | PRs without adequate test coverage |

## Blueprints — Stack-Agnostic Design

The harness separates the **universal pipeline** (phases, state machine, artifact gating, board protocol) from **stack-specific patterns** (coding standards, test frameworks, build commands). Stack-specific content lives in **blueprint reference files**.

### Available Blueprints

| Blueprint | Stack | Architecture |
|-----------|-------|-------------|
| `dotnet-hexagonal` | .NET 10 / C# 13 | Hexagonal (Ports & Adapters) |
| `python-fastapi` | Python 3.13 / FastAPI | Layered (api → services → repositories → db) |

Set the active blueprint in `.claude/CLAUDE.md`. Agent roles, skills, and rules automatically read the active blueprint's `reference.md` for stack-specific guidance.

### Creating a New Blueprint

1. Create `.claude/blueprints/<stack-name>/reference.md` with sections: §project, §stack, §architecture, §coding-standards, §enterprise-patterns, §test-stack, §static-analysis, §ci-cd, §qa-checklist, §build-commands
2. Create a real, buildable reference project locally
3. Set it as the active blueprint in CLAUDE.md

## Quick Start

### 1. Clone into your project

```bash
# From your project root
git clone https://github.com/iB2/capivaOS.git .harness-tmp
cp -r .harness-tmp/.claude .claude
cp -r .harness-tmp/.board .board
cp -r .harness-tmp/docs docs
cp -r .harness-tmp/templates templates
cp .harness-tmp/.gitignore .gitignore  # or merge with existing
rm -rf .harness-tmp
```

### 2. Configure

Edit `.claude/CLAUDE.md`:
- Set the Active Blueprint to match your stack
- Solution/project path (if not in root)
- Jira integration (optional)
- Quality threshold overrides (optional)

### 3. Populate the board

Add tasks to `.board/tasks.md`:

```markdown
## Backlog — P1 Sprint

- [ ] **TASK-001** Implement user authentication service (P1)
  - **Spec**: JWT auth, refresh tokens, password hashing
  - **AC**: 1. Login/logout works 2. Tokens expire correctly 3. Unit + integration tests
  - **Depends**: none
  - **Status**: Backlog
```

### 4. Start

```
/sprint
```

The sprint skill reads the board, picks the highest-priority task, and drives it through all 6 phases with human checkpoints.

## Skills

| Skill | Phase | Produces | Guards |
|-------|-------|----------|--------|
| `/sprint` | Orchestrator | Sprint state transitions | Reads state, manages loop |
| `/grill-spec` | 1 - GRILL_SPEC | `docs/specs/TASK-ID-spec.md`, CONTEXT.md, ADRs | Phase = GRILL_SPEC |
| `/plan` | 2 - PLAN | `PLAN.md`, `docs/tech-context/TASK-ID-tech.md` | Phase = PLAN, Spec Approved |
| `/implement` | 3 - IMPLEMENT | Code + tests on feature branch | Phase = IMPLEMENT, Plan Approved |
| `/test-verify` | 4 - TEST_VERIFY | `docs/reports/TASK-ID-quality.md` | Phase = TEST_VERIFY, branch exists |
| `/finish` | 5 - FINISH | PR, board update, Jira transition | Phase = FINISH, Quality Gate = PASS |

## Artifact Chain

```
GRILL_SPEC → docs/specs/TASK-ID-spec.md  ──→  /plan reads it
PLAN       → PLAN.md + tech-context.md    ──→  /implement reads both
IMPLEMENT  → feature branch (green tests) ──→  /test-verify runs on it
TEST_VERIFY→ docs/reports/TASK-ID-quality.md → /finish includes in PR
FINISH     → PR #N on remote              ──→  /sprint resets to IDLE
```

Each arrow = artifact verification. Missing artifact = skill refuses to run.

## State Files

| File | Purpose | Managed By |
|------|---------|-----------|
| `.board/tasks.md` | Task backlog and status | All skills (with lock) |
| `.board/sprint-state.md` | Pipeline state machine | All skills (every transition) |
| `.board/board.lock` | Write concurrency control | Lock protocol (gitignored) |
| `docs/CONTEXT.md` | Domain glossary | /grill-spec |
| `docs/adr/*.md` | Architecture decisions | /grill-spec |
| `PLAN.md` | Micro-task breakdown | /plan |
| `docs/tech-context/*.md` | Current library docs (Context7) | /plan |
| `docs/specs/*.md` | Formal spec documents | /grill-spec |
| `docs/reports/*.md` | Quality reports | /test-verify |

## Quality Gates

| Metric | Target | Hard Fail |
|--------|--------|-----------|
| Unit coverage | >= 80% | < 60% |
| Linter warnings (new code) | 0 | Any warning |
| Quality gate (per blueprint) | Pass | Fail |
| Integration tests | All pass | Any failure |
| AC coverage | All covered | Any uncovered |

## Requirements

- **Claude Code** (Opus recommended)
- **Context7 MCP** configured in `.mcp.json` (library documentation lookup)
- **Stack-specific toolchain** (per your chosen blueprint — e.g., .NET SDK, Python, Docker)
- **Git** (worktree support)

### MCP Configuration

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp@latest"]
    }
  }
}
```

Place `.mcp.json` in your project root. Context7 provides current library documentation during the /plan phase, preventing stale API usage from training data.

## Directory Structure

```
your-project/
├── .board/
│   ├── sprint-state.md              # Pipeline state machine (current phase + task)
│   └── tasks.md                     # Task board (source of truth)
├── .claude/
│   ├── CLAUDE.md                    # Main config + enforcement rules + active blueprint
│   ├── agents/roles/
│   │   ├── arch.md                  # Architect subagent role
│   │   ├── dev.md                   # Developer subagent role
│   │   └── qa.md                    # QA subagent role
│   ├── blueprints/
│   │   ├── dotnet-hexagonal/
│   │   │   └── reference.md         # .NET stack-specific patterns & commands
│   │   └── python-fastapi/
│   │       └── reference.md         # Python stack-specific patterns & commands
│   ├── rules/
│   │   ├── artifact-standards.md    # Artifact naming, format, gating rules
│   │   ├── board-protocol.md        # Task format, write protocol, locking
│   │   ├── coding-standards.md      # Universal conventions + blueprint pointer
│   │   ├── context-management.md    # Context budget, surgical reads, compaction
│   │   ├── enterprise-blueprint.md  # Universal enterprise constraints + blueprint pointer
│   │   ├── quality-gates.md         # Coverage/static analysis thresholds
│   │   ├── state-management.md      # State machine, board lock, artifacts
│   │   └── workflow-pipeline.md     # Phase guards, transitions, failures
│   └── skills/
│       ├── finish/SKILL.md          # Phase 5 — PR, board update, Jira transition
│       ├── grill-spec/SKILL.md      # Phase 1 — interrogate requirements
│       ├── handover/SKILL.md        # Mid-sprint context handover between sessions
│       ├── implement/SKILL.md       # Phase 3 — TDD code on feature branch
│       ├── plan/SKILL.md            # Phase 2 — decompose into micro-tasks
│       ├── sprint/SKILL.md          # Orchestrator — drives the full pipeline
│       └── test-verify/SKILL.md     # Phase 4 — static analysis + test run
├── docs/
│   ├── CONTEXT.md                   # Domain glossary (built during grill-spec)
│   ├── DESIGN.md                    # Design philosophy, source attribution, rationale
│   ├── SCOPE.md                     # What harness is/isn't, adaptation guide
│   ├── adr/                         # Architecture Decision Records (harness design)
│   ├── blueprint-migration-map.md   # File classification for blueprint separation
│   ├── reports/.gitkeep             # Quality reports from test-verify
│   ├── specs/.gitkeep               # Formal spec documents from grill-spec
│   ├── tech-context/.gitkeep        # Current library docs (Context7 MCP)
│   └── workflow-complete.mmd        # Mermaid diagram of the full pipeline
├── templates/
│   ├── cab-ticket.md                # Change Advisory Board ticket template
│   ├── deviation-record.md          # Process deviation record template
│   ├── release-checklist.md         # Pre-release checklist template
│   └── solution-document.md         # Solution design document template
├── .gitignore
└── README.md
```

### Templates

The `templates/` directory contains universal process document templates (CAB tickets, deviation records, release checklists, solution documents). Stack-specific templates (editor config, build props, CI pipelines) are part of the blueprint project, not the harness.

---

Built for teams that want Claude Code to write production-quality code, not prototypes.
State-machine enforced. Board-locked. Artifact-gated. Human-checkpointed. Stack-agnostic.
