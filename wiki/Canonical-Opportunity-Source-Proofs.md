# Canonical Opportunity Source Proofs

## Purpose

Run the RFC-0002 Slice 5 source-backed proof families against the governed
canonical front-office runtime. This proves source consumption and
deterministic signal evaluation; it does not promote a product feature.

## Preconditions

1. Start the governed Workbench stack with `npm run live:stack:up` from
   `lotus-workbench`.
2. Use the governed portfolio `PB_SG_GLOBAL_BAL_001` and its current as-of
   date.
3. Confirm `risk.dev.lotus` and `performance.dev.lotus` are reachable.
4. Use unique correlation and trace IDs for every run.

## Run

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

The aggregate artifact is written to
`output/opportunity/canonical-source-proofs/canonical-opportunity-source-proofs.json`.
It records source revision, dirty-tree posture, correlation/trace IDs, bounded
per-proof observations, and non-proof boundaries. Raw child stdout/stderr is
not copied into the artifact.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | All child artifacts passed their validators. |
| `3` | A source was stale, unavailable, incomplete, entitlement-blocked, or contract-invalid. |
| `2` | Runner configuration or artifact I/O was invalid. |

## Current Proof Families

1. Lotus Risk concentration evidence.
2. Lotus Performance returns-series underperformance evidence.
3. Lotus Performance benchmark-readiness evidence.

A valid child proof clears only its named source blocker. The aggregate does
not certify data-mesh activation, Gateway/Workbench product behavior, client
publication, official calculation authority, downstream execution, or
supported-feature promotion.

## Current Runtime Result

On 2026-07-10, canonical Risk concentration and Performance underperformance
proofs were current and valid. Performance benchmark-readiness remained
blocked by `performance_returns_series_pending`; the aggregate correctly
remained not certification-ready. Do not replace that result with
caller-supplied values or a relaxed validator.
