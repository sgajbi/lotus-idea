# Persistence And Migration Operations

Current posture: `lotus-idea` has internal in-memory repository behavior, a
versioned SQL schema, rollback contract, PostgreSQL migration execution CLI, a
tested PostgreSQL repository adapter foundation, and opt-in API repository
wiring through `LOTUS_IDEA_DATABASE_URL`. Runtime API state remains
process-local by default and reports `durableStorageBacked=false` unless the
database URL is configured. When configured, repository-backed API responses and
operation events report `durableStorageBacked=true`, but this is still not
data-product certification, live source integration proof, downstream
realization proof, or supported-feature promotion.

## Current Contract

1. `migrations/001_idea_repository_foundation.sql` defines the future candidate,
   idempotency, lifecycle, audit, review, feedback, conversion, and report
   evidence-pack tables.
2. `migrations/001_idea_repository_foundation.rollback.sql` drops the same
   indexes and tables in dependency-safe reverse order.
3. `scripts/migration_contract_gate.py` blocks missing migration files, missing
   rollback posture, missing tables, missing indexes, missing JSONB payload
   columns, missing UTC timestamp columns, missing source relationships, and
   placeholder SQL.
4. `scripts/run_migrations.py` executes the migration plan against PostgreSQL
   when `LOTUS_IDEA_DATABASE_URL` is set, and dry-runs the apply/rollback plan
   for CI without requiring a database.
5. `src/app/infrastructure/postgres_repository.py` implements the governed
   repository port surface over the schema. It materializes candidate,
   idempotency, lifecycle, audit, review, feedback, conversion, and report
   evidence-pack state through typed table columns plus JSONB snapshots, and
   rolls back the database transaction on flush failure.
6. `src/app/repository_state.py` selects the process-local in-memory repository
   by default, or a `PostgresIdeaRepository` backed by a psycopg connection with
   mapping rows when `LOTUS_IDEA_DATABASE_URL` is set. `src/app/api/repository_state.py`
   is only a compatibility shim and must not own concrete infrastructure wiring.
7. Repository-backed endpoints derive `durableStorageBacked` and
   `durable_storage_backed` operation-event labels from the active repository
   instead of hardcoding storage posture.

## Validation

Run the migration contract gate directly:

```powershell
make migration-contract-gate
make migration-execution-gate
```

Both gates are also part of `make lint`, `make check`, and `make ci`.

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

Do not claim production storage readiness, recovery, data-product promotion, or
supported business workflows until later slices add:

1. integration/e2e proof against a real PostgreSQL service,
2. deploy-pipeline migration evidence,
3. rollback/recovery evidence against the real service,
4. data-product telemetry and platform mesh certification,
5. Gateway/Workbench/downstream proof for supported workflows,
6. updated endpoint certification, supported-feature, docs, wiki, and mesh
   posture.
