from __future__ import annotations

from fastapi.testclient import TestClient

from app.domain import OutboxEventRecord
from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_review_workflow_api import (
    approve_candidate_for_conversion,
    conversion_intent_headers,
    conversion_intent_payload,
    conversion_outcome_headers,
    conversion_outcome_payload,
    feedback_headers,
    feedback_payload,
    lifecycle_headers,
    lifecycle_payload,
    persisted_candidate_id,
    report_evidence_pack_headers,
    report_evidence_pack_payload,
    review_headers,
    suppress_review_payload,
)


def test_candidate_and_lifecycle_api_preserve_parent_lineage_across_replay() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="lineage-candidate-001")
    headers = lifecycle_headers("lineage-lifecycle-001")
    headers["X-Causation-Id"] = "event-candidate-persisted-001"
    route = f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions"

    accepted = client.post(route, json=lifecycle_payload(), headers=headers)
    replayed = client.post(
        route,
        json=lifecycle_payload(),
        headers={**headers, "X-Trace-Id": "trace-lifecycle-retry-api"},
    )

    assert accepted.status_code == 200
    assert replayed.status_code == 200
    assert replayed.json()["persistence"]["decision"] == "replayed"
    candidate_event = _latest_event("idea.candidate.persisted.v1")
    assert candidate_event.correlation_id == "corr-candidate-persist-api"
    assert candidate_event.trace_id == "trace-candidate-persist-api"
    lifecycle_event = _latest_event("idea.lifecycle.transitioned.v1")
    assert lifecycle_event.correlation_id == "corr-lifecycle-api"
    assert lifecycle_event.trace_id == "trace-lifecycle-api"
    assert lifecycle_event.causation_id == "event-candidate-persisted-001"
    assert lifecycle_event.lineage_origin.value == "parent_event"


def test_review_and_feedback_apis_persist_distinct_request_lineage() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    review_candidate_id = persisted_candidate_id(client, idempotency_key="lineage-review-seed-001")
    review = client.post(
        f"/api/v1/idea-candidates/{review_candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=review_headers("lineage-review-001"),
    )
    assert review.status_code == 200
    review_event = _latest_event("idea.review.decision_recorded.v1")
    assert review_event.correlation_id == "corr-review-api"
    assert review_event.trace_id == "trace-review-api"
    assert review_event.causation_id is None
    assert review_event.lineage_origin.value == "request"

    reset_idea_repository_for_tests()
    feedback_candidate_id = persisted_candidate_id(
        client,
        idempotency_key="lineage-feedback-seed-001",
    )
    feedback = client.post(
        f"/api/v1/idea-candidates/{feedback_candidate_id}/feedback",
        json=feedback_payload(),
        headers=feedback_headers("lineage-feedback-001"),
    )

    assert feedback.status_code == 200
    feedback_event = _latest_event("idea.feedback.recorded.v1")
    assert feedback_event.correlation_id == "corr-feedback-api"
    assert feedback_event.trace_id == "trace-feedback-api"


def test_conversion_and_report_apis_persist_lineage_for_each_event_family() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="lineage-conversion-seed-001")
    approve_candidate_for_conversion(client, candidate_id)
    intent_id = "lineage-conversion-intent-001"
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=intent_id),
        headers=conversion_intent_headers("lineage-conversion-intent-001"),
    )
    assert intent.status_code == 200

    outcome_headers = conversion_outcome_headers("lineage-conversion-outcome-001")
    outcome_headers["X-Causation-Id"] = "event-conversion-intent-001"
    outcome = client.post(
        f"/api/v1/conversion-intents/{intent_id}/outcomes",
        json=conversion_outcome_payload(),
        headers=outcome_headers,
    )
    report_pack = client.post(
        f"/api/v1/conversion-intents/{intent_id}/report-evidence-packs",
        json=report_evidence_pack_payload(),
        headers=report_evidence_pack_headers("lineage-report-pack-001"),
    )

    assert outcome.status_code == 200
    assert report_pack.status_code == 200
    intent_event = _latest_event("idea.conversion.intent_requested.v1")
    assert intent_event.correlation_id == "corr-conversion-intent-api"
    assert intent_event.trace_id == "trace-conversion-intent-api"
    outcome_event = _latest_event("idea.conversion.outcome_recorded.v1")
    assert outcome_event.correlation_id == "corr-conversion-outcome-api"
    assert outcome_event.trace_id == "trace-conversion-outcome-api"
    assert outcome_event.causation_id == "event-conversion-intent-001"
    assert outcome_event.lineage_origin.value == "parent_event"
    report_event = _latest_event("idea.report_evidence_pack.requested.v1")
    assert report_event.correlation_id == "corr-report-evidence-pack-api"
    assert report_event.trace_id == "trace-report-evidence-pack-api"


def test_mutation_api_rejects_sensitive_causation_without_event_write() -> None:
    reset_idea_repository_for_tests()
    client = TestClient(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="lineage-sensitive-seed-001")
    headers = lifecycle_headers("lineage-sensitive-causation-001")
    headers["X-Causation-Id"] = "bearer-secret-token"

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert not _events("idea.lifecycle.transitioned.v1")


def test_mutation_openapi_exposes_optional_causation_header() -> None:
    mutation_paths = (
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        "/api/v1/idea-candidates/{candidateId}/lifecycle-transitions",
        "/api/v1/idea-candidates/{candidateId}/review-actions",
        "/api/v1/idea-candidates/{candidateId}/feedback",
        "/api/v1/idea-candidates/{candidateId}/conversion-intents",
        "/api/v1/conversion-intents/{conversionIntentId}/outcomes",
        "/api/v1/conversion-intents/{conversionIntentId}/report-evidence-packs",
    )

    for path in mutation_paths:
        parameters = app.openapi()["paths"][path]["post"]["parameters"]
        causation = [parameter for parameter in parameters if parameter["name"] == "X-Causation-Id"]
        assert len(causation) == 1
        assert causation[0]["in"] == "header"
        assert causation[0]["required"] is False


def _events(event_type: str) -> tuple[OutboxEventRecord, ...]:
    return tuple(
        event
        for event in get_idea_repository().snapshot().outbox_events.values()
        if event.event_type == event_type
    )


def _latest_event(event_type: str) -> OutboxEventRecord:
    events = _events(event_type)
    assert events, f"missing outbox event: {event_type}"
    return events[-1]
