# Enterprise Readiness

- Service: lotus-idea
- Status: baseline adopted.

Enterprise-quality enforcement is repo-native from day one. `make lint`, `make check`, and GitHub
lanes protect architecture boundaries, maintainability thresholds, documentation surface
contracts, quality-scorecard truth, OpenAPI quality, data-mesh
contract posture, migration safety, supported-feature promotion control, endpoint certification,
security audit, coverage, PostgreSQL runtime proof, workflow timeout posture, no soft-failed
critical CI jobs, immutable GitHub Action SHA pins with version provenance,
repository hygiene, and implementation-truth claims in README/docs/wiki current-state surfaces.
Protected `main` requires the strict PR Merge Gate status set, including
`PR Merge Gate / PostgreSQL Runtime Proof`, before merge.

Day-one enterprise posture is governed by
`lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`.
`make documentation-contract-gate` enforces the minimum durable documentation
surface that lets engineers, operators, reviewers, and future agents apply that
contract: README, repository context, standards, runbooks, RFC index, quality
scorecard, evidence guide, and repo-local wiki source.

The maintainability gate is intentionally conservative and measured against the current baseline:
source files/functions, test files/functions, and script files/functions have explicit maximum
line-count thresholds. New work should refactor or split modules before exceeding those thresholds.

`make repository-hygiene-gate` is blocking through `make lint`. It prevents
committed generated Python cache files, local coverage artifacts, build outputs,
dependency directories, local environment files, logs, and local databases so
the repository remains a durable source, contract, test, evidence, and
documentation surface rather than a dump of runtime byproducts.

`make clean` is the repo-native cleanup command for ignored generated residue.
It removes local Python cache directories, coverage files, build outputs, and
HTML coverage output while pruning `.git`, `.venv`, and dependency cache
directories. `make ci-contract-gate` protects this wiring so future agentic
changes cannot replace cleanup with an untested one-liner.

`make quality-scorecard-gate` protects the local bank-buyable scorecard from
becoming stale as implementation lands. The scorecard must retain the required
control rows, use approved readiness statuses, name implementation-backed
evidence for each control, and avoid scaffold-era underclaims once certified
internal APIs, persistence proof, operation events, and meaningful tests exist.

`make implementation-truth-gate` also protects against stale scaffold-era underclaims in
current-state demo documentation. As internal APIs, architecture gates, persistence, and other
foundations become real, the demo ledger must move from generic scaffold wording to
implementation-backed evidence plus explicit unsupported boundaries.
