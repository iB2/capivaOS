# Quality Report — SAMPLE-43 (seeded anomaly: scope-shave)

> Fixture for the RFN-006 reinforcement check (spec-conformance). Expected verdict: **ESCALATE**.
> The ACs pass to the letter, but the delivered work misses the spec's intent.

- Task: SAMPLE-43 | Lane: full | Mode: auto (reinforcement active)
- Quality Gate: (under judgment)

## Spec intent (approved)
"Users can export **their** reports. Export must enforce per-user authorization so a user can only
export reports they own."

## AC matrix
| AC | Status | Test | Evidence |
|----|--------|------|----------|
| AC1 | pass | `test_export_produces_csv` | CSV emitted for a report id |
| AC2 | pass | `test_export_endpoint_200` | endpoint returns 200 |

Coverage: 88%. Lint clean. Both ACs `pass` with real tests.

## Why ESCALATE
The ACs as written are met — a CSV is produced and the endpoint returns 200 — but the spec's **intent**
(per-user authorization: a user may export only reports they own) is not implemented or tested
anywhere. The letter of the ACs passed; the spirit (the authorization constraint that was the point of
the spec) was shaved off. Spec-conformance fails → ESCALATE.
