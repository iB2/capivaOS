# Deviation Record: DEV-NNN — [Short Title]

## Metadata
- **Date**: [ISO date]
- **Author**: [who proposed this]
- **Blueprint Rule**: [which enterprise-blueprint.md section this deviates from]
- **Scope**: [which project/module is affected]
- **Status**: Proposed | Approved | Rejected

## What Is Being Deviated

[Exact blueprint constraint being deviated from. Quote the rule.]

## Why

[Technical justification. NOT "it's easier" — a real reason:]
- What constraint makes the blueprint pattern impractical?
- What does the codebase need that the blueprint doesn't support?
- What would the cost be of following the blueprint here?

## Alternative Approach

[What will be done instead of the blueprint pattern:]
- Specific implementation approach
- How it still meets the spirit of the constraint
- How it affects maintainability and consistency

## Impact Analysis

### Positive
- [What this deviation enables]

### Negative
- [What this deviation costs — be honest]

### Risk
- [What could go wrong with this deviation]

## Review

- [ ] Tech Lead reviewed
- [ ] Consistent with other approved deviations
- [ ] Does NOT compromise security, observability, or testability
- [ ] Documented in PR description

## Related
- PR: [#number]
- Task: [TASK-ID]
- ADR: [if applicable]
