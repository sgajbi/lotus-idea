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
live source proof, certified runtime trust telemetry, data-mesh certification,
Gateway and Workbench proof, downstream realization proof, supported-feature
registration, and evidence on `main`.

Current implemented foundations include:

- high-cash signal evaluation over caller-supplied Core evidence,
- Core-backed high-cash source ingestion orchestration and run-once worker CLI,
- candidate persistence, replay, idempotency, lifecycle, review, and feedback,
- advisor queue projection and queue readiness diagnostics,
- AI explanation governance diagnostics without provider execution,
- conversion intent, conversion outcome, and report evidence-pack request
  foundations,
- governed downstream contract-readiness diagnostics, source-safe application
  orchestration, certified internal downstream submission APIs, and HTTP
  adapter foundations for Advise, Manage, and Report handoff seams, backed by
  a repo contract plan and blocking gate, without downstream route-existence
  or execution claims,
- source-safe outbox records plus internal retry/dead-letter delivery
  semantics, a source-safe HTTP broker-publisher adapter foundation, and
  readiness diagnostics for accepted internal mutations,
- runtime trust telemetry preview, contract-shaped runtime snapshot generation,
  and data-mesh readiness diagnostics,
- PostgreSQL schema, migration, rollback, and repository adapter proof,
- bounded `lotus-gateway` read-only routes for advisor queue and candidate
  detail.

Detailed current-state inventory lives in [docs/rfcs/README.md](docs/rfcs/README.md),
[docs/operations/api-certification.md](docs/operations/api-certification.md),
[docs/operations/implementation-proof-readiness.md](docs/operations/implementation-proof-readiness.md),
and [wiki/Overview.md](wiki/Overview.md).

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

All products remain proposed and not certified until runtime behavior,
telemetry, platform catalog inclusion, Gateway and Workbench discovery,
certification evidence, and supported-feature promotion are complete.

## Architecture At A Glance

```mermaid
flowchart LR
    Core["Source authorities<br/>Core / Performance / Risk / Advise / Manage / Report"]
    Idea["lotus-idea<br/>candidate policy, lifecycle, evidence, review, conversion intent"]
    Store["Active repository<br/>process-local or PostgreSQL"]
    Gateway["lotus-gateway<br/>bounded read-only publication"]
    Workbench["lotus-workbench<br/>planned product proof"]
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
make typecheck
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
| `make test-unit` | Run unit tests. |
| `make test-integration` | Run integration tests. |
| `make test-e2e` | Run e2e tests. |
| `make openapi-gate` | Validate OpenAPI quality. |
| `make endpoint-certification-gate` | Validate certified endpoint ledger evidence. |
| `make data-mesh-contract-gate` | Validate proposed data-mesh contract posture. |
| `make downstream-realization-contract-gate` | Validate planned downstream realization contract posture. |
| `make migration-contract-gate` | Validate migration contract structure. |
| `make migration-execution-gate` | Dry-run apply and rollback migration execution. |
| `make source-ingestion-worker-check` | Validate the run-once source-ingestion manifest and source-safe check-only output contract without calling Core. |
| `make implementation-proof-readiness-check` | Generate source-safe RFC proof readiness evidence. |
| `make runtime-trust-telemetry-preview-check` | Generate source-safe runtime trust telemetry preview evidence. |
| `make runtime-trust-telemetry-snapshot-check` | Generate a source-safe runtime trust telemetry snapshot under ignored `output/trust-telemetry/runtime/`. |
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

Feature-lane checks:

```powershell
make lint
make typecheck
make test-unit
```

PR-grade local checks:

```powershell
make check
make postgres-integration-gate
make security-audit
make docker-build
```

Documentation and governance checks:

```powershell
make documentation-contract-gate
make implementation-truth-gate
make quality-scorecard-gate
make downstream-realization-contract-gate
make supported-features-gate
```

The same controls are explained in [wiki/Validation-And-CI.md](wiki/Validation-And-CI.md),
[quality/ci_quality_gates.md](quality/ci_quality_gates.md), and
[quality/quality_scorecard.md](quality/quality_scorecard.md).

## Runtime And Operations

Process-local repository state is the default. Repository-durable API behavior
is enabled only when `LOTUS_IDEA_DATABASE_URL` is configured and migrations have
been applied.

Operational entrypoints:

- local diagnostics: `/health`, `/health/live`, `/health/ready`, `/metrics`, and `/docs`
- source ingestion readiness: `/api/v1/source-ingestion/readiness`
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
- `make no-sensitive-content-guard` keeps local evidence and output artifacts
  free of sensitive marker names.
- `make repository-hygiene-gate` blocks generated cache, build, dependency,
  environment, and database artifacts.
- `make clean` removes ignored local byproducts through the governed cleanup
  utility that the CI contract gate protects.
- `make maintainability-gate` blocks oversized source, test, and script files
  or functions beyond measured thresholds.

## Documentation Map

- [wiki/Home.md](wiki/Home.md): authored source for the GitHub wiki.
- [wiki/Overview.md](wiki/Overview.md): product and current-state summary.
- [wiki/Architecture.md](wiki/Architecture.md): architecture and flow summary.
- [wiki/Integrations.md](wiki/Integrations.md): upstream and downstream map.
- [wiki/Validation-And-CI.md](wiki/Validation-And-CI.md): CI lane model and branch hygiene policy.
- [wiki/Supported-Features.md](wiki/Supported-Features.md): promotion status.
- [docs/rfcs/README.md](docs/rfcs/README.md): RFC index and slice evidence.
- [docs/standards/enterprise-readiness.md](docs/standards/enterprise-readiness.md):
  local enterprise-readiness posture.
- [docs/operations/api-certification.md](docs/operations/api-certification.md):
  certified internal endpoint inventory.

Repo-local `wiki/` is the authored source of truth. The GitHub wiki is a
publication target and should be updated through the platform wiki sync flow
after merge to `main`.
