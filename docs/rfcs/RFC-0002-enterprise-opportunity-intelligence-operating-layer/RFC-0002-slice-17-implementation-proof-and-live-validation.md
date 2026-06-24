# RFC-0002 Slice 17: Implementation Proof And Live Validation

Status: Partially implemented - aggregate proof-readiness diagnostic, bounded live source-ingestion proof artifact contract, scheduled-worker deploy-contract proof, durable repository proof artifact, runtime telemetry proof artifact, Workbench read-path proof artifact, report-intake route proof artifact, bounded outbox broker proof artifact, and bounded Workbench read-path proof available; full live opportunity-journey proof remains pending

## Outcome

Prove the complete supported opportunity journey end to end.

## Current Implementation Evidence

1. `src/app/application/implementation_proof_readiness.py` builds a
   machine-readable RFC-0002 proof-readiness snapshot over current internal
   implementation foundations and known proof blockers.
2. `GET /api/v1/implementation-proof/readiness` exposes the snapshot as a
   certified internal operator endpoint with
   `idea.implementation-proof.readiness.read` capability enforcement.
3. `scripts/generate_implementation_proof_readiness.py` accepts explicit
   source-ingestion manifest, live-proof, scheduled-worker proof, and durable
   repository proof paths. `make implementation-proof-readiness-check` now
   generates the scheduled source-ingestion worker deploy-proof artifact and
   durable repository proof artifact before producing the same source-safe
   readiness snapshot as repo-native automation evidence without requiring the
   HTTP service to run.
4. `docs/operations/endpoint-certification-ledger.json` certifies the endpoint
   as an internal operator diagnostic and preserves the no-full-live-journey,
   no-Gateway-product-support, no-Workbench-product-support,
   no-client-ready-publication, and no-supported-feature-promotion boundary.
5. Unit and integration tests prove blocked posture, source-safe output,
   permission denial, timezone validation, unavailable-contract handling, and
   bounded `implementation_proof_readiness_read` operation events.
6. `GET /api/v1/downstream-realization/readiness` now supplies the downstream
   realization proof family used by the aggregate diagnostic. It reports
   Advise, Manage, Report, Render, and Archive blockers with current
   conversion/report workflow counts, while preserving the no-downstream-call
   and no-supported-feature boundary.
7. `GET /api/v1/outbox-delivery/readiness` and
   `POST /api/v1/outbox-delivery/run-once` now supply the outbox-delivery
   proof family used by the aggregate diagnostic. Readiness reports broker,
   downstream-consumer, platform mesh-event, Gateway/Workbench, and
   supported-feature blockers. Run-once proves the bounded internal publisher
   orchestration surface and fail-closed broker configuration behavior without
   exposing event identifiers, exposing raw idempotency keys, exposing broker
   payloads, or claiming downstream delivery.
   `scripts/generate_outbox_broker_proof.py` and
   `make outbox-broker-proof-contract-gate` now generate and validate the
   bounded outbox broker proof artifact consumed by aggregate
   implementation-proof readiness. A valid artifact clears only
   `outbox_broker_not_configured` and
   `external_broker_runtime_proof_missing`; downstream consumer, platform mesh
   event, Gateway/Workbench, and supported-feature blockers remain.
8. `make downstream-realization-contract-gate` now validates the planned
   downstream realization contract plan used by the downstream readiness proof
   family, so proof blockers stay source-authority preserving and cannot be
   rewritten as route-existence or downstream-execution claims.
9. `GET /api/v1/data-mesh/trust-telemetry/runtime-snapshot` now supplies the
   contract-shaped runtime trust telemetry proof family used by operators and
   certification reviewers before platform mesh promotion. It remains blocked
   and not certified, omits source-sensitive identifiers, and does not replace
   platform certification or supported-feature promotion.
10. `POST /api/v1/source-ingestion/run-once` now supplies the bounded internal
    source-ingestion operator proof surface. It can exercise the configured
    manifest and Core source adapter only when durable repository posture is
    active, returns aggregate decision counts only, and remains not certified
    until bounded live Core source proof, certified long-running scheduling proof,
    data-mesh runtime telemetry, Gateway/Workbench proof, and supported-feature
    promotion evidence exist.
11. `src/app/application/source_ingestion_live_proof.py`,
    `scripts/generate_source_ingestion_live_proof.py`, and
    `make source-ingestion-live-proof-contract-gate` now define and enforce the
    source-safe live Core proof artifact shape. When a valid artifact is
    referenced through `LOTUS_IDEA_SOURCE_INGESTION_LIVE_PROOF`, the
    source-ingestion readiness diagnostic can clear only
    `live_core_source_proof_missing`; scheduled worker, data-mesh,
    Gateway/Workbench, and supported-feature blockers remain.
    The artifact now carries aggregate `blockReasonCounts` for blocked proof
    attempts, with bounded codes for Core source unavailability, entitlement
    denial, missing cash-weight evidence, and Core-reported cash-weight
    supportability blockers. This improves live-proof diagnosis without
    exposing source payloads or reconstructing cash weight in `lotus-idea`.
12. `src/app/application/source_ingestion_scheduled_worker.py`,
    `scripts/run_scheduled_source_ingestion_worker.py`,
    `scripts/generate_scheduled_source_ingestion_worker_proof.py`, and
    `make source-ingestion-scheduled-worker-check` now define and enforce the
    source-safe scheduled worker deploy-contract proof shape. When a valid
    artifact is referenced through
    `LOTUS_IDEA_SOURCE_INGESTION_SCHEDULED_WORKER_PROOF`, the
     source-ingestion readiness diagnostic can clear only
     `scheduled_worker_deploy_proof_missing`; live Core, data-mesh,
     Gateway/Workbench, and supported-feature blockers remain.
13. `make implementation-proof-readiness-check` now generates that scheduled
    worker deploy-proof artifact under ignored `output/source-ingestion/` and
    passes it explicitly into aggregate proof-readiness generation, so repo-native
    evidence no longer reports a stale scheduled-worker deploy-proof blocker
    after the deploy contract is validated. Aggregate implementation-readiness
    evidence records validated live and scheduled source-ingestion proof
    artifact refs in the `source-ingestion` capability when those blockers are
    cleared.
14. `src/app/application/durable_repository_proof.py`,
    `scripts/generate_durable_repository_proof.py`, and
    `make durable-repository-proof-contract-gate` now define and enforce a
    source-safe durable repository proof artifact. The aggregate
    implementation-readiness generator can consume that artifact to clear only
    the stale aggregate `durable_repository_not_configured` proof blocker while
    preserving live Core, production storage, data-mesh, Gateway/Workbench,
    downstream, and supported-feature blockers.
15. `src/app/application/runtime_trust_telemetry_proof.py`,
    `scripts/generate_runtime_trust_telemetry_proof.py`, and
    `make runtime-trust-telemetry-proof-contract-gate` now define and enforce a
    source-safe runtime trust telemetry candidate-snapshot proof artifact. The
    aggregate implementation-readiness generator consumes that artifact to clear
    only `runtime_candidate_snapshot_missing`, while preserving platform
    source-manifest, platform mesh, Gateway/Workbench discovery, and
    supported-feature blockers.
16. `lotus-workbench` PR #391 merged bounded read-only Workbench rendering for
    the Gateway-published advisor queue and source-safe candidate detail. The
    live-validation script now fails unless a populated candidate row, loaded
    detail posture, non-empty source count, and observed candidate-detail route
    are present before screenshot evidence is recorded. This clears only the
    prior absence of a Workbench read-path implementation; it does not certify
    live source ingestion, entitlement-denied panel proof, mutation
    affordances, downstream realization, data-product certification, or
    supported-feature promotion.
17. `src/app/application/workbench_read_path_proof.py`,
    `scripts/generate_workbench_read_path_proof.py`, and
    `make workbench-read-path-proof-contract-gate` now define and enforce a
    source-safe bounded Workbench read-path proof artifact. The aggregate
    implementation-readiness generator consumes that artifact to clear only
    `workbench_gateway_bff_consumption_proof_missing`, while preserving full
    panel, browser accessibility, canonical demo runtime, data-product, and
    supported-feature blockers.
18. `src/app/runtime/proof_artifacts.py` now gives the certified operator API
    the same source-safe artifact-ref path as the aggregate generator for
    source-ingestion live proof, source-ingestion scheduled-worker proof,
    durable repository, runtime trust telemetry, Workbench read-path, outbox
    broker, and platform mesh onboarding proofs. `tests/unit/test_proof_artifacts.py`,
    `tests/unit/test_implementation_proof_readiness.py`, and
    `tests/integration/test_implementation_proof_readiness_api.py` prove that
    configured valid artifacts clear only their intended aggregate blockers,
    record source-safe evidence refs, and keep the API `blocked`,
    `not_certified`, and unpromoted.
19. The aggregate `ai-explanation` capability evidence now cites
    `contracts/observability/lotus-idea-ai-model-risk-operations.v1.json` and
    `make ai-model-risk-ops-contract-gate`. This makes the not-certified
    dashboard-control and alert-candidate posture visible in proof-readiness
    evidence without clearing the certified dashboard, alert, `lotus-ai`
    runtime, lineage-store, runtime trust telemetry, Workbench, or
    supported-feature blockers.
20. `src/app/application/platform_mesh_onboarding_proof.py`,
    `scripts/generate_platform_mesh_onboarding_proof.py`, and
    `make platform-mesh-onboarding-proof-contract-gate` now define and enforce
    a bounded cross-repo platform onboarding proof. The aggregate readiness
    generator consumes that artifact to clear only
    `platform_source_manifest_inclusion_missing` and
    `platform_catalog_inclusion_missing`, while preserving mesh certification,
    product activation, SLO/access/evidence, Gateway/Workbench, and
    supported-feature blockers.
21. `src/app/application/report_intake_route_proof.py`,
    `scripts/generate_report_intake_route_proof.py`, and
    `make report-intake-route-proof-contract-gate` now define and enforce a
    source-safe `lotus-report` route-foundation proof artifact. The aggregate
    implementation-readiness generator and operator API consume that artifact
    to clear only `lotus_report_live_intake_route_proof_missing`, while
    preserving report materialization, render output, archive record,
    client-publication, and supported-feature blockers.

This is a proof-control surface with bounded live source-ingestion evidence
support, not full live opportunity-journey proof. It makes missing evidence
durable and machine-readable so future implementation slices can clear blockers
without relying on chat memory.

## Required Work

1. Run repo-native checks and affected cross-repo gates.
2. Run canonical live validation through source APIs, `lotus-idea`, Gateway,
   Workbench, downstream conversion, report/render/archive where claimed, and
   AI fallback/provider paths.
3. Capture proof under non-git-tracked `output/` and summarize evidence in this
   slice file.
4. Critically review returned figures, statuses, reason codes, source refs,
   lineage refs, score, review state, AI posture, conversion outcome, and
   screenshots.

## Remaining Gap

1. Bounded live Core source-ingestion proof can be captured and consumed, but no
   canonical live proof run has been captured for the full opportunity journey.
2. Full Workbench live proof, live broker runtime, downstream materialization
   proof, render proof, archive proof, and client-publication proof remain
   pending.
3. Platform data-mesh certification, runtime trust telemetry, and mesh event
   certification remain pending.
4. Supported-feature promotion remains blocked until the readiness diagnostic
   reports no blockers and evidence is merged to `main`.
5. Durable repository proof is now explicit in aggregate readiness evidence, but
    deploy migration evidence, backup/restore, recovery operations, and
    production storage certification remain pending.
6. Runtime telemetry candidate-snapshot proof is now explicit in aggregate
   readiness evidence, but platform mesh certification and product discovery
   proof remain pending.
7. Workbench read-path proof is now explicit in aggregate readiness evidence,
   but full Workbench panel proof, browser accessibility proof, canonical demo
   runtime proof, entitlement-denied proof, mutation affordances, and
   supported-feature promotion remain pending.

The new downstream realization readiness diagnostic narrows the proof gap from
"unknown" to "explicitly blocked with source-authority refs"; it does not close
the downstream proof gap. The downstream realization contract gate makes those
blockers durable and machine-readable; it also does not close the downstream
proof gap.
The source-ingestion run-once operator action narrows the source proof gap from
"worker exists only as a CLI" to "service-boundary execution exists when
durable storage and runtime configuration are present"; it does not close live
Core source certification or certified long-running scheduled runtime proof.
The live-proof artifact contract narrows the live Core gap from "no durable
proof shape" to "operator-captured bounded live source-ingestion proof can be
validated and wired into readiness"; it does not close certified scheduled
daemon runtime, platform mesh, Gateway/Workbench, downstream, or
supported-feature proof.
The aggregate block-reason diagnostics further narrow the operator-debugging
gap for blocked live attempts; they are not source certification and do not
change the supported-feature posture.
The scheduled-worker deploy-contract artifact narrows the scheduling proof gap
from "no deployable worker contract" to "bounded scheduler entrypoint, Compose
worker service, source-safe proof, and aggregate readiness consumption are
CI-enforced"; it does not close long-running scheduler operations, live Core
source certification, platform mesh certification, Gateway/Workbench,
downstream, or supported-feature proof.
The outbox-delivery readiness diagnostic, run-once operator action, and bounded
outbox broker proof artifact do the same for broker and event delivery posture;
they do not close the external publication, platform mesh event certification,
or downstream consumer proof gap.
The runtime trust telemetry snapshot endpoint narrows the trust-evidence proof
gap from "generated artifact only" to "API-certified diagnostic plus generated
artifact"; it does not close platform mesh certification, Gateway/Workbench
discovery, or supported-feature proof gaps.
The runtime telemetry proof artifact narrows the aggregate readiness gap from
"runtime candidate snapshot missing" to "source-safe seeded candidate snapshot
contract is proven"; it also does not close platform mesh certification,
Gateway/Workbench discovery, or supported-feature proof gaps.
The Workbench read-path proof artifact narrows the aggregate readiness gap from
"no durable Workbench BFF-consumption proof" to "bounded read-only Gateway
queue/detail consumption has a source-safe proof artifact"; it does not close
full Workbench product proof, browser proof, canonical demo proof, mutation
affordances, or supported-feature proof.
The platform mesh onboarding proof narrows the aggregate readiness gap from
"no platform source-manifest/catalog proof" to "catalog-visible proposed
products and consumer dependencies are proven"; it does not close mesh
certification, active product, Gateway/Workbench discovery, SLO/access/evidence,
or supported-feature proof gaps.
The runtime proof-artifact loader narrows the operator-readiness gap from
"generator-only artifact consumption" to "HTTP and generated readiness share
the same configured proof evidence." It now includes source-ingestion live and
scheduled proof artifact refs plus optional report-intake route and platform
mesh onboarding proof refs as auditable evidence when those blockers clear; it
does not certify storage, live scheduler operations, mesh, Workbench,
Report/Render/Archive materialization, or supported-feature readiness.
The report-intake route proof narrows the downstream proof gap from "no
route-foundation evidence" to "`lotus-report` intake route is source-safely
proven and linked into readiness." It does not close Report package creation,
rendered output, archive record, client-publication, or supported-feature proof.
The AI model-risk operations contract refs narrow the model-risk proof index
gap from "contract exists outside aggregate readiness" to "contract and gate are
visible in the `ai-explanation` capability evidence." They do not certify a
dashboard, alert pack, `lotus-ai` runtime workflow, AI lineage store,
Workbench surface, or supported feature.

## Acceptance Gate

1. All proof gaps are fixed inside RFC-0002 or the supported claim is narrowed.
2. Evidence includes success, unsupported, degraded, denied, stale, duplicate,
   AI unavailable, and downstream failure paths.
3. GitHub checks and local gates are recorded with commit SHAs.
