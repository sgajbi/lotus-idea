# lotus-idea

`lotus-idea` is the Lotus wealth opportunity intelligence and idea lifecycle
service. It detects governed private-banking opportunities from source-owned
Lotus facts, ranks and explains candidate ideas, records review evidence, and
orchestrates conversion into advisory, portfolio-management, reporting, and
Workbench workflows.

Service profile: `domain-service`

Current status: scaffolded foundation, governance RFCs, the first pure domain
model/lifecycle foundation, verified platform scaffold/wiki baseline evidence,
an internal high-cash deterministic signal policy, the first Core source-port
and conservative HTTP adapter foundation for high-cash evidence,
an internal persistence/replay/idempotency/audit foundation, an internal
high-cash evaluate-and-persist orchestration foundation, an internal
Core-backed source-ingestion orchestration foundation with a manifest-backed
run-once CLI, generated
idempotency keys and accepted/replayed/conflict/blocked/suppressed/not-eligible
outcome classification plus a bounded run-once batch worker foundation,
deterministic scoring/review-queue projection and repository-snapshot queue
orchestration foundation, an internal advisor review/feedback governance and
workflow persistence foundation, and an internal AI governance
foundation for redaction, verifier, fallback controls, and a certified internal
AI explanation evaluator API plus a certified internal AI explanation
readiness diagnostic for operator model-risk supportability checks. It also exposes the
first certified internal high-cash signal evaluation and evaluate-and-persist
API foundations for caller-supplied, source-owned Core evidence, certified
internal candidate lifecycle, advisor queue, review-action, and feedback API
foundations over persisted candidates, and an internal conversion-governance
foundation plus certified internal conversion intent/outcome API foundations
for review-gated downstream intent/outcome tracking. It now also has an
internal source-safe candidate detail API foundation, an internal report
evidence-pack request foundation plus a certified internal API for reviewed
report conversion intents, a certified internal candidate evidence replay API
foundation for source-ref hash replay posture, and the first bounded
operation-event observability foundation across certified internal signal,
persistence, candidate detail, evidence replay, lifecycle, AI explanation,
AI explanation readiness, queue, queue-readiness, review, feedback, conversion,
report evidence, and data-mesh-readiness APIs plus certified internal source-ingestion and advisor
queue readiness diagnostics and an aggregate implementation-proof readiness
diagnostic for operator configuration, proof, and certification blockers. The first versioned persistence schema, rollback
contract, PostgreSQL migration execution CLI, tested PostgreSQL repository
adapter, opt-in API repository wiring, and real PostgreSQL runtime proof for
high-cash persistence plus the first internal review, feedback, conversion,
report evidence-pack, advisor queue, source-ingestion replay/conflict recovery,
and migration rollback/reapply recovery workflow now exist behind blocking
gates. `lotus-gateway` now publishes bounded read-only routes for advisor
queue and candidate detail while preserving `lotus-idea` source authority and
blocking unsupported-feature promotion.
Advisor queue reads are scope-aware through optional tenant, book, portfolio,
and client filters over persisted candidate scope, but platform caller-context
entitlement proof and Workbench product proof remain future slices.
Runtime API state is process-local by default and becomes repository-durable
only when `LOTUS_IDEA_DATABASE_URL` is configured after migrations are applied.
No business feature is supported until the relevant
RFC slice has full runtime evidence, tests, data-mesh posture, downstream
proof, Workbench proof, and supported-feature registration.

## Product Boundary

`lotus-idea` owns:

- idea detection policy, candidate lifecycle, scoring, ranking, and review state,
- governed idea evidence, rationale, advisor feedback, and conversion intent,
- source-authority mapping for idea inputs and downstream realization,
- orchestration contracts for `lotus-advise`, `lotus-manage`, `lotus-report`,
  `lotus-workbench`, and `lotus-gateway`.

`lotus-idea` does not own:

- portfolio accounting, positions, transactions, or client/product master data,
- official performance, risk, suitability, mandate, or compliance calculations,
- trade execution, order routing, report rendering, document lifecycle, or AI
  model infrastructure.

## Ecosystem Role

Primary upstream services:

- `lotus-core`: portfolio, holding, instrument, mandate, client, and product facts.
- `lotus-performance`: official return, attribution, benchmark, and performance
  health analytics.
- `lotus-risk`: official risk measures, stress/scenario outputs, risk flags, and
  risk evidence.
- `lotus-advise`: suitability, proposal, and advisory journey context.
- `lotus-manage`: model portfolio, rebalance, mandate, and implementation context.
- `lotus-report`: report pack and commentary context when idea evidence must be
  reportable.
- `lotus-ai`: provider-neutral AI workflows, prompt governance, model evaluation,
  RAG, and explanation assistance.

Primary downstream consumers:

- `lotus-gateway`: BFF/API composition for product surfaces.
- `lotus-workbench`: advisor and portfolio-manager idea review surfaces.
- `lotus-advise`: conversion into proposals and suitability workflows.
- `lotus-manage`: conversion into portfolio action, rebalance, and review flows.
- `lotus-report`: inclusion of reviewed idea evidence in report packs.

## Data Mesh Posture

`lotus-idea` is a planned data-mesh producer and consumer from day one.
Repo-owned source truth starts in:

- `contracts/domain-data-products/lotus-idea-products.v1.json`
- `contracts/domain-data-products/lotus-idea-consumers.v1.json`
- `contracts/domain-data-products/mesh-readiness.v1.json`
- `docs/operations/mesh-readiness.md`

All `lotus-idea` products remain proposed and not certified until runtime
implementation, live trust telemetry, platform source-manifest inclusion,
Gateway/Workbench discovery, and platform mesh certification pass.

`GET /api/v1/data-mesh/readiness` is a certified internal operator diagnostic
for that posture. It requires `idea.mesh.readiness.read` plus the `operator`
role, reads the repo-owned contract files above, and returns the current
`not_certified` status, explicit blockers, source-of-truth paths, proposed
products, and `supportedFeaturePromoted=false`. It is not data-product
certification and must not be exposed as Gateway/Workbench product discovery.

`GET /api/v1/source-ingestion/readiness` is a certified internal operator
diagnostic for the high-cash Core source-ingestion run-once worker posture. It
requires `idea.source-ingestion.readiness.read` plus the `operator` role and
reports manifest, Core base URL, durable repository configuration, and
certification blockers. It does not call Core, certify live source ingestion,
prove a scheduled worker deployment, certify a data product, expose
Gateway/Workbench support, or promote a supported feature.

`GET /api/v1/review-queues/advisor/readiness` is a certified internal operator
diagnostic for advisor queue supportability. It requires
`idea.review.queue.readiness.read` plus the `operator` role and reports only
aggregate candidate counts, queue exclusion counts, durable-storage posture,
and certification blockers. It does not expose candidate identifiers, inspect
access-scope identifiers, certify a durable queue store, provide a
Gateway/Workbench surface, certify a data product, or promote a supported
feature.

`GET /api/v1/ai-explanations/readiness` is a certified internal operator
diagnostic for AI explanation supportability. It requires
`idea.ai-explanation.readiness.read` plus the `operator` role and reports
guardrail availability, model-risk supportability posture, and certification
blockers. It does not call `lotus-ai`, execute provider workflows, expose
prompts or provider payloads, certify durable AI lineage, provide
Gateway/Workbench support, certify a data product, or promote a supported
feature.

`GET /api/v1/downstream-realization/readiness` is a certified internal
operator diagnostic for downstream realization supportability. It requires
`idea.downstream-realization.readiness.read` plus the `operator` role and
reports `lotus-idea` conversion intent, conversion outcome, and report
evidence-pack request counts plus Advise, Manage, Report, Render, and Archive
blockers. It does not call downstream services, create proposals, create manage
actions, render or archive documents, authorize client-ready publication, or
promote a supported feature.

`GET /api/v1/implementation-proof/readiness` is a certified internal operator
diagnostic for RFC-0002 implementation proof posture. It requires
`idea.implementation-proof.readiness.read` plus the `operator` role and a
timezone-aware `evaluatedAtUtc` query parameter. It aggregates source
ingestion, advisor queue, AI explanation, data mesh, Workbench, downstream
realization, and supported-feature promotion blockers. It does not expose
candidate identifiers, source payloads, Gateway/Workbench proof, data-product
certification, client-ready publication, or supported-feature promotion.

The first consumer dependency set is aligned to the RFC-0002 source map:
`lotus-core` portfolio state, holdings/cash balance, cash movement, cashflow
projection, and benchmark assignment; `lotus-performance` returns and mandate
performance health; `lotus-risk` risk metrics and mandate/scenario context;
`lotus-advise` proposal, policy, and copilot evidence; `lotus-manage` action
register; and `lotus-report` client report evidence. These declarations are
source-authority contracts only, not runtime certification.

## Repository Map

- `src/app/api/`: HTTP route modules, API DTO mapping, shared caller-header
  parsing, and the repository provider used by certified internal API
  foundations. The provider defaults to a process-local repository and selects
  `PostgresIdeaRepository` when `LOTUS_IDEA_DATABASE_URL` is configured.
- `src/app/application/`: use-case orchestration. The current first use cases
  evaluate high-cash signals over caller-supplied Core evidence and over a
  Core source port that fetches governed Core evidence, and internally persist
  created candidates through the Slice 06 idempotency/audit repository contract.
  `source_ingestion.py` adds the first internal high-cash source-ingestion
  orchestration wrapper over the same Core source port and repository port,
  including generated source-ingestion idempotency keys, batch decision counts,
  and explicit accepted/replayed/conflict/blocked/suppressed/not-eligible
  decisions. `source_ingestion_worker.py` adds a manifest-backed run-once
  worker plan and product-safe run summary for operator execution without
  source payload leakage or supported-feature promotion.
  Internal candidate detail orchestration reads persisted repository snapshots
  and returns source-safe detail projections with redacted source references,
  workflow summaries, audit summary posture, and no downstream authority or
  supported-feature promotion.
  Internal candidate evidence replay orchestration compares caller-supplied
  current source refs with persisted evidence hashes and returns matched,
  stale-source, hash-mismatch, expired, or missing-candidate posture without
  calling Core, exporting raw source routes, or granting downstream authority.
  Internal review-queue orchestration projects persisted candidate snapshots
  through the Slice 07 deterministic queue policy and certified internal advisor
  queue API foundation. Internal candidate lifecycle orchestration records
  idempotent lifecycle transitions through the Slice 06 repository
  history/audit contract and certified internal lifecycle API foundation.
  Internal review/feedback workflow orchestration records
  governed decisions and feedback through the repository idempotency/audit
  contract and certified internal review/feedback API foundations.
  Internal AI governance orchestration evaluates deterministic fallback or
  supplied workflow output against persisted candidate evidence without calling
  providers, executing `lotus-ai` runtime workflows, persisting durable AI
  lineage, or granting downstream authority.
  Internal conversion workflow orchestration records review-gated conversion
  intents and source-authorized outcomes through the repository
  idempotency/audit contract and certified internal conversion API foundations.
  Internal report evidence-pack orchestration records source-provenanced request
  packages for reviewed report conversion intents without creating Report,
  Render, or Archive records. Internal data-mesh-readiness orchestration reads
  repo-owned contract truth and returns operator-facing planned/not-certified
  posture without promoting products. Internal source-ingestion-readiness
  orchestration returns source-safe operator posture for the high-cash
  run-once worker configuration and certification blockers without calling
  Core or promoting live source support. Internal review-queue-readiness
  orchestration returns source-safe aggregate queue counts, exclusion counts,
  durable-storage posture, and certification blockers without exposing
  candidate identifiers, access scope, or supported queue posture. Internal
  downstream-realization-readiness orchestration returns source-safe workflow
  counts and downstream blockers without calling Advise, Manage, Report, Render,
  or Archive or promoting support. Internal
  implementation-proof-readiness orchestration aggregates current RFC-0002
  capability proof blockers across source ingestion, queue, AI, data mesh,
  Workbench, downstream realization, and supported-feature promotion without
  exposing source payloads or promoting support.
- `src/app/domain/`: framework-free idea domain models, policies, scoring,
  lifecycle rules, review-queue projection, review governance, AI governance,
  conversion governance, report evidence-pack request governance, internal
  persistence records, replay posture, idempotency, and audit primitives.
- `src/app/ports/`: source-owned service interfaces consumed by application
  logic. `idea_repository.py` centralizes the repository workflow protocols for
  candidate snapshots, persistence, evidence replay, lifecycle, review,
  conversion, report evidence, and AI explanation reads; `core_sources.py`
  defines the first Core high-cash evidence port.
- `src/app/infrastructure/`: adapters and clients behind ports, including a
  conservative Core high-cash source adapter that does not infer cash weight
  when Core omits a source-reported value, PostgreSQL migration execution
  helpers, and the tested `PostgresIdeaRepository` adapter.
- `migrations/`: versioned SQL migration and rollback contracts. The first
  contract defines the future durable idea repository schema; it can be applied
  or rolled back with `make migrate` / `make migrate-rollback` when
  `LOTUS_IDEA_DATABASE_URL` is set. Runtime API repository wiring uses the same
  variable after the schema exists.
- `src/app/observability/`: structured logging, correlation, metrics, tracing,
  and bounded idea operation events. Certified internal high-cash, candidate
  persistence, candidate detail, candidate evidence replay, lifecycle, AI
  explanation, advisor queue, queue-readiness, review, feedback, conversion,
  and report evidence-pack foundation APIs plus downstream-realization,
  data-mesh, source-ingestion, and implementation-proof readiness diagnostics emit
  product-safe operation logs and the `lotus_idea_operation_events_total`
  metric without sensitive labels or supported-feature promotion.
- `src/app/security/`: caller context and authorization policy.
- `src/app/resilience/`: timeout, retry, and circuit-breaker primitives.
- `scripts/run_source_ingestion_worker.py`: run-once high-cash source-ingestion
  worker CLI. `--check-only` validates a versioned manifest and is enforced by
  `make source-ingestion-worker-check`; run mode requires
  `LOTUS_CORE_BASE_URL` or `--core-base-url` and the active repository provider.
- `contracts/`: proposed data-product declarations, consumer dependencies,
  trust telemetry, access, SLO, and evidence-policy contracts.
- `docs/architecture/adr/`: durable architecture decisions.
- `docs/rfcs/`: governed implementation roadmap.
- `supported-features/`: implementation-backed feature registry.
- `wiki/`: in-repo GitHub wiki source.

## Quick Start

```powershell
make install
make lint
make ci-contract-gate
make repository-hygiene-gate
make maintainability-gate
make documentation-contract-gate
make quality-scorecard-gate
make monetary-float-guard
make no-sensitive-content-guard
make source-observability-contract-gate
make implementation-truth-gate
make data-mesh-contract-gate
make migration-contract-gate
make migration-execution-gate
make source-ingestion-worker-check
make implementation-proof-readiness-check
make supported-features-gate
make endpoint-certification-gate
make postgres-integration-gate
make typecheck
make architecture-boundary-gate
make architecture-boundary-report
make quality-baseline
make openapi-gate
make check
make ci
```

`make endpoint-certification-gate` now requires certified business/operator
endpoints to cite bounded operation-event test evidence in addition to
OpenAPI, capability, 403, test-reference, and unsupported-boundary evidence.
For the first bounded read-only Gateway publication routes, the same gate
requires the endpoint ledger to cite the exact `lotus-gateway` route and keep
Workbench proof, data-product certification, client-ready publication, and
supported-feature promotion explicitly out of scope.

Equivalent explicit commands:

```powershell
.venv\Scripts\python.exe -m pip install -e '.[dev]'
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe scripts/ci_contract_gate.py
.venv\Scripts\python.exe scripts/repository_hygiene_gate.py
.venv\Scripts\python.exe scripts/maintainability_gate.py
.venv\Scripts\python.exe scripts/documentation_contract_gate.py
.venv\Scripts\python.exe scripts/quality_scorecard_gate.py
.venv\Scripts\python.exe scripts/check_monetary_float_usage.py
.venv\Scripts\python.exe scripts/no_sensitive_content_guard.py
.venv\Scripts\python.exe scripts/source_observability_contract_gate.py
.venv\Scripts\python.exe scripts/implementation_truth_gate.py
.venv\Scripts\python.exe scripts/data_mesh_contract_gate.py
.venv\Scripts\python.exe scripts/migration_contract_gate.py
.venv\Scripts\python.exe scripts/run_migrations.py --direction apply --dry-run
.venv\Scripts\python.exe scripts/run_source_ingestion_worker.py --manifest docs/examples/source-ingestion/high-cash-worker-manifest.example.json --check-only
.venv\Scripts\python.exe scripts/generate_implementation_proof_readiness.py --evaluated-at-utc 2026-06-21T10:10:00Z
.venv\Scripts\python.exe scripts/supported_features_gate.py
.venv\Scripts\python.exe scripts/endpoint_certification_gate.py
.venv\Scripts\python.exe -m pytest tests/integration/test_postgres_runtime_integration.py
.venv\Scripts\python.exe -m mypy --config-file mypy.ini
.venv\Scripts\python.exe scripts/openapi_quality_gate.py
.venv\Scripts\python.exe -m pytest tests/unit tests/integration tests/e2e
.venv\Scripts\python.exe scripts/coverage_gate.py
```

## Run Locally

```powershell
uvicorn app.main:app --reload --port 8330
```

To run the API against PostgreSQL, apply migrations first and keep the database
URL configured:

```powershell
$env:LOTUS_IDEA_DATABASE_URL = "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea"
make migrate
uvicorn app.main:app --reload --port 8330
```

To run the PostgreSQL runtime proof locally, provide an integration database URL.
The test applies and rolls back the repository schema, persists a high-cash
candidate through the API, resets the repository provider, proves idempotent
replay from PostgreSQL, proves schema rollback/reapply restores a usable runtime
contract, projects the advisor queue, records review approval and feedback,
records report conversion intent/outcome state, records a report evidence-pack
request, and proves internal Core-backed source-ingestion replay/conflict
recovery through the PostgreSQL repository adapter. The run-once batch worker
foundation is covered by unit tests; this command is still not live Core worker
certification:

```powershell
$env:LOTUS_IDEA_POSTGRES_INTEGRATION_URL = "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea"
$env:LOTUS_IDEA_POSTGRES_INTEGRATION_REQUIRED = "1"
make postgres-integration-gate
```

To validate the run-once source-ingestion worker manifest contract without
calling Core or writing repository state:

```powershell
make source-ingestion-worker-check
```

To execute the worker against a configured Core service and active repository
provider, provide a versioned manifest and Core base URL:

```powershell
$env:LOTUS_IDEA_SOURCE_INGESTION_MANIFEST = "docs/examples/source-ingestion/high-cash-worker-manifest.example.json"
$env:LOTUS_CORE_BASE_URL = "http://localhost:8310"
.venv\Scripts\python.exe scripts/run_source_ingestion_worker.py
```

Run mode is an internal run-once operator entrypoint only. It is not a scheduled
daemon, deploy-pipeline worker proof, live Core certification, Gateway/Workbench
support, data-product certification, or supported-feature promotion.

To inspect source-ingestion run-once configuration and certification blockers
without calling Core or writing repository state:

```powershell
curl -H "X-Caller-Roles: operator" -H "X-Caller-Capabilities: idea.source-ingestion.readiness.read" http://localhost:8330/api/v1/source-ingestion/readiness
```

To inspect advisor queue supportability without exposing candidate identifiers
or access scope:

```powershell
curl -H "X-Caller-Roles: operator" -H "X-Caller-Capabilities: idea.review.queue.readiness.read" "http://localhost:8330/api/v1/review-queues/advisor/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z"
```

To inspect AI explanation model-risk supportability without invoking `lotus-ai`
or exposing prompts, provider payloads, candidate identifiers, or source
routes:

```powershell
curl -H "X-Caller-Roles: operator" -H "X-Caller-Capabilities: idea.ai-explanation.readiness.read" http://localhost:8330/api/v1/ai-explanations/readiness
```

To inspect aggregate RFC-0002 implementation proof blockers without exposing
candidate identifiers or source payloads:

```powershell
curl -H "X-Caller-Roles: operator" -H "X-Caller-Capabilities: idea.implementation-proof.readiness.read" "http://localhost:8330/api/v1/implementation-proof/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z"
```

To inspect downstream realization blockers without calling Advise, Manage,
Report, Render, or Archive:

```powershell
curl -H "X-Caller-Roles: operator" -H "X-Caller-Capabilities: idea.downstream-realization.readiness.read" http://localhost:8330/api/v1/downstream-realization/readiness
```

Repository-backed endpoints report `durableStorageBacked=true` only in this
configured posture. This does not promote data-product certification,
Gateway/Workbench support, live source ingestion, downstream realization, or
any supported business feature.

## Docker

```powershell
docker compose up --build
```

## Governance

Day-one governing standard:

- `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`

`lotus-idea` must treat this as an active delivery contract from the first
commit: supported claims require code, tests, CI, endpoint certification,
security/dependency posture, documentation, wiki source, and operating evidence.
`make implementation-truth-gate` blocks unqualified current-state README,
operations, quality, and wiki claims that imply demo readiness, production
support, certification, live source ingestion, Gateway/Workbench support, or
client-ready publication while the supported-feature registry remains
foundation-only. It also blocks stale scaffold-era underclaims in current-state
demo documentation, such as saying no business workflow exists or that
architecture-boundary enforcement is still report-only after implementation and
CI evidence prove otherwise.
Rebase auto-merge is allowed only with `LOTUS_AUTOMERGE_TOKEN` plus merged-PR
Main Releasability dispatch so post-merge release evidence is produced on
`main` by a non-suppressed merge actor. When the token is absent, the
auto-merge helper emits an explicit warning and skips queuing auto-merge; use
an authorized human or release actor for a manual rebase merge. GitHub workflow
jobs must declare bounded `timeout-minutes` values, and critical lanes must not use
`continue-on-error: true`; `make ci-contract-gate` blocks drift in those
controls and rejects floating GitHub Action tags in favor of verified immutable
action SHAs with version provenance comments. `make repository-hygiene-gate` is
blocking through `make lint`;
it prevents future agentic changes from committing generated Python cache,
coverage, build, dependency, local environment, or local database artifacts.
`make maintainability-gate` is also blocking through `make lint`;
it prevents future agentic changes from adding oversized source, test, or
script files/functions beyond the measured enterprise-quality thresholds.
`make monetary-float-guard` is blocking through `make lint` with AST-backed
precision checks; it fails money-like `float` annotations, literals, and
conversions so private-banking amounts, prices, balances, rates, valuations,
and P&L fields continue to use explicit decimal/domain types.
`make no-sensitive-content-guard` is blocking through `make lint` and has
focused pass/fail unit coverage; it scans local evidence, log, and output
artifacts for sensitive marker names so future CI evidence cannot accidentally
publish portfolio, client, account, holding, transaction, request-body, response-body,
or raw-entitlement-failure material.
`make source-observability-contract-gate` is also blocking through
`make lint`; it prevents future application code from adding raw `print()`,
direct Python logging, or low-level `log_event` bypasses outside the central
observability module. Request diagnostics use route templates rather than raw
URL paths.
`make documentation-contract-gate` is blocking through `make lint` as well;
it prevents future agentic work from deleting, thinning, or hollowing out the
README, repository context, standards, runbooks, RFC index, quality scorecard,
evidence guide, and wiki pages that operators and implementation agents need
to follow the bank-buyable contract. It also enforces a polished operator-doc
profile for proof and readiness guides, including current-truth tables,
explicit proof and non-proof boundaries, blocker sections, response-shape
tables, evidence links, and executable examples.
`make quality-scorecard-gate` is also blocking through `make lint`; it keeps
the bank-buyable control matrix aligned with implementation truth by enforcing
approved status vocabulary, non-empty evidence/gap/next-slice cells, required
evidence anchors, and stale scaffold-era underclaim detection.

- Bank-buyable contract:
  `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`
- Backend refactoring and delivery playbook:
  `lotus-platform/context/playbooks/ENTERPRISE-BACKEND-REFACTORING-INSTRUCTIONS.md`
- Repository context: `REPOSITORY-ENGINEERING-CONTEXT.md`
- Demo claim ledger: `docs/demo/demo-claims.md`
- API certification guide: `docs/operations/api-certification.md`
- Observability guide: `docs/operations/observability.md`
- AI governance guide: `docs/operations/ai-governance.md`
- Downstream realization readiness guide:
  `docs/operations/downstream-realization-readiness.md`
- Implementation proof readiness guide:
  `docs/operations/implementation-proof-readiness.md`
- Conversion governance guide: `docs/operations/conversion-governance.md`
- Report evidence-pack guide: `docs/operations/report-evidence-packs.md`
- Data mesh readiness guide: `docs/operations/mesh-readiness.md`
- Persistence and migration guide: `docs/operations/persistence.md`
- Data mesh contract gate: `scripts/data_mesh_contract_gate.py`
- Migration contract gate: `scripts/migration_contract_gate.py`
- Migration execution CLI: `scripts/run_migrations.py`
- Source-ingestion worker CLI: `scripts/run_source_ingestion_worker.py`
- Implementation proof readiness generator:
  `scripts/generate_implementation_proof_readiness.py`
- RFC implementation evidence guide: `evidence/rfc-implementation/README.md`
- RFC index: `docs/rfcs/README.md`

The API certification guide mirrors the machine-readable endpoint certification
ledger and must keep current foundation endpoints, required capabilities, and
unsupported boundaries synchronized with implementation truth.
