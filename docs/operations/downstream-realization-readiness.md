# Downstream Realization Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and integration owners |
| Required role | `operator` |
| Required capability | `idea.downstream-realization.readiness.read` |
| Supportability | `not_certified` |
| Product claim | No downstream realization or supported-feature promotion |

`GET /api/v1/downstream-realization/readiness` reports source-safe readiness
for realizing approved ideas through `lotus-advise`, `lotus-manage`,
`lotus-report`, `lotus-render`, and `lotus-archive`.

## What It Proves

The diagnostic proves that `lotus-idea` can summarize its own downstream
workflow foundation without overstepping downstream ownership boundaries.

It returns:

1. current `lotus-idea` conversion intent count,
2. current conversion outcome count,
3. current report evidence-pack request count,
4. source-of-truth implementation paths,
5. capability-level blockers for Advise, Manage, and Report/Render/Archive
   realization,
6. `not_certified` supportability until downstream live contracts and product
   proof exist.

## What It Does Not Prove

The diagnostic is deliberately not downstream execution proof. It does not:

1. call downstream Lotus services,
2. create Advise proposals or suitability records,
3. create Manage action-register, model, rebalance, or execution records,
4. create Report packages,
5. create Render output,
6. create Archive records,
7. authorize publication of client-facing material,
8. promote a supported feature.

## Current Blockers

The response remains `blocked` until all of the following are implemented and
validated through the owning repositories and platform gates:

1. `lotus-advise` proposal/suitability intake is implemented and certified,
2. `lotus-manage` action-register or DPM review intake is implemented and
   certified,
3. `lotus-report`, `lotus-render`, and `lotus-archive` materialization proof
   exists for an idea evidence pack,
4. downstream live contract proof is captured,
5. Gateway/Workbench product proof exists where a product surface consumes the
   flow,
6. data-mesh runtime trust telemetry and platform certification are complete,
7. supported-feature promotion evidence is present.

## Response Shape

The success response is intentionally aggregate and source-safe:

| Field | Meaning |
| --- | --- |
| `conversionIntentCount` | Count of `lotus-idea` conversion intents in the active repository provider |
| `conversionOutcomeCount` | Count of recorded downstream outcome records in `lotus-idea` |
| `reportEvidencePackRequestCount` | Count of Report/Render/Archive request records in `lotus-idea` |
| `capabilities` | Capability-level downstream readiness posture and blockers |
| `sourceOfTruth` | Implementation and RFC paths that define current behavior |
| `supportedFeaturePromoted` | Always `false` until supported-feature evidence exists |

## Evidence

Implementation-backed evidence:

1. application builder:
   `src/app/application/downstream_realization_readiness.py`,
2. API route: `src/app/api/downstream_realization_readiness.py`,
3. operation event: `downstream_realization_readiness_read`,
4. endpoint ledger:
   `docs/operations/endpoint-certification-ledger.json`,
5. unit tests:
   `tests/unit/test_downstream_realization_readiness.py`,
6. integration tests:
   `tests/integration/test_downstream_realization_readiness_api.py`.

Run:

```powershell
python -m pytest tests/unit/test_downstream_realization_readiness.py tests/integration/test_downstream_realization_readiness_api.py -q
make endpoint-certification-gate
make openapi-gate
```

## Example

```powershell
curl -H "X-Caller-Roles: operator" -H "X-Caller-Capabilities: idea.downstream-realization.readiness.read" http://localhost:8330/api/v1/downstream-realization/readiness
```

Use this endpoint when preparing RFC-0002 implementation proof or diagnosing
why downstream realization is still blocked. Use downstream service APIs and
canonical product validation only after live integration contracts are
implemented.
