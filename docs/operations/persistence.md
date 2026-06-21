# Persistence And Migration Operations

Current posture: `lotus-idea` has internal in-memory repository behavior plus a
versioned SQL schema, rollback contract, and PostgreSQL migration execution CLI
for the future durable repository. Runtime API state is still process-local and
must report `durableStorageBacked=false` until a database repository adapter and
integration/e2e storage proof exist.

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

Do not claim durable database persistence, recovery, data-product promotion, or
supported business workflows until a later slice adds:

1. a database-backed adapter behind `src/app/ports/idea_repository.py`,
2. integration/e2e proof against real storage,
3. deploy-pipeline migration evidence,
4. rollback/recovery evidence,
5. updated endpoint certification, supported-feature, docs, wiki, and mesh
   posture.
