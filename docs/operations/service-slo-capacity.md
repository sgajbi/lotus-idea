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
readiness, lifecycle authority, and recovery operations. Source-ingestion and
outbox run-once routes now enforce that policy before constructing downstream
clients or publishers. Production saturation/load-shed evidence remains a
certification blocker.

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
snapshot duration/outcomes plus bounded aggregate connection utilization,
collection success, and one-hot `normal`, `warning`, `shed`, or `unavailable`
posture. These metrics observe server connection use through the existing
repository connection; they do not certify an application connection pool.

### PostgreSQL Capacity Response

1. Treat `collection unavailable` as unknown capacity, not zero utilization.
   Nonessential source-ingestion and outbox runs fail closed until posture is
   observable again.
2. At 70% utilization, investigate connection growth, query duration,
   dependency latency, release/configuration changes, and abandoned clients.
   Do not increase concurrency before identifying the cause.
3. At 90% utilization, keep nonessential workflow shedding active. Preserve
   health, readiness, lifecycle authority, dead-letter recovery, downstream
   reconciliation, and data-lifecycle controls.
4. Verify the alert and dashboard agree with `pg_stat_activity` aggregate
   posture. Never publish DSNs, database identities, query text, or client
   identifiers in evidence.
5. Resume nonessential workflows only after utilization is below the warning
   threshold for the governed observation window and recovery checks pass.

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

## Capacity Baseline Evidence

The workload runner uses the same governed evidence model for five closed
scenario families:

| Scenario | Probe | Stored evidence | Important boundary |
| --- | --- | --- | --- |
| `api` | `GET /health/ready` | Latency and accepted/error counts | Read-only; readiness is not business-feature proof. |
| `source_ingestion` | Bounded run-once endpoint | Duration and aggregate item count | Mutating; maximum 100 manifest items. |
| `outbox_delivery` | Bounded run-once endpoint | Duration, aggregate attempts, and retry posture | Mutating; unique transient idempotency keys and maximum 100 events. |
| `dependency_failure` | Faulted source-ingestion call followed by recovery | Failure handling and explicit recovery outcome | Requires externally controlled fault injection; a blocked call is not recovery. |
| `postgresql` | Read-only `SELECT 1` plus aggregate connection posture | Query latency and maximum observed utilization | Observation does not prove a threshold stress/recovery exercise. |

PostgreSQL statistics are transaction-snapshot scoped. The capacity adapter clears only its
session-local statistics snapshot with `pg_stat_clear_snapshot()` immediately before reading
`pg_stat_activity`; otherwise a long-lived transaction can repeatedly report stale utilization
and fail to shed nonessential work. The adapter does not commit or roll back the caller's business
transaction.

Artifacts use `lotus-idea.service-capacity-baseline.v1` and contain aggregate
measurements only. Request or response bodies, URLs, DSNs, credentials, caller
assertions, and business identifiers are rejected or discarded.

Test runs remain `report_only_baseline`. Certification requires at least 1,000
samples per scenario, a one-hour observed window, production-like or production
provenance, explicit dependency recovery, a PostgreSQL saturation-threshold
exercise, and cost/resource evidence. These conditions do not replace review
of SLO results and operator actions.

### Safe Execution

Run the default read-only API scenario:

```powershell
make service-capacity-workload `
  SERVICE_CAPACITY_PROFILE=test `
  SERVICE_CAPACITY_SCENARIO_ARGS="--scenario api"
```

Source-ingestion, outbox, and dependency-failure scenarios require
`--allow-mutating-workflows`. Production additionally requires
`--allow-production-mutations`; invoke the script directly for those flags.
Provide transient authorization or trusted-caller assertions only through
`LOTUS_IDEA_CAPACITY_AUTHORIZATION` or
`LOTUS_IDEA_CAPACITY_TRUSTED_CALLER_CONTEXT`.

The PostgreSQL scenario reads `LOTUS_IDEA_DATABASE_URL` transiently. It stores
only query outcome, duration, and aggregate utilization. It does not retain the
DSN or database error detail and does not clear saturation certification.

Run threshold/recovery proof only against a dedicated bounded target:

```powershell
$env:LOTUS_IDEA_DATABASE_URL = "<transient dedicated proof DSN>"
make postgres-capacity-threshold-proof `
  SERVICE_CAPACITY_PROFILE=test `
  POSTGRES_CAPACITY_EXPECTED_DATABASE=idea_capacity_proof `
  POSTGRES_CAPACITY_MAX_TARGET_CONNECTIONS=20 `
  POSTGRES_CAPACITY_MAX_LOAD_CONNECTIONS=20 `
  POSTGRES_CAPACITY_CONFIRMATION=SATURATE_DEDICATED_LOTUS_IDEA_POSTGRES
```

The command verifies the exact database identity and refuses targets above the
declared connection cap. It is test-classified and always releases held
connections. A baseline accepts `--postgres-threshold-proof <path>` as
behavioral evidence but cannot clear saturation from that file alone.

Qualifying evidence must be produced by the manual, main-only
`postgres-capacity-evidence.yml` workflow through the protected
`capacity-production-like` GitHub environment on a dedicated
`lotus-capacity-evidence` runner. The baseline must additionally receive
`--verify-postgres-threshold-attestation`; verification pins the repository,
signer workflow, `refs/heads/main`, and source commit. The workflow and
protected runtime must exist on `main` before qualifying evidence can be
produced. Cost/resource evidence has no equivalent attested artifact yet and
therefore cannot clear its blocker.

Validate the evidence boundary independently:

```powershell
make service-capacity-baseline-contract-gate
```
