# Enterprise Readiness

- Service: lotus-idea
- Status: baseline adopted.

Enterprise-quality enforcement is repo-native from day one. `make lint`, `make check`, and GitHub
lanes protect architecture boundaries, maintainability thresholds, documentation surface
contracts, OpenAPI quality, data-mesh
contract posture, migration safety, supported-feature promotion control, endpoint certification,
security audit, coverage, workflow timeout posture, no soft-failed critical CI jobs, and
implementation-truth claims in README/docs/wiki current-state surfaces.

Day-one enterprise posture is governed by
`lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`.
`make documentation-contract-gate` enforces the minimum durable documentation
surface that lets engineers, operators, reviewers, and future agents apply that
contract: README, repository context, standards, runbooks, RFC index, quality
scorecard, evidence guide, and repo-local wiki source.

The maintainability gate is intentionally conservative and measured against the current baseline:
source files/functions, test files/functions, and script files/functions have explicit maximum
line-count thresholds. New work should refactor or split modules before exceeding those thresholds.

`make implementation-truth-gate` also protects against stale scaffold-era underclaims in
current-state demo documentation. As internal APIs, architecture gates, persistence, and other
foundations become real, the demo ledger must move from generic scaffold wording to
implementation-backed evidence plus explicit unsupported boundaries.
