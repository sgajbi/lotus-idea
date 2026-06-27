from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.application.drawdown_review_signal import (
    EvaluateDrawdownReviewFromRiskCommand,
    EvaluateDrawdownReviewSignalCommand,
    evaluate_drawdown_review_signal_command,
    evaluate_drawdown_review_signal_from_risk,
)
from app.domain import EvidenceFreshness, SignalEvaluationOutcome, SourceRef, SourceSystem
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskDrawdownEvidence,
    RiskDrawdownEvidenceRequest,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
    RiskVolatilityEvidence,
    RiskVolatilityEvidenceRequest,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class StubRiskSource:
    def __init__(
        self,
        evidence: RiskDrawdownEvidence | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exc = exc
        self.requests: list[RiskDrawdownEvidenceRequest] = []

    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        self.requests.append(request)
        if self.exc is not None:
            raise self.exc
        assert self.evidence is not None
        return self.evidence

    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        raise AssertionError("concentration evidence is not used by drawdown tests")

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        raise AssertionError("volatility evidence is not used by drawdown tests")


def source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-risk:DrawdownAnalyticsReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        product_version="v1",
        route="/analytics/risk/drawdown",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:drawdown-analytics-report",
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )


def command() -> EvaluateDrawdownReviewFromRiskCommand:
    return EvaluateDrawdownReviewFromRiskCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-risk",
        trace_id="trace-risk",
    )


def test_evaluate_drawdown_review_signal_command_maps_source_input() -> None:
    result = evaluate_drawdown_review_signal_command(
        EvaluateDrawdownReviewSignalCommand(
            as_of_date=AS_OF_DATE,
            source_reported_max_drawdown=Decimal("-0.1245"),
            risk_supportability_state="ready",
            risk_ref=source_ref(),
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_drawdown_review_")


def test_evaluate_drawdown_review_signal_from_risk_uses_source_evidence() -> None:
    risk_source = StubRiskSource(
        RiskDrawdownEvidence(
            source_reported_max_drawdown=Decimal("-0.1245"),
            risk_supportability_state="ready",
            risk_ref=source_ref(),
            risk_diagnostic="risk_drawdown_source_ready",
        )
    )

    result = evaluate_drawdown_review_signal_from_risk(command(), risk_source=risk_source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert risk_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert risk_source.requests[0].period_name == "YTD"
    assert risk_source.requests[0].correlation_id == "corr-risk"
    assert risk_source.requests[0].drawdown_threshold == Decimal("-0.08")


def test_evaluate_drawdown_review_signal_from_risk_blocks_entitlement_denial() -> None:
    result = evaluate_drawdown_review_signal_from_risk(
        command(),
        risk_source=StubRiskSource(exc=RiskSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None


def test_evaluate_drawdown_review_signal_from_risk_blocks_source_unavailable() -> None:
    result = evaluate_drawdown_review_signal_from_risk(
        command(),
        risk_source=StubRiskSource(exc=RiskSourceUnavailable(code="risk_unavailable")),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
