# Operations Runbook

Current posture: scaffold operations plus internal domain, persistence/replay,
lifecycle, review, AI-governance, certified internal high-cash, lifecycle,
AI explanation, advisor queue, review-action, and feedback API foundations, and
conversion governance plus certified internal conversion intent/outcome and
report evidence-pack API foundations. The service remains internal foundation only:
repository-backed API persistence is process-local by default and
PostgreSQL-backed only when `LOTUS_IDEA_DATABASE_URL` is configured. There is no
downstream adapter, production recovery command, Gateway/Workbench proof, or
supported business API yet. A versioned migration/rollback schema contract
exists for the durable repository and is enforced by `make migration-contract-gate`.
`make migration-execution-gate` dry-runs apply and rollback execution plans, and
`make migrate` / `make migrate-rollback` execute against PostgreSQL when
`LOTUS_IDEA_DATABASE_URL` is configured. `make postgres-integration-gate` proves
the high-cash API persistence/replay path and the first internal review,
feedback, conversion, report evidence-pack, and advisor queue workflow path
against a real PostgreSQL 18 service when
`LOTUS_IDEA_POSTGRES_INTEGRATION_URL` is configured, including schema
rollback/reapply recovery.
Internal high-cash source-ingestion orchestration now exists as an application
foundation over the Core source port and repository port. It generates a
source-ingestion idempotency key when one is not supplied and classifies
accepted, replayed, conflict, blocked, suppressed, and not-eligible outcomes,
and it now includes a bounded run-once batch worker foundation with per-item
idempotency, batch decision counts, and maximum item validation.
`scripts/run_source_ingestion_worker.py` provides the versioned run-once worker
CLI, and `make source-ingestion-worker-check` validates the manifest contract
without calling Core or writing state. The PostgreSQL runtime proof covers
replay after repository reload plus same-key
changed-source conflict recovery. This is not a deployed scheduler daemon, live
Core source-worker certification, production storage certification,
data-product certification, Gateway route, Workbench proof, or supported
business feature.
The internal `GET /api/v1/data-mesh/readiness` diagnostic is available for
operators to inspect the repo-authored `not_certified` data-mesh posture and
blockers; it does not certify or promote a data product.
The internal `GET /api/v1/source-ingestion/readiness` diagnostic is available
for operators with `idea.source-ingestion.readiness.read` to inspect high-cash
run-once worker manifest, Core base URL, durable repository configuration, and
remaining certification blockers without calling Core or exposing source
payloads. It remains `not_certified` until live Core source proof, scheduled
worker deploy proof, runtime data-mesh telemetry, and Gateway/Workbench proof
exist.

Initial commands:

```powershell
make install
make check
make ci
make postgres-integration-gate
make source-ingestion-worker-check
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
actions, AI explanation fallback/verifier evaluation, feedback records,
conversion intent recording, conversion outcome
recording, report evidence-pack request recording, data-mesh-readiness
diagnostic reads, and source-ingestion-readiness diagnostic reads.

Current outcomes:

1. `accepted`: new foundation record created in the active repository provider.
2. `fallback`: deterministic AI explanation was returned without verified AI
   workflow output.
3. `replayed`: duplicate submission with the same idempotency key and payload.
4. `conflict`: idempotency key reused with a different payload.
5. `not_found`: candidate, conversion intent, or related foundation record is absent.
6. `duplicate`, `suppressed`, and `not_eligible`: deterministic signal or
   persistence outcomes that did not create a new candidate.
7. `permission_denied`: caller capability failed closed.
8. `invalid_request`: request shape, timestamp, or idempotency key is invalid.
9. `invalid_state`: lifecycle, review, target authority, report intent, or AI
   explanation precondition failed.
10. `blocked`: verifier rejected unsupported AI output, or expected current
    data-mesh-readiness posture while runtime trust telemetry and platform
    certification remain absent, or source-ingestion readiness is missing
    run-once worker configuration/certification proof.

The metric labels are intentionally low-cardinality: `operation`, `outcome`,
`supportability_status`, `source_authority`, `durable_storage_backed`, and
`supported_feature_promoted`. They must not include portfolio, client, account,
holding, transaction, request body, response body, raw entitlement failure,
trace id, or correlation id values.

These signals are operator diagnostics only. `durable_storage_backed=true`
confirms only that the active repository provider is durable; it does not
certify production recovery readiness, data-product promotion, broader
downstream Report/Render/Archive realization, Gateway/Workbench proof, or
supported business capability.

## API Certification Reference

The current certified foundation endpoint inventory is summarized in
`docs/operations/api-certification.md` and backed by
`docs/operations/endpoint-certification-ledger.json`.

The inventory covers high-cash evaluation, high-cash persistence, lifecycle
transition, AI explanation evaluation, advisor queue, review action, feedback,
conversion intent, conversion outcome, report evidence-pack request, and
data-mesh-readiness and source-ingestion-readiness diagnostic endpoints. These endpoints are certified as
internal foundations or operator diagnostics only; they are not supported
business features.
