# ADR-0018: Workflow-Agnostic Base Skills — Workflows Compose, They Don't Mutate

**Status**: Accepted (2026-07-14, maintainer directive during the RFN merge).
**Context**: the RFN epic (ADR-0017 + the ADR-0014 clustered-mode amendment) shipped the first
*additional* workflow (batch-refine / clustered mode) alongside the original attended sprint. Building
it, workflow-specific rules were **inlined into base skills** — an opt-in `context-answerer` step
inside `grill-spec`, and an "auto/clustered-mandatory reinforcement" rule inside `test-verify`. They
were default-safe, but they coupled reusable base skills to one workflow.

## The problem this prevents
The harness is heading toward an **ecosystem of workflows** over the *same* skills (attended sprint;
grill-sprint; auto execution; and more to come). If each new workflow edits the base skills, the base
skills accrete `if this-workflow / if that-workflow` conditionals until they are unreadable, un-reusable,
and every workflow risks regressing the others. A base skill edited for workflow #1 is a landmine for
workflow #2.

## Decision
**Base skills are workflow-agnostic. Workflows compose them.**

1. **Base skills** — `grill-spec`, `plan`, `implement`, `test-verify`, `finish` — do their one job the
   same way regardless of which workflow invokes them. They contain **no workflow-specific
   conditionals**. `grill-spec` is a pure adversarial interview; `test-verify` is two-agent testing
   with a config-optional second reviewer; etc.
2. **Workflows** — attended `/capiva:sprint`, grill-sprint `/capiva:refine`, auto `/capiva:auto`, and
   future ones — **compose** base skills and own their own rules. A workflow may *interpose* around a
   base skill (e.g. `/capiva:refine` inserts the `context-answerer` between `grill-spec`'s
   question-generation and human-answering) or *impose* a requirement on it (e.g. `/capiva:auto`
   requires the second reviewer + the reinforced gate-judge at the quality gate).
3. **Placement rule**: a rule used by exactly one workflow lives in that workflow's skill, never in a
   base skill. A rule shared by all workflows may live in the base skill (or a law/ADR).
4. **Agents** (dev, qa, arch, gate-judge, phase-runner, context-answerer) are likewise composed; an
   agent applies its full method whenever invoked — the invoking workflow decides *when*.

## Consequences
- **RFN-009 (this task) is the first application**: the `context-answerer` interposition + decision-log
  write move out of `grill-spec` into `/capiva:refine`; the "reinforcement mandatory when unattended"
  rule moves out of `test-verify` into `/capiva:auto`. No behavior changes — the workflows still get
  the same behavior, sourced from the workflow layer.
- Base skills stay small and legible; a new workflow is a new composition, not a base-skill edit.
- Cost: a workflow that interposes mid-base-skill (like the answerer) must describe the composition in
  its own skill rather than flip a flag — slightly more prose in the workflow, but the base stays clean.
- Revisit when: a base skill needs a genuine extension *point* that several workflows share — then add
  a single generic hook to the base skill (documented as generic), not a per-workflow conditional.

Related: [ADR-0017](0017-context-answerer-contract.md) (the answerer), the
[ADR-0014](0014-autonomy-contract.md) clustered-mode amendment (the workflow), and
[ADR-0009](0009-machine-readable-ac-gating.md) amendment (the reinforcement the auto workflow imposes).
