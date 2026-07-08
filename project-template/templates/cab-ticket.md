# Change Request — CAB Submission

## Change Details
- **Title**: [Brief description of the change]
- **Task ID**: [Board task reference]
- **PR**: [#number]
- **Requested By**: [name]
- **Date**: [submission date — must be 24h+ before deployment]

## Change Description

[2-3 paragraphs: what is being changed, why, and what is the business impact]

## Risk Assessment

| Factor | Rating | Justification |
|--------|--------|---------------|
| Complexity | Low / Medium / High | [why] |
| Impact | Low / Medium / High | [what's affected] |
| Urgency | Low / Medium / High | [timeline pressure] |
| Overall Risk | Low / Medium / High | [combined assessment] |

## Technical Details

### Database Changes
- [ ] Schema changes (migrations): [list or "None"]
- [ ] Data migrations: [list or "None"]
- [ ] Rollback scripts prepared: Yes / No / N/A

### Infrastructure Changes
- [ ] New cloud resources: [list or "None"]
- [ ] Configuration changes: [list or "None"]
- [ ] Networking changes: [list or "None"]

### Code Changes
- [ ] New endpoints: [list or "None"]
- [ ] Modified endpoints: [list or "None"]
- [ ] Breaking changes: [list or "None"]

## Rollback Plan

1. [Step-by-step rollback procedure]
2. [Database rollback if applicable]
3. [Verification steps after rollback]

**Estimated rollback time**: [minutes]

## Test Evidence

- Quality report: `docs/reports/[TASK-ID]-quality.md`
- Coverage: [X]%
- All tests passing: Yes
- UAT sign-off: [name and date]

## Deployment Plan

1. [ ] Maintenance page activated (if required)
2. [ ] Database scripts executed
3. [ ] Application deployed
4. [ ] Smoke tests run
5. [ ] Maintenance page deactivated
6. [ ] Business validation

**Deployment window**: [date and time]
**Estimated duration**: [minutes]

## Approvals

| Role | Name | Status | Date |
|------|------|--------|------|
| Tech Lead | | Pending | |
| Engineering Manager | | Pending | |
| CAB | | Pending | |
