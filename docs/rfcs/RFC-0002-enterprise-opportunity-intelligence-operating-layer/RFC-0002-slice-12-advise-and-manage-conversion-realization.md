# RFC-0002 Slice 12: Advise And Manage Conversion Realization

Status: Partially implemented - internal conversion governance and certified API foundation only

## Outcome

Convert reviewed ideas into downstream advisory and portfolio-management
workflows without moving downstream authority into `lotus-idea`.

## Current Implementation Evidence

Implemented in this slice:

1. `src/app/domain/conversion_governance.py` adds a framework-free conversion
   governance layer for review-gated downstream intents and source-owned
   downstream outcomes.
2. `ConversionIntentCommand` requires a target, actor, idempotency key, reason
   codes, and timezone-aware request time before an intent can be created.
3. `request_conversion_intent` accepts only candidates that are already
   lifecycle-approved, have `approved_for_conversion` review posture, and carry
   ready evidence. It rejects unreviewed, not-approved, or blocked-evidence
   candidates.
4. Conversion targets map to the downstream source authority that owns
   realization:
   - `advise_proposal` -> `lotus-advise`,
   - `manage_review` -> `lotus-manage`,
   - `report_evidence` -> `lotus-report`.
5. Requesting a conversion intent moves the candidate into the appropriate
   converted lifecycle posture while keeping the conversion boundary
   `intent_only`; it does not create proposals, DPM actions, reports, orders,
   client communications, suitability approvals, compliance approvals, or
   mandate approvals.
6. `record_conversion_outcome` accepts outcome status only from the expected
   downstream source authority and records a governed outcome without granting
   execution, suitability, or client-communication authority.
7. Safe audit events are emitted for conversion intent and outcome recording
   without portfolio/client identifiers or raw payloads.
8. `tests/unit/test_conversion_governance.py` covers report, advise, and manage
   target mapping, review gating, blocked evidence, idempotency-key validation,
   target source-authority enforcement, safe audit fields, forbidden target
   vocabulary, and no downstream-authority semantics.
9. `src/app/domain/persistence.py` stores conversion intents and outcomes in
   the in-memory repository foundation with idempotency replay, conflict,
   not-found posture, lifecycle history updates, safe audit event append, and
   snapshot recovery for conversion-intent lookup.
10. `src/app/application/conversion_workflow.py` adds the application use case
    layer for repository precheck, conversion intent creation, and conversion
    outcome recording without re-running domain transitions on idempotency
    replay.
11. `src/app/api/conversion_governance.py` exposes certified internal API
    foundations:
    - `POST /api/v1/idea-candidates/{candidateId}/conversion-intents`,
    - `POST /api/v1/conversion-intents/{conversionIntentId}/outcomes`.
12. `docs/operations/endpoint-certification-ledger.json` records certification
    evidence, examples, error posture, and test proof for the conversion API
    foundations.
13. `tests/unit/test_idea_persistence.py` and
    `tests/integration/test_review_workflow_api.py` cover repository
    idempotency, audit posture, API permission, invalid state, missing
    resources, wrong source authority, replay, and conflict behavior.
14. `tests/integration/test_postgres_runtime_integration.py` now proves the
    first PostgreSQL-backed internal report conversion path by creating a
    review-approved candidate, recording the report conversion intent, replaying
    the intent from database idempotency state, recording a source-authorized
    conversion outcome, and validating the conversion intent/outcome tables.
15. `src/app/application/downstream_realization_readiness.py` and
    `GET /api/v1/downstream-realization/readiness` add a certified internal
    operator diagnostic over current conversion intent/outcome counts and
    Advise/Manage realization blockers. The diagnostic requires both the
    `operator` role and `idea.downstream-realization.readiness.read`
    capability, emits `downstream_realization_readiness_read`, and keeps the
    supportability posture `not_certified` until live downstream contract proof
    exists.

## Remaining Work

This slice is not yet a supported conversion product. Remaining work includes:

1. Gateway/Workbench proof,
2. `lotus-advise` acceptance contract for proposal/suitability workflow intake,
3. `lotus-manage` acceptance contract for DPM review/action candidate intake,
4. `lotus-report` report-evidence package intake proof for the first
   report-only conversion path,
5. downstream failure/rejection/completion integration tests across owning
   services,
6. data-product trust telemetry and mesh certification,
7. supported-feature promotion after runtime and downstream proof.

The downstream-realization readiness diagnostic is a blocker index only. It
does not create proposals, suitability records, manage action-register records,
rebalance records, orders, client communications, reports, rendered output, or
archive records.

## Required Work

1. Implement `IdeaConversionIntent` and `IdeaConversionOutcome`.
2. Add certified internal API/OpenAPI contracts for conversion intent and
   outcome recording.
3. Add advisory conversion contract into `lotus-advise` for proposal or
   suitability workflow intake.
4. Add manage conversion contract into `lotus-manage` for DPM review/action
   candidate intake.
5. Record idempotency, downstream acceptance, rejection, failure, and
   completion.

## Acceptance Gate

1. Conversion requires human review.
2. Advise owns proposal and suitability realization.
3. Manage owns action and rebalance realization.
4. No conversion path creates orders, client communications, or autonomous
   advice.

The current implementation satisfies the internal domain governance and
certified internal API foundation portions of this gate only. Cross-repository
downstream realization remains planned.
