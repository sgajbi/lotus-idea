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
18. `make mesh-policy-source-contract-proof-gate`
19. `make opportunity-archetype-contract-gate`
20. `make downstream-realization-contract-gate`
21. `make migration-contract-gate`
22. `make migration-execution-gate`
23. `make durable-repository-proof-contract-gate`
24. `make runtime-trust-telemetry-test-execution-contract-gate`
25. `make ai-lineage-store-proof-contract-gate`
26. `make ai-workflow-pack-registration-proof-contract-gate`
27. `make ai-workflow-pack-runtime-execution-proof-contract-gate`
28. `make workbench-read-path-source-contract-proof-gate`
29. `make gateway-workbench-contract-proof-contract-gate`
30. `make gateway-workbench-discovery-contract-proof-contract-gate`
31. `make outbox-broker-source-contract-proof-gate`
32. `make platform-catalog-source-contract-proof-gate`
33. `make downstream-route-source-contract-proof-gate`
34. `make source-ingestion-worker-check`
35. `make source-ingestion-scheduled-worker-check`
36. `make source-ingestion-runtime-execution-contract-gate`
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
47. `make supported-features-gate`
48. `make endpoint-certification-gate`
49. `make postgres-integration-gate`
50. `make openapi-gate`
51. `make coverage-gate`
52. `make security-audit`
53. `make docker-build`
54. `make container-runtime-smoke`

Support commands:

1. `make clean`
2. `make github-security-posture-check`

On-demand local report commands:

1. `make architecture-boundary-report`
2. `make quality-baseline`

Generated report artifacts from these commands are local review evidence and are
ignored by git. They are not durable current-state proof in the quality
scorecard; rerun the commands when a reviewer asks for a fresh artifact.

Release and review evidence commands:

1. `make implementation-proof-readiness-check` generates the scheduled-worker
   deploy-proof artifact, durable repository proof artifact, runtime trust
   telemetry proof artifact, Workbench read-path source-contract proof artifact,
   Gateway/Workbench contract proof artifact, Gateway/Workbench discovery
   proof artifact, outbox broker source-contract proof artifact, default digest-bound Advise and
   Manage route source-contract artifacts, default Report
   intake route proof artifact, default mesh policy source-contract artifact, and default
   platform catalog source contract artifact, plus AI lineage store and AI
   workflow-pack registration proof artifacts and optional Core
   portfolio-state, Manage mandate, Advise mandate/restriction,
   receipt-bound missing-suitability runtime evidence and missing risk-profile live proof, then consumes all
   in aggregate RFC proof-readiness evidence.
2. `make runtime-trust-telemetry-snapshot-check` writes the source-safe runtime
   trust telemetry snapshot under ignored `output/` for release/review evidence.
3. `make ci-release` runs `make ci`, the implementation-proof readiness
   generator, runtime trust telemetry snapshot generation, PostgreSQL runtime
   proof, Docker build, container startup smoke, image scan, and SBOM evidence.

These commands intentionally write ignored local proof artifacts and are not
part of `make lint`. Clean contract gates and non-writing preview checks for
the same proof families remain blocking in lint so fast lanes stay
deterministic.

`make ci-contract-gate` is the anti-drift gate for the day-one bank-buyable baseline. It checks that
the Makefile and GitHub workflow lanes still include architecture boundaries, maintainability,
OpenAPI quality,
supported-feature promotion control, endpoint certification, data-mesh contract validation,
mesh policy source-contract validation,
opportunity archetype contract validation,
downstream realization contract validation, migration contract validation,
migration execution dry-run validation,
source-ingestion worker manifest and source-safe output-contract validation,
scheduled source-ingestion worker deploy-contract validation,
source-ingestion runtime-execution receipt contract validation with aggregate blocked-reason
diagnostics,
durable repository proof contract validation,
runtime trust telemetry test-execution contract validation,
AI lineage store proof contract validation,
AI workflow-pack registration proof contract validation,
AI model-risk operations proof validation,
Core portfolio-state live-proof contract validation,
Risk high-volatility and drawdown live-proof contract validation,
Advise mandate/restriction live-proof contract validation,
Workbench read-path source-contract proof validation,
Gateway/Workbench discovery contract proof contract validation,
outbox broker source-contract proof validation,
implementation-proof readiness target wiring and release-lane placement, runtime trust telemetry preview generation, runtime trust telemetry snapshot release-lane placement,
source-observability contract validation, API route metadata validation,
API ProblemDetails boundary validation, OpenAPI ProblemDetails example validation,
protected private import boundary validation, operation metric contract validation, AI model-risk
operations contract validation, governed generated-artifact cleanup, PostgreSQL runtime proof, coverage,
security audit, Docker build, packaged container startup smoke proof, release evidence, least-privilege workflow permissions, bounded job
timeouts, no soft-failed critical jobs, implementation-truth enforcement, non-suppressed
auto-merge dispatch posture, verified immutable GitHub Action SHA pins with version provenance,
scoped test-target variables for focused fix-forward validation, repo-native GitHub test and
coverage target usage, report-only CI timing/signal evidence, and pass/fail unit coverage for the
CI contract gate itself. The CI contract
gate now explicitly fails if clean blocking gates are removed from `make lint`,
if artifact-producing implementation-proof readiness or runtime trust telemetry
snapshot generation is added back to `make lint`, or if the release lane drops
those evidence generators.
Main Releasability is intentionally `workflow_dispatch` only: merged PRs use
`merged-pr-main-releasability.yml` to dispatch one authoritative post-merge
release-proof run, and manual reruns use the same dispatchable workflow. The
CI contract gate rejects reintroducing a `push` trigger that would create
expected push-cancelled / dispatch-success duplicate run pairs.

GitHub Security posture is also under the CI contract gate. The repository has
Dependabot alerts/security updates enabled, secret scanning with push
protection enabled, private vulnerability reporting enabled, and CodeQL default
setup configured for GitHub-owned static analysis over Python and GitHub
Actions. Source-controlled `SECURITY.md` and `.github/dependabot.yml` define
the supported security baseline, source-safe report content, a single grouped
Python dependency-closure root update stream, and grouped GitHub Actions
dependency monitoring. Routine Dependabot version-update PRs are paused with
`open-pull-requests-limit: 0` while RFC delivery is active; dependency
suggestions must be manually regenerated or cherry-picked into the active
implementation branch and validated through repo-native gates. `make
ci-contract-gate` rejects removal or weakening of those files and blocks
reintroduced `/requirements` lock-only Python update streams. GitHub currently reports
non-provider secret patterns and secret validity checks as disabled for this
repository even after an admin API enable attempt, so those controls are
advisory future options and are not claimed as active release evidence.
`make github-security-posture-check` is the live operator check for mutable
GitHub Security state. It verifies required enabled settings, CodeQL's governed
`default` query suite and `remote` threat model, private vulnerability
reporting, and zero open code-scanning, secret-scanning, and Dependabot alerts.
The target is intentionally not part of offline lint because it depends on live
GitHub API access through `gh auth`.

Main Releasability release evidence now keeps container provenance
reproducible without requiring developers to pin local defaults by digest. The
workflow uses the governed `CONTAINER_BASE_IMAGE` and `TRIVY_IMAGE` references,
pulls both images in the release lane, resolves their immutable `RepoDigest`
values with Docker, and writes `docker_base_image_resolved_digest` plus
`container_scanner_resolved_digest` to `release-evidence.json`. The CI contract
gate rejects removal of the digest-resolution step or digest fields so future
agents cannot preserve only mutable tag evidence.

Main Releasability SBOM evidence is also explicit about scope. `make
release-sbom` uses the pinned CycloneDX tool against
`requirements/runtime-resolved.lock.txt`, not the CI virtual environment, and
writes `sbom.cdx.json` as runtime Python dependency evidence. The release
manifest records that SBOM under `sboms[]` with scope, path, generator,
dependency source, project metadata, target service image reference, and built
image id. This is not a full container image SBOM; container OS and packaged
image posture remain covered by the Trivy image scan.
`make runtime-dependency-closure-gate` blocks direct-only runtime locks by
checking the resolved lock against the installed transitive dependency closure
for the `pyproject.toml` runtime roots and against the
`requirements/requirements.txt` GitHub Dependency Graph mirror.
`make dependency-refresh` is the governed local reconciliation command for
Python dependency update PRs: it installs from root pins without the stale
runtime-lock constraint, then regenerates both
`requirements/runtime-resolved.lock.txt` and `requirements/requirements.txt`
from the active runtime closure. Run
`python -m scripts.refresh_runtime_dependency_locks --check` to validate that
the committed locks match the active validation venv.

PR Merge Gate and Main Releasability now run `make container-runtime-smoke`
after `make docker-build` and before Docker release evidence can pass. The
target starts the built `backend-service:ci-test` image, probes `/health`,
`/health/live`, and reachable default-profile `/health/ready`, captures
container logs on failure, and always removes the smoke container. The readiness
probe accepts `200` or the default fail-closed `503` because the local packaged
runtime may not have durable write storage configured; this is startup and
health-surface proof, not production readiness, live upstream connectivity, or
supported-feature proof.

The runtime Dockerfile is cache-aware without weakening release proof. It copies
`pyproject.toml`, `README.md`, and `requirements/runtime-resolved.lock.txt`,
installs the resolved runtime dependency lock before `COPY src`, then installs
the local service package with `--no-deps`. `make ci-contract-gate` rejects
source-before-dependency-install ordering and package installs that would
reinstall dependencies after a source-only change. Docker build, runtime smoke,
image scan, and SBOM evidence remain blocking release-lane proof.

Docker build context hygiene follows the same generated-artifact policy as
repository hygiene and `make clean`. `.dockerignore` excludes coverage data,
`coverage.xml`, `sbom.cdx.json`, `output`, and generated quality reports so
local validation byproducts do not become remote-builder inputs. `make
ci-contract-gate` rejects Docker-context generated-artifact parity drift while
preserving the Dockerfile's selective runtime inputs.

Duplicate implementation enforcement is split into a report command and a blocking gate. `make
duplicate-implementation-inventory` scans exact function-body duplicates across `src/app` and
`scripts`, writes no artifacts, and reports `thresholdEnforced: false` for review evidence. `make
duplicate-implementation-gate` runs the same scanner with `--fail-on-duplicates`, reports
`thresholdEnforced: true`, and is wired into `make lint` as the zero-cluster regression blocker. The
initial six-line baseline scanned 1,750 functions and reported 31 exact duplicate clusters,
including the known proof source-safety helper families. The
first proof-helper consolidations moved source-safety traversal into
`scripts/proof_source_safety.py` and live-proof generator timeout/output plumbing plus
generated-at UTC parsing into `scripts/proof_generator_io.py`, and shared proof timestamp
validation, make-target evidence checks, and cross-repository file-evidence checks into
`src/app/application/source_safe_cross_repo_proof.py`, and AST call-name parsing into
`scripts/ast_gate_helpers.py`, and Core live-proof base URL resolution into
`scripts/proof_generator_io.py`, and Advise/Manage proof evidence request construction into
`scripts/proof_request_builders.py`, and mutating API reason-code validation into
`app.api.request_validation`, and bounded API telemetry count buckets into
`app.api.telemetry_buckets`, and caller-supplied signal response DTO projection into
`app.api.signal_models.SignalEvaluationResponse`, and application-layer portfolio-only signal
review scopes into `app.application.access_scope`, and source-reference/access-scope write-side
payload projection into `app.ports.evidence_payloads`, and API persistence-summary response
projection into `app.api.persistence_summary`, and API review access-scope DTOs into
`app.api.access_scope_models`, and blocked signal-result construction into
`app.domain.signal_evaluation.blocked_signal_result`, and optional proof-artifact JSON object
loading into `app.runtime.proof_artifact_files`, and source-product proof payload text-sequence
normalization into `app.application.source_product_proof_values`, and outbox contract
forbidden-text traversal into `scripts.contract_text_guards`, and operations-contract payload,
operation, and label validation into `scripts.operations_contract_validators`; the current
measured baseline ignores pass/ellipsis-only protocol stubs, scans 1,607 executable function
bodies, and reports 0 exact duplicate clusters. The CI contract gate protects the report-only and
blocking target split, the strict `--fail-on-duplicates` flag, and the `make lint` lane placement.
Intentional exceptions must be implemented as measured scanner policy with tests, not by removing
the blocking gate.

Focused test runs must stay on the Makefile surface instead of bypassing repository governance:

```powershell
make test-unit UNIT_TESTS=tests/unit/runtime_trust_telemetry/test_telemetry.py
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
instead of raw workflow `pytest` commands; PR Merge and Main Releasability combined coverage jobs
call `make coverage-gate COVERAGE_DATA_DIR=coverage-data` after downloading suite artifacts.
`scripts/coverage_gate.py --coverage-dir <directory>` owns the artifact layout and threshold
logic, and `make ci-contract-gate` rejects raw workflow-level `coverage combine coverage-data` or
`coverage report --fail-under=99` shortcuts so future agents cannot make GitHub appear green while
bypassing local governance.

CI timing and signal-quality evidence is report-only. Feature Lane, PR Merge Gate, and Main
Releasability have an `if: always()` CI Signal Evidence job that reads GitHub's run-job metadata
through `actions: read`, generates source-safe `ci-signal-evidence.json` with
`scripts/ci_signal_evidence.py`, and uploads lane-specific artifacts. The `gh api` call must
quote the composed `repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}/jobs` argument so
workflow lint stays free of ShellCheck word-splitting annotations. Main Releasability's
`release-evidence.json` references the `main-releasability-ci-signal-evidence` artifact and
`ci-signal-evidence.json` path. The artifact reports workflow feedback time from the first job
start to the last job completion as `workflowWallClockSeconds` and `criticalPathSeconds`, while
`longestJobName` and `longestJobSeconds` retain the longest individual job signal for optimization
triage. `make ci-signal-evidence-contract-gate` validates the schema shape, keeps
`thresholdEnforced` false, and blocks sensitive source markers; `make ci-contract-gate` prevents
workflow wiring drift. This establishes a measured baseline for future optimization without
introducing duration pass/fail thresholds.

GitHub branch protection requires the strict PR Merge Gate contexts, including
`PR Merge Gate / PostgreSQL Runtime Proof`, before `main` can move. The Docker validation job also
depends on the PostgreSQL proof and runs `make container-runtime-smoke` after the image build, but
the runtime proof is listed as a first-class required status so durable persistence and migration
behavior cannot become an implicit or forgotten prerequisite.

`make maintainability-gate` blocks oversized Python files/functions across `src`, `tests`, and
`scripts`. The thresholds are set above the current measured baseline so the gate prevents new
agent-generated bloat without forcing unrelated refactors into every feature slice.

`make private-import-boundary-gate` blocks private imports from protected module surfaces:
`app.domain.*`, `app.application.implementation_proof_capability_updates`, and
`app.infrastructure.postgres_codecs`. Domain helpers may remain private inside their owning file,
proof capability updates expose public `apply_blocker_proof` and
`build_capability_readiness` functions, and PostgreSQL repository code consumes public row, JSON,
datetime, and domain JSON codec functions. Broader application helper cleanup and adapter-internal
codec cleanup remain future refactoring work until each boundary is measured and low-noise.

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
templates rather than raw URL paths, keeping operator evidence product-safe. The same gate blocks
source adapters from mapping readiness, supportability, coverage, health-state, data-quality, or
`ready` predicates to `EvidenceFreshness.CURRENT`; freshness must come from explicit
source-authored freshness metadata such as `current` or `same_day`.

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
sibling `lotus-ai` workflow-pack registration source contract used by aggregate
implementation-proof readiness. It blocks source-unsafe evidence refs, missing
registry/binding/queue-policy/supportability/test evidence, non-`source_contract`
classification, non-empty blocker clearance, and any attempt to claim runtime
execution, deployment, production certification, provider invocation,
Workbench proof, or supported-feature promotion. A valid artifact adds
provenance while retaining `workflow_pack_runtime_contract_not_certified`.
Model-risk dashboard and alert artifact certification remains owned by
`make ai-model-risk-operations-proof-contract-gate`.

`make ai-attestation-source-contract-gate` validates the closed signed Lotus AI
attestation v2 `source_contract`. It requires exact producer/consumer
repository/ref/SHA-256 records, canonical collection digests, closed top-level
and check-field sets, source-safe content, and zero blocker clearance. With no
sibling producer checkout it accepts only an explicit Idea-consumer-only
non-proof posture. It rejects runtime execution, live-provider, model-risk
approval, deployment, production, Workbench, publication, and promotion claim
inflation. The retired flat v1 module, scripts, tests, target names, and output
variable are prohibited by repository hygiene and CI target contracts.

`make source-ingestion-runtime-execution-contract-gate` validates the closed
v2 `runtime_execution` artifact against real application-use-case and
persistence results. It reconciles decision/receipt counts, exact Core source
products, source-evidence hashes, durable storage, and source-safe receipt
digests; rejects the former self-asserted booleans and unknown fields; and
preserves scheduled-worker, mesh, Gateway/Workbench, production, and promotion
boundaries. Raw portfolio, tenant, route, payload, idempotency, and candidate
values remain prohibited.

`make outbox-broker-source-contract-proof-gate` validates the bounded outbox
broker source-contract artifact used by aggregate implementation-proof
readiness. It rejects runtime, deployment, production, support, and
blocker-clearance claim inflation; uses AST-backed publisher port and adapter
checks instead of scanning test-source fragments; and blocks source-sensitive
event, aggregate, idempotency, payload, portfolio, client, trace, and broker
content. External broker configuration/publication, downstream consumers,
platform mesh events, Gateway/Workbench proof, and supported-feature promotion
remain uncertified.

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
