from __future__ import annotations

from datetime import UTC, date, datetime

from app.domain.ideas import EvidenceFreshness, ReasonCode, SourceRef, SourceSystem, UnsupportedEvidenceReason
from app.domain.source_temporal import source_temporal_violation


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
            requested_as_of_date=date(2026, 6, 21),
            evaluated_at_utc=evaluated_at,
            source_refs=(_source_ref(as_of_date=date(2026, 6, 21), generated_at_utc=evaluated_at),),
        )
        is None
    )


def test_source_temporal_contract_rejects_business_date_mismatch() -> None:
    violation = source_temporal_violation(
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
