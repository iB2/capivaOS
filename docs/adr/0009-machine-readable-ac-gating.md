# ADR-0009: Machine-Readable AC Gating and Adversarial Verification

## Status

Accepted

## Context

The 2026-07-07 harness audit (finding F6.3) identified that the pipeline's weight
sits almost entirely BEFORE code exists: adversarial spec grilling, micro-task
planning, TDD enforcement. Verification AFTER code exists is comparatively weak —
three specific gaps:

1. **The AC coverage matrix is hand-maintained prose.** /test-verify copies
   acceptance criteria from the spec into a markdown table and fills in test names
   by hand. Nothing prevents an AC from being paraphrased, silently dropped, or
   marked ✅ without a test actually existing. The matrix LOOKS authoritative but
   is regenerated from conversation memory each time — exactly the failure mode
   Law 3 (artifact gating) exists to prevent.

2. **"Tests pass" is accepted as "the feature works."** The quality gate can go
   PASS without anyone ever exercising the built feature end-to-end — calling the
   endpoint, driving the UI, running the CLI. Unit and integration tests verify
   components; they do not verify that the assembled feature behaves as the spec
   describes. Anthropic's long-running-harness guidance is explicit that
   verification is the bottleneck for agent-built code: verify by driving the
   system, not just by its tests.

3. **The QA reviewer is prompted to confirm, not refute.** The QA role receives
   the implementation report and checks it — but a reviewer whose framing is
   "check that the claims hold" tends to find that they do. Agent self-review
   exhibits confirmation bias; the same agent lineage that produced optimistic
   claims will accept them.

The constraint: any fix must survive compaction and session boundaries (Law 3 —
disk artifacts, not conversation), must be auditable, and must not add a new
always-loaded rules burden.

### Options Considered

**Option A: Strengthen the prose rules only**
- Add "do not drop ACs" and "be skeptical" language to artifact-standards.md and qa.md.
- Pro: Zero new artifacts, zero tooling.
- Con: Prompt-level rules are exactly what the audit found insufficient — they
  degrade after compaction and are unverifiable after the fact.
- Con: A hand-maintained matrix remains hand-maintained; the failure mode is unchanged.

**Option B: Machine-readable AC list as a gating artifact (chosen)**
- /grill-spec emits `docs/specs/TASK-ID-acs.json` alongside the spec: one entry
  per AC with `id`, `text`, and `status` (`pending|pass|fail`). After spec
  approval, `id` and `text` are immutable — skills may only flip `status`.
  /test-verify generates the quality-report AC matrix FROM this file and writes
  verdicts back to it. `harness_lint.py` validates the schema.
- Pro: The AC list becomes a diskable, diffable contract. Dropping or rewording
  an AC is a visible file change, not a silent paraphrase.
- Pro: The matrix cannot disagree with the spec — it is derived, not transcribed.
- Pro: Schema is trivially lintable in CI (the harness already has a linter).
- Con: One more artifact to keep in sync when a spec is legitimately revised
  (mitigated: revision goes back through GRILL_SPEC, which regenerates the file).

**Option C: Full test-results integration (parse test runner output, auto-map tests to ACs)**
- Machine-verify AC status by parsing TRX/JUnit output and matching test names to AC ids.
- Pro: Strongest guarantee — status flips only when a matching test actually passed.
- Con: Requires per-blueprint test-output parsers (three stacks today, more later) —
  significant tooling surface for a template repo.
- Con: Couples the harness to test naming conventions it doesn't control.
- Deferred, not rejected: Option B's JSON schema is designed so a future parser
  can populate `status` mechanically.

## Decision

**Option B — machine-readable AC list, plus two verification-side changes that
need no new tooling.**

1. `docs/specs/TASK-ID-acs.json` is a first-class artifact of GRILL_SPEC,
   registered in sprint-state, gated by /plan (existence) and /finish (all
   `status: pass`). Immutable except `status` once the spec is approved.
2. /test-verify must exercise the built feature end-to-end (per blueprint
   §build-commands tooling — endpoint call, UI drive, CLI run) and record the
   evidence in the quality report before the verdict can be PASS. Component
   tests alone cannot flip an AC to `pass`.
3. The QA reviewer's briefing is inverted from confirmation to refutation: it
   receives the implementation report as a set of CLAIMS and is scored on
   finding the claim that doesn't hold. Option A's "be skeptical" phrasing was
   rejected as too weak; the refutation framing changes the reviewer's goal
   function, not just its tone.

Option C was deferred because per-stack result parsing is disproportionate
tooling for a template; the JSON contract leaves the door open.

## Consequences

- Every AC now threads through the pipeline as data: spec (prose) →
  `TASK-ID-acs.json` (contract) → quality report matrix (generated) → /finish
  gate (all pass). A dropped AC becomes a mechanical failure, not an oversight.
- The quality report gains a mandatory "End-to-End Exercise" section with
  reproducible evidence (command + observed output). PASS without it is invalid.
- QA review verdicts change shape: findings are refutations with evidence, and
  "CLAIMS VERIFIED" replaces "APPROVE" to keep the adversarial framing.
- `harness_lint.py` gains a schema check for `docs/specs/*-acs.json` — malformed
  or status-invalid files fail CI.
- Cost accepted: /grill-spec produces one more file, and spec revisions must
  regenerate it (enforced by the immutability rule routing changes through
  GRILL_SPEC).
- Revisit when: a blueprint gains a machine-parsable test-report format in CI —
  then Option C's auto-population becomes worth its tooling cost.

---

## Amendment (2026-07-13 — reinforcement layer for unattended execution, RFN-006)

The RFN clustered/auto modes defer the mid-run human quality gate, so the automated checker must
catch what the human would. In **auto and clustered execution only** (attended is unchanged — the
human *is* the check), the quality gate is reinforced:

1. **The gate-judge is MANDATORY at every quality gate** (not only policy-uncovered ones).
2. **Test-meaningfulness** — the gate-judge additionally asks, per AC: *does this test exercise the
   AC's behavior, or is it a tautology / green-but-empty?* A passing-but-vacuous test is an anomaly →
   ESCALATE. (The `scenario_*` rename already killed one green-but-empty class; this generalizes it.)
3. **Spec-conformance** — does the delivered work match the approved spec's **intent**, not just the
   letter of its ACs? Scope-shaving (AC technically met, spirit missed) → ESCALATE.
4. **Dual-review is MANDATORY** in these modes (promoted from the LOOP-008 optional second reviewer);
   any unresolved disagreement → ESCALATE.

**Honest scope (the boundary that keeps this from overclaiming):** this reinforcement protects against
a *half-assed implementation of a good spec*. It does **not** catch a *faithful implementation of a
bad spec* — that failure is upstream, and is the context-answerer's job ([ADR-0017](0017-context-answerer-contract.md),
proven by the RFN-002 gate). Neither substitutes for the other. The never-list is unchanged; these are
checks *within* the delegable remainder, not new delegations.
