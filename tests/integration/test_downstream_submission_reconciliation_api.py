from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.domain import (
    DownstreamSubmissionPosture,
    InMemoryIdeaRepository,
)
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.unit.downstream_submission_helpers import build_downstream_submission_claim


SUBMITTED_AT = datetime(2026, 7, 10, 8, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def reset_repository_provider() -> Iterator[None]:
    reset_idea_repository_for_tests()
    yield
    reset_idea_repository_for_tests()


def test_operator_can_inspect_source_safe_reconciliation_queue() -> None:
    repository = _repository_with_uncertain_submission()
    reset_idea_repository_for_tests(repository=repository)
    client = TestClient(app)

    denied = client.get("/api/v1/downstream-submissions/reconciliation")
    response = client.get(
        "/api/v1/downstream-submissions/reconciliation",
        headers=_headers("idea.downstream-reconciliation.read"),
    )

    assert denied.status_code == 403
    assert response.status_code == 200
    payload = response.json()
    assert payload["returnedCount"] == 1
    item = payload["items"][0]
    assert item["supportReference"].startswith("downstream-submission-")
    assert item["submissionPosture"] == "reconciliation_required"
    assert item["downstreamFailureReason"] == "downstream_timeout"
    assert item["reconciliationEligible"] is True
    assert "secret-idempotency-key" not in response.text
    assert "conversion-sensitive" not in response.text
    assert "client" not in response.text.lower()
    assert "portfolio" not in response.text.lower()


def test_operator_reconciliation_is_replay_safe_and_conflict_aware() -> None:
    repository = _repository_with_uncertain_submission()
    support_reference = repository.downstream_submissions_requiring_reconciliation()[
        0
    ].support_reference
    reset_idea_repository_for_tests(repository=repository)
    client = TestClient(app)
    headers = _headers(
        "idea.downstream-reconciliation.resolve",
        idempotency_key="CHG-334-API-001",
    )
    request = {
        "resolution": "accepted_by_downstream",
        "reason": "downstream_receipt_verified",
        "changeReference": "CHG-334-API-001",
    }

    accepted = client.post(
        f"/api/v1/downstream-submissions/reconciliation/{support_reference}",
        headers=headers,
        json=request,
    )
    replayed = client.post(
        f"/api/v1/downstream-submissions/reconciliation/{support_reference}",
        headers=headers,
        json=request,
    )
    conflict = client.post(
        f"/api/v1/downstream-submissions/reconciliation/{support_reference}",
        headers=headers,
        json={
            **request,
            "resolution": "rejected_by_downstream",
            "reason": "downstream_receipt_rejected",
        },
    )

    assert accepted.status_code == 200
    assert accepted.json()["reconciliationStatus"] == "accepted"
    assert accepted.json()["submission"]["submissionPosture"] == "accepted_by_downstream"
    assert accepted.json()["submission"]["reconciliationEligible"] is False
    assert replayed.status_code == 200
    assert replayed.json()["reconciliationStatus"] == "replayed"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "downstream_submission_change_reference_conflict"
    assert "secret-idempotency-key" not in accepted.text
    assert "conversion-sensitive" not in accepted.text


def test_reconciliation_requires_matching_mutation_identity() -> None:
    repository = _repository_with_uncertain_submission()
    support_reference = repository.downstream_submissions_requiring_reconciliation()[
        0
    ].support_reference
    reset_idea_repository_for_tests(repository=repository)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/downstream-submissions/reconciliation/{support_reference}",
        headers=_headers(
            "idea.downstream-reconciliation.resolve",
            idempotency_key="CHG-334-API-DIFFERENT",
        ),
        json={
            "resolution": "quarantined",
            "reason": "downstream_receipt_unverifiable",
            "changeReference": "CHG-334-API-002",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert repository.downstream_submissions_requiring_reconciliation()


def _repository_with_uncertain_submission() -> InMemoryIdeaRepository:
    repository = InMemoryIdeaRepository()
    claim = build_downstream_submission_claim(
        idempotency_key="secret-idempotency-key",
        request_fingerprint="sha256:reconciliation-api-test",
        resource_id="conversion-sensitive",
        submitted_at_utc=SUBMITTED_AT,
    )
    repository.claim_downstream_submission(claim)
    repository.finalize_downstream_submission(
        idempotency_key=claim.idempotency_key,
        lease_owner=claim.lease_owner or "",
        lease_attempt_id=claim.lease_attempt_id or "",
        posture=DownstreamSubmissionPosture.RECONCILIATION_REQUIRED,
        finalized_at_utc=SUBMITTED_AT + timedelta(minutes=1),
        failure_reason="downstream_timeout",
    )
    return repository


def _headers(capability: str, *, idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": "operator",
        "X-Caller-Capabilities": capability,
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers
