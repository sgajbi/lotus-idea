from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.api.base_model import CamelModel
from app.application.review_queue_exceptions import (
    ReviewQueueAudienceExceptionSummary,
    ReviewQueueExceptionSnapshot,
)
from app.domain import ReviewQueueAudience


class ReviewQueueAudienceExceptionResponse(CamelModel):
    audience: ReviewQueueAudience
    candidate_snapshot_count: int = Field(..., alias="candidateSnapshotCount")
    exception_count: int = Field(..., alias="exceptionCount")
    exception_counts: dict[str, int] = Field(..., alias="exceptionCounts")

    @classmethod
    def from_domain(
        cls,
        summary: ReviewQueueAudienceExceptionSummary,
    ) -> "ReviewQueueAudienceExceptionResponse":
        return cls(
            audience=summary.audience,
            candidateSnapshotCount=summary.candidate_snapshot_count,
            exceptionCount=summary.exception_count,
            exceptionCounts=dict(summary.exception_counts),
        )


class ReviewQueueExceptionResponse(CamelModel):
    policy_version: str = Field(..., alias="policyVersion")
    evaluated_at_utc: datetime = Field(..., alias="evaluatedAtUtc")
    audiences: tuple[ReviewQueueAudienceExceptionResponse, ...]
    total_exception_count: int = Field(..., alias="totalExceptionCount")
    durable_storage_backed: bool = Field(..., alias="durableStorageBacked")
    supportability_status: str = Field(..., alias="supportabilityStatus")
    supported_feature_promoted: bool = Field(..., alias="supportedFeaturePromoted")

    @classmethod
    def from_domain(cls, snapshot: ReviewQueueExceptionSnapshot) -> "ReviewQueueExceptionResponse":
        return cls(
            policyVersion=snapshot.policy_version,
            evaluatedAtUtc=snapshot.evaluated_at_utc,
            audiences=tuple(
                ReviewQueueAudienceExceptionResponse.from_domain(summary)
                for summary in snapshot.audiences
            ),
            totalExceptionCount=snapshot.total_exception_count,
            durableStorageBacked=snapshot.durable_storage_backed,
            supportabilityStatus=snapshot.supportability_status,
            supportedFeaturePromoted=snapshot.supported_feature_promoted,
        )


__all__ = ["ReviewQueueAudienceExceptionResponse", "ReviewQueueExceptionResponse"]
