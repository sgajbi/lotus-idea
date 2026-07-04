from __future__ import annotations

from datetime import UTC, datetime

from app.api.review_queue_models import AdvisorReviewQueueResponse, ReviewQueueReadinessResponse
from app.application.review_queue import ReviewQueuePage, ReviewQueuePageMetadata
from app.application.review_queue import ReviewQueueReadinessSnapshot
from app.domain import QueueExclusionReason, build_review_queue
from tests.unit.test_postgres_repository import high_cash_candidate


EVALUATED_AT = datetime(2026, 6, 21, 10, 10, tzinfo=UTC)


def test_advisor_review_queue_response_maps_source_safe_page() -> None:
    queue = build_review_queue(
        (high_cash_candidate(),),
        evaluated_at_utc=EVALUATED_AT,
    )
    page = ReviewQueuePage(
        projection=queue,
        page=ReviewQueuePageMetadata(
            limit=25,
            offset=0,
            returned_item_count=1,
            total_reviewable_item_count=1,
            returned_exclusion_count=0,
            total_excluded_candidate_count=0,
            next_offset=None,
            has_next_page=False,
        ),
    )

    response = AdvisorReviewQueueResponse.from_domain(
        page,
        durable_storage_backed=True,
    ).model_dump(by_alias=True)

    assert response["policyVersion"] == "idea-deterministic-ranking-v1"
    assert response["evaluatedAtUtc"] == EVALUATED_AT
    assert response["durableStorageBacked"] is True
    assert response["supportedFeaturePromoted"] is False
    assert response["page"] == {
        "limit": 25,
        "offset": 0,
        "returnedItemCount": 1,
        "totalReviewableItemCount": 1,
        "returnedExclusionCount": 0,
        "totalExcludedCandidateCount": 0,
        "nextOffset": None,
        "hasNextPage": False,
    }
    assert len(response["items"]) == 1
    item = response["items"][0]
    assert item["rank"] == 1
    assert item["candidate"]["family"] == "high_cash"
    assert item["candidate"]["score"] == "82"
    assert item["reasonCodes"] == ("high_cash_ratio", "review_required")
    assert response["exclusions"] == ()
    assert "route" not in str(response)
    assert "contentHash" not in str(response)


def test_review_queue_readiness_response_preserves_blockers_without_promotion() -> None:
    snapshot = ReviewQueueReadinessSnapshot(
        repository="lotus-idea",
        policy_version="idea-deterministic-ranking-v1",
        evaluated_at_utc=EVALUATED_AT,
        queue_projection_available=True,
        candidate_snapshot_count=2,
        reviewable_item_count=1,
        excluded_candidate_count=1,
        exclusion_counts={reason.value: 0 for reason in QueueExclusionReason}
        | {QueueExclusionReason.EXPIRED.value: 1},
        scored_candidate_count=2,
        unscored_candidate_count=0,
        durable_storage_backed=True,
        repository_side_pagination_certified=True,
        readiness_status="blocked",
        supportability_status="not_certified",
        certification_blockers=(
            "workbench_product_proof_missing",
            "supported_feature_promotion_missing",
        ),
        supported_feature_promoted=False,
    )

    response = ReviewQueueReadinessResponse.from_domain(snapshot).model_dump(by_alias=True)

    assert response["repository"] == "lotus-idea"
    assert response["queueProjectionAvailable"] is True
    assert response["reviewableItemCount"] == 1
    assert response["excludedCandidateCount"] == 1
    assert response["exclusionCounts"]["expired"] == 1
    assert response["durableStorageBacked"] is True
    assert response["repositorySidePaginationCertified"] is True
    assert response["certificationReady"] is False
    assert response["certificationBlockers"] == (
        "workbench_product_proof_missing",
        "supported_feature_promotion_missing",
    )
    assert response["supportedFeaturePromoted"] is False
    assert "PB_SG_GLOBAL_BAL_001" not in str(response)
