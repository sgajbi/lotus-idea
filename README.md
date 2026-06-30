# lotus-idea

`lotus-idea` is the Lotus opportunity intelligence and idea lifecycle domain service for private-banking workflows. It turns source-owned Lotus evidence into governed opportunity candidates, review queues, feedback records, and conversion intent for downstream advisory, management, reporting, and Workbench flows.

Service profile: `domain-service`; repository context: [REPOSITORY-ENGINEERING-CONTEXT.md](REPOSITORY-ENGINEERING-CONTEXT.md)

## Current Posture

`lotus-idea` is in RFC-0002 foundation implementation with certified internal API foundations, persistence and migration support, operator readiness diagnostics, source-safe observability, and CI guardrails.

No external business feature is supported yet. Feature promotion still requires certified source-ingestion runtime, trust telemetry, data mesh, Gateway/Workbench, downstream realization, supported-feature registration, and evidence on `main`.

Current implemented foundations include source-authority-preserving high-cash, concentration-risk, underperformance, allocation-drift mandate-review, bond-maturity / reinvestment, high-volatility / drawdown review, missing suitability context, missing risk-profile review, mandate/restriction review, low-income / liquidity-shortfall, and missing-benchmark review policies with Core, Risk, Performance, Manage, and Advise source boundaries. The concentration-risk foundation consumes Lotus Risk `ConcentrationRiskReport:v1` posture only for advisor-review candidates; `POST /api/v1/idea-signals/concentration-risk/evaluate` exposes the same bounded evaluation over caller-supplied Risk concentration evidence and does not calculate concentration, approve risk methodology, recommend trades, create rebalance actions, certify data mesh, prove Workbench behavior, authorize client publication, or promote a supported feature. The underperformance foundation consumes Lotus Performance `ReturnsSeriesBundle:v1` active-return and benchmark-context posture only for advisor-review candidates; `POST /api/v1/idea-signals/underperformance/evaluate` exposes the same bounded evaluation over caller-supplied Performance evidence and does not calculate returns, assign benchmarks, certify benchmark methodology, recommend trades, create rebalance actions, certify data mesh, prove Workbench behavior, authorize client publication, or promote a supported feature. The allocation-drift mandate-review foundation consumes source-owned Manage `PortfolioActionRegister:v1` posture only for portfolio-manager review candidates; `POST /api/v1/idea-signals/allocation-drift/evaluate` exposes the same bounded evaluation over caller-supplied Manage action-register and mandate-health source-ref posture and does not fetch Manage sources, calculate drift, approve mandate compliance, create rebalance actions, create orders, certify data mesh, prove Workbench behavior, authorize client publication, or promote a supported feature. The bond-maturity foundation evaluates caller-supplied Core maturity evidence only for advisor-review candidates; live Core source-adapter proof is blocked until Core exposes explicit source-owned maturity summary facts and fails closed as `core_maturity_summary_missing` when those facts are absent. The low-income foundation consumes Core cashflow evidence only for advisor-review candidates; `POST /api/v1/idea-signals/low-income/evaluate` exposes the same bounded evaluation over caller-supplied Core cashflow projection and cash movement evidence, and a source-safe Core cashflow live-proof artifact can clear only the low-income live Core cashflow source blocker. These foundations do not certify client income needs, reinvestment advice, product recommendation, funding advice, treasury instruction, risk profiling, suitability, mandate changes, restriction clearance, planning claims, benchmark assignment, benchmark methodology, maturity-schedule authority, data mesh, Workbench behavior, client publication, or supported-feature promotion.
High-volatility / drawdown review consumes Risk-owned volatility and drawdown evidence through separate bounded proof contracts. `POST /api/v1/idea-signals/high-volatility/evaluate` exposes bounded caller-supplied Lotus Risk `RiskMetricsReport:v1` volatility evidence evaluation for advisor-review posture; `POST /api/v1/idea-signals/drawdown-review/evaluate` exposes bounded caller-supplied Lotus Risk `DrawdownAnalyticsReport:v1` maximum-drawdown evidence evaluation for advisor-review posture. These endpoints do not fetch Risk sources, calculate volatility or drawdown, approve Risk methodology, recommend trades, create rebalance actions, certify data mesh, prove Workbench behavior, authorize client publication, or promote a supported feature. Valid proof artifacts can clear only the live Risk volatility blocker and drawdown source blocker.
The Manage adapter blocks store-wide supportability evidence from becoming a portfolio opportunity claim and requires Manage-provided lineage or fingerprint metadata before populating `SourceRef.content_hash`.
Source-safe Manage mandate live proof can now clear only the portfolio-scoped Manage action-register source blocker plus the mandate performance-health and mandate risk-health source-ref blockers when live `lotus-manage:PortfolioActionRegister:v1` evidence proves current workflow decisions, source-authored lineage, source freshness, portfolio-scope confirmation, and current source refs for `lotus-performance:MandatePerformanceHealthContext:v1` and `lotus-risk:MandateRiskHealthContext:v1`; source-safe Core portfolio-state live proof can clear only the allocation-drift Core portfolio-state source-ref blocker when live `lotus-core:PortfolioStateSnapshot:v1` evidence proves current source freshness. Data-mesh, Workbench, client-publication, supported-feature, rebalance, action, and order-execution blockers remain.
Source-safe Core benchmark assignment live proof can now clear only the underperformance review benchmark-assignment source-ref blocker when live `lotus-core:BenchmarkAssignment:v1` evidence proves current effective assignment posture; Performance source proof, data-mesh, Workbench, client-publication, supported-feature, benchmark methodology, benchmark composition, and benchmark return blockers remain.
The missing-benchmark foundation consumes Core-owned benchmark-assignment posture only to create an advisor-review evidence-gap candidate when benchmark identity, effective assignment, active status, or assignment version is missing; `POST /api/v1/idea-signals/missing-benchmark/evaluate` exposes the same bounded evaluation over caller-supplied Core benchmark-assignment evidence. Source-safe missing-benchmark live Core proof can clear only the missing-benchmark live Core source blocker, and source-safe Performance benchmark-readiness proof can clear only the missing-benchmark Performance readiness blocker; neither proof nor the API assigns a benchmark, calculates benchmark returns, certifies benchmark methodology, proves data-mesh or Workbench behavior, authorizes client publication, or promotes a supported feature.
The Advise adapter consumes policy-evaluation workflow posture only to create a compliance-review candidate for missing suitability context; `POST /api/v1/idea-signals/missing-suitability/evaluate` exposes the same bounded evaluation over caller-supplied Advise policy-evaluation evidence and does not approve suitability, policy, proposal, sign-off, client publication, or external communication.
The missing risk-profile foundation consumes only explicit Advise-owned risk-profile diagnostic posture to create an advisor-review evidence-gap candidate; `POST /api/v1/idea-signals/missing-risk-profile/evaluate` exposes the same bounded evaluation over caller-supplied Advise evidence and does not approve risk profiling, suitability, policy, proposal, client publication, or external communication. A source-safe typed Advise risk-profile source-product proof can clear only `opportunity_archetype_typed_advise_risk_profile_source_product_missing`, and a separate source-safe live Advise proof can clear only `opportunity_archetype_advise_risk_profile_live_source_proof_missing`; neither proof certifies data mesh, Workbench behavior, client publication, or supported-feature promotion. Source-safe missing-suitability live Advise proof can clear only its corresponding opportunity-archetype live-source blocker. The mandate/restriction review foundation adds a source-safe `POST /api/v1/idea-signals/mandate-restriction/evaluate` API over caller-supplied Core, Manage, or Advise restriction posture evidence; a source-safe typed Advise mandate/restriction source-product proof can clear only `opportunity_archetype_typed_restriction_source_product_missing`, and a separate source-safe Advise mandate/restriction live proof can clear only `opportunity_archetype_live_restriction_source_proof_missing` when the live Advise workflow source carries an explicit restriction diagnostic. It creates only compliance-review candidates and keeps Workbench, data-mesh, client-publication, supported-feature, mandate-state-change, restriction-clearance, approval, rebalance, action, and order-execution blockers intact.
Other foundations cover candidate persistence, replay, lifecycle, review, feedback, queue readiness, AI diagnostics, conversion/report submission, Advise/Manage/Report proof consumption, outbox, runtime trust telemetry, data-mesh readiness, PostgreSQL/migration, Workbench proof, platform mesh proof, bounded downstream readiness counts, opt-in bounded downstream HTTP retry/backoff with idempotency-gated writes, and bounded Gateway/Workbench queue/detail reads. These are internal foundations only: client publication and supported-feature claims remain blocked.

## Product Boundary

`lotus-idea` owns:

- idea detection policy, candidate lifecycle, scoring, ranking, review state,
  and feedback,
- governed idea evidence, rationale, source references, and replay posture,
- conversion intent and outcome tracking for reviewed opportunities,
- data-product declarations and readiness posture for idea candidates,
- internal orchestration contracts for Advise, Manage, Report, Workbench,
  Gateway, Render, Archive, and AI-adjacent workflows.

`lotus-idea` does not own:

- portfolio accounting, holdings, transactions, product master, or client master
  records,
- official performance, risk, suitability, mandate, or compliance
  calculations,
- trade execution, order routing, report rendering, document archiving, or AI
  provider infrastructure,
- client-ready publication or supported product claims before explicit
  promotion evidence exists.

## Ecosystem Role

Primary upstream source authorities:

- `lotus-core`: portfolio, holding, instrument, mandate, client, and product
  facts.
- `lotus-performance`: returns, attribution, benchmark, and performance-health
  evidence.
- `lotus-risk`: risk measures, scenario results, risk flags, and mandate risk
  posture.
- `lotus-advise`: suitability, proposal, policy, and advisory journey context.
- `lotus-manage`: model portfolio, rebalance, mandate, and action-register
  context.
- `lotus-report`: report-pack and commentary context when reviewed idea
  evidence must be reportable.
- `lotus-ai`: provider-neutral AI workflow, prompt governance, model evaluation,
  RAG, and explanation assistance.

Primary downstream consumers:

- `lotus-gateway`: API composition and BFF publication.
- `lotus-workbench`: advisor and portfolio-manager idea review surfaces.
- `lotus-advise`: proposal and suitability workflow conversion.
- `lotus-manage`: portfolio action, rebalance, and mandate review conversion.
- `lotus-report`, `lotus-render`, and `lotus-archive`: report evidence,
  rendering, and archive realization after review-gated publication.

## Data Mesh Posture

`lotus-idea` is designed as a first-class data-mesh producer and consumer from
day one. Repo-owned source truth starts in:

- [contracts/domain-data-products/lotus-idea-products.v1.json](contracts/domain-data-products/lotus-idea-products.v1.json)
- [contracts/domain-data-products/lotus-idea-consumers.v1.json](contracts/domain-data-products/lotus-idea-consumers.v1.json)
- [contracts/domain-data-products/mesh-readiness.v1.json](contracts/domain-data-products/mesh-readiness.v1.json)
- [docs/operations/mesh-readiness.md](docs/operations/mesh-readiness.md)
- [Lotus Data Mesh Standard](../lotus-platform/docs/standards/Lotus%20Data%20Mesh%20Standard.md)

All products remain proposed and not certified until runtime behavior, telemetry, platform
certification, full Gateway/Workbench product proof, and supported-feature promotion are complete. Repo-owned
mesh policy proof validates SLO/access/evidence contracts only; optional platform onboarding proof
validates catalog visibility only. Certification and support stay blocked.

## Architecture At A Glance

```mermaid
flowchart LR
    Core["Source authorities<br/>Core / Performance / Risk / Advise / Manage / Report"]
    Idea["lotus-idea<br/>candidate policy, lifecycle, evidence, review, conversion intent"]
    Store["Active repository<br/>process-local or PostgreSQL"]
    Gateway["lotus-gateway<br/>bounded read-only publication"]
    Workbench["lotus-workbench<br/>bounded read proof<br/>full support blocked"]
    Downstream["Advise / Manage / Report / Render / Archive<br/>planned realization proof"]

    Core -->|"source refs, freshness, evidence"| Idea
    Idea -->|"idempotent records"| Store
    Idea -->|"source-safe diagnostics"| Gateway
    Gateway --> Workbench
    Idea -->|"review-gated intent, submission posture, outcome tracking"| Downstream
```

- `src/app/api/`: FastAPI routes, DTO mapping, caller headers, certified internal API foundations, shared DTO base model, shared signal DTOs, shared route metadata, and the route runtime dependency facade.
- `src/app/application/`: use-case orchestration for signal evaluation, source ingestion,
  candidate detail, evidence replay, review queues,
  lifecycle, feedback, AI diagnostics, conversion, report evidence, downstream
  realization submission foundations, readiness views, and public proof capability update helpers.
- `src/app/domain/`: framework-free domain models, policies, scoring,
  lifecycle, review, AI governance, conversion, report evidence, persistence
  records, idempotency, replay, audit primitives, outbox records, downstream
  submission posture records, claim/lease fencing, retry/dead-letter semantics, and public domain API exports guarded by `make private-import-boundary-gate`.
- `src/app/ports/`: source-owned service, outbox publisher, and repository
  protocols.
- `src/app/infrastructure/`: Core, Performance, Risk, and Manage source adapters,
  migration helpers,
  outbox publisher adapter, public PostgreSQL codec APIs, and PostgreSQL
  repository adapter.
- `src/app/middleware/`: HTTP boundary controls for correlation, trusted
  hosts, CORS allowlisting, request-size limits, JSON writes, and security headers.
- `src/app/observability/`: structured logging, correlation, metrics, tracing,
  and bounded operation events.
- `src/app/security/`: caller context and fail-closed authorization policy.
- `migrations/`: versioned SQL migration and rollback contracts.
- `contracts/`: data-mesh, downstream realization, trust telemetry, SLO,
  access, and evidence-policy contracts.
- `docs/`: RFCs, standards, operations, architecture decisions, and runbooks.
- `wiki/`: authored GitHub wiki source.

## Quick Start

```powershell
make install
make lint
make check
```

Run the service locally:

```powershell
uvicorn app.main:app --reload --port 8330
```

Run with PostgreSQL after applying migrations:

```powershell
$env:LOTUS_IDEA_DATABASE_URL = "postgresql://lotus_idea:lotus_idea@localhost:5432/lotus_idea"
make migrate
uvicorn app.main:app --reload --port 8330
```

Run the Docker entrypoint from a clean checkout:

```powershell
docker compose up --build
```

Compose uses `.env.example` defaults and optional ignored `.env` overrides; the runtime image installs only runtime dependencies, runs as non-root `lotus`, preserves service and source-ingestion worker entrypoints, records governed base/scanner image references plus resolved immutable digests in CI release evidence, and remains runtime-parity evidence only, not production, Workbench, data-mesh, client-publication, or supported-feature proof.

## Common Commands

| Command | Purpose |
| --- | --- |
| `make install` | Create `.venv` and install runtime plus dev dependencies. |
| `make lint` | Run formatting, linting, and fast governance gates. |
| `make typecheck` | Run `mypy` over the service. |
| `make test-unit` | Run unit tests; override `UNIT_TESTS` for a focused path. |
| `make test-integration` | Run integration tests; override `INTEGRATION_TESTS` for a focused path. |
| `make test-e2e` | Run deterministic e2e tests, including the critical internal idea workflow; override `E2E_TESTS` for a focused path. |
| `make openapi-gate` | Validate OpenAPI quality. |
| `make data-mesh-contract-gate` | Validate proposed data-mesh contract posture. |
| `make mesh-policy-proof-contract-gate` | Validate the repo-owned mesh SLO, access, and evidence policy proof without certifying platform mesh readiness or supported features. |
| `make opportunity-archetype-contract-gate` | Validate the governed opportunity archetype and scenario contract while preserving not-certified demo, client-publication, data-mesh, and supported-feature boundaries. |
| `make downstream-realization-contract-gate` | Validate planned downstream realization contract posture. |
| `make outbox-event-contract-gate`, `make outbox-consumer-contract-gate` | Validate repo-owned outbox event and downstream consumer contracts, source-safe payload policy, source-authority boundaries, and remaining proof blockers. |
| `make migration-contract-gate` | Validate migration contract structure. |
| `make migration-execution-gate` | Dry-run apply and rollback migration execution. |
| `make durable-repository-proof-contract-gate` | Validate the source-safe durable PostgreSQL repository proof contract without connecting to a database. |
| `make workbench-read-path-proof-contract-gate` | Validate the bounded Workbench queue/detail read-path proof contract without promoting support. |
| `make gateway-workbench-operational-proof-contract-gate` | Validate the bounded Gateway/Workbench operational proof that consumes the Workbench read-path proof and clears only the generic source-ingestion/outbox Gateway/Workbench blocker. |
| `make gateway-workbench-discovery-proof-contract-gate` | Validate the bounded Gateway/Workbench discovery proof that consumes platform catalog/onboarding and read-path evidence while keeping data-mesh certification and support blocked. |
| `make outbox-broker-proof-contract-gate` | Validate the bounded outbox broker runtime proof contract without certifying external publication, platform mesh event publication, or downstream delivery. |
| `make outbox-consumer-runtime-proof-contract-gate` | Validate the bounded downstream consumer runtime proof contract without certifying platform mesh event publication, Gateway/Workbench behavior, downstream delivery, or supported-feature promotion. |
| `make outbox-platform-mesh-event-publication-proof-contract-gate` | Validate the bounded source-safe outbox event contract plus platform source-manifest/catalog onboarding proof without certifying external broker publication, downstream delivery, Gateway/Workbench behavior, or supported-feature promotion. |
| `make platform-mesh-onboarding-proof-contract-gate` | Validate sibling `lotus-platform` source-manifest/catalog onboarding proof without certifying mesh readiness or supported features. |
| `make ai-lineage-store-proof-contract-gate` | Validate the source-safe AI lineage store proof artifact without, by itself, certifying `lotus-ai` runtime execution, Workbench, or supported-feature promotion. |
| `make ai-workflow-pack-registration-proof-contract-gate` | Validate the bounded sibling `lotus-ai` workflow-pack registration proof without certifying workflow execution, provider calls, model-risk operations, Workbench, or supported-feature promotion. |
| `make ai-workflow-pack-runtime-execution-proof-contract-gate` | Validate the bounded sibling `lotus-ai` deterministic runtime execution proof without certifying live provider execution, model-risk operations, Workbench, client-ready publication, or supported-feature promotion. |
| `make source-ingestion-worker-check`, `make source-ingestion-scheduled-worker-check`, `make source-ingestion-live-proof-contract-gate` | Validate the run-once manifest, scheduled-worker deploy contract, source-safe check-only output, live-proof artifact contract, and aggregate block diagnostics without calling Core. |
| `make risk-concentration-live-proof-contract-gate`, `make high-volatility-live-proof-contract-gate`, `make risk-drawdown-live-proof-contract-gate` | Validate source-safe Lotus Risk concentration, high-volatility, and drawdown live-proof artifact contracts that can clear only their named opportunity-archetype live Risk blockers when valid artifacts are supplied. |
| `make performance-underperformance-live-proof-contract-gate`, `make missing-benchmark-performance-readiness-proof-contract-gate` | Validate source-safe Lotus Performance underperformance and missing-benchmark benchmark-readiness proof artifact contracts that clear only their named opportunity-archetype blockers when valid evidence is supplied. |
| `make core-benchmark-assignment-live-proof-contract-gate`, `make core-portfolio-state-live-proof-contract-gate`, `make missing-benchmark-live-proof-contract-gate` | Validate source-safe Lotus Core benchmark assignment, portfolio-state, and missing-benchmark live-proof artifact contracts that clear only their named opportunity-archetype blockers when valid evidence is supplied. |
| `make low-income-core-cashflow-live-proof-contract-gate` | Validate the source-safe Lotus Core cashflow live-proof artifact contract that can clear only the low-income / liquidity-shortfall live Core cashflow source blocker when valid evidence is supplied. |
| `make manage-mandate-live-proof-contract-gate` | Validate the source-safe Lotus Manage mandate live-proof artifact contract that can clear only the portfolio-scoped Manage source blocker and the source-owned mandate performance/risk health source-ref blockers while preserving Core portfolio-state, data-mesh, Workbench, client-publication, supported-feature, rebalance, action, and order-execution blockers. |
| `make mandate-restriction-source-product-proof-contract-gate`, `make mandate-restriction-live-proof-contract-gate` | Validate the source-safe typed Lotus Advise mandate/restriction source-product proof and live-proof contracts; each clears only its named mandate/restriction blocker while product-readiness blockers remain. |
| `make missing-suitability-live-proof-contract-gate` | Validate the source-safe Lotus Advise policy-evaluation live-proof artifact contract that can clear only the missing-suitability live Advise source blocker when valid evidence is supplied. |
| `make missing-risk-profile-source-product-proof-contract-gate`, `make missing-risk-profile-live-proof-contract-gate` | Validate the source-safe typed Lotus Advise risk-profile source-product proof and live diagnostic proof contracts; each clears only its named missing risk-profile blocker while product-readiness blockers remain. |
| `make implementation-proof-readiness-check` | Generate scheduled-worker deploy, durable repository, runtime telemetry, Workbench read-path, Gateway/Workbench operational, Gateway/Workbench discovery, outbox broker, outbox consumer runtime, outbox platform mesh event publication, Advise proposal route, Manage action route, Report intake route, Report materialization, mesh policy, platform mesh onboarding, AI lineage store, AI workflow-pack registration/runtime execution, AI model-risk operations proof, opportunity archetype scenario readiness, and source-safe RFC proof-readiness evidence. Cross-repo Advise, Manage, Report, platform, and `lotus-ai` proof artifacts default to sibling checkouts and can be overridden through `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF`, `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF`, `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF`, `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF`, `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF`, `LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF`, `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF`, `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF`, `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF`, and `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF`; `LOTUS_IDEA_MESH_POLICY_PROOF`, `LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF`, `LOTUS_IDEA_HIGH_VOLATILITY_LIVE_PROOF`, `LOTUS_IDEA_RISK_DRAWDOWN_LIVE_PROOF`, `LOTUS_IDEA_PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF`, `LOTUS_IDEA_MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF`, `LOTUS_IDEA_CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF`, `LOTUS_IDEA_CORE_PORTFOLIO_STATE_LIVE_PROOF`, `LOTUS_IDEA_MISSING_BENCHMARK_LIVE_PROOF`, `LOTUS_IDEA_LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF`, `LOTUS_IDEA_MANAGE_MANDATE_LIVE_PROOF`, `LOTUS_IDEA_MANDATE_RESTRICTION_LIVE_PROOF`, `LOTUS_IDEA_MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF`, `LOTUS_IDEA_MISSING_SUITABILITY_LIVE_PROOF`, `LOTUS_IDEA_MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF`, and `LOTUS_IDEA_MISSING_RISK_PROFILE_LIVE_PROOF` can override repo-owned or source-specific proof paths without promoting support. Missing sibling evidence leaves cross-repo proof invalid and blockers intact. |
| `make runtime-trust-telemetry-preview-check`, `make runtime-trust-telemetry-snapshot-check` | Generate source-safe runtime trust telemetry preview and snapshot evidence. |
| `make runtime-trust-telemetry-proof-contract-gate` | Validate the source-safe runtime trust telemetry proof contract used by aggregate readiness. |
| `make report-intake-route-proof-contract-gate` | Validate the source-safe `lotus-report` idea evidence intake route proof contract without certifying materialization or publication. |
| `make report-materialization-proof-contract-gate` | Validate the source-safe `lotus-report` idea evidence materialization proof contract without certifying client publication or supported features. |
| `make api-problem-details-boundary-gate`, `make api-idempotency-boundary-gate`, `make api-camel-model-boundary-gate`, `make api-signal-model-boundary-gate`, `make api-temporal-validation-boundary-gate`, `make openapi-problem-details-example-gate`, `make signal-api-contract-gate` | Block direct API route or app-entrypoint imports from `app.errors`, route-local idempotency validator clones, route-local camel-case DTO base-model clones, signal route-to-route DTO coupling, route-local timestamp-awareness checks, missing public `ProblemDetails` OpenAPI examples, and duplicated caller-supplied signal API caller-context headers, scope-unaware permission checks, source-authority, 400/403 examples, and operation-event mechanics. |
| `make operation-metric-contract-gate` | Validate the code-synchronized operation metric catalog without claiming dashboard, alert, mesh, or feature support. |
| `make ai-model-risk-ops-contract-gate` | Validate the AI model-risk operations contract against certified dashboard and alert artifact references. |
| `make ai-model-risk-operations-proof-contract-gate` | Certify the source-safe Grafana dashboard, Prometheus alert rules, and runbook over implemented AI explanation telemetry. |
| `make postgres-integration-gate` | Prove the PostgreSQL runtime repository path. |
| `make check` | Run the local PR-grade gate set. |
| `make ci` | Run the broader CI-equivalent local suite. |
| `make clean` | Remove ignored generated test, coverage, build, and Python cache artifacts without touching `.venv`, `.git`, or dependency caches. |

## Validation And CI Lanes

```mermaid
flowchart LR
    Feature["Feature Lane<br/>lint, typecheck, unit, fast gates"]
    PR["PR Merge Gate<br/>integration, coverage, Docker, Postgres proof"]
    Main["Main Releasability<br/>post-merge release truth"]
    Publish["Wiki and evidence publication<br/>after merge to main"]

    Feature --> PR --> Main --> Publish
```

Run `make lint`, `make typecheck`, and `make test-unit` for feature-lane
feedback; run `make check`, `make postgres-integration-gate`,
`make security-audit`, and `make docker-build` for PR-grade proof.
Governance-focused changes should also run `make documentation-contract-gate`, `make implementation-truth-gate`, `make quality-scorecard-gate`, `make opportunity-archetype-contract-gate`, `make downstream-realization-contract-gate`, and `make supported-features-gate`.

The same controls are explained in [wiki/Validation-and-CI.md](wiki/Validation-and-CI.md),
[quality/ci_quality_gates.md](quality/ci_quality_gates.md), and
[quality/quality_scorecard.md](quality/quality_scorecard.md).

## Runtime And Operations

`LOTUS_IDEA_RUNTIME_PROFILE` defaults to `local`. Only `local` and `test` allow process-local writes; production-like profiles require `LOTUS_IDEA_DATABASE_URL`, while HTTP boundary env vars govern host, origin, and request-size limits with product-safe rejections.

Operational entrypoints:

- local diagnostics: `/health`, `/health/live`, `/health/ready`, `/metrics`, and `/docs`
- source ingestion readiness/run-once: `/api/v1/source-ingestion/readiness`, `/api/v1/source-ingestion/run-once`
- outbox delivery readiness/run-once: `/api/v1/outbox-delivery/readiness`, `/api/v1/outbox-delivery/run-once`
- advisor queue readiness: `/api/v1/review-queues/advisor/readiness`
- AI explanation readiness: `/api/v1/ai-explanations/readiness`
- downstream realization readiness: `/api/v1/downstream-realization/readiness`
- implementation proof readiness: `/api/v1/implementation-proof/readiness`
- data-mesh readiness: `/api/v1/data-mesh/readiness`
- runtime trust telemetry preview: `/api/v1/data-mesh/trust-telemetry/runtime-preview`
- runtime trust telemetry snapshot: `/api/v1/data-mesh/trust-telemetry/runtime-snapshot` and `output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`

Operator details live in [docs/runbooks/service-operations.md](docs/runbooks/service-operations.md), [docs/operations/observability.md](docs/operations/observability.md), [docs/operations/persistence.md](docs/operations/persistence.md), and [wiki/Operations-Runbook.md](wiki/Operations-Runbook.md).

## Governance

Day-one governing standard: `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`

Local controls keep implementation claims grounded:

- `make implementation-truth-gate` blocks unqualified support, certification, live-source, Gateway/Workbench, and client-ready claims.
- `make documentation-contract-gate` protects the README, repo context, docs, quality pages, evidence guide, and wiki pages.
- `make source-observability-contract-gate` prevents raw logs, raw `print()`, direct Python logging, and unsafe observability bypasses.
- `make api-route-metadata-gate` prevents duplicate route metadata type definitions outside `app.api.route_metadata`.
- `make api-idempotency-boundary-gate` prevents route-local `Idempotency-Key` validator clones outside `app.api.idempotency`.
- `make api-camel-model-boundary-gate` prevents route-local camel-case DTO base-model clones outside `app.api.base_model`, `make api-signal-model-boundary-gate` prevents shared signal DTO imports from concrete signal route modules instead of `app.api.signal_models`, `make signal-api-contract-gate` keeps caller-supplied signal caller-context and entitlement-scope headers behind `app.api.caller_headers.CallerContextHeaders`, and `make api-temporal-validation-boundary-gate` keeps API timestamp-awareness and UTC checks behind `app.api.temporal_validation`.
- `make signal-api-contract-gate` prevents copied signal evaluation policy, scope-unaware permission checks, source-authority, operation-event, error-model code, and weak 400/403 `ProblemDetails` OpenAPI examples.
- `make operation-metric-contract-gate` keeps the operation metric catalog
  synchronized with code-owned vocabulary and blocks dashboard, alert, mesh,
  Gateway/Workbench, or supported-feature overclaims.
- `make ai-model-risk-ops-contract-gate` keeps the AI model-risk operations
  contract aligned to implemented AI explanation/readiness telemetry and
  certified dashboard/alert artifact references.
- `make ai-model-risk-operations-proof-contract-gate` proves the repo-owned
  dashboard, alert rules, and runbook reference only implemented, bounded
  operation telemetry while still blocking `lotus-ai`, Workbench,
  data-mesh, client-ready, and supported-feature overclaims.
- `make ai-lineage-store-proof-contract-gate` keeps the AI lineage store proof
  artifact source-safe and prevents durable persistence evidence from becoming
  a false `lotus-ai` runtime, Workbench, client-demo, or supported-feature
  claim.
- `make ai-workflow-pack-registration-proof-contract-gate` keeps sibling `lotus-ai`
  registration evidence source-safe and blocks false runtime, provider, model-risk,
  Workbench, client-demo, or supported-feature claims.
- `make ai-workflow-pack-runtime-execution-proof-contract-gate` keeps sibling `lotus-ai`
  deterministic runtime execution evidence source-safe and blocks false live provider,
  model-risk operations, Workbench, client-demo, or supported-feature claims.
- `make no-sensitive-content-guard` keeps local evidence and output artifacts
  free of sensitive marker names.
- `make durable-repository-proof-contract-gate` keeps the aggregate
  proof-readiness storage evidence source-safe and explicit about remaining production, mesh, live-source, Workbench, and supported-feature blockers.
- `make gateway-workbench-operational-proof-contract-gate` keeps the bounded
  Gateway/Workbench operational artifact tied to the Workbench read-path proof and prevents it from becoming full panel, browser, canonical demo, mesh discovery, or supported-feature proof.
- `make gateway-workbench-discovery-proof-contract-gate` keeps the bounded
  Gateway/Workbench discovery artifact tied to platform catalog/onboarding and read-path evidence while preventing data-mesh certification, product activation, or supported-feature promotion.
- `make report-intake-route-proof-contract-gate` keeps the bounded
  `lotus-report` route proof source-safe and prevents it from becoming a
  false report/render/archive, client-publication, or supported-feature claim.
- `make report-materialization-proof-contract-gate` keeps the bounded `lotus-report` materialization proof source-safe and prevents Report/Render/Archive evidence from becoming a false client-publication or supported-feature claim.
- `make repository-hygiene-gate` blocks generated cache, build, dependency,
  environment, and database artifacts.
- `make clean` removes ignored local byproducts through the governed cleanup
  utility that the CI contract gate protects.
- `make maintainability-gate` blocks oversized source, test, and script files
  or functions beyond measured thresholds.

## Documentation Map

Product and operator overview: [wiki/Overview.md](wiki/Overview.md), [wiki/Architecture.md](wiki/Architecture.md), [wiki/API-Surface.md](wiki/API-Surface.md), [wiki/Integrations.md](wiki/Integrations.md), and [wiki/Troubleshooting.md](wiki/Troubleshooting.md). Governance and release posture: [wiki/Validation-and-CI.md](wiki/Validation-and-CI.md), [wiki/Supported-Features.md](wiki/Supported-Features.md), [docs/operations/supported-feature-promotion.md](docs/operations/supported-feature-promotion.md), and [docs/standards/enterprise-readiness.md](docs/standards/enterprise-readiness.md).
Implementation evidence: [docs/rfcs/README.md](docs/rfcs/README.md) and [docs/operations/api-certification.md](docs/operations/api-certification.md). Client-demo process, client-facing brief, and template: [wiki/Demo-Readiness.md](wiki/Demo-Readiness.md) and [docs/demo/README.md](docs/demo/README.md).

Repo-local `wiki/` is the authored source of truth. The GitHub wiki is a publication target and should be updated through the platform wiki sync flow after merge to `main`.
