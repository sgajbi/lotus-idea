# Service SLO And Capacity Policy

## Purpose

Lotus Idea separates service and workflow reliability objectives from mesh
data-product quality objectives. The service contract governs API, scheduled
source ingestion, outbox delivery, downstream submission, and PostgreSQL
operability. The mesh contract continues to govern freshness, completeness,
reconciliation, data quality, and lineage for published data products.

## Current Posture

The versioned contract is an implemented internal foundation and remains
`not_certified`. Its target values are initial engineering budgets. They do not
prove production capacity until runtime SLIs, load and dependency-failure
baselines, PostgreSQL saturation evidence, recording rules, dashboards, and
burn-rate alerts are implementation-backed.

## Governed Objectives

| Workflow | Availability | p95 | p99 | Initial operating boundary |
| --- | ---: | ---: | ---: | --- |
| API | 99.9% | 500 ms | 1.5 s | Route-template and status-class aggregation only |
| Source ingestion | 99.0% | 300 s | 600 s | Maximum 100 items per bounded run |
| Outbox delivery | 99.9% | 60 s | 300 s | Maximum 100 events and three retries |
| Downstream submission | 99.0% | 2 s | 5 s | Dependency outcomes remain separate from saturation |
| PostgreSQL | 99.9% | 100 ms | 500 ms | Warn at 70% and shed nonessential work at 90% pool use |

The 28-day measurement window uses the complement of each availability target
as its error budget. Low-volume periods with fewer than 1,000 API requests are
reported as insufficient samples, never as certified success.

## Capacity And Back Pressure

Source-ingestion and outbox batch ceilings are fail-closed application limits,
not throughput certification. Dependency clients use bounded pools and
timeouts. At the PostgreSQL shed threshold, the intended policy is to reject or
defer nonessential operator and background work while preserving health,
readiness, lifecycle authority, and recovery operations. Actual load-shed code
and production pool evidence remain certification blockers.

## Error-Budget Response

Fast and slow burn windows distinguish acute failure from sustained erosion.
Exhaustion freezes promotion and reduces nonessential workload. Operators must
classify dependency failure separately from Lotus Idea saturation before
changing capacity. Do not hide errors by excluding valid requests or resetting
measurement windows.

## Safe Labels

Metrics may use bounded route templates, methods, status classes, workflows,
operations, outcomes, dependencies, and repository identity. Tenant, client,
portfolio, candidate, event, request, idempotency, correlation, and trace
identifiers are prohibited from metric labels.

## Validation

Run:

```powershell
make service-slo-capacity-contract-gate
```

Certification additionally requires representative API, worker, outbox,
downstream, and PostgreSQL load/failure scenarios plus dashboard, alert, and
operator-action proof. The contract alone must not unblock supported features.
