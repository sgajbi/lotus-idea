from __future__ import annotations

import pytest

from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.integration.test_candidate_evidence_replay_api import (
    persisted_candidate_id,
    replay_headers,
    replay_payload,
)
from tests.support.http import managed_test_client


@pytest.mark.parametrize(
    ("header_name", "header_value"),
    (
        ("X-Caller-Tenant-Ids", None),
        ("X-Caller-Book-Ids", None),
        ("X-Caller-Portfolio-Ids", None),
        ("X-Caller-Client-Ids", None),
        ("X-Caller-Tenant-Ids", "tenant-other"),
        ("X-Caller-Book-Ids", "book-other"),
        ("X-Caller-Portfolio-Ids", "PB_SG_OTHER_002"),
        ("X-Caller-Client-Ids", "client-other"),
    ),
)
def test_evidence_replay_api_denies_incomplete_or_mismatched_candidate_scope(
    header_name: str,
    header_value: str | None,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client, suffix="-scope", idempotency_key="seed-evidence-replay-scope-001"
    )
    headers = replay_headers()
    if header_value is None:
        headers.pop(header_name)
    else:
        headers[header_name] = header_value

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-scope"),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert candidate_id not in response.text
    assert "evidencePacketId" not in response.text


def test_evidence_replay_api_refuses_operator_role_without_any_scope() -> None:
    """A generic operator role grants no estate-wide read; scope is required, not inferred."""

    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client, suffix="-noscope", idempotency_key="seed-evidence-replay-scope-002"
    )
    headers = replay_headers()
    for header_name in (
        "X-Caller-Tenant-Ids",
        "X-Caller-Book-Ids",
        "X-Caller-Portfolio-Ids",
        "X-Caller-Client-Ids",
    ):
        headers.pop(header_name)

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-noscope"),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert candidate_id not in response.text


def test_evidence_replay_api_accepts_plural_and_reordered_grants() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client, suffix="-plural", idempotency_key="seed-evidence-replay-scope-003"
    )

    first = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-plural"),
        headers=replay_headers(
            tenant_ids="tenant-other,tenant-a",
            book_ids="book-other,book-advisor-001",
            portfolio_ids="PB_SG_OTHER_002,PB_SG_GLOBAL_BAL_001",
            client_ids="client-other,client-001",
        ),
    )
    reordered = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-plural"),
        headers=replay_headers(
            tenant_ids="tenant-a,tenant-other",
            book_ids="book-advisor-001,book-other",
            portfolio_ids="PB_SG_GLOBAL_BAL_001,PB_SG_OTHER_002",
            client_ids="client-001,client-other",
        ),
    )

    assert first.status_code == 200
    assert reordered.status_code == 200
    assert first.json()["replayStatus"] == "matched"
    assert reordered.json() == first.json()


def test_evidence_replay_api_rejects_malformed_scope_before_any_read() -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client, suffix="-malformed", idempotency_key="seed-evidence-replay-scope-004"
    )
    headers = replay_headers()
    headers["X-Caller-Book-Ids"] = "book-advisor-001,,book-other"

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/evidence-replay",
        json=replay_payload(suffix="-malformed"),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert candidate_id not in response.text
