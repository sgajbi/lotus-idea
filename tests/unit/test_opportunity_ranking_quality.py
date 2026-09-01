from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from typing import cast

import pytest

from app.application.opportunity_effectiveness import OpportunityEffectivenessDataError
from app.application.opportunity_ranking_quality import (
    RankingQualityBoundExceeded,
    RankingQualityDataError,
    build_ranking_presentation_facts,
    build_ranking_quality,
    presentation_evidence_hash,
)
from app.domain import (
    CandidateChangeReason,
    CandidateVersionHistoryEntry,
    FeedbackReason,
    IdeaLifecycleStatus,
    OpportunityFamily,
    ReviewAction,
)
from app.domain.ranking_evaluation import RankingPresentationFact
from tests.unit import test_opportunity_effectiveness as fixtures


def test_ranking_quality_application_translates_invalid_snapshot_facts() -> None:
    with pytest.raises(RankingQualityDataError, match="RankingPresentationFact"):
        build_ranking_quality((cast(RankingPresentationFact, "invalid"),))


def test_ranking_presentation_fact_builder_rejects_cross_tenant_receipt_directly() -> None:
    candidate = fixtures._candidate(
        "idea-ranking-cross-tenant-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=fixtures.WINDOW_START + timedelta(hours=1),
    )
    record = fixtures._record(candidate)
    receipt = replace(
        fixtures._receipt(
            candidate,
            receipt_id="receipt-ranking-cross-tenant-001",
            rank=1,
            presented_at=fixtures.WINDOW_START + timedelta(hours=2),
        ),
        tenant_id="tenant-b",
    )

    with pytest.raises(RankingQualityDataError, match="tenant does not match"):
        build_ranking_presentation_facts(
            fixtures._snapshot(record, receipts=(receipt,)),
            records=(record,),
            evaluated_at_utc=fixtures.EVALUATED_AT,
        )


def test_ranking_presentation_fact_builder_enforces_its_independent_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.application.opportunity_ranking_quality.MAX_RANKING_PRESENTATION_FACTS",
        1,
    )
    candidates = tuple(
        fixtures._candidate(
            f"idea-ranking-bound-{index}",
            family=OpportunityFamily.HIGH_CASH,
            score=Decimal("91"),
            created_at=fixtures.WINDOW_START + timedelta(hours=1),
        )
        for index in range(2)
    )
    records = tuple(fixtures._record(candidate) for candidate in candidates)
    receipts = tuple(
        replace(
            fixtures._receipt(
                candidate,
                receipt_id=f"receipt-ranking-bound-{index}",
                rank=index + 1,
                presented_at=fixtures.WINDOW_START + timedelta(hours=2),
            ),
            visible_candidate_count=2,
        )
        for index, candidate in enumerate(candidates)
    )

    with pytest.raises(RankingQualityBoundExceeded, match="fact bound"):
        build_ranking_presentation_facts(
            fixtures._snapshot(*records, receipts=receipts),
            records=records,
            evaluated_at_utc=fixtures.EVALUATED_AT,
        )


def test_presentation_version_resolution_rejects_ambiguous_and_missing_versions() -> None:
    candidate = fixtures._candidate(
        "idea-ranking-version-resolution-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=fixtures.WINDOW_START + timedelta(hours=1),
    )
    receipt = replace(
        fixtures._receipt(
            candidate,
            receipt_id="receipt-ranking-version-resolution-001",
            rank=1,
            presented_at=fixtures.WINDOW_START + timedelta(hours=2),
        ),
        visible_candidate_count=1,
    )
    version = CandidateVersionHistoryEntry(
        candidate_id=candidate.candidate_id,
        business_identity_id=candidate.identity.business_identity_id,
        material_fingerprint=candidate.identity.material_fingerprint,
        material_version=1,
        evidence_version=1,
        change_reason=CandidateChangeReason.INITIAL_DETECTION,
        source_lifecycle_status=None,
        resulting_lifecycle_status=IdeaLifecycleStatus.GENERATED,
        supersedes_material_version=None,
        evidence_hash=candidate.evidence_packet.lineage_ref.content_hash,
        recorded_at_utc=candidate.created_at_utc,
    )
    ambiguous = replace(
        fixtures._record(candidate),
        version_history=(version, replace(version, evidence_hash=f"sha256:{'7' * 64}")),
    )

    with pytest.raises(RankingQualityDataError, match="multiple candidate versions"):
        presentation_evidence_hash(ambiguous, receipt)
    with pytest.raises(RankingQualityDataError, match="does not resolve"):
        presentation_evidence_hash(
            fixtures._record(candidate),
            replace(receipt, candidate_evidence_version=99),
        )


def test_ranking_relevance_rejects_conflicting_same_instant_human_evidence() -> None:
    candidate = fixtures._candidate(
        "idea-ranking-conflict-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=fixtures.WINDOW_START + timedelta(hours=1),
    )
    record = fixtures._record(
        candidate,
        review=fixtures._review(
            candidate.candidate_id,
            action=ReviewAction.APPROVE_FOR_CONVERSION,
            decided_at=fixtures.WINDOW_START + timedelta(hours=6),
        ),
        feedback_reason=FeedbackReason.NOT_RELEVANT,
    )
    receipt = replace(
        fixtures._receipt(
            candidate,
            receipt_id="receipt-ranking-conflict-001",
            rank=1,
            presented_at=fixtures.WINDOW_START + timedelta(hours=2),
        ),
        visible_candidate_count=1,
    )

    with pytest.raises(RankingQualityDataError, match="conflicting human judgments"):
        build_ranking_presentation_facts(
            fixtures._snapshot(record, receipts=(receipt,)),
            records=(record,),
            evaluated_at_utc=fixtures.EVALUATED_AT,
        )


def test_effectiveness_snapshot_translates_invalid_queue_snapshot_and_version_evidence() -> None:
    first = fixtures._candidate(
        "idea-ranking-invalid-snapshot-001",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("91"),
        created_at=fixtures.WINDOW_START + timedelta(hours=1),
    )
    second = fixtures._candidate(
        "idea-ranking-invalid-snapshot-002",
        family=OpportunityFamily.HIGH_CASH,
        score=Decimal("90"),
        created_at=fixtures.WINDOW_START + timedelta(hours=1),
    )
    presented_at = fixtures.WINDOW_START + timedelta(hours=2)
    duplicate_rank_receipts = tuple(
        replace(
            fixtures._receipt(
                candidate,
                receipt_id=f"receipt-{candidate.candidate_id}",
                rank=1,
                presented_at=presented_at,
            ),
            visible_candidate_count=2,
        )
        for candidate in (first, second)
    )

    with pytest.raises(OpportunityEffectivenessDataError, match="ranks must be unique"):
        fixtures._build(
            fixtures._snapshot(
                fixtures._record(first),
                fixtures._record(second),
                receipts=duplicate_rank_receipts,
            )
        )

    unresolved_receipt = replace(
        duplicate_rank_receipts[0],
        visible_candidate_count=1,
        candidate_evidence_version=99,
    )
    with pytest.raises(OpportunityEffectivenessDataError, match="does not resolve"):
        fixtures._build(fixtures._snapshot(fixtures._record(first), receipts=(unresolved_receipt,)))
