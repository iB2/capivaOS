# Changelog

All notable changes to the capivaOS harness. Versions follow semver; users
receive updates only when the version in `.claude-plugin/plugin.json` is bumped.
Schema-affecting changes MUST land with a matching migration row in
`skills/update-project/SKILL.md`.

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
