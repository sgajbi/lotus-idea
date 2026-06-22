# Persistence And Migration Operations

Current posture: `lotus-idea` has internal in-memory repository behavior, a
versioned SQL schema, rollback contract, PostgreSQL migration execution CLI, a
tested PostgreSQL repository adapter foundation, and opt-in API repository
wiring through `LOTUS_IDEA_DATABASE_URL`. Accepted internal repository
mutations now also create source-safe pending outbox records in the active
repository snapshot, with internal retry/dead-letter delivery state semantics
over a publisher port and a source-safe HTTP broker-publisher adapter
foundation. It also has real PostgreSQL runtime
proof for high-cash API persistence/replay and the first internal review,
feedback, conversion, report evidence-pack, advisor queue, and migration
rollback/reapply recovery workflow path. Internal high-cash source-ingestion
orchestration now uses generated source-ingestion idempotency keys when needed
and classifies accepted, replayed, conflict, blocked, suppressed, and
not-eligible outcomes over the Core source port and repository port. It also
has a bounded run-once batch worker foundation with per-item idempotency and
batch decision counts for scheduling-ready internal execution.
`scripts/run_source_ingestion_worker.py` now provides a versioned
manifest-backed run-once CLI, and `make source-ingestion-worker-check`
validates the example manifest and source-safe check-only output contract
without calling Core or writing repository state. The PostgreSQL runtime proof
also covers internal source-ingestion
replay after repository reload and same-key changed-source conflict recovery.
`POST /api/v1/source-ingestion/run-once` now exposes that bounded
source-ingestion orchestration as a protected internal operator action. It
requires `idea.source-ingestion.run`, requires durable repository posture,
fails closed before mutation when manifest or Core configuration is absent or
invalid, and returns aggregate decision counts only.
Runtime API state remains process-local by default and reports
`durableStorageBacked=false` unless the database URL is configured. When
configured, repository-backed API responses and operation events report
`durableStorageBacked=true`, but this is still not production storage
certification, data-product certification, live source integration proof,
downstream realization proof, certified live broker runtime, or supported-feature
promotion.
`GET /api/v1/outbox-delivery/readiness` now exposes the outbox delivery
foundation as a certified internal operator diagnostic. It reports aggregate
outbox status counts, delivery-ready backlog, durable repository posture,
broker configuration posture, publisher-adapter presence, and certification
blockers. It does not expose event identifiers, aggregate identifiers, raw
idempotency keys, broker payloads, or downstream claims.
`POST /api/v1/outbox-delivery/run-once` now exposes the bounded run-once
delivery orchestration as a certified internal operator action. It requires
`idea.outbox-delivery.run`, fails closed without valid broker configuration,
returns aggregate counts only, and remains `not_certified` until live broker
runtime, downstream consumer contracts, platform mesh event certification,
Gateway/Workbench proof, and supported-feature promotion exist.
`POST /api/v1/idea-candidates/{candidateId}/evidence-replay` now exposes the
same evidence-hash replay posture as a certified internal operator API over the
active repository provider. It compares caller-supplied current source refs with
persisted source-ref evidence hashes and returns matched, stale-source,
hash-mismatch, expired, or missing-candidate posture without calling Core,
exporting raw source routes, granting downstream authority, or promoting a
supported feature.

## Current Contract

| Area | Current implementation truth | Boundary |
| --- | --- | --- |
| Repository provider | Process-local by default; PostgreSQL when `LOTUS_IDEA_DATABASE_URL` is configured | Not production recovery certification |
| Outbox delivery foundation | Source-safe records, retryable failure status, published status, dead-letter status, HTTP publisher adapter foundation, aggregate readiness diagnostic, and bounded run-once operator action for accepted internal mutations | No certified live broker runtime or downstream delivery |
| Source-ingestion worker check | Manifest plus source-safe check-only output contract | No Core call or repository write |
| Source-ingestion run-once API | Durable-repository-only operator action over the configured manifest and Core adapter | No live Core certification, scheduler proof, or supported product claim |
| Runtime proof | PostgreSQL 18 integration proof for internal workflow persistence/replay | Not supported-feature promotion |

```mermaid
flowchart LR
    Manifest["Versioned worker manifest"]
    Gate["make source-ingestion-worker-check"]
    Summary["Source-safe check-only summary"]
    Runner["run-once worker run mode"]
    Core["lotus-core"]
    Repo["Active idea repository"]

    Manifest --> Gate --> Summary
    Manifest --> Runner
    Runner -->|"configured runtime only"| Core
    Runner -->|"accepted/replayed/conflict decisions"| Repo
```

1. `migrations/001_idea_repository_foundation.sql` defines the future candidate,
   idempotency, lifecycle, audit, outbox, review, feedback, conversion, and
   report evidence-pack tables.
2. `migrations/001_idea_repository_foundation.rollback.sql` drops the same
   indexes and tables in dependency-safe reverse order.
3. `scripts/migration_contract_gate.py` blocks missing migration files, missing
   rollback posture, missing tables, missing indexes, missing JSONB payload
   columns, missing UTC timestamp columns, missing source relationships, and
   placeholder SQL.
4. `scripts/run_migrations.py` executes the migration plan against PostgreSQL
   when `LOTUS_IDEA_DATABASE_URL` is set, and dry-runs the apply/rollback plan
   for CI without requiring a database.
5. `src/app/domain/events.py` defines the outbox event envelope,
   deterministic event identity, status vocabulary, hashed idempotency
   fingerprint, forbidden payload-key guard, published transition, failed retry
   transition, and dead-letter transition. Accepted internal mutations append
   pending events; replay, conflict, not-found, blocked, suppressed, and
   not-eligible paths do not create duplicate outbox work.
6. `src/app/infrastructure/postgres_repository.py` implements the governed
   repository port surface over the schema. It materializes candidate,
   idempotency, lifecycle, audit, review, feedback, conversion, and report
   evidence-pack state plus pending outbox records through typed table columns
   plus JSONB snapshots, and rolls back the database transaction on flush
   failure.
7. `src/app/repository_state.py` selects the process-local in-memory repository
   by default, or a `PostgresIdeaRepository` backed by a psycopg connection with
   mapping rows when `LOTUS_IDEA_DATABASE_URL` is set. `src/app/api/repository_state.py`
   is only a compatibility shim and must not own concrete infrastructure wiring.
8. Repository-backed endpoints derive `durableStorageBacked` and
   `durable_storage_backed` operation-event labels from the active repository
   instead of hardcoding storage posture.
9. The evidence replay endpoint derives matched, stale-source, hash-mismatch,
   expired, and not-found posture from the active repository provider and emits
   bounded `candidate_evidence_replay` operation events.
10. `tests/integration/test_postgres_runtime_integration.py` applies the schema
   to a real PostgreSQL service, persists through the FastAPI
   evaluate-and-persist endpoint, reloads the repository provider, proves
   idempotency replay from database state, projects the advisor queue, records
   lifecycle transitions, review approval, feedback, conversion intent,
   conversion outcome, and report evidence-pack request state, validates the
   backing tables, proves internal Core-backed source-ingestion replay/conflict
   recovery through the PostgreSQL repository adapter, rolls back the schema,
   reapplies it, and proves the recovered API persistence contract is usable.
   GitHub PR Merge Gate and Main Releasability run this proof against
   `postgres:18-alpine`.
11. `src/app/application/source_ingestion.py` is the internal high-cash
   source-ingestion orchestration and bounded run-once batch worker foundation.
   It standardizes the future scheduler's generated idempotency key shape,
   per-item replay/conflict posture, batch decision counts, and non-mutating
   behavior for blocked, suppressed, and below-threshold Core source evidence.
12. `src/app/application/source_ingestion_worker.py` and
    `scripts/run_source_ingestion_worker.py` add a versioned manifest-backed
    run-once worker entrypoint. Check-only mode returns a product-safe
    validation summary, and `make source-ingestion-worker-check` enforces both
    manifest parseability and the exact source-safe check-only output contract;
    run mode requires a configured Core base URL and active repository
    provider. Both check-only and run summaries redact raw source payloads,
    portfolio ids, and raw idempotency keys. It is not a daemon,
    deploy-pipeline worker, or live Core certification.
13. `POST /api/v1/source-ingestion/run-once` adds the protected service
    boundary for the same source-ingestion batch foundation. It requires
    durable repository configuration and blocks before mutation when runtime
    inputs are missing or invalid.
14. `src/app/application/outbox_delivery.py` adds the first run-once delivery
    orchestration over a publisher port and the governed repository port. It
    reads pending and retryable failed events, marks accepted publications as
    published, marks rejected publications as failed for retry, dead-letters
    events at the configured retry limit, maps publisher exceptions to bounded
    `publisher_unavailable` failure reasons, and returns aggregate counts only.
    `InMemoryIdeaRepository` and `PostgresIdeaRepository` expose the same
    delivery-ready query and status-update contract. `src/app/ports/outbox_publisher.py`
    now owns the publisher protocol, and `src/app/infrastructure/outbox_publisher.py`
    implements a source-safe HTTP adapter that posts bounded event envelopes,
    propagates correlation/causation headers, and maps broker failures to
    bounded publisher reasons. This is internal recoverability and adapter
    foundation only; certified live broker runtime, downstream consumers, and
    event-publication support remain unimplemented.
15. `src/app/application/outbox_delivery_readiness.py` and
    `GET /api/v1/outbox-delivery/readiness` expose source-safe outbox
    delivery readiness for operators. The diagnostic reports aggregate status
    counts, adapter presence, and blockers only, so operators can see backlog
    posture without accessing event ids, aggregate ids, raw idempotency keys,
    source payloads, broker payloads, or downstream event contracts.
16. `POST /api/v1/outbox-delivery/run-once` exposes the same orchestration
    through the service boundary for operators. It does not mutate pending
    records when broker configuration is absent or invalid, and successful runs
    return only aggregate attempted, published, failed, dead-lettered, and
    skipped counts.

## Validation

Run the migration contract gate directly:

```powershell
make migration-contract-gate
make migration-execution-gate
make source-ingestion-worker-check
```

These gates are also part of `make lint`, `make check`, and `make ci`.

Run the run-once worker contract check without calling Core or writing state:

```powershell
make source-ingestion-worker-check
```

Run the worker manually only against an intended Core service and repository
provider:

```powershell
$env:LOTUS_IDEA_SOURCE_INGESTION_MANIFEST = "docs/examples/source-ingestion/high-cash-worker-manifest.example.json"
$env:LOTUS_CORE_BASE_URL = "http://localhost:8310"
.venv\Scripts\python.exe scripts/run_source_ingestion_worker.py
```

Run the opt-in PostgreSQL runtime proof locally with a disposable or dedicated
integration database:

```powershell
$env:LOTUS_IDEA_POSTGRES_INTEGRATION_URL = "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea"
$env:LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED = "1"
make postgres-integration-gate
```

When `LOTUS_IDEA_POSTGRES_INTEGRATION_URL` is not set, the proof test skips
locally. GitHub lanes set `LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED=1`, so a
missing database URL fails instead of silently skipping release evidence.

Apply or roll back against a configured PostgreSQL database:

```powershell
$env:LOTUS_IDEA_DATABASE_URL = "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea"
make migrate
make migrate-rollback
```

Run the API with the PostgreSQL adapter after migrations have been applied:

```powershell
$env:LOTUS_IDEA_DATABASE_URL = "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea"
uvicorn app.main:app --reload --port 8330
```

If the variable is unset or blank, the API uses the process-local repository.
That default is intentional for local foundation tests and must not be described
as durable storage.

## Unsupported Until Proven

Do not claim production storage readiness, production recovery, certified event
publication, data-product promotion, or supported business workflows until
later slices add:

1. deploy-pipeline migration evidence,
2. certified long-running scheduled source-ingestion worker proof against the real service,
3. live source adapter proof against a running Core service,
4. live broker runtime behavior, downstream consumer contract proof, and live
   event-publication evidence beyond the internal retry/dead-letter foundation,
5. data-product telemetry and platform mesh certification,
6. Gateway/Workbench/downstream proof for supported workflows,
7. updated endpoint certification, supported-feature, docs, wiki, and mesh
   posture.
