# RFC-0002 Slice 06: Persistence, Replay, Idempotency, And Audit

Status: Partially implemented - internal persistence plus high-cash orchestration foundation only

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

Not implemented yet:

1. database-backed durable persistence,
2. migrations and rollback automation,
3. database-backed source-ingestion workers,
4. stateful API routes and OpenAPI certification,
5. integration or e2e persistence proof over durable storage,
6. data-product certification,
7. supported-feature promotion.

## Migration And Rollback Posture

This slice intentionally does not introduce a database schema. No migration is
required for the current internal in-memory persistence foundation. The first
database-backed persistence slice must add explicit migrations, rollback
posture, integration tests, and recovery evidence before any API or
data-product claim is promoted.

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

GitHub PR validation and wiki publication remain required before mainline
closure.
