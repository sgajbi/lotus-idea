# Validation And CI

`lotus-idea` starts with the Lotus backend lane model:

1. Feature Lane for branch feedback.
2. PR Merge Gate for required merge readiness.
3. Main Releasability Gate for post-merge truth.

Repo-native validation commands:

```powershell
make check
make ci
make openapi-gate
make architecture-boundary-gate
make architecture-boundary-report
make quality-baseline
```

Baseline required checks include lint, format check, typecheck, architecture boundary enforcement,
OpenAPI quality, supported-feature gate, endpoint-certification gate, unit tests, integration
tests, e2e tests, coverage gate, security audit, Docker build validation, and workflow lint.

Data-mesh foundation checks:

1. repo-owned proposed producer and consumer declarations must exist,
2. mesh placeholder files must not exist in contract or operations paths,
3. planned trust telemetry must remain blocked and `not_certified`,
4. SLO, access, and evidence policies must be present before promotion work,
5. platform mesh certification is required before any supported mesh claim.

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
