# Operator Workflows Operations Runbook

## Purpose

This runbook supports non-AI internal operator workflows in `lotus-idea`.
It helps operators interpret source-safe dashboard panels and Prometheus alert
rules for source ingestion, outbox delivery, downstream realization, runtime
trust telemetry, and aggregate implementation-proof readiness.

## Operating Boundary

The dashboard and alert rules certify operational visibility over implemented
`lotus_idea_operation_events_total` telemetry only. They do not certify live
source ingestion, external broker publication, downstream execution outcomes,
data-mesh certification, Gateway or Workbench behavior, client-ready use, or
supported-feature promotion.

The `source_authority` metric label is governed by
`OPERATION_EVENT_SOURCE_AUTHORITIES` in `src/app/observability/logging.py`.
Allowed labels are `lotus-advise`, `lotus-ai`, `lotus-archive`,
`lotus-core`, `lotus-idea`, `lotus-manage`, `lotus-performance`,
`lotus-render`, `lotus-report`, `lotus-risk`, and aggregate
`source-owned`. Dashboards and alerts may group by this label, but any
explicit matcher must use only those labels. Never encode client, account,
portfolio, holding, request, response, raw entitlement, or local ad hoc
identifiers as source authority.

## Dashboard Panels

| Panel | Operator Question | Expected Use |
| --- | --- | --- |
| Source Ingestion Readiness And Run Once | Are source-ingestion readiness checks or run-once attempts blocked? | Start with configuration, manifest, Core query/control-plane URL, and scheduled-worker proof posture. |
| Outbox Delivery Backlog And Recovery Posture | Are outbox readiness checks or run-once attempts blocked or invalid? | Inspect broker configuration, due retry/dead-letter posture, expired leases, and idempotent operator run identity. |
| Downstream Realization Readiness And Submission | Are downstream readiness or local submission paths blocked? | Separate local submission posture from downstream-owned execution or approval outcomes. |
| Runtime Trust And Implementation Proof Readiness | Are runtime trust telemetry or aggregate proof readiness checks blocked? | Identify remaining proof blockers before any support or product-surface promotion. |

## source-ingestion-readiness-blocked

Trigger: `source_ingestion_readiness_read` or `source_ingestion_run_once`
operation events with `outcome="blocked"` or `outcome="invalid_state"`
increase within the alert window.

Response:

1. Read `GET /api/v1/source-ingestion/readiness` with an operator caller
   context.
2. Confirm whether the blocker is missing manifest configuration, unavailable
   Core query or control-plane URLs, missing durable repository configuration,
   missing live Core source proof, or missing scheduled-worker proof.
3. Do not infer live source certification from run-once execution alone.

## outbox-delivery-readiness-blocked

Trigger: `outbox_delivery_readiness_read` or `outbox_delivery_run_once`
operation events with `outcome="blocked"` or `outcome="invalid_state"`
increase within the alert window.

Response:

1. Read `GET /api/v1/outbox-delivery/readiness`.
2. Inspect backlog, due retry, cooling-down failed, final, dead-letter,
   expired-lease, and blocker posture through source-safe aggregate fields
   only.
3. Preserve idempotent operator run identity before invoking
   `POST /api/v1/outbox-delivery/run-once`.
4. Do not inspect raw event payloads or downstream payload bodies in dashboard
   or alert context.

## downstream-realization-readiness-blocked

Trigger: `downstream_realization_readiness_read` or
`downstream_realization_submission` operation events with
`outcome="blocked"`, `outcome="invalid_state"`, or
`outcome="permission_denied"` increase within the alert window.

Response:

1. Read `GET /api/v1/downstream-realization/readiness`.
2. Separate local submission posture from downstream-owned outcomes.
3. Route Advise proposal, Manage action, and Report intake/materialization
   blockers to the owning service when the blocker is outside `lotus-idea`.
4. Do not treat local accepted submission posture as suitability approval,
   mandate approval, report rendering, archive authority, or execution proof.

## implementation-proof-readiness-blocked

Trigger: `mesh_readiness_read`, `mesh_trust_telemetry_preview_read`,
`mesh_trust_telemetry_snapshot_read`, or `implementation_proof_readiness_read`
operation events with `outcome="blocked"` increase within the alert window.

Response:

1. Read `GET /api/v1/implementation-proof/readiness`.
2. Use `overallBlockers` and capability-level blockers to identify missing
   source, runtime, downstream, Gateway, Workbench, or supported-feature proof.
3. Keep supported-feature promotion blocked until implementation, API,
   OpenAPI, supported-features, docs, wiki, CI, and mainline evidence agree.
4. Do not reclassify not-certified posture as production support.

## Evidence Requirements

Certification evidence must include:

1. `contracts/observability/lotus-idea-operator-workflows-operations.v1.json`,
2. `monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json`,
3. `monitoring/prometheus/rules/lotus-idea-operator-workflows-operations.rules.yml`,
4. `scripts/operator_workflows_operations_contract_gate.py`,
5. `scripts/operator_workflows_operations_proof_contract_gate.py`,
6. `make operator-workflows-ops-contract-gate`,
7. `make operator-workflows-operations-proof-contract-gate`.

Both gates must pass after any operation metric, dashboard, alert, or
source-authority vocabulary change. The gates fail closed if the contract,
dashboard, or alert artifacts drift away from the code-owned source-authority
vocabulary.
