---
name: verify-finish
description: Fast lane — combined verification + finish phase (VERIFY_FINISH) with a single quality gate. Tests, static analysis, e2e exercise, compact quality report, PR. See ADR-0010.
---

# Verify-Finish — Fast Lane, Combined Phase

Compress TEST_VERIFY + FINISH into one phase for fast-lane tasks. One quality
gate: the human reviews the compact quality report and decides the merge in the
same checkpoint.

**What is compressed**: the two-agent test-generation pattern (the orchestrator
verifies directly — fast-lane diffs are small enough to review in one context),
the report size, the CAB/release ceremony (P2/P3 don't require CAB tickets), and
the gate count.

**What is NOT compressed**: the gates themselves. Full test suite, zero new
linter warnings, every AC `pass` in `TASK-ID-acs.json`, and the end-to-end
exercise (ADR-0009) all apply at full-lane thresholds.

## Phase Guard (MANDATORY)

**Before executing ANY step below:**

1. Read `.board/sprint-state.md`
2. Verify Phase = VERIFY_FINISH
3. Verify Lane = fast
4. Verify a feature branch exists (Branch field is not "--")
5. Verify `docs/specs/TASK-ID-acs.json` exists and parses
6. If ANY check fails → **STOP**: "⛔ Phase guard failed. [specific failure]. Complete /capiva:implement first."
7. If ALL checks pass → proceed

## Process

### Step 1: Verify

1. Run the full test suite (blueprint §build-commands) — all green or STOP
2. Run the linter (blueprint §static-analysis) — zero new warnings in changed files or fix
3. Adversarial self-check on the diff (`git diff main..HEAD`): for each AC in
   `TASK-ID-acs.json`, apply the delete-the-code thought experiment — is there a
   test that would FAIL if this behavior were broken? Add the missing test if not
   (test paths are writable in this phase).

### Step 2: End-to-End Exercise (MANDATORY — same as full lane)

Drive the built change the way its caller will (per blueprint tooling): call the
endpoint, run the CLI, trigger the job. Record command + observed output per AC.
Then update `TASK-ID-acs.json` statuses to `pass`/`fail` — the ONLY edit allowed
to that file. Any `fail` → fix and re-exercise. See /capiva:test-verify Step 5b for the
full protocol, which applies verbatim.

### Step 3: Compact Quality Report

Write `docs/reports/TASK-ID-quality.md`:

```markdown
# Quality Report: [Task Title] (fast lane)

## Task Reference
- ID / Branch / Spec / Lane: fast

## Gates
| Gate | Value | Target | Status |
|------|-------|--------|--------|
| Test suite | [N]/[N] pass | all | ✅/❌ |
| Linter (new code) | [N] warnings | 0 | ✅/❌ |
| Coverage (changed files) | X% | >= 80% business / 60% infra | ✅/❌ |
| ACs pass in acs.json | [N]/[N] | all | ✅/❌ |
| End-to-end exercise | [N]/[N] ACs | all | ✅/❌ |

## End-to-End Exercise
| AC | How Exercised | Observed | Verdict |
|----|--------------|----------|---------|

## Acceptance Criteria Coverage
[GENERATED from TASK-ID-acs.json — row count equals entry count]
| AC | Criterion (from acs.json) | Test(s) | E2E | Status |
|----|---------------------------|---------|-----|--------|

## Verdict
PASS / SOFT FAIL / HARD FAIL — [one line]
```

### Step 4: Single Gate — Quality Review + Merge Decision

Present the report, then WAIT:

```
Fast lane quality gates: [PASS/...]
  Tests: N/N | Linter: 0 warnings | ACs: N/N pass | E2E: N/N exercised

🧑 ONE gate: approve to create the PR (merge options presented immediately after),
   request fixes, or escalate to the full /capiva:test-verify if something looks off.
```

- Approved → update sprint-state Quality Gate = PASS, create the PR (Step 5)
- HARD FAIL → cannot be approved; fix and re-verify
- Human says "full pipeline" → set Phase = TEST_VERIFY, Lane = full, log the transition, hand to /capiva:test-verify

### Step 5: PR + Board + Reset

1. Pre-flight: clean `git status`, branch pushed, rebased on origin/main, tests re-run
2. Create the PR (`gh pr create`) — Summary, Spec Reference, Changes, Gates table,
   AC checkboxes generated from acs.json, link to the quality report. Note
   `Lane: fast` in the description.
3. Update board (with lock): task → Done, PR number, quality metrics, Completed date
4. Present merge options (merge / keep for review / discard) — **never merge without explicit approval**
5. After the human decides:
   - Sprint-state: Phase = IDLE, Lane = full (reset to default), Current Task = (none), metrics incremented
   - Phase History: `| [now] | [task] | VERIFY_FINISH | IDLE | quality-pass+[merge/review/discard] | fast lane, PR #[N] |`
6. **→ Return control to /capiva:sprint**

## Rules

- **Thresholds are full-lane thresholds.** Compression is in ceremony, not standards.
- **acs.json statuses gate the PR.** Any `pending` or `fail` → no PR. Immutable except status.
- **E2E exercise is not optional.** Same protocol as /capiva:test-verify Step 5b.
- **CAB/release artifacts are skipped for P2/P3** — if the task were P0/P1 it would not be in this lane.
- **Escalation is always available.** Human can route to full /capiva:test-verify at the gate; scope surprises follow the same abort-to-full-lane rule as /capiva:spec-plan.
- **Never merge without explicit human approval.**
