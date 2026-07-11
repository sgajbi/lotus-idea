# Service SLO And Capacity Policy

## Purpose

Lotus Idea separates service and workflow reliability objectives from mesh
data-product quality objectives. The service contract governs API, scheduled
source ingestion, outbox delivery, downstream submission, and PostgreSQL
operability. The mesh contract continues to govern freshness, completeness,
reconciliation, data quality, and lineage for published data products.

## Current Posture

The versioned contract, bounded runtime SLIs, recording rules, burn alerts, and
operator dashboard are implemented internal foundations. The posture remains
`not_certified`. Target values are initial engineering budgets and do not prove
production capacity until load and dependency-failure baselines, PostgreSQL
saturation evidence, and cost/resource evidence exist.

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

### Fast API Error-Budget Burn

1. Freeze feature and supported-feature promotion for the affected build.
2. Compare API p95/p99 with dependency and PostgreSQL panels. Do not classify
   a dependency failure as Lotus Idea saturation without evidence.
3. Check status-class and route-template aggregates. Never add request,
   candidate, tenant, client, or portfolio labels for diagnosis.
4. Preserve health, readiness, lifecycle authority, and recovery operations.
   Defer nonessential source-ingestion and outbox runs if they amplify load.
5. Roll back or fix forward only after verifying idempotent writes, outbox
   recovery posture, and PostgreSQL health.

### Sustained API Error-Budget Burn

1. Confirm both the 30-minute and six-hour windows are breached.
2. Review release, configuration, dependency, and traffic changes across the
   same window; do not reset the measurement window after deployment.
3. Keep promotion frozen until long-window burn returns inside budget and
   recovery checks pass.

### Workflow Error-Budget Burn

1. For source ingestion, inspect bounded batch size, dependency outcomes,
   retry pressure, and scheduled lag before increasing concurrency.
2. For outbox delivery, inspect ready count, oldest-ready age, deferred
   retries, expired leases, and dead letters before re-drive or scaling.
3. Replays are successful idempotent outcomes. Conflicts and pre-run
   configuration blocks remain separate from execution failures.
4. Use governed recovery or reconciliation. Never bypass lifecycle fencing,
   mutate durable rows manually, or infer downstream execution.

## Dashboard And Alerts

| Artifact | Purpose |
| --- | --- |
| `monitoring/grafana/dashboards/lotus-idea-service-slo.json` | API, workflow, dependency, PostgreSQL, outbox, and certification posture. |
| `monitoring/prometheus/rules/lotus-idea-service-slo.rules.yml` | Error-ratio recording rules and multi-window burn alerts. |
| `monitoring/prometheus/tests/lotus-idea-service-slo.test.yml` | Healthy and sustained-breach rule evaluation. |

Dependency availability includes bounded retries and stays separate from
service failures. PostgreSQL panels cover logical mutation, lifecycle, and
snapshot duration/outcomes. They do not expose pool utilization; the service
currently receives an injected/direct connection rather than an observable
production pool.

## Safe Labels

Metrics may use bounded route templates, methods, status classes, workflows,
operations, outcomes, dependencies, and repository identity. Tenant, client,
portfolio, candidate, event, request, idempotency, correlation, and trace
identifiers are prohibited from metric labels.

## Validation

Run:

```powershell
make service-slo-capacity-contract-gate
make service-slo-rule-test
```

Certification additionally requires representative API, worker, outbox,
downstream, and PostgreSQL load/failure scenarios plus dashboard, alert, and
operator-action proof. The contract alone must not unblock supported features.
