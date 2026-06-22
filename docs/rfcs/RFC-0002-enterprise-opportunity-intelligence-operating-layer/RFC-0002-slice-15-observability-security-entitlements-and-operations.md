# RFC-0002 Slice 15: Observability, Security, Entitlements, And Operations

Status: Partially Implemented

## Outcome

Harden the service for production-grade operation, support, and secure use.

## Current Implementation Evidence

RFC-0002 Slice 15 now has a first implementation-backed operation observability
foundation:

1. `src/app/observability/logging.py` defines bounded operation, outcome, and
   supportability vocabulary for idea operations.
2. `src/app/observability/logging.py` emits product-safe structured operation
   logs and increments `lotus_idea_operation_events_total`.
3. Operation metric labels are limited to `operation`, `outcome`,
   `supportability_status`, `source_authority`, `durable_storage_backed`, and
   `supported_feature_promoted`.
4. `OperationEvent` rejects sensitive attributes such as client, portfolio,
   account, holding, transaction, request body, response body, raw entitlement
   failure, trace id, and correlation id fields.
5. `src/app/api/conversion_governance.py` emits bounded operation events for
   conversion-intent and conversion-outcome accepted, replayed, conflict,
   not-found, permission-denied, invalid-request, and invalid-state outcomes.
6. `src/app/api/report_evidence.py` emits bounded operation events for report
   evidence-pack request accepted, replayed, conflict, not-found,
   permission-denied, invalid-request, and invalid-state outcomes.
7. `src/app/api/idea_signals.py`, `src/app/api/candidate_lifecycle.py`,
   `src/app/api/candidate_evidence_replay.py`,
   `src/app/api/ai_governance.py`, `src/app/api/review_queues.py`, and
   `src/app/api/review_workflow.py` emit bounded operation events for
   high-cash evaluation, candidate persistence, lifecycle transitions,
   candidate evidence replay, AI explanation fallback/verifier evaluation,
   advisor queue reads, review actions, and feedback.
8. `tests/unit/test_observability_logging.py` locks the no-sensitive operation
   attribute and metric-label contract.
9. `tests/integration/test_api_operation_events.py` proves the operation-event
   coverage for the certified internal high-cash, candidate persistence,
   lifecycle, candidate evidence replay, AI explanation, queue, review, and
   feedback API foundations.
10. `tests/integration/test_review_workflow_api.py` continues to prove the
    conversion and report evidence-pack API behavior while the event layer is
    active.
11. `src/app/application/source_ingestion_readiness.py` adds a source-safe
    readiness snapshot for the high-cash Core source-ingestion run-once worker
    configuration and certification blockers.
12. `GET /api/v1/source-ingestion/readiness` exposes that snapshot to
    operators with `idea.source-ingestion.readiness.read`, returns
    `not_certified` posture, and emits bounded
    `source_ingestion_readiness_read` operation events.
13. `tests/unit/test_source_ingestion_readiness.py` and
    `tests/integration/test_source_ingestion_readiness_api.py` prove blocked,
    configured, permission-denied, relative-manifest, and operation-event
    behavior without calling Core or writing repository state.

This foundation remains internal and `foundation_only`. It does not prove
production durable-storage certification, data-product certification,
downstream Report/Render/Archive realization, Gateway/Workbench proof,
dashboard/alert certification, or supported-feature promotion.
The source-ingestion readiness diagnostic is explicitly `not_certified` until
live Core source proof, scheduled worker deploy proof, runtime data-mesh
telemetry, and Gateway/Workbench proof exist.

## Required Work

1. Add metrics, logs, traces, audit events, health/readiness diagnostics, and
   supportability endpoints.
2. Enforce fail-closed entitlements for direct service and Gateway paths.
3. Run dependency, vulnerability, secret, sensitive-content, metric-label, and
   container reviews.
4. Write runbooks for source failures, stale evidence, duplicate bursts, AI
   unavailable, conversion failure, entitlement denial, and replay mismatch.

## Remaining Gap

1. Add dashboard and alert references only after metric families are stable and
   implemented.
2. Add live runtime source-readiness proof after Core source adapters and
   deployable worker runtime exist.
3. Add Gateway path entitlement proof when Gateway routes are implemented.
4. Complete dependency, vulnerability, secret, sensitive-content, metric-label,
   and container reviews for the full supported service surface before any
   supported-feature promotion.
5. Expand runbooks for source failures, stale evidence, duplicate bursts,
   AI-unavailable fallback, conversion failure, entitlement denial, and replay
   mismatch after those flows have implementation-backed runtime behavior.

## Acceptance Gate

1. No sensitive data appears in logs, metrics, docs, or screenshots.
2. Security findings are fixed or formally treated.
3. Operational diagnostics are useful without exposing restricted payloads.
4. Runbooks are implementation-backed.
