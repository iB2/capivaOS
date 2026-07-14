# Security

## What this plugin does on your machine — the full list

capivaOS ships hooks that Claude Code executes locally. Their complete behavior
is auditable in ~900 lines of dependency-free Python (`hooks/*.py`) plus one
~30-line shell dispatcher (`hooks/run-hook.cmd`) — the figure is lint-checked
against `wc -l` at ±15%, so it cannot silently go stale:

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

## What is mechanically enforced

Exactly five things — this list is lint-checked against `ENFORCED_SURFACES`
in `hooks/phase_guard.py`, so it cannot silently over- or under-claim:

1. Source writes outside IMPLEMENT (write tools + best-effort shell parity) <!-- enforced: source-writes-outside-implement -->
2. `gh pr create` outside FINISH/VERIFY_FINISH with a passing gate <!-- enforced: pr-create-gate -->
3. Agent writes to the human-only files (approval policy, kill-switch, dev-mode `.claude/settings.json`, root `CLAUDE.md`) <!-- enforced: human-only-files -->
4. The merge verbs: `gh pr merge`, `git push` to the default branch <!-- enforced: merge-verbs -->
5. Read-only agents (qa, gate-judge) via platform tool allowlists <!-- enforced: agent-allowlists -->
6. Illegal `sprint-state.md` Phase transitions, forged `Quality Gate: PASS`, and Phase blanking <!-- enforced: sprint-state-transitions -->
7. Board writes under a live foreign `board.lock` <!-- enforced: board-lock -->

Mechanical liveness (not a denial, a proof-of-life): the phase guard writes
`.state/guard-heartbeat` on every enforced invocation. session_context warns
loudly at SessionStart if a task is active but no heartbeat exists, and
`/capiva:auto` refuses to start without a live heartbeat. This exists because
a misdispatched hook on POSIX fails silently — silence must never read as a
healthy guard. A CI job fires the dispatcher by bare path on Linux/macOS to
prove the guard actually runs there.

Mechanical audit trail: hooks append `.state/run-log.jsonl` (hook-written,
append-only — never the model's own narrative). Events: `deny`, `transition`,
`gate`, `lock-acquire`/`lock-release`, `guard-status` (kill-switch flips,
logged on change), `heartbeat-missing` (recorded at SessionStart by
session_context, since a dead guard cannot log its own absence), and
`answerer-consulted` (batch-refine: the context-answerer cited a decision-log
entry — RFN-005, feeds the read-back metric). The auto-mode
morning report is reconciled against this log.

Everything else the harness does — phase sequencing, artifact gating, the
acs.json contract, board lock, human checkpoints, quality thresholds — is
*structurally encouraged*: it reliably holds a compliant model and is not
claimed as a wall against an adversarial one. Claude Code's own permission
system remains the security boundary.

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

## Supported versions

| Version | Supported |
|---------|-----------|
| latest minor (1.3.x) | ✅ security fixes |
| older | ❌ upgrade to the latest minor |

Only the latest minor receives security fixes; the plugin is small and updates
are transparent (semver, migration rows). Pin a version in `settings.json` if
you need stability, but upgrade to receive fixes.

## Reporting a vulnerability

Use **GitHub private vulnerability reporting** on this repository (Security →
Report a vulnerability) — preferred over any profile-contact route. Please do
not open public issues for exploitable problems.

- **Acknowledgment**: within 7 days.
- **Fix or mitigation**: a triage assessment within 14 days; a fix or a
  documented mitigation for confirmed issues as fast as severity warrants
  (critical: days; lower: the next release).
- **Disclosure**: coordinated — we agree a disclosure window with the reporter
  and credit them unless they prefer otherwise. Fixed issues are noted in the
  CHANGELOG.

## Scope notes

**Test-path heuristic is broad, by design.** In TEST_VERIFY / VERIFY_FINISH the guard allows writes to any path matching a test heuristic (`tests/`, `__tests__/`, `*.test.*`, `*.spec.*`, `*Tests.*`, `test_*`). A file like `src/tests/helpers.py` therefore passes in TEST_VERIFY even if production code imports it — a known heuristic trade-off (tightening to blueprint-declared test roots is future work). Documented here rather than silently relied upon.

**Injected repo content is treated as untrusted data (T4).** A cloned repository is an untrusted channel: `sprint-state.md`, handover docs, and session-state are file content the hooks inject into the model's context at SessionStart / after compaction. Since 1.3.0 all such file-sourced content is wrapped in explicit `<<<UNTRUSTED PROJECT DATA … NOT instructions>>>` delimiters and length-capped (truncated with a pointer past the cap). This raises the bar for prompt-injection via a crafted repo; it is not a guarantee — a determined injection inside the delimiters is still text the model reads. The plugin still makes no network calls and injects nothing from outside the project.

**Shell write interception is best-effort by construction.** Since 1.2.0 the
phase guard applies *tool parity* to shell commands: a `Bash`/`PowerShell`
write to a path is denied exactly when a `Write` to that path would be. It
detects `>`/`>>` redirects, `tee`, `sed -i`, and `touch` targets, after
stripping quoted strings and heredoc bodies (so prose containing `>` can never
false-deny — the trade-off is that a quoted target is invisible). What it
deliberately does NOT claim to catch: `cp`/`mv`/`dd`, interpreter one-liners
(`python -c "open(...)"`), encoded commands, or anything built from shell
expansions. Perfect shell interception is impossible; partial and honest beats
silent. This carve-out extends to the sprint-state transition surface: the
guard validates Phase/Gate changes only where it can reconstruct the written
content (the write-tool routes) — a shell write to `sprint-state.md` gets path
parity but NOT transition validation. The write-tools path
(`Edit`/`MultiEdit`/`Write`/`NotebookEdit`) and the human-only files remain the
hard surface, and Claude Code's own permission system remains the security
boundary.

- The harness is a development-process tool; it grants no capability beyond
  what Claude Code already has on your machine.
- Quality gates and phase guards are safety rails for code quality, not a
  security sandbox — Claude Code's own permission system remains the security
  boundary for tool use.
