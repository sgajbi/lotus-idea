from __future__ import annotations

from typing import Any, NoReturn, Protocol

import pytest
from tests.support.http import managed_test_client

from app.api import candidate_lifecycle as candidate_lifecycle_api
from app.api import conversion_governance as conversion_governance_api
from app.api import report_evidence as report_evidence_api
from app.api import review_workflow as review_workflow_api
from app.application.persisted_action_evidence import PersistedActionEvidenceUnavailable
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
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
    review_headers,
    report_evidence_pack_headers,
    report_evidence_pack_payload,
    suppress_review_payload,
)


def _raise_unavailable(*args: Any, **kwargs: Any) -> NoReturn:
    raise PersistedActionEvidenceUnavailable("sensitive persistence detail")


class _HttpResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    def json(self) -> Any: ...


def _assert_product_safe_degraded_response(response: _HttpResponse) -> None:
    assert response.status_code == 503
    assert response.json()["code"] == "service_recovery_degraded"
    assert "sensitive persistence detail" not in response.text


def test_review_action_api_fails_safely_when_persisted_evidence_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-review-evidence-001")
    monkeypatch.setattr(
        review_workflow_api,
        "apply_review_action_to_repository",
        _raise_unavailable,
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/review-actions",
        json=suppress_review_payload(),
        headers=review_headers("review-action-api-missing-evidence-001"),
    )

    _assert_product_safe_degraded_response(response)


def test_lifecycle_api_fails_safely_when_persisted_evidence_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-lifecycle-evidence-001")
    monkeypatch.setattr(
        candidate_lifecycle_api,
        "apply_candidate_lifecycle_transition_to_repository",
        _raise_unavailable,
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/lifecycle-transitions",
        json=lifecycle_payload(),
        headers=lifecycle_headers("lifecycle-api-missing-evidence-001"),
    )

    _assert_product_safe_degraded_response(response)


def test_feedback_api_fails_safely_when_persisted_evidence_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-feedback-evidence-001")
    monkeypatch.setattr(
        review_workflow_api,
        "record_feedback_to_repository",
        _raise_unavailable,
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/feedback",
        json=feedback_payload(),
        headers=feedback_headers("feedback-api-missing-evidence-001"),
    )

    _assert_product_safe_degraded_response(response)


def test_conversion_intent_api_fails_safely_when_persisted_evidence_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-conversion-evidence-001")
    approve_candidate_for_conversion(client, candidate_id)
    monkeypatch.setattr(
        conversion_governance_api,
        "request_conversion_intent_to_repository",
        _raise_unavailable,
    )

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(),
        headers=conversion_intent_headers("conversion-intent-api-missing-evidence-001"),
    )

    _assert_product_safe_degraded_response(response)


def test_conversion_outcome_api_fails_safely_when_persisted_evidence_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-outcome-evidence-001")
    approve_candidate_for_conversion(client, candidate_id)
    conversion_intent_id = "conversion-outcome-evidence-001"
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=conversion_intent_id),
        headers=conversion_intent_headers("conversion-outcome-evidence-intent-001"),
    )
    assert intent.status_code == 200
    monkeypatch.setattr(
        conversion_governance_api,
        "record_conversion_outcome_to_repository",
        _raise_unavailable,
    )

    response = client.post(
        f"/api/v1/conversion-intents/{conversion_intent_id}/outcomes",
        json=conversion_outcome_payload(
            conversion_outcome_id="conversion-outcome-evidence-result-001"
        ),
        headers=conversion_outcome_headers("conversion-outcome-evidence-request-001"),
    )

    _assert_product_safe_degraded_response(response)


def test_report_evidence_api_fails_safely_when_persisted_evidence_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(client, idempotency_key="seed-report-evidence-001")
    approve_candidate_for_conversion(client, candidate_id)
    conversion_intent_id = "conversion-report-evidence-001"
    intent = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/conversion-intents",
        json=conversion_intent_payload(conversion_intent_id=conversion_intent_id),
        headers=conversion_intent_headers("conversion-report-evidence-intent-001"),
    )
    assert intent.status_code == 200
    monkeypatch.setattr(
        report_evidence_api,
        "request_report_evidence_pack_to_repository",
        _raise_unavailable,
    )

    response = client.post(
        f"/api/v1/conversion-intents/{conversion_intent_id}/report-evidence-packs",
        json=report_evidence_pack_payload(
            report_evidence_pack_id="report-evidence-persisted-result-001"
        ),
        headers=report_evidence_pack_headers("report-evidence-persisted-request-001"),
    )

    _assert_product_safe_degraded_response(response)
