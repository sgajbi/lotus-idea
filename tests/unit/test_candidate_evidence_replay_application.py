from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app.application.candidate_evidence_replay import ReplayCandidateEvidenceCommand
from app.domain import EvidenceFreshness, SourceRef, SourceSystem


def source_ref() -> SourceRef:
    return SourceRef(
        product_id="lotus-core:PortfolioStateSnapshot:v1",
        source_system=SourceSystem.LOTUS_CORE,
        product_version="v1",
        route="/integration/portfolios/{portfolioRef}/core-snapshot",
        as_of_date=date(2026, 6, 21),
        generated_at_utc=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
        content_hash="sha256:portfolio-state-snapshot-demo",
        data_quality_status="complete",
        freshness=EvidenceFreshness.CURRENT,
    )


def test_replay_candidate_evidence_command_requires_candidate_and_source_refs() -> None:
    with pytest.raises(ValueError, match="candidate_id is required"):
        ReplayCandidateEvidenceCommand(
            candidate_id=" ",
            current_source_refs=(source_ref(),),
        )

    with pytest.raises(ValueError, match="current_source_refs is required"):
        ReplayCandidateEvidenceCommand(
            candidate_id="idea_high_cash_001",
            current_source_refs=(),
        )
