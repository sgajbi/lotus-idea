# Service Operations Runbook

## Standard Commands

- make lint
- make typecheck
- make ci
- docker compose up --build

## Health and Readiness

- Liveness: /health/live
- Readiness: /health/ready
- General health: /health
- Metadata: /metadata

## Incident First Checks

1. Check container logs for request failures and stack traces.
2. Verify /health/ready and metrics endpoint.
3. Run local parity check (make ci) before hotfix PR.

## Current Operation Event Diagnostics

RFC-0002 Slice 15 adds bounded operation-event logs and the
`lotus_idea_operation_events_total` metric for these internal foundations:

1. conversion intent recording,
2. conversion outcome recording,
3. report evidence-pack request recording.

Use the operation `outcome` before inspecting payload-level evidence:

1. `accepted`: new process-local foundation record created.
2. `replayed`: duplicate submission with the same idempotency key and payload.
3. `conflict`: idempotency key reused with a different payload.
4. `not_found`: candidate, conversion intent, or related foundation record is absent.
5. `permission_denied`: caller capability failed closed.
6. `invalid_request`: request shape, timestamp, or idempotency key is invalid.
7. `invalid_state`: lifecycle, review, target authority, or report intent precondition failed.

Operation metrics are diagnostic support evidence only. They do not prove durable database state,
data-product certification, downstream Report/Render/Archive realization, Gateway/Workbench proof,
or supported-feature promotion.
