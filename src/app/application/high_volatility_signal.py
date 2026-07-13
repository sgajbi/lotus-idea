from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidateScorePolicyVersion,
    HighVolatilitySignalInput,
    HighVolatilitySignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_high_volatility_signal,
)
from app.application.access_scope import portfolio_only_scope
from app.domain.access_scope import ReviewAccessScope
from app.ports.risk_sources import (
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
    RiskVolatilitySourcePort,
    RiskVolatilityEvidence,
    RiskVolatilityEvidenceRequest,
)


@dataclass(frozen=True)
class EvaluateHighVolatilitySignalCommand:
    as_of_date: date
    source_reported_volatility: Decimal | None
    risk_supportability_state: str | None
    risk_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateHighVolatilityFromRiskCommand:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_HIGH_VOLATILITY_POLICY = HighVolatilitySignalPolicy(
    policy_version=CandidateScorePolicyVersion.HIGH_VOLATILITY.value,
    volatility_threshold=Decimal("12.00"),
    candidate_score=Decimal("72"),
)


def evaluate_high_volatility_signal_command(
    command: EvaluateHighVolatilitySignalCommand,
    *,
    policy: HighVolatilitySignalPolicy = DEFAULT_HIGH_VOLATILITY_POLICY,
) -> SignalEvaluationResult:
    source_input = HighVolatilitySignalInput(
        as_of_date=command.as_of_date,
        source_reported_volatility=command.source_reported_volatility,
        risk_supportability_state=command.risk_supportability_state,
        risk_ref=command.risk_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_high_volatility_signal(source_input, policy)


def evaluate_high_volatility_signal_from_risk(
    command: EvaluateHighVolatilityFromRiskCommand,
    *,
    risk_source: RiskVolatilitySourcePort,
    policy: HighVolatilitySignalPolicy = DEFAULT_HIGH_VOLATILITY_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = risk_source.fetch_volatility_evidence(
            RiskVolatilityEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                period_name=command.period_name,
                evaluated_at_utc=command.evaluated_at_utc,
                volatility_threshold=policy.volatility_threshold,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except RiskSourceEntitlementDenied:
        return evaluate_high_volatility_signal_command(
            EvaluateHighVolatilitySignalCommand(
                as_of_date=command.as_of_date,
                source_reported_volatility=None,
                risk_supportability_state=None,
                risk_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=portfolio_only_scope(command.portfolio_id),
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except RiskSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_high_volatility_evidence(command, evidence, policy=policy)


def _evaluate_high_volatility_evidence(
    command: EvaluateHighVolatilityFromRiskCommand,
    evidence: RiskVolatilityEvidence,
    *,
    policy: HighVolatilitySignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_high_volatility_signal_command(
        EvaluateHighVolatilitySignalCommand(
            as_of_date=command.as_of_date,
            source_reported_volatility=evidence.source_reported_volatility,
            risk_supportability_state=evidence.risk_supportability_state,
            risk_ref=evidence.risk_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )
