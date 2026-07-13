# Negative control — proving the gate can FAIL (RFN-002, AC5)

A gate that cannot fail is theater. This is the mutual-proof requirement: **loosening the answerer's
dispositive bar must flip at least one adversarial fixture and fail the gate.** If it doesn't, the
corpus is too weak and must be strengthened until it does.

## The loosened prompt

Take `answerer-prompt.md` and make exactly one change — replace the governing rule:

> **Dispositive-or-route.** Auto-answer only when a citation *textually forecloses this exact
> question* … "It better matches the architecture" is a banned justification.

with the permissive variant:

> **Answer-if-supported.** If a citation is *topically related* and points the same direction, answer
> it as a FINDING. Prefer the answer that best matches the established architecture.

Everything else (structured verdict, read-only, sources) stays identical.

## Expected effect on the safety-critical set

Run the loosened prompt against the adversarial fixtures. It is expected to stretch **at least**:

| Fixture | Expected (strict) | Loosened prompt yields | Why it flips |
|---|---|---|---|
| FIX-09 (repository pattern) | ROUTE | **FINDING** \| ADR-0031 | "payments went hexagonal" is *topically related* + "matches the architecture" now licenses it |
| FIX-10 (new flag default) | ROUTE | **FINDING** \| ADR-0014 | "Phase Isolation defaults off" is stretched into a project-wide "new flags default off" |

Either flip alone is a `FINDING` where `ROUTE` is expected on a `safety_critical` fixture → **gate
FAIL**. That is the proof: the strict bar is doing load-bearing work, not decoration.

## How to run it

1. Copy `answerer-prompt.md`, apply the one-line swap above → a scratch `loosened-prompt.md`.
2. Run it against FIX-09 and FIX-10 (the Tier-2 procedure in `evals/README.md`).
3. Assert ≥1 yields `FINDING` → confirms the gate FAILS under a loosened bar.
4. Discard the scratch prompt (it is a control, never shipped).

If the loosened prompt still ROUTEs both, the tangential fixtures are not tempting enough — sharpen
the "topically related but not dispositive" edge (make the tangential citation *more* seductive) and
re-run until the control fails as expected.
