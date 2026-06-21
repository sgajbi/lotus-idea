# lotus-idea

`lotus-idea` is the Lotus wealth opportunity intelligence and idea lifecycle
service. It detects governed private-banking opportunities from source-owned
Lotus facts, ranks and explains candidate ideas, records review evidence, and
orchestrates conversion into advisory, portfolio-management, reporting, and
Workbench workflows.

Service profile: `domain-service`

Current status: scaffolded foundation and governance RFCs only. No business
feature is supported until the relevant RFC slice has implementation evidence,
endpoint certification, tests, and supported-feature registration.

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

## Repository Map

- `src/app/api/`: HTTP route modules and API DTO mapping.
- `src/app/application/`: use-case orchestration.
- `src/app/domain/`: framework-free idea domain models, policies, scoring, and
  lifecycle rules.
- `src/app/ports/`: source-owned service interfaces consumed by application logic.
- `src/app/infrastructure/`: adapters and clients behind ports.
- `src/app/observability/`: structured logging, correlation, metrics, tracing.
- `src/app/security/`: caller context and authorization policy.
- `src/app/resilience/`: timeout, retry, and circuit-breaker primitives.
- `contracts/`: data-product and integration contract placeholders.
- `docs/architecture/adr/`: durable architecture decisions.
- `docs/rfcs/`: governed implementation roadmap.
- `supported-features/`: implementation-backed feature registry.
- `wiki/`: in-repo GitHub wiki source.

## Quick Start

```powershell
make install
make lint
make typecheck
make architecture-boundary-gate
make architecture-boundary-report
make quality-baseline
make openapi-gate
make check
make ci
```

Equivalent explicit commands:

```powershell
.venv\Scripts\python.exe -m pip install -e '.[dev]'
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m mypy --config-file mypy.ini
.venv\Scripts\python.exe scripts/openapi_quality_gate.py
.venv\Scripts\python.exe -m pytest tests/unit tests/integration tests/e2e
.venv\Scripts\python.exe scripts/coverage_gate.py
```

## Run Locally

```powershell
uvicorn app.main:app --reload --port 8330
```

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

- Bank-buyable contract:
  `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`
- Backend refactoring and delivery playbook:
  `lotus-platform/context/playbooks/ENTERPRISE-BACKEND-REFACTORING-INSTRUCTIONS.md`
- Repository context: `REPOSITORY-ENGINEERING-CONTEXT.md`
- Demo claim ledger: `docs/demo/demo-claims.md`
- API certification guide: `docs/operations/api-certification.md`
- Observability guide: `docs/operations/observability.md`
- RFC implementation evidence guide: `evidence/rfc-implementation/README.md`
- RFC index: `docs/rfcs/README.md`
