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

Issue `#346` adds deterministic release-compliance review evidence. The
repository now reconciles exact runtime and CI locks to a versioned SPDX policy,
generates notices reproducibly, fails closed on unapproved or incomplete
exceptions, packages license material, and binds policy/NOTICE/SBOM truth to
the digest-pinned release manifest. Focused mutation tests cover direct and
transitive drift, unknown and denied licenses, conditional obligations,
approval evidence, expiry, notices, external components, assets, and release
binding. Legal approval and base-image package rights remain external review
truth; a passing engineering gate cannot certify either.

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
   preserving Workbench, data-product, external-publication authority, and
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

1. `scripts/source_ingestion_scheduler/contract_gate.py` validates scheduler
   configuration, source-contract and deployment-evidence schemas, entrypoint
   and Compose presence, digest reconciliation, retired-path absence, and
   source-sensitive field exclusions.
2. `make source-ingestion-scheduled-worker-check` runs the validator directly,
   `make lint` runs it as a blocking local/GitHub lane gate, and
   `scripts/ci_contract_gate.py` prevents future agents from removing the
   target or lint call.
3. `tests/unit/test_source_ingestion_scheduled_worker.py` and
   `tests/unit/source_ingestion_scheduler/` cover scheduler behavior,
   non-clearing static evidence, deployment identity reconciliation, unknown
   fields, class substitution, digest drift, rollout ordering, source-safe
   output, and missing Core runtime configuration in run mode.
4. README, repository context, source-ingestion runbook, API certification
   docs, observability docs, quality guides, RFC evidence, and wiki source now
   distinguish scheduler `source_contract` and `deployment` evidence without
   promoting scheduled execution, live Core ingestion, certified long-running
   scheduling, Gateway/Workbench, data-product certification, or
   supported-feature support.

This slice also hardens workflow/operator API error-model polish:

1. `src/app/api/problem_details.py` centralizes product-safe RFC-7807
   OpenAPI response metadata and common permission/request failure helpers for
   workflow and operator route modules. GitHub issue `#308` extends this
   contract so generated OpenAPI publishes `ProblemDetails` examples under
   both `application/json` and `application/problem+json`.
2. `src/app/api/candidate_lifecycle.py`, `src/app/api/review_workflow.py`,
   `src/app/api/conversion_governance.py`, and
   `src/app/api/report_evidence.py` now compose concrete 400/403/404/409
   `ProblemDetails` examples from the shared helper while preserving their
   route-specific error codes, descriptions, and idempotency/state semantics.
3. `src/app/api/signal_api_support.py` and the high-cash persist route no
   longer carry route-local `ProblemDetails` OpenAPI dictionaries; they compose
   shared metadata helpers so signal-family 400/403 and persist 400/403/409
   responses stay aligned with the media-type contract.
4. `tests/unit/test_api_problem_details.py` proves the shared helper shape and
   verifies OpenAPI examples for lifecycle, review, feedback, conversion,
   downstream submission, signal, and report evidence-pack workflow routes.
   `scripts/openapi_problem_details_example_gate.py` blocks future public
   `ProblemDetails` responses that omit examples for either media type.
5. `src/app/api/README.md`, `docs/operations/api-certification.md`, RFC-0002
   Slice 10 evidence, and `wiki/API-Surface.md` now describe the pattern.
6. This is API contract and design-modularity hardening only. It does not add a
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

GitHub issue `#342` closes a remaining release-identity contradiction. An OCI
image cannot embed its own final registry manifest digest because the embedded
value changes the digest. `lotus.image-identity.v1` therefore separates the
image's immutable build identity from registry/deployment identity. Docker OCI
labels carry commit, branch, timestamp, repository, run, build ID, contract,
and binding authority; they no longer carry a placeholder self-digest.

Main Releasability resolves the digest after its single push, pulls and runs
that exact digest reference, captures labels and `/version`, and validates the
release manifest, Kubernetes reference, signature subject, provenance/SBOM
attestation subjects, and runtime digest through
`make release-image-identity-contract-gate`. Local/PR `/version` responses use
null digest fields and explicit `local_unpublished` posture. Production-like
readiness fails closed for missing, malformed, partial, placeholder, or
mismatched digest bindings. The same image is promoted without rebuild or
post-push mutation. This is internal runtime/CI modularity, not another service.

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
   Workbench support, data-product certification, external-publication authority, or
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
   Workbench support, data-product certification, external-publication authority, or
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
   policy/argument behavior, direct script execution remains supported, and
   issue `#614` keeps report-only quality baseline generation aligned with the
   blocking scanners: pass/ellipsis-only protocol stubs are excluded before
   reporting executable function rows, baseline paths are POSIX-normalized for
   deterministic Windows/Linux evidence, the current local generated quality
   baseline reports 9,252 executable source/test/script function rows, and the
   current duplicate implementation gate reports 0 exact duplicate clusters
   across 2,953 source/script functions.
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
6. After GitHub issue `#316`, advisor queue readiness has a separate
   `ReviewQueueReadinessProjectionRepository` aggregate contract so durable
   PostgreSQL providers compute readiness counts over `idea_candidate_record`
   without hydrating whole repository snapshots or unrelated state families.
   The application keeps the deterministic snapshot fallback for process-local
   repositories and snooze-aware evaluations. This is design modularity inside
   the existing service, not a separate runtime queue-readiness process.
7. This is production-scale internal read-path hardening only. It does not
   certify Workbench support, data-product promotion, PM/compliance queue
   support, external-publication authority, or supported-feature promotion.

GitHub issue `#332` further hardens that bounded read path with a real temporal
snapshot contract:

1. `evaluatedAtUtc` is an inclusive candidate-creation boundary in both
   in-memory and PostgreSQL paths; readiness counts use the same boundary.
2. Continuation pages require opaque identity bound to evaluation time, scope,
   ranking policy, and visible candidate state. Stable 400/409 ProblemDetails
   prevent consumers from silently skipping or duplicating work.
3. PostgreSQL compares fingerprints around the page query, so an in-flight
   state change fails closed. Later-created candidates are excluded and do not
   invalidate a historical traversal.
4. `make review-queue-snapshot-contract-gate` blocks future command, port,
   adapter, SQL, API, response-model, or error-code drift.
5. Focused in-memory/fake-adapter tests and a real PostgreSQL runtime test prove
   exact-boundary inclusion, source-date non-reinterpretation, backdated insert
   conflict, and future-insert stability.
6. The change improves design modularity through a pure domain policy and
   bounded PostgreSQL mixin. There is no separate queue process because no
   scaling, isolation, ownership, or operability evidence justifies one.

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
   event publication, Gateway/Workbench support, external-publication authority, or
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

This slice also bounds review, feedback, and conversion-intent idempotency
prechecks after issue review showed replay/conflict handling still loaded whole
repository snapshots:

1. `src/app/infrastructure/postgres_idempotency_lookup.py` defines a bounded
   `idea_idempotency_record` lookup by idempotency key; this is design
   modularity inside the existing repository adapter, not a runtime service
   split.
2. `PostgresIdeaRepository.precheck_review_mutation(...)` and
   `precheck_conversion_mutation(...)` now evaluate replay/conflict decisions
   from that idempotency row and hydrate only the associated candidate through
   the existing candidate-detail projection. Feedback uses the review precheck
   path through the same repository method.
3. PostgreSQL tests prove review replay, review conflict, conversion replay,
   and conversion conflict prechecks use `WHERE idempotency_key = %s`, use
   candidate-detail projection, and avoid broad candidate scans, outbox rows,
   and downstream-submission rows.
4. Accepted mutations still use the repository mutation path and keep existing
   idempotency, audit, lifecycle, conversion, and outbox behavior. This does not
   certify production storage, downstream authority, Workbench support,
   data-product promotion, or supported-feature promotion.

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
   authority, external-publication authority, or supported-feature promotion.

This slice also hardens AI explanation workflow-pack identity after issue
review showed the runtime API accepted arbitrary caller-supplied pack id,
version, and evaluator references:

1. `app.domain.ai_governance` now owns one governed idea-explanation workflow
   pack contract. The public runtime request identity
   `lotus-ai:idea-explanation:v1` / `v1` /
   `lotus-ai:governed-verifier:v1` deliberately maps to the proof identity
   `idea_explanation.pack@v1`.
2. AI explanation command construction and request building fail closed for any
   unregistered pack identity before candidate lookup or lineage persistence.
   The API maps this to product-safe `400 invalid_ai_workflow_pack` without
   echoing caller-supplied workflow text, candidate-sensitive details, prompts,
   or provider output.
3. The AI workflow-pack registration proof now reuses the same domain contract
   values for proof identity, workflow authority owner, and AI capability owner
   instead of duplicating string literals.
4. Unit and integration tests prove canonical requests still pass while
   noncanonical `workflowPackId`, `workflowPackVersion`, and `evaluationRef`
   each fail independently.
5. This is contract governance and design modularity inside the existing
   `lotus-idea` runtime. It does not certify `lotus-ai` runtime execution,
   provider calls, prompt/RAG infrastructure, Workbench support, client-ready
   publication, or supported-feature promotion.

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
   report authority, external-publication authority, Gateway/Workbench support, or
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
   external-publication authority, or supported-feature promotion.

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
   downstream execution, report materialization, external-publication authority,
   Gateway/Workbench support, or supported-feature promotion.

GitHub issue `#312` extends that source-ingestion resilience hardening to
route-owned runtime cleanup. `POST /api/v1/source-ingestion/run-once` now closes
its owned `SourceIngestionRuntime` after accepted and source-unavailable batch
execution, while durable-repository and runtime-configuration blockers that
never construct a runtime remain unchanged. This is resource lifecycle proof
only; it does not certify live Core ingestion, data-mesh promotion,
Gateway/Workbench support, or supported-feature readiness.

The same resource-lifecycle pattern is applied to the sibling
outbox-delivery run-once operator action. `POST /api/v1/outbox-delivery/run-once`
now closes its route-owned broker publisher after execution begins, including
accepted, replayed, failed, and idempotency-conflict outcomes. This prevents
HTTP client resource leakage during repeated operator runs while preserving the
existing `not_certified` posture for live broker publication, downstream
consumer proof, platform-mesh event runtime publication, Gateway/Workbench support, and
supported-feature promotion.

GitHub issue `#314` hardens the cleanup pattern itself. Route-owned cleanup is
now best-effort after run-once execution begins: outbox publisher close failures
emit `publisher_cleanup_failed` with `cleanup_phase=publisher_close`, and
source-ingestion runtime close failures emit `runtime_cleanup_failed` with
`cleanup_phase=runtime_close`. Both diagnostics use `suppressed` operation
events and keep raw broker/Core details out of product responses, so already
computed completed, replayed, conflict, and bounded blocked outcomes remain
stable for operators.

GitHub issue `#313` adds the matching run-once capacity guard. The
source-ingestion command and manifest parser enforce a code-owned 100-item
ceiling over both `maxItems` and raw `workItems`; the API returns the
source-safe `source_ingestion_batch_limit_exceeded` blocker before Core calls or
repository mutation when a manifest exceeds that ceiling. Larger ingestion
remains a future chunked or scheduled workflow with capacity evidence, not a
run-once manifest escalation.

GitHub issue `#311` hardens operation metric source-authority vocabulary.
`OperationEvent` now rejects ungoverned `source_authority` labels before logs
or metrics are emitted, while allowing every code-owned `SourceSystem` value,
`lotus-idea`, and the aggregate `source-owned` label for mixed governed source
refs. The operation metric contract, operator workflow operations contract, and
dashboard/alert proof validators now consume the same runtime-owned vocabulary
instead of retaining partial hardcoded allowlists. This preserves source-safe
operator telemetry for `lotus-risk`, `lotus-performance`, `lotus-advise`,
`lotus-manage`, and other governed source labels without permitting client,
portfolio, account, request, response, raw entitlement, or local ad hoc labels.

GitHub issue `#315` hardens caller-supplied signal source contracts. Signal
routes now validate present source refs against the route-owned source system
and product-id contract before domain evaluation or candidate creation. Wrong
Risk, Performance, Core, Manage, or Advise source refs return product-safe
`400 invalid_request` responses, and rejection operation events use the expected
route source authority instead of the caller-supplied mismatched authority.
Missing refs still flow to the existing deterministic blocked evaluation
semantics.

GitHub issue `#507` hardens typed Advise source-product evidence and the
aggregate proof inventory:

1. Mandate/restriction and missing-risk-profile source contracts now bind the
   current Advise product declaration and trust telemetry by
   repository/ref/SHA-256.
2. Closed field sets, canonical source-authority digests, independent
   capability profiles, and authority-claim denial prevent a static contract
   from becoming live, advisory, deployment, production, or support proof.
3. A typed registry covers every aggregate proof CLI input and reconciles it
   with readiness arguments, evidence classification, issue ownership, and
   documentation inventory.
4. Repository hygiene requires capability-owned paths and prohibits the
   retired flat source-product modules, scripts, and tests.
5. The same-pattern scan opened issue `#508`; the current slice now separates
   non-clearing scheduler `source_contract` evidence from matching
   `deployment` evidence. No actual environment deployment receipt is
   fabricated by repository-local validation.

Issue `#513` closes the remaining design gap between the typed registry and
proof consumption. Registry lookup is unique and fail-closed, duplicate
payload/reference keys are blocking documentation errors, every blocker
mutation path is effect-aware, and source-ingestion proof currency is evaluated
once and shared across capability projections. The same-pattern scan found no
additional aggregate blocker-mutation family outside the standard and
opportunity consumers. This remains design modularity inside the existing
deployable; no process split is justified.

GitHub issue `#318` hardens review and feedback mutation entitlements. Review
actions and feedback now bind `ReviewActorContext` to trusted
`X-Caller-Tenant-Ids`, `X-Caller-Book-Ids`, `X-Caller-Portfolio-Ids`, and
`X-Caller-Client-Ids` headers and evaluate review/feedback governance against
persisted candidate access scope. Request bodies cannot assert `accessScope` or
`authorizedScope`. Missing or mismatched entitlement headers fail closed with
product-safe `403 permission_denied` responses and no raw portfolio/client
values in the response.

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
   publication, Gateway/Workbench support, external-publication authority, or
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
   publication, Gateway/Workbench support, external-publication authority, or
   supported-feature promotion.

## Issue 331 Supported-Feature Promotion Reconciliation

The structured supported-feature policy now lives in
`app.application.supported_feature_promotion`; the CLI gate is a thin adapter,
and implementation-proof readiness consumes the typed evaluation. A status
string cannot clear promotion blockers without valid current evidence.

`make supported-feature-promotion-contract-gate` statically requires both
callers to use the shared evaluator, rejects restoration of the former counter,
and binds API/generated output to the domain snapshot. Tests cover empty,
planned/not-applicable, malformed, missing path, stale review, missing/invalid
registry, and valid current evidence. This is design modularity inside the
existing runtime, not a publication service or supported-feature promotion.

## Issue 594 Blueprint Context Durability

Issue `#594` hardens RFC and agent context durability after Slice 00 still
depended on a local Downloads-path blueprint. The repo now owns
`docs/LOTUS_IDEA_BLUEPRINT.md` as the durable product and architecture anchor
for Lotus Idea's opportunity-intelligence definition, source-authority map,
owned/non-owned capability boundary, AI/human-governance posture, and current
non-claim rules.

README, repository context, architecture docs, wiki source, and Slice 00 now
link that repo-authored anchor so future RFC work does not rely on chat memory
or a local user file path. This is documentation/context hardening only. It
does not change API behavior, implement authentication or authorization,
certify live source ingestion, promote Gateway/Workbench support, certify data
products, prove downstream execution, certify AI provider runtime, publish
client-ready material, or promote a supported feature.

## Issue 596 Architecture Boundary Report Freshness

Issue `#596` hardens deterministic architecture-governance evidence. The
tracked `quality/architecture_boundary_report.json` artifact now uses
`architecture-boundary-report.v2` and binds the current `src/app` import
inventory plus the architecture rule digest through stable SHA-256
fingerprints.

`make architecture-boundary-report` regenerates the report, and
`make architecture-boundary-gate` now fails closed when the tracked report is
missing, malformed, generated with an unsupported schema, generated in the
wrong mode, stale against source/rule inputs, or tampered in status,
violations, repository, or rules. `make quality-baseline` records report
freshness status while keeping the broader size/function baseline report-only.

Focused unit tests cover current pass, regenerated-report pass, missing schema,
stale fingerprint, and tampered status. This clears only the Slice 19
architecture-report freshness gap. It does not certify runtime behavior,
Gateway/Workbench product support, data-mesh certification, production
deployment, client publication, or supported-feature promotion.

## Issue 598 E2E Managed TestClient Lifecycle

Issue `#598` hardens the existing managed FastAPI/Starlette `TestClient`
lifecycle guard after the integration suite was protected but the E2E smoke and
critical idea workflow tests could still construct unmanaged clients directly.

`scripts/testing/test_client_lifecycle_gate.py` now scans both `tests/integration`
and `tests/e2e`, and focused unit tests prove the current pass path plus the
unmanaged E2E import/construction failure path. The E2E suite now has an
autouse managed-client lifecycle fixture and its API callers use
`tests.support.http.managed_test_client`, preserving application lifespan and
deterministic shutdown cleanup for repeated local and CI runs.

This is test-governance hardening only. It does not change product runtime
behavior, API contracts, OpenAPI output, migrations, authentication,
authorization, Gateway, Workbench, source authority, or supported-feature
promotion. The current platform and backend skills already require governed
in-process API client lifecycle handling, so no central skill change is
justified; the durable prevention is the repository-native blocking gate and
repo-local documentation/context update.

PR `#599` merged by rebase to exact-main SHA
`68e9faf91a438c2b7315dd32c5b60431fa15d2e5`. Feature Lane, PR Merge Gate,
CodeQL, exact-main Main Releasability `29635864355`, exact-main CodeQL
`29635862048`, wiki publication `66194f1`, and strict wiki parity passed.
Issue `#598` is closed; local and remote implementation branches are absent.

## Issue 601 Service-Capacity Builder Maintainability

Issue `#601` hardens the Slice 19 maintainability posture for the
service-capacity proof path. The report-only quality baseline on exact main
`4c3e6c91fe9f04257a09212b866f97aa4a645792` listed
`src/app/application/service_capacity_baseline.py::build_service_capacity_baseline`
at `130` lines, exactly at the blocking source-function threshold. That
function built a source-safe capacity artifact but mixed request validation,
scenario summarization, protected evidence qualification, certification-blocker
derivation, artifact assembly, and schema validation in one review surface.

`src/app/application/service_capacity_baseline.py` now preserves the public
builder signature, artifact schema, evidence-class semantics, certification
blockers, and `supportedFeaturePromoted=false` posture while extracting:

1. capacity-baseline request validation,
2. governed scenario summarization,
3. protected PostgreSQL/dependency/load/resource/cost qualification,
4. blocker calculation through `CapacityEvidenceQualificationSet`,
5. source-safe artifact assembly.

Focused validation passed:

1. Ruff format/check for `src/app/application/service_capacity_baseline.py`
   and `tests/unit/test_service_capacity_baseline.py`,
2. `make test-unit UNIT_TESTS=tests/unit/test_service_capacity_baseline.py`
   (`34` passed),
3. `make service-capacity-baseline-contract-gate`,
4. `make maintainability-gate`,
5. `make duplicate-implementation-gate`,
6. `make quality-baseline`.

The same-pattern scan covered source maintainability hotspots, duplicate
implementation inventory, service-capacity tests, the service-capacity
contract gate, the codebase review ledger, and the GitHub issue closure
matrix. `build_service_capacity_baseline` is reduced to `64` lines and is no
longer in the report-only top-function list. This is internal
production-readiness proof modularity only; it does not execute live load/soak,
certify capacity, certify platform cost attribution, certify downstream
execution, change API behavior, change migrations, prove Gateway/Workbench,
promote data products, or promote supported features. README, wiki, central
skills, and supported-features truth are unchanged by explicit scope decision.

PR `#602` merged by rebase to exact-main SHA
`2a2dc5d89d0e2c2284bf41e5b9f9ada373bec4a2`. Feature Lane, PR Merge Gate,
exact-main Main Releasability `29637109887`, and exact-main CodeQL
`29637107707` passed. Release evidence published
`ghcr.io/sgajbi/lotus-idea@sha256:d0893699122b9b51ba3ae6c03cc8927c5cdebd94087ca3fbf277a4fbe9a3f3c9`.
Issue `#601` is closed and the local and remote implementation branches are
absent after remote prune.

## Issue 603 Outbox Delivery Run-Once API Maintainability

Issue `#603` applies the #601/#602 learning to the adjacent operability and
architecture-boundary hotspot. The report-only quality baseline on exact main
`2a2dc5d89d0e2c2284bf41e5b9f9ada373bec4a2` listed
`src/app/api/outbox/delivery.py::post_outbox_delivery_run_once` at `129`
lines, one line below the blocking source-function threshold. The route is an
operator-facing run-once API and mixed caller construction, permission mapping,
idempotency validation, durable-write configuration, capacity posture,
delivery-time validation, publisher configuration, observed execution,
operation events, conflict/replay handling, and final response assembly in one
review surface.

`src/app/api/outbox/delivery.py` now preserves the public route signature,
OpenAPI contract, response schema, idempotency replay/conflict behavior,
publisher cleanup, SLO observation, operation-event posture, and
`supportedFeaturePromoted=false` semantics while extracting:

1. trusted caller construction,
2. product-safe permission failure mapping,
3. idempotency/run context construction,
4. durable-write, capacity, and UTC delivery-time preconditions,
5. fail-closed publisher configuration posture,
6. run-status response and operation-event mapping.

Focused validation passed:

1. Ruff format/check for `src/app/api/outbox/delivery.py`,
2. MyPy over `src/app/api/outbox/delivery.py`,
3. `make test-unit UNIT_TESTS=tests/unit/outbox/test_outbox_delivery.py`
   (`16` passed),
4. `make test-integration INTEGRATION_TESTS=tests/integration/outbox/test_delivery_readiness_api.py`
   (`16` passed),
5. `make maintainability-gate`,
6. `make duplicate-implementation-gate`,
7. `make quality-baseline`.

The same-pattern scan covered #601/#602 review evidence, open GitHub issues,
source maintainability hotspots, duplicate implementation inventory, outbox
delivery unit/integration tests, the codebase review ledger, the issue closure
matrix, and repository context. `post_outbox_delivery_run_once` is reduced to
`71` lines and is no longer in the report-only top-function list. The next
source hotspot, `src/app/api/review_workflow.py::record_review_action` at
`127` lines, is classified for later issue-backed review rather than widening
this PR. This is internal API-boundary modularity only; it does not certify
external broker runtime, downstream consumer execution, platform-mesh event
publication, Gateway/Workbench support, data-product support, client-ready
publication, or supported-feature promotion. README, wiki, supported-features,
OpenAPI, migrations, runtime topology, and central skills are unchanged by
explicit scope decision.

PR `#604` merged by rebase to exact-main SHA
`b83321e5bd7ee774a76e92a656400dd647634ab7`. Feature Lane, PR Merge Gate,
exact-main CodeQL `29638083923`, and exact-main Main Releasability
`29638086274` passed. Release evidence published
`ghcr.io/sgajbi/lotus-idea@sha256:4c9c66dd950c324ba7f2ff9e3a1c5c401438cca5236445a7b7c7e8b2a2e3325a`.
Issue `#603` is closed and the local and remote implementation branches are
absent after remote prune. Strict wiki parity passed with DiffCount `0`; no
wiki publication change was needed.

## Issue 606 Review-Action API Maintainability

Issue `#606` applies the #601/#603 same-pattern learning to the human-governance
review-action API boundary. The report-only quality baseline on exact main
`f357d263fb95c3b2ab08462844b54a0ec711b71b` listed
`src/app/api/review_workflow.py::record_review_action` at `127` lines. The
route mixed trusted caller construction, entitlement failure mapping,
idempotency lineage, application command construction, invalid-state telemetry,
invalid-request mapping, persistence problem mapping, operation events, final
response assembly, and no-supported-feature posture in one review surface.

`src/app/api/review_workflow.py` now preserves the public route signature,
OpenAPI metadata, response schema, idempotency lineage, entitlement semantics,
persistence decision mapping, operation-event posture, and
`supportedFeaturePromoted=false` semantics while extracting:

1. trusted caller and repository mutation-context construction,
2. review-action command construction and application execution,
3. permission and entitlement problem mapping,
4. state-conflict telemetry attributes and problem responses,
5. invalid-request problem responses,
6. persistence problem and success response assembly.

Focused validation passed:

1. Ruff over `src/app/api/review_workflow.py`,
2. MyPy over `src/app/api/review_workflow.py`,
3. `make test-unit UNIT_TESTS=tests/unit/test_review_workflow_api_operations.py`
   (`6` passed),
4. `make test-unit UNIT_TESTS=tests/unit/test_review_workflow_application.py`
   (`16` passed),
5. `make test-unit UNIT_TESTS=tests/unit/api_examples/test_review_workflow.py`
   (`2` passed),
6. `make test-integration INTEGRATION_TESTS=tests/integration/test_review_workflow_api.py`
   (`24` passed),
7. `make test-integration INTEGRATION_TESTS=tests/integration/test_review_workflow_entitlements_api.py`
   (`13` passed),
8. `make test-integration INTEGRATION_TESTS=tests/integration/test_api_operation_events.py`
   (`21` passed),
9. `make quality-baseline`,
10. `make maintainability-gate`,
11. `make duplicate-implementation-gate` with zero duplicate clusters across
    `2,947` functions.

The same-pattern scan covered #601/#603 evidence, open and closed GitHub issue
searches, source maintainability hotspots, duplicate implementation inventory,
review workflow unit/integration tests, operation-event tests, the codebase
review ledger, the issue closure matrix, and repository context.
`record_review_action` is reduced to `54` lines and is no longer in the
report-only top-function list. Sibling `record_feedback` remains below the
current source-hotspot threshold at `99` lines, so this slice does not expand
into a behavior-neutral feedback refactor.

This is internal API-boundary modularity only; it does not implement an identity
provider, authenticated sessions, token-claims, new authorization policy,
Gateway/Workbench behavior, data-product support, external-publication authority,
runtime topology, or supported-feature promotion. README, wiki,
supported-features, OpenAPI, migrations, and central skills are unchanged by
explicit scope decision until a later slice changes reader-facing product or
operator truth.

PR `#607` merged by rebase to exact-main SHA
`6281106f5fe314bce7b7b3c9db20a64252a8fb0e`. Feature Lane, PR Merge Gate,
exact-main Main Releasability `29639367176`, and exact-main CodeQL
`29639364976` passed. Release evidence published
`ghcr.io/sgajbi/lotus-idea@sha256:6ba9d633707a1045901f899055fcc86cf3766806fea0905dcd5c406e76969154`.
Issue `#606` is closed and the local and remote implementation branches are
absent after remote prune. Strict wiki parity and the repo-local wiki quality
audit passed; no wiki publication change was needed.

## Issue 609 Mandate-Health Signal Evaluation Maintainability

Issue `#609` applies the same Slice 19 same-pattern maintainability lens to the
allocation-drift mandate-health domain evaluator. After issue `#606` closed,
`make quality-baseline` listed
`src/app/domain/signal_evaluation.py::evaluate_mandate_health_signal` as the
next production-code hotspot at `127` lines. The function mixed evaluation-time
validation, entitlement and source blockers, temporal/freshness/supportability
decisions, duplicate suppression, materiality checks, identity generation,
signal, lineage, evidence-packet, candidate, and final result assembly.

`src/app/domain/signal_evaluation.py` now preserves the public evaluator
signature, allocation-drift family, blocker outcomes, PM review posture,
source refs, stable identity semantics, evidence packet, candidate score, and
access scope while extracting:

1. timezone-aware evaluation precondition validation,
2. entitlement and mandatory action-register source blocker selection,
3. temporal, freshness, portfolio-scope, and Manage-supportability blockers,
4. duplicate, count, and materiality decisions,
5. signal, lineage, evidence-packet, candidate, and success result assembly.

Focused validation passed:

1. Ruff over `src/app/domain/signal_evaluation.py`,
2. MyPy over `src/app/domain/signal_evaluation.py`,
3. `make test-unit UNIT_TESTS=tests/unit/test_mandate_health_signal_evaluation.py`
   (`19` passed),
4. `make test-unit UNIT_TESTS=tests/unit/test_mandate_health_application.py`
   (`6` passed),
5. `make test-integration INTEGRATION_TESTS=tests/integration/test_allocation_drift_signal_api.py`
   (`18` passed),
6. `make quality-baseline`,
7. `make maintainability-gate`,
8. `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,952` functions.

The same-pattern scan covered #601/#603/#606 evidence, open and closed GitHub
duplicate searches, source maintainability hotspots, duplicate implementation
inventory, mandate-health unit and application tests, allocation-drift API
integration tests, the codebase review ledger, the issue closure matrix,
repository context, and issue-discovery ledger `#225`.
`evaluate_mandate_health_signal` moved from `127` lines to `15` lines; the
candidate-created helper is `52` lines.

This is internal domain modularity only. It does not change source-authority
contracts, Manage/Risk/Performance ownership, API/OpenAPI behavior, migrations,
runtime topology, authentication/authorization implementation, Gateway or
Workbench behavior, data-product support, external-publication authority, or
supported-feature promotion. README, wiki, supported features, OpenAPI,
migrations, and central skills are unchanged by explicit scope decision until a
later slice changes reader-facing product or operator truth.

PR `#610` merged by rebase to exact-main SHA
`0156f7030a7be223a0b7b67f579326efb0e00a52`. Feature Lane, PR Merge Gate,
exact-main CodeQL `29640841746`, and exact-main Main Releasability
`29640844111` passed. Release evidence published
`ghcr.io/sgajbi/lotus-idea@sha256:f74756d41fab84d1dc9e5878d23ae0b2e73db9a4d352561d16a898f04c199659`
with provenance attestation
`https://github.com/sgajbi/lotus-idea/attestations/35955171` and SBOM
attestation `https://github.com/sgajbi/lotus-idea/attestations/35955178`.
Issue `#609` is closed and the local and remote implementation branches are
absent after remote prune. Strict wiki parity and the repo-local wiki quality
audit passed; no wiki publication change was needed.

## Issue 618 PostgreSQL Fake Dispatcher Maintainability

Issue `#618` applies the same Slice 19 quality-baseline learning to the
PostgreSQL repository fake used by persistence, readiness, review queue,
runtime trust telemetry, downstream, and outbox tests. After issue `#614`
aligned report-only baseline generation with the blocking scanners,
`make quality-baseline` listed
`tests/unit/postgres_repository_fake.py::FakePostgresCursor.execute` as the
largest remaining executable function at `179` lines.

`FakePostgresCursor.execute` now preserves its public test-double behavior
while delegating SQL families to named handlers for:

1. review queue count/page/readiness queries,
2. outbox and downstream readiness summaries,
3. runtime trust telemetry aggregate queries,
4. candidate detail, downstream lookup, and idempotency lookup queries,
5. review identity queries,
6. outbox event claim/update behavior,
7. candidate update behavior,
8. generic select, delete, insert, and idempotency insert behavior.

Focused validation passed:

1. `tests/unit/test_postgres_repository_fake_dispatch.py`,
2. `tests/unit/test_postgres_repository.py`,
3. `tests/unit/test_postgres_downstream_readiness.py`,
4. `tests/unit/runtime_trust_telemetry/test_postgres_projection.py`,
5. `tests/unit/test_postgres_review_queue.py`,
6. `make quality-baseline`,
7. `make maintainability-gate`,
8. `make duplicate-implementation-gate`,
9. `make lint`,
10. `make typecheck`.

The same-pattern scan covered existing capability-owned fake helpers,
open/closed GitHub duplicate searches, the quality baseline, maintainability
and duplicate gates, the codebase review ledger, the issue closure matrix,
repository context, and issue-discovery ledger `#225`. The dispatcher dropped
out of the top largest-function list; the next largest function is an
end-to-end repository round-trip test, not a reusable SQL-family dispatcher.

This is test-support maintainability only. It does not change production
PostgreSQL adapters, schema, migrations, API/OpenAPI behavior, runtime
topology, authentication/authorization, Core, Gateway, Workbench,
data-product support, external-publication authority, or supported-feature
promotion. README, wiki, supported features, OpenAPI, migrations, and central
skills are unchanged by explicit scope decision.

## Issue 623 AI Workflow-Pack Fixture Maintainability

Issue `#623` follows the same Slice 19 report-only quality-baseline pattern
into AI workflow-pack test support. After issue `#620` moved the PostgreSQL
fake row builder out of the largest-function list, `make quality-baseline` on
exact main `2b740aed4c2c5f5b723861cd8468ddcbe138d997` listed:

1. `tests/support/ai_workflow_pack_fixture.py::write_lotus_ai_workflow_pack_runtime_execution_fixture`
   at `150` lines,
2. `tests/support/ai_workflow_pack_fixture.py::write_lotus_ai_workflow_pack_fixture`
   at `129` lines.

The helpers were reusable test-support infrastructure rather than scenario
tests. They inline-built Lotus AI source-contract specs, registry seed,
bindings, queue policy, supportability surface, runtime provider stub,
guardrails, caller policy, migration seed, and test files. That made the AI
source-authority and non-proof boundaries harder to review.

The public helpers now remain stable entry points while delegating file
generation to:

1. a base source-contract file catalog,
2. a runtime-execution file catalog,
3. one shared writer loop.

Focused validation passed:

1. `python -m pytest tests/unit/test_ai_workflow_pack_fixture.py tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py -q`
   (`48` tests),
2. Ruff check over `tests/support/ai_workflow_pack_fixture.py` and
   `tests/unit/test_ai_workflow_pack_fixture.py`,
3. Ruff format-check over the same files,
4. `make quality-baseline`,
5. `make maintainability-gate`,
6. `make duplicate-implementation-gate`.

The same-pattern scan used open and closed GitHub duplicate searches for
`ai_workflow_pack_fixture`,
`write_lotus_ai_workflow_pack_runtime_execution_fixture`, and
`AI workflow pack maintainability`. Existing issue `#340` tracks external
attested Lotus AI run/model provenance, and closed issue `#392` tracks runtime
blocker proof semantics; neither owns this fixture-maintainability root cause.
Issue `#623` was filed before source mutation and ledger issue `#225` was
updated.

The targeted fixture writers dropped out of the largest-function list after
refactoring. The remaining larger functions are scenario tests, source-safe
proof/readiness tests, a data-lifecycle test scaffold, a Core-source adapter,
and unrelated API/domain hotspots; they are not the same AI workflow-pack
fixture-catalog pattern.

This is test-support maintainability only. It does not change production
runtime behavior, API/OpenAPI contracts, persistence, migrations,
authentication/authorization, Core, Gateway, Workbench, Lotus AI
runtime/provider certification, external-publication authority, data-mesh
certification, or supported-feature promotion. README, wiki, supported
features, OpenAPI, migrations, and central skills are unchanged by explicit
scope decision; no wiki publication is required because no wiki source changed.

PR `#624` merged this hardening by rebase to exact-main SHA
`79a319c37624d62dacd35b516924521c8ddabb06`. PR checks passed Feature Lane, PR
Merge Gate, and CodeQL. Exact-main Main Releasability run `29648568930` and
CodeQL run `29648566676` passed on that SHA. The implementation branch was
removed remotely by GitHub and deleted locally after patch-equivalence
verification. Follow-up issue `#625` captures the next production domain
maintainability candidate instead of broadening this test-support slice.

## Issue 625 Concentration-Risk Signal Evaluation Maintainability

Issue `#625` applies the same Slice 19 quality-baseline learning to the
production concentration-risk domain evaluator. After issue `#623`,
`make quality-baseline` listed
`src/app/domain/signal_evaluation.py::evaluate_concentration_risk_signal` at
`123` lines. The function mixed evaluation-time validation, entitlement and
source blockers, temporal/freshness/issuer-coverage decisions, duplicate
suppression, top-position and top-issuer materiality checks, deterministic
identity, signal, lineage, evidence packet, candidate, and score assembly.

`src/app/domain/signal_evaluation.py` now preserves the public
`evaluate_concentration_risk_signal(source_input, policy)` signature,
concentration-risk family, Lotus Risk source-authority semantics, blocker
outcomes, advisor-review posture, source refs, stable identity semantics,
evidence packet, candidate score, and access scope while extracting:

1. timezone-aware evaluation precondition validation,
2. entitlement and mandatory Lotus Risk source blocker selection,
3. temporal, freshness, and issuer-coverage source blockers,
4. duplicate, source-weight, and materiality decisions,
5. signal, lineage, evidence-packet, candidate, and success result assembly.

Focused validation passed:

1. `python -m pytest tests/unit/test_concentration_risk_signal_evaluation.py -q`
   (`17` passed),
2. `python -m pytest tests/unit/test_github_issue_closure_matrix_gate.py -q`
   (`42` passed),
3. Ruff check and format-check over touched Python files,
4. `make quality-baseline`,
5. `make maintainability-gate`,
6. `make duplicate-implementation-gate`,
7. `make lint`,
8. `make check` (`4,864` unit tests).

The same-pattern scan covered #561 concentration success-mode certification,
#609 mandate-health domain-helper evidence, open and closed GitHub duplicate
searches for `evaluate_concentration_risk_signal`, `concentration risk signal
maintainability`, and `quality baseline concentration risk evaluator`, the
concentration-risk unit tests, the codebase review ledger, the issue closure
matrix, repository context, and issue-discovery ledger `#225`.
`evaluate_concentration_risk_signal` moved from `123` lines to an `18` line
public orchestrator; the candidate-created helper is `52` lines.

This is internal domain modularity only. It does not change source-authority
contracts, Lotus Risk ownership, API/OpenAPI behavior, persistence,
migrations, runtime topology, authentication/authorization, Core, Gateway,
Workbench, data-product support, external-publication authority, or
supported-feature promotion. README, wiki, supported features, OpenAPI,
migrations, and central skills are unchanged by explicit scope decision; no
wiki publication is required because no wiki source changed.

PR `#627` merged this hardening by rebase to exact-main SHA
`148f3038bb60482b1a84a88d0b638c32623ffa17`. PR checks passed Feature Lane,
PR Merge Gate, and CodeQL. Exact-main Main Releasability run `29650135797`
and CodeQL run `29650132606` passed on that SHA. Strict wiki parity passed
with `DiffCount 0`; no wiki publication change was needed. Issue `#625` is
closed and the local and remote implementation branches are absent after
patch-equivalence verification.

## Issue 630 High-Cash Persist API Maintainability

Issue `#630` applies the same Slice 19 quality-baseline learning to the
high-cash candidate persistence API boundary. After issue `#625`,
`make quality-baseline` listed
`src/app/api/idea_signals.py::evaluate_and_persist_high_cash_signal` at `123`
lines. The route mixed candidate-persistence capability authorization,
idempotency-key validation, Core source-ref contract validation, repository
lookup, durable-write readiness, event-lineage parsing, application command
execution, idempotency conflict mapping, operation-event emission, and final
response projection.

`src/app/api/idea_signals.py` now preserves the public
`evaluate_and_persist_high_cash_signal(...)` FastAPI route signature,
response model, status codes, source-authority validation, idempotency/replay
semantics, durable fail-closed behavior, operation-event family, and
`supportedFeaturePromoted=false` posture while extracting:

1. candidate-persistence capability problem mapping,
2. idempotency-key problem mapping,
3. Core source-ref and durable repository context construction,
4. request event-lineage parsing,
5. application command execution through the existing high-cash use case,
6. idempotency conflict problem mapping,
7. candidate-persistence operation-event outcome emission,
8. final API response projection.

Focused validation passed:

1. `python -m ruff check src/app/api/idea_signals.py`,
2. `python -m ruff format --check src/app/api/idea_signals.py`,
3. `python -m mypy src/app/api/idea_signals.py`,
4. `python -m pytest tests/integration/test_high_cash_signal_api.py -q`
   (`36` passed),
5. `python -m pytest tests/integration/test_api_operation_events.py -q`
   (`21` passed),
6. `python -m pytest tests/integration/outbox/test_event_lineage_api.py -q`
   (`5` passed),
7. `make quality-baseline`,
8. `make maintainability-gate`,
9. `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,965` source/script functions.

The same-pattern scan covered #601/#603/#606/#609/#618/#620/#623/#625
maintainability evidence, the current report-only quality baseline, focused
high-cash API regression tests, operation-event tests, event-lineage tests,
the codebase review ledger, the issue closure matrix, refactor decisions, and
issue-discovery ledger `#225`. `evaluate_and_persist_high_cash_signal` moved
from `123` lines to a `38` line public orchestrator.

This is internal API-boundary modularity only. It does not implement
authentication or authorization infrastructure, Core changes, Gateway,
Workbench, data-product support, external-publication authority, runtime
topology changes, migrations, OpenAPI behavior changes, or supported-feature
promotion. README, wiki, supported features, OpenAPI, migrations, and central
skills are unchanged by explicit scope decision; no wiki publication is
required unless later PR/mainline evidence changes repo-authored wiki truth.

PR `#631` merged by rebase to exact-main SHA
`640dba29a3f592df60381c1875e55bc12b2120bd`. Main Releasability
`29652436655` and CodeQL `29652431830` passed on that exact SHA. Strict wiki
publication parity passed with `DiffCount 0`, so no wiki publication was
required. Issue `#630` is closed on exact main, and the implementation branch
is absent locally and remotely after patch-equivalence cleanup.

## Issue 633 Bond-Maturity Core Adapter Maintainability

Issue `#633` applies the same Slice 19 quality-baseline learning to the
bond-maturity Core source adapter. After issue `#630`, the current
report-only quality baseline on exact main
`5dd200fe9f385bb27c566fa3ae76bf720249f241` listed
`src/app/infrastructure/lotus_core_sources.py::fetch_bond_maturity_evidence`
at `126` lines. The method mixed Core maturity-summary HTTP execution,
entitlement/dependency mapping, Core `PortfolioMaturitySummary:v1` source-ref
construction, upstream `HoldingsAsOf:v1` lineage validation, maturity-window
and supportability field extraction, source-currentness and policy metadata,
hash/correlation metadata, and product-safe diagnostic projection.

`src/app/infrastructure/lotus_core_sources.py` now preserves the public
`fetch_bond_maturity_evidence(request)` adapter behavior while extracting:

1. `_bond_maturity_source_facts(...)` for next maturity date, maturing position
   count, fail-closed holdings lineage, and maturity fact source-ref
   construction;
2. `_bond_maturity_evidence(...)` for the final `CoreBondMaturityEvidence`
   response DTO projection.

Focused validation passed:

1. `python -m pytest tests/unit/test_lotus_core_sources.py tests/unit/bond_maturity_runtime_evidence/test_core_adapter.py -q`
   (`62` passed),
2. `python -m ruff check src/app/infrastructure/lotus_core_sources.py tests/unit/test_lotus_core_sources.py tests/unit/bond_maturity_runtime_evidence/test_core_adapter.py`,
3. `python -m ruff format --check src/app/infrastructure/lotus_core_sources.py tests/unit/test_lotus_core_sources.py tests/unit/bond_maturity_runtime_evidence/test_core_adapter.py`,
4. `python -m mypy src/app/infrastructure/lotus_core_sources.py`,
5. `make quality-baseline`,
6. `make maintainability-gate`,
7. `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,967` functions,
8. `make github-issue-closure-matrix-gate`,
9. `make documentation-contract-gate`.

The same-pattern scan covered #601/#603/#606/#609/#618/#620/#623/#625/#630
maintainability evidence, current `quality/baseline_report.md`, open and
closed GitHub duplicate searches for `fetch_bond_maturity_evidence`, `bond
maturity maintainability`, and `lotus_core_sources maintainability`, focused
Core adapter tests, runtime-evidence adapter tests, the codebase review ledger,
the issue closure matrix, refactor decisions, and issue-discovery ledger
`#225`. `fetch_bond_maturity_evidence` moved from `126` lines to a `19` line
public orchestrator; the extracted helpers are `14` and `73` lines.

This is internal adapter modularity only. It does not implement Core changes,
live Core certification, authentication or authorization infrastructure,
Gateway, Workbench, data-product support, external-publication authority,
runtime topology changes, migrations, OpenAPI behavior changes, or
supported-feature promotion. README, wiki, supported features, OpenAPI,
migrations, and central skills are unchanged by explicit scope decision; no
wiki publication is required unless later PR/mainline evidence changes
repo-authored wiki truth.

## Issue 636 Core Portfolio-State Runtime Validator Maintainability

Issue `#636` applies the same Slice 19 quality-baseline learning to the Core
portfolio-state runtime proof-contract validator. After issue `#633`, the
current report-only quality baseline listed
`src/app/application/core_portfolio_state_runtime_evidence/contract.py::core_portfolio_state_runtime_execution_is_valid`
at `121` lines. The function mixed proof-envelope validation, non-proof claim
boundary checks, request/source receipt shape validation, Core
`PortfolioStateSnapshot:v1` scope and product posture checks, temporal
currentness, hash/digest identity, diagnostic and blocker/evidence-ref closure,
and final runtime-evidence clearing.

`src/app/application/core_portfolio_state_runtime_evidence/contract.py` now
preserves the public `core_portfolio_state_runtime_execution_is_valid(payload)`
validator while extracting:

1. `_runtime_execution_validation_parts(...)` for top-level proof envelope and
   receipt shape parsing;
2. `_non_proof_claims_are_valid(...)` for no-claim boundary validation;
3. `_request_receipt_is_valid(...)` for request digest, scope, and hash checks;
4. `_source_receipt_is_valid(...)` and its source scope, product/posture,
   temporal, hash, and required-string helpers;
5. `_execution_closure_is_valid(...)` for status, diagnostic, blocker, and
   evidence-ref closure.

Focused validation passed:

1. `python -m pytest tests/unit/core_portfolio_state_runtime_evidence/test_runtime_execution.py tests/unit/core_portfolio_state_runtime_evidence/test_generator.py -q`
   (`56` passed),
2. `python -m ruff check src/app/application/core_portfolio_state_runtime_evidence/contract.py tests/unit/core_portfolio_state_runtime_evidence/test_runtime_execution.py`,
3. `python -m ruff format --check src/app/application/core_portfolio_state_runtime_evidence/contract.py tests/unit/core_portfolio_state_runtime_evidence/test_runtime_execution.py`,
4. `python -m mypy src/app/application/core_portfolio_state_runtime_evidence/contract.py`,
5. `make quality-baseline`,
6. `make maintainability-gate`,
7. `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,977` source/script functions,
8. `make github-issue-closure-matrix-gate`,
9. `make documentation-contract-gate`.

The same-pattern scan covered #601/#603/#606/#609/#618/#620/#623/#625/#630/#633
maintainability evidence, current `quality/baseline_report.md`, GitHub
searches for `core_portfolio_state_runtime_execution_is_valid`,
`PortfolioStateSnapshot maintainability`, and `core portfolio state runtime
evidence`, focused runtime-evidence tests, generator tests, the codebase review
ledger, the issue closure matrix, refactor decisions, and issue-discovery
ledger `#225`. Closed runtime-evidence/source-contract issues #479/#482 and
open external blockers #380/#345 do not own this maintainability root cause.
The public validator moved from `121` lines to a `12` line orchestrator; every
extracted helper is `39` lines or smaller.

This is internal proof-contract modularity only. It does not implement Core
changes, Core issue `sgajbi/lotus-core#790`, live Core certification,
authentication or authorization infrastructure, Gateway, Workbench,
data-product support, external-publication authority, runtime topology
changes, migrations, OpenAPI behavior changes, or supported-feature promotion.
README, wiki, supported features, OpenAPI, migrations, and central skills are
unchanged by explicit scope decision; no wiki publication is required unless
later PR/mainline evidence changes repo-authored wiki truth.

## Issue 620 PostgreSQL Fake Row Construction Maintainability

Issue `#620` follows through on the issue `#618` fake-infrastructure pattern.
After the SQL dispatcher moved out of the top largest-function list,
`make quality-baseline` listed
`tests/unit/postgres_repository_mutation_fake_helpers.py::row_for_insert` as a
`154` line reusable fake row-construction helper. The two larger functions are
scenario tests; this helper owned many independent table shapes and therefore
qualified as the next internally actionable Slice 19 test-support hardening
target.

`row_for_insert` now preserves its public fake-insert entry point while
delegating row construction to table-owned builders for:

1. candidate records,
2. idempotency records,
3. lifecycle history,
4. audit events,
5. outbox events,
6. review decisions and feedback,
7. conversion intent and outcome records,
8. report evidence-pack requests,
9. downstream submissions,
10. AI explanation lineage records.

Focused validation passed:

1. `tests/unit/test_postgres_repository_mutation_fake_helpers.py`,
2. `tests/unit/test_postgres_repository.py`,
3. `tests/unit/test_postgres_downstream_submission.py`,
4. `tests/unit/outbox/test_postgres_delivery_adapter.py`,
5. `tests/integration/test_postgres_runtime_integration.py`,
6. `make quality-baseline`,
7. `make maintainability-gate`,
8. `make duplicate-implementation-gate`.

The same-pattern scan used open and closed GitHub duplicate searches for
`row_for_insert postgres repository fake`,
`postgres_repository_mutation_fake_helpers`,
`fake row construction table builders`, and `quality baseline row_for_insert`.
No owning issue existed beyond related closed issue `#618`, so issue `#620`
was filed before source mutation. The helper dropped out of the largest
function list after refactoring; the remaining larger functions are scenario
tests or unrelated support fixtures, not the same reusable row-construction
dispatcher pattern.

This is test-support maintainability only. It does not change production
PostgreSQL adapters, schema, migrations, API/OpenAPI behavior, runtime
topology, authentication/authorization, Core, Gateway, Workbench,
data-product support, external-publication authority, or supported-feature
promotion. README, wiki, supported features, OpenAPI, migrations, and central
skills are unchanged by explicit scope decision.
