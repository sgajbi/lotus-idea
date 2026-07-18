from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidatePersistenceResult,
    CandidateScorePolicyVersion,
    DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY,
    DrawdownReviewSignalInput,
    DrawdownReviewSignalPolicy,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_drawdown_review_signal,
)
from app.application.access_scope import portfolio_only_scope
from app.domain.access_scope import ReviewAccessScope
from app.application.risk_runtime_evidence import build_risk_candidate_idempotency_payload
from app.ports.idea_repository import CandidatePersistenceRepository
from app.ports.risk_sources import (
    RiskDrawdownSourcePort,
    RiskDrawdownEvidence,
    RiskDrawdownEvidenceRequest,
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


@dataclass(frozen=True)
class EvaluateAndPersistDrawdownReviewFromRiskCommand:
    evaluation: EvaluateDrawdownReviewFromRiskCommand
    idempotency_key: str
    actor_subject: str


@dataclass(frozen=True)
class DrawdownReviewSignalPersistenceResult:
    evaluation: SignalEvaluationResult
    persistence: CandidatePersistenceResult | None
    source_diagnostic_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _DrawdownReviewSourceEvaluation:
    evaluation: SignalEvaluationResult
    source_diagnostic_codes: tuple[str, ...] = ()


DEFAULT_DRAWDOWN_REVIEW_POLICY = DrawdownReviewSignalPolicy(
    policy_version=CandidateScorePolicyVersion.DRAWDOWN_REVIEW.value,
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
    risk_source: RiskDrawdownSourcePort,
    policy: DrawdownReviewSignalPolicy = DEFAULT_DRAWDOWN_REVIEW_POLICY,
) -> SignalEvaluationResult:
    return _evaluate_drawdown_review_source(
        command,
        risk_source=risk_source,
        policy=policy,
    ).evaluation


def evaluate_and_persist_drawdown_review_signal_from_risk(
    command: EvaluateAndPersistDrawdownReviewFromRiskCommand,
    *,
    risk_source: RiskDrawdownSourcePort,
    repository: CandidatePersistenceRepository,
    policy: DrawdownReviewSignalPolicy = DEFAULT_DRAWDOWN_REVIEW_POLICY,
) -> DrawdownReviewSignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    source_evaluation = _evaluate_drawdown_review_source(
        command.evaluation,
        risk_source=risk_source,
        policy=policy,
    )
    evaluation = source_evaluation.evaluation
    if evaluation.candidate is None:
        return DrawdownReviewSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
        )

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=build_risk_candidate_idempotency_payload(
            portfolio_id=command.evaluation.portfolio_id,
            as_of_date=command.evaluation.as_of_date,
            period_name=command.evaluation.period_name,
            evaluated_at_utc=command.evaluation.evaluated_at_utc,
            family=DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family,
            policy_version=policy.policy_version,
            evaluation=evaluation,
        ),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluation.evaluated_at_utc,
    )
    return DrawdownReviewSignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
        source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
    )


def _evaluate_drawdown_review_source(
    command: EvaluateDrawdownReviewFromRiskCommand,
    *,
    risk_source: RiskDrawdownSourcePort,
    policy: DrawdownReviewSignalPolicy,
) -> _DrawdownReviewSourceEvaluation:
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
        return _DrawdownReviewSourceEvaluation(
            evaluation=evaluate_drawdown_review_signal_command(
                EvaluateDrawdownReviewSignalCommand(
                    as_of_date=command.as_of_date,
                    source_reported_max_drawdown=None,
                    risk_supportability_state=None,
                    risk_ref=None,
                    evaluated_at_utc=command.evaluated_at_utc,
                    entitlement_allowed=False,
                    access_scope=portfolio_only_scope(command.portfolio_id),
                    duplicate_of_candidate_id=command.duplicate_of_candidate_id,
                ),
                policy=policy,
            ),
            source_diagnostic_codes=("risk_source_entitlement_denied",),
        )
    except RiskSourceUnavailable as exc:
        return _DrawdownReviewSourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=DRAWDOWN_REVIEW_FAMILY_COMPATIBILITY.family,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            source_diagnostic_codes=(exc.code,),
        )

    return _DrawdownReviewSourceEvaluation(
        evaluation=_evaluate_drawdown_evidence(command, evidence, policy=policy),
        source_diagnostic_codes=_risk_source_diagnostic_codes(evidence),
    )


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
            access_scope=portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )


def _risk_source_diagnostic_codes(evidence: RiskDrawdownEvidence) -> tuple[str, ...]:
    diagnostic = evidence.risk_diagnostic
    if isinstance(diagnostic, str) and diagnostic.strip():
        return (diagnostic.strip(),)
    return ()


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
