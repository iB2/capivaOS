---
name: update-project
description: Migrate a project's scaffolded harness files (.board, docs skeleton, config) after a capiva plugin update changed the schema. Invoked by /capiva:update on version skew, or directly when the session-start hook flags skew.
---

# Update-Project — Scaffolded-File Migration

The plugin updates centrally; the files `/capiva:init` scaffolded into this
project do not. This skill closes that gap: it applies the migration steps
between the project's stamped schema version and the installed plugin version,
then re-stamps.

## Guard (MANDATORY)

1. Read `.board/harness-schema-version` (the stamp) and the plugin version from
   `${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json`.
2. **Stamp == plugin version** → report "Project schema already current ([version])."
   Change NOTHING. Done.
3. **No stamp** → this project predates stamping; recommend `/capiva:init`
   (re-runs safely, scaffolds only what's missing, stamps). Done.
4. **Stamp newer than plugin** → the plugin was downgraded; warn the user and
   STOP (migrations are forward-only).
5. Read `.board/sprint-state.md`: if Phase ≠ IDLE → **ask for explicit
   confirmation** before migrating ("A schema migration mid-task can invalidate
   the running plan. Migrate now, or finish the current task first?"). Silence
   is not approval.

## Migrations

Applied in order, each step from its version to the next. Every step must be
idempotent (safe to re-run) and must never destroy user content — additive
edits and format transforms only.

| From → To | Migration |
|-----------|-----------|
| 1.0.0 → 1.1.0 | No project-file migration required. Guard allowlist gained `capiva-blueprints/`; laws text updated (ships with the engine). OPTIONAL: `.board/harness-config.md` MAY add `- **Phase Isolation**: on|off` (absent = off). Re-stamp only. |

Maintainer note: when a release changes anything under
`${CLAUDE_PLUGIN_ROOT}/project-template/` or any field format that
`phase_guard.py` / `context-persistence.py` / `session_context.py` parse, add a
row here IN THE SAME release. A schema change without a migration row is a
release-blocking defect.

## Procedure

1. Run the Guard above.
2. For each row in Migrations between stamp and plugin version, in order:
   - Apply the described transform to the project files
   - Verify the transform (read back the changed file)
3. Write the plugin version to `.board/harness-schema-version`.
4. Update `.board/harness-config.md`: add/refresh `- **Migrated**: [ISO date] ([old] → [new])`.
5. Log in `.board/sprint-state.md` Phase History:
   `| [now] | -- | -- | -- | harness-migrated | schema [old] -> [new], [N] steps |`
6. Report:

```
Project schema migrated: [old] → [new]
Steps applied: [list or "none — stamp refresh only"]
Sprint state: [unchanged | note]
```

## Rules

- **Forward-only, additive-only.** Never delete user content; never downgrade.
- **Idempotent steps.** Re-running after a partial failure must be safe.
- **Mid-pipeline migration needs explicit consent.** Phase ≠ IDLE → ask first.
- **Every applied migration is logged** in Phase History — auditable like any transition.
