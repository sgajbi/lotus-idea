from __future__ import annotations

from types import SimpleNamespace

from app.api.persistence_summary import persistence_summary_payload


def test_persistence_summary_payload_uses_explicit_audit_event() -> None:
    result = SimpleNamespace(
        decision="persisted",
        record=_record("candidate-1", audit_event_types=("fallback",)),
        audit_event=SimpleNamespace(event_type="explicit"),
    )

    assert persistence_summary_payload(result) == {
        "decision": "persisted",
        "candidateId": "candidate-1",
        "lifecycleStatus": "review_ready",
        "reviewPosture": "needs_review",
        "auditEventType": "explicit",
    }


def test_persistence_summary_payload_falls_back_to_latest_record_audit() -> None:
    result = SimpleNamespace(
        decision="persisted",
        record=_record("candidate-1", audit_event_types=("created", "updated")),
        audit_event=None,
    )

    assert persistence_summary_payload(result)["auditEventType"] == "updated"


def test_persistence_summary_payload_allows_blocked_without_record() -> None:
    result = SimpleNamespace(decision="blocked", record=None, audit_event=None)

    assert persistence_summary_payload(result) == {
        "decision": "blocked",
        "candidateId": None,
        "lifecycleStatus": None,
        "reviewPosture": None,
        "auditEventType": None,
    }


def _record(candidate_id: str, *, audit_event_types: tuple[str, ...]) -> SimpleNamespace:
    return SimpleNamespace(
        candidate=SimpleNamespace(
            candidate_id=candidate_id,
            lifecycle_status=SimpleNamespace(value="review_ready"),
            review_posture=SimpleNamespace(value="needs_review"),
        ),
        audit_events=[
            SimpleNamespace(event_type=audit_event_type) for audit_event_type in audit_event_types
        ],
    )
