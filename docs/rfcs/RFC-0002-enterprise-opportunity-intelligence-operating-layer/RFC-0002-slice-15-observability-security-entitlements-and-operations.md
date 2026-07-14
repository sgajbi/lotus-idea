# RFC-0002 Slice 15: Observability, Security, Entitlements, And Operations

Status: Partially Implemented - bounded operation events plus evidence replay, source-ingestion, scheduled-worker proof, outbox delivery readiness/run-once with durable retry scheduling and PostgreSQL repository-side readiness projection, outbox broker proof, downstream realization, AI explanation, implementation-proof, and advisor queue readiness diagnostics with bounded PostgreSQL aggregate projection

## Outcome

Harden the service for production-grade operation, support, and secure use.

## Issue 346 License And IP Compliance

The service now has a versioned, fail-closed license and IP control for the
complete resolved runtime and CI dependency closure:

1. The policy records exact component versions, scopes, SPDX expressions,
   authoritative source links, attribution, and conditional obligations.
2. Lock hashes and deterministic `THIRD_PARTY_NOTICES.md` generation prevent
   dependency and attribution drift. Unknown and denied expressions fail.
3. Exceptions require application-owner, security, and legal approval,
   immutable evidence, a bounded reason, and expiry. `CODEOWNERS` routes source
   review but does not replace those decisions.
4. Main Releasability records policy version, runtime/CI lock hashes, NOTICE
   digest, SBOM serial, active exception IDs, and final image digest, then
   verifies the exact binding before accepting release evidence.
5. The image includes the proprietary service license and notices. Base-image
   packages, generated code, model assets, and data assets retain explicit
   independent review posture.

This is release and governance hardening inside the existing service. It adds
no customer capability, data-product certification, legal authority, or
runtime boundary, and does not change supported-feature posture.

## Current Implementation Evidence

RFC-0002 Slice 15 now has a first implementation-backed operation observability
foundation. Its security posture includes
`lotus-idea.ai-action-content-policy.v1`.

Proposed AI actions are checked by type and untrusted content before claim
verification, accepted labels are server-owned, and unsafe raw labels are
excluded from responses, persistence, and audit attributes. The readiness
endpoint and model-risk operations contract expose the same policy version
without claiming provider-runtime or supported-feature readiness.

AI lineage now also exposes `lotus-idea.ai-output-integrity.v1`. The digest
binds ordered explanation, claim, action, workflow/evaluator, and policy
content into replay/conflict identity while retaining no unrestricted output
text. Model-risk and lifecycle contracts govern digest semantics, access,
seven-year regulated-advisory retention, and explicit pre-v1 unverifiable
migration posture.

Production-like AI output now fails closed under
`lotus-idea.ai-execution-provenance-policy.v1`. Only local/test may accept an
explicitly unattested fixture, and that posture is carried in API, audit, and
lineage evidence without clearing runtime proof. Deterministic fallback remains
available. Signed Lotus AI run/model attestation issuance and Idea-side
verification are mainline-proven with bounded success/rejection telemetry;
producer issue `sgajbi/lotus-ai#113` is closed. This remains
implementation-backed consumer hardening rather than live AI runtime or
supported-feature completion.

Implementation evidence:

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
   `src/app/api/ai_governance.py`, `src/app/api/review_queue/`, and
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
    snapshot over deterministic queue policy. Durable repositories can provide
    aggregate counts, exclusion counts, durable-storage posture,
    `not_certified` supportability, and certification blockers through a
    repository-side readiness summary projection; process-local and snooze-aware
    evaluations retain the domain snapshot fallback. The diagnostic does not
    expose candidate identifiers or access-scope identifiers.
19. `GET /api/v1/review-queues/advisor/readiness` exposes that snapshot to
    operators with `idea.review.queue.readiness.read`, returns
    `supportedFeaturePromoted=false`, and emits bounded
    `review_queue_readiness_read` operation events.
20. `tests/unit/test_review_queue_application.py`,
    `tests/integration/test_review_queue_api.py`, and
    `tests/integration/test_api_operation_events.py` prove aggregate readiness
    counts, bounded PostgreSQL aggregate query shape, non-storage blockers,
    permission-denied behavior, timestamp validation, product-safe payloads, and
    operation-event behavior for the advisor queue readiness diagnostic.
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
    operation events. Durable PostgreSQL providers compute those workflow
    counts through a repository-side projection over only
    `idea_conversion_intent`, `idea_conversion_outcome`, and
    `idea_report_evidence_pack_request`, without materializing candidate,
    audit, outbox, downstream-submission, or AI-lineage state.
26. `tests/unit/test_downstream_realization_readiness.py` and
    `tests/unit/test_postgres_downstream_readiness.py`, plus
    `tests/integration/test_downstream_realization_readiness_api.py`, prove the
    blocked/not-certified posture, source-authority boundaries, repository-side
    readiness projection without `snapshot()` hydration, role plus capability
    enforcement, product-safe payloads, and operation-event behavior for the
    downstream realization readiness diagnostic.
27. `src/app/application/outbox/readiness.py` and
    `GET /api/v1/outbox-delivery/readiness` expose certified internal outbox
    delivery readiness for aggregate backlog, status counts, due retry posture,
    retry-deferred failed-row counts, durable repository posture, broker configuration posture,
    publisher-adapter presence, source-of-truth paths, and certification
    blockers. The route requires both the `operator` role and
    `idea.outbox-delivery.readiness.read`, returns source-safe aggregate counts
    only, and emits bounded `outbox_delivery_readiness_read` operation events.
    Durable PostgreSQL providers compute the readiness summary with bounded
    `idea_outbox_event` aggregate queries that count failed events as
    delivery-ready only when their `next_attempt_at_utc` is due and report
    failed events still cooling down separately, instead of materializing
    unrelated repository snapshots.
28. `tests/unit/outbox/test_outbox_delivery_readiness.py` and
    `tests/unit/outbox/test_postgres_readiness.py`, plus
    `tests/integration/outbox/test_delivery_readiness_api.py`, prove the
    blocked/not-certified posture, broker-configured still-blocked posture,
    invalid retry-limit guard, retry-deferred count posture, repository-side
    projection without snapshot hydration, role plus capability enforcement,
    product-safe payloads, and
    operation-event behavior for the outbox delivery readiness diagnostic.
29. `POST /api/v1/outbox-delivery/run-once` exposes the bounded outbox
    delivery orchestration as an internal operator action with
    `idea.outbox-delivery.run`. It emits bounded
    `outbox_delivery_run_once` events, fails closed without valid broker
    configuration, records first/last failure timing plus a deterministic
    capped next-attempt schedule for failed publication attempts, and returns
    aggregate counts only.
30. `tests/integration/outbox/test_delivery_readiness_api.py` proves the
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
33. `contracts/observability/lotus-idea-operation-metrics.v1.json`,
    `scripts/operation_metric_contract_gate.py`, and
    `make operation-metric-contract-gate` now define and enforce a
    machine-readable operation metric catalog for
    `lotus_idea_operation_events_total`. The gate keeps the catalog aligned to
    code-owned operation, outcome, label, source-authority, and supportability
    vocabulary, and blocks premature dashboard, alert, mesh,
    Gateway/Workbench, or supported-feature claims.
34. `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`,
    `scripts/ai_model_risk_operations_contract_gate.py`,
    `scripts/ai_model_risk_operations_proof_contract_gate.py`,
    `monitoring/grafana/dashboards/lotus-idea-ai-model-risk-operations.json`,
    `monitoring/prometheus/rules/lotus-idea-ai-model-risk-operations.rules.yml`,
    and `make ai-model-risk-operations-proof-contract-gate` now define and
    enforce certified repo-owned AI model-risk dashboard, alert-rule, and
    runbook artifacts for implemented AI explanation and readiness telemetry.
    The proof blocks premature `lotus-ai`, Workbench, client-ready, data-mesh,
    or supported-feature certification claims.

This foundation remains internal and `foundation_only`. It does not prove
production durable-storage certification, data-product certification,
downstream Report/Render/Archive realization, Gateway/Workbench proof,
client-ready publication, or supported-feature promotion.
The source-ingestion readiness diagnostic and run-once operator action are
explicitly `not_certified` until live Core source proof, certified long-running
scheduled runtime proof, runtime data-mesh telemetry, Gateway/Workbench proof,
and supported-feature promotion evidence exist. A valid scheduled-worker
deploy-contract artifact may clear only the
`scheduled_worker_deploy_proof_missing` blocker.
The advisor queue readiness diagnostic is explicitly `not_certified` until
durable queue posture, Workbench proof, data-product certification, and runtime
trust telemetry exist. Platform caller-context scope forwarding and direct
queue enforcement now exist for the first bounded Gateway advisor-queue route.
The candidate detail route also applies platform caller-context scope headers
fail-closed against the persisted candidate scope, and the bounded Gateway
candidate detail route forwards those headers without interpreting them.
The AI explanation readiness diagnostic is explicitly `not_certified` until
`lotus-ai` runtime workflow execution, workflow-pack runtime certification,
certified model-risk operations dashboards and alerts, runtime trust telemetry,
and Workbench proof exist. The current AI lineage store proof clears only the
aggregate lineage-store blocker, and the current AI model-risk operations
contract narrows the prior dashboard gap to a not-certified contract posture;
neither is `lotus-ai` runtime, dashboard, alert, Workbench, or supported
feature certification evidence.
The verifier may report `lotusAiRunAttestationAvailable=true`; this is local
capability availability, not certification. The source-safe
`lotus-ai-attestation-contract-proof` validates producer and consumer code but
clears no blocker until mainline CI evidence is available.
The implementation-proof readiness diagnostic is explicitly `not_certified`
until every reported proof family has implementation-backed live evidence and
supported-feature promotion evidence where applicable.
The downstream realization readiness diagnostic is explicitly `not_certified`
until Advise proposal/suitability intake, Manage action realization,
Report/Render/Archive materialization, Gateway/Workbench product proof,
runtime trust telemetry, and supported-feature evidence exist.
The outbox delivery readiness diagnostic and run-once operator action are
explicitly `not_certified` until live broker runtime proof, downstream consumer
contracts, platform mesh event publication proof, Gateway/Workbench proof, and
supported-feature evidence exist.
The bounded outbox broker proof artifact is source-safe and clears only
aggregate broker configuration/runtime-proof blockers in implementation-proof
readiness. It does not change the endpoint supportability posture or certify
external event publication.
The runtime trust telemetry preview and snapshot diagnostics are explicitly
`not_certified` until platform mesh certification, Gateway/Workbench
discovery, and supported-feature evidence exist.

## Issue 329 Durable Outbox Supportability Telemetry

Prometheus scrapes now invoke the existing bounded readiness use case and emit
fixed-label gauges for outbox state counts, oldest delivery-ready age,
configuration readiness, and projection collection success. API-call volume
remains a separate operation counter, so absent operator traffic cannot hide a
stalled queue.

The dashboard separates runtime state, operator activity, due age, and
configuration/collection posture. Sustained alerts cover collection failure,
dead letters, expired leases, due backlog count/age, and deferred-retry
pressure. Threshold policy is code-owned, contract-gated, and exercised by a
real `promtool test rules` fixture for healthy and breached scenarios. Labels
are limited to repository and governed state; event, client, portfolio,
payload, request, and idempotency identity remain forbidden. This improves
internal supportability only and does not certify a broker or consumer.

## Issue 345 Service SLO And Capacity Foundation

Lotus Idea now separates service/workflow reliability from mesh data-product
quality through `lotus-idea-service-slo-capacity.v1.json`. The service contract
defines initial API, source-ingestion, outbox-delivery, downstream-dependency,
and PostgreSQL availability/latency budgets plus bounded capacity assumptions.

Runtime metrics are implementation-backed for HTTP route-template latency and
status classes, workflow duration/outcomes/item throughput, governed dependency
logical calls including retries, and PostgreSQL mutation/lifecycle/snapshot
duration and outcomes. Prometheus recording rules and multi-window burn alerts
are tested with real `promtool` healthy and breached fixtures. A repo-owned
Grafana dashboard separates service, dependency, database, workflow, and queue
posture and retains explicit certification gaps.

This is design modularity inside the existing process. No workload,
failure-isolation, ownership, or operability evidence justifies a separate SLO
service. Production certification remains blocked on representative load/soak,
dependency-failure, PostgreSQL pool-saturation, production-like resource, and
platform-owned cost baselines.
The current injected/direct PostgreSQL connection must not be described as a
measured pool, and no supported feature is promoted by this foundation.

The issue `#345` baseline sub-slice now adds a closed, source-safe evidence
model and guarded workload runner. It can exercise API, source-ingestion,
outbox-delivery, dependency-failure/recovery, and read-only PostgreSQL probes;
stores only aggregate latency, outcome, throughput, queue, retry, and
utilization posture; and requires explicit mutation confirmation, including a
second production confirmation. Test-profile evidence remains report-only.
Observed PostgreSQL utilization does not clear the saturation/load-shed
blocker, and no load/soak, dependency-failure, saturation, or cost blocker is
removed until a qualifying production-like artifact is reviewed.

The PostgreSQL capacity sub-slice now implements code-owned 70% warning and 90%
shed thresholds, a shared aggregate `pg_stat_activity/max_connections`
projection, a durable repository posture port, bounded collection, utilization,
and one-hot posture metrics, tested warning/shed/unavailable alerts, and
fail-closed source-ingestion/outbox shedding before external runtime
construction. Health, readiness, lifecycle, recovery, reconciliation, and
data-lifecycle authority remain available. This clears the missing-metric
implementation blocker only; production-like threshold stress, recovery,
resource, and platform-owned cost evidence remain required.

Controlled PostgreSQL threshold/recovery automation now crosses a narrow
application port and guarded infrastructure adapter. It verifies dedicated
database identity and a hard `max_connections` ceiling, requires an exact
operator acknowledgement, prohibits production execution, releases held
connections on every path, and emits source-safe evidence. The baseline no
longer accepts caller-asserted saturation, resource, or cost booleans.
Disposable test evidence reached the 90% shed threshold and recovered to
normal, but remains explicitly non-certifying.

Production-like qualification is now a separate attested path. A manual,
main-only workflow runs through the protected `capacity-production-like`
GitHub environment on a dedicated runner and signs the exact proof artifact.
Baseline verification pins repository, signer workflow, main source ref, and
source commit before saturation evidence can count. This implementation cannot
produce qualifying evidence until merged to `main` and the protected
environment and runner are configured; the blocker therefore remains open.

The resource-evidence sub-slice adds a bounded process snapshot model, a
narrow probe port, a Prometheus parser adapter, guarded collection CLI, and
blocking contract gate. It records CPU core consumption rate, resident and
virtual memory, and optional file-descriptor utilization without retaining raw
scrapes or endpoint identity. A live test observation against Lotus Idea
validated the HTTP/parser path. The artifact is deliberately non-certifying:
process metrics do not prove production-like sizing, cloud cost, billing
allocation, horizontal scale, or a need for another deployable.

Production-like resource attestation is now implementation-backed in the
protected load/soak producer. It collects 61 samples over 3,600 seconds while
the five steady-state scenarios run, fails fast if either process fails,
validates load and resource artifacts independently, and signs each artifact
separately. Consumer verification pins repository, load/soak signer, main ref,
and exact commit. A valid receipt removes only
`production_like_resource_attestation_missing`; no qualifying receipt exists
until mainline execution succeeds.

The aggregate baseline now separates `resourceAttestationVerified` from
`costAttributionVerified`. Official provider/platform billing adapters,
allocation, decimal reconciliation, and attestation remain outside Idea and are
tracked in `lotus-platform#495`. The platform producer contract and protected
workflow plus Idea's narrow cross-repository verifier are implemented locally.
Idea accepts cost qualification only when the platform repository, signer,
main ref, commit, and artifact digest verify and the platform resource digest
and run id match the already attested Idea resource proof. Therefore
`cost_attribution_evidence_missing` stays open until protected mainline
execution produces that matching evidence.

Dependency-failure evidence now uses closed source-failure classification
instead of a caller-selected expectation boolean. The source-ingestion API
publishes aggregate `sourceFailureCounts` and both governed 502 Problem Details
contracts. The bounded HTTP adapter retains only those counters or governed
codes. Workload qualification accepts only exclusive `source_unavailable`
evidence and requires a completed or replayed recovery with all failure counts
at zero. Entitlement denial, mixed failures, capacity/configuration blocks, and
generic blocked responses fail closed. This clears the evidence-classification
implementation gap only; controlled production-like fault injection, recovery
execution, attestation, mainline CI, and review remain required.

Dependency recovery now has a distinct protected attestation path. Local
measurements can set `dependencyRecoveryObserved` but cannot remove
`dependency_recovery_attestation_missing`. The manual main-only producer
workflow requires the protected capacity environment, governed self-hosted
runner, exact operator confirmation, externally controlled source fault, and
clean recovery during the configured delay. It validates and attests the exact
source-safe baseline. Consumer verification pins repository, dedicated signer,
main ref, and exact commit; qualification requires at least one classified
fault plus one successful recovery and zero errors/conflicts. This
implementation cannot produce qualifying evidence before merge and protected
runtime configuration, so the blocker remains open.

The capacity vocabulary now includes `downstream_submission`, closing a
contract/documentation mismatch that previously claimed downstream load
coverage without an executable scenario. The runner accepts only allowlisted
conversion-intent or report evidence-pack handoff paths, requires the existing
Idea downstream-submit capability, emits unique transient idempotency keys,
expects accepted responses, and never stores the resource path or identifiers.
This remains Idea-owned intent handoff measurement; it does not grant
suitability, execution, render, archive, or downstream outcome authority. The
scenario set is contract-gated against runtime vocabulary. Idea-local protected
automation now seeds the dedicated synthetic handoff resource. Canonical
front-office stack invocation and successful mainline evidence remain separate
and pending.

Idea-local seed automation now closes the resource-construction gap through a
layered application use case, narrow seed port, bounded HTTP adapter, guarded
CLI, and repository-native Make target. It creates deterministic synthetic
high-cash candidate evidence, advances only the governed lifecycle sequence,
records explicit advisor review approval, and creates an Advise proposal
conversion intent. Credentials remain environment-only; response size, status,
and shape fail closed; every mutation is idempotent; and the atomic manifest is
explicitly seed-only, non-certifying, and non-promoting. Capacity runs accept
the manifest only when schema, synthetic posture, commit, branch, and route
shape match. Canonical Workbench/platform automation still needs to invoke and
prove this command for cross-repository live-stack evidence; the Idea-local
protected producer invokes it directly.

The steady-state load/soak producer is now implementation-backed. A paced
application use case cycles API, source ingestion, outbox delivery, downstream
submission, and PostgreSQL batches over one shared observation window while
retaining a monotonic offset on every sample. Qualification requires at least
1,000 samples and a 3,600-second first-to-last span for each scenario; total
process lifetime alone is insufficient. Equal scenario volume/concurrency and
PostgreSQL parity fail closed. Dependency fault/recovery remains a separate
attested exercise so expected source failure cannot dilute steady-state SLOs.

The manual main-only `service-load-soak-evidence.yml` workflow runs in the
protected capacity environment, seeds the isolated synthetic handoff resource,
executes the five scenarios, validates the exact source-safe artifact against
code-owned SLO thresholds, and only then creates provenance attestation. The
consumer verifier pins repository, dedicated signer, main ref, and source
commit. Contract gates bind SLO values, sample minima, workflow shape, scenario
set, and gate-before-attestation ordering. This is design modularity over the
existing application ports and adapters; there is still no workload,
failure-isolation, ownership, or operability evidence for another deployable.
No qualifying artifact exists until this implementation is merged and the
protected workflow succeeds, so certification and supported-feature posture do
not change.

## Required Work

The AI metadata boundary is now allowlist-based rather than denylist-based.
`lotus-idea.ai-metadata-envelope.v1` admits only code-owned, purpose-scoped
operational routing values; unknown fields, unapproved values, length abuse,
and control characters fail before candidate lookup or persistence. OpenAPI,
readiness, model-risk contracts, API tests, and source-safe lineage retention
are aligned. This closes the Idea-side defect tracked by `#341` without
claiming a live `lotus-ai` provider call, runtime certification, or supported
feature.

1. Add metrics, logs, traces, audit events, health/readiness diagnostics, and
   supportability endpoints.
2. Enforce fail-closed entitlements for direct service and Gateway paths.
3. Run dependency, vulnerability, secret, sensitive-content, metric-label, and
   container reviews.
4. Write runbooks for source failures, stale evidence, duplicate bursts, AI
   unavailable, conversion failure, entitlement denial, and replay mismatch.

The first bounded read-only Gateway publication routes now have caller-context
forwarding and unsupported-feature blocking proof in `lotus-gateway`. The
advisor queue and candidate detail routes also forward platform
entitlement-scope headers. `lotus-idea` enforces them fail-closed against queue
query filters and candidate-detail access scope before returning candidate
detail. Review-action and feedback mutation routes use trusted caller-context
entitlement headers as actor scope and apply governance against persisted
candidate scope. Request bodies cannot assert access or authorization scope.
`make
endpoint-certification-gate` requires the `lotus-idea` endpoint ledger to name
the exact Gateway route without implying Workbench proof, data-product
certification, client-ready publication, or supported-feature promotion.

## Remaining Gap

Release image identity now follows `lotus.image-identity.v1`. Issue `#342` is
fixed locally by removing the pre-push digest placeholder, exposing explicit
local versus digest-bound `/version` posture, degrading production-like
readiness on invalid bindings, and cross-checking the published digest against
OCI build labels, release evidence, signature/attestation subjects, Kubernetes
reference, and the exact digest-pinned runtime. Mainline publication evidence
is still required before the issue can close.

1. Certify dashboard and alert references only after metric families are stable
   and implemented. The operation metric catalog and AI model-risk operations
   contract now prove code-owned, bounded, not-certified telemetry/control
   posture, but dashboards and alerts remain uncertified.
2. Add live runtime source-readiness proof after Core source adapters and
   deployable worker runtime exist.
3. Add product-scope entitlement proof for Workbench and any broader Gateway
   route set after those surfaces are implemented; the first read-only Gateway
   advisor queue and candidate detail routes remain bounded caller-scope
   publication proof only.
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
