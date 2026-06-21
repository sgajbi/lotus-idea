# RFC-0002 Slice 12: Advise And Manage Conversion Realization

Status: Partially implemented - internal conversion governance foundation only

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

## Remaining Work

This slice is not yet a supported conversion product. Remaining work includes:

1. database-backed persistence and idempotency storage for conversion intents
   and outcomes,
2. application use cases and API/OpenAPI contracts,
3. endpoint certification and Gateway/Workbench proof,
4. `lotus-advise` acceptance contract for proposal/suitability workflow intake,
5. `lotus-manage` acceptance contract for DPM review/action candidate intake,
6. `lotus-report` report-evidence package intake proof for the first
   report-only conversion path,
7. downstream failure/rejection/completion integration tests,
8. data-product trust telemetry and mesh certification,
9. supported-feature promotion after runtime and downstream proof.

## Required Work

1. Implement `IdeaConversionIntent` and `IdeaConversionOutcome`.
2. Add advisory conversion contract into `lotus-advise` for proposal or
   suitability workflow intake.
3. Add manage conversion contract into `lotus-manage` for DPM review/action
   candidate intake.
4. Record idempotency, downstream acceptance, rejection, failure, and completion.

## Acceptance Gate

1. Conversion requires human review.
2. Advise owns proposal and suitability realization.
3. Manage owns action and rebalance realization.
4. No conversion path creates orders, client communications, or autonomous
   advice.

The current implementation satisfies the internal domain governance portion of
this gate only. Cross-repository downstream realization remains planned.
