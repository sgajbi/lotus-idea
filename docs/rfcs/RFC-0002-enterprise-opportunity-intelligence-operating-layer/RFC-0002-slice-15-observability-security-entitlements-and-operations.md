# RFC-0002 Slice 15: Observability, Security, Entitlements, And Operations

Status: Partially Implemented - bounded operation events plus evidence replay, source-ingestion, outbox delivery readiness/run-once, downstream realization, AI explanation, implementation-proof, and advisor queue readiness diagnostics

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
5. `src/app/observability/logging.py` also exposes a bounded request diagnostic
   helper for validation, HTTP, and unhandled-error events. `src/app/main.py`
   uses route templates rather than raw URL paths for those diagnostics.
6. `scripts/source_observability_contract_gate.py` and
   `make source-observability-contract-gate` block raw `print()`, direct Python
   logging, and low-level `log_event` bypasses in application source.
7. `src/app/api/conversion_governance.py` emits bounded operation events for
   conversion-intent and conversion-outcome accepted, replayed, conflict,
   not-found, permission-denied, invalid-request, and invalid-state outcomes.
8. `src/app/api/report_evidence.py` emits bounded operation events for report
   evidence-pack request accepted, replayed, conflict, not-found,
   permission-denied, invalid-request, and invalid-state outcomes.
9. `src/app/api/idea_signals.py`, `src/app/api/candidate_lifecycle.py`,
   `src/app/api/candidate_evidence_replay.py`,
   `src/app/api/ai_governance.py`, `src/app/api/review_queues.py`, and
   `src/app/api/review_workflow.py` emit bounded operation events for
   high-cash evaluation, candidate persistence, lifecycle transitions,
   candidate evidence replay, AI explanation fallback/verifier evaluation,
   advisor queue reads, review actions, and feedback.
10. `tests/unit/test_observability_logging.py` locks the no-sensitive operation
   attribute, metric-label, and route-template request diagnostic contract.
11. `tests/unit/test_source_observability_contract_gate.py` covers the current
    pass behavior and failure cases for raw prints, direct logging imports,
    direct logging calls, and low-level `log_event` bypasses.
12. `tests/integration/test_api_operation_events.py` proves the operation-event
   coverage for the certified internal high-cash, candidate persistence,
   lifecycle, candidate evidence replay, AI explanation, queue, review,
   feedback, conversion, and report evidence-pack API foundations.
13. `tests/integration/test_review_workflow_api.py` continues to prove the
    conversion and report evidence-pack API behavior while the event layer is
    active.
14. `src/app/application/source_ingestion_readiness.py` adds a source-safe
    readiness snapshot for the high-cash Core source-ingestion run-once worker
    configuration and certification blockers.
15. `GET /api/v1/source-ingestion/readiness` exposes that snapshot to
    operators with `idea.source-ingestion.readiness.read`, returns
    `not_certified` posture, and emits bounded
    `source_ingestion_readiness_read` operation events.
16. `POST /api/v1/source-ingestion/run-once` exposes the bounded
    source-ingestion batch foundation as an internal operator action with
    `idea.source-ingestion.run`. It emits bounded
    `source_ingestion_run_once` events, fails closed before mutation when
    durable repository, manifest, or Core configuration is absent or invalid,
    and returns aggregate decision counts only.
17. `tests/unit/test_source_ingestion_readiness.py` and
    `tests/integration/test_source_ingestion_readiness_api.py` prove blocked,
    configured, permission-denied, relative-manifest, source-ingestion
    run-once, and operation-event behavior without exposing portfolio ids, raw
    idempotency keys, source payloads, or candidate ids.
18. `src/app/application/review_queue.py` adds an advisor queue readiness
    snapshot over the existing deterministic queue projection and repository
    snapshot, reporting aggregate counts, exclusion counts, durable-storage
    posture, `not_certified` supportability, and certification blockers without
    exposing candidate identifiers or access-scope identifiers.
19. `GET /api/v1/review-queues/advisor/readiness` exposes that snapshot to
    operators with `idea.review.queue.readiness.read`, returns
    `supportedFeaturePromoted=false`, and emits bounded
    `review_queue_readiness_read` operation events.
20. `tests/unit/test_review_queue_application.py`,
    `tests/integration/test_review_queue_api.py`, and
    `tests/integration/test_api_operation_events.py` prove aggregate readiness
    counts, non-storage blockers, permission-denied behavior, timestamp
    validation, product-safe payloads, and operation-event behavior for the
    advisor queue readiness diagnostic.
20. `GET /api/v1/ai-explanations/readiness` exposes a source-safe model-risk
    operator diagnostic for AI explanation guardrail availability and
    certification blockers. It requires both the `operator` role and
    `idea.ai-explanation.readiness.read`, returns `not_certified` posture and
    `supportedFeaturePromoted=false`, and emits bounded
    `ai_explanation_readiness_read` operation events with `lotus-ai` source
    authority.
21. `tests/unit/test_ai_explanation_readiness.py`,
    `tests/integration/test_ai_governance_api.py`, and
    `tests/integration/test_api_operation_events.py` prove blocked readiness
    posture, permission-denied behavior, product-safe payloads, and
    not-certified operation-event behavior for the AI explanation readiness
    diagnostic.
22. `src/app/application/implementation_proof_readiness.py` adds an aggregate
    RFC-0002 proof-readiness snapshot over existing source-ingestion,
    review-queue, AI-explanation, data-mesh, runtime trust telemetry
    preview/snapshot evidence, outbox-delivery, Workbench, downstream, and
    supported-feature proof
    families without exposing source payloads, outbox event identifiers, raw
    idempotency keys, or broker payloads.
23. `GET /api/v1/implementation-proof/readiness` exposes that snapshot to
    operators with `idea.implementation-proof.readiness.read`, returns
    `not_certified` posture, and emits bounded
    `implementation_proof_readiness_read` operation events.
24. `tests/unit/test_implementation_proof_readiness.py`,
    `tests/unit/test_generate_implementation_proof_readiness.py`, and
    `tests/integration/test_implementation_proof_readiness_api.py` prove
    blocked aggregate proof posture, outbox-delivery proof-family inclusion,
    source-safe payloads, permission-denied behavior, timezone validation,
    unavailable-contract safe errors, and not-certified operation-event
    behavior.
25. `src/app/application/downstream_realization_readiness.py` and
    `GET /api/v1/downstream-realization/readiness` expose certified internal
    downstream realization readiness for Advise, Manage, Report, Render, and
    Archive blockers. The route requires both the `operator` role and
    `idea.downstream-realization.readiness.read`, returns source-safe workflow
    counts only, and emits bounded `downstream_realization_readiness_read`
    operation events.
26. `tests/unit/test_downstream_realization_readiness.py` and
    `tests/integration/test_downstream_realization_readiness_api.py` prove the
    blocked/not-certified posture, source-authority boundaries, role plus
    capability enforcement, product-safe payloads, and operation-event behavior
    for the downstream realization readiness diagnostic.
27. `src/app/application/outbox_delivery_readiness.py` and
    `GET /api/v1/outbox-delivery/readiness` expose certified internal outbox
    delivery readiness for aggregate backlog, status counts, durable repository
    posture, broker configuration posture, publisher-adapter presence,
    source-of-truth paths, and certification blockers. The route requires both
    the `operator` role and
    `idea.outbox-delivery.readiness.read`, returns source-safe aggregate counts
    only, and emits bounded `outbox_delivery_readiness_read` operation events.
28. `tests/unit/test_outbox_delivery_readiness.py` and
    `tests/integration/test_outbox_delivery_readiness_api.py` prove the
    blocked/not-certified posture, broker-configured still-blocked posture,
    invalid retry-limit guard, role plus capability enforcement, product-safe
    payloads, and operation-event behavior for the outbox delivery readiness
    diagnostic.
29. `POST /api/v1/outbox-delivery/run-once` exposes the bounded outbox
    delivery orchestration as an internal operator action with
    `idea.outbox-delivery.run`. It emits bounded
    `outbox_delivery_run_once` events, fails closed without valid broker
    configuration, and returns aggregate counts only.
30. `tests/integration/test_outbox_delivery_readiness_api.py` proves the
    run-once action's blocked-without-broker posture, configured publisher
    delivery path, permission denial, UTC validation, product-safe response
    shape, and `not_certified` operation-event behavior.
31. `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` exposes the
    contract-shaped runtime trust telemetry diagnostic for callers with the
    `operator` role and `idea.mesh.trust-telemetry.snapshot.read`, returning
    source-safe platform trust fields while emitting bounded
    `mesh_trust_telemetry_snapshot_read` operation events.
32. `tests/integration/test_runtime_trust_telemetry_api.py` proves source-safe
    payloads, role plus capability enforcement, timezone validation, and
    not-certified operation-event behavior for the runtime trust telemetry
    snapshot diagnostic.

This foundation remains internal and `foundation_only`. It does not prove
production durable-storage certification, data-product certification,
downstream Report/Render/Archive realization, Gateway/Workbench proof,
dashboard/alert certification, or supported-feature promotion.
The source-ingestion readiness diagnostic and run-once operator action are
explicitly `not_certified` until live Core source proof, scheduled worker
deploy proof, runtime data-mesh telemetry, and Gateway/Workbench proof exist.
The advisor queue readiness diagnostic is explicitly `not_certified` until
durable queue posture, platform caller-context entitlement proof, Workbench
proof, data-product certification, and runtime trust telemetry exist.
The AI explanation readiness diagnostic is explicitly `not_certified` until
`lotus-ai` runtime workflow execution, durable AI lineage storage,
workflow-pack runtime certification, model-risk operations dashboards, runtime
trust telemetry, and Workbench proof exist.
The implementation-proof readiness diagnostic is explicitly `not_certified`
until every reported proof family has implementation-backed live evidence and
supported-feature promotion evidence where applicable.
The downstream realization readiness diagnostic is explicitly `not_certified`
until Advise proposal/suitability intake, Manage action realization,
Report/Render/Archive materialization, Gateway/Workbench product proof,
runtime trust telemetry, and supported-feature evidence exist.
The outbox delivery readiness diagnostic and run-once operator action are
explicitly `not_certified` until live broker runtime proof, downstream consumer
contracts, platform mesh event certification, Gateway/Workbench proof, and
supported-feature evidence exist.
The runtime trust telemetry preview and snapshot diagnostics are explicitly
`not_certified` until platform mesh certification, Gateway/Workbench
discovery, and supported-feature evidence exist.

## Required Work

1. Add metrics, logs, traces, audit events, health/readiness diagnostics, and
   supportability endpoints.
2. Enforce fail-closed entitlements for direct service and Gateway paths.
3. Run dependency, vulnerability, secret, sensitive-content, metric-label, and
   container reviews.
4. Write runbooks for source failures, stale evidence, duplicate bursts, AI
   unavailable, conversion failure, entitlement denial, and replay mismatch.

The first bounded read-only Gateway publication routes now have caller-context
forwarding and unsupported-feature blocking proof in `lotus-gateway`, and
`make endpoint-certification-gate` requires the `lotus-idea` endpoint ledger to
name the exact Gateway route without implying Workbench proof, data-product
certification, client-ready publication, or supported-feature promotion.

## Remaining Gap

1. Add dashboard and alert references only after metric families are stable and
   implemented.
2. Add live runtime source-readiness proof after Core source adapters and
   deployable worker runtime exist.
3. Add product-scope entitlement proof for Workbench and any broader Gateway
   route set after those surfaces are implemented; the first read-only Gateway
   routes remain bounded publication proof only.
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
