# API Surface

This page is the first-stop map for `lotus-idea` API readers.

Current posture: API support is internal foundation and operator diagnostics only. Bounded
Gateway publication exists for advisor queue/detail reads and Idea-owned review, feedback, and
conversion-intent controls. The Workbench BFF permits its configured authority fixture only in
local, development, and test and fails closed before Gateway otherwise. This is not end-user
identity-provider proof. Workbench live proof, authenticated-principal proof, data-product
certification, client-ready publication, and supported-feature promotion remain separately gated.

## Route Families

Eleven families covering the 63 operations this service serves. The machine-readable inventory is the [endpoint certification ledger](https://github.com/sgajbi/lotus-idea/blob/main/docs/operations/endpoint-certification-ledger.json), which `make endpoint-certification-gate` verifies against the generated OpenAPI.

Each family below states what its routes do today and, separately, what they explicitly do **not** grant. The boundary text is load-bearing: it is what keeps a certified internal foundation from being read as an externally supported capability.

| # | Family | Covers |
| ---: | --- | --- |
| 1 | [Health and metadata](#health-and-metadata) | Platform probes and release identity |
| 2 | [Caller-supplied opportunity signals](#caller-supplied-opportunity-signals) | All 12 caller-supplied signal evaluations |
| 3 | [Bounded source-backed signal evaluation](#bounded-source-backed-signal-evaluation) | All 12 source-backed signal evaluations |
| 4 | [Candidate persistence and lifecycle](#candidate-persistence-and-lifecycle) | Persistence, lifecycle, detail, evidence replay |
| 5 | [Privacy and records lifecycle](#privacy-and-records-lifecycle) | Legal hold, erasure, purge |
| 6 | [Review workflow](#review-workflow) | Advisor, PM, compliance and operator queues; review and feedback |
| 7 | [AI explanation governance](#ai-explanation-governance) | Explanation evaluation and readiness |
| 8 | [Conversion and report evidence](#conversion-and-report-evidence) | Conversion intent, outcomes, report evidence packs |
| 9 | [Downstream realization and recovery](#downstream-realization-and-recovery) | Submission, reconciliation, readiness |
| 10 | [Source ingestion and outbox operations](#source-ingestion-and-outbox-operations) | Ingestion and outbox operator actions |
| 11 | [Data mesh and implementation proof](#data-mesh-and-implementation-proof) | Readiness, trust telemetry, proof diagnostics |

### Health and metadata

**Routes**

- `GET /health`
- `GET /health/live`
- `GET /health/ready`
- `GET /metadata`
- `GET /version`

**Current use**

Platform smoke checks, readiness probes, service inventory. `/health/ready` publishes code-owned `200 ready` and source-safe `503` draining, restoring, durable-repository, and release-identity traffic-control modes.

`GET /version` publishes the release identity used by the deployment and container-provenance checks in [Validation and CI](Validation-and-CI).

**Boundary — not granted by these routes**

No business capability, source quality, portfolio supportability, Gateway/Workbench product proof, client publication, or supported-feature proof.

### Caller-supplied opportunity signals

**Routes**

- `POST /api/v1/idea-signals/*/evaluate`

**Current use**

Deterministic candidate posture over source-owned evidence supplied by authorized callers. Signal routes reject source refs whose `sourceSystem` or `productId` does not match the route's governed source contract before candidate creation. High-cash, low-income, bond-maturity, allocation-drift, underperformance, concentration-risk, high-volatility, drawdown-review, mandate-restriction, missing-risk-profile, missing-benchmark, and missing-suitability OpenAPI publish candidate-created, blocked, and not-eligible modes from application-backed response factories. Mandate-restriction, missing-risk-profile, and missing-suitability preserve Advise `AdvisoryPolicyEvaluationRecord:v1` authority; missing-benchmark preserves Core `BenchmarkAssignment:v1` authority.

**Boundary — not granted by these routes**

No upstream source fetch, official calculation ownership, suitability or policy approval, client risk-profile approval or creation, risk-capacity determination, Gateway/Workbench support, or supported-feature promotion.

### Bounded source-backed signal evaluation

**Routes**

- `POST /api/v1/idea-signals/high-cash/evaluate-from-source`
- `POST /api/v1/idea-signals/low-income/evaluate-from-source`
- `POST /api/v1/idea-signals/bond-maturity/evaluate-from-source`
- `POST /api/v1/idea-signals/missing-benchmark/evaluate-from-source`
- `POST /api/v1/idea-signals/concentration-risk/evaluate-from-source`
- `POST /api/v1/idea-signals/high-volatility/evaluate-from-source`
- `POST /api/v1/idea-signals/drawdown-review/evaluate-from-source`
- `POST /api/v1/idea-signals/underperformance/evaluate-from-source`
- `POST /api/v1/idea-signals/allocation-drift/evaluate-from-source`
- `POST /api/v1/idea-signals/missing-suitability/evaluate-from-source`
- `POST /api/v1/idea-signals/missing-risk-profile/evaluate-from-source`
- `POST /api/v1/idea-signals/mandate-restriction/evaluate-from-source`

**Current use**

Fetches Core-owned high-cash, low-income, bond-maturity, or benchmark-assignment evidence, Lotus Risk-owned concentration, volatility, or drawdown evidence, Lotus Performance-owned active-return and benchmark-context evidence, Lotus Manage-owned action-register posture, or Lotus Advise-owned policy-evaluation workflow, risk-profile diagnostic, or explicit mandate/restriction diagnostic posture through the configured source adapter after advisor role, `idea.signal.evaluate`, and required entitlement checks pass. It returns source-redacted candidate or blocked posture and closes the runtime client after each request. High-cash, low-income, bond-maturity, missing-benchmark, allocation-drift, underperformance, concentration-risk, high-volatility, drawdown-review, mandate-restriction, missing-risk-profile, and missing-suitability each publish complete candidate-created, blocked, and not-eligible named modes through their source-backed application paths. Missing-benchmark retains Core `BenchmarkAssignment:v1` identity without transferring benchmark assignment, methodology, or performance authority; allocation-drift candidate lineage retains supporting Manage, Performance, and Risk product identities without transferring source authority; underperformance retains Performance `ReturnsSeriesBundle:v1` identity without transferring returns or benchmark authority; concentration-risk retains Risk `ConcentrationRiskReport:v1` identity without transferring calculation or methodology authority; high-volatility retains Risk `RiskMetricsReport:v1` identity without transferring volatility, VaR, tracking-error, or methodology authority; drawdown-review retains Risk `DrawdownAnalyticsReport:v1` identity without transferring calculation, period-selection, or methodology authority; mandate-restriction, missing-risk-profile, and missing-suitability retain Advise `AdvisoryPolicyEvaluationRecord:v1` identity without transferring restriction, mandate, client risk-profile approval or creation, risk-capacity, suitability, policy, publication, rebalance, order, or execution authority.

**Boundary — not granted by these routes**

High-cash, low-income, bond-maturity, missing-benchmark, concentration-risk, high-volatility, drawdown-review, underperformance, allocation-drift, missing-suitability, missing-risk-profile, and mandate/restriction only; no persistence, source-worker certification, live source certification, income-needs assessment, funding advice, treasury instruction, maturity schedule authority, replacement product recommendation, reinvestment advice, planning suitability approval, benchmark assignment, benchmark methodology authority, performance calculation, concentration calculation, volatility/VaR/tracking-error calculation, drawdown calculation, drift calculation, mandate compliance approval, mandate-state change, restriction clearance, risk-profile approval or creation, risk-capacity determination, suitability approval, policy approval, proposal approval, sign-off approval, typed risk-profile or restriction data-product certification, risk methodology approval, trade recommendation, rebalance action, order creation, data-product certification, Gateway/Workbench support, client publication, or supported-feature promotion.

Missing-suitability caller and Advise-backed source evaluation publish candidate-created, blocked, and not-eligible response modes from their application paths. Advise retains suitability, policy, proposal, sign-off, and client-publication posture authority; Idea only detects evidence gaps and routes compliance review.

### Candidate persistence and lifecycle

**Routes**

- `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`
- `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions`
- `GET /api/v1/idea-candidates/{candidateId}`
- `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`

**Current use**

Internal persisted candidate, idempotency, lifecycle, detail, and evidence-replay foundations. High-cash persistence requires complete `accessScope`; the evaluation-only route remains available for explicitly diagnostic unscoped evaluation. OpenAPI distinguishes accepted, evidence-refreshed, material-version-created, recurrent-condition-reopened, replayed, duplicate-candidate, blocked, and not-eligible modes. Non-candidate outcomes return `persistence=null`; authoritative high-cash `not_eligible` evidence nevertheless expires a matching active candidate through lifecycle/audit/outbox, while blocked evidence remains non-mutating. Missing scope fails as a product-safe invalid request before candidate, idempotency, audit, or outbox mutation, and the repository enforces the same invariant for non-HTTP callers. Lifecycle transition input uses the caller-settable vocabulary and rejects `accepted` and `executed`; accepted and idempotent replay modes return the same exact persisted transition. Missing, ambiguous, or malformed persisted transition evidence fails closed instead of being synthesized from the request. Evidence replay publishes matched, hash-mismatch, stale-source, and expired modes from one DTO-validated factory. Durable PostgreSQL providers use repository-side candidate-detail projection instead of whole-store snapshot hydration for ordinary detail reads.

**Boundary — not granted by these routes**

`local`/`test` may use process-local writes and pseudonymous governed scope; production-like profiles require PostgreSQL and fail closed when absent. Economic access scope is not production authentication or identity-provider proof. Replay responses expose no raw source route or payload. No downstream authority, client-ready publication, or supported-feature promotion.

### Privacy and records lifecycle

**Routes**

- `POST /api/v1/data-lifecycle/candidates/{candidateId}/actions`

**Current use**

Authorized preview/apply workflow for legal hold, hold release, erasure, and purge with exact tenant scope, idempotency, governed authority, dual approval, immutable audit, and PostgreSQL lifecycle fencing.

**Boundary — not granted by these routes**

Internal and not certified. Lotus Idea enforces approved local decisions but does not own legal/privacy approval, Report/Archive policy, AI-provider deletion, or supported-feature promotion.

### Review workflow

**Routes**

- `GET /api/v1/review-queues/advisor`
- `GET /api/v1/review-queues/portfolio-manager`
- `GET /api/v1/review-queues/compliance`
- `GET /api/v1/review-queues/operator/exceptions`
- `GET /api/v1/review-queues/advisor/readiness`
- `POST /api/v1/idea-candidates/{candidateId}/review-actions`
- `POST /api/v1/idea-candidates/{candidateId}/feedback`
- `POST /api/v1/idea-candidates/{candidateId}/presentation-receipts`

**Current use**

Audience-bound business queues, candidate-safe operator exception posture, readiness, review/feedback capture, and immutable visible-render evidence. Queue reads use candidate-created-at as-of visibility and audience-bound opaque continuation snapshots. The advisor queue publishes application-backed `itemsAvailable` and `noItemsAvailable` 200 examples through its real projection and response DTO. Each queue item includes the current Idea-owned candidate material/evidence versions needed to bind a visible-render receipt without consumer reconstruction. Queue `policyVersion` is distinct from candidate `scorePolicyVersion`; unknown score policies fail closed. Review and feedback authorize persisted candidate scope against trusted caller entitlements. Feedback uses `idea-feedback-taxonomy-v1`: `useful/relevant` or `not_useful` with a bounded reason. Presentation receipts use a stable `Idempotency-Key` and are fenced by tenant, candidate material/evidence versions, UTC chronology, positive global rank, independently bounded visible-set count, and queue digest. Queue retrieval is never treated as presentation. Gateway and Workbench must pass and produce the receipt contract without rewriting it; their consumer certification remains open. See [Feedback Evaluation](Feedback-Evaluation) and [Opportunity Effectiveness](Opportunity-Effectiveness).

**Boundary — not granted by these routes**

PM/compliance routes do not grant Manage or compliance authority. Presentation receipt storage does not certify shown metrics until Gateway and Workbench consumer proof passes. These paths are not authenticated-principal proof, full Workbench runtime proof, data-product certification, or supported review-product promotion.

### AI explanation governance

**Routes**

- `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`
- `GET /api/v1/ai-explanations/readiness`

**Current use**

Deterministic fallback and model-risk diagnostics. Local/test may use a visibly unattested fixture; production-like profiles accept workflow output only as a complete producer bundle with verified Lotus AI run attestation. Accepted narrative is server-rendered from verified claims under `lotus-idea.ai-claim-grounding-policy.v1`, with source-safe product/version, as-of, freshness, and quality references. Blocked output exposes no grounding and uses deterministic server-owned explanation text; submitted provider narrative is digest-bound but not returned or persisted across accepted, blocked, replay, or conflict paths. Readiness reports dashboard and alert-rule source-contract validity separately from their runtime blockers.

**Boundary — not granted by these routes**

No provider call by Idea, autonomous advice, dashboard provisioning, alert evaluation/delivery, live-provider certification, or client-ready explanation claim.

### Conversion and report evidence

**Routes**

- `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`
- `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`
- `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`

**Current use**

Internal review-gated intent, source-versioned append-only outcome history/current posture, and report evidence-pack request recording. Conversion-intent recording requires the conversion capability, `Idempotency-Key`, and complete trusted tenant/book/portfolio/client caller entitlement scope covering the persisted candidate; missing or mismatched scope fails closed as `403 permission_denied` before intent persistence. All three mutations publish named accepted and replayed OpenAPI modes that return the same exact persisted action. A successful persistence decision with zero or multiple identity-bound matches fails closed as `503 service_recovery_degraded`; no action is reconstructed from the request. Report evidence-pack examples preserve no client-publication, rendered-output, or archive-record authority. Outcome resource identity is independent of the retry key; equivalent cross-key events replay, changed identity/version/progression returns `conversion_outcome_conflict`, and candidate detail separates full history from policy-valid current posture.

**Boundary — not granted by these routes**

No suitability approval, rebalance/execution authority, report rendering, archive record, client publication, or supported-feature promotion; quarantined histories do not count as ready.

### Downstream realization and recovery

**Routes**

- `GET /api/v1/downstream-realization/readiness`
- `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions`
- `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions`
- `GET /api/v1/downstream-submissions/reconciliation`
- `POST /api/v1/downstream-submissions/reconciliation/{supportReference}`

**Current use**

Planned-contract readiness plus source-safe claim-before-call submission. Readiness includes the local downstream submission denominator and unresolved reconciliation workload. Both submission routes publish accepted, rejected, accepted-replayed, and rejected-replayed `200` modes, with `reconciliation_required` separately published as `202`; exact retries never make another adapter call. Timeouts, transport ambiguity, 5xx responses, malformed responses, lease loss, and local finalization failure become durable reconciliation posture. Operator routes expose opaque inspection and audited accepted/rejected/quarantined resolution.

**Boundary — not granted by these routes**

No authoritative conversion outcome, automatic uncertain-call retry, route-existence proof by default, suitability, execution, materialization, client publication, or support promotion.

### Source ingestion and outbox operations

**Routes**

- `GET /api/v1/source-ingestion/readiness`
- `POST /api/v1/source-ingestion/run-once`
- `GET /api/v1/outbox-delivery/readiness`
- `POST /api/v1/outbox-delivery/run-once`
- `GET /api/v1/outbox-delivery/dead-letters`
- `POST /api/v1/outbox-delivery/dead-letters/{supportReference}/redrive`

**Current use**

Operator diagnostics and bounded actions over configured internal foundations. Dead-letter inspection exposes opaque support references and bounded failure posture only. Re-drive requires a dedicated capability, trusted production provenance, idempotency key, reason, change reference, eligibility checks, append-only audit evidence, and a fenced lease. Poison or unsupported events remain quarantined.

**Boundary — not granted by these routes**

No long-running scheduler certification, live broker certification, downstream delivery proof, platform mesh proof, or supported ingestion/event product.

### Data mesh and implementation proof

**Routes**

- `GET /api/v1/data-mesh/readiness`
- `GET /api/v1/data-mesh/trust-telemetry/runtime-preview`
- `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot`
- `GET /api/v1/implementation-proof/readiness`

**Current use**

Source-safe readiness, telemetry, local downstream submission posture, and aggregate proof-blocker diagnostics.

**Boundary — not granted by these routes**

Diagnostics only; downstream posture is local Idea state, not downstream acceptance or materialization proof. No mesh certification, Gateway/Workbench discovery, live implementation proof, or supported-feature promotion.

Core-backed source routes require exactly one tenant from trusted caller
context. They reject missing, ambiguous, self-asserted production, and
request-body tenant overrides before source I/O. The resolved tenant is carried
through the application/port/adapter path where Core publishes tenant-aware
input and is retained in candidate access scope and identity. Responses and
operation telemetry never expose raw tenant IDs.

## Request And Error Model

### Advisor Queue Paging

1. Start at `offset=0` with a timezone-aware `evaluatedAtUtc`.
2. Read `page.snapshotToken` from the response.
3. Return the same evaluation time, scope filters, and token with every later
   offset.
4. Restart at offset zero after `409 review_queue_snapshot_conflict`.

Candidates created after the evaluation instant are not visible and do not
invalidate that traversal. Backdated inserts and changes to visible lifecycle,
review or persisted snooze, suppression, score, or evidence state invalidate it. The token is
opaque and must not be decoded, persisted as a business identifier, or logged
with portfolio/client context.

The token also binds the queue ranking-policy version and its accepted
candidate score-policy set. A candidate with an absent or unknown score policy
is excluded as `unrankable_score_policy`; it is never compared on the assumption
that all numeric scores share one scale.

An accepted adviser `snooze` action is authoritative from persisted review
history. The candidate is absent strictly before `snoozedUntilUtc` and becomes
eligible at that exact instant when other queue rules pass. Evidence refresh
preserves the snooze; a new material version or recurrent reopen starts a new
review cycle rather than inheriting stale queue suppression.

| Control | Current expectation |
| --- | --- |
| Authorization | API routes fail closed through platform caller-context roles and `idea.*` capabilities. `local` and `test` may simulate `X-Caller-*` headers; production-like profiles require `X-Lotus-Trusted-Caller-Context` to match `LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN` before those headers can authorize a route. This is trusted-ingress provenance only, not full identity-provider or Workbench entitlement proof. |
| Runtime composition | API routes use `app.api.runtime_dependencies` as the only facade for repository providers, source-ingestion runtime, outbox publisher wiring, proof-artifact configuration, and downstream realization clients. Direct route imports from `app.runtime` are blocked by `make architecture-boundary-gate`. |
| Route metadata | API routes use the shared `app.api.route_metadata.RouteMetadata` contract for route-registration metadata. Local route metadata clones are blocked by `make api-route-metadata-gate`. |
| Idempotency | Mutating workflow routes require `Idempotency-Key`, validate blank keys through shared `app.api.idempotency`, and return replay or conflict posture instead of duplicating state. `make api-idempotency-boundary-gate` blocks route-local validator clones and optional/defaulted `Idempotency-Key` OpenAPI headers on certified idempotent mutations. |
| Event lineage | Outbox-producing mutation routes expose optional `X-Causation-Id` and map it with middleware correlation/trace through `app.api.event_lineage`. Correlation and trace are required and distinct in durable events; causation is present only for a parent event/workflow. Replays retain original event lineage even when the retry trace changes. |
| Conversion outcome lifecycle | `conversionOutcomeId` and `sourceEventVersion` govern source identity and ordering independently of transport idempotency. OpenAPI publishes named `idempotency_conflict` and `conversion_outcome_conflict` examples; current posture exists only for a valid history. |
| Privacy lifecycle | `privacy_officer` or `records_manager` plus `idea.data-lifecycle.manage`, exact trusted tenant scope, governed authority, preview, and distinct approval for release/erase/purge. Erased and purged resources are suppressed from direct reads and active trust-telemetry product counts. |
| DTO alias handling | API DTOs that need camel-case aliases use `app.api.base_model.CamelModel`. `make api-camel-model-boundary-gate` blocks route-local `CamelModel` or `ConfigDict(populate_by_name=True)` clones. |
| Signal DTO ownership | Shared signal-family DTOs for source refs, review access scope, source-ref responses, and candidate summaries live in `app.api.signal_models`. `make api-signal-model-boundary-gate` blocks route-to-route imports from `app.api.idea_signals`. |
| Candidate identity | `idea-opportunity-identity-v3` derives tenant-scoped economic business identity independently from source content hashes, exact observation date, and transport keys. Equivalent evidence/date refreshes retain the business/material version while incrementing evidence version; material change and recurrent conditions create explicit governed transitions. A one-way v2 backfill preserves existing lifecycle posture, evaluation DTOs reject `duplicateOfCandidateId`, and persistence owns duplicate reconciliation. |
| Signal caller context | Caller-supplied signal routes bind standard identity, capability, and entitlement-scope headers through `app.api.caller_headers.CallerContextHeaders`. Requests with `accessScope` must pass that scope into `signal_permission_problem_or_none(...)`; out-of-scope requests fail closed with product-safe 403 behavior before domain evaluation. `make signal-api-contract-gate` blocks route-local `X-Caller-*` header clones, scope-unaware permission checks, duplicate signal permission policy, weak 400/403 examples, and operation-event drift. |
| Caller-context provenance | `make caller-context-contract-gate` verifies that shared and route-local caller-context parsing binds `X-Lotus-Trusted-Caller-Context` and forwards `trusted_caller_context` so production-like profiles cannot authorize self-asserted `X-Caller-*` headers. It scans nested route packages under `src/app/api/**`, not only top-level API modules, so protected review-queue, outbox, data-lifecycle, and future route families stay inside the same role-plus-capability and trusted-provenance contract. The dependency preserves exact `400 invalid_request` and `403 permission_denied` problems through the global handler, including safe detail, RFC 7807 runtime media, sanitized correlation, bounded diagnostic category, and generated examples on every protected operation. |
| Temporal validation | API timestamp-awareness and UTC checks live in `app.api.temporal_validation`. Signal evidence additionally uses `idea-source-temporal-v2`: every included ref must exactly match request `asOfDate`, must not be generated after `evaluatedAtUtc`, and must pass freshness policy. Caller, adapter, and ingestion paths return bounded blocked posture without persistence on mismatch; changed source hashes preserve business candidate identity while versioning evidence packets and lineage. `make api-temporal-validation-boundary-gate` and `make source-temporal-contract-gate` prevent boundary drift. |
| Source authority | Signal routes consume source-owned evidence, carry source refs, and validate caller-supplied refs against route-owned source contracts before evaluation; `lotus-idea` does not recompute official performance, risk, accounting, suitability, or report facts. |
| Error responses | Implemented business and operator endpoints, including `implemented_not_certified` operations, must expose product-safe `ProblemDetails` examples under both `application/json` and `application/problem+json`. Workflow/operator routes and app-entrypoint exception handlers use shared `app.api.problem_details` metadata and runtime response helpers for concrete 400/403/404/409/503 problems. Caller-context dependency failures return `application/problem+json`, preserve stable `invalid_request` and `permission_denied` contracts, and emit only source-safe error categories; unrelated framework exceptions retain `request_rejected`. The generated OpenAPI customizer injects caller-boundary 400/403 examples for every protected operation while preserving route-specific examples. `make api-problem-details-boundary-gate`, `make openapi-problem-details-example-gate`, and `make caller-context-contract-gate` block layer drift. Caller-supplied signal routes use `app.api.signal_api_support` for their stricter route-family contract. |
| Sensitive data | Responses and diagnostics must not expose raw source payloads, raw idempotency keys, portfolio identifiers in aggregate diagnostics, prompt/provider payloads, or broker payloads. |

## Evidence Paths

| Evidence | Use |
| --- | --- |
| [API certification guide](https://github.com/sgajbi/lotus-idea/blob/main/docs/operations/api-certification.md) | Human-readable endpoint inventory, intended use, boundaries, and test evidence. |
| [Endpoint certification ledger](https://github.com/sgajbi/lotus-idea/blob/main/docs/operations/endpoint-certification-ledger.json) | Machine-readable source for endpoint certification and evidence references. |
| [OpenAPI quality gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/openapi_quality_gate.py) | Contract documentation and example validation. |
| [ProblemDetails example gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/openapi_problem_details_example_gate.py) | Generated OpenAPI check that every public `ProblemDetails` response has product-safe examples for both JSON and RFC-7807 media types. |
| [ProblemDetails boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_problem_details_boundary_gate.py) | API boundary check that route modules and the app entrypoint import ProblemDetails runtime helpers through `app.api.problem_details`, not directly from `app.errors`. |
| [Idempotency boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_idempotency_boundary_gate.py) | API boundary check that mutating workflow routes use shared `app.api.idempotency` validation and publish required, non-defaulted `Idempotency-Key` OpenAPI headers instead of route-local validator clones or understated mutation contracts. |
| [Review identity contract gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/review_identity_contract_gate.py) | Guards business-resource identity precheck, atomic PostgreSQL claim ordering, typed conflict behavior, named OpenAPI examples, and architecture truth for reviews and feedback. |
| [Feedback evaluation contract gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/feedback_evaluation_contract_gate.py) | Guards canonical taxonomy combinations, migration and outbox version, bounded offline projection, privacy exclusions, no production mutation authority, and supported-feature non-promotion. |
| [Conversion outcome contract gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/conversion_outcome_contract_gate.py) | Guards source identity/version lifecycle, provider parity, atomic PostgreSQL claim, legacy quarantine, distinct conflict examples, and architecture truth for conversion outcomes. |
| [CamelModel boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_camel_model_boundary_gate.py) | API boundary check that route modules use shared `app.api.base_model.CamelModel` instead of local camel-case DTO base-model clones. |
| [Signal model boundary gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/api_signal_model_boundary_gate.py) | API boundary check that shared signal-family DTOs are imported from `app.api.signal_models`, not from concrete route modules. |
| [Caller context contract gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/caller_context_contract_gate.py) | API security contract check that privileged caller-context headers stay bound to trusted-ingress provenance in production-like profiles across top-level and nested API route modules. |
| [Endpoint certification gate](https://github.com/sgajbi/lotus-idea/blob/main/scripts/endpoint_certification_gate.py) | Synchronizes OpenAPI operations with implementation-quality evidence and supported-boundary language. `implemented_not_certified` rows retain the full security, observability, OpenAPI, and test contract while declaring external blockers and no-promotion success posture. |
| [Data Lifecycle Operations](Data-Lifecycle-Operations) | Operator workflow, authority boundaries, failure response, aggregate telemetry, and remaining certification blockers. |
| [Operations Runbook](Operations-Runbook) | Operator diagnostics, readiness semantics, proof-artifact interpretation, and first checks. |
| [Validation and CI](Validation-and-CI) | Repo-native gates that block weak API, OpenAPI, documentation, and supported-feature claims. |

## Copy-Paste Checks

```powershell
make openapi-gate
make endpoint-certification-gate
make api-route-metadata-gate
make api-problem-details-boundary-gate
make api-idempotency-boundary-gate
make api-camel-model-boundary-gate
make api-signal-model-boundary-gate
make api-temporal-validation-boundary-gate
make openapi-problem-details-example-gate
make caller-context-contract-gate
make signal-api-contract-gate
make documentation-contract-gate
```

Use `make check` before PR when an API route, schema, OpenAPI description,
endpoint ledger row, or wiki API claim changes.

## Do Not Infer

Certified API foundation does not mean the product is externally supported.
Do not infer client publication, suitability approval, rebalance authority,
official risk/performance methodology, report rendering, archive authority,
data-mesh certification, live provider execution, or Workbench support unless
the owning repository evidence, `supported-features`, docs/wiki truth, CI, and
mainline validation all agree.
