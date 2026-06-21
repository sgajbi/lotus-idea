# CI Quality Gates

The scaffold starts with baseline gates in `Makefile` and `.github/workflows/`.

Promote stricter gates only after the signal is measured, deterministic, low-noise, locally
runnable, and tied to a real bank-buyable control.

Blocking scaffold commands:

1. `make architecture-boundary-gate`
2. `make ci-contract-gate`

Report-only scaffold commands:

1. `make architecture-boundary-report`
2. `make quality-baseline`

Generated report artifacts from these commands are local evidence and are
ignored by git unless an RFC explicitly promotes a specific evidence snapshot.

`make ci-contract-gate` is the anti-drift gate for the day-one bank-buyable baseline. It checks that
the Makefile and GitHub workflow lanes still include architecture boundaries, OpenAPI quality,
supported-feature promotion control, endpoint certification, coverage, security audit, Docker build,
release evidence, least-privilege workflow permissions, and approved action-runtime majors.
