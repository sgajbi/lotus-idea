from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.concentration_risk_signal import (
    EvaluateAndPersistConcentrationRiskFromRiskCommand,
    EvaluateAndPersistConcentrationRiskSignalCommand,
    EvaluateConcentrationRiskFromRiskCommand,
    EvaluateConcentrationRiskSignalCommand,
    evaluate_and_persist_concentration_risk_signal,
    evaluate_and_persist_concentration_risk_signal_from_risk,
    evaluate_concentration_risk_signal_command,
    evaluate_concentration_risk_signal_from_risk,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    InMemoryIdeaRepository,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
)
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskDrawdownEvidence,
    RiskDrawdownEvidenceRequest,
    RiskOpportunitySourcePort,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
    RiskVolatilityEvidence,
    RiskVolatilityEvidenceRequest,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-risk:ConcentrationRiskReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        product_version="v1",
        route="/analytics/risk/concentration",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:concentration-risk-report",
        data_quality_status="ready",
        freshness=freshness,
    )


def command(
    *,
    top_position_weight: Decimal | None = Decimal("0.23"),
    top_issuer_weight: Decimal | None = Decimal("0.245"),
    issuer_coverage_status: str | None = "complete",
    entitlement_allowed: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
) -> EvaluateConcentrationRiskSignalCommand:
    return EvaluateConcentrationRiskSignalCommand(
        as_of_date=AS_OF_DATE,
        top_position_weight_current=top_position_weight,
        top_issuer_weight_current=top_issuer_weight,
        issuer_coverage_status=issuer_coverage_status,
        concentration_ref=source_ref(freshness),
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
    )


def test_application_evaluates_concentration_command_with_default_policy() -> None:
    result = evaluate_concentration_risk_signal_command(command())

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.score is not None
    assert result.candidate.score.policy_version == "concentration-attention-v1"


def test_application_preserves_entitlement_denied_as_blocked_domain_posture() -> None:
    result = evaluate_concentration_risk_signal_command(command(entitlement_allowed=False))

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_application_preserves_partial_coverage_as_blocked_domain_posture() -> None:
    result = evaluate_concentration_risk_signal_command(command(issuer_coverage_status="partial"))

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,)


@dataclass
class RecordingRiskSource(RiskOpportunitySourcePort):
    evidence: RiskConcentrationEvidence | None = None
    error: Exception | None = None
    seen_request: RiskConcentrationEvidenceRequest | None = None

    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        self.seen_request = request
        if self.error is not None:
            raise self.error
        if self.evidence is None:
            raise AssertionError("evidence must be configured")
        return self.evidence

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        raise AssertionError("volatility evidence is not used by concentration tests")

    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        raise AssertionError("drawdown evidence is not used by concentration tests")


def from_risk_command() -> EvaluateConcentrationRiskFromRiskCommand:
    return EvaluateConcentrationRiskFromRiskCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-idea",
        trace_id="trace-idea",
    )


def current_risk_evidence(
    *,
    top_position_weight: Decimal | None = Decimal("0.23"),
    top_issuer_weight: Decimal | None = Decimal("0.245"),
    issuer_coverage_status: str | None = "complete",
    concentration_diagnostic: str | None = "risk_issuer_coverage_complete",
) -> RiskConcentrationEvidence:
    return RiskConcentrationEvidence(
        top_position_weight_current=top_position_weight,
        top_issuer_weight_current=top_issuer_weight,
        issuer_coverage_status=issuer_coverage_status,
        concentration_ref=source_ref(),
        concentration_diagnostic=concentration_diagnostic,
    )


def test_application_fetches_risk_source_evidence_before_concentration_evaluation() -> None:
    source = RecordingRiskSource(evidence=current_risk_evidence())

    result = evaluate_concentration_risk_signal_from_risk(
        from_risk_command(),
        risk_source=source,
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert source.seen_request is not None
    assert source.seen_request.portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert source.seen_request.correlation_id == "corr-idea"
    assert source.seen_request.trace_id == "trace-idea"


def test_application_blocks_source_backed_flow_when_risk_denies_entitlement() -> None:
    source = RecordingRiskSource(error=RiskSourceEntitlementDenied())

    result = evaluate_concentration_risk_signal_from_risk(
        from_risk_command(),
        risk_source=source,
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)
    assert result.candidate is None


def test_application_blocks_source_backed_flow_when_risk_is_unavailable() -> None:
    source = RecordingRiskSource(error=RiskSourceUnavailable(code="upstream_timeout"))

    result = evaluate_concentration_risk_signal_from_risk(
        from_risk_command(),
        risk_source=source,
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,)
    assert result.candidate is None


def test_application_does_not_infer_concentration_when_risk_omits_source_value() -> None:
    source = RecordingRiskSource(
        evidence=current_risk_evidence(top_position_weight=None, top_issuer_weight=None)
    )

    result = evaluate_concentration_risk_signal_from_risk(
        from_risk_command(),
        risk_source=source,
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)
    assert result.candidate is None


def persist_command(
    *,
    evaluation: EvaluateConcentrationRiskSignalCommand | None = None,
    idempotency_key: str = "signal-ingestion:concentration:pb-001:2026-06-21",
) -> EvaluateAndPersistConcentrationRiskSignalCommand:
    return EvaluateAndPersistConcentrationRiskSignalCommand(
        evaluation=evaluation or command(),
        idempotency_key=idempotency_key,
        actor_subject="signal-ingestion-worker",
    )


def test_application_persists_created_concentration_candidate_with_audit_event() -> None:
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_concentration_risk_signal(
        persist_command(),
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.persistence is not None
    assert result.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert result.persistence.record is not None
    assert result.persistence.record.audit_events[0].event_type == "idea.candidate.persisted"


def test_application_replays_same_concentration_idempotency_payload() -> None:
    repository = InMemoryIdeaRepository()
    first = evaluate_and_persist_concentration_risk_signal(
        persist_command(),
        repository=repository,
    )

    replayed = evaluate_and_persist_concentration_risk_signal(
        persist_command(),
        repository=repository,
    )

    assert first.persistence is not None
    assert replayed.persistence is not None
    assert replayed.persistence.decision is CandidatePersistenceDecision.REPLAYED
    assert replayed.persistence.record == first.persistence.record


def test_application_does_not_persist_blocked_concentration_evaluation() -> None:
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_concentration_risk_signal(
        persist_command(evaluation=command(issuer_coverage_status="partial")),
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.persistence is None
    assert len(repository.snapshot().candidate_records) == 0


def test_application_persists_risk_backed_concentration_candidate() -> None:
    source = RecordingRiskSource(evidence=current_risk_evidence())
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        EvaluateAndPersistConcentrationRiskFromRiskCommand(
            evaluation=from_risk_command(),
            idempotency_key="signal-ingestion:concentration:risk:pb-001:2026-06-21",
            actor_subject="signal-ingestion-worker",
        ),
        risk_source=source,
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.persistence is not None
    assert result.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert result.source_diagnostic_codes == ("risk_issuer_coverage_complete",)
    assert source.seen_request is not None
    assert source.seen_request.portfolio_id == "PB_SG_GLOBAL_BAL_001"


def test_application_does_not_persist_risk_backed_entitlement_denial() -> None:
    source = RecordingRiskSource(error=RiskSourceEntitlementDenied())
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        EvaluateAndPersistConcentrationRiskFromRiskCommand(
            evaluation=from_risk_command(),
            idempotency_key="signal-ingestion:concentration:risk:denied:2026-06-21",
            actor_subject="signal-ingestion-worker",
        ),
        risk_source=source,
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.persistence is None
    assert result.source_diagnostic_codes == ("risk_source_entitlement_denied",)
    assert len(repository.snapshot().candidate_records) == 0


def test_application_does_not_persist_risk_backed_unavailable_source() -> None:
    source = RecordingRiskSource(error=RiskSourceUnavailable(code="upstream_timeout"))
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        EvaluateAndPersistConcentrationRiskFromRiskCommand(
            evaluation=from_risk_command(),
            idempotency_key="signal-ingestion:concentration:risk:unavailable:2026-06-21",
            actor_subject="signal-ingestion-worker",
        ),
        risk_source=source,
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.persistence is None
    assert result.source_diagnostic_codes == ("upstream_timeout",)
    assert len(repository.snapshot().candidate_records) == 0


def test_application_does_not_persist_risk_backed_below_materiality_result() -> None:
    source = RecordingRiskSource(
        evidence=current_risk_evidence(
            top_position_weight=Decimal("0.01"),
            top_issuer_weight=Decimal("0.02"),
            concentration_diagnostic=" ",
        )
    )
    repository = InMemoryIdeaRepository()

    result = evaluate_and_persist_concentration_risk_signal_from_risk(
        EvaluateAndPersistConcentrationRiskFromRiskCommand(
            evaluation=from_risk_command(),
            idempotency_key="signal-ingestion:concentration:risk:below:2026-06-21",
            actor_subject="signal-ingestion-worker",
        ),
        risk_source=source,
        repository=repository,
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.persistence is None
    assert result.source_diagnostic_codes == ()
    assert len(repository.snapshot().candidate_records) == 0


def test_application_requires_actor_for_risk_backed_persistence() -> None:
    source = RecordingRiskSource(evidence=current_risk_evidence())

    with pytest.raises(ValueError, match="actor_subject is required"):
        evaluate_and_persist_concentration_risk_signal_from_risk(
            EvaluateAndPersistConcentrationRiskFromRiskCommand(
                evaluation=from_risk_command(),
                idempotency_key="signal-ingestion:concentration:risk:actor:2026-06-21",
                actor_subject=" ",
            ),
            risk_source=source,
            repository=InMemoryIdeaRepository(),
        )
