from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from tests.support.http import managed_test_client
from pytest import MonkeyPatch, mark

import app.api.high_volatility_signals as high_volatility_api
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.risk_sources import (
    RiskSourceUnavailable,
    RiskVolatilityEvidence,
    RiskVolatilityEvidenceRequest,
)
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    RiskVolatilitySourceRuntime,
    RiskVolatilitySourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingRiskVolatilitySource:
    seen_request: RiskVolatilityEvidenceRequest | None = None
    evidence: RiskVolatilityEvidence | None = None
    error: Exception | None = None
    close_count: int = 0

    def fetch_volatility_evidence(
        self,
        request: RiskVolatilityEvidenceRequest,
    ) -> RiskVolatilityEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return self.evidence or _risk_volatility_evidence()

    def close(self) -> None:
        self.close_count += 1


def test_high_volatility_signal_api_returns_review_candidate() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate",
        json=high_volatility_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "high_volatility"
    assert payload["reasonCodes"] == ["volatility_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-risk"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "high-volatility-attention-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-risk:RiskMetricsReport:v1"
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_high_volatility_signal_api_reports_below_threshold_not_eligible() -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = high_volatility_payload()
    payload["sourceReportedVolatility"] = "8.50"

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "high_volatility",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }
    assert len(get_idea_repository().snapshot().candidate_records) == 0


def test_high_volatility_signal_api_reports_duplicate_suppressed() -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = high_volatility_payload()
    payload["duplicateOfCandidateId"] = "idea_high_volatility_existing"

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "suppressed",
        "family": "high_volatility",
        "reasonCodes": ["duplicate_suppressed"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }
    assert len(get_idea_repository().snapshot().candidate_records) == 0


def test_high_volatility_signal_api_reports_non_ready_source_blocker() -> None:
    client = managed_test_client(app)
    payload = high_volatility_payload()
    payload["riskSupportabilityState"] = "degraded"

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "high_volatility",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_high_volatility_signal_api_reports_stale_source_blocker() -> None:
    client = managed_test_client(app)
    payload = high_volatility_payload()
    payload["riskRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "high_volatility",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_high_volatility_signal_api_rejects_wrong_source_contract(
    monkeypatch: MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = high_volatility_payload()
    payload["riskRef"] = {
        **payload["riskRef"],
        "sourceSystem": "lotus-core",
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "route": "/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot",
        "contentHash": "sha256:wrong-high-volatility-source",
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

    monkeypatch.setattr(high_volatility_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate",
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
            "lotus-risk",
            "source_ref_contract_mismatch",
        )
    ]


def test_high_volatility_signal_api_requires_signal_permission() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate",
        json=high_volatility_payload(),
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


def test_high_volatility_signal_from_source_api_returns_review_candidate(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    risk_source = RecordingRiskVolatilitySource()
    monkeypatch.setattr(
        high_volatility_api,
        "_build_risk_volatility_source_runtime_from_environment",
        lambda: RiskVolatilitySourceRuntime(
            risk_source=risk_source,
            risk_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate-from-source",
        json=high_volatility_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "high_volatility"
    assert payload["sourceAuthority"] == "lotus-risk"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["scorePolicyVersion"] == "high-volatility-attention-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-risk:RiskMetricsReport:v1"
    }
    assert risk_source.seen_request == RiskVolatilityEvidenceRequest(
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=EVALUATED_AT,
        volatility_threshold=Decimal("12.00"),
        correlation_id="corr-risk-volatility-source-api",
        trace_id="trace-risk-volatility-source-api",
    )
    assert risk_source.close_count == 1


def test_high_volatility_signal_from_source_blocks_when_runtime_not_configured(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    monkeypatch.setattr(
        high_volatility_api,
        "_build_risk_volatility_source_runtime_from_environment",
        lambda: RiskVolatilitySourceRuntimeBlocker("lotus_risk_base_url_not_configured"),
    )

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate-from-source",
        json=high_volatility_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": "Risk source runtime is not configured for high-volatility source evaluation.",
    }
    assert PORTFOLIO_ID not in response.text


def test_high_volatility_signal_from_source_checks_scope_before_runtime(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)

    def fail_if_called() -> RiskVolatilitySourceRuntimeBlocker:
        raise AssertionError("runtime must not be built when caller scope is denied")

    monkeypatch.setattr(
        high_volatility_api,
        "_build_risk_volatility_source_runtime_from_environment",
        fail_if_called,
    )

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate-from-source",
        json=high_volatility_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_SG_OTHER_002"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert PORTFOLIO_ID not in response.text
    assert "PB_SG_OTHER_002" not in response.text


def test_high_volatility_signal_from_source_closes_runtime_on_source_blocker(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    risk_source = RecordingRiskVolatilitySource(
        error=RiskSourceUnavailable(code="risk_source_unavailable")
    )
    monkeypatch.setattr(
        high_volatility_api,
        "_build_risk_volatility_source_runtime_from_environment",
        lambda: RiskVolatilitySourceRuntime(
            risk_source=risk_source,
            risk_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate-from-source",
        json=high_volatility_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "high_volatility",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_unavailable"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }
    assert risk_source.close_count == 1


@mark.parametrize(
    (
        "source_reported_volatility",
        "duplicate_of_candidate_id",
        "expected_outcome",
        "expected_reason",
    ),
    (
        (
            Decimal("14.25"),
            "idea_high_volatility_existing",
            "suppressed",
            "duplicate_suppressed",
        ),
        (
            Decimal("8.50"),
            None,
            "not_eligible",
            "below_materiality",
        ),
    ),
)
def test_high_volatility_signal_from_source_exposes_non_candidate_success_modes(
    monkeypatch: MonkeyPatch,
    source_reported_volatility: Decimal,
    duplicate_of_candidate_id: str | None,
    expected_outcome: str,
    expected_reason: str,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    risk_source = RecordingRiskVolatilitySource(
        evidence=_risk_volatility_evidence(source_reported_volatility=source_reported_volatility)
    )
    monkeypatch.setattr(
        high_volatility_api,
        "_build_risk_volatility_source_runtime_from_environment",
        lambda: RiskVolatilitySourceRuntime(
            risk_source=risk_source,
            risk_base_url_configured=True,
        ),
    )
    request_payload = high_volatility_source_payload()
    request_payload["duplicateOfCandidateId"] = duplicate_of_candidate_id

    response = client.post(
        "/api/v1/idea-signals/high-volatility/evaluate-from-source",
        json=request_payload,
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": expected_outcome,
        "family": "high_volatility",
        "reasonCodes": [expected_reason],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }
    assert risk_source.close_count == 1
    assert len(get_idea_repository().snapshot().candidate_records) == 0


def evaluate_headers() -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
    }


def source_evaluation_headers(*, portfolio_ids: str = PORTFOLIO_ID) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-risk-volatility-source-api",
        "X-Trace-Id": "trace-risk-volatility-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
    }


def high_volatility_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "sourceReportedVolatility": "14.25",
        "riskSupportabilityState": "ready",
        "riskRef": {
            "productId": "lotus-risk:RiskMetricsReport:v1",
            "sourceSystem": "lotus-risk",
            "productVersion": "v1",
            "route": "/analytics/risk/calculate",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:risk-metrics-report",
            "dataQualityStatus": "ready",
            "freshness": "current",
        },
        "entitlementAllowed": True,
    }


def high_volatility_source_payload(*, portfolio_id: str = PORTFOLIO_ID) -> dict[str, Any]:
    return {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "periodName": "YTD",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
    }


def _risk_volatility_evidence(
    *, source_reported_volatility: Decimal = Decimal("14.25")
) -> RiskVolatilityEvidence:
    return RiskVolatilityEvidence(
        source_reported_volatility=source_reported_volatility,
        risk_supportability_state="ready",
        risk_ref=SourceRef(
            product_id="lotus-risk:RiskMetricsReport:v1",
            source_system=SourceSystem.LOTUS_RISK,
            product_version="v1",
            route="/analytics/risk/calculate",
            as_of_date=AS_OF_DATE,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:risk-metrics-report",
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        risk_diagnostic="risk_volatility_source_ready",
    )
