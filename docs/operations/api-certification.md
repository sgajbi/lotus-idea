# API Certification Baseline

Every endpoint added after scaffold creation must include:

1. domain-correct tag grouping,
2. clear what/when/how description,
3. complete request and response examples,
4. product-safe error examples,
5. attribute descriptions, types, and examples,
6. focused unit or integration tests for success and failure behavior,
7. OpenAPI gate coverage before merge.

API route modules should use the shared `app.api.problem_details` helpers for
workflow/operator `ProblemDetails` response metadata unless a route-family
support module owns a stricter contract. This keeps 400/403/404/409 examples
concrete, product-safe, and consistent without duplicating RFC-7807 shapes in
each route; 503 operator/dependency failures should use the same helper family
so unavailable-readiness states are also example-backed. Generated OpenAPI must
publish those examples under both `application/json` and
`application/problem+json`; `make openapi-problem-details-example-gate` blocks
public ProblemDetails responses that lack either media-type example.
Caller-supplied signal routes remain governed by `app.api.signal_api_support`,
which owns their permission, source-authority, operation-event, and 400/403
OpenAPI metadata as one contract.

All signal operations also share `idea-source-temporal-v1` at the domain
boundary. Every included source ref must match request `asOfDate`, must not be
generated after `evaluatedAtUtc`, and must pass freshness policy before a ready
candidate is returned. This applies to caller-supplied, source-adapter, and
source-ingestion paths. Misalignment returns bounded `blocked` posture with
`source_date_mismatch` or `source_generated_after_evaluation` plus
`source_temporal_mismatch`; it does not persist a candidate. A source correction
with a new content hash is retained in lineage and produces new candidate
identity. No signal family currently permits an inferred effective-date window.
The shared caller-context dependency preserves the same stable runtime
vocabulary: malformed entitlement headers are `400 invalid_request`, and
missing trusted provenance is `403 permission_denied`; raw header values never
cross the ProblemDetails boundary. Runtime responses use
`application/problem+json`, retain the sanitized `X-Correlation-Id`, and emit
only bounded `caller_context_invalid_request` or
`caller_context_permission_denied` diagnostic categories.

Protected business/operator endpoints publish caller-context requirements in
generated OpenAPI through the `LotusCallerContext` security scheme and the
`x-lotus-caller-context` operation extension. The extension records required
`idea.*` capabilities, required or alternative roles where policy uses them,
entitlement-scope behavior, product-safe 403 posture, and production-like
trusted-ingress provenance for privileged `X-Caller-*` headers. The generated
contract injects product-safe caller-boundary 400/403 examples under both
`application/json` and `application/problem+json` for every protected
operation, while preserving route-specific examples. `make
endpoint-certification-gate` fails if a certified endpoint names an `idea.*`
capability in the ledger but generated OpenAPI omits the matching caller-context
publication or leaves key caller-context headers undescribed. `make
caller-context-contract-gate` binds the exception, handler, route registry,
OpenAPI, runtime media, and representative cross-route tests into one blocking
contract.

Route metadata dictionaries should use `app.api.route_metadata.RouteMetadata`.
`make api-route-metadata-gate` blocks local `RouteMetadata` and
`SignalRouteMetadata` `TypedDict` clones, keeping route-registration metadata
on one reviewable API contract while preserving route-family support modules.

Rows below that require `Idempotency-Key` are enforced by
`make api-idempotency-boundary-gate`: generated OpenAPI must mark the header as
required with no default, and route code must use the shared idempotency
boundary instead of route-local validator clones.

Outbox-producing mutation operations expose optional `X-Causation-Id` in
OpenAPI. Correlation and trace come from the shared request middleware and are
required in the durable event; causation is accepted only for a distinct
parent event or workflow. The shared `app.api.event_lineage` mapper and
`make outbox-event-contract-gate` prevent route-local interpretation and
trace/causation substitution. Lineage headers do not alter business
idempotency: an equivalent replay retains the original durable event context.

The machine-readable source for endpoint certification tracking is:

- docs/operations/endpoint-certification-ledger.json

Run `make endpoint-certification-gate` before promoting any endpoint as supported. The gate now
blocks weak certification by requiring:

1. every public OpenAPI operation to have exactly one ledger entry,
2. required evidence fields for purpose, usage, non-usage boundaries, examples, tests, and OpenAPI,
3. valid JSON request and response examples when an example is JSON-shaped,
4. real `tests/path.py::test_name` references,
5. `baseline_certified` status only for health/metadata baseline endpoints,
6. implemented business/operator endpoints, whether `certified` or
   `implemented_not_certified`, to name an `idea.*` capability,
7. implemented endpoints to preserve Gateway, Workbench, and
   supported-feature-promotion boundaries,
8. product-safe 403 behavior and `scripts/openapi_quality_gate.py` evidence,
9. bounded operation-event test evidence for every implemented business/operator endpoint,
10. exact bounded read-only `lotus-gateway` route citation before a ledger entry can claim Gateway
    publication, while still preserving Workbench, data-product, client-ready publication, and
    supported-feature boundaries,
11. at least one non-operation-event integration API behavior test and at least one negative or
    degraded-path test reference for every implemented business/operator endpoint, so endpoint
    certification cannot be based only on schema examples, unit tests, or telemetry assertions,
12. generated OpenAPI caller-context security publication for every implemented endpoint that names
    an `idea.*` capability, including matching required capability values, trusted caller-context
    provenance wording, and descriptions for `X-Caller-Capabilities` and
    `X-Lotus-Trusted-Caller-Context`,
13. machine-readable `certification_blockers`, ledger response examples, and generated OpenAPI
    success examples that preserve `not_certified` plus `supportedFeaturePromoted=false` for every
    `implemented_not_certified` operation,
14. the AI explanation readiness ledger and generated OpenAPI success examples to exactly match
    the complete code-owned default response produced by the application snapshot and API
    serializer, including every control field and certification blocker,
15. every materially different executable success family to have one complete named example whose
    serialized value exactly matches the code-owned response factory in both the endpoint ledger
    and generated OpenAPI.
16. accepted and idempotent replay modes for candidate lifecycle, review, feedback, conversion,
    and report evidence-pack mutations to remain distinct named HTTP 200 examples, with required
    integration evidence and false downstream/client-publication/supported-feature authority
    preserved exactly,
17. candidate evidence replay to publish matched, hash-mismatch, stale-source, and expired HTTP 200
    postures from one DTO-validated factory; none may be omitted from the ledger or generated
    OpenAPI merely because it is degraded rather than successful in business terms.
18. high-cash caller and source-backed evaluation to publish candidate-created, blocked,
    suppressed, and not-eligible HTTP 200 modes, and high-cash evaluate-and-persist to publish
    accepted, replayed, duplicate-candidate, blocked, suppressed, and not-eligible modes from
    one capability-owned deterministic factory. Non-candidate persistence modes must retain an
    explicit null persistence summary.
19. low-income caller and Core-backed evaluation to publish candidate-created, blocked,
    suppressed, and not-eligible HTTP 200 modes from application-backed, DTO-serialized
    factories. Candidate examples must preserve both Core cash-movement and cashflow-projection
    source products while redacting source routes and content hashes.
20. bond-maturity caller and Core-backed evaluation to publish candidate-created, blocked,
    suppressed, and not-eligible HTTP 200 modes from application-backed, DTO-serialized
    factories. Candidate examples must preserve Core holdings and maturity-summary lineage while
    redacting source routes and content hashes.
21. allocation-drift caller and Manage-backed evaluation to publish candidate-created, blocked,
    suppressed, and not-eligible HTTP 200 modes from application-backed, DTO-serialized
    factories. Source-backed candidate examples must preserve Manage action-register,
    Performance mandate-health, and Risk mandate-health lineage while redacting source routes
    and content hashes. Named-success validators must register in
    `scripts/endpoint_named_success_contracts.py` so the central certification gate remains a
    stable orchestrator instead of accumulating capability imports and calls.
22. underperformance caller and Performance-backed evaluation to publish candidate-created,
    blocked, suppressed, and not-eligible HTTP 200 modes from application-backed,
    DTO-serialized factories. Candidate examples must preserve the governed Performance
    `ReturnsSeriesBundle:v1` identity while redacting source routes and content hashes. Idea owns
    opportunity detection and advisor-review posture, not returns calculation, benchmark
    assignment, benchmark methodology, or investment action authority.

Certified readiness examples must not be maintained as parallel hand-written
objects when the endpoint has a deterministic no-I/O response factory. The
factory remains the source for the runtime response and OpenAPI example; the
ledger is compared against the complete serialized structure. Dynamic
repository posture may vary at runtime only through explicitly modelled inputs
such as durable-storage availability.

For multi-mode endpoints, schema-valid excerpts are not certification evidence.
The code-owned factory must cover every executable response family, including
fallback and blocked outcomes, and each example must retain explicit nulls,
control fields, grounding posture, retention posture, provenance, and authority
boundaries. When the framework drops explicit nulls while generating OpenAPI,
the application may apply a bounded post-generation example injection from the
same factory. Public enum states without an executable constructor, route
outcome, and behavioral test are stale contract surface and must be removed.

`implemented_not_certified` means the public operation exists and must meet the
same implementation-quality, security, observability, OpenAPI, and test
standards as a certified operation, while named external production evidence
still blocks certification. `planned` and `not_applicable` remain inventory
vocabulary only; they do not satisfy implemented-operation requirements and
must not be used to describe an available public route.

## Certified Foundation Endpoints

The current certified foundation inventory is:

Caller-supplied signal endpoints reject source refs whose `sourceSystem` or
`productId` does not match the route's governed source contract before domain
evaluation or candidate creation. These rejections return product-safe
`400 invalid_request` Problem Details and emit `signal_evaluation`
`invalid_request` telemetry using the expected source authority rather than the
caller-supplied mismatched authority.
Source-fetching signal endpoints are separately bounded: they call only the
configured source adapter for the declared source authority, enforce caller
portfolio entitlement before runtime construction, return product-safe 503
posture when source runtime configuration is absent, and do not persist
candidates or certify live source support.

| Endpoint | Foundation Scope | Required Capability | Current Boundary |
| --- | --- | --- | --- |
| `POST /api/v1/idea-signals/high-cash/evaluate` | High-cash deterministic evaluation over caller-supplied, source-owned Core evidence. Named OpenAPI success modes cover candidate-created, blocked, suppressed, and not-eligible posture. | advisor role and `idea.signal.evaluate` capability | No live source ingestion, durable state, Gateway, Workbench, mesh certification, or supported-feature promotion. |
| `POST /api/v1/idea-signals/high-cash/evaluate-from-source` | High-cash deterministic evaluation over Core evidence fetched through the configured source adapter after caller portfolio entitlement passes. The same four named success modes are built through the source-backed application path. | advisor role, `idea.signal.evaluate` capability, portfolio entitlement scope, and exactly one tenant from trusted caller context; body tenant overrides are forbidden | No durable state, source-worker certification, live source certification, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/low-income/evaluate` | Low-income / liquidity-shortfall deterministic evaluation over caller-supplied, source-owned Core cashflow projection and cash movement evidence. Named OpenAPI modes cover candidate-created, blocked, suppressed, and not-eligible posture. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, client income-needs assessment, funding advice, treasury instruction, planning suitability approval, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/low-income/evaluate-from-source` | Low-income / liquidity-shortfall deterministic evaluation over Core cash movement and cashflow projection evidence fetched through the configured source adapter after caller portfolio entitlement passes. The same four named modes are built through the Core-backed application path. | advisor role, `idea.signal.evaluate` capability, portfolio entitlement scope, and exactly one tenant from trusted caller context; body tenant overrides are forbidden | No durable state, source-worker certification, live source certification, client income-needs assessment, funding advice, treasury instruction, planning suitability approval, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/bond-maturity/evaluate` | Bond-maturity / reinvestment review deterministic evaluation over caller-supplied, source-owned Core `PortfolioMaturitySummary:v1` evidence with upstream `HoldingsAsOf:v1` lineage. Named OpenAPI modes cover candidate-created, blocked, suppressed, and not-eligible posture. Canonical live Core source proof remains blocked until a valid source-safe runtime artifact is captured and merged. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, raw-position maturity schedule derivation, replacement product recommendation, reinvestment advice, maturity schedule authority, planning suitability approval, orders/execution, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/bond-maturity/evaluate-from-source` | Bond-maturity / reinvestment review deterministic evaluation over Core `PortfolioMaturitySummary:v1` and `HoldingsAsOf:v1` evidence fetched through the configured source adapter after caller portfolio entitlement passes. The same four named modes are built through the Core-backed application path. | advisor role, `idea.signal.evaluate` capability, portfolio entitlement scope, and exactly one tenant from trusted caller context; body tenant overrides are forbidden | No durable state, source-worker certification, live source certification, raw-position maturity schedule derivation, replacement product recommendation, reinvestment advice, maturity schedule authority, planning suitability approval, orders/execution, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/concentration-risk/evaluate` | Concentration-risk review deterministic evaluation over caller-supplied, source-owned Lotus Risk concentration evidence. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, concentration calculation, risk methodology approval, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/concentration-risk/evaluate-from-source` | Concentration-risk review deterministic evaluation over Lotus Risk `ConcentrationRiskReport:v1` evidence fetched through the configured source adapter after caller portfolio entitlement passes. | advisor role, `idea.signal.evaluate` capability, and portfolio entitlement scope for the requested portfolio | No durable state, source-worker certification, live source certification, concentration calculation, risk methodology approval, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/high-volatility/evaluate` | High-volatility deterministic evaluation over caller-supplied, source-owned Lotus Risk metrics evidence. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, volatility, VaR, or tracking-error calculation, risk methodology approval, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/high-volatility/evaluate-from-source` | High-volatility deterministic evaluation over Lotus Risk `RiskMetricsReport:v1` volatility evidence fetched through the configured source adapter after caller portfolio entitlement passes. | advisor role, `idea.signal.evaluate` capability, and portfolio entitlement scope for the requested portfolio | No durable state, source-worker certification, live source certification, volatility, VaR, or tracking-error calculation, risk methodology approval, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/drawdown-review/evaluate` | Drawdown-review deterministic evaluation over caller-supplied, source-owned Lotus Risk drawdown analytics evidence. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, drawdown calculation, risk methodology approval, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/drawdown-review/evaluate-from-source` | Drawdown-review deterministic evaluation over Lotus Risk `DrawdownAnalyticsReport:v1` evidence fetched through the configured source adapter after caller portfolio entitlement passes. | advisor role, `idea.signal.evaluate` capability, and portfolio entitlement scope for the requested portfolio | No durable state, source-worker certification, live source certification, drawdown calculation, risk methodology approval, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/underperformance/evaluate` | Underperformance review deterministic evaluation over caller-supplied, source-owned Lotus Performance active-return and benchmark-context evidence. OpenAPI publishes candidate-created, blocked, suppressed, and not-eligible modes from the application path. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, returns calculation, benchmark assignment, benchmark methodology authority, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/underperformance/evaluate-from-source` | Underperformance review deterministic evaluation over Lotus Performance `ReturnsSeriesBundle:v1` evidence fetched through the configured source adapter after caller portfolio entitlement passes. OpenAPI publishes candidate-created, blocked, suppressed, and not-eligible modes through the source-backed application path. | advisor role, `idea.signal.evaluate` capability, and portfolio entitlement scope for the requested portfolio | No durable state, source-worker certification, live source certification, returns calculation, benchmark assignment, benchmark methodology authority, trade recommendation, rebalance action, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/allocation-drift/evaluate` | Allocation-drift / mandate-review deterministic evaluation over caller-supplied, source-owned Lotus Manage action-register and mandate-health source-ref posture. OpenAPI publishes candidate-created, blocked, suppressed, and not-eligible modes from the application path. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, drift calculation, mandate compliance approval, rebalance action, order creation, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/allocation-drift/evaluate-from-source` | Allocation-drift / mandate-review deterministic evaluation over Lotus Manage `PortfolioActionRegister:v1` posture fetched through the configured source adapter after caller portfolio entitlement passes. OpenAPI publishes candidate-created, blocked, suppressed, and not-eligible modes; candidate lineage retains the supporting Manage, Performance, and Risk products. | advisor role, `idea.signal.evaluate` capability, and portfolio entitlement scope for the requested portfolio | No durable state, source-worker certification, live source certification, drift calculation, mandate compliance approval, rebalance action, order creation, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/mandate-restriction/evaluate` | Mandate/restriction deterministic evaluation over caller-supplied, source-owned Core, Manage, or Advise posture evidence. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, restriction clearance, mandate change, suitability approval, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/mandate-restriction/evaluate-from-source` | Mandate/restriction deterministic evaluation over explicit Lotus Advise restriction diagnostic posture fetched through the configured source adapter after optional caller access-scope entitlement passes. | advisor role, `idea.signal.evaluate` capability, and entitlement scope when request accessScope is supplied | No durable state, source-worker certification, live source certification, restriction clearance, mandate-state change, suitability approval, policy/proposal approval, rebalance/order authority, Gateway, Workbench, mesh certification, client publication, data-product certification, or supported-feature promotion. |
| `POST /api/v1/idea-signals/missing-benchmark/evaluate` | Missing benchmark deterministic evaluation over caller-supplied, source-owned Core benchmark-assignment evidence. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, benchmark assignment, benchmark methodology authority, performance calculation, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/missing-benchmark/evaluate-from-source` | Missing benchmark deterministic evaluation over Core benchmark-assignment evidence fetched through the configured source adapter after caller portfolio entitlement passes. | advisor role, `idea.signal.evaluate` capability, portfolio entitlement scope, and exactly one tenant from trusted caller context; body tenant overrides are forbidden | No durable state, source-worker certification, live source certification, benchmark assignment, benchmark methodology authority, performance calculation, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/missing-risk-profile/evaluate` | Missing risk-profile deterministic evaluation over caller-supplied, source-owned Advise posture evidence. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, risk-profile approval, suitability approval, typed risk-profile data-product certification, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/missing-risk-profile/evaluate-from-source` | Missing risk-profile deterministic evaluation over Lotus Advise policy-evaluation diagnostic posture fetched through the configured source adapter after optional caller access-scope entitlement passes. | advisor role, `idea.signal.evaluate` capability, and entitlement scope when request accessScope is supplied | No durable state, source-worker certification, live source certification, risk-profile approval, suitability approval, policy/proposal approval, typed risk-profile data-product certification, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/missing-suitability/evaluate` | Missing suitability-context deterministic evaluation over caller-supplied, source-owned Advise policy-evaluation evidence. | advisor role and `idea.signal.evaluate` capability | No upstream source fetch, suitability approval, policy/proposal/sign-off approval, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/missing-suitability/evaluate-from-source` | Missing suitability-context deterministic evaluation over Lotus Advise policy-evaluation workflow posture fetched through the configured source adapter after optional caller access-scope entitlement passes. | advisor role, `idea.signal.evaluate` capability, and entitlement scope when request accessScope is supplied | No durable state, source-worker certification, live source certification, suitability approval, policy/proposal/sign-off approval, Gateway, Workbench, mesh certification, client publication, or supported-feature promotion. |
| `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` | High-cash evaluation plus internal candidate persistence, idempotency, replay, and audit posture through the active repository provider. Named success modes distinguish accepted, replayed, duplicate-candidate, blocked, suppressed, and not-eligible behavior; non-candidate modes perform no write and return `persistence=null`. | `idea.candidate.persist` plus `Idempotency-Key` | `local`/`test` profiles may write to process-local storage; `demo`/`staging`/`production` require `LOTUS_IDEA_DATABASE_URL` and fail closed with `durable_repository_not_configured` before in-memory mutation. Real PostgreSQL persistence/replay, source-ingestion replay/conflict recovery, and migration rollback/reapply recovery proof exists for this path and the first review/conversion/report workflow path, while production storage certification, source-worker certification beyond bounded live proof, mesh certification, Gateway/Workbench proof, and supported-feature promotion remain planned. |
| `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions` | Internal governed lifecycle transition recording over persisted candidate snapshots. Request input uses the caller-settable lifecycle vocabulary and rejects `accepted` and `executed`; downstream acceptance posture belongs to conversion outcomes and downstream submissions. | `idea.candidate.lifecycle.transition` plus `Idempotency-Key` | Generated OpenAPI and the endpoint ledger publish distinct DTO-validated accepted and idempotent replay modes; replay returns `transition=null`. No downstream authority, suitability, execution, Gateway, Workbench, or supported-feature promotion. |
| `GET /api/v1/idea-candidates/{candidateId}` | Internal source-safe candidate detail projection over persisted candidate snapshots, redacted evidence, workflow summaries, audit summary, and caller entitlement-scope enforcement when scope headers are present. | `idea.candidate.detail.read` or advisor/operator role | Read-only Gateway publication exists through `lotus-gateway` `GET /api/v1/ideas/candidates/{candidate_id}`, including entitlement-scope header forwarding. With the durable PostgreSQL repository provider active, ordinary candidate-detail reads use a repository-side projection over the requested candidate and related detail rows instead of whole-store snapshot hydration. Bounded read-only Workbench rendering exists for source-safe candidate detail through PR #391. No source-system route disclosure, raw evidence export, full Workbench live proof, data-product certification, downstream authority, client-ready publication, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/evidence-replay` | Internal operator evidence replay posture over persisted candidate evidence hashes and caller-supplied current source refs. | `idea.candidate.evidence.replay` plus operator role | Generated OpenAPI and the endpoint ledger publish DTO-validated matched, hash-mismatch, stale-source, and expired modes. Stale-source and expired are normal product-safe HTTP 200 supportability postures with no current evidence hash. No live Core source export, downstream authority, Gateway/Workbench proof, data-product certification, production recovery certification, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate` | Internal governed AI explanation fallback/verifier evaluation over persisted candidate evidence with source-safe idempotent lineage recording. An attested result may include a separately signed provider-retention confirmation bound to candidate tenant plus verified run/provider/model identity. | `idea.ai-explanation.evaluate`, exact candidate tenant entitlement when scoped, plus `Idempotency-Key` | Generated OpenAPI and the endpoint ledger publish complete named local-fixture, verified-attested, deterministic-fallback, unsupported-claim, forbidden-action, and unsafe-action-content responses from one DTO-validated code factory. Local/test output is visibly `unattested_local_test_fixture`; production-like workflow output requires verified Lotus AI provenance. Blocked responses expose server-owned narrative and empty grounding. Signed provider-retention receipts are atomic, replay-fenced, and source-safe; provider failure is blocked and not deletion proof. Same-key replay returns persisted lineage after re-verification. No provider call, lifecycle authority, runtime certification, downstream authority, Gateway/Workbench surface, client-ready publication, or supported-feature promotion. |
| `GET /api/v1/ai-explanations/readiness` | Internal operator diagnostic for AI explanation guardrail availability, model-risk operations posture, and certification blockers. | `idea.ai-explanation.readiness.read` plus operator role | Diagnostic only; it reports source-contract validity for repo-owned model-risk dashboard/alert artifacts while preserving runtime blockers. It is not dashboard provisioning, alert evaluation/delivery, `lotus-ai` runtime execution, provider-call proof, prompt exposure, Gateway/Workbench proof, data-product certification, client-ready publication, or supported-feature promotion. AI lineage and model-risk operations proofs are consumed by aggregate implementation-proof readiness, not promoted by this endpoint alone. |
| `GET /api/v1/review-queues/advisor` | Internal deterministic advisor queue over persisted candidates routed to `advisor_review_required`. `evaluatedAtUtc` is the inclusive candidate-created-at boundary; source/evidence dates retain source-authority meaning. | `idea.review.queue.read` plus advisor role | Queue `policyVersion` names the ranking policy; candidate `scorePolicyVersion` names score provenance. Unknown policies fail closed. Page size defaults to 25 and is capped at 100. The opaque `snapshotToken` binds audience, scope, queue policy, accepted score-policy set, and visible state; changed state returns `409 review_queue_snapshot_conflict`. PostgreSQL uses the same audience-filtered bounded projection. Read-only Gateway publication exists; Workbench proof, data-product certification, client publication, and supported-feature promotion remain out of scope. |
| `GET /api/v1/review-queues/portfolio-manager` | Internal deterministic queue for candidates routed to `pm_review_required`. | `idea.review.queue.portfolio-manager.read` plus portfolio-manager role | Uses the shared audience-bound queue policy and snapshot contract. This is review work routing only; Manage retains mandate, rebalance, action, and execution authority. |
| `GET /api/v1/review-queues/compliance` | Internal deterministic queue for candidates routed to `compliance_review_required`. | `idea.review.queue.compliance.read` plus compliance role | Uses the shared audience-bound queue policy and snapshot contract. Queue presence is not compliance approval or suitability clearance. |
| `GET /api/v1/review-queues/operator/exceptions` | Aggregate support-exception posture grouped by business audience. | `idea.review.queue.exceptions.read` plus operator role | Reports invalid-state, unsupported-evidence, unscored, unrankable-policy, and non-reviewable counts without candidate identifiers or business decision authority. It is an internal operational foundation, not a supported product feature. |
| `GET /api/v1/review-queues/advisor/readiness` | Internal operator diagnostic for deterministic advisor queue projection readiness, aggregate counts, exclusion counts, durable-storage posture, repository-side readiness aggregation posture, and certification blockers. | `idea.review.queue.readiness.read` plus operator role | Diagnostic only; no candidate identifier or access-scope discovery. PostgreSQL classifies unknown score policies without hydrating unrelated state and reports `review_queue_score_policy_coverage_incomplete`; snooze-aware and process-local evaluations retain the domain fallback. Gateway contract, Workbench proof, data-product certification, client publication, and supported-feature promotion remain independently blocked. |
| `POST /api/v1/idea-candidates/{candidateId}/review-actions` | Internal advisor review decision recording with fail-closed trusted entitlement scope and lifecycle/review-posture checks. | `idea.review.record`, advisor role, trusted caller entitlement scope headers, and `Idempotency-Key` | The request body cannot assert access or authorization scope. Candidate lookup uses the bounded projection when available; governance evaluates persisted scope against trusted caller entitlements and `idea-candidate-state-v1`. `reviewId` is a durable resource identity: equivalent content under a new key replays; changed business content returns `review_identity_conflict`. PostgreSQL claims identity before candidate/audit/outbox mutation. No suitability, compliance, mandate, execution, client communication, Gateway, Workbench, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/feedback` | Internal source-provenanced advisor feedback recording with fail-closed trusted entitlement scope checks. | `idea.feedback.record`, advisor role, trusted caller entitlement scope headers, and `Idempotency-Key` | The request body cannot assert access or authorization scope. Candidate lookup uses the bounded projection when available; `feedbackId` binds candidate, evidence, source signals, actor, outcome, reasons, and event time independently of the transport key. Equivalent content under a new key replays; changed content returns `review_identity_conflict`; PostgreSQL prevents duplicate feedback/audit/outbox writes under concurrency. No model-training automation, Gateway, Workbench, data-product certification, or supported-feature promotion. |
| `POST /api/v1/idea-candidates/{candidateId}/conversion-intents` | Internal review-gated conversion intent recording for Advise, Manage, or Report targets. | `idea.conversion.intent.record` plus `Idempotency-Key` | Candidate lookup before conversion governance uses the bounded candidate projection when available. Durable replay/conflict prechecks use bounded idempotency-key lookup plus candidate-detail projection, while accepted writes remain on the repository mutation path. Intent only; no downstream proposal, manage-review, report authority, suitability, execution, client communication, or supported-feature promotion. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions` | Internal source-safe claim-before-call submission for Advise or Manage. Acceptance is returned only after local terminal state commits; uncertain transport or finalization returns `202 reconciliation_required`. | `idea.downstream-realization.submit` plus `Idempotency-Key` | Same-key uncertain retries never call downstream again. No authoritative outcome recording, proposal/action creation proof, suitability, execution, Gateway, Workbench, data-product certification, or supported-feature promotion. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes` | Internal source-authorized, source-versioned downstream outcome recording with cross-key resource replay, append-only correction, and deterministic current posture. | `idea.conversion.outcome.record` plus `Idempotency-Key` | `conversion_outcome_conflict` is distinct from transport `idempotency_conflict`; outcome tracking grants no downstream workflow, suitability, execution, reporting, archive, client-publication, or supported-feature authority. |
| `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs` | Internal report evidence-pack request recording for reviewed report conversion intents. | `idea.report-evidence-pack.request` plus `Idempotency-Key` | Request only; no `lotus-report` package intake, `lotus-render` output, `lotus-archive` record, client-ready publication, or supported-feature promotion. |
| `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions` | Internal source-safe claim-before-call submission for an existing Report evidence-pack request. Acceptance is returned only after local terminal state commits; uncertain transport or finalization returns `202 reconciliation_required`. | `idea.downstream-realization.submit` plus `Idempotency-Key` | Same-key uncertain retries never call downstream again. No Report package intake proof, Render output, Archive record, authoritative outcome, Gateway, Workbench, data-product certification, client-ready publication, or supported-feature promotion. |
| `GET /api/v1/downstream-realization/readiness` | Internal operator diagnostic for Advise, Manage, Report, Render, and Archive realization blockers over current `lotus-idea` workflow counts, manifest-backed planned downstream contract readiness, and optional bounded evidence artifacts. | `idea.downstream-realization.readiness.read` plus operator role | Diagnostic only; planned contract records are validated by `make downstream-realization-contract-gate` but are not downstream route-existence proof. Report intake and materialization source contracts clear no blocker and do not prove report-job execution, rendered output, archive creation, suitability authority, rebalance/action authority, client-ready publication, production certification, or supported-feature promotion. |
| `GET /api/v1/downstream-submissions/reconciliation` | Bounded source-safe operator queue for in-flight and uncertain downstream submissions using opaque support references. | `idea.downstream-reconciliation.read` plus operator role | No raw resource IDs, idempotency keys, payloads, client/portfolio data, downstream calls, Gateway/Workbench product proof, or supported-feature promotion. |
| `POST /api/v1/downstream-submissions/reconciliation/{supportReference}` | Explicit audited accepted/rejected/quarantined local resolution after the operator verifies source-owned downstream truth. | `idea.downstream-reconciliation.resolve` plus operator role; `Idempotency-Key` must equal `changeReference` | Exact repeats replay and conflicting reuse fails closed. The route never retries downstream, creates an authoritative conversion outcome, grants execution/suitability authority, or promotes support. |
| `GET /api/v1/source-ingestion/readiness` | Internal operator diagnostic for high-cash Core source-ingestion configuration, optional receipt-bound runtime evidence, scheduler source-contract posture, deployment-evidence posture, and certification blockers. | `idea.source-ingestion.readiness.read` plus operator role | Diagnostic only. Static scheduler declarations are `source_contract` evidence and clear no blocker. Only matching `deployment` evidence over immutable image, Git, environment, controller, rollout, and configuration identities may clear the scheduler deployment blocker. No scheduled execution, data-product, mesh, Gateway/Workbench, production, downstream, or supported-feature certification follows. |
| `POST /api/v1/source-ingestion/run-once` | Internal operator action that runs one bounded high-cash Core source-ingestion pass through the configured manifest, active repository provider, and Core source adapter. | `idea.source-ingestion.run` plus operator role | Aggregate run summary only; fails closed without durable repository, manifest, or Core configuration; no portfolio identifiers, raw Core payloads, raw idempotency keys, candidate identifiers, live Core certification, scheduled-worker deployment evidence, Gateway/Workbench support, or supported-feature promotion. |
| `GET /api/v1/outbox-delivery/readiness` | Internal operator diagnostic for aggregate outbox backlog, due retry/dead-letter posture, retry-deferred failed rows, durable repository posture, PostgreSQL repository-side readiness projection, broker configuration, publisher-adapter presence, and broker/downstream certification blockers. | `idea.outbox-delivery.readiness.read` plus operator role | Diagnostic only; failed rows below the retry limit become delivery-ready only after their durable `next_attempt_at_utc` is due, and `retryDeferredCount` reports the aggregate failed rows still cooling down while expired leases remain immediately recoverable. `make outbox-event-contract-gate`, `make outbox-consumer-contract-gate`, and bounded proof gates validate repo-owned event, consumer, broker, consumer-runtime, and platform-mesh event-publication evidence, but there are no event identifiers, certified external broker publication, downstream delivery, Gateway/Workbench support, or supported-feature promotion. |
| `POST /api/v1/outbox-delivery/run-once` | Internal operator action that runs one bounded outbox delivery pass through the active repository and configured publisher adapter. | `idea.outbox-delivery.run`, operator role, and `Idempotency-Key` | Aggregate run summary only; failed publication attempts record first/last failure timing plus a deterministic capped retry schedule and are not reclaimed again until due. Same-key/same-request calls replay without mutation, same-key/different-request calls return product-safe conflict, and responses expose only a source-safe `operatorRunReference`. Fails closed without broker configuration; no raw idempotency keys, event identifiers, certified external broker publication, downstream delivery, Gateway/Workbench support, or supported-feature promotion. |
| `GET /api/v1/outbox-delivery/dead-letters` | Bounded operator inspection of quarantined local outbox events. | `idea.outbox-recovery.read` and operator role | Opaque support reference, event family/schema, bounded failure posture, eligibility, and owning-service handoff only; no payload, aggregate/client/portfolio identifiers, or idempotency material. |
| `POST /api/v1/outbox-delivery/dead-letters/{supportReference}/redrive` | One explicit, fenced publication attempt for an eligible local dead letter. | `idea.outbox-recovery.redrive`, operator role, trusted production provenance, `Idempotency-Key`, reason, and change reference | Persists original failure history and a new lease before publication. Same-key replay is non-mutating; conflict, unsupported schema/family, lease conflict, or attempt exhaustion remain quarantined. This is not external broker or consumer certification. |
| `GET /api/v1/data-mesh/readiness` | Internal operator diagnostic for repo-authored planned/not-certified data-mesh posture and platform-aligned promotion blockers. | `idea.mesh.readiness.read` plus operator role | Diagnostic only; no data-product certification, platform source-manifest inclusion, platform catalog inclusion, SLO/access/evidence certification, runtime lineage proof, Gateway/Workbench discovery, or supported-feature promotion. |
| `GET /api/v1/data-mesh/trust-telemetry/runtime-preview` | Internal operator diagnostic for source-safe aggregate runtime trust telemetry preview over the active repository provider. | `idea.mesh.trust-telemetry.preview.read` plus operator role | Diagnostic only; no candidate detail, source route export, data-product certification, platform source-manifest inclusion, Gateway/Workbench discovery, or supported-feature promotion. |
| `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` | Internal operator diagnostic for source-safe contract-shaped runtime trust telemetry snapshot evidence over the active repository provider. | `idea.mesh.trust-telemetry.snapshot.read` plus operator role | Diagnostic only; no candidate detail, source route export, data-product certification, platform source-manifest inclusion, Gateway/Workbench discovery, client-ready publication, or supported-feature promotion. |
| `GET /api/v1/implementation-proof/readiness` | Internal aggregate operator diagnostic for RFC-0002 implementation proof blockers, including outbox-delivery readiness, run-once posture, and bounded downstream/outbox/Gateway-Workbench proof artifact consumption. | `idea.implementation-proof.readiness.read` plus operator role | Diagnostic only; bounded proof artifacts clear only named blockers. No full live implementation proof, certified external broker publication, Advise suitability authority, Manage rebalance/action authority, downstream delivery, data-product certification, full Gateway/Workbench product proof, client-ready publication, or supported-feature promotion. |

Baseline health and metadata endpoints are also tracked in the ledger with
`baseline_certified` posture:

1. `GET /health`,
2. `GET /health/live`,
3. `GET /health/ready`,
4. `GET /metadata`.

Use these endpoints only for their current internal foundation, bounded
read-only Gateway publication, or operator diagnostic/action purpose. Do not use them
as live source ingestion proof, Workbench proof, data-product certification,
durable database evidence beyond the explicit PostgreSQL runtime proof,
downstream realization proof, client-ready publication, or supported-feature
promotion. Those remain blocked until later RFC slices add runtime adapters,
downstream contracts, trust telemetry, UI proof, and supported-feature
registration.

Caller-context authorization headers are local/test simulation inputs unless
they arrive through trusted ingress. In `demo`, `staging`, and `production`,
requests carrying privileged `X-Caller-*` role, capability, or entitlement
headers must also carry `X-Lotus-Trusted-Caller-Context` matching
`LOTUS_IDEA_TRUSTED_CALLER_CONTEXT_TOKEN`; otherwise the shared caller-context
boundary rejects the request with product-safe `403` behavior before route
authorization. `tests/integration/test_caller_context_boundary_api.py` proves
the stable response and source-safe diagnostic behavior across representative
signal, lifecycle, review, AI, report, downstream, and readiness routes. This
is trusted-ingress provenance only, not identity-provider, signed assertion,
Workbench entitlement, or client-publication proof.

Every row above is backed by
`docs/operations/endpoint-certification-ledger.json`; keep this narrative guide
and the ledger synchronized when a certified endpoint is added, removed, or
materially changes boundary.

## Source-Degraded And Reconciliation Endpoints

Endpoints that reconcile expected-versus-realized state or consume another Lotus app as source
authority must also include:

1. explicit source-owner fields in success and degraded responses,
2. source freshness, lineage, and supportability fields where the source owner exposes them,
3. READY, DEGRADED, BLOCKED, and NOT_SUPPORTED examples where those states are applicable,
4. tests for missing, stale, unavailable, partial, malformed, and conflicting upstream evidence,
5. proof that the service does not clone calculations owned by another Lotus app,
6. same-RFC upstream source-contract and downstream consumer realization evidence when contracts
   change,
7. README, wiki, supported-feature, and RFC evidence updates before any product support claim.
