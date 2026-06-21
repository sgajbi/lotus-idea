# lotus-idea

`lotus-idea` is the Lotus wealth opportunity intelligence and idea lifecycle
service. It detects governed private-banking opportunities from source-owned
Lotus facts, ranks and explains candidate ideas, records review evidence, and
orchestrates conversion into advisory, portfolio-management, reporting, and
Workbench workflows.

Service profile: `domain-service`

Current status: scaffolded foundation, governance RFCs, the first pure domain
model/lifecycle foundation, an internal high-cash deterministic signal policy,
the first Core source-port and conservative HTTP adapter foundation for
high-cash evidence,
an internal persistence/replay/idempotency/audit foundation, an internal
high-cash evaluate-and-persist orchestration foundation,
deterministic scoring/review-queue projection and repository-snapshot queue
orchestration foundation, an internal advisor review/feedback governance and
workflow persistence foundation, and an internal AI governance
foundation for redaction, verifier, and fallback controls. It also exposes the
first certified internal high-cash signal evaluation and evaluate-and-persist
API foundations for caller-supplied, source-owned Core evidence, certified
internal candidate lifecycle, advisor queue, review-action, and feedback API
foundations over persisted candidates, and an internal conversion-governance
foundation for review-gated downstream intent/outcome tracking. No business feature is
supported until the relevant RFC slice has full runtime evidence, endpoint
certification, tests, data-mesh posture, downstream proof, and supported-feature
registration.

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

The first consumer dependency set is aligned to the RFC-0002 source map:
`lotus-core` portfolio state, holdings/cash balance, cash movement, cashflow
projection, and benchmark assignment; `lotus-performance` returns and mandate
performance health; `lotus-risk` risk metrics and mandate/scenario context;
`lotus-advise` proposal, policy, and copilot evidence; `lotus-manage` action
register; and `lotus-report` client report evidence. These declarations are
source-authority contracts only, not runtime certification.

## Repository Map

- `src/app/api/`: HTTP route modules, API DTO mapping, shared caller-header
  parsing, and the temporary process-local repository provider used by certified
  internal API foundations until durable persistence is implemented.
- `src/app/application/`: use-case orchestration. The current first use cases
  evaluate high-cash signals over caller-supplied Core evidence and over a
  Core source port that fetches governed Core evidence, and internally persist
  created candidates through the Slice 06 idempotency/audit repository contract.
  Internal review-queue orchestration projects persisted candidate snapshots
  through the Slice 07 deterministic queue policy and certified internal advisor
  queue API foundation. Internal candidate lifecycle orchestration records
  idempotent lifecycle transitions through the Slice 06 repository
  history/audit contract and certified internal lifecycle API foundation.
  Internal review/feedback workflow orchestration records
  governed decisions and feedback through the repository idempotency/audit
  contract and certified internal review/feedback API foundations.
- `src/app/domain/`: framework-free idea domain models, policies, scoring,
  lifecycle rules, review-queue projection, review governance, AI governance,
  conversion governance, internal persistence records, replay posture,
  idempotency, and audit primitives.
- `src/app/ports/`: source-owned service interfaces consumed by application
  logic, including the first Core high-cash evidence port.
- `src/app/infrastructure/`: adapters and clients behind ports, including a
  conservative Core high-cash source adapter that does not infer cash weight
  when Core omits a source-reported value.
- `src/app/observability/`: structured logging, correlation, metrics, tracing.
- `src/app/security/`: caller context and authorization policy.
- `src/app/resilience/`: timeout, retry, and circuit-breaker primitives.
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
make data-mesh-contract-gate
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
.venv\Scripts\python.exe scripts/ci_contract_gate.py
.venv\Scripts\python.exe scripts/data_mesh_contract_gate.py
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
Rebase auto-merge is allowed only with `LOTUS_AUTOMERGE_TOKEN` plus merged-PR
Main Releasability dispatch so post-merge release evidence is produced on
`main` by a non-suppressed merge actor.

- Bank-buyable contract:
  `lotus-platform/platform-standards/LOTUS_BANK_BUYABLE_ENGINEERING_CONTRACT.md`
- Backend refactoring and delivery playbook:
  `lotus-platform/context/playbooks/ENTERPRISE-BACKEND-REFACTORING-INSTRUCTIONS.md`
- Repository context: `REPOSITORY-ENGINEERING-CONTEXT.md`
- Demo claim ledger: `docs/demo/demo-claims.md`
- API certification guide: `docs/operations/api-certification.md`
- Observability guide: `docs/operations/observability.md`
- AI governance guide: `docs/operations/ai-governance.md`
- Conversion governance guide: `docs/operations/conversion-governance.md`
- Data mesh readiness guide: `docs/operations/mesh-readiness.md`
- Data mesh contract gate: `scripts/data_mesh_contract_gate.py`
- RFC implementation evidence guide: `evidence/rfc-implementation/README.md`
- RFC index: `docs/rfcs/README.md`
