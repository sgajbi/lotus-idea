# RFC-0002 Slice 03: Opportunity Domain Model, Vocabulary, And Lifecycle

Status: Planned

## Outcome

Implement the pure domain contract for idea candidates before persistence,
ingestion, APIs, AI, or UI work.

## Required Work

1. Implement domain models for candidate, signal, evidence packet, source ref,
   lineage ref, lifecycle state, review posture, score, feedback, suppression,
   conversion intent, conversion outcome, unsupported evidence, and audit event.
2. Implement allowed lifecycle transitions and forbidden transition errors.
3. Define stable reason-code and status vocabulary.
4. Keep the model independent from FastAPI, database, HTTP clients, and AI
   provider details.

## Acceptance Gate

1. Unit tests cover valid and invalid lifecycle transitions.
2. Review state cannot approve suitability, compliance, mandate, execution, or
   client communication.
3. Unsupported-evidence reasons are explicit and typed.
4. No source-owned calculation is implemented in `lotus-idea`.
