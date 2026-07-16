from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain import (
    CandidateScorePolicyVersion,
    MissingRiskProfileSignalInput,
    MissingRiskProfileSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    RiskProfilePosture,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    SourceRef,
    UnsupportedEvidenceReason,
    evaluate_missing_risk_profile_signal,
    risk_profile_posture_from_advise_diagnostic,
)
from app.domain.access_scope import ReviewAccessScope
from app.ports.advise_sources import (
    AdviseOpportunitySourcePort,
    AdvisePolicyEvaluationEvidence,
    AdvisePolicyEvaluationEvidenceRequest,
    AdviseSourceEntitlementDenied,
    AdviseSourceUnavailable,
)


@dataclass(frozen=True)
class EvaluateMissingRiskProfileSignalCommand:
    as_of_date: date
    risk_profile_ref: SourceRef | None
    risk_profile_status: str | None
    risk_profile_effective_for_as_of_date: bool | None
    risk_profile_review_due: bool | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None


@dataclass(frozen=True)
class EvaluateMissingRiskProfileFromAdviseCommand:
    evaluation_id: str
    as_of_date: date
    evaluated_at_utc: datetime
    access_scope: ReviewAccessScope | None = None
    duplicate_of_candidate_id: str | None = None
    correlation_id: str | None = None
    trace_id: str | None = None


@dataclass(frozen=True)
class MissingRiskProfileSourceEvaluation:
    evaluation: SignalEvaluationResult
    evidence: AdvisePolicyEvaluationEvidence | None
    source_error_code: str | None = None


DEFAULT_MISSING_RISK_PROFILE_POLICY = MissingRiskProfileSignalPolicy(
    policy_version=CandidateScorePolicyVersion.MISSING_RISK_PROFILE.value,
    candidate_score=Decimal("64"),
)


def evaluate_missing_risk_profile_signal_command(
    command: EvaluateMissingRiskProfileSignalCommand,
    *,
    policy: MissingRiskProfileSignalPolicy = DEFAULT_MISSING_RISK_PROFILE_POLICY,
) -> SignalEvaluationResult:
    source_input = MissingRiskProfileSignalInput(
        as_of_date=command.as_of_date,
        risk_profile_ref=command.risk_profile_ref,
        risk_profile_status=command.risk_profile_status,
        risk_profile_effective_for_as_of_date=command.risk_profile_effective_for_as_of_date,
        risk_profile_review_due=command.risk_profile_review_due,
        evaluated_at_utc=command.evaluated_at_utc,
        entitlement_allowed=command.entitlement_allowed,
        access_scope=command.access_scope,
        duplicate_of_candidate_id=command.duplicate_of_candidate_id,
    )
    return evaluate_missing_risk_profile_signal(source_input, policy)


def evaluate_missing_risk_profile_signal_from_advise(
    command: EvaluateMissingRiskProfileFromAdviseCommand,
    *,
    advise_source: AdviseOpportunitySourcePort,
    policy: MissingRiskProfileSignalPolicy = DEFAULT_MISSING_RISK_PROFILE_POLICY,
) -> SignalEvaluationResult:
    return evaluate_missing_risk_profile_readiness_from_advise(
        command,
        advise_source=advise_source,
        policy=policy,
    ).evaluation


def evaluate_missing_risk_profile_readiness_from_advise(
    command: EvaluateMissingRiskProfileFromAdviseCommand,
    *,
    advise_source: AdviseOpportunitySourcePort,
    policy: MissingRiskProfileSignalPolicy = DEFAULT_MISSING_RISK_PROFILE_POLICY,
) -> MissingRiskProfileSourceEvaluation:
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
        return MissingRiskProfileSourceEvaluation(
            evaluation=evaluate_missing_risk_profile_signal_command(
                EvaluateMissingRiskProfileSignalCommand(
                    as_of_date=command.as_of_date,
                    risk_profile_ref=None,
                    risk_profile_status=None,
                    risk_profile_effective_for_as_of_date=None,
                    risk_profile_review_due=None,
                    evaluated_at_utc=command.evaluated_at_utc,
                    entitlement_allowed=False,
                    access_scope=command.access_scope,
                    duplicate_of_candidate_id=command.duplicate_of_candidate_id,
                ),
                policy=policy,
            ),
            evidence=None,
            source_error_code="advise_source_entitlement_denied",
        )
    except AdviseSourceUnavailable as exc:
        return MissingRiskProfileSourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.MISSING_RISK_PROFILE,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
            ),
            evidence=None,
            source_error_code=exc.code,
        )

    try:
        evaluation = _evaluate_advise_evidence(command, evidence, policy=policy)
    except ValueError:
        return MissingRiskProfileSourceEvaluation(
            evaluation=SignalEvaluationResult(
                outcome=SignalEvaluationOutcome.BLOCKED,
                family=OpportunityFamily.MISSING_RISK_PROFILE,
                reason_codes=(ReasonCode.SOURCE_PARTIAL,),
                unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
            ),
            evidence=evidence,
            source_error_code="advise_policy_evidence_invalid",
        )
    return MissingRiskProfileSourceEvaluation(evaluation=evaluation, evidence=evidence)


def _evaluate_advise_evidence(
    command: EvaluateMissingRiskProfileFromAdviseCommand,
    evidence: AdvisePolicyEvaluationEvidence,
    *,
    policy: MissingRiskProfileSignalPolicy,
) -> SignalEvaluationResult:
    posture = risk_profile_posture_from_advise_diagnostic(evidence.advise_diagnostic)
    if posture is None or posture is RiskProfilePosture.CURRENT:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.MISSING_RISK_PROFILE,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )
    return evaluate_missing_risk_profile_signal_command(
        EvaluateMissingRiskProfileSignalCommand(
            as_of_date=command.as_of_date,
            risk_profile_ref=evidence.policy_ref,
            risk_profile_status=posture.value,
            risk_profile_effective_for_as_of_date=posture is not RiskProfilePosture.MISSING,
            risk_profile_review_due=posture
            in {
                RiskProfilePosture.STALE,
                RiskProfilePosture.EXPIRED,
                RiskProfilePosture.REVIEW_DUE,
            },
            evaluated_at_utc=command.evaluated_at_utc,
            entitlement_allowed=evidence.entitlement_allowed,
            access_scope=command.access_scope,
            duplicate_of_candidate_id=command.duplicate_of_candidate_id,
        ),
        policy=policy,
    )
