# Operator Workflows Operations Runbook

## Purpose

This runbook supports non-AI internal operator workflows in `lotus-idea`.
It helps operators interpret source-safe dashboard panels and Prometheus alert
rules for source ingestion, outbox delivery, downstream realization, runtime
trust telemetry, and aggregate implementation-proof readiness.

## Operating Boundary

The dashboard and alert rules certify operational visibility over implemented
operation-event telemetry and the bounded outbox readiness projection. They do not certify live
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
| Outbox Delivery Runtime State | Is durable work pending, due, deferred, leased, failed, published, or dead-lettered? | Triage actual aggregate queue state independently of API traffic. |
| Downstream Realization Readiness And Submission | Are downstream readiness or local submission paths blocked? | Separate local submission posture from downstream-owned execution or approval outcomes. |
| Runtime Trust And Implementation Proof Readiness | Are runtime trust telemetry or aggregate proof readiness checks blocked? | Identify remaining proof blockers before any support or product-surface promotion. |
| Outbox Operator Activity | Are readiness and run-once calls blocked or invalid? | Diagnose operator interaction separately from durable queue state. |
| Outbox Oldest Due Age | How long has the oldest delivery-ready event waited? | Escalate sustained age above 900 seconds. |
| Outbox Configuration And Collection | Is broker configuration ready and is the bounded projection collectible? | Separate configuration/certification blockers from runtime backlog. |

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

### Outbox Lineage Investigation

When a request cannot be connected to a durable or published event:

1. confirm the producer contract with `make outbox-event-contract-gate`,
2. use authorized database support access to compare the event's correlation,
   trace, optional causation, and lineage-origin fields,
3. confirm the publisher transport trace equals the event trace, not its
   causation identifier,
4. expect an idempotent replay to retain the first event lineage even when the
   retry request has a new trace,
5. preserve the row and use governed dead-letter recovery for delivery
   failure; do not rewrite lineage or copy raw broker payloads into tickets.

Missing required lineage, causation on ordinary request lineage, or equal
trace and causation values is a producer-contract defect. It is not evidence
of downstream certification or authority.

## outbox-delivery-collection-failed

Trigger: `lotus_idea_outbox_delivery_collection_success` remains below `1`
for 5 minutes.

Response:

1. Confirm `/health/ready` and PostgreSQL connectivity.
2. Check bounded projection logs and database saturation without querying raw
   event payloads.
3. Restore projection collection before using the remaining outbox gauges for
   recovery decisions.

## outbox-delivery-dead-letter-present

Trigger: dead-letter state remains above `0` for 15 minutes.

Response:

1. Use the governed dead-letter inspection API and preserve source-safe output.
2. Classify the publisher failure and confirm event-family/schema eligibility.
3. Re-drive only through the authorized one-time fenced workflow, then verify
   dead-letter count returns to `0` or retain quarantine with an incident record.

## outbox-delivery-expired-lease-present

Trigger: expired-lease state remains above `0` for 10 minutes.

Response:

1. Confirm active publisher workers and lease duration configuration.
2. Verify an expired lease becomes delivery-ready and can be reclaimed with a
   new fenced lease.
3. Escalate repeated expiry as worker latency or availability degradation; do
   not clear lease ownership directly in the database.

## outbox-delivery-backlog-stalled

Trigger: delivery-ready count remains above `100`, or oldest delivery-ready age
remains above `900` seconds, for 15 minutes. Values at those thresholds remain
quiet.

Response:

1. Check collection success and configuration readiness first.
2. Compare delivery-ready, failed, deferred-retry, expired-lease, and
   dead-letter counts to identify the pressure source.
3. Run the idempotent bounded delivery action only when publisher configuration
   and downstream posture are valid, then verify count and age decline.

## outbox-delivery-retry-pressure

Trigger: deferred-retry count remains above `50` for 30 minutes. A count of
`50` remains quiet.

Response:

1. Confirm the failure is transient and inspect bounded failure categories.
2. Preserve backoff and retry limits; do not accelerate retries by editing due
   timestamps.
3. Verify deferred work becomes due and drains, or escalates to governed
   dead-letter handling after the retry limit.

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
2. `contracts/observability/lotus-idea-outbox-supportability.v1.json`,
3. `monitoring/grafana/dashboards/lotus-idea-operator-workflows-operations.json`,
4. `monitoring/prometheus/rules/lotus-idea-operator-workflows-operations.rules.yml`,
5. `scripts/operator_workflows_operations_contract_gate.py`,
6. `scripts/outbox/supportability_contract_gate.py`,
7. `scripts/operator_workflows_operations_proof_contract_gate.py`,
8. `make operator-workflows-ops-contract-gate`,
9. `make outbox-supportability-contract-gate`,
10. `make operator-workflows-operations-proof-contract-gate`.

Both gates must pass after any operation metric, dashboard, alert, or
source-authority vocabulary change. The gates fail closed if the contract,
dashboard, or alert artifacts drift away from the code-owned source-authority
vocabulary.
