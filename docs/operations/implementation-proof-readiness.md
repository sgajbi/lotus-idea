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
5. Workbench product realization,
6. downstream Advise, Manage, Report, Render, and Archive realization,
7. supported-feature promotion.

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
6. Workbench realization blockers,
7. downstream realization blockers,
8. supported-feature promotion blockers,
9. source-of-truth implementation paths.

## What It Does Not Prove

The diagnostic is deliberately not live journey proof. It does not:

1. call `lotus-core`,
2. execute source-ingestion against a live source,
3. call `lotus-ai`,
4. certify data products or runtime trust telemetry,
5. prove Gateway or Workbench product behavior,
6. create downstream proposals, manage actions, reports, rendered output, or
   archive records,
7. authorize client-ready publication,
8. promote any supported feature.

## Current Blockers

Current posture is `blocked` and `not_certified`.

That is expected. The endpoint exists so operators and implementation agents can
see the real proof gap before demo, data-mesh, Workbench, downstream, or
supported-feature promotion.

The response remains blocked until all of the following are implemented and
validated through the owning repositories and platform gates:

1. live Core source-ingestion proof,
2. scheduled worker deployment proof,
3. runtime trust telemetry and platform mesh certification,
4. Workbench panel and browser proof,
5. downstream Advise, Manage, Report, Render, and Archive realization,
6. supported-feature promotion evidence.

## Response Shape

The success response is intentionally aggregate and source-safe:

| Field | Meaning |
| --- | --- |
| `proofPosture` | Aggregate RFC-0002 proof state |
| `sourceIngestion` | Source-ingestion configuration and certification blockers |
| `advisorQueue` | Advisor queue supportability blockers |
| `aiExplanation` | AI explanation guardrail and runtime blockers |
| `dataMesh` | Data-product and mesh certification blockers |
| `workbenchRealization` | Gateway/Workbench product proof blockers |
| `downstreamRealization` | Advise, Manage, Report, Render, and Archive blockers |
| `supportedFeaturePromotion` | Supported-feature promotion blockers |
| `sourceOfTruth` | Implementation and RFC paths that define current behavior |

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
6. request or response bodies,
7. raw entitlement failures,
8. trace or correlation identifiers.

## Evidence

Implementation-backed evidence:

1. application builder: `src/app/application/implementation_proof_readiness.py`,
2. API route: `src/app/api/implementation_proof_readiness.py`,
3. artifact generator: `scripts/generate_implementation_proof_readiness.py`,
4. repo-native check: `make implementation-proof-readiness-check`,
5. operation event: `implementation_proof_readiness_read`,
6. endpoint ledger:
   `docs/operations/endpoint-certification-ledger.json`,
7. unit tests:
   `tests/unit/test_implementation_proof_readiness.py`,
8. generator tests:
   `tests/unit/test_generate_implementation_proof_readiness.py`,
9. integration tests:
   `tests/integration/test_implementation_proof_readiness_api.py`.

Run:

```powershell
python -m pytest tests/unit/test_implementation_proof_readiness.py tests/integration/test_implementation_proof_readiness_api.py -q
make implementation-proof-readiness-check
make endpoint-certification-gate
make openapi-gate
```

Use this endpoint to decide whether RFC-0002 is ready for live validation.
Use the live canonical stack only after the readiness blockers have been
cleared by implementation-backed slices.
