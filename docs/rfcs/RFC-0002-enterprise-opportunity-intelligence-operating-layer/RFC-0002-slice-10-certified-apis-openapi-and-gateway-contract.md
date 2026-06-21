# RFC-0002 Slice 10: Certified APIs, OpenAPI, And Gateway Contract

Status: Partially implemented - certified high-cash evaluate and evaluate-and-persist API foundations only

## Outcome

Expose certified `lotus-idea` APIs and Gateway routes for supported behavior.

## Implemented In This Slice

The first certified API foundations are:

- `POST /api/v1/idea-signals/high-cash/evaluate`
- `POST /api/v1/idea-signals/high-cash/evaluate-and-persist`

These endpoints evaluate caller-supplied, source-owned `lotus-core` evidence
for the high-cash / idle-liquidity signal family. They consume source-reported
cash weight and source references; they do not fetch upstream data and do not
calculate official cash, holdings, or portfolio values.

`evaluate-and-persist` adds internal candidate persistence through the Slice 06
in-memory repository foundation. It requires `Idempotency-Key` and
`idea.candidate.persist`, returns replay/conflict posture for idempotency
behavior, and keeps `durableStorageBacked=false` until database-backed
persistence, migrations, and recovery evidence exist.

Implementation files:

1. `src/app/api/idea_signals.py`: FastAPI DTOs, authorization mapping,
   product-safe errors, idempotency-conflict handling, OpenAPI examples, and
   route registration.
2. `src/app/application/high_cash_signal.py`: application command and policy
   orchestration over framework-free domain evaluation and internal
   evaluate-and-persist behavior.
3. `src/app/domain/signal_evaluation.py`: existing deterministic high-cash
   domain policy reused by the endpoint.
4. `src/app/domain/persistence.py`: internal idempotency/audit repository used
   by the evaluate-and-persist API foundation.
5. `src/app/errors.py`: RFC-7807-shaped problem detail body with stable
   `type`, `status`, `code`, `title`, and `detail` fields.
6. `docs/operations/endpoint-certification-ledger.json`: machine-readable
   endpoint certification evidence for the new route.

## Current Contract

The evaluate endpoint returns deterministic posture only:

1. `candidate_created` when all source evidence is current, entitlement is
   allowed, and source-reported cash weight meets the policy threshold,
2. `blocked` for stale/missing source evidence, missing cash weight, or
   entitlement denial,
3. `suppressed` for duplicate candidate evidence,
4. `not_eligible` when source-reported cash weight is below threshold.

The evaluate endpoint is permissioned by `idea.signal.evaluate` capability or
advisor role. The evaluate-and-persist endpoint is permissioned by
`idea.candidate.persist` and requires `Idempotency-Key`. Validation,
permission, and idempotency-conflict failures return product-safe Problem
Details.

`supportedFeaturePromoted` is always `false` in these foundation endpoints.
`durableStorageBacked` is always `false` for evaluate-and-persist. The endpoints
are certified as API foundations but are not supported business features because
live source adapters, Gateway/Workbench proof, database-backed API state,
data-product certification, runtime trust telemetry, and supported-feature
registration are not implemented yet.

## Required Work

1. Implement route families approved by prior slices.
2. Add complete OpenAPI descriptions, examples, error cases, degraded cases,
   unsupported-evidence cases, idempotency behavior, and entitlement behavior.
3. Update endpoint certification ledger.
4. Add `lotus-gateway` contracts and routes without Gateway-side idea
   generation or ranking.

## Remaining Work

1. Add database-backed application state and idempotent API persistence once the
   persistence slice moves from internal records to durable storage.
2. Extend the current Core high-cash source-port and conservative HTTP adapter
   into live source contract proof once Core publishes an explicit
   source-reported cash-weight field; keep all official cash/holding
   calculations in `lotus-core`.
3. Add Gateway contracts and tests that prove Gateway preserves `lotus-idea`
   source authority and does not rank or generate ideas.
4. Add Workbench review-surface proof before any UI or demo claim.
5. Add data-product trust telemetry, platform mesh certification, and
   supported-feature promotion only after runtime proof exists.
6. Add additional route families for candidate lifecycle, evidence packs,
   review actions, feedback, conversion intent, and supportability after their
   storage and orchestration slices are implementation-backed.

## Platform Follow-Up

The local slice exposed a reusable scaffold concern: FastAPI business route
registration must stay compatible with Prometheus instrumentation. The current
`lotus-idea` route is registered directly on the app before instrumentation.
Platform scaffold follow-up is tracked in
`sgajbi/lotus-platform#420`.

## Validation Evidence

Focused validation passed for the current foundation:

1. `python -m pytest tests/unit/test_high_cash_application.py tests/integration/test_high_cash_signal_api.py tests/unit/test_service_contract.py -q`
2. `python -m ruff check src/app/api/idea_signals.py src/app/application/high_cash_signal.py src/app/errors.py src/app/main.py tests/unit/test_high_cash_application.py tests/integration/test_high_cash_signal_api.py tests/unit/test_service_contract.py`
3. `python -m mypy --config-file mypy.ini`
4. `python scripts/openapi_quality_gate.py`
5. `python scripts/endpoint_certification_gate.py`
6. `.venv\Scripts\python.exe -m pytest tests\integration\test_high_cash_signal_api.py tests\unit\test_service_contract.py -q` passed with `16 passed` after adding evaluate-and-persist API certification and blank idempotency-key hardening.
7. `make check` passed with `187` unit tests plus lint, format, typecheck,
   architecture, OpenAPI, supported-feature, endpoint-certification,
   data-mesh, and contract gates.
8. `make ci` passed with `19` integration tests, `2` e2e tests, `187` unit
   tests under coverage, coverage gate at `99.18%`, and dependency audit.

PR merge-gate evidence remains required before merge.

## Acceptance Gate

1. OpenAPI quality gate passes for every exposed route.
2. Endpoint certification passes for every exposed route.
3. Gateway contract tests prove source-owned `lotus-idea` truth is preserved
   before Gateway routes are claimed complete.
4. No alias or stale endpoint remains without explicit time-boxed justification.
5. Supported-feature promotion remains blocked until live runtime,
   Gateway/Workbench, data-product, docs/wiki, and certification evidence all
   exist.
