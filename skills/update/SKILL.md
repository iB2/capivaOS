---
name: update
description: Update the capivaOS harness engine (plugin) safely — marketplace refresh, plugin update, reload, schema-skew check. Use when the user asks to update the harness/capiva plugin.
---

# Update — Harness Engine Update Ritual

Updates the capiva plugin to the latest released version. The order below is
load-bearing — do not improvise, skip, or reorder steps.

## Why the order matters

- `claude plugin update` resolves against the **locally cached** marketplace
  catalog; without a refresh first it can silently report "up to date" against
  a stale catalog.
- The running session keeps executing hooks from the OLD plugin directory until
  `/reload-plugins` — updating without reloading means the new version isn't
  actually active.
- Plugin updates never touch the project's scaffolded files (`.board/`,
  `docs/`); a schema check afterward is what keeps engine and project in
  lockstep.

## Ritual

### Step 1: Record the current version

```bash
claude plugin list --json
```

Note the installed `capiva` version. Also read `.board/harness-schema-version`
if present (the project's stamp).

### Step 2: Refresh the marketplace catalog

```bash
claude plugin marketplace update capiva
```

If this fails ("marketplace not found"): the marketplace isn't registered —
run `claude plugin marketplace add iB2/capivaOS` and retry.

### Step 3: Update the plugin

```bash
claude plugin update capiva@capiva
```

`plugin update` takes the marketplace-qualified plugin id (`<name>@<marketplace>`) — bare
`claude plugin update capiva` fails with `Plugin "capiva" not found`. Defaults to `--scope user`; pass
`--scope <user|project|local>` if the plugin is installed elsewhere.

If the `claude` CLI is unavailable in this environment, give the user the
interactive fallback: `/plugin` → Marketplaces → capiva → update, then continue
from Step 4.

### Step 4: Reload

Tell the user to run `/reload-plugins` (or run it if invocable) — hooks, skills,
and agents switch to the new plugin directory without a session restart.

### Step 5: Schema-skew check

Compare the NEW plugin version (`claude plugin list --json`, or
`${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json` after reload) against
`.board/harness-schema-version`:

- **Equal** → done.
- **Stamp older** → invoke `/capiva:update-project` to migrate the scaffolded files.
- **No stamp** (pre-1.0 or legacy project) → recommend `/capiva:init` (it re-runs
  safely and stamps without overwriting).

### Step 6: Report

```
capivaOS updated: [old] → [new]
Project schema: [current | migrated via /capiva:update-project | n/a]
Changelog highlights: [read ${CLAUDE_PLUGIN_ROOT}/CHANGELOG.md — top entry]
```

## Failure handling

Any step fails → STOP. Report the exact command, its output, and the
remediation from that step. Do not continue the ritual past a failed step —
a half-updated harness (new catalog, old plugin; or new plugin, stale hooks)
is worse than an old one.

## Rules

- **Never migrate project files here.** That's `/capiva:update-project`'s job, with its own confirmation gate.
- **Never update mid-phase without saying so.** If sprint-state Phase ≠ IDLE, tell the user an engine update mid-task is usually fine (engine is backward-compatible within a major version) but a SCHEMA migration mid-task is not — update-project will enforce its own gate.
- **Auto-update note**: users can enable per-marketplace auto-update (`/plugin` → Marketplaces → capiva → Enable auto-update); this ritual remains the explicit, verifiable path.
