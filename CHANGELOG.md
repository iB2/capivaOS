# Changelog

All notable changes to the capivaOS harness. Versions follow semver; users
receive updates only when the version in `.claude-plugin/plugin.json` is bumped.
Schema-affecting changes MUST land with a matching migration row in
`skills/update-project/SKILL.md`.

## [1.3.0] — 2026-07-09

Production-readiness release: resilience and containment hardening from a
second external code review (the resilience/containment lens). Guardrails gain
a proof-of-life, the state file the guard trusts stops being freely rewritable,
and the write surface stops self-licensing.

### Guard liveness (PRD-001)
- **POSIX dispatch fixed**: `hooks/run-hook.cmd` now ships with the exec bit; a
  CI job fires the hook by bare path on Linux/macOS. The dispatcher was
  shebang-less mode-0644 — on POSIX that meant the guard could be silently
  absent for every non-Windows adopter, masked by both CI paths.
- **Enforcement heartbeat**: the guard writes `.state/guard-heartbeat` on every
  enforced invocation; SessionStart warns loudly if a task is active with no
  heartbeat; `/capiva:auto` refuses to start without a live heartbeat. Silence
  no longer reads as a healthy guard. Lint check 16 keeps the claim honest.

### Write-surface integrity (PRD-002)
- `.github/`, `scripts/`, and `.claude/` are **no longer writable in any
  phase** — they are source now, writable only in IMPLEMENT (a task whose plan
  covers them). Blanket always-allow was a self-licensing route: CI YAML is
  arbitrary code on push, `scripts/` are the validators the pipeline trusts.
- `.claude/settings.json` (dev-mode hook registration) and root `CLAUDE.md`
  (auto-loaded instructions) join the human-only files — an agent can no longer
  deregister its own guard or plant project instructions.
- `.claude/settings.json` PreToolUse matcher gains `MultiEdit` (it bypassed the
  dev-mode guard; the 1.2.0 fix reached hooks.json only). Lint check 17 keeps
  the two registrations in parity.

### State-file integrity (PRD-003)
- **Transition validation (ADR-0015, now implemented)**: the guard validates
  Phase transitions in `sprint-state.md` against the legal full/fast-lane
  chain. Illegal jumps (IDLE→IMPLEMENT), a forged `Quality Gate: PASS` with no
  report on disk, and Phase-blanking are denied. Entering IMPLEMENT requires
  PLAN.md + acs.json; entering FINISH requires the quality report (Law 3 rises
  from prompt to hook). The state file the guard trusts is no longer freely
  rewritable by the constrained party — closing the review's core loophole.
- **Mechanical board lock (ADR-0016, supersedes ADR-0003)**: `board_lock.py`
  with atomic `O_EXCL` acquire, one staleness window, and `time.time()`
  timestamps replaces the prose ritual (which carried two contradictory
  staleness numbers). The guard denies board writes held by another live
  holder. Enforced only when the lock mechanism is in use — no adopter is
  bricked mid-migration.
- Lint checks 18 (staleness parity) keep the two constants from drifting.

### Real audit trail (PRD-004)
- **False hash claim removed**: the approval-policy template and ADR-0014
  claimed "changes detected by hash and logged" — no code ever computed a
  hash. Deleted (not faked); lint check 19 blocks any doc from re-claiming a
  hash-audit mechanism no code implements.
- **Mechanical run-log**: hooks append `.state/run-log.jsonl` (deny,
  transition, gate, and lock events) — an append-only, hook-written record
  the same agent's markdown narrative is checked against, not vice-versa.
  The morning report now reconciles against it.

## [1.2.1] — 2026-07-09

Patch: consistency and claims hardening — the remainder of the 2026-07
external-review follow-up.

- **Lint check 14** — quantitative-claim parity: SECURITY.md's "~N lines"
  figure is recomputed against `wc -l` at ±15% (the figure went stale in both
  directions across two releases; now it cannot rot silently)
- **Lint check 15** — private board IDs (LOOP/CAP/AUD-n) may not appear in
  skills/, rules/, agents/: adopters cannot resolve this repo's own task IDs.
  The check caught 3 further refs pre-commit, before they ever shipped
- SDLC mapping unified across all three blueprints (named stages, namespaced
  commands — the numeric scheme collided with enterprise-blueprint gate
  numbers); python-fastapi §ci-cd now ships the GitHub Actions workflow its
  summary card promises
- Universal doc templates de-.NET/de-Azure'd; README gains headless-auth
  requirement + "Schema migrations" section; state-management artifact chain
  includes tech-context (briefs isolated phase-runners); assorted numbering
  nits
- 8 shipped LOOP-nnn references re-anchored to ADR-0014 / plain descriptions

## [1.2.0] — 2026-07-08

The honesty release: an external code review found that "mechanically
enforced" claimed more than the hooks delivered — and that the audience this
product courts would find the gap in minutes. 1.2.0 closes the enforcement
holes, re-segments every claim, and converts each identified bug class into a
lint check so the class cannot recur.

### Enforcement (phase guard)
- **Kill-switch protected**: `.state/phase-guard-off` is HUMAN_ONLY — an agent
  can no longer disable its own guard (the review's top code finding)
- **Merge verbs denied everywhere**: `gh pr merge` (any form) and `git push`
  targeting the default branch, in every phase and mode — "AUTO never merges"
  is now hook-backed, not prose
- **Shell write parity**: a Bash/PowerShell write (redirects, `tee`, `sed -i`,
  `touch`, heredoc-fed) is denied exactly when a `Write` would be — same
  decision function; quoted strings/heredoc bodies stripped so prose with `>`
  can never false-deny. `MultiEdit` matched. Both human-only files now closed
  via shell too
- **Conflicted sprint-state fails open LOUDLY** instead of trusting the first
  `Phase:` match
- **`ENFORCED_SURFACES`**: the guard declares its exact deny surface; lint
  locks README/SECURITY claims to it in both directions (over- AND
  under-claiming fail CI)

### Claims and docs
- README enforcement table re-segmented: "Mechanically enforced" (5
  marker-locked rows) vs "Structurally encouraged" (residuals named in place)
- SECURITY.md: "What is mechanically enforced — exactly five things" +
  best-effort shell-interception scope note
- "Independent judge" → "context-fresh judge" (independence is of context,
  not model); "What This Costs" (both lanes, honest gate counts); uninstall
  section; coverage claims reconciled to the 3-tier normative table;
  docs/COMPARISON.md (source-verified, dated, caveats included); CONTRIBUTING
- ADR-0014 amendment (budget unit, interlocutor carve-out, merge hook);
  ADR-0015 drafted (transition validation — design approved, implementation
  scheduled)

### Wiring fixes
- Auto budget field canonical: `Loop Phase Budget` (session_context read a
  field nothing wrote; the loop's post-compaction resume degraded silently)
- Fast-lane interlocutor carve-out: human-authored board ACs count, with
  AC-traceability as the condition — the policy grant is no longer dead
- P3 tasks are selectable (triage ordering, end condition, gate — the fast
  lane's headline case was unreachable)
- Project ADRs write to project `docs/adr/` (never the plugin cache);
  exemplars still read from the plugin; init scaffolds `docs/adr/` +
  `docs/handover/`
- Agent roster: all 5 documented (gate-judge, phase-runner added to README,
  laws, SCOPE); personal paths genericized; deny messages namespaced
- Compaction counter: hook-maintained, injected after compaction, reset on
  startup/clear — the "2 compactions = handover" rule is finally evaluable

### Tooling
- harness_lint grows from 8 to 13 checks, every new one self-tested: manifest
  key allowlists, agent-roster parity, personal paths, hook-literal skill
  refs, plugin-root write-intent, field parity, claims parity
- `--check-blueprint <dir>`: custom-blueprint authoring validation, run by
  init; shipped blueprints now validate against the 11-section contract
- CI: real `claude plugin install` against two pinned CLIs (floor 2.1.50 +
  recent 2.1.160)
- Scenario runners renamed (`test_*` → `scenario_*`) — `pytest hooks/tests/`
  no longer collects zero and reads green

## [1.1.1] — 2026-07-08

Hotfix: the documented install command failed deterministically on Claude Code
2.1.50 — the CLI manifest validator rejects unrecognized plugin.json keys.

- **Manifest fix**: `$schema` and `displayName` removed from `plugin.json`
  (`$schema` also removed from `marketplace.json`). Install now succeeds on
  both the strict validator (2.1.50) and current CLIs.
- **harness_lint check 7**: manifest key allowlists — an unknown manifest key
  is now a lint finding (self-tested against both rejected keys).
- **CI**: new `plugin-install` job runs the README's exact install against two
  pinned CLI versions (strict floor 2.1.50 + recent 2.1.160) in an isolated
  `CLAUDE_CONFIG_DIR`. The linter said "clean" while the real CLI rejected the
  manifest — only a real install catches this class.

## [1.1.0] — 2026-07-08

The autonomy release: capivaOS gains an opt-in AUTO mode under a strict contract
(ADR-0014), while attended mode remains the unchanged default.

- **ADR-0014 autonomy contract**: gates route through your written approval
  policy + an independent judge in auto mode; exceptions escalate to
  `.board/approvals.md`. Hard-coded never-list: merge, P0/P1 gates, human-less
  spec approval, policy silence. Policy file is human-only (hook-enforced).
- **Isolation-first context**: fresh subagent context per phase — mandatory in
  auto mode, opt-in for attended via `Phase Isolation` in harness-config
  (default off; today's behavior preserved).
- **Budget invariants**: no uncapped auto runs (task + token limits always);
  clean parking at phase boundaries with standard handover docs.
- Guard allowlist gains `capiva-blueprints/` (project blueprint config is
  writable in any phase); PLAN.md and the self-dev CONTEXT.md are no longer
  tracked in the harness repo.

## [1.0.0] — 2026-07-07

First plugin release. capivaOS becomes an installable Claude Code plugin +
self-marketplace (previously: copy-directories template).

- Engine (skills, agents, hooks, rules, blueprints) ships in the plugin; project
  state is scaffolded by `/capiva:init` and stamped with a schema version
- Skills namespaced under `/capiva:*`
- SessionStart hook injects the laws + live sprint state (replaces CLAUDE.md/rules
  auto-load); inert in projects without `.board/`
- Windows-safe polyglot hook dispatcher; a missing interpreter or script can
  never block a session
- Self-update ritual: `/capiva:update` + `/capiva:update-project`
- Everything from the pre-plugin harness: 6-phase pipeline + fast lane,
  hook-enforced phase guards, machine-readable AC gating (acs.json), adversarial
  QA, tool-restricted dev/qa/arch agents, structured implementation reports
