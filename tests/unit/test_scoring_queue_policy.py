from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    EvidenceSupportability,
    IdeaCandidate,
    IdeaEvidencePacket,
    IdeaLifecycleStatus,
    IdeaScore,
    IdeaScoringInputs,
    IdeaScoringPolicy,
    LineageRef,
    OpportunityFamily,
    QueueExclusion,
    QueueExclusionReason,
    QueuePriorityBucket,
    QueueSnooze,
    ReasonCode,
    ReviewQueueItem,
    ReviewQueuePolicy,
    ReviewPosture,
    SourceRef,
    SourceSystem,
    SuppressionReason,
    UnsupportedEvidenceReason,
    build_review_queue,
    priority_bucket_for_score,
    score_candidate,
    score_inputs,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)
SCORING_POLICY = IdeaScoringPolicy(policy_version="idea-weighted-evidence-score-v1")
QUEUE_POLICY = ReviewQueuePolicy(
    policy_version="idea-deterministic-ranking-v1",
    rankable_score_policy_versions=(SCORING_POLICY.policy_version,),
)


def source_ref(product_id: str = "lotus-core:PortfolioStateSnapshot:v1") -> SourceRef:
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def evidence_packet(
    *,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
) -> IdeaEvidencePacket:
    source = source_ref()
    lineage = LineageRef(
        lineage_id="lineage:lotus-idea:high-cash:test",
        source_refs=(source,),
        content_hash="sha256:lineage",
    )
    return IdeaEvidencePacket(
        evidence_packet_id="iep_high_cash_test",
        supportability=supportability,
        source_refs=(source,),
        lineage_ref=lineage,
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        unsupported_reasons=(
            (UnsupportedEvidenceReason.STALE_SOURCE,)
            if supportability is EvidenceSupportability.BLOCKED
            else ()
        ),
        created_at_utc=EVALUATED_AT,
    )


def candidate(
    candidate_id: str,
    *,
    score: Decimal | None = Decimal("75"),
    created_at_utc: datetime = EVALUATED_AT,
    source_signal_ids: tuple[str, ...] | None = None,
    lifecycle_status: IdeaLifecycleStatus = IdeaLifecycleStatus.SCORED,
    review_posture: ReviewPosture = ReviewPosture.ADVISOR_REVIEW_REQUIRED,
    suppression_reason: SuppressionReason | None = None,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
    score_policy_version: str = SCORING_POLICY.policy_version,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id=candidate_id,
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=lifecycle_status,
        review_posture=review_posture,
        evidence_packet=evidence_packet(supportability=supportability),
        source_signal_ids=source_signal_ids or (f"signal:{candidate_id}",),
        score=(
            IdeaScore(
                policy_version=score_policy_version,
                score=score,
                reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
            )
            if score is not None
            else None
        ),
        suppression_reason=suppression_reason,
        created_at_utc=created_at_utc,
        updated_at_utc=created_at_utc,
    )


def scoring_inputs(**overrides: Decimal | bool) -> IdeaScoringInputs:
    values: dict[str, Decimal | bool] = {
        "materiality": Decimal("90"),
        "urgency": Decimal("80"),
        "confidence": Decimal("75"),
        "evidence_quality": Decimal("85"),
        "freshness": Decimal("100"),
        "relevance": Decimal("70"),
        "downstream_fit": Decimal("65"),
        "has_conflict_flags": False,
    }
    values.update(overrides)
    return IdeaScoringInputs(**values)  # type: ignore[arg-type]


def test_score_inputs_are_deterministic_versioned_and_explainable() -> None:
    first = score_inputs(scoring_inputs(), policy=SCORING_POLICY)
    second = score_inputs(scoring_inputs(), policy=SCORING_POLICY)

    assert first == second
    assert first.policy_version == "idea-weighted-evidence-score-v1"
    assert first.final_score == Decimal("80.75")
    assert first.reason_codes == (
        ReasonCode.MATERIALITY_SCORE,
        ReasonCode.URGENCY_SCORE,
        ReasonCode.CONFIDENCE_SCORE,
        ReasonCode.EVIDENCE_QUALITY_SCORE,
        ReasonCode.FRESHNESS_SCORE,
        ReasonCode.RELEVANCE_SCORE,
        ReasonCode.DOWNSTREAM_FIT_SCORE,
    )
    assert [contribution.component.value for contribution in first.contributions] == [
        "materiality",
        "urgency",
        "confidence",
        "evidence_quality",
        "freshness",
        "relevance",
        "downstream_fit",
    ]


def test_conflict_flags_apply_bounded_reasoned_penalty() -> None:
    breakdown = score_inputs(scoring_inputs(has_conflict_flags=True), policy=SCORING_POLICY)

    assert breakdown.final_score == Decimal("65.75")
    assert breakdown.conflict_penalty_applied == Decimal("15")
    assert ReasonCode.CONFLICT_PENALTY in breakdown.reason_codes


def test_score_candidate_attaches_policy_score_without_changing_lifecycle() -> None:
    unscored = candidate("idea-001", score=None, lifecycle_status=IdeaLifecycleStatus.GENERATED)

    scored, breakdown = score_candidate(
        unscored,
        scoring_inputs(),
        policy=SCORING_POLICY,
        scored_at_utc=datetime(2026, 6, 21, 10, 5, tzinfo=UTC),
    )

    assert scored.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert scored.score is not None
    assert scored.score.score == breakdown.final_score
    assert scored.score.policy_version == SCORING_POLICY.policy_version
    assert scored.updated_at_utc == datetime(2026, 6, 21, 10, 5, tzinfo=UTC)


def test_review_queue_ranking_is_stable_and_priority_bucketed() -> None:
    newer_high_score = candidate(
        "idea-newer-high",
        score=Decimal("85"),
        created_at_utc=datetime(2026, 6, 21, 10, 2, tzinfo=UTC),
    )
    older_same_score = candidate(
        "idea-older-same-score",
        score=Decimal("80"),
        created_at_utc=datetime(2026, 6, 21, 9, 59, tzinfo=UTC),
    )
    newer_same_score = candidate(
        "idea-newer-same-score",
        score=Decimal("80"),
        created_at_utc=datetime(2026, 6, 21, 10, 1, tzinfo=UTC),
    )

    queue = build_review_queue(
        (newer_same_score, newer_high_score, older_same_score),
        policy=QUEUE_POLICY,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert [item.candidate.candidate_id for item in queue.items] == [
        "idea-newer-high",
        "idea-older-same-score",
        "idea-newer-same-score",
    ]
    assert [item.rank for item in queue.items] == [1, 2, 3]
    assert queue.items[0].priority_bucket is QueuePriorityBucket.CRITICAL
    assert queue.items[1].priority_bucket is QueuePriorityBucket.HIGH


def test_review_queue_ranks_candidates_from_explicitly_approved_score_policies() -> None:
    queue_policy = ReviewQueuePolicy(
        policy_version="idea-deterministic-ranking-v1",
        rankable_score_policy_versions=(
            "concentration-attention-v1",
            "idle-liquidity-v1",
        ),
    )
    high_cash = candidate(
        "idea-high-cash",
        score=Decimal("80"),
        score_policy_version="idle-liquidity-v1",
    )
    concentration = candidate(
        "idea-concentration",
        score=Decimal("90"),
        score_policy_version="concentration-attention-v1",
    )

    queue = build_review_queue(
        (high_cash, concentration),
        policy=queue_policy,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert [item.candidate.candidate_id for item in queue.items] == [
        "idea-concentration",
        "idea-high-cash",
    ]
    assert {
        item.candidate.score.policy_version for item in queue.items if item.candidate.score
    } == {
        "concentration-attention-v1",
        "idle-liquidity-v1",
    }
    assert {item.policy_version for item in queue.items} == {queue_policy.policy_version}


def test_review_queue_excludes_suppressed_blocked_expired_snoozed_and_unscored() -> None:
    active = candidate("idea-active")
    suppressed = candidate(
        "idea-suppressed",
        suppression_reason=SuppressionReason.MANUAL_SUPPRESSION,
    )
    blocked = candidate("idea-blocked", supportability=EvidenceSupportability.BLOCKED)
    expired = candidate(
        "idea-expired",
        lifecycle_status=IdeaLifecycleStatus.EXPIRED,
        review_posture=ReviewPosture.NO_ACTION,
    )
    snoozed = candidate("idea-snoozed")
    unscored = candidate("idea-unscored", score=None)

    queue = build_review_queue(
        (active, suppressed, blocked, expired, snoozed, unscored),
        policy=QUEUE_POLICY,
        evaluated_at_utc=EVALUATED_AT,
        snoozes=(
            QueueSnooze(
                candidate_id="idea-snoozed",
                snoozed_until_utc=datetime(2026, 6, 21, 11, 0, tzinfo=UTC),
                reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            ),
        ),
    )

    assert [item.candidate.candidate_id for item in queue.items] == ["idea-active"]
    assert {exclusion.reason for exclusion in queue.exclusions} == {
        QueueExclusionReason.SUPPRESSED,
        QueueExclusionReason.UNSUPPORTED_EVIDENCE,
        QueueExclusionReason.EXPIRED,
        QueueExclusionReason.SNOOZED,
        QueueExclusionReason.UNSCORED,
    }


def test_review_queue_excludes_scores_from_a_different_policy_version() -> None:
    current = candidate("idea-current-policy", score=Decimal("70"))
    stale = candidate(
        "idea-stale-policy",
        score=Decimal("99"),
        score_policy_version="retired-score-policy-v0",
    )

    queue = build_review_queue(
        (stale, current),
        policy=QUEUE_POLICY,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert [item.candidate.candidate_id for item in queue.items] == ["idea-current-policy"]
    assert queue.policy_version == QUEUE_POLICY.policy_version
    assert queue.exclusions == (
        QueueExclusion(
            candidate_id="idea-stale-policy",
            reason=QueueExclusionReason.UNRANKABLE_SCORE_POLICY,
            detail="candidate score policy is not rankable under the active queue policy",
        ),
    )


def test_review_queue_deduplicates_source_signals_and_keeps_highest_ranked_candidate() -> None:
    lower_duplicate = candidate(
        "idea-duplicate-lower",
        score=Decimal("70"),
        source_signal_ids=("shared-signal",),
    )
    higher_duplicate = candidate(
        "idea-duplicate-higher",
        score=Decimal("90"),
        source_signal_ids=("shared-signal",),
    )

    queue = build_review_queue(
        (lower_duplicate, higher_duplicate),
        policy=QUEUE_POLICY,
        evaluated_at_utc=EVALUATED_AT,
    )

    assert [item.candidate.candidate_id for item in queue.items] == ["idea-duplicate-higher"]
    assert queue.exclusions[0].candidate_id == "idea-duplicate-lower"
    assert queue.exclusions[0].reason is QueueExclusionReason.DUPLICATE


def test_expired_snooze_returns_candidate_to_queue() -> None:
    snoozed = candidate("idea-snooze-expired")

    queue = build_review_queue(
        (snoozed,),
        policy=QUEUE_POLICY,
        evaluated_at_utc=EVALUATED_AT,
        snoozes=(
            QueueSnooze(
                candidate_id="idea-snooze-expired",
                snoozed_until_utc=datetime(2026, 6, 21, 9, 59, tzinfo=UTC),
                reason_codes=(ReasonCode.REVIEW_REQUIRED,),
            ),
        ),
    )

    assert [item.candidate.candidate_id for item in queue.items] == ["idea-snooze-expired"]
    assert queue.exclusions == ()


def test_scoring_inputs_and_policy_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="materiality must be between 0 and 100"):
        scoring_inputs(materiality=Decimal("101"))

    with pytest.raises(ValueError, match="policy_version is required"):
        IdeaScoringPolicy(policy_version=" ")

    with pytest.raises(ValueError, match="score weights must sum to 1.00"):
        IdeaScoringPolicy(
            policy_version="bad-policy",
            materiality_weight=Decimal("0.10"),
        )

    with pytest.raises(ValueError, match="priority thresholds must be descending"):
        ReviewQueuePolicy(
            policy_version="bad-threshold-policy",
            rankable_score_policy_versions=(SCORING_POLICY.policy_version,),
            critical_threshold=Decimal("70"),
            high_threshold=Decimal("80"),
        )

    with pytest.raises(ValueError, match="rankable_score_policy_versions is required"):
        ReviewQueuePolicy(
            policy_version="missing-score-policies",
            rankable_score_policy_versions=(),
        )

    with pytest.raises(ValueError, match="rankable_score_policy_versions must be unique"):
        ReviewQueuePolicy(
            policy_version="duplicate-score-policies",
            rankable_score_policy_versions=("score-v1", "score-v1"),
        )

    with pytest.raises(ValueError, match="snoozed_until_utc must be timezone-aware"):
        QueueSnooze(
            candidate_id="idea-001",
            snoozed_until_utc=datetime(2026, 6, 21, 11, 0),
            reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        QueueSnooze(
            candidate_id="idea-001",
            snoozed_until_utc=datetime(2026, 6, 21, 11, 0, tzinfo=UTC),
            reason_codes=(),
        )


def test_queue_excludes_non_reviewable_post_review_status() -> None:
    approved = replace(
        candidate("idea-approved"),
        lifecycle_status=IdeaLifecycleStatus.APPROVED,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
    )

    queue = build_review_queue((approved,), policy=QUEUE_POLICY, evaluated_at_utc=EVALUATED_AT)

    assert queue.items == ()
    assert queue.exclusions[0].reason is QueueExclusionReason.NON_REVIEWABLE_STATUS


def test_queue_excludes_closed_and_rejected_terminal_statuses() -> None:
    closed = candidate(
        "idea-closed",
        lifecycle_status=IdeaLifecycleStatus.CLOSED,
        review_posture=ReviewPosture.NO_ACTION,
    )
    rejected = candidate(
        "idea-rejected",
        lifecycle_status=IdeaLifecycleStatus.REJECTED,
        review_posture=ReviewPosture.REJECTED,
    )

    queue = build_review_queue(
        (closed, rejected), policy=QUEUE_POLICY, evaluated_at_utc=EVALUATED_AT
    )

    assert queue.items == ()
    assert [exclusion.reason for exclusion in queue.exclusions] == [
        QueueExclusionReason.CLOSED,
        QueueExclusionReason.REJECTED,
    ]


def test_queue_item_and_exclusion_validate_required_fields() -> None:
    active_candidate = candidate("idea-validation")

    with pytest.raises(ValueError, match="rank must be greater than zero"):
        ReviewQueueItem(
            rank=0,
            candidate=active_candidate,
            score=Decimal("75"),
            priority_bucket=QueuePriorityBucket.HIGH,
            policy_version=QUEUE_POLICY.policy_version,
            reason_codes=(ReasonCode.QUEUE_PRIORITY,),
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        ReviewQueueItem(
            rank=1,
            candidate=active_candidate,
            score=Decimal("75"),
            priority_bucket=QueuePriorityBucket.HIGH,
            policy_version=QUEUE_POLICY.policy_version,
            reason_codes=(),
        )

    with pytest.raises(ValueError, match="detail is required"):
        QueueExclusion(
            candidate_id="idea-validation",
            reason=QueueExclusionReason.SUPPRESSED,
            detail=" ",
        )


def test_priority_bucket_boundaries_include_standard_and_watchlist() -> None:
    assert (
        priority_bucket_for_score(Decimal("50"), policy=QUEUE_POLICY)
        is QueuePriorityBucket.STANDARD
    )
    assert (
        priority_bucket_for_score(Decimal("49.99"), policy=QUEUE_POLICY)
        is QueuePriorityBucket.WATCHLIST
    )
