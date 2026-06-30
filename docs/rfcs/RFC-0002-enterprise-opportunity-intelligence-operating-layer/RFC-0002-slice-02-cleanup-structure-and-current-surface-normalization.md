# RFC-0002 Slice 02: Cleanup, Structure, And Current Surface Normalization

Status: Partially implemented - runtime composition providers, route metadata governance, API DTO base-model governance, shared signal DTO governance, API ProblemDetails boundary governance, API idempotency boundary governance, OpenAPI ProblemDetails example governance, protected private import boundary governance, public proof capability update APIs, and public PostgreSQL codec APIs normalized behind shared public surfaces with blocking enforcement retained

## Current Implementation Evidence

Implemented in this slice:

1. `src/app/runtime/repository_state.py` now owns the process-local idea
   repository provider and test reset hook for the current in-memory persistence
   foundation.
2. `src/app/api/idea_signals.py` no longer owns mutable repository state
   directly; the high-cash evaluate-and-persist route resolves the shared
   repository through the runtime composition module.
3. API DTOs and route handlers remain mapping and authorization surfaces only;
   domain evaluation, persistence, review, and queue behavior stay in
   application/domain modules.
4. Integration tests now reset the shared repository provider instead of
   importing a signal-route-local test hook, preparing review, feedback, and
   queue APIs to reuse the same candidate store without duplicating state.
5. Runtime composition providers for source ingestion, outbox publication, and
   downstream realization now live under `src/app/runtime/`, keeping
   environment wiring out of API route modules while concrete adapters remain
   in `src/app/infrastructure/`.
6. `src/app/runtime/README.md`, `src/app/README.md`,
   `quality/architecture_rules.md`, and the blocking
   `scripts/architecture_boundary_gate.py --mode blocking` rule define and
   enforce that runtime composition may wire repositories, source adapters,
   publishers, workers, and proof generators but must not import API routes,
   HTTP DTOs, FastAPI, or Starlette.
7. `src/app/api/runtime_dependencies.py` now owns the API-layer facade for
   runtime composition helpers used by route modules. API routes no longer
   import `app.runtime` directly, and the blocking architecture-boundary gate
   now fails any route that bypasses this facade.
8. `src/app/api/route_metadata.py` now owns the shared route-registration
   metadata `TypedDict` for API modules. Non-signal route modules and
   `app.api.signal_api_support` use the same metadata contract, and
   `make api-route-metadata-gate` blocks future local `RouteMetadata` or
   `SignalRouteMetadata` clones.
9. Workflow and operator routes plus `app.main` exception handlers now use
   `app.api.problem_details` for product-safe 400/403/404/409/503 OpenAPI
   response examples and runtime response helpers. `make
   api-problem-details-boundary-gate` blocks API route modules and the app
   entrypoint from importing low-level `app.errors` directly, and
   `make openapi-problem-details-example-gate` blocks public `ProblemDetails`
   responses without examples.
10. Mutating workflow routes now use `app.api.idempotency` for shared
    `Idempotency-Key` blank-key validation. `make
    api-idempotency-boundary-gate` blocks future route-local validator clones
    while preserving the existing request-failure semantics.
11. API DTOs that need camel-case aliases now use shared
    `app.api.base_model.CamelModel`; `make api-camel-model-boundary-gate`
    blocks future route-local `CamelModel` or `ConfigDict(populate_by_name=True)`
    clones. This is API design modularity only and does not introduce a runtime
    service split.
12. Shared signal-family DTOs now live in `app.api.signal_models` instead of
    the concrete `app.api.idea_signals` route module. The extracted models cover
    source refs, review access scope, source-ref responses, and candidate
    summary responses reused by the caller-supplied signal family routes and
    evidence replay route. `make api-signal-model-boundary-gate` blocks future
    imports of those shared DTOs from `app.api.idea_signals`. This is API design
    modularity only; it does not create a separately scalable signal
    microservice or promote signal APIs as supported features.
13. Cross-module callers now use public `app.domain` exports for domain
    invariants. `make private-import-boundary-gate` blocks direct imports of
    private `app.domain.*` helpers across `src`, `tests`, and `scripts`.
14. Implementation-proof readiness now uses public
    `app.application.implementation_proof_capability_updates` functions for
    blocker clearance and capability readiness construction. The same
    `make private-import-boundary-gate` target blocks reintroducing private
    imports from that shared proof helper module. This is design modularity
    inside the existing `lotus-idea` service; it does not create a separately
    scalable runtime microservice or promote proof-readiness support.
15. `src/app/infrastructure/postgres_repository.py` now consumes public
    `app.infrastructure.postgres_codecs` APIs for row access, JSON object
    decoding, datetime decoding, and domain JSON serialization. The same
    `make private-import-boundary-gate` target blocks new cross-module imports
    of private PostgreSQL codec helpers, keeping the durable repository adapter
    on an explicit design-modularity boundary without changing the runtime
    deployment model or database schema.

Validation evidence from the cleanup slice:

1. `.venv\Scripts\python.exe -m ruff check src\app\api\idea_signals.py src\app\api\repository_state.py tests\integration\test_high_cash_signal_api.py`
2. `.venv\Scripts\python.exe -m pytest tests\integration\test_high_cash_signal_api.py tests\unit\test_service_contract.py -q`
3. `make architecture-boundary-gate`
4. `make test-unit UNIT_TESTS=tests/unit/test_ci_enforcement_contract.py`
5. `.venv\Scripts\python.exe -m pytest tests\unit\test_ci_enforcement_contract.py -q`
6. `.venv\Scripts\python.exe -m ruff check scripts\architecture_boundary_gate.py src\app\api tests\unit\test_ci_enforcement_contract.py`
7. `.venv\Scripts\python.exe scripts\api_route_metadata_gate.py`
8. `.venv\Scripts\python.exe -m pytest tests\unit\test_ci_enforcement_contract.py -q`
9. `.venv\Scripts\python.exe scripts\openapi_problem_details_example_gate.py`
10. `.venv\Scripts\python.exe -m pytest tests\unit\test_api_problem_details.py tests\unit\test_ci_enforcement_contract.py -q`
11. `.venv\Scripts\python.exe scripts\api_problem_details_boundary_gate.py`
12. `.venv\Scripts\python.exe scripts\private_import_boundary_gate.py`
13. `.venv\Scripts\python.exe -m pytest tests\unit\test_private_import_boundary_gate.py tests\unit\test_ci_enforcement_contract.py tests\unit\test_missing_suitability_signal_evaluation.py -q`
14. `.venv\Scripts\python.exe -m pytest tests\unit\test_private_import_boundary_gate.py tests\unit\test_implementation_proof_readiness.py tests\unit\test_implementation_proof_readiness_gateway_discovery.py tests\unit\test_implementation_proof_readiness_gateway_workbench.py -q`
15. `.venv\Scripts\python.exe -m ruff check src\app\infrastructure\postgres_codecs.py src\app\infrastructure\postgres_repository.py scripts\private_import_boundary_gate.py tests\unit\test_private_import_boundary_gate.py tests\unit\test_postgres_repository.py`
16. `.venv\Scripts\python.exe -m pytest tests\unit\test_private_import_boundary_gate.py tests\unit\test_postgres_repository.py -q`
17. `.venv\Scripts\python.exe scripts\api_idempotency_boundary_gate.py`
18. `.venv\Scripts\python.exe -m pytest tests\unit\test_api_idempotency.py tests\unit\test_ci_enforcement_contract.py -q`
19. `make api-camel-model-boundary-gate`
20. `.venv\Scripts\python.exe -m pytest tests\unit\test_api_base_model.py tests\unit\test_ci_enforcement_contract.py -q`
21. `.venv\Scripts\python.exe -m ruff check src\app\api scripts\api_camel_model_boundary_gate.py tests\unit\test_api_base_model.py tests\unit\test_ci_enforcement_contract.py`
22. `make api-signal-model-boundary-gate`
23. `.venv\Scripts\python.exe -m pytest tests\unit\test_api_signal_models.py tests\unit\test_ci_enforcement_contract.py -q`
24. `.venv\Scripts\python.exe -m ruff check src\app\api\signal_models.py src\app\api\idea_signals.py src\app\api\allocation_drift_signals.py src\app\api\bond_maturity_signals.py src\app\api\candidate_evidence_replay.py src\app\api\concentration_risk_signals.py src\app\api\drawdown_review_signals.py src\app\api\high_volatility_signals.py src\app\api\low_income_signals.py src\app\api\missing_benchmark_signals.py src\app\api\missing_risk_profile_signals.py src\app\api\missing_suitability_signals.py src\app\api\underperformance_signals.py scripts\api_signal_model_boundary_gate.py tests\unit\test_api_signal_models.py tests\unit\test_ci_enforcement_contract.py`

## Remaining Work

The broader cleanup slice is not complete. Remaining work includes:

1. continued removal of scaffold placeholders as each product surface becomes
   implementation-backed,
2. continued route-module normalization as candidate lifecycle, review,
   feedback, queue, conversion, downstream realization, and operator readiness
   surfaces grow,
3. continued cleanup of remaining application helpers and adapter-internal
   persistence codec details as each boundary becomes measured and low-noise,
4. documentation/wiki/context synchronization for each material repository
   structure change,
5. periodic dead-code, duplicate-vocabulary, and unsupported-claim checks before
   supported-feature promotion.

## Outcome

Normalize the repository before adding business behavior so the implementation
starts with clean modules, vocabulary, docs, and test structure.

## Required Work

1. Replace generic scaffold placeholders with service-specific truth.
2. Establish domain/application/ports/infrastructure boundaries for
   opportunities, evidence, scoring, review, conversion, and AI orchestration.
3. Remove dead or misleading placeholder docs, sample claims, aliases, or
   duplicated vocabulary.
4. Align docs, wiki, supported-features, and repository context with current
   foundation-only truth.

## Acceptance Gate

1. No business feature is claimed as supported.
2. Domain code remains framework-free.
3. API layers contain no business logic.
4. Docs and wiki state planned versus supported posture consistently.
