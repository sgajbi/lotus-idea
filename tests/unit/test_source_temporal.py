from __future__ import annotations

from datetime import UTC, date, datetime

from app.domain.ideas import (
    EvidenceFreshness,
    OpportunityFamily,
    ReasonCode,
    SourceRef,
    SourceSystem,
    UnsupportedEvidenceReason,
)
from app.domain.source_temporal import source_temporal_violation
from app.domain.source_temporal import (
    SOURCE_TEMPORAL_CONTRACTS,
    SOURCE_TEMPORAL_CONTRACT_VERSION,
    SourceBusinessDateRule,
    SourceCorrectionIdentityRule,
    SourceGeneratedTimeRule,
)


def _source_ref(*, as_of_date: date, generated_at_utc: datetime) -> SourceRef:
    return SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/source/portfolio-state",
        as_of_date=as_of_date,
        generated_at_utc=generated_at_utc,
        content_hash="sha256:source-temporal-test",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def test_source_temporal_contract_accepts_exact_date_and_generation_boundary() -> None:
    evaluated_at = datetime(2026, 6, 21, 10, tzinfo=UTC)

    assert (
        source_temporal_violation(
            family=OpportunityFamily.HIGH_CASH,
            requested_as_of_date=date(2026, 6, 21),
            evaluated_at_utc=evaluated_at,
            source_refs=(_source_ref(as_of_date=date(2026, 6, 21), generated_at_utc=evaluated_at),),
        )
        is None
    )


def test_source_temporal_contract_rejects_business_date_mismatch() -> None:
    violation = source_temporal_violation(
        family=OpportunityFamily.HIGH_CASH,
        requested_as_of_date=date(2026, 6, 21),
        evaluated_at_utc=datetime(2026, 6, 21, 10, tzinfo=UTC),
        source_refs=(
            _source_ref(
                as_of_date=date(2026, 6, 20),
                generated_at_utc=datetime(2026, 6, 21, 9, tzinfo=UTC),
            ),
        ),
    )

    assert violation == (
        ReasonCode.SOURCE_DATE_MISMATCH,
        UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
    )


def test_source_temporal_contract_rejects_future_generated_evidence() -> None:
    violation = source_temporal_violation(
        family=OpportunityFamily.HIGH_CASH,
        requested_as_of_date=date(2026, 6, 21),
        evaluated_at_utc=datetime(2026, 6, 21, 10, tzinfo=UTC),
        source_refs=(
            _source_ref(
                as_of_date=date(2026, 6, 21),
                generated_at_utc=datetime(2026, 6, 21, 10, 0, 1, tzinfo=UTC),
            ),
        ),
    )

    assert violation == (
        ReasonCode.SOURCE_GENERATED_AFTER_EVALUATION,
        UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
    )


def test_every_opportunity_family_declares_the_versioned_exact_date_contract() -> None:
    assert set(SOURCE_TEMPORAL_CONTRACTS) == set(OpportunityFamily)
    for family, contract in SOURCE_TEMPORAL_CONTRACTS.items():
        assert contract.contract_version == SOURCE_TEMPORAL_CONTRACT_VERSION
        assert contract.family is family
        assert contract.business_date_rule is SourceBusinessDateRule.EXACT_REQUEST_DATE
        assert contract.generated_time_rule is SourceGeneratedTimeRule.NOT_AFTER_EVALUATION
        assert (
            contract.correction_identity_rule
            is SourceCorrectionIdentityRule.NEW_CONTENT_HASH_CREATES_NEW_CANDIDATE_IDENTITY
        )


def test_multi_source_temporal_contract_blocks_the_first_conflicting_source() -> None:
    evaluated_at = datetime(2026, 6, 21, 10, tzinfo=UTC)
    violation = source_temporal_violation(
        family=OpportunityFamily.CONCENTRATION,
        requested_as_of_date=date(2026, 6, 21),
        evaluated_at_utc=evaluated_at,
        source_refs=(
            _source_ref(as_of_date=date(2026, 6, 21), generated_at_utc=evaluated_at),
            _source_ref(as_of_date=date(2026, 6, 20), generated_at_utc=evaluated_at),
            _source_ref(
                as_of_date=date(2026, 6, 21),
                generated_at_utc=datetime(2026, 6, 21, 10, 0, 1, tzinfo=UTC),
            ),
        ),
    )

    assert violation == (
        ReasonCode.SOURCE_DATE_MISMATCH,
        UnsupportedEvidenceReason.SOURCE_TEMPORAL_MISMATCH,
    )
