from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    DrawdownReviewSignalInput,
    DrawdownReviewSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_drawdown_review_signal,
)
from app.domain.access_scope import ReviewAccessScope
from app.ports.risk_sources import (
    RiskDrawdownEvidence,
    RiskDrawdownEvidenceRequest,
    RiskOpportunitySourcePort,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateDrawdownReviewSignalCommand:
    as_of_date: date
    source_reported_max_drawdown: Decimal | None
    risk_supportability_state: str | None
    risk_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateDrawdownReviewFromRiskCommand:
    portfolio_id: str
    as_of_date: date
    period_name: str
    evaluated_at_utc: datetime
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_DRAWDOWN_REVIEW_POLICY = DrawdownReviewSignalPolicy(
    policy_version="drawdown-review-attention-v1",
    max_drawdown_threshold=Decimal("-0.08"),
    candidate_score=Decimal("72"),
)


def evaluate_drawdown_review_signal_command(
    command: EvaluateDrawdownReviewSignalCommand,
    *,
    policy: DrawdownReviewSignalPolicy = DEFAULT_DRAWDOWN_REVIEW_POLICY,
) -> SignalEvaluationResult:
    source_input = DrawdownReviewSignalInput(
        as_of_date=command.as_of_date,
        source_reported_max_drawdown=command.source_reported_max_drawdown,
        risk_supportability_state=command.risk_supportability_state,
        risk_ref=command.risk_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_drawdown_review_signal(source_input, policy)


def evaluate_drawdown_review_signal_from_risk(
    command: EvaluateDrawdownReviewFromRiskCommand,
    *,
    risk_source: RiskOpportunitySourcePort,
    policy: DrawdownReviewSignalPolicy = DEFAULT_DRAWDOWN_REVIEW_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = risk_source.fetch_drawdown_evidence(
            RiskDrawdownEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                period_name=command.period_name,
                evaluated_at_utc=command.evaluated_at_utc,
                drawdown_threshold=policy.max_drawdown_threshold,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except RiskSourceEntitlementDenied:
        return evaluate_drawdown_review_signal_command(
            EvaluateDrawdownReviewSignalCommand(
                as_of_date=command.as_of_date,
                source_reported_max_drawdown=None,
                risk_supportability_state=None,
                risk_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=_portfolio_only_scope(command.portfolio_id),
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

    return _evaluate_drawdown_evidence(command, evidence, policy=policy)


def _evaluate_drawdown_evidence(
    command: EvaluateDrawdownReviewFromRiskCommand,
    evidence: RiskDrawdownEvidence,
    *,
    policy: DrawdownReviewSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_drawdown_review_signal_command(
        EvaluateDrawdownReviewSignalCommand(
            as_of_date=command.as_of_date,
            source_reported_max_drawdown=evidence.source_reported_max_drawdown,
            risk_supportability_state=evidence.risk_supportability_state,
            risk_ref=evidence.risk_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=_portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )


def _portfolio_only_scope(portfolio_id: str) -> ReviewAccessScope:
    return ReviewAccessScope(
        tenant_id="unknown",
        book_id="unknown",
        portfolio_id=portfolio_id,
        client_id="unknown",
    )
