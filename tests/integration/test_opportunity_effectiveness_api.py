from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

import app.api.opportunity_effectiveness as opportunity_effectiveness_api
from app.domain import InMemoryIdeaRepository
from app.main import app
from app.ports.idea_repository import (
    OpportunityEffectivenessRepositorySummary,
    OpportunityFamilyEffectivenessRepositorySummary,
)
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
    assert payload["methodologyPolicyVersion"] == "idea-opportunity-effectiveness-v3"
    assert payload["counts"]["generatedOpportunityCount"] == 3
    assert payload["counts"]["reviewedOpportunityCount"] == 3
    assert payload["rates"]["approval"] == {
        "numerator": 1,
        "denominator": 3,
        "value": "0.333333",
        "zeroDenominatorBehavior": "null",
    }
    assert payload["presentation"] == {
        "measurementStatus": "unavailable_consumer_certification_pending",
        "presentedOpportunityCount": None,
        "topRankedPresentedOpportunityCount": None,
        "topRankedAcceptedOpportunityCount": None,
        "presentationRate": None,
        "topRankedAcceptanceRate": None,
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


def test_opportunity_effectiveness_api_uses_bounded_durable_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _ProjectionRepository(_summary(generated_opportunity_count=2))
    monkeypatch.setattr(opportunity_effectiveness_api, "get_idea_repository", lambda: repository)

    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 200
    assert response.json()["counts"]["generatedOpportunityCount"] == 2
    assert response.json()["familyEffectiveness"][0]["counts"]["presentedOpportunityCount"] is None
    assert response.json()["familyEffectiveness"][0]["rates"]["presentation"] is None
    assert repository.calls == [
        {
            "tenant_id": "tenant-a",
            "window_start_utc": FIXTURE_WINDOW_START,
            "window_end_utc": FIXTURE_WINDOW_END,
            "evaluated_at_utc": FIXTURE_EVALUATED_AT,
            "max_opportunities": 100,
        }
    ]


def test_opportunity_effectiveness_api_returns_stored_presentation_measurement_without_certifying(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _ProjectionRepository(
        _summary(
            generated_opportunity_count=3,
            presented_opportunity_count=2,
            top_ranked_presented_opportunity_count=2,
            top_ranked_accepted_opportunity_count=1,
        )
    )
    monkeypatch.setattr(opportunity_effectiveness_api, "get_idea_repository", lambda: repository)

    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 200
    assert response.json()["presentation"] == {
        "measurementStatus": "stored_consumer_certification_pending",
        "presentedOpportunityCount": 2,
        "topRankedPresentedOpportunityCount": 2,
        "topRankedAcceptedOpportunityCount": 1,
        "presentationRate": {
            "numerator": 2,
            "denominator": 3,
            "value": "0.666667",
            "zeroDenominatorBehavior": "null",
        },
        "topRankedAcceptanceRate": {
            "numerator": 1,
            "denominator": 2,
            "value": "0.500000",
            "zeroDenominatorBehavior": "null",
        },
    }
    assert response.json()["familyEffectiveness"][0]["counts"]["presentedOpportunityCount"] == 2
    assert response.json()["familyEffectiveness"][0]["rates"]["presentation"] == {
        "numerator": 2,
        "denominator": 3,
        "value": "0.666667",
        "zeroDenominatorBehavior": "null",
    }
    assert response.json()["certificationStatus"] == "not_certified"
    assert response.json()["supportedFeaturePromoted"] is False


@pytest.mark.parametrize(
    "summary_overrides",
    (
        {"generated_opportunity_count": -1},
        {"detection_to_review_seconds": (Decimal("-1"),)},
        {
            "presented_opportunity_count": 1,
            "top_ranked_presented_opportunity_count": 1,
            "top_ranked_accepted_opportunity_count": 2,
        },
        {
            "presented_opportunity_count": 1,
            "top_ranked_presented_opportunity_count": 2,
        },
        {"presented_opportunity_count": 1},
    ),
)
def test_opportunity_effectiveness_api_fails_closed_on_corrupt_projection_facts(
    monkeypatch: pytest.MonkeyPatch,
    summary_overrides: dict[str, Any],
) -> None:
    monkeypatch.setattr(
        opportunity_effectiveness_api,
        "get_idea_repository",
        lambda: _ProjectionRepository(_summary(**summary_overrides)),
    )

    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "opportunity_effectiveness_unavailable"


@pytest.mark.parametrize(
    "corrupt_family",
    (
        lambda family: replace(family, generated_opportunity_count=2),
        lambda family: replace(family, presented_opportunity_count=2),
        lambda family: replace(family, approved_opportunity_count=2),
        lambda family: replace(family, duplicate_suppressed_opportunity_count=1),
        lambda family: replace(family, conversion_intent_count=0),
        lambda family: replace(family, downstream_accepted_count=0),
        lambda family: replace(family, feedback_opportunity_count=0),
    ),
)
def test_opportunity_effectiveness_api_fails_closed_on_corrupt_family_funnel(
    monkeypatch: pytest.MonkeyPatch,
    corrupt_family: Callable[
        [OpportunityFamilyEffectivenessRepositorySummary],
        OpportunityFamilyEffectivenessRepositorySummary,
    ],
) -> None:
    summary = _summary(
        generated_opportunity_count=1,
        reviewed_opportunity_count=1,
        feedback_opportunity_count=1,
        conversion_opportunity_count=1,
        conversion_intent_count=1,
        latest_review_action_counts={"approve_for_conversion": 1},
        current_downstream_outcome_counts={"accepted": 1},
    )
    family = summary.family_effectiveness[0]
    corrupt_summary = replace(
        summary,
        family_effectiveness=(corrupt_family(family),),
    )
    monkeypatch.setattr(
        opportunity_effectiveness_api,
        "get_idea_repository",
        lambda: _ProjectionRepository(corrupt_summary),
    )

    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "opportunity_effectiveness_unavailable"


def test_opportunity_effectiveness_api_fails_closed_when_family_cohort_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary = replace(
        _summary(generated_opportunity_count=1),
        family_effectiveness=(),
    )
    monkeypatch.setattr(
        opportunity_effectiveness_api,
        "get_idea_repository",
        lambda: _ProjectionRepository(summary),
    )

    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "opportunity_effectiveness_unavailable"


def test_opportunity_effectiveness_api_fails_closed_on_projection_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        opportunity_effectiveness_api,
        "get_idea_repository",
        lambda: _ProjectionRepository(RuntimeError("database unavailable")),
    )

    response = managed_test_client(app).get(
        "/api/v1/operations/opportunity-effectiveness",
        params=_params(),
        headers=_headers(),
    )

    assert response.status_code == 503
    assert response.json()["code"] == "opportunity_effectiveness_unavailable"


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


class _ProjectionRepository:
    durable_storage_backed = True

    def __init__(
        self,
        result: OpportunityEffectivenessRepositorySummary | RuntimeError,
    ) -> None:
        self._result = result
        self.calls: list[dict[str, object]] = []

    def opportunity_effectiveness_summary(
        self,
        *,
        tenant_id: str,
        window_start_utc: datetime,
        window_end_utc: datetime,
        evaluated_at_utc: datetime,
        max_opportunities: int,
    ) -> OpportunityEffectivenessRepositorySummary:
        self.calls.append(
            {
                "tenant_id": tenant_id,
                "window_start_utc": window_start_utc,
                "window_end_utc": window_end_utc,
                "evaluated_at_utc": evaluated_at_utc,
                "max_opportunities": max_opportunities,
            }
        )
        if isinstance(self._result, RuntimeError):
            raise self._result
        return self._result


def _summary(**overrides: Any) -> OpportunityEffectivenessRepositorySummary:
    values: dict[str, Any] = {
        "generated_opportunity_count": 0,
        "reviewed_opportunity_count": 0,
        "feedback_opportunity_count": 0,
        "conversion_opportunity_count": 0,
        "conversion_intent_count": 0,
        "stale_evidence_opportunity_count": 0,
        "unavailable_evidence_opportunity_count": 0,
        "unsupported_evidence_opportunity_count": 0,
        "suppressed_opportunity_count": 0,
        "duplicate_suppressed_opportunity_count": 0,
        "recurrent_opportunity_count": 0,
        "recurrent_detection_count": 0,
        "reconciled_submission_count": 0,
        "presented_opportunity_count": 0,
        "top_ranked_presented_opportunity_count": 0,
        "top_ranked_accepted_opportunity_count": 0,
        "family_effectiveness": (),
        "family_counts": {},
        "score_band_counts": {},
        "latest_review_action_counts": {},
        "feedback_reason_counts": {},
        "current_downstream_outcome_counts": {},
        "downstream_submission_posture_counts": {},
        "detection_to_review_seconds": (),
        "approval_to_conversion_seconds": (),
    }
    values.update(overrides)
    generated_count = values["generated_opportunity_count"]
    if isinstance(generated_count, int) and generated_count > 0:
        values["family_counts"] = {"high_cash": generated_count}
        values["score_band_counts"] = {"unranked": generated_count}
        values["family_effectiveness"] = (
            OpportunityFamilyEffectivenessRepositorySummary(
                family="high_cash",
                generated_opportunity_count=generated_count,
                presented_opportunity_count=values["presented_opportunity_count"],
                reviewed_opportunity_count=values["reviewed_opportunity_count"],
                approved_opportunity_count=values["latest_review_action_counts"].get(
                    "approve_for_conversion", 0
                ),
                rejected_opportunity_count=values["latest_review_action_counts"].get("reject", 0),
                suppressed_opportunity_count=values["suppressed_opportunity_count"],
                duplicate_suppressed_opportunity_count=values[
                    "duplicate_suppressed_opportunity_count"
                ],
                feedback_opportunity_count=values["feedback_opportunity_count"],
                conversion_opportunity_count=values["conversion_opportunity_count"],
                conversion_intent_count=values["conversion_intent_count"],
                downstream_accepted_count=values["current_downstream_outcome_counts"].get(
                    "accepted", 0
                )
                + values["current_downstream_outcome_counts"].get("completed", 0),
                downstream_rejected_count=values["current_downstream_outcome_counts"].get(
                    "rejected", 0
                ),
                downstream_uncertain_count=values["current_downstream_outcome_counts"].get(
                    "not_reported", 0
                )
                + values["current_downstream_outcome_counts"].get("requested", 0),
            ),
        )
    return OpportunityEffectivenessRepositorySummary(**values)
