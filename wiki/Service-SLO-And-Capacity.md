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
| Source-safe baseline runner | Implemented for guarded API, source-ingestion, outbox, downstream intent handoff, exact source-unavailable failure/clean recovery, and read-only PostgreSQL scenarios. |
| Controlled PostgreSQL threshold proof | Implemented with exact target identity, hard connection caps, mandatory acknowledgement, release/recovery checks, and proof-only baseline linkage. Test evidence is non-certifying. |
| Process resource observation | Bounded CPU, memory, and optional file-descriptor collection is implemented through a narrow Prometheus adapter. Test observations are non-certifying and are not cost evidence. |
| Dependency recovery attestation | A manual, main-only protected workflow and exact signer verification are implemented. No qualifying artifact exists until the workflow executes successfully on `main`. |
| Production capacity certification | Blocked on load/soak, dependency-failure, pool-saturation, and cost/resource evidence. |

No tenant, client, portfolio, candidate, event, request, idempotency,
correlation, or trace identifier is permitted as a metric label.

Downstream capacity requires an allowlisted path to a pre-seeded synthetic
conversion intent or report evidence pack. `make downstream-capacity-seed`
creates the conversion intent through existing candidate, lifecycle, review,
and conversion APIs and emits an atomic non-certifying seed manifest. The
workload runner validates exact commit/branch and synthetic posture before
using the manifest. Resource identity and unique transient workload
idempotency keys are never written to capacity evidence. Canonical front-office
automation does not yet invoke this command, so live downstream load/soak
certification remains blocked.

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
make service-resource-baseline-contract-gate
make service-slo-rule-test
make postgres-capacity-threshold-proof `
  SERVICE_CAPACITY_PROFILE=test `
  POSTGRES_CAPACITY_EXPECTED_DATABASE=idea_capacity_proof `
  POSTGRES_CAPACITY_MAX_TARGET_CONNECTIONS=20 `
  POSTGRES_CAPACITY_MAX_LOAD_CONNECTIONS=20 `
  POSTGRES_CAPACITY_CONFIRMATION=SATURATE_DEDICATED_LOTUS_IDEA_POSTGRES
```

`make service-capacity-workload` defaults to a read-only test-profile API
baseline. Mutating workflow scenarios require explicit flags and a second
confirmation for production. Stored evidence is aggregate and report-only;
observed PostgreSQL utilization and policy execution are not saturation stress
or recovery certification.

Dependency-failure evidence is fail closed. Only an exact
`source_unavailable` classification qualifies; entitlement denial,
configuration or capacity blocks, mixed failures, and generic blocked responses
are rejected. Recovery requires a completed or replayed run with every source
failure counter at zero. Production certification still requires controlled,
attested fault injection and recovery execution.

The governed producer is
`.github/workflows/service-dependency-recovery-evidence.yml`. It requires the
protected capacity environment, governed self-hosted runner, and exact operator
confirmation. Consumers must use `--dependency-recovery-proof` together with
`--verify-dependency-recovery-attestation`; a local artifact or serialized
attestation claim cannot clear the blocker.

The PostgreSQL adapter refreshes its session-local statistics snapshot before
reading aggregate connection utilization. This prevents a long-lived
transaction from masking a threshold crossing while preserving the caller's
business transaction boundary.

The threshold command is test-classified, requires a dedicated database, and
reads `LOTUS_IDEA_DATABASE_URL` transiently. It cannot clear production
certification by itself. Qualifying evidence must come from the main-only
`postgres-capacity-evidence.yml` workflow, protected GitHub environment, and
dedicated runner, then pass `gh attestation verify` with exact repository,
signer-workflow, main-ref, and source-commit constraints. This path becomes
operational only after merge and protected-environment configuration.

`make service-resource-baseline` collects bounded process-resource aggregates.
It never stores the metrics URL or raw scrape and cannot clear production-like
or cost-attribution blockers. Process telemetry must not be presented as cloud
billing, unit economics, horizontal-scale evidence, or justification for a new
runtime service.
The aggregate capacity runner can link this artifact with
`--resource-baseline <path>` only when commit and branch match. A validated
link records observation provenance but does not clear cost certification.

See `docs/operations/service-slo-capacity.md` for target values, alert response,
capacity assumptions, and non-proof boundaries.
