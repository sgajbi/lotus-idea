# RFC-0002 Slice 10: Certified APIs, OpenAPI, And Gateway Contract

Status: Partially implemented - certified internal API foundations plus bounded read-only Gateway publication for advisor queue and candidate detail

## Outcome

Expose certified `lotus-idea` APIs and Gateway routes for supported behavior.

## Implemented In This Slice

The first certified API foundations are:

- `POST /api/v1/idea-signals/high-cash/evaluate`
- `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`
- `POST /api/v1/idea-signals/low-income/evaluate`
- `POST /api/v1/idea-signals/bond-maturity/evaluate`
- `POST /api/v1/idea-signals/concentration-risk/evaluate`
- `POST /api/v1/idea-signals/high-volatility/evaluate`
- `POST /api/v1/idea-signals/drawdown-review/evaluate`
- `POST /api/v1/idea-signals/underperformance/evaluate`
- `POST /api/v1/idea-signals/allocation-drift/evaluate`
- `POST /api/v1/idea-signals/missing-suitability/evaluate`
- `POST /api/v1/idea-signals/missing-risk-profile/evaluate`
- `POST /api/v1/idea-signals/mandate-restriction/evaluate`
- `POST /api/v1/idea-signals/missing-benchmark/evaluate`
- `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions`
- `GET /api/v1/idea-candidates/{candidateId}`
- `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`
- `POST /api/v1/idea-candidates/{candidateId}/ai-explanations/evaluate`
- `GET /api/v1/review-queues/advisor`
- `POST /api/v1/idea-candidates/{candidateId}/review-actions`
- `POST /api/v1/idea-candidates/{candidateId}/feedback`
- `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`
- `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`
- `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`

These endpoints evaluate caller-supplied, source-owned `lotus-core` evidence
for the high-cash / idle-liquidity signal family. They consume source-reported
cash weight and source references; they do not fetch upstream data and do not
calculate official cash, holdings, or portfolio values.

The concentration-risk, high-volatility, drawdown-review, underperformance, allocation-drift, low-income, bond-maturity, missing suitability, missing
risk-profile, mandate/restriction, and missing-benchmark signal endpoints
expose bounded caller-supplied evidence evaluation over source-owned Risk,
Performance, Core, Advise, or Manage
posture evidence. They create only source-safe review candidates or blocked
posture, require `idea.signal.evaluate` or advisor role, redact raw source
routes and content hashes from response candidates, emit bounded operation
events, and do not infer client income needs, provide funding advice, issue
treasury instructions, approve planning suitability, recommend replacement
products, calculate reinvestment advice, calculate concentration, calculate volatility, calculate
drawdown, calculate returns, calculate allocation drift, assign benchmarks, approve risk
methodology, recommend trades, create rebalance actions, own maturity
schedules, create orders, approve suitability, policy, proposal, sign-off,
mandate state, restriction clearance, benchmark assignment, benchmark
methodology, performance calculation, client publication, Gateway, Workbench,
data-mesh certification, or supported-feature promotion.

`evaluate-and-persist` adds internal candidate persistence through the Slice 06
repository foundation. It requires `Idempotency-Key` and
`idea.candidate.persist`, returns replay/conflict posture for idempotency
behavior, and reports `durableStorageBacked` from the active repository
provider. `local` and `test` profiles may use process-local writes; `demo`,
`staging`, and `production` require `LOTUS_IDEA_DATABASE_URL` and return
`durable_repository_not_configured` before in-memory mutation when durable
storage is absent.

The lifecycle transition endpoint exposes the Slice 06 internal lifecycle
history, idempotency, and audit foundation over persisted candidates. It
requires `Idempotency-Key` and `idea.candidate.lifecycle.transition`, applies
the canonical domain lifecycle transition graph, returns replay/conflict,
not-found, and invalid-transition posture, and keeps
`supportedFeaturePromoted=false`. `durableStorageBacked` follows the active
repository provider.

The candidate detail endpoint exposes a source-safe internal read projection
over persisted candidate snapshots. It requires
`idea.candidate.detail.read` capability or advisor/operator role, returns
redacted source evidence, lifecycle history, review decisions, feedback,
conversion intents/outcomes, report evidence-pack summaries, and audit summary
posture, and does not expose source-system routes, raw source content hashes,
downstream authority, Workbench proof, data-product certification, or
supported-feature promotion. The bounded read-only Gateway candidate detail
publication preserves this source-safe projection and forwards caller
entitlement-scope headers; `lotus-idea` applies those headers fail-closed before
returning detail. `durableStorageBacked` follows the active repository provider.
When the active durable provider is PostgreSQL, ordinary candidate-detail reads
use an internal repository-side projection for the requested candidate and its
related lifecycle, audit, review, feedback, conversion, report-evidence, and
AI-lineage rows rather than hydrating a whole repository snapshot. This is
bounded design modularity inside `lotus-idea`; it is not a separate runtime
service boundary or a supported-feature promotion.

The candidate evidence replay endpoint exposes internal operator replay posture
over persisted evidence hashes. It requires `idea.candidate.evidence.replay`
plus operator role, accepts caller-supplied current source refs, returns
matched, stale-source, hash-mismatch, expired, or not-found posture, and never
calls Core, exports raw source routes, grants downstream authority, certifies
data products, proves Gateway/Workbench behavior, or promotes a supported
feature. `durableStorageBacked` follows the active repository provider.

The review-action and feedback endpoints expose the Slice 08 internal workflow
foundation over persisted candidates. They require `Idempotency-Key`, a
mutating capability, caller role, and upstream-authorized review scope. They
record review decisions or feedback through the same internal repository
foundation, return replay/conflict/not-found posture, never grant downstream
suitability/compliance/mandate/execution/client-communication authority, and
keep `supportedFeaturePromoted=false`. `durableStorageBacked` follows the
active repository provider.

The conversion-intent and conversion-outcome endpoints expose the Slice 12
internal conversion workflow foundation over persisted, review-approved
candidates. They require `Idempotency-Key` and conversion-specific
capabilities, record source-authority mapped conversion intent/outcome audit
evidence, enforce target-source authority for downstream outcomes, never grant
Advise/Manage/Report workflow authority, suitability, execution, or
client-communication authority, and keep `supportedFeaturePromoted=false`.
`durableStorageBacked` follows the active repository provider.

The advisor review queue endpoint exposes the Slice 07 deterministic queue
projection over persisted candidate snapshots. It requires
`idea.review.queue.read` capability or advisor role, returns ranked items plus
exclusions, accepts optional tenant/book/portfolio/client query filters for
scope-aware projection, and keeps `supportedFeaturePromoted=false`.
`durableStorageBacked` follows the active repository provider.

`lotus-gateway` now publishes the first bounded read-only idea routes on main:
`GET /api/v1/ideas/review-queues/advisor` and
`GET /api/v1/ideas/candidates/{candidate_id}`. Gateway forwards caller
context, caller entitlement-scope, and correlation headers to `lotus-idea`,
preserves `lotus-idea` ranking, source references, durable-storage posture, and
unsupported-feature posture, blocks any upstream `supportedFeaturePromoted=true` response, and
does not generate, rank, enrich, certify, or promote ideas locally. Workbench
PR #391 now consumes these read-only Gateway paths for bounded queue/detail
rendering. This is not full Workbench live proof, data-product certification,
full source-ingestion certification, client-ready publication, or
supported-feature promotion.

The AI explanation endpoint exposes the Slice 09 internal fallback/verifier
foundation over persisted candidate evidence. It requires
`idea.ai-explanation.evaluate`, returns redacted evidence only, blocks
unsupported claims and forbidden actions, never calls providers or executes
`lotus-ai` runtime workflows, never certifies runtime AI lineage-store proof, never grants
downstream authority, and keeps `durableStorageBacked=false`,
`lotusAiRuntimeExecuted=false`, and `supportedFeaturePromoted=false`.

Implementation files:

1. `src/app/api/idea_signals.py`: FastAPI DTOs, authorization mapping,
   product-safe errors, idempotency-conflict handling, OpenAPI examples, and
   route registration.
2. `src/app/api/missing_suitability_signals.py`: bounded missing
   suitability-context signal API over caller-supplied Advise policy-evaluation
   evidence with product-safe authorization, source-redacted response
   projection, OpenAPI examples, and operation events.
3. `src/app/api/missing_benchmark_signals.py`: bounded missing-benchmark
   signal API over caller-supplied Core benchmark-assignment evidence with
   product-safe authorization, source-redacted response projection, OpenAPI
   examples, and operation events.
4. `src/app/api/low_income_signals.py`: bounded low-income /
   liquidity-shortfall signal API over caller-supplied Core cashflow projection
   and cash movement evidence with product-safe authorization, source-redacted
   response projection, OpenAPI examples, and operation events.
5. `src/app/api/bond_maturity_signals.py`: bounded bond-maturity /
   reinvestment review signal API over caller-supplied Core holdings maturity
   evidence with product-safe authorization, source-redacted response
   projection, OpenAPI examples, and operation events.
6. `src/app/api/concentration_risk_signals.py`: bounded concentration-risk
   signal API over caller-supplied Lotus Risk concentration evidence with
   shared product-safe authorization, source-redacted response projection,
   OpenAPI examples, operation events, and no local risk-methodology authority.
7. `src/app/api/drawdown_review_signals.py`: bounded drawdown-review signal
   API over caller-supplied Lotus Risk drawdown analytics evidence with shared
   product-safe authorization, source-redacted response projection, OpenAPI
   examples, operation events, and no local Risk drawdown calculation or
   risk-methodology authority.
8. `src/app/api/allocation_drift_signals.py`: bounded allocation-drift /
   mandate-review signal API over caller-supplied Lotus Manage action-register
   and mandate-health source-ref posture with shared product-safe
   authorization, source-redacted response projection, OpenAPI examples,
   operation events, and no local drift calculation, mandate approval,
   rebalance action, order, or downstream authority.
9. `src/app/api/signal_api_support.py`: shared signal API route metadata,
   permission, source-authority, operation outcome, and product-safe 400/403
   `ProblemDetails` OpenAPI response metadata used by caller-supplied signal
   endpoints for design modularity without a new runtime service boundary.
10. `src/app/application/high_cash_signal.py`: application command and policy
   orchestration over framework-free domain evaluation and internal
   evaluate-and-persist behavior.
11. `src/app/domain/signal_evaluation.py`: existing deterministic high-cash
   domain policy reused by the endpoint.
12. `src/app/domain/persistence.py`: internal idempotency/audit repository used
   by the evaluate-and-persist and lifecycle transition API foundations.
13. `src/app/errors.py`: RFC-7807-shaped problem detail body with stable
    `type`, `status`, `code`, `title`, and `detail` fields.
14. `src/app/api/problem_details.py`: shared workflow/operator API
    `ProblemDetails` OpenAPI metadata and common product-safe permission and
    request-failure response helpers, used for design modularity without adding
    a runtime service boundary.
15. `docs/operations/endpoint-certification-ledger.json`: machine-readable
    endpoint certification evidence for the new route.
16. `src/app/api/review_workflow.py`: review-action and feedback DTOs,
    authorization/scope mapping, product-safe errors, idempotency-conflict
    handling, OpenAPI examples, and route registration.
17. `src/app/api/review_queues.py`: advisor queue DTOs, authorization mapping,
    optional tenant/book/portfolio/client scope filters, product-safe errors,
    OpenAPI examples, and route registration.
18. `src/app/api/caller_headers.py`: shared API caller-header parsing used by
    signal and review routes.
19. `src/app/api/candidate_lifecycle.py`: lifecycle transition DTOs,
    authorization mapping, product-safe errors, idempotency-conflict handling,
    OpenAPI examples, and route registration.
20. `src/app/application/candidate_lifecycle.py`: application command and
    idempotency payload construction for lifecycle transitions.
21. `src/app/api/candidate_detail.py`: source-safe candidate detail DTOs,
    authorization and caller-scope mapping, redacted source projection,
    product-safe errors, OpenAPI examples, and route registration.
22. `src/app/application/candidate_detail.py`: persisted candidate snapshot
    lookup and access-scope matching through the governed repository port.
23. `src/app/api/candidate_evidence_replay.py`: evidence replay DTOs,
    authorization mapping, product-safe errors, OpenAPI examples, operation
    events, and route registration.
24. `src/app/application/candidate_evidence_replay.py`: command validation and
    replay orchestration through the governed repository port.
25. `src/app/api/ai_governance.py`: AI explanation DTOs, authorization
    mapping, redacted response projection, product-safe errors, OpenAPI
    examples, and route registration.
26. `src/app/application/ai_governance.py`: persisted candidate snapshot
    lookup plus deterministic fallback/verifier orchestration without provider
    execution or durable persistence claims.
27. `src/app/api/conversion_governance.py`: conversion intent/outcome DTOs,
    authorization mapping, product-safe errors, idempotency-conflict handling,
    OpenAPI examples, and route registration.
28. `src/app/application/conversion_workflow.py`: application commands,
    idempotency payload construction, repository precheck, and domain
    invocation for conversion intent/outcome workflow.
29. `tests/integration/test_review_workflow_api.py`: certified API behavior
   evidence for lifecycle transition, review action, feedback, and conversion
   foundations.
30. `tests/integration/test_review_queue_api.py`: certified API behavior
    evidence for advisor queue projection.
31. `tests/integration/test_candidate_detail_api.py`: certified API behavior
    evidence for source-safe detail projection, workflow summaries, permission,
    missing candidate, and no-authority promotion.
32. `tests/integration/test_candidate_evidence_replay_api.py`: certified API
    behavior evidence for matched, stale-source, hash-mismatch, permission,
    missing candidate, invalid request, and no-authority replay posture.
33. `tests/integration/test_ai_governance_api.py`: certified API behavior
    evidence for AI fallback, verifier acceptance, blocked output, permission,
    missing candidate, invalid state, and forbidden metadata.
34. `tests/integration/test_missing_suitability_signal_api.py`: certified API
    behavior evidence for candidate creation, blocked publication posture,
    permission denial, source-redacted response projection, and no-authority
    promotion.
35. `tests/integration/test_missing_benchmark_signal_api.py`: certified API
    behavior evidence for missing-benchmark candidate creation, ready-assignment
    not-eligible posture, stale-source blocking, permission denial,
    source-redacted response projection, and no-authority promotion.
36. `tests/integration/test_low_income_signal_api.py`: certified API behavior
    evidence for low-income / liquidity-shortfall candidate creation,
    above-threshold not-eligible posture, stale-source blocking, permission
    denial, source-redacted response projection, and no-authority promotion.
37. `tests/integration/test_bond_maturity_signal_api.py`: certified API
    behavior evidence for bond-maturity / reinvestment review candidate
    creation, outside-window not-eligible posture, stale-source blocking,
    permission denial, source-redacted response projection, and no-authority
    promotion.
38. `tests/integration/test_concentration_risk_signal_api.py`: certified API
    behavior evidence for concentration-risk review candidate creation,
    below-threshold not-eligible posture, partial issuer-coverage blocking,
    stale-source blocking, permission denial, and no-authority promotion.
39. `tests/integration/test_drawdown_review_signal_api.py`: certified API
    behavior evidence for drawdown-review candidate creation, below-threshold
    not-eligible posture, non-ready source blocking, stale-source blocking,
    permission denial, and no-authority promotion.
40. `tests/integration/test_allocation_drift_signal_api.py`: certified API
    behavior evidence for allocation-drift / mandate-review candidate creation,
    below-threshold not-eligible posture, store-wide Manage supportability
    blocking, non-ready and stale source blocking, permission denial,
    source-redacted response projection, and no-authority promotion.
41. `tests/integration/test_api_operation_events.py`: bounded operation-event
    evidence for certified signal endpoint posture.

## Current Contract

The evaluate endpoint returns deterministic posture only:

1. `candidate_created` when all source evidence is current, entitlement is
   allowed, and the source-reported signal evidence satisfies the relevant
   policy threshold, review window, or evidence-gap policy,
2. `blocked` for stale/missing source evidence, missing source-reported metric,
   or entitlement denial,
3. `suppressed` for duplicate candidate evidence,
4. `not_eligible` when source-reported evidence is current but below the
   relevant policy threshold or outside the review window.

The evaluate endpoint is permissioned by `idea.signal.evaluate` capability or
advisor role. The evaluate-and-persist endpoint is permissioned by
`idea.candidate.persist` and requires `Idempotency-Key`. Validation,
permission, and idempotency-conflict failures return product-safe Problem
Details.

The review-action endpoint is permissioned by `idea.review.record` plus one
recognized review actor role. The feedback endpoint is permissioned by
`idea.feedback.record` plus one recognized review actor role. Both endpoints
require upstream-authorized tenant/book/portfolio/client scope in the request
and continue to use request-carried authorized scope until their Gateway or
Workbench mutation surfaces are implemented. Scope, permission, missing
candidate, idempotency conflict, and invalid candidate-state failures return
product-safe Problem Details.

The advisor review queue endpoint is permissioned by
`idea.review.queue.read` capability or advisor role. It requires a
timezone-aware `evaluatedAtUtc` query parameter, accepts optional
tenant/book/portfolio/client scope filters, applies platform caller-context
entitlement scope headers automatically when present, rejects query scopes
outside caller entitlements fail-closed, excludes persisted candidates outside
the effective scope with `access_scope_mismatch`, and returns product-safe
Problem Details for permission or validation failures.

The candidate detail endpoint is permissioned by
`idea.candidate.detail.read` capability or advisor/operator role. It returns
source-safe details for an existing candidate only when any provided platform
caller-context entitlement scope matches the persisted candidate scope, and
returns product-safe Problem Details for permission, validation, out-of-scope,
or missing-candidate failures.

The candidate evidence replay endpoint is permissioned by
`idea.candidate.evidence.replay` plus operator role. It requires non-empty
`currentSourceRefs`, compares current source refs against persisted evidence
hash posture, returns product-safe replay status, and returns Problem Details
for permission, validation, or missing-candidate failures.

The AI explanation endpoint is permissioned by
`idea.ai-explanation.evaluate`. It accepts a governed workflow-pack reference,
approved metadata, optional workflow output, and a requested timestamp. If no
workflow output is supplied, it returns deterministic fallback. If workflow
output is supplied, it verifies source-product claim support and forbidden
action policy, returning a blocked posture for unsupported claims or prohibited
actions. Missing candidates, permission failure, invalid request shape,
forbidden metadata, and invalid candidate lifecycle posture return product-safe
Problem Details.

The lifecycle transition endpoint is permissioned by
`idea.candidate.lifecycle.transition` and requires `Idempotency-Key`. It accepts
only target statuses allowed by the domain lifecycle graph and returns
product-safe Problem Details for validation, permission, missing candidate,
idempotency conflict, or invalid lifecycle transition failures.

The conversion-intent endpoint is permissioned by
`idea.conversion.intent.record` and requires `Idempotency-Key`. It accepts only
persisted candidates that are already approved for conversion and returns
product-safe Problem Details for validation, permission, missing candidate,
idempotency conflict, or invalid conversion-state failures.

The conversion-outcome endpoint is permissioned by
`idea.conversion.outcome.record` and requires `Idempotency-Key`. It records
downstream outcome posture only when the reporting `sourceSystem` matches the
conversion target source authority and returns product-safe Problem Details for
validation, permission, missing intent, idempotency conflict, or wrong-source
failures.

The source-ingestion run-once endpoint is permissioned by
`idea.source-ingestion.run` and operator role. It executes the bounded
high-cash source-ingestion batch foundation only when durable repository,
manifest, and Core source configuration are present. It returns aggregate
decision counts only and returns blocked posture without mutation when runtime
configuration is absent or invalid.

`supportedFeaturePromoted` is always `false` in these foundation endpoints.
`durableStorageBacked` follows the active repository provider for
repository-backed foundation endpoints: allowed `local`/`test` process-local
runtime reports `false`, and `LOTUS_IDEA_DATABASE_URL` runtime reports `true`.
Production-like profiles without durable storage fail closed before mutation. The endpoints are
certified as API foundations but are not supported business features because
source-worker certification beyond bounded live proof, Workbench proof,
data-product certification, runtime trust telemetry, downstream realization
proof, and supported-feature registration are not implemented yet. The bounded read-only Gateway
publication listed above is integration foundation only, not support.

## Required Work

1. Implement route families approved by prior slices.
2. Add complete OpenAPI descriptions, examples, error cases, degraded cases,
   unsupported-evidence cases, idempotency behavior, and entitlement behavior.
3. Update endpoint certification ledger.
4. Extend `lotus-gateway` contracts and routes without Gateway-side idea
   generation or ranking when additional read or workflow surfaces become
   implementation-backed.

## Remaining Work

1. Extend the current Core high-cash source-port and conservative HTTP adapter
   into live source contract proof once Core publishes an explicit
   source-reported cash-weight field; keep all official cash/holding
   calculations in `lotus-core`.
2. Extend Gateway coverage beyond the first read-only advisor queue and
   candidate detail publication where needed, preserving `lotus-idea` source
   authority and preventing Gateway-side ranking or generation.
3. Extend the bounded Workbench read-only review surface into full live,
   entitlement-denied, mutation, and demo proof before any supported UI or demo
   claim.
4. Add deployment and recovery proof for PostgreSQL-backed API state.
5. Add data-product trust telemetry, platform mesh certification, and
   supported-feature promotion only after runtime proof exists.
6. Add additional route families for evidence packs and supportability after
   their storage and orchestration slices are implementation-backed.

## Platform Follow-Up

The local slice exposed a reusable scaffold concern: FastAPI business route
registration must stay compatible with Prometheus instrumentation. The current
`lotus-idea` route is registered directly on the app before instrumentation.
Platform scaffold follow-up is tracked in
`sgajbi/lotus-platform#420`.

## Validation Evidence

Focused validation passed for the current foundation:

1. `python -m pytest tests/unit/test_high_cash_application.py tests/integration/test_high_cash_signal_api.py tests/unit/test_service_contract.py -q`
2. `python -m ruff check src/app/api/idea_signals.py src/app/application/high_cash_signal.py src/app/errors.py src/app/main.py tests/unit/test_high_cash_application.py tests/integration/test_high_cash_signal_api.py tests/unit/test_service_contract.py`
3. `python -m mypy --config-file mypy.ini`
4. `python scripts/openapi_quality_gate.py`
5. `python scripts/endpoint_certification_gate.py`
6. `.venv\Scripts\python.exe -m pytest tests\integration\test_high_cash_signal_api.py tests\unit\test_service_contract.py -q` passed with `16 passed` after adding evaluate-and-persist API certification and blank idempotency-key hardening.
7. `make check` passed with `187` unit tests plus lint, format, typecheck,
   architecture, OpenAPI, supported-feature, endpoint-certification,
   data-mesh, and contract gates.
8. `make ci` passed with `19` integration tests, `2` e2e tests, `187` unit
   tests under coverage, coverage gate at `99.18%`, and dependency audit.
9. `.venv\Scripts\python.exe -m pytest tests\integration\test_review_workflow_api.py tests\unit\test_service_contract.py -q` passed with `17 passed` after adding review-action and feedback API certification.
10. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` passed
    after adding review-action and feedback route ledger evidence.
11. `.venv\Scripts\python.exe -m pytest tests\integration\test_review_queue_api.py -q`
    passed with `4 passed` after adding advisor review queue API certification.
12. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` passed
    after adding advisor review queue route ledger evidence.
13. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_service_contract.py tests\integration\test_review_workflow_api.py -q`
    passed with `29 passed` after adding lifecycle transition API
    certification.
14. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` and
    `.venv\Scripts\python.exe scripts\openapi_quality_gate.py` passed after
    adding lifecycle transition route ledger evidence.
15. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `189` unit tests.
16. `make ci` passed with `39` integration tests, `2` e2e tests, `189` unit
    tests under coverage, coverage gate at `99.14%`, and dependency audit
    reporting no known vulnerabilities.
17. `make docker-build` passed for `backend-service:ci-test`.
18. `.venv\Scripts\python.exe -m pytest tests\unit\test_conversion_governance.py tests\unit\test_idea_persistence.py tests\integration\test_review_workflow_api.py -q`
    passed with `42 passed` after adding conversion intent/outcome API
    foundations, repository idempotency persistence, and outcome source
    authority enforcement.
19. `python -m pytest tests/integration/test_ai_governance_api.py tests/integration/test_api_operation_events.py`
    passed with `8 passed` after adding the AI explanation evaluator API
    foundation and operation-event coverage.
20. `python -m ruff check src/app/application/ai_governance.py src/app/api/ai_governance.py tests/integration/test_ai_governance_api.py tests/integration/test_api_operation_events.py`
    passed after adding the AI API route, DTOs, and tests.
21. `make ci` passed after adding the AI explanation API foundation with `59`
    integration tests, `2` e2e tests, `218` unit tests, coverage gate at
    `99.17%`, and dependency audit reporting no known vulnerabilities.
22. `python -m pytest tests/integration/test_candidate_detail_api.py tests/integration/test_api_operation_events.py tests/unit/test_service_contract.py -q`
    passed with `12 passed` after adding the candidate detail API foundation,
    source-redaction assertions, workflow summary assertions,
    permission/not-found behavior, endpoint-ledger contract, and bounded
    operation-event coverage.
23. `.venv\Scripts\python.exe -m pytest tests\integration\test_candidate_evidence_replay_api.py tests\integration\test_api_operation_events.py -q`
    passed with `9 passed` after adding the evidence replay API foundation,
    OpenAPI/ledger examples, matched/stale/hash-mismatch/not-found/permission
    behavior, and bounded `candidate_evidence_replay` operation-event coverage.
24. `lotus-gateway` PR #467 merged to main at
    `c32c7ebda5deac798a6c04675c35df63f36a79cb` with read-only Gateway
    publication for advisor queue and candidate detail. Gateway validation
    passed `make lint`, `make check`, Feature Lane, Quality Baseline, PR Merge
    Gate, Main Releasability, and wiki publication.
25. `.venv\Scripts\python.exe -m pytest tests/unit/test_review_queue_application.py tests/integration/test_review_queue_api.py tests/unit/test_postgres_repository.py`
    passed with `16 passed` after adding scope-aware advisor queue filtering,
    product-safe blank-scope validation, and PostgreSQL candidate-scope
    serialization evidence.
26. `.venv\Scripts\python.exe -m pytest tests\integration\test_low_income_signal_api.py tests\integration\test_api_operation_events.py tests\unit\test_service_contract.py -q`
    passed with `21 passed` after adding the low-income / liquidity-shortfall
    caller-supplied API foundation, endpoint ledger contract, and bounded
    signal-evaluation operation-event coverage.
27. `make endpoint-certification-gate`, `make openapi-gate`, and
    `make opportunity-archetype-contract-gate` passed after adding
    `POST /api/v1/idea-signals/low-income/evaluate`, API certification ledger
    evidence, and low-income archetype contract evidence.
28. `make lint`, `make typecheck`, `make documentation-contract-gate`,
    `make supported-features-gate`, `make test-integration`, `make test-e2e`,
    and `make check` passed after the low-income API slice. `make check`
    included `1774` unit tests; `make test-integration` passed with `163`
    integration tests and `5` PostgreSQL-runtime tests skipped; `make test-e2e`
    passed with `2` smoke tests.
29. `.venv\Scripts\python.exe -m pytest tests\unit\test_api_problem_details.py tests\integration\test_review_workflow_api.py -q`
    passed with `27 passed` after adding shared workflow/operator
    `ProblemDetails` OpenAPI metadata for lifecycle, review, feedback,
    conversion, and report evidence-pack routes.
30. `.venv\Scripts\python.exe -m ruff check src\app\api\problem_details.py src\app\api\candidate_lifecycle.py src\app\api\review_workflow.py src\app\api\conversion_governance.py src\app\api\report_evidence.py tests\unit\test_api_problem_details.py`,
    `.venv\Scripts\python.exe -m mypy --config-file mypy.ini`,
    `.venv\Scripts\python.exe scripts\openapi_quality_gate.py`,
    `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py`, and
    `.venv\Scripts\python.exe scripts\architecture_boundary_gate.py --mode blocking`
    passed for the shared API error-model polish.
31. `make test-coverage` passed with `1832` unit tests, `199` integration
    tests and `5` PostgreSQL-runtime tests skipped, `2` e2e tests, and
    coverage gate `99.00`.
32. `make ci` passed after the coverage fix, including repository contract
    gates, OpenAPI, endpoint certification, architecture boundary, migrations,
    integration/e2e/unit coverage, coverage gate `99.00`, and dependency audit
    with no known vulnerabilities.

PR merge-gate evidence remains required before merge.

## Acceptance Gate

1. OpenAPI quality gate passes for every exposed route.
2. Endpoint certification passes for every exposed route.
3. Gateway contract tests prove source-owned `lotus-idea` truth is preserved
   before each Gateway route is claimed implemented; the first bounded
   read-only advisor queue and candidate detail routes satisfy this foundation
   rule, including caller entitlement-scope forwarding. Workbench PR #391
   consumes those routes for bounded read-only rendering, but this does not
   complete full live Workbench proof or supported-feature promotion.
4. No alias or stale endpoint remains without explicit time-boxed justification.
5. Supported-feature promotion remains blocked until live runtime,
   Gateway/Workbench, data-product, docs/wiki, and certification evidence all
   exist.
