from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from tests.support.http import ManagedTestClient, managed_test_client

from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_review_workflow_api import (
    approve_candidate_for_conversion,
    approve_review_payload,
    conversion_intent_headers,
    conversion_intent_payload,
    persisted_candidate_id,
    review_headers,
    transition_candidate_to_review_ready,
)


def _review_request(client: ManagedTestClient, candidate_id: str) -> dict[str, Any]:
    transition_candidate_to_review_ready(client, candidate_id)
    return approve_review_payload(candidate_id)


def _conversion_request(client: ManagedTestClient, candidate_id: str) -> dict[str, Any]:
    approve_candidate_for_conversion(client, candidate_id)
    return conversion_intent_payload()


@pytest.mark.parametrize(
    ("route_suffix", "request_factory", "headers_factory"),
    (
        ("review-actions", _review_request, review_headers),
        ("conversion-intents", _conversion_request, conversion_intent_headers),
    ),
)
@pytest.mark.parametrize(
    ("field_name", "malformed_value"),
    (
        ("expectedEvidenceContentHash", "x"),
        ("expectedSourceRevisionVectorDigest", f"sha256:{'A' * 64}"),
    ),
)
def test_human_authority_api_rejects_malformed_evidence_identity_without_side_effects(
    route_suffix: str,
    request_factory: Callable[[ManagedTestClient, str], dict[str, Any]],
    headers_factory: Callable[[str], dict[str, str]],
    field_name: str,
    malformed_value: str,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    candidate_id = persisted_candidate_id(
        client,
        idempotency_key=f"seed-{route_suffix}-{field_name}",
    )
    payload = request_factory(client, candidate_id)
    payload[field_name] = malformed_value
    repository = get_idea_repository()
    before = repository.snapshot()

    response = client.post(
        f"/api/v1/idea-candidates/{candidate_id}/{route_suffix}",
        json=payload,
        headers=headers_factory(f"malformed-{route_suffix}-{field_name}"),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert repository.snapshot() == before
