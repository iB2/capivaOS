# Security

## What this plugin does on your machine — the full list

capivaOS ships hooks that Claude Code executes locally. Their complete behavior
is auditable in ~600 lines of dependency-free Python (`hooks/*.py`) plus one
~40-line shell dispatcher (`hooks/run-hook.cmd`):

- **`phase_guard.py`** (PreToolUse) — reads `.board/sprint-state.md`, prints an
  allow/deny decision as JSON to stdout. Nothing else.
- **`context-persistence.py`** (PreCompact/SessionStart/Stop) — reads board/git
  state, writes a session snapshot to `.state/` INSIDE your project. Nothing else.
- **`session_context.py`** (SessionStart) — reads the plugin's rules + your
  board, prints context JSON to stdout. Nothing else.

Security properties, by construction:

| Property | Meaning |
|----------|---------|
| **Zero network** | No hook or skill makes any network call. No telemetry, no analytics, no version-check phone-home, no remote code |
| **Zero dependencies** | Python standard library only. There is no package install step and no third-party supply chain |
| **Inert outside harness projects** | In any repo without a `.board/` directory, every hook exits silently with no output and no writes |
| **Fail-open** | Missing interpreter, missing script, unreadable state → hooks allow and warn, never block. The harness disables itself rather than break your project |
| **Project-scoped writes** | Hooks write only inside your project (`.state/`, `.board/`) — never to the plugin cache, your home directory, or elsewhere |

The PreToolUse hook necessarily *receives* tool inputs (commands, file paths)
from Claude Code to make its allow/deny decision. It inspects them in memory
and prints a decision; it stores and transmits nothing.

## Official distribution channels

Install only from:

1. **This repository as a marketplace**: `/plugin marketplace add iB2/capivaOS`
2. Anthropic's community catalog, if/where listed (entries there are screened
   and pinned to a commit SHA by Anthropic)

Anyone can fork this repo and republish a modified plugin under a similar name.
A plugin named "capiva" from any other source is not ours.

## Supply-chain posture

- **Explicit semver releases**: the plugin declares `version` in
  `.claude-plugin/plugin.json`, so installs update only when Capiva cuts a
  release — pushing commits alone changes nothing for users
- **Protected main**: changes land only via reviewed pull requests
  (CODEOWNERS-gated); CI must pass (lint, hook test suites, validators)
- **Pin harder if you want**: consumers can pin the marketplace to a tag
  (`/plugin marketplace add iB2/capivaOS@v1.0.0`) or an exact commit SHA in a
  private marketplace entry
- **Review before update**: `CHANGELOG.md` describes every release;
  `claude plugin details capiva` shows the component inventory and context cost

## Autonomy prerequisite

Auto mode (`/capiva:auto`, v1.1+) never merges. Since 1.2.0 the phase guard
denies the merge verbs mechanically in every phase and mode: `gh pr merge` in
any form, and `git push` whose target resolves to the default branch
(main/master — including `HEAD:main` refspecs, `--delete`, `--all`/`--mirror`).
Routes a PreToolUse hook cannot see (the GitHub web UI, GitHub MCP tools, a
bare `git push` while the default branch is checked out) are covered by branch
protection: `/capiva:init` checks it and offers to configure it; do not enable
auto mode on an unprotected branch. (The check uses YOUR `gh` authentication —
the plugin itself still makes no network calls.)

## Reporting a vulnerability

Open a GitHub Security Advisory on this repository (preferred), or a private
report to the maintainer via the contact on the GitHub profile. Please do not
open public issues for exploitable problems. You can expect an acknowledgment
within 7 days.

## Scope notes

**Shell write interception is best-effort by construction.** Since 1.2.0 the
phase guard applies *tool parity* to shell commands: a `Bash`/`PowerShell`
write to a path is denied exactly when a `Write` to that path would be. It
detects `>`/`>>` redirects, `tee`, `sed -i`, and `touch` targets, after
stripping quoted strings and heredoc bodies (so prose containing `>` can never
false-deny — the trade-off is that a quoted target is invisible). What it
deliberately does NOT claim to catch: `cp`/`mv`/`dd`, interpreter one-liners
(`python -c "open(...)"`), encoded commands, or anything built from shell
expansions. Perfect shell interception is impossible; partial and honest beats
silent. The write-tools path (`Edit`/`MultiEdit`/`Write`/`NotebookEdit`) and
the human-only files remain the hard surface, and Claude Code's own permission
system remains the security boundary.

- The harness is a development-process tool; it grants no capability beyond
  what Claude Code already has on your machine.
- Quality gates and phase guards are safety rails for code quality, not a
  security sandbox — Claude Code's own permission system remains the security
  boundary for tool use.
