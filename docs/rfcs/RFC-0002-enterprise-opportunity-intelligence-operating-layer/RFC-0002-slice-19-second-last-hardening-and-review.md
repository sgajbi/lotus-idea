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
