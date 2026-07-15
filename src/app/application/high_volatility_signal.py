from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain import (
    CandidatePersistenceResult,
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
from app.ports.evidence_payloads import source_ref_payload
from app.ports.idea_repository import CandidatePersistenceRepository
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


@dataclass(frozen=True)
class EvaluateAndPersistHighVolatilityFromRiskCommand:
    evaluation: EvaluateHighVolatilityFromRiskCommand
    idempotency_key: str
    actor_subject: str


@dataclass(frozen=True)
class HighVolatilitySignalPersistenceResult:
    evaluation: SignalEvaluationResult
    persistence: CandidatePersistenceResult | None
    source_diagnostic_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _HighVolatilitySourceEvaluation:
    evaluation: SignalEvaluationResult
    source_diagnostic_codes: tuple[str, ...] = ()


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
    return _evaluate_high_volatility_source(
        command,
        risk_source=risk_source,
        policy=policy,
    ).evaluation


def evaluate_and_persist_high_volatility_signal_from_risk(
    command: EvaluateAndPersistHighVolatilityFromRiskCommand,
    *,
    risk_source: RiskVolatilitySourcePort,
    repository: CandidatePersistenceRepository,
    policy: HighVolatilitySignalPolicy = DEFAULT_HIGH_VOLATILITY_POLICY,
) -> HighVolatilitySignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    source_evaluation = _evaluate_high_volatility_source(
        command.evaluation,
        risk_source=risk_source,
        policy=policy,
    )
    evaluation = source_evaluation.evaluation
    if evaluation.candidate is None:
        return HighVolatilitySignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
        )

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=_idempotency_payload_for_risk_volatility(command.evaluation, evaluation, policy),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluation.evaluated_at_utc,
    )
    return HighVolatilitySignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
        source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
    )


def _evaluate_high_volatility_source(
    command: EvaluateHighVolatilityFromRiskCommand,
    *,
    risk_source: RiskVolatilitySourcePort,
    policy: HighVolatilitySignalPolicy,
) -> _HighVolatilitySourceEvaluation:
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
        return _HighVolatilitySourceEvaluation(
            evaluation=evaluate_high_volatility_signal_command(
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
            ),
            source_diagnostic_codes=("risk_source_entitlement_denied",),
        )
    except RiskSourceUnavailable as exc:
        return _HighVolatilitySourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.HIGH_VOLATILITY,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            source_diagnostic_codes=(exc.code,),
        )

    return _HighVolatilitySourceEvaluation(
        evaluation=_evaluate_high_volatility_evidence(command, evidence, policy=policy),
        source_diagnostic_codes=_risk_source_diagnostic_codes(evidence),
    )


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


def _risk_source_diagnostic_codes(evidence: RiskVolatilityEvidence) -> tuple[str, ...]:
    diagnostic = evidence.risk_diagnostic
    if isinstance(diagnostic, str) and diagnostic.strip():
        return (diagnostic.strip(),)
    return ()


def _idempotency_payload_for_risk_volatility(
    command: EvaluateHighVolatilityFromRiskCommand,
    evaluation: SignalEvaluationResult,
    policy: HighVolatilitySignalPolicy,
) -> dict[str, Any]:
    source_refs = (
        evaluation.candidate.evidence_packet.source_refs if evaluation.candidate is not None else ()
    )
    return {
        "as_of_date": command.as_of_date.isoformat(),
        "candidate_id": (
            evaluation.candidate.candidate_id if evaluation.candidate is not None else None
        ),
        "evaluated_at_utc": command.evaluated_at_utc.isoformat(),
        "family": OpportunityFamily.HIGH_VOLATILITY.value,
        "period_name": command.period_name,
        "portfolio_id": command.portfolio_id,
        "policy_version": policy.policy_version,
        "source_signal_ids": (
            list(evaluation.candidate.source_signal_ids) if evaluation.candidate is not None else []
        ),
        "source_refs": [source_ref_payload(source_ref) for source_ref in source_refs],
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
