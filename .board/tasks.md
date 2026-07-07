# Task Board

## In Progress

<!-- Max 1 task. Managed by /sprint. Do NOT manually edit while sprint is running. -->

## Up Next

<!-- Queued for this sprint, priority order. /sprint picks from here. -->

## Blocked

<!-- Cannot proceed. Must include Blocker: with reason and date. -->

## Done

<!-- Completed. Immutable. PR + quality metrics. -->

## Backlog — P0 Critical

<!-- Blocking other work or requiring immediate attention -->

## Backlog — P1 Sprint

<!-- Committed for delivery this sprint -->

- [ ] **COS-001** Implement quote creation endpoint (P1)
  - **Spec**: REST endpoint to create FX quotes with currency pair, rate, and TTL. Returns quote ID for downstream consumption.
  - **AC**:
    1. POST /api/v1/quotes accepts QuoteRequest and returns 201 with QuoteResponse
    2. Validation rejects invalid currency pairs and non-positive rates
    3. Quote stored with Active=true and ExpiresAt calculated from TTL
    4. Unit + integration tests cover happy path and validation errors
  - **Depends**: none
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Example task — replace with your actual backlog items.

- [ ] **COS-002** Add quote expiration sweep function (P1)
  - **Spec**: Azure Function on timer trigger that marks expired quotes as inactive. Runs every 5 minutes.
  - **AC**:
    1. Timer function triggers every 5 minutes
    2. Queries quotes where ExpiresAt < now AND Active == true
    3. Sets Active = false on all expired quotes (soft delete pattern)
    4. Logs count of expired quotes per run
  - **Depends**: COS-001
  - **Assignee**: unassigned
  - **Status**: Backlog
  - **Phase**: IDLE
  - **Branch**: --
  - **PR**: --
  - **Quality**: --
  - **Started**: --
  - **Completed**: --
  - **Notes**: Example task — replace with your actual backlog items.

## Backlog — P2 Planned

<!-- Planned, specs may be in progress -->

## Backlog — P3 Nice to Have

<!-- Scheduled but not committed -->

## Backlog — P4 Ideas

<!-- Exploration, spikes, research. No spec required. -->
