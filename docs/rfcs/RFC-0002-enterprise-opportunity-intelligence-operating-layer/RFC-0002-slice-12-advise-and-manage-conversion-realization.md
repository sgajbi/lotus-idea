# RFC-0002 Slice 12: Advise And Manage Conversion Realization

Status: Planned

## Outcome

Convert reviewed ideas into downstream advisory and portfolio-management
workflows without moving downstream authority into `lotus-idea`.

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
