# CI Quality Gates

The scaffold starts with baseline gates in `Makefile` and `.github/workflows/`.

Promote stricter gates only after the signal is measured, deterministic, low-noise, locally
runnable, and tied to a real bank-buyable control.

Blocking scaffold commands:

1. `make architecture-boundary-gate`
2. `make ci-contract-gate`
3. `make maintainability-gate`
4. `make private-import-boundary-gate`
5. `make documentation-contract-gate`
6. `make quality-scorecard-gate`
7. `make monetary-float-guard`
8. `make no-sensitive-content-guard`
9. `make source-observability-contract-gate`
10. `make api-route-metadata-gate`
11. `make api-problem-details-boundary-gate`
12. `make openapi-problem-details-example-gate`
13. `make operation-metric-contract-gate`
14. `make ai-model-risk-ops-contract-gate`
15. `make ai-model-risk-operations-proof-contract-gate`
16. `make implementation-truth-gate`
17. `make data-mesh-contract-gate`
18. `make mesh-policy-proof-contract-gate`
19. `make opportunity-archetype-contract-gate`
20. `make downstream-realization-contract-gate`
21. `make migration-contract-gate`
22. `make migration-execution-gate`
23. `make durable-repository-proof-contract-gate`
24. `make runtime-trust-telemetry-proof-contract-gate`
25. `make ai-lineage-store-proof-contract-gate`
26. `make ai-workflow-pack-registration-proof-contract-gate`
27. `make ai-workflow-pack-runtime-execution-proof-contract-gate`
28. `make workbench-read-path-proof-contract-gate`
29. `make gateway-workbench-operational-proof-contract-gate`
30. `make gateway-workbench-discovery-proof-contract-gate`
31. `make outbox-broker-proof-contract-gate`
32. `make platform-mesh-onboarding-proof-contract-gate`
33. `make downstream-route-contract-proof-gate`
34. `make source-ingestion-worker-check`
35. `make source-ingestion-scheduled-worker-check`
36. `make source-ingestion-live-proof-contract-gate`
37. `make risk-concentration-live-proof-contract-gate`
38. `make high-volatility-live-proof-contract-gate`
39. `make risk-drawdown-live-proof-contract-gate`
40. `make manage-mandate-live-proof-contract-gate`
41. `make mandate-restriction-live-proof-contract-gate`
42. `make missing-suitability-live-proof-contract-gate`
43. `make missing-risk-profile-live-proof-contract-gate`
44. `make performance-underperformance-live-proof-contract-gate`
45. `make core-benchmark-assignment-live-proof-contract-gate`
46. `make core-portfolio-state-live-proof-contract-gate`
47. `make implementation-proof-readiness-check` generates the scheduled-worker
    deploy-proof artifact, durable repository proof artifact, runtime trust
    telemetry proof artifact, Workbench read-path proof artifact,
    Gateway/Workbench operational proof artifact, Gateway/Workbench discovery proof artifact, outbox
    broker proof artifact, default Advise proposal route proof artifact,
    default Manage action route proof artifact, default Report intake route
    proof artifact, default mesh policy proof artifact, and default platform
    mesh onboarding proof artifact, plus AI lineage store and AI workflow-pack
    registration proof artifacts and optional Core portfolio-state, Manage
    mandate, Advise mandate/restriction, missing-suitability, and missing
    risk-profile live proof, then consumes all in aggregate RFC proof-readiness
    evidence.
48. `make supported-features-gate`
49. `make endpoint-certification-gate`
50. `make postgres-integration-gate`
51. `make openapi-gate`
52. `make coverage-gate`
53. `make security-audit`
54. `make docker-build`

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
mesh policy proof contract validation,
opportunity archetype contract validation,
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
AI model-risk operations proof validation,
Core portfolio-state live-proof contract validation,
Risk high-volatility and drawdown live-proof contract validation,
Advise mandate/restriction live-proof contract validation,
Workbench read-path proof contract validation,
Gateway/Workbench discovery proof contract validation,
outbox broker proof contract validation,
implementation-proof readiness artifact generation, runtime trust telemetry preview generation,
source-observability contract validation, API route metadata validation,
API ProblemDetails boundary validation, OpenAPI ProblemDetails example validation,
private domain import boundary validation, operation metric contract validation, AI model-risk
operations contract validation, governed generated-artifact cleanup, PostgreSQL runtime proof, coverage,
security audit, Docker build, release evidence, least-privilege workflow permissions, bounded job
timeouts, no soft-failed critical jobs, implementation-truth enforcement, non-suppressed
auto-merge dispatch posture, verified immutable GitHub Action SHA pins with version provenance,
scoped test-target variables for focused fix-forward validation, repo-native GitHub test and
coverage target usage, and pass/fail unit coverage for the CI contract gate itself. The CI contract
gate now explicitly fails if these current blocking lint gates are removed from `make lint`, so
agent-driven quality controls cannot quietly become optional local commands.

Focused test runs must stay on the Makefile surface instead of bypassing repository governance:

```powershell
make test-unit UNIT_TESTS=tests/unit/test_runtime_trust_telemetry.py
make test-integration INTEGRATION_TESTS=tests/integration/test_runtime_trust_telemetry_api.py
make test-e2e E2E_TESTS=tests/e2e/test_service_contract.py
```

The defaults remain the full unit, integration, and e2e suites. The CI contract gate blocks
removal of `UNIT_TESTS`, `INTEGRATION_TESTS`, and `E2E_TESTS` wiring.

Coverage collection also stays on the Makefile surface:

```powershell
make test-unit-coverage
make test-integration-coverage
make test-e2e-coverage
make test-coverage
```

`test-coverage` runs the three suite-level coverage targets before `make coverage-gate`. GitHub
Feature, PR Merge, and Main Releasability lanes must call the repo-native test and coverage targets
instead of raw workflow `pytest` commands; `make ci-contract-gate` rejects workflow shortcuts so
future agents cannot make GitHub appear green while bypassing local governance.

GitHub branch protection requires the strict PR Merge Gate contexts, including
`PR Merge Gate / PostgreSQL Runtime Proof`, before `main` can move. The Docker validation job also
depends on the PostgreSQL proof, but the runtime proof is listed as a first-class required status so
durable persistence and migration behavior cannot become an implicit or forgotten prerequisite.

`make maintainability-gate` blocks oversized Python files/functions across `src`, `tests`, and
`scripts`. The thresholds are set above the current measured baseline so the gate prevents new
agent-generated bloat without forcing unrelated refactors into every feature slice.

`make private-import-boundary-gate` blocks private `app.domain.*` imports from other modules.
Domain helpers may remain private inside their owning file, but cross-module callers must use
public, named APIs. The gate is deliberately scoped to domain ownership; broader cleanup of
application proof-helper and persistence-codec private imports remains future refactoring work.

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

`make api-route-metadata-gate` blocks local `RouteMetadata` and `SignalRouteMetadata`
`TypedDict` clones in `src/app/api`. Route modules must use
`app.api.route_metadata.RouteMetadata`, and signal-route support may alias that
shared contract rather than carrying a parallel metadata definition.

`make openapi-problem-details-example-gate` blocks public OpenAPI
`ProblemDetails` responses that lack product-safe examples. Workflow and
operator routes should use `app.api.problem_details` helpers for route-specific
400/403/404/409/503 metadata; signal routes keep their stricter route-family
metadata in `app.api.signal_api_support`.

`make operation-metric-contract-gate` validates
`contracts/observability/lotus-idea-operation-metrics.v1.json` against the code-owned operation,
outcome, supportability, source-authority, and metric-label vocabulary. It blocks sensitive metric
labels and prevents the implemented metric catalog from being treated as dashboard certification,
alert certification, platform mesh certification, Gateway/Workbench proof, or supported-feature
promotion.

`make ai-model-risk-ops-contract-gate` validates
`contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`
against implemented AI explanation and readiness operation telemetry. It
blocks missing dashboard controls, missing alert rules, sensitive labels,
unsupported operation names, missing source-of-truth paths, and product-support
overclaims.

`make ai-model-risk-operations-proof-contract-gate` validates the repo-owned
Grafana dashboard, Prometheus alert rules, and model-risk runbook against
implemented AI explanation telemetry. It blocks sensitive identifiers,
unimplemented metrics, missing alert runbook anchors, and any attempt to treat
operations monitoring as `lotus-ai`, Workbench, data-mesh, client-ready, or
supported-feature certification.

`make ai-workflow-pack-registration-proof-contract-gate` validates the bounded
sibling `lotus-ai` workflow-pack registration proof used by aggregate
implementation-proof readiness. It blocks source-unsafe evidence refs, missing
registry/binding/queue-policy/supportability/test proof, and any attempt to
treat registration as `lotus-ai` runtime execution, provider invocation,
Workbench proof, or supported-feature promotion. Model-risk dashboard and
alert artifact certification remains owned by
`make ai-model-risk-operations-proof-contract-gate`.

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
