from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from app.domain import (
    CandidatePersistenceResult,
    CandidateScorePolicyVersion,
    BondMaturitySignalInput,
    BondMaturitySignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_bond_maturity_signal,
)
from app.application.access_scope import require_authoritative_scope, tenant_portfolio_scope
from app.application.candidate_expiry import (
    CandidateExpiryResult,
    ExpireCandidateCommand,
    expire_candidate,
)
from app.application.candidate_evaluation_acceptance import accept_candidate_evaluation
from app.application.candidate_persistence_identity import build_candidate_idempotency_payload
from app.domain.access_scope import ReviewAccessScope
from app.domain.opportunity_identity import build_opportunity_business_identity
from app.ports.core_sources import (
    CoreBondMaturityEvidence,
    CoreBondMaturityEvidenceRequest,
    CoreBondMaturitySourcePort,
    CoreSourceEntitlementDenied,
    CoreSourceUnavailable,
)
from app.ports.idea_repository import CandidateEvaluationRepository


@dataclass(frozen=True)
class EvaluateBondMaturitySignalCommand:
    as_of_date: date
    source_reported_next_maturity_date: date | None
    source_reported_maturing_position_count: int | None
    holdings_ref: SourceRef | None
    maturity_fact_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None


@dataclass(frozen=True)
class EvaluateBondMaturityFromCoreCommand:
    portfolio_id: str
    tenant_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    maturity_window_days: int = 30
    correlation_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class EvaluateAndPersistBondMaturityFromCoreCommand:
    evaluation: EvaluateBondMaturityFromCoreCommand
    access_scope: ReviewAccessScope
    idempotency_key: str
    actor_subject: str
    accepted_at_utc: datetime


@dataclass(frozen=True)
class BondMaturitySignalPersistenceResult:
    evaluation: SignalEvaluationResult
    persistence: CandidatePersistenceResult | None
    expiry: CandidateExpiryResult | None = None
    source_diagnostic_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class _BondMaturitySourceEvaluation:
    evaluation: SignalEvaluationResult
    source_diagnostic_codes: tuple[str, ...] = ()


DEFAULT_BOND_MATURITY_POLICY = BondMaturitySignalPolicy(
    policy_version=CandidateScorePolicyVersion.BOND_MATURITY.value,
    maturity_window_days=30,
)


def evaluate_bond_maturity_signal_command(
    command: EvaluateBondMaturitySignalCommand,
    *,
    policy: BondMaturitySignalPolicy = DEFAULT_BOND_MATURITY_POLICY,
) -> SignalEvaluationResult:
    return evaluate_bond_maturity_signal(
        BondMaturitySignalInput(
            as_of_date=command.as_of_date,
            source_reported_next_maturity_date=command.source_reported_next_maturity_date,
            source_reported_maturing_position_count=(
                command.source_reported_maturing_position_count
            ),
            holdings_ref=command.holdings_ref,
            maturity_fact_ref=command.maturity_fact_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=command.entitlement_allowed,
            access_scope=command.access_scope,
        ),
        policy,
    )


def evaluate_bond_maturity_signal_from_core(
    command: EvaluateBondMaturityFromCoreCommand,
    *,
    core_source: CoreBondMaturitySourcePort,
    policy: BondMaturitySignalPolicy = DEFAULT_BOND_MATURITY_POLICY,
) -> SignalEvaluationResult:
    return _evaluate_bond_maturity_source(
        command,
        core_source=core_source,
        policy=policy,
    ).evaluation


def evaluate_and_persist_bond_maturity_signal_from_core(
    command: EvaluateAndPersistBondMaturityFromCoreCommand,
    *,
    core_source: CoreBondMaturitySourcePort,
    repository: CandidateEvaluationRepository,
    policy: BondMaturitySignalPolicy = DEFAULT_BOND_MATURITY_POLICY,
) -> BondMaturitySignalPersistenceResult:
    _require_text(command.idempotency_key, "idempotency_key")
    _require_text(command.actor_subject, "actor_subject")
    require_authoritative_scope(command.access_scope)
    if command.access_scope.tenant_id != command.evaluation.tenant_id:
        raise ValueError("access_scope tenant_id must match evaluation tenant_id")
    if command.access_scope.portfolio_id != command.evaluation.portfolio_id:
        raise ValueError("access_scope portfolio_id must match evaluation portfolio_id")

    source_evaluation = _evaluate_bond_maturity_source(
        command.evaluation,
        core_source=core_source,
        policy=policy,
        access_scope=command.access_scope,
    )
    evaluation = accept_candidate_evaluation(
        source_evaluation.evaluation,
        accepted_at_utc=command.accepted_at_utc,
    )
    if evaluation.candidate is None:
        return BondMaturitySignalPersistenceResult(
            evaluation=evaluation,
            persistence=None,
            expiry=_expire_non_eligible_bond_maturity(
                evaluation=evaluation,
                as_of_date=command.evaluation.as_of_date,
                access_scope=command.access_scope,
                actor_subject=command.actor_subject,
                evaluated_at_utc=command.accepted_at_utc,
                repository=repository,
            ),
            source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
        )

    persistence = repository.persist_candidate(
        evaluation.candidate,
        idempotency_key=command.idempotency_key,
        payload=build_candidate_idempotency_payload(
            portfolio_id=command.evaluation.portfolio_id,
            as_of_date=command.evaluation.as_of_date,
            period_name=f"{command.evaluation.maturity_window_days}d",
            evaluated_at_utc=command.evaluation.evaluated_at_utc,
            family=OpportunityFamily.BOND_MATURITY,
            policy_version=policy.policy_version,
            evaluation=evaluation,
        ),
        actor_subject=command.actor_subject,
        occurred_at_utc=command.accepted_at_utc,
    )
    return BondMaturitySignalPersistenceResult(
        evaluation=evaluation,
        persistence=persistence,
        source_diagnostic_codes=source_evaluation.source_diagnostic_codes,
    )


def _evaluate_bond_maturity_source(
    command: EvaluateBondMaturityFromCoreCommand,
    *,
    core_source: CoreBondMaturitySourcePort,
    policy: BondMaturitySignalPolicy,
    access_scope: ReviewAccessScope | None = None,
) -> _BondMaturitySourceEvaluation:
    fallback_scope = access_scope or tenant_portfolio_scope(
        tenant_id=command.tenant_id,
        portfolio_id=command.portfolio_id,
    )
    try:
        evidence = core_source.fetch_bond_maturity_evidence(
            CoreBondMaturityEvidenceRequest(
                portfolio_id=command.portfolio_id,
                tenant_id=command.tenant_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                maturity_window_days=command.maturity_window_days,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except CoreSourceEntitlementDenied:
        return _BondMaturitySourceEvaluation(
            evaluation=evaluate_bond_maturity_signal_command(
                EvaluateBondMaturitySignalCommand(
                    as_of_date=command.as_of_date,
                    source_reported_next_maturity_date=None,
                    source_reported_maturing_position_count=None,
                    holdings_ref=None,
                    maturity_fact_ref=None,
                    evaluated_at_utc=command.evaluated_at_utc,
                    entitlement_allowed=False,
                    access_scope=fallback_scope,
                ),
                policy=policy,
            ),
            source_diagnostic_codes=("core_source_entitlement_denied",),
        )
    except CoreSourceUnavailable as exc:
        return _BondMaturitySourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.BOND_MATURITY,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            source_diagnostic_codes=(exc.code,),
        )

    return _BondMaturitySourceEvaluation(
        evaluation=_evaluate_bond_maturity_core_evidence(
            command,
            evidence,
            policy=policy,
            access_scope=fallback_scope,
        ),
        source_diagnostic_codes=_core_source_diagnostic_codes(evidence),
    )


def _evaluate_bond_maturity_core_evidence(
    command: EvaluateBondMaturityFromCoreCommand,
    evidence: CoreBondMaturityEvidence,
    *,
    policy: BondMaturitySignalPolicy,
    access_scope: ReviewAccessScope | None = None,
) -> SignalEvaluationResult:
    return evaluate_bond_maturity_signal_command(
        EvaluateBondMaturitySignalCommand(
            as_of_date=command.as_of_date,
            source_reported_next_maturity_date=evidence.source_reported_next_maturity_date,
            source_reported_maturing_position_count=(
                evidence.source_reported_maturing_position_count
            ),
            holdings_ref=evidence.holdings_ref,
            maturity_fact_ref=evidence.maturity_fact_ref,
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


def _core_source_diagnostic_codes(evidence: CoreBondMaturityEvidence) -> tuple[str, ...]:
    diagnostic = evidence.maturity_diagnostic
    if isinstance(diagnostic, str) and diagnostic.strip():
        return (diagnostic.strip(),)
    return ()


def _expire_non_eligible_bond_maturity(
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
        family=OpportunityFamily.BOND_MATURITY,
        opportunity_kind="bond_maturity",
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
