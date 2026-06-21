# Persistence And Migration Operations

Current posture: `lotus-idea` has internal in-memory repository behavior, a
versioned SQL schema, rollback contract, PostgreSQL migration execution CLI, and
a tested PostgreSQL repository adapter foundation. Runtime API state is still
process-local and must report `durableStorageBacked=false` until the adapter is
wired behind API dependencies and proven against a real PostgreSQL service in
integration/e2e storage checks.

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

## Unsupported Until Proven

Do not claim API-level durable database persistence, recovery, data-product
promotion, or supported business workflows until a later slice adds:

1. API dependency wiring from `src/app/api/repository_state.py` to the
   PostgreSQL adapter,
2. integration/e2e proof against a real PostgreSQL service,
3. deploy-pipeline migration evidence,
4. rollback/recovery evidence against the real service,
5. updated endpoint certification, supported-feature, docs, wiki, and mesh
   posture.
