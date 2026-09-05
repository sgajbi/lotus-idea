# Downstream Realization Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and integration owners |
| Required role | `operator` |
| Required capability | `idea.downstream-realization.readiness.read` |
| Supportability | `not_certified` |
| Product claim | Internal submission posture plus default source-safe `lotus-advise`, `lotus-manage`, and `lotus-report` route-foundation evidence when sibling contracts are present; opt-in source-safe Advise and Manage intake runtime-execution proof for local/dev route serving and bounded receipt behavior; local/test-only server-side Advise, Manage, and Report service-context fixtures for owner intake routes; source contracts clear no live blocker; Advise runtime execution clears only `advise_live_contract_proof_missing`; Manage runtime execution clears only `manage_live_contract_proof_missing`; no report-job execution, rendered output, archive record, suitability, rebalance/action-register persistence/execution, client publication, production identity, or supported-feature promotion |

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
4. current local downstream submission count,
5. current unresolved downstream submission reconciliation workload count,
6. source-of-truth implementation paths,
7. capability-level blockers for Advise, Manage, and Report/Render/Archive
   realization,
7. source-safe application orchestration and HTTP adapter-foundation presence
   for the Advise proposal, Manage action, and Report evidence-pack handoff
   seams,
8. certified internal submission routes for existing Advise/Manage conversion
   intents and Report evidence-pack requests,
9. planned downstream contract readiness for the Advise proposal, Manage
   action, and Report evidence-pack handoff seams,
10. default source-safe proof that `lotus-advise` exposes
   `POST /advisory/proposals/idea-intake` for proposal intake when sibling
   evidence is present, including the owner-declared bounded receipt outcomes
   `ACCEPTED`, `ACCEPTED_REPLAYED`, and `REJECTED`,
11. opt-in source-safe runtime-execution proof that the Advise idea-intake
   route served bounded accepted, replayed, rejected, idempotency-conflict,
   authorization-denied, and tenant-scoped idempotency requests in local/dev
   scope,
12. default source-safe proof that `lotus-manage` exposes
    `POST /api/v1/rebalance/idea-action-intake` for action intake when sibling
    evidence is present,
13. opt-in source-safe runtime-execution proof that the Manage action-intake
    route served bounded accepted, replayed, rejected, idempotency-conflict,
    authorization-denied, and tenant-scoped idempotency requests in local/dev
    scope,
14. default source-safe proof that `lotus-report` exposes
    `POST /reports/idea-evidence-packs` for idea evidence-pack intake,
15. default source-contract evidence that `lotus-report` declares
    `POST /reports/idea-evidence-packs/materializations` as a report-owned route
    without asserting runtime execution, rendered output, or archive creation,
16. `not_certified` supportability until downstream live contracts and product
   proof exist.

When PostgreSQL is the active durable provider, the workflow, submission, and
reconciliation counts use a repository-side readiness projection over
`idea_conversion_intent`, `idea_conversion_outcome`,
`idea_report_evidence_pack_request`, and bounded counts from
`idea_downstream_submission`. The ordinary readiness read does not hydrate
candidate snapshots, audit history, outbox events, downstream-submission
payloads, or AI explanation lineage.

The submission routes are:

| Route | Purpose | Required capability |
| --- | --- | --- |
| `POST /api/v1/conversion-intents/{conversionIntentId}/downstream-submissions` | Submit an existing Advise or Manage conversion intent through configured source-safe adapters and return bounded submission posture. | `idea.downstream-realization.submit` plus `Idempotency-Key` |
| `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions` | Submit an existing Report evidence-pack request and return bounded submission posture plus the exact validated Report-owned materialization receipt. | `idea.downstream-realization.submit` plus `Idempotency-Key` |
| `POST /api/v1/downstream-submissions/{supportReference}/advise-realization-reconciliation` | Read the exact Advise-owned realization history for a receipt-bearing Advise submission and persist an append-only local evidence copy. | `idea.downstream-realization.reconcile` plus complete tenant/book/portfolio/client entitlement scope |
| `POST /api/v1/downstream-submissions/{supportReference}/manage-realization-reconciliation` | Read the exact Manage-owned action outcome history for a receipt-bearing Manage submission and persist an append-only local evidence copy. | `idea.downstream-realization.reconcile` plus complete tenant/book/portfolio/client entitlement scope |
| `POST /api/v1/downstream-submissions/{supportReference}/report-materialization-reconciliation` | Recover the exact Report-owned receipt for an uncertain evidence-pack submission without repeating materialization. | `idea.downstream-realization.reconcile` plus complete tenant/book/portfolio/client entitlement scope |

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
downstream outcomes or promote support. Advise is the first owner integration
to return a durable receipt on both accepted-for-review and
rejected-before-work responses. Idea persists that bounded receipt and uses it
as the only owner lookup key; HTTP success alone never becomes proposal or
business-outcome truth.

An accepted Report submission must carry a typed owner receipt. Idea validates
the exact evidence-pack identity and content fingerprint, idempotency key,
Report job identity, source-authority partition, Render/Archive creation flags
and identifiers, and the explicit publication/supportability blockers before
persisting it. Exact retries return the persisted receipt without another owner
call. Receipt validation failure is uncertain delivery requiring reconciliation;
it is never converted into Report completion or publication truth.

For an uncertain Report handoff, the Report reconciliation route authorizes
complete caller scope before owner I/O and performs one read-only lookup using
the persisted idempotency key plus exact evidence-pack, conversion-intent,
candidate, evidence fingerprint, and portfolio identity. Only an exact typed
receipt advances the existing submission. A stored receipt replays locally
without another owner read; unavailable or contradictory owner evidence leaves
the uncertain record unchanged. The route never repeats the materialization
`POST` and does not create a second submission registry.

The Advise reconciliation route authorizes complete caller scope before owner
I/O, reads the owner history through the typed port, validates source and
realization authority, scope, evidence fingerprint, exact event versions,
legal transitions, and stable work/proposal identity, then persists only an
exact replay or append-only extension. Regression, mutation of prior events,
identity drift, malformed owner evidence, and unsupported authority claims fail
closed. A rejected-before-work history is a valid terminal owner outcome with
no review-work or proposal identity; its durable receipt is not discarded.
The returned appended count is the delta committed by that serialized repository
mutation. An exact replay, including a request that loses a concurrent append
race, returns zero rather than overstating new owner progress.

## What It Does Not Prove

The diagnostic is deliberately not downstream execution authority. It does not:

1. call downstream Lotus services except through the explicitly configured
   submission and read-only reconciliation adapters described above,
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
| `lotus-idea-to-lotus-advise-proposal-intake:v1` | `lotus-advise` | Contract-plan target remains unchanged when Advise source-contract evidence is present | `not_certified`; source-contract declarations add provenance for the owner intake receipt contract and required trusted local/test headers, but Idea still needs live submission proof before clearing runtime blockers |
| `lotus-idea-to-lotus-manage-action-intake:v1` | `lotus-manage` | Contract-plan target remains unchanged when Manage source-contract evidence is present | `not_certified`; static declarations add provenance but do not prove serving or acceptance |
| `lotus-idea-to-lotus-report-evidence-pack-intake:v1` | `lotus-report` | `planned:lotus-report-idea-evidence-pack-intake`; a valid source-contract artifact may cite the declared `POST /reports/idea-evidence-packs` route as provenance but cannot make it a current runtime target | `not_certified`; adapter foundation present; source-contract evidence clears no blocker |

These contract records are planning and certification evidence only. They are
not route-existence proof in the downstream repositories by themselves. Valid
route proofs generated from merged sibling contracts are source-contract
provenance; they do not clear live route, authorization, tenant-isolation,
request-acceptance, downstream-record, or supportability blockers:

| Proof | Blocker it may clear | Boundaries that remain |
| --- | --- | --- |
| Advise route source contract | None | The owner contract declares a live executable intake receipt boundary and bounded receipt outcomes, but Idea still needs governed runtime submission evidence before `advise_live_contract_proof_missing` can clear. Suitability and proposal authority remain with `lotus-advise`. |
| Advise idea-intake runtime execution | `advise_live_contract_proof_missing` only | The proof observes bounded local/dev route serving and source-safe receipt behavior from `lotus-advise`. It does not create an advisory proposal, grant suitability or policy authority, certify production identity, authorize client publication, prove Workbench/Gateway behavior, or promote support. |
| Manage route source contract | None | The source contract must use Manage-native action-intake vocabulary (`runtime_action_receipt_proven`, `manage.idea_action_intake.accept`, bounded `ACCEPTED` / `ACCEPTED_REPLAYED` / `REJECTED` receipts). Source declarations still do not prove serving, authorization, tenant isolation, request acceptance, or a downstream action record. Rebalance/execution authority remains with `lotus-manage`. |
| Manage action-intake runtime execution | `manage_live_contract_proof_missing` only | The proof observes bounded local/dev route serving, trusted-header authorization, tenant-scoped idempotency, durable pending-review action creation, accepted/replayed/rejected receipts, idempotency conflict, and authorization denial from `lotus-manage`. It does not grant rebalance or execution authority, create orders, certify production identity, authorize client publication, prove Workbench/Gateway behavior, or promote support. |
| Report intake route source contract | None | `lotus_report_live_intake_route_proof_missing` remains, together with report materialization, render output, archive record creation, client publication, and supported-feature promotion boundaries owned by Report/Render/Archive. |
| Report intake runtime execution | `lotus_report_live_intake_route_proof_missing` only | The proof observes bounded local/dev Report route serving and source-safe accepted/replayed/conflict/rejection receipts for `POST /reports/idea-evidence-packs` through an isolated Report intake ledger. It does not create a report job, prove materialization, create rendered output, create an Archive record, grant client-publication authority, certify production identity, or promote support. |
| Report materialization source contract | None | The v4 artifact consumes the exact Report materialization and recovery declarations, links owner proofs `sgajbi/lotus-report#152` and `sgajbi/lotus-report#286`, and preserves client publication and supported-feature blockers; `lotus-report`, `lotus-render`, and `lotus-archive` retain downstream authority. |
| Report materialization local-ASGI runtime execution | `report_evidence_pack_live_materialization_proof_missing` | The proof observes bounded Report route execution with injected Render/Archive test doubles and source-safe receipt outcomes. It cannot prove live Render output or Archive custody. Those blockers require the current-source owner-service HTTP chain under #1240. It does not grant client-publication authority, retention/legal-hold authority, production identity, Workbench/Gateway behavior, supported-feature promotion, or final support certification. |

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
| `advise_live_contract_proof_missing` | Advise source-contract evidence is present only when sibling files match; Idea still needs governed runtime submission evidence proving the Advise route served and accepted a bounded request from Idea. |
| `manage_live_contract_proof_missing` | Clears only when a valid aggregate-current Manage action-intake runtime-execution proof observes bounded local/dev serving, authorization, tenant-scoped idempotency, accepted/replayed/rejected receipts, idempotency conflict, and authorization denial. Source-contract evidence alone does not clear it. |
| `suitability_policy_authority_remains_lotus_advise` | `lotus-advise` remains the downstream authority for suitability, policy approval, advisory proposal lifecycle, and client communication. |
| `rebalance_execution_authority_remains_lotus_manage` | `lotus-manage` remains the source authority for action-register, DPM/rebalance workflow, order/execution, and settlement posture. |
| `client_publication_authority_blocked` | No client-ready communication authority is granted. |

## Advise Idea-Intake Runtime Execution Proof

`scripts/downstream_realization/generate_advise_intake_runtime_execution.py`
can execute the Advise owner route through a sibling local ASGI TestClient or
an explicitly configured HTTP service and produce a source-safe
`runtime_execution` artifact:

```powershell
python scripts/downstream_realization/generate_advise_intake_runtime_execution.py `
  --generated-at-utc 2026-07-22T00:00:00Z `
  --advise-root ..\lotus-advise `
  --advise-python ..\lotus-advise\.venv-codex\Scripts\python.exe `
  --output output\downstream\advise-intake-runtime-execution-proof.json

make advise-intake-runtime-execution-proof-gate
```

`make implementation-proof-readiness-check` generates and consumes this proof
by default from `LOTUS_ADVISE_ROOT=../lotus-advise` and
`LOTUS_ADVISE_PYTHON=../lotus-advise/.venv-codex/Scripts/python.exe`. Set
`LOTUS_IDEA_ADVISE_INTAKE_RUNTIME_EXECUTION_PROOF` only when an already
generated artifact should be consumed instead.

The artifact validates closed receipt posture for accepted, replayed, rejected,
idempotency-conflict, authorization-denied, and tenant-scoped idempotency calls.
It also requires an identical concurrent duplicate pair to converge on one
accepted receipt and one exact replay, then reads Advise's owner history and
binds source-safe digests of trusted scope, source intent, and owner work plus
the evidence fingerprint, status, and version to the accepted receipt. It
stores only the bounded fields needed for that causal
proof. It clears
`advise_live_contract_proof_missing` only when the proof is valid and
aggregate-current; it deliberately preserves suitability authority, proposal
lifecycle persistence, client publication, production identity, production
certification, supported-feature, timeout, restart, owner-correction, and
concurrent owner-version advancement blockers.

## Manage Action-Intake Runtime Execution Proof

`scripts/downstream_realization/generate_manage_intake_runtime_execution.py`
can execute the Manage owner route through a sibling local ASGI TestClient or
an explicitly configured HTTP service and produce a source-safe
`runtime_execution` artifact:

```powershell
python scripts/downstream_realization/generate_manage_intake_runtime_execution.py `
  --generated-at-utc 2026-07-22T00:00:00Z `
  --manage-root ..\lotus-manage `
  --manage-python python `
  --output output\downstream\manage-intake-runtime-execution-proof.json

make manage-intake-runtime-execution-proof-gate
```

`make implementation-proof-readiness-check` generates and consumes this proof
by default from `LOTUS_MANAGE_ROOT=../lotus-manage` and
`LOTUS_MANAGE_PYTHON=python`. Override `LOTUS_MANAGE_PYTHON` only when a
repo-local Manage virtual environment is required. Set
`LOTUS_IDEA_MANAGE_INTAKE_RUNTIME_EXECUTION_PROOF` only when an already
generated artifact should be consumed instead.

The artifact validates closed receipt posture for accepted, replayed, rejected,
idempotency-conflict, authorization-denied, and tenant-scoped idempotency calls.
It stores only bounded status fields and canonical receipt digests. It clears
`manage_live_contract_proof_missing` only when the proof is valid and
aggregate-current; it deliberately preserves rebalance execution authority,
action-register persistence, OMS/order execution, client publication,
production identity, production certification, and supported-feature blockers.

## Downstream Outcome Certification Aggregate Proof

`scripts/generate_downstream_outcome_certification.py` composes the current
Advise intake runtime proof, Manage action-intake runtime proof, Report
materialization runtime proof, and Idea durable submission/reconciliation
evidence into a source-safe RFC-0002 Slice 12/13 proof artifact:

```powershell
python scripts/generate_downstream_outcome_certification.py `
  --generated-at-utc 2026-07-22T00:00:00Z `
  --advise-intake-runtime-execution-proof output\downstream\advise-intake-runtime-execution-proof.json `
  --manage-intake-runtime-execution-proof output\downstream\manage-intake-runtime-execution-proof.json `
  --report-materialization-runtime-execution-proof output\report\materialization-runtime-execution-proof.json `
  --output output\downstream\downstream-outcome-certification-proof.json

make downstream-outcome-certification-proof-gate
```

The aggregate validates that the three owner artifacts are
`runtime_execution` evidence and that Idea covers accepted, rejected,
duplicate/replay, idempotency conflict, timeout-before-response,
response-before-local-commit, restart reconciliation, and operator
reconciliation replay windows through its durable submission and
reconciliation tests. It clears no new aggregate blocker and keeps #379 open in
`open_blocked`: owner-app local implementation evidence is mainline-backed, but
full downstream outcome certification still requires production/certification
evidence, trusted IdP caller context, retention/legal proof, Archive production
conformance, supported-feature promotion evidence, and client-publication
authority. The artifact must keep suitability,
rebalance/execution, report-rendering authority, archive authority,
client-publication, production certification, supported-feature, and
certification-closure claims false.

Current mainline evidence: PR #742 merged this aggregate proof to `main` at
`0a4e7a55495cb3b979672f52b08ba2630603cf94`; Main Releasability run
`30323405962` passed for that exact SHA, including coverage and
Docker/release-image validation; wiki publication completed at
`lotus-idea.wiki` commit `ce29814` with strict `DiffCount 0` parity. PR #743
then reconciled the RFC-0002 execution ledger on `main` at
`8ccee32d9a25fb6c47c723e105e2c48d1c4b3c70`, with Main Releasability run
`30324178801` passing for the current main SHA. Treat this as source-safe
supporting proof only: issue #379 remains open in `status/blocked` until
production/certification evidence proves downstream outcome, publication,
production-identity, supported-feature, legal/privacy, Archive production
conformance, and client-safe authority boundaries.

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

## Report Intake Runtime Execution

`scripts/report/generate_intake_runtime_execution.py` executes the sibling
`lotus-report` ASGI app through `TestClient` with an isolated
`IdeaEvidenceIntakeLedger` and writes
`output/report/intake-runtime-execution-proof.json`. The proof is
`runtime_execution` evidence and may clear only
`lotus_report_live_intake_route_proof_missing` when it is aggregate-current and
registered as blocker-clearing. It records accepted, replayed, idempotency
conflict, missing-idempotency-key, client-publication-denied, and render-claim
denied receipts without raw request or response bodies.

The proof intentionally retains materialization, rendered-output,
Archive-record, client-publication, supported-feature, and production-identity
blockers. Use `make report-intake-runtime-execution-proof-gate` before relying
on the artifact in downstream or aggregate readiness.

## Response Shape

The success response is intentionally aggregate and source-safe:

| Field | Meaning |
| --- | --- |
| `conversionIntentCount` | Count of `lotus-idea` conversion intents in the active repository provider |
| `conversionOutcomeCount` | Count of recorded downstream outcome records in `lotus-idea` |
| `reportEvidencePackRequestCount` | Count of Report/Render/Archive request records in `lotus-idea` |
| `downstreamSubmissionCount` | Count of local downstream submission records across terminal and non-terminal posture; this is a source-safe denominator, not downstream acceptance proof |
| `downstreamReconciliationRequiredCount` | Count of local downstream submissions in `in_flight` or `reconciliation_required` posture that need operator verification or reconciliation |
| `downstreamAdapterFoundationPresent` | Whether the repo contains source-safe downstream orchestration, adapter ports, and HTTP adapter foundations |
| `capabilities` | Capability-level downstream readiness posture and blockers |
| `downstreamContracts` | Planned downstream handoff contracts, owner repositories, target route posture, adapter status, evidence refs, and blockers |
| `blockerIssueRefs` | Snapshot-level map from every downstream blocker code to durable `sgajbi/<repo>#<issue>` execution references; capability and contract rows carry the same field at their own scope |
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
| Advise proposal realization | `LOTUS_IDEA_ADVISE_REALIZATION_BASE_URL` | `LOTUS_IDEA_ADVISE_REALIZATION_SUBMIT_PATH`, `LOTUS_IDEA_ADVISE_REALIZATION_HISTORY_PATH_TEMPLATE`, `LOTUS_IDEA_ADVISE_REALIZATION_RECOVERY_HISTORY_PATH` |
| Manage action realization | `LOTUS_IDEA_MANAGE_REALIZATION_BASE_URL` | `LOTUS_IDEA_MANAGE_REALIZATION_SUBMIT_PATH` |
| Report evidence-pack realization | `LOTUS_IDEA_REPORT_REALIZATION_BASE_URL` | `LOTUS_IDEA_REPORT_REALIZATION_SUBMIT_PATH`, `LOTUS_IDEA_REPORT_REALIZATION_RECOVERY_PATH` |

Local Compose configures all three realization pairs to the canonical Advise,
Manage, and Report owner routes. These variables are distinct from source-read
base URLs: configuring `LOTUS_ADVISE_BASE_URL` does not configure proposal
realization. `make ci-contract-gate` blocks missing Compose realization wiring
so a healthy source adapter cannot mask an unavailable downstream handoff.

`LOTUS_IDEA_DOWNSTREAM_REALIZATION_TIMEOUT_SECONDS` controls the HTTP adapter
timeout and defaults conservatively when absent.

### Advise Lost-Response Recovery

If Advise commits an intake but Idea loses the HTTP response, Idea preserves the
submission as `reconciliation_required`; it does not infer acceptance and does
not automatically repeat the mutating intake request. An authorized
reconciliation call reads the Advise-owned realization by the already-persisted
Idea `conversion_intent_id`, under the exact tenant, legal-entity, and portfolio
scope. Idea accepts the recovery only when candidate identity, conversion
intent, evidence fingerprint, and owner scope all match.
The owner lookup carries the opaque conversion identity as a query parameter, so previously
accepted printable identities remain addressable without rewriting durable records.

The recovery read reconstructs the original version-one intake receipt, while
later Advise events remain append-only owner history. Idea then commits its
local accepted/rejected submission posture and persists the full owner history.
Replay uses the recovered `intake_id` read route and never sends a second
intake. A missing, malformed, unavailable, or mismatched owner response leaves
the submission uncertain or returns a conflict; transport ambiguity never
becomes business success.

If the owner returned acceptance but Idea failed before finalizing its local
claim, the durable record remains `in_flight`. Advise and Report recovery both
reject owner reads while that claim lease is active, because the original POST
may still be running. After the lease expires, an authorized recovery may read
the exact owner identity and reconcile the existing claim. Trusted server
acceptance time controls this boundary; recovery never reissues the POST, never
increments the submission attempt, and exact replay performs no further owner
I/O.

### Local Advise, Manage, And Report Intake Fixtures

Until the platform has trusted service identity and an identity-provider claim
mapping, local Compose supplies a development-only Advise intake fixture from
server process configuration. It is never read from browser or caller request
headers. The fixture is restricted in code to the `local` and `test` runtime
profiles; `demo`, `staging`, and `production` fail closed before any Advise
call, even when the variables are present.

| Server-side environment variable | Local Compose value |
| --- | --- |
| `LOTUS_IDEA_ADVISE_REALIZATION_ACTOR_ID` | `lotus-idea-local-development` |
| `LOTUS_IDEA_ADVISE_REALIZATION_ROLE` | `SERVICE` |
| `LOTUS_IDEA_ADVISE_REALIZATION_TENANT_ID` | `tenant-sg` |
| `LOTUS_IDEA_ADVISE_REALIZATION_LEGAL_ENTITY_CODE` | `SGPB` |
| `LOTUS_IDEA_ADVISE_REALIZATION_SERVICE_IDENTITY` | `lotus-idea-local-development` |
| `LOTUS_IDEA_ADVISE_REALIZATION_CAPABILITIES` | `advisory.idea_proposal_intake.accept,advisory.idea_proposal_realization.read` |

The adapter sends these values only as `X-Actor-Id`, `X-Role`,
`X-Tenant-Id`, `X-Legal-Entity-Code`, `X-Service-Identity`,
`X-Capabilities`, and `X-Principal-Status: ACTIVE`, in addition to
correlation, trace, and idempotency headers. This fixture proves neither
production authentication nor advisory suitability. It only lets local/test
Idea submit the source-safe conversion-intent envelope to the Advise-owned
intake receipt route.

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
| `LOTUS_IDEA_MANAGE_REALIZATION_LEGAL_ENTITY_CODE` | `SGPB` |
| `LOTUS_IDEA_MANAGE_REALIZATION_SERVICE_IDENTITY` | `lotus-idea-local-development` |
| `LOTUS_IDEA_MANAGE_REALIZATION_CAPABILITIES` | `manage.write` |

The adapter sends these values only as `X-Actor-Id`, `X-Role`, `X-Tenant-Id`,
`X-Legal-Entity-Code`, `X-Service-Identity`, `X-Capabilities`, and
`X-Principal-Status: ACTIVE` to the current Manage route, in addition to
governed correlation, trace, and idempotency headers. This fixture does not
authenticate an end user, map a session or token claim, grant suitability or
rebalance authority, or certify downstream acceptance. The future trusted
identity path remains tracked in GitHub issue `#380`; this branch keeps the
fixture explicitly non-authoritative.

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
| `LOTUS_IDEA_REPORT_REALIZATION_OUTPUT_FORMATS` | `pdf` |

The local/test profile accepts exactly one server-configured `pdf` output. This intentionally
selects Report's governed Render and Archive path; blank, duplicate, mixed, JSON-only, or unknown
values fail before downstream I/O. The setting is not request or browser authority.

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
16. Advise idea-intake runtime-execution proof builder:
    `src/app/application/downstream_realization/advise_intake_runtime_execution.py`,
17. Advise idea-intake runtime-execution proof generator:
    `scripts/downstream_realization/generate_advise_intake_runtime_execution.py`,
18. Advise idea-intake runtime-execution proof gate:
    `scripts/downstream_realization/advise_intake_runtime_execution_gate.py`,
19. Manage action-intake runtime-execution proof builder:
    `src/app/application/downstream_realization/manage_intake_runtime_execution.py`,
20. Manage action-intake runtime-execution proof generator:
    `scripts/downstream_realization/generate_manage_intake_runtime_execution.py`,
21. Manage action-intake runtime-execution proof gate:
    `scripts/downstream_realization/manage_intake_runtime_execution_gate.py`,
22. focused downstream route source-contract tests:
    `tests/unit/downstream_realization/test_route_source_contract.py`,
23. Advise idea-intake runtime-execution tests:
    `tests/unit/downstream_realization/test_advise_intake_runtime_execution.py`,
24. Manage action-intake runtime-execution tests:
    `tests/unit/downstream_realization/test_manage_intake_runtime_execution.py`,
25. report intake source-contract generator:
   `scripts/report/generate_intake_route_source_contract.py`,
26. report intake source-contract gate:
    `scripts/report/intake_route_source_contract_gate.py`,
27. report intake runtime-execution generator:
   `scripts/report/generate_intake_runtime_execution.py`,
28. report intake runtime-execution gate:
    `scripts/report/intake_runtime_execution_gate.py`,
29. report materialization source-contract generator:
   `scripts/report/generate_materialization_source_contract.py`,
30. report materialization source-contract gate:
    `scripts/report/materialization_source_contract_gate.py`,
29. readiness API route: `src/app/api/downstream_realization_readiness.py`,
30. operation events:
   `downstream_realization_readiness_read` and
   `downstream_realization_submission`, plus
   `downstream_reconciliation_read` and `downstream_reconciliation_resolve`,
31. endpoint ledger:
   `docs/operations/endpoint-certification-ledger.json`,
32. unit tests:
   `tests/unit/test_downstream_realization_readiness.py`,
33. application orchestration tests:
   `tests/unit/test_downstream_realization_application.py`,
34. adapter tests:
   `tests/unit/test_downstream_realization_adapters.py`,
35. gate tests:
   `tests/unit/test_downstream_realization_contract_gate.py`,
32. route proof tests:
    `tests/unit/downstream_realization/test_route_source_contract.py`,
33. report intake source-contract tests:
    `tests/unit/report/test_intake_route_source_contract.py`,
34. report materialization source-contract tests:
    `tests/unit/report/test_materialization_source_contract.py`,
35. submission reconciliation and real PostgreSQL tests:
   `tests/integration/test_downstream_submission_reconciliation_api.py` and
   `tests/integration/test_postgres_downstream_submission_runtime.py`,
36. integration tests:
   `tests/integration/test_downstream_realization_readiness_api.py` and
   `tests/integration/test_downstream_realization_api.py`.

Run:

```powershell
python -m pytest tests/unit/test_downstream_realization_application.py tests/unit/test_downstream_realization_adapters.py tests/unit/test_downstream_intake_wire_contract.py tests/unit/test_downstream_realization_readiness.py tests/integration/test_downstream_realization_api.py tests/integration/test_downstream_realization_readiness_api.py -q
make downstream-realization-contract-gate
make downstream-route-source-contract-proof-gate
make advise-intake-runtime-execution-proof-gate
make manage-intake-runtime-execution-proof-gate
make downstream-outcome-certification-proof-gate
make report-intake-route-source-contract-proof-gate
make report-intake-runtime-execution-proof-gate
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
