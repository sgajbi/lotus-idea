from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidatePersistenceResult,
    CandidateScorePolicyVersion,
    LowIncomeSignalInput,
    LowIncomeSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_low_income_signal,
)
from app.application.access_scope import require_authoritative_scope, tenant_portfolio_scope
from app.application.candidate_evaluation_acceptance import accept_candidate_evaluation
from app.application.candidate_expiry import (
    CandidateExpiryResult,
    ExpireCandidateCommand,
    expire_candidate,
)
from app.application.candidate_persistence_identity import build_candidate_idempotency_payload
from app.application.low_income_source_qualification import (
    low_income_source_qualification_blockers,
)
from app.domain.access_scope import ReviewAccessScope
from app.domain.opportunity_identity import build_opportunity_business_identity
from app.ports.core_sources import (
    CoreLowIncomeEvidence,
    CoreLowIncomeEvidenceRequest,
    CoreLowIncomeSourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)
from app.ports.idea_repository import CandidateEvaluationRepository


@dataclass(frozen=True)
class EvaluateLowIncomeSignalCommand:
    as_of_date: date
    source_reported_min_projected_cumulative_cashflow: Decimal | None
    cash_movement_count: int | None
    cash_movement_ref: SourceRef | None
    cashflow_projection_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None


@dataclass(frozen=True)
class EvaluateLowIncomeFromCoreCommand:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    horizon_days: int = 30
    correlation_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class EvaluateAndPersistLowIncomeFromCoreCommand:
    evaluation: EvaluateLowIncomeFromCoreCommand
    access_scope: ReviewAccessScope
    idempotency_key: str
    actor_subject: str
    accepted_at_utc: datetime


@dataclass(frozen=True)
class LowIncomeSignalPersistenceResult:
    evaluation: SignalEvaluationResult
    persistence: CandidatePersistenceResult | None
    expiry: CandidateExpiryResult | None = None
    source_diagnostic_codes: tuple[str, ...] = ()
    source_evidence: CoreLowIncomeEvidence | None = None


@dataclass(frozen=True)
class _LowIncomeSourceEvaluation:
    evaluation: SignalEvaluationResult
    source_diagnostic_codes: tuple[str, ...] = ()
    source_evidence: CoreLowIncomeEvidence | None = None


DEFAULT_LOW_INCOME_POLICY = LowIncomeSignalPolicy(
    policy_version=CandidateScorePolicyVersion.LOW_INCOME.value,
    projected_cumulative_cashflow_threshold=Decimal("-10000"),
)


def evaluate_low_income_signal_command(
    command: EvaluateLowIncomeSignalCommand,
    *,
    policy: LowIncomeSignalPolicy = DEFAULT_LOW_INCOME_POLICY,
) -> SignalEvaluationResult:
    return evaluate_low_income_signal(
        LowIncomeSignalInput(
            as_of_date=command.as_of_date,
            source_reported_min_projected_cumulative_cashflow=(
                command.source_reported_min_projected_cumulative_cashflow
            ),
            cash_movement_count=command.cash_movement_count,
            cash_movement_ref=command.cash_movement_ref,
            cashflow_projection_ref=command.cashflow_projection_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=command.entitlement_allowed,
            access_scope=command.access_scope,
        ),
        policy,
    )


def evaluate_low_income_signal_from_core(
    command: EvaluateLowIncomeFromCoreCommand,
    *,
    core_source: CoreLowIncomeSourcePort,
    policy: LowIncomeSignalPolicy = DEFAULT_LOW_INCOME_POLICY,
) -> SignalEvaluationResult:
    return _evaluate_low_income_source(
        command,
        core_source=core_source,
        policy=policy,
    ).evaluation


def evaluate_and_persist_low_income_signal_from_core(
    command: EvaluateAndPersistLowIncomeFromCoreCommand,
    *,
    core_source: CoreLowIncomeSourcePort,
    repository: CandidateEvaluationRepository,
    policy: LowIncomeSignalPolicy = DEFAULT_LOW_INCOME_POLICY,
) -> LowIncomeSignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    require_authoritative_scope(command.access_scope)
    if command.access_scope.tenant_id != command.evaluation.tenant_id:
        raise ValueError("access_scope tenant_id must match evaluation tenant_id")
    if command.access_scope.portfolio_id != command.evaluation.portfolio_id:
        raise ValueError("access_scope portfolio_id must match evaluation portfolio_id")

    source_evaluation = _evaluate_low_income_source(
        command.evaluation,
        core_source=core_source,
        policy=policy,
        access_scope=command.access_scope,
        require_runtime_qualification=True,
    )
    evaluation = accept_candidate_evaluation(
        source_evaluation.evaluation,
        accepted_at_utc=command.accepted_at_utc,
    )
    if evaluation.candidate is None:
        return LowIncomeSignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            expiry=_expire_non_eligible_low_income(
                evaluation=evaluation,
                as_of_date=command.evaluation.as_of_date,
                access_scope=command.access_scope,
                actor_subject=command.actor_subject,
                evaluated_at_utc=command.accepted_at_utc,
                repository=repository,
            ),
            source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
            source_evidence=source_evaluation.source_evidence,
        )

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=build_candidate_idempotency_payload(
            portfolio_id=command.evaluation.portfolio_id,
            as_of_date=command.evaluation.as_of_date,
            period_name=f"{command.evaluation.horizon_days}d",
            evaluated_at_utc=command.evaluation.evaluated_at_utc,
            family=OpportunityFamily.LOW_INCOME,
            policy_version=policy.policy_version,
            evaluation=evaluation,
        ),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.accepted_at_utc,
    )
    return LowIncomeSignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
        source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
        source_evidence=source_evaluation.source_evidence,
    )


def _evaluate_low_income_source(
    command: EvaluateLowIncomeFromCoreCommand,
    *,
    core_source: CoreLowIncomeSourcePort,
    policy: LowIncomeSignalPolicy,
    access_scope: ReviewAccessScope | None = None,
    require_runtime_qualification: bool = False,
) -> _LowIncomeSourceEvaluation:
    fallback_scope = access_scope or tenant_portfolio_scope(
        tenant_id=command.tenant_id,
        portfolio_id=command.portfolio_id,
    )
    try:
        evidence = core_source.fetch_low_income_evidence(
            CoreLowIncomeEvidenceRequest(
                portfolio_id=command.portfolio_id,
                tenant_id=command.tenant_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                horizon_days=command.horizon_days,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        return _LowIncomeSourceEvaluation(
            evaluation=evaluate_low_income_signal_command(
                EvaluateLowIncomeSignalCommand(
                    as_of_date=command.as_of_date,
                    source_reported_min_projected_cumulative_cashflow=None,
                    cash_movement_count=None,
                    cash_movement_ref=None,
                    cashflow_projection_ref=None,
                    evaluated_at_utc=command.evaluated_at_utc,
                    entitlement_allowed=False,
                    access_scope=fallback_scope,
                ),
                policy=policy,
            ),
            source_diagnostic_codes=("core_source_entitlement_denied",),
        )
    except CoreSourceUnavailable as exc:
        return _LowIncomeSourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.LOW_INCOME,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            source_diagnostic_codes=(exc.code,),
        )

    source_blockers = (
        low_income_source_qualification_blockers(
            tenant_id=command.tenant_id,
            portfolio_id=command.portfolio_id,
            as_of_date=command.as_of_date,
            evaluated_at_utc=command.evaluated_at_utc,
            horizon_days=command.horizon_days,
            correlation_id=command.correlation_id,
            evidence=evidence,
        )
        if require_runtime_qualification
        else ()
    )
    if source_blockers:
        return _LowIncomeSourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.LOW_INCOME,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            source_diagnostic_codes=source_blockers,
            source_evidence=evidence,
        )

    return _LowIncomeSourceEvaluation(
        evaluation=_evaluate_low_income_core_evidence(
            command,
            evidence,
            policy=policy,
            access_scope=fallback_scope,
        ),
        source_diagnostic_codes=_core_source_diagnostic_codes(evidence),
        source_evidence=evidence,
    )


def _evaluate_low_income_core_evidence(
    command: EvaluateLowIncomeFromCoreCommand,
    evidence: CoreLowIncomeEvidence,
    *,
    policy: LowIncomeSignalPolicy,
    access_scope: ReviewAccessScope | None = None,
) -> SignalEvaluationResult:
    return evaluate_low_income_signal_command(
        EvaluateLowIncomeSignalCommand(
            as_of_date=command.as_of_date,
            source_reported_min_projected_cumulative_cashflow=(
                evidence.source_reported_min_projected_cumulative_cashflow
            ),
            cash_movement_count=evidence.cash_movement_count,
            cash_movement_ref=evidence.cash_movement_ref,
            cashflow_projection_ref=evidence.cashflow_projection_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=access_scope
            or tenant_portfolio_scope(
                tenant_id=command.tenant_id,
                portfolio_id=command.portfolio_id,
            ),
        ),
        policy=policy,
    )


def _core_source_diagnostic_codes(evidence: CoreLowIncomeEvidence) -> tuple[str, ...]:
    diagnostic = evidence.cashflow_diagnostic
    if isinstance(diagnostic, str) and diagnostic.strip():
        return (diagnostic.strip(),)
    return ()


def _expire_non_eligible_low_income(
    *,
    evaluation: SignalEvaluationResult,
    as_of_date: date,
    access_scope: ReviewAccessScope,
    actor_subject: str,
    evaluated_at_utc: datetime,
    repository: CandidateEvaluationRepository,
) -> CandidateExpiryResult | None:
    if evaluation.outcome is not SignalEvaluationOutcome.NOT_ELIGIBLE:
        return None
    business_identity = build_opportunity_business_identity(
        family=OpportunityFamily.LOW_INCOME,
        opportunity_kind="low_income",
        as_of_date=as_of_date,
        access_scope=access_scope,
    )
    reason_codes = tuple(
        dict.fromkeys((ReasonCode.OPPORTUNITY_NO_LONGER_ELIGIBLE, *evaluation.reason_codes))
    )
    return expire_candidate(
        ExpireCandidateCommand(
            candidate_id=business_identity.candidate_id,
            actor_subject=actor_subject,
            evaluated_at_utc=evaluated_at_utc,
            reason_codes=reason_codes,
        ),
        repository=repository,
    )


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} is required")
