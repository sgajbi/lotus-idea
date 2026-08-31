from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from app.domain.ideas import (
    CandidateChangeReason,
    CandidateIdentity,
    IdeaCandidate,
    IdeaLifecycleStatus,
)
from app.domain.persistence_models import CandidatePersistenceDecision
from app.domain.opportunity_identity import (
    OPPORTUNITY_IDENTITY_POLICY_VERSION,
    PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION,
)


REOPENABLE_TERMINAL_STATUSES = frozenset(
    {
        IdeaLifecycleStatus.ACCEPTED,
        IdeaLifecycleStatus.REJECTED,
        IdeaLifecycleStatus.EXPIRED,
        IdeaLifecycleStatus.EXECUTED,
        IdeaLifecycleStatus.CLOSED,
    }
)


@dataclass(frozen=True)
class CandidateReconciliation:
    decision: CandidatePersistenceDecision
    candidate: IdeaCandidate | None


def reconcile_candidate(
    *,
    existing: IdeaCandidate,
    incoming: IdeaCandidate,
    existing_evidence_hash: str,
    incoming_evidence_hash: str,
    occurred_at_utc: datetime,
) -> CandidateReconciliation:
    """Reconcile one detected condition against its governed business aggregate."""
    if not _same_business_scope(existing, incoming):
        return CandidateReconciliation(
            decision=CandidatePersistenceDecision.IDENTITY_CONFLICT,
            candidate=None,
        )

    if existing.identity.policy_version != incoming.identity.policy_version:
        if not _is_supported_policy_upgrade(existing, incoming):
            return CandidateReconciliation(
                decision=CandidatePersistenceDecision.IDENTITY_CONFLICT,
                candidate=None,
            )
        return CandidateReconciliation(
            decision=CandidatePersistenceDecision.EVIDENCE_REFRESHED,
            candidate=_backfill_identity_policy(
                existing=existing,
                incoming=incoming,
                occurred_at_utc=occurred_at_utc,
            ),
        )

    material_changed = (
        incoming.identity.material_fingerprint != existing.identity.material_fingerprint
    )
    if not material_changed and (
        incoming.evidence_packet.applicability_expires_at_utc
        != existing.evidence_packet.applicability_expires_at_utc
    ):
        return CandidateReconciliation(
            decision=CandidatePersistenceDecision.IDENTITY_CONFLICT,
            candidate=None,
        )
    evidence_changed = incoming_evidence_hash != existing_evidence_hash
    if not material_changed and not evidence_changed:
        return CandidateReconciliation(
            decision=CandidatePersistenceDecision.DUPLICATE_CANDIDATE,
            candidate=None,
        )

    if material_changed and existing.lifecycle_status in REOPENABLE_TERMINAL_STATUSES:
        return CandidateReconciliation(
            decision=CandidatePersistenceDecision.RECURRENT_CONDITION_REOPENED,
            candidate=_new_material_version(
                existing=existing,
                incoming=incoming,
                occurred_at_utc=occurred_at_utc,
                reason=CandidateChangeReason.RECURRENT_CONDITION,
            ),
        )

    if material_changed:
        return CandidateReconciliation(
            decision=CandidatePersistenceDecision.MATERIAL_VERSION_CREATED,
            candidate=_new_material_version(
                existing=existing,
                incoming=incoming,
                occurred_at_utc=occurred_at_utc,
                reason=CandidateChangeReason.MATERIAL_CHANGE,
            ),
        )

    identity = replace(
        existing.identity,
        evidence_version=existing.identity.evidence_version + 1,
        change_reason=CandidateChangeReason.EVIDENCE_CORRECTION,
        supersedes_material_version=None,
    )
    return CandidateReconciliation(
        decision=CandidatePersistenceDecision.EVIDENCE_REFRESHED,
        candidate=replace(
            incoming,
            identity=identity,
            lifecycle_status=existing.lifecycle_status,
            review_posture=existing.review_posture,
            suppression_reason=existing.suppression_reason,
            created_at_utc=existing.created_at_utc,
            updated_at_utc=max(existing.updated_at_utc, occurred_at_utc),
        ),
    )


def _same_business_scope(existing: IdeaCandidate, incoming: IdeaCandidate) -> bool:
    return (
        incoming.candidate_id == existing.candidate_id
        and incoming.identity.business_identity_id == existing.identity.business_identity_id
        and incoming.family is existing.family
        and incoming.access_scope == existing.access_scope
    )


def _is_supported_policy_upgrade(existing: IdeaCandidate, incoming: IdeaCandidate) -> bool:
    return (
        existing.identity.policy_version == PREVIOUS_OPPORTUNITY_IDENTITY_POLICY_VERSION
        and incoming.identity.policy_version == OPPORTUNITY_IDENTITY_POLICY_VERSION
    )


def _backfill_identity_policy(
    *,
    existing: IdeaCandidate,
    incoming: IdeaCandidate,
    occurred_at_utc: datetime,
) -> IdeaCandidate:
    identity = replace(
        incoming.identity,
        material_version=existing.identity.material_version,
        evidence_version=existing.identity.evidence_version + 1,
        change_reason=CandidateChangeReason.MIGRATION_BACKFILL,
        supersedes_material_version=existing.identity.supersedes_material_version,
    )
    return replace(
        incoming,
        identity=identity,
        lifecycle_status=existing.lifecycle_status,
        review_posture=existing.review_posture,
        suppression_reason=existing.suppression_reason,
        created_at_utc=existing.created_at_utc,
        updated_at_utc=max(existing.updated_at_utc, occurred_at_utc),
    )


def _new_material_version(
    *,
    existing: IdeaCandidate,
    incoming: IdeaCandidate,
    occurred_at_utc: datetime,
    reason: CandidateChangeReason,
) -> IdeaCandidate:
    material_version = existing.identity.material_version + 1
    identity = CandidateIdentity(
        business_identity_id=existing.identity.business_identity_id,
        policy_version=existing.identity.policy_version,
        material_fingerprint=incoming.identity.material_fingerprint,
        material_version=material_version,
        evidence_version=1,
        change_reason=reason,
        supersedes_material_version=existing.identity.material_version,
    )
    return replace(
        incoming,
        identity=identity,
        suppression_reason=None,
        created_at_utc=existing.created_at_utc,
        updated_at_utc=max(existing.updated_at_utc, occurred_at_utc),
    )


__all__ = [
    "CandidateReconciliation",
    "REOPENABLE_TERMINAL_STATUSES",
    "reconcile_candidate",
]
