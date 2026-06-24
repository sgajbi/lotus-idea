# lotus-idea

`lotus-idea` is the Lotus opportunity intelligence and idea lifecycle domain
service for private-banking workflows. It turns source-owned Lotus evidence
into governed opportunity candidates, review queues, feedback records, and
conversion intent for downstream advisory, management, reporting, and Workbench
flows.

Service profile: `domain-service`; repository context: [REPOSITORY-ENGINEERING-CONTEXT.md](REPOSITORY-ENGINEERING-CONTEXT.md)

## Current Posture

`lotus-idea` is in RFC-0002 foundation implementation. The repository has
certified internal API foundations, persistence and migration support,
operator readiness diagnostics, source-safe observability, and CI guardrails.

No external business feature is supported yet. Feature promotion still requires
full source-ingestion certification beyond the bounded live-proof artifact,
certified long-running scheduler proof, certified runtime trust telemetry,
data-mesh certification, full Gateway/Workbench live proof, downstream
realization proof, supported-feature registration, and evidence on `main`.

Current implemented foundations include:

- high-cash evaluation and Core-backed source-ingestion orchestration with
  run-once/scheduled workers, readiness, aggregate APIs, and proof diagnostics,
- candidate persistence, replay, idempotency, lifecycle, review, and feedback,
- advisor queue projection with fail-closed entitlement-scope enforcement and queue readiness,
- AI explanation governance diagnostics and source-safe lineage persistence with
  PostgreSQL runtime proof, without provider execution,
- conversion/report foundations plus governed downstream contract-readiness,
  submission APIs, and HTTP adapter foundations for Advise, Manage, and Report,
  plus optional source-safe proof consumption for the merged `lotus-report`
  intake route, without report materialization, render, archive, publication,
  or supported-feature claims,
- source-safe outbox records with retry/dead-letter semantics, HTTP
  broker-publisher adapter foundation, readiness diagnostics, and bounded
  outbox broker proof evidence for accepted internal mutations,
- runtime trust telemetry, data-mesh readiness, PostgreSQL/migration, durable
  repository, live Core, Workbench, outbox, and optional platform mesh proof
  evidence for aggregate readiness,
- bounded `lotus-gateway` read-only queue/detail routes, including caller
  entitlement-scope forwarding for both published read paths,
- bounded `lotus-workbench` read-only queue/detail rendering through Gateway,
  with stricter live validation before demo evidence is accepted.

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
certification, Gateway/Workbench proof, and supported-feature promotion are complete. Optional
platform onboarding proof validates catalog visibility only; certification and support stay blocked.

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

- `src/app/api/`: FastAPI routes, DTO mapping, caller headers, repository
  provider selection, and certified internal API foundations.
- `src/app/application/`: use-case orchestration for signal evaluation,
  source ingestion, candidate detail, evidence replay, review queues,
  lifecycle, feedback, AI diagnostics, conversion, report evidence, downstream
  realization submission foundations, and readiness views.
- `src/app/domain/`: framework-free domain models, policies, scoring,
  lifecycle, review, AI governance, conversion, report evidence, persistence
  records, idempotency, replay, audit primitives, outbox records, and
  retry/dead-letter state semantics.
- `src/app/ports/`: source-owned service, outbox publisher, and repository
  protocols.
- `src/app/infrastructure/`: Core source adapter, migration helpers,
  outbox publisher adapter, PostgreSQL codecs, and PostgreSQL repository
  adapter.
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

Run the Docker entrypoint:

```powershell
docker compose up --build
```

## Common Commands

| Command | Purpose |
| --- | --- |
| `make install` | Create `.venv` and install runtime plus dev dependencies. |
| `make lint` | Run formatting, linting, and fast governance gates. |
| `make typecheck` | Run `mypy` over the service. |
| `make test-unit` | Run unit tests; override `UNIT_TESTS` for a focused path. |
| `make test-integration` | Run integration tests; override `INTEGRATION_TESTS` for a focused path. |
| `make test-e2e` | Run e2e tests; override `E2E_TESTS` for a focused path. |
| `make openapi-gate` | Validate OpenAPI quality. |
| `make endpoint-certification-gate` | Validate certified endpoint ledger evidence. |
| `make data-mesh-contract-gate` | Validate proposed data-mesh contract posture. |
| `make downstream-realization-contract-gate` | Validate planned downstream realization contract posture. |
| `make migration-contract-gate` | Validate migration contract structure. |
| `make migration-execution-gate` | Dry-run apply and rollback migration execution. |
| `make durable-repository-proof-contract-gate` | Validate the source-safe durable PostgreSQL repository proof contract without connecting to a database. |
| `make workbench-read-path-proof-contract-gate` | Validate the bounded Workbench queue/detail read-path proof contract without promoting support. |
| `make outbox-broker-proof-contract-gate` | Validate the bounded outbox broker runtime proof contract without certifying external publication, mesh events, or downstream consumers. |
| `make platform-mesh-onboarding-proof-contract-gate` | Validate sibling `lotus-platform` source-manifest/catalog onboarding proof without certifying mesh readiness or supported features. |
| `make source-ingestion-worker-check`, `make source-ingestion-scheduled-worker-check`, `make source-ingestion-live-proof-contract-gate` | Validate the run-once manifest, scheduled-worker deploy contract, source-safe check-only output, live-proof artifact contract, and aggregate block diagnostics without calling Core. |
| `make implementation-proof-readiness-check` | Generate scheduled-worker deploy, durable repository, runtime telemetry, Workbench read-path, outbox broker, report-intake route, AI model-risk contract, and source-safe RFC proof-readiness evidence. The report proof defaults to `LOTUS_REPORT_ROOT=../lotus-report` and `output/downstream/report-intake-route-proof.json`, with `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` as an override; missing sibling evidence leaves the proof invalid and blockers intact. Platform mesh onboarding proof is consumed explicitly through `--platform-mesh-onboarding-proof` or `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF`. |
| `make runtime-trust-telemetry-preview-check` | Generate source-safe runtime trust telemetry preview evidence. |
| `make runtime-trust-telemetry-proof-contract-gate` | Validate the source-safe runtime telemetry candidate-snapshot proof contract. |
| `make report-intake-route-proof-contract-gate` | Validate the source-safe `lotus-report` idea evidence intake route proof contract without certifying materialization or publication. |
| `make runtime-trust-telemetry-snapshot-check` | Generate a source-safe runtime trust telemetry snapshot under ignored `output/trust-telemetry/runtime/`. |
| `make operation-metric-contract-gate` | Validate the code-synchronized operation metric catalog without claiming dashboard, alert, mesh, or feature support. |
| `make ai-model-risk-ops-contract-gate` | Validate the AI model-risk dashboard and alert readiness contract while keeping it not certified. |
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
Governance-focused changes should also run `make documentation-contract-gate`,
`make implementation-truth-gate`, `make quality-scorecard-gate`,
`make downstream-realization-contract-gate`, and
`make supported-features-gate`.

The same controls are explained in [wiki/Validation-And-CI.md](wiki/Validation-And-CI.md),
[quality/ci_quality_gates.md](quality/ci_quality_gates.md), and
[quality/quality_scorecard.md](quality/quality_scorecard.md).

## Runtime And Operations

Process-local repository state is the default. Repository-durable API behavior
is enabled only when `LOTUS_IDEA_DATABASE_URL` is configured and migrations have
been applied.

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

Operator details live in:

- [docs/runbooks/service-operations.md](docs/runbooks/service-operations.md)
- [docs/operations/observability.md](docs/operations/observability.md)
- [docs/operations/persistence.md](docs/operations/persistence.md)
- [docs/operations/source-ingestion-run-once.md](docs/operations/source-ingestion-run-once.md)
- [docs/operations/implementation-proof-readiness.md](docs/operations/implementation-proof-readiness.md)
- [wiki/Operations-Runbook.md](wiki/Operations-Runbook.md)

## Governance

Day-one governing standard:

- `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`

Local controls keep implementation claims grounded:

- `make implementation-truth-gate` blocks unqualified claims that imply support,
  certification, live source ingestion, Gateway or Workbench support, or
  client-ready publication while no supported feature is promoted.
- `make documentation-contract-gate` protects the README, repo context, docs,
  quality pages, evidence guide, and wiki pages that operators and agents need.
- `make source-observability-contract-gate` prevents raw logs, raw `print()`,
  direct Python logging, and unsafe observability bypasses.
- `make operation-metric-contract-gate` keeps the operation metric catalog
  synchronized with code-owned vocabulary and blocks dashboard, alert, mesh,
  Gateway/Workbench, or supported-feature overclaims.
- `make ai-model-risk-ops-contract-gate` keeps the AI model-risk operations
  contract aligned to implemented AI explanation/readiness telemetry and blocks
  premature dashboard, alert, `lotus-ai`, Workbench, or supported-feature
  claims.
- `make no-sensitive-content-guard` keeps local evidence and output artifacts
  free of sensitive marker names.
- `make durable-repository-proof-contract-gate` keeps the aggregate
  proof-readiness storage evidence source-safe and explicit about remaining
  production, mesh, live-source, Workbench, and supported-feature blockers.
- `make report-intake-route-proof-contract-gate` keeps the bounded
  `lotus-report` route proof source-safe and prevents it from becoming a
  false report/render/archive, client-publication, or supported-feature claim.
- `make repository-hygiene-gate` blocks generated cache, build, dependency,
  environment, and database artifacts.
- `make clean` removes ignored local byproducts through the governed cleanup
  utility that the CI contract gate protects.
- `make maintainability-gate` blocks oversized source, test, and script files
  or functions beyond measured thresholds.

## Documentation Map

Product and operator overview: [wiki/Overview.md](wiki/Overview.md), [wiki/Architecture.md](wiki/Architecture.md), and [wiki/Integrations.md](wiki/Integrations.md).
Governance and release posture: [wiki/Validation-And-CI.md](wiki/Validation-And-CI.md), [wiki/Supported-Features.md](wiki/Supported-Features.md), and [docs/standards/enterprise-readiness.md](docs/standards/enterprise-readiness.md).
Implementation evidence: [docs/rfcs/README.md](docs/rfcs/README.md) and [docs/operations/api-certification.md](docs/operations/api-certification.md).
Client-demo process, client-facing brief, and template: [wiki/Demo-Readiness.md](wiki/Demo-Readiness.md) and [docs/demo/](docs/demo/).

Repo-local `wiki/` is the authored source of truth. The GitHub wiki is a
publication target and should be updated through the platform wiki sync flow
after merge to `main`.
