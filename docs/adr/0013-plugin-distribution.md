# ADR-0013: Plugin Distribution — Engine/State Split, Self-Marketplace, Session Injection

## Status

Accepted

## Context

Through v0 (PRs #5, #10–#15) the harness was distributed as a template: adopters
copied `.claude/`, `.board/`, `docs/`, `templates/` into their repos. That model
has no update story — every adopter fork diverges immediately, fixes never
propagate, and "keep session residue out of template files" required a manual
cleanup gate (HARN-010). Meanwhile Claude Code's plugin system matured into the
ecosystem-standard distribution channel: versioned installs, per-marketplace
auto-update, a non-interactive CLI (`claude plugin install/update`), and
platform-enforced tool allowlists for agents.

Three constraints shaped the port:

1. **Plugins cannot ship always-loaded context.** A plugin's CLAUDE.md is
   ignored by design; there is no plugin `rules/` concept. The laws must reach
   every session some other way.
2. **The plugin cache is read-only and versioned.** Mutable project state
   (board, sprint-state, specs) cannot live in the plugin; `${CLAUDE_PLUGIN_ROOT}`
   changes on every update.
3. **Plugin hooks fire in every enabled project, on machines we don't control.**
   Anthropic's own plugin shipped broken on Windows by hardcoding `python3`;
   and our own migration live-fire showed a missing hook script exits python
   with code 2 — indistinguishable from a deliberate PreToolUse deny, which
   deadlocks the session (the guard denied its own author, again).

### Options Considered

**Option A: Stay a template repo, improve the copy script**
- Pro: No namespacing, no cache constraints, works on any Claude Code version.
- Con: The update story remains "diff by hand"; the audit's distribution goal
  (install/maintain/update with one command) is unmet.

**Option B: npx installer CLI**
- Pro: Real versioning via npm; can scaffold and migrate with arbitrary logic.
- Con: A second toolchain (Node) and a custom installer to maintain; Claude Code
  users already have a native package manager for exactly this — the plugin system.

**Option C: Plugin + self-marketplace, engine/state split (chosen)**
- The repo IS the plugin and its own marketplace (`.claude-plugin/marketplace.json`,
  `source: "./"`). Engine (skills, agents, hooks, rules, blueprints) ships in the
  plugin; `/capiva:init` scaffolds mutable state from `project-template/` into the
  adopter repo and stamps `.board/harness-schema-version`.
- Pro: Two-command install, one-command update, team pinning via checked-in
  settings, air-gapped installs from a local clone.
- Con: All skills are namespaced (`/capiva:sprint`); the always-loaded rules
  model dies (see Decision 2); we own the scaffold-migration problem.

## Decision

**Option C**, with these load-bearing mechanisms:

1. **Engine/state split.** Plugin = read-only versioned engine. Project =
   `.board/`, `docs/` artifacts, `PLAN.md`, stamped with the schema version.
   In the harness repo itself, the root `.board/` and root `docs/specs|reports|
   tech-context|handover` are GITIGNORED — the live dogfooding workspace is
   pristine-by-construction, replacing HARN-010's restore-before-merge gate.
2. **SessionStart injection replaces always-loaded rules.** `session_context.py`
   injects `rules/laws.md` + the live sprint-state Current Task block on
   startup/clear (~3K tokens), a credo-only reminder on compact, and a
   schema-skew nudge. It is inert in projects without `.board/` — a user-scope
   install adds zero noise to unrelated repos. This completes ADR-0011's
   trajectory: the always-loaded layer is now ~3K tokens, paid only in harness
   projects.
3. **The dispatcher absorbs environment failures.** `run-hook.cmd` is a CMD/sh
   polyglot that resolves `py`/`python`/`python3` per platform and exits 0 when
   the interpreter OR script is missing. Harness hooks signal decisions via
   stdout JSON only — exit codes carry no meaning, so a broken environment can
   never block a session. (Enforcement degrades to prose guards; SECURITY.md
   documents fail-open as a feature.)
4. **Deterministic self-update.** `/capiva:update` encodes the ritual
   (marketplace refresh → plugin update → reload → skew check);
   `/capiva:update-project` owns forward-only, idempotent, logged migrations of
   scaffolded files, gated on confirmation mid-pipeline. `bump_version.py`
   makes "schema change without migration row" release-blocking, and lint
   check 7 keeps the manifests honest (name parity, single version source).
5. **Explicit semver releases.** Users update only when Capiva cuts a version;
   pushing commits changes nothing. Channel hardening (tag/SHA pinning,
   community-catalog SHA pinning) is documented in SECURITY.md.

## Consequences

- Install: `/plugin marketplace add iB2/capivaOS` + `/plugin install capiva@capiva`
  + `/capiva:init`. Update: `/capiva:update` (or auto-update opt-in). "Update the
  harness" is now a deterministic skill, executable by the agent itself.
- Every skill invocation gains the `capiva:` prefix — all cross-references were
  rewritten, and lint now rejects un-namespaced or bare-engine-path references.
- The copy-mode template is retired; legacy installs migrate via `/capiva:init`
  with a strict ordering rule (settings.json first, old hook scripts survive
  until session restart) learned from the live-fire deadlock during this port.
- The harness repo remains its own consumer via `.claude/settings.json`
  registering the same hooks from the repo root (dev mode = dogfooding daily).
- Cost accepted: two docs surfaces (plugin-root refs in engine content,
  file-relative in repo docs), and a migrations table that must grow with every
  schema-touching release — enforced mechanically, not by memory.
- Revisit when: Claude Code adds native always-loaded plugin context or plugin
  scaffold/migration primitives — Decisions 2 and 4 shrink accordingly.

---

## Amendment (2026-07-09 — guard liveness)

A production-readiness review found the dispatcher shipped mode 0644 (no
exec bit) and shebang-less. On POSIX, Claude Code's bare-path invocation of
a non-executable dispatcher fails before any hook `.py` runs — so the entire
enforcement layer was silently absent for non-Windows adopters, and both CI
paths masked it (scenario tests `sh`-prefix the file; the install job never
fires a hook). Fix: the exec bit is now committed (`git update-index
--chmod=+x`), `.gitattributes` still forces LF, and a CI job fires the hook
by bare path on Linux/macOS — the empirical proof, not an assumption.

Deeper lesson (Principle: silence != healthy): a guard that can be silently
absent needs a proof-of-life. phase_guard now writes `.state/guard-heartbeat`
on every enforced invocation; session_context warns when a task is active
with no heartbeat; `/capiva:auto` refuses autonomy without one.
