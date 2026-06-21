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
make data-mesh-contract-gate
make migration-contract-gate
make migration-execution-gate
make openapi-gate
make architecture-boundary-gate
make architecture-boundary-report
make quality-baseline
```

Baseline required checks include lint, format check, typecheck, architecture boundary enforcement,
OpenAPI quality, supported-feature gate, endpoint-certification gate, unit tests, integration
tests, e2e tests, data-mesh contract validation, migration contract validation, coverage gate,
safe migration execution dry-run validation, security audit, Docker build validation, and workflow
lint.

The CI contract gate is blocking from day one. It prevents accidental removal of bank-buyable
controls from the Makefile or GitHub lanes, including least-privilege workflow permissions,
approved action-runtime majors, 99% combined coverage in merge/releasability lanes, Docker build
validation, SBOM/release evidence, endpoint certification, supported-feature promotion control,
data-mesh contract validation, migration contract validation, migration execution dry-run
validation, workflow-dispatch access, non-suppressed auto-merge token usage, merged-PR
main-releasability dispatch, and source-safe local quality gates.

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
