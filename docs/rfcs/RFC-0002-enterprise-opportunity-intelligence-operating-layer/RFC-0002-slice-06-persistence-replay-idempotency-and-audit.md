# RFC-0002 Slice 06: Persistence, Replay, Idempotency, And Audit

Status: Partially implemented - internal persistence, source-safe outbox retry/dead-letter delivery foundation, certified evidence replay API, schema/rollback contract, migration execution, PostgreSQL adapter, opt-in API repository wiring, first PostgreSQL runtime workflow proof, source-ingestion replay/conflict recovery proof, manifest-backed run-once ingestion worker CLI/check, and migration rollback/reapply recovery proof

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
   decisions, replay status vocabulary, evidence hash helpers, source-safe
   pending outbox snapshots, repository snapshots, and an
   `InMemoryIdeaRepository` internal adapter. `src/app/domain/events.py`
   defines the typed outbox event envelope, status vocabulary, deterministic
   event identity, hashed idempotency fingerprint, and forbidden payload-key
   guard for source/client-sensitive fields.
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
8. `src/app/application/source_ingestion.py` now adds an internal
   high-cash source-ingestion orchestration wrapper over the Core source port
   and repository port. It generates source-ingestion idempotency keys, maps
   repository and evaluator results into explicit accepted, replayed, conflict,
   duplicate-candidate, blocked, suppressed, and skipped-not-eligible decisions,
   and keeps blocked, suppressed, and below-threshold evaluations non-mutating.
   Core-backed idempotency payloads now include generated candidate and
   source-signal identity, so same-key source changes conflict instead of being
   treated as an equivalent replay. It also exposes a bounded run-once batch
   worker foundation with maximum item validation, per-item replay/conflict
   posture, batch decision counts, and correlation/trace propagation through
   the Core source port. This is not a daemon, deploy-pipeline worker, live Core
   certification, or supported ingestion product.
9. `src/app/application/source_ingestion_worker.py` and
   `scripts/run_source_ingestion_worker.py` now provide a versioned
   manifest-backed run-once worker entrypoint. `--check-only` validates the
   manifest and returns a product-safe summary without Core calls, repository
   writes, portfolio ids, or raw idempotency keys. Run mode requires an
   explicit Core base URL or `LOTUS_CORE_BASE_URL` and emits decision counts,
   candidate ids when candidates are created, and idempotency-key presence only,
   without source payloads, portfolio ids in result items, raw idempotency keys,
   or supported-feature promotion.
10. `make source-ingestion-worker-check` now validates the example manifest and
    source-safe check-only output contract in the lint path. It blocks raw
    portfolio identifiers, source routes, source payloads, raw idempotency
    keys, and candidate identifiers from check-only output.
11. `scripts/ci_contract_gate.py` blocks future removal or downgrade of the
    source-ingestion worker contract gate from local quality enforcement.
12. `POST /api/v1/idea-signals/high-cash/evaluate-and-persist` now exposes the
   caller-supplied high-cash evaluate-and-persist path as a certified internal
   API foundation with `Idempotency-Key`, `idea.candidate.persist`, product-safe
   conflict errors, and repository-derived `durableStorageBacked` posture.
13. `src/app/application/candidate_lifecycle.py` and
   `src/app/api/candidate_lifecycle.py` now expose certified internal candidate
   lifecycle transition orchestration over the same repository contract.
   `POST /api/v1/idea-candidates/{candidateId}/lifecycle-transitions` requires
   `idea.candidate.lifecycle.transition` plus `Idempotency-Key`, applies the
   canonical domain lifecycle transition graph, writes lifecycle history and
   audit evidence, returns accepted/replayed/not-found/conflict/invalid-state
   posture, and keeps `supportedFeaturePromoted=false`.
14. `src/app/application/candidate_evidence_replay.py` and
    `src/app/api/candidate_evidence_replay.py` now expose evidence replay
    posture as a certified internal operator API at
    `POST /api/v1/idea-candidates/{candidateId}/evidence-replay`. The route
    requires `idea.candidate.evidence.replay` plus operator role, compares
    caller-supplied current source refs with persisted evidence hashes, returns
    matched, stale-source, hash-mismatch, expired, or not-found posture, emits
    bounded operation events, and does not call Core, export raw source routes,
    grant downstream authority, or promote a supported feature.
15. `src/app/ports/idea_repository.py` now centralizes the repository workflow
    protocols used by application orchestration. Candidate persistence,
    candidate snapshots, evidence replay, lifecycle mutation, review and
    feedback mutation, conversion mutation, report evidence-pack requests, and
    AI explanation reads depend on the ports layer instead of declaring local
    per-use-case repository protocols. `tests/unit/test_repository_port_boundary.py`
    prevents future application modules from reintroducing scattered repository
    protocol declarations outside the governed runtime provider.
16. Accepted internal repository mutations now append pending outbox records for
    candidate persistence, lifecycle transitions, review decisions, feedback,
    conversion intents, conversion outcomes, and report evidence-pack requests.
    Replayed, conflict, not-found, blocked, suppressed, and not-eligible paths
    remain non-publishing and do not create duplicate outbox work. This is an
    internal outbox foundation only; no external broker, Gateway event, platform
    mesh event, or downstream publication is claimed.
17. `src/app/domain/events.py`, `src/app/domain/persistence.py`,
    `src/app/application/outbox_delivery.py`, and
    `src/app/ports/idea_repository.py` now add the first internal outbox
    delivery semantics. Delivery-ready reads include pending events and
    retryable failed events below the configured retry limit. Status updates can
    mark an event published, failed for retry, or dead-lettered when the retry
    limit is reached. Publisher exceptions are mapped to bounded
    `publisher_unavailable` failure reason codes, failure reasons reject
    source/client-sensitive marker names, and run summaries expose aggregate
    counts only. `PostgresIdeaRepository` persists the same status transitions
    through the existing `idea_outbox_event` table. This is not external broker
    publication, downstream delivery, Gateway event publication, data-product
    certification, or supported-feature promotion.
18. `migrations/001_idea_repository_foundation.sql` and
    `migrations/001_idea_repository_foundation.rollback.sql` now define the
    first versioned database schema and rollback contract for future candidate,
    idempotency, lifecycle, audit, outbox, review, feedback, conversion, and
    report evidence-pack repository state. `scripts/migration_contract_gate.py`
    validates required tables, indexes, JSONB payload columns, UTC timestamp
    columns, source relationships, and rollback statements so future agents
    cannot add persistence-shaped work without governed reversibility evidence.
19. `src/app/infrastructure/migrations.py` and `scripts/run_migrations.py` now
    provide a PostgreSQL migration execution path. `make migration-execution-gate`
    dry-runs apply and rollback plans in CI without needing a database, while
    `make migrate` and `make migrate-rollback` execute the same plans when
    `LOTUS_IDEA_DATABASE_URL` points to a PostgreSQL database. The Docker image
    now includes `migrations/` so runtime migration commands have the same SQL
    contract as local development.
20. `src/app/infrastructure/postgres_repository.py` now implements the first
    PostgreSQL repository adapter behind the governed port surface. The adapter
    hydrates repository snapshots from the schema, delegates domain decisions to
    the same in-memory repository contract, flushes typed table rows and JSONB
    snapshots transactionally, persists pending outbox records across reload,
    and rolls back when a database flush fails.
    `tests/unit/test_postgres_repository.py` proves candidate persistence,
    idempotency replay, lifecycle history, audit events, review decisions,
    feedback, conversion intent/outcome, report evidence-pack requests, pending
    outbox hydration, and rollback behavior with a fake Postgres cursor.
21. `src/app/infrastructure/postgres_codecs.py` now isolates PostgreSQL JSON
    serialization/deserialization helpers from the repository adapter so future
    persistence growth does not erode source-file maintainability gates.
22. `src/app/repository_state.py` now selects the process-local
    `InMemoryIdeaRepository` by default and selects `PostgresIdeaRepository`
    when `LOTUS_IDEA_DATABASE_URL` is configured. psycopg connections use
    mapping rows so the adapter receives the row shape it enforces. The
    `src/app/api/repository_state.py` module remains a compatibility shim so
    concrete infrastructure wiring stays out of the API layer.
23. Repository-backed API routes now derive `durableStorageBacked` responses and
    `durable_storage_backed` operation-event labels from the active repository
    instead of hardcoding storage posture. Default local/test runtime remains
    process-local and continues to report `durableStorageBacked=false`; a
    configured PostgreSQL runtime reports `durableStorageBacked=true` for the
    repository-backed foundation routes.
24. `tests/integration/test_postgres_runtime_integration.py` now runs the
    first real PostgreSQL runtime proof. It applies the governed schema,
    persists a high-cash candidate through
    `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`, reloads the
    repository provider to force a new database connection, proves idempotency
    replay from PostgreSQL state, projects the advisor queue from the reloaded
    repository, transitions the candidate to review-ready state, records review
    approval, advisor feedback, report conversion intent, conversion outcome,
    and report evidence-pack request state, validates the backing workflow
    tables, proves internal Core-backed source-ingestion replay and same-key
    changed-source conflict recovery through the PostgreSQL repository adapter,
    rolls the schema back, reapplies it, and proves the recovered API
    persistence contract is usable. `make postgres-integration-gate` is the
    repo-native command, and PR Merge Gate / Main Releasability run it against
    `postgres:18-alpine` with
    `LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED=1`.

Not implemented yet:

1. deploy-pipeline migration execution proof against a real PostgreSQL service,
2. scheduled daemon/deploy source-ingestion workers,
3. live source adapter and live source-ingestion proof against a running Core service,
4. data-product certification,
5. external broker/downstream consumer proof,
6. Gateway/Workbench/downstream proof,
7. supported-feature promotion.

## Migration And Rollback Posture

The slice now introduces the first explicit schema, rollback contract,
executable migration path, adapter, opt-in runtime repository wiring, and a real
PostgreSQL API persistence/replay proof plus migration rollback/reapply
recovery proof. CI dry-runs the apply and rollback plans and separately runs the
PostgreSQL runtime proof in PR/main lanes. Real service execution still requires
`LOTUS_IDEA_DATABASE_URL`. This is intentionally ahead of production storage
promotion so schema, rollback, indexing, relationship posture, execution command
shape, adapter behavior, runtime selection, and the first durable replay path
become CI-visible before any supported database-backed product claim is made.
The current proof now also exercises the first internal review, queue,
conversion, report evidence-pack workflow, pending outbox persistence, and
internal source-ingestion replay/conflict recovery path against PostgreSQL. The
source-ingestion application layer now has a bounded run-once batch primitive
plus a versioned manifest-backed run-once CLI and check-only gate. The outbox
foundation now includes internal retry and dead-letter status semantics through
the repository port, but external broker publication and downstream consumer
contracts remain unimplemented. The next durable persistence slices must still
prove scheduled daemon/deploy worker behavior, deploy-pipeline migration
evidence, live Core source-adapter behavior against that service, broker
adapter behavior, downstream consumer contracts, and event-publication proof
before any event publication claim, and keep API responses truthful:
`durableStorageBacked=true` means the configured repository adapter is active,
not that the idea product is data-mesh certified or supported.

## Validation

Current slice validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_high_cash_application.py tests\unit\test_idea_persistence.py -q`
   passed with `19 passed` for the new orchestration and persistence replay
   coverage.
2. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion.py tests\unit\test_high_cash_application.py -q`
   passed with `24 passed` for the internal source-ingestion orchestration,
   generated idempotency key, replay, conflict, blocked, suppressed, and
   skipped-not-eligible coverage.
3. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion.py -q`
   passed with `11 passed` after adding bounded run-once batch worker coverage
   for duplicate replay, changed-source conflict, batch decision counts,
   timezone validation, maximum item enforcement, and correlation propagation.
4. `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion_worker.py tests\unit\test_source_ingestion.py tests\unit\test_ci_enforcement_contract.py -q`
   passed with `30 passed` after adding manifest parsing, unknown-key
   rejection, product-safe summary, CLI check-only, and CI-contract coverage.
5. `make source-ingestion-worker-check` passed, validating
   `docs/examples/source-ingestion/high-cash-worker-manifest.example.json` and
   the source-safe check-only output contract without Core calls or repository
   writes.
6. `.venv\Scripts\python.exe scripts\ci_contract_gate.py` passed after adding
   the source-ingestion worker check target to the required local lint
   contract.
7. `.venv\Scripts\python.exe -m pytest tests\integration\test_postgres_runtime_integration.py -q`
   skips locally when `LOTUS_IDEA_POSTGRES_INTEGRATION_URL` is not configured;
   the suite now includes internal source-ingestion replay/conflict recovery
   proof for GitHub PR/Main PostgreSQL lanes where `postgres:18-alpine` is
   configured.
8. `make check` passed with lint, format, CI contract, maintainability,
   monetary/no-sensitive guards, implementation-truth, data-mesh,
   migration, supported-feature, endpoint-certification, typecheck,
   architecture, OpenAPI, and `265` unit tests.
9. `make ci` passed with `60` integration tests, `4` local PostgreSQL skips,
   `2` e2e tests, `265` unit tests under coverage, coverage gate at `99.00%`,
   and dependency audit reporting no known vulnerabilities.
10. `.venv\Scripts\python.exe -m pytest tests\integration\test_candidate_evidence_replay_api.py tests\integration\test_api_operation_events.py -q`
    passed with `9 passed` after adding the certified evidence replay API,
    matched/stale/hash-mismatch/not-found/permission/validation coverage, and
    bounded operation-event proof.
11. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py -q`
    passed with `17 passed` after adding source-safe pending outbox records,
    replay/conflict non-publication coverage, snapshot recovery proof, and
    forbidden payload-key coverage.
12. `.venv\Scripts\python.exe -m pytest tests\unit\test_postgres_repository.py tests\unit\test_migration_contract_gate.py -q`
    passed with `9 passed` after adding outbox schema enforcement and
    PostgreSQL outbox round-trip coverage.
13. `.venv\Scripts\python.exe scripts\migration_contract_gate.py`,
    `.venv\Scripts\python.exe scripts\run_migrations.py --direction apply --dry-run`,
    and `.venv\Scripts\python.exe scripts\run_migrations.py --direction rollback --dry-run`
    passed with the outbox table/index contract included in the baseline
    migration.
14. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_outbox_delivery.py tests\unit\test_postgres_repository.py -q`
    passed with `29 passed` after adding internal outbox retry/dead-letter
    delivery state, bounded publisher exception handling, sensitive
    failure-reason rejection, and PostgreSQL outbox status persistence coverage.
15. `.venv\Scripts\python.exe -m ruff check src\app\domain\events.py src\app\domain\persistence.py src\app\application\outbox_delivery.py src\app\ports\idea_repository.py src\app\infrastructure\postgres_repository.py tests\unit\test_idea_persistence.py tests\unit\test_outbox_delivery.py tests\unit\test_postgres_repository.py`
    passed.
16. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini src\app\domain\events.py src\app\domain\persistence.py src\app\application\outbox_delivery.py src\app\ports\idea_repository.py src\app\infrastructure\postgres_repository.py`
    passed.

Prior Slice 06 validation:

1. `.venv\Scripts\python.exe -m ruff check src\app\application\high_cash_signal.py tests\unit\test_high_cash_application.py`
   passed.
2. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini` passed.
3. Prior persistence validation also covered
   `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_idempotency_audit.py -q`
   with `11 passed`.
4. `make check` passed with lint, format, CI contract, monetary/no-sensitive
   guards, data-mesh contract gate, supported-feature gate,
   endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
   `257` unit tests.
5. `make ci` passed with `13` integration tests, `2` e2e tests, `174` unit
   tests under coverage, coverage gate at `99.37%`, and dependency audit
   reporting no known vulnerabilities.
6. Later endpoint foundation validation covered the certified
   evaluate-and-persist API with OpenAPI and endpoint-certification gates; at
   that point database-backed persistence remained planned.
7. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_service_contract.py tests\integration\test_review_workflow_api.py -q`
   passed with `29 passed` after adding idempotent lifecycle transition
   repository and API coverage.
8. `.venv\Scripts\python.exe scripts\endpoint_certification_gate.py` and
   `.venv\Scripts\python.exe scripts\openapi_quality_gate.py` passed after
   adding lifecycle route certification evidence.
9. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `189` unit tests.
10. `make ci` passed with `39` integration tests, `2` e2e tests, `189` unit
    tests under coverage, coverage gate at `99.14%`, and dependency audit
    reporting no known vulnerabilities.
11. `make docker-build` passed for `backend-service:ci-test`.
12. `.venv\Scripts\python.exe -m ruff check src\app\application src\app\ports\idea_repository.py tests\unit\test_repository_port_boundary.py`
    passed after centralizing repository workflow protocols.
13. `.venv\Scripts\python.exe -m pytest tests\unit\test_repository_port_boundary.py tests\unit\test_high_cash_application.py tests\unit\test_review_queue_application.py tests\unit\test_review_workflow_application.py tests\unit\test_idea_persistence.py -q`
    passed with `43 passed`.
14. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini src\app\application src\app\ports\idea_repository.py`
    passed.
15. `.venv\Scripts\python.exe scripts\migration_contract_gate.py` passed after
    adding the first versioned schema/rollback contract.
16. `.venv\Scripts\python.exe -m pytest tests\unit\test_migration_contract_gate.py tests\unit\test_ci_enforcement_contract.py -q`
    passed with `14 passed`.
17. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, migration contract gate,
    supported-feature gate, endpoint-certification gate, typecheck,
    architecture boundary, OpenAPI, and `223` unit tests.
18. `make ci` passed with `59` integration tests, `2` e2e tests, `223` unit
    tests under coverage, coverage gate at `99.17%`, and dependency audit
    reporting no known vulnerabilities.
19. `.venv\Scripts\python.exe scripts\run_migrations.py --direction apply --dry-run`
    and `.venv\Scripts\python.exe scripts\run_migrations.py --direction rollback --dry-run`
    passed with `20` planned statements each.
20. `.venv\Scripts\python.exe -m pytest tests\unit\test_migration_execution.py tests\unit\test_migration_contract_gate.py tests\unit\test_ci_enforcement_contract.py -q`
    passed with `19 passed`.
21. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini src\app\infrastructure\migrations.py scripts\run_migrations.py`
    passed.
22. `.venv\Scripts\python.exe -m pip_audit -r requirements\shared-runtime.lock.txt -r requirements\ci-tooling.lock.txt`
    passed with no known vulnerabilities after adding
    `psycopg[binary]==3.3.4`.
23. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, migration contract gate,
    migration execution dry-run gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `228` unit tests.
24. `make ci` passed with `59` integration tests, `2` e2e tests, `228` unit
    tests under coverage, coverage gate at `99.08%`, and dependency audit
    reporting no known vulnerabilities.
25. `make docker-build` passed for `backend-service:ci-test` after adding
    `migrations/` to the Docker image.
26. `make postgres-integration-gate` passed against a disposable
    `postgres:18-alpine` service on `localhost:55434` with `2 passed` after
    broadening the proof to cover high-cash persistence/replay, advisor queue
    projection, lifecycle transitions, review approval replay, feedback,
    report conversion intent replay, conversion outcome, report evidence-pack
    request replay, and backing workflow table counts.
27. `make check` passed with lint, format, CI contract, monetary/no-sensitive
    guards, data-mesh contract gate, migration contract gate,
    migration execution dry-run gate, supported-feature gate,
    endpoint-certification gate, typecheck, architecture boundary, OpenAPI, and
    `237` unit tests.
28. `make ci` passed with `60` integration tests, `2` local PostgreSQL skips,
    `2` e2e tests, `237` unit tests under coverage, coverage gate at `99.15%`,
    and dependency audit reporting no known vulnerabilities.
29. `make docker-build` passed for `backend-service:ci-test` after broadening
    the PostgreSQL runtime proof and synchronizing docs/wiki truth.

GitHub PR validation and wiki publication remain required before mainline
closure.
