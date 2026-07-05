from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain import (
    CandidatePersistenceResult,
    ConcentrationRiskSignalInput,
    ConcentrationRiskSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationResult,
    SignalEvaluationOutcome,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_concentration_risk_signal,
)
from app.application.access_scope import portfolio_only_scope
from app.domain.access_scope import ReviewAccessScope
from app.ports.evidence_payloads import access_scope_payload, source_ref_payload
from app.ports.idea_repository import CandidatePersistenceRepository
from app.ports.risk_sources import (
    RiskConcentrationEvidence,
    RiskConcentrationEvidenceRequest,
    RiskConcentrationSourcePort,
    RiskSourceEntitlementDenied,
    RiskSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateConcentrationRiskSignalCommand:
    as_of_date: date
    top_position_weight_current: Decimal | None
    top_issuer_weight_current: Decimal | None
    issuer_coverage_status: str | None
    concentration_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateConcentrationRiskFromRiskCommand:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class EvaluateAndPersistConcentrationRiskSignalCommand:
    evaluation: EvaluateConcentrationRiskSignalCommand
    idempotency_key: str
    actor_subject: str


@dataclass(frozen=True)
class EvaluateAndPersistConcentrationRiskFromRiskCommand:
    evaluation: EvaluateConcentrationRiskFromRiskCommand
    idempotency_key: str
    actor_subject: str


@dataclass(frozen=True)
class ConcentrationRiskSignalPersistenceResult:
    evaluation: SignalEvaluationResult
    persistence: CandidatePersistenceResult | None
    source_diagnostic_codes: tuple[str, ...] = ()


DEFAULT_CONCENTRATION_RISK_POLICY = ConcentrationRiskSignalPolicy(
    policy_version="concentration-attention-v1",
    top_position_weight_threshold=Decimal("0.15"),
    top_issuer_weight_threshold=Decimal("0.20"),
    candidate_score=Decimal("78"),
)


def evaluate_concentration_risk_signal_command(
    command: EvaluateConcentrationRiskSignalCommand,
    *,
    policy: ConcentrationRiskSignalPolicy = DEFAULT_CONCENTRATION_RISK_POLICY,
) -> SignalEvaluationResult:
    source_input = ConcentrationRiskSignalInput(
        as_of_date=command.as_of_date,
        top_position_weight_current=command.top_position_weight_current,
        top_issuer_weight_current=command.top_issuer_weight_current,
        issuer_coverage_status=command.issuer_coverage_status,
        concentration_ref=command.concentration_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_concentration_risk_signal(source_input, policy)


def evaluate_concentration_risk_signal_from_risk(
    command: EvaluateConcentrationRiskFromRiskCommand,
    *,
    risk_source: RiskConcentrationSourcePort,
    policy: ConcentrationRiskSignalPolicy = DEFAULT_CONCENTRATION_RISK_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = risk_source.fetch_concentration_evidence(
            RiskConcentrationEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except RiskSourceEntitlementDenied:
        return evaluate_concentration_risk_signal_command(
            EvaluateConcentrationRiskSignalCommand(
                as_of_date=command.as_of_date,
                top_position_weight_current=None,
                top_issuer_weight_current=None,
                issuer_coverage_status=None,
                concentration_ref=None,
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
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_concentration_risk_evidence(command, evidence, policy=policy)


def evaluate_and_persist_concentration_risk_signal(
    command: EvaluateAndPersistConcentrationRiskSignalCommand,
    *,
    repository: CandidatePersistenceRepository,
    policy: ConcentrationRiskSignalPolicy = DEFAULT_CONCENTRATION_RISK_POLICY,
) -> ConcentrationRiskSignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    evaluation = evaluate_concentration_risk_signal_command(command.evaluation, policy=policy)
    if evaluation.candidate is None:
        return ConcentrationRiskSignalPersistenceResult(evaluation=evaluation, persistence=None)

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=_idempotency_payload_for_concentration(command.evaluation, policy=policy),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluation.evaluated_at_utc,
    )
    return ConcentrationRiskSignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
    )


def evaluate_and_persist_concentration_risk_signal_from_risk(
    command: EvaluateAndPersistConcentrationRiskFromRiskCommand,
    *,
    risk_source: RiskConcentrationSourcePort,
    repository: CandidatePersistenceRepository,
    policy: ConcentrationRiskSignalPolicy = DEFAULT_CONCENTRATION_RISK_POLICY,
) -> ConcentrationRiskSignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    try:
        evidence = risk_source.fetch_concentration_evidence(
            RiskConcentrationEvidenceRequest(
                portfolio_id=command.evaluation.portfolio_id,
                as_of_date=command.evaluation.as_of_date,
                evaluated_at_utc=command.evaluation.evaluated_at_utc,
                correlation_id=command.evaluation.correlation_id,
                trace_id=command.evaluation.trace_id,
            )
        )
    except RiskSourceEntitlementDenied:
        evaluation = evaluate_concentration_risk_signal_command(
            EvaluateConcentrationRiskSignalCommand(
                as_of_date=command.evaluation.as_of_date,
                top_position_weight_current=None,
                top_issuer_weight_current=None,
                issuer_coverage_status=None,
                concentration_ref=None,
                evaluated_at_utc=command.evaluation.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=portfolio_only_scope(command.evaluation.portfolio_id),
                duplicate_of_candidate_id=command.evaluation.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
        return ConcentrationRiskSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=("risk_source_entitlement_denied",),
        )
    except RiskSourceUnavailable as exc:
        evaluation = SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.CONCENTRATION,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )
        return ConcentrationRiskSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=(exc.code,),
        )

    evaluation = _evaluate_concentration_risk_evidence(command.evaluation, evidence, policy=policy)
    source_diagnostic_codes = _risk_source_diagnostic_codes(evidence)
    if evaluation.candidate is None:
        return ConcentrationRiskSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=source_diagnostic_codes,
        )

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=_idempotency_payload_for_risk_concentration(command.evaluation, evaluation, policy),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluation.evaluated_at_utc,
    )
    return ConcentrationRiskSignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
        source_diagnostic_codes=source_diagnostic_codes,
    )


def _evaluate_concentration_risk_evidence(
    command: EvaluateConcentrationRiskFromRiskCommand,
    evidence: RiskConcentrationEvidence,
    *,
    policy: ConcentrationRiskSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_concentration_risk_signal_command(
        EvaluateConcentrationRiskSignalCommand(
            as_of_date=command.as_of_date,
            top_position_weight_current=evidence.top_position_weight_current,
            top_issuer_weight_current=evidence.top_issuer_weight_current,
            issuer_coverage_status=evidence.issuer_coverage_status,
            concentration_ref=evidence.concentration_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )


def _risk_source_diagnostic_codes(evidence: RiskConcentrationEvidence) -> tuple[str, ...]:
    diagnostic = evidence.concentration_diagnostic
    if isinstance(diagnostic, str) and diagnostic.strip():
        return (diagnostic.strip(),)
    return ()


def _idempotency_payload_for_risk_concentration(
    command: EvaluateConcentrationRiskFromRiskCommand,
    evaluation: SignalEvaluationResult,
    policy: ConcentrationRiskSignalPolicy,
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
        "family": OpportunityFamily.CONCENTRATION.value,
        "portfolio_id": command.portfolio_id,
        "policy_version": policy.policy_version,
        "source_signal_ids": (
            list(evaluation.candidate.source_signal_ids) if evaluation.candidate is not None else []
        ),
        "source_refs": [source_ref_payload(source_ref) for source_ref in source_refs],
    }


def _idempotency_payload_for_concentration(
    command: EvaluateConcentrationRiskSignalCommand,
    *,
    policy: ConcentrationRiskSignalPolicy,
) -> dict[str, Any]:
    return {
        "as_of_date": command.as_of_date.isoformat(),
        "duplicate_of_candidate_id": command.duplicate_of_candidate_id,
        "entitlement_allowed": command.entitlement_allowed,
        "evaluated_at_utc": command.evaluated_at_utc.isoformat(),
        "family": OpportunityFamily.CONCENTRATION.value,
        "policy_version": policy.policy_version,
        "access_scope": access_scope_payload(command.access_scope),
        "issuer_coverage_status": command.issuer_coverage_status,
        "top_issuer_weight_current": (
            str(command.top_issuer_weight_current)
            if command.top_issuer_weight_current is not None
            else None
        ),
        "top_position_weight_current": (
            str(command.top_position_weight_current)
            if command.top_position_weight_current is not None
            else None
        ),
        "source_refs": (
            [source_ref_payload(command.concentration_ref)]
            if command.concentration_ref is not None
            else []
        ),
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
