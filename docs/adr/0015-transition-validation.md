# ADR-0015: Sprint-State Transition Validation — the Guard Learns the State Machine

**Status**: Accepted — design approved 2026-07-08, **implemented 2026-07-09**
(1.3.0): the guard now validates sprint-state Phase transitions, artifact
preconditions on entering IMPLEMENT/FINISH, forged-PASS, and Phase-blanking.
**Context**: a 2026-07 external code review's core-loophole finding: "the
enforcement file is inside the agent's writable surface."

## Context

The phase guard derives every decision from `.board/sprint-state.md` — and
`.board/` is writable in every phase (it must be: the pipeline's artifacts live
there). The review stated the consequence precisely: *an agent that wants to
write source out of phase simply sets `Phase: IMPLEMENT` first. The goalposts
are agent-writable.* The same applies to `Quality Gate: PASS` before
`gh pr create`, and to blanking the Phase field to trigger fail-open.

1.2.0 closed the *other* self-licensing routes (kill-switch, merge
verbs, shell writes), which makes this the last structural gap between
"mechanically enforced" and "mechanically enforced unless the agent edits the
state file". Today that gap is honestly labeled (the claims re-segmentation);
this ADR designs the wall that closes most of it.

The review's suggested remedy — hash/sign the Phase field — does not survive
design analysis: **there is nowhere to keep a secret the agent cannot reach.**
The repo is the agent's workspace; `.state/` is agent-readable; the hook's own
source is readable. A MAC without a secret is recomputable by the party it
constrains. Tamper-*evidence* without a trust anchor is theater.

What the hook DOES have, at PreToolUse time, that the agent cannot fake:
1. The **old** state (on disk, read by the hook before the write lands).
2. The **new** state (in the Edit/Write payload it is inspecting).
3. The **filesystem** (artifact existence is checkable at decision time).

That is exactly enough to validate *transitions*, not *integrity*.

## Options Considered

### Option A: Cryptographic integrity (hash/HMAC of the Phase field)
The audit's literal suggestion. **Rejected**: no secret storage exists that
the agent cannot read (repo, `.state/`, env are all reachable or forgeable;
an unkeyed hash is recomputable). Would add crypto-shaped confidence without
crypto-shaped guarantees — worse than the honest label we ship today.

### Option B: Dual-state JSON mirror maintained by hooks
A hook-owned `.state/phase-mirror.json` the guard cross-checks. **Rejected**:
ADR-0008 already rejected dual state for the exact drift reason, and the
mirror file sits in the same writable surface (until the shell-parity work,
`touch`-able; after it, still `Write`-able unless HUMAN_ONLY — and if it is
HUMAN_ONLY, hooks can't maintain it via tools either... as processes they
can, but then a conflicted mirror reintroduces the ADR-0008 problem).
Complexity without closing the hole.

### Option C: The guard validates transitions + artifact preconditions (CHOSEN)
Make `sprint-state.md` writes themselves a guarded surface. On every
Edit/Write/MultiEdit whose target is `.board/sprint-state.md` (and, via
shell-write parity, redirects to it), the guard parses old Phase (disk) and
new Phase (payload) and denies when:

1. **Illegal transition** — the (old → new) pair is not in the legal-transition
   table, which becomes DATA in the hook (source of truth; the four prose
   copies reference it). Legal set today: the full-lane chain, the fast-lane
   chain, `ANY → BLOCKED`, `BLOCKED → previous`, `ANY → IDLE` (abort),
   `SPEC_PLAN → GRILL_SPEC`, `VERIFY_FINISH → TEST_VERIFY` (fast-lane abort).
2. **Missing artifact precondition** — transitions gain existence checks,
   Law 3 rising from prompt (L3) to hook (L1):
   - `→ IMPLEMENT` requires `PLAN.md` AND `docs/specs/<Task ID>-acs.json`
   - `→ FINISH` / `→ VERIFY_FINISH`(from IMPLEMENT) requires
     `docs/reports/<Task ID>-quality.md`
   - `→ TRIAGE` requires a non-empty `.board/tasks.md`
   Existence only — content quality stays with the skills (ADR-0006's
   gating-vs-validation split, unchanged).
3. **Phase-skip via blanking** — a new state whose Phase field is empty or
   missing while the old one was valid (the fail-open exploit becomes a deny;
   genuine corruption still fails open on READ, per the loud
   conflict-marker path — the asymmetry is deliberate: reads fail open,
   writes fail closed).

`Quality Gate` flips to PASS/ACCEPTED_SOFT_FAIL are allowed only in phases
that produce a quality report and only when the report file exists. Approval
fields (`Spec Approved`, `Plan Approved`) remain OUT of hook enforcement —
see Consequences for why, stated honestly.

## Decision

Option C. One new deny surface — `sprint-state-transitions` — added to
`ENFORCED_SURFACES`, which by the claims-parity lint contract forces the README and
SECURITY.md rows, the scenario coverage, and this ADR to land together.

## Consequences

- The §2.1 attack degrades from "one Edit" to "must move through the legal
  chain with real artifacts on disk at each step" — an agent can still walk
  IDLE→TRIAGE→…→IMPLEMENT, but only by producing a plan and an acs.json,
  which is the pipeline working, not the pipeline bypassed.
- **Honest residual, stated up front**: the hook cannot distinguish "the
  orchestrator records a human approval that happened in chat" from "the
  agent invents one" — approval fields stay structurally-encouraged (L3), and
  the claims tables must keep saying so. The wall is around
  *sequence and evidence*, not *consent*.
- Human edit paths must keep working: a human fixing state from their
  terminal never passes through PreToolUse (hooks see agent tools only), so
  no escape hatch is needed for them — the existing env/marker hatches cover
  agent-assisted repair under supervision.
- Handover/restore flows write state legitimately (`context-persistence`
  writes as a process, not via tools — unaffected). `/capiva:handover`'s
  in-conversation state edits do pass through the guard: its writes are
  field updates within the same Phase (legal: self-transition), plus
  `ANY → IDLE` at abort — both in the legal set.
- Board rebuilds (the 2026-07-07 `.board` deletion incident) start from a
  missing file: old state = None → validation skips, fail-open on first
  write. Recovery stays unbricked.
- Cost: the transition table becomes hook data — the four prose copies
  (laws, state-management, workflow-pipeline, template) must reference it or
  drift; a lint parity check (same family as checks 12/13) must land in the
  implementation task.
- Revisit when: Claude Code ships hook-native state or signed hook storage
  (would reopen Option A with an actual trust anchor).
