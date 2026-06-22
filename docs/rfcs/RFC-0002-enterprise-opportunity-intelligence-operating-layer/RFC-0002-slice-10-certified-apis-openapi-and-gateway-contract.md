# RFC-0002 Slice 10: Certified APIs, OpenAPI, And Gateway Contract

Status: Partially implemented - certified internal API foundations plus bounded read-only Gateway publication for advisor queue and candidate detail

## Outcome

Expose certified `lotus-idea` APIs and Gateway routes for supported behavior.

## Implemented In This Slice

The first certified API foundations are:

- `POST /api/v1/idea-signals/high-cash/evaluate`
- `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`
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

`evaluate-and-persist` adds internal candidate persistence through the Slice 06
repository foundation. It requires `Idempotency-Key` and
`idea.candidate.persist`, returns replay/conflict posture for idempotency
behavior, and reports `durableStorageBacked` from the active repository
provider. Default runtime remains process-local; configured
`LOTUS_IDEA_DATABASE_URL` runtime uses the PostgreSQL repository adapter.

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
publication preserves this source-safe projection; `durableStorageBacked`
follows the active repository provider.

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
context and correlation headers to `lotus-idea`, preserves `lotus-idea`
ranking, source references, durable-storage posture, and unsupported-feature
posture, blocks any upstream `supportedFeaturePromoted=true` response, and
does not generate, rank, enrich, certify, or promote ideas locally. This is
not Workbench proof, data-product certification, live source proof, client-ready
publication, or supported-feature promotion.

The AI explanation endpoint exposes the Slice 09 internal fallback/verifier
foundation over persisted candidate evidence. It requires
`idea.ai-explanation.evaluate`, returns redacted evidence only, blocks
unsupported claims and forbidden actions, never calls providers or executes
`lotus-ai` runtime workflows, never persists durable AI lineage, never grants
downstream authority, and keeps `durableStorageBacked=false`,
`lotusAiRuntimeExecuted=false`, and `supportedFeaturePromoted=false`.

Implementation files:

1. `src/app/api/idea_signals.py`: FastAPI DTOs, authorization mapping,
   product-safe errors, idempotency-conflict handling, OpenAPI examples, and
   route registration.
2. `src/app/application/high_cash_signal.py`: application command and policy
   orchestration over framework-free domain evaluation and internal
   evaluate-and-persist behavior.
3. `src/app/domain/signal_evaluation.py`: existing deterministic high-cash
   domain policy reused by the endpoint.
4. `src/app/domain/persistence.py`: internal idempotency/audit repository used
   by the evaluate-and-persist and lifecycle transition API foundations.
5. `src/app/errors.py`: RFC-7807-shaped problem detail body with stable
   `type`, `status`, `code`, `title`, and `detail` fields.
6. `docs/operations/endpoint-certification-ledger.json`: machine-readable
   endpoint certification evidence for the new route.
7. `src/app/api/review_workflow.py`: review-action and feedback DTOs,
   authorization/scope mapping, product-safe errors, idempotency-conflict
   handling, OpenAPI examples, and route registration.
8. `src/app/api/review_queues.py`: advisor queue DTOs, authorization mapping,
   optional tenant/book/portfolio/client scope filters, product-safe errors,
   OpenAPI examples, and route registration.
9. `src/app/api/caller_headers.py`: shared API caller-header parsing used by
   signal and review routes.
10. `src/app/api/candidate_lifecycle.py`: lifecycle transition DTOs,
    authorization mapping, product-safe errors, idempotency-conflict handling,
    OpenAPI examples, and route registration.
11. `src/app/application/candidate_lifecycle.py`: application command and
    idempotency payload construction for lifecycle transitions.
12. `src/app/api/candidate_detail.py`: source-safe candidate detail DTOs,
    authorization mapping, redacted source projection, product-safe errors,
    OpenAPI examples, and route registration.
13. `src/app/application/candidate_detail.py`: persisted candidate snapshot
    lookup through the governed repository port.
14. `src/app/api/candidate_evidence_replay.py`: evidence replay DTOs,
    authorization mapping, product-safe errors, OpenAPI examples, operation
    events, and route registration.
15. `src/app/application/candidate_evidence_replay.py`: command validation and
    replay orchestration through the governed repository port.
16. `src/app/api/ai_governance.py`: AI explanation DTOs, authorization
    mapping, redacted response projection, product-safe errors, OpenAPI
    examples, and route registration.
17. `src/app/application/ai_governance.py`: persisted candidate snapshot
    lookup plus deterministic fallback/verifier orchestration without provider
    execution or durable persistence claims.
18. `src/app/api/conversion_governance.py`: conversion intent/outcome DTOs,
    authorization mapping, product-safe errors, idempotency-conflict handling,
    OpenAPI examples, and route registration.
19. `src/app/application/conversion_workflow.py`: application commands,
    idempotency payload construction, repository precheck, and domain
    invocation for conversion intent/outcome workflow.
20. `tests/integration/test_review_workflow_api.py`: certified API behavior
   evidence for lifecycle transition, review action, feedback, and conversion
   foundations.
21. `tests/integration/test_review_queue_api.py`: certified API behavior
    evidence for advisor queue projection.
22. `tests/integration/test_candidate_detail_api.py`: certified API behavior
    evidence for source-safe detail projection, workflow summaries, permission,
    missing candidate, and no-authority promotion.
23. `tests/integration/test_candidate_evidence_replay_api.py`: certified API
    behavior evidence for matched, stale-source, hash-mismatch, permission,
    missing candidate, invalid request, and no-authority replay posture.
24. `tests/integration/test_ai_governance_api.py`: certified API behavior
    evidence for AI fallback, verifier acceptance, blocked output, permission,
    missing candidate, invalid state, and forbidden metadata.

## Current Contract

The evaluate endpoint returns deterministic posture only:

1. `candidate_created` when all source evidence is current, entitlement is
   allowed, and source-reported cash weight meets the policy threshold,
2. `blocked` for stale/missing source evidence, missing cash weight, or
   entitlement denial,
3. `suppressed` for duplicate candidate evidence,
4. `not_eligible` when source-reported cash weight is below threshold.

The evaluate endpoint is permissioned by `idea.signal.evaluate` capability or
advisor role. The evaluate-and-persist endpoint is permissioned by
`idea.candidate.persist` and requires `Idempotency-Key`. Validation,
permission, and idempotency-conflict failures return product-safe Problem
Details.

The review-action endpoint is permissioned by `idea.review.record` plus one
recognized review actor role. The feedback endpoint is permissioned by
`idea.feedback.record` plus one recognized review actor role. Both endpoints
require upstream-authorized tenant/book/portfolio/client scope in the request
until the platform caller context carries scoped entitlements. Scope,
permission, missing candidate, idempotency conflict, and invalid candidate-state
failures return product-safe Problem Details.

The advisor review queue endpoint is permissioned by
`idea.review.queue.read` capability or advisor role. It requires a
timezone-aware `evaluatedAtUtc` query parameter, accepts optional
tenant/book/portfolio/client scope filters, excludes persisted candidates
outside the requested scope with `access_scope_mismatch`, and returns
product-safe Problem Details for permission or validation failures.

The candidate detail endpoint is permissioned by
`idea.candidate.detail.read` capability or advisor/operator role. It returns
source-safe details for an existing candidate and product-safe Problem Details
for permission, validation, or missing-candidate failures.

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
repository-backed foundation endpoints: process-local runtime reports `false`,
and `LOTUS_IDEA_DATABASE_URL` runtime reports `true`. The endpoints are
certified as API foundations but are not supported business features because
live source adapters, Workbench proof, data-product certification, runtime
trust telemetry, downstream realization proof, and supported-feature
registration are not implemented yet. The bounded read-only Gateway
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
3. Add Workbench review-surface proof before any UI or demo claim.
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

PR merge-gate evidence remains required before merge.

## Acceptance Gate

1. OpenAPI quality gate passes for every exposed route.
2. Endpoint certification passes for every exposed route.
3. Gateway contract tests prove source-owned `lotus-idea` truth is preserved
   before each Gateway route is claimed implemented; the first bounded
   read-only advisor queue and candidate detail routes satisfy this foundation
   rule but do not complete Workbench or supported-feature promotion.
4. No alias or stale endpoint remains without explicit time-boxed justification.
5. Supported-feature promotion remains blocked until live runtime,
   Gateway/Workbench, data-product, docs/wiki, and certification evidence all
   exist.
