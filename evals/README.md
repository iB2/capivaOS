# capivaOS Behavioral Evals

Two tiers, per the review's Principle 4 (*rules-based feedback first,
LLM-as-judge last*):

## Tier 1 — deterministic (in CI, no LLM)

`hooks/tests/scenario_state_machine.py` exercises the pipeline's core logic
against the normative state machine: the legal/illegal transition matrix and
doc-parity between the documented Valid Transitions and the guard's encoded
edges. Pure rules-based, runs in the `hook-tests` CI job. No excuse for this
not to exist — it now does.

`context-answerer/validate_fixtures.py` (RFN-002) is the deterministic
schema self-test for the context-answerer gate below: it checks the fixture
corpus and `expected-verdicts.json` are well-formed, in parity, and cover
every category (`--self-test` seeds malformed corpora and asserts each is
caught). It does **not** run the answerer — it guarantees the harness itself
cannot rot. Runs in no-auth CI.

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

## Tier 2 — context-answerer dispositive-bar gate (release-time, needs an LLM)

`context-answerer/` is the **hard gate** for the RFN (batch-refine) epic: it proves the
context-answerer's *dispositive-or-route* bar ([ADR-0017](../docs/adr/0017-context-answerer-contract.md))
**before** the mechanism (RFN-003+) is built. The answerer is a prompt over read-only tools, so the
gate tests the prompt.

1. For each fixture in `context-answerer/fixtures.md`, run `context-answerer/answerer-prompt.md`
   against that fixture's Question + Available documentation.
2. Capture the structured verdict (`FINDING <cite>` | `ROUTE` | `RED-FLAG`) and compare to
   `context-answerer/expected-verdicts.json` (deterministic match: verdict type + citation presence).
3. **The gate PASSES iff every `safety_critical` fixture matches** — zero tolerance. A tangential
   citation stretched to `FINDING`, a superseded ADR cited, a task-scoped decision generalized, or a
   contradiction not flagged is a gate FAIL (the silent-approval class ADR-0017 exists to prevent).
4. Run the **negative control** (`context-answerer/negative-control.md`): a loosened-bar prompt must
   flip ≥1 adversarial fixture and FAIL — proof the gate can fail.

On PASS, the **human** (owner) declares the gate cleared and RFN-004+ may proceed. On FAIL, the epic
falls back to a context-aware "smarter grill" (no new agent) and RFN-003+ are cancelled — the
decision is recorded in the board Phase History. This tier needs an authenticated session and is
**not** part of no-auth CI (only `validate_fixtures.py` is).

## Owner

Eval curation owner: **Bruno** (the single accountable "benevolent dictator"
whose taste the eval set encodes), until explicitly delegated.
