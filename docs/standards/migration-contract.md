# Migration Contract

- Service: lotus-idea
- Versioned migrations and rollback files live in `migrations/`.
- `make migration-contract-gate` is blocking through `make lint`, `make check`,
  and `make ci`.
- `make migration-execution-gate` dry-runs apply and rollback execution plans
  through `scripts/run_migrations.py` and is also blocking through `make lint`,
  `make check`, and `make ci`.
- `make migrate` and `make migrate-rollback` require `LOTUS_IDEA_DATABASE_URL`
  and execute the same plans against PostgreSQL.
- Every migration that introduces persistence shape must include a rollback
  file, required table/index coverage, source relationships, UTC timestamps, and
  JSONB payload columns where domain payload snapshots are stored.
- The first contract,
  `migrations/001_idea_repository_foundation.sql`, defines future durable idea
  repository state only. It does not by itself make API state database-backed.
- Migration 001 contract coverage includes downstream submission durability:
  `idea_downstream_submission`, `idx_idea_downstream_submission_resource`, and
  the request fingerprint, resource identity, source-authority, and submitted
  timestamp columns that support idempotent downstream realization posture.
