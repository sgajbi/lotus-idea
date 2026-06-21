# RFC-0002 Slice 02: Cleanup, Structure, And Current Surface Normalization

Status: Partially implemented - API repository state normalized for shared route use

## Current Implementation Evidence

Implemented in this slice:

1. `src/app/api/repository_state.py` now owns the process-local idea repository
   provider and test reset hook for the current in-memory persistence
   foundation.
2. `src/app/api/idea_signals.py` no longer owns mutable repository state
   directly; the high-cash evaluate-and-persist route resolves the shared
   repository through the API state module.
3. API DTOs and route handlers remain mapping and authorization surfaces only;
   domain evaluation, persistence, review, and queue behavior stay in
   application/domain modules.
4. Integration tests now reset the shared repository provider instead of
   importing a signal-route-local test hook, preparing review, feedback, and
   queue APIs to reuse the same candidate store without duplicating state.

Validation evidence from the cleanup slice:

1. `.venv\Scripts\python.exe -m ruff check src\app\api\idea_signals.py src\app\api\repository_state.py tests\integration\test_high_cash_signal_api.py`
2. `.venv\Scripts\python.exe -m pytest tests\integration\test_high_cash_signal_api.py tests\unit\test_service_contract.py -q`

## Remaining Work

The broader cleanup slice is not complete. Remaining work includes:

1. continued removal of scaffold placeholders as each product surface becomes
   implementation-backed,
2. route-module normalization for candidate lifecycle, review, feedback, queue,
   and conversion APIs when those routes are added,
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
