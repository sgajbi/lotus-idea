# RFC-0002 Slice 10: Certified APIs, OpenAPI, And Gateway Contract

Status: Partially implemented - certified high-cash API foundation only

## Outcome

Expose certified `lotus-idea` APIs and Gateway routes for supported behavior.

## Implemented In This Slice

The first certified API foundation is:

- `POST /api/v1/idea-signals/high-cash/evaluate`

This endpoint evaluates caller-supplied, source-owned `lotus-core` evidence for
the high-cash / idle-liquidity signal family. It consumes source-reported cash
weight and source references; it does not fetch upstream data and does not
calculate official cash, holdings, or portfolio values.

Implementation files:

1. `src/app/api/idea_signals.py`: FastAPI DTOs, authorization mapping,
   product-safe errors, OpenAPI examples, and route registration.
2. `src/app/application/high_cash_signal.py`: application command and policy
   orchestration over framework-free domain evaluation.
3. `src/app/domain/signal_evaluation.py`: existing deterministic high-cash
   domain policy reused by the endpoint.
4. `src/app/errors.py`: RFC-7807-shaped problem detail body with stable
   `type`, `status`, `code`, `title`, and `detail` fields.
5. `docs/operations/endpoint-certification-ledger.json`: machine-readable
   endpoint certification evidence for the new route.

## Current Contract

The endpoint returns deterministic posture only:

1. `candidate_created` when all source evidence is current, entitlement is
   allowed, and source-reported cash weight meets the policy threshold,
2. `blocked` for stale/missing source evidence, missing cash weight, or
   entitlement denial,
3. `suppressed` for duplicate candidate evidence,
4. `not_eligible` when source-reported cash weight is below threshold.

The endpoint is permissioned by `idea.signal.evaluate` capability or advisor
role. Validation and permission failures return product-safe Problem Details.

`supportedFeaturePromoted` is always `false` in this foundation endpoint. The
endpoint is certified as an API foundation but is not a supported business
feature because live source adapters, Gateway/Workbench proof, data-product
certification, runtime trust telemetry, and supported-feature registration are
not implemented yet.

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

Full `make check` and PR merge-gate evidence remain required before merge.

## Acceptance Gate

1. OpenAPI quality gate passes for every exposed route.
2. Endpoint certification passes for every exposed route.
3. Gateway contract tests prove source-owned `lotus-idea` truth is preserved
   before Gateway routes are claimed complete.
4. No alias or stale endpoint remains without explicit time-boxed justification.
5. Supported-feature promotion remains blocked until live runtime,
   Gateway/Workbench, data-product, docs/wiki, and certification evidence all
   exist.
