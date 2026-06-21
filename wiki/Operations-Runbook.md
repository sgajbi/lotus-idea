# Operations Runbook

Current posture: scaffold operations plus internal domain, persistence/replay,
lifecycle, review, AI-governance, certified internal high-cash, lifecycle,
advisor queue, review-action, and feedback API foundations, and conversion
governance plus certified internal conversion intent/outcome and report
evidence-pack API foundations. The service remains internal foundation only:
there is no database-backed business persistence, migration, downstream adapter,
runtime recovery command, Gateway/Workbench proof, or supported business API yet.
The internal `GET /api/v1/data-mesh/readiness` diagnostic is available for
operators to inspect the repo-authored `not_certified` data-mesh posture and
blockers; it does not certify or promote a data product.

Initial commands:

```powershell
make install
make check
make ci
uvicorn app.main:app --reload --port 8330
```

RFC-0002 will add support runbooks for:

1. upstream source unavailable,
2. stale evidence,
3. duplicate idea burst,
4. scoring policy disabled,
5. review queue backlog,
6. entitlement denial,
7. idempotency conflict,
8. AI unavailable,
9. unsupported AI output,
10. downstream conversion failure,
11. report/archive handoff failure,
12. replay hash mismatch.

## Current Operation Event Diagnostics

RFC-0002 Slice 15 now emits bounded operation-event logs and the
`lotus_idea_operation_events_total` metric for high-cash signal evaluation,
candidate persistence, lifecycle transitions, advisor queue reads, review
actions, feedback records, conversion intent recording, conversion outcome
recording, report evidence-pack request recording, and data-mesh-readiness
diagnostic reads.

Current outcomes:

1. `accepted`: new process-local foundation record created.
2. `replayed`: duplicate submission with the same idempotency key and payload.
3. `conflict`: idempotency key reused with a different payload.
4. `not_found`: candidate, conversion intent, or related foundation record is absent.
5. `duplicate`, `suppressed`, and `not_eligible`: deterministic signal or
   persistence outcomes that did not create a new candidate.
6. `permission_denied`: caller capability failed closed.
7. `invalid_request`: request shape, timestamp, or idempotency key is invalid.
8. `invalid_state`: lifecycle, review, target authority, or report intent precondition failed.
9. `blocked`: expected current data-mesh-readiness posture while runtime trust
   telemetry and platform certification remain absent.

The metric labels are intentionally low-cardinality: `operation`, `outcome`,
`supportability_status`, `source_authority`, `durable_storage_backed`, and
`supported_feature_promoted`. They must not include portfolio, client, account,
holding, transaction, request body, response body, raw entitlement failure,
trace id, or correlation id values.

These signals are operator diagnostics only. They do not certify durable
database state, data-product promotion, downstream Report/Render/Archive
realization, Gateway/Workbench proof, or supported business capability.
