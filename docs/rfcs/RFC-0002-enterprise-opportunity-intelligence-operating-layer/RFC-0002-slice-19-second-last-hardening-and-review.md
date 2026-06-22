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
   and explicit Gateway/Workbench/supported-feature-promotion boundary wording.
3. `tests/unit/test_endpoint_certification_gate.py` covers current pass behavior
   and failure cases for missing capabilities, weak unsupported-boundary text,
   stale test references, and malformed JSON examples.
4. `docs/operations/api-certification.md`, README, repository context, quality
   scorecard, CI quality guide, and wiki source now describe the stronger gate.
