# ADR-0017: The Context-Answerer Contract — Dispositive-or-Route, Never Suggest

## Status

Accepted (grill interview with the maintainer, 2026-07-13, eight forks resolved).
Rationale record: [docs/rfn-loop-engineering-deliberation.md](../rfn-loop-engineering-deliberation.md)
(the full design journey — research, pivots, and why each alternative was rejected).
Part of the **cluster-HITL** capability: the *oversight* half is the clustered-mode amendment to
[ADR-0014](0014-autonomy-contract.md); the *reinforcement* half is the RFN-006 amendment to
[ADR-0009](0009-machine-readable-ac-gating.md); this ADR is the *new mechanism*.

## Context

The batch-refine / clustered oversight mode (ADR-0014 amendment) front-loads grilling for the whole
board into an attended session, then runs execution unattended. The bottleneck it targets is the
maintainer's per-task context-switching, not the gates themselves. But a full-board grill re-asks a
lot of questions the project has *already decided* elsewhere (an ADR, a CONTEXT term, an existing
spec). Making the human re-answer those is the friction we want gone.

A **context-answerer** triages the grill's questions: where the documentation *already* decides a
question, it answers from the citation; where it does not, it routes to the human. This is Matt
Pocock's "Grill-With-Docs" taken to its logical end — if you grill *with* docs, the docs can answer
some of the grilling.

The danger is precise and must be named. The grill is *adversarial by design*: its job is to surface
ambiguity and force decisions. An LLM "answering from context" will confidently resolve genuine forks
a human would have flagged — the confident-but-wrong agent. Worse, in the clustered mode there is **no
human quality gate mid-run**, so a wrong auto-answer becomes an approved spec fact, is faithfully
implemented, passes its own (wrong) ACs, and reaches a PR. **The answerer sits UPSTREAM of the entire
checker stack** (the acs.json gate, the gate-judge, the QA agent, the reinforcement layer of RFN-006):
all of those protect against a half-assed implementation of a *good* spec; none protects against a
faithful implementation of a *bad* spec. The answerer's error rate is therefore the quality floor for
everything downstream, and its only backstops are the human's spot-check at approval and the
end-of-run review. That single fact drives every decision below toward conservatism.

### Options Considered

**Axis 1 — When may the answerer answer?**

**Option A: Confidence-graded auto-answer**
- The answerer scores its confidence and auto-answers above a threshold.
- Pro: resolves more, asks the human less.
- Con: "confidence" is exactly what a confident-wrong model miscalibrates; upstream-of-checker means
  the miscalibration is un-caught. Rejected.

**Option B: Dispositive-or-route (chosen)**
- Auto-answer *only* when a citation textually forecloses **this** question with no room for a
  reasonable human alternative. Any case that requires *reasoning from* the docs rather than *quoting*
  them → route. "Better matches the architecture" is a banned inference channel: matching is a
  judgment, not a lookup.
- Pro: the answerer never decides — it reports decisions already made; safe to be upstream.
- Con: resolves less (only the genuinely-settled); the human still faces the hard forks — which is the
  correct outcome (human time goes to irreducible judgment).

**Axis 2 — How does the answerer present a routed question?**

**Option A: Route with a recommended pick + rationale**
- Pro: fastest for the human to rubber-stamp.
- Con: **anchoring / automation bias** — the human approves the machine's pick and *believes* they
  judged. Strictly worse than no HITL: it launders a machine decision as a human approval, wearing the
  human's signature. Rejected.

**Option B: Frame the fork; recommend only as far as citations reach (chosen)**
- Route Type-1 (undocumented) questions as *framed forks* — options + trade-offs, no pick. On Type-3
  (documented-adjacent) the answerer may offer a **citation-bounded lean**, but it must (a) label the
  line where citation ends and extrapolation begins, and (b) **steelman the alternative it is
  rejecting**. No unopposed suggestions, ever.

**Axis 3 — Do human answers feed back into the docs?**

**Option A: Auto-promote answers to project documentation**
- Pro: the same question is auto-answerable next time; the undocumented surface shrinks.
- Con: a *local* one-off decision amplifies into a *false global rule* — next run the answerer cites
  it as dispositive and auto-answers a question that deserved re-litigation, and never escalates
  again. Self-inflicted, compounding confident-wrong. Rejected as a single tier.

**Option B: Two-tier write-back (chosen)**
- Task-scoped **decision-log** (`.board/decisions.md`, auto, records rationale + constraints, NOT a
  bare verdict) is *non-dispositive* — surfaced next time as prior art, never as auto-answer authority.
  The *only* path to dispositive authority is a **human** promoting the decision to an ADR / CONTEXT
  term. Convergence is kept; amplification is blocked.

## Decision

The context-answerer is a **read-only agent** (Read/Grep/Glob tool allowlist per ADR-0012) so it
mechanically cannot fabricate artifacts; its proposed answers are written only by grill-spec inside a
guard-legal phase. It triages every grill question into one of three kinds:

| Kind | Definition | Move |
|------|-----------|------|
| **Type 2 — locally ambiguous, globally documented** | a standard question the project already decided in a live ADR / CONTEXT term / spec | **auto-answer as a *finding*** — cited, dispositive |
| **Type 3 — documented-adjacent** | docs constrain but do not decide; answering needs reasoning | **route** with a citation-bounded lean + mandatory steelman |
| **Type 1 — genuinely undocumented** | no doc decides it | **route**, framed fork only |
| **contradiction** | task intent conflicts with a documented decision | **red-flag escalation** (the answerer as documentation-consistency adversary) |

**The six invariants (binding; do NOT relax without re-grilling — each is "no concessions" at a
different seam):**

1. **Dispositive-or-route.** Auto-answer only on a citation that forecloses the question; under any
   doubt, route. (It is upstream of the checker and un-backstopped — conservatism is non-negotiable.)
2. **The write-back loop must be mechanically forced to close, or it is not built.** A no-orphan lint
   invariant on `.board/decisions.md` + a surfaced read-back metric (RFN-005); if read-back stays ≈ 0,
   the write-back is removed. Half a loop that doesn't close is the worst outcome.
3. **Generation stays context-blind to answer-availability; the batch flow WRAPS grill-spec, never
   forks it.** The full adversarial question set is the contract; the answerer filters *presentation*,
   never *generation*. A grill that asks fewer questions over time is a rubber stamp, not a smarter
   grill.
4. **Cite only live docs; honor supersession.** A superseded ADR is not authority; promotion marks the
   superseded entry `retired`.
5. **"Approved" itemizes findings (auto, cited) vs decisions (human).** Approval stays auditable and
   meaningful; the human actively decides every routed fork (that is the interlocutor moment — see the
   ADR-0014 clustered-mode amendment) and spot-checks findings; human-override rate is logged as the
   answerer's false-positive signal.
6. **Contradiction → red-flag.** A finding-vs-intent conflict is neither auto-answer nor routine route;
   it is surfaced as a flag.

**Placement:** per-task triage — the answerer runs *inside* each task's grill, between
question-generation and human-answering. A board-wide context-index pre-pass is a deferred
optimization, not v1.

## Consequences

- The answerer *reduces and clusters* the maintainer's grilling load to the hard forks; it does not
  eliminate it, and the residual is by design the highest-value decisions (the genuine architectural
  forks nobody wrote down). A grill session becomes *concentrated*, not *quick*.
- Because it is upstream of the checker, its correctness is guarded almost entirely by invariant 1 and
  by human approval (invariant 5). If invariant 1 is ever softened, the confident-wrong agent returns
  with no downstream net — hence the re-grill clause.
- The two-tier write-back makes the harness *learn*: every promoted decision shrinks next sprint's
  undocumented surface, converging the grill toward near-zero human questions — the honest payoff that
  justifies the mechanism's complexity.
- The answerer adds a *documentation-consistency* adversary the manual grill never was (nobody
  remembers every ADR) — recovering, in a different form, the serendipity a full manual grill provides.
- **The eval gate (RFN-002) is a hard precondition.** Nothing mechanical (this agent, the `REFINING`
  state, the write-back) ships until adversarial fixtures prove the dispositive bar holds — a
  tangential citation must resolve to *escalate*, not stretch. If the bar cannot pass, the capability
  falls back to a context-aware "smarter grill" (no new agent) and this ADR's mechanism is not built.
- Revisit when: Claude Code ships a native retrieval-grounded grilling primitive (collapse onto it, as
  ADR-0012/0013 did for agents/plugins), or the measured human-override rate shows the dispositive bar
  is mis-calibrated (tighten, do not loosen).
