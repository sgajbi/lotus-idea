from __future__ import annotations

import pytest

import app.api.opportunity_effectiveness as opportunity_effectiveness_api
from app.domain import InMemoryIdeaRepository
from app.main import app
from app.runtime.repository_state import reset_idea_repository_for_tests
from tests.support.http import managed_test_client
from tests.support.opportunity_effectiveness_fixture import (
    FIXTURE_EVALUATED_AT,
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    golden_effectiveness_snapshot,
)


@pytest.fixture(autouse=True)
def reset_repository() -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository(golden_effectiveness_snapshot()))


def test_opportunity_effectiveness_api_returns_bounded_privacy_safe_funnel() -> None:
    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schemaVersion"] == "lotus-idea.opportunity-effectiveness.v1"
    assert payload["methodologyPolicyVersion"] == "idea-opportunity-effectiveness-v1"
    assert payload["counts"]["generatedOpportunityCount"] == 3
    assert payload["counts"]["reviewedOpportunityCount"] == 3
    assert payload["rates"]["approval"] == {
        "numerator": 1,
        "denominator": 3,
        "value": "0.333333",
        "zeroDenominatorBehavior": "null",
    }
    assert payload["presentation"] == {
        "measurementStatus": "unavailable_no_governed_presentation_receipts",
        "presentedOpportunityCount": None,
        "topRankedAcceptedOpportunityCount": None,
    }
    assert payload["privacyBoundary"]["containsRawCandidateIdentifier"] is False
    assert payload["certificationStatus"] == "not_certified"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["productionMutationAuthority"] == "none_read_only_effectiveness_evidence"
    for prohibited in (
        "tenant-a",
        "client-001",
        "portfolio-001",
        "idea-approved-001",
        "advisor-sensitive-subject",
        "downstream-sensitive-reference",
    ):
        assert prohibited not in response.text


def test_opportunity_effectiveness_api_requires_capability_role_and_exact_tenant_scope() -> None:
    client = managed_test_client(app)

    missing_capability = client.get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(capabilities="idea.review-queue.read"),
    )
    wrong_role = client.get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(roles="advisor"),
    )
    wrong_tenant = client.get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(tenant_ids="tenant-b"),
    )

    for response in (missing_capability, wrong_role, wrong_tenant):
        assert response.status_code == 403
        assert response.json()["code"] == "permission_denied"


def test_opportunity_effectiveness_api_emits_bounded_operation_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr(
        opportunity_effectiveness_api,
        "emit_operation_event",
        lambda event: events.append(event.log_fields()),
    )

    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 200
    assert events == [
        {
            "operation": "opportunity_effectiveness_read",
            "outcome": "accepted",
            "source_authority": "lotus-idea",
            "supportability_status": "not_certified",
            "durable_storage_backed": False,
            "supported_feature_promoted": False,
            "generated_opportunity_count_bucket": "1-10",
        }
    ]


@pytest.mark.parametrize(
    "override",
    (
        {"windowStartUtc": "2026-06-21T08:00:00"},
        {"windowEndUtc": "2026-06-21T07:59:59Z"},
        {"evaluatedAtUtc": "2026-06-21T11:59:59Z"},
        {"maxOpportunities": 0},
        {"maxOpportunities": 10_001},
    ),
)
def test_opportunity_effectiveness_api_rejects_invalid_windows_and_bounds(
    override: dict[str, str | int],
) -> None:
    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params={**_params(), **override},
        headers=_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"


def _params() -> dict[str, str | int]:
    return {
        "tenantId": "tenant-a",
        "windowStartUtc": FIXTURE_WINDOW_START.isoformat(),
        "windowEndUtc": FIXTURE_WINDOW_END.isoformat(),
        "evaluatedAtUtc": FIXTURE_EVALUATED_AT.isoformat(),
        "maxOpportunities": 100,
    }


def _headers(
    *,
    roles: str = "operator",
    capabilities: str = "idea.opportunity-effectiveness.read",
    tenant_ids: str = "tenant-a",
) -> dict[str, str]:
    return {
        "X-Caller-Subject": "platform-operator",
        "X-Caller-Roles": roles,
        "X-Caller-Capabilities": capabilities,
        "X-Caller-Tenant-Ids": tenant_ids,
    }
