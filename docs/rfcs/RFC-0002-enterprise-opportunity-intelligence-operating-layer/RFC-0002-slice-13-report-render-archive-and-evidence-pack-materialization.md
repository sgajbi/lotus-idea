# RFC-0002 Slice 13: Report, Render, Archive, And Evidence-Pack Materialization

Status: Partially implemented - internal report evidence-pack request foundation, source-safe downstream submission API, application orchestration and adapter foundation, governed downstream contract-plan gate, bounded `lotus-report` intake route proof consumption, and bounded `lotus-report` materialization proof consumption while client publication and supported-feature promotion remain blocked

## Outcome

Materialize reviewed idea evidence through reporting, rendering, and archiving
services where product claims require documentable proof.

## Required Work

1. Define reportable idea evidence package.
2. Integrate with `lotus-report` for report package intake.
3. Integrate with `lotus-render` for deterministic render projections.
4. Integrate with `lotus-archive` for archive metadata, retention, legal hold
   posture, retrieval refs, and access audit.

## Current Implementation Evidence

Implemented in the first Slice 13 foundation:

1. `src/app/domain/report_evidence.py` defines the governed report evidence-pack
   request contract, purpose vocabulary, source-summary projection,
   Report/Render/Archive source-authority refs, retention policy refs, audit
   event, and explicit no-client-publication/no-render/no-archive authority.
2. `src/app/application/report_evidence.py` orchestrates report evidence-pack
   requests through repository protocols instead of route-owned business logic.
3. `src/app/domain/persistence.py` persists report evidence-pack requests with
   idempotency replay/conflict posture and snapshot recovery.
4. `src/app/api/report_evidence.py` exposes the certified internal endpoint:
   `POST /api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs`.
5. `docs/operations/endpoint-certification-ledger.json` records the route,
   examples, non-goals, error posture, and test evidence.
6. Tests cover domain gating, idempotency, source-authority refs, API
   permission, safe errors, replay/conflict, missing resource, and blocked
   client-ready publication:
   - `tests/unit/test_report_evidence.py`,
   - `tests/unit/test_idea_persistence.py`,
   - `tests/integration/test_review_workflow_api.py`,
   - `tests/integration/test_postgres_runtime_integration.py`,
   - `tests/unit/test_service_contract.py`.
7. `GET /api/v1/downstream-realization/readiness` now reports the current
   report evidence-pack request count and the explicit Report/Render/Archive
   blockers for operators without calling `lotus-report`, `lotus-render`, or
   `lotus-archive`. It also exposes the planned
   `lotus-idea-to-lotus-report-evidence-pack-intake:v1` contract readiness
   record with `lotus-report` ownership, planned route posture, adapter status,
   the report-owned planned intake contract evidence ref, and the remaining
   live intake route/materialization blockers.
8. `contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`
   is the governed source for that planned report handoff row, and
   `make downstream-realization-contract-gate` keeps it planned,
   source-authority preserving, blocker-backed, and free of route-existence,
   downstream-execution, or supported-feature claims.
   The report-owned intake contract now exists at
   `lotus-report/contracts/idea-evidence-intake/lotus-report-idea-evidence-pack-intake.v1.json`.
   The merged `lotus-report` route foundation can now be proven through
   `scripts/generate_report_intake_route_proof.py` and
   `make report-intake-route-proof-contract-gate`. A valid artifact clears only
   `lotus_report_live_intake_route_proof_missing`; it does not prove
   materialization, render, archive, client-publication authority, or a
   supported feature.
   The merged `lotus-report` materialization path can now also be proven through
   `scripts/generate_report_materialization_proof.py` and
   `make report-materialization-proof-contract-gate`. A valid artifact clears
   only `report_evidence_pack_live_materialization_proof_missing`,
   `rendered_output_creation_missing`, and `archive_record_creation_missing`;
   it does not grant client-publication authority or promote a supported
   feature.
9. `src/app/ports/downstream_realization.py` and
   `src/app/infrastructure/downstream_realization.py` add a source-safe HTTP
   adapter foundation for Report evidence-pack request handoff envelopes. The
   envelope preserves Report/Render/Archive source authority, retention
   posture, reason codes, and bounded source summaries, while omitting source
   routes, raw source payloads, raw downstream responses, and client-ready
   publication authority.
10. `src/app/application/downstream_realization.py` now adds source-safe
    application orchestration for submitting existing report evidence-pack
    requests through the Report downstream realization port. It finds the
    request from repository snapshot truth, propagates correlation and trace
    identifiers, returns accepted, rejected, and not-found posture, and
    deliberately does not claim or record Report package creation, Render
    output creation, Archive record creation, or client-ready publication.
11. `tests/unit/test_downstream_realization_application.py` proves report
    evidence-pack submission behavior, not-found behavior, no downstream
    outcome recording, no downstream-authority grant, and no supported-feature
    promotion.
12. `src/app/api/downstream_realization.py` exposes the certified internal
    `POST /api/v1/report-evidence-packs/{reportEvidencePackId}/downstream-submissions`
    route for existing report evidence-pack requests. The route requires
    `idea.downstream-realization.submit` and `Idempotency-Key`, obtains the
    configured Report client from `src/app/runtime/downstream_realization_state.py`,
    propagates correlation, trace, and idempotency headers through the
    application layer, and fails closed with
    `503 downstream_realization_not_configured` when adapter configuration is
    absent.
13. `docs/operations/endpoint-certification-ledger.json` and
    `docs/operations/api-certification.md` record endpoint certification,
    product-safe errors, usage boundaries, and operation-event evidence for
    the report evidence-pack downstream submission route.
14. `tests/integration/test_downstream_realization_api.py` proves the Report
    submission success path, missing-adapter fail-closed posture, permission
    denial, not-certified operation-event emission, and absence of Report
    package intake, Render output, Archive record, client-publication, or
    supported-feature claims.

Current endpoint behavior:

1. requires a previously recorded `report_evidence` conversion intent,
2. requires `idea.report-evidence-pack.request` and `Idempotency-Key`,
3. requires reviewed, approved, ready evidence that has already moved to
   `converted_to_report`,
4. preserves source evidence summaries and evidence hash without returning raw
   source routes or payloads,
5. records retention policy reference and safe audit event,
6. returns `durableStorageBacked` from the active repository provider and
   `supportedFeaturePromoted=false`.

## Acceptance Gate

1. Only reviewed idea evidence can be materialized.
2. Rendered output matches source evidence and review state.
3. Archive refs preserve lineage and access posture.
4. Client-ready publication remains blocked unless explicitly supported and
   proven.

## Acceptance Status

Partially satisfied:

1. Reviewed idea evidence gate is implemented for the internal request
   foundation.
2. Client-ready publication is explicitly blocked.
3. Source evidence lineage and safe source summaries are preserved.
4. `lotus-report` can provide source-safe materialization/render/archive proof
   for reviewed idea evidence when the sibling materialization contract is
   present.

Not yet satisfied:

1. Client-ready publication authority remains blocked.
2. Supported-feature promotion remains blocked.
3. Suitability, rebalance/action, and execution authority remain in the owning
   downstream applications.
4. No Gateway/Workbench product surface, data-product certification, runtime
   trust telemetry, client-publication proof, or supported-feature promotion
   exists. PostgreSQL-backed internal request recording proof exists
   only inside the opt-in runtime proof.

The downstream-realization readiness diagnostic and report submission API are
certified as internal foundations. With a valid report-intake route proof, they
can cite `POST /reports/idea-evidence-packs` as a route-foundation proof, but
they are still not materialization proof. With a valid report-materialization
proof, they can also cite
`POST /reports/idea-evidence-packs/materializations` as report-owned
materialization/render/archive evidence. They keep Report/Render/Archive
ownership outside `lotus-idea` and remain `not_certified` until client
publication, Gateway/Workbench product proof, data-mesh certification, and
supported-feature promotion are implemented and validated.

## Boundary Decision

This slice intentionally starts with `lotus-idea` source-owned request truth and
a source-safe adapter foundation. Report, Render, and Archive remain the
authorities for package intake, deterministic rendering, archive records,
retention, legal hold, retrieval, and access audit. The next Slice 13 increment
should decide whether client-publication authority, rendered-output equivalence,
retrieval/legal-hold audit evidence, or product-surface proof belongs in this
RFC slice or in later publication/demo certification slices. It must not move
downstream authority into `lotus-idea`.
