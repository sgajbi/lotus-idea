# Getting Started

Current posture: `lotus-idea` is an RFC-0002 foundation implementation. Internal deterministic
signal evaluation, candidate lifecycle, review, proof-readiness, and source-proof automation exist;
no external business feature is supported or promoted yet.

This page gets you a running local service and a green validation run. For what the service *is*,
read [Overview](Overview) first; for the route inventory, [API Surface](API-Surface).

## Prerequisites

| Requirement | Version | Needed for |
| --- | --- | --- |
| Python | `>= 3.12`, pinned in `pyproject.toml` | Everything. |
| PostgreSQL | `18-alpine`, provided by `docker-compose.yml` | Durable providers, integration tests, and `make migration-execution-gate`. `local` and `test` profiles may use process-local writes; production-like profiles require PostgreSQL and fail closed without it. |
| Docker | any current engine | `docker-compose.yml`, `make docker-build`, and container proofs. |

## First run

```powershell
make install
```

`make install` creates `.venv`, upgrades `pip`, and installs the project **editable** with its dev
extras against `requirements/runtime-resolved.lock.txt`. That editable install is what makes
`app.main` importable, so run it before `uvicorn` or any direct `python scripts/...` call.

```powershell
uvicorn app.main:app --reload --port 8330
```

Verify it came up:

```powershell
Invoke-RestMethod http://127.0.0.1:8330/health/ready
```

`/health/ready` publishes code-owned `200 ready` and source-safe `503` draining, restoring,
durable-repository, and release-identity traffic-control modes, so a `503` here is a governed
answer rather than a crash. [Operations Runbook](Operations-Runbook) explains how to read each
mode.

## Validate a change

```powershell
make check
```

`check` runs lint, typecheck, the architecture boundary gate, `openapi-gate`, both migration gates,
`supported-features-gate`, `endpoint-certification-gate`, and the test suite. Run it before every
PR. `make ci` additionally runs integration, e2e, coverage, and the security audit.

Narrower loops while working:

```powershell
make test-unit
make test-integration
make lint
make typecheck
```

## What the running service exposes

The application serves **66 routes**: **61** appear in the generated OpenAPI document, and **5** are
deliberately excluded from the schema.

| Excluded from OpenAPI | Purpose |
| --- | --- |
| `/metrics` | Prometheus scrape target. Because it is outside the schema it does not appear in `/docs` or in the endpoint certification ledger. |
| `/openapi.json` | The generated document itself. |
| `/docs`, `/docs/oauth2-redirect` | Swagger UI. |
| `/redoc` | ReDoc UI. |

The 61 schema routes are grouped and bounded in [API Surface](API-Surface). The machine-readable
inventory is `docs/operations/endpoint-certification-ledger.json`, which
`make endpoint-certification-gate` verifies against the generated document.

## Beyond the local loop

Running the canonical opportunity source proofs needs **live Lotus Risk and Lotus Performance
endpoints** plus a governed portfolio, so it is not part of first-run setup. The command, its
required environment, and how to read its evidence are on
[Canonical Opportunity Source Proofs](Canonical-Opportunity-Source-Proofs) and in
`docs/operations/canonical-opportunity-source-proofs.md`.

## Orientation reading

Read in this order; each assumes the one before it.

1. `README.md` — product boundary and quick start.
2. [Overview](Overview) — what the service does and does not own.
3. `REPOSITORY-ENGINEERING-CONTEXT.md` — current-state summary and repo-native commands.
4. [Architecture](Architecture) — components, flows, and responsibilities.
5. [API Surface](API-Surface) — route families and their boundaries.
6. `supported-features/supported-features.json` — the authoritative support truth.
7. `docs/rfcs/README.md` and `docs/rfcs/RFC-0002-enterprise-opportunity-intelligence-operating-layer/` — why the current shape exists.

## Do not infer

A green `make check` proves repository-native validation, not product support. Product behavior is
promoted only after implementation, endpoint certification, supported-feature registration, CI
evidence, and wiki publication. Client publication, suitability approval, data-mesh certification,
live-provider execution, and Workbench support each require their own evidence in the owning
repository before any claim is made.
