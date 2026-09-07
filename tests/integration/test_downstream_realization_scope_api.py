from __future__ import annotations

import pytest
from tests.support.http import managed_test_client

import app.api.downstream_realization as downstream_realization_api
from app.main import app
from app.ports.downstream_realization import DownstreamRealizationOutcome
from app.runtime.downstream_realization_state import ConversionRealizationClients
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from tests.integration.test_downstream_realization_api import (
    CapturingConversionClient,
    downstream_submission_headers,
    record_conversion_intent,
    seed_approved_candidate,
)


def test_downstream_submission_api_requires_complete_entitlement_scope() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/conversion-intents/missing-conversion/downstream-submissions",
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Capabilities": "idea.downstream-realization.submit",
            "X-Correlation-Id": "corr-downstream-scope-denied-api",
            "Idempotency-Key": "downstream-submit-scope-denied-api-001",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


@pytest.mark.parametrize(
    ("path", "caller_capability", "idempotency_key"),
    [
        (
            "/api/v1/conversion-intents/missing-conversion/downstream-submissions",
            "idea.conversion.intent.record",
            "downstream-submit-denied-api-001",
        ),
        (
            "/api/v1/report-evidence-packs/missing-pack/downstream-submissions",
            "idea.report-evidence-pack.request",
            "report-downstream-submit-denied-api-001",
        ),
    ],
)
def test_downstream_submission_api_requires_submission_capability(
    path: str,
    caller_capability: str,
    idempotency_key: str,
) -> None:
    client = managed_test_client(app)

    response = client.post(
        path,
        headers={
            "X-Caller-Subject": "advisor-001",
            "X-Caller-Capabilities": caller_capability,
            "X-Correlation-Id": "corr-downstream-denied-api",
            "Idempotency-Key": idempotency_key,
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_conversion_downstream_submission_api_rejects_cross_portfolio_scope_before_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    candidate_id = seed_approved_candidate(
        client,
        suffix="-cross-portfolio-denied",
        idempotency_prefix="cross-portfolio-denied",
    )
    record_conversion_intent(
        client,
        candidate_id,
        conversion_intent_id="conversion-cross-portfolio-denied-api-001",
        target="advise_proposal",
        idempotency_key="conversion-cross-portfolio-denied-api-001",
    )

    response = client.post(
        "/api/v1/conversion-intents/conversion-cross-portfolio-denied-api-001/downstream-submissions",
        headers=downstream_submission_headers(
            "downstream-submit-cross-portfolio-denied-api-001",
            portfolio_id="PB_SG_ALT_BAL_002",
        ),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert advise_client.submitted == ()
    assert manage_client.submitted == ()
    assert (
        get_idea_repository().downstream_submission_by_idempotency_key(
            "tenant-private-bank-sg", "downstream-submit-cross-portfolio-denied-api-001"
        )
        is None
    )


def test_conversion_downstream_submission_api_scopes_idempotency_by_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests()
    client = managed_test_client(app)
    advise_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    manage_client = CapturingConversionClient(DownstreamRealizationOutcome.accepted_by_downstream())
    monkeypatch.setattr(
        downstream_realization_api,
        "get_conversion_realization_clients",
        lambda: ConversionRealizationClients(advise_client, manage_client),
    )
    first_candidate_id = seed_approved_candidate(
        client,
        suffix="-tenant-a",
        idempotency_prefix="tenant-a",
        tenant_id="tenant-private-bank-sg",
    )
    second_candidate_id = seed_approved_candidate(
        client,
        suffix="-tenant-b",
        idempotency_prefix="tenant-b",
        tenant_id="tenant-private-bank-hk",
    )
    record_conversion_intent(
        client,
        first_candidate_id,
        conversion_intent_id="conversion-tenant-a-001",
        target="advise_proposal",
        idempotency_key="conversion-tenant-a-001",
        tenant_id="tenant-private-bank-sg",
    )
    record_conversion_intent(
        client,
        second_candidate_id,
        conversion_intent_id="conversion-tenant-b-001",
        target="advise_proposal",
        idempotency_key="conversion-tenant-b-001",
        tenant_id="tenant-private-bank-hk",
    )
    shared_key = "downstream-submit-shared-tenant-key"

    first = client.post(
        "/api/v1/conversion-intents/conversion-tenant-a-001/downstream-submissions",
        headers=downstream_submission_headers(
            shared_key,
            tenant_id="tenant-private-bank-sg",
        ),
    )
    second = client.post(
        "/api/v1/conversion-intents/conversion-tenant-b-001/downstream-submissions",
        headers=downstream_submission_headers(
            shared_key,
            tenant_id="tenant-private-bank-hk",
        ),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["downstreamSubmission"]["idempotencyReplayed"] is False
    assert second.json()["downstreamSubmission"]["idempotencyReplayed"] is False
    assert (
        first.json()["downstreamSubmission"]["supportReference"]
        != second.json()["downstreamSubmission"]["supportReference"]
    )
    assert len(advise_client.submitted) == 2
    repository = get_idea_repository()
    assert (
        repository.downstream_submission_by_idempotency_key("tenant-private-bank-sg", shared_key)
        is not None
    )
    assert (
        repository.downstream_submission_by_idempotency_key("tenant-private-bank-hk", shared_key)
        is not None
    )
    assert manage_client.submitted == ()
