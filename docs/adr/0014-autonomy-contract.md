# ADR-0014: The Autonomy Contract — Delegated Gates, Isolation-First Context

## Status

Accepted (grill interview with the maintainer, 2026-07-07, six questions resolved)

## Context

Through v1.0.0 the harness is strictly attended: four blocking human gates per
full-lane task (Law 5) and a reactive context model — one long session per task,
compaction managed by handover when pressure appears (Law 6). Two forces make
that insufficient:

1. **Throughput**: a well-specified backlog of small tasks costs a human
   presence it doesn't deserve. The maintainer felt this immediately when the
   LOOP epic itself — eight tasks — met the four-gates-each ceremony. Lane
   evasion (doing work outside the harness because ceremony is expensive) is a
   worse outcome than scaled ceremony; ADR-0010 established that principle for
   task size, this ADR extends it to human presence.
2. **Context quality**: even attended, a long session degrades. The artifact
   chain (Law 3) already makes every phase resumable from disk — the handover
   mechanism proves it on every use — but v1.0.0 never *exploits* that to give
   each phase a fresh context.

The 2026 ecosystem validated the building blocks: Anthropic's Claude Code auto
mode ships classifier-delegated approvals (two-stage: fast over-blocking filter
→ reasoning stage, 8.5%→0.4% false positives, recursive into subagents) —
delegation with exception escalation is now a platform-sanctioned pattern at the
*permission* level. sd0x-dev-flow demonstrates sentinel-gated auto-loops with
compaction resume and a hard stop before irreversible operations. No surveyed
harness applies delegation at the *pipeline gate* level; that is the gap this
contract fills.

The founding tension is real and must be named: DESIGN.md's whole thesis is
that agents self-approve mediocre work, so human judgment at the gates IS the
quality mechanism. Any autonomy design that quietly dissolves the gates
destroys the product. This ADR therefore defines autonomy as a *re-routing* of
human judgment (written policy + exception escalation), never its removal.

### Options Considered

**Axis 1 — Delegation model**

**Option A: No delegation (status quo)**
- Pro: Zero risk to the quality thesis; nothing changes.
- Con: The throughput problem stands; lane evasion pressure grows; the harness
  falls behind platform norms (auto mode exists; users will combine it with the
  harness anyway, ungoverned).

**Option B: Full autonomy switch (gates off in auto mode)**
- Pro: Simplest to build; maximum throughput.
- Con: Destroys the founding thesis — the agent approves its own specs and
  quality. Rejected outright.

**Option C: Policy + independent judge with exception escalation (chosen)**
- Human writes an approval policy (predicates over lane/priority/scope); an
  independent judge — never the artifact's producer — scores what policy
  doesn't cover and either clears within explicit bounds or escalates to a
  queue. A hard-coded never-list is beyond both.
- Pro: Human judgment is exercised once, deliberately, in writing — then applied
  mechanically; exceptions still reach a human; every delegated decision is
  logged with rationale.
- Con: Judge calibration is real work (LOOP-006); a badly written policy
  delegates more than intended — mitigated by the never-list floor and
  silence-means-escalate default.

**Axis 2 — Policy authorship**

**Option A: Agent-editable policy with audit log**
- Pro: The loop can fix its own false-escalation friction.
- Con: Self-licensing — an agent widening its own authority is the exact
  failure Law 5 exists to prevent; audit-after-the-fact is too late. Rejected.

**Option B: Human-authored, hook-enforced (chosen)**
- `phase_guard.py` denies agent writes to `.board/approval-policy.md` in every
  phase (same enforcement class as `gh pr create` gating). The agent may
  *propose* amendments only as escalation items. (Historical note: earlier
  drafts spoke of a policy-file *hash* audit; that was never implemented and
  the claim was removed in 1.3.0 — the mechanical audit trail is the run-log,
  not a hash.)

**Axis 3 — Overnight spec drafting**

**Option A: Draft specs unattended, escalate approval**
- Pro: Mornings start with ready-to-review specs.
- Con: Anchor effect — a confident self-grilled spec *frames* the reviewer into
  approving what they would never have specified; the grill's value is the
  interlocutor. Deferred, not lost: LOOP-009 (P3) with SELF-GRILLED marking and
  mandatory anchor warnings, if ever built.

**Option B: Skip un-specced tasks (chosen for v1.1)**
- The loop only takes tasks with human-approved specs or fast-lane qualifiers;
  un-specced full-lane tasks appear in the morning report as "awaiting attended
  grill."

**Axis 4 — Context strategy rollout**

**Option A: Isolation-first everywhere, immediately**
- Pro: One story — "v1.1 never compacts."
- Con: Silently changes the attended experience (phases dispatched to subagents
  instead of reasoning visibly in-conversation) — a legibility/trust cost for
  adopters who chose the harness to watch it work. Rejected for attended default.

**Option B: Auto always; attended opt-in now, default later (chosen)**
- Auto mode requires isolation (it is what makes never-compact real). Attended
  runs keep today's behavior unless `- **Phase Isolation**: on` is set in
  `.board/harness-config.md`; the default flips in a later minor release with a
  CHANGELOG entry and migration row, after dogfooding proves it.

## Decision

Two modes, one contract:

1. **Attended remains the default and is unchanged.** Auto mode is opt-in
   **per run** (`/capiva:auto`), never a standing repo state.
2. **The never-list — no machine may clear, regardless of policy or judge
   confidence:** (a) the merge decision; (b) any gate on a P0/P1 task; (c) spec
   approval for any spec produced without a human interlocutor or carrying open
   questions; (d) anything the policy file does not explicitly cover — silence
   means escalate, never approve. The never-list is hard-coded in the engine
   (skills + phase guard); no project-side configuration can extend delegation
   into it, and a policy attempting to is ignored, escalated, and logged.
3. **Delegable remainder:** spec+plan gates for fast-lane-qualifying P2/P3
   tasks under written policy; quality-gate clearance on any lane when all
   mechanical gates PASS and the independent judge finds zero anomalies.
4. **Policy is human law:** `.board/approval-policy.md`, `- **Field**:` format,
   human-authored only (hook-denied to agents; implementation lands with
   LOOP-006), agent proposes via escalation. (The policy-file hash audit
   mentioned in earlier drafts was removed in 1.3.0 — see the note above.)
5. **Escalation is file-based:** `.board/approvals.md` queue with
   exception-first summaries + a morning report artifact; SessionStart injection
   surfaces the pending count. Notification is a documented adopter-side recipe
   — the plugin gains no network path; SECURITY.md's zero-network sentence
   remains true verbatim.
6. **Budgets are invariant:** every auto run carries BOTH a max-task cap and a
   token budget — an unlimited value does not exist. The loop parks only at
   phase boundaries, producing the standard handover document; mid-phase budget
   death abandons that phase's fresh context (branch untouched past its last
   green commit) and the task re-enters at that phase. The morning report leads
   with why the loop stopped. Default numbers are calibrated in LOOP-007.

## Consequences

- Law 5 becomes mode-aware: in auto mode, gates are *routed* (policy → judge →
  escalation queue) instead of *blocking*, except the never-list. Law 6 becomes
  isolation-first: fresh context per phase is the auto-mode rule and the
  attended opt-in, with compaction-survival (LOOP-004) as the fallback layer.
- The human's role shifts from operator to reviewer-of-exceptions: the morning
  interaction is the approvals queue and the PR list, not gate-sitting. The
  known cost — batch review attends less per item than blocking review — is
  mitigated, not eliminated: policy handles the routine, the judge clears only
  zero-anomaly arithmetic, exception-first summaries focus attention, and the
  merge gate stays absolute. Per-task output quality in auto mode is expected
  to be somewhat below attended quality; that trade is the price of throughput
  and is stated honestly in SCOPE.md.
- Un-specced work cannot enter the loop — the evening grill (attended) becomes
  the natural preparation ritual for an overnight run.
- The guard's enforcement surface grows again (policy-file denial), continuing
  the pattern: every contract line lives in a hook or lint check, not prose.
- GitHub branch protection becomes a safety prerequisite worth checking
  mechanically (LOOP-002) — the merge gate is only real if the forge enforces it.
- Revisit when: judge false-escalation rates are measurable in practice
  (tighten policy), or platform-native gate delegation appears in Claude Code
  (collapse LOOP-006 onto it, as ADR-0012/0013 did with agents and plugins).

---

## Amendment (2026-07-08 — external code review follow-up)

Three contract clarifications, each closing a gap a 2026-07 external code
review surfaced:

1. **The budget unit is phase executions, canonically `Loop Phase Budget`.**
   The original text said "token budget"; no token counter exists in Claude
   Code, and the driver was already counting phases as the proxy (isolation
   bounds each phase, so phases × bound ≈ tokens). The audit found the doc
   layer and `session_context.py` reading `Loop Token Budget` — a field the
   driver never writes — so the post-compaction [AUTO_LOOP_RESUME] injection
   degraded to its fallback. Field name is now `Loop Phase Budget`
   everywhere; harness_lint's field-parity check (delivered with this
   amendment) asserts hooks only read fields the registry documents.

2. **The interlocutor carve-out for fast-lane specs.** Never-list item (3)
   escalates specs "produced without a human interlocutor" — and every
   fast-lane spec in an unattended run is produced without one, which made
   the `Auto-Approve Fast-Lane Spec+Plan` policy grant a dead option (the
   judge always escalated it). Resolution: human-authored board ACs count as
   the interlocutor — the human wrote the task and its acceptance criteria.
   Condition: every spec AC must trace to the board task's ACs; the driver
   includes the board task text in the judge's briefing, and any untraceable
   AC escalates. The grant now means what the template says it means.

3. **Never-list item (1) is hook-enforced.** "The merge decision" was
   prompt-level at 1.1.0 (the review's sharpest finding). The phase guard now
   denies `gh pr merge` and `git push` targeting the default branch in every
   phase and mode; web UI / MCP routes remain covered by branch protection
   (the LOOP-002 prerequisite). The contract line moved from prose to code,
   completing the pattern this ADR set for the policy file.

---

## Amendment (2026-07-13 — clustered / batch-refine, a third oversight mode)

The RFN epic (loop-engineering study; rationale record
`docs/rfn-loop-engineering-deliberation.md`) adds a **third oversight
mode** alongside attended and auto. This amendment defines the mode and its
never-list treatment *in place* — the never-list stays single-source here in
ADR-0014; no downstream doc restates it. The mode's *mechanism* lives in
[ADR-0017](0017-context-answerer-contract.md) (the context-answerer) and the
RFN-006 amendment to [ADR-0009](0009-machine-readable-ac-gating.md) (the
reinforcement layer).

1. **Clustered mode = cluster HITL, don't scatter it.** Front-load grilling for
   the *whole board* in an attended session (the new first-class `REFINING`
   state), run execution unattended, and review results once at the end (the
   review packet). It targets the maintainer's per-task context-switching, not
   the gates. Honest expectation is unchanged from the auto-mode paragraph:
   per-task quality runs somewhat below a fully-attended session; the end-of-run
   review is the batched — not removed — human backstop.

2. **`REFINING` is a first-class state.** Legal edges `IDLE → REFINING →`
   execution handoff (guard/state impl: RFN-004). It converges by fixed-point
   iteration over the backlog in dependency order with a spawn cap (grilling a
   task may spawn another; a batch that leaves spawn un-grilled is not
   "refined"). It **wraps** grill-spec's generator + synthesizer verbatim —
   question *generation* stays context-blind (ADR-0017 invariant 3); it never
   forks the grill.

3. **Never-list under clustered mode — the interlocutor is preserved.** All four
   never-list items stand. Item (3) ("no spec approval without a human
   interlocutor") is satisfied **per task**: the human explicitly approves each
   task's *itemized* sheet — findings (auto-answered from dispositive citations,
   ADR-0017) shown separately from decisions (the routed forks the human
   actively resolved). The human deciding every routed fork **is** the
   interlocutor moment; findings are boring-by-construction and spot-checkable.
   One batch sign-off covering many tasks was rejected — approval stays per-task.
   Merge, P0/P1 gates, and policy-silence remain beyond all delegation exactly
   as above.

4. **Consequence for Law 5.** The clustered mode is a *third* routing of human
   judgment on the same axis as auto mode — front-loaded (grill cluster) and
   deferred (review cluster) rather than blocking per task, and still never
   removed. The gate-judge and the RFN-006 reinforcement checks become mandatory
   for the unattended execution segment, since the mid-run human quality gate is
   the thing being deferred.

---

## Amendment (2026-07-13 — composing with native auto mode, RFN-008)

Claude Code's native **auto mode** (a classifier that removes routine per-tool prompts) composes
*under* this contract's never-list, it does not weaken it. The classifier is a second gate that runs
*after* the permissions system; the never-list is a PreToolUse deny that fires before it and in every
permission mode, so no auto-mode configuration can delegate into the never-list. Adopters are
*recommended* (not required) to enable auto mode with a trusted-environment config +
`classifyAllShell: true` — it removes per-tool friction during unattended runs with zero concession to
the never-list. `/capiva:auto`'s entry gate detects auto mode and surfaces this recommendation
alongside its branch-protection and guard-liveness checks. Details + the config snippet live in
SECURITY.md ("Composing with Claude Code's native auto mode"). This is documentation + a nudge — it
adds no enforced surface.

---

## Amendment (2026-07-15 — the grill→execute cycle, RFN-013)

The two oversight modes that carry Bruno's autonomy vision already exist as separate skills:
`/capiva:refine` (the **grill-sprint** — clustered `REFINING`, per-task itemized approval, produces
approved specs and exits) and `/capiva:auto` (the **execution-sprint** — unattended fresh-context
execution, PRs, review packet). This amendment packages them as one documented **two-sprint cycle**
without fusing them. It changes no contract line above; the never-list stays single-source here and is
referenced, not restated.

1. **Topology — two commands, not one.** The cycle is `/capiva:refine → review → /capiva:auto`, kept as
   two commands and a documented flow. A single `/capiva:cycle` orchestrator was considered and
   rejected: it would couple attended judgment and unattended execution into one invocation and blur
   the boundary this contract depends on (Option Axis 1 / the founding tension). The two skills remain
   independently useful and ADR-0018-clean (base skills composed, not modified).

2. **Handoff — board state.** `Spec Approved: Yes` on `.board/tasks.md` (written by refine, read by
   auto's eligibility check) IS the handoff; there is no separate manifest. The execution-sprint
   consumes ALL eligible pre-approved tasks in dependency order — a pre-approved task is pre-approved
   regardless of which grill-sprint approved it. refine's exit report names the approved set and points
   to `/capiva:auto`.

3. **The single execution-entry gate.** Bruno's "auto after ONE entry approval" is an **interactive
   pre-flight confirmation** at the top of `/capiva:auto`, after the mechanical entry-gate checks and
   before the loop: it summarizes the tasks it will execute (dependency order), the task/phase budgets,
   and that PRs are created but the merge is never touched, then waits for an explicit "begin". It is
   the ONLY human gate in the execution-sprint — every per-task gate is delegated/deferred exactly as
   the auto-mode paragraph above already specifies. Declining exits cleanly with zero board/state
   mutation.

4. **Unattended runs are unbroken (fail-safe).** The pre-flight gate is skipped ONLY on an explicit
   unattended signal — the invocation token `unattended` or `- **Auto Preflight**: off` in
   `.board/harness-config.md` (the scheduling recipe sets one). Absent any signal, the gate is SHOWN:
   silence shows the gate, it never auto-proceeds. Scheduled/cron runs therefore behave exactly as
   before; the interactive checkpoint is additive.

5. **Docs generation is a named future step, not part of this.** RFN-012 (documentation generated
   automatically after development) is an execution-phase step the cycle doc names but does not yet
   implement — it lands in the auto/execution workflow (ADR-0018), specced separately.

Consequence for Law 5: unchanged in substance. The cycle is presentation + a single interactive
checkpoint over the same routing of human judgment auto mode already defines; it removes no gate and
adds no delegation. The never-list (merge, P0/P1 gates, interlocutor-less spec approval, policy
silence) stands verbatim as above.
