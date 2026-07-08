# Changelog

All notable changes to the capivaOS harness. Versions follow semver; users
receive updates only when the version in `.claude-plugin/plugin.json` is bumped.
Schema-affecting changes MUST land with a matching migration row in
`skills/update-project/SKILL.md`.

## [1.2.0] — 2026-07-08

The honesty release: the 2026-07-08 external audit (6 evidence reports) found
that "mechanically enforced" claimed more than the hooks delivered — and that
the audience this product courts would find the gap in minutes. 1.2.0 closes
the enforcement holes, re-segments every claim, and converts each audited bug
class into a lint check so the class cannot recur. 17 tasks (AUD-001..017),
one PR each.

### Enforcement (phase guard)
- **Kill-switch protected**: `.state/phase-guard-off` is HUMAN_ONLY — an agent
  can no longer disable its own guard (the audit's top code finding)
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
  refs, plugin-root write-intent, field parity (HARN-005), claims parity
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
