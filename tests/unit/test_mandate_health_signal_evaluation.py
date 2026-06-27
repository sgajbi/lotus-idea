from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.domain import (
    EvidenceFreshness,
    IdeaLifecycleStatus,
    MandateHealthSignalInput,
    MandateHealthSignalPolicy,
    OpportunityFamily,
    ReasonCode,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_mandate_health_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> MandateHealthSignalPolicy:
    return MandateHealthSignalPolicy(
        policy_version="allocation-drift-mandate-review-v1",
        minimum_workflow_decision_count=1,
        minimum_lineage_edge_count=1,
        candidate_score=Decimal("70"),
    )


def source_ref(freshness: EvidenceFreshness = EvidenceFreshness.CURRENT) -> SourceRef:
    return SourceRef(
        product_id="lotus-manage:PortfolioActionRegister:v1",
        source_system=SourceSystem.LOTUS_MANAGE,
        product_version="v1",
        route="/api/v1/rebalance/supportability/summary",
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash="sha256:portfolio-action-register",
        data_quality_status="ready",
        freshness=freshness,
    )


def mandate_input(
    *,
    workflow_decision_count: int | None = 2,
    lineage_edge_count: int | None = 4,
    supportability_state: str | None = "ready",
    portfolio_scope_confirmed: bool = True,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    duplicate_of_candidate_id: str | None = None,
    include_source_ref: bool = True,
) -> MandateHealthSignalInput:
    return MandateHealthSignalInput(
        as_of_date=AS_OF_DATE,
        workflow_decision_count=workflow_decision_count,
        lineage_edge_count=lineage_edge_count,
        manage_supportability_state=supportability_state,
        portfolio_scope_confirmed=portfolio_scope_confirmed,
        action_register_ref=source_ref(freshness) if include_source_ref else None,
        evaluated_at_utc=EVALUATED_AT,
        entitlement_allowed=entitlement_allowed,
        duplicate_of_candidate_id=duplicate_of_candidate_id,
    )


def test_mandate_health_positive_case_creates_pm_review_candidate() -> None:
    first = evaluate_mandate_health_signal(mandate_input(), policy())
    second = evaluate_mandate_health_signal(mandate_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.ALLOCATION_DRIFT
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.PM_REVIEW_REQUIRED
    assert first.reason_codes == (
        ReasonCode.ALLOCATION_DRIFT_ATTENTION,
        ReasonCode.REVIEW_REQUIRED,
    )


def test_mandate_health_store_wide_manage_posture_blocks_portfolio_claim() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(portfolio_scope_confirmed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_mandate_health_non_ready_manage_posture_blocks_positive_claim() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(supportability_state="degraded"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.SOURCE_UNCERTIFIED,)


def test_mandate_health_stale_source_blocks_positive_claim() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_mandate_health_missing_source_ref_blocks_positive_claim() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(include_source_ref=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_mandate_health_missing_counts_block_positive_claim() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(workflow_decision_count=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_mandate_health_missing_supportability_state_blocks_positive_claim() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(supportability_state=None),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_mandate_health_below_threshold_does_not_create_candidate() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(workflow_decision_count=0),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_mandate_health_rejects_negative_source_counts() -> None:
    with pytest.raises(ValueError, match="workflow_decision_count must be non-negative"):
        evaluate_mandate_health_signal(
            mandate_input(workflow_decision_count=-1),
            policy(),
        )
    with pytest.raises(ValueError, match="lineage_edge_count must be non-negative"):
        evaluate_mandate_health_signal(
            mandate_input(lineage_edge_count=-1),
            policy(),
        )


def test_mandate_health_duplicate_source_is_suppressed() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(duplicate_of_candidate_id="idea_allocation_drift_existing"),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.SUPPRESSED
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.DUPLICATE_SUPPRESSED,)


def test_mandate_health_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_mandate_health_signal(
        mandate_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_mandate_health_requires_timezone_aware_evaluation_time() -> None:
    invalid_input = MandateHealthSignalInput(
        as_of_date=AS_OF_DATE,
        workflow_decision_count=2,
        lineage_edge_count=4,
        manage_supportability_state="ready",
        portfolio_scope_confirmed=True,
        action_register_ref=source_ref(),
        evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
    )

    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_mandate_health_signal(invalid_input, policy())


def test_mandate_health_policy_rejects_negative_threshold() -> None:
    with pytest.raises(ValueError, match="minimum_workflow_decision_count"):
        MandateHealthSignalPolicy(
            policy_version="allocation-drift-mandate-review-v1",
            minimum_workflow_decision_count=-1,
            minimum_lineage_edge_count=1,
            candidate_score=Decimal("70"),
        )

    with pytest.raises(ValueError, match="minimum_lineage_edge_count"):
        MandateHealthSignalPolicy(
            policy_version="allocation-drift-mandate-review-v1",
            minimum_workflow_decision_count=1,
            minimum_lineage_edge_count=-1,
            candidate_score=Decimal("70"),
        )


def test_mandate_health_policy_requires_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        MandateHealthSignalPolicy(
            policy_version=" ",
            minimum_workflow_decision_count=1,
            minimum_lineage_edge_count=1,
            candidate_score=Decimal("70"),
        )


@pytest.mark.parametrize("score", [Decimal("-0.01"), Decimal("100.01")])
def test_mandate_health_policy_rejects_invalid_candidate_score(score: Decimal) -> None:
    with pytest.raises(ValueError, match="candidate_score"):
        MandateHealthSignalPolicy(
            policy_version="allocation-drift-mandate-review-v1",
            minimum_workflow_decision_count=1,
            minimum_lineage_edge_count=1,
            candidate_score=score,
        )
