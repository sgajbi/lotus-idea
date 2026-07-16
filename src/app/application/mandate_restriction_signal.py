from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidateScorePolicyVersion,
    MandateRestrictionSignalInput,
    MandateRestrictionSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_mandate_restriction_signal,
)
from app.domain.access_scope import ReviewAccessScope
from app.ports.advise_sources import (
    AdviseOpportunitySourcePort,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


RESTRICTION_REVIEW_DIAGNOSTICS = {
    "mandate_restriction_review_required",
    "mandate_restriction_blocked",
    "restriction_review_required",
    "restriction_changed",
    "product_restriction_review_required",
    "product_restriction_changed",
    "country_restriction_review_required",
    "country_restriction_changed",
    "actionability_blocked",
    "suitability_policy_actionability_blocked",
    "policy_restriction_blocked",
    "mandate_breach",
    "restriction_breached",
}


@dataclass(frozen=True)
class EvaluateMandateRestrictionSignalCommand:
    as_of_date: date
    restriction_ref: SourceRef | None
    restriction_status: str | None
    changed_since_last_review: bool | None
    actionability_blocked: bool | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateMandateRestrictionFromAdviseCommand:
    evaluation_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class MandateRestrictionSourceEvaluation:
    command: EvaluateMandateRestrictionFromAdviseCommand
    evidence: AdvisePolicyEvaluationEvidence | None
    evaluation: SignalEvaluationResult
    source_error_code: str | None = None


DEFAULT_MANDATE_RESTRICTION_POLICY = MandateRestrictionSignalPolicy(
    policy_version=CandidateScorePolicyVersion.MANDATE_RESTRICTION.value,
    candidate_score=Decimal("66"),
)


def evaluate_mandate_restriction_signal_command(
    command: EvaluateMandateRestrictionSignalCommand,
    *,
    policy: MandateRestrictionSignalPolicy = DEFAULT_MANDATE_RESTRICTION_POLICY,
) -> SignalEvaluationResult:
    source_input = MandateRestrictionSignalInput(
        as_of_date=command.as_of_date,
        restriction_ref=command.restriction_ref,
        restriction_status=command.restriction_status,
        changed_since_last_review=command.changed_since_last_review,
        actionability_blocked=command.actionability_blocked,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_mandate_restriction_signal(source_input, policy)


def evaluate_mandate_restriction_signal_from_advise(
    command: EvaluateMandateRestrictionFromAdviseCommand,
    *,
    advise_source: AdviseOpportunitySourcePort,
    policy: MandateRestrictionSignalPolicy = DEFAULT_MANDATE_RESTRICTION_POLICY,
) -> SignalEvaluationResult:
    return evaluate_mandate_restriction_readiness_from_advise(
        command,
        advise_source=advise_source,
        policy=policy,
    ).evaluation


def evaluate_mandate_restriction_readiness_from_advise(
    command: EvaluateMandateRestrictionFromAdviseCommand,
    *,
    advise_source: AdviseOpportunitySourcePort,
    policy: MandateRestrictionSignalPolicy = DEFAULT_MANDATE_RESTRICTION_POLICY,
) -> MandateRestrictionSourceEvaluation:
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
        evaluation = evaluate_mandate_restriction_signal_command(
            EvaluateMandateRestrictionSignalCommand(
                as_of_date=command.as_of_date,
                restriction_ref=None,
                restriction_status=None,
                changed_since_last_review=None,
                actionability_blocked=None,
                evaluated_at_utc=command.evaluated_at_utc,
                entitlement_allowed=False,
                access_scope=command.access_scope,
                duplicate_of_candidate_id=command.duplicate_of_candidate_id,
            ),
            policy=policy,
        )
        return MandateRestrictionSourceEvaluation(
            command=command,
            evidence=None,
            evaluation=evaluation,
            source_error_code="advise_source_entitlement_denied",
        )
    except AdviseSourceUnavailable as exc:
        return MandateRestrictionSourceEvaluation(
            command=command,
            evidence=None,
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.MANDATE_RESTRICTION,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            source_error_code=exc.code,
        )

    return MandateRestrictionSourceEvaluation(
        command=command,
        evidence=evidence,
        evaluation=_evaluate_advise_evidence(command, evidence, policy=policy),
    )


def mandate_restriction_review_ready_from_advise_diagnostic(
    advise_diagnostic: str | None,
) -> bool:
    return bool(_restriction_diagnostic_codes(advise_diagnostic) & RESTRICTION_REVIEW_DIAGNOSTICS)


def _evaluate_advise_evidence(
    command: EvaluateMandateRestrictionFromAdviseCommand,
    evidence: AdvisePolicyEvaluationEvidence,
    *,
    policy: MandateRestrictionSignalPolicy,
) -> SignalEvaluationResult:
    restriction_review_ready = mandate_restriction_review_ready_from_advise_diagnostic(
        evidence.advise_diagnostic
    )
    return evaluate_mandate_restriction_signal_command(
        EvaluateMandateRestrictionSignalCommand(
            as_of_date=command.as_of_date,
            restriction_ref=evidence.policy_ref,
            restriction_status="REVIEW_REQUIRED" if restriction_review_ready else "CLEAR",
            changed_since_last_review=restriction_review_ready,
            actionability_blocked=restriction_review_ready,
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=command.access_scope,
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )


def _restriction_diagnostic_codes(advise_diagnostic: str | None) -> set[str]:
    if advise_diagnostic is None:
        return set()
    return {
        code.strip().lower()
        for token in advise_diagnostic.replace(";", ",").replace("|", ",").split(",")
        for code in token.split()
        if code.strip()
    }
