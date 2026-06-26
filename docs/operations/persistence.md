# Persistence And Migration Operations

Current posture: `lotus-idea` has internal in-memory repository behavior, a
versioned SQL schema, rollback contract, PostgreSQL migration execution CLI, a
tested PostgreSQL repository adapter foundation, and opt-in API repository
wiring through `LOTUS_IDEA_DATABASE_URL`. Accepted internal repository
mutations now also create source-safe pending outbox records in the active
repository snapshot, with internal retry/dead-letter delivery state semantics
over a publisher port and a source-safe HTTP broker-publisher adapter
foundation. It also has real PostgreSQL runtime
proof for high-cash API persistence/replay, source-safe AI explanation lineage
acceptance/replay/conflict, and the first internal review, feedback,
conversion, report evidence-pack, advisor queue, and migration
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
Source-safe AI explanation lineage is now part of the repository contract and
the real PostgreSQL runtime proof. It
records request identity, candidate identity, evidence packet identity,
evidence hash, workflow-pack identity, posture, verifier outcome, fallback
state, bounded output summary ids, actor, timestamps, and
no-downstream-authority posture without storing prompts, provider payloads,
raw source routes, trace ids, correlation ids, portfolio ids, client ids, or
free-form source payloads.
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
`scripts/generate_durable_repository_proof.py` and
`make durable-repository-proof-contract-gate` now provide a source-safe proof
artifact for aggregate RFC implementation-readiness evidence. The artifact
cites migration contracts, the PostgreSQL adapter, and the GitHub PostgreSQL
runtime proof lane; it does not connect to a database, replace
`make postgres-integration-gate`, or make runtime endpoints report durable
storage unless `LOTUS_IDEA_DATABASE_URL` is actually configured.
`GET /api/v1/outbox-delivery/readiness` now exposes the outbox delivery
foundation as a certified internal operator diagnostic. It reports aggregate
outbox status counts, delivery-ready backlog, durable repository posture,
broker configuration posture, publisher-adapter presence, and certification
blockers. It does not expose event identifiers, aggregate identifiers, raw
idempotency keys, broker payloads, or downstream claims.
`scripts/generate_outbox_broker_proof.py` and
`make outbox-broker-proof-contract-gate` now provide a source-safe outbox
broker proof artifact for aggregate RFC implementation-readiness evidence. The
artifact cites the implemented outbox delivery orchestration, publisher port,
HTTP publisher adapter, readiness endpoint, run-once endpoint, and
configured-publisher API proof. It clears only aggregate broker configuration
and broker runtime-proof blockers; it does not certify external publication,
platform mesh event delivery, downstream consumer contracts, or supported
features.
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
| Outbox delivery foundation | Source-safe records, retryable failure status, published status, dead-letter status, HTTP publisher adapter foundation, aggregate readiness diagnostic, bounded run-once operator action, and source-safe outbox broker proof artifact for accepted internal mutations | No certified external publication, platform mesh event delivery, or downstream consumer support |
| Source-ingestion worker check | Manifest plus source-safe check-only output contract | No Core call or repository write |
| Source-ingestion run-once API | Durable-repository-only operator action over the configured manifest and Core adapter | No live Core certification, scheduler proof, or supported product claim |
| AI explanation lineage | Source-safe request/result lineage through the repository port, PostgreSQL migration `002`, and PostgreSQL runtime API proof | No `lotus-ai` runtime execution, prompt/provider telemetry, Workbench proof, or supported product claim |
| Runtime proof | PostgreSQL 18 integration proof for internal workflow persistence/replay and AI explanation lineage accepted/replayed/conflict behavior | Not supported-feature promotion |
| Durable repository proof artifact | Source-safe aggregate readiness artifact citing migration, adapter, and CI runtime proof evidence | Not live runtime configuration or production storage certification |

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
3. `migrations/002_ai_explanation_lineage.sql` adds the source-safe AI
   explanation lineage table and candidate, workflow-pack, and posture/time
   indexes. `002_ai_explanation_lineage.rollback.sql` removes the same objects.
4. `scripts/migration_contract_gate.py` blocks missing migration files, missing
   rollback posture, missing tables, missing indexes, missing JSONB payload
   columns, missing UTC timestamp columns, missing source relationships, and
   placeholder SQL.
5. `scripts/run_migrations.py` executes the migration plan against PostgreSQL
   when `LOTUS_IDEA_DATABASE_URL` is set, and dry-runs the apply/rollback plan
   for CI without requiring a database.
6. `src/app/domain/events.py` defines the outbox event envelope,
   deterministic event identity, status vocabulary, hashed idempotency
   fingerprint, forbidden payload-key guard, published transition, failed retry
   transition, and dead-letter transition. Accepted internal mutations append
   pending events; replay, conflict, not-found, blocked, suppressed, and
   not-eligible paths do not create duplicate outbox work.
7. `src/app/infrastructure/postgres_repository.py` implements the governed
   repository port surface over the schema. It materializes candidate,
   idempotency, lifecycle, audit, review, feedback, conversion, and report
   evidence-pack state, AI explanation lineage records, plus pending outbox
   records through typed table columns plus JSONB snapshots, and rolls back the
   database transaction on flush failure.
8. `src/app/runtime/repository_state.py` selects the process-local in-memory
   repository by default, or a `PostgresIdeaRepository` backed by a psycopg
   connection with mapping rows when `LOTUS_IDEA_DATABASE_URL` is set. Runtime
   composition stays outside the API layer and app root.
9. Repository-backed endpoints derive `durableStorageBacked` and
   `durable_storage_backed` operation-event labels from the active repository
   instead of hardcoding storage posture.
10. The evidence replay endpoint derives matched, stale-source, hash-mismatch,
   expired, and not-found posture from the active repository provider and emits
   bounded `candidate_evidence_replay` operation events.
11. `tests/integration/test_postgres_runtime_integration.py` applies the schema
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
12. `src/app/application/source_ingestion.py` is the internal high-cash
   source-ingestion orchestration and bounded run-once batch worker foundation.
   It standardizes the future scheduler's generated idempotency key shape,
   per-item replay/conflict posture, batch decision counts, and non-mutating
   behavior for blocked, suppressed, and below-threshold Core source evidence.
13. `src/app/application/source_ingestion_worker.py` and
    `scripts/run_source_ingestion_worker.py` add a versioned manifest-backed
    run-once worker entrypoint. Check-only mode returns a product-safe
    validation summary, and `make source-ingestion-worker-check` enforces both
    manifest parseability and the exact source-safe check-only output contract;
    run mode requires configured Core query and query-control-plane URLs, or
    the legacy compatibility Core base URL, plus an active repository provider.
    Both check-only and run summaries redact raw source payloads,
    portfolio ids, and raw idempotency keys. It is not a daemon,
    deploy-pipeline worker, or live Core certification.
14. `POST /api/v1/source-ingestion/run-once` adds the protected service
    boundary for the same source-ingestion batch foundation. It requires
    durable repository configuration and blocks before mutation when runtime
    inputs are missing or invalid.
15. `src/app/application/outbox_delivery.py` adds the first run-once delivery
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
16. `src/app/application/outbox_delivery_readiness.py` and
    `GET /api/v1/outbox-delivery/readiness` expose source-safe outbox
    delivery readiness for operators. The diagnostic reports aggregate status
    counts, adapter presence, and blockers only, so operators can see backlog
    posture without accessing event ids, aggregate ids, raw idempotency keys,
    source payloads, broker payloads, or downstream event contracts.
17. `POST /api/v1/outbox-delivery/run-once` exposes the same orchestration
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
$env:LOTUS_CORE_QUERY_BASE_URL = "http://localhost:8201"
$env:LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL = "http://localhost:8202"
.venv\Scripts\python.exe scripts/run_source_ingestion_worker.py
```

Use `LOTUS_CORE_BASE_URL` only as a compatibility fallback for older
single-base Core stacks.

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
4. downstream consumer contract proof, platform mesh event certification, and
   production event-publication evidence beyond the bounded outbox broker proof artifact,
5. data-product telemetry and platform mesh certification,
6. Gateway/Workbench/downstream proof for supported workflows,
7. updated endpoint certification, supported-feature, docs, wiki, and mesh
   posture.
