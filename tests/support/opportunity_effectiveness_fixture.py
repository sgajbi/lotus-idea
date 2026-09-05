from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.domain import (
    SourceCutPosture,
    CandidateChangeReason,
    CandidateVersionHistoryEntry,
    ConversionBoundary,
    ConversionOutcomeStatus,
    ConversionTarget,
    EvidenceFreshness,
    EvidenceSupportability,
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackCommand,
    FeedbackOutcome,
    FeedbackReason,
    GovernedConversionIntent,
    GovernedConversionOutcome,
    GovernedFeedbackEvent,
    GovernedReviewDecision,
    IdeaCandidate,
    IdeaConversionIntent,
    IdeaConversionOutcome,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaRepositorySnapshot,
    LineageRef,
    OpportunityFamily,
    ReasonCode,
    ReviewAccessScope,
    ReviewAction,
    ReviewActorContext,
    ReviewActorRole,
    ReviewChannel,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    UnsupportedEvidenceReason,
    record_feedback,
)
from app.domain.persistence_models import CandidatePersistenceRecord
from tests.support.candidate_identity import initial_candidate_identity
from tests.support.score_fixture import score_fixture


FIXTURE_WINDOW_START = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
FIXTURE_WINDOW_END = datetime(2026, 6, 21, 12, 0, tzinfo=UTC)
FIXTURE_EVALUATED_AT = datetime(2026, 6, 22, 8, 0, tzinfo=UTC)


def candidate_fixture(
    candidate_id: str,
    *,
    family: OpportunityFamily,
    score: Decimal | None,
    created_at: datetime,
    tenant_id: str = "tenant-a",
    lifecycle_status: IdeaLifecycleStatus = IdeaLifecycleStatus.GENERATED,
    review_posture: ReviewPosture = ReviewPosture.ADVISOR_REVIEW_REQUIRED,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    suppression_reason: SuppressionReason | None = None,
    recurrent: bool = False,
) -> IdeaCandidate:
    source = SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=created_at - timedelta(minutes=5),
        content_hash=f"sha256:{'1' * 64}",
        data_quality_status="complete",
        freshness=freshness,
    )
    unsupported_reasons = (
        (UnsupportedEvidenceReason.STALE_SOURCE,)
        if supportability is not EvidenceSupportability.READY
        else ()
    )
    evidence = IdeaEvidencePacket(
        evidence_packet_id=f"evidence-{candidate_id}",
        supportability=supportability,
        source_refs=(source,),
        lineage_ref=LineageRef(
            lineage_id=f"lineage-{candidate_id}",
            source_refs=(source,),
            content_hash=f"sha256:{'2' * 64}",
        ),
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        unsupported_reasons=unsupported_reasons,
        created_at_utc=created_at,
    )
    identity = initial_candidate_identity(candidate_id)
    if recurrent:
        identity = replace(
            identity,
            material_fingerprint=f"sha256:{'4' * 64}",
            material_version=2,
            change_reason=CandidateChangeReason.RECURRENT_CONDITION,
            supersedes_material_version=1,
        )
    return IdeaCandidate(
        candidate_id=candidate_id,
        identity=identity,
        family=family,
        lifecycle_status=lifecycle_status,
        review_posture=review_posture,
        evidence_packet=evidence,
        source_signal_ids=(f"signal-{candidate_id}",),
        score=(
            score_fixture(
                policy_version=_score_policy(family),
                score=score,
                reason_codes=(ReasonCode.QUEUE_PRIORITY,),
            )
            if score is not None
            else None
        ),
        access_scope=ReviewAccessScope(
            tenant_id=tenant_id,
            book_id="book-001",
            portfolio_id="portfolio-001",
            client_id="client-001",
        ),
        suppression_reason=suppression_reason,
        created_at_utc=created_at,
        updated_at_utc=created_at,
    )


def review_fixture(
    candidate_id: str,
    *,
    action: ReviewAction,
    decided_at: datetime,
    suppression_reason: SuppressionReason | None = None,
) -> GovernedReviewDecision:
    resulting_posture = {
        ReviewAction.APPROVE_FOR_CONVERSION: ReviewPosture.APPROVED_FOR_CONVERSION,
        ReviewAction.REJECT: ReviewPosture.REJECTED,
        ReviewAction.SUPPRESS: ReviewPosture.SUPPRESSED,
    }[action]
    return GovernedReviewDecision(
        review_id=f"review-{candidate_id}-{action.value}",
        candidate_id=candidate_id,
        evidence_packet_id=f"evidence-{candidate_id}",
        evidence_content_hash=f"sha256:{'2' * 64}",
        source_revision_vector_digest="legacy:unknown",
        source_cut_posture=SourceCutPosture.UNKNOWN,
        candidate_material_version=1,
        candidate_evidence_version=1,
        review_channel=ReviewChannel.LEGACY_UNVERIFIED,
        presentation_receipt_id=None,
        queue_snapshot_digest=None,
        review_policy_version="legacy-unverified",
        action=action,
        resulting_posture=resulting_posture,
        actor_subject="advisor-sensitive-subject",
        actor_role=ReviewActorRole.ADVISOR,
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        decided_at_utc=decided_at,
        accepted_at_utc=decided_at,
        suppression_reason=suppression_reason,
    )


def record_fixture(
    candidate: IdeaCandidate,
    *,
    review: GovernedReviewDecision | None = None,
    feedback_reason: FeedbackReason | None = None,
    feedback_outcome: FeedbackOutcome = FeedbackOutcome.NOT_USEFUL,
    conversion: bool = False,
) -> CandidatePersistenceRecord:
    feedback: tuple[GovernedFeedbackEvent, ...] = ()
    if feedback_reason is not None:
        scope = candidate.access_scope
        assert scope is not None
        feedback = (
            record_feedback(
                candidate,
                FeedbackCommand(
                    feedback_id=f"feedback-{candidate.candidate_id}",
                    actor=ReviewActorContext(
                        actor_subject="advisor-sensitive-subject",
                        role=ReviewActorRole.ADVISOR,
                        tenant_ids=frozenset({scope.tenant_id}),
                        book_ids=frozenset({scope.book_id}),
                        portfolio_ids=frozenset({scope.portfolio_id}),
                        client_ids=frozenset({scope.client_id}),
                    ),
                    outcome=feedback_outcome,
                    reason=feedback_reason,
                    taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
                    recorded_at_utc=FIXTURE_WINDOW_START + timedelta(hours=6),
                ),
                accepted_at_utc=FIXTURE_WINDOW_START + timedelta(hours=6),
            ).feedback_event,
        )
    intent = (
        conversion_intent_fixture(
            candidate,
            requested_at=FIXTURE_WINDOW_START + timedelta(hours=3),
        )
        if conversion
        else None
    )
    outcomes = (
        (
            conversion_outcome_fixture(
                intent,
                status=ConversionOutcomeStatus.REQUESTED,
                version=1,
                recorded_at=FIXTURE_WINDOW_START + timedelta(hours=4),
            ),
            conversion_outcome_fixture(
                intent,
                status=ConversionOutcomeStatus.ACCEPTED,
                version=2,
                recorded_at=FIXTURE_WINDOW_START + timedelta(hours=5),
            ),
        )
        if intent is not None
        else ()
    )
    version_history = (
        (
            CandidateVersionHistoryEntry(
                candidate_id=candidate.candidate_id,
                business_identity_id=candidate.identity.business_identity_id,
                material_fingerprint=candidate.identity.material_fingerprint,
                material_version=2,
                evidence_version=1,
                change_reason=CandidateChangeReason.RECURRENT_CONDITION,
                source_lifecycle_status=IdeaLifecycleStatus.CLOSED,
                resulting_lifecycle_status=IdeaLifecycleStatus.GENERATED,
                supersedes_material_version=1,
                evidence_hash=f"sha256:{'3' * 64}",
                recorded_at_utc=FIXTURE_WINDOW_START + timedelta(minutes=90),
            ),
        )
        if candidate.identity.change_reason is CandidateChangeReason.RECURRENT_CONDITION
        else ()
    )
    return CandidatePersistenceRecord(
        candidate=candidate,
        evidence_hash=f"sha256:{'3' * 64}",
        persisted_at_utc=candidate.created_at_utc,
        version_history=version_history,
        review_decisions=(review,) if review is not None else (),
        feedback_events=feedback,
        conversion_intents=(intent,) if intent is not None else (),
        conversion_outcomes=outcomes,
    )


def conversion_intent_fixture(
    candidate: IdeaCandidate,
    *,
    requested_at: datetime,
) -> GovernedConversionIntent:
    return GovernedConversionIntent(
        intent=IdeaConversionIntent(
            conversion_intent_id=f"intent-{candidate.candidate_id}",
            candidate_id=candidate.candidate_id,
            target=ConversionTarget.ADVISE_PROPOSAL,
            source_status=IdeaLifecycleStatus.APPROVED,
            requested_at_utc=requested_at,
        ),
        evidence_packet_id=candidate.evidence_packet.evidence_packet_id,
        evidence_content_hash=candidate.evidence_packet.lineage_ref.content_hash,
        source_revision_vector_digest=candidate.evidence_packet.source_revision_vector_digest,
        source_cut_posture=candidate.evidence_packet.source_cut_posture,
        source_signal_ids=candidate.source_signal_ids,
        actor_subject="advisor-sensitive-subject",
        idempotency_key=f"intent-key-{candidate.candidate_id}",
        reason_codes=(ReasonCode.REVIEW_APPROVED_FOR_CONVERSION,),
        target_source_authority=SourceSystem.LOTUS_ADVISE,
        accepted_at_utc=requested_at,
    )


def conversion_outcome_fixture(
    intent: GovernedConversionIntent,
    *,
    status: ConversionOutcomeStatus,
    version: int,
    recorded_at: datetime,
) -> GovernedConversionOutcome:
    return GovernedConversionOutcome(
        outcome=IdeaConversionOutcome(
            conversion_outcome_id=f"outcome-{intent.intent.candidate_id}-{version}",
            conversion_intent_id=intent.intent.conversion_intent_id,
            status=status,
            downstream_reference=(
                "downstream-sensitive-reference"
                if status in {ConversionOutcomeStatus.ACCEPTED, ConversionOutcomeStatus.COMPLETED}
                else None
            ),
            recorded_at_utc=recorded_at,
        ),
        conversion_intent_id=intent.intent.conversion_intent_id,
        target=intent.intent.target,
        source_system=SourceSystem.LOTUS_ADVISE,
        boundary=ConversionBoundary.DOWNSTREAM_REALIZATION_REQUIRED,
        source_event_version=version,
        actor_subject="advise-sensitive-subject",
        accepted_at_utc=recorded_at,
    )


def snapshot_fixture(*records: CandidatePersistenceRecord) -> IdeaRepositorySnapshot:
    return IdeaRepositorySnapshot(
        candidate_records={record.candidate.candidate_id: record for record in records},
        idempotency_records={},
        idempotency_candidates={},
    )


def golden_effectiveness_snapshot() -> IdeaRepositorySnapshot:
    approved = record_fixture(
        candidate_fixture(
            "idea-approved-001",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("91"),
            created_at=FIXTURE_WINDOW_START + timedelta(hours=1),
            lifecycle_status=IdeaLifecycleStatus.APPROVED,
            review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
            recurrent=True,
        ),
        review=review_fixture(
            "idea-approved-001",
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=FIXTURE_WINDOW_START + timedelta(hours=2),
        ),
        feedback_reason=FeedbackReason.RELEVANT,
        feedback_outcome=FeedbackOutcome.USEFUL,
        conversion=True,
    )
    rejected = record_fixture(
        candidate_fixture(
            "idea-rejected-001",
            family=OpportunityFamily.UNDERPERFORMANCE,
            score=Decimal("74"),
            created_at=FIXTURE_WINDOW_START + timedelta(hours=1),
            lifecycle_status=IdeaLifecycleStatus.REJECTED,
            review_posture=ReviewPosture.REJECTED,
        ),
        review=review_fixture(
            "idea-rejected-001",
            action=ReviewAction.REJECT,
            decided_at=FIXTURE_WINDOW_START + timedelta(hours=5),
        ),
        feedback_reason=FeedbackReason.WRONG_TIMING,
    )
    suppressed = record_fixture(
        candidate_fixture(
            "idea-suppressed-001",
            family=OpportunityFamily.CONCENTRATION,
            score=None,
            created_at=FIXTURE_WINDOW_START + timedelta(hours=2),
            lifecycle_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
            review_posture=ReviewPosture.SUPPRESSED,
            supportability=EvidenceSupportability.PARTIAL,
            freshness=EvidenceFreshness.STALE,
            suppression_reason=SuppressionReason.DUPLICATE,
        ),
        review=review_fixture(
            "idea-suppressed-001",
            action=ReviewAction.SUPPRESS,
            decided_at=FIXTURE_WINDOW_START + timedelta(hours=3),
            suppression_reason=SuppressionReason.DUPLICATE,
        ),
    )
    return snapshot_fixture(approved, rejected, suppressed)


def _score_policy(family: OpportunityFamily) -> str:
    return {
        OpportunityFamily.HIGH_CASH: "idle-liquidity-v2",
        OpportunityFamily.UNDERPERFORMANCE: "underperformance-review-v2",
        OpportunityFamily.CONCENTRATION: "concentration-attention-v2",
    }.get(family, "idea-weighted-evidence-score-v1")


__all__ = [
    "FIXTURE_EVALUATED_AT",
    "FIXTURE_WINDOW_END",
    "FIXTURE_WINDOW_START",
    "candidate_fixture",
    "conversion_intent_fixture",
    "conversion_outcome_fixture",
    "golden_effectiveness_snapshot",
    "record_fixture",
    "review_fixture",
    "snapshot_fixture",
]
