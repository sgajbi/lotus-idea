# Refactor Decisions

Record architecture, API, security, observability, testing, CI, and documentation decisions that
change the repository's bank-buyable posture.

Do not use this file for aspirational claims. Every entry should name code, tests, and validation
evidence or explicitly mark the item as planned.

## 2026-07-04: Review Workflow API Operation Boundary

The review-action and feedback API routes now share
`src/app/api/review_workflow_operations.py` for caller-header parsing, mutating
review capability checks, body authorized-scope subset validation, idempotency
validation, durable-write blocking, product-safe persistence problem mapping,
and operation-event mapping.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, a queue boundary,
or independent scaling. The runtime split remains unjustified until workload,
failure-isolation, ownership, or operability evidence shows that a separate
boundary would reduce total system risk.

Evidence:

1. Code: `src/app/api/review_workflow.py`,
   `src/app/api/review_workflow_operations.py`.
2. Tests: `tests/unit/test_review_workflow_api_operations.py` plus existing
   review workflow API and application tests.
3. Gates: run focused unit/integration tests, `make maintainability-gate`,
   `make architecture-boundary-gate`, and `make duplicate-implementation-gate`
   before committing the slice.

## 2026-07-04: Conversion Governance API Operation Boundary

The conversion-intent and conversion-outcome API routes now share
`src/app/api/conversion_governance_operations.py` for caller-header parsing,
mutating conversion capability checks, idempotency validation, durable-write
blocking, product-safe persistence problem mapping, and operation-event
mapping.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, queue boundary, or
independent scaling. Conversion intent/outcome posture stays in the same API
process because it shares repository, audit, idempotency, and operation-event
ownership with the existing opportunity lifecycle.

Private-banking boundary preserved:

1. Conversion intent remains local and review-gated.
2. Conversion outcome records downstream source posture only.
3. The routes still do not grant execution, suitability, compliance,
   rebalance, report-render, archive, or client-communication authority.

Evidence:

1. Code: `src/app/api/conversion_governance.py`,
   `src/app/api/conversion_governance_operations.py`.
2. Tests: `tests/unit/test_conversion_governance_api_operations.py` plus
   existing conversion domain and review workflow API integration tests.
3. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_api_error_mappings.py tests\unit\test_conversion_governance_api_operations.py tests\unit\test_review_workflow_api_operations.py tests\unit\test_conversion_governance.py tests\integration\test_review_workflow_api.py -q`
   (`49 passed`).
4. Aggregate validation passed: `make lint`, `make typecheck`,
   `make duplicate-implementation-gate`, and `make test-unit` (`2376 passed`).
5. Documentation/context decision: README, repository context, quality
   scorecard, review ledger, refactor decision log, and wiki source were
   updated. No supported-feature promotion or seed/automation change is
   justified by this internal modularity slice. No platform skill update is
   required because the existing backend-delivery and codebase-review skills
   already require design-vs-runtime modularity, same-pattern scans, and
   evidence-backed ledger entries.

## 2026-07-04: Domain Persistence Model Boundary

Immutable persistence decisions, records, results, lifecycle history, and
repository snapshots now live in `src/app/domain/persistence_models.py`.
`src/app/domain/persistence.py` imports and re-exports those types while keeping
`InMemoryIdeaRepository` behavior and existing public imports stable.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, queue boundary,
worker boundary, or independent scaling. Persistence model contracts and
repository behavior share the same domain-service ownership until workload,
failure-isolation, ownership, or operability evidence justifies a runtime split.

Private-banking boundary preserved:

1. The repository still stores idea candidates, evidence replay, idempotency,
   lifecycle, review, feedback, conversion, report evidence-pack, AI lineage,
   outbox, and downstream submission posture.
2. No portfolio accounting, official performance, risk, suitability,
   compliance, rebalance execution, report rendering, archive authority, or AI
   infrastructure authority moves into lotus-idea.

Evidence:

1. Code: `src/app/domain/persistence.py`,
   `src/app/domain/persistence_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_persistence.py tests\unit\test_postgres_repository.py tests\unit\test_repository_port_boundary.py tests\unit\test_domain_validation.py -q`
   (`46 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/domain/persistence.py` moved from 1185 to
   1004 lines; `src/app/domain/persistence_models.py` is 215 lines.

## 2026-07-04: Signal Evaluation Model Boundary

Immutable signal-family inputs, policies, outcomes, and result contracts now
live in `src/app/domain/signal_evaluation_models.py`.
`src/app/domain/signal_evaluation.py` imports and re-exports those types while
keeping deterministic evaluator algorithms and existing public imports stable.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate service, queue boundary,
worker boundary, or independently scalable evaluator. Signal evaluation remains
local because lotus-idea consumes caller/source-owned evidence, produces local
candidate posture, and has no workload, failure-isolation, ownership, or
operability evidence for a runtime split.

Private-banking boundary preserved:

1. Signal policies consume source-owned posture and deterministic thresholds.
2. No portfolio accounting, official performance, risk, benchmark assignment,
   suitability, compliance, rebalance execution, report rendering, archive
   authority, or AI infrastructure authority moves into lotus-idea.
3. Source-authority validation and caller entitlement checks remain enforced by
   the API/application boundary before candidate creation.

Evidence:

1. Code: `src/app/domain/signal_evaluation.py`,
   `src/app/domain/signal_evaluation_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_high_cash_signal_evaluation.py tests\unit\test_concentration_risk_signal_evaluation.py tests\unit\test_underperformance_signal_evaluation.py tests\unit\test_mandate_health_signal_evaluation.py tests\unit\test_high_volatility_signal_evaluation.py tests\unit\test_drawdown_review_signal_evaluation.py tests\unit\test_api_signal_models.py -q`
   (`90 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/domain/signal_evaluation.py` moved from
   1113 to 954 lines; `src/app/domain/signal_evaluation_models.py` is 230
   lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   supported-feature promotion or seed/automation change is justified by this
   internal modularity slice.

## 2026-07-04: AI Governance API Model Boundary

AI explanation request and response DTOs now live in
`src/app/api/ai_governance_models.py`. `src/app/api/ai_governance.py` imports
and re-exports those DTOs while keeping authorization, idempotency,
durable-write checks, route metadata, operation events, and response handling
in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate AI governance service,
queue boundary, worker boundary, or independently scalable AI execution path.
AI explanation governance remains local because lotus-idea evaluates
deterministic evidence and fallback posture for persisted idea candidates; it
does not execute AI runtime workflows.

Private-banking and AI boundaries preserved:

1. The route still requires explicit AI explanation capabilities and
   `Idempotency-Key` for mutation.
2. The route still does not call AI providers, own prompts/provider payloads,
   execute lotus-ai runtime workflows, grant downstream authority, or promote a
   supported feature.
3. Source-authority, entitlement, model-risk, audit, and human-review posture
   remain enforced by the existing API/application/domain contracts.

Evidence:

1. Code: `src/app/api/ai_governance.py`,
   `src/app/api/ai_governance_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_ai_governance.py tests\unit\test_ai_governance_api_contract.py tests\unit\test_ai_explanation_readiness.py -q`
   (`23 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/ai_governance.py` moved from 955 to
   567 lines; `src/app/api/ai_governance_models.py` is 444 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   supported-feature promotion or seed/automation change is justified by this
   internal modularity slice.

## 2026-07-04: Outbox Delivery API Model Boundary

Outbox delivery readiness, status-count, and run-once response DTOs now live in
`src/app/api/outbox_delivery_readiness_models.py`.
`src/app/api/outbox_delivery_readiness.py` imports those DTOs while keeping
caller authorization, idempotency validation, durable-write blocking, publisher
cleanup, operation-event emission, route metadata, and response handling in the
existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate outbox delivery service,
queue boundary, worker boundary, or independently scalable broker-publication
path. Outbox delivery run-once remains an internal operator foundation because
there is no workload, failure-isolation, ownership, security, or operability
evidence for a runtime split.

Private-banking and operating boundaries preserved:

1. The route still requires operator caller context plus
   `idea.outbox-delivery.*` capabilities.
2. The route still requires `Idempotency-Key` for mutation, uses the configured
   repository and publisher adapter, returns aggregate counts only, and emits
   source-safe operation events.
3. The route still does not certify live broker publication, downstream
   consumer runtime, platform mesh event publication, Gateway/Workbench support,
   data-product certification, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/outbox_delivery_readiness.py`,
   `src/app/api/outbox_delivery_readiness_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\integration\test_outbox_delivery_readiness_api.py tests\unit\test_outbox_delivery_readiness.py -q`
   (`19 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/outbox_delivery_readiness.py` moved
   from 625 to 494 lines; `src/app/api/outbox_delivery_readiness_models.py`
   is 145 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Runtime Trust Telemetry API Model Boundary

Runtime trust telemetry preview, product posture, snapshot, freshness, lineage,
blocking, and evidence response DTOs now live in
`src/app/api/runtime_trust_telemetry_models.py`.
`src/app/api/runtime_trust_telemetry.py` imports those DTOs while keeping
operator caller checks, timezone query validation, aggregate preview/snapshot
construction, operation-event emission, route metadata, and response handling
in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate telemetry service, worker
boundary, data-product certification process, or independently scalable mesh
publication path. Runtime trust telemetry remains an internal operator and
data-mesh readiness surface because there is no workload, failure-isolation,
ownership, security, or operability evidence for a runtime split.

Private-banking and data-mesh boundaries preserved:

1. The route still requires operator caller context plus
   `idea.mesh.trust-telemetry.*` capabilities.
2. The route still returns source-safe aggregate posture and contract-shaped
   telemetry without candidate identifiers, source routes, portfolio/account
   holdings, client identifiers, or official performance/risk facts.
3. The route still does not certify data products, platform mesh, live source
   ingestion, Gateway/Workbench support, client publication, or
   supported-feature promotion.

Evidence:

1. Code: `src/app/api/runtime_trust_telemetry.py`,
   `src/app/api/runtime_trust_telemetry_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\integration\test_runtime_trust_telemetry_api.py tests\unit\test_runtime_trust_telemetry.py -q`
   (`16 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/runtime_trust_telemetry.py` moved
   from 584 to 416 lines; `src/app/api/runtime_trust_telemetry_models.py` is
   187 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.
