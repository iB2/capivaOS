# Quality Report — EX-001 (fixture: CLEAR expected)

- **Task**: EX-001 — add a slugify helper
- **Lane**: fast

## AC Matrix (generated from EX-001-acs.json — 3 ACs, 3 rows)

| AC | Text | Status | Test | E2E evidence |
|----|------|--------|------|--------------|
| AC1 | slugify lowercases and hyphenates | pass | test_slugify_basic | ran `slugify("Hello World") == "hello-world"` |
| AC2 | strips non-alphanumerics | pass | test_slugify_strips | ran `slugify("a@b!") == "a-b"` |
| AC3 | collapses repeated separators | pass | test_slugify_collapse | ran `slugify("a  b") == "a-b"` |

## Coverage

- Business logic: 92% (min 80%) ✓
- Overall: 88% (min 75%) ✓
- Lint: 0 warnings ✓
- Types: clean ✓

All 3 acs.json statuses are `pass` with a test AND an end-to-end exercise.
Row count (3) == acs.json count (3). No anomalies.
