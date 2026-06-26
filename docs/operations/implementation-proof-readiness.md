# Implementation Proof Readiness

| Field | Current Truth |
| --- | --- |
| Status | Certified internal operator diagnostic |
| Audience | Operators, implementation reviewers, demo leads, and release reviewers |
| Required role | `operator` |
| Required capability | `idea.implementation-proof.readiness.read` |
| Required query | Timezone-aware `evaluatedAtUtc` |
| Supportability | `not_certified` while blockers remain |
| Product claim | Bounded live source-ingestion, default report-intake route, outbox broker, platform mesh onboarding, AI lineage store, and AI workflow-pack registration/runtime execution proof artifacts can be consumed; no full live journey, live AI provider execution, mesh certification, report materialization, external event publication, client-ready publication, or supported-feature promotion |

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
6. runtime trust telemetry preview, snapshot endpoint, generated snapshot, and
   candidate-snapshot proof posture,
7. outbox delivery readiness and run-once posture,
8. Workbench realization blockers,
9. downstream realization blockers and internal submission route evidence,
10. supported-feature promotion blockers,
11. source-of-truth implementation paths.

## What It Does Not Prove

The diagnostic is deliberately not full live journey proof. It does not:

1. call `lotus-core`,
2. certify source-ingestion as a supported live source product beyond a
   configured bounded proof artifact,
3. live-call `lotus-ai`, execute live provider/RAG workflows, or certify provider rollout,
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

1. source-ingestion certification beyond the bounded live Core proof artifact,
2. certified long-running scheduled worker runtime proof beyond the current
   deploy-contract artifact,
3. certified runtime trust telemetry and platform mesh certification,
4. certified downstream consumer contracts and production event-publication evidence,
5. platform mesh event certification for outbox publication,
6. `lotus-ai` live-provider rollout and runtime trust certification,
7. Workbench panel and browser proof,
8. downstream Advise, Manage, Report, Render, and Archive realization,
9. supported-feature promotion evidence.

Downstream realization blockers are backed by
`contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`.
`make downstream-realization-contract-gate` validates that the planned
contract rows stay source-authority preserving and do not become false
route-existence, downstream-execution, or supported-feature claims.
The downstream realization capability now also cites the internal submission
routes for Advise/Manage conversion intents and Report evidence-pack requests,
plus the report-owned planned intake contract at
`lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`.
Those refs prove contract posture only; they do not clear live downstream route,
materialization, render, archive, or client-publication blockers.

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
| `LOTUS_REPORT_ROOT` | Selects the sibling `lotus-report` checkout used to generate the default source-safe report-intake route proof. Defaults to `../lotus-report`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT` | Selects the default generated report-intake route proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/downstream/report-intake-route-proof.json`. |
| `LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF` | Overrides the default generated report-intake route proof artifact passed into aggregate readiness. |
| `LOTUS_PLATFORM_ROOT` | Selects the sibling `lotus-platform` checkout used to generate the default source-safe platform mesh onboarding proof. Defaults to `../lotus-platform`. |
| `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF_OUTPUT` | Selects the default generated platform mesh onboarding proof artifact consumed by aggregate readiness when no override is set. Defaults to `output/data-mesh/platform-mesh-onboarding-proof.json`. |
| `LOTUS_IDEA_PLATFORM_MESH_ONBOARDING_PROOF` | Overrides the default generated platform mesh onboarding proof artifact passed into aggregate readiness. |
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
`--runtime-trust-telemetry-proof` clears only the aggregate
`runtime_candidate_snapshot_missing` blocker inside generated
implementation-proof readiness evidence and the operator API readiness
snapshot. It exercises a deterministic, source-safe candidate snapshot through
the runtime trust telemetry builder. It does not certify the platform source
manifest, platform mesh, Gateway or Workbench discovery, client-ready
publication, or supported-feature promotion.

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
contracts, platform mesh event publication, Gateway/Workbench behavior,
client-ready publication, or supported-feature promotion.

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
| `capabilities[].evidenceRefs` | Source-safe implementation, endpoint, and validated proof artifact references |
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
3. runtime artifact loader: `src/app/runtime/proof_artifacts.py`,
4. artifact generator: `scripts/generate_implementation_proof_readiness.py`,
5. repo-native check that generates and consumes the scheduled-worker
   deploy-proof, durable repository proof, runtime telemetry proof, Workbench
   read-path proof, and outbox broker proof artifacts, and records validated
   proof refs in capability evidence:
   `make implementation-proof-readiness-check`,
6. AI model-risk operations contract:
   `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json`,
7. AI model-risk operations contract gate:
   `make ai-model-risk-ops-contract-gate`,
8. AI model-risk operations proof gate:
   `make ai-model-risk-operations-proof-contract-gate`,
9. downstream contract check: `make downstream-realization-contract-gate`,
10. report-owned planned intake contract:
   `lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`,
11. runtime trust telemetry snapshot check:
   `make runtime-trust-telemetry-snapshot-check`,
11. runtime trust telemetry snapshot endpoint:
   `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot`,
12. generated runtime telemetry evidence:
   `output/trust-telemetry/runtime/idea-candidate.telemetry.v1.json`,
13. source-ingestion run-once endpoint:
   `POST /api/v1/source-ingestion/run-once`,
14. source-ingestion run-once runbook:
    `docs/operations/source-ingestion-run-once.md`,
15. source-ingestion live-proof generator:
    `scripts/generate_source_ingestion_live_proof.py`,
16. source-ingestion block-reason diagnostics tests:
    `tests/unit/test_source_ingestion_worker.py`,
17. scheduled source-ingestion worker proof generator:
    `scripts/generate_scheduled_source_ingestion_worker_proof.py`,
18. scheduled source-ingestion worker contract gate:
    `make source-ingestion-scheduled-worker-check`,
19. source-ingestion live-proof contract gate:
    `make source-ingestion-live-proof-contract-gate`,
20. durable repository proof generator:
    `scripts/generate_durable_repository_proof.py`,
21. durable repository proof contract gate:
    `make durable-repository-proof-contract-gate`,
22. runtime trust telemetry proof generator:
    `scripts/generate_runtime_trust_telemetry_proof.py`,
23. runtime trust telemetry proof contract gate:
    `make runtime-trust-telemetry-proof-contract-gate`,
24. Workbench read-path proof generator:
    `scripts/generate_workbench_read_path_proof.py`,
25. Workbench read-path proof contract gate:
    `make workbench-read-path-proof-contract-gate`,
26. outbox broker proof generator:
    `scripts/generate_outbox_broker_proof.py`,
27. outbox broker proof contract gate:
    `make outbox-broker-proof-contract-gate`,
28. report intake route proof generator:
    `scripts/generate_report_intake_route_proof.py`,
29. report intake route proof contract gate:
    `make report-intake-route-proof-contract-gate`,
30. report intake route proof tests:
    `tests/unit/test_report_intake_route_proof.py`,
31. outbox broker proof tests:
    `tests/unit/test_outbox_broker_proof.py`,
32. platform mesh onboarding proof generator:
    `scripts/generate_platform_mesh_onboarding_proof.py`,
33. platform mesh onboarding proof contract gate:
    `make platform-mesh-onboarding-proof-contract-gate`,
34. platform mesh onboarding proof tests:
    `tests/unit/test_platform_mesh_onboarding_proof.py`,
35. Workbench read-path proof tests:
    `tests/unit/test_workbench_read_path_proof.py`,
36. runtime trust telemetry proof tests:
    `tests/unit/test_runtime_trust_telemetry_proof.py`,
37. outbox delivery run-once endpoint:
    `POST /api/v1/outbox-delivery/run-once`,
38. operation event: `implementation_proof_readiness_read`,
39. endpoint ledger:
    `docs/operations/endpoint-certification-ledger.json`,
40. runtime artifact loader tests:
    `tests/unit/test_proof_artifacts.py`,
41. unit tests:
    `tests/unit/test_implementation_proof_readiness.py`,
42. durable repository proof tests:
    `tests/unit/test_durable_repository_proof.py`,
43. generator tests:
    `tests/unit/test_generate_implementation_proof_readiness.py`,
44. AI workflow-pack registration proof generator:
    `scripts/generate_ai_workflow_pack_registration_proof.py`,
45. AI workflow-pack registration proof contract gate:
    `make ai-workflow-pack-registration-proof-contract-gate`,
46. AI workflow-pack registration proof tests:
    `tests/unit/test_ai_workflow_pack_registration_proof.py`,
47. AI workflow-pack runtime execution proof generator:
    `scripts/generate_ai_workflow_pack_runtime_execution_proof.py`,
48. AI workflow-pack runtime execution proof contract gate:
    `make ai-workflow-pack-runtime-execution-proof-contract-gate`,
49. AI workflow-pack runtime execution proof tests:
    `tests/unit/test_ai_workflow_pack_runtime_execution_proof.py`,
50. integration tests:
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
$env:LOTUS_REPORT_ROOT = "..\lotus-report"
$env:LOTUS_IDEA_REPORT_INTAKE_ROUTE_PROOF_OUTPUT = "output/downstream/report-intake-route-proof.json"
$env:IMPLEMENTATION_PROOF_OUTPUT = "output/implementation-proof/implementation-proof-readiness.json"
make implementation-proof-readiness-check

make durable-repository-proof-contract-gate
make runtime-trust-telemetry-proof-contract-gate
make ai-workflow-pack-registration-proof-contract-gate
make outbox-broker-proof-contract-gate
make report-intake-route-proof-contract-gate
make workbench-read-path-proof-contract-gate
make source-ingestion-scheduled-worker-check
make source-ingestion-live-proof-contract-gate
make downstream-realization-contract-gate
make runtime-trust-telemetry-snapshot-check
make endpoint-certification-gate
make openapi-gate
```

Use this endpoint to decide whether RFC-0002 is ready for live validation.
Use the live canonical stack only after the readiness blockers have been
cleared by implementation-backed slices.
