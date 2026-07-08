# capivaOS Behavioral Evals

Two tiers, per the review's Principle 4 (*rules-based feedback first,
LLM-as-judge last*):

## Tier 1 — deterministic (in CI, no LLM)

`hooks/tests/scenario_state_machine.py` exercises the pipeline's core logic
against the normative state machine: the legal/illegal transition matrix and
doc-parity between the documented Valid Transitions and the guard's encoded
edges. Pure rules-based, runs in the `hook-tests` CI job. No excuse for this
not to exist — it now does.

## Tier 2 — gate-judge adversarial set (release-time, needs an LLM)

`gate-judge/` holds fixture quality reports with known-correct verdicts. The
gate-judge is the component whose *failure silently approves bad work*, so it
must be checked — but it is an LLM agent, so this tier needs an authenticated
session and is **not** part of the no-auth CI gate. Run it at least at each
release:

1. For each fixture in `gate-judge/`, spawn the `gate-judge` agent with the
   report as its artifact under judgment.
2. Assert the verdict matches `gate-judge/expected-verdicts.json`.
   - Clean reports **must** verdict `CLEAR`.
   - Seeded-anomaly reports **must** verdict `ESCALATE` (a CLEAR here is a
     silent-approval failure — the worst outcome).

Grow the fixture set from real adopter traces as they arrive (the prescribed
method — golden transcripts are built from real usage, not synthesized).

## Owner

Eval curation owner: **Bruno** (the single accountable "benevolent dictator"
whose taste the eval set encodes), until explicitly delegated.
