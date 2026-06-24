# Downstream Realization Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and integration owners |
| Required role | `operator` |
| Required capability | `idea.downstream-realization.readiness.read` |
| Supportability | `not_certified` |
| Product claim | Internal submission posture plus default source-safe `lotus-report` route-foundation proof when sibling evidence is present; no downstream materialization, client publication, or supported-feature promotion |

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
6. source-safe application orchestration and HTTP adapter-foundation presence
   for the Advise proposal, Manage action, and Report evidence-pack handoff
   seams,
7. certified internal submission routes for existing Advise/Manage conversion
   intents and Report evidence-pack requests,
8. planned downstream contract readiness for the Advise proposal, Manage
   action, and Report evidence-pack handoff seams,
9. default source-safe proof that `lotus-report` exposes
   `POST /reports/idea-evidence-packs` for idea evidence-pack intake,
10. `not_certified` supportability until downstream live contracts and product
   proof exist.

The submission routes are:

| Route | Purpose | Required capability |
| --- | --- | --- |
| `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions` | Submit an existing Advise or Manage conversion intent through configured source-safe adapters and return bounded submission posture. | `idea.downstream-realization.submit` plus `Idempotency-Key` |
| `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions` | Submit an existing Report evidence-pack request through the configured Report adapter and return bounded submission posture. | `idea.downstream-realization.submit` plus `Idempotency-Key` |

These routes are API-certified internal foundations. They propagate
correlation, trace, and idempotency headers to configured adapters, fail closed
when adapter configuration is missing, and emit
`downstream_realization_submission` operation events with
`supportability_status=not_certified`. They do not record authoritative
downstream outcomes or promote support.

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

The submission routes also do not prove that the downstream target route exists
or accepted business authority. A downstream service remains the source of
truth for proposal creation, action creation, report package intake, render
output, archive record creation, completion, rejection, and failure reasons.

## Downstream Contract Plan

The diagnostic exposes planned contract seams from the governed source file
[contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json](../../contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json).
Implementation agents must update that contract plan when Advise, Manage, or
Report handoff truth changes; the runtime readiness snapshot reads the same
artifact that CI validates.

| Contract | Owner | Target Route Posture | Current Status |
| --- | --- | --- | --- |
| `lotus-idea-to-lotus-advise-proposal-intake:v1` | `lotus-advise` | `planned:lotus-advise-proposal-intake` | `not_certified`; adapter foundation present |
| `lotus-idea-to-lotus-manage-action-intake:v1` | `lotus-manage` | `planned:lotus-manage-action-intake` | `not_certified`; adapter foundation present |
| `lotus-idea-to-lotus-report-evidence-pack-intake:v1` | `lotus-report` | `planned:lotus-report-idea-evidence-pack-intake` when proof is invalid or absent; `POST /reports/idea-evidence-packs` when the generated or overridden report-intake route proof is valid | `not_certified`; adapter foundation present; source-safe route proof can clear only the route-existence blocker |

These contract records are planning and certification evidence only. They are
not route-existence proof in the downstream repositories by themselves. A valid
report-intake route proof generated from the merged `lotus-report` contract can
clear only `lotus_report_live_intake_route_proof_missing`; materialization,
render, archive, client-publication, and supported-feature blockers remain.

`make downstream-realization-contract-gate` blocks:

1. missing Advise, Manage, or Report contract records,
2. premature `supported`, route-existence, downstream-execution, or
   supported-feature claims,
3. contract rows that move source authority into `lotus-idea`,
4. planned target routes that are rewritten as current downstream routes,
5. missing blocker or evidence references,
6. broken source-of-truth paths.

## Current Blockers

The response remains `blocked` until all of the following are implemented and
validated through the owning repositories and platform gates:

1. `lotus-advise` proposal/suitability intake is implemented and certified,
2. `lotus-manage` action-register or DPM review intake is implemented and
   certified,
3. `lotus-report`, `lotus-render`, and `lotus-archive` materialization proof
   exists for an idea evidence pack,
4. downstream live contract proof is captured beyond route-foundation posture,
5. Gateway/Workbench product proof exists where a product surface consumes the
   flow,
6. data-mesh runtime trust telemetry and platform certification are complete,
7. supported-feature promotion evidence is present.

## Report Intake Route Proof

`scripts/generate_report_intake_route_proof.py` can read the sibling
`lotus-report` contract and produce a source-safe artifact such as:

```powershell
python scripts/generate_report_intake_route_proof.py `
  --generated-at-utc 2026-06-24T00:00:00Z `
  --report-root ..\lotus-report `
  --output output\downstream\report-intake-route-proof.json
```

`make implementation-proof-readiness-check` generates this artifact by default
from `LOTUS_REPORT_ROOT=../lotus-report` into
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT=output/downstream/report-intake-route-proof.json`
and passes it to aggregate readiness. Set
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` only when you need to override that
artifact. Missing sibling evidence writes an invalid non-proof artifact and
keeps the route blocker. A valid artifact proves only that `lotus-report` owns
a live intake route for source-safe idea evidence-pack handoff. It deliberately
keeps these blockers:

| Remaining blocker | Why it remains |
| --- | --- |
| `report_evidence_pack_live_materialization_proof_missing` | No `lotus-report` report job or report package is created. |
| `rendered_output_creation_missing` | No `lotus-render` output exists. |
| `archive_record_creation_missing` | No `lotus-archive` record, retention action, legal hold, or retrieval ref exists. |
| `client_publication_authority_blocked` | No client-ready communication authority is granted. |

## Response Shape

The success response is intentionally aggregate and source-safe:

| Field | Meaning |
| --- | --- |
| `conversionIntentCount` | Count of `lotus-idea` conversion intents in the active repository provider |
| `conversionOutcomeCount` | Count of recorded downstream outcome records in `lotus-idea` |
| `reportEvidencePackRequestCount` | Count of Report/Render/Archive request records in `lotus-idea` |
| `downstreamAdapterFoundationPresent` | Whether the repo contains source-safe downstream orchestration, adapter ports, and HTTP adapter foundations |
| `capabilities` | Capability-level downstream readiness posture and blockers |
| `downstreamContracts` | Planned downstream handoff contracts, owner repositories, target route posture, adapter status, evidence refs, and blockers |
| `sourceOfTruth` | Implementation and RFC paths that define current behavior |
| `supportedFeaturePromoted` | Always `false` until supported-feature evidence exists |

## Adapter Configuration

The submission routes require explicit adapter configuration. Missing or blank
configuration returns product-safe `503 downstream_realization_not_configured`
instead of silently pretending to submit work.

| Adapter | Base URL env var | Submit path env var |
| --- | --- | --- |
| Advise proposal realization | `LOTUS_IDEA_ADVISE_REALIZATION_BASE_URL` | `LOTUS_IDEA_ADVISE_REALIZATION_SUBMIT_PATH` |
| Manage action realization | `LOTUS_IDEA_MANAGE_REALIZATION_BASE_URL` | `LOTUS_IDEA_MANAGE_REALIZATION_SUBMIT_PATH` |
| Report evidence-pack realization | `LOTUS_IDEA_REPORT_REALIZATION_BASE_URL` | `LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH` |

`LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS` controls the HTTP adapter
timeout and defaults conservatively when absent.

## Evidence

Implementation-backed evidence:

1. application builder:
   `src/app/application/downstream_realization_readiness.py`,
2. downstream realization orchestration:
   `src/app/application/downstream_realization.py`,
3. downstream submission API:
   `src/app/api/downstream_realization.py`,
4. downstream adapter port:
   `src/app/ports/downstream_realization.py`,
5. downstream adapter foundation:
   `src/app/infrastructure/downstream_realization.py`,
6. governed contract plan:
   `contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`,
7. report-owned planned intake contract:
   `lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`,
8. contract gate: `scripts/downstream_realization_contract_gate.py`,
9. report route proof generator:
   `scripts/generate_report_intake_route_proof.py`,
10. report route proof gate:
    `scripts/report_intake_route_proof_contract_gate.py`,
11. readiness API route: `src/app/api/downstream_realization_readiness.py`,
12. operation events:
   `downstream_realization_readiness_read` and
   `downstream_realization_submission`,
13. endpoint ledger:
   `docs/operations/endpoint-certification-ledger.json`,
14. unit tests:
   `tests/unit/test_downstream_realization_readiness.py`,
15. application orchestration tests:
   `tests/unit/test_downstream_realization_application.py`,
16. adapter tests:
   `tests/unit/test_downstream_realization_adapters.py`,
17. gate tests:
   `tests/unit/test_downstream_realization_contract_gate.py`,
18. route proof tests:
    `tests/unit/test_report_intake_route_proof.py`,
19. integration tests:
   `tests/integration/test_downstream_realization_readiness_api.py` and
   `tests/integration/test_downstream_realization_api.py`.

Run:

```powershell
python -m pytest tests/unit/test_downstream_realization_application.py tests/unit/test_downstream_realization_adapters.py tests/unit/test_downstream_realization_readiness.py tests/integration/test_downstream_realization_api.py tests/integration/test_downstream_realization_readiness_api.py -q
make downstream-realization-contract-gate
make report-intake-route-proof-contract-gate
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
