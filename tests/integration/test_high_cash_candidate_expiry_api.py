from __future__ import annotations

from typing import Any

from app.domain import IdeaLifecycleStatus
from app.main import app
from app.runtime.repository_state import (
    get_idea_repository,
    reset_idea_repository_for_tests,
)
from tests.integration.postgres_runtime_support import (
    high_cash_payload,
    persistence_headers,
)
from tests.support.http import managed_test_client


def _payload(*, cash_weight: str = "0.18", freshness: str = "current") -> dict[str, Any]:
    payload = high_cash_payload()
    payload["sourceReportedCashWeight"] = cash_weight
    for source_ref in payload["sourceEvidence"].values():
        source_ref["freshness"] = freshness
    return payload


def test_high_cash_persist_api_skips_not_eligible_evaluation_without_candidate() -> None:
    reset_idea_repository_for_tests()

    response = managed_test_client(app).post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_payload(cash_weight="0.05"),
        headers=persistence_headers("persist-high-cash-api-not-eligible"),
    )

    assert response.status_code == 200
    assert response.json()["evaluation"]["outcome"] == "not_eligible"
    assert response.json()["evaluation"]["candidate"] is None
    assert response.json()["persistence"] is None
    assert response.json()["supportedFeaturePromoted"] is False
    assert get_idea_repository().snapshot().candidate_records == {}


def test_high_cash_persist_api_expires_candidate_after_authoritative_resolution() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    created = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_payload(),
        headers=persistence_headers("persist-high-cash-api-expiry-created"),
    )
    candidate_id = created.json()["persistence"]["candidateId"]

    resolved = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_payload(cash_weight="0.10"),
        headers=persistence_headers("persist-high-cash-api-expiry-resolved"),
    )

    assert (created.status_code, resolved.status_code) == (200, 200)
    assert resolved.json()["evaluation"]["outcome"] == "not_eligible"
    assert resolved.json()["persistence"] is None
    record = get_idea_repository().snapshot().candidate_records[candidate_id]
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.EXPIRED
    assert len(record.lifecycle_history) == 1
    assert record.audit_events[-1].attributes["reason_codes"] == (
        "opportunity_no_longer_eligible,below_materiality"
    )


def test_high_cash_persist_api_preserves_candidate_when_reevaluation_is_blocked() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    created = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_payload(),
        headers=persistence_headers("persist-high-cash-api-blocked-created"),
    )
    candidate_id = created.json()["persistence"]["candidateId"]

    blocked = client.post(
        "/api/v1/idea-signals/high-cash/evaluate-and-persist",
        json=_payload(freshness="stale"),
        headers=persistence_headers("persist-high-cash-api-blocked-reevaluation"),
    )

    assert (created.status_code, blocked.status_code) == (200, 200)
    assert blocked.json()["evaluation"]["outcome"] == "blocked"
    record = get_idea_repository().snapshot().candidate_records[candidate_id]
    assert record.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert record.lifecycle_history == ()
