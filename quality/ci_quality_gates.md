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
6. `make monetary-float-guard`
7. `make no-sensitive-content-guard`
8. `make source-observability-contract-gate`
9. `make operation-metric-contract-gate`
10. `make ai-model-risk-ops-contract-gate`
11. `make implementation-truth-gate`
12. `make data-mesh-contract-gate`
13. `make downstream-realization-contract-gate`
14. `make migration-contract-gate`
15. `make migration-execution-gate`
16. `make durable-repository-proof-contract-gate`
17. `make runtime-trust-telemetry-proof-contract-gate`
18. `make ai-lineage-store-proof-contract-gate`
19. `make ai-workflow-pack-registration-proof-contract-gate`
20. `make workbench-read-path-proof-contract-gate`
21. `make outbox-broker-proof-contract-gate`
22. `make platform-mesh-onboarding-proof-contract-gate`
23. `make source-ingestion-worker-check`
24. `make source-ingestion-scheduled-worker-check`
25. `make source-ingestion-live-proof-contract-gate`
26. `make implementation-proof-readiness-check` generates the scheduled-worker
    deploy-proof artifact, durable repository proof artifact, runtime trust
    telemetry proof artifact, Workbench read-path proof artifact, outbox
    broker proof artifact, default report-intake route proof artifact, and
    default platform mesh onboarding proof artifact, plus AI lineage store and
    AI workflow-pack registration proof artifacts, then consumes all nine in
    aggregate RFC proof-readiness evidence.
27. `make supported-features-gate`
28. `make endpoint-certification-gate`
29. `make postgres-integration-gate`
30. `make openapi-gate`
31. `make coverage-gate`
32. `make security-audit`
33. `make docker-build`

Cleanup support command:

1. `make clean`

Report-only scaffold commands:

1. `make architecture-boundary-report`
2. `make quality-baseline`

Generated report artifacts from these commands are local evidence and are
ignored by git unless an RFC explicitly promotes a specific evidence snapshot.

`make ci-contract-gate` is the anti-drift gate for the day-one bank-buyable baseline. It checks that
the Makefile and GitHub workflow lanes still include architecture boundaries, maintainability,
OpenAPI quality,
supported-feature promotion control, endpoint certification, data-mesh contract validation,
downstream realization contract validation, migration contract validation,
migration execution dry-run validation,
source-ingestion worker manifest and source-safe output-contract validation,
scheduled source-ingestion worker deploy-contract validation,
source-ingestion live-proof contract validation with aggregate blocked-reason
diagnostics,
durable repository proof contract validation,
runtime trust telemetry proof contract validation,
AI lineage store proof contract validation,
AI workflow-pack registration proof contract validation,
Workbench read-path proof contract validation,
outbox broker proof contract validation,
implementation-proof readiness artifact generation, source-observability
contract validation, operation metric contract validation, AI model-risk
operations contract validation, governed generated-artifact cleanup, PostgreSQL runtime proof, coverage,
security audit, Docker build, release evidence, least-privilege workflow permissions, bounded job
timeouts, no soft-failed critical jobs, implementation-truth enforcement, non-suppressed
auto-merge dispatch posture, verified immutable GitHub Action SHA pins with version provenance,
scoped test-target variables for focused fix-forward validation, and pass/fail unit coverage for
the CI contract gate itself.

Focused test runs must stay on the Makefile surface instead of bypassing repository governance:

```powershell
make test-unit UNIT_TESTS=tests/unit/test_runtime_trust_telemetry.py
make test-integration INTEGRATION_TESTS=tests/integration/test_runtime_trust_telemetry_api.py
make test-e2e E2E_TESTS=tests/e2e/test_service_contract.py
```

The defaults remain the full unit, integration, and e2e suites. The CI contract gate blocks
removal of `UNIT_TESTS`, `INTEGRATION_TESTS`, and `E2E_TESTS` wiring.

GitHub branch protection requires the strict PR Merge Gate contexts, including
`PR Merge Gate / PostgreSQL Runtime Proof`, before `main` can move. The Docker validation job also
depends on the PostgreSQL proof, but the runtime proof is listed as a first-class required status so
durable persistence and migration behavior cannot become an implicit or forgotten prerequisite.

`make maintainability-gate` blocks oversized Python files/functions across `src`, `tests`, and
`scripts`. The thresholds are set above the current measured baseline so the gate prevents new
agent-generated bloat without forcing unrelated refactors into every feature slice.

`make monetary-float-guard` blocks money-like `float` usage in application
source. The guard is AST-backed and fails monetary `float` annotations,
money-like float literals, and money-like `float(...)` conversions while
allowing operational floats such as timeout seconds. This protects private
banking precision without forcing unrelated runtime configuration code into
Decimal types.

`make documentation-contract-gate` blocks removal, thinning, placeholder
erosion, and text-dump operator guides across the required durable
documentation and wiki surfaces. It is scoped to operator and agent context,
not RFC target-state prose, so it remains fast and deterministic while
preserving the context needed to apply the bank-buyable contract across future
implementation slices. Proof and readiness guides must keep a polished
operator structure with current-truth tables, explicit proof and non-proof
boundaries, blocker sections, response-shape tables, evidence references, and
executable examples.

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

`make no-sensitive-content-guard` blocks sensitive marker names in local
evidence, log, and output artifacts before those artifacts can become PR or
wiki evidence. The guard has focused pass/fail unit coverage for clean
artifacts, forbidden marker detection, allowlisted documentation, and binary
artifact handling.

`make clean` removes ignored local Python bytecode cache directories, coverage
files, build output, distribution output, and HTML coverage output through
`scripts/clean_generated_artifacts.py`. The cleanup utility prunes `.git`,
`.venv`, and dependency cache directories, and the CI contract gate blocks
weakening the Makefile cleanup target so local hygiene remains test-backed
instead of becoming another unreviewed shell one-liner.

`make source-observability-contract-gate` blocks ad hoc application logging in `src/app`. Feature
code must use bounded operation-event emitters or the central request diagnostic helper instead of
raw `print()`, direct Python logging, or low-level `log_event` calls. Request diagnostics log route
templates rather than raw URL paths, keeping operator evidence product-safe.

`make operation-metric-contract-gate` validates
`contracts/observability/lotus-idea-operation-metrics.v1.json` against the code-owned operation,
outcome, supportability, source-authority, and metric-label vocabulary. It blocks sensitive metric
labels and prevents the implemented metric catalog from being treated as dashboard certification,
alert certification, platform mesh certification, Gateway/Workbench proof, or supported-feature
promotion.

`make ai-model-risk-ops-contract-gate` validates
`contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`
against implemented AI explanation and readiness operation telemetry. It
blocks missing dashboard controls, missing alert candidates, sensitive labels,
unsupported operation names, missing source-of-truth paths, and premature
model-risk dashboard, alert, `lotus-ai`, Workbench, or supported-feature
certification claims.

`make ai-workflow-pack-registration-proof-contract-gate` validates the bounded
sibling `lotus-ai` workflow-pack registration proof used by aggregate
implementation-proof readiness. It blocks source-unsafe evidence refs, missing
registry/binding/queue-policy/supportability/test proof, and any attempt to
treat registration as `lotus-ai` runtime execution, provider invocation,
model-risk dashboard/alert certification, Workbench proof, or
supported-feature promotion.

`make source-ingestion-live-proof-contract-gate` also protects the live-proof
artifact's aggregate `blockReasonCounts`. This keeps Core-runtime proof
failures diagnosable while blocking raw portfolio identifiers, source payloads,
idempotency keys, candidate identifiers, and premature support claims.

`make outbox-broker-proof-contract-gate` validates the bounded outbox broker
proof artifact used by aggregate implementation-proof readiness. It blocks
source-sensitive event, aggregate, idempotency, payload, portfolio, client,
trace, and broker-content leakage while preserving the boundary that external
publication, downstream consumers, platform mesh events, Gateway/Workbench
proof, and supported-feature promotion remain uncertified.

`make downstream-realization-contract-gate` validates
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
It keeps planned Advise, Manage, and Report handoff records source-authority
preserving, blocker-backed, and free of route-existence, downstream-execution,
or supported-feature claims until the owning repositories certify live
contracts.

`make endpoint-certification-gate` blocks weak API certification. It requires every public OpenAPI
operation to have a ledger entry; validates required evidence fields, valid JSON examples,
real `tests/path.py::test_name` references, baseline endpoint status discipline, OpenAPI-gate
evidence, certified endpoint capability posture, product-safe 403 behavior, and explicit
Gateway/Workbench/supported-feature boundary wording before an endpoint can remain `certified`.
Certified business/operator endpoints must also reference bounded operation-event test evidence so
API certification cannot drift away from supportability telemetry proof.
When bounded read-only Gateway publication exists, the gate requires the endpoint ledger to cite the
exact `lotus-gateway` route and still preserve Workbench, data-product, client-ready publication,
and supported-feature boundaries.
