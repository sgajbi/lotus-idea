# Validation And CI

`lotus-idea` starts with the Lotus backend lane model:

1. Feature Lane for branch feedback.
2. PR Merge Gate for required merge readiness.
3. Main Releasability Gate for post-merge truth.
4. Merged PR Main Releasability Dispatch so rebase auto-merged PRs still
   generate post-merge release evidence on `main`.
5. Non-suppressed auto-merge token enforcement through `LOTUS_AUTOMERGE_TOKEN`;
   without that secret, use a human/release actor to rebase merge.

Repo-native validation commands:

```powershell
make check
make ci
make ci-contract-gate
make maintainability-gate
make implementation-truth-gate
make data-mesh-contract-gate
make migration-contract-gate
make migration-execution-gate
make postgres-integration-gate
make openapi-gate
make architecture-boundary-gate
make architecture-boundary-report
make quality-baseline
```

Baseline required checks include lint, format check, typecheck, architecture boundary enforcement,
maintainability thresholds, OpenAPI quality, implementation-truth gate, supported-feature gate, endpoint-certification gate,
unit tests, integration tests, e2e tests, data-mesh contract validation, migration contract validation, coverage gate,
safe migration execution dry-run validation, PostgreSQL runtime proof in PR/main GitHub lanes,
security audit, Docker build validation, bounded GitHub job timeouts, no soft-failed critical
jobs, and workflow lint.

Persistence adapter validation:

1. `tests/unit/test_postgres_repository.py` exercises the PostgreSQL repository
   adapter with a fake Postgres cursor across candidate persistence,
   idempotency replay, lifecycle history, audit events, review decisions,
   feedback, conversion intent/outcome, report evidence-pack requests, snapshot
   hydration, commit behavior, and rollback on flush failure.
2. `tests/unit/test_repository_state.py` proves repository provider selection:
   process-local by default, `PostgresIdeaRepository` when
   `LOTUS_IDEA_DATABASE_URL` is configured, psycopg mapping-row configuration,
   provider caching, durable-storage status, and connection close/reset
   behavior.
3. `tests/integration/test_high_cash_signal_api.py` pins route-level
   `durableStorageBacked` derivation with an injected durable repository so
   future changes cannot hardcode repository-backed API posture to `false`.
4. `tests/integration/test_postgres_runtime_integration.py` is the first real
   PostgreSQL runtime proof. GitHub PR Merge Gate and Main Releasability run it
   against `postgres:18-alpine` with
   `LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED=1`; local runs skip unless
   `LOTUS_IDEA_POSTGRES_INTEGRATION_URL` is configured. The proof covers
   high-cash persistence/replay plus the first advisor queue, lifecycle,
   review, feedback, conversion intent/outcome, and report evidence-pack
   request workflow path against real PostgreSQL state, plus schema
   rollback/reapply recovery.
5. Runtime API database wiring is opt-in and still requires deploy migration
   evidence, source-ingestion recovery proof, and mesh/support promotion evidence
   before any supported durable product claim.

The CI contract gate is blocking from day one. It prevents accidental removal of bank-buyable
controls from the Makefile or GitHub lanes, including least-privilege workflow permissions,
approved action-runtime majors, 99% combined coverage in merge/releasability lanes, Docker build
validation, SBOM/release evidence, endpoint certification, supported-feature promotion control,
data-mesh contract validation, migration contract validation, migration execution dry-run
validation, PostgreSQL runtime proof, workflow-dispatch access, non-suppressed auto-merge token
usage, merged-PR main-releasability dispatch, bounded job timeouts, no `continue-on-error: true`
in critical lanes, maintainability enforcement, implementation-truth enforcement, and source-safe local quality gates.

The maintainability gate blocks oversized Python files/functions in source, test, and script
trees. It is calibrated above the current baseline so new agentic work must split or refactor
large additions instead of normalizing hard-to-review modules.

The implementation-truth gate scans README, repository context, operations/demo docs, quality docs,
and wiki source for unqualified current-state claims that imply demo readiness, production support,
certification, live source ingestion, Gateway/Workbench support, or client-ready publication while
no supported feature is implemented. RFC target-state planning text is excluded; current-state
surfaces must describe unsupported, planned, blocked, or evidence-required posture explicitly. The
gate also blocks stale scaffold-era underclaims in demo documentation when current implementation
and CI evidence prove a stronger foundation, so future agent work cannot leave outdated scaffold
truth behind while adding real APIs or gates.

Data-mesh foundation checks:

1. repo-owned proposed producer and consumer declarations must exist,
2. mesh placeholder files must not exist in contract or operations paths,
3. planned trust telemetry must remain blocked and `not_certified`,
4. SLO, access, and evidence policies must be present before promotion work,
5. optional sibling platform catalog/source-manifest evidence is used to catch
   source-product drift or premature `lotus-idea` source-manifest inclusion,
6. platform mesh certification is required before any supported mesh claim.

The internal data-mesh-readiness endpoint is covered by OpenAPI, endpoint
certification, unit tests, and integration tests. Its passing checks certify the
diagnostic route only; they do not certify the data products it reports as
blocked.

CI warning policy:

1. use current approved action versions,
2. fix owned warning sources,
3. suppress only known upstream runner noise with an explicit rationale,
4. do not downgrade action versions to make logs quieter.

Branch hygiene policy:

1. after a PR is merged to `main`, delete the remote feature branch,
2. delete the corresponding local feature branch,
3. re-run branch audits before final closure,
4. keep no durable RFC/docs/wiki/context truth outside `main`.
