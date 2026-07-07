# Release Checklist — [Task Title]

## Pre-Deployment (24h+ before)

- [ ] CAB ticket submitted (see `docs/cab/[TASK-ID]-cab.md`)
- [ ] All quality gates pass
- [ ] UAT sign-off obtained
- [ ] Rollback scripts prepared and tested
- [ ] Database migration scripts reviewed by DBA (if applicable)
- [ ] Infrastructure changes provisioned in target environment
- [ ] Configuration values confirmed for target environment
- [ ] PR approved by Tech Lead

## Day of Deployment

### Before
- [ ] Maintenance page ready (if required)
- [ ] Team notified of deployment window
- [ ] Monitoring dashboards open
- [ ] Rollback scripts accessible
- [ ] Previous deployment version noted: [version/commit]

### During
- [ ] Maintenance page activated (if required)
- [ ] Database scripts executed in order
- [ ] Application deployed via Azure Pipelines
- [ ] Deployment logs reviewed — no errors
- [ ] Maintenance page deactivated

### After (Smoke Tests)
- [ ] Health endpoint responds: `GET /health` → 200
- [ ] Key business flow works end-to-end
- [ ] No error spikes in Application Insights
- [ ] No latency degradation in monitoring
- [ ] Business team confirms functionality

## Post-Deployment (24h)

- [ ] Monitor error rates — no regression
- [ ] Monitor performance — no degradation
- [ ] Business production validation sign-off
- [ ] Merge to `main` (if not already merged)
- [ ] Clean up feature branch
- [ ] Update board task status
- [ ] Close CAB ticket

## Rollback Trigger Criteria

Rollback immediately if ANY of these occur:
1. Error rate exceeds [X]% above baseline
2. P95 latency exceeds [Y]ms (2x baseline)
3. Business-critical flow is broken
4. Data corruption detected
5. Security vulnerability identified

## Environment Details

| Environment | URL | Status |
|-------------|-----|--------|
| DEV | [url] | Deployed |
| UAT | [url] | Deployed |
| Production | [url] | Pending |
