# RFC-0002 Slice 06: Persistence, Replay, Idempotency, And Audit

Status: Partially implemented - internal persistence plus schema/rollback contract foundation only

## Outcome

Persist candidate and evidence state with replayable, hash-backed, audit-ready
behavior.

## Required Work

1. Add persistence for candidate, evidence packet, lifecycle history, review
   state, feedback, suppression, conversion state, and audit events.
2. Add idempotency for signal ingestion, candidate creation, review decisions,
   AI explanation requests, and conversion intents.
3. Add replay or rebuild behavior with evidence hashes and source refs.
4. Add migration and rollback posture where persistence is introduced.

## Acceptance Gate

1. Duplicate requests do not create duplicate candidates.
2. Replay returns matching evidence hash or a clear stale-source posture.
3. Every mutating action writes an audit event.
4. Persistence tests cover conflict, replay, expiry, and recovery cases.

## Implementation Evidence

Implemented first-wave internal scope:

1. `src/app/domain/persistence.py` defines immutable candidate persistence
   records, lifecycle history entries, idempotent candidate persistence
   decisions, replay status vocabulary, evidence hash helpers, repository
   snapshots, and an `InMemoryIdeaRepository` internal adapter.
2. Candidate persistence now evaluates idempotency keys and payload hashes
   before writing. Matching keys and matching payloads replay the existing
   candidate record; matching keys with different payloads return conflict; a
   duplicate candidate identity under a different key returns
   `duplicate_candidate` instead of creating another record.
3. Evidence replay compares current source refs with the persisted source-ref
   hash and returns explicit matched, stale-source, hash-mismatch, expired, and
   not-found posture.
4. Candidate persistence and lifecycle transitions write safe bounded
   `AuditEvent` records. Audit events reject sensitive attribute keys and now
   validate event identity, actor, outcome, and timezone-aware event time.
5. Repository snapshots allow internal recovery of candidate records,
   idempotency records, and idempotency-to-candidate mappings for replay tests.
6. `src/app/application/high_cash_signal.py` now adds internal high-cash
   evaluate-and-persist orchestration over the Slice 06 repository contract.
   Created high-cash candidates are persisted with deterministic idempotency
   payloads, matching requests replay, changed payloads conflict, and blocked,
   suppressed, or not-eligible evaluations remain non-mutating.
7. The same orchestration shape exists for the Core source-port flow, but it
   still does not promote live source support while Core cash-weight authority
   remains governed by `sgajbi/lotus-core#430`.
8. `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` now exposes the
   caller-supplied high-cash evaluate-and-persist path as a certified internal
   API foundation with `Idempotency-Key`, `idea.candidate.persist`, product-safe
   conflict errors, and explicit `durableStorageBacked=false` posture.
9. `src/app/application/candidate_lifecycle.py` and
   `src/app/api/candidate_lifecycle.py` now expose certified internal candidate
   lifecycle transition orchestration over the same repository contract.
   `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions` requires
   `idea.candidate.lifecycle.transition` plus `Idempotency-Key`, applies the
   canonical domain lifecycle transition graph, writes lifecycle history and
   audit evidence, returns accepted/replayed/not-found/conflict/invalid-state
   posture, and keeps `durableStorageBacked=false` and
   `supportedFeaturePromoted=false`.
10. `src/app/ports/idea_repository.py` now centralizes the repository workflow
    protocols used by application orchestration. Candidate persistence,
    candidate snapshots, lifecycle mutation, review and feedback mutation,
    conversion mutation, report evidence-pack requests, and AI explanation
    reads depend on the ports layer instead of declaring local per-use-case
    repository protocols. `tests/unit/test_repository_port_boundary.py`
    prevents future application modules from reintroducing scattered
    repository protocol declarations before the durable adapter lands.
11. `migrations/001_idea_repository_foundation.sql` and
    `migrations/001_idea_repository_foundation.rollback.sql` now define the
    first versioned database schema and rollback contract for future candidate,
    idempotency, lifecycle, audit, review, feedback, conversion, and report
    evidence-pack repository state. `scripts/migration_contract_gate.py`
    validates required tables, indexes, JSONB payload columns, UTC timestamp
    columns, source relationships, and rollback statements so future agents
    cannot add persistence-shaped work without governed reversibility evidence.

Not implemented yet:

1. runtime database-backed repository adapter,
2. migration execution automation in local/deploy runtime,
3. database-backed source-ingestion workers,
4. database-backed stateful API routes,
5. integration or e2e persistence proof over durable storage,
6. data-product certification,
7. supported-feature promotion.

## Migration And Rollback Posture

The slice now introduces the first explicit schema and rollback contract but
does not execute migrations or wire runtime API state to a database. The
contract is intentionally ahead of the durable adapter so schema, rollback,
indexing, and relationship posture become CI-blocking before any database-backed
claim is made. The next durable persistence slice must execute this migration
against a real database, add a repository adapter behind
`src/app/ports/idea_repository.py`, prove rollback/recovery behavior, and keep
API responses truthful until `durableStorageBacked=true` is backed by
integration and e2e evidence.

## Validation

Targeted validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_high_cash_application.py tests\unit\test_idea_persistence.py -q`
   passed with `19 passed` for the new orchestration and persistence replay
   coverage.
2. `.venv\Scripts\python.exe -m ruff check src\app\application\high_cash_signal.py tests\unit\test_high_cash_application.py`
   passed.
3. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini` passed.
4. Prior Slice 06 validation also covered
   `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_idempotency_audit.py -q`
   with `11 passed`.
5. `make check` passed with lint, format, CI contract, monetary/no-sensitive
   guards, data-mesh contract gate, supported-feature gate,
   endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
   `174` unit tests.
6. `make ci` passed with `13` integration tests, `2` e2e tests, `174` unit
   tests under coverage, coverage gate at `99.37%`, and dependency audit
   reporting no known vulnerabilities.
7. Later endpoint foundation validation covered the certified
   evaluate-and-persist API with OpenAPI and endpoint-certification gates, but
   database-backed persistence remains planned.
8. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_service_contract.py tests\integration\test_review_workflow_api.py -q`
   passed with `29 passed` after adding idempotent lifecycle transition
   repository and API coverage.
9. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` and
   `.venv\Scripts\python.exe scripts\openapi_quality_gate.py` passed after
   adding lifecycle route certification evidence.
10. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `189` unit tests.
11. `make ci` passed with `39` integration tests, `2` e2e tests, `189` unit
    tests under coverage, coverage gate at `99.14%`, and dependency audit
    reporting no known vulnerabilities.
12. `make docker-build` passed for `backend-service:ci-test`.
13. `.venv\Scripts\python.exe -m ruff check src\app\application src\app\ports\idea_repository.py tests\unit\test_repository_port_boundary.py`
    passed after centralizing repository workflow protocols.
14. `.venv\Scripts\python.exe -m pytest tests\unit\test_repository_port_boundary.py tests\unit\test_high_cash_application.py tests\unit\test_review_queue_application.py tests\unit\test_review_workflow_application.py tests\unit\test_idea_persistence.py -q`
    passed with `43 passed`.
15. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini src\app\application src\app\ports\idea_repository.py`
    passed.
16. `.venv\Scripts\python.exe scripts\migration_contract_gate.py` passed after
    adding the first versioned schema/rollback contract.
17. `.venv\Scripts\python.exe -m pytest tests\unit\test_migration_contract_gate.py tests\unit\test_ci_enforcement_contract.py -q`
    passed with `14 passed`.
18. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, migration contract gate,
    supported-feature gate, endpoint-certification gate, typecheck,
    architecture boundary, OpenAPI, and `223` unit tests.
19. `make ci` passed with `59` integration tests, `2` e2e tests, `223` unit
    tests under coverage, coverage gate at `99.17%`, and dependency audit
    reporting no known vulnerabilities.

GitHub PR validation and wiki publication remain required before mainline
closure.
