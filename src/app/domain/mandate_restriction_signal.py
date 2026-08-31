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
from app.domain.scoring import IdeaScoringInput, IdeaScoringPolicy, score_inputs
from app.domain.signal_evaluation import (
    SignalEvaluationOutcome,
    SignalEvaluationResult,
    temporal_blocked_signal_result,
)


_ACTIONABLE_RESTRICTION_STATUSES = {
    "BLOCKED",
    "BREACHED",
    "REVIEW_REQUIRED",
    "RESTRICTION_CHANGED",
    "POLICY_CHANGED",
    "PENDING_REVIEW",
}
_NON_ACTIONABLE_RESTRICTION_STATUSES = {
    "CLEAR",
    "CURRENT",
    "NO_RESTRICTION",
    "WITHIN_MANDATE",
}


@dataclass(frozen=True)
class MandateRestrictionSignalPolicy:
    policy_version: str

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")


@dataclass(frozen=True)
class MandateRestrictionSignalInput:
    as_of_date: date
    restriction_ref: SourceRef | None
    restriction_status: str | None
    changed_since_last_review: bool | None
    actionability_blocked: bool | None
    evaluated_at_utc: datetime
    entitlement_allowed: bool = True
    access_scope: ReviewAccessScope | None = None


def evaluate_mandate_restriction_signal(
    source_input: MandateRestrictionSignalInput,
    policy: MandateRestrictionSignalPolicy,
) -> SignalEvaluationResult:
    if (
        source_input.evaluated_at_utc.tzinfo is None
        or source_input.evaluated_at_utc.utcoffset() is None
    ):
        raise ValueError("evaluated_at_utc must be timezone-aware")

    temporal_block = temporal_blocked_signal_result(
        family=OpportunityFamily.MANDATE_RESTRICTION,
        as_of_date=source_input.as_of_date,
        evaluated_at_utc=source_input.evaluated_at_utc,
        source_refs=((source_input.restriction_ref,) if source_input.restriction_ref else ()),
    )
    if temporal_block is not None:
        return temporal_block

    blocked = _blocking_result(source_input)
    if blocked is not None:
        return blocked
    if not _restriction_review_required(source_input):
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.NOT_ELIGIBLE,
            family=OpportunityFamily.MANDATE_RESTRICTION,
            reason_codes=(ReasonCode.BELOW_MATERIALITY,),
        )

    return _candidate_result(source_input, policy)


def _blocking_result(
    source_input: MandateRestrictionSignalInput,
) -> SignalEvaluationResult | None:
    if not source_input.entitlement_allowed:
        return _blocked(
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            unsupported_reasons=(UnsupportedEvidenceReason.ENTITLEMENT_DENIED,),
        )
    if source_input.restriction_ref is None:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    if source_input.restriction_ref.freshness is not EvidenceFreshness.CURRENT:
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_STALE,),
            unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
        )
    if (
        source_input.restriction_status is None
        or source_input.changed_since_last_review is None
        or source_input.actionability_blocked is None
    ):
        return _blocked(
            reason_codes=(ReasonCode.SOURCE_PARTIAL,),
            unsupported_reasons=(UnsupportedEvidenceReason.MISSING_SOURCE,),
        )
    return None


def _restriction_review_required(source_input: MandateRestrictionSignalInput) -> bool:
    assert source_input.restriction_status is not None
    assert source_input.changed_since_last_review is not None
    assert source_input.actionability_blocked is not None
    normalized_status = source_input.restriction_status.upper()
    if normalized_status in _NON_ACTIONABLE_RESTRICTION_STATUSES:
        return source_input.changed_since_last_review or source_input.actionability_blocked
    return (
        normalized_status in _ACTIONABLE_RESTRICTION_STATUSES
        or source_input.changed_since_last_review
        or source_input.actionability_blocked
    )


def _candidate_result(
    source_input: MandateRestrictionSignalInput,
    policy: MandateRestrictionSignalPolicy,
) -> SignalEvaluationResult:
    assert source_input.restriction_ref is not None
    source_refs = (source_input.restriction_ref,)
    identity = _stable_mandate_restriction_identity(source_input, policy, source_refs)
    signal = OpportunitySignal(
        signal_id=identity.signal_id,
        family=OpportunityFamily.MANDATE_RESTRICTION,
        source_refs=source_refs,
        reason_codes=(ReasonCode.MANDATE_RESTRICTION_REVIEW,),
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
        reason_codes=(ReasonCode.MANDATE_RESTRICTION_REVIEW, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=identity.candidate_id,
        identity=identity.initial_candidate_identity(),
        family=OpportunityFamily.MANDATE_RESTRICTION,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=_mandate_restriction_score(source_input, policy),
        access_scope=source_input.access_scope,
        created_at_utc=source_input.evaluated_at_utc,
        updated_at_utc=source_input.evaluated_at_utc,
    )
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.CANDIDATE_CREATED,
        family=OpportunityFamily.MANDATE_RESTRICTION,
        reason_codes=evidence_packet.reason_codes,
        signal=signal,
        candidate=candidate,
    )


def _mandate_restriction_score(
    source_input: MandateRestrictionSignalInput,
    policy: MandateRestrictionSignalPolicy,
) -> IdeaScore:
    status = (source_input.restriction_status or "").strip().upper()
    relevance_by_status = {
        "BREACHED": Decimal("100"),
        "BLOCKED": Decimal("95"),
        "POLICY_CHANGED": Decimal("85"),
        "RESTRICTION_CHANGED": Decimal("85"),
        "REVIEW_REQUIRED": Decimal("75"),
        "PENDING_REVIEW": Decimal("70"),
    }
    relevance = relevance_by_status.get(status, Decimal("65"))
    if source_input.actionability_blocked:
        urgency = Decimal("100")
    elif status in {"BREACHED", "BLOCKED"}:
        urgency = Decimal("95")
    elif source_input.changed_since_last_review:
        urgency = Decimal("85")
    else:
        urgency = Decimal("70")
    return score_inputs(
        (
            IdeaScoringInput(ScoreComponent.RELEVANCE, relevance, Decimal("0.55")),
            IdeaScoringInput(ScoreComponent.URGENCY, urgency, Decimal("0.25")),
            IdeaScoringInput(ScoreComponent.EVIDENCE_QUALITY, Decimal("100"), Decimal("0.10")),
            IdeaScoringInput(ScoreComponent.FRESHNESS, Decimal("100"), Decimal("0.10")),
        ),
        policy=IdeaScoringPolicy(policy_version=policy.policy_version),
        reason_codes=(ReasonCode.MANDATE_RESTRICTION_REVIEW, ReasonCode.REVIEW_REQUIRED),
    )


def _blocked(
    *,
    reason_codes: tuple[ReasonCode, ...],
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...],
) -> SignalEvaluationResult:
    return SignalEvaluationResult(
        outcome=SignalEvaluationOutcome.BLOCKED,
        family=OpportunityFamily.MANDATE_RESTRICTION,
        reason_codes=reason_codes,
        unsupported_reasons=unsupported_reasons,
    )


def _stable_mandate_restriction_identity(
    source_input: MandateRestrictionSignalInput,
    policy: MandateRestrictionSignalPolicy,
    source_refs: tuple[SourceRef, ...],
) -> OpportunityIdentity:
    return build_opportunity_identity(
        family=OpportunityFamily.MANDATE_RESTRICTION,
        opportunity_kind="mandate_restriction",
        as_of_date=source_input.as_of_date,
        access_scope=source_input.access_scope,
        material_facts={
            "actionability_blocked": source_input.actionability_blocked,
            "as_of_date": source_input.as_of_date.isoformat(),
            "changed_since_last_review": source_input.changed_since_last_review,
            "policy_version": policy.policy_version,
            "restriction_status": (source_input.restriction_status or "").strip().upper(),
        },
        source_refs=source_refs,
    )
