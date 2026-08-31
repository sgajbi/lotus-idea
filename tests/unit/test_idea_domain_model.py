from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from tests.support.candidate_identity import initial_candidate_identity
from tests.support.score_fixture import score_fixture

from app.domain import (
    ALLOWED_LIFECYCLE_TRANSITIONS,
    CandidateChangeReason,
    CandidateIdentity,
    ConversionOutcomeStatus,
    ConversionTarget,
    DOWNSTREAM_AUTHORITY_LIFECYCLE_STATUSES,
    EvidenceFreshness,
    EvidenceSupportability,
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackOutcome,
    FeedbackReason,
    IdeaCandidate,
    IdeaConversionIntent,
    IdeaConversionOutcome,
    IdeaEvidencePacket,
    IdeaFeedback,
    IdeaLifecycleStatus,
    IdeaScore,
    InvalidLifecycleTransition,
    LineageRef,
    OpportunityFamily,
    OpportunitySignal,
    ReasonCode,
    ReviewDecision,
    ReviewPosture,
    ScoreComponent,
    ScoreContribution,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    transition_candidate,
)


def source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolio_id}/core-snapshot",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
        content_hash="sha256:portfolio-state",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def evidence_packet(
    *,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
    unsupported_reasons: tuple[UnsupportedEvidenceReason, ...] = (),
) -> IdeaEvidencePacket:
    source = source_ref()
    lineage = LineageRef(
        lineage_id="lineage:idea:high-cash:pb-sg-global-bal-001",
        source_refs=(source,),
        content_hash="sha256:lineage",
    )
    return IdeaEvidencePacket(
        evidence_packet_id="iep_high_cash_001",
        supportability=supportability,
        source_refs=(source,),
        lineage_ref=lineage,
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        unsupported_reasons=unsupported_reasons,
        created_at_utc=datetime(2026, 6, 21, 9, 1, tzinfo=UTC),
    )


def candidate(
    *,
    lifecycle_status: IdeaLifecycleStatus = IdeaLifecycleStatus.DETECTED,
    review_posture: ReviewPosture = ReviewPosture.NOT_REVIEWED,
    supportability: EvidenceSupportability = EvidenceSupportability.READY,
) -> IdeaCandidate:
    return IdeaCandidate(
        candidate_id="idea_high_cash_001",
        identity=initial_candidate_identity("idea_high_cash_001"),
        family=OpportunityFamily.HIGH_CASH,
        lifecycle_status=lifecycle_status,
        review_posture=review_posture,
        evidence_packet=evidence_packet(supportability=supportability),
        source_signal_ids=("signal_high_cash_001",),
        score=score_fixture(
            policy_version="idle-liquidity-v2",
            score=Decimal("82.5"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.REVIEW_REQUIRED),
        ),
        created_at_utc=datetime(2026, 6, 21, 9, 2, tzinfo=UTC),
        updated_at_utc=datetime(2026, 6, 21, 9, 2, tzinfo=UTC),
    )


def test_source_refs_require_provenance_freshness_and_quality() -> None:
    source = source_ref()

    assert source.product_id == "lotus-core:PortfolioStateSnapshot:v1"
    assert source.source_system is SourceSystem.LOTUS_CORE
    assert source.freshness is EvidenceFreshness.CURRENT
    assert source.content_hash.startswith("sha256:")


def test_source_ref_rejects_missing_contract_identity() -> None:
    with pytest.raises(ValueError, match="product_id is required"):
        SourceRef(
            product_id=" ",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/integration/portfolios/{portfolio_id}/core-snapshot",
            as_of_date=date(2026, 6, 21),
            generated_at_utc=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
            content_hash="sha256:portfolio-state",
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        )


def test_source_ref_requires_timezone_aware_generated_at() -> None:
    with pytest.raises(ValueError, match="generated_at_utc must be timezone-aware"):
        SourceRef(
            product_id="lotus-core:PortfolioStateSnapshot:v1",
            source_system=SourceSystem.LOTUS_CORE,
            product_version="v1",
            route="/integration/portfolios/{portfolio_id}/core-snapshot",
            as_of_date=date(2026, 6, 21),
            generated_at_utc=datetime(2026, 6, 21, 9, 0),
            content_hash="sha256:portfolio-state",
            data_quality_status="complete",
            freshness=EvidenceFreshness.CURRENT,
        )


def test_lineage_ref_requires_source_refs() -> None:
    with pytest.raises(ValueError, match="source_refs is required"):
        LineageRef(
            lineage_id="lineage:idea:empty",
            source_refs=(),
            content_hash="sha256:lineage",
        )


def test_blocked_evidence_requires_typed_unsupported_reason() -> None:
    packet = evidence_packet(
        supportability=EvidenceSupportability.BLOCKED,
        unsupported_reasons=(UnsupportedEvidenceReason.STALE_SOURCE,),
    )

    assert packet.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_blocked_evidence_without_reason_is_rejected() -> None:
    with pytest.raises(ValueError, match="blocked evidence requires unsupported_reasons"):
        evidence_packet(supportability=EvidenceSupportability.BLOCKED)


def test_ready_evidence_cannot_carry_unsupported_reason() -> None:
    with pytest.raises(ValueError, match="ready evidence cannot carry"):
        evidence_packet(
            supportability=EvidenceSupportability.READY,
            unsupported_reasons=(UnsupportedEvidenceReason.SOURCE_UNAVAILABLE,),
        )


def test_evidence_packet_requires_source_refs_and_reason_codes() -> None:
    source = source_ref()
    lineage = LineageRef(
        lineage_id="lineage:idea:high-cash:pb-sg-global-bal-001",
        source_refs=(source,),
        content_hash="sha256:lineage",
    )

    with pytest.raises(ValueError, match="source_refs is required"):
        IdeaEvidencePacket(
            evidence_packet_id="iep_high_cash_001",
            supportability=EvidenceSupportability.READY,
            source_refs=(),
            lineage_ref=lineage,
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            created_at_utc=datetime(2026, 6, 21, 9, 1, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        IdeaEvidencePacket(
            evidence_packet_id="iep_high_cash_001",
            supportability=EvidenceSupportability.READY,
            source_refs=(source,),
            lineage_ref=lineage,
            reason_codes=(),
            created_at_utc=datetime(2026, 6, 21, 9, 1, tzinfo=UTC),
        )


def test_opportunity_signal_requires_source_refs_and_reason_codes() -> None:
    signal = OpportunitySignal(
        signal_id="signal_high_cash_001",
        family=OpportunityFamily.HIGH_CASH,
        source_refs=(source_ref(),),
        reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
        detected_at_utc=datetime(2026, 6, 21, 9, 3, tzinfo=UTC),
    )

    assert signal.family is OpportunityFamily.HIGH_CASH
    assert signal.reason_codes == (ReasonCode.HIGH_CASH_RATIO,)


def test_opportunity_signal_validates_expiry_and_required_collections() -> None:
    with pytest.raises(ValueError, match="expires_at_utc must be timezone-aware"):
        OpportunitySignal(
            signal_id="signal_high_cash_001",
            family=OpportunityFamily.HIGH_CASH,
            source_refs=(source_ref(),),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            detected_at_utc=datetime(2026, 6, 21, 9, 3, tzinfo=UTC),
            expires_at_utc=datetime(2026, 6, 22, 9, 3),
        )

    with pytest.raises(ValueError, match="source_refs is required"):
        OpportunitySignal(
            signal_id="signal_high_cash_001",
            family=OpportunityFamily.HIGH_CASH,
            source_refs=(),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            detected_at_utc=datetime(2026, 6, 21, 9, 3, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="reason_codes is required"):
        OpportunitySignal(
            signal_id="signal_high_cash_001",
            family=OpportunityFamily.HIGH_CASH,
            source_refs=(source_ref(),),
            reason_codes=(),
            detected_at_utc=datetime(2026, 6, 21, 9, 3, tzinfo=UTC),
        )


def test_valid_lifecycle_path_reaches_approved_conversion_ready_state() -> None:
    current = candidate()

    for target in (
        IdeaLifecycleStatus.GENERATED,
        IdeaLifecycleStatus.ENRICHED,
        IdeaLifecycleStatus.SCORED,
        IdeaLifecycleStatus.GOVERNANCE_CHECKED,
        IdeaLifecycleStatus.READY_FOR_REVIEW,
        IdeaLifecycleStatus.REVIEWED_BY_ADVISOR,
        IdeaLifecycleStatus.APPROVED,
    ):
        current = transition_candidate(current, target)

    reviewed = IdeaCandidate(
        candidate_id=current.candidate_id,
        identity=current.identity,
        family=current.family,
        lifecycle_status=current.lifecycle_status,
        review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        evidence_packet=current.evidence_packet,
        source_signal_ids=current.source_signal_ids,
        score=current.score,
        created_at_utc=current.created_at_utc,
        updated_at_utc=current.updated_at_utc,
    )

    assert reviewed.ready_for_conversion is True


def test_invalid_lifecycle_transition_blocks_direct_conversion() -> None:
    with pytest.raises(InvalidLifecycleTransition) as error:
        transition_candidate(
            candidate(lifecycle_status=IdeaLifecycleStatus.GENERATED),
            IdeaLifecycleStatus.CONVERTED_TO_REPORT,
        )

    assert error.value.source is IdeaLifecycleStatus.GENERATED
    assert error.value.target is IdeaLifecycleStatus.CONVERTED_TO_REPORT


def test_lifecycle_graph_quarantines_downstream_authority_statuses() -> None:
    assert DOWNSTREAM_AUTHORITY_LIFECYCLE_STATUSES == frozenset(
        {
            IdeaLifecycleStatus.ACCEPTED,
            IdeaLifecycleStatus.EXECUTED,
        }
    )
    assert IdeaLifecycleStatus.ACCEPTED not in {
        *ALLOWED_LIFECYCLE_TRANSITIONS[IdeaLifecycleStatus.APPROVED],
        *ALLOWED_LIFECYCLE_TRANSITIONS[IdeaLifecycleStatus.CONVERTED_TO_PROPOSAL],
        *ALLOWED_LIFECYCLE_TRANSITIONS[IdeaLifecycleStatus.CONVERTED_TO_MANAGE_REVIEW],
        *ALLOWED_LIFECYCLE_TRANSITIONS[IdeaLifecycleStatus.CONVERTED_TO_REPORT],
    }
    assert (
        IdeaLifecycleStatus.EXECUTED
        not in ALLOWED_LIFECYCLE_TRANSITIONS[IdeaLifecycleStatus.ACCEPTED]
    )

    with pytest.raises(InvalidLifecycleTransition):
        transition_candidate(
            candidate(
                lifecycle_status=IdeaLifecycleStatus.APPROVED,
                review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
            ),
            IdeaLifecycleStatus.ACCEPTED,
        )
    with pytest.raises(InvalidLifecycleTransition):
        transition_candidate(
            candidate(
                lifecycle_status=IdeaLifecycleStatus.ACCEPTED,
                review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
            ),
            IdeaLifecycleStatus.EXECUTED,
        )

    closed_legacy = transition_candidate(
        candidate(
            lifecycle_status=IdeaLifecycleStatus.ACCEPTED,
            review_posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        ),
        IdeaLifecycleStatus.CLOSED,
    )
    assert closed_legacy.lifecycle_status is IdeaLifecycleStatus.CLOSED


def test_closed_lifecycle_is_terminal() -> None:
    with pytest.raises(InvalidLifecycleTransition):
        transition_candidate(
            candidate(
                lifecycle_status=IdeaLifecycleStatus.CLOSED,
                review_posture=ReviewPosture.NO_ACTION,
            ),
            IdeaLifecycleStatus.GENERATED,
        )


def test_review_decision_does_not_grant_downstream_authority() -> None:
    decision = ReviewDecision(
        review_id="review_001",
        posture=ReviewPosture.APPROVED_FOR_CONVERSION,
        reviewer_role="advisor",
        reason_codes=(ReasonCode.REVIEW_REQUIRED,),
        decided_at_utc=datetime(2026, 6, 21, 9, 4, tzinfo=UTC),
    )

    assert decision.grants_downstream_authority is False
    forbidden_review_values = {
        "approved_for_suitability",
        "approved_for_compliance",
        "approved_for_mandate",
        "approved_for_execution",
        "approved_for_client_communication",
    }
    assert forbidden_review_values.isdisjoint({posture.value for posture in ReviewPosture})


def test_review_decision_requires_reason_codes() -> None:
    with pytest.raises(ValueError, match="reason_codes is required"):
        ReviewDecision(
            review_id="review_001",
            posture=ReviewPosture.APPROVED_FOR_CONVERSION,
            reviewer_role="advisor",
            reason_codes=(),
            decided_at_utc=datetime(2026, 6, 21, 9, 4, tzinfo=UTC),
        )


def test_feedback_records_are_typed_and_time_aware() -> None:
    feedback = IdeaFeedback(
        feedback_id="feedback_001",
        outcome=FeedbackOutcome.USEFUL,
        reason=FeedbackReason.RELEVANT,
        taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
        actor_role="advisor",
        recorded_at_utc=datetime(2026, 6, 21, 9, 4, tzinfo=UTC),
    )

    assert feedback.outcome is FeedbackOutcome.USEFUL
    assert feedback.reason is FeedbackReason.RELEVANT
    assert feedback.taxonomy_version == FEEDBACK_TAXONOMY_VERSION

    with pytest.raises(ValueError, match="actor_role is required"):
        IdeaFeedback(
            feedback_id="feedback_001",
            outcome=FeedbackOutcome.USEFUL,
            reason=FeedbackReason.RELEVANT,
            taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
            actor_role=" ",
            recorded_at_utc=datetime(2026, 6, 21, 9, 4, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="recorded_at_utc must be timezone-aware"):
        IdeaFeedback(
            feedback_id="feedback_001",
            outcome=FeedbackOutcome.USEFUL,
            reason=FeedbackReason.RELEVANT,
            taxonomy_version=FEEDBACK_TAXONOMY_VERSION,
            actor_role="advisor",
            recorded_at_utc=datetime(2026, 6, 21, 9, 4),
        )


def test_conversion_intent_requires_approved_candidate_status() -> None:
    with pytest.raises(ValueError, match="requires approved source_status"):
        IdeaConversionIntent(
            conversion_intent_id="intent_001",
            candidate_id="idea_high_cash_001",
            target=ConversionTarget.REPORT_EVIDENCE,
            source_status=IdeaLifecycleStatus.READY_FOR_REVIEW,
            requested_at_utc=datetime(2026, 6, 21, 9, 5, tzinfo=UTC),
        )


def test_conversion_intent_allows_only_review_approved_source_status() -> None:
    intent = IdeaConversionIntent(
        conversion_intent_id="intent_001",
        candidate_id="idea_high_cash_001",
        target=ConversionTarget.REPORT_EVIDENCE,
        source_status=IdeaLifecycleStatus.APPROVED,
        requested_at_utc=datetime(2026, 6, 21, 9, 5, tzinfo=UTC),
    )

    assert intent.target is ConversionTarget.REPORT_EVIDENCE


def test_candidate_requires_source_signal_ids() -> None:
    with pytest.raises(ValueError, match="source_signal_ids is required"):
        IdeaCandidate(
            candidate_id="idea_high_cash_001",
            identity=initial_candidate_identity("idea_high_cash_001"),
            family=OpportunityFamily.HIGH_CASH,
            lifecycle_status=IdeaLifecycleStatus.GENERATED,
            review_posture=ReviewPosture.ADVISOR_REVIEW_REQUIRED,
            evidence_packet=evidence_packet(),
            source_signal_ids=(),
            created_at_utc=datetime(2026, 6, 21, 9, 2, tzinfo=UTC),
            updated_at_utc=datetime(2026, 6, 21, 9, 2, tzinfo=UTC),
        )


def test_conversion_outcome_validates_optional_downstream_reference() -> None:
    outcome = IdeaConversionOutcome(
        conversion_outcome_id="outcome_001",
        conversion_intent_id="intent_001",
        status=ConversionOutcomeStatus.ACCEPTED,
        downstream_reference="report-job-001",
        recorded_at_utc=datetime(2026, 6, 21, 9, 6, tzinfo=UTC),
    )

    assert outcome.downstream_reference == "report-job-001"

    with pytest.raises(ValueError, match="downstream_reference is required"):
        IdeaConversionOutcome(
            conversion_outcome_id="outcome_001",
            conversion_intent_id="intent_001",
            status=ConversionOutcomeStatus.ACCEPTED,
            downstream_reference=" ",
            recorded_at_utc=datetime(2026, 6, 21, 9, 6, tzinfo=UTC),
        )


def test_domain_models_are_immutable() -> None:
    source = source_ref()

    with pytest.raises(FrozenInstanceError):
        source.product_id = "lotus-risk:RiskMetricsReport:v1"  # type: ignore[misc]


def test_score_policy_is_bounded_and_versioned() -> None:
    score = IdeaScore(
        policy_version="idle-liquidity-v2",
        score=Decimal("75"),
        reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
        contributions=(_score_contribution(),),
    )

    assert score.policy_version == "idle-liquidity-v2"


def test_score_policy_requires_reason_codes() -> None:
    with pytest.raises(ValueError, match="reason_codes is required"):
        IdeaScore(
            policy_version="idle-liquidity-v2",
            score=Decimal("75"),
            reason_codes=(),
            contributions=(_score_contribution(),),
        )


def test_score_policy_requires_reconstructable_contributions() -> None:
    with pytest.raises(ValueError, match="contributions is required"):
        IdeaScore(
            policy_version="idle-liquidity-v2",
            score=Decimal("75"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            contributions=(),
        )


@pytest.mark.parametrize("score", [Decimal("-1"), Decimal("101")])
def test_score_policy_rejects_out_of_bounds_values(score: Decimal) -> None:
    with pytest.raises(ValueError, match="score must be between 0 and 100"):
        IdeaScore(
            policy_version="idle-liquidity-v2",
            score=score,
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            contributions=(_score_contribution(),),
        )


def test_score_contribution_rejects_mismatched_weighted_value() -> None:
    with pytest.raises(ValueError, match="input_score multiplied by weight"):
        _score_contribution(
            input_score=Decimal("80"),
            weight=Decimal("0.50"),
            contribution=Decimal("39.99"),
        )


@pytest.mark.parametrize("weight", (Decimal("-0.01"), Decimal("1.01")))
def test_score_contribution_rejects_out_of_range_weight(weight: Decimal) -> None:
    with pytest.raises(ValueError, match="weight must be between 0 and 1"):
        _score_contribution(weight=weight)


def test_score_rejects_duplicate_components() -> None:
    contribution = _score_contribution(
        input_score=Decimal("75"),
        weight=Decimal("0.50"),
        contribution=Decimal("37.50"),
    )

    with pytest.raises(ValueError, match="components must be unique"):
        IdeaScore(
            policy_version="idle-liquidity-v2",
            score=Decimal("75"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            contributions=(contribution, contribution),
        )


def test_score_rejects_weights_that_do_not_sum_to_one() -> None:
    with pytest.raises(ValueError, match="weights must sum to 1"):
        IdeaScore(
            policy_version="idle-liquidity-v2",
            score=Decimal("37.50"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            contributions=(
                _score_contribution(
                    input_score=Decimal("75"),
                    weight=Decimal("0.50"),
                    contribution=Decimal("37.50"),
                ),
            ),
        )


def test_score_rejects_scalar_that_cannot_be_reconstructed() -> None:
    with pytest.raises(ValueError, match="contributions minus conflict penalty"):
        IdeaScore(
            policy_version="idle-liquidity-v2",
            score=Decimal("74.99"),
            reason_codes=(ReasonCode.HIGH_CASH_RATIO,),
            contributions=(_score_contribution(),),
        )


def test_score_reconstructs_zero_after_conflict_penalty_floor() -> None:
    score = IdeaScore(
        policy_version="idle-liquidity-v2",
        score=Decimal("0"),
        reason_codes=(ReasonCode.HIGH_CASH_RATIO, ReasonCode.CONFLICT_PENALTY),
        contributions=(_score_contribution(input_score=Decimal("10"), contribution=Decimal("10")),),
        conflict_penalty_applied=Decimal("15"),
    )

    assert score.score == Decimal("0")


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"material_fingerprint": "not-a-digest"}, "must use sha256"),
        ({"material_version": 0}, "material_version must be positive"),
        ({"evidence_version": 0}, "evidence_version must be positive"),
        (
            {"material_version": 2, "supersedes_material_version": 0},
            "supersedes_material_version must be positive",
        ),
        (
            {"material_version": 2, "supersedes_material_version": 2},
            "supersedes_material_version must precede material_version",
        ),
    ),
)
def test_candidate_identity_rejects_invalid_version_lineage(
    overrides: dict[str, object],
    message: str,
) -> None:
    values: dict[str, object] = {
        "business_identity_id": "business-high-cash-001",
        "policy_version": "opportunity-identity-v1",
        "material_fingerprint": "sha256:material",
        "material_version": 1,
        "evidence_version": 1,
        "change_reason": CandidateChangeReason.INITIAL_DETECTION,
        "supersedes_material_version": None,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        CandidateIdentity(**values)  # type: ignore[arg-type]


def _score_contribution(
    *,
    input_score: Decimal = Decimal("75"),
    weight: Decimal = Decimal("1"),
    contribution: Decimal = Decimal("75.00"),
) -> ScoreContribution:
    return ScoreContribution(
        component=ScoreComponent.MATERIALITY,
        input_score=input_score,
        weight=weight,
        contribution=contribution,
    )
