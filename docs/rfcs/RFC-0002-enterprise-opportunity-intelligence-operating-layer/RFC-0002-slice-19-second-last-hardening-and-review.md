# RFC-0002 Slice 19: Second-Last Hardening And Review

Status: Partially implemented

## Outcome

Perform the full engineering review before final closure.

## Required Work

1. Review code boundaries, duplicate logic, dead code, stale endpoints, docs,
   tests, OpenAPI, data products, trust telemetry, security, observability,
   model-risk controls, and UI behavior.
2. Verify API certification and Swagger quality.
3. Verify source-authority boundaries and no unsupported feature claims.
4. Fix loose ends before closure.

## Acceptance Gate

1. No dead code, duplicate paths, stale docs, unsupported claims, raw prompt
   leakage, raw provider output leakage, or source-authority violations remain.
2. All affected local and GitHub checks are green or formally treated.
3. The codebase is cleaner, more modular, and easier to extend than before.

## Current Implementation Evidence

This slice now includes the first enterprise-quality hardening control over the
bank-buyable scorecard itself:

1. `scripts/quality_scorecard_gate.py` validates the required control matrix,
   approved readiness vocabulary, non-empty evidence/gap/next-slice cells,
   implementation-backed evidence anchors, and stale scaffold-era scorecard
   underclaims.
2. `make quality-scorecard-gate` runs the validator directly and `make lint`
   runs it as a blocking local and GitHub lane gate.
3. `scripts/ci_contract_gate.py` requires the target and lint call so future
   agents cannot silently remove scorecard enforcement from the repo-native
   quality path.
4. `tests/unit/test_quality_scorecard_gate.py` covers current pass behavior and
   failure cases for stale scaffold claims, missing control rows, unsupported
   status vocabulary, and missing evidence anchors.
5. `quality/quality_scorecard.md` now reflects the current internal API,
   persistence, source-ingestion, observability, and testing foundation without
   promoting Gateway/Workbench support, live source ingestion, data-product
   certification, or externally supported product capability.

This does not close the full second-last review slice. Dead-code review,
duplication review, broader API/data-mesh/security review, and live proof
hardening remain planned before final closure.

This slice also hardens endpoint certification quality:

1. `scripts/endpoint_certification_gate.py` now validates that public OpenAPI
   operations remain synchronized with
   `docs/operations/endpoint-certification-ledger.json`.
2. The gate validates required evidence fields, JSON-shaped examples, real
   pytest evidence references, baseline endpoint status discipline, OpenAPI-gate
   evidence, certified endpoint capability posture, product-safe 403 behavior,
   explicit Gateway/Workbench/supported-feature-promotion boundary wording, and
   bounded operation-event test evidence for certified business/operator
   endpoints.
3. The gate now blocks stale Gateway-publication truth: only endpoints with
   implemented bounded read-only `lotus-gateway` publication may cite Gateway
   publication, and those ledger entries must name the exact Gateway route while
   preserving Workbench, data-product, client-ready publication, and
   supported-feature boundaries.
4. `tests/unit/test_endpoint_certification_gate.py` covers current pass behavior
   and failure cases for missing capabilities, weak unsupported-boundary text,
   missing operation-event evidence, stale Gateway-publication claims, stale
   test references, and malformed JSON examples.
5. `docs/operations/api-certification.md`, README, repository context, quality
   scorecard, CI quality guide, and wiki source now describe the stronger gate.

This slice also hardens repository hygiene:

1. `scripts/repository_hygiene_gate.py` validates tracked Git files and fails if
   generated Python cache files, local coverage artifacts, build outputs,
   dependency directories, local environment files, logs, or local databases are
   committed.
2. `make repository-hygiene-gate` runs the validator directly and `make lint`
   runs it as a blocking local and GitHub lane gate.
3. `scripts/ci_contract_gate.py` requires the target and lint call so future
   agents cannot silently remove repository hygiene enforcement.
4. `tests/unit/test_repository_hygiene_gate.py` covers current pass behavior and
   generated/cache/local-artifact failure cases.
5. README, repository context, enterprise-readiness guidance, quality
   scorecard, and wiki source now describe the new source-tree hygiene control.

This slice also hardens API/runtime architecture boundaries:

1. `src/app/api/runtime_dependencies.py` is the only API-layer module permitted
   to import `app.runtime` composition helpers.
2. Route modules now depend on that facade instead of importing runtime
   repository providers, source-ingestion runtime, outbox publisher wiring,
   proof-artifact configuration, or downstream realization clients directly.
3. `scripts/architecture_boundary_gate.py` now blocks direct `app.runtime`
   imports from API routes while allowing only the explicit facade.
4. `tests/unit/test_ci_enforcement_contract.py` covers the allowed facade and
   the failure case for a route that imports runtime composition directly.
5. API docs, architecture rules, repository context, RFC evidence, quality
   scorecard, and wiki source describe the stronger boundary without promoting
   any product, data-mesh, Workbench, downstream, or supported-feature claim.

This slice also hardens generated-artifact cleanup:

1. `scripts/clean_generated_artifacts.py` provides a testable cleanup utility
   for ignored Python bytecode caches, local coverage files, build/dist output,
   and HTML coverage output while pruning `.git`, `.venv`, and dependency
   cache directories.
2. `make clean` now calls the utility instead of an inline one-off command, so
   future cleanup behavior can be unit-tested and reviewed.
3. `scripts/ci_contract_gate.py` requires the Makefile cleanup target to call
   the governed utility, preventing future agents from weakening local cleanup
   ergonomics while leaving repository hygiene claims in place.
4. `tests/unit/test_clean_generated_artifacts.py` covers cleanup planning,
   deletion behavior, and pruned-directory safety.
5. README, repository context, enterprise-readiness guidance, CI quality guide,
   quality scorecard, and wiki source now describe the cleanup path without
   promoting any product capability.

GitHub issue `#310` extends that generated-artifact policy to Docker build
context hygiene. `.dockerignore` excludes coverage data, `coverage.xml`,
`sbom.cdx.json`, `output`, and generated quality reports, and
`scripts/ci_contract_gate.py` rejects Docker-context parity drift so local
validation byproducts cannot silently become builder inputs.

This slice also hardens no-sensitive-content evidence guarding:

1. `scripts/no_sensitive_content_guard.py` now exposes a testable
   `validate_no_sensitive_content(...)` validation function while preserving
   the blocking CLI behavior used by `make no-sensitive-content-guard`.
2. The guard scans local evidence, log, and output artifacts for forbidden
   sensitive marker names covering portfolio, client, account, holding,
   transaction, request-body, response-body, and raw entitlement failure
   material before those artifacts become PR or wiki evidence.
3. `tests/unit/test_no_sensitive_content_guard.py` covers clean artifacts,
   forbidden marker detection, allowlisted documentation, and binary artifact
   handling so this blocking merge-path check has explicit pass/fail proof.
4. README, repository context, CI quality guide, RFC index, and wiki source now
   describe the stronger evidence-artifact guard without promoting any
   supported business feature.

This slice also hardens CI runtime provenance:

1. GitHub workflow actions are pinned to verified immutable upstream tag SHAs
   while retaining readable version comments for operator review.
2. `scripts/ci_contract_gate.py` now rejects floating action tags or branches,
   wrong verified SHAs for approved actions, missing version provenance
   comments, and weakened Makefile test targets that ignore scoped
   `UNIT_TESTS`, `INTEGRATION_TESTS`, or `E2E_TESTS` overrides.
3. `tests/unit/test_ci_contract_gate.py` covers current repository pass
   behavior plus failure cases for floating tags, unverified SHAs, missing
   provenance comments, weakened cleanup wiring, and unscoped test target
   regression.
4. The CI quality guide, enterprise-readiness standard, README, repository
   context, quality scorecard, and wiki source now describe the immutable
   action-pin and scoped test-target expectations for future agentic work.

This slice also hardens CI lint-gate contract coverage:

1. `scripts/ci_contract_gate.py` now treats the current `make lint` gate set as
   an explicit contract for AI model-risk operations proof, Risk
   high-volatility and drawdown live-proof gates, Advise mandate/restriction
   live-proof gates, aggregate implementation-proof readiness generation, and
   runtime trust telemetry preview generation.
2. The gate fails if a future change removes these blocking calls from
   `make lint` or replaces the target scripts with weak placeholders.
3. `tests/unit/test_ci_contract_gate.py` covers those failure cases so the
   enforcement itself has pass/fail evidence.
4. This is CI enforcement only. It does not promote supported features,
   data-mesh certification, live source ingestion, Workbench support, client
   publication, or production-ready claims.

This slice also hardens repo-native CI test and coverage enforcement:

1. The Makefile now exposes suite-specific coverage targets:
   `make test-unit-coverage`, `make test-integration-coverage`, and
   `make test-e2e-coverage`.
2. `make test-coverage` runs those suite-level targets before
   `make coverage-gate`, preserving the combined coverage gate while keeping
   suite execution on the same Makefile surface used locally.
3. Feature, PR Merge, and Main Releasability workflows call repo-native test
   and coverage targets instead of raw workflow `pytest` commands.
4. `scripts/ci_contract_gate.py` now rejects raw workflow `pytest` shortcuts
   and weakened coverage-target selectors, so future agents cannot make GitHub
   appear green while bypassing local quality governance.
5. `tests/unit/test_ci_contract_gate.py` and
   `tests/unit/test_ci_enforcement_contract.py` cover current pass behavior,
   raw workflow shortcut rejection, and scoped coverage-target failure cases.
6. This is CI enforcement only. It does not promote supported features,
   data-mesh certification, live source ingestion, Workbench support, client
   publication, or production-ready claims.

This slice also hardens the local aggregate command model after GitHub issue
`#263` showed `make ci` could be cited as a local green signal without
PostgreSQL runtime or Docker/release proof:

1. `make ci` remains the broad local aggregate for lint, typecheck, contract
   gates, OpenAPI, migrations, integration/e2e/coverage, and dependency audit.
   It is not, by itself, PostgreSQL runtime, Docker build, container smoke,
   image scan, SBOM, or release-evidence proof.
2. `make ci-release` is the governed full-lane local command. It runs `make ci`
   plus `postgres-integration-gate`, `docker-build`,
   `container-runtime-smoke`, `container-image-scan`, and `release-sbom`.
3. `scripts/ci_contract_gate.py` fails if `ci-release` drops PostgreSQL,
   Docker build, container smoke, image scan, or SBOM proof dependencies.
4. `tests/unit/test_ci_contract_gate.py` and
   `tests/unit/test_ci_enforcement_contract.py` prove the command split and
   full-lane dependency guard.
5. GitHub PR Merge Gate and Main Releasability continue to call repo-native
   targets rather than opaque inline proof commands.
6. This is command-model governance. `make ci-release` should be cited only
   when local Docker and disposable PostgreSQL prerequisites were actually
   available and run.

This slice also hardens downstream realization contract governance:

1. `contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`
   is now the machine-readable source of truth for planned Advise, Manage, and
   Report handoff contract posture.
2. `scripts/downstream_realization_contract_gate.py` validates required
   contract rows, source-authority ownership, planned target-route posture,
   not-certified route fit, planned adapter status, evidence references,
   blockers, source-of-truth paths, and no premature route-existence,
   downstream-execution, or supported-feature claims.
3. `make downstream-realization-contract-gate` runs the validator directly,
   `make lint` runs it as a blocking local/GitHub lane gate, and
   `scripts/ci_contract_gate.py` prevents future agents from removing the
   target or lint call.
4. `tests/unit/test_downstream_realization_contract_gate.py` covers current
   pass behavior plus premature certification, contract drift, current-route
   evidence, missing blockers, and broken source-of-truth paths.
5. README, repository context, API certification docs, downstream realization
   runbook, CI quality guide, quality scorecard, RFC index, and wiki source now
   describe the gate without promoting downstream realization.

This slice also hardens scheduled source-ingestion worker proof governance:

1. `scripts/source_ingestion_scheduled_worker_contract_gate.py` validates the
   scheduled worker check summary, proof artifact schema, entrypoint presence,
   Compose worker service, and source-sensitive field exclusions.
2. `make source-ingestion-scheduled-worker-check` runs the validator directly,
   `make lint` runs it as a blocking local/GitHub lane gate, and
   `scripts/ci_contract_gate.py` prevents future agents from removing the
   target or lint call.
3. `tests/unit/test_source_ingestion_scheduled_worker.py` and
   `tests/unit/test_source_ingestion_scheduled_worker_contract_gate.py` cover
   current pass behavior, invalid proof behavior, source-safe output, and
   missing Core runtime configuration in run mode.
4. README, repository context, source-ingestion runbook, API certification
   docs, observability docs, quality guides, RFC evidence, and wiki source now
   describe the scheduled worker deploy-contract proof without promoting live
   Core ingestion, certified long-running scheduling, Gateway/Workbench,
   data-product certification, or supported-feature support.

This slice also hardens workflow/operator API error-model polish:

1. `src/app/api/problem_details.py` centralizes product-safe RFC-7807
   OpenAPI response metadata and common permission/request failure helpers for
   workflow and operator route modules.
2. `src/app/api/candidate_lifecycle.py`, `src/app/api/review_workflow.py`,
   `src/app/api/conversion_governance.py`, and
   `src/app/api/report_evidence.py` now compose concrete 400/403/404/409
   `ProblemDetails` examples from the shared helper while preserving their
   route-specific error codes, descriptions, and idempotency/state semantics.
3. `tests/unit/test_api_problem_details.py` proves the shared helper shape and
   verifies OpenAPI examples for lifecycle, review, feedback, conversion, and
   report evidence-pack workflow routes.
4. `src/app/api/README.md`, `docs/operations/api-certification.md`, RFC-0002
   Slice 10 evidence, and `wiki/API-Surface.md` now describe the pattern.
5. This is API contract and design-modularity hardening only. It does not add a
   runtime microservice boundary, Gateway/Workbench mutation support, client
   publication, data-mesh certification, or supported-feature promotion.

This slice also hardens runtime Docker and release image identity governance:

1. The Dockerfile now builds from a governed `PYTHON_BASE_IMAGE` argument,
   installs the resolved runtime dependency lock before copying `src`, installs
   the local service package afterward with `--no-deps`, preserves `/app/src`
   on `PYTHONPATH`, copies only the runtime source-ingestion worker entrypoints
   from `scripts/`, and runs the service as the non-root `lotus` user. After
   GitHub issue `#295`, the CI release-evidence contract also rejects
   source-before-dependency-install ordering and dependency reinstall drift.
2. `Makefile` exposes `CONTAINER_BASE_IMAGE` and passes it into the Docker
   build. PR merge and main releasability workflows expose both
   `CONTAINER_BASE_IMAGE` and pinned `TRIVY_IMAGE` values so release evidence
   records the base image and scanner identity instead of hiding those choices
   inside ad hoc workflow strings. Main Releasability now also pulls and
   inspects both images, then writes resolved immutable base/scanner digests to
   `release-evidence.json`.
3. `scripts/ci_release_evidence_contract.py` and
   `scripts/ci_contract_gate.py` now reject development extras in the runtime
   image, bulk `COPY scripts ./scripts`, root runtime execution, missing worker
   entrypoints, missing base-image build-arg wiring, and missing release
   image-identity evidence.
4. `tests/unit/test_ci_release_evidence_contract.py` and
   `tests/unit/test_ci_contract_gate.py` cover current pass behavior and
   failure cases for dev-tooling, root-user, release-evidence drift, missing
   image-provenance resolution, and missing digest fields.
5. This is runtime and CI hardening only. It does not certify production
   capacity, live source ingestion, Workbench support, data-product readiness,
   client publication, or supported-feature promotion.

This slice also hardens packaged container startup proof after GitHub issue
`#270` showed Docker release gates built and scanned the image without starting
the packaged service:

1. `make container-runtime-smoke` now starts the built
   `backend-service:ci-test` image with governed host/container port, container
   name, startup timeout, and probe interval values.
2. `scripts/container_runtime_smoke.py` probes `/health` and `/health/live` for
   `200`, requires `/health/ready` to return reachable JSON with either `200`
   or the default-profile fail-closed `503`, prints container logs on startup
   failure, and removes the smoke container in all cases.
3. PR Merge Gate and Main Releasability run the smoke target after
   `make docker-build` and before image scan/release evidence can pass.
4. `scripts/ci_release_evidence_contract.py`,
   `scripts/ci_workflow_contract_expectations.py`, and focused tests reject
   missing smoke-target variables, missing Makefile target wiring, and missing
   PR/Main workflow calls.
5. This is packaged runtime entrypoint and health-surface proof only. It does
   not certify production deployment, live upstream source connectivity,
   Workbench support, data-product certification, client-ready publication, or
   supported-feature promotion.

This slice also hardens release SBOM scope after GitHub issue `#272` showed
Main Releasability uploaded an ambiguous CI-environment SBOM beside image scan
evidence:

1. `make release-sbom` now generates `sbom.cdx.json` from
   `requirements/runtime-resolved.lock.txt` with the pinned CycloneDX tool and
   project metadata, rather than inventorying the CI virtual environment or only
   the direct runtime dependency list.
2. Main Releasability records the built service image reference and local image
   id, then writes `sboms[]` release metadata with SBOM path, scope, target
   artifact, target artifact id, dependency source, project metadata,
   generator, format, and non-proof boundary.
3. `scripts/ci_release_evidence_contract.py`,
   `scripts/ci_workflow_contract_expectations.py`, and focused tests reject
   ambiguous `cyclonedx_py environment` SBOM generation, missing runtime
   lockfile source, missing reproducible/project metadata flags, and missing
   release-manifest SBOM target/scope fields.
4. `scripts/clean_generated_artifacts.py` and `.gitignore` treat the generated
   `sbom.cdx.json` as local release evidence, not repository source truth.
5. This is runtime Python dependency SBOM evidence only. It does not certify a
   full container-image SBOM, registry attestation, production signing,
   Workbench support, data-product certification, client-ready publication, or
   supported-feature promotion. Container OS and packaged-image vulnerability
   posture remains the Trivy image scan's scope.

This slice also hardens post-merge Main Releasability signal quality:

1. `main-releasability.yml` is now `workflow_dispatch` only. Normal merged PRs
   use `merged-pr-main-releasability.yml` as the authoritative post-merge
   dispatch path, and manual reruns still use the same dispatchable workflow.
2. `scripts/ci_contract_gate.py` requires the dispatch policy text and rejects
   reintroducing a `push` trigger on Main Releasability while the merged-PR
   dispatch helper remains active.
3. `tests/unit/test_ci_contract_gate.py` covers the duplicate-trigger
   regression by injecting a `push` trigger and proving the CI contract gate
   fails.
4. CI docs, repository context, quality scorecard, and wiki source now describe
   one authoritative post-merge release-proof run per normal merged PR instead
   of an expected push-cancelled / dispatch-success run pair.
5. This is CI signal-quality hardening only. It does not reduce required
   post-merge release proof, weaken `LOTUS_AUTOMERGE_TOKEN` posture, or hide
   real Main Releasability failures.

This slice also adopts GitHub Security-tab controls where they add durable
signal without widening lotus-idea's product boundary:

1. Repository settings now enable Dependabot alerts/security updates, secret
   scanning with push protection, private vulnerability reporting, and CodeQL
   default setup for GitHub-owned static analysis over Python and GitHub
   Actions. GitHub currently reports non-provider secret patterns and secret
   validity checks as disabled for this repository even after an admin API
   enable attempt, so they are advisory future controls and are not claimed as
   active release evidence.
2. `SECURITY.md` defines the supported security baseline, private
   vulnerability reporting path, source-safe report-content boundary, and
   lotus-idea product-ownership limits.
3. `.github/dependabot.yml` defines one grouped Python dependency-closure root
   update stream plus grouped GitHub Actions dependency monitoring, but routine
   version-update PRs are paused with `open-pull-requests-limit: 0` while RFC
   delivery is active. Dependency suggestions are manually regenerated or
   cherry-picked into the active implementation branch before repo-native gates.
   It deliberately does not open separate `/requirements` lock-only Python PRs.
4. `make dependency-refresh` is the governed follow-up path for Python
   dependency PRs: it installs from root pins without a stale runtime-lock
   constraint, then regenerates both `requirements/runtime-resolved.lock.txt`
   and the `requirements/requirements.txt` GitHub Dependency Graph mirror from
   the active runtime closure. Run
   `python -m scripts.refresh_runtime_dependency_locks --check` to verify
   committed lock truth before merge validation.
5. `scripts/github_security_posture_check.py` and
   `make github-security-posture-check` provide an operator-run live check for
   mutable GitHub Security settings, CodeQL `default` / `remote` posture,
   private vulnerability reporting, and zero open code-scanning,
   secret-scanning, and Dependabot alerts. The live check also warns when
   repo-authored Security-tab controls such as `SECURITY.md` or
   `.github/dependabot.yml` are not present on the default branch that GitHub
   renders publicly, preventing unmerged branch truth from being mistaken for
   active Security-tab posture.
6. `scripts/ci_contract_gate.py` requires the security policy, Dependabot
   coverage, and dependency refresh target wiring, while
   `tests/unit/test_security_tab_governance_contract.py` covers policy,
   client-data, dependency-ecosystem, lock-only stream, and PR-noise regression
   cases.
7. This is GitHub Security and CI-governance hardening only. It does not
   certify service-to-service authentication, platform entitlement proof, live
   threat monitoring, production incident response, or supported-feature
   promotion.

This slice also closes the HTTP request-size enforcement gap found through the
GitHub issue review loop:

1. `src/app/middleware/http_boundary.py` now measures the actual ASGI body
   stream for JSON write methods after header-level rejection checks and before
   route handlers process payloads.
2. Oversized bodies return the existing source-safe `413 request_too_large`
   `ProblemDetails` whether `Content-Length` is missing, accurate, or
   understated.
3. Accepted bounded JSON write bodies are replayed to downstream handlers so
   normal route behavior is preserved after middleware inspection.
4. `tests/integration/test_http_boundary.py` covers missing-`Content-Length`,
   understated-`Content-Length`, replay of accepted body streams, existing
   header-based oversized rejection, unsupported content type, trusted-host,
   CORS, configuration, and secure-header behavior.
5. This remains service-boundary hardening only. It is not a gateway/WAF
   replacement, rate limiter, production ingress proof, or supported-feature
   promotion.

This slice also closes the unsafe diagnostic-header propagation gap found
through the GitHub issue review loop:

1. `src/app/observability/correlation_context.py` defines the shared product-safe
   diagnostic identifier policy for correlation and trace ids: bounded length,
   strict characters, no blank values, no portfolio-like values, and no
   secret/token-like fragments.
2. `CorrelationIdMiddleware` preserves valid `X-Correlation-Id` and
   `X-Trace-Id` values, but replaces missing, blank, overlong, malformed,
   portfolio-like, or token-like values with generated `corr-*` and `trace-*`
   identifiers before writing request state or response headers.
3. Request diagnostic and operation-event logging reject unsafe diagnostic ids
   supplied outside the middleware path, and the shared downstream HTTP client
   sanitizes non-HTTP caller-provided ids before propagating headers.
4. Unit and integration tests cover valid preservation, generated missing ids,
   blank/overlong/portfolio-like/token-like/malformed replacement, log safety,
   and downstream header replacement.
5. This is observability and service-boundary hardening only. It does not
   certify service-to-service authentication, trusted ingress, Gateway/Workbench
   support, production monitoring, client publication, or supported-feature
   promotion.

This slice also hardens workflow coverage enforcement after issue review showed
raw workflow coverage commands duplicating the repository gate:

1. `scripts/coverage_gate.py` now accepts `--coverage-dir`, and the Makefile
   exposes `COVERAGE_DATA_DIR ?= .` so local runs and downloaded GitHub
   coverage artifacts use the same gate implementation.
2. PR Merge and Main Releasability combined coverage jobs now call
   `make coverage-gate COVERAGE_DATA_DIR=coverage-data` instead of invoking
   `coverage combine` and `coverage report --fail-under=99` directly.
3. `scripts/ci_contract_gate.py` rejects raw workflow-level coverage combine
   and report shortcuts, and unit tests cover Makefile target drift plus PR and
   main workflow regression cases.
4. This is CI enforcement only. It does not weaken the 99% coverage threshold,
   expand product support, certify live data products, or promote supported
   features.

This slice also adds report-only CI timing/signal evidence after issue review
showed workflow duration and failure signal existed only in GitHub UI/API:

1. `scripts/ci_signal_evidence.py` generates source-safe
   `ci-signal-evidence.json` from GitHub run-job metadata, including job and
   step duration, conclusion, workflow feedback time, longest-job duration,
   failure category, and `thresholdEnforced: false`. The artifact reports
   first-job-start to last-job-completion wall-clock time as
   `workflowWallClockSeconds` and `criticalPathSeconds`; it reports the largest
   single job separately as `longestJobName` and `longestJobSeconds`.
2. Feature Lane, PR Merge Gate, and Main Releasability upload lane-specific CI
   signal evidence artifacts through `if: always()` jobs with `actions: read`.
3. Main Releasability `release-evidence.json` references
   `main-releasability-ci-signal-evidence` and `ci-signal-evidence.json` so
   release evidence can link to timing/support evidence without embedding live
   GitHub API payloads.
4. `make ci-signal-evidence-contract-gate`, `scripts/ci_contract_gate.py`, and
   unit tests validate schema/source-safety and block workflow wiring drift.
5. This is measured-baseline evidence only. It does not add duration
   thresholds, weaken existing CI gates, certify production capacity, or promote
   supported features.

This slice also adds duplicate implementation inventory and promotes the stable
zero-cluster baseline to blocking enforcement after GitHub issues `#296` and
`#309` showed repeated proof-helper bodies were invisible to the existing
file/function-size maintainability gate:

1. `make duplicate-implementation-inventory` runs
   `scripts/duplicate_implementation_inventory.py` to scan exact function-body
   duplicates across `src/app` and `scripts` in report-only mode.
2. `make duplicate-implementation-gate` runs the same scanner with
   `--fail-on-duplicates`, reports `thresholdEnforced: true`, and is wired into
   `make lint` as the current zero-cluster regression blocker.
3. The initial six-line baseline scanned 1,750 functions and reported 31 exact
   duplicate clusters, including the known proof source-safety helper families.
4. The first follow-through refactors move proof source-safety traversal into
   `scripts/proof_source_safety.py` and live-proof generator timeout/output
   plumbing plus generated-at UTC parsing into `scripts/proof_generator_io.py`,
   then consolidate proof timestamp validation, make-target evidence checks,
   and cross-repository file-evidence checks through
   `src/app/application/source_safe_cross_repo_proof.py`, and centralize AST
   call-name parsing for contract gates in `scripts/ast_gate_helpers.py`, and
   centralize Core live-proof base URL resolution in
   `scripts/proof_generator_io.py`, and centralize Advise/Manage proof evidence
   request construction in `scripts/proof_request_builders.py`, and centralize
   mutating API reason-code validation in `app.api.request_validation`, and
   centralize bounded API telemetry count buckets in
   `app.api.telemetry_buckets`, centralize caller-supplied signal response
   DTO projection in `app.api.signal_models.SignalEvaluationResponse`, and
   centralize application-layer portfolio-only signal review scopes in
   `app.application.access_scope`, and centralize source-reference/access-scope
   write-side payload projection in `app.ports.evidence_payloads`, and
   centralize API persistence-summary response projection in
   `app.api.persistence_summary`, and centralize API review access-scope DTOs
   in `app.api.access_scope_models`, and centralize blocked signal-result
   construction in `app.domain.signal_evaluation.blocked_signal_result`, and
   centralize optional proof-artifact JSON object loading in
   `app.runtime.proof_artifact_files`, and centralize source-product proof
   payload text-sequence normalization in
   `app.application.source_product_proof_values`, and centralize outbox
   contract forbidden-text traversal in `scripts.contract_text_guards`, and
   centralize operations-contract payload, operation, and label validation in
   `scripts.operations_contract_validators`; each
   proof gate, generator, contract gate, and API route retains family-specific
   policy/argument behavior, direct script execution remains supported, and the
   current measured baseline ignores pass/ellipsis-only protocol stubs, scans
   1,607 executable function bodies, and reports 0 exact duplicate clusters.
5. `scripts/ci_contract_gate.py` protects the report-only/blocking target split,
   strict flag, and `make lint` lane placement.
6. This is exact first-party implementation-body enforcement only. It does not
   block near-duplicates, generated-pattern similarity, protocol stubs,
   intentional tiny helpers, every repetition, or an LLM-based quality gate.

This slice also hardens Manage source-ref freshness vocabulary after issue
review showed a repeatable source-authority drift pattern:

1. `lotus_manage_sources.py` no longer maps `ready` freshness values to
   `EvidenceFreshness.CURRENT`; only explicit `current` and `same_day`
   freshness metadata certify current source refs.
2. Manage source-ref tests now cover `freshness`, `freshnessBucket`, and
   `freshness_bucket` values for `ready`, plus explicit current/same-day,
   stale, expired, missing, unavailable, and unrecognized vocabulary.
3. `source_observability_contract_gate.py` rejects future source adapters that
   infer current freshness from `ready` or other readiness/supportability,
   coverage, health-state, or data-quality predicates.
4. This is source-authority and data-mesh contract hardening only. It does not
   move Manage supportability ownership into `lotus-idea`, certify live source
   ingestion, promote Workbench support, or widen downstream execution
   authority.

This slice also hardens the advisor review queue durable read path after issue
review showed the API page contract was bounded while PostgreSQL still used a
whole-store snapshot:

1. `ReviewQueueProjectionRepository` and `ReviewQueueRepositoryPage` define an
   internal bounded repository page interface; this is design modularity only,
   not a new runtime service boundary.
2. `PostgresIdeaRepository.review_queue_candidate_page(...)` reads only
   `idea_candidate_record`, applies lifecycle/posture/supportability,
   caller-scope, stable score/created-time ordering, source-signal dedupe,
   counts, and `LIMIT`/`OFFSET` bounds before hydrating the page window.
3. Migration 001 now includes
   `idx_idea_candidate_record_review_queue_order`, and
   `migration_contract_gate.py` requires that index so the hot queue path stays
   index-backed.
4. After GitHub issue `#287`, Migration 001 also includes narrow expression
   indexes for the exact tenant/book/portfolio/client `access_scope` JSONB
   predicates used by scoped advisor queue reads:
   `idx_idea_candidate_record_scope_tenant`,
   `idx_idea_candidate_record_scope_book`,
   `idx_idea_candidate_record_scope_portfolio`, and
   `idx_idea_candidate_record_scope_client`. This preserves design modularity
   inside the existing repository adapter; there is no runtime queue-service
   split because workload, failure-isolation, ownership, and operability
   evidence do not justify a distributed boundary.
5. Review queue application tests prove repository-side page projections bypass
   `snapshot()` for ordinary page reads and clear only the
   `repository_side_queue_pagination_not_certified` blocker when durable
   storage exposes the projection. PostgreSQL adapter tests prove the page read
   does not select outbox, downstream submission, report evidence-pack, or AI
   lineage tables, and now prove scoped count/page reads retain eligibility
   filters, all indexed scope predicates, stable ordering, count, and
   `LIMIT`/`OFFSET` bounds.
6. This is production-scale internal read-path hardening only. It does not
   certify Workbench support, data-product promotion, PM/compliance queue
   support, client-ready publication, or supported-feature promotion.

This slice also applies the same bounded durable-read pattern to the outbox
delivery readiness path after issue review showed operator readiness was still
counting outbox state through whole-store repository snapshots:

1. `OutboxDeliveryReadinessProjectionRepository` and
   `OutboxDeliveryReadinessRepositorySummary` define an internal readiness
   projection contract for aggregate outbox status, expired-lease, and
   delivery-ready counts; later durable retry scheduling narrows failed-event
   readiness to rows whose next-attempt timestamp is due. This is design
   modularity only, not a separate runtime outbox service.
2. `PostgresIdeaRepository.outbox_delivery_readiness_summary(...)` reads
   aggregate counts directly from `idea_outbox_event`, while
   `PostgresIdeaRepository.outbox_events_for_delivery(...)` now uses a bounded
   outbox-table query for worker-ready events instead of hydrating an
   `IdeaRepositorySnapshot`.
3. Readiness application tests prove the projection bypasses `snapshot()` and
   delivery-ready event hydration. PostgreSQL repository tests prove the
   ordinary readiness summary reads only `idea_outbox_event` and does not touch
   candidate, audit, review, downstream submission, conversion, report
   evidence-pack, or AI lineage tables.
4. This is production-scale internal operator-readiness hardening only. It does
   not certify external broker publication, downstream delivery, platform mesh
   event publication, Gateway/Workbench support, client-ready publication, or
   supported-feature promotion.

This slice also applies the same bounded durable-read pattern to the
candidate-detail path after issue review showed other bounded API reads could
still depend on whole-store repository snapshots:

1. `CandidateDetailProjectionRepository` defines an internal candidate-detail
   projection contract; this is design modularity only, not a new runtime
   service boundary.
2. `PostgresIdeaRepository.candidate_record_by_id(...)` reads the requested
   candidate from `idea_candidate_record` and attaches lifecycle, audit,
   review, feedback, conversion, report-evidence, and AI-lineage rows through
   candidate-id or conversion-intent-id filters instead of hydrating unrelated
   repository state.
3. Candidate-detail application tests prove the projection bypasses
   `snapshot()` while preserving entitlement-scope denial. PostgreSQL adapter
   tests prove the detail read does not select outbox, downstream submission,
   or idempotency tables and returns `None` without querying child tables when
   the candidate is missing.
4. This is production-scale internal read-path hardening only. It does not
   certify Workbench support, data-product promotion, client-ready
   publication, downstream authority, or supported-feature promotion.

This slice also applies the candidate-detail projection to adjacent workflow
prechecks after issue review showed several API-facing workflows still loaded a
whole repository snapshot just to find one candidate before domain evaluation:

1. `src/app/application/candidate_lookup.py` centralizes candidate lookup for
   application services and prefers `CandidateDetailProjectionRepository`
   before falling back to legacy/process-local `snapshot()` providers.
2. Review actions, feedback recording, conversion-intent requests, and AI
   explanation evaluation now use that helper before applying domain
   governance. This is internal design modularity only, not a new runtime
   service boundary.
3. Focused application tests prove each workflow can run against a
   projection-capable repository whose `snapshot()` method raises. The tests
   cover accepted review action lookup, feedback lookup, conversion-intent
   lookup, missing conversion candidate handling, and AI explanation lookup.
4. This is bounded pre-mutation lookup hardening only. Existing repository
   mutation methods still own idempotency, audit, lifecycle, conversion, and
   AI-lineage persistence until later write-path refactors add narrower write
   projections. It does not certify downstream execution, AI runtime
   execution, suitability/rebalance/report authority, client-ready
   publication, or supported-feature promotion.

This slice also applies the bounded durable-read pattern to downstream
realization lookup after issue review showed submission paths could still scan
repository snapshots before adapter calls:

1. `DownstreamSubmissionRepository` now exposes explicit conversion-intent and
   report evidence-pack lookup methods used by the downstream realization
   application service before idempotency and adapter execution.
2. `PostgresIdeaRepository.conversion_intent_by_id(...)` and
   `PostgresIdeaRepository.report_evidence_pack_by_id(...)` query
   `idea_conversion_intent` and `idea_report_evidence_pack_request` directly,
   while `candidate_record_for_conversion_intent(...)` resolves the candidate
   through a bounded conversion-intent lookup plus the existing
   candidate-detail projection.
3. `PostgresIdeaRepository.downstream_submission_by_idempotency_key(...)` now
   queries `idea_downstream_submission` by primary-key idempotency key directly
   before replay/conflict handling instead of hydrating a whole repository
   snapshot.
4. Application tests prove downstream submission uses lookup methods without
   hydrating `snapshot()`. PostgreSQL tests prove lookup queries avoid
   candidate snapshots, outbox, conversion, report evidence-pack, AI-lineage,
   and unrelated state tables.
5. This is production-scale internal read-path hardening only. It does not
   certify downstream execution, route existence, suitability/rebalance/report
   authority, client-ready publication, or supported-feature promotion.

This slice also applies the bounded durable-read pattern to downstream
realization readiness counts after the same issue-review pattern showed
operator diagnostics should not pay whole-store snapshot cost for narrow
workflow totals:

1. `DownstreamRealizationReadinessProjectionRepository` and
   `DownstreamRealizationReadinessRepositorySummary` define an internal
   readiness-count projection for conversion intents, conversion outcomes, and
   report evidence-pack requests; this is design modularity only, not a
   separate downstream-realization runtime service.
2. `PostgresIdeaRepository.downstream_realization_readiness_summary(...)`
   queries only `idea_conversion_intent`, `idea_conversion_outcome`, and
   `idea_report_evidence_pack_request` for the operator readiness counts.
3. Application tests prove the readiness builder uses the projection without
   calling `snapshot()`. PostgreSQL tests prove the count query avoids
   candidate, audit, outbox, downstream submission, and AI-lineage tables.
4. This is production-scale internal operator-readiness hardening only. It does
   not certify downstream execution, route existence, suitability/rebalance/
   report authority, client-ready publication, Gateway/Workbench support, or
   supported-feature promotion.

This slice also applies the bounded durable-read pattern to runtime trust
telemetry after the same issue-review pattern showed operator diagnostics
should not hydrate whole repository snapshots for aggregate counts:

1. `RuntimeTrustTelemetryProjectionRepository` and
   `RuntimeTrustTelemetryRepositorySummary` define an internal projection for
   candidate count, source-authority/freshness/supportability/lifecycle
   buckets, workflow counts, lineage posture, data-quality posture, latest
   source generation time, and source as-of-date coverage; this is design
   modularity only, not a separate trust-telemetry runtime service.
2. `PostgresIdeaRepository.runtime_trust_telemetry_summary(...)` queries
   `idea_candidate_record`, `idea_review_decision`, `idea_feedback_event`,
   `idea_conversion_intent`, `idea_conversion_outcome`, and
   `idea_report_evidence_pack_request` for aggregate telemetry only.
3. Application tests prove preview/snapshot builders use the projection without
   calling `snapshot()`. PostgreSQL tests prove the projection avoids audit,
   outbox, downstream-submission, lifecycle-history, idempotency, and
   AI-lineage tables.
4. This is production-scale internal trust-telemetry hardening only. It does
   not certify data products, platform mesh, Gateway/Workbench discovery,
   client-ready publication, or supported-feature promotion.

This slice also hardens the shared downstream HTTP policy after issue review
showed outbound calls had timeouts and safe failure mapping but no governed
retry/backoff contract:

1. `DownstreamClientConfig` now carries a bounded retry policy with disabled
   default behavior (`retry_max_attempts=1`), conservative retryable statuses
   (`429`, `502`, `503`, `504`), capped backoff, and optional `Retry-After`
   handling.
2. `DownstreamJsonClient` retries only timeouts, transport failures, and the
   configured transient statuses. `POST` retries require an idempotency key
   unless the runtime explicitly marks the boundary as read-only source-query
   traffic.
3. Downstream realization, Core source-ingestion, and outbox broker runtime
   wiring expose fail-closed retry/backoff environment settings. Outbox
   publication now propagates the event idempotency fingerprint as the
   outbound `Idempotency-Key`; source-ingestion Core query/control-plane
   clients are explicitly marked as read-only before permitting retryable
   `POST` calls without an idempotency key.
4. Unit tests cover timeout/status retry success, retry exhaustion,
   `Retry-After` capping, non-retryable `4xx` behavior, POST idempotency
   gating, header preservation, downstream timeout mapping, source-ingestion
   runtime config, and outbox idempotency propagation.
5. This is internal resilience hardening only. It does not certify live Core
   ingestion, external broker publication, downstream route existence,
   downstream execution, report materialization, client-ready publication,
   Gateway/Workbench support, or supported-feature promotion.

GitHub issue `#312` extends that source-ingestion resilience hardening to
route-owned runtime cleanup. `POST /api/v1/source-ingestion/run-once` now closes
its owned `SourceIngestionRuntime` after accepted and source-unavailable batch
execution, while durable-repository and runtime-configuration blockers that
never construct a runtime remain unchanged. This is resource lifecycle proof
only; it does not certify live Core ingestion, data-mesh promotion,
Gateway/Workbench support, or supported-feature readiness.

This slice also hardens outbox-delivery run-once operator identity after
GitHub issue `#271` showed privileged run-once actions needed explicit
API-level run identity before external side effects:

1. `POST /api/v1/outbox-delivery/run-once` now requires the shared
   `Idempotency-Key` validation path after caller authorization and before
   durable repository, broker, or event-claim work.
2. The application layer records the operator run request through the repository
   idempotency ledger before claiming outbox events. Same-key/same-safe-request
   calls return `runStatus=replayed` without mutation, while same-key/different
   safe request reuse returns `409 idempotency_conflict` without mutation.
3. The API returns and logs only a source-safe `operatorRunReference` derived
   from the run identity. Raw idempotency keys, event ids, broker payloads, and
   downstream payloads are not exposed and are not Prometheus labels.
4. Unit and integration tests prove missing key rejection, replay without
   mutation, conflict without mutation, source-safe response posture,
   permission ordering, and operation-event attributes.
5. This is internal operator-action hardening only. It does not certify
   external broker publication, downstream delivery, platform mesh event
   publication, Gateway/Workbench support, client-ready publication, or
   supported-feature promotion.

This slice also hardens durable outbox retry scheduling after GitHub issue
`#297` showed failed events could be reclaimed immediately on every polling
pass:

1. `OutboxEventRecord` now carries source-safe failure timing and
   `next_attempt_at_utc` eligibility. Retryable failed events require
   first/last failure timing plus a future next-attempt timestamp; dead-lettered
   events retain first/last failure timing and cannot carry a next-attempt
   timestamp.
2. The domain and PostgreSQL delivery paths compute deterministic capped retry
   eligibility, starting at 60 seconds and capping at 900 seconds. Failed rows
   below the retry limit are not delivery-ready until the durable timestamp is
   due; expired leases remain immediately recoverable.
3. PostgreSQL claim/readiness queries use `status` plus `next_attempt_at_utc`
   predicates and the migration contract now requires
   `idx_idea_outbox_event_retry_due`. Retry claims clear only the due timestamp
   and lease fields needed for the active attempt, preserving first/last
   failure timing until successful publication clears the failure lifecycle or
   dead-letter closure retains final failure evidence.
4. Unit and integration tests cover immediate no-reclaim behavior, due retry
   behavior, retry-to-dead-letter behavior, publication cleanup, repository-side
   readiness counts, and Postgres adapter parity.
5. This is internal outbox operability hardening only. It does not certify
   external broker publication, downstream delivery, platform mesh event
   publication, Gateway/Workbench support, client-ready publication, or
   supported-feature promotion.
