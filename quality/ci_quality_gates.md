# CI Quality Gates

The scaffold starts with baseline gates in `Makefile` and `.github/workflows/`.

Promote stricter gates only after the signal is measured, deterministic, low-noise, locally
runnable, and tied to a real bank-buyable control.

Blocking scaffold commands:

1. `make architecture-boundary-gate`
2. `make ci-contract-gate`
3. `make maintainability-gate`
4. `make documentation-contract-gate`
5. `make quality-scorecard-gate`
6. `make implementation-truth-gate`
7. `make endpoint-certification-gate`

Report-only scaffold commands:

1. `make architecture-boundary-report`
2. `make quality-baseline`

Generated report artifacts from these commands are local evidence and are
ignored by git unless an RFC explicitly promotes a specific evidence snapshot.

`make ci-contract-gate` is the anti-drift gate for the day-one bank-buyable baseline. It checks that
the Makefile and GitHub workflow lanes still include architecture boundaries, maintainability,
OpenAPI quality,
supported-feature promotion control, endpoint certification, coverage, security audit, Docker build,
release evidence, least-privilege workflow permissions, bounded job timeouts, no soft-failed
critical jobs, implementation-truth enforcement, and approved action-runtime majors.

`make maintainability-gate` blocks oversized Python files/functions across `src`, `tests`, and
`scripts`. The thresholds are set above the current measured baseline so the gate prevents new
agent-generated bloat without forcing unrelated refactors into every feature slice.

`make documentation-contract-gate` blocks removal, thinning, or placeholder
erosion of the required durable documentation and wiki surfaces. It is scoped to
operator and agent context, not RFC target-state prose, so it remains fast and
deterministic while preserving the context needed to apply the bank-buyable
contract across future implementation slices.

`make quality-scorecard-gate` blocks bank-buyable scorecard drift. It verifies
the required control matrix, approved status vocabulary, non-empty evidence and
gap cells, implementation-backed evidence anchors, and stale scaffold-era
underclaims such as claiming business endpoints or behavior tests do not exist
after certified internal API foundations have landed.

`make implementation-truth-gate` blocks unqualified current-state claims of demo readiness,
production readiness, external support, certification, live source ingestion, Gateway/Workbench
support, or client-ready publication while `supported-features/supported-features.json` has no
implemented features. It prevents agent-written README/wiki/operations text from outpacing code,
endpoint certification, data-mesh proof, and supported-feature evidence.

`make endpoint-certification-gate` blocks weak API certification. It requires every public OpenAPI
operation to have a ledger entry; validates required evidence fields, valid JSON examples,
real `tests/path.py::test_name` references, baseline endpoint status discipline, OpenAPI-gate
evidence, certified endpoint capability posture, product-safe 403 behavior, and explicit
Gateway/Workbench/supported-feature boundary wording before an endpoint can remain `certified`.
