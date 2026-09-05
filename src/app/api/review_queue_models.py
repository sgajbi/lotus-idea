from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.api.base_model import CamelModel
from app.api.score_models import ScoreContributionResponse
from app.application.review_queue import ReviewQueuePage, ReviewQueueReadinessSnapshot
from app.domain import QueueExclusion, ReviewQueueAudience, ReviewQueueItem


class ReviewQueueCandidateResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    material_version: int = Field(
        ...,
        alias="materialVersion",
        ge=1,
        description=(
            "Current Idea-owned material version required to bind visible-render evidence "
            "to the economic opportunity state shown to the adviser."
        ),
    )
    evidence_version: int = Field(
        ...,
        alias="evidenceVersion",
        ge=1,
        description=(
            "Current Idea-owned evidence version required to bind visible-render evidence "
            "to the exact source-evidence refresh shown to the adviser."
        ),
    )
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    source_revision_vector_digest: str = Field(..., alias="sourceRevisionVectorDigest")
    source_cut_posture: str = Field(..., alias="sourceCutPosture")
    score: str
    score_policy_version: str = Field(..., alias="scorePolicyVersion")
    score_reason_codes: tuple[str, ...] = Field(..., alias="scoreReasonCodes")
    score_components: tuple[ScoreContributionResponse, ...] = Field(..., alias="scoreComponents")
    score_conflict_penalty_applied: str = Field(..., alias="scoreConflictPenaltyApplied")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")
    applicability_expires_at_utc: datetime | None = Field(
        default=None,
        alias="applicabilityExpiresAtUtc",
    )

    @classmethod
    def from_item(cls, item: ReviewQueueItem) -> "ReviewQueueCandidateResponse":
        candidate = item.candidate
        assert candidate.score is not None
        return cls(
            candidateId=candidate.candidate_id,
            materialVersion=candidate.identity.material_version,
            evidenceVersion=candidate.identity.evidence_version,
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            sourceRevisionVectorDigest=candidate.evidence_packet.source_revision_vector_digest,
            sourceCutPosture=candidate.evidence_packet.source_cut_posture.value,
            score=str(candidate.score.score),
            scorePolicyVersion=candidate.score.policy_version,
            scoreReasonCodes=tuple(reason.value for reason in candidate.score.reason_codes),
            scoreComponents=tuple(
                ScoreContributionResponse.from_domain(item)
                for item in candidate.score.contributions
            ),
            scoreConflictPenaltyApplied=str(candidate.score.conflict_penalty_applied),
            sourceSignalIds=candidate.source_signal_ids,
            applicabilityExpiresAtUtc=(candidate.evidence_packet.applicability_expires_at_utc),
        )


class ReviewQueueItemResponse(CamelModel):
    rank: int
    candidate: ReviewQueueCandidateResponse
    score: str
    priority_bucket: str = Field(..., alias="priorityBucket")
    policy_version: str = Field(
        ...,
        alias="policyVersion",
        description="Review-queue ranking policy applied to this item.",
    )
    reason_codes: tuple[str, ...] = Field(..., alias="reasonCodes")

    @classmethod
    def from_domain(cls, item: ReviewQueueItem) -> "ReviewQueueItemResponse":
        return cls(
            rank=item.rank,
            candidate=ReviewQueueCandidateResponse.from_item(item),
            score=str(item.score),
            priorityBucket=item.priority_bucket.value,
            policyVersion=item.policy_version,
            reasonCodes=tuple(reason.value for reason in item.reason_codes),
        )


class ReviewQueueExclusionResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    reason: str
    detail: str

    @classmethod
    def from_domain(cls, exclusion: QueueExclusion) -> "ReviewQueueExclusionResponse":
        return cls(
            candidateId=exclusion.candidate_id,
            reason=exclusion.reason.value,
            detail=exclusion.detail,
        )


class ReviewQueuePageResponse(CamelModel):
    limit: int
    offset: int
    returned_item_count: int = Field(..., alias="returnedItemCount")
    total_reviewable_item_count: int = Field(..., alias="totalReviewableItemCount")
    returned_exclusion_count: int = Field(..., alias="returnedExclusionCount")
    total_excluded_candidate_count: int = Field(..., alias="totalExcludedCandidateCount")
    next_offset: int | None = Field(None, alias="nextOffset")
    has_next_page: bool = Field(..., alias="hasNextPage")
    snapshot_token: str = Field(..., alias="snapshotToken")

    @classmethod
    def from_domain(cls, queue_page: ReviewQueuePage) -> "ReviewQueuePageResponse":
        page = queue_page.page
        return cls(
            limit=page.limit,
            offset=page.offset,
            returnedItemCount=page.returned_item_count,
            totalReviewableItemCount=page.total_reviewable_item_count,
            returnedExclusionCount=page.returned_exclusion_count,
            totalExcludedCandidateCount=page.total_excluded_candidate_count,
            nextOffset=page.next_offset,
            hasNextPage=page.has_next_page,
            snapshotToken=page.snapshot_token,
        )


class BusinessReviewQueueResponse(CamelModel):
    audience: ReviewQueueAudience
    policy_version: str = Field(
        ...,
        alias="policyVersion",
        description="Review-queue ranking policy applied to this projection.",
    )
    evaluated_at_utc: datetime = Field(..., alias="evaluatedAtUtc")
    items: tuple[ReviewQueueItemResponse, ...]
    exclusions: tuple[ReviewQueueExclusionResponse, ...]
    page: ReviewQueuePageResponse
    durable_storage_backed: bool = Field(False, alias="durableStorageBacked")
    supported_feature_promoted: bool = Field(False, alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        queue: ReviewQueuePage,
        *,
        durable_storage_backed: bool = False,
    ) -> "BusinessReviewQueueResponse":
        return cls(
            audience=queue.projection.audience,
            policyVersion=queue.projection.policy_version,
            evaluatedAtUtc=queue.projection.evaluated_at_utc,
            items=tuple(
                ReviewQueueItemResponse.from_domain(item) for item in queue.projection.items
            ),
            exclusions=tuple(
                ReviewQueueExclusionResponse.from_domain(exclusion)
                for exclusion in queue.projection.exclusions
            ),
            page=ReviewQueuePageResponse.from_domain(queue),
            durableStorageBacked=durable_storage_backed,
            supportedFeaturePromoted=False,
        )


class ReviewQueueReadinessResponse(CamelModel):
    repository: str
    policy_version: str = Field(..., alias="policyVersion")
    evaluated_at_utc: datetime = Field(..., alias="evaluatedAtUtc")
    queue_projection_available: bool = Field(..., alias="queueProjectionAvailable")
    candidate_snapshot_count: int = Field(..., alias="candidateSnapshotCount")
    reviewable_item_count: int = Field(..., alias="reviewableItemCount")
    excluded_candidate_count: int = Field(..., alias="excludedCandidateCount")
    exclusion_counts: dict[str, int] = Field(..., alias="exclusionCounts")
    scored_candidate_count: int = Field(..., alias="scoredCandidateCount")
    unscored_candidate_count: int = Field(..., alias="unscoredCandidateCount")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    repository_side_pagination_certified: bool = Field(
        ...,
        alias="repositorySidePaginationCertified",
    )
    readiness_status: str = Field(..., alias="readinessStatus")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    certification_ready: bool = Field(..., alias="certificationReady")
    certification_blockers: tuple[str, ...] = Field(..., alias="certificationBlockers")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(
        cls,
        snapshot: ReviewQueueReadinessSnapshot,
    ) -> "ReviewQueueReadinessResponse":
        return cls(
            repository=snapshot.repository,
            policyVersion=snapshot.policy_version,
            evaluatedAtUtc=snapshot.evaluated_at_utc,
            queueProjectionAvailable=snapshot.queue_projection_available,
            candidateSnapshotCount=snapshot.candidate_snapshot_count,
            reviewableItemCount=snapshot.reviewable_item_count,
            excludedCandidateCount=snapshot.excluded_candidate_count,
            exclusionCounts=dict(snapshot.exclusion_counts),
            scoredCandidateCount=snapshot.scored_candidate_count,
            unscoredCandidateCount=snapshot.unscored_candidate_count,
            durableStorageBacked=snapshot.durable_storage_backed,
            repositorySidePaginationCertified=snapshot.repository_side_pagination_certified,
            readinessStatus=snapshot.readiness_status,
            supportabilityStatus=snapshot.supportability_status,
            certificationReady=snapshot.certification_ready,
            certificationBlockers=snapshot.certification_blockers,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )
