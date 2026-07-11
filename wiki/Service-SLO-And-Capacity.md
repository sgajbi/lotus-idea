# Service SLO And Capacity

Lotus Idea has a versioned internal service/workflow SLO foundation for API,
source-ingestion, outbox-delivery, downstream-dependency, and PostgreSQL
posture. This is separate from mesh data-product freshness, completeness,
reconciliation, quality, and lineage policy.

## Current Truth

| Evidence | Current posture |
| --- | --- |
| HTTP request count and duration | Implemented with method, route-template, and status-class labels. |
| Workflow run, duration, and item throughput | Implemented for source ingestion and outbox delivery. |
| Dependency availability and duration | Implemented for governed dependencies as one logical call including retries. |
| PostgreSQL duration and outcomes | Implemented for mutations, lifecycle actions, and snapshot reads. |
| PostgreSQL capacity posture | Aggregate utilization, collection success, one-hot posture, alerts, and nonessential source/outbox shedding are implemented. |
| Error-budget rules and alerts | Implemented and tested with `promtool`. |
| Grafana dashboard | Implemented from bounded metrics and recording rules. |
| Source-safe baseline runner | Implemented for guarded API, source-ingestion, outbox, dependency-failure/recovery, and read-only PostgreSQL scenarios. |
| Production capacity certification | Blocked on load/soak, dependency-failure, pool-saturation, and cost/resource evidence. |

No tenant, client, portfolio, candidate, event, request, idempotency,
correlation, or trace identifier is permitted as a metric label.

## First Response

1. Freeze promotion when fast or sustained burn alerts fire.
2. Compare API failures with dependency and PostgreSQL panels before assigning
   fault or increasing capacity.
3. Preserve lifecycle, health, readiness, and recovery operations; defer
   nonessential background work when it amplifies saturation.
4. Use outbox recovery and downstream reconciliation rather than manual
   durable-state changes.
5. Keep the posture `not_certified` until remaining evidence blockers clear.

## Validation

```powershell
make service-slo-capacity-contract-gate
make service-capacity-baseline-contract-gate
make service-slo-rule-test
```

`make service-capacity-workload` defaults to a read-only test-profile API
baseline. Mutating workflow scenarios require explicit flags and a second
confirmation for production. Stored evidence is aggregate and report-only;
observed PostgreSQL utilization and policy execution are not saturation stress
or recovery certification.

The PostgreSQL adapter refreshes its session-local statistics snapshot before
reading aggregate connection utilization. This prevents a long-lived
transaction from masking a threshold crossing while preserving the caller's
business transaction boundary.

See `docs/operations/service-slo-capacity.md` for target values, alert response,
capacity assumptions, and non-proof boundaries.
