from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from tests.support.http import managed_test_client
from pytest import MonkeyPatch, mark

import app.api.concentration_risk_signals as concentration_risk_api
from app.api.caller_headers import INVALID_CALLER_SCOPE_DETAIL
from app.domain import EvidenceFreshness, InMemoryIdeaRepository, SourceRef, SourceSystem
from app.main import app
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskSourceUnavailable,
)
from app.runtime.repository_state import get_idea_repository, reset_idea_repository_for_tests
from app.runtime.source_ingestion_state import (
    RiskConcentrationSourceRuntime,
    RiskConcentrationSourceRuntimeBlocker,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
PORTFOLIO_ID = "PB_SG_GLOBAL_BAL_001"


@dataclass
class RecordingRiskSource:
    seen_request: RiskConcentrationEvidenceRequest | None = None
    evidence: RiskConcentrationEvidence | None = None
    error: Exception | None = None
    close_count: int = 0

    def fetch_concentration_evidence(
        self,
        request: RiskConcentrationEvidenceRequest,
    ) -> RiskConcentrationEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        return self.evidence or _risk_evidence()

    def close(self) -> None:
        self.close_count += 1


def test_concentration_risk_signal_api_returns_review_candidate() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "concentration"
    assert payload["reasonCodes"] == ["concentration_attention", "review_required"]
    assert payload["unsupportedReasons"] == []
    assert payload["sourceAuthority"] == "lotus-risk"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["reviewPosture"] == "advisor_review_required"
    assert payload["candidate"]["scorePolicyVersion"] == "concentration-attention-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-risk:ConcentrationRiskReport:v1"
    }
    assert "route" not in payload["candidate"]["sourceRefs"][0]
    assert "contentHash" not in payload["candidate"]["sourceRefs"][0]


def test_concentration_risk_signal_api_reports_below_threshold_not_eligible() -> None:
    client = managed_test_client(app)
    payload = concentration_payload()
    payload["topPositionWeightCurrent"] = "0.05"
    payload["topIssuerWeightCurrent"] = "0.08"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "not_eligible",
        "family": "concentration",
        "reasonCodes": ["below_materiality"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_concentration_risk_signal_api_reports_duplicate_suppressed() -> None:
    client = managed_test_client(app)
    payload = concentration_payload()
    payload["duplicateOfCandidateId"] = "idea_concentration_existing"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "suppressed",
        "family": "concentration",
        "reasonCodes": ["duplicate_suppressed"],
        "unsupportedReasons": [],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_concentration_risk_signal_api_reports_partial_issuer_coverage_blocker() -> None:
    client = managed_test_client(app)
    payload = concentration_payload()
    payload["issuerCoverageStatus"] = "partial"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "concentration",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_uncertified"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_concentration_risk_signal_api_reports_stale_source_blocker() -> None:
    client = managed_test_client(app)
    payload = concentration_payload()
    payload["concentrationRef"]["freshness"] = "stale"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "concentration",
        "reasonCodes": ["source_stale"],
        "unsupportedReasons": ["stale_source"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }


def test_concentration_risk_signal_api_rejects_wrong_source_contract(
    monkeypatch: MonkeyPatch,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    payload = concentration_payload()
    payload["concentrationRef"] = {
        **payload["concentrationRef"],
        "sourceSystem": "lotus-core",
        "productId": "lotus-core:PortfolioStateSnapshot:v1",
        "route": "/integration/portfolios/PB_SG_GLOBAL_BAL_001/core-snapshot",
        "contentHash": "sha256:wrong-concentration-source",
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

    monkeypatch.setattr(concentration_risk_api, "emit_foundation_operation_event", capture)

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text
    assert "lotus-core:PortfolioStateSnapshot:v1" not in response.text
    assert len(get_idea_repository().snapshot().candidate_records) == 0
    assert events == [
        (
            "signal_evaluation",
            "invalid_request",
            "lotus-risk",
            "source_ref_contract_mismatch",
        )
    ]


def test_concentration_risk_signal_api_rejects_wrong_risk_product_id() -> None:
    client = managed_test_client(app)
    payload = concentration_payload()
    payload["concentrationRef"]["productId"] = "lotus-risk:RiskMetricsReport:v1"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=payload,
        headers=evaluate_headers(),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert "candidate_created" not in response.text


def test_concentration_risk_signal_api_requires_signal_permission() -> None:
    client = managed_test_client(app)

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
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


def test_concentration_risk_signal_api_rejects_out_of_scope_access_scope() -> None:
    client = managed_test_client(app)
    headers = evaluate_headers()
    headers["X-Caller-Portfolio-Ids"] = "PB_SG_OTHER_002"

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json() == {
        "type": "about:blank",
        "status": 403,
        "code": "permission_denied",
        "title": "Permission denied",
        "detail": "The caller is not permitted to evaluate idea signals for the requested scope.",
    }
    assert "PB_SG_GLOBAL_BAL_001" not in response.text
    assert "PB_SG_OTHER_002" not in response.text


def test_concentration_risk_signal_api_rejects_blank_entitlement_scope_header() -> None:
    client = managed_test_client(app)
    headers = evaluate_headers()
    headers["X-Caller-Portfolio-Ids"] = "PB_SG_GLOBAL_BAL_001, "

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate",
        json=concentration_payload(),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json() == {
        "type": "about:blank",
        "status": 400,
        "code": "invalid_request",
        "title": "Invalid request",
        "detail": INVALID_CALLER_SCOPE_DETAIL,
    }


def test_concentration_risk_signal_from_source_api_returns_review_candidate(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    risk_source = RecordingRiskSource()
    monkeypatch.setattr(
        concentration_risk_api,
        "_build_risk_concentration_source_runtime_from_environment",
        lambda: RiskConcentrationSourceRuntime(
            risk_source=risk_source,
            risk_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
        json=concentration_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "candidate_created"
    assert payload["family"] == "concentration"
    assert payload["sourceAuthority"] == "lotus-risk"
    assert payload["supportedFeaturePromoted"] is False
    assert payload["candidate"]["scorePolicyVersion"] == "concentration-attention-v1"
    assert {source_ref["productId"] for source_ref in payload["candidate"]["sourceRefs"]} == {
        "lotus-risk:ConcentrationRiskReport:v1"
    }
    assert risk_source.seen_request == RiskConcentrationEvidenceRequest(
        portfolio_id=PORTFOLIO_ID,
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-risk-source-api",
        trace_id="trace-risk-source-api",
    )
    assert risk_source.close_count == 1


def test_concentration_risk_signal_from_source_blocks_when_runtime_not_configured(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    monkeypatch.setattr(
        concentration_risk_api,
        "_build_risk_concentration_source_runtime_from_environment",
        lambda: RiskConcentrationSourceRuntimeBlocker("lotus_risk_base_url_not_configured"),
    )

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
        json=concentration_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 503
    assert response.json() == {
        "type": "about:blank",
        "status": 503,
        "code": "source_runtime_not_configured",
        "title": "Source runtime not configured",
        "detail": "Risk source runtime is not configured for concentration source evaluation.",
    }
    assert PORTFOLIO_ID not in response.text


def test_concentration_risk_signal_from_source_checks_scope_before_runtime(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)

    def fail_if_called() -> RiskConcentrationSourceRuntimeBlocker:
        raise AssertionError("runtime must not be built when caller scope is denied")

    monkeypatch.setattr(
        concentration_risk_api,
        "_build_risk_concentration_source_runtime_from_environment",
        fail_if_called,
    )

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
        json=concentration_source_payload(),
        headers=source_evaluation_headers(portfolio_ids="PB_SG_OTHER_002"),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
    assert PORTFOLIO_ID not in response.text
    assert "PB_SG_OTHER_002" not in response.text


def test_concentration_risk_signal_from_source_closes_runtime_on_source_blocker(
    monkeypatch: MonkeyPatch,
) -> None:
    client = managed_test_client(app)
    risk_source = RecordingRiskSource(error=RiskSourceUnavailable(code="risk_source_unavailable"))
    monkeypatch.setattr(
        concentration_risk_api,
        "_build_risk_concentration_source_runtime_from_environment",
        lambda: RiskConcentrationSourceRuntime(
            risk_source=risk_source,
            risk_base_url_configured=True,
        ),
    )

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
        json=concentration_source_payload(),
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": "blocked",
        "family": "concentration",
        "reasonCodes": ["source_partial"],
        "unsupportedReasons": ["source_unavailable"],
        "candidate": None,
        "sourceAuthority": "lotus-risk",
        "supportedFeaturePromoted": False,
    }
    assert risk_source.close_count == 1


@mark.parametrize(
    (
        "top_position_weight",
        "top_issuer_weight",
        "duplicate_of_candidate_id",
        "expected_outcome",
        "expected_reason",
    ),
    (
        (
            Decimal("0.22"),
            Decimal("0.27"),
            "idea_concentration_existing",
            "suppressed",
            "duplicate_suppressed",
        ),
        (
            Decimal("0.05"),
            Decimal("0.08"),
            None,
            "not_eligible",
            "below_materiality",
        ),
    ),
)
def test_concentration_risk_signal_from_source_exposes_non_candidate_success_modes(
    monkeypatch: MonkeyPatch,
    top_position_weight: Decimal,
    top_issuer_weight: Decimal,
    duplicate_of_candidate_id: str | None,
    expected_outcome: str,
    expected_reason: str,
) -> None:
    reset_idea_repository_for_tests(InMemoryIdeaRepository())
    client = managed_test_client(app)
    risk_source = RecordingRiskSource(
        evidence=_risk_evidence_with_weights(top_position_weight, top_issuer_weight)
    )
    monkeypatch.setattr(
        concentration_risk_api,
        "_build_risk_concentration_source_runtime_from_environment",
        lambda: RiskConcentrationSourceRuntime(
            risk_source=risk_source,
            risk_base_url_configured=True,
        ),
    )
    request_payload = concentration_source_payload()
    request_payload["duplicateOfCandidateId"] = duplicate_of_candidate_id

    response = client.post(
        "/api/v1/idea-signals/concentration-risk/evaluate-from-source",
        json=request_payload,
        headers=source_evaluation_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "outcome": expected_outcome,
        "family": "concentration",
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
        "X-Caller-Tenant-Ids": "tenant-private-bank-sg",
        "X-Caller-Book-Ids": "book-advisor-001",
        "X-Caller-Portfolio-Ids": "PB_SG_GLOBAL_BAL_001",
        "X-Caller-Client-Ids": "client-001",
    }


def source_evaluation_headers(*, portfolio_ids: str = PORTFOLIO_ID) -> dict[str, str]:
    return {
        "X-Caller-Subject": "advisor-001",
        "X-Caller-Roles": "advisor",
        "X-Caller-Capabilities": "idea.signal.evaluate",
        "X-Correlation-Id": "corr-risk-source-api",
        "X-Trace-Id": "trace-risk-source-api",
        "X-Caller-Portfolio-Ids": portfolio_ids,
    }


def concentration_payload() -> dict[str, Any]:
    return {
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
        "topPositionWeightCurrent": "0.18",
        "topIssuerWeightCurrent": "0.24",
        "issuerCoverageStatus": "complete",
        "concentrationRef": {
            "productId": "lotus-risk:ConcentrationRiskReport:v1",
            "sourceSystem": "lotus-risk",
            "productVersion": "v1",
            "route": "/analytics/risk/concentration",
            "asOfDate": "2026-06-21",
            "generatedAtUtc": "2026-06-21T10:00:00Z",
            "contentHash": "sha256:concentration-risk-report",
            "dataQualityStatus": "quality_passed",
            "freshness": "current",
        },
        "accessScope": {
            "tenantId": "tenant-private-bank-sg",
            "bookId": "book-advisor-001",
            "portfolioId": "PB_SG_GLOBAL_BAL_001",
            "clientId": "client-001",
        },
        "entitlementAllowed": True,
    }


def concentration_source_payload(*, portfolio_id: str = PORTFOLIO_ID) -> dict[str, Any]:
    return {
        "portfolioId": portfolio_id,
        "asOfDate": "2026-06-21",
        "evaluatedAtUtc": "2026-06-21T10:00:00Z",
    }


def _risk_evidence() -> RiskConcentrationEvidence:
    return RiskConcentrationEvidence(
        top_position_weight_current=Decimal("0.22"),
        top_issuer_weight_current=Decimal("0.27"),
        issuer_coverage_status="complete",
        concentration_ref=SourceRef(
            product_id="lotus-risk:ConcentrationRiskReport:v1",
            source_system=SourceSystem.LOTUS_RISK,
            product_version="v1",
            route="/analytics/risk/concentration",
            as_of_date=AS_OF_DATE,
            generated_at_utc=EVALUATED_AT,
            content_hash="sha256:risk-concentration-report",
            data_quality_status="ready",
            freshness=EvidenceFreshness.CURRENT,
        ),
        concentration_diagnostic="risk_issuer_coverage_complete",
    )


def _risk_evidence_with_weights(
    top_position_weight: Decimal,
    top_issuer_weight: Decimal,
) -> RiskConcentrationEvidence:
    evidence = _risk_evidence()
    return RiskConcentrationEvidence(
        top_position_weight_current=top_position_weight,
        top_issuer_weight_current=top_issuer_weight,
        issuer_coverage_status=evidence.issuer_coverage_status,
        concentration_ref=evidence.concentration_ref,
        concentration_diagnostic=evidence.concentration_diagnostic,
        entitlement_allowed=evidence.entitlement_allowed,
    )
