from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.domain.access_scope import ReviewAccessScope
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
    ScoreComponent,
    SourceRef,
    UnsupportedEvidenceReason,
)
from app.domain.opportunity_identity import OpportunityIdentity, build_opportunity_identity
from app.domain.scoring import (
    IdeaScoringInput,
    IdeaScoringPolicy,
    relative_threshold_score,
    score_inputs,
)
from app.domain.signal_evaluation import (
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    blocked_signal_result,
    temporal_blocked_signal_result,
)


@dataclass(frozen=True)
class MissingSuitabilityContextSignalPolicy:
    policy_version: str
    minimum_open_requirement_count: int

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.minimum_open_requirement_count < 0:
            raise ValueError("minimum_open_requirement_count must be non-negative")


@dataclass(frozen=True)
class MissingSuitabilityContextSignalInput:
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


def evaluate_missing_suitability_context_signal(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
) -> SignalEvaluationResult:
    _validate_evaluated_at(source_input.evaluated_at_utc)
    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=((source_input.policy_ref,) if source_input.policy_ref else ()),
    )
    if temporal_block is not None:
        return temporal_block
    blocked = _blocking_result(source_input)
    if blocked is not None:
        return blocked
    validate_missing_suitability_counts(source_input)
    if not missing_suitability_review_required(source_input, policy):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    return _candidate_result(source_input, policy)


def _validate_evaluated_at(evaluated_at_utc: datetime) -> None:
    if evaluated_at_utc.tzinfo is None or evaluated_at_utc.utcoffset() is None:
        raise ValueError("evaluated_at_utc must be timezone-aware")


def _blocking_result(
    source_input: MissingSuitabilityContextSignalInput,
) -> SignalEvaluationResult | None:
    family = OpportunityFamily.MISSING_SUITABILITY_CONTEXT
    if not source_input.entitlement_allowed:
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.policy_ref is None:
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.policy_ref.freshness is not EvidenceFreshness.CURRENT:
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if source_input.client_ready_publication is None:
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.client_ready_publication.upper() != "BLOCKED":
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,),
        )
    if source_input.evaluation_status is None or source_input.sign_off_status is None:
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if (
        source_input.open_requirement_count is None
        or source_input.blocked_requirement_count is None
        or source_input.sign_off_blocker_count is None
    ):
        return blocked_signal_result(
            family=family,
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def validate_missing_suitability_counts(
    source_input: MissingSuitabilityContextSignalInput,
) -> None:
    for field_name, value in (
        ("open_requirement_count", source_input.open_requirement_count),
        ("blocked_requirement_count", source_input.blocked_requirement_count),
        ("sign_off_blocker_count", source_input.sign_off_blocker_count),
    ):
        if value is None:
            raise ValueError(f"{field_name} must be available after blocking validation")
        if value < 0:
            raise ValueError(f"{field_name} must be non-negative")


def missing_suitability_review_required(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
) -> bool:
    assert source_input.evaluation_status is not None
    assert source_input.sign_off_status is not None
    assert source_input.open_requirement_count is not None
    assert source_input.blocked_requirement_count is not None
    assert source_input.sign_off_blocker_count is not None
    return missing_suitability_review_required_from_workflow(
        evaluation_status=source_input.evaluation_status,
        open_requirement_count=source_input.open_requirement_count,
        blocked_requirement_count=source_input.blocked_requirement_count,
        sign_off_status=source_input.sign_off_status,
        sign_off_blocker_count=source_input.sign_off_blocker_count,
        minimum_open_requirement_count=policy.minimum_open_requirement_count,
    )


def missing_suitability_review_required_from_workflow(
    *,
    evaluation_status: str,
    open_requirement_count: int,
    blocked_requirement_count: int,
    sign_off_status: str,
    sign_off_blocker_count: int,
    minimum_open_requirement_count: int,
) -> bool:
    return (
        evaluation_status.upper() in {"PENDING_REVIEW", "BLOCKED"}
        or sign_off_status.upper() in {"PENDING_REVIEW", "BLOCKED"}
        or open_requirement_count >= minimum_open_requirement_count
        or blocked_requirement_count > 0
        or sign_off_blocker_count > 0
    )


def _candidate_result(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
) -> SignalEvaluationResult:
    assert source_input.policy_ref is not None
    source_refs = (source_input.policy_ref,)
    identity = _stable_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=identity.signal_id,
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        source_refs=source_refs,
        reason_codes=(ReasonCode.SUITABILITY_CONTEXT_MISSING,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=identity.lineage_id,
        source_refs=source_refs,
        content_hash=identity.evidence_fingerprint,
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=identity.evidence_packet_id,
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(
            ReasonCode.SUITABILITY_CONTEXT_MISSING,
            ReasonCode.REVIEW_REQUIRED,
        ),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=identity.candidate_id,
        identity=identity.initial_candidate_identity(),
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=_missing_suitability_score(source_input, policy),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _missing_suitability_score(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
) -> IdeaScore:
    open_count = source_input.open_requirement_count
    blocked_count = source_input.blocked_requirement_count
    sign_off_blockers = source_input.sign_off_blocker_count
    if open_count is None or blocked_count is None or sign_off_blockers is None:
        raise ValueError("eligible missing-suitability scoring requires requirement counts")
    if policy.minimum_open_requirement_count == 0:
        relevance = Decimal("100") if open_count > 0 else Decimal("50")
    elif open_count >= policy.minimum_open_requirement_count:
        relevance = relative_threshold_score(
            Decimal(open_count),
            Decimal(policy.minimum_open_requirement_count),
        )
    else:
        relevance = Decimal("50")
    evaluation_status = (source_input.evaluation_status or "").strip().upper()
    sign_off_status = (source_input.sign_off_status or "").strip().upper()
    if (
        blocked_count > 0
        or sign_off_blockers > 0
        or "BLOCKED" in {evaluation_status, sign_off_status}
    ):
        urgency = Decimal("100")
    else:
        urgency = Decimal("75")
    return score_inputs(
        (
            IdeaScoringInput(ScoreComponent.RELEVANCE, relevance, Decimal("0.50")),
            IdeaScoringInput(ScoreComponent.URGENCY, urgency, Decimal("0.30")),
            IdeaScoringInput(ScoreComponent.EVIDENCE_QUALITY, Decimal("100"), Decimal("0.10")),
            IdeaScoringInput(ScoreComponent.FRESHNESS, Decimal("100"), Decimal("0.10")),
        ),
        policy=IdeaScoringPolicy(policy_version=policy.policy_version),
        reason_codes=(ReasonCode.SUITABILITY_CONTEXT_MISSING, ReasonCode.REVIEW_REQUIRED),
    )


def _stable_identity(
    source_input: MissingSuitabilityContextSignalInput,
    policy: MissingSuitabilityContextSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.MISSING_SUITABILITY_CONTEXT,
        opportunity_kind="missing_suitability_context",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "blocked_requirement_count": source_input.blocked_requirement_count,
            "client_ready_publication": (source_input.client_ready_publication or "")
            .strip()
            .upper(),
            "evaluation_status": (source_input.evaluation_status or "").strip().upper(),
            "open_requirement_count": source_input.open_requirement_count,
            "policy_version": policy.policy_version,
            "sign_off_blocker_count": source_input.sign_off_blocker_count,
            "sign_off_status": (source_input.sign_off_status or "").strip().upper(),
        },
        source_refs=source_refs,
    )
