# CapivaOS × Loop Engineering — Design Deliberation Record

> **Status:** the durable rationale record for the RFN epic — linked from
> [ADR-0017](adr/0017-context-answerer-contract.md) and the ADR-0014 clustered-mode amendment.
> Captured 2026-07-13; preserves the full reasoning (pivots and *why* we changed approach). The RFN
> tasks live on `.board/tasks.md`; the binding contract lives in the ADRs — this is the "why".
>
> **Scope of this doc:** the *journey* of the design conversation, the research it rests on, every
> place we changed our minds and the reason, and the final hardened design. Read top-to-bottom to
> understand not just *what* we decided but *why the rejected alternatives were rejected* — so a
> future session cannot quietly relax a hard-won invariant.

---

## 0. Origin

The trigger was a transcript from **The AI Automators** on "loop engineering" (the Boris Cherny /
OpenClaw "I don't prompt, I write loops" discourse). Bruno's ask, verbatim intent:

- Study the video, then do independent web research on the harness + loop combo.
- Assess whether adding a "loop" (as the video suggests) would help CapivaOS.
- The video implies loops **cut corners on HITL** (auto mode "runs without stopping to ask for
  permission") — so if we adopt anything, verify **no concessions** are made first.
- **Do not force it as an improvement.** Genuinely assess whether it helps Bruno's *actual* HITL
  bottlenecks, given he already runs long sessions successfully.
- CapivaOS has already **custom-built** an autonomy/goal capability — compare native features
  against it, and only recommend change that is a real improvement.

The deliberation then evolved well past "should we adopt /loop" into a concrete redesign of the
**grilling phase** — the core of the harness (adapted from Matt Pocock's "Grill-With-Docs").

---

## 1. Research findings (the factual base)

### 1.1 Anthropic's loop taxonomy (four levels)
Source: [Loop engineering](https://claude.com/blog/getting-started-with-loops). A loop =
*"agents repeating cycles of work until a stop condition is met."*

| Level | Native primitive | Checker / stop condition |
|---|---|---|
| L1 turn-based | inner agent loop | Claude self-judges completion |
| L2 goal-based | `/goal` | a **Stop hook** + small fast model (Haiku) that **reads the transcript only — cannot run tools/files**; soft turn cap in prose |
| L3 time-based | `/loop`, `/schedule`, routines | cron/interval trigger; stops on completion/cancel |
| L4 proactive | schedule + goal + workflows + **auto mode** | event/schedule triggered, goal-stopped, runs until turned off |

### 1.2 `/goal` internals (the key technical finding)
Source: [/goal docs](https://code.claude.com/docs/en/goal). `/goal` is literally **a wrapper around
a session-scoped prompt-based Stop hook.** After each turn, the condition + conversation is sent to
the small fast model (default Haiku); returns yes/no + a reason. Critically: *"It does not call
tools, so it can only judge what Claude has already surfaced in the conversation."* Turn bounding is
natural-language prose (`"or stop after 20 turns"`), i.e. a **soft** cap.

### 1.3 Auto mode is NOT "skip all prompts"
Source: [auto-mode config](https://code.claude.com/docs/en/auto-mode-config). It routes tool calls
through a **classifier that blocks anything irreversible, destructive, or aimed outside your
environment**, with `hard_deny`/`soft_deny`/`allow` tiers. And: *"`permissions.deny` in managed
settings… blocks the action before the classifier is consulted and can't be overridden."*
`classifyAllShell:true` closes the "narrow Bash allow rule leaks a destructive arg" gap.

### 1.4 Harness engineering (Martin Fowler)
Source: [Harness engineering](https://martinfowler.com/articles/harness-engineering.html).
Inner vs outer harness; **guides/feedforward vs sensors/feedback**; **computational** (deterministic:
tests, linters, type-checkers — cheap, run every change) vs **inferential** (LLM-as-judge — expensive,
selective) checks. Human role = *steer the harness*, direct judgment where it matters. "Delete
redundant scaffolding as agents improve."

### 1.5 Ralph Wiggum loop
A bash `while` loop feeding a fresh-context prompt each iteration; deterministic stop. Relevant as the
"hard cap done in code" contrast to `/goal`'s soft cap.

---

## 2. Mapping the research onto CapivaOS (the first conclusion)

**Verified via a full repo map** (state machine, hooks, auto skill, gate-judge, evals, lint).

CapivaOS already implements the loop taxonomy — with a **stronger checker** than the native
primitives:

| Level | CapivaOS equivalent | Verdict |
|---|---|---|
| L1 | inherited (runs inside Claude Code) | have |
| **L2 goal** | state machine + `gate-judge` (context-fresh adversarial judge) + `acs.json` AC contract + **hard** budgets | **stronger than `/goal`** (Haiku/transcript-only/soft-cap) |
| L3 time | `/capiva:auto` is cron/routine-schedulable, made safe by a mandatory entry gate | have (no native `/loop` needed) |
| **L4 proactive** | `/capiva:auto` *is* a purpose-built proactive loop | have |

Key architectural facts that matter downstream:
- **The never-list is a `PreToolUse` deny** (`hooks/phase_guard.py`, registered in `hooks/hooks.json`
  on `Edit|MultiEdit|Write|NotebookEdit` and `Bash|PowerShell`). PreToolUse hooks fire in **every
  permission mode, including auto mode.** → **Native auto mode cannot bypass the merge gate, phase
  gates, or human-only-file locks.** (This is why `/goal` is disabled under `disableAllHooks` —
  hooks are a separate layer from permission mode.)
- ADR-0014 already frames autonomy as *"a re-routing of human judgment… never its removal."* Option
  "gates off in auto mode" was explicitly **rejected**.
- The checker is layered: computational (guard 104 scenarios, lint 19 checks, coverage floors, CI)
  + inferential (gate-judge, qa agent, arch, two-agent test pattern). Philosophy, verbatim from
  `evals/README.md`: *"rules-based feedback first, LLM-as-judge last."*
- Bruno's real usage (from the board): attended **grill → standing approval for the epic →
  autonomous implement→verify→PR → merge gate**. The gates aren't the bottleneck; the friction is
  per-tool permission clicking during the autonomous middle.

### 2.1 First recommendation (before the redesign discussion)
- **① Adopt native auto mode *under* the never-list** — the one zero-concession HITL-friction win
  (removes routine per-tool prompts; can't cross the never-list). Ship a recommended
  `autoMode.environment` snippet; document layering in SECURITY.md; have `/capiva:auto`'s entry gate
  detect + recommend it.
- **② `classifyAllShell:true`** as defense-in-depth.
- **③** consider Monitor/Channels (event-driven vs polling) for the auto driver.
- **④** self-audit for redundant scaffolding.
- **Reject:** replacing gate-judge with the weaker native `/goal`; always-on `/loop` over the
  harness (erodes identity — SCOPE.md: "ends at PR", un-specced tasks skipped); weakening the merge
  gate or the attended grill (load-bearing quality mechanisms, not friction).

---

## 3. Bruno's workflow idea, and the design pivots

Bruno then proposed the real target: **cluster HITL instead of scattering it.** Front-load all
grilling for the whole board in 1–2 attended sessions, run execution unattended, review everything
once at the end. This is the **L4 proactive loop done correctly for a spec-driven harness** — and a
quality *upgrade* over today's blanket standing-approval (which approves specs sight-unseen with
"full artifacts to follow"). The reframe that anchors everything:

> **We are not removing HITL. We are clustering it** — into a grill-cluster up front and a
> review-cluster at the end — so Bruno's attention goes only to irreducible judgment, not to
> per-task gate-clicking.

### 3.1 Pieces: reuse vs new (established early)
| Idea | Status | Action |
|---|---|---|
| Autonomous backlog execution, escalate-don't-guess | ✅ `/capiva:auto` | reuse as engine |
| "Report when done" | ✅ `auto-run-[date].md` + `run-log.jsonl` | enrich into a **review packet** |
| Spec/plan approval only on deviation | ✅ never-list: policy-silence → escalate | tighten deviation detection |
| **Batch-grill the whole board** | ❌ grill is per-task | **new** — a batch phase |
| **Context-search auto-answerer** | ❌ (CONTEXT.md/ADRs/specs exist to search) | **new** — the dangerous one |
| **Reinforcement layer** (anti-half-assing) | ⚠️ partial | **enrich** — the crux |

### 3.2 PIVOT A — "run grill outside the sprint to avoid locking state?"
**Bruno's instinct: smart. His mechanism: rejected.** Grill-all is a *different activity* from
per-task execution and shouldn't hold a per-task `Phase=GRILL_SPEC` lock across a batch — **right.**
But running it *outside* the harness violates Law 1 ("the state machine governs all") and forfeits
**approval provenance**: when `/capiva:auto` later reads `Spec Approved: Yes`, nothing trustworthy
set it. Also, without a legal transition edge for "grill task 2 while task 1 is TRIAGE," the
transition guard (ADR-0015) would deny it anyway.
**Resolution:** a **board-level `REFINING` state *inside* governance** — the machine legitimately
sits there while producing + approving all backlog specs, then hands off to the execution loop.
Decoupling achieved; provenance preserved.

### 3.3 PIVOT B — plan vs spec front-loading
Split what Bruno lumped as "plan and spec":
- **Spec** → fully approved in the batch grill (high judgment, front-loaded).
- **Plan** → generated **just-in-time** in the autonomous run; auto-proceeds *unless it can't honor
  the approved spec* → then escalate. (Up-front plans go stale as earlier tasks change the tree.)

### 3.4 The reinforcement layer (the crux — price of removing the mid-run gate)
When the mid-run human quality gate is removed, the automated checker must catch what the human
would. Enrichments required for the unattended batch mode:
1. **gate-judge mandatory on every task's quality gate** (today: only policy-uncovered gates), and
   extended from arithmetic to **test-meaningfulness** ("does this test exercise the AC's behavior,
   or is it a tautology?").
2. **Spec-conformance check** — delivered work matches the approved spec's *intent*, not just its
   ACs (catches scope-shaving).
3. **Dual-reviewer (LOOP-008) promoted from optional to mandatory** in batch mode.
4. **Aggressive deviation detection** — any ambiguity the grilled spec didn't resolve → park +
   escalate, never improvise.
- Honest residual (SCOPE.md already admits it): per-task auto quality is *somewhat below* an attended
  session. The **end-of-run review is the backstop that closes the gap** — that review is HITL,
  deferred and batched, not removed.

---

## 4. The context-answerer — the deep dive (most iteration happened here)

### 4.1 PIVOT C — the "suggest how to pick" veto (anchoring)
Bruno initially wanted: on an unanswered question, route to the human **with a suggested pick +
rationale**. **Vetoed as written.** The grill's purpose is to force *human* thought. A pre-loaded
recommendation causes **anchoring / automation bias** — the human rubber-stamps the machine's pick
and *believes* they judged. That's strictly worse than no HITL: it launders a confident-but-wrong
machine decision as a human approval (the exact failure the video warns about, now wearing Bruno's
signature).
**Safe form:** on a routed item the agent **frames the fork, it does not pick.** If a recommendation
is given, it must be paired with a **mandatory steelman of the alternative** — no unopposed
suggestions, ever.

### 4.2 PIVOT D — the premise correction (this *strengthened* the design)
Bruno's premise: *"if nothing were undocumented, grill would have no questions; so every question
presupposes ambiguity"* → implies the answerer can only ever route, which would collapse the
auto-answer branch. **Too strong.** Grill questions come in **three kinds**:

| Kind | What it is | Answerer's move |
|---|---|---|
| **Type 2 — locally ambiguous, globally documented** | grill re-asks a standard question the project already decided in an ADR/CONTEXT term | **auto-resolve** — dispositive citation |
| **Type 3 — documented-adjacent** | docs constrain but don't decide; agent would have to *reason* | **route, with a citation-bounded lean** |
| **Type 1 — genuinely undocumented** | no doc decides it; a real fork | **route, frame only** |

**The answerer's real job is Type 2** (locally ambiguous, globally documented) — the redundancy worth
deduping. This validated the auto-answer branch instead of collapsing it.

### 4.3 PIVOT E — "finding," not "suggestion"; recommendation ≤ citation
- **Type 2 auto-answer is a *finding*, not a suggestion:** "the docs already decided this: ADR-0002
  §3 — <quote>." The agent isn't deciding; it's *reporting a decision already made.* No anchoring
  risk, because no human judgment is being anchored.
- **"Matches the architecture" is an inference channel, banned as a bar.** The bar is: *the citation
  textually forecloses THIS question, with no room for a reasonable human alternative. Under any
  doubt → escalate.* If the agent must *reason from* docs rather than *quote* them → route.
- On routed items: **recommendation is allowed only as far as citations reach.** The moment it
  crosses into extrapolation it must **label that line** ("citation ends here; the rest is my
  extrapolation") **and steelman the rejected alternative.**

### 4.4 PIVOT F — self-enriching write-back + the amplification landmine
Bruno's idea: after the human answers a routed question, **log the decision and write it back to the
docs** so the same question is Type-2 next time. **Best idea in the thread** — it makes the
undocumented surface shrink every sprint (compounding convergence), and it's not new machinery
(grill-spec already writes CONTEXT.md terms + ADRs).
**Landmine:** auto-promoting a *local* one-off decision into "architecture" can amplify it into a
**false global rule** — next sprint the answerer cites it as dispositive and auto-answers a question
that deserved re-litigation, and it never escalates again (self-inflicted, compounding confident-wrong).
**Fix — two tiers of write-back:**

| Tier | Authority | Who promotes |
|---|---|---|
| **Decision log** (task-scoped: "chose X for task-7 *because* <constraints>") | **surfaced** as prior art next time — *not* auto-answer authority | automatic |
| **ADR / CONTEXT term** (project-scoped, dispositive) | *can* be cited to auto-answer future Type-2s | **human-promoted** |

Always record **rationale + constraints**, never a bare verdict — a future match requires the
*conditions* to line up, not just the topic.

---

## 5. Final stress test — the angles that make or break it

### 5.1 The answerer sits *upstream* of the entire checker (the deepest risk)
The reinforcement layer (§3.4) protects against **a half-assed implementation of a good spec.** It
does **nothing** against **a faithful implementation of a bad spec.** A Type-2 false positive writes
a wrong premise into the spec → implementation faithfully builds it → its ACs pass → gate-judge
confirms the arithmetic → QA refutes nothing, because *everything downstream trusts the spec.* **The
answerer's errors are un-backstopped by the reinforcement layer.** Its only backstops are the human
spot-check at approval and the end-of-run review. ⇒ Auto-answer **must be radically conservative**
(non-adjustable), and **approval is the load-bearing backstop** (must be cheap to do *well*).

### 5.2 The dead-text fear, answered structurally (Bruno's core worry)
Precedent: this repo *already* rotted `docs/CONTEXT.md` (stub since v1.0.0). A write-back loop that
isn't mechanically forced to close **will** rot. Guardrails:
- **Lint invariant on the decision log** (native harness move): every entry is exactly one of
  `open` (valid task-ref, unpromoted) / `promoted` (a live ADR cites it and exists) / `retired`.
  **No orphans** → fails lint. Converts the log from a dumping ground into an audited surface.
- **Measured read-back rate** via `.state/run-log.jsonl`: the answerer logs *what it consulted* per
  question. **If read-back ≈ 0 over a few sprints, the log is dead text → delete the feature.** An
  empirical kill-switch — the direct, measurable answer to the dead-text fear.
- If we can't commit to the lint invariant + read-back metric, **don't build the write-back** — ship
  the answerer read-only-from-existing-ADRs and drop self-enrichment. Half a loop that doesn't close
  is the worst outcome.

### 5.3 The checker must not become a rubber stamp
If the answerer's dedup ever feeds back into question *generation* (grill "learning" to ask fewer
questions), adversarial coverage shrinks invisibly. **Invariant: the generator stays context-blind to
answer-availability** — grill produces the same exhaustive set regardless of what's documented; the
answerer filters *presentation*, never *generation.* **Corollary: do not fork grill-spec** — batch
mode *wraps* its generator + synthesizer verbatim; the answerer is the only insert. (Forking = the
"losing the skill" rot + 2× maintenance on a single-maintainer prod plugin.)

### 5.4 Staleness / supersession
The answerer's authority is only as good as the cited doc, and ADRs supersede each other. Retrieval
**must honor supersession** — cite only *live* ADRs; promotion marks the superseded entry `retired`.
The harness has ADR-index-sync (lint check 3); the answerer must *respect* that status, not just file
existence. (Concrete correctness-bug class.)

### 5.5 "Approved" changes meaning — governance, not UX
Today `Spec Approved: Yes` = a human grilled + approved. In batch mode a spec may be 85%
auto-answered. Never-list already: *"spec approval for any spec produced without a human interlocutor
→ escalate."* Therefore:
- The approval artifact **itemizes** *findings* (auto, cited) vs *decisions* (human). "Approved" stays
  auditable and meaningful.
- Approval must be **cheap to do well**: the human actively decides every routed item (can't skip);
  findings are a skimmable list *with citations inline* so verifying one is a glance. Safety comes
  from findings being **boring by construction** (dispositive bar), not from re-deriving each.
- **Human-override rate** (findings the human overrides at approval) = the answerer's false-positive
  signal. Log it; rising overrides → tighten the bar.

### 5.6 Fidelity to Matt Pocock + turning the loss into a feature
Pocock's insight = *"Grill-With-Docs"* — grilling done **against documentation.** The answerer is that
idea taken to its logical end: *if you grill with docs, the docs can answer some of the grilling.*
**In the spirit of the source, not a departure** — provided §5.3 holds. Honest loss: attended
grilling has *serendipity* (being forced to answer everything sometimes reveals "this whole task is
wrong"); dedup reduces it. **Recovered as a feature:** when the answerer finds a **contradiction**
between a documented decision and the task's apparent intent, that's a **red-flag escalation** ("task
wants X, but ADR-0002 §3 says Y — conflict"). The answerer becomes a **documentation-consistency
adversary** — an edge a human grill often *can't* be (nobody remembers every ADR).

---

## 6. The final hardened design

### 6.1 The flow
```
REFINING  (attended, batch, inside governance)
   grill-spec GENERATES the full adversarial question set per backlog task  (context-blind)
      → answerer TRIAGES each question:
            Type 2 (dispositive citation)      → auto-answer as a FINDING (cited)
            Type 3 (documented-adjacent)       → route, citation-bounded lean + steelman
            Type 1 (undocumented)              → route, frame only
            contradiction (task vs docs)       → RED-FLAG escalation
      → human actively DECIDES routed items; SPOT-CHECKS findings; approves the itemized sheet
      → grill-spec SYNTHESIZES spec + acs.json
      → decisions WRITTEN BACK: decision-log (auto) / ADR+CONTEXT (human-promoted)
        │  (decision log is live within the batch: later tasks see earlier decisions as prior art)
        ▼
EXECUTION LOOP  (unattended, /capiva:auto)
   one task at a time, JIT plan (escalate if spec unhonorable),
   implement → REINFORCED verify (mandatory gate-judge + dual-review + spec-conformance),
   deviation/ambiguity → park + escalate, hard task/phase budgets enforced
        ▼
REVIEW PACKET  (attended, batch)
   board cleared → human reviews PRs / tests / docs / reports / gate-judge verdicts / parks once
```

### 6.2 The six invariants (each is "no concessions" at a different seam)
1. **Auto-answer is dispositive-or-route** — it's upstream of the checker, so it's un-backstopped;
   conservatism is non-adjustable. (§5.1, §4.3)
2. **The write-back loop is mechanically forced to close, or it isn't built** — lint invariant (no
   orphan entries) + read-back kill-switch. (§5.2)
3. **Generation stays full-strength and context-blind; wrap grill-spec, never fork it.** (§5.3)
4. **Cite only live docs; honor supersession.** (§5.4)
5. **"Approved" itemizes auto vs human; approval is the load-bearing backstop, made cheap-to-do-well.**
   (§5.5)
6. **Contradiction → red-flag escalation; the answerer is a documentation-consistency adversary.**
   (§5.6)

### 6.3 What we explicitly rejected (and why — so it isn't re-proposed)
- Adding native `/loop`/`/schedule`/`/goal` as the loop engine — CapivaOS's checker is stronger; the
  native ones are weaker or identity-eroding. (§2)
- Running grill outside the state machine — forfeits approval provenance; use `REFINING` inside. (§3.2)
- "Suggest a pick" on routed items — anchoring/automation bias. (§4.1)
- Auto-promoting one-off decisions to dispositive authority — amplification landmine; two-tier. (§4.4)
- Letting the answerer's dedup shrink question *generation* — rubber-stamps the checker. (§5.3)
- Forking grill-spec into a second skill — "losing the skill" rot. (§5.3)

### 6.4 Hard prod constraints (v1.3.0 is released to adopters)
- **Opt-in, additive** — attended grill stays byte-for-byte unchanged; batch is a mode (like auto).
- **No enforced-surface weakening** — answerer is read-only (can't fabricate); its answers are written
  only by grill-spec inside a guard-legal phase.
- **New state/edges (`REFINING`) = engine change** — touches `_LEGAL_EDGES`, the 104-scenario guard
  suite, lint parity checks → **ADR-0017** + full pipeline treatment + migration notes.
- **Inferential component in prod ⇒ must ship with an eval fixture set, or don't ship.** Mirror of
  `evals/gate-judge/`: `(question, available docs) → expected (auto-answer+citation | escalate)`,
  **including adversarial fixtures** where a *tangential* citation exists and the correct behavior is
  **escalate, not stretch**, and where a *task-scoped decision-log entry must NOT auto-generalize.*

---

### 6.5 Integration mandate (no dead scaffolding)
**Every piece must be wired into a flow and the wiring must be proven — creating the artifact is not
the deliverable, integrating it is.** This is the harness's own discipline turned on this epic. For
each new artifact, the task's ACs must answer:
- **New skill/agent?** → *what step in which flow calls it?* (must appear in the skill's steps + the
  agent roster; proven by **agent-roster parity** lint check 8 + a scenario that shows it is spawned).
- **New reference doc (ADR/CONTEXT/contract)?** → *what references it?* (proven by **ADR-index-sync**
  lint check 3 + **file-reference existence** lint check 2 + cross-links from the implementing skill).
- **New PreToolUse/hook behavior?** → *is it registered in `hooks/hooks.json` and does it actually
  fire?* (proven by **hook-registration parity** lint check 16 + guard **scenario** that triggers a
  deny/heartbeat, as the POSIX-exec CI job already does).
- **New state/transition?** → *does the orchestrator route through it?* (proven by guard
  `_LEGAL_EDGES` **scenarios** + `scenario_state_machine.py` + **field-parity** lint check 12).
- **Logs a decision / metric?** → *does it write at the intended point, and is it read back?* (proven
  by a **run-log assertion scenario** + the new **no-orphan decision-log** lint invariant + a
  **read-back metric**).
- **Makes a claim in docs?** → proven by **claims-parity** lint check 13 (enforced-surfaces ↔ markers).

Rule of thumb, borrowed from the AUD/PRD epics: **the check that proves a piece is wired should, if
the wiring were removed, FAIL** — mutual proof, not a green-but-empty pass. Any task that can't state
its Wired-into + Proven-by is not ready to start.

---

## 7. Open questions (to grill before/while building)
- Does `REFINING` need to be a first-class state, or a sub-mode of TRIAGE/GRILL_SPEC that iterates the
  backlog? (Transition-table + guard-scenario cost differs.)
- Batch grill mutates the board (spawns tasks, amends ACs). How does `REFINING` converge when
  grilling task N adds task N+1? (iterate-until-stable; dependency order.)
- Where does the decision log live? (`.board/decisions.md`? `docs/adr/decisions/`?) What format makes
  the lint invariant + read-back metric cheap?
- Minimum-human-content floor: is there a threshold of auto-answer ratio above which a task is
  *disqualified* from the batch lane (too little human judgment to trust)? Or is itemized approval
  enough?
- Does the answerer run per-task (inside each task's grill) or as a one-time board-wide context-index
  pass feeding all grills? (We leaned per-task triage; a board-wide pre-index is a possible optimization.)

---

## 8. Proposed task breakdown (seed — to be grilled onto the board)
Exact IDs/lane/ACs set during board-write + grill. Ordering respects "prove the risky inferential
piece before touching the engine." **Every task carries the §6.5 triad — Adds / Wired-into /
Proven-by — so nothing ships as dead scaffolding.**

**1. ADR-0017 — "Batch-Refine / Cluster-HITL" contract.** *(doc anchor)*
- Adds: `docs/adr/0017-*.md` capturing §6.2 invariants, §4.2 taxonomy, §6.3 rejections, §6.4 constraints.
- Wired-into: linked from `docs/DESIGN.md` ADR index; every downstream task's spec cites it.
- Proven-by: lint check 3 (ADR-index-sync) + check 2 (file-reference existence) pass.

**2. Answerer eval-fixture spike — GATE.** *(prove the bar before building the agent)*
- Adds: `evals/context-answerer/` fixtures + `expected-verdicts.json` + runner, incl. adversarial
  **tangential-citation → escalate** and **local-decision → do-not-generalize** cases.
- Wired-into: `evals/README.md` tier list; run at release like `evals/gate-judge/`.
- Proven-by: runner executes, verdicts match; **removing the dispositive bar makes an adversarial
  fixture fail** (mutual proof). **If the bar can't pass, fall back to smarter-grill and STOP.**

**3. Context-answerer agent.** *(read-only; finding-vs-frame; citation ≤ recommendation + steelman; contradiction red-flag)*
- Adds: `agents/context-answerer.md` with a **read-only tool allowlist** (Read/Grep/Glob — ADR-0012).
- Wired-into: invoked by a named step in the batch-grill flow (§6.1); added to the agent roster.
- Proven-by: **agent-roster parity lint check 8** + a scenario/eval showing the flow spawns it +
  tool-allowlist asserts read-only (mechanically cannot fabricate).

**4. `REFINING` state + transition edges.** *(the engine change — gated behind #2/#3)*
- Adds: new state + edges in `hooks/phase_guard.py` `_LEGAL_EDGES`; itemized approval artifact
  (findings vs decisions); generation stays context-blind (§5.3).
- Wired-into: sprint orchestrator routes IDLE→REFINING→execution; `rules/state-management.md` +
  `rules/workflow-pipeline.md` document it; `sprint-state.md` template updated.
- Proven-by: guard **scenarios** (legal + illegal transitions) added to the 104→N suite;
  `scenario_state_machine.py` coverage; **field-parity lint check 12**. (Backward-compat: attended
  path unchanged; batch is opt-in.)

**5. Two-tier write-back + no-orphan lint invariant + read-back metric.** *(closes the loop — §5.2)*
- Adds: decision-log (task-scoped, auto) with rationale+constraints; human-promotion path to
  ADR/CONTEXT; run-log `answerer-consulted` event.
- Wired-into: the batch-grill flow writes a decision-log entry at the point a routed item is answered;
  promotion step surfaces in the flow; `session_context`/`run-log` records consulted docs.
- Proven-by: **NEW lint check (no orphan decision-log entries)** with a `--self-test` seeding a bad
  fixture (like existing checks); a **run-log assertion scenario** (entry written when a decision is
  logged); **read-back metric** computable from `run-log.jsonl`. Honors supersession (§5.4).

**6. Reinforcement enrichments for batch mode.** *(price of removing the mid-run gate — §3.4/§5.1)*
- Adds: gate-judge **mandatory** at every batch quality gate + **test-meaningfulness** check;
  **spec-conformance** check; dual-review **mandatory** in batch; aggressive deviation→park.
- Wired-into: `test-verify`/`verify-finish` flows require them when mode=batch; `agents/gate-judge.md`
  policy updated; never-list unchanged.
- Proven-by: `evals/gate-judge/` extended with tautological-test + scope-shave fixtures; scenario
  asserts batch mode refuses to proceed without them.

**7. Review-packet end-of-run report.** *(the batched HITL backstop — §3.4/§5.1)*
- Adds: report template + generator (per task: PR / spec / ACs+evidence / quality / judge verdict /
  deviations / parks), reconciled against `run-log.jsonl`.
- Wired-into: `/capiva:auto` emits it on board-clear (alongside `auto-run-[date].md`).
- Proven-by: a **report-validator** (pattern of `validate_impl_report.py` + report-validator
  scenarios) asserting required sections + run-log reconciliation.

**8. (Independent) Native auto-mode adoption under the never-list.** *(from §2.1 — ships regardless)*
- Adds: recommended `autoMode.environment` snippet + `classifyAllShell:true` guidance;
  SECURITY.md "classifier is a 2nd gate; PreToolUse never-list is the floor beneath it" note.
- Wired-into: `/capiva:auto` entry gate detects auto mode and recommends enabling it.
- Proven-by: **claims-parity lint check 13** if it asserts an enforced surface; entry-gate scenario.

> **Sequencing gate:** #2 is a hard gate. Nothing from #4 onward starts until the eval spike proves the
> answerer's dispositive bar survives adversarial fixtures. #1 first (anchor); #8 is parallel/independent.

