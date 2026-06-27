# Implementation Proof Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and release reviewers |
| Required role | `operator` |
| Required capability | `idea.implementation-proof.readiness.read` |
| Required query | Timezone-aware `evaluatedAtUtc` |
| Supportability | `not_certified` while blockers remain |
| Product claim | Bounded live source-ingestion, runtime trust telemetry, default Advise proposal route, Manage action route, Report intake route, Report materialization, outbox broker, outbox consumer runtime, outbox platform mesh event publication, Gateway/Workbench operational, Gateway/Workbench discovery, mesh policy, platform mesh onboarding, AI lineage store, AI workflow-pack registration/runtime execution proof artifacts, and opportunity archetype scenario readiness can be consumed; no full live journey, live AI provider execution, suitability/rebalance authority, platform mesh certification, external broker publication, downstream delivery, full Gateway/Workbench product proof, live archetype replay proof, client-ready publication, or supported-feature promotion |

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
8. opportunity archetype scenario readiness,
9. downstream Advise, Manage, Report, Render, and Archive realization,
10. supported-feature promotion.

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
6. runtime trust telemetry preview, snapshot endpoint, generated snapshot, and
   candidate-snapshot proof posture,
7. outbox delivery readiness and run-once posture,
8. Workbench realization blockers,
9. opportunity archetype scenario blockers from the governed contract,
10. downstream realization blockers and internal submission route evidence,
11. supported-feature promotion blockers,
12. source-of-truth implementation paths.

## What It Does Not Prove

The diagnostic is deliberately not full live journey proof. It does not:

1. call `lotus-core`,
2. certify source-ingestion as a supported live source product beyond a
   configured bounded proof artifact,
3. live-call `lotus-ai`, execute live provider/RAG workflows, or certify provider rollout,
4. certify data products through platform mesh certification,
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

1. source-ingestion certification beyond the bounded live Core proof artifact,
2. certified long-running scheduled worker runtime proof beyond the current
   deploy-contract artifact,
3. platform mesh certification, active producer products, and Gateway/Workbench discovery,
4. certified downstream delivery evidence beyond the bounded consumer-runtime proof artifact,
5. certified external broker publication and production event-publication evidence beyond the bounded platform mesh event publication proof artifact,
6. `lotus-ai` live-provider rollout and runtime trust certification,
7. Workbench panel and browser proof,
8. downstream Advise and Manage realization authority,
9. Report/Render/Archive client-publication authority,
10. supported-feature promotion evidence.

Downstream realization blockers are backed by
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
`make downstream-realization-contract-gate` validates that the planned
contract rows stay source-authority preserving and do not become false
route-existence, downstream-execution, or supported-feature claims.
The downstream realization capability now also cites the internal submission
routes for Advise/Manage conversion intents and Report evidence-pack requests,
plus the report-owned planned intake contract at
`lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`.
Default source-safe Advise proposal route, Manage action route, Report intake
route, and Report materialization proof artifacts can clear only their
corresponding bounded blockers when merged sibling evidence is present. Those
refs do not clear suitability policy authority, rebalance/action authority,
client-publication authority, or supported-feature blockers.

Source-ingestion live proof is captured by
`scripts/generate_source_ingestion_live_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF` clears only
`live_core_source_proof_missing`; it does not clear scheduled worker,
data-mesh, Gateway/Workbench, downstream, or supported-feature blockers.
The artifact carries source-safe aggregate `blockReasonCounts` so blocked
attempts can distinguish Core unavailable, entitlement denied, missing
cash-weight evidence, and Core-reported blocked cash-weight supportability
without exposing source payloads or reconstructing source-owned calculations.
When aggregate implementation-proof readiness consumes a valid live proof path,
the `source-ingestion` capability also records a source-safe artifact reference
in `evidenceRefs`, so release reviewers can trace why that blocker cleared
without exposing Core payloads or portfolio identity.
Canonical Core runtimes should pass explicit `--core-query-base-url` and
`--core-query-control-plane-base-url` values because query-service reads and
query-control-plane snapshots can be served by different Core processes.
`--core-base-url` remains a compatibility fallback for older single-base
stacks.
The repo-native `make implementation-proof-readiness-check` target accepts the
same live-evidence inputs through Make variables, so release reviewers can use
the canonical target instead of a one-off command:

| Variable | Effect |
| --- | --- |
| `IMPLEMENTATION_PROOF_EVALUATED_AT_UTC` | Overrides the deterministic proof timestamp. |
| `IMPLEMENTATION_PROOF_OUTPUT` | Writes the aggregate readiness JSON to a chosen ignored output path. |
| `LOTUS_CORE_QUERY_BASE_URL` | Passes the live Core query-service URL into readiness generation. |
| `LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL` | Passes the live Core query-control-plane URL into readiness generation. |
| `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF` | Passes the validated live source-ingestion proof artifact into aggregate readiness. |
| `LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF` | Passes a validated source-safe Lotus Risk concentration live-proof artifact into opportunity-archetype readiness. A valid artifact clears only `opportunity_archetype_live_risk_source_proof_missing`; it does not certify data mesh, Workbench, client publication, or supported-feature promotion. |
| `LOTUS_ADVISE_ROOT` | Selects the sibling `lotus-advise` checkout used to generate the default source-safe Advise proposal route proof. Defaults to `../lotus-advise`. |
| `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT` | Selects the default generated Advise proposal route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/downstream/advise-proposal-route-proof.json`. |
| `LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF` | Overrides the default generated Advise proposal route proof artifact passed into aggregate readiness. |
| `LOTUS_MANAGE_ROOT` | Selects the sibling `lotus-manage` checkout used to generate the default source-safe Manage action route proof. Defaults to `../lotus-manage`. |
| `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT` | Selects the default generated Manage action route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/downstream/manage-action-route-proof.json`. |
| `LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF` | Overrides the default generated Manage action route proof artifact passed into aggregate readiness. |
| `LOTUS_REPORT_ROOT` | Selects the sibling `lotus-report` checkout used to generate the default source-safe report-intake route proof. Defaults to `../lotus-report`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT` | Selects the default generated report-intake route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/downstream/report-intake-route-proof.json`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` | Overrides the default generated report-intake route proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT` | Selects the default generated report materialization proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/downstream/report-materialization-proof.json`. |
| `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF` | Overrides the default generated report materialization proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT` | Selects the default generated mesh policy proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/data-mesh/mesh-policy-proof.json`. |
| `LOTUS_IDEA_MESH_POLICY_PROOF` | Overrides the default generated mesh policy proof artifact passed into aggregate readiness. |
| `LOTUS_PLATFORM_ROOT` | Selects the sibling `lotus-platform` checkout used to generate the default source-safe platform mesh onboarding proof. Defaults to `../lotus-platform`. |
| `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT` | Selects the default generated platform mesh onboarding proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/data-mesh/platform-mesh-onboarding-proof.json`. |
| `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF` | Overrides the default generated platform mesh onboarding proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF_OUTPUT` | Selects the default generated outbox consumer runtime proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/outbox/outbox-consumer-runtime-proof.json`. |
| `LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF` | Overrides the default generated outbox consumer runtime proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT` | Selects the default generated outbox platform mesh event publication proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/outbox/outbox-platform-mesh-event-publication-proof.json`. |
| `LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF` | Overrides the default generated outbox platform mesh event publication proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT` | Selects the default generated Gateway/Workbench operational proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/workbench/gateway-workbench-operational-proof.json`. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF` | Overrides the default generated Gateway/Workbench operational proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF_OUTPUT` | Selects the default generated Gateway/Workbench discovery proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/workbench/gateway-workbench-discovery-proof.json`. |
| `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF` | Overrides the default generated Gateway/Workbench discovery proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT` | Selects the default generated AI lineage store proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-lineage-store-proof.json`. |
| `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF` | Overrides the default generated AI lineage store proof artifact passed into aggregate readiness. |
| `LOTUS_AI_ROOT` | Selects the sibling `lotus-ai` checkout used to generate default workflow-pack registration and runtime execution proof artifacts. Defaults to `../lotus-ai`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT` | Selects the default generated AI workflow-pack registration proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-workflow-pack-registration-proof.json`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF` | Overrides the default generated AI workflow-pack registration proof artifact passed into aggregate readiness. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT` | Selects the default generated AI workflow-pack runtime execution proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/ai/ai-workflow-pack-runtime-execution-proof.json`. |
| `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF` | Overrides the default generated AI workflow-pack runtime execution proof artifact passed into aggregate readiness. |

When rerunning live proof against an existing durable PostgreSQL repository,
preserve idempotency history. If the same generated default idempotency key was
accepted before an upstream Core source fingerprint changed, a later run can
correctly return `conflict`. Capture a fresh release-proof run with an ignored
manifest under `output/source-ingestion/` and a source-safe explicit
`idempotencyKey`; do not reset durable state to force an accepted outcome. The
checked-in example manifest remains the canonical source-safe default, while
ignored proof-run manifests are local evidence inputs only.

Scheduled source-ingestion worker deploy proof is captured by
`scripts/generate_scheduled_source_ingestion_worker_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF` clears
only `scheduled_worker_deploy_proof_missing`; it does not clear live Core,
data-mesh, Gateway/Workbench, downstream, or supported-feature blockers.
`make implementation-proof-readiness-check` now generates that deploy-proof
artifact under ignored `output/source-ingestion/` and passes it explicitly into
the aggregate readiness generator, so the repo-native proof snapshot does not
report a stale scheduled-worker deploy-proof blocker. Aggregate
implementation-proof readiness records the validated artifact reference in the
`source-ingestion` capability `evidenceRefs`, making the blocker-clearance
evidence auditable without leaking source payloads. This remains deploy
topology proof only; it is not live long-running scheduler certification.

Lotus Risk concentration live proof is captured by
`scripts/generate_risk_concentration_live_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_RISK_CONCENTRATION_LIVE_PROOF` clears only
`opportunity_archetype_live_risk_source_proof_missing` for the
`opportunity-archetype-scenarios` capability. The artifact proves a live
`lotus-risk:ConcentrationRiskReport:v1` source call, current source evidence,
and deterministic concentration candidate generation without storing portfolio
identity, request or response payloads, correlation IDs, trace IDs, candidate
IDs, or source routes. It deliberately retains data-mesh, Workbench,
client-publication, and supported-feature blockers.

Durable repository proof is captured by
`scripts/generate_durable_repository_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_DURABLE_REPOSITORY_PROOF` or passed with
`--durable-repository-proof` clears only the aggregate
`durable_repository_not_configured` blocker inside generated
implementation-proof readiness evidence and the operator API readiness
snapshot. It does not configure the running service, connect to PostgreSQL,
certify production storage, prove deploy migrations, certify live Core
ingestion, certify runtime trust telemetry, prove Gateway or Workbench
behavior, or promote a supported feature. Runtime readiness endpoints continue
to report missing durable repository posture when `LOTUS_IDEA_DATABASE_URL` is
absent.

Runtime trust telemetry proof is captured by
`scripts/generate_runtime_trust_telemetry_proof.py`. A valid artifact
referenced through `LOTUS_IDEA_RUNTIME_TRUST_TELEMETRY_PROOF` or passed with
`--runtime-trust-telemetry-proof` clears only repo-owned runtime telemetry
blockers inside generated implementation-proof readiness evidence and the
operator API readiness snapshot:

1. `runtime_candidate_snapshot_missing`,
2. `certified_runtime_trust_telemetry_missing`,
3. `data_mesh_runtime_telemetry_not_certified`.

It exercises a deterministic, source-safe candidate snapshot through the
runtime trust telemetry builder and records the proof artifact as aggregate
evidence. It does not certify the platform source manifest, platform mesh,
active producer products, SLO/access/evidence policy, Gateway or Workbench
discovery, client-ready publication, or supported-feature promotion.

Workbench read-path proof is captured by
`scripts/generate_workbench_read_path_proof.py`. A valid artifact referenced
through `LOTUS_IDEA_WORKBENCH_READ_PATH_PROOF` or passed with
`--workbench-read-path-proof` clears only the aggregate
`workbench_gateway_bff_consumption_proof_missing` blocker inside generated
implementation-proof readiness evidence and the operator API readiness
snapshot. It records the bounded Gateway-backed Workbench queue/detail read
path from `lotus-workbench` PR #391. It does not certify a full Workbench
panel, browser accessibility proof, canonical demo runtime proof, data-product
certification, client-ready publication, or supported-feature promotion.

Gateway/Workbench operational proof is captured by
`scripts/generate_gateway_workbench_operational_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT` from the
validated Workbench read-path proof and passes it into aggregate readiness when
`LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF` is not set. A valid artifact
clears only `gateway_workbench_proof_missing` from the source-ingestion and
outbox-delivery proof families. It does not clear full Workbench product proof,
Workbench panel proof, browser accessibility proof, canonical demo runtime
proof, Gateway/Workbench data-product discovery proof, client-ready
publication, or supported-feature promotion.

Gateway/Workbench discovery proof is captured by
`scripts/generate_gateway_workbench_discovery_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF_OUTPUT` from
platform catalog/onboarding evidence, the Workbench read-path proof, and the
Gateway/Workbench operational proof. A valid artifact clears only
`gateway_workbench_discovery_proof_missing` from the data-mesh and runtime
trust telemetry proof families. It does not certify data-mesh products,
activate producer products, publish product routes, certify full Workbench
product behavior, or promote supported features.

Outbox broker proof is captured by
`scripts/generate_outbox_broker_proof.py`. A valid artifact referenced through
`LOTUS_IDEA_OUTBOX_BROKER_PROOF` or passed with `--outbox-broker-proof` clears
only the aggregate `outbox_broker_not_configured` and
`external_broker_runtime_proof_missing` blockers inside generated
implementation-proof readiness evidence and the operator API readiness
snapshot. It cites the implemented outbox delivery orchestration, publisher
port, HTTP publisher adapter foundation, readiness endpoint, run-once endpoint,
configured-publisher API proof, and `make outbox-broker-proof-contract-gate`.
It does not certify external broker publication support, downstream consumer
runtime proof, platform mesh event publication, Gateway/Workbench behavior,
client-ready publication, or supported-feature promotion.

Downstream outbox consumer contract posture is enforced by
`contracts/outbox-events/lotus-idea-outbox-consumers.v1.json` and
`make outbox-consumer-contract-gate`. The contract declares Gateway, Advise,
Manage, and Report consumers with source-authority boundaries and keeps each
consumer `contract_declared_not_runtime_certified`; it changes the outbox
blocker from `downstream_consumer_contracts_missing` to
`downstream_consumer_runtime_proof_missing` without promoting support.

Outbox consumer runtime proof is captured by
`scripts/generate_outbox_consumer_runtime_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF_OUTPUT` and passes it
into aggregate readiness when `LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF` is not
set. A valid artifact clears only `downstream_consumer_runtime_proof_missing`
inside aggregate implementation-proof readiness. It proves the declared
Gateway, Advise, Manage, and Report consumer contract coverage, consumed event
type coverage, and source-authority boundaries remain runtime-checkable and
source-safe. It does not certify external broker publication, platform mesh
event publication, Gateway/Workbench behavior, downstream delivery,
client-ready publication, or supported-feature promotion.

Outbox platform mesh event publication proof is captured by
`scripts/generate_outbox_platform_mesh_event_publication_proof.py`. The
repo-native `make implementation-proof-readiness-check` target now generates
the default artifact from repo-owned outbox event/consumer contracts and
sibling `lotus-platform` source-manifest/catalog evidence under
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT`, then passes
it into aggregate readiness when
`LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF` is not set. A valid
artifact clears only `platform_mesh_event_publication_proof_missing` inside
aggregate implementation-proof readiness. It proves the source-safe event
contract, declared consumer contract coverage, platform source-manifest
inclusion, and generated catalog mapping for proposed `lotus-idea` products.
It does not certify external broker publication, downstream delivery,
Gateway/Workbench behavior, client-ready publication, or supported-feature
promotion. Missing sibling evidence writes an invalid non-proof artifact and
keeps the blocker so CI remains stable without treating absence as proof;
drift in present sibling evidence still exits non-zero.

Advise proposal route proof and Manage action route proof are captured by
`scripts/generate_advise_proposal_route_proof.py` and
`scripts/generate_manage_action_route_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates default
artifacts from `LOTUS_ADVISE_ROOT` and `LOTUS_MANAGE_ROOT` under
`LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT` and
`LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT`, then passes them into aggregate
readiness when the corresponding override variables are not set. Valid
artifacts clear only `advise_live_contract_proof_missing` or
`manage_live_contract_proof_missing` inside downstream realization and
aggregate implementation-proof readiness. Missing sibling evidence writes
invalid non-proof artifacts and keeps the blockers so CI remains stable without
treating absence as proof. Drift in present sibling evidence exits non-zero.
These proofs cite the sibling route contract, sibling route/service evidence,
the `lotus-idea` downstream contract, and readiness endpoints. They do not
grant suitability, policy approval, mandate/rebalance authority, execution,
order creation, client communication, or supported-feature promotion.

Report intake route proof is captured by
`scripts/generate_report_intake_route_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_REPORT_ROOT` under
`LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT` and passes it into aggregate
readiness when `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` is not set. A valid
artifact clears only `lotus_report_live_intake_route_proof_missing` inside
downstream realization and aggregate implementation-proof readiness. Missing
sibling evidence writes an invalid non-proof artifact and keeps the blocker so
CI remains stable without treating absence as proof. It cites the merged
`lotus-report` route contract for `POST /reports/idea-evidence-packs`, the
report-owned intake route modules and tests, the `lotus-idea` downstream
contract, and the readiness endpoints. It does not create a report job, render
output, archive record, client publication, suitability decision, mandate
action, execution instruction, or supported feature.

Report materialization proof is captured by
`scripts/generate_report_materialization_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_REPORT_ROOT` under
`LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT` and passes it into aggregate
readiness when `LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF` is not set. A valid
artifact clears only `report_evidence_pack_live_materialization_proof_missing`,
`rendered_output_creation_missing`, and `archive_record_creation_missing`
inside downstream realization and aggregate implementation-proof readiness.
Missing sibling evidence writes an invalid non-proof artifact and keeps those
blockers so CI remains stable without treating absence as proof. It cites the
merged `lotus-report` materialization contract for
`POST /reports/idea-evidence-packs/materializations`, report-owned
materialization/render/archive modules and tests, the `lotus-idea` downstream
contract, and the readiness endpoints. It does not grant client-publication
authority, suitability authority, mandate action, execution instruction, or a
supported feature.

Platform mesh onboarding proof is captured by
`scripts/generate_platform_mesh_onboarding_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_PLATFORM_ROOT` under
`LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT` and passes it into aggregate
readiness when `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF` is not set. A valid
artifact clears only
`platform_source_manifest_inclusion_missing` and
`platform_catalog_inclusion_missing` from data-mesh aggregate readiness. It
cites sibling `lotus-platform` source-manifest, generated catalog, dependency
graph, maturity matrix, and mesh handoff evidence. It does not certify the
platform mesh, activate producer products, certify SLO/access/evidence policy,
prove Gateway/Workbench discovery, or promote a supported feature.
Missing sibling evidence writes an invalid non-proof artifact and keeps the
blockers so CI remains stable without treating absence as proof; drift in
present sibling evidence still exits non-zero.

Mesh policy proof is captured by `scripts/generate_mesh_policy_proof.py`. The
repo-native `make implementation-proof-readiness-check` target now generates
the default artifact under `LOTUS_IDEA_MESH_POLICY_PROOF_OUTPUT` and passes it
into aggregate readiness when `LOTUS_IDEA_MESH_POLICY_PROOF` is not set. A valid
artifact clears only the repo-owned policy blockers:

1. `mesh_slo_policy_certification_missing`,
2. `mesh_access_policy_certification_missing`,
3. `mesh_evidence_policy_certification_missing`.

It cites the mesh readiness, SLO, access, and evidence-pack policy contracts
plus the repo-native gates. It does not certify the platform mesh, activate
producer products, prove platform source-manifest/catalog inclusion,
Gateway/Workbench discovery, client-ready publication, or supported-feature
promotion. `make mesh-policy-proof-contract-gate` validates the artifact shape,
source-safe evidence refs, and three-blocker clearance boundary before the proof
is consumed by aggregate readiness.

AI lineage store proof is captured by
`scripts/generate_ai_lineage_store_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact under `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_LINEAGE_STORE_PROOF` is not set. A
valid artifact clears only `certified_ai_lineage_store_missing` from the
AI explanation capability. It cites the AI explanation lineage migration,
rollback, governance code, persistence port, PostgreSQL adapter, PostgreSQL
runtime proof tests, and the required GitHub PostgreSQL runtime proof lane.
It does not execute `lotus-ai`, call an AI provider, expose prompts or provider
responses, prove Workbench behavior, authorize client-ready publication, or
promote a supported feature.
`make ai-lineage-store-proof-contract-gate` validates the artifact shape and
blocks source-sensitive content before the proof is consumed by aggregate
readiness.

AI workflow-pack registration proof is captured by
`scripts/generate_ai_workflow_pack_registration_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_AI_ROOT` under
`LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_WORKFLOW_PACK_REGISTRATION_PROOF` is
not set. A valid artifact clears only
`workflow_pack_runtime_contract_not_certified` from the AI explanation
capability. It cites the sibling `lotus-ai` workflow-pack phase-one spec,
registry seed, execution binding, queue policy catalog, supportability surface,
and registry/API/runtime tests for `idea_explanation.pack@v1`.
It does not execute `lotus-ai`, call an AI provider, certify runtime trust
telemetry, prove Workbench behavior, authorize client-ready publication, or
promote a supported feature.
Missing sibling evidence writes an invalid non-proof artifact and keeps the
blocker so CI remains stable without treating absence as proof; drift in
present sibling evidence still exits non-zero.
`make ai-workflow-pack-registration-proof-contract-gate` validates the artifact
shape, source-safe evidence refs, and one-blocker clearance boundary before the
proof is consumed by aggregate readiness.

AI workflow-pack runtime execution proof is captured by
`scripts/generate_ai_workflow_pack_runtime_execution_proof.py`. The repo-native
`make implementation-proof-readiness-check` target now generates the default
artifact from `LOTUS_AI_ROOT` under
`LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF_OUTPUT` and passes it into
aggregate readiness when `LOTUS_IDEA_AI_WORKFLOW_PACK_RUNTIME_EXECUTION_PROOF`
is not set. A valid artifact clears only
`lotus_ai_runtime_execution_missing` from the AI explanation capability. It
cites the sibling `lotus-ai` deterministic idea explanation stub, source-safe
guardrails, workflow-pack execution path, stub provider routing, restricted
`lotus-idea` caller policy, migration seed, and tests. It does not execute a
live AI provider, certify provider rollout, certify runtime trust telemetry,
prove Workbench behavior,
authorize client-ready publication, or promote a supported feature. Missing
sibling evidence writes an invalid non-proof artifact and keeps the blocker so
CI remains stable without treating absence as proof; drift in present sibling
evidence still exits non-zero. `make ai-workflow-pack-runtime-execution-proof-contract-gate`
validates the artifact shape, source-safe evidence refs, and one-blocker
clearance boundary before the proof is consumed by aggregate readiness.

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
| `capabilities[].readinessStatus` | Capability readiness derived from remaining blockers after proof artifact consumption; blocker-free capabilities report `ready` |
| `capabilities[].supportabilityStatus` | Capability supportability derived from remaining blockers after proof artifact consumption; blocker-free capabilities report `supported` |
| `capabilities[].evidenceRefs` | Source-safe implementation, endpoint, and validated proof artifact references |
| `capabilities[].blockers` | Source-safe blocker codes for that capability family |

The `opportunity-archetype-scenarios` capability reads
`contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`
and prefixes its scenario blockers with `opportunity_archetype_` so they do not
collide with source-ingestion, Workbench, data-mesh, or supported-feature
blockers from other proof families. It is a taxonomy and scenario-readiness
view only; it does not clear live replay, client-demo, data-mesh, or
supported-feature blockers.

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
3. runtime artifact loader: `src/app/runtime/proof_artifacts.py`,
4. artifact generator: `scripts/generate_implementation_proof_readiness.py`,
5. repo-native check that generates and consumes the scheduled-worker
   deploy-proof, durable repository proof, runtime telemetry proof, Workbench
   read-path proof, Advise proposal route proof, Manage action route proof,
   Report intake route proof, Report materialization proof, outbox broker
   proof, outbox consumer runtime proof, and outbox platform mesh event
   publication proof artifacts, and records validated proof refs in capability
   evidence:
   `make implementation-proof-readiness-check`,
6. opportunity archetype scenario contract:
   `contracts/opportunity-archetypes/lotus-idea-opportunity-archetypes.v1.json`,
7. opportunity archetype contract gate:
   `make opportunity-archetype-contract-gate`,
8. AI model-risk operations contract:
   `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`,
9. AI model-risk operations contract gate:
   `make ai-model-risk-ops-contract-gate`,
10. AI model-risk operations proof gate:
   `make ai-model-risk-operations-proof-contract-gate`,
11. downstream contract check: `make downstream-realization-contract-gate`,
12. report-owned planned intake contract:
   `lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`,
13. runtime trust telemetry snapshot check:
   `make runtime-trust-telemetry-snapshot-check`,
14. runtime trust telemetry snapshot endpoint:
   `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot`,
15. generated runtime telemetry evidence:
   `output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`,
16. source-ingestion run-once endpoint:
   `POST /api/v1/source-ingestion/run-once`,
17. source-ingestion run-once runbook:
    `docs/operations/source-ingestion-run-once.md`,
18. source-ingestion live-proof generator:
    `scripts/generate_source_ingestion_live_proof.py`,
19. source-ingestion block-reason diagnostics tests:
    `tests/unit/test_source_ingestion_worker.py`,
20. scheduled source-ingestion worker proof generator:
    `scripts/generate_scheduled_source_ingestion_worker_proof.py`,
21. scheduled source-ingestion worker contract gate:
    `make source-ingestion-scheduled-worker-check`,
22. source-ingestion live-proof contract gate:
    `make source-ingestion-live-proof-contract-gate`,
23. Risk concentration live-proof generator:
    `scripts/generate_risk_concentration_live_proof.py`,
24. Risk concentration live-proof contract gate:
    `make risk-concentration-live-proof-contract-gate`,
25. durable repository proof generator:
    `scripts/generate_durable_repository_proof.py`,
26. durable repository proof contract gate:
    `make durable-repository-proof-contract-gate`,
27. runtime trust telemetry proof generator:
    `scripts/generate_runtime_trust_telemetry_proof.py`,
28. runtime trust telemetry proof contract gate:
    `make runtime-trust-telemetry-proof-contract-gate`,
29. Workbench read-path proof generator:
    `scripts/generate_workbench_read_path_proof.py`,
30. Workbench read-path proof contract gate:
    `make workbench-read-path-proof-contract-gate`,
28. Gateway/Workbench operational proof generator:
    `scripts/generate_gateway_workbench_operational_proof.py`,
29. Gateway/Workbench operational proof contract gate:
    `make gateway-workbench-operational-proof-contract-gate`,
30. Gateway/Workbench discovery proof generator:
    `scripts/generate_gateway_workbench_discovery_proof.py`,
31. Gateway/Workbench discovery proof contract gate:
    `make gateway-workbench-discovery-proof-contract-gate`,
32. outbox broker proof generator:
    `scripts/generate_outbox_broker_proof.py`,
31. outbox consumer contract gate:
    `make outbox-consumer-contract-gate`,
32. outbox consumer runtime proof generator:
    `scripts/generate_outbox_consumer_runtime_proof.py`,
33. outbox consumer runtime proof contract gate:
    `make outbox-consumer-runtime-proof-contract-gate`,
34. outbox consumer runtime proof tests:
    `tests/unit/test_outbox_consumer_runtime_proof.py`,
35. outbox broker proof contract gate:
    `make outbox-broker-proof-contract-gate`,
36. outbox platform mesh event publication proof generator:
    `scripts/generate_outbox_platform_mesh_event_publication_proof.py`,
37. outbox platform mesh event publication proof contract gate:
    `make outbox-platform-mesh-event-publication-proof-contract-gate`,
38. outbox platform mesh event publication proof tests:
    `tests/unit/test_outbox_platform_mesh_event_publication_proof.py`,
39. Advise proposal route proof generator:
    `scripts/generate_advise_proposal_route_proof.py`,
40. Manage action route proof generator:
    `scripts/generate_manage_action_route_proof.py`,
41. downstream route proof contract gate:
    `make downstream-route-contract-proof-gate`,
42. downstream route proof tests:
    `tests/unit/test_downstream_route_contract_proof.py`,
43. report intake route proof generator:
    `scripts/generate_report_intake_route_proof.py`,
44. report intake route proof contract gate:
    `make report-intake-route-proof-contract-gate`,
45. report intake route proof tests:
    `tests/unit/test_report_intake_route_proof.py`,
46. report materialization proof generator:
    `scripts/generate_report_materialization_proof.py`,
47. report materialization proof contract gate:
    `make report-materialization-proof-contract-gate`,
48. report materialization proof tests:
    `tests/unit/test_report_materialization_proof.py`,
49. outbox broker proof tests:
    `tests/unit/test_outbox_broker_proof.py`,
50. platform mesh onboarding proof generator:
    `scripts/generate_platform_mesh_onboarding_proof.py`,
51. platform mesh onboarding proof contract gate:
    `make platform-mesh-onboarding-proof-contract-gate`,
52. platform mesh onboarding proof tests:
    `tests/unit/test_platform_mesh_onboarding_proof.py`,
53. Workbench read-path proof tests:
    `tests/unit/test_workbench_read_path_proof.py`,
54. runtime trust telemetry proof tests:
    `tests/unit/test_runtime_trust_telemetry_proof.py`,
55. outbox delivery run-once endpoint:
    `POST /api/v1/outbox-delivery/run-once`,
56. operation event: `implementation_proof_readiness_read`,
53. endpoint ledger:
    `docs/operations/endpoint-certification-ledger.json`,
54. runtime artifact loader tests:
    `tests/unit/test_proof_artifacts.py`,
55. unit tests:
    `tests/unit/test_implementation_proof_readiness.py`,
56. durable repository proof tests:
    `tests/unit/test_durable_repository_proof.py`,
57. generator tests:
    `tests/unit/test_generate_implementation_proof_readiness.py`,
58. AI workflow-pack registration proof generator:
    `scripts/generate_ai_workflow_pack_registration_proof.py`,
59. AI workflow-pack registration proof contract gate:
    `make ai-workflow-pack-registration-proof-contract-gate`,
60. AI workflow-pack registration proof tests:
    `tests/unit/test_ai_workflow_pack_registration_proof.py`,
61. AI workflow-pack runtime execution proof generator:
    `scripts/generate_ai_workflow_pack_runtime_execution_proof.py`,
62. AI workflow-pack runtime execution proof contract gate:
    `make ai-workflow-pack-runtime-execution-proof-contract-gate`,
63. AI workflow-pack runtime execution proof tests:
    `tests/unit/test_ai_workflow_pack_runtime_execution_proof.py`,
64. integration tests:
    `tests/integration/test_implementation_proof_readiness_api.py`.

The `ai-explanation` capability evidence includes the AI model-risk operations
contract, certified dashboard, certified Prometheus alert rules, runbook, and
proof gate. Those refs clear only the model-risk dashboard/alert operations
blockers. They do not clear `lotus-ai` runtime execution, runtime trust
telemetry, Workbench product proof, client-ready publication, or
supported-feature promotion.

Run:

```powershell
python -m pytest tests/unit/test_implementation_proof_readiness.py tests/integration/test_implementation_proof_readiness_api.py -q
make implementation-proof-readiness-check

$env:LOTUS_CORE_QUERY_BASE_URL = "http://localhost:8201"
$env:LOTUS_CORE_QUERY_CONTROL_PLANE_BASE_URL = "http://localhost:8202"
$env:LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF = "output/source-ingestion/live-proof.json"
$env:LOTUS_ADVISE_ROOT = "..\lotus-advise"
$env:LOTUS_IDEA_ADVISE_PROPOSAL_ROUTE_PROOF_OUTPUT = "output/downstream/advise-proposal-route-proof.json"
$env:LOTUS_MANAGE_ROOT = "..\lotus-manage"
$env:LOTUS_IDEA_MANAGE_ACTION_ROUTE_PROOF_OUTPUT = "output/downstream/manage-action-route-proof.json"
$env:LOTUS_REPORT_ROOT = "..\lotus-report"
$env:LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT = "output/downstream/report-intake-route-proof.json"
$env:LOTUS_IDEA_REPORT_MATERIALIZATION_PROOF_OUTPUT = "output/downstream/report-materialization-proof.json"
$env:LOTUS_IDEA_OUTBOX_CONSUMER_RUNTIME_PROOF_OUTPUT = "output/outbox/outbox-consumer-runtime-proof.json"
$env:LOTUS_IDEA_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_OUTPUT = "output/outbox/outbox-platform-mesh-event-publication-proof.json"
$env:LOTUS_IDEA_GATEWAY_WORKBENCH_OPERATIONAL_PROOF_OUTPUT = "output/workbench/gateway-workbench-operational-proof.json"
$env:LOTUS_IDEA_GATEWAY_WORKBENCH_DISCOVERY_PROOF_OUTPUT = "output/workbench/gateway-workbench-discovery-proof.json"
$env:IMPLEMENTATION_PROOF_OUTPUT = "output/implementation-proof/implementation-proof-readiness.json"
make implementation-proof-readiness-check

make durable-repository-proof-contract-gate
make runtime-trust-telemetry-proof-contract-gate
make ai-workflow-pack-registration-proof-contract-gate
make outbox-broker-proof-contract-gate
make outbox-consumer-runtime-proof-contract-gate
make outbox-platform-mesh-event-publication-proof-contract-gate
make downstream-route-contract-proof-gate
make report-intake-route-proof-contract-gate
make report-materialization-proof-contract-gate
make workbench-read-path-proof-contract-gate
make gateway-workbench-operational-proof-contract-gate
make gateway-workbench-discovery-proof-contract-gate
make source-ingestion-scheduled-worker-check
make source-ingestion-live-proof-contract-gate
make risk-concentration-live-proof-contract-gate
make downstream-realization-contract-gate
make runtime-trust-telemetry-snapshot-check
make endpoint-certification-gate
make openapi-gate
```

Use this endpoint to decide whether RFC-0002 is ready for live validation.
Use the live canonical stack only after the readiness blockers have been
cleared by implementation-backed slices.
