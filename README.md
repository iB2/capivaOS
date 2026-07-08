# capivaOS — Spec-Driven Development Harness for Claude Code

A state-machine enforced, spec-first, test-enforced development pipeline for Claude Code, installed as a **plugin**. Board-driven, artifact-gated, human-checkpointed. **Stack-agnostic** via pluggable blueprints. Free, by [Capiva](https://github.com/iB2).

Synthesizes ideas from [Matt Pocock's skills](https://github.com/mattpocock/skills) (the adversarial spec interview), [Superpowers](https://github.com/obra/superpowers) (SDD+TDD pipeline, by obra), and Claudio (Bruno Americo's board-driven agent orchestration framework, not publicly released). Full design philosophy and rationale: [docs/DESIGN.md](docs/DESIGN.md). What it is and isn't: [docs/SCOPE.md](docs/SCOPE.md). Security properties: [SECURITY.md](SECURITY.md).

## Install

```
/plugin marketplace add iB2/capivaOS
/plugin install capiva@capiva
```

Then, inside the project you want the harness on:

```
/capiva:init
```

`/capiva:init` scaffolds the project state (`.board/` task board + sprint state, docs skeleton), validates your project docs, detects your stack, and stamps the harness schema version. The engine (skills, hooks, agents, rules, blueprints) stays in the plugin and updates centrally — your project keeps only its own mutable state.

**Non-interactive / CI:**

```bash
claude plugin marketplace add iB2/capivaOS
claude plugin install capiva@capiva --scope project
```

**Team pinning** — commit this to your repo's `.claude/settings.json` and every teammate gets prompted to install on folder trust:

```json
{
  "extraKnownMarketplaces": {
    "capiva": { "source": { "source": "github", "repo": "iB2/capivaOS" } }
  },
  "enabledPlugins": { "capiva@capiva": true }
}
```

**Air-gapped / offline:** clone this repo to a shared path, then `claude plugin marketplace add /path/to/capivaOS` — everything works from the local clone; no other network access is ever needed (see SECURITY.md).

## Update

```
/capiva:update
```

Runs the safe ritual: marketplace refresh → plugin update → `/reload-plugins` → schema-skew check → project migration (`/capiva:update-project`) if the release changed scaffolded-file formats. You can just tell Claude "update the harness" — the skill makes it deterministic.

Optional: enable per-marketplace auto-update in `/plugin` → Marketplaces → capiva. Releases are explicit semver — you only receive updates when a version is cut, never on raw pushes ([CHANGELOG.md](CHANGELOG.md)).

## Uninstall

```
claude plugin uninstall capiva@capiva
claude plugin marketplace remove capiva
```

What stays in your repo: `.board/`, `.state/`, `docs/specs|reports|tech-context|adr|handover/`, and two `.gitignore` lines. All of it is **inert without the plugin** — no hooks run, nothing is enforced; the files are plain markdown you can keep (they are your project's decision history) or delete. The plugin never writes outside your project (see [SECURITY.md](SECURITY.md)), so uninstalling is the complete exit — no cleanup owed.

## What This Does

Instead of ad-hoc prompting, the harness enforces a strict pipeline via a state machine:

1. **Pick a task** from the board → state: TRIAGE (lane selected: full or fast)
2. **Grill the spec** until zero ambiguities → formal spec + machine-readable AC list (`acs.json`)
3. **Plan** — current library docs via Context7, micro-task decomposition → PLAN.md + tech context
4. **Implement** via tool-restricted subagents with TDD enforced → feature branch + validated JSON reports
5. **Verify** — integration tests, static analysis, an end-to-end exercise of the built feature, adversarial QA review → quality report generated from the AC list
6. **Ship** a PR with full traceability → board updated, state reset

**Every phase reads and writes `.board/sprint-state.md`.** Skills refuse to run if the phase doesn't match. Artifacts from each phase gate the next. Board writes use a lock file for concurrency safety.

## Pipeline State Machine

```
/capiva:init ─→ IDLE ─→ TRIAGE ─→ GRILL_SPEC ─→ PLAN ─→ IMPLEMENT ─→ TEST_VERIFY ─→ FINISH ─→ IDLE
 🧑 docs                       🧑 approve spec  🧑 approve plan     🧑 review report  🧑 merge

Fast lane (small, low-risk tasks): IDLE ─→ TRIAGE ─→ SPEC_PLAN ─→ IMPLEMENT ─→ VERIFY_FINISH ─→ IDLE
                                                   🧑 one gate                 🧑 one gate
```

Each 🧑 is a blocking human checkpoint. Silence is NOT approval. The fast lane (P2/P3, no new files, no schema/arch changes) compresses ceremony, never verification substance.

### Enforcement Mechanisms

Two honest tiers. **Mechanically enforced** — a hook or the platform denies
the action; model compliance is not involved (this list is generated from
`ENFORCED_SURFACES` in `hooks/phase_guard.py` and lint-checked against it —
claims and code cannot drift apart without failing CI):

| Mechanism | What It Denies |
|-----------|----------------|
| **Phase guard: source writes** (PreToolUse) <!-- enforced: source-writes-outside-implement --> | Source writes outside IMPLEMENT (tests also allowed in TEST_VERIFY/VERIFY_FINISH) — via Edit/MultiEdit/Write/NotebookEdit AND shell writes (redirects, `tee`, `sed -i`, `touch`) under tool parity |
| **Phase guard: PR gate** <!-- enforced: pr-create-gate --> | `gh pr create` outside FINISH/VERIFY_FINISH or without a passing quality-gate status |
| **Phase guard: human-only files** <!-- enforced: human-only-files --> | Agent writes to `.board/approval-policy.md` and to the guard's own kill-switch marker, in every phase |
| **Phase guard: merge verbs** <!-- enforced: merge-verbs --> | `gh pr merge` and `git push` targeting the default branch, in every phase and mode (ADR-0014 never-list item 1) |
| **Tool-restricted agents** (platform, ADR-0012) <!-- enforced: agent-allowlists --> | qa and gate-judge are read-only *by construction* — they cannot modify what they review |

Also mechanical (persistence, not denial): sprint state on disk + PreCompact/Stop
snapshots + SessionStart re-injection — pipeline position survives crashes and
compaction. Known limits of the deny surface are documented plainly in
[SECURITY.md](SECURITY.md): shell interception is best-effort; the GitHub web
UI and MCP merge routes are covered by branch protection, not hooks.

**Structurally encouraged** — the pipeline makes the disciplined path the easy
path; these hold a compliant model, and are honestly NOT walls against a
drifting one:

| Mechanism | What It Prevents |
|-----------|-----------------|
| **Init gate** | Running the pipeline without project docs or blueprint config |
| **Phase sequencing in skills** | Skills running out of sequence |
| **Artifact gates** | Advancing without required outputs |
| **acs.json contract** | ACs silently dropped (the diff is visible; status flips are agent-attested — ADR-0009 names this residual gap) |
| **Board lock protocol** | Concurrent writes corrupting state (convention, ADR-0003 — no lock code exists by design) |
| **Human checkpoints** | Silence-as-approval (prompt discipline; the hook enforces only the recorded gate status at PR time) |
| **Quality gates** | PRs below thresholds (agent-executed checks per the blueprint) |

## Skills

| Skill | Phase | Produces |
|-------|-------|----------|
| `/capiva:init` | 0 — Bootstrap | Scaffolded board/docs, blueprint config, schema stamp |
| `/capiva:sprint` | Orchestrator | State transitions, lane selection, the loop |
| `/capiva:grill-spec` | 1 — GRILL_SPEC | `docs/specs/TASK-ID-spec.md` + `TASK-ID-acs.json`, CONTEXT.md terms, ADRs |
| `/capiva:plan` | 2 — PLAN | `PLAN.md`, `docs/tech-context/TASK-ID-tech.md` |
| `/capiva:implement` | 3 — IMPLEMENT | Code + tests on a feature branch, validated JSON reports |
| `/capiva:test-verify` | 4 — TEST_VERIFY | `docs/reports/TASK-ID-quality.md`, AC statuses |
| `/capiva:finish` | 5 — FINISH | PR, board update, Jira transition |
| `/capiva:spec-plan` | fast lane | Spec-lite + plan behind one gate |
| `/capiva:verify-finish` | fast lane | Verification + PR behind one gate |
| `/capiva:handover` | any | `docs/handover/TASK-ID-handover.md` for multi-session work |
| `/capiva:update` | any | Safe engine update ritual |
| `/capiva:update-project` | any | Scaffolded-file migration after engine updates |

## Blueprints — Stack-Agnostic Design

The universal pipeline (phases, state machine, gating, board protocol) is separated from stack-specific patterns (coding standards, test frameworks, build commands), which live in blueprint reference files.

| Blueprint | Stack | Architecture |
|-----------|-------|-------------|
| `dotnet-hexagonal` | .NET 10 / C# 13 | Hexagonal (Ports & Adapters) |
| `python-fastapi` | Python 3.13 / FastAPI | Layered (api → services → repositories → db) |
| `nextjs-typescript` | Node.js 22 / Next.js 15+ / App Router | Feature-based colocation (Server/Client split) |

`/capiva:init` selects the blueprint and records it in `.board/harness-config.md`. **Custom stacks**: create `capiva-blueprints/<name>/reference.md` in your project (project blueprints override shipped ones) with the standard sections: §project, §stack, §architecture, §coding-standards, §enterprise-patterns, §test-stack, §static-analysis, §ci-cd, §qa-checklist, §build-commands.

## Artifact Chain

```
GRILL_SPEC → docs/specs/TASK-ID-spec.md + acs.json ─→ /capiva:plan reads them
PLAN       → PLAN.md + tech-context.md             ─→ /capiva:implement reads both
IMPLEMENT  → feature branch (green tests)          ─→ /capiva:test-verify runs on it
TEST_VERIFY→ docs/reports/TASK-ID-quality.md       ─→ /capiva:finish includes in PR
FINISH     → PR #N on remote                       ─→ /capiva:sprint resets to IDLE
```

Each arrow = artifact verification. Missing artifact = skill refuses to run.

## Project State Files (yours, scaffolded by init)

| File | Purpose | Managed By |
|------|---------|-----------|
| `.board/tasks.md` | Task backlog and status | All skills (with lock) |
| `.board/sprint-state.md` | Pipeline state machine | All skills (every transition) |
| `.board/harness-config.md` | Active blueprint + config | /capiva:init, /capiva:update-project |
| `.board/harness-schema-version` | Scaffold schema stamp | /capiva:init, /capiva:update-project |
| `docs/CONTEXT.md` | Domain glossary | /capiva:init (gate), /capiva:grill-spec |
| `docs/specs/`, `docs/reports/`, `docs/tech-context/`, `docs/handover/` | Pipeline artifacts | Phase skills |
| `PLAN.md` | Micro-task breakdown | /capiva:plan |

## Quality Gates

Coverage is scoped (normative table: `rules/quality-gates.md` — below minimum = the gate fails):

| Metric | Minimum (gate) | Target |
|--------|----------------|--------|
| Unit coverage — business logic | 80% | 90% |
| Unit coverage — infrastructure | 60% | 75% |
| Unit coverage — overall | 75% | 85% |
| Linter warnings (new code) | 0 | 0 |
| Integration tests | all pass | all pass |
| AC statuses in acs.json | all `pass` (test + e2e evidence) | — |

## How This Compares

Full table with source-verified mechanisms and dated figures: [docs/COMPARISON.md](docs/COMPARISON.md). The one-liner: *Spec Kit's lifecycle breadth, tdd-guard's mechanical teeth* — and the caveats live in the comparison itself.

## What This Costs

Figures from the ADR benchmarks ([ADR-0004](docs/adr/0004-token-bounded-execution.md), [ADR-0010](docs/adr/0010-fast-lane-pipeline.md)) — estimates as of 2026-07, not guarantees:

| | Full lane | Fast lane (qualifying P2/P3) |
|---|---|---|
| Blocking human gates | 4 (spec, plan, quality, merge) plus the grill interview (typically 6–12 questions) | 2 (combined spec+plan, combined quality+merge) |
| Pipeline token overhead | ~165K typical | ~75K typical |
| Heaviest phases | IMPLEMENT ~60–100K, TEST_VERIFY ~40–70K | combined verify+finish |
| Sessions per task | 1–2 (handover on complex tasks is expected, not a failure) | usually 1 |

The overhead buys the artifact chain (spec, acs.json, PLAN.md, quality report) and the mechanical enforcement. If a task doesn't merit that, it doesn't belong in the pipeline — see [docs/SCOPE.md](docs/SCOPE.md) for what the harness is deliberately NOT for.

## Requirements

- **Claude Code** with plugin support
- **Python 3** available as `py`, `python`, or `python3` (hooks; they disable themselves gracefully if absent)
- **Context7 MCP** recommended (current library docs during /capiva:plan):

```json
{
  "mcpServers": {
    "context7": { "command": "npx", "args": ["-y", "@upstash/context7-mcp@latest"] }
  }
}
```

- **Git** and your stack's toolchain (per blueprint)
- **Protected default branch** (require PRs) before enabling auto mode — `/capiva:init` checks and offers to configure it

## Repository Layout (this repo = the plugin = its own marketplace)

```
capivaOS/
├── .claude-plugin/
│   ├── plugin.json           # name: capiva, semver — the release contract
│   └── marketplace.json      # self-referencing marketplace (source: ./)
├── skills/                   # the capiva:* pipeline phases + update ritual
├── agents/                   # dev / qa / arch / gate-judge / phase-runner — platform-enforced tool allowlists
├── hooks/                    # phase guard, context persistence, session injection
│   ├── hooks.json            # plugin hook registration
│   └── run-hook.cmd          # Windows/POSIX polyglot dispatcher (never blocks)
├── rules/                    # laws.md (injected each session) + detailed rules (read on demand)
├── blueprints/               # shipped stacks
├── project-template/         # what /capiva:init scaffolds into YOUR repo
├── scripts/                  # harness_lint, report validator, bump_version
└── docs/                     # DESIGN, SCOPE, ADRs, troubleshooting
```

For harness development itself (this repo), see [docs/DESIGN.md](docs/DESIGN.md) and the CI suite (`scripts/harness_lint.py`, `hooks/tests/`).

---

Built for teams that want Claude Code to write production-quality code, not prototypes.
State-machine enforced. Board-locked. Artifact-gated. Human-checkpointed. Stack-agnostic. Zero-telemetry.
