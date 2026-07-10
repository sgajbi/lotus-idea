# Canonical Opportunity Source Proofs

## Purpose

Run the source-backed RFC-0002 Slice 5 proof families against the governed
canonical front-office runtime and produce one attributable result. The runner
proves source consumption and deterministic signal evaluation only; it does
not promote a product feature.

## Preconditions

1. Start the governed Workbench stack using
   `lotus-workbench` `npm run live:stack:up`.
2. Confirm the canonical seed uses portfolio `PB_SG_GLOBAL_BAL_001` and the
   governed as-of date.
3. Confirm `risk.dev.lotus` and `performance.dev.lotus` resolve and are
   reachable from the host.
4. Use a unique correlation ID and trace ID for each proof run.

## Command

```powershell
make canonical-opportunity-source-proofs `
  CANONICAL_OPPORTUNITY_PORTFOLIO_ID=PB_SG_GLOBAL_BAL_001 `
  CANONICAL_OPPORTUNITY_AS_OF_DATE=2026-04-10 `
  CANONICAL_OPPORTUNITY_RISK_BASE_URL=http://risk.dev.lotus `
  CANONICAL_OPPORTUNITY_PERFORMANCE_BASE_URL=http://performance.dev.lotus `
  CANONICAL_OPPORTUNITY_GENERATED_AT_UTC=2026-07-10T00:00:00Z `
  CANONICAL_OPPORTUNITY_EVALUATED_AT_UTC=2026-07-10T00:00:00Z `
  CANONICAL_OPPORTUNITY_CORRELATION_ID=corr-canonical-proof `
  CANONICAL_OPPORTUNITY_TRACE_ID=trace-canonical-proof
```

The direct Python equivalent is:

```powershell
.\.venv\Scripts\python.exe scripts\run_canonical_opportunity_source_proofs.py `
  --portfolio-id PB_SG_GLOBAL_BAL_001 `
  --as-of-date 2026-04-10 `
  --risk-base-url http://risk.dev.lotus `
  --performance-base-url http://performance.dev.lotus `
  --generated-at-utc 2026-07-10T00:00:00Z `
  --evaluated-at-utc 2026-07-10T00:00:00Z `
  --correlation-id corr-canonical-proof `
  --trace-id trace-canonical-proof `
  --output-directory output\opportunity\canonical-source-proofs
```

## Result Interpretation

| Result | Meaning |
| --- | --- |
| Exit `0` | Every child proof exited successfully and every artifact passed its contract validator. |
| Exit `3` | At least one source was stale, unavailable, entitlement-blocked, incomplete, or contract-invalid. Treat the named blocker as real. |
| Exit `2` | Runner configuration or artifact I/O was invalid. Fix the invocation or runtime setup. |

The aggregate artifact is written to
`output/opportunity/canonical-source-proofs/canonical-opportunity-source-proofs.json`.
It includes source revision, dirty-tree posture, correlation/trace IDs,
bounded per-proof observations, and explicit non-proof boundaries. It does not
copy child process stdout/stderr.

## Current Boundary

The runner currently certifies these source-owned proof families:

1. Lotus Risk concentration evidence and deterministic concentration review.
2. Lotus Performance returns-series evidence and deterministic
   underperformance review.
3. Lotus Performance benchmark-readiness evidence for missing-benchmark
   review.

A valid child proof clears only its named source blocker. The aggregate does
not certify data-mesh activation, Gateway/Workbench product behavior, client
publication, official performance/risk methodology, downstream execution, or
supported-feature promotion.

## Troubleshooting

If Performance reports `performance_returns_series_pending`, wait for the
canonical Performance/Core data path to reach the governed as-of date and rerun
the command. The clean-tree 2026-07-10 run reached current evidence and passed
all three proof families. Do not substitute caller-supplied values or relax the
validator.

If the canonical stack fails before Idea proof execution, preserve the failing
service name and readiness response as cross-repository evidence. Idea proof
artifacts must not claim stack-wide certification from a partial runtime.
