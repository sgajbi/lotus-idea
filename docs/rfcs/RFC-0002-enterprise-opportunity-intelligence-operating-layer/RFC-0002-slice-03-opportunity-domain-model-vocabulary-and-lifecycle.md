# RFC-0002 Slice 03: Opportunity Domain Model, Vocabulary, And Lifecycle

Status: Implemented - pure domain foundation with public domain API boundary enforcement

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

## Implementation Evidence

Implemented scope:

1. `src/app/domain/ideas.py` defines framework-free domain vocabulary for
   opportunity family, source system, evidence freshness/supportability,
   unsupported-evidence reasons, reason codes, lifecycle status, review
   posture, suppression, feedback, conversion target, and conversion outcome.
2. `SourceRef`, `LineageRef`, `OpportunitySignal`, `IdeaEvidencePacket`,
   `IdeaScore`, `ReviewDecision`, `IdeaFeedback`, `IdeaCandidate`,
   `IdeaConversionIntent`, and `IdeaConversionOutcome` are immutable dataclass
   domain models.
3. `ALLOWED_LIFECYCLE_TRANSITIONS` and `transition_candidate` implement valid
   lifecycle movement and reject forbidden transitions with
   `InvalidLifecycleTransition`.
4. Review decisions expose `grants_downstream_authority=False`, so review can
   gate conversion readiness but cannot approve suitability, compliance,
   mandate, execution, or client communication.
5. Evidence supportability is typed: blocked evidence requires explicit
   unsupported reasons, and ready evidence cannot carry unsupported reasons.
6. Conversion intent requires an approved candidate source status.
7. Cross-module callers use public `app.domain` exports for domain invariants;
   `make private-import-boundary-gate` blocks imports from private
   `app.domain.*` helpers so implementation slices do not create hidden domain
   coupling.
8. `src/app/domain/candidate_state.py` defines the exhaustive, versioned
   `idea-candidate-state-v1` lifecycle/review-posture matrix. Candidate
   construction rejects contradictions, and lifecycle transitions normalize
   reviewed, approved, rejected, expired, and closed posture deterministically.
9. `tests/unit/test_candidate_state_policy.py` covers every lifecycle/posture
   pair and proves terminal states cannot remain conversion-ready or reviewable.

Out of scope for this slice:

1. persistence,
2. API routes,
3. source adapters,
4. scoring methodology beyond bounded score envelope,
5. AI workflow execution,
6. supported-feature promotion,
7. data-product certification.

## Validation

Targeted validation:

1. `.venv\Scripts\python.exe -m pytest tests\unit\test_idea_domain_model.py -q`
   passed with `16 passed`.
2. `.venv\Scripts\python.exe -m ruff check src\app\domain\ideas.py src\app\domain\__init__.py tests\unit\test_idea_domain_model.py`
   passed.
3. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini` passed.
4. `.venv\Scripts\python.exe scripts\private_import_boundary_gate.py` passed.

Full repository validation for the current branch must still run before PR
closure.
