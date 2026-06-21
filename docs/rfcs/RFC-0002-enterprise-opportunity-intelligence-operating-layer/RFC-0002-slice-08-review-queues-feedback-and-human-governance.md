# RFC-0002 Slice 08: Review Queues, Feedback, And Human Governance

Status: Planned

## Outcome

Implement human review, feedback, and governance over opportunity queues.

## Required Work

1. Add advisor, PM, compliance, and operator queue projections as approved by
   Slice 0.
2. Implement review decisions, feedback, rejection, suppression, snooze,
   escalation, and no-action outcomes.
3. Enforce role, book, portfolio, client, and tenant entitlements.
4. Capture audit reason and actor context for all review actions.

## Acceptance Gate

1. Review actions cannot approve downstream suitability, compliance, mandate, or
   execution state.
2. Entitlement tests fail closed.
3. Queue projections update after decisions.
4. Feedback events are durable and source-provenanced.
