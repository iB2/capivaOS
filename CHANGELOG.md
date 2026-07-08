# Changelog

All notable changes to the capivaOS harness. Versions follow semver; users
receive updates only when the version in `.claude-plugin/plugin.json` is bumped.
Schema-affecting changes MUST land with a matching migration row in
`skills/update-project/SKILL.md`.

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
