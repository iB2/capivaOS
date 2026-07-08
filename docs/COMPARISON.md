# How capivaOS Compares

> **Method and date**: traction figures pulled from the GitHub API on
> **2026-07-08**; every mechanism claim below was verified by reading each
> repo's actual source (hooks, linters, gate logic) — not marketing copy.
> Numbers age; mechanisms age slower. If you find a row that is no longer
> true, please open an issue.

The spec-driven-development-for-agents category splits into two camps:
**prompt frameworks** (the discipline lives in text the model is trusted to
follow) and **mechanical harnesses** (some part of the discipline is enforced
by code that denies actions). capivaOS's bet is that both are needed: a full
SDD lifecycle *and* hooks with teeth.

| Tool | Stars (2026-07-08) | Mechanism (source-verified) | Blocking gates | Machine-readable ACs | Autonomy contract | Stack blueprints |
|---|---|---|---|---|---|---|
| [obra/Superpowers](https://github.com/obra/superpowers) | 249.5k | Prompt/skills; its one hook injects context at SessionStart — it denies nothing | Skippable (its own issue #528: Claude skips review) | No | Partial, no contract | No |
| [mattpocock/skills](https://github.com/mattpocock/skills) | 160.8k | Pure prompts; *explicitly anti-process-ownership* by philosophy | None, by design | No | No | No |
| [github/spec-kit](https://github.com/github/spec-kit) | 118.8k | Pure markdown; its own test docs note steps fire only if the LLM obeys | Skippable | Prose checklists | No | Agnostic by not prescribing |
| [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) | 50.2k | Hybrid; real Python, but the linter exits 0 by design; gates are LLM-adjudicated | Skippable by design | Partial (AD-n fields) | Closest analog (bmad-dev-auto) | Domain-agnostic, no blueprints |
| [claude-task-master](https://github.com/eyaltoledano/claude-task-master) | 27.8k | MCP task tracking; no gating | No | No | No | No |
| [gotalab/cc-sdd](https://github.com/gotalab/cc-sdd) | 3.5k | Agent Skills across 8 platforms; enforcement unverified | Unverified | No | No | No |
| [nizos/tdd-guard](https://github.com/nizos/tdd-guard) | 2.2k | **Real PreToolUse blocking** — TDD only | Yes (narrow) | No | No | No |
| AWS Kiro | proprietary | Paid IDE; spec artifacts + event hooks; no hard phase gate confirmed | Soft | No | No | Prompt templates |
| **capivaOS** | see repo | **Real PreToolUse phase guard** — the exact deny surface is [lint-locked to the code](../SECURITY.md) | 5 mechanically-denied surfaces + structurally-encouraged human gates | **Yes — `acs.json`** (ADR-0009) | **Yes — ADR-0014 never-list** | **Yes — 3 shipped** |

## The one-line positioning

> Spec Kit's lifecycle breadth, tdd-guard's mechanical teeth.

No tool in the scan combines full-pipeline mechanical gating + machine-readable
acceptance criteria + a written autonomy contract + stack blueprints, free/MIT.
The nearest single-axis rivals: tdd-guard (teeth, no lifecycle) and Spec Kit
(lifecycle, no teeth).

## What we do NOT claim

Honesty is the moat, so the caveats live here, in the comparison itself:

- **Every mechanical primitive we use is a documented, first-party Claude Code
  capability** — PreToolUse deny hooks, plugins/marketplaces, agent tool
  allowlists, Skills. Anthropic ships no opinionated SDD state machine; that
  packaging gap is the product. A capable team could replicate the mechanism
  in weeks — what they'd have to re-earn is the curation, the ADR trail, and
  the tested edge cases.
- **The deny surface is exactly five things** (lint-locked list in
  [SECURITY.md](../SECURITY.md)); everything else is structurally encouraged.
  Tools above marked "skippable" are not being mocked — most of capivaOS's own
  human gates are prompt-level too. The difference is we segment the claim.
- **The largest audience in this category disagrees with the premise.**
  mattpocock/skills (160k★) explicitly rejects process-owning frameworks.
  If you share that philosophy, capivaOS is not for you — see
  [docs/SCOPE.md](SCOPE.md) for what this deliberately is not.
- **Ceremony is real.** A full-lane task costs ~165K tokens of pipeline
  overhead and 4 blocking gates plus a grill interview (see README "What This
  Costs"). The fast lane and auto mode exist precisely because that price is
  wrong for small tasks.
