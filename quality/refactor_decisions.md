# Refactor Decisions

Record architecture, API, security, observability, testing, CI, and documentation decisions that
change the repository's bank-buyable posture.

Do not use this file for aspirational claims. Every entry should name code, tests, and validation
evidence or explicitly mark the item as planned.

## 2026-07-19: PostgreSQL Mutating Workflow Test Boundary

Issue `#645` applies the Slice 19 report-only quality-baseline lens to the
PostgreSQL repository mutating workflow regression. After issue `#642`,
`make quality-baseline` listed
`tests/unit/test_postgres_repository.py::test_postgres_repository_round_trips_mutating_workflow_details`
at `178` lines.

The test mixed:

1. review-ready and approved candidate setup,
2. lifecycle transition persistence,
3. review action and feedback persistence,
4. conversion intent and outcome persistence,
5. report evidence-pack persistence,
6. evidence replay and idempotency prechecks,
7. conversion/report lookup assertions,
8. recovered snapshot and outbox ordering assertions,
9. replacement snapshot round-trip assertions.

The regression now lives in
`tests/unit/test_postgres_repository_mutating_workflow.py`. Its public test is
a short orchestrator over named test-support helpers for seed candidates,
workflow mutation execution, persistence decisions, replay/precheck evidence,
lookup evidence, recovered snapshot assertions, and replacement snapshot
round-trip proof. `tests/unit/test_postgres_repository.py` moved from `1,179`
to `992` lines, and the focused workflow module is `334` lines.

Focused validation passed:

1. `python -m ruff format --check tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py`,
2. `python -m ruff check tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py`,
3. `python -m mypy tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py`,
4. `python -m pytest tests/unit/test_postgres_repository.py tests/unit/test_postgres_repository_mutating_workflow.py -q`
   with `19` tests,
5. `make quality-baseline`,
6. `make maintainability-gate`,
7. `make duplicate-implementation-gate` with zero duplicate clusters across
   `3,004` source/script functions.

The same-pattern scan covered
#601/#603/#606/#609/#618/#620/#623/#625/#630/#633/#636/#638/#640/#642
maintainability evidence, current `quality/baseline_report.md`, GitHub
searches for `test_postgres_repository_round_trips_mutating_workflow_details`,
`postgres repository workflow details maintainability`, and
`mutating workflow details quality baseline`, the codebase review ledger, the
issue closure matrix, RFC Slice 19, and issue-discovery ledger `#225`. Closed
issue `#222` owned production row-scoped PostgreSQL writes, not this
test-support decomposition.

This is test-support maintainability only. It does not change production
PostgreSQL adapters, schema, migrations, API/OpenAPI behavior, authentication
or authorization infrastructure, Core, Gateway, Workbench, data-product
support, external-publication authority, runtime topology, wiki source, README,
supported features, or supported-feature promotion.

## 2026-07-19: PostgreSQL Runtime Trust Telemetry Loader Boundary

Issue `#642` applies the Slice 19 report-only quality-baseline lens to the
PostgreSQL runtime trust telemetry projection loader. After issue `#640`,
`make quality-baseline` listed
`src/app/infrastructure/postgres_runtime_trust_telemetry.py::load_runtime_trust_telemetry_summary`
at `120` lines.

The loader mixed:

1. PostgreSQL cursor orchestration and summary query execution,
2. repeated count-map SQL for source authority, freshness, supportability,
   lifecycle, and data-lifecycle states,
3. row decoding/defaulting for source dates, generated-at timestamps, booleans,
   and integers,
4. `RuntimeTrustTelemetryRepositorySummary` DTO assembly.

The public loader now stays as a `7` line orchestrator and delegates to
infrastructure-owned row loading, count-map, DTO-projection, and defaulting
helpers. The SQL comments remain stable so fake PostgreSQL projection tests and
operator evidence can continue to bind query ownership.

This is design modularity inside the existing `lotus-idea` service. It does
not create a telemetry service, change runtime trust telemetry semantics,
certify a data product, change API/OpenAPI behavior, alter migrations, promote
supported features, or prove Gateway/Workbench/client-publication readiness.
README, wiki source, supported features, central context, and central skills
are unchanged by explicit scope decision.

## 2026-07-19: Bond-Maturity Runtime Proof Validator Boundary

Issue `#640` applies the Slice 19 report-only quality-baseline lens to the
Core bond-maturity runtime proof contract. After issue `#638`,
`make quality-baseline` listed
`src/app/application/bond_maturity_runtime_evidence/contract.py::bond_maturity_runtime_execution_is_valid`
at `120` lines.

The validator mixed:

1. top-level proof envelope and source-authority checks,
2. non-proof claim boundary validation,
3. request and source receipt shape validation,
4. Core `PortfolioMaturitySummary:v1` and upstream `HoldingsAsOf:v1`
   product posture checks,
5. horizon, window, temporal, reconciliation, and supportability checks,
6. source hash, digest, request fingerprint, and upstream holdings identity
   checks,
7. maturity fact posture for empty-window versus opportunity-detected outputs,
8. blocker, evidence-ref, and runtime-evidence clearing.

This slice preserves the public
`bond_maturity_runtime_execution_is_valid(payload)` contract while extracting
proof-owned helpers for runtime-execution parts, non-proof claims, request
receipts, source receipts, source scope, source product posture, temporal/window
posture, source hash identity, required source strings, execution closure, and
maturity fact posture. The public validator moved from `120` lines to `13`
lines; every extracted helper is `39` lines or smaller.

Validation:

1. `python -m pytest tests/unit/bond_maturity_runtime_evidence/test_runtime_execution.py tests/unit/bond_maturity_runtime_evidence/test_generator.py -q`
   passed with `69` tests.
2. `python -m ruff check`, `python -m ruff format --check`, and
   `python -m mypy src/app/application/bond_maturity_runtime_evidence/contract.py`
   passed for the touched Python scope.
3. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed; duplicate inventory reported
   `0` duplicate clusters across `2,995` source/script functions.

No-claim decision: this is internal proof-contract modularity only. It does
not implement Core changes, Core issue `sgajbi/lotus-core#792`, live Core
certification, authentication or authorization infrastructure, Gateway,
Workbench, data-mesh certification, external-publication authority, runtime
topology changes, migrations, OpenAPI behavior changes, or supported-feature
promotion. README, wiki, supported-features, OpenAPI, migrations, central
context, and central skills are unchanged by explicit scope decision unless
final validation changes repo-authored truth.

## 2026-07-19: AI Explanation Evaluation API Boundary

Issue `#638` applies the Slice 19 report-only quality-baseline lens to the
AI explanation evaluation route. After issue `#636`, `make quality-baseline`
listed `src/app/api/ai_governance.py::evaluate_ai_explanation` at `120`
lines.

The route mixed:

1. trusted caller-context parsing and capability authorization,
2. idempotency validation,
3. request DTO to application-command mapping,
4. durable repository configuration checks,
5. application use-case execution,
6. exception-to-ProblemDetails mapping and operation-event emission,
7. lineage persistence and response DTO projection.

This slice preserves the public `evaluate_ai_explanation(...)` FastAPI route,
response model, status/error codes, idempotency semantics, entitlement checks,
durable-write fail-closed behavior, Lotus AI provenance and metadata
validation, and operation-event semantics while extracting API-boundary helpers
for caller binding, command construction, durable-write problem mapping,
exception/problem mapping, and success/result response assembly. The public
route moved from `120` lines to `54` lines; the exception dispatcher is `14`
lines and each extracted problem helper is `13` lines or smaller.

Validation:

1. `python -m py_compile src/app/api/ai_governance.py` passed.
2. `python -m pytest tests/unit/test_ai_governance.py tests/unit/test_ai_governance_api_contract.py tests/unit/test_ai_lineage_idempotency.py tests/unit/test_attested_ai_explanation_application.py tests/integration/test_ai_governance_api.py -q`
   passed with `60` tests.
3. `python -m ruff check`, `python -m ruff format --check`, and
   `python -m mypy src/app/api/ai_governance.py` passed for the touched Python
   scope.
4. The focused AI governance plus closure-matrix suite passed with `114`
   tests.
5. `make quality-baseline`, `make maintainability-gate`,
   `make duplicate-implementation-gate`, `make github-issue-closure-matrix-gate`,
   and `make documentation-contract-gate` passed.
6. `make lint` and `make check` passed; the full unit suite reported `4,878`
   passed tests.

No-claim decision: this is internal API-boundary modularity only. It does not
implement authentication or authorization infrastructure, Lotus AI
runtime/provider certification, API/OpenAPI behavior changes, migrations,
runtime topology, Core, Gateway, Workbench, data-mesh certification,
external-publication authority, or supported-feature promotion. README, wiki,
supported-features, OpenAPI, migrations, and central skills are unchanged by
explicit scope decision unless final validation changes repo-authored truth.

## 2026-07-19: Core Portfolio-State Runtime Proof Validator Boundary

Issue `#636` applies the Slice 19 report-only quality-baseline lens to the
Core portfolio-state runtime proof contract. After issue `#633`,
`make quality-baseline` listed
`src/app/application/core_portfolio_state_runtime_evidence/contract.py::core_portfolio_state_runtime_execution_is_valid`
at `121` lines.

The validator mixed:

1. top-level proof envelope and source-authority checks,
2. non-proof claim boundary validation,
3. request and source receipt shape validation,
4. Core `PortfolioStateSnapshot:v1` source scope and product posture checks,
5. temporal currentness and latest-evidence checks,
6. source hash, digest, and receipt identity checks,
7. diagnostic, blocker, evidence-ref, and runtime-evidence clearing.

This slice preserves the public `core_portfolio_state_runtime_execution_is_valid(payload)`
contract while extracting proof-owned helpers for runtime-execution parts,
non-proof claims, request receipts, source receipts, source scope, source
product posture, temporal posture, hash identity, required source strings, and
execution closure. The public validator moved from `121` lines to a `12` line
orchestrator; every extracted helper is `39` lines or smaller.

Validation:

1. `python -m pytest tests/unit/core_portfolio_state_runtime_evidence/test_runtime_execution.py tests/unit/core_portfolio_state_runtime_evidence/test_generator.py -q`
   passed with `56` tests.
2. Ruff check and format-check passed over the touched source and tests.
3. `python -m mypy src/app/application/core_portfolio_state_runtime_evidence/contract.py`
   passed.
4. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed with zero duplicate clusters
   across `2,977` source/script functions.
5. `make github-issue-closure-matrix-gate` and
   `make documentation-contract-gate` passed.

No-claim decision: this is internal proof-contract modularity only. It does
not change Core implementation, Core producer gap `sgajbi/lotus-core#790`,
Core source authority, API/OpenAPI behavior, migrations, runtime topology,
authentication or authorization infrastructure, Gateway, Workbench, data-mesh
certification, external-publication authority, or supported-feature promotion.
README, wiki, supported-features, OpenAPI, migrations, and central skills are
unchanged by explicit scope decision.

## 2026-07-19: Bond-Maturity Core Adapter Source Boundary

Issue `#633` applies the Slice 19 report-only quality-baseline lens to the
Core bond-maturity source adapter. On exact main
`5dd200fe9f385bb27c566fa3ae76bf720249f241`, `make quality-baseline` listed
`src/app/infrastructure/lotus_core_sources.py::fetch_bond_maturity_evidence`
at `126` lines, near the blocking `130` line source-function threshold.

The method mixed:

1. Core maturity-summary HTTP path construction and query execution,
2. entitlement-denied and dependency-unavailable mapping,
3. `PortfolioMaturitySummary:v1` source-ref construction,
4. `HoldingsAsOf:v1` upstream lineage validation,
5. response DTO assembly for maturity window, supportability, hash, freshness,
   policy, and correlation metadata,
6. product-safe bond-maturity diagnostic projection.

This slice preserves the public `fetch_bond_maturity_evidence(request)`
adapter behavior while extracting `_bond_maturity_source_facts(...)` and
`_bond_maturity_evidence(...)`. The public method moved from `126` lines to a
`19` line orchestrator; the extracted helpers are `14` and `73` lines.

Validation:

1. `python -m pytest tests/unit/test_lotus_core_sources.py tests/unit/bond_maturity_runtime_evidence/test_core_adapter.py -q`
   passed with `62` tests.
2. Ruff check and format-check passed over the touched source and tests.
3. `python -m mypy src/app/infrastructure/lotus_core_sources.py` passed.
4. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed with zero duplicate clusters
   across `2,967` functions.
5. `make github-issue-closure-matrix-gate` and
   `make documentation-contract-gate` passed.

No-claim decision: this is internal adapter modularity only. It does not
change Core implementation, Core source authority, source contracts,
API/OpenAPI behavior, migrations, runtime topology, authentication or
authorization infrastructure, Gateway, Workbench, data-mesh certification,
external-publication authority, or supported-feature promotion. README, wiki,
supported-features, OpenAPI, migrations, and central skills are unchanged by
explicit scope decision.

## 2026-07-19: High-Cash Persist API Boundary

Issue `#630` applies the Slice 19 report-only quality-baseline lens to the
high-cash candidate persistence route.

The public `evaluate_and_persist_high_cash_signal(...)` FastAPI route remains
the stable API entry point for caller-supplied high-cash evaluation and
candidate persistence. The implementation now delegates API-boundary decisions
to named private helpers for:

1. candidate-persistence capability validation,
2. idempotency-key validation,
3. Core source-ref contract validation,
4. durable repository readiness and durable-storage posture,
5. request event-lineage parsing,
6. application command execution through the existing use case,
7. idempotency conflict mapping,
8. operation-event outcome emission,
9. final response projection.

This deliberately does not introduce authentication or authorization
infrastructure, a generic signal framework, Core changes, Gateway/Workbench
behavior, or a runtime service split. The route remains an API/controller
orchestrator over the existing application use case and repository port.

Validation and scope decisions:

1. `evaluate_and_persist_high_cash_signal` moved from the report-only `123`
   line hotspot to a `38` line public orchestrator.
2. Existing high-value regression coverage already proves permission denial,
   blank idempotency key rejection, source-contract rejection, durable
   repository fail-closed behavior, replay, duplicate-candidate retry,
   idempotency conflict, blocked/non-candidate no-persistence behavior, event
   lineage, and operation-event outcomes.
3. Local validation passed:
   `python -m ruff check src/app/api/idea_signals.py`,
   `python -m ruff format --check src/app/api/idea_signals.py`,
   `python -m mypy src/app/api/idea_signals.py`,
   `python -m pytest tests/integration/test_high_cash_signal_api.py -q`
   (`36` passed),
   `python -m pytest tests/integration/test_api_operation_events.py -q`
   (`21` passed),
   `python -m pytest tests/integration/outbox/test_event_lineage_api.py -q`
   (`5` passed),
   `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,965` source/script functions.
4. README, wiki, supported-features, OpenAPI, migrations, authn/authz
   infrastructure, Core, Gateway, Workbench, data-mesh certification,
   external-publication authority, and supported-feature truth are unchanged by
   explicit scope decision.
5. PR `#631` merged by rebase to exact-main SHA
   `640dba29a3f592df60381c1875e55bc12b2120bd`. Main Releasability
   `29652436655` and CodeQL `29652431830` passed on that exact SHA. Strict wiki
   publication parity passed with `DiffCount 0`; issue `#630` is closed and the
   implementation branch is absent locally and remotely.

## 2026-07-18: Concentration-Risk Signal Evaluator Boundary

Issue `#625` applies the Slice 19 report-only quality-baseline lens to the
production concentration-risk domain evaluator.

The public `evaluate_concentration_risk_signal(source_input, policy)` contract
remains the only evaluation entry point. The implementation now delegates to
private concentration-risk helpers for:

1. timezone-aware evaluation validation,
2. entitlement and missing Lotus Risk source blockers,
3. source temporal, freshness, and issuer-coverage validation,
4. duplicate suppression and top position / top issuer materiality decisions,
5. deterministic concentration signal, lineage, evidence-packet, candidate,
   and score construction.

This deliberately does not introduce a generic signal framework. The helper
boundary stays capability-owned because concentration risk has its own source
authority, issuer exposure language, materiality semantics, advisor-review
posture, and no-trade/no-rebalance boundary.

Validation and scope decisions:

1. `evaluate_concentration_risk_signal` moved from the report-only `123` line
   hotspot to an `18` line public orchestrator.
2. Existing focused regression coverage in
   `tests/unit/test_concentration_risk_signal_evaluation.py` already proves
   candidate-created, entitlement-denied, missing source, stale source,
   uncertified issuer coverage, below-materiality, duplicate suppression,
   invalid weights, and policy validation paths.
3. Local validation passed:
   `python -m pytest tests/unit/test_concentration_risk_signal_evaluation.py -q`
   (`17` passed),
   `python -m pytest tests/unit/test_github_issue_closure_matrix_gate.py -q`
   (`42` passed), Ruff check/format-check over touched Python files,
   `make quality-baseline`, `make maintainability-gate`,
   `make duplicate-implementation-gate`, `make lint`, and `make check`
   (`4,864` unit tests).
4. README, wiki, supported-features, OpenAPI, migrations, authn/authz, Core,
   Gateway, Workbench, data-mesh certification, external-publication authority,
   and supported-feature truth are unchanged by explicit scope decision.

## 2026-07-18: AI Workflow-Pack Fixture Boundary

Issue `#623` applies the Slice 19 report-only quality-baseline lens to
`tests/support/ai_workflow_pack_fixture.py`.

The public `write_lotus_ai_workflow_pack_fixture()` and
`write_lotus_ai_workflow_pack_runtime_execution_fixture()` helpers remain the
stable entry points for Idea's Lotus AI source-contract and runtime-execution
proof tests. They no longer inline-build every fake Lotus AI file. Base
source-contract fixture files and runtime-execution fixture files now live in
capability-owned module-level catalogs, with one shared writer loop preserving
the generated tree.

This is test-support maintainability only. It does not change runtime
behavior, API/OpenAPI contracts, persistence, migrations,
authentication/authorization, Core, Gateway, Workbench, Lotus AI
runtime/provider certification, external-publication authority, data-mesh
certification, or supported-feature promotion.

Evidence:

1. `write_lotus_ai_workflow_pack_fixture` and
   `write_lotus_ai_workflow_pack_runtime_execution_fixture` dropped out of the
   report-only largest-function list after `make quality-baseline`.
2. `tests/unit/test_ai_workflow_pack_fixture.py` covers critical
   source-contract files, runtime-execution files, and no-claim boundaries for
   external-publication authority, downstream authority, live provider, and
   supported-feature promotion.
3. Focused validation passed:
   `python -m pytest tests/unit/test_ai_workflow_pack_fixture.py tests/unit/ai_workflow_pack_registration/test_source_contract_proof.py -q`
   (`48` tests), Ruff check and format-check over touched files,
   `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate`.
4. PR `#624` merged by rebase to exact-main SHA
   `79a319c37624d62dacd35b516924521c8ddabb06`; exact-main Main Releasability
   `29648568930` and CodeQL `29648566676` passed.

## 2026-07-18: PostgreSQL Fake Row Builder Boundary

Issue `#620` applies the follow-through Slice 19 test-support hardening from
issue `#618` to `tests/unit/postgres_repository_mutation_fake_helpers.py`.

The public `row_for_insert()` helper remains the single insertion entry point
used by the PostgreSQL fake, but it no longer owns every table's fake row
shape inline. It unwraps JSONB values once and delegates to table-owned row
builders for candidate records, idempotency, lifecycle history, audit events,
outbox events, review decisions, feedback, conversion intent/outcome, report
evidence-pack requests, downstream submissions, and AI explanation lineage.

This is test-support maintainability only. It does not change the production
PostgreSQL adapter, database schema, migrations, API/OpenAPI behavior,
authentication/authorization, Core, Gateway, Workbench, runtime certification,
or supported-feature promotion.

Evidence:

1. `row_for_insert` dropped out of the report-only largest-function list after
   `make quality-baseline`.
2. `tests/unit/test_postgres_repository_mutation_fake_helpers.py` covers
   representative candidate-row JSONB unwrapping, downstream-submission row
   shape, unknown-table failure, and column/value mismatch failure.
3. Affected suites passed:
   `tests/unit/test_postgres_repository_mutation_fake_helpers.py`,
   `tests/unit/test_postgres_repository.py`,
   `tests/unit/test_postgres_downstream_submission.py`,
   `tests/unit/outbox/test_postgres_delivery_adapter.py`, and
   `tests/integration/test_postgres_runtime_integration.py` (`45` passed,
   `9` skipped).
4. `make quality-baseline`, `make maintainability-gate`, and
   `make duplicate-implementation-gate` passed locally.

## 2026-07-18: PostgreSQL Fake SQL Dispatcher Boundary

Issue `#618` reduces the remaining report-only test-support hotspot in
`tests/unit/postgres_repository_fake.py::FakePostgresCursor.execute`.

The fake cursor remains a single in-process test double for the PostgreSQL
repository, but its public `execute()` method now delegates to named
SQL-family handlers for review queues, readiness summaries, runtime trust
telemetry, lookups, review identity, outbox events, candidate updates, generic
selects, deletes, inserts, and idempotency inserts. Existing capability-owned
helpers continue to own bounded mutation, downstream submission, outbox
recovery, runtime trust telemetry row building, review queue rows, and lookup
rows.

This is test-support maintainability only. It does not change the production
PostgreSQL adapter, database schema, migrations, API/OpenAPI behavior,
authentication/authorization, Core, Gateway, Workbench, runtime certification,
or supported-feature promotion.

Evidence:

1. `FakePostgresCursor.execute` dropped out of the report-only largest-function
   list after `make quality-baseline`.
2. `tests/unit/test_postgres_repository_fake_dispatch.py` covers generic
   insert/select/delete write tracking and downstream readiness quarantine
   behavior.
3. Affected suites passed:
   `tests/unit/test_postgres_repository_fake_dispatch.py`,
   `tests/unit/test_postgres_repository.py`,
   `tests/unit/test_postgres_downstream_readiness.py`,
   `tests/unit/runtime_trust_telemetry/test_postgres_projection.py`, and
   `tests/unit/test_postgres_review_queue.py` (`35` tests).
4. `make quality-baseline`, `make maintainability-gate`,
   `make duplicate-implementation-gate`, `make lint`, and `make typecheck`
   passed locally.

## 2026-07-18: PostgreSQL Snapshot Write Boundary

Issue `#612` extracts PostgreSQL snapshot replacement and detail-write helpers
from `src/app/infrastructure/postgres_repository.py` into
`src/app/infrastructure/postgres_snapshot_writes.py`.

The public `PostgresIdeaRepository` API and durable behavior remain unchanged.
The new `PostgresSnapshotWriteRepositoryMixin` owns candidate snapshot inserts,
snapshot idempotency inserts, downstream submission inserts, lifecycle/audit
detail inserts, review/feedback identity-conflict inserts, conversion intent
and outcome detail inserts, report evidence-pack inserts, and AI explanation
lineage detail insertion used during snapshot replacement.

This is design modularity inside the existing Lotus Idea PostgreSQL adapter. It
does not change schema, migrations, source-authority contracts, API/OpenAPI
shape, runtime topology, authentication/authorization, Core, Gateway,
Workbench, or supported-feature promotion.

Evidence:

1. `src/app/infrastructure/postgres_repository.py` moved from `1,186` lines to
   `866` lines.
2. `src/app/infrastructure/postgres_snapshot_writes.py` is a focused `358` line
   PostgreSQL write helper module.
3. Targeted validation passed: Ruff and MyPy over the changed infrastructure
   modules; `make test-unit UNIT_TESTS=tests/unit/test_postgres_repository.py`
   (`19` passed); `make maintainability-gate`; and
   `make duplicate-implementation-gate` with zero duplicate clusters across
   `2,952` functions.

## 2026-07-18: Mandate-Health Signal Evaluation Boundary

`src/app/domain/signal_evaluation.py::evaluate_mandate_health_signal` became
the next production-code source hotspot after #606 closed. Issue `#609`
applies the same Slice 19 maintainability pattern to the allocation-drift
domain signal without changing source authority, Manage/Risk/Performance
ownership, API/OpenAPI shape, migrations, runtime topology, Gateway/Workbench,
authentication/authorization, or supported-feature promotion.

The public evaluator keeps its signature and behavior while delegating to
explicit domain helpers:

1. `_validate_mandate_health_evaluation_time` for timezone-aware evaluation
   preconditions,
2. `_mandate_health_pre_source_block` for entitlement and mandatory
   action-register source blockers,
3. `_mandate_health_source_block` for temporal, freshness, portfolio-scope, and
   Manage supportability blockers,
4. `_mandate_health_materiality_result` for duplicate, count, and threshold
   decisions,
5. `_mandate_health_candidate_created_result` for stable identity, signal,
   lineage, evidence packet, candidate, and final result assembly.

`evaluate_mandate_health_signal` moved from `127` lines to `15` lines; the
candidate-created helper is `52` lines. Focused mandate-health unit,
application, and allocation-drift API integration tests preserve blocker,
not-eligible, suppressed, and candidate-created behavior.

## 2026-07-18: Review-Action API Boundary

`src/app/api/review_workflow.py::record_review_action` was the next source
hotspot left by the #603 same-pattern scan at `127` lines on exact main
`f357d263fb95c3b2ab08462844b54a0ec711b71b`. Issue `#606` applies the same
API-boundary lens to the human-governance review route without widening scope
into authentication, authorization, Workbench, Gateway, or supported-feature
promotion.

The route keeps its public signature, OpenAPI metadata, response schema,
idempotency lineage, entitlement semantics, operation events, persistence
problem mapping, and `supportedFeaturePromoted=false` posture while delegating
to explicit API-boundary helpers:

1. `_review_action_mutation_context` for trusted caller and repository
   mutation context construction,
2. `_apply_review_action_request` for domain command construction and
   application execution,
3. `_review_action_permission_problem` for permission and entitlement failure
   mapping,
4. `_review_action_state_problem` and `_review_action_state_attributes` for
   state-conflict telemetry and problem details,
5. `_review_action_invalid_request_problem` for request validation failure
   mapping,
6. `_review_action_response` for persistence problem and success response
   assembly.

This is design modularity inside the existing Lotus Idea API process. It does
not implement identity provider integration, authenticated sessions,
token-claims, Gateway/Workbench behavior, schema changes, data migration,
runtime topology changes, or supported-feature promotion.

## 2026-07-18: Outbox Delivery Run-Once API Boundary

`src/app/api/outbox/delivery.py::post_outbox_delivery_run_once` appeared in
the report-only quality baseline at `129` lines, one line below the blocking
source-function maintainability threshold. Issue `#603` applies the same
operability and architecture-boundary lens learned from issue `#601`: an
operator-facing run-once route should not mix caller parsing, authorization,
idempotency, durable-write gating, capacity posture, publisher configuration,
execution observation, response mapping, and no-promotion posture in one
near-limit function.

The route keeps its public signature, OpenAPI contract, response schema,
operation events, idempotency replay/conflict behavior, publisher cleanup,
durable-write fail-closed posture, and `supportedFeaturePromoted=false`
semantics while delegating to explicit API-boundary helpers:

1. `_outbox_delivery_run_caller` for trusted caller construction,
2. `_outbox_delivery_run_permission_problem` for product-safe authorization
   failure mapping,
3. `_outbox_delivery_run_context` for idempotency validation, operator run
   reference, repository, and durable-storage posture,
4. `_outbox_delivery_run_precondition_problem` for durable-write, capacity, and
   UTC delivery-time blockers,
5. `_outbox_delivery_run_publisher_or_block` for fail-closed broker
   configuration posture,
6. `_outbox_delivery_run_response` for conflict/replay/accepted response and
   operation-event mapping.

This is design modularity inside the existing Lotus Idea API process. It does
not certify external broker runtime, downstream consumer execution,
platform-mesh event publication, Gateway/Workbench support, data-product
support, external-publication authority, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/outbox/delivery.py`.
2. Tests and gates: Ruff and MyPy over `src/app/api/outbox/delivery.py`,
   `make test-unit UNIT_TESTS=tests/unit/outbox/test_outbox_delivery.py`
   (`16` passed),
   `make test-integration INTEGRATION_TESTS=tests/integration/outbox/test_delivery_readiness_api.py`
   (`16` passed), `make maintainability-gate`,
   `make duplicate-implementation-gate`, and `make quality-baseline`.
3. Maintainability impact: `post_outbox_delivery_run_once` moved from `129` to
   `71` lines and left the report-only top-function list; no duplicate
   implementation clusters were introduced.
4. Documentation/context decision: RFC Slice 19, the codebase review ledger,
   issue closure matrix, repository context, and this decision log were
   updated. README, wiki, supported-features, OpenAPI, migrations, runtime
   topology, and central skills are unchanged because public behavior and
   operating commands did not change.

## 2026-07-18: Service-Capacity Baseline Builder Boundary

`src/app/application/service_capacity_baseline.py::build_service_capacity_baseline`
was at the blocking source-function maintainability threshold in the
report-only quality baseline. The builder is a high-consequence
production-readiness proof path, so future Slice 19 capacity hardening should
not add validation, qualification, or artifact fields into one near-limit
function.

The builder now keeps its public signature and artifact schema but delegates to
explicit internal boundaries:

1. `_validate_capacity_baseline_request` for request-level invariants,
2. `_scenario_summaries` for governed scenario aggregation,
3. `_capacity_evidence_qualifications` for protected PostgreSQL,
   dependency-recovery, load/soak, resource, and cost qualification,
4. `CapacityEvidenceQualificationSet` for derived certification-blocker state,
5. `_capacity_baseline_artifact` for source-safe artifact assembly.

This is design modularity inside the existing Lotus Idea deployable. It does
not execute a live load/soak run, certify capacity, certify cost attribution,
change API behavior, change migrations, prove Gateway/Workbench behavior,
promote a data product, or promote a supported feature.

Evidence:

1. Code: `src/app/application/service_capacity_baseline.py`.
2. Tests and gates:
   `make test-unit UNIT_TESTS=tests/unit/test_service_capacity_baseline.py`
   (`34` passed), `make service-capacity-baseline-contract-gate`,
   `make maintainability-gate`, `make duplicate-implementation-gate`, and
   `make quality-baseline`.
3. Maintainability impact: `build_service_capacity_baseline` moved from
   `130` lines to `64` lines and no longer appears in the report-only
   top-function list; no duplicate implementation clusters were introduced.
4. Documentation/context decision: RFC Slice 19, the codebase review ledger,
   issue closure matrix, and this decision log were updated. README, wiki,
   supported-features, OpenAPI, migrations, runtime topology, and central
   skills are unchanged because public behavior and operating commands did not
   change.

## 2026-07-16: Typed Advise Source-Product Evidence Boundary

The mandate/restriction and missing-risk-profile typed source-product proofs
now share a capability-owned application and automation package. Stable
operator environment variables and Make targets remain, but retired flat v1
modules, scripts, and tests are prohibited.

The shared module owns only source-authority loading, digest binding, closed
field validation, and authority-denial mechanics. Independent profiles retain
diagnostic vocabulary, blocker effects, evidence refs, and non-proof
boundaries. The aggregate proof artifact registry maps every CLI input to its
application arguments, evidence class, blocker effect, tracking issue, and
classification status; documentation validation rejects drift.

This is design modularity inside the existing Lotus Idea deployable. It does
not add an API, database, migration, worker, service, deployment boundary, or
supported feature. Advise retains risk-profile, suitability, policy, proposal,
mandate, and restriction authority. Issue `#508` tracks scheduled-worker
deployment evidence separately because static topology declarations are not a
deployment receipt.

## 2026-07-16: Performance Benchmark-Readiness Evidence Boundary

Performance benchmark-readiness proof generation now uses one named
source-preserving application use case and capability-owned closed v2 runtime
evidence. The source port preserves the exact `ReturnsSeriesBundle:v1`
response identity needed for audit and replay: product/route/time, response
portfolio, calculation and input hashes, benchmark context, coverage,
freshness/quality, and producer correlation/trace.

The runtime contract pseudonymizes consumer scope and cross-binds request,
source, benchmark-context, and deterministic review-required or
no-opportunity receipts. It rejects blocked source execution, malformed or
contradictory context, unknown fields, raw identifiers, stale/future evidence,
scope/time/hash/count drift, diagnostic drift, and recomputed-digest semantic
tampering. Flat v1 implementation, generator, gate, and test paths are removed
and prohibited while the stable environment variable, CLI argument, output
filename, and Make target remain.

This is design modularity inside the existing `lotus-idea` deployable. A
separate runtime service would add network, deployment, support, and failure
surface without workload, scaling, ownership, or isolation evidence. No API,
OpenAPI, persistence, database, migration, or supported-feature change is
introduced. Lotus Performance retains official performance and benchmark
context authority; Lotus Core retains benchmark assignment authority.

Evidence:

1. Code: `src/app/application/performance_benchmark_readiness.py`,
   `src/app/application/performance_benchmark_readiness_runtime_evidence/`,
   `src/app/domain/performance_benchmark_readiness.py`, and the Performance
   port/adapter.
2. Tests: `tests/unit/test_performance_benchmark_readiness.py`,
   `tests/unit/performance_benchmark_readiness_runtime_evidence/`, aggregate
   readiness, archetype, adapter, and canonical-runner suites.
3. Gates: `make missing-benchmark-performance-readiness-proof-contract-gate`,
   `make opportunity-archetype-contract-gate`, and `make ci-contract-gate`.
4. Guidance decision: repository context and operator/wiki truth changed and
   are updated. Existing platform skills already require source-preserving
   one-fetch receipts, semantic tamper checks, capability-owned organization,
   same-pattern scans, and design-versus-runtime modularity, so no skill or
   central-context change is required.

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
`src/app/api/outbox/delivery_models.py`.
`src/app/api/outbox/delivery.py` imports those DTOs while keeping
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
   consumer runtime, platform-mesh event runtime publication, Gateway/Workbench support,
   data-product certification, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/outbox/delivery.py`,
   `src/app/api/outbox/delivery_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\integration\test_outbox_delivery_readiness_api.py tests\unit\test_outbox_delivery_readiness.py -q`
   (`19 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/outbox/delivery.py` moved
   from 625 to 494 lines; `src/app/api/outbox/delivery_models.py`
   is 145 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## Aggregate Persistence Mutation Boundary

Candidate ingestion first exposed the generic whole-repository snapshot cost.
The same-pattern fix now covers lifecycle, review, feedback, conversion, report
evidence, AI lineage, outbox run idempotency, evidence replay, and report
precheck. Aggregate snapshot composition, PostgreSQL mutation orchestration,
and replay projections are separate internal modules with stable interfaces.

Identity, sorted candidate, and idempotency locks fence exact state before the
unchanged domain decision and atomic row delta. Full snapshots remain explicit
administrative/test/DR operations. Query-shape tests and all 17 disposable
PostgreSQL 18 tests pass. This is design and data-access modularity inside one
deployable and one Idea-owned database; it creates no database-per-module,
microservice, schema, API, migration, source-authority, or supported-feature
boundary.

PR `#365` merged the bounded mutation family to main SHA `69326064`; Main
Releasability `29239140276`, CodeQL `29239134509`, and wiki publication
`8386705` provide exact merged-main closure evidence.

## 2026-07-13: Outbox Capability Packages Inside Existing Layers

Outbox ownership now uses an `outbox/` package inside each applicable runtime
layer and support area. The migration covers API routes/DTOs, application use
cases and proof evaluators, domain event/lineage/delivery/recovery policy, the
publisher port, PostgreSQL and HTTP adapters, runtime composition,
observability, operator scripts, and focused tests.

This is design modularity inside the existing `lotus-idea` deployable. API and
optional worker roles still use one Idea-owned PostgreSQL boundary. Folder
cohesion does not justify another service, broker ownership, or independently
scalable process.

Decisions:

1. Internal consumers use explicit capability paths; stable public domain
   exports remain available through `app.domain` without legacy module aliases.
2. Event lineage, in-memory writes, PostgreSQL fake behavior, and event-lineage
   integration proof move with the outbox capability. Aggregate
   implementation-proof consumers remain with their actual owning capability.
3. Direct scripts share `scripts/outbox/_bootstrap.py` so package and Windows
   direct execution resolve the repository consistently.
4. Repository hygiene requires canonical package paths and rejects every
   retired flat path. It does not impose directory-size limits.
5. Supported features, seed data, runtime topology, and external broker,
   consumer, and platform-mesh certification remain unchanged.

Validation evidence:

1. Focused outbox, domain, integration, and hygiene suite: `293 passed`, one
   environment-dependent PostgreSQL skip.
2. Ruff, focused MyPy, architecture, private-import, maintainability,
   duplicate-implementation, repository-hygiene, and all seven outbox contract
   gates pass.
3. Final `make ci`: MyPy over 739 files; 3,567 unit tests; 430 integration
   tests passed with 19 environment-dependent skips; 4 E2E tests; 99.02%
   coverage over 23,779 statements; no known dependency vulnerabilities.
4. Disposable PostgreSQL 18: all 16 required persistence, recovery, queue,
   downstream, and lifecycle tests passed.
5. A clean isolated wheel contains and imports the canonical package paths with
   no retired modules. SHA-tagged Docker build, container package imports,
   health/version smoke, and OCI label inspection passed.

## 2026-07-04: Review Workflow API Model Boundary

Review-action and feedback request/response DTOs now live in
`src/app/api/review_workflow_models.py`.
`src/app/api/review_workflow.py` imports and explicitly re-exports those DTOs
while keeping caller checks, entitlement-scope validation, idempotency,
review workflow persistence, operation-event emission, route metadata, and
response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate review service, worker
boundary, compliance approval runtime, or independently scalable human-review
runtime. Review workflow remains an internal human-review foundation.

Private-banking and authority boundaries preserved:

1. The route still requires explicit review/feedback capabilities, actor role,
   trusted entitlement-scope subset validation, and `Idempotency-Key`.
2. The route still records idea review and feedback posture only; it does not
   approve suitability, compliance, mandates, execution, reporting, or client
   communication.
3. The route still does not certify Gateway/Workbench support, data-product
   publication, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/review_workflow.py`,
   `src/app/api/review_workflow_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_review_workflow_api_operations.py tests\unit\test_api_request_validation.py tests\integration\test_api_operation_events.py -q`
   (`26 passed`), plus targeted ruff and mypy over the changed modules.
3. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Conversion Governance API Model Boundary

Conversion-intent and conversion-outcome request/response DTOs now live in
`src/app/api/conversion_governance_models.py`.
`src/app/api/conversion_governance.py` imports those DTOs while keeping caller
checks, idempotency validation, conversion workflow persistence, operation-event
emission, route metadata, and response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate conversion service, worker
boundary, downstream execution boundary, report materialization boundary, or
independently scalable conversion runtime. Conversion governance remains an
internal lifecycle-intent/outcome foundation.

Private-banking and authority boundaries preserved:

1. The route still requires explicit conversion capabilities and
   `Idempotency-Key` for mutations.
2. The route still records only governed conversion intent/outcome posture; it
   does not grant Advise, Manage, Report, suitability, execution, render,
   archive, or client-communication authority.
3. The route still does not certify downstream execution, Gateway/Workbench
   support, data-product publication, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/conversion_governance.py`,
   `src/app/api/conversion_governance_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_conversion_governance.py tests\unit\test_conversion_governance_api_operations.py tests\unit\test_api_request_validation.py tests\integration\test_api_operation_events.py -q`
   (`37 passed`), plus targeted ruff and mypy over the changed modules.
3. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Idea Signal API Model Boundary

High-cash and mandate-restriction request/response DTOs now live in
`src/app/api/idea_signal_models.py`.
`src/app/api/idea_signals.py` imports those DTOs while keeping caller checks,
source-ref authority validation, candidate persistence orchestration,
operation-event emission, route metadata, and response handling in the
existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate idea-signal service,
worker boundary, source-ingestion runtime, or independently scalable signal
evaluation path. The endpoints remain bounded API foundations that consume
caller-supplied, source-owned evidence.

Private-banking and source-authority boundaries preserved:

1. The route still requires explicit caller capabilities and validates
   source-ref contracts against owning source authorities.
2. The route still does not calculate official portfolio cash, holdings,
   suitability, risk, performance, execution, or report facts.
3. The route still does not certify live source ingestion, Gateway/Workbench
   support, client publication, or supported-feature promotion.

Test-harness learning:

1. API operation-event tests now patch review/conversion helper emitter aliases
   after route/helper extraction so integration tests follow the real operation
   boundary instead of stale route-local emitter names.

Evidence:

1. Code: `src/app/api/idea_signals.py`,
   `src/app/api/idea_signal_models.py`,
   `tests/integration/test_api_operation_events.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\integration\test_api_operation_events.py tests\unit\test_api_signal_models.py -q`
   (`24 passed`), plus targeted ruff and mypy over the changed modules.
3. Documentation/context decision: repository context, quality scorecard,
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

## 2026-07-04: Candidate Detail API Model Boundary

Source-safe candidate-detail response DTOs now live in
`src/app/api/candidate_detail_models.py`. `src/app/api/candidate_detail.py`
imports and explicitly re-exports those DTOs while keeping caller authorization,
entitlement-scope filtering, candidate lookup, operation-event emission, route
metadata, and product-safe response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate candidate-detail service,
Gateway boundary, Workbench boundary, data-product publication path, or
independently scalable read model. Candidate detail remains a bounded internal
read-only API foundation.

Private-banking and source-safety boundaries preserved:

1. The route still requires explicit `idea.candidate.detail.read` capability and
   caller entitlement scope is applied fail-closed before returning detail.
2. The response model still redacts source routes and source content hashes from
   source refs while exposing source authority, product id, version, as-of date,
   generated-at timestamp, data-quality status, and freshness posture.
3. The route still does not provide portfolio accounting, official risk or
   performance facts, suitability/compliance approval, execution authority,
   report rendering/archive authority, client communication, Workbench product
   proof, data-product certification, or supported-feature promotion.

Evidence:

1. Code: `src/app/api/candidate_detail.py`,
   `src/app/api/candidate_detail_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_candidate_detail_models.py tests\unit\test_candidate_detail_application.py tests\integration\test_candidate_detail_api.py tests\integration\test_api_operation_events.py::test_candidate_detail_api_emits_bounded_operation_event -q`
   (`12 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/candidate_detail.py` moved from 624 to
   289 lines; `src/app/api/candidate_detail_models.py` is 349 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Source-Ingestion Readiness API Model Boundary

Source-ingestion readiness and aggregate run-once response DTOs now live in
`src/app/api/source_ingestion_readiness_models.py`.
`src/app/api/source_ingestion_readiness.py` imports and explicitly re-exports
those DTOs while keeping operator caller authorization, durable-repository
gating, runtime composition, Core runtime cleanup, operation-event emission,
route metadata, and product-safe response handling in the existing route
module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate source-ingestion service,
new worker boundary, data-product publication path, Gateway/Workbench product
surface, or independently scalable ingestion runtime. Source ingestion remains
a bounded internal operator proof foundation until workload,
failure-isolation, ownership, security, or operability evidence justifies a
runtime split.

Private-banking, source-authority, and modernization boundaries preserved:

1. The routes still require operator caller context with explicit
   `idea.source-ingestion.*` capabilities.
2. The run-once response still returns aggregate decision counts only and does
   not expose portfolio identifiers, candidate identifiers, idempotency keys,
   raw Core payloads, source routes, or source content hashes.
3. The routes still do not certify live Core source ingestion, data-product
   readiness, Gateway/Workbench support, client publication, downstream
   execution, or supported-feature promotion.
4. The slice does not add compatibility shims, legacy route aliases, or new
   runtime process boundaries; it reduces design-time complexity inside the
   current module boundary.

Evidence:

1. Code: `src/app/api/source_ingestion_readiness.py`,
   `src/app/api/source_ingestion_readiness_models.py`,
   `tests/unit/test_source_ingestion_readiness_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_source_ingestion_readiness_models.py tests\unit\test_source_ingestion_readiness.py tests\integration\test_source_ingestion_readiness_api.py`
   (`28 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/source_ingestion_readiness.py` moved
   from 546 to 384 lines; `src/app/api/source_ingestion_readiness_models.py`
   is 162 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.

## 2026-07-04: Review Queue API Model Boundary

Advisor queue and review queue readiness response DTOs now live in
`src/app/api/review_queue_models.py`. `src/app/api/review_queues.py` imports
and explicitly re-exports those DTOs while keeping caller authorization,
entitlement-scope narrowing, repository selection, readiness snapshot
construction, operation-event emission, route metadata, and product-safe
response handling in the existing route module.

This is a design-modularity refactor inside the existing lotus-idea deployable.
It does not introduce runtime modularity, a separate queue service, PM or
compliance queue runtime, Workbench boundary, data-product publication path, or
independently scalable read model. Advisor review queues remain bounded
internal API and readiness foundations until workload, failure-isolation,
ownership, security, or operability evidence justifies a runtime split.

Private-banking, source-safety, and modernization boundaries preserved:

1. The advisor queue route still requires advisor role plus
   `idea.review.queue.read` capability and applies caller entitlement scope
   fail-closed.
2. The readiness route still requires operator role plus
   `idea.review.queue.readiness.read` capability.
3. The queue response still returns ranked idea candidates, page metadata, and
   exclusions only; it does not expose source routes, source content hashes,
   raw evidence, portfolio accounting, suitability/compliance approval,
   execution authority, or report rendering/archive authority.
4. The routes still do not prove Workbench product support, data-product
   certification, external-publication authority, PM/compliance queue support, or
   supported-feature promotion.
5. The slice does not add compatibility shims, legacy route aliases, or new
   runtime process boundaries; it reduces design-time complexity inside the
   current module boundary.

Evidence:

1. Code: `src/app/api/review_queues.py`,
   `src/app/api/review_queue_models.py`,
   `tests/unit/test_review_queue_models.py`.
2. Focused validation passed:
   `.venv\Scripts\python.exe -m pytest tests\unit\test_review_queue_models.py tests\unit\test_review_queue_application.py tests\integration\test_review_queue_api.py`
   (`37 passed`), plus targeted ruff and mypy over the changed modules.
3. Maintainability impact: `src/app/api/review_queues.py` moved from 606 to
   484 lines; `src/app/api/review_queue_models.py` is 174 lines.
4. Documentation/context decision: repository context, quality scorecard,
   review ledger, refactor decision log, and wiki source were updated. No
   README, supported-feature, seed, automation, or platform skill change is
   justified by this internal modularity slice.
