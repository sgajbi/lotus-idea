from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json

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
    SourceRef,
    UnsupportedEvidenceReason,
)
from app.domain.signal_evaluation import SignalEvaluationOutcome, SignalEvaluationResult


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
    candidate_score: Decimal

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version is required")
        if self.candidate_score < Decimal("0") or self.candidate_score > Decimal("100"):
            raise ValueError("candidate_score must be between 0 and 100")


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
    duplicate_of_candidate_id: str | None = None


def evaluate_mandate_restriction_signal(
    source_input: MandateRestrictionSignalInput,
    policy: MandateRestrictionSignalPolicy,
) -> SignalEvaluationResult:
    if (
        source_input.evaluated_at_utc.tzinfo is None
        or source_input.evaluated_at_utc.utcoffset() is None
    ):
        raise ValueError("evaluated_at_utc must be timezone-aware")

    blocked = _blocking_result(source_input)
    if blocked is not None:
        return blocked
    if source_input.duplicate_of_candidate_id is not None:
        return SignalEvaluationResult(
            outcome=SignalEvaluationOutcome.SUPPRESSED,
            family=OpportunityFamily.MANDATE_RESTRICTION,
            reason_codes=(ReasonCode.DUPLICATE_SUPPRESSED,),
        )
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
        signal_id=f"signal_mandate_restriction_{identity}",
        family=OpportunityFamily.MANDATE_RESTRICTION,
        source_refs=source_refs,
        reason_codes=(ReasonCode.MANDATE_RESTRICTION_REVIEW,),
        detected_at_utc=source_input.evaluated_at_utc,
    )
    lineage = LineageRef(
        lineage_id=f"lineage:lotus-idea:mandate-restriction:{identity}",
        source_refs=source_refs,
        content_hash=f"sha256:{identity}",
    )
    evidence_packet = IdeaEvidencePacket(
        evidence_packet_id=f"iep_mandate_restriction_{identity}",
        supportability=EvidenceSupportability.READY,
        source_refs=source_refs,
        lineage_ref=lineage,
        reason_codes=(ReasonCode.MANDATE_RESTRICTION_REVIEW, ReasonCode.REVIEW_REQUIRED),
        created_at_utc=source_input.evaluated_at_utc,
    )
    candidate = IdeaCandidate(
        candidate_id=f"idea_mandate_restriction_{identity}",
        family=OpportunityFamily.MANDATE_RESTRICTION,
        lifecycle_status=IdeaLifecycleStatus.GENERATED,
        review_posture=ReviewPosture.COMPLIANCE_REVIEW_REQUIRED,
        evidence_packet=evidence_packet,
        source_signal_ids=(signal.signal_id,),
        score=IdeaScore(
            policy_version=policy.policy_version,
            score=policy.candidate_score,
            reason_codes=(ReasonCode.MANDATE_RESTRICTION_REVIEW, ReasonCode.REVIEW_REQUIRED),
        ),
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
) -> str:
    identity_payload = {
        "as_of_date": source_input.as_of_date.isoformat(),
        "family": OpportunityFamily.MANDATE_RESTRICTION.value,
        "policy_version": policy.policy_version,
        "restriction_status": source_input.restriction_status,
        "changed_since_last_review": source_input.changed_since_last_review,
        "actionability_blocked": source_input.actionability_blocked,
        "access_scope": (
            {
                "tenant_id": source_input.access_scope.tenant_id,
                "book_id": source_input.access_scope.book_id,
                "portfolio_id": source_input.access_scope.portfolio_id,
                "client_id": source_input.access_scope.client_id,
            }
            if source_input.access_scope is not None
            else None
        ),
        "source_hashes": [source_ref.content_hash for source_ref in source_refs],
    }
    canonical = json.dumps(identity_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
