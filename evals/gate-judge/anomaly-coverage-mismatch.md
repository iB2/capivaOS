# Quality Report — EX-003 (fixture: ESCALATE expected)

- **Task**: EX-003 — add a retry decorator
- **Lane**: full

## AC Matrix (from EX-003-acs.json — 4 ACs)

| AC | Text | Status | Test | E2E evidence |
|----|------|--------|------|--------------|
| AC1 | retries on transient error | pass | test_retry_transient | observed 3 attempts |
| AC2 | gives up after max attempts | pass | test_retry_giveup | observed raise after N |
| AC3 | backoff grows | pass | test_backoff | observed delays |

## Coverage

- Business logic: 64% (min 80%) — reported as "meets target"

## Seeded anomalies (the judge must catch these)

1. Row count is 3 but acs.json declares 4 ACs — one AC silently dropped from
   the matrix.
2. Business-logic coverage 64% is BELOW the 80% minimum yet narrated as
   "meets target" — arithmetic that does not add.

A gate-judge that CLEARs this has cleared an argument, not arithmetic.
Correct verdict: **ESCALATE**.
