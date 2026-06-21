import pytest

from app.domain.audit import AuditEvent
from app.domain.idempotency import (
    IdempotencyDecision,
    evaluate_idempotency,
)


def test_same_key_same_payload_replays_existing_record() -> None:
    decision, record = evaluate_idempotency(
        key="request-1",
        payload={"action": "approve", "amount": "100.00"},
        existing=None,
    )
    assert decision == IdempotencyDecision.ACCEPTED

    replay_decision, replay_record = evaluate_idempotency(
        key="request-1",
        payload={"amount": "100.00", "action": "approve"},
        existing=record,
    )
    assert replay_decision == IdempotencyDecision.REPLAYED
    assert replay_record == record


def test_same_key_different_payload_conflicts() -> None:
    _, record = evaluate_idempotency(
        key="request-1",
        payload={"action": "approve", "amount": "100.00"},
        existing=None,
    )
    decision, _ = evaluate_idempotency(
        key="request-1",
        payload={"action": "reject", "amount": "100.00"},
        existing=record,
    )
    assert decision == IdempotencyDecision.CONFLICT


def test_audit_event_rejects_sensitive_attributes() -> None:
    with pytest.raises(ValueError):
        AuditEvent(
            event_type="workflow.updated",
            actor_subject="operator",
            outcome="denied",
            attributes={"portfolio_id": "PB_SG_GLOBAL_BAL_001"},
        )


def test_audit_event_allows_bounded_non_sensitive_attributes() -> None:
    event = AuditEvent(
        event_type="workflow.updated",
        actor_subject="operator",
        outcome="accepted",
        attributes={"workflow_state": "planned"},
    )
    assert event.attributes["workflow_state"] == "planned"
