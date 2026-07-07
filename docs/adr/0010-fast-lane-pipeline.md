# ADR-0010: Fast-Lane Pipeline for Small, Low-Risk Tasks

## Status

Accepted

## Context

The 2026-07-07 harness audit (finding F6.5) flagged that the six-phase pipeline
applies identical ceremony to every task regardless of size. A one-file bug fix
with a clear reproduction pays the same cost as a new subsystem: adversarial
interview, Context7 discovery, micro-task decomposition, two-agent test
generation, CAB artifacts — four blocking human gates and (per the
context-management budget model) ~165K tokens of pipeline overhead.

2026 process-framework research consensus is that spec-driven-development
overhead exceeds its return on small tasks. In practice this manifests as lane
evasion: humans batch small fixes outside the pipeline entirely ("just edit it,
skip the harness"), which is worse than a lighter lane — those changes get NO
spec, NO board entry, and NO quality gate. The harness's own P4 escape ("no spec
required, no quality gates") is too blunt: it removes the guarantees instead of
scaling them.

The constraint from Laws 1–3: whatever the lighter path is, it must remain a
state-machine path — task on the board, phases in sprint-state, artifacts gating
progression. A "bypass" that steps outside the state machine would break session
recovery, the phase-guard hook, and the audit trail.

### Options Considered

**Option A: Keep one pipeline, tell humans to use P4 for small tasks**
- Pro: Zero new states, zero new skills.
- Con: P4 removes specs and quality gates entirely — small production fixes ship unverified.
- Con: Doesn't fix lane evasion; the gap between "full ceremony" and "nothing" stays.

**Option B: Skip-flags on the existing phases (e.g., `--lite` on /grill-spec, /plan)**
- Per-phase toggles that shorten each skill.
- Pro: No new states; the guard matrix is untouched.
- Con: Combinatorial — every skill needs a lite mode and every gate needs a rule
  for which combination is legal. "Which flags were on?" is exactly the kind of
  conversation-state Law 1 forbids.
- Con: Four human gates remain four interruptions; the audit's cost finding was
  gates and phase count, not prose length.

**Option C: A second state-machine path with combined phases (chosen)**
- Fast lane: `IDLE → TRIAGE → SPEC_PLAN → IMPLEMENT → VERIFY_FINISH → IDLE`.
  SPEC_PLAN combines spec-lite + plan behind ONE gate; IMPLEMENT is unchanged
  (TDD is not ceremony); VERIFY_FINISH combines verification + PR behind one
  quality gate. Lane recorded in sprint-state; selection by a mechanical
  qualifying predicate at TRIAGE.
- Pro: Still a state machine — recoverable, hook-enforceable, audited in Phase
  History like any other transition.
- Con: Two new phases and two new skills to maintain; the phase guard must
  understand them (one more place to keep in sync).
- Con: A wrongly-qualified task gets less scrutiny — mitigated by a conservative
  predicate, a mandatory abort-to-full-lane rule when scope grows, and the human
  gate at SPEC_PLAN (the human sees the lane and can force full).

## Decision

**Option C — an alternate state-machine path, not a bypass.**

Qualifying predicate (ALL must hold, evaluated by /sprint at TRIAGE):
priority P2/P3, no new source files, no schema/migration changes, no
architectural changes (per blueprint §architecture), no new dependencies.
P0/P1 and anything failing the predicate takes the full pipeline — the default
is full; fast is the exception that must be earned. The human can veto fast or
force full at the SPEC_PLAN gate; nothing can force a non-qualifying task fast.

TDD (Law: no test, no implementation) and the machine-readable AC contract
(ADR-0009: acs.json, end-to-end exercise, generated matrix) apply IDENTICALLY in
both lanes — the fast lane compresses interviews and gate count, never the
verification substance.

Option A was rejected because it trades quality for speed instead of scaling
ceremony. Option B was rejected because flag-combinations are unauditable
conversation state; two named phases are two auditable states.

## Consequences

- Small tasks cost 2 human gates instead of 4 and roughly half the token budget
  (~75K vs ~165K typical), making "use the harness" cheaper than "evade the harness".
- `sprint-state.md` gains a `Lane` field (`full` | `fast`); phase guards and the
  `phase_guard.py` hook treat SPEC_PLAN like PLAN (no source writes) and
  VERIFY_FINISH like TEST_VERIFY + FINISH (test writes; `gh pr create` with
  passing gates).
- Two new skills (`/spec-plan`, `/verify-finish`) own the combined phases; /sprint
  owns lane selection and records it in Phase History.
- Scope growth mid-lane is a mandatory abort: discovering a new file, schema
  change, or architectural decision during a fast-lane task resets the task to
  the full pipeline at GRILL_SPEC (logged, not silent).
- Maintenance cost accepted: the transition diagram, guard matrix, hook, and
  hook tests now describe two paths.
- Revisit when: fast-lane tasks show quality-gate regressions (escaped defects,
  refuted claims at VERIFY_FINISH) — the predicate should tighten, or the lane
  should be removed.
