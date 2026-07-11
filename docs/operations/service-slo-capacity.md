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

The workload runner uses the same governed evidence model for six closed
scenario families:

| Scenario | Probe | Stored evidence | Important boundary |
| --- | --- | --- | --- |
| `api` | `GET /health/ready` | Latency and accepted/error counts | Read-only; readiness is not business-feature proof. |
| `source_ingestion` | Bounded run-once endpoint | Duration and aggregate item count | Mutating; maximum 100 manifest items. |
| `outbox_delivery` | Bounded run-once endpoint | Duration, aggregate attempts, and retry posture | Mutating; unique transient idempotency keys and maximum 100 events. |
| `downstream_submission` | Pre-seeded synthetic conversion-intent or report evidence-pack handoff | End-to-end Idea submission latency and accepted/error counts | Mutating; unique transient idempotency keys. The resource path is allowlisted, transient, and never stored. |
| `dependency_failure` | Faulted source-ingestion call followed by recovery | Exact source-unavailable classification and explicit clean recovery | Only `source_unavailable` qualifies. Entitlement denial, configuration/capacity blocks, mixed failures, and generic blocked responses fail closed. |
| `postgresql` | Read-only `SELECT 1` plus aggregate connection posture | Query latency and maximum observed utilization | Observation does not prove a threshold stress/recovery exercise. |

PostgreSQL statistics are transaction-snapshot scoped. The capacity adapter clears only its
session-local statistics snapshot with `pg_stat_clear_snapshot()` immediately before reading
`pg_stat_activity`; otherwise a long-lived transaction can repeatedly report stale utilization
and fail to shed nonessential work. The adapter does not commit or roll back the caller's business
transaction.

Artifacts use `lotus-idea.service-capacity-baseline.v1` and contain aggregate
measurements only. Request or response bodies, URLs, DSNs, credentials, caller
assertions, and business identifiers are rejected or discarded.

All runs remain `report_only_baseline`. Load/soak qualification requires at
least 1,000 samples and a measured one-hour observation span for each of the
five steady-state scenarios, not merely a one-hour process lifetime. Full
certification additionally requires separately attested dependency recovery,
PostgreSQL saturation/recovery, and cost/resource evidence. These conditions
do not replace review of SLO results and operator actions.

### Safe Execution

Run the default read-only API scenario:

```powershell
make service-capacity-workload `
  SERVICE_CAPACITY_PROFILE=test `
  SERVICE_CAPACITY_SCENARIO_ARGS="--scenario api"
```

Source-ingestion, outbox, downstream-submission, and dependency-failure scenarios require
`--allow-mutating-workflows`. Production additionally requires
`--allow-production-mutations`; invoke the script directly for those flags.
Provide transient authorization or trusted-caller assertions only through
`LOTUS_IDEA_CAPACITY_AUTHORIZATION` or
`LOTUS_IDEA_CAPACITY_TRUSTED_CALLER_CONTEXT`.

The downstream scenario requires either a validated seed manifest through
`--downstream-capacity-seed` or the diagnostic
`LOTUS_IDEA_CAPACITY_DOWNSTREAM_PATH` fallback. Only governed conversion-intent
and report evidence-pack submission route shapes are accepted. The referenced
resource must be synthetic, pre-seeded through governed Idea lifecycle APIs,
and isolated from client activity.

Create the deterministic synthetic conversion intent through the layered seed
automation:

```powershell
make downstream-capacity-seed `
  SERVICE_CAPACITY_BASE_URL=http://localhost:8330 `
  DOWNSTREAM_CAPACITY_SEED_CONFIRMATION=SEED_SYNTHETIC_LOTUS_IDEA_CAPACITY_RESOURCE
```

The command calls candidate persistence, ordered lifecycle transitions, human
review approval, and conversion-intent recording through the public API. It
uses only the `capacity-synthetic-*` scope, deterministic replay identities,
environment-only credentials, bounded responses, and atomic output. The seed
manifest is explicitly `seed_only_not_capacity_evidence`, non-certifying, and
non-promoting. Bind it to a workload with
`SERVICE_CAPACITY_DOWNSTREAM_SEED_ARG="--downstream-capacity-seed <path>"`;
the runner requires exact commit/branch and synthetic provenance.

The protected load/soak producer invokes this seed command directly. Canonical
front-office automation does not yet invoke it; that cross-repository live-stack
proof remains tracked separately and must not be inferred from Idea-local CI.

### Protected Load And Soak Evidence

Dispatch `.github/workflows/service-load-soak-evidence.yml` from `main` with
the exact confirmation `RUN_CONTROLLED_LOTUS_IDEA_LOAD_SOAK`. The job runs only
in the protected `capacity-production-like` environment on the governed
`lotus-capacity-evidence` runner. It requires the Idea base URL, transient
authorization/trusted-caller context, a dedicated database URL, and governed
synthetic as-of date from protected environment configuration.

The workflow seeds an isolated synthetic downstream resource, then cycles API,
source ingestion, outbox delivery, downstream submission, and PostgreSQL
samples through shared paced rounds. Every scenario receives 1,000 samples
spanning at least 3,600 seconds. `observationSpanSeconds` is derived from
monotonic sample offsets, so a short burst followed by idle waiting fails
qualification. Dependency fault/recovery remains in its separate controlled
workflow and is never mixed into steady-state error budgets.

Before signing, the workflow runs:

```powershell
make service-load-soak-proof-gate
```

The gate enforces source-safe posture, mainline production-like provenance,
sample/span minima, zero conflicts, and the code-owned error and latency
budgets. Only then is the exact artifact attested and uploaded. An aggregate
baseline may consume it through `--load-soak-proof <path>` together with
`--verify-load-soak-attestation`; verification pins repository, signer, main
ref, and commit. The workflow must merge and execute successfully before
`load_soak_attestation_missing` can clear.

The dependency-failure scenario accepts only a classified source-unavailable
outcome: either aggregate `sourceFailureCounts` containing one or more
`source_unavailable` failures and zero other failure classes, or the governed
`502 source_dependency_unavailable` Problem Details response. Entitlement
denial and unrelated blocked outcomes never count as expected faults. Recovery
requires `runStatus` `completed` or `replayed` with all source-failure counters
at zero. This validates evidence semantics only; certification still requires
externally controlled production-like fault injection and attested execution.

Local recovery observations cannot clear
`dependency_recovery_attestation_missing`. Qualifying evidence must be emitted
by the manual, main-only `service-dependency-recovery-evidence.yml` workflow in
the protected `capacity-production-like` environment on the governed
self-hosted capacity runner. The operator must arrange the controlled
source-unavailable condition, dispatch with the exact confirmation
`RUN_CONTROLLED_LOTUS_IDEA_DEPENDENCY_RECOVERY`, and restore the authoritative
source during the configured recovery delay. The workflow validates, attests,
and uploads only the source-safe capacity artifact.

Consume the downloaded artifact only through cryptographic verification:

```powershell
make service-capacity-workload `
  SERVICE_CAPACITY_PROFILE=production-like `
  SERVICE_CAPACITY_SCENARIO_ARGS="--scenario api" `
  SERVICE_CAPACITY_DEPENDENCY_RECOVERY_PROOF_ARG="--dependency-recovery-proof <path> --verify-dependency-recovery-attestation"
```

Verification pins repository, dedicated signer workflow, `refs/heads/main`,
and source commit. The proof must contain at least one exclusively classified
fault plus one clean recovery, with zero errors and conflicts. This clears only
the dependency-recovery attestation blocker; load/soak, PostgreSQL saturation,
resource/cost, supported-feature, and mainline closure evidence remain separate.

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
make service-resource-baseline-contract-gate
```

## Resource Observation

Collect a bounded test observation from the service's Prometheus endpoint:

```powershell
make service-resource-baseline `
  SERVICE_RESOURCE_SAMPLE_COUNT=5 `
  SERVICE_RESOURCE_SAMPLE_INTERVAL_SECONDS=1
```

The adapter consumes only unlabeled `process_cpu_seconds_total`, resident and
virtual memory, and paired open/max file-descriptor metrics. Responses are
limited to 1 MiB; labeled, duplicate, incomplete, non-finite, or negative
resource measurements fail closed. The endpoint URL and raw metrics are not
stored.

The resulting `lotus-idea.service-resource-baseline.v1` artifact reports CPU
core-seconds per second, peak/average resident memory, optional virtual memory,
and optional file-descriptor utilization. It is test-classified and retains
both `production_like_resource_attestation_missing` and
`cost_attribution_evidence_missing`. Process telemetry is not billing evidence;
no cost, scale, supported-feature, or runtime-split claim follows from it.
Pass the artifact to `run_service_capacity_workload.py` with
`--resource-baseline <path>` (or set
`SERVICE_CAPACITY_RESOURCE_BASELINE_ARG`) to link the observation into the
aggregate capacity baseline. The link is accepted only for matching commit and
branch provenance and still leaves `costResourceMeasured=false`.
