# Migration Contract

- Service: lotus-idea
- Versioned migrations and rollback files live in `migrations/`.
- `make migration-contract-gate` is blocking through `make lint`, `make check`,
  and `make ci`.
- Every migration that introduces persistence shape must include a rollback
  file, required table/index coverage, source relationships, UTC timestamps, and
  JSONB payload columns where domain payload snapshots are stored.
- The first contract,
  `migrations/001_idea_repository_foundation.sql`, defines future durable idea
  repository state only. It does not by itself make API state database-backed.
