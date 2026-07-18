# Downstream Realization Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and integration owners |
| Required role | `operator` |
| Required capability | `idea.downstream-realization.readiness.read` |
| Supportability | `not_certified` |
| Product claim | Internal submission posture plus default source-safe `lotus-advise`, `lotus-manage`, and `lotus-report` route-foundation evidence when sibling contracts are present; the `lotus-report` materialization source contract clears no blocker; no report-job execution, rendered output, archive record, suitability, rebalance/execution, client publication, or supported-feature promotion |

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
9. default source-safe proof that `lotus-advise` exposes
   `POST /advisory/proposals/idea-intake` for proposal intake when sibling
   evidence is present,
10. default source-safe proof that `lotus-manage` exposes
    `POST /api/v1/rebalance/idea-action-intake` for action intake when sibling
    evidence is present,
11. default source-safe proof that `lotus-report` exposes
    `POST /reports/idea-evidence-packs` for idea evidence-pack intake,
12. default source-contract evidence that `lotus-report` declares
    `POST /reports/idea-evidence-packs/materializations` as a report-owned route
    without asserting runtime execution, rendered output, or archive creation,
13. `not_certified` supportability until downstream live contracts and product
   proof exist.

When PostgreSQL is the active durable provider, the three workflow counts use a
repository-side readiness projection over `idea_conversion_intent`,
`idea_conversion_outcome`, and `idea_report_evidence_pack_request`. The
ordinary readiness read does not hydrate candidate snapshots, audit history,
outbox events, downstream-submission records, or AI explanation lineage.

The submission routes are:

| Route | Purpose | Required capability |
| --- | --- | --- |
| `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions` | Submit an existing Advise or Manage conversion intent through configured source-safe adapters and return bounded submission posture. | `idea.downstream-realization.submit` plus `Idempotency-Key` |
| `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions` | Submit an existing Report evidence-pack request through the configured Report adapter and return bounded submission posture. | `idea.downstream-realization.submit` plus `Idempotency-Key` |

These routes are API-certified internal foundations. They propagate
correlation, trace, and idempotency headers to configured adapters after a
local idempotency precheck. The repository stores source authority, target,
resource id, bounded posture, bounded failure reason, correlation id, trace id,
and timestamp by idempotency key without storing sensitive request payloads.
The same key and request fingerprint replays the stored posture without another
adapter call; the same key with a different resource/target/source-authority
fingerprint returns `409 idempotency_conflict`. Missing adapter configuration
is recorded as a replayable `downstream_realization_not_configured` posture and
returns `503`. The routes emit
`downstream_realization_submission` operation events with
`supportability_status=not_certified`. They do not record authoritative
downstream outcomes or promote support.

## What It Does Not Prove

The diagnostic is deliberately not downstream execution authority. It does not:

1. call downstream Lotus services,
2. create Advise proposals or suitability records,
3. create Manage action-register, model, rebalance, or execution records,
4. create Report packages from within `lotus-idea`,
5. create Render output from within `lotus-idea`,
6. create Archive records from within `lotus-idea`,
7. grant suitability, rebalance, execution, or client-communication authority,
8. authorize publication of client-facing material,
9. promote a supported feature.

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
| `lotus-idea-to-lotus-advise-proposal-intake:v1` | `lotus-advise` | Contract-plan target remains unchanged when Advise source-contract evidence is present | `not_certified`; static declarations add provenance but do not prove serving or acceptance |
| `lotus-idea-to-lotus-manage-action-intake:v1` | `lotus-manage` | Contract-plan target remains unchanged when Manage source-contract evidence is present | `not_certified`; static declarations add provenance but do not prove serving or acceptance |
| `lotus-idea-to-lotus-report-evidence-pack-intake:v1` | `lotus-report` | `planned:lotus-report-idea-evidence-pack-intake`; a valid source-contract artifact may cite the declared `POST /reports/idea-evidence-packs` route as provenance but cannot make it a current runtime target | `not_certified`; adapter foundation present; source-contract evidence clears no blocker |

These contract records are planning and certification evidence only. They are
not route-existence proof in the downstream repositories by themselves. Valid
route proofs generated from merged sibling contracts can clear only these route
existence blockers:

| Proof | Blocker it may clear | Boundaries that remain |
| --- | --- | --- |
| Advise route source contract | `advise_live_contract_proof_missing` | Source declarations do not prove serving, authorization, tenant isolation, request acceptance, or a downstream proposal record. Suitability and proposal authority remain with `lotus-advise`. |
| Manage route source contract | `manage_live_contract_proof_missing` | Source declarations do not prove serving, authorization, tenant isolation, request acceptance, or a downstream action record. Rebalance/execution authority remains with `lotus-manage`. |
| Report intake route source contract | None | `lotus_report_live_intake_route_proof_missing` remains, together with report materialization, render output, archive record creation, client publication, and supported-feature promotion boundaries owned by Report/Render/Archive. |
| Report materialization source contract | None | Materialization execution, rendered output creation, archive record creation, client publication, and supported-feature promotion remain blocked; `lotus-report`, `lotus-render`, and `lotus-archive` retain downstream authority. |

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
3. downstream live contract proof is captured beyond route-foundation and
   materialization posture,
4. Gateway/Workbench product proof exists where a product surface consumes the
   flow,
5. data-mesh runtime trust telemetry and platform certification are complete,
6. client-publication authority is explicitly granted by owning services,
7. supported-feature promotion evidence is present.

## Advise And Manage Route Source Contracts

`scripts/downstream_realization/generate_advise_route_source_contract.py` and
`scripts/downstream_realization/generate_manage_route_source_contract.py` can read sibling `lotus-advise`
and `lotus-manage` declarations and produce digest-bound `source_contract`
artifacts:

```powershell
python scripts/downstream_realization/generate_advise_route_source_contract.py `
  --generated-at-utc 2026-06-27T00:00:00Z `
  --advise-root ..\lotus-advise `
  --output output\downstream\advise-route-source-contract-proof.json

python scripts/downstream_realization/generate_manage_route_source_contract.py `
  --generated-at-utc 2026-06-27T00:00:00Z `
  --manage-root ..\lotus-manage `
  --output output\downstream\manage-route-source-contract-proof.json
```

`make implementation-proof-readiness-check` generates both artifacts by
default from `LOTUS_ADVISE_ROOT=../lotus-advise` and
`LOTUS_MANAGE_ROOT=../lotus-manage`, then passes them to aggregate readiness.
Set `LOTUS_IDEA_ADVISE_ROUTE_SOURCE_CONTRACT_PROOF` or
`LOTUS_IDEA_MANAGE_ROUTE_SOURCE_CONTRACT_PROOF` only when you need to override the
generated artifact. Missing sibling evidence writes an invalid non-proof
artifact and keeps the corresponding blocker. Drift in present sibling
evidence exits non-zero so contract mismatch is not hidden.

A valid artifact proves only that the owning repository contains the declared
contract and route/service source at the bound SHA-256 values. It does not
observe route serving, caller authorization, tenant isolation, request
execution, or downstream record acceptance. Aggregate and downstream readiness
attach the artifact reference as supporting evidence without changing blocker
or route-fit posture. Both artifacts deliberately keep these blockers:

| Remaining blocker | Why it remains |
| --- | --- |
| `advise_live_contract_proof_missing` | No governed runtime receipt proves the Advise route served and accepted a bounded request. |
| `manage_live_contract_proof_missing` | No governed runtime receipt proves the Manage route served and accepted a bounded request. |
| `suitability_policy_authority_remains_lotus_advise` | `lotus-advise` remains the downstream authority for suitability, policy approval, advisory proposal lifecycle, and client communication. |
| `rebalance_execution_authority_remains_lotus_manage` | `lotus-manage` remains the source authority for action-register, DPM/rebalance workflow, order/execution, and settlement posture. |
| `client_publication_authority_blocked` | No client-ready communication authority is granted. |

## Report Materialization Source Contract

`scripts/report/generate_materialization_source_contract.py` can read the sibling
`lotus-report` materialization contract and produce a source-safe artifact such
as:

```powershell
python scripts/report/generate_materialization_source_contract.py `
  --generated-at-utc 2026-06-27T00:00:00Z `
  --report-root ..\lotus-report `
  --output output\report\materialization-source-contract-proof.json
```

`make implementation-proof-readiness-check` generates this artifact by default
from `LOTUS_REPORT_ROOT=../lotus-report` into
`LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF_OUTPUT=output/report/materialization-source-contract-proof.json`
and passes it to aggregate readiness. Set
`LOTUS_IDEA_REPORT_MATERIALIZATION_SOURCE_CONTRACT_PROOF` only when you need to
override that artifact. Missing sibling evidence writes an invalid
source-contract artifact. A valid artifact confirms only the declared
`lotus-report` owner, route, product compatibility, and non-proof boundaries.
It is `source_contract` evidence: aggregate readiness may cite it but must not
change target routes, readiness status, supportability status, or blockers.
It deliberately keeps these blockers:

| Remaining blocker | Why it remains |
| --- | --- |
| `report_evidence_pack_live_materialization_proof_missing` | A source declaration is not execution evidence from a report materialization job. |
| `rendered_output_creation_missing` | No rendered output instance or digest was observed. |
| `archive_record_creation_missing` | No archive record, retention policy, or legal-hold posture was observed. |
| `client_publication_authority_blocked` | No client-ready communication authority is granted. |
| `supported_feature_promotion_missing` | Source-contract compatibility is not supported-feature promotion. |

## Report Intake Route Source Contract

`scripts/report/generate_intake_route_source_contract.py` can read the sibling
`lotus-report` contract and produce a source-safe artifact such as:

```powershell
python scripts/report/generate_intake_route_source_contract.py `
  --generated-at-utc 2026-06-24T00:00:00Z `
  --report-root ..\lotus-report `
  --output output\report\intake-route-source-contract-proof.json
```

`make implementation-proof-readiness-check` generates this artifact by default
from `LOTUS_REPORT_ROOT=../lotus-report` into
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF_OUTPUT=output/report/intake-route-source-contract-proof.json`
and passes it to aggregate readiness. Set
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_SOURCE_CONTRACT_PROOF` only when you need to override that
artifact. Missing sibling evidence writes an invalid non-proof artifact and
keeps the route blocker. A valid artifact proves only that a governed sibling
contract declares `lotus-report` ownership of the intended intake route. It
does not observe route serving, authorization, tenant isolation, or request
execution, clears no blocker, and deliberately keeps these blockers:

| Remaining blocker | Why it remains |
| --- | --- |
| `lotus_report_live_intake_route_proof_missing` | Static sibling contracts do not prove that the Report runtime serves or accepts the handoff route. |
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

## Submission Recovery

Every outbound submission is claimed durably before an adapter can run. The
submission response is authoritative only for local posture:

| HTTP/posture | Meaning | Operator action |
| --- | --- | --- |
| `200 accepted_by_downstream` | The adapter reported acceptance and the local terminal state committed. | Await source-owned conversion outcome; do not infer suitability or execution. |
| `200 rejected_by_downstream` | The adapter reported a definitive rejection and the local terminal state committed. | Correct the source-owned request condition through the owning workflow. |
| `202 reconciliation_required` | The downstream result or local finalization is uncertain. | Verify the downstream receipt, then reconcile by opaque support reference. |
| `503 downstream_realization_not_configured` | The local adapter is absent and that posture is durable. | Configure the governed adapter; do not reuse the same key to force a call. |

Inspect uncertain work:

```powershell
curl `
  -H "X-Caller-Subject: platform-operator" `
  -H "X-Caller-Roles: operator" `
  -H "X-Caller-Capabilities: idea.downstream-reconciliation.read" `
  http://localhost:8330/api/v1/downstream-submissions/reconciliation
```

Resolve only after checking the source-owned downstream receipt. The mutation
identity and operational change reference are intentionally the same value:

```powershell
curl -X POST `
  -H "Content-Type: application/json" `
  -H "X-Caller-Subject: platform-operator" `
  -H "X-Caller-Roles: operator" `
  -H "X-Caller-Capabilities: idea.downstream-reconciliation.resolve" `
  -H "Idempotency-Key: CHG-334-001" `
  -d '{"resolution":"accepted_by_downstream","reason":"downstream_receipt_verified","changeReference":"CHG-334-001"}' `
  http://localhost:8330/api/v1/downstream-submissions/reconciliation/downstream-submission-0123456789abcdef01234567
```

Exact repeats return `replayed`. Reusing a change reference for another
resolution, reason, or actor returns `409`. The recovery route never calls the
downstream service and never creates an authoritative conversion outcome.

## Adapter Configuration

The submission routes require explicit adapter configuration. Missing or blank
configuration returns product-safe `503 downstream_realization_not_configured`
instead of silently pretending to submit work.

Generated OpenAPI for downstream submission routes must publish the same stable
problem-detail codes the runtime can return. The `503` response uses named
examples so adapter-not-configured and durable repository write-readiness
failures are visible under both `application/json` and
`application/problem+json` without exposing downstream URLs, DSNs, hostnames,
raw adapter errors, request payloads, response payloads, or idempotency keys.

| Adapter | Base URL env var | Submit path env var |
| --- | --- | --- |
| Advise proposal realization | `LOTUS_IDEA_ADVISE_REALIZATION_BASE_URL` | `LOTUS_IDEA_ADVISE_REALIZATION_SUBMIT_PATH` |
| Manage action realization | `LOTUS_IDEA_MANAGE_REALIZATION_BASE_URL` | `LOTUS_IDEA_MANAGE_REALIZATION_SUBMIT_PATH` |
| Report evidence-pack realization | `LOTUS_IDEA_REPORT_REALIZATION_BASE_URL` | `LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH` |

Local Compose configures all three realization pairs to the canonical Advise,
Manage, and Report owner routes. These variables are distinct from source-read
base URLs: configuring `LOTUS_ADVISE_BASE_URL` does not configure proposal
realization. `make ci-contract-gate` blocks missing Compose realization wiring
so a healthy source adapter cannot mask an unavailable downstream handoff.

`LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS` controls the HTTP adapter
timeout and defaults conservatively when absent.

### Local Manage And Report Intake Fixtures

Until the platform has trusted service identity and an identity-provider claim
mapping, local Compose supplies a development-only Manage intake fixture from
server process configuration. It is never read from browser or caller request
headers. The fixture is restricted in code to the `local` and `test` runtime
profiles; `demo`, `staging`, and `production` fail closed before any Manage
call, even when the variables are present.

| Server-side environment variable | Local Compose value |
| --- | --- |
| `LOTUS_IDEA_MANAGE_REALIZATION_ACTOR_ID` | `lotus-idea-local-development` |
| `LOTUS_IDEA_MANAGE_REALIZATION_ROLE` | `service` |
| `LOTUS_IDEA_MANAGE_REALIZATION_TENANT_ID` | `local-development` |
| `LOTUS_IDEA_MANAGE_REALIZATION_SERVICE_IDENTITY` | `lotus-idea-local-development` |
| `LOTUS_IDEA_MANAGE_REALIZATION_CAPABILITIES` | `manage.write` |

The adapter sends these values only as `X-Actor-Id`, `X-Role`, `X-Tenant-Id`,
`X-Service-Identity`, and `X-Capabilities` to the current Manage route, in
addition to governed correlation, trace, and idempotency headers. This fixture
does not authenticate an end user, map a session or token claim, grant
suitability or rebalance authority, or certify downstream acceptance. The
future trusted identity path remains tracked in GitHub issue `#380`; this
branch keeps the fixture explicitly non-authoritative.

Report materialization has the same identity-provider deferral. The Idea adapter
maps a persisted, trusted-scope report-evidence request to the Report-owned
strict snake-case contract at
`POST /reports/idea-evidence-packs/materializations`. It projects only the
persisted candidate `portfolio_id`, requires the candidate tenant to match the
configured local/test Report fixture, derives one valid `as_of_date` from
consistent source summaries, and uses server-fixed `json` output. Missing or
mismatched scope and invalid or inconsistent dates fail before HTTP I/O;
browser-supplied scope and identity authority are never used. The nested pack
keeps the Report intake purpose, owner retention-policy selector, and
`REPORT_INTAKE_ONLY` vocabulary while the outer request uses
`REPORT_JOB_MATERIALIZATION`.
The Idea-owned persisted reference
`lotus-report:idea-evidence-retention:v1` maps only at this adapter boundary to
the Report-owned `generated-report-standard` selector; it does not alter Idea
lifecycle retention metadata or create Report, Render, Archive, or publication
authority. Local Compose supplies
the caller context from server process configuration, never from browser or
caller request headers. The fixture is restricted in code to `local` and
`test`; `demo`, `staging`, and `production` fail closed before any Report call
until a trusted service identity and IdP/session/token-claim mapping are
available.

| Server-side environment variable | Local Compose value |
| --- | --- |
| `LOTUS_IDEA_REPORT_REALIZATION_ACTOR_ID` | `lotus-idea-local-development` |
| `LOTUS_IDEA_REPORT_REALIZATION_CALLER_APPLICATION` | `lotus-idea` |
| `LOTUS_IDEA_REPORT_REALIZATION_TENANT_ID` | `tenant-sg` |
| `LOTUS_IDEA_REPORT_REALIZATION_REGION` | `APAC` |
| `LOTUS_IDEA_REPORT_REALIZATION_OUTPUT_FORMATS` | `json` |

The adapter sends these values only as `X-Actor-Id`,
`X-Caller-Application`, `X-Tenant-Id`, and `X-Region`, in addition to
correlation, trace, and idempotency headers. They do not authenticate an end
user, grant Report/Render/Archive authority, prove downstream acceptance, or
promote a supported feature. The `tenant-sg` / `APAC` / `json` values are the
Report-owned local/test fixture scope and are enforced in Lotus Idea; arbitrary
local values fail closed. The deferred production identity work remains tracked
by GitHub issue `#380`. A successful request may return a local Report JSON
job, but it is not supportable Report completion, Render output, Archive
record, retention/legal-hold, publication, or support evidence.

## Evidence

Implementation-backed evidence:

1. application builder:
   `src/app/application/downstream_realization_readiness.py`,
2. downstream realization orchestration:
   `src/app/application/downstream_realization/submission_use_cases.py`,
3. downstream submission API:
   `src/app/api/downstream_realization.py`,
4. downstream adapter port:
   `src/app/ports/downstream_realization.py`,
5. downstream adapter foundation:
   `src/app/infrastructure/downstream_realization.py`,
6. downstream submission state and PostgreSQL adapter:
   `src/app/domain/downstream_submission.py` and
   `src/app/infrastructure/postgres_downstream_submission.py`,
7. reconciliation application/API:
   `src/app/application/downstream_submission_reconciliation.py` and
   `src/app/api/downstream_submission_reconciliation.py`,
8. governed contract plan:
   `contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`,
9. versioned Advise/Manage/Report consumer wire contract:
   `contracts/downstream-realization/lotus-idea-downstream-intake-wire-contract.v1.json`,
10. report-owned planned intake contract:
   `lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`,
11. contract gate: `scripts/downstream_realization_contract_gate.py`,
12. downstream route source-contract implementation:
   `src/app/application/downstream_realization/route_source_contract.py`,
13. Advise route proof generator:
    `scripts/downstream_realization/generate_advise_route_source_contract.py`,
14. Manage route proof generator:
    `scripts/downstream_realization/generate_manage_route_source_contract.py`,
15. downstream route source-contract gate:
    `scripts/downstream_realization/route_source_contract_gate.py`,
16. focused downstream route source-contract tests:
    `tests/unit/downstream_realization/test_route_source_contract.py`,
17. report intake source-contract generator:
   `scripts/report/generate_intake_route_source_contract.py`,
18. report intake source-contract gate:
    `scripts/report/intake_route_source_contract_gate.py`,
19. report materialization source-contract generator:
   `scripts/report/generate_materialization_source_contract.py`,
20. report materialization source-contract gate:
    `scripts/report/materialization_source_contract_gate.py`,
21. readiness API route: `src/app/api/downstream_realization_readiness.py`,
22. operation events:
   `downstream_realization_readiness_read` and
   `downstream_realization_submission`, plus
   `downstream_reconciliation_read` and `downstream_reconciliation_resolve`,
23. endpoint ledger:
   `docs/operations/endpoint-certification-ledger.json`,
24. unit tests:
   `tests/unit/test_downstream_realization_readiness.py`,
25. application orchestration tests:
   `tests/unit/test_downstream_realization_application.py`,
26. adapter tests:
   `tests/unit/test_downstream_realization_adapters.py`,
27. gate tests:
   `tests/unit/test_downstream_realization_contract_gate.py`,
28. route proof tests:
    `tests/unit/downstream_realization/test_route_source_contract.py`,
29. report intake source-contract tests:
    `tests/unit/report/test_intake_route_source_contract.py`,
30. report materialization source-contract tests:
    `tests/unit/report/test_materialization_source_contract.py`,
31. submission reconciliation and real PostgreSQL tests:
   `tests/integration/test_downstream_submission_reconciliation_api.py` and
   `tests/integration/test_postgres_downstream_submission_runtime.py`,
32. integration tests:
   `tests/integration/test_downstream_realization_readiness_api.py` and
   `tests/integration/test_downstream_realization_api.py`.

Run:

```powershell
python -m pytest tests/unit/test_downstream_realization_application.py tests/unit/test_downstream_realization_adapters.py tests/unit/test_downstream_intake_wire_contract.py tests/unit/test_downstream_realization_readiness.py tests/integration/test_downstream_realization_api.py tests/integration/test_downstream_realization_readiness_api.py -q
make downstream-realization-contract-gate
make downstream-route-source-contract-proof-gate
make report-intake-route-source-contract-proof-gate
make report-materialization-source-contract-proof-gate
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
