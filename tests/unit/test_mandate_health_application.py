from __future__ import annotations

from datetime import UTC, date, datetime

from app.application.mandate_health_signal import (
    EvaluateMandateHealthFromManageCommand,
    evaluate_mandate_health_signal_from_manage,
)
from app.domain import (
    EvidenceFreshness,
    ReasonCode,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
from app.ports.manage_sources import (
    ManageMandateHealthEvidence,
    ManageMandateHealthEvidenceRequest,
    ManageSourceEntitlementDenied,
    ManageSourceUnavailable,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


class StubManageSource:
    def __init__(
        self,
        evidence: ManageMandateHealthEvidence | None = None,
        exception: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exception = exception
        self.requests: list[ManageMandateHealthEvidenceRequest] = []

    def fetch_mandate_health_evidence(
        self,
        request: ManageMandateHealthEvidenceRequest,
    ) -> ManageMandateHealthEvidence:
        self.requests.append(request)
        if self.exception is not None:
            raise self.exception
        assert self.evidence is not None
        return self.evidence


def test_mandate_health_application_consumes_manage_source_evidence() -> None:
    manage_source = StubManageSource(
        ManageMandateHealthEvidence(
            workflow_decision_count=2,
            lineage_edge_count=4,
            supportability_state="ready",
            supportability_reason="supportability_summary_ready",
            freshness_bucket="current",
            portfolio_scope_confirmed=True,
            action_register_ref=_source_ref(),
            manage_diagnostic="manage_action_register_ready_portfolio_scope",
        )
    )

    result = evaluate_mandate_health_signal_from_manage(
        _command(),
        manage_source=manage_source,
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.reason_codes == (
        ReasonCode.ALLOCATION_DRIFT_ATTENTION,
        ReasonCode.REVIEW_REQUIRED,
    )
    assert manage_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_mandate_health_application_blocks_store_wide_manage_source_evidence() -> None:
    manage_source = StubManageSource(
        ManageMandateHealthEvidence(
            workflow_decision_count=2,
            lineage_edge_count=4,
            supportability_state="ready",
            supportability_reason="supportability_summary_ready",
            freshness_bucket="current",
            portfolio_scope_confirmed=False,
            action_register_ref=_source_ref(),
            manage_diagnostic="manage_action_register_ready_store_wide_scope",
        )
    )

    result = evaluate_mandate_health_signal_from_manage(
        _command(),
        manage_source=manage_source,
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def test_mandate_health_application_blocks_when_manage_source_unavailable() -> None:
    result = evaluate_mandate_health_signal_from_manage(
        _command(),
        manage_source=StubManageSource(
            exception=ManageSourceUnavailable(code="manage_supportability_summary_pending")
        ),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)


def test_mandate_health_application_blocks_entitlement_denial_without_candidate() -> None:
    result = evaluate_mandate_health_signal_from_manage(
        _command(),
        manage_source=StubManageSource(exception=ManageSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.REVIEW_REQUIRED,)


def _command() -> EvaluateMandateHealthFromManageCommand:
    return EvaluateMandateHealthFromManageCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-manage",
        trace_id="trace-manage",
    )


def _source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-manage:PortfolioActionRegister:v1",
        source_system=SourceSystem.LOTUS_MANAGE,
        product_version="v1",
        route="/api/v1/rebalance/supportability/summary",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:portfolio-action-register",
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )
