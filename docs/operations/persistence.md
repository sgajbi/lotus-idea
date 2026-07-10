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
API idempotency, same-key replay, distinct-key request-id conflict, and the first internal review, feedback,
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
the real PostgreSQL runtime proof. The API requires `Idempotency-Key` before
lineage writes: same-key/same-request calls replay without duplicate rows,
same-key/different-request calls return governed idempotency conflict, and
distinct-key request-id replay/conflict remains governed by the lineage store. It
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
Runtime API state is profile-aware. `LOTUS_IDEA_RUNTIME_PROFILE` defaults to
`local`; only `local` and `test` allow process-local repository writes. `demo`,
`staging`, and `production` require `LOTUS_IDEA_DATABASE_URL`; otherwise
`/health/ready` returns degraded posture and mutating API routes fail closed
with `durable_repository_not_configured` before in-memory mutation. When
configured, repository-backed API responses and operation events report
`durableStorageBacked=true`, but this is still not production storage
certification, data-product certification, live source integration proof,
downstream realization proof, certified live broker runtime, or supported-feature
promotion.
The PostgreSQL adapter now applies normal mutating repository operations as
row-delta inserts and candidate-row updates inside the repository transaction
instead of deleting and reinserting unrelated repository tables. This preserves
independent candidate, review, conversion, report evidence, AI lineage, outbox,
and downstream-submission rows when separate mutations are applied from the same
starting snapshot. Review, feedback, and conversion-intent replay/conflict
prechecks now use a bounded idempotency-key lookup plus candidate-detail
projection instead of whole-store snapshot hydration. It is still not production
storage certification, and future adapter work should continue moving hot
precheck/replay paths toward database-native conditional reads and writes where
that reduces contention.

Review and feedback resources also have identity independent of the HTTP
`Idempotency-Key`. Equivalent `reviewId` or `feedbackId` submissions under a
new key replay without candidate, audit, or outbox duplication. Changed
candidate, evidence, actor, action/outcome, reason, lineage, or timestamp returns
`review_identity_conflict`. PostgreSQL claims the resource primary key before
candidate mutation and retries one collision from fresh state; see
`docs/architecture/review-feedback-identity-and-idempotency.md`.

Conversion outcomes follow the same resource-versus-transport distinction but
add a source-owned lifecycle. `conversionOutcomeId` and a contiguous
`sourceEventVersion` identify one intent stream; equivalent new-key retries do
not duplicate outcome, audit, or outbox rows. PostgreSQL atomically protects
both outcome ID and intent/version. Migration 006 snapshots contradictory
legacy streams to `idea_conversion_outcome_quarantine` without deleting their
source rows, and readiness excludes those streams. See
`docs/architecture/conversion-outcome-identity-and-lifecycle.md`.

All seven outbox mutation families now preserve required correlation and trace
metadata from API request through application command, repository port,
durable row, and publisher envelope. Optional causation identifies a distinct
parent event only and is never substituted for transport trace. Migration
`007_outbox_event_lineage` backfills legacy rows without deletion and enforces
safe identifier and origin/causation combinations. Equivalent idempotent
replays retain the original event lineage even when the retry has a new trace.
See `docs/architecture/outbox-event-lineage.md` for the operator and consumer
contract.
Review and feedback mutation governance now uses the persisted candidate access
scope after bounded candidate lookup. Request `accessScope` remains request
shape, but it is not the runtime authorization target; trusted caller
entitlement headers and persisted candidate scope are the enforced source of
truth.
`scripts/generate_durable_repository_proof.py` and
`make durable-repository-proof-contract-gate` now provide a source-safe proof
artifact for aggregate RFC implementation-readiness evidence. The artifact
cites migration contracts, the PostgreSQL adapter, the bounded PostgreSQL
advisor review-queue projection, and the GitHub PostgreSQL runtime proof lane;
it can clear the aggregate durable-repository and repository-side
queue-pagination proof blockers. It does not connect to a database, replace
`make postgres-integration-gate`, certify production storage, or make runtime
endpoints report durable storage unless `LOTUS_IDEA_DATABASE_URL` is actually
configured.
`GET /api/v1/outbox-delivery/readiness` now exposes the outbox delivery
foundation as a certified internal operator diagnostic. It reports aggregate
outbox status counts, delivery-ready backlog, retry-deferred failed rows that
are still cooling down, durable repository posture, broker configuration
posture, publisher-adapter presence, and certification blockers. It does not
expose event identifiers, aggregate identifiers, raw idempotency keys, broker
payloads, or downstream claims.
`contracts/outbox-events/lotus-idea-outbox-events.v1.json` and
`make outbox-event-contract-gate` now define and enforce the repo-owned internal
outbox event contract. Runtime construction, repository replay, contract-gate
alignment, the PostgreSQL foundation schema, and
`003_outbox_event_contract_constraints.sql` all fail closed unless the event
family, aggregate type, and schema version match the v1 contract.
The same gate now requires correlation, trace, lineage origin, API mapper
coverage, PostgreSQL wiring, and correct publisher trace semantics.
`scripts/generate_outbox_broker_proof.py` and
`make outbox-broker-proof-contract-gate` provide a source-safe outbox broker
proof artifact for aggregate RFC implementation-readiness evidence. The artifact
cites the implemented outbox delivery orchestration, publisher port, HTTP
publisher adapter, readiness endpoint, run-once endpoint, event contract, and
configured-publisher API proof. It clears only aggregate broker configuration
and broker runtime-proof blockers; it does not certify external publication,
platform mesh event publication proof, downstream consumer runtime proof, or
supported features.
`contracts/outbox-events/lotus-idea-outbox-consumers.v1.json` and
`make outbox-consumer-contract-gate` now declare governed downstream consumers
for Gateway, Advise, Manage, and Report without certifying runtime consumption.
Readiness therefore reports `downstream_consumer_runtime_proof_missing` instead
of a missing-contract blocker until a bounded consumer runtime proof artifact is
supplied.
`scripts/generate_outbox_consumer_runtime_proof.py` and
`make outbox-consumer-runtime-proof-contract-gate` now provide the bounded
consumer runtime proof artifact consumed by aggregate RFC implementation
readiness. The artifact validates declared consumer coverage, consumed event
type coverage, and source-authority boundaries, clearing only
`downstream_consumer_runtime_proof_missing`. It does not certify external
publication, platform mesh event publication, Gateway/Workbench behavior,
downstream delivery, or supported features.
`scripts/generate_outbox_platform_mesh_event_publication_proof.py` and
`make outbox-platform-mesh-event-publication-proof-contract-gate` now provide
the bounded outbox platform mesh event publication proof artifact consumed by
aggregate RFC implementation readiness. The artifact validates repo-owned
source-safe event contracts plus sibling platform source-manifest/catalog
onboarding evidence, clearing only
`platform_mesh_event_publication_proof_missing`. It does not certify external
broker publication, downstream delivery, Gateway/Workbench behavior,
client-ready publication, or supported features.
`POST /api/v1/outbox-delivery/run-once` now exposes the bounded run-once
delivery orchestration as a certified internal operator action. It requires
`idea.outbox-delivery.run` plus `Idempotency-Key`, binds the operator run
identity to safe request parameters and caller subject, replays same-key /
same-request retries without mutation, rejects same-key / different-request
reuse with product-safe conflict, fails closed without valid broker
configuration, returns aggregate counts plus a source-safe
`operatorRunReference` only, closes the route-owned broker publisher after
execution begins, and remains `not_certified` until live broker runtime,
downstream delivery evidence, certified external broker publication,
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
| Repository provider | `local`/`test` may use process-local writes; `demo`/`staging`/`production` require PostgreSQL through `LOTUS_IDEA_DATABASE_URL` and fail closed when it is absent | Not production recovery certification |
| Disaster recovery | Versioned 15-table contract, real logical backup/restore, provider-restore validator, replay/fencing/no-mutation proof, recovery-aware write guard, and weekly attested CI drill | Logical evidence has `pitrProof=false`; managed physical base-backup/WAL topology and exercise remain required for production certification |
| Outbox delivery foundation | Source-safe records, durable retry scheduling with first/last failure timing and due retry eligibility, retryable failure status, published status, dead-letter status, HTTP publisher adapter foundation, repo-owned outbox event and downstream consumer contracts, aggregate readiness diagnostic, bounded run-once operator action, source-safe outbox broker proof artifact, bounded downstream consumer runtime proof artifact, and bounded outbox platform mesh event publication proof artifact | No certified external broker publication, downstream delivery, Gateway/Workbench behavior, client-ready publication, or supported-feature promotion |
| Source-ingestion worker check | Manifest plus source-safe check-only output contract | No Core call or repository write |
| Source-ingestion run-once API | Durable-repository-only operator action over the configured manifest and Core adapter | No live Core certification, scheduler proof, or supported product claim |
| AI explanation lineage | Source-safe request/result lineage through the repository port, PostgreSQL migration `002`, API `Idempotency-Key` replay/conflict protection, and PostgreSQL runtime API proof | No `lotus-ai` runtime execution, prompt/provider telemetry, Workbench proof, or supported product claim |
| Runtime proof | PostgreSQL 18 integration proof for internal workflow persistence/replay, row-delta repository mutation, and AI explanation lineage idempotency/replay/conflict behavior | Not production storage certification or supported-feature promotion |
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
   `003_outbox_event_contract_constraints.sql` retrofits named outbox event
   family, aggregate-type, and schema-version constraints onto existing
   `idea_outbox_event` tables.
6. `src/app/domain/events.py` defines the outbox event envelope,
   deterministic event identity, status vocabulary, hashed idempotency
   fingerprint, forbidden payload-key guard, governed event-family allowlist,
   v1 schema-version guard, fixed candidate aggregate-type guard, published
   transition, failed retry transition, and dead-letter transition. Accepted
   internal mutations append pending events; replay, conflict, not-found,
   blocked, suppressed, and not-eligible paths do not create duplicate outbox
   work.
7. `src/app/infrastructure/postgres_repository.py` implements the governed
   repository port surface over the schema. It materializes candidate,
   idempotency, lifecycle, audit, review, feedback, conversion, and report
   evidence-pack state, AI explanation lineage records, plus pending outbox
   records through typed table columns plus JSONB snapshots, and rolls back the
   database transaction on flush failure.
8. `src/app/runtime/settings.py` owns runtime profile semantics. `local` and
   `test` may use the process-local in-memory repository; `demo`, `staging`,
   and `production` require `LOTUS_IDEA_DATABASE_URL` and fail closed before
   write-capable routes mutate memory. Runtime composition stays outside the
   API layer and app root.
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
    bounded publisher reasons. The broker publisher uses the shared downstream
    HTTP client resource model with explicit timeout, connection-pool,
    keepalive, and pool-timeout limits from
    `LOTUS_IDEA_OUTBOX_BROKER_TIMEOUT_SECONDS`,
    `LOTUS_IDEA_OUTBOX_BROKER_MAX_CONNECTIONS`,
    `LOTUS_IDEA_OUTBOX_BROKER_MAX_KEEPALIVE_CONNECTIONS`, and
    `LOTUS_IDEA_OUTBOX_BROKER_POOL_TIMEOUT_SECONDS`; invalid values fail
    closed before publication is attempted. The outbox-delivery run-once API
    closes the route-owned broker publisher after execution begins so repeated
    operator runs do not leak HTTP client resources. Cleanup failures emit
    source-safe `suppressed` operation events and do not replace completed,
    replayed, conflict, or bounded blocked run-once responses. This is internal
    recoverability and adapter foundation only; certified live broker runtime,
    downstream consumers, and event-publication support remain unimplemented.
16. `src/app/application/outbox_delivery_readiness.py` and
    `GET /api/v1/outbox-delivery/readiness` expose source-safe outbox
    delivery readiness for operators. The diagnostic reports aggregate status
    counts, adapter presence, and blockers only, so operators can see backlog
    posture without accessing event ids, aggregate ids, raw idempotency keys,
    source payloads, broker payloads, or downstream event contracts.
    PostgreSQL-backed readiness uses repository-side aggregate queries against
    `idea_outbox_event` for status counts, expired leases, and delivery-ready
    count instead of materializing the whole idea repository snapshot.
    Downstream realization readiness now follows the same pattern for workflow
    counts: PostgreSQL reads `idea_conversion_intent`,
    `idea_conversion_outcome`, and `idea_report_evidence_pack_request`
    directly instead of hydrating unrelated repository state.
    Downstream submission idempotency replay/conflict checks now use a direct
    PostgreSQL primary-key lookup against `idea_downstream_submission`, so
    duplicate downstream submission requests no longer hydrate candidate,
    outbox, conversion, report evidence-pack, or AI-lineage state before
    adapter execution.
    Review, feedback, and conversion-intent idempotency prechecks use the same
    bounded PostgreSQL posture: a direct `idea_idempotency_record` lookup by
    key followed by the candidate-detail projection for the associated
    candidate only. They avoid whole-store candidate, outbox,
    downstream-submission, and unrelated workflow hydration before returning
    replay or conflict decisions.
    Runtime trust telemetry preview and snapshot diagnostics also use a
    repository-side PostgreSQL aggregate projection over candidate and workflow
    tables, so ordinary operator reads avoid hydrating audit, outbox,
    downstream-submission, lifecycle-history, idempotency, or AI-lineage state.
17. `POST /api/v1/outbox-delivery/run-once` exposes the same orchestration
    through the service boundary for operators. It requires `Idempotency-Key`,
    records the operator run identity before claiming events, does not mutate
    pending records when broker configuration is absent or invalid, and
    successful runs return only aggregate attempted, published, failed,
    dead-lettered, and skipped counts plus a source-safe
    `operatorRunReference`.

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

If the variable is unset or blank, only `local` and `test` profiles may use the
process-local repository for writes. Production-like profiles degrade readiness
and return `durable_repository_not_configured` for write-capable routes.
That default is intentional for local foundation tests and must not be described
as durable storage.

## Governed Dead-Letter Recovery

GitHub issue `#337` adds a narrow recovery path over the existing outbox state
machine. A source-safe inspection projection and per-reference re-drive check a
dedicated operator capability, idempotency identity, event family, schema
version, and one-attempt poison-message ceiling before recording an append-only
audit snapshot and acquiring a new lease.

Migration `004_outbox_dead_letter_recovery` commits the audit row and lease
transition together. In-memory and PostgreSQL adapters share the same port.
Successful publication preserves retry count, failure reason, and first/last
failure timestamps; failed re-drive returns directly to quarantine without a
scheduled retry. PostgreSQL maps the opaque support reference through an exact
immutable SHA-256 expression index and locks one matching event across
dead-letter, leased, or terminal posture; arbitrary recent-row scans are
forbidden by the recovery contract gate. The real PostgreSQL lane proves this
lookup after repository reload and durable same-key replay. See
`docs/operations/outbox-dead-letter-recovery.md`.

## Unsupported Until Proven

Do not claim production storage readiness, production recovery, certified event
publication, data-product promotion, or supported business workflows until
later slices add:

1. approved managed-provider physical base-backup/WAL topology, encrypted
   backup evidence, and a successful PITR cutover exercise,
2. deploy-pipeline migration evidence,
3. certified long-running scheduled source-ingestion worker proof against the real service,
4. live source adapter proof against a running Core service,
5. certified external broker publication and production event-publication
   evidence beyond the bounded outbox proof artifacts,
6. data-product telemetry and platform mesh certification,
7. Gateway/Workbench/downstream proof for supported workflows,
8. updated endpoint certification, supported-feature, docs, wiki, and mesh
   posture.

Migration rollback, repository replay, outbox re-drive, and logical dump
restore are distinct controls. Use
`docs/runbooks/postgres-disaster-recovery.md` for the governed DR procedure.
