# RFC-0002 Slice 17: Implementation Proof And Live Validation

Status: Partially implemented - aggregate proof-readiness diagnostic, live source-proof artifact contract, and scheduled-worker deploy-contract proof available; full live proof remains pending

## Outcome

Prove the complete supported opportunity journey end to end.

## Current Implementation Evidence

1. `src/app/application/implementation_proof_readiness.py` builds a
   machine-readable RFC-0002 proof-readiness snapshot over current internal
   implementation foundations and known proof blockers.
2. `GET /api/v1/implementation-proof/readiness` exposes the snapshot as a
   certified internal operator endpoint with
   `idea.implementation-proof.readiness.read` capability enforcement.
3. `scripts/generate_implementation_proof_readiness.py` and
   `make implementation-proof-readiness-check` generate the same source-safe
   readiness snapshot as repo-native automation evidence without requiring the
   HTTP service to run.
4. `docs/operations/endpoint-certification-ledger.json` certifies the endpoint
   as an internal operator diagnostic and preserves the no-live-proof,
   no-Gateway, no-Workbench, no-client-ready-publication, and
   no-supported-feature-promotion boundary.
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
    until live Core source proof, certified long-running scheduling proof,
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

This is a proof-control surface, not live proof. It makes missing evidence
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

1. No canonical live proof run has been captured for the full opportunity
   journey.
2. Workbench, live broker runtime, and downstream realization proof
   remain pending.
3. Platform data-mesh certification, runtime trust telemetry, and mesh event
   certification remain pending.
4. Supported-feature promotion remains blocked until the readiness diagnostic
   reports no blockers and evidence is merged to `main`.

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
proof shape" to "operator-captured proof can be validated and wired into
readiness"; it does not close certified scheduled daemon runtime, platform mesh,
Gateway/Workbench, downstream, or supported-feature proof.
The scheduled-worker deploy-contract artifact narrows the scheduling proof gap
from "no deployable worker contract" to "bounded scheduler entrypoint, Compose
worker service, and source-safe proof are CI-enforced"; it does not close
long-running scheduler operations, live Core source certification, platform
mesh certification, Gateway/Workbench, downstream, or supported-feature proof.
The outbox-delivery readiness diagnostic and run-once operator action do the
same for broker and event delivery posture; they do not close the external
publication, platform mesh event certification, or downstream consumer proof
gap.
The runtime trust telemetry snapshot endpoint narrows the trust-evidence proof
gap from "generated artifact only" to "API-certified diagnostic plus generated
artifact"; it does not close platform mesh certification, Gateway/Workbench
discovery, or supported-feature proof gaps.

## Acceptance Gate

1. All proof gaps are fixed inside RFC-0002 or the supported claim is narrowed.
2. Evidence includes success, unsupported, degraded, denied, stale, duplicate,
   AI unavailable, and downstream failure paths.
3. GitHub checks and local gates are recorded with commit SHAs.
