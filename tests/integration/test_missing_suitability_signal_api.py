from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from tests.support.http import managed_test_client

import app.api.missing_suitability_signals as missing_suitability_api
from app.ports.advise_sources import (
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceUnavailable,
)
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    AdvisePolicyEvaluationSourceRuntime,
    AdvisePolicyEvaluationSourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
EVALUATION_ID = "pev_001"


class RecordingAdvisePolicyEvaluationSource:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.close_count = 0
        self.seen_request: AdvisePolicyEvaluationEvidenceRequest | None = None

    def fetch_policy_evaluation_evidence(
        self,
        request: AdvisePolicyEvaluationEvidenceRequest,
    ) -> AdvisePolicyEvaluationEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return _advise_policy_evidence()

    def close(self) -> None:
        self.close_count += 1


def test_missing_suitability_signal_api_returns_compliance_review_candidate() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate",
        json=missing_suitability_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "missing_suitability_context"
    assert payload["reasonCodes"] == ["suitability_context_missing", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-advise"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "compliance_review_required"
    assert payload["candidate"]["sourceRefs"][0]["productId"] == (
        "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    )
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_missing_suitability_signal_api_reports_uncertified_publication_blocker() -> None:
    client = managed_test_client(app)
    payload = missing_suitability_payload()
    payload["clientReadyPublication"] = "READY"

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "missing_suitability_context",
        "reasonCodes": ["review_required"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-advise",
        "supportedFeaturePromoted": False,
    }


def test_missing_suitability_signal_api_rejects_wrong_source_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = missing_suitability_payload()
    payload["policyRef"] = {
        **payload["policyRef"],
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "sourceSystem": "lotus-core",
        "route": "/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot",
        "contentHash": "sha256:wrong-missing-suitability-source",
    }
    events: list[tuple[str, str, str, str | None]] = []

    def capture(operation: Any, outcome: Any, **kwargs: Any) -> None:
        events.append(
            (
                operation.value,
                outcome.value,
                kwargs["source_authority"],
                kwargs.get("error_code"),
            )
        )

    monkeypatch.setattr(missing_suitability_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "PortfolioStateSnapshot" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-advise",
            "source_ref_contract_mismatch",
        )
    ]


def test_missing_suitability_signal_api_requires_signal_permission() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate",
        json=missing_suitability_payload(),
        headers={
            "X-Caller-Subject": "viewer-001",
            "X-Caller-Roles": "viewer",
            "X-Caller-Capabilities": "idea.review.queue.read",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals.",
    }


def test_missing_suitability_signal_from_source_api_returns_compliance_review_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    advise_source = RecordingAdvisePolicyEvaluationSource()
    monkeypatch.setattr(
        missing_suitability_api,
        "_build_advise_policy_evaluation_source_runtime_from_environment",
        lambda: AdvisePolicyEvaluationSourceRuntime(
            advise_source=advise_source,
            advise_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate-from-source",
        json=missing_suitability_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "missing_suitability_context"
    assert payload["sourceAuthority"] == "lotus-advise"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "compliance_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "missing-suitability-context-review-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-advise:AdvisoryPolicyEvaluationRecord:v1"
    }
    assert advise_source.seen_request == AdvisePolicyEvaluationEvidenceRequest(
        evaluation_id=EVALUATION_ID,
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-advise-missing-suitability-source-api",
        trace_id="trace-advise-missing-suitability-source-api",
    )
    assert advise_source.close_count == 1


def test_missing_suitability_signal_from_source_blocks_when_runtime_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    monkeypatch.setattr(
        missing_suitability_api,
        "_build_advise_policy_evaluation_source_runtime_from_environment",
        lambda: AdvisePolicyEvaluationSourceRuntimeBlocker("lotus_advise_base_url_not_configured"),
    )

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate-from-source",
        json=missing_suitability_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": (
            "Advise source runtime is not configured for missing-suitability source evaluation."
        ),
    }
    assert EVALUATION_ID not in response.text


def test_missing_suitability_signal_from_source_checks_scope_before_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = managed_test_client(app)

    def fail_if_called() -> AdvisePolicyEvaluationSourceRuntimeBlocker:
        raise AssertionError("runtime must not be built when caller scope is denied")

    monkeypatch.setattr(
        missing_suitability_api,
        "_build_advise_policy_evaluation_source_runtime_from_environment",
        fail_if_called,
    )

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate-from-source",
        json=missing_suitability_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_SG_OTHER_002"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert EVALUATION_ID not in response.text
    assert "PB_SG_OTHER_002" not in response.text


def test_missing_suitability_signal_from_source_closes_runtime_on_source_blocker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    advise_source = RecordingAdvisePolicyEvaluationSource(
        error=AdviseSourceUnavailable(code="advise_policy_workflow_unavailable")
    )
    monkeypatch.setattr(
        missing_suitability_api,
        "_build_advise_policy_evaluation_source_runtime_from_environment",
        lambda: AdvisePolicyEvaluationSourceRuntime(
            advise_source=advise_source,
            advise_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/missing-suitability/evaluate-from-source",
        json=missing_suitability_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "missing_suitability_context",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_unavailable"],
        "candidate": None,
        "sourceAuthority": "lotus-advise",
        "supportedFeaturePromoted": False,
    }
    assert advise_source.close_count == 1


def evaluate_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
    }


def source_evaluation_headers(*, portfolio_ids: str = "PB_SG_GLOBAL_BAL_001") -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-advise-missing-suitability-source-api",
        "X-Trace-Id": "trace-advise-missing-suitability-source-api",
        "X-Caller-Tenant-Ids": "tenant-sg",
        "X-Caller-Book-Ids": "global-balanced",
        "X-Caller-Portfolio-Ids": portfolio_ids,
        "X-Caller-Client-Ids": "client-001",
    }


def missing_suitability_source_payload() -> dict[str, Any]:
    return {
        "evaluationId": EVALUATION_ID,
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "accessScope": {
            "tenantId": "tenant-sg",
            "bookId": "global-balanced",
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "clientId": "client-001",
        },
    }


def missing_suitability_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "policyRef": {
            "productId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "sourceSystem": "lotus-advise",
            "productVersion": "v1",
            "route": "/advisory/policy-evaluations/pev_001/workflow",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:missing-suitability-context-review",
            "dataQualityStatus": "quality_passed",
            "freshness": "current",
        },
        "evaluationStatus": "PENDING_REVIEW",
        "openRequirementCount": 2,
        "blockedRequirementCount": 0,
        "signOffStatus": "PENDING_REVIEW",
        "signOffBlockerCount": 1,
        "clientReadyPublication": "BLOCKED",
        "entitlementAllowed": True,
    }


def _advise_policy_evidence() -> AdvisePolicyEvaluationEvidence:
    return AdvisePolicyEvaluationEvidence(
        evaluation_status="PENDING_REVIEW",
        open_requirement_count=2,
        blocked_requirement_count=0,
        sign_off_status="PENDING_REVIEW",
        sign_off_blocker_count=1,
        client_ready_publication="BLOCKED",
        policy_ref=SourceRef(
            product_id="lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            source_system=SourceSystem.LOTUS_ADVISE,
            product_version="v1",
            route="/advisory/policy-evaluations/pev_001/workflow",
            as_of_date=AS_OF_DATE,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:missing-suitability-context-review",
            data_quality_status="quality_passed",
            freshness=EvidenceFreshness.CURRENT,
        ),
    )
