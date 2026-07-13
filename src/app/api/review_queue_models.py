from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.api.base_model import CamelModel
from app.application.review_queue import ReviewQueuePage, ReviewQueueReadinessSnapshot
from app.domain import QueueExclusion, ReviewQueueItem


class ReviewQueueCandidateResponse(CamelModel):
    candidate_id: str = Field(..., alias="candidateId")
    family: str
    lifecycle_status: str = Field(..., alias="lifecycleStatus")
    review_posture: str = Field(..., alias="reviewPosture")
    evidence_packet_id: str = Field(..., alias="evidencePacketId")
    score: str
    score_policy_version: str = Field(..., alias="scorePolicyVersion")
    source_signal_ids: tuple[str, ...] = Field(..., alias="sourceSignalIds")

    @classmethod
    def from_item(cls, item: ReviewQueueItem) -> "ReviewQueueCandidateResponse":
        candidate = item.candidate
        assert candidate.score is not None
        return cls(
            candidateId=candidate.candidate_id,
            family=candidate.family.value,
            lifecycleStatus=candidate.lifecycle_status.value,
            reviewPosture=candidate.review_posture.value,
            evidencePacketId=candidate.evidence_packet.evidence_packet_id,
            score=str(candidate.score.score),
            scorePolicyVersion=candidate.score.policy_version,
            sourceSignalIds=candidate.source_signal_ids,
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


class AdvisorReviewQueueResponse(CamelModel):
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
    ) -> "AdvisorReviewQueueResponse":
        return cls(
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
