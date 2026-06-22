# RFC-0002 Slice 13: Report, Render, Archive, And Evidence-Pack Materialization

Status: Partially implemented - internal report evidence-pack request foundation, source-safe downstream application orchestration and adapter foundation, and governed downstream contract-plan gate

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
   and the dedicated report idea evidence intake blocker.
8. `contracts/downstream-realization/lotus-idea-downstream-contracts.v1.json`
   is the governed source for that planned report handoff row, and
   `make downstream-realization-contract-gate` keeps it planned,
   source-authority preserving, blocker-backed, and free of route-existence,
   downstream-execution, or supported-feature claims.
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

Not yet satisfied:

1. No certified live `lotus-report` package intake contract or acceptance proof
   exists.
2. No dedicated `lotus-report` idea evidence-pack intake route or acceptance
   proof exists.
3. No `lotus-render` deterministic output projection exists.
4. No `lotus-archive` metadata, retention, legal-hold, retrieval, or access-audit
   record exists.
5. No rendered-output equivalence proof exists.
6. No Gateway/Workbench product surface, data-product certification, runtime
   trust telemetry, downstream materialization proof, or supported-feature
   promotion exists. PostgreSQL-backed internal request recording proof exists
   only inside the opt-in runtime proof.

The downstream-realization readiness diagnostic is certified as an internal
operator endpoint, but it is not materialization proof or downstream
route-existence proof. It keeps Report/Render/Archive ownership outside
`lotus-idea` and remains `not_certified` until downstream intake,
deterministic rendering, archive metadata, retention/legal-hold, retrieval, and
access-audit proof are implemented in the owning services.

## Boundary Decision

This slice intentionally starts with `lotus-idea` source-owned request truth and
a source-safe adapter foundation. Report, Render, and Archive remain the
authorities for package intake, deterministic rendering, archive records,
retention, legal hold, retrieval, and access audit. The next Slice 13 increment
should certify a live downstream intake contract only after the owning service
accepts the request shape and can test it without moving downstream authority
into `lotus-idea`.
