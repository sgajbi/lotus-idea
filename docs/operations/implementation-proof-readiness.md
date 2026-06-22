# Implementation Proof Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and release reviewers |
| Required role | `operator` |
| Required capability | `idea.implementation-proof.readiness.read` |
| Required query | Timezone-aware `evaluatedAtUtc` |
| Supportability | `not_certified` while blockers remain |
| Product claim | No live proof, client-ready publication, or supported-feature promotion |

`GET /api/v1/implementation-proof/readiness` is the internal operator
diagnostic for RFC-0002 implementation proof posture.

It aggregates current evidence and blockers across:

1. source-owned high-cash signal ingestion,
2. deterministic advisor review queue,
3. AI-assisted explanation governance,
4. data-mesh producer and consumer certification,
5. source-safe runtime trust telemetry preview, snapshot endpoint, and snapshot generation,
6. internal outbox delivery foundation and bounded run-once operator action,
7. Workbench product realization,
8. downstream Advise, Manage, Report, Render, and Archive realization,
9. supported-feature promotion.

## What It Proves

The diagnostic proves that `lotus-idea` can produce a source-safe, aggregate
readiness view over the current RFC-0002 implementation foundations and known
proof blockers.

It returns:

1. the current aggregate proof posture,
2. source-ingestion readiness posture,
3. advisor queue readiness posture,
4. AI explanation readiness posture,
5. data-mesh readiness posture,
6. runtime trust telemetry preview, snapshot endpoint, and generated snapshot posture,
7. outbox delivery readiness and run-once posture,
8. Workbench realization blockers,
9. downstream realization blockers and internal submission route evidence,
10. supported-feature promotion blockers,
11. source-of-truth implementation paths.

## What It Does Not Prove

The diagnostic is deliberately not live journey proof. It does not:

1. call `lotus-core`,
2. certify source-ingestion against a live source,
3. call `lotus-ai`,
4. certify data products or runtime trust telemetry,
5. prove Gateway or Workbench product behavior,
6. create downstream proposals, manage actions, reports, rendered output, or
   archive records,
7. authorize external publication of client-facing material,
8. promote any supported feature.

## Current Blockers

Current posture is `blocked` and `not_certified`.

That is expected. The endpoint exists so operators and implementation agents can
see the real proof gap before demo, data-mesh, Workbench, downstream, or
supported-feature promotion.

The response remains blocked until all of the following are implemented and
validated through the owning repositories and platform gates:

1. live Core source-ingestion proof beyond the bounded internal run-once API,
2. scheduled worker deployment proof,
3. certified runtime trust telemetry and platform mesh certification,
4. live broker runtime proof and downstream consumer contracts,
5. platform mesh event certification for outbox publication,
6. Workbench panel and browser proof,
7. downstream Advise, Manage, Report, Render, and Archive realization,
8. supported-feature promotion evidence.

Downstream realization blockers are backed by
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
`make downstream-realization-contract-gate` validates that the planned
contract rows stay source-authority preserving and do not become false
route-existence, downstream-execution, or supported-feature claims.
The downstream realization capability now also cites the internal submission
routes for Advise/Manage conversion intents and Report evidence-pack requests,
but those routes are submission posture only and do not clear live downstream
proof blockers.

## Response Shape

The success response is intentionally aggregate and source-safe:

| Field | Meaning |
| --- | --- |
| `readinessStatus` | Aggregate RFC-0002 proof state, currently `blocked` |
| `supportabilityStatus` | Aggregate certification posture, currently `not_certified` |
| `capabilityCount` | Number of proof families represented in `capabilities` |
| `blockedCapabilityCount` | Number of proof families still blocked by evidence gaps |
| `overallBlockers` | Source-safe blocker codes across all proof families |
| `sourceOfTruth` | Implementation, RFC, supported-feature, demo-claim, and endpoint-ledger paths |
| `capabilities[]` | Capability-level readiness records for each proof family |
| `capabilities[].capabilityId` | Stable proof-family identifier such as `source-ingestion`, `outbox-delivery`, or `downstream-realization` |
| `capabilities[].evidenceRefs` | Source-safe implementation and endpoint references |
| `capabilities[].blockers` | Source-safe blocker codes for that capability family |

## Example

```powershell
curl -H "X-Caller-Roles: operator" `
  -H "X-Caller-Capabilities: idea.implementation-proof.readiness.read" `
  "http://localhost:8330/api/v1/implementation-proof/readiness?evaluatedAtUtc=2026-06-21T10:10:00Z"
```

## Source Safety

The endpoint returns aggregate capability posture only. It does not expose:

1. candidate identifiers,
2. portfolio identifiers,
3. client identifiers,
4. source routes,
5. source payloads,
6. outbox event identifiers,
7. aggregate identifiers,
8. raw idempotency keys,
9. broker payloads,
10. request or response bodies,
11. raw entitlement failures,
12. trace or correlation identifiers.

## Evidence

Implementation-backed evidence:

1. application builder: `src/app/application/implementation_proof_readiness.py`,
2. API route: `src/app/api/implementation_proof_readiness.py`,
3. artifact generator: `scripts/generate_implementation_proof_readiness.py`,
4. repo-native check: `make implementation-proof-readiness-check`,
5. downstream contract check: `make downstream-realization-contract-gate`,
6. runtime trust telemetry snapshot check:
   `make runtime-trust-telemetry-snapshot-check`,
7. runtime trust telemetry snapshot endpoint:
   `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot`,
8. generated runtime telemetry evidence:
   `output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`,
9. source-ingestion run-once endpoint:
   `POST /api/v1/source-ingestion/run-once`,
10. source-ingestion run-once runbook:
   `docs/operations/source-ingestion-run-once.md`,
11. outbox delivery run-once endpoint:
   `POST /api/v1/outbox-delivery/run-once`,
12. operation event: `implementation_proof_readiness_read`,
13. endpoint ledger:
   `docs/operations/endpoint-certification-ledger.json`,
14. unit tests:
   `tests/unit/test_implementation_proof_readiness.py`,
15. generator tests:
   `tests/unit/test_generate_implementation_proof_readiness.py`,
16. integration tests:
   `tests/integration/test_implementation_proof_readiness_api.py`.

Run:

```powershell
python -m pytest tests/unit/test_implementation_proof_readiness.py tests/integration/test_implementation_proof_readiness_api.py -q
make implementation-proof-readiness-check
make downstream-realization-contract-gate
make runtime-trust-telemetry-snapshot-check
make endpoint-certification-gate
make openapi-gate
```

Use this endpoint to decide whether RFC-0002 is ready for live validation.
Use the live canonical stack only after the readiness blockers have been
cleared by implementation-backed slices.
