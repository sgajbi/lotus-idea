# RFC-0002 Slice 17: Implementation Proof And Live Validation

Status: Partially implemented - aggregate proof-readiness diagnostic available; live proof remains pending

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
7. `GET /api/v1/outbox-delivery/readiness` now supplies the outbox-delivery
   proof family used by the aggregate diagnostic. It reports broker,
   downstream-consumer, platform mesh-event, Gateway/Workbench, and
   supported-feature blockers without publishing events, exposing event
   identifiers, exposing raw idempotency keys, or exposing broker payloads.

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
2. Workbench, external broker publication, and downstream realization proof
   remain pending.
3. Platform data-mesh certification, runtime trust telemetry, and mesh event
   certification remain pending.
4. Supported-feature promotion remains blocked until the readiness diagnostic
   reports no blockers and evidence is merged to `main`.

The new downstream realization readiness diagnostic narrows the proof gap from
"unknown" to "explicitly blocked with source-authority refs"; it does not close
the downstream proof gap.
The outbox-delivery readiness diagnostic does the same for broker and event
delivery posture; it does not close the external publication or downstream
consumer proof gap.

## Acceptance Gate

1. All proof gaps are fixed inside RFC-0002 or the supported claim is narrowed.
2. Evidence includes success, unsupported, degraded, denied, stale, duplicate,
   AI unavailable, and downstream failure paths.
3. GitHub checks and local gates are recorded with commit SHAs.
