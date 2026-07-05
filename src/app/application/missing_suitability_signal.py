from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    MissingSuitabilityContextSignalInput,
    MissingSuitabilityContextSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_missing_suitability_context_signal,
)
from app.domain.access_scope import ReviewAccessScope
from app.ports.advise_sources import (
    AdvisePolicyEvaluationSourcePort,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateMissingSuitabilityContextSignalCommand:
    as_of_date: date
    evaluation_status: str | None
    open_requirement_count: int | None
    blocked_requirement_count: int | None
    sign_off_status: str | None
    sign_off_blocker_count: int | None
    client_ready_publication: str | None
    policy_ref: SourceRef | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateMissingSuitabilityContextFromAdviseCommand:
    evaluation_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY = MissingSuitabilityContextSignalPolicy(
    policy_version="missing-suitability-context-review-v1",
    minimum_open_requirement_count=1,
    candidate_score=Decimal("68"),
)


def evaluate_missing_suitability_context_signal_command(
    command: EvaluateMissingSuitabilityContextSignalCommand,
    *,
    policy: MissingSuitabilityContextSignalPolicy = DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY,
) -> SignalEvaluationResult:
    source_input = MissingSuitabilityContextSignalInput(
        as_of_date=command.as_of_date,
        evaluation_status=command.evaluation_status,
        open_requirement_count=command.open_requirement_count,
        blocked_requirement_count=command.blocked_requirement_count,
        sign_off_status=command.sign_off_status,
        sign_off_blocker_count=command.sign_off_blocker_count,
        client_ready_publication=command.client_ready_publication,
        policy_ref=command.policy_ref,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_missing_suitability_context_signal(source_input, policy)


def evaluate_missing_suitability_context_signal_from_advise(
    command: EvaluateMissingSuitabilityContextFromAdviseCommand,
    *,
    advise_source: AdvisePolicyEvaluationSourcePort,
    policy: MissingSuitabilityContextSignalPolicy = DEFAULT_MISSING_SUITABILITY_CONTEXT_POLICY,
) -> SignalEvaluationResult:
    try:
        evidence = advise_source.fetch_policy_evaluation_evidence(
            AdvisePolicyEvaluationEvidenceRequest(
                evaluation_id=command.evaluation_id,
                as_of_date=command.as_of_date,
                evaluated_at_utc=command.evaluated_at_utc,
                correlation_id=command.correlation_id,
                trace_id=command.trace_id,
            )
        )
    except AdviseSourceEntitlementDenied:
        return evaluate_missing_suitability_context_signal_command(
            EvaluateMissingSuitabilityContextSignalCommand(
                as_of_date=command.as_of_date,
                evaluation_status=None,
                open_requirement_count=None,
                blocked_requirement_count=None,
                sign_off_status=None,
                sign_off_blocker_count=None,
                client_ready_publication=None,
                policy_ref=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
    except AdviseSourceUnavailable:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.BLOCKED,
            family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )

    return _evaluate_advise_evidence(command, evidence, policy=policy)


def _evaluate_advise_evidence(
    command: EvaluateMissingSuitabilityContextFromAdviseCommand,
    evidence: AdvisePolicyEvaluationEvidence,
    *,
    policy: MissingSuitabilityContextSignalPolicy,
) -> SignalEvaluationResult:
    return evaluate_missing_suitability_context_signal_command(
        EvaluateMissingSuitabilityContextSignalCommand(
            as_of_date=command.as_of_date,
            evaluation_status=evidence.evaluation_status,
            open_requirement_count=evidence.open_requirement_count,
            blocked_requirement_count=evidence.blocked_requirement_count,
            sign_off_status=evidence.sign_off_status,
            sign_off_blocker_count=evidence.sign_off_blocker_count,
            client_ready_publication=evidence.client_ready_publication,
            policy_ref=evidence.policy_ref,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=command.access_scope,
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )
