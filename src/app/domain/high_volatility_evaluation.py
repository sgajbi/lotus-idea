from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.ideas import (
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    LineageRef,
    OpportunityFamily,
    OpportunitySignal,
    ReasonCode,
    ReviewPosture,
    SourceRef,
    UnsupportedEvidenceReason,
)
from app.domain.opportunity_identity import OpportunityIdentity, build_opportunity_identity
from app.domain.signal_evaluation_common import (
    blocked_signal_result,
    temporal_blocked_signal_result,
    validate_timezone_aware_evaluation_time,
)
from app.domain.signal_evaluation_models import (
    HighVolatilitySignalInput,
    HighVolatilitySignalPolicy,
    SignalEvaluationOutcome,
    SignalEvaluationResult,
)


@dataclass(frozen=True)
class _HighVolatilityCandidateInputs:
    source_input: HighVolatilitySignalInput
    policy: HighVolatilitySignalPolicy
    source_refs: tuple[SourceRef, ...]
    identity: OpportunityIdentity


def evaluate_high_volatility_signal(
    source_input: HighVolatilitySignalInput,
    policy: HighVolatilitySignalPolicy,
) -> SignalEvaluationResult:
    _validate_evaluation_time(source_input)
    blocking_result = _evaluate_blocking_posture(source_input)
    if blocking_result is not None:
        return blocking_result

    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )

    volatility_result = _source_volatility(source_input)
    if isinstance(volatility_result, SignalEvaluationResult):
        return volatility_result
    volatility = volatility_result
    if volatility < policy.volatility_threshold:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    risk_ref = source_input.risk_ref
    if risk_ref is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    source_refs = (risk_ref,)
    return _candidate_result(
        _HighVolatilityCandidateInputs(
            source_input=source_input,
            policy=policy,
            source_refs=source_refs,
            identity=_stable_high_volatility_identity(source_input, policy, source_refs),
        )
    )


def _validate_evaluation_time(source_input: HighVolatilitySignalInput) -> None:
    validate_timezone_aware_evaluation_time(source_input.evaluated_at_utc)


def _evaluate_blocking_posture(
    source_input: HighVolatilitySignalInput,
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.risk_ref is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )

    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.HIGH_VOLATILITY,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=(source_input.risk_ref,),
    )
    if temporal_block is not None:
        return temporal_block

    if source_input.risk_ref.freshness is not EvidenceFreshness.CURRENT:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.risk_supportability_state is None:
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.risk_supportability_state.lower() != "ready":
        return blocked_signal_result(
            family=OpportunityFamily.HIGH_VOLATILITY,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    return None


def _source_volatility(source_input: HighVolatilitySignalInput) -> Decimal | SignalEvaluationResult:
    if source_input.source_reported_volatility is None:
        return _missing_volatility_result()
    if source_input.source_reported_volatility < Decimal("0"):
        raise ValueError("source_reported_volatility must be non-negative")
    return source_input.source_reported_volatility


def _missing_volatility_result() -> SignalEvaluationResult:
    return blocked_signal_result(
        family=OpportunityFamily.HIGH_VOLATILITY,
        reason_codes=(ReasonCode.SOURCE_PARTIAL,),
        unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
    )


def _candidate_result(inputs: _HighVolatilityCandidateInputs) -> SignalEvaluationResult:
    signal = _opportunity_signal(inputs)
    evidence_packet = _evidence_packet(inputs)
    candidate = IdeaCandidate(
        candidate_id=inputs.identity.candidate_id,
        identity=inputs.identity.initial_candidate_identity(),
        family=OpportunityFamily.HIGH_VOLATILITY,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=inputs.policy.policy_version,
            score=inputs.policy.candidate_score,
            reason_codes=(ReasonCode.VOLATILITY_ATTENTION, ReasonCode.REVIEW_REQUIRED),
        ),
        access_scope=inputs.source_input.access_scope,
        created_at_utc=inputs.source_input.evaluated_at_utc,
        updated_at_utc=inputs.source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.HIGH_VOLATILITY,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _opportunity_signal(inputs: _HighVolatilityCandidateInputs) -> OpportunitySignal:
    return OpportunitySignal(
        signal_id=inputs.identity.signal_id,
        family=OpportunityFamily.HIGH_VOLATILITY,
        source_refs=inputs.source_refs,
        reason_codes=(ReasonCode.VOLATILITY_ATTENTION,),
        detected_at_utc=inputs.source_input.evaluated_at_utc,
    )


def _evidence_packet(inputs: _HighVolatilityCandidateInputs) -> IdeaEvidencePacket:
    lineage = LineageRef(
        lineage_id=inputs.identity.lineage_id,
        source_refs=inputs.source_refs,
        content_hash=inputs.identity.evidence_fingerprint,
    )
    return IdeaEvidencePacket(
        evidence_packet_id=inputs.identity.evidence_packet_id,
        supportability=EvidenceSupportability.READY,
        source_refs=inputs.source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.VOLATILITY_ATTENTION,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=inputs.source_input.evaluated_at_utc,
    )


def _stable_high_volatility_identity(
    source_input: HighVolatilitySignalInput,
    policy: HighVolatilitySignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.HIGH_VOLATILITY,
        opportunity_kind="high_volatility",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "as_of_date": source_input.as_of_date.isoformat(),
            "policy_version": policy.policy_version,
            "risk_supportability_state": source_input.risk_supportability_state,
            "source_reported_volatility": str(source_input.source_reported_volatility),
        },
        source_refs=source_refs,
    )


__all__ = ["evaluate_high_volatility_signal"]
