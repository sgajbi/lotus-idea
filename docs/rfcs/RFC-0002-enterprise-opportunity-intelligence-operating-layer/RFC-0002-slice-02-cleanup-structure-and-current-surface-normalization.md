# RFC-0002 Slice 02: Cleanup, Structure, And Current Surface Normalization

Status: Partially implemented - runtime composition providers normalized behind the API runtime dependency facade and architecture-boundary enforcement retained

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

Validation evidence from the cleanup slice:

1. `.venv\Scripts\python.exe -m ruff check src\app\api\idea_signals.py src\app\api\repository_state.py tests\integration\test_high_cash_signal_api.py`
2. `.venv\Scripts\python.exe -m pytest tests\integration\test_high_cash_signal_api.py tests\unit\test_service_contract.py -q`
3. `make architecture-boundary-gate`
4. `make test-unit UNIT_TESTS=tests/unit/test_ci_enforcement_contract.py`
5. `.venv\Scripts\python.exe -m pytest tests\unit\test_ci_enforcement_contract.py -q`
6. `.venv\Scripts\python.exe -m ruff check scripts\architecture_boundary_gate.py src\app\api tests\unit\test_ci_enforcement_contract.py`

## Remaining Work

The broader cleanup slice is not complete. Remaining work includes:

1. continued removal of scaffold placeholders as each product surface becomes
   implementation-backed,
2. continued route-module normalization as candidate lifecycle, review,
   feedback, queue, conversion, downstream realization, and operator readiness
   surfaces grow,
3. documentation/wiki/context synchronization for each material repository
   structure change,
4. periodic dead-code, duplicate-vocabulary, and unsupported-claim checks before
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
