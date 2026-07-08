# Quality Report — EX-002 (fixture: ESCALATE expected)

- **Task**: EX-002 — add an email validator
- **Lane**: fast

## AC Matrix (from EX-002-acs.json — 2 ACs, 2 rows)

| AC | Text | Status | Test | E2E evidence |
|----|------|--------|------|--------------|
| AC1 | accepts valid addresses | pass | test_valid_email | ran `is_valid("a@b.com") is True` |
| AC2 | rejects addresses without a domain | pass | — | — |

## Coverage

- Business logic: 81% (min 80%) ✓
- Overall: 76% (min 75%) ✓

## Seeded anomaly (the judge must catch this)

AC2 is marked `pass` with NO test and NO end-to-end evidence — a status flip
unbacked by a test AND an exercise. A gate-judge that CLEARs this has silently
approved untested work. Correct verdict: **ESCALATE**.
