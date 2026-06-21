# RFC-0002 Slice 08: Review Queues, Feedback, And Human Governance

Status: Partially implemented - internal advisor review and feedback governance foundation only

## Outcome

Implement human review, feedback, and governance over opportunity queues.

## Current Implementation Evidence

Implemented in this slice:

1. `src/app/domain/review_governance.py` adds a framework-free review
   governance domain layer for the first-wave advisor audience approved by
   Slice 0.
2. Advisor review actions now cover approve-for-conversion, reject, no-action,
   suppress, snooze, escalate-to-PM, and escalate-to-compliance outcomes.
3. Review actor scope fails closed across tenant, book, portfolio, and client
   membership before a review decision or feedback event is accepted.
4. Advisor-only first-wave action policy is explicit. PM, compliance, and
   operator roles are modeled as vocabulary for escalation and later queue
   slices, but they are not yet permitted to execute first-wave review actions.
5. Governed review decisions and feedback events carry candidate identity,
   evidence packet identity, evidence content hash, source signal provenance,
   actor subject, actor role, typed reason codes, and safe audit events.
6. Review decisions never grant downstream suitability, compliance, mandate,
   execution, or client-communication authority.
7. Queue projections react to review outcomes through lifecycle, posture,
   suppression, and snooze state without introducing persisted queue state.
8. `tests/unit/test_review_governance.py` covers advisor approval, entitlement
   failure, non-advisor denial, blocked-evidence approval denial, rejection,
   no-action, suppression, snooze, escalation, feedback provenance, safe audit
   attributes, and command validation.

Validation evidence from the implementation slice:

1. `.venv\Scripts\python.exe -m ruff check src\app\domain\review_governance.py src\app\domain\ideas.py src\app\domain\__init__.py tests\unit\test_review_governance.py`
2. `.venv\Scripts\python.exe -m mypy --config-file mypy.ini`
3. `.venv\Scripts\python.exe -m pytest tests/unit/test_review_governance.py`

## Remaining Work

This slice is not yet a supported review product. Remaining work includes:

1. database-backed durable review decision and feedback persistence,
2. application use cases and API/OpenAPI contracts,
3. endpoint certification and Gateway/Workbench integration proof,
4. PM, compliance, and operator queue surfaces and permission policy,
5. integration with the runtime caller-context and entitlement system,
6. feedback data-product declaration promotion and mesh certification,
7. trust telemetry, operational support, and supported-feature promotion.

## Required Work

1. Add advisor, PM, compliance, and operator queue projections as approved by
   Slice 0.
2. Implement review decisions, feedback, rejection, suppression, snooze,
   escalation, and no-action outcomes.
3. Enforce role, book, portfolio, client, and tenant entitlements.
4. Capture audit reason and actor context for all review actions.

## Acceptance Gate

1. Review actions cannot approve downstream suitability, compliance, mandate, or
   execution state.
2. Entitlement tests fail closed.
3. Queue projections update after decisions.
4. Feedback events are source-provenanced.

The durable feedback portion remains planned until a database-backed persistence
slice stores review decisions and feedback events behind application/API
contracts.
