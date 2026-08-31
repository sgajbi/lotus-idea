from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from app.domain import (
    BondMaturitySignalInput,
    BondMaturitySignalPolicy,
    CandidateChangeReason,
    CandidatePersistenceDecision,
    EvidenceFreshness,
    IdeaLifecycleStatus,
    InMemoryIdeaRepository,
    OpportunityFamily,
    ReasonCode,
    ReviewAccessScope,
    ReviewPosture,
    SignalEvaluationOutcome,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
    evaluate_bond_maturity_signal,
)


AS_OF_DATE = date(2026, 6, 21)
EVALUATED_AT = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def policy() -> BondMaturitySignalPolicy:
    return BondMaturitySignalPolicy(
        policy_version="bond-maturity-review-v2",
        maturity_window_days=30,
    )


def source_ref(
    product_id: str,
    *,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    content_hash_suffix: str = "",
) -> SourceRef:
    route_by_product = {
        "lotus-core:HoldingsAsOf:v1": "/portfolios/{portfolio_id}/positions",
        "lotus-core:PortfolioMaturitySummary:v1": ("/portfolios/{portfolio_id}/maturity-summary"),
    }
    return SourceRef(
        product_id=product_id,
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route=route_by_product[product_id],
        as_of_date=AS_OF_DATE,
        generated_at_utc=EVALUATED_AT,
        content_hash=f"sha256:{product_id}{content_hash_suffix}",
        data_quality_status="complete",
        freshness=freshness,
    )


def maturity_input(
    *,
    next_maturity_date: date | None = date(2026, 7, 10),
    maturing_position_count: int | None = 2,
    freshness: EvidenceFreshness = EvidenceFreshness.CURRENT,
    entitlement_allowed: bool = True,
    include_maturity_fact_ref: bool = True,
    evaluated_at_utc: datetime = EVALUATED_AT,
) -> BondMaturitySignalInput:
    return BondMaturitySignalInput(
        as_of_date=AS_OF_DATE,
        source_reported_next_maturity_date=next_maturity_date,
        source_reported_maturing_position_count=maturing_position_count,
        holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1", freshness=freshness),
        maturity_fact_ref=(
            source_ref(
                "lotus-core:PortfolioMaturitySummary:v1",
                freshness=freshness,
                content_hash_suffix=":maturity",
            )
            if include_maturity_fact_ref
            else None
        ),
        evaluated_at_utc=evaluated_at_utc,
        entitlement_allowed=entitlement_allowed,
    )


def test_bond_maturity_positive_case_creates_review_candidate() -> None:
    first = evaluate_bond_maturity_signal(maturity_input(), policy())
    second = evaluate_bond_maturity_signal(maturity_input(), policy())

    assert first.outcome is SignalEvaluationOutcome.CANDIDATE_CREATED
    assert first.signal is not None
    assert first.candidate is not None
    assert second.candidate is not None
    assert first.signal.family is OpportunityFamily.BOND_MATURITY
    assert first.candidate.candidate_id == second.candidate.candidate_id
    assert first.candidate.lifecycle_status is IdeaLifecycleStatus.GENERATED
    assert first.candidate.review_posture is ReviewPosture.ADVISOR_REVIEW_REQUIRED
    assert first.reason_codes == (ReasonCode.MATURITY_WINDOW, ReasonCode.REVIEW_REQUIRED)
    assert first.candidate.source_signal_ids == (first.signal.signal_id,)
    assert first.candidate.evidence_packet.source_refs == first.signal.source_refs
    assert first.candidate.evidence_packet.lineage_ref is not None
    expected_expiry = datetime(2026, 7, 11, tzinfo=UTC)
    assert first.signal.expires_at_utc == expected_expiry
    assert first.candidate.evidence_packet.applicability_expires_at_utc == expected_expiry
    assert second.signal is not None
    assert first.signal.signal_id == second.signal.signal_id
    assert (
        first.candidate.evidence_packet.evidence_packet_id
        == second.candidate.evidence_packet.evidence_packet_id
    )
    assert (
        first.candidate.evidence_packet.lineage_ref.lineage_id
        == second.candidate.evidence_packet.lineage_ref.lineage_id
    )


@pytest.mark.parametrize(
    ("evaluated_at_utc", "expected_outcome"),
    [
        (
            datetime(2026, 7, 10, 23, 59, 59, 999999, tzinfo=UTC),
            SignalEvaluationOutcome.CANDIDATE_CREATED,
        ),
        (datetime(2026, 7, 11, tzinfo=UTC), SignalEvaluationOutcome.NOT_ELIGIBLE),
        (datetime(2026, 7, 12, tzinfo=UTC), SignalEvaluationOutcome.NOT_ELIGIBLE),
    ],
)
def test_bond_maturity_enforces_exact_contractual_date_expiry_boundary(
    evaluated_at_utc: datetime,
    expected_outcome: SignalEvaluationOutcome,
) -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(evaluated_at_utc=evaluated_at_utc),
        policy(),
    )

    assert result.outcome is expected_outcome
    if expected_outcome is SignalEvaluationOutcome.CANDIDATE_CREATED:
        assert result.candidate is not None
    else:
        assert result.candidate is None
        assert result.reason_codes == (ReasonCode.OPPORTUNITY_NO_LONGER_ELIGIBLE,)


def test_bond_maturity_score_increases_with_urgency_and_position_count() -> None:
    later_single = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=date(2026, 7, 20), maturing_position_count=1),
        policy(),
    )
    imminent_multiple = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=date(2026, 6, 22), maturing_position_count=5),
        policy(),
    )

    assert later_single.candidate is not None and later_single.candidate.score is not None
    assert imminent_multiple.candidate is not None
    assert imminent_multiple.candidate.score is not None
    assert imminent_multiple.candidate.score.score > later_single.candidate.score.score


def test_bond_maturity_source_correction_preserves_candidate_and_versions_evidence() -> None:
    source_input = maturity_input()
    assert source_input.holdings_ref is not None
    corrected_input = replace(
        source_input,
        holdings_ref=replace(
            source_input.holdings_ref,
            content_hash="sha256:lotus-core:HoldingsAsOf:v1:correction-2",
        ),
    )

    original = evaluate_bond_maturity_signal(source_input, policy())
    corrected = evaluate_bond_maturity_signal(corrected_input, policy())

    assert original.signal is not None
    assert corrected.signal is not None
    assert original.candidate is not None
    assert corrected.candidate is not None
    assert original.candidate.candidate_id == corrected.candidate.candidate_id
    assert original.signal.signal_id != corrected.signal.signal_id
    assert (
        original.candidate.evidence_packet.evidence_packet_id
        != corrected.candidate.evidence_packet.evidence_packet_id
    )
    assert (
        original.candidate.evidence_packet.lineage_ref.lineage_id
        != corrected.candidate.evidence_packet.lineage_ref.lineage_id
    )
    assert (
        original.candidate.evidence_packet.lineage_ref.content_hash
        != corrected.candidate.evidence_packet.lineage_ref.content_hash
    )
    assert corrected.candidate.evidence_packet.source_refs[0].content_hash.endswith("correction-2")
    assert (
        corrected.candidate.evidence_packet.lineage_ref.source_refs
        == corrected.candidate.evidence_packet.source_refs
    )


def test_changed_contractual_maturity_reopens_with_new_material_expiry() -> None:
    scope = ReviewAccessScope(
        tenant_id="tenant-a",
        book_id="book-a",
        portfolio_id="portfolio-a",
        client_id="client-a",
    )
    original = evaluate_bond_maturity_signal(
        replace(maturity_input(next_maturity_date=date(2026, 7, 10)), access_scope=scope),
        policy(),
    )
    changed = evaluate_bond_maturity_signal(
        replace(maturity_input(next_maturity_date=date(2026, 7, 12)), access_scope=scope),
        policy(),
    )
    assert original.candidate is not None
    assert changed.candidate is not None
    repository = InMemoryIdeaRepository()
    accepted = repository.persist_candidate(
        original.candidate,
        idempotency_key="bond-maturity-original",
        payload={"candidate_id": original.candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=EVALUATED_AT,
    )
    assert accepted.record is not None
    repository.record_lifecycle_transition(
        original.candidate.candidate_id,
        IdeaLifecycleStatus.EXPIRED,
        idempotency_key="bond-maturity-original-expired",
        payload={"candidate_id": original.candidate.candidate_id},
        actor_subject="candidate-expiry-worker",
        occurred_at_utc=datetime(2026, 7, 11, tzinfo=UTC),
    )

    reopened = repository.persist_candidate(
        changed.candidate,
        idempotency_key="bond-maturity-changed",
        payload={"candidate_id": changed.candidate.candidate_id},
        actor_subject="signal-ingestion-worker",
        occurred_at_utc=datetime(2026, 7, 11, 1, 0, tzinfo=UTC),
    )

    assert reopened.decision is CandidatePersistenceDecision.RECURRENT_CONDITION_REOPENED
    assert reopened.record is not None
    assert reopened.record.candidate.identity.material_version == 2
    assert (
        reopened.record.candidate.identity.change_reason
        is CandidateChangeReason.RECURRENT_CONDITION
    )
    assert reopened.record.candidate.evidence_packet.applicability_expires_at_utc == datetime(
        2026, 7, 13, tzinfo=UTC
    )


def test_bond_maturity_not_eligible_outside_maturity_window() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=date(2026, 8, 1)),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_bond_maturity_not_eligible_without_maturing_positions() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(maturing_position_count=0),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_bond_maturity_not_eligible_for_supported_empty_maturity_window() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=None, maturing_position_count=0),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.NOT_ELIGIBLE
    assert result.candidate is None
    assert result.reason_codes == (ReasonCode.BELOW_MATERIALITY,)


def test_bond_maturity_blocks_missing_maturity_source_ref() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(include_maturity_fact_ref=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_PARTIAL,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_bond_maturity_blocks_missing_maturity_date() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(next_maturity_date=None, maturing_position_count=1),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.MISSING_SOURCE,)


def test_bond_maturity_blocks_stale_source() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(freshness=EvidenceFreshness.STALE),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.reason_codes == (ReasonCode.SOURCE_STALE,)
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.STALE_SOURCE,)


def test_bond_maturity_entitlement_denial_blocks_positive_claim() -> None:
    result = evaluate_bond_maturity_signal(
        maturity_input(entitlement_allowed=False),
        policy(),
    )

    assert result.outcome is SignalEvaluationOutcome.BLOCKED
    assert result.unsupported_reasons == (UnsupportedEvidenceReason.ENTITLEMENT_DENIED,)


def test_bond_maturity_rejects_negative_maturing_position_count() -> None:
    with pytest.raises(
        ValueError,
        match="source_reported_maturing_position_count must be non-negative",
    ):
        evaluate_bond_maturity_signal(
            maturity_input(maturing_position_count=-1),
            policy(),
        )


def test_bond_maturity_requires_timezone_aware_evaluation_time() -> None:
    with pytest.raises(ValueError, match="evaluated_at_utc must be timezone-aware"):
        evaluate_bond_maturity_signal(
            BondMaturitySignalInput(
                as_of_date=AS_OF_DATE,
                source_reported_next_maturity_date=date(2026, 7, 10),
                source_reported_maturing_position_count=2,
                holdings_ref=source_ref("lotus-core:HoldingsAsOf:v1"),
                maturity_fact_ref=source_ref(
                    "lotus-core:HoldingsAsOf:v1",
                    content_hash_suffix=":maturity",
                ),
                evaluated_at_utc=datetime(2026, 6, 21, 10, 0),
            ),
            policy(),
        )


def test_bond_maturity_policy_rejects_invalid_window() -> None:
    with pytest.raises(ValueError, match="maturity_window_days must be between 1 and 366"):
        BondMaturitySignalPolicy(
            policy_version="bond-maturity-review-v2",
            maturity_window_days=0,
        )


def test_bond_maturity_policy_requires_version() -> None:
    with pytest.raises(ValueError, match="policy_version is required"):
        BondMaturitySignalPolicy(
            policy_version=" ",
            maturity_window_days=30,
        )
