from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.high_volatility_signal import (
    EvaluateAndPersistHighVolatilityFromRiskCommand,
    EvaluateHighVolatilityFromRiskCommand,
    EvaluateHighVolatilitySignalCommand,
    evaluate_and_persist_high_volatility_signal_from_risk,
    evaluate_high_volatility_signal_command,
    evaluate_high_volatility_signal_from_risk,
)
from app.domain import (
    CandidatePersistenceDecision,
    EvidenceFreshness,
    InMemoryIdeaRepository,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
)
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
        evidence: RiskVolatilityEvidence | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.evidence = evidence
        self.exc = exc
        self.requests: list[RiskVolatilityEvidenceRequest] = []

    def fetch_volatility_evidence(
        self, request: RiskVolatilityEvidenceRequest
    ) -> RiskVolatilityEvidence:
        self.requests.append(request)
        if self.exc is not None:
            raise self.exc
        assert self.evidence is not None
        return self.evidence

    def fetch_concentration_evidence(
        self, request: RiskConcentrationEvidenceRequest
    ) -> RiskConcentrationEvidence:
        raise AssertionError("concentration evidence is not used by high-volatility tests")

    def fetch_drawdown_evidence(self, request: RiskDrawdownEvidenceRequest) -> RiskDrawdownEvidence:
        raise AssertionError("drawdown evidence is not used by high-volatility tests")


def source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-risk:RiskMetricsReport:v1",
        source_system=SourceSystem.LOTUS_RISK,
        product_version="v1",
        route="/analytics/risk/calculate",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:risk-metrics-report",
        data_quality_status="ready",
        freshness=EvidenceFreshness.CURRENT,
    )


def command() -> EvaluateHighVolatilityFromRiskCommand:
    return EvaluateHighVolatilityFromRiskCommand(
        portfolio_id="PB_SG_GLOBAL_BAL_001",
        as_of_date=AS_OF_DATE,
        period_name="YTD",
        evaluated_at_utc=EVALUATED_AT,
        correlation_id="corr-risk",
        trace_id="trace-risk",
    )


def test_evaluate_high_volatility_signal_command_maps_source_input() -> None:
    result = evaluate_high_volatility_signal_command(
        EvaluateHighVolatilitySignalCommand(
            as_of_date=AS_OF_DATE,
            source_reported_volatility=Decimal("14.25"),
            risk_supportability_state="ready",
            risk_ref=source_ref(),
            evaluated_at_utc=EVALUATED_AT,
        )
    )

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert result.candidate is not None
    assert result.candidate.candidate_id.startswith("idea_high_volatility_")


def test_evaluate_high_volatility_signal_from_risk_uses_source_evidence() -> None:
    risk_source = StubRiskSource(
        RiskVolatilityEvidence(
            source_reported_volatility=Decimal("14.25"),
            risk_supportability_state="ready",
            risk_ref=source_ref(),
            risk_diagnostic="risk_volatility_source_ready",
        )
    )

    result = evaluate_high_volatility_signal_from_risk(command(), risk_source=risk_source)

    assert result.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert risk_source.requests[0].portfolio_id == "PB_SG_GLOBAL_BAL_001"
    assert risk_source.requests[0].period_name == "YTD"
    assert risk_source.requests[0].correlation_id == "corr-risk"


def test_evaluate_high_volatility_signal_from_risk_blocks_entitlement_denial() -> None:
    result = evaluate_high_volatility_signal_from_risk(
        command(),
        risk_source=StubRiskSource(exc=RiskSourceEntitlementDenied()),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None


def test_evaluate_high_volatility_signal_from_risk_blocks_source_unavailable() -> None:
    result = evaluate_high_volatility_signal_from_risk(
        command(),
        risk_source=StubRiskSource(exc=RiskSourceUnavailable(code="risk_unavailable")),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None


def test_evaluate_and_persist_high_volatility_accepts_then_replays_same_command() -> None:
    repository = InMemoryIdeaRepository()
    source = StubRiskSource(
        RiskVolatilityEvidence(
            source_reported_volatility=Decimal("14.25"),
            risk_supportability_state="ready",
            risk_ref=source_ref(),
            risk_diagnostic="risk_volatility_source_ready",
        )
    )
    persisted_command = EvaluateAndPersistHighVolatilityFromRiskCommand(
        evaluation=command(),
        idempotency_key="high-volatility-runtime",
        actor_subject="runtime-evidence",
    )

    accepted = evaluate_and_persist_high_volatility_signal_from_risk(
        persisted_command,
        risk_source=source,
        repository=repository,
    )
    replayed = evaluate_and_persist_high_volatility_signal_from_risk(
        persisted_command,
        risk_source=source,
        repository=repository,
    )

    assert accepted.persistence is not None
    assert accepted.persistence.decision is CandidatePersistenceDecision.ACCEPTED
    assert replayed.persistence is not None
    assert replayed.persistence.decision is CandidatePersistenceDecision.REPLAYED
    assert accepted.source_diagnostic_codes == ("risk_volatility_source_ready",)


@pytest.mark.parametrize(
    ("exception", "diagnostic"),
    (
        (RiskSourceEntitlementDenied(), "risk_source_entitlement_denied"),
        (RiskSourceUnavailable(code="risk_unavailable"), "risk_unavailable"),
    ),
)
def test_evaluate_and_persist_high_volatility_fails_before_persistence_on_source_failure(
    exception: Exception,
    diagnostic: str,
) -> None:
    result = evaluate_and_persist_high_volatility_signal_from_risk(
        EvaluateAndPersistHighVolatilityFromRiskCommand(
            evaluation=command(),
            idempotency_key="high-volatility-runtime",
            actor_subject="runtime-evidence",
        ),
        risk_source=StubRiskSource(exc=exception),
        repository=InMemoryIdeaRepository(),
    )

    assert result.evaluation.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.persistence is None
    assert result.source_diagnostic_codes == (diagnostic,)


@pytest.mark.parametrize(("idempotency_key", "actor_subject"), (("", "actor"), ("key", "")))
def test_evaluate_and_persist_high_volatility_requires_command_identity(
    idempotency_key: str,
    actor_subject: str,
) -> None:
    with pytest.raises(ValueError, match="required"):
        evaluate_and_persist_high_volatility_signal_from_risk(
            EvaluateAndPersistHighVolatilityFromRiskCommand(
                evaluation=command(),
                idempotency_key=idempotency_key,
                actor_subject=actor_subject,
            ),
            risk_source=StubRiskSource(),
            repository=InMemoryIdeaRepository(),
        )
