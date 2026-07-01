from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.domain import (
    CandidatePersistenceResult,
    HighCashSignalInput,
    HighCashSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationResult,
    SignalEvaluationOutcome,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_high_cash_signal,
)
from app.application.access_scope import portfolio_only_scope
from app.domain.access_scope import ReviewAccessScope
from app.ports.core_sources import (
    CoreHighCashEvidence,
    CoreHighCashEvidenceRequest,
    CoreOpportunitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)
from app.ports.evidence_payloads import access_scope_payload, source_ref_payload
from app.ports.idea_repository import CandidatePersistenceRepository


@dataclass(frozen=True)
class EvaluateHighCashSignalCommand:
    as_of_date: date
    source_reported_cash_weight: Decimal | None
    portfolio_state_ref: SourceRef | None
    holdings_ref: SourceRef | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateHighCashFromCoreCommand:
    portfolio_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class EvaluateAndPersistHighCashSignalCommand:
    evaluation: EvaluateHighCashSignalCommand
    idempotency_key: str
    actor_subject: str


@dataclass(frozen=True)
class EvaluateAndPersistHighCashFromCoreCommand:
    evaluation: EvaluateHighCashFromCoreCommand
    idempotency_key: str
    actor_subject: str


@dataclass(frozen=True)
class HighCashSignalPersistenceResult:
    evaluation: SignalEvaluationResult
    persistence: CandidatePersistenceResult | None
    source_diagnostic_codes: tuple[str, ...] = ()


DEFAULT_HIGH_CASH_POLICY = HighCashSignalPolicy(
    policy_version="idle-liquidity-v1",
    cash_weight_threshold=Decimal("0.12"),
    candidate_score=Decimal("82"),
)


def evaluate_high_cash_signal_command(
    command: EvaluateHighCashSignalCommand,
    *,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> SignalEvaluationResult:
    source_input = HighCashSignalInput(
        as_of_date=command.as_of_date,
        source_reported_cash_weight=command.source_reported_cash_weight,
        portfolio_state_ref=command.portfolio_state_ref,
        holdings_ref=command.holdings_ref,
        cash_movement_ref=command.cash_movement_ref,
        cashflow_projection_ref=command.cashflow_projection_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_high_cash_signal(source_input, policy)


def evaluate_high_cash_signal_from_core(
    command: EvaluateHighCashFromCoreCommand,
    *,
    core_source: CoreOpportunitySourcePort,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = core_source.fetch_high_cash_evidence(
            CoreHighCashEvidenceRequest(
                portfolio_id=command.portfolio_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        return evaluate_high_cash_signal_command(
            EvaluateHighCashSignalCommand(
                as_of_date=command.as_of_date,
                source_reported_cash_weight=None,
                portfolio_state_ref=None,
                holdings_ref=None,
                cash_movement_ref=None,
                cashflow_projection_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=portfolio_only_scope(command.portfolio_id),
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except CoreSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_high_cash_core_evidence(command, evidence, policy=policy)


def evaluate_and_persist_high_cash_signal(
    command: EvaluateAndPersistHighCashSignalCommand,
    *,
    repository: CandidatePersistenceRepository,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> HighCashSignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    evaluation = evaluate_high_cash_signal_command(command.evaluation, policy=policy)
    if evaluation.candidate is None:
        return HighCashSignalPersistenceResult(evaluation=evaluation, persistence=None)

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=_idempotency_payload_for_high_cash(command.evaluation, policy=policy),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluation.evaluated_at_utc,
    )
    return HighCashSignalPersistenceResult(evaluation=evaluation, persistence=persistence)


def evaluate_and_persist_high_cash_signal_from_core(
    command: EvaluateAndPersistHighCashFromCoreCommand,
    *,
    core_source: CoreOpportunitySourcePort,
    repository: CandidatePersistenceRepository,
    policy: HighCashSignalPolicy = DEFAULT_HIGH_CASH_POLICY,
) -> HighCashSignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    try:
        evidence = core_source.fetch_high_cash_evidence(
            CoreHighCashEvidenceRequest(
                portfolio_id=command.evaluation.portfolio_id,
                as_of_date=command.evaluation.as_of_date,
                evaluated_at_utc=command.evaluation.evaluated_at_utc,
                correlation_id=command.evaluation.correlation_id,
                trace_id=command.evaluation.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        evaluation = evaluate_high_cash_signal_command(
            EvaluateHighCashSignalCommand(
                as_of_date=command.evaluation.as_of_date,
                source_reported_cash_weight=None,
                portfolio_state_ref=None,
                holdings_ref=None,
                cash_movement_ref=None,
                cashflow_projection_ref=None,
                evaluated_at_utc=command.evaluation.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=portfolio_only_scope(command.evaluation.portfolio_id),
                duplicate_of_candidate_id=command.evaluation.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
        return HighCashSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=("core_source_entitlement_denied",),
        )
    except CoreSourceUnavailable as exc:
        evaluation = SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.HIGH_CASH,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )
        return HighCashSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=(exc.code,),
        )

    evaluation = _evaluate_high_cash_core_evidence(command.evaluation, evidence, policy=policy)
    source_diagnostic_codes = _core_source_diagnostic_codes(evidence)
    if evaluation.candidate is None:
        return HighCashSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            source_diagnostic_codes=source_diagnostic_codes,
        )

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=_idempotency_payload_for_core_high_cash(command.evaluation, evaluation, policy),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.evaluation.evaluated_at_utc,
    )
    return HighCashSignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
        source_diagnostic_codes=source_diagnostic_codes,
    )


def _evaluate_high_cash_core_evidence(
    command: EvaluateHighCashFromCoreCommand,
    evidence: CoreHighCashEvidence,
    *,
    policy: HighCashSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_high_cash_signal_command(
        EvaluateHighCashSignalCommand(
            as_of_date=command.as_of_date,
            source_reported_cash_weight=evidence.source_reported_cash_weight,
            portfolio_state_ref=evidence.portfolio_state_ref,
            holdings_ref=evidence.holdings_ref,
            cash_movement_ref=evidence.cash_movement_ref,
            cashflow_projection_ref=evidence.cashflow_projection_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=portfolio_only_scope(command.portfolio_id),
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )


def _core_source_diagnostic_codes(evidence: CoreHighCashEvidence) -> tuple[str, ...]:
    diagnostic = evidence.cash_weight_diagnostic
    if isinstance(diagnostic, str) and diagnostic.strip():
        return (diagnostic.strip(),)
    return ()


def _idempotency_payload_for_core_high_cash(
    command: EvaluateHighCashFromCoreCommand,
    evaluation: SignalEvaluationResult,
    policy: HighCashSignalPolicy,
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
        "family": OpportunityFamily.HIGH_CASH.value,
        "portfolio_id": command.portfolio_id,
        "policy_version": policy.policy_version,
        "source_signal_ids": (
            list(evaluation.candidate.source_signal_ids) if evaluation.candidate is not None else []
        ),
        "source_refs": [source_ref_payload(source_ref) for source_ref in source_refs],
    }


def _idempotency_payload_for_high_cash(
    command: EvaluateHighCashSignalCommand,
    *,
    policy: HighCashSignalPolicy,
) -> dict[str, Any]:
    return {
        "as_of_date": command.as_of_date.isoformat(),
        "duplicate_of_candidate_id": command.duplicate_of_candidate_id,
        "entitlement_allowed": command.entitlement_allowed,
        "evaluated_at_utc": command.evaluated_at_utc.isoformat(),
        "family": OpportunityFamily.HIGH_CASH.value,
        "policy_version": policy.policy_version,
        "access_scope": access_scope_payload(command.access_scope),
        "source_reported_cash_weight": (
            str(command.source_reported_cash_weight)
            if command.source_reported_cash_weight is not None
            else None
        ),
        "source_refs": [
            source_ref_payload(source_ref)
            for source_ref in (
                command.portfolio_state_ref,
                command.holdings_ref,
                command.cash_movement_ref,
                command.cashflow_projection_ref,
            )
            if source_ref is not None
        ],
    }


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
